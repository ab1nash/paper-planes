import os
from typing import Dict, Any, Optional, Tuple, List
import uuid
from datetime import datetime
from pathlib import Path
import shutil
import numpy as np

from app.core.config import settings
from app.core.models import PaperMetadata, PaperIngestionResponse
from app.services.text_extraction import text_extraction_service
from app.services.llm_service import llm_service
from app.db.vector_db import vector_db
from app.db.metadata_db import metadata_db


class IngestionService:
    """Service for ingesting research papers into the system.
    
    Handles the entire pipeline from PDF upload to embedding generation
    and storage in the vector and metadata databases.
    """
    
    def __init__(self, 
                 upload_dir: str = None,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200):
        """Initialize the ingestion service.
        
        Args:
            upload_dir: Directory for storing uploaded papers
            chunk_size: Size of text chunks for embeddings
            chunk_overlap: Overlap between chunks
        """
        self.upload_dir = Path(upload_dir or settings.UPLOAD_DIR)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Create upload directory if it doesn't exist
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def ingest_paper(self, 
                     file_content: bytes, 
                     filename: str,
                     extract_metadata: bool = True,
                     custom_metadata: Optional[PaperMetadata] = None) -> PaperIngestionResponse:
        """Process a new paper and add it to the search system.
        
        Args:
            file_content: Binary content of the PDF file
            filename: Name of the uploaded file
            extract_metadata: Whether to extract metadata from the PDF
            custom_metadata: Optional custom metadata to use instead of extraction
            
        Returns:
            PaperIngestionResponse with details of the ingestion
        """
        try:
            # Generate a unique ID for the paper
            paper_id = str(uuid.uuid4())
            
            # Save the file
            file_path = self._save_file(file_content, filename, paper_id)
            
            # Extract text
            text = text_extraction_service.extract_text_from_pdf(file_path)
            
            if not text:
                return PaperIngestionResponse(
                    paper_id=paper_id,
                    filename=filename,
                    metadata=PaperMetadata(title=filename, authors=[]),
                    ingestion_time=datetime.now(),
                    success=False,
                    message="Failed to extract text from PDF."
                )
            
            # Extract or use provided metadata
            metadata = custom_metadata
            if not metadata and extract_metadata:
                metadata = text_extraction_service.extract_metadata(text, filename)
            
            if not metadata:
                # Basic fallback metadata
                metadata = PaperMetadata(title=filename, authors=[])
            
            # Create document chunks for embedding
            chunks = self._chunk_text(text)
            
            # Generate embeddings for each chunk
            embeddings = [llm_service.get_embedding(chunk) for chunk in chunks]
            
            # Compute the mean embedding to represent the entire document
            mean_embedding = np.mean(embeddings, axis=0)
            
            # Store in vector database
            vector_db.add_document(
                doc_id=paper_id,
                embedding=mean_embedding,
                metadata={
                    "filename": filename,
                    "file_path": str(file_path),
                    "title": metadata.title,
                    "chunk_count": len(chunks)
                }
            )
            
            # Store in metadata database
            metadata_dict = metadata.dict(exclude_none=True)
            metadata_dict.update({
                "filename": filename,
                "file_path": str(file_path)
            })
            
            metadata_db.add_paper({
                "id": paper_id,
                **metadata_dict
            })
            
            # Return success response
            return PaperIngestionResponse(
                paper_id=paper_id,
                filename=filename,
                metadata=metadata,
                ingestion_time=datetime.now(),
                success=True
            )
            
        except Exception as e:
            # Log the error
            print(f"Error ingesting paper: {e}")
            
            # Return error response
            return PaperIngestionResponse(
                paper_id="",
                filename=filename,
                metadata=PaperMetadata(title=filename, authors=[]),
                ingestion_time=datetime.now(),
                success=False,
                message=f"Error ingesting paper: {str(e)}"
            )
    
    def _save_file(self, 
                   file_content: bytes, 
                   filename: str, 
                   paper_id: str) -> Path:
        """Save the uploaded file to disk.
        
        Args:
            file_content: Binary content of the file
            filename: Original filename
            paper_id: Generated paper ID
            
        Returns:
            Path where the file was saved
        """
        # Create a safe filename 
        safe_filename = f"{paper_id}_{filename.replace(' ', '_')}"
        file_path = self.upload_dir / safe_filename
        
        # Save the file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return file_path
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for embedding.
        
        Args:
            text: Full text to chunk
            
        Returns:
            List of text chunks
        """
        # Simple chunking by character count
        chunks = []
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Split by sentences approximately
        sentences = []
        for paragraph in text.split('\n'):
            for sentence in paragraph.split('. '):
                if sentence:
                    sentences.append(sentence.strip() + '.')
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed the chunk size,
            # save the current chunk and start a new one
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # Keep overlap sentences
                overlap_start = max(0, len(current_chunk) - self.chunk_overlap // 30)
                current_chunk = current_chunk[overlap_start:]
                current_length = sum(len(s) for s in current_chunk)
            
            # Add the sentence to the current chunk
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add the last chunk if there's anything left
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def delete_paper(self, paper_id: str) -> bool:
        """Delete a paper from the system.
        
        Args:
            paper_id: ID of the paper to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Get paper details from metadata DB
            paper = metadata_db.get_paper(paper_id)
            if not paper:
                return False
            
            # Delete from vector DB
            vector_db.delete_document(paper_id)
            
            # Delete from metadata DB
            metadata_db.delete_paper(paper_id)
            
            # Delete file if it exists
            file_path = paper.get('file_path')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                
            return True
        
        except Exception as e:
            print(f"Error deleting paper {paper_id}: {e}")
            return False


# Create a singleton instance
ingestion_service = IngestionService()