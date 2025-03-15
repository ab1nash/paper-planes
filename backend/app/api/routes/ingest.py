from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import json

from app.core.models import PaperIngestionRequest, PaperIngestionResponse, PaperMetadata
from app.services.ingestion_service import ingestion_service

router = APIRouter(prefix="/papers", tags=["papers"])


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