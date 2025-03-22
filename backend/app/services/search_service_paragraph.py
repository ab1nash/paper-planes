import time
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from collections import defaultdict

from app.core.config import settings
from app.core.models import SearchRequest, SearchResponse, SearchResultItem, SearchFilter, ParagraphMatch
from app.services.llm_service import llm_service
from app.db.hybrid_vector_db import get_vector_db
from app.db.metadata_db import metadata_db
from app.services.search_service import search_service, SearchService

# Set up logging
logger = logging.getLogger("paragraph_search")

class ParagraphSearchService(SearchService):
    """Enhanced service for searching research papers at the paragraph level.
    
    Extends the base SearchService to handle paragraph-level searches.
    """
    
    def __init__(self, 
                 similarity_threshold: float = None,
                 default_limit: int = None,
                 max_paragraphs_per_paper: int = 3,
                 **kwargs):
        """Initialize the paragraph search service."""
        # Call parent constructor to inherit base functionality
        super().__init__(similarity_threshold=similarity_threshold, 
                         default_limit=default_limit, 
                         **kwargs)
        
        # Paragraph-specific parameters
        self.max_paragraphs_per_paper = max_paragraphs_per_paper
        
        logger.info(f"Initialized paragraph search service (extends base SearchService)")
    
    async def search_papers(self, search_request: SearchRequest) -> SearchResponse:
        """Search for papers based on a natural language query at paragraph level.
        
        Overrides the base method to add paragraph-level search.
        """
        start_time = time.time()
        
        try:
            # Generate embedding for the query - reuse from base class
            query_embedding = llm_service.get_embedding(search_request.query)
            logger.info(f"Generated embedding for query: {search_request.query}")
            
            # Search vector database for matching paragraphs
            limit = search_request.limit or self.default_limit
            
            # Request more results since we'll be grouping by paper
            vector_results = get_vector_db().search(
                query_embedding=query_embedding,
                k=limit * 10,  # Get more results for filtering and grouping
                threshold=self.similarity_threshold
            )
            
            logger.info(f"Vector search returned {len(vector_results)} paragraph matches")
            
            # Apply metadata filters - reuse from base class
            filtered_results = self._apply_filters(vector_results, search_request.filters)
            logger.info(f"After filtering: {len(filtered_results)} paragraph matches")
            
            # Group results by paper_id - this is specific to paragraph search
            paper_results = self._group_by_paper(filtered_results)
            logger.info(f"Grouped into {len(paper_results)} unique papers")
            
            # Sort papers by max paragraph score
            sorted_papers = sorted(
                paper_results.values(), 
                key=lambda x: x['max_score'], 
                reverse=True
            )
            
            # Limit to requested number of papers
            sorted_papers = sorted_papers[:limit]
            
            # Convert to SearchResultItem objects
            result_items = self._convert_to_result_items(sorted_papers)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Create response - similar to base implementation
            response = SearchResponse(
                results=result_items,
                total_count=len(paper_results),
                query=search_request.query,
                execution_time_ms=execution_time_ms
            )
            
            logger.info(f"Search completed in {execution_time_ms:.1f}ms with {len(result_items)} results")
            return response
            
        except Exception as e:
            # Log the error
            logger.error(f"Error searching papers: {e}", exc_info=True)
            
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
        
        Overrides the base method to handle paragraph metadata.
        Reuses most of the base logic but adapts for paragraph structure.
        """
        # If no filters, return original results
        if not filters:
            return results
            
        filtered_results = []
        
        for doc_id, score, metadata in results:
            # Skip if this isn't a paragraph (should have paper_id)
            if 'paper_id' not in metadata:
                continue
                
            # Get paper metadata from the paragraph metadata
            # We include basic paper metadata in each paragraph for quick filtering
            
            # Check year range
            year = metadata.get('publication_year')
            if filters.year_min is not None and (year is None or year < filters.year_min):
                continue
            if filters.year_max is not None and (year is None or year > filters.year_max):
                continue
                
            # Check authors
            if filters.authors:
                authors = metadata.get('authors', [])
                if not any(self._partial_match(author, filters.authors) for author in authors):
                    continue
                    
            # Check keywords - this may require fetching paper metadata
            if filters.keywords:
                # Two options: check if keywords in paragraph text,
                # or get paper metadata and check its keywords
                paragraph_text = metadata.get('text', '')
                if not any(keyword.lower() in paragraph_text.lower() for keyword in filters.keywords):
                    # Keywords not found in paragraph, check paper metadata
                    paper_id = metadata.get('paper_id')
                    paper_data = metadata_db.get_paper(paper_id)
                    
                    if paper_data:
                        paper_keywords = paper_data.get('keywords', [])
                        if not any(self._partial_match(keyword, filters.keywords) for keyword in paper_keywords):
                            continue
                    else:
                        # No paper data or keywords, skip
                        continue
                    
            # Check conference
            if filters.conference and not self._partial_match(metadata.get('conference', ''), [filters.conference]):
                continue
                
            # Check journal
            if filters.journal and not self._partial_match(metadata.get('journal', ''), [filters.journal]):
                continue
                
            # Add to filtered results
            filtered_results.append((doc_id, score, metadata))
            
        return filtered_results
    
    def _group_by_paper(self, 
                      results: List[Tuple[str, float, Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
        """Group paragraph results by paper.
        
        This is specific to paragraph search - not in base class.
        
        Args:
            results: List of (doc_id, score, metadata) tuples
            
        Returns:
            Dictionary of paper_id -> paper data with paragraphs
        """
        paper_results = {}
        
        for doc_id, score, metadata in results:
            paper_id = metadata.get('paper_id')
            
            if not paper_id:
                # This is likely a paper rather than a paragraph
                continue
                
            if paper_id not in paper_results:
                paper_results[paper_id] = {
                    'paper_id': paper_id,
                    'paragraphs': [],
                    'max_score': 0,
                    'metadata': {
                        'title': metadata.get('title', ''),
                        'authors': metadata.get('authors', []),
                        'publication_year': metadata.get('publication_year'),
                        'conference': metadata.get('conference'),
                        'journal': metadata.get('journal'),
                        'filename': metadata.get('filename', ''),
                        'file_path': metadata.get('file_path', '')
                    }
                }
            
            # Add this paragraph
            paragraph_info = {
                'doc_id': doc_id,
                'text': metadata.get('text', ''),
                'context': metadata.get('context', ''),
                'score': score,
                'section': metadata.get('section', 'unknown'),
                'paragraph_index': metadata.get('paragraph_index', 0),
                'is_header': metadata.get('is_header', False)
            }
            
            paper_results[paper_id]['paragraphs'].append(paragraph_info)
            
            # Keep track of the highest score for sorting
            if score > paper_results[paper_id]['max_score']:
                paper_results[paper_id]['max_score'] = score
        
        # Sort paragraphs within each paper
        for paper_id, paper_data in paper_results.items():
            paper_data['paragraphs'] = sorted(
                paper_data['paragraphs'],
                key=lambda x: x['score'],
                reverse=True
            )
            
            # Limit paragraphs per paper
            paper_data['paragraphs'] = paper_data['paragraphs'][:self.max_paragraphs_per_paper]
        
        return paper_results
    
    def _convert_to_result_items(self, 
                               paper_data_list: List[Dict[str, Any]]) -> List[SearchResultItem]:
        """Convert grouped paper data to SearchResultItem objects.
        
        This is specific to paragraph search - extends base functionality.
        
        Args:
            paper_data_list: List of paper data dictionaries
            
        Returns:
            List of SearchResultItem objects
        """
        result_items = []
        
        for paper_data in paper_data_list:
            metadata = paper_data['metadata']
            
            # Get paper abstract from database if not in metadata
            abstract = metadata.get('abstract')
            if not abstract and 'paper_id' in paper_data:
                paper_record = metadata_db.get_paper(paper_data['paper_id'])
                if paper_record:
                    abstract = paper_record.get('abstract')
                    # Also get keywords if available
                    metadata['keywords'] = paper_record.get('keywords', [])
            
            # Convert paragraphs to ParagraphMatch objects
            paragraph_matches = []
            for para in paper_data['paragraphs']:
                # Skip section headers
                if para.get('is_header', False):
                    continue
                    
                paragraph_matches.append(
                    ParagraphMatch(
                        text=para['text'],
                        context=para.get('context', ''),
                        score=para['score'],
                        section=para['section'],
                        paragraph_index=para['paragraph_index']
                    )
                )
            
            # Create result item
            result_items.append(
                SearchResultItem(
                    paper_id=paper_data['paper_id'],
                    title=metadata.get('title', ''),
                    authors=metadata.get('authors', []),
                    publication_year=metadata.get('publication_year'),
                    abstract=abstract,
                    similarity_score=paper_data['max_score'],
                    filename=metadata.get('filename', ''),
                    file_path=metadata.get('file_path', ''),
                    conference=metadata.get('conference'),
                    journal=metadata.get('journal'),
                    keywords=metadata.get('keywords', []),
                    matching_paragraphs=paragraph_matches
                )
            )
        
        return result_items
        
    # Inherit get_filter_options from the base class - no need to override
    # async def get_filter_options(self) -> Dict[str, Any]:
    #     """Get available filter options from the database."""
    #     return await super().get_filter_options()


# Create a singleton instance
paragraph_search_service = ParagraphSearchService()