import os
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
import re
import torch

from app.core.config import settings


class LLMService:
    """Service for embedding generation and semantic analysis.
    
    Uses pre-trained transformer models to generate embeddings for
    search queries and document text.
    """
    
    def __init__(self, model_name: str = None, model_dir: str = None):
        """Initialize the embedding service with a pre-trained model.
        
        Args:
            model_name: Name of the pre-trained model to use
            model_dir: Directory where models are cached
        """
        self.model_dir = Path(model_dir or settings.LLM_MODEL_DIR)
        self.model_name = model_name or settings.LLM_MODEL_NAME
        self.model = None
        
        # Ensure model directory exists
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Load model
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the pre-trained transformer model for embeddings.
        
        If the model has been previously downloaded, it's loaded from local cache.
        Otherwise, it's downloaded (requires internet access during first run).
        """
        model_path = self.model_dir / self.model_name
        
        # Check if model is already downloaded
        if model_path.exists():
            self.model = SentenceTransformer(str(model_path))
        else:
            # Download model if not available locally
            print(f"Downloading model {self.model_name}...")
            self.model = SentenceTransformer(self.model_name)
            
            # Save model for future offline use
            os.makedirs(model_path, exist_ok=True)
            self.model.save(str(model_path))
            print(f"Model saved to {model_path}")
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Generate an embedding for the given text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        # Preprocess text
        processed_text = self._preprocess_text(text)
        
        # Generate embedding
        embedding = self.model.encode(processed_text, convert_to_numpy=True)
        return embedding
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts.
        
        This is more efficient than calling get_embedding multiple times
        as it batches the computation.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Array of embedding vectors
        """
        # Preprocess texts
        processed_texts = [self._preprocess_text(text) for text in texts]
        
        # Generate embeddings
        embeddings = self.model.encode(processed_texts, convert_to_numpy=True)
        return embeddings
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for embedding.
        
        Cleans text by removing extra whitespace and normalizing it.
        
        Args:
            text: Raw text
            
        Returns:
            Processed text
        """
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep important punctuation
        text = re.sub(r'[^\w\s.,;:!?()]', '', text)
        
        # Trim
        text = text.strip()
        
        return text
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate the cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score (0-1)
        """
        # Convert to PyTorch tensors if they're not already
        if isinstance(embedding1, np.ndarray):
            embedding1 = torch.from_numpy(embedding1)
        if isinstance(embedding2, np.ndarray):
            embedding2 = torch.from_numpy(embedding2)
        
        # Normalize the vectors
        embedding1 = embedding1 / embedding1.norm()
        embedding2 = embedding2 / embedding2.norm()
        
        # Calculate cosine similarity
        similarity = torch.dot(embedding1, embedding2).item()
        
        # Ensure the result is between 0 and 1
        return max(0, min(1, similarity))
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text.
        
        Uses a simple frequency-based approach with stopword filtering.
        
        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of keywords
        """
        # For a simple implementation, we'll use common word filtering
        
        # Lowercase and tokenize
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Remove common stop words
        stop_words = set([
            'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'in', 'on', 'at', 'to', 'for', 'with',
            'by', 'about', 'against', 'between', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'from', 'up', 'down', 'of',
            'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them',
            'their', 'who', 'whom', 'whose', 'which', 'what', 'where', 'when',
            'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most',
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'can', 'will', 'just', 'should', 'now'
        ])
        
        # Filter out stop words and count occurrences
        word_counts = {}
        for word in words:
            if word not in stop_words and len(word) > 2:  # Ignore very short words
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Return the top keywords
        return [word for word, count in sorted_words[:max_keywords]]


# Create a singleton instance
llm_service = LLMService()