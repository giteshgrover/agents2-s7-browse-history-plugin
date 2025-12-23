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
import requests
from google import genai
from google.genai import types

# embedding_model_name = "all-MiniLM-L6-v2
# embedding_model_name = "gemini-embedding-exp-03-07"
embedding_model_name = "nomic-embed-text"

class FAISSIndexer:
    def __init__(self, index_path: str = "faiss_index"):
        """
        Initialize FAISS indexer
        
        Args:
            index_path: Path to store FAISS index and metadata
            embedding_model: Sentence transformer model name
        """
        
        if embedding_model_name == "nomic-embed-text":
            self.dimension = 768
        elif embedding_model_name == "gemini-embedding-exp-03-07":
            self.dimension = 3072
            self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        else:
            self.model = SentenceTransformer(embedding_model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
        
        
        # Create index directory if it doesn't exist
        os.makedirs(index_path, exist_ok=True)
    
        # Load or create FAISS index
        self.index_path = index_path
        self.index_file = os.path.join(index_path, "index.bin") #"index.faiss"
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
    
    def get_embedding(self, text: str) -> np.ndarray:
        if embedding_model_name == "nomic-embed-text":
            response = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": text
                }
            )
            response.raise_for_status()
            return np.array(response.json()["embedding"], dtype=np.float32)
        elif embedding_model_name == "gemini-embedding-exp-03-07":
            response = self.client.models.embed_content(
                model="gemini-embedding-exp-03-07",
                contents=text,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            response.raise_for_status()
            return np.array(response.embeddings[0].values, dtype=np.float32)
        else:
            embeddings = self.model.encode(text, show_progress_bar=False)
            embeddings = np.array(embeddings).astype('float32')
            return embeddings
        

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
        # TODO optional - Check whether the text and url has already been indexed. If so, just update the timestamp

        # Chunk the text
        chunks = self.chunk_text(text)
        
        if not chunks:
            return 0
        
        # Create embedding anf Store metadata for each chunk
        page_embedding = []
        page_metadata = []
        start_idx = len(self.metadata)
        for i, chunk in enumerate(chunks):
            embedding = self.get_embedding(chunk)
            page_embedding.append(embedding)
            page_metadata.append({
                'url': url,
                'title': title,
                'description': description,
                'chunk_text': chunk,
                'chunk_index': i,
                'total_chunks': len(chunks),
                'timestamp': timestamp,
                'faiss_id': start_idx + i
            })
        print(f"Page embedding size: {len(page_embedding)}")
        print(f"Page metadata size: {len(page_metadata)}")
        print(f"Page chunk count: {len(chunks)}")
        
        self.index.add(np.stack(page_embedding))
        self.metadata.extend(page_metadata)
    
        print(f"Total index size: {self.index.ntotal}")
        print(f"Total Metadata size: {len(self.metadata)}")
        print(f"Total pages indexed: {self.get_total_pages()}")
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
        query_embedding = self.get_embedding(query).reshape(1, -1) # Reshape to 1D array
        
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

