import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pathlib import Path
import faiss
import psutil
from datetime import datetime

from app.core.config import settings


class HybridVectorDB:
    """Hybrid vector database that combines HNSW and Flat indexing for optimal performance.
    
    Uses HNSW for fast initial search and flat indexing for:
    1. Final precise ranking of top candidates
    2. When memory pressure exceeds the configured threshold
    """
    
    def __init__(self, 
                 db_path: str = None,
                 memory_threshold: float = 0.85,
                 use_hybrid: bool = True,
                 hnsw_m: int = 32,
                 ef_construction: int = 200,
                 ef_search: int = 128,
                 rerank_size: int = 30):
        """Initialize the hybrid vector database.
        
        Args:
            db_path: Path to the directory where vector data will be stored
            memory_threshold: Memory threshold (0-1) to switch to flat indexing
            use_hybrid: Whether to use hybrid indexing or fall back to flat indexing
            hnsw_m: HNSW M parameter (connections per layer)
            ef_construction: HNSW efConstruction parameter (build accuracy)
            ef_search: HNSW efSearch parameter (search accuracy)
            rerank_size: Number of candidates to re-rank using flat indexing
        """
        self.db_path = Path(db_path or settings.VECTOR_DB_PATH)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Configuration parameters
        self.memory_threshold = memory_threshold
        self.use_hybrid = use_hybrid
        self.hnsw_m = hnsw_m
        self.ef_construction = ef_construction
        self.ef_search = ef_search
        self.rerank_size = rerank_size
        
        # Paths for storing indexes and metadata
        self.hnsw_index_path = self.db_path / "hnsw_index.bin"
        self.flat_index_path = self.db_path / "flat_index.bin"
        self.metadata_path = self.db_path / "metadata.json"
        
        # Initialize or load the indexes and metadata
        self._load_or_create_indexes()
        
        # Check memory usage on startup
        self._check_memory_usage()
    
    def _load_or_create_indexes(self) -> None:
        """Load existing indexes and metadata or create new ones if they don't exist."""
        # Load or create metadata
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "documents": {},
                "id_map": [],
                "embedding_dimension": settings.EMBEDDING_DIMENSION,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "using_hybrid": self.use_hybrid
            }
        
        # Load or create HNSW index
        if self.hnsw_index_path.exists() and self.use_hybrid:
            self.hnsw_index = faiss.read_index(str(self.hnsw_index_path))
            # Update the efSearch parameter
            self.hnsw_index.hnsw.efSearch = self.ef_search
        else:
            # Create new HNSW index
            self.hnsw_index = faiss.IndexHNSWFlat(settings.EMBEDDING_DIMENSION, self.hnsw_m)
            self.hnsw_index.hnsw.efConstruction = self.ef_construction
            self.hnsw_index.hnsw.efSearch = self.ef_search
        
        # Load or create flat index
        if self.flat_index_path.exists():
            self.flat_index = faiss.read_index(str(self.flat_index_path))
        else:
            # Create new flat index
            self.flat_index = faiss.IndexFlatL2(settings.EMBEDDING_DIMENSION)
        
        # Set the current active index based on the metadata or default
        self.using_hybrid = self.metadata.get("using_hybrid", self.use_hybrid)
    
    def _save_state(self) -> None:
        """Persist the indexes and metadata to disk."""
        # Save HNSW index
        if self.use_hybrid:
            faiss.write_index(self.hnsw_index, str(self.hnsw_index_path))
        
        # Save flat index
        faiss.write_index(self.flat_index, str(self.flat_index_path))
        
        # Update metadata
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["using_hybrid"] = self.using_hybrid
        
        # Save metadata
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def _check_memory_usage(self) -> bool:
        """Check system memory usage and switch to flat indexing if needed.
        
        Returns:
            bool: True if using hybrid, False if using flat due to memory constraints
        """
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent / 100.0
        
        # If memory usage is above threshold, switch to flat indexing
        if memory_percent > self.memory_threshold and self.using_hybrid:
            print(f"Memory usage is high ({memory_percent:.1%}). Switching to flat indexing.")
            self.using_hybrid = False
            return False
        # If memory usage is below threshold and we're not using hybrid, switch back
        elif memory_percent < (self.memory_threshold - 0.1) and not self.using_hybrid:
            print(f"Memory usage is normal ({memory_percent:.1%}). Switching to hybrid indexing.")
            self.using_hybrid = True
            return True
        
        return self.using_hybrid
    
    def add_document(self, doc_id: str, embedding: np.ndarray, metadata: Dict[str, Any]) -> None:
        """Add a document embedding and its metadata to the database.
        
        Args:
            doc_id: Unique identifier for the document
            embedding: Vector representation of the document
            metadata: Additional information about the document
        """
        # Ensure embedding is properly shaped
        if len(embedding.shape) == 1:
            embedding = embedding.reshape(1, -1)
        
        # Also save the raw embedding for rebuilding the index later
        embeddings_file = self.db_path / f"{doc_id}_embedding.npy"
        np.save(embeddings_file, embedding)
        
        # Add to both indexes
        if self.use_hybrid:
            self.hnsw_index.add(embedding)
        self.flat_index.add(embedding)
        
        # Add metadata
        self.metadata["documents"][doc_id] = metadata
        self.metadata["id_map"].append(doc_id)
        self.metadata["last_updated"] = datetime.now().isoformat()
        
        # Save state
        self._save_state()
        
        # Check memory usage after adding
        self._check_memory_usage()
    
    def search(self, 
               query_embedding: np.ndarray, 
               k: int = 10, 
               threshold: float = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for documents similar to the query embedding.
        
        Uses HNSW for initial search, then refines top candidates with flat index.
        Automatically falls back to flat index if memory usage is high.
        
        Args:
            query_embedding: Vector representation of the query
            k: Maximum number of results to return
            threshold: Minimum similarity score threshold
            
        Returns:
            List of tuples containing (doc_id, similarity_score, metadata)
        """
        # Check memory usage and update index choice
        using_hybrid = self._check_memory_usage()
        
        # Ensure embedding is properly shaped
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Calculate how many results to get for each stage
        candidates_k = max(self.rerank_size, k * 3)
        candidates_k = min(candidates_k, self.flat_index.ntotal)  # Cap at total number of docs
        
        # If no documents or not enough documents, return empty list
        if self.flat_index.ntotal == 0 or candidates_k == 0:
            return []
        
        start_time = time.time()
        
        if using_hybrid and self.hnsw_index.ntotal > 0:
            # First stage: Use HNSW to get candidates efficiently
            self.hnsw_index.hnsw.efSearch = max(self.ef_search, candidates_k)
            distances, indices = self.hnsw_index.search(query_embedding, candidates_k)
            
            # Get document IDs for candidates
            candidate_ids = []
            for idx in indices[0]:
                if idx != -1 and idx < len(self.metadata["id_map"]):
                    candidate_ids.append(self.metadata["id_map"][idx])
            
            # Second stage: Precise re-ranking with flat index
            if candidate_ids:
                # Get embeddings for candidates
                candidate_embeddings = []
                for doc_id in candidate_ids:
                    embedding_file = self.db_path / f"{doc_id}_embedding.npy"
                    if embedding_file.exists():
                        candidate_embeddings.append(np.load(embedding_file))
                
                if candidate_embeddings:
                    # Stack embeddings and do precise search
                    candidate_embeddings = np.vstack(candidate_embeddings)
                    flat_index = faiss.IndexFlatL2(settings.EMBEDDING_DIMENSION)
                    flat_index.add(candidate_embeddings)
                    
                    precise_distances, precise_indices = flat_index.search(query_embedding, min(k, len(candidate_ids)))
                    
                    # Map back to document IDs
                    results = []
                    for i, (idx, dist) in enumerate(zip(precise_indices[0], precise_distances[0])):
                        if idx != -1 and idx < len(candidate_ids):
                            doc_id = candidate_ids[idx]
                            # Convert distance to similarity score
                            score = 1 / (1 + dist)
                            
                            # Apply threshold if provided
                            if threshold is None or score >= threshold:
                                metadata = self.metadata["documents"].get(doc_id, {})
                                results.append((doc_id, float(score), metadata))
                    
                    search_time = time.time() - start_time
                    print(f"Hybrid search completed in {search_time:.3f}s")
                    return results
        
        # Fallback to flat index (either due to configuration or if hybrid search fails)
        distances, indices = self.flat_index.search(query_embedding, k)
        
        # Convert distances to similarity scores
        similarity_scores = 1 / (1 + distances[0])
        
        # Gather results
        results = []
        for i, (idx, score) in enumerate(zip(indices[0], similarity_scores)):
            if idx != -1 and idx < len(self.metadata["id_map"]):
                doc_id = self.metadata["id_map"][idx]
                metadata = self.metadata["documents"].get(doc_id, {})
                
                # Apply threshold if provided
                if threshold is None or score >= threshold:
                    results.append((doc_id, float(score), metadata))
        
        search_time = time.time() - start_time
        print(f"Flat search completed in {search_time:.3f}s")
        return results
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a specific document.
        
        Args:
            doc_id: Unique identifier for the document
            
        Returns:
            Document metadata or None if not found
        """
        return self.metadata["documents"].get(doc_id)
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the database.
        
        Args:
            doc_id: Unique identifier for the document
            
        Returns:
            True if document was deleted, False otherwise
        """
        if doc_id not in self.metadata["documents"]:
            return False
        
        # Remove from metadata
        del self.metadata["documents"][doc_id]
        
        # Find index position
        try:
            idx = self.metadata["id_map"].index(doc_id)
            self.metadata["id_map"].pop(idx)
        except ValueError:
            # ID not found in id_map
            pass
        
        # Delete the saved embedding file
        embedding_file = self.db_path / f"{doc_id}_embedding.npy"
        if embedding_file.exists():
            embedding_file.unlink()
        
        # Rebuild indexes
        self.rebuild_indexes()
        
        return True
    
    def rebuild_indexes(self) -> None:
        """Rebuild both the HNSW and flat indexes from stored embeddings."""
        print("Rebuilding vector indexes...")
        
        # Create new indexes with the same dimensions
        dim = settings.EMBEDDING_DIMENSION
        new_flat_index = faiss.IndexFlatL2(dim)
        
        if self.use_hybrid:
            new_hnsw_index = faiss.IndexHNSWFlat(dim, self.hnsw_m)
            new_hnsw_index.hnsw.efConstruction = self.ef_construction
            new_hnsw_index.hnsw.efSearch = self.ef_search
        
        # Clear the id_map
        new_id_map = []
        
        # Add each document back to the indexes
        for doc_id in self.metadata["documents"]:
            embedding_file = self.db_path / f"{doc_id}_embedding.npy"
            
            if embedding_file.exists():
                # Load the embedding
                embedding = np.load(embedding_file)
                
                # Ensure correct shape
                if len(embedding.shape) == 1:
                    embedding = embedding.reshape(1, -1)
                
                # Add to the new indexes
                new_flat_index.add(embedding)
                if self.use_hybrid:
                    new_hnsw_index.add(embedding)
                
                # Add to the new id_map
                new_id_map.append(doc_id)
            else:
                print(f"Warning: Embedding file for document {doc_id} not found")
        
        # Replace the old indexes and id_map
        self.flat_index = new_flat_index
        if self.use_hybrid:
            self.hnsw_index = new_hnsw_index
        
        self.metadata["id_map"] = new_id_map
        self.metadata["last_updated"] = datetime.now().isoformat()
        
        # Save the updated state
        self._save_state()
        
        print(f"Indexes rebuilt with {len(new_id_map)} documents")
    
    def count_documents(self) -> int:
        """Get the total number of documents in the database."""
        return len(self.metadata["documents"])
    
    def get_index_info(self) -> Dict[str, Any]:
        """Get information about the current index state."""
        return {
            "total_documents": self.count_documents(),
            "using_hybrid": self.using_hybrid,
            "memory_usage": psutil.virtual_memory().percent / 100.0,
            "memory_threshold": self.memory_threshold,
            "hnsw_m": self.hnsw_m,
            "ef_construction": self.ef_construction,
            "ef_search": self.ef_search,
            "rerank_size": self.rerank_size,
            "last_updated": self.metadata["last_updated"]
        }


# Factory function to get the appropriate vector database
def get_vector_db(use_hybrid=None):
    """Get the appropriate vector database based on settings.
    
    Args:
        use_hybrid: Override settings to force hybrid mode on/off
        
    Returns:
        Either the hybrid or standard vector database
    """
    from app.db.vector_db import vector_db  # Import the standard vector_db
    
    # Check if hybrid is explicitly requested
    if use_hybrid is not None:
        if use_hybrid and hybrid_vector_db is not None:
            return hybrid_vector_db
        else:
            return vector_db
            
    # Otherwise use settings
    if hasattr(settings, 'USE_HYBRID_VECTOR_DB') and settings.USE_HYBRID_VECTOR_DB:
        if hybrid_vector_db is not None:
            return hybrid_vector_db
    
    # Default to standard vector_db
    return vector_db


# Create the hybrid DB instance if settings allow
try:
    if hasattr(settings, 'USE_HYBRID_VECTOR_DB') and settings.USE_HYBRID_VECTOR_DB:
        hybrid_vector_db = HybridVectorDB(
            memory_threshold=getattr(settings, 'MEMORY_THRESHOLD', 0.85),
            use_hybrid=getattr(settings, 'USE_HYBRID_VECTOR_DB', True),
            hnsw_m=getattr(settings, 'HNSW_M', 32),
            ef_construction=getattr(settings, 'HNSW_EF_CONSTRUCTION', 200),
            ef_search=getattr(settings, 'HNSW_EF_SEARCH', 128),
            rerank_size=getattr(settings, 'RERANK_SIZE', 30)
        )
    else:
        hybrid_vector_db = None
except ImportError:
    print("Warning: psutil not installed. Hybrid vector DB disabled.")
    hybrid_vector_db = None