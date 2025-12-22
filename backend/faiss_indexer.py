"""
FAISS indexer for storing and searching page content chunks
"""

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
import pickle

class FAISSIndexer:
    def __init__(self, index_path: str = "faiss_index", embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize FAISS indexer
        
        Args:
            index_path: Path to store FAISS index and metadata
            embedding_model: Sentence transformer model name
        """
        self.index_path = index_path
        self.embedding_model_name = embedding_model
        self.model = SentenceTransformer(embedding_model)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        # Create index directory if it doesn't exist
        os.makedirs(index_path, exist_ok=True)
        
        # Load or create FAISS index
        self.index_file = os.path.join(index_path, "index.faiss")
        self.metadata_file = os.path.join(index_path, "metadata.pkl")
        
        if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
            self.index = faiss.read_index(self.index_file)
            with open(self.metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)
        else:
            # Create new index (L2 distance)
            self.index = faiss.IndexFlatL2(self.dimension)
            self.metadata = []
        
        self.chunk_size = 500  # Characters per chunk
        self.chunk_overlap = 50  # Overlap between chunks
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # If not the last chunk, try to break at word boundary
            if end < len(text):
                # Look for sentence boundary first
                last_period = text.rfind('.', start, end)
                last_newline = text.rfind('\n', start, end)
                break_point = max(last_period, last_newline)
                
                if break_point > start:
                    end = break_point + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def add_page(self, url: str, title: str, description: str, text: str, timestamp: str) -> int:
        """
        Add a page's content to the FAISS index
        
        Args:
            url: Page URL
            title: Page title
            description: Page description
            text: Page text content
            timestamp: Timestamp of page visit
            
        Returns:
            Number of chunks added
        """
        # Chunk the text
        chunks = self.chunk_text(text)
        
        if not chunks:
            return 0
        
        # Create embeddings for all chunks
        embeddings = self.model.encode(chunks, show_progress_bar=False)
        embeddings = np.array(embeddings).astype('float32')
        
        # Add to FAISS index
        self.index.add(embeddings)
        
        # Store metadata for each chunk
        start_idx = len(self.metadata)
        for i, chunk in enumerate(chunks):
            self.metadata.append({
                'url': url,
                'title': title,
                'description': description,
                'chunk_text': chunk,
                'chunk_index': i,
                'total_chunks': len(chunks),
                'timestamp': timestamp,
                'faiss_id': start_idx + i
            })
        
        # Save index and metadata
        self.save()
        
        return len(chunks)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search the FAISS index
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of search results with metadata
        """
        if self.index.ntotal == 0:
            return []
        
        # Encode query
        query_embedding = self.model.encode([query])
        query_embedding = np.array(query_embedding).astype('float32')
        
        # Search
        k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_embedding, k)
        
        # Get metadata for results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.metadata):
                result = self.metadata[idx].copy()
                result['distance'] = float(distances[0][i])
                results.append(result)
        
        return results
    
    def save(self):
        """Save FAISS index and metadata to disk"""
        faiss.write_index(self.index, self.index_file)
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.metadata, f)
    
    def get_index_size(self) -> int:
        """Get number of vectors in index"""
        return self.index.ntotal
    
    def get_total_pages(self) -> int:
        """Get total number of unique pages indexed"""
        unique_urls = set(m['url'] for m in self.metadata)
        return len(unique_urls)
    
    def export_to_colab(self, output_path: str = "faiss_index_colab.zip"):
        """
        Export index for use in Google Colab
        
        Args:
            output_path: Path to save the zip file
        """
        import shutil
        shutil.make_archive(output_path.replace('.zip', ''), 'zip', self.index_path)
        return output_path

