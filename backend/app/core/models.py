from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class PaperMetadata(BaseModel):
    """Metadata extracted from a research paper."""
    title: str
    authors: List[str]
    abstract: Optional[str] = None
    publication_year: Optional[int] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    keywords: Optional[List[str]] = None
    conference: Optional[str] = None
    journal: Optional[str] = None


class PaperIngestionRequest(BaseModel):
    """Request model for paper ingestion endpoint."""
    # The actual file will be uploaded as form data
    extract_metadata: bool = True
    custom_metadata: Optional[PaperMetadata] = None


class PaperIngestionResponse(BaseModel):
    """Response model for paper ingestion endpoint."""
    paper_id: str
    filename: str
    metadata: PaperMetadata
    ingestion_time: datetime
    success: bool
    message: Optional[str] = None


class SearchFilter(BaseModel):
    """Search filter criteria."""
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    authors: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    conference: Optional[str] = None
    journal: Optional[str] = None


class SearchRequest(BaseModel):
    """Request model for search endpoint."""
    query: str
    filters: Optional[SearchFilter] = None
    limit: int = 10
    offset: int = 0


class SearchResultItem(BaseModel):
    """A single search result item."""
    paper_id: str
    title: str
    authors: List[str]
    publication_year: Optional[int] = None
    abstract: Optional[str] = None
    similarity_score: float
    filename: str
    file_path: str
    
    # Additional metadata that might be useful for filtering/display
    conference: Optional[str] = None
    journal: Optional[str] = None
    keywords: Optional[List[str]] = None
    

class SearchResponse(BaseModel):
    """Response model for search endpoint."""
    results: List[SearchResultItem]
    total_count: int
    query: str
    execution_time_ms: float
    