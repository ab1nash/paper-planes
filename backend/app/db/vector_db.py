import os
import json
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pathlib import Path
import faiss
import pickle
from datetime import datetime

from app.core.config import settings


class VectorDB:
    """Vector database for storing and retrieving document embeddings.
    
    Uses FAISS for efficient similarity search in vector space. This implementation
    creates a simple on-disk vector store with JSON metadata index.
    """
    
    def __init__(self, db_path: str = None):
        """Initialize the vector database.
        
        Args:
            db_path: Path to the directory where vector data will be stored
        """
        self.db_path = Path(db_path or settings.VECTOR_DB_PATH)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Paths for storing index and metadata
        self.index_path = self.db_path / "faiss_index.bin"
        self.metadata_path = self.db_path / "metadata.json"
        self.embeddings_path = self.db_path / "embeddings.npz"
        
        # Initialize or load the index and metadata
        self._load_or_create_index()
    
    def _load_or_create_index(self) -> None:
        """Load existing index and metadata or create new ones if they don't exist."""
        if self.index_path.exists() and self.metadata_path.exists():
            # Load existing index and metadata
            self.index = faiss.read_index(str(self.index_path))
            with open(self.metadata_path, 'r') as f:
                self.metadata = json.load(f)
        else:
            # Create new index and metadata store
            self.index = faiss.IndexFlatL2(settings.EMBEDDING_DIMENSION)
            self.metadata = {
                "documents": {},
                "id_map": [],
                "embedding_dimension": settings.EMBEDDING_DIMENSION,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
            self._save_state()
    
    def _save_state(self) -> None:
        """Persist the index and metadata to disk."""
        faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
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
        
        # Add embedding to index
        self.index.add(embedding)
        
        # Add metadata
        self.metadata["documents"][doc_id] = metadata
        self.metadata["id_map"].append(doc_id)
        self.metadata["last_updated"] = datetime.now().isoformat()
        
        # Save state
        self._save_state()
    
    def search(self, 
               query_embedding: np.ndarray, 
               k: int = 10, 
               threshold: float = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for documents similar to the query embedding.
        
        Args:
            query_embedding: Vector representation of the query
            k: Maximum number of results to return
            threshold: Minimum similarity score threshold
            
        Returns:
            List of tuples containing (doc_id, similarity_score, metadata)
        """
        # Ensure embedding is properly shaped
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Use actual index size if k is larger than the index
        actual_k = min(k, self.index.ntotal)
        
        if actual_k == 0:
            # No documents in the index
            return []
        
        # Perform the search
        distances, indices = self.index.search(query_embedding, actual_k)
        
        # Convert distances to similarity scores (higher is better)
        # Using simple normalization: 1 / (1 + distance)
        similarity_scores = 1 / (1 + distances[0])
        
        # Gather results
        results = []
        for i, (idx, score) in enumerate(zip(indices[0], similarity_scores)):
            if idx != -1:  # Valid index
                doc_id = self.metadata["id_map"][idx]
                metadata = self.metadata["documents"][doc_id]
                
                # Apply threshold if provided
                if threshold is None or score >= threshold:
                    results.append((doc_id, float(score), metadata))
        
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
        
        # Rebuild index
        self.rebuild_index()
        
        return True
    
    def rebuild_index(self) -> None:
        """Rebuild the entire index from stored metadata and embeddings."""
        print("Rebuilding vector index...")
        
        # Create a new index with the same dimension
        dim = settings.EMBEDDING_DIMENSION
        new_index = faiss.IndexFlatL2(dim)
        
        # Clear the id_map
        new_id_map = []
        
        # Add each document back to the index
        for doc_id in self.metadata["documents"]:
            embedding_file = self.db_path / f"{doc_id}_embedding.npy"
            
            if embedding_file.exists():
                # Load the embedding
                embedding = np.load(embedding_file)
                
                # Ensure correct shape
                if len(embedding.shape) == 1:
                    embedding = embedding.reshape(1, -1)
                
                # Add to the new index
                new_index.add(embedding)
                
                # Add to the new id_map
                new_id_map.append(doc_id)
            else:
                print(f"Warning: Embedding file for document {doc_id} not found")
        
        # Replace the old index and id_map
        self.index = new_index
        self.metadata["id_map"] = new_id_map
        self.metadata["last_updated"] = datetime.now().isoformat()
        
        # Save the updated state
        self._save_state()
        
        print(f"Index rebuilt with {len(new_id_map)} documents")
    
    def count_documents(self) -> int:
        """Get the total number of documents in the database."""
        return len(self.metadata["documents"])


# Create a singleton instance
vector_db = VectorDB()