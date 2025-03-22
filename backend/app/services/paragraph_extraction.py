import re
from typing import List, Dict, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("paragraph_extraction")

class ParagraphExtractionService:
    """Service for extracting and processing paragraphs from research paper text.
    
    Identifies paragraphs, sections, and manages the chunking of papers for 
    more granular semantic search.
    """
    
    def __init__(self, 
                 min_paragraph_length: int = 50,
                 max_paragraph_length: int = 1000):
        """Initialize the paragraph extraction service.
        
        Args:
            min_paragraph_length: Minimum character length to consider as a paragraph
            max_paragraph_length: Maximum paragraph length before considering splitting
        """
        self.min_paragraph_length = min_paragraph_length
        self.max_paragraph_length = max_paragraph_length
        
        # Common section patterns in research papers
        self.section_patterns = [
            r"abstract",
            r"introduction",
            r"related\s+work",
            r"background",
            r"methodology|methods",
            r"experimental?\s+setup|experimental?\s+design",
            r"implementation",
            r"evaluation|experiments|results",
            r"discussion",
            r"conclusion",
            r"references|bibliography",
            r"appendix"
        ]
        
        # Regex for identifying section headers
        self.section_header_pattern = r"(?i)^[0-9.]*\s*(" + "|".join(self.section_patterns) + r")[\s:.]*$"
    
    def extract_paragraphs(self, text: str) -> List[Dict[str, Any]]:
        """Extract paragraphs from paper text.
        
        Args:
            text: Full text content of the paper
            
        Returns:
            List of dictionaries with paragraph data:
            - text: The paragraph text
            - section: The paper section this paragraph belongs to
            - is_header: Whether this is a section header
        """
        # Split text into lines
        lines = text.split('\n')
        
        paragraphs = []
        current_paragraph = []
        current_section = "preamble"
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            
            # Check if this is a section header
            section_match = re.match(self.section_header_pattern, line)
            if section_match:
                # Save current paragraph if it exists
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    if len(paragraph_text) >= self.min_paragraph_length:
                        paragraphs.append({
                            'text': paragraph_text,
                            'section': current_section,
                            'is_header': False,
                            'line_num': line_num - len(current_paragraph)
                        })
                    current_paragraph = []
                
                # Save section header as a special paragraph
                current_section = section_match.group(1).lower()
                paragraphs.append({
                    'text': line,
                    'section': current_section,
                    'is_header': True,
                    'line_num': line_num
                })
                continue
            
            # Handle paragraph breaks (empty lines)
            if not line and current_paragraph:
                paragraph_text = ' '.join(current_paragraph)
                if len(paragraph_text) >= self.min_paragraph_length:
                    paragraphs.append({
                        'text': paragraph_text,
                        'section': current_section,
                        'is_header': False,
                        'line_num': line_num - len(current_paragraph)
                    })
                current_paragraph = []
                continue
            
            # Add non-empty lines to current paragraph
            if line:
                # Check if this might be a subsection header
                if re.match(r'^[0-9.]+\s+\w+', line) and current_paragraph:
                    # Save current paragraph before starting a new one with the subsection
                    paragraph_text = ' '.join(current_paragraph)
                    if len(paragraph_text) >= self.min_paragraph_length:
                        paragraphs.append({
                            'text': paragraph_text,
                            'section': current_section,
                            'is_header': False,
                            'line_num': line_num - len(current_paragraph)
                        })
                    current_paragraph = []
                
                current_paragraph.append(line)
                
                # Check if current paragraph is getting too long
                current_text = ' '.join(current_paragraph)
                if len(current_text) > self.max_paragraph_length:
                    paragraphs.append({
                        'text': current_text,
                        'section': current_section,
                        'is_header': False,
                        'line_num': line_num - len(current_paragraph)
                    })
                    current_paragraph = []
        
        # Add final paragraph if it exists
        if current_paragraph:
            paragraph_text = ' '.join(current_paragraph)
            if len(paragraph_text) >= self.min_paragraph_length:
                paragraphs.append({
                    'text': paragraph_text,
                    'section': current_section,
                    'is_header': False,
                    'line_num': len(lines) - len(current_paragraph)
                })
        
        # Post-process paragraphs
        processed_paragraphs = self._post_process_paragraphs(paragraphs)
        
        logger.info(f"Extracted {len(processed_paragraphs)} paragraphs from text of length {len(text)}")
        return processed_paragraphs
    
    def _post_process_paragraphs(self, paragraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Post-process extracted paragraphs.
        
        - Merges very short paragraphs
        - Removes duplicates
        - Adds paragraph numbers
        
        Args:
            paragraphs: List of paragraph dictionaries
            
        Returns:
            Processed list of paragraphs
        """
        if not paragraphs:
            return []
        
        # Remove duplicate paragraphs (same text)
        seen_texts = set()
        unique_paragraphs = []
        
        for para in paragraphs:
            # Skip very short paragraphs that aren't headers
            if len(para['text']) < self.min_paragraph_length and not para['is_header']:
                continue
                
            # Skip duplicates
            if para['text'] in seen_texts:
                continue
                
            seen_texts.add(para['text'])
            unique_paragraphs.append(para)
        
        # Add paragraph numbers
        for i, para in enumerate(unique_paragraphs):
            para['paragraph_index'] = i
        
        return unique_paragraphs
    
    def get_paragraph_context(self, 
                             paragraphs: List[Dict[str, Any]], 
                             paragraph_index: int, 
                             context_size: int = 1) -> str:
        """Get context around a paragraph by including adjacent paragraphs.
        
        Args:
            paragraphs: List of all paragraphs
            paragraph_index: Index of the target paragraph
            context_size: Number of paragraphs to include before and after
            
        Returns:
            Combined text with context
        """
        if not paragraphs or paragraph_index >= len(paragraphs):
            return ""
        
        start_idx = max(0, paragraph_index - context_size)
        end_idx = min(len(paragraphs), paragraph_index + context_size + 1)
        
        # Collect paragraphs
        context_paragraphs = []
        for i in range(start_idx, end_idx):
            # Skip section headers in context to avoid repetition
            if i != paragraph_index and paragraphs[i].get('is_header', False):
                continue
            context_paragraphs.append(paragraphs[i]['text'])
        
        return "\n\n".join(context_paragraphs)


# Create singleton instance
paragraph_extraction_service = ParagraphExtractionService()