import sqlite3
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
from pathlib import Path

from app.core.config import settings


class MetadataDB:
    """Database for storing paper metadata and managing search indexes.
    
    Uses SQLite for efficient storage and retrieval of paper metadata,
    with indexes for common search operations.
    """
    
    def __init__(self, db_path: str = None):
        """Initialize the metadata database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path or settings.METADATA_DB_PATH
        self.conn = None
        self._connect()
        self._create_tables()


    def _connect(self):
        """Connect to the SQLite database."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Return rows as dictionaries
        self.conn.row_factory = sqlite3.Row


    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Papers table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            abstract TEXT,
            publication_year INTEGER,
            doi TEXT,
            url TEXT,
            conference TEXT,
            journal TEXT,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            paragraph_count INTEGER,
            ingestion_date TIMESTAMP NOT NULL,
            last_updated TIMESTAMP NOT NULL
        )
        ''')
        
        # Authors table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS authors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            UNIQUE(name)
        )
        ''')
        
        # Paper-Author relationship table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS paper_authors (
            paper_id TEXT,
            author_id INTEGER,
            PRIMARY KEY (paper_id, author_id),
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
            FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
        )
        ''')
        
        # Keywords table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            UNIQUE(keyword)
        )
        ''')
        
        # Paper-Keyword relationship table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS paper_keywords (
            paper_id TEXT,
            keyword_id INTEGER,
            PRIMARY KEY (paper_id, keyword_id),
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
            FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
        )
        ''')
        
        # Create indexes for efficient searching
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(publication_year)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_conference ON papers(conference)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_papers_journal ON papers(journal)')
        
        self.conn.commit()


    def add_paper(self, paper_data: Dict[str, Any]) -> str:
        """Add a new paper to the database.
        
        Args:
            paper_data: Dictionary containing paper metadata
            
        Returns:
            ID of the newly added paper
        """
        cursor = self.conn.cursor()
        
        # Generate a unique ID if not provided
        paper_id = paper_data.get('id', str(uuid.uuid4()))
        
        # Current timestamp
        now = datetime.now().isoformat()
        
        # Insert paper record
        cursor.execute('''
        INSERT INTO papers 
        (id, title, abstract, publication_year, doi, url, conference, journal, 
         filename, file_path, paragraph_count, ingestion_date, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            paper_id,
            paper_data['title'],
            paper_data.get('abstract'),
            paper_data.get('publication_year'),
            paper_data.get('doi'),
            paper_data.get('url'),
            paper_data.get('conference'),
            paper_data.get('journal'),
            paper_data['filename'],
            paper_data['file_path'],
            paper_data['paragraph_count'],
            now,
            now
        ))
        
        # Add authors
        self._add_authors(paper_id, paper_data.get('authors', []))
        
        # Add keywords
        self._add_keywords(paper_id, paper_data.get('keywords', []))
        
        self.conn.commit()
        return paper_id


    def _add_authors(self, paper_id: str, authors: List[str]) -> None:
        """Add authors for a paper.
        
        Args:
            paper_id: ID of the paper
            authors: List of author names
        """
        cursor = self.conn.cursor()
        
        for author in authors:
            # Insert author if not exists
            cursor.execute('''
            INSERT OR IGNORE INTO authors (name) VALUES (?)
            ''', (author,))
            
            # Get author ID
            cursor.execute('SELECT id FROM authors WHERE name = ?', (author,))
            author_id = cursor.fetchone()[0]
            
            # Link author to paper
            cursor.execute('''
            INSERT INTO paper_authors (paper_id, author_id) VALUES (?, ?)
            ''', (paper_id, author_id))


    def _add_keywords(self, paper_id: str, keywords: List[str]) -> None:
        """Add keywords for a paper.
        
        Args:
            paper_id: ID of the paper
            keywords: List of keywords
        """
        cursor = self.conn.cursor()
        
        for keyword in keywords:
            # Insert keyword if not exists
            cursor.execute('''
            INSERT OR IGNORE INTO keywords (keyword) VALUES (?)
            ''', (keyword,))
            
            # Get keyword ID
            cursor.execute('SELECT id FROM keywords WHERE keyword = ?', (keyword,))
            keyword_id = cursor.fetchone()[0]
            
            # Link keyword to paper
            cursor.execute('''
            INSERT INTO paper_keywords (paper_id, keyword_id) VALUES (?, ?)
            ''', (paper_id, keyword_id))


    def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get paper details by ID.
        
        Args:
            paper_id: ID of the paper
            
        Returns:
            Dictionary with paper details or None if not found
        """
        cursor = self.conn.cursor()
        
        # Get paper details
        cursor.execute('SELECT * FROM papers WHERE id = ?', (paper_id,))
        paper_row = cursor.fetchone()
        
        if not paper_row:
            return None
        
        # Convert row to dict
        paper = dict(paper_row)
        
        # Get authors
        cursor.execute('''
        SELECT a.name 
        FROM authors a
        JOIN paper_authors pa ON a.id = pa.author_id
        WHERE pa.paper_id = ?
        ''', (paper_id,))
        
        paper['authors'] = [row[0] for row in cursor.fetchall()]
        
        # Get keywords
        cursor.execute('''
        SELECT k.keyword 
        FROM keywords k
        JOIN paper_keywords pk ON k.id = pk.keyword_id
        WHERE pk.paper_id = ?
        ''', (paper_id,))
        
        paper['keywords'] = [row[0] for row in cursor.fetchall()]
        
        return paper
    

    def search_papers(self, filters: Dict[str, Any], limit: int = 10, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """Search for papers using metadata filters.
        
        Args:
            filters: Dictionary of search criteria
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            Tuple of (list of matching papers, total count)
        """
        cursor = self.conn.cursor()
        
        # Start building query
        query = 'SELECT DISTINCT p.* FROM papers p'
        count_query = 'SELECT COUNT(DISTINCT p.id) FROM papers p'
        
        params = []
        where_clauses = []
        join_authors = False
        join_keywords = False
        
        # Handle filters
        if 'year_min' in filters and filters['year_min'] is not None:
            where_clauses.append('p.publication_year >= ?')
            params.append(filters['year_min'])
        
        if 'year_max' in filters and filters['year_max'] is not None:
            where_clauses.append('p.publication_year <= ?')
            params.append(filters['year_max'])
        
        if 'title' in filters and filters['title']:
            where_clauses.append('p.title LIKE ?')
            params.append(f'%{filters["title"]}%')
        
        if 'conference' in filters and filters['conference']:
            where_clauses.append('p.conference LIKE ?')
            params.append(f'%{filters["conference"]}%')
        
        if 'journal' in filters and filters['journal']:
            where_clauses.append('p.journal LIKE ?')
            params.append(f'%{filters["journal"]}%')
            
        # Author filter requires joining with authors table
        if 'authors' in filters and filters['authors']:
            join_authors = True
            query += ' JOIN paper_authors pa ON p.id = pa.paper_id JOIN authors a ON pa.author_id = a.id'
            count_query += ' JOIN paper_authors pa ON p.id = pa.paper_id JOIN authors a ON pa.author_id = a.id'
            
            author_clauses = []
            for author in filters['authors']:
                author_clauses.append('a.name LIKE ?')
                params.append(f'%{author}%')
            
            if author_clauses:
                where_clauses.append(f'({" OR ".join(author_clauses)})')
        
        # Keyword filter requires joining with keywords table
        if 'keywords' in filters and filters['keywords']:
            join_keywords = True
            query += ' JOIN paper_keywords pk ON p.id = pk.paper_id JOIN keywords k ON pk.keyword_id = k.id'
            count_query += ' JOIN paper_keywords pk ON p.id = pk.paper_id JOIN keywords k ON pk.keyword_id = k.id'
            
            keyword_clauses = []
            for keyword in filters['keywords']:
                keyword_clauses.append('k.keyword LIKE ?')
                params.append(f'%{keyword}%')
            
            if keyword_clauses:
                where_clauses.append(f'({" OR ".join(keyword_clauses)})')
        
        # Add WHERE clause if we have conditions
        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)
            count_query += ' WHERE ' + ' AND '.join(where_clauses)
        
        # Add order, limit and offset
        query += ' ORDER BY p.publication_year DESC, p.title LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        # Execute query
        cursor.execute(query, params)
        papers_rows = cursor.fetchall()
        
        # Get total count
        cursor.execute(count_query, params[:-2])  # Remove limit and offset params
        total_count = cursor.fetchone()[0]
        
        # Convert rows to dicts and add authors and keywords
        papers = []
        for row in papers_rows:
            paper = dict(row)
            paper_id = paper['id']
            
            # Get authors
            cursor.execute('''
            SELECT a.name 
            FROM authors a
            JOIN paper_authors pa ON a.id = pa.author_id
            WHERE pa.paper_id = ?
            ''', (paper_id,))
            
            paper['authors'] = [row[0] for row in cursor.fetchall()]
            
            # Get keywords
            cursor.execute('''
            SELECT k.keyword 
            FROM keywords k
            JOIN paper_keywords pk ON k.id = pk.keyword_id
            WHERE pk.paper_id = ?
            ''', (paper_id,))
            
            paper['keywords'] = [row[0] for row in cursor.fetchall()]
            papers.append(paper)
        
        return papers, total_count


    def delete_paper(self, paper_id: str) -> bool:
        """Delete a paper from the database.
        
        Args:
            paper_id: ID of the paper to delete
            
        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.cursor()
        
        # Check if paper exists
        cursor.execute('SELECT id FROM papers WHERE id = ?', (paper_id,))
        if not cursor.fetchone():
            return False
        
        # Delete paper (cascading delete will handle relationships)
        cursor.execute('DELETE FROM papers WHERE id = ?', (paper_id,))
        self.conn.commit()
        
        return True


    def get_all_authors(self) -> List[str]:
        """Get a list of all authors in the database.
        
        Returns:
            List of author names
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT name FROM authors ORDER BY name')
        return [row[0] for row in cursor.fetchall()]


    def get_all_keywords(self) -> List[str]:
        """Get a list of all keywords in the database.
        
        Returns:
            List of keywords
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT keyword FROM keywords ORDER BY keyword')
        return [row[0] for row in cursor.fetchall()]


    def get_publication_years(self) -> List[int]:
        """Get a list of all publication years in the database.
        
        Returns:
            List of years
        """
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT DISTINCT publication_year 
        FROM papers 
        WHERE publication_year IS NOT NULL 
        ORDER BY publication_year DESC
        ''')
        return [row[0] for row in cursor.fetchall()]


    def get_conferences(self) -> List[str]:
        """Get a list of all conferences in the database.
        
        Returns:
            List of conference names
        """
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT DISTINCT conference 
        FROM papers 
        WHERE conference IS NOT NULL 
        ORDER BY conference
        ''')
        return [row[0] for row in cursor.fetchall()]


    def get_journals(self) -> List[str]:
        """Get a list of all journals in the database.
        
        Returns:
            List of journal names
        """
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT DISTINCT journal 
        FROM papers 
        WHERE journal IS NOT NULL 
        ORDER BY journal
        ''')
        return [row[0] for row in cursor.fetchall()]
    
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()


# Create a singleton instance
metadata_db = MetadataDB()