import os
import logging
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime
from pathlib import Path
import numpy as np

from app.core.config import settings
from app.core.models import PaperMetadata, PaperIngestionResponse
from app.services.text_extraction import text_extraction_service
from app.services.paragraph_extraction import paragraph_extraction_service
from app.services.llm_service import llm_service
from app.db.hybrid_vector_db import get_vector_db
from app.db.metadata_db import metadata_db
from app.services.ingestion_service import ingestion_service, IngestionService

# Set up logging
logger = logging.getLogger("paragraph_ingestion")

class ParagraphIngestionService(IngestionService):
    """Enhanced service for ingesting research papers by paragraphs.
    
    Extends the base IngestionService to process papers at paragraph level.
    """

    def __init__(self, upload_dir: str = None, **kwargs):
        """Initialize the paragraph ingestion service."""
        # Call parent constructor to inherit base functionality
        super().__init__(upload_dir=upload_dir, **kwargs)
        logger.info(f"Initialized paragraph ingestion service (extends base IngestionService)")
        
    async def ingest_paper(self, 
                     file_content: bytes, 
                     filename: str,
                     extract_metadata: bool = True,
                     custom_metadata: Optional[PaperMetadata] = None) -> PaperIngestionResponse:
        """Process a new paper and add its paragraphs to the search system.
        
        Overrides the base method to add paragraph-level processing.
        """
        try:
            # Generate a unique ID for the paper
            paper_id = str(uuid.uuid4())
            logger.info(f"Ingesting paper: {filename} with ID: {paper_id}")

            # Save the file - reuse parent method
            file_path = self._save_file(file_content, filename, paper_id)

            # Extract text - reuse text extraction from base service
            text = text_extraction_service.extract_text_from_pdf(file_path)

            if not text:
                logger.warning(f"Failed to extract text from PDF: {filename}")
                return PaperIngestionResponse(
                    paper_id=paper_id,
                    filename=filename,
                    metadata=PaperMetadata(title=filename, authors=[]),
                    ingestion_time=datetime.now(),
                    success=False,
                    message="Failed to extract text from PDF."
                )

            # Extract or use provided metadata - reuse from base service
            metadata = custom_metadata
            if not metadata and extract_metadata:
                metadata = text_extraction_service.extract_metadata(text, filename)

            if not metadata:
                # Basic fallback metadata
                metadata = PaperMetadata(title=filename, authors=[])

            # Extract paragraphs - this is new in the paragraph implementation
            paragraphs = paragraph_extraction_service.extract_paragraphs(text)
            logger.info(f"Extracted {len(paragraphs)} paragraphs from {filename}")
            
            # Process each paragraph
            for paragraph in paragraphs:
                # Skip very short paragraphs and section headers for embedding
                # Headers will still be stored in metadata DB for context
                if len(paragraph['text']) < 100 and paragraph.get('is_header', False):
                    continue
                
                # Create chunk ID based on paper ID and paragraph index
                chunk_id = f"{paper_id}_{paragraph['paragraph_index']}"
                
                # Get paragraph context (includes neighboring paragraphs)
                context = paragraph_extraction_service.get_paragraph_context(
                    paragraphs, 
                    paragraph['paragraph_index'], 
                    context_size=1
                )
                
                # Generate embedding for the paragraph
                paragraph_embedding = llm_service.get_embedding(paragraph['text'])
                
                # Extended metadata for the paragraph
                paragraph_metadata = {
                    "paper_id": paper_id,
                    "paragraph_index": paragraph['paragraph_index'],
                    "section": paragraph.get('section', 'unknown'),
                    "text": paragraph['text'],
                    "context": context,
                    "is_header": paragraph.get('is_header', False),
                    "filename": filename,
                    "file_path": str(file_path),
                    "title": metadata.title,
                    # Include essential paper metadata
                    "authors": metadata.authors,
                    "publication_year": metadata.publication_year,
                    "conference": metadata.conference,
                    "journal": metadata.journal
                }
                
                # Store in vector database
                get_vector_db().add_document(
                    doc_id=chunk_id,
                    embedding=paragraph_embedding,
                    metadata=paragraph_metadata
                )
                
                logger.debug(f"Added paragraph {chunk_id} to vector database")
            
            # Store paper metadata in metadata database - similar to base implementation
            metadata_dict = metadata.dict(exclude_none=True)
            metadata_dict.update({
                "filename": filename,
                "file_path": str(file_path),
                "paragraph_count": len(paragraphs)
            })

            metadata_db.add_paper({
                "id": paper_id,
                **metadata_dict
            })
            
            logger.info(f"Successfully ingested paper {paper_id} with {len(paragraphs)} paragraphs")

            # Return success response
            return PaperIngestionResponse(
                paper_id=paper_id,
                filename=filename,
                metadata=metadata,
                ingestion_time=datetime.now(),
                success=True,
                message=f"Successfully processed {len(paragraphs)} paragraphs"
            )

        except Exception as e:
            # Log the error
            logger.error(f"Error ingesting paper: {e}", exc_info=True)

            # Return error response
            return PaperIngestionResponse(
                paper_id="",
                filename=filename,
                metadata=PaperMetadata(title=filename, authors=[]),
                ingestion_time=datetime.now(),
                success=False,
                message=f"Error ingesting paper: {str(e)}"
            )

# Create a singleton instance
paragraph_ingestion_service = ParagraphIngestionService()