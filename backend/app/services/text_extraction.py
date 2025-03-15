import os
from typing import Dict, Any, Optional, Tuple, List
import re
from pathlib import Path
import PyPDF2
import io

from app.core.config import settings
from app.core.models import PaperMetadata


class TextExtractionService:
    """Service for extracting text and metadata from PDF files.
    
    Provides functionality to extract full text content from PDF files
    and also attempt to extract metadata like title, authors, abstract, etc.
    """
    
    def __init__(self):
        """Initialize the text extraction service."""
        pass
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract full text content from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content
        """
        text = ""
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Extract text from each page
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text() + "\n\n"
                
                return text
                
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    def extract_sections(self, text: str) -> Dict[str, str]:
        """Extract common sections from the paper text.
        
        Args:
            text: Full text content of the paper
            
        Returns:
            Dictionary with section names as keys and section text as values
        """
        # Common section names in research papers
        section_patterns = [
            r"abstract",
            r"introduction",
            r"related\s+work",
            r"background",
            r"methodology|methods",
            r"experimental?\s+setup|experimental?\s+design",
            r"evaluation|experiments|results",
            r"discussion",
            r"conclusion",
            r"references|bibliography"
        ]
        
        # Combine patterns to detect section headers
        pattern = r"(?i)^[0-9.]*\s*(" + "|".join(section_patterns) + r")[\s:.]*$"
        
        # Split text into lines
        lines = text.split('\n')
        
        # Identify section boundaries
        sections = {}
        current_section = "preamble"
        current_content = []
        
        for line in lines:
            match = re.match(pattern, line.strip())
            if match:
                # Save the previous section
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                
                # Start a new section
                current_section = match.group(1).lower()
                current_content = []
            else:
                current_content.append(line)
        
        # Save the last section
        if current_content:
            sections[current_section] = "\n".join(current_content).strip()
        
        return sections
    
    def extract_metadata(self, text: str, filename: str) -> PaperMetadata:
        """Extract metadata from the paper text.
        
        Args:
            text: Full text content of the paper
            filename: Name of the PDF file
            
        Returns:
            PaperMetadata object with extracted metadata
        """
        # Extract sections to help with metadata extraction
        sections = self.extract_sections(text)
        
        # Initialize metadata with default values
        metadata = {
            "title": self._extract_title(text, filename, sections),
            "authors": self._extract_authors(text, sections),
            "abstract": self._extract_abstract(text, sections),
            "publication_year": self._extract_year(text, filename),
            "doi": self._extract_doi(text),
            "keywords": self._extract_keywords(text, sections),
            "conference": None,  # More sophisticated extraction needed
            "journal": None,     # More sophisticated extraction needed
        }
        
        return PaperMetadata(**metadata)
    
    def _extract_title(self, text: str, filename: str, sections: Dict[str, str]) -> str:
        """Extract paper title from text or filename.
        
        Args:
            text: Paper text
            filename: Name of the PDF file
            sections: Paper sections
            
        Returns:
            Extracted title or empty string
        """
        # Try to find the title at the beginning of the paper
        lines = text.split('\n')
        
        # Look for the first substantial line, which is often the title
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if line and len(line) > 15 and not line.lower().startswith(('abstract', 'introduction')):
                # Likely the title
                return line
        
        # Fallback to filename without extension
        return Path(filename).stem.replace('_', ' ').title()
    
    def _extract_authors(self, text: str, sections: Dict[str, str]) -> List[str]:
        """Extract authors from paper text.
        
        Args:
            text: Paper text
            sections: Paper sections
            
        Returns:
            List of author names
        """
        # Try to find author lines near the beginning
        lines = text.split('\n')
        
        # Authors typically appear in the first few lines after the title
        potential_author_lines = []
        for line in lines[1:30]:  # Check lines after potential title
            line = line.strip()
            
            # Skip empty lines and lines that look like section headers
            if not line or re.match(r'^(abstract|introduction|keywords)', line.lower()):
                continue
                
            # Lines with email addresses or affiliations often contain authors
            if '@' in line or re.search(r'university|institute|department', line.lower()):
                potential_author_lines.append(line)
            
            # Lines with multiple names separated by commas or 'and'
            if ',' in line or ' and ' in line.lower():
                potential_author_lines.append(line)
        
        # Extract names from the most promising line
        authors = []
        if potential_author_lines:
            best_line = potential_author_lines[0]
            
            # Split by common separators
            for separator in [', ', ' and ', '; ']:
                if separator in best_line:
                    name_parts = best_line.split(separator)
                    for part in name_parts:
                        # Clean up name part
                        name = re.sub(r'[0-9*†]', '', part)  # Remove numbers and footnote symbols
                        name = re.sub(r'\s+', ' ', name)     # Normalize whitespace
                        name = name.strip()
                        
                        # Check if it looks like a name
                        if name and len(name) > 3 and not '@' in name:
                            authors.append(name)
                    
                    if authors:
                        break
        
        # If no authors were found, return an empty list
        return authors
    
    def _extract_abstract(self, text: str, sections: Dict[str, str]) -> Optional[str]:
        """Extract abstract from paper text.
        
        Args:
            text: Paper text
            sections: Paper sections
            
        Returns:
            Abstract text or None
        """
        # Check if we have an abstract section
        if 'abstract' in sections:
            return sections['abstract']
        
        # Try to find an abstract using regex
        abstract_match = re.search(r'(?i)abstract[:\.\s]+(.*?)(?=\n\n|\n[A-Z]|\nKeywords|\n[0-9]\.)', text)
        if abstract_match:
            return abstract_match.group(1).strip()
        
        return None
    
    def _extract_year(self, text: str, filename: str) -> Optional[int]:
        """Extract publication year from text or filename.
        
        Args:
            text: Paper text
            filename: Name of the PDF file
            
        Returns:
            Publication year as int or None
        """
        # Look for years in the text (typically in the first few pages)
        # We limit to reasonable publication years (1990-2030)
        year_matches = re.findall(r'\b(19[9][0-9]|20[0-3][0-9])\b', text[:10000])
        
        if year_matches:
            # Take the most common year
            year_counts = {}
            for year in year_matches:
                year_counts[year] = year_counts.get(year, 0) + 1
            
            most_common_year = max(year_counts.items(), key=lambda x: x[1])[0]
            return int(most_common_year)
        
        # Try to find year in filename
        filename_year_match = re.search(r'\b(19[9][0-9]|20[0-3][0-9])\b', filename)
        if filename_year_match:
            return int(filename_year_match.group(1))
        
        return None
    
    def _extract_doi(self, text: str) -> Optional[str]:
        """Extract DOI from paper text.
        
        Args:
            text: Paper text
            
        Returns:
            DOI or None
        """
        # Look for DOI patterns in the text
        doi_match = re.search(r'(?i)(?:doi|DOI)[\s:\.\]]+([0-9\.]{2,}/\S+)', text)
        if doi_match:
            return doi_match.group(1).strip()
        
        return None
    
    def _extract_keywords(self, text: str, sections: Dict[str, str]) -> List[str]:
        """Extract keywords from paper text.
        
        Args:
            text: Paper text
            sections: Paper sections
            
        Returns:
            List of keywords
        """
        # Look for a keywords section
        keyword_match = re.search(r'(?i)keywords[ :]+(.+?)(?:\n\n|\n[A-Z])', text)
        if keyword_match:
            keyword_text = keyword_match.group(1).strip()
            
            # Split by common separators
            keywords = []
            if ',' in keyword_text:
                keywords = [k.strip() for k in keyword_text.split(',')]
            elif ';' in keyword_text:
                keywords = [k.strip() for k in keyword_text.split(';')]
            else:
                keywords = [keyword_text]
                
            return keywords
        
        return []


# Create a singleton instance
text_extraction_service = TextExtractionService()