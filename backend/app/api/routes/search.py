from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.core.models import SearchRequest, SearchResponse
from app.services.search_service import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_papers(search_request: SearchRequest):
    """
    Search for papers based on a natural language query.
    
    - **query**: The search query in natural language
    - **filters**: Optional metadata filters
    - **limit**: Maximum number of results to return
    - **offset**: Number of results to skip for pagination
    """
    # Validate request
    if not search_request.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    # Perform search
    results = await search_service.search_papers(search_request)
    
    return results


@router.get("/filter-options")
async def get_filter_options():
    """
    Get available filter options for the search interface.
    
    Returns lists of available years, authors, keywords, conferences, and journals.
    """
    options = await search_service.get_filter_options()
    return options