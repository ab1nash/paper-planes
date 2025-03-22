from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional, List
import json
import os
from pydantic import BaseModel

from app.core.models import PaperIngestionRequest, PaperIngestionResponse, PaperMetadata
from app.services.ingestion_service import ingestion_service
from app.services.ingestion_service_paragraph import paragraph_ingestion_service
from app.db.metadata_db import metadata_db

router = APIRouter(prefix="/papers", tags=["papers"])


class PaperListResponse(BaseModel):
    """Response model for listing papers."""

    papers: List[dict]
    total_count: int


@router.get("", response_model=PaperListResponse)
async def list_papers(
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)
):
    """
    List all papers in the system.

    - **limit**: Maximum number of papers to return (default: 100, max: 1000)
    - **offset**: Number of papers to skip for pagination (default: 0)
    """
    # Use empty filter to get all papers
    papers, total_count = metadata_db.search_papers({}, limit=limit, offset=offset)

    return PaperListResponse(papers=papers, total_count=total_count)


@router.post("/upload", response_model=PaperIngestionResponse)
async def upload_paper(
    file: UploadFile = File(...),
    extract_metadata: bool = Form(True),
    custom_metadata: Optional[str] = Form(None),
    use_paragraphs: bool = Form(False)
):
    """
    Upload and process a research paper (PDF).
    
    - **file**: PDF file to upload
    - **extract_metadata**: Whether to extract metadata from the PDF
    - **custom_metadata**: Optional JSON string with custom metadata
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Parse custom metadata if provided
    parsed_metadata = None
    if custom_metadata:
        try:
            metadata_dict = json.loads(custom_metadata)
            parsed_metadata = PaperMetadata(**metadata_dict)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid metadata format: {str(e)}")
    
    # Read file content
    file_content = await file.read()
    
    # Check file size
    if len(file_content) > 20 * 1024 * 1024:  # 20 MB limit
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")
    
    # Process the paper
    if use_paragraphs:
        result = await paragraph_ingestion_service.ingest_paper(
            file_content=file_content,
            filename=file.filename,
            extract_metadata=extract_metadata,
            custom_metadata=parsed_metadata
        )
    else:
        result = await ingestion_service.ingest_paper(
            file_content=file_content,
            filename=file.filename,
            extract_metadata=extract_metadata,
            custom_metadata=parsed_metadata
        )
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)
    
    return result


@router.get("/download/{paper_id}")
async def download_paper(paper_id: str):
    """
    Download a paper by its ID.
    
    - **paper_id**: ID of the paper to download
    """
    # Get paper metadata
    paper = metadata_db.get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Get file path
    file_path = paper.get('file_path')
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Paper file not found")
    
    # Get original filename
    filename = paper.get('filename', os.path.basename(file_path))
    
    # Return the file
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf"
    )

@router.delete("/{paper_id}")
async def delete_paper(paper_id: str):
    """
    Delete a paper from the system.
    
    - **paper_id**: ID of the paper to delete
    """
    success = ingestion_service.delete_paper(paper_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    return {"detail": "Paper deleted successfully"}

# INDEXING ===========================================

@router.post("/rebuild-indexes")
async def rebuild_indexes(use_paragraphs: bool = Query(False)):
    """
    Rebuild vector indexes for all documents.
    This operation might take some time for large collections.
    Creates a backup of the current index before rebuilding.
    
    - **use_paragraphs**: Whether to use paragraph-level indexing
    """
    try:
        # Get the appropriate vector database
        from app.db.hybrid_vector_db import get_vector_db
        vector_db = get_vector_db()
        
        # Create backup of current index
        backup_success = await _backup_index()
        if not backup_success:
            raise HTTPException(status_code=500, detail="Failed to create index backup")
            
        # Perform the rebuild operation
        if hasattr(vector_db, 'rebuild_indexes'):  # For hybrid DB
            vector_db.rebuild_indexes()
        else:
            vector_db.rebuild_index()  # For standard DB
            
        # Log the operation
        import logging
        logging.info(f"Vector indexes rebuilt successfully. Paragraph mode: {use_paragraphs}")
        
        return {"status": "success", "message": "Indexes rebuilt successfully"}
        
    except Exception as e:
        # Log the error
        import logging
        logging.error(f"Error rebuilding indexes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to rebuild indexes: {str(e)}")


@router.post("/rollback-index")
async def rollback_index():
    """
    Rollback to the previous version of the vector index.
    Only works if there is a valid backup from a previous rebuild operation.
    """
    try:
        rollback_success = await _restore_index_backup()
        
        if not rollback_success:
            raise HTTPException(status_code=404, detail="No valid index backup found")
            
        return {"status": "success", "message": "Index rolled back to previous version"}
        
    except Exception as e:
        import logging
        logging.error(f"Error rolling back index: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to rollback index: {str(e)}")


# Helper functions for backup and restore
async def _backup_index():
    """Create a backup of the current index files."""
    import shutil
    import os
    from datetime import datetime
    from app.core.config import settings
    
    try:
        # Source directory (current index)
        vector_db_path = settings.VECTOR_DB_PATH
        
        # Backup directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"{vector_db_path}_backup_{timestamp}"
        
        # Create backup if the source directory exists
        if os.path.exists(vector_db_path):
            shutil.copytree(vector_db_path, backup_dir)
            
            # Save the path to the most recent backup
            backup_info_path = os.path.join(os.path.dirname(vector_db_path), "index_backup_info.json")
            import json
            with open(backup_info_path, 'w') as f:
                json.dump({
                    "backup_path": backup_dir,
                    "timestamp": timestamp,
                    "is_valid": True
                }, f)
                
            return True
        return False
    except Exception as e:
        import logging
        logging.error(f"Backup creation failed: {str(e)}", exc_info=True)
        return False


async def _restore_index_backup():
    """Restore the index from the most recent backup."""
    import shutil
    import os
    import json
    from app.core.config import settings
    
    try:
        # Get backup info
        vector_db_path = settings.VECTOR_DB_PATH
        backup_info_path = os.path.join(os.path.dirname(vector_db_path), "index_backup_info.json")
        
        if not os.path.exists(backup_info_path):
            return False
            
        with open(backup_info_path, 'r') as f:
            backup_info = json.load(f)
            
        # Check if backup is valid
        if not backup_info.get("is_valid", False):
            return False
            
        backup_path = backup_info["backup_path"]
        if not os.path.exists(backup_path):
            return False
            
        # Remove current index
        if os.path.exists(vector_db_path):
            shutil.rmtree(vector_db_path)
            
        # Restore from backup
        shutil.copytree(backup_path, vector_db_path)
        
        # Mark backup as used
        backup_info["is_valid"] = False  # Prevent multiple rollbacks to same backup
        with open(backup_info_path, 'w') as f:
            json.dump(backup_info, f)
            
        return True
    except Exception as e:
        import logging
        logging.error(f"Restore failed: {str(e)}", exc_info=True)
        return False
    

@router.get("/index-status")
async def get_index_status():
    """
    Get information about the current index and whether a backup is available.
    """
    try:
        # Get vector database information
        from app.db.hybrid_vector_db import get_vector_db
        vector_db = get_vector_db()
        
        if hasattr(vector_db, 'get_index_info'):
            index_info = vector_db.get_index_info()
        else:
            # Basic info for standard vector DB
            index_info = {
                "total_documents": vector_db.count_documents(),
                "last_updated": "unknown"
            }
            
        # Check if backup exists
        import os
        import json
        from app.core.config import settings
        
        backup_info_path = os.path.join(os.path.dirname(settings.VECTOR_DB_PATH), "index_backup_info.json")
        has_backup = False
        backup_info = {}
        
        if os.path.exists(backup_info_path):
            try:
                with open(backup_info_path, 'r') as f:
                    backup_info = json.load(f)
                has_backup = backup_info.get("is_valid", False)
            except:
                pass
                
        # Return combined information
        return {
            "index": index_info,
            "has_backup": has_backup,
            "backup_info": backup_info if has_backup else None
        }
        
    except Exception as e:
        import logging
        logging.error(f"Error getting index status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get index status")
    
async def _rebuild_paragraph_index():
    """Helper function to rebuild paragraph indexes specifically."""
    try:
        from app.services.paragraph_extraction import paragraph_extraction_service
        from app.services.text_extraction import text_extraction_service
        from app.services.llm_service import llm_service
        from app.db.hybrid_vector_db import get_vector_db
        from app.db.metadata_db import metadata_db
        import os
        import logging
        
        logging.info("Starting paragraph index rebuild...")
        
        # Get all papers from metadata DB
        papers, total_count = metadata_db.search_papers({}, limit=1000, offset=0)
        
        # Track processed papers and paragraphs
        processed_papers = 0
        total_paragraphs = 0
        
        # Get vector database
        vector_db = get_vector_db()
        
        # Process each paper
        for paper in papers:
            paper_id = paper['id']
            file_path = paper.get('file_path')
            filename = paper.get('filename', os.path.basename(file_path) if file_path else 'unknown')
            
            # Skip if file doesn't exist
            if not file_path or not os.path.exists(file_path):
                logging.warning(f"File not found for paper {paper_id}: {file_path}")
                continue
                
            # Extract text
            text = text_extraction_service.extract_text_from_pdf(file_path)
            if not text:
                logging.warning(f"Failed to extract text from PDF: {paper_id}")
                continue
                
            # Extract paragraphs
            paragraphs = paragraph_extraction_service.extract_paragraphs(text)
            
            # Process each paragraph
            for paragraph in paragraphs:
                # Skip very short paragraphs and section headers
                if len(paragraph['text']) < 100 and paragraph.get('is_header', False):
                    continue
                
                # Create chunk ID
                chunk_id = f"{paper_id}_{paragraph['paragraph_index']}"
                
                # Get paragraph context
                context = paragraph_extraction_service.get_paragraph_context(
                    paragraphs, 
                    paragraph['paragraph_index'], 
                    context_size=1
                )
                
                # Generate embedding
                paragraph_embedding = llm_service.get_embedding(paragraph['text'])
                
                # Prepare metadata
                paragraph_metadata = {
                    "paper_id": paper_id,
                    "paragraph_index": paragraph['paragraph_index'],
                    "section": paragraph.get('section', 'unknown'),
                    "text": paragraph['text'],
                    "context": context,
                    "is_header": paragraph.get('is_header', False),
                    "filename": filename,
                    "file_path": file_path,
                    "title": paper.get('title', ''),
                    "authors": paper.get('authors', []),
                    "publication_year": paper.get('publication_year'),
                    "conference": paper.get('conference'),
                    "journal": paper.get('journal')
                }
                
                # Add to vector database
                vector_db.add_document(
                    doc_id=chunk_id,
                    embedding=paragraph_embedding,
                    metadata=paragraph_metadata
                )
                
                total_paragraphs += 1
            
            # Update metadata to include paragraph count
            metadata_db.update_paper(paper_id, {"paragraph_count": len(paragraphs)})
            
            processed_papers += 1
            logging.info(f"Processed paper {processed_papers}/{len(papers)}: {paper_id}")
            
        logging.info(f"Paragraph index rebuild complete. Processed {processed_papers} papers with {total_paragraphs} paragraphs.")
        return True, f"Rebuilt paragraph index for {processed_papers} papers with {total_paragraphs} paragraphs."
        
    except Exception as e:
        logging.error(f"Error rebuilding paragraph index: {str(e)}", exc_info=True)
        return False, f"Error rebuilding paragraph index: {str(e)}"

# Modify the rebuild_indexes endpoint to handle paragraph-specific rebuilding
@router.post("/rebuild-indexes")
async def rebuild_indexes(use_paragraphs: bool = Query(False)):
    try:
        # Backup current index
        backup_success = await _backup_index()
        if not backup_success:
            raise HTTPException(status_code=500, detail="Failed to create index backup")
            
        # Check if we need paragraph-specific rebuild
        if use_paragraphs:
            success, message = await _rebuild_paragraph_index()
            if not success:
                raise HTTPException(status_code=500, detail=message)
            return {"status": "success", "message": message}
        else:
            # Standard index rebuild
            from app.db.hybrid_vector_db import get_vector_db
            vector_db = get_vector_db()
            
            if hasattr(vector_db, 'rebuild_indexes'):
                vector_db.rebuild_indexes()
            else:
                vector_db.rebuild_index()
                
            return {"status": "success", "message": "Indexes rebuilt successfully"}
            
    except Exception as e:
        import logging
        logging.error(f"Error rebuilding indexes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to rebuild indexes: {str(e)}")

# Also add this helper method to metadata_db.py
def update_paper(self, paper_id: str, updates: dict) -> bool:
    """Update paper metadata.
    
    Args:
        paper_id: ID of the paper to update
        updates: Dictionary with fields to update
        
    Returns:
        True if updated, False if not found
    """
    cursor = self.conn.cursor()
    
    # Check if paper exists
    cursor.execute('SELECT id FROM papers WHERE id = ?', (paper_id,))
    if not cursor.fetchone():
        return False
        
    # Build update query
    update_fields = []
    update_values = []
    
    for field, value in updates.items():
        if field in ['title', 'abstract', 'publication_year', 'doi', 'url', 
                     'conference', 'journal', 'filename', 'file_path', 'paragraph_count']:
            update_fields.append(f"{field} = ?")
            update_values.append(value)
            
    if not update_fields:
        return False  # No valid fields to update
        
    # Add last_updated timestamp
    update_fields.append("last_updated = ?")
    from datetime import datetime
    update_values.append(datetime.now().isoformat())
    
    # Add paper ID as the last parameter
    update_values.append(paper_id)
    
    # Execute update
    query = f"UPDATE papers SET {', '.join(update_fields)} WHERE id = ?"
    cursor.execute(query, update_values)
    self.conn.commit()
    
    return cursor.rowcount > 0

# INDEXING ===========================================