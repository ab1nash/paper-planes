from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional, List
import json
import os
from pydantic import BaseModel

from app.core.models import PaperIngestionRequest, PaperIngestionResponse, PaperMetadata
from app.services.ingestion_service import ingestion_service
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
    custom_metadata: Optional[str] = Form(None)
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
