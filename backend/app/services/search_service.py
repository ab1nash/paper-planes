import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from app.core.config import settings
from app.core.models import SearchRequest, SearchResponse, SearchResultItem, SearchFilter
from app.services.llm_service import llm_service
from app.db.hybrid_vector_db import get_vector_db
from app.db.metadata_db import metadata_db


class SearchService:
    """Service for searching research papers using semantic understanding.
    
    Handles processing search queries, generating embeddings, and
    retrieving relevant papers from the vector and metadata databases.
    """
    
    def __init__(self, 
                 similarity_threshold: float = None,
                 default_limit: int = None):
        """Initialize the search service.
        
        Args:
            similarity_threshold: Minimum similarity score to include in results
            default_limit: Default maximum number of results to return
        """
        self.similarity_threshold = similarity_threshold or settings.SIMILARITY_THRESHOLD
        self.default_limit = default_limit or settings.DEFAULT_SEARCH_LIMIT
    
    async def search_papers(self, search_request: SearchRequest) -> SearchResponse:
        """Search for papers based on a natural language query.
        
        Args:
            search_request: Search request containing query and filters
            
        Returns:
            SearchResponse with search results
        """
        start_time = time.time()
        
        try:
            # Generate embedding for the query
            query_embedding = llm_service.get_embedding(search_request.query)
            
            # Search vector database
            limit = search_request.limit or self.default_limit
            vector_results = get_vector_db().search(
                query_embedding=query_embedding,
                k=limit * 3,  # Get more results for filtering
                threshold=self.similarity_threshold
            )
            
            # Apply metadata filters
            filtered_results = self._apply_filters(vector_results, search_request.filters)
            
            # Get detailed metadata
            result_items = []
            for doc_id, score, _ in filtered_results[:limit]:
                paper_metadata = metadata_db.get_paper(doc_id)
                if paper_metadata:
                    result_items.append(
                        SearchResultItem(
                            paper_id=doc_id,
                            title=paper_metadata.get('title', ''),
                            authors=paper_metadata.get('authors', []),
                            publication_year=paper_metadata.get('publication_year'),
                            abstract=paper_metadata.get('abstract'),
                            similarity_score=score,
                            filename=paper_metadata.get('filename', ''),
                            file_path=paper_metadata.get('file_path', ''),
                            conference=paper_metadata.get('conference'),
                            journal=paper_metadata.get('journal'),
                            keywords=paper_metadata.get('keywords', [])
                        )
                    )
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Create response
            response = SearchResponse(
                results=result_items,
                total_count=len(filtered_results),
                query=search_request.query,
                execution_time_ms=execution_time_ms
            )
            
            return response
            
        except Exception as e:
            # Log the error
            print(f"Error searching papers: {e}")
            
            # Return empty response
            return SearchResponse(
                results=[],
                total_count=0,
                query=search_request.query,
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _apply_filters(self, 
                     results: List[Tuple[str, float, Dict[str, Any]]], 
                     filters: Optional[SearchFilter]) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Apply metadata filters to search results.
        
        Args:
            results: List of (doc_id, score, metadata) tuples
            filters: Search filters to apply
            
        Returns:
            Filtered list of results
        """
        # If no filters, return original results
        if not filters:
            return results
            
        filtered_results = []
        
        for doc_id, score, metadata in results:
            # Get full metadata from database
            paper_metadata = metadata_db.get_paper(doc_id)
            if not paper_metadata:
                continue
                
            # Check year range
            year = paper_metadata.get('publication_year')
            if filters.year_min is not None and (year is None or year < filters.year_min):
                continue
            if filters.year_max is not None and (year is None or year > filters.year_max):
                continue
                
            # Check authors
            if filters.authors:
                authors = paper_metadata.get('authors', [])
                if not any(self._partial_match(author, filters.authors) for author in authors):
                    continue
                    
            # Check keywords
            if filters.keywords:
                keywords = paper_metadata.get('keywords', [])
                if not any(self._partial_match(keyword, filters.keywords) for keyword in keywords):
                    continue
                    
            # Check conference
            if filters.conference and not self._partial_match(paper_metadata.get('conference', ''), [filters.conference]):
                continue
                
            # Check journal
            if filters.journal and not self._partial_match(paper_metadata.get('journal', ''), [filters.journal]):
                continue
                
            # Add to filtered results
            filtered_results.append((doc_id, score, metadata))
            
        return filtered_results
    
    def _partial_match(self, text: str, patterns: List[str]) -> bool:
        """Check if any pattern partially matches the text.
        
        Args:
            text: Text to check
            patterns: List of patterns to match against
            
        Returns:
            True if any pattern partially matches, False otherwise
        """
        if not text:
            return False
            
        text_lower = text.lower()
        return any(pattern.lower() in text_lower for pattern in patterns)
        
    async def get_filter_options(self) -> Dict[str, Any]:
        """Get available filter options from the database.
        
        Returns:
            Dictionary with available filter options
        """
        try:
            return {
                "years": metadata_db.get_publication_years(),
                "authors": metadata_db.get_all_authors(),
                "keywords": metadata_db.get_all_keywords(),
                "conferences": metadata_db.get_conferences(),
                "journals": metadata_db.get_journals()
            }
        except Exception as e:
            print(f"Error getting filter options: {e}")
            return {
                "years": [],
                "authors": [],
                "keywords": [],
                "conferences": [],
                "journals": []
            }


# Create a singleton instance
search_service = SearchService()