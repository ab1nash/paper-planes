from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional

from app.core.models import SearchRequest, SearchResponse
from app.services.search_service import search_service
from app.services.search_service_paragraph import paragraph_search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_papers(search_request: SearchRequest,  use_paragraphs: Optional[bool] = False):
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
    
    doc_level_response = await search_service.search_papers(search_request)
    if use_paragraphs:
        paragraph_level_response = await paragraph_search_service.search_papers(search_request)
        doc_level_response.results += [*paragraph_level_response.results]
        doc_level_response.total_count = len(doc_level_response.results)

    
    return doc_level_response


@router.get("/filter-options")
async def get_filter_options():
    """
    Get available filter options for the search interface.
    
    Returns lists of available years, authors, keywords, conferences, and journals.
    """
    options = await search_service.get_filter_options()
    return options