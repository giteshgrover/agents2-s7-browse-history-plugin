"""
Text chunking utilities
"""

from typing import List

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks
    
    Args:
        text: Text to chunk
        chunk_size: Maximum size of each chunk (in characters)
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # If not the last chunk, try to break at word boundary
        if end < len(text):
            # Look for sentence boundary first
            last_period = text.rfind('.', start, end)
            last_newline = text.rfind('\n', start, end)
            last_space = text.rfind(' ', start, end)
            
            break_point = max(last_period, last_newline, last_space)
            
            if break_point > start:
                end = break_point + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start with overlap
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def chunk_text_by_sentences(text: str, sentences_per_chunk: int = 5) -> List[str]:
    """
    Split text into chunks by sentences
    
    Args:
        text: Text to chunk
        sentences_per_chunk: Number of sentences per chunk
        
    Returns:
        List of text chunks
    """
    import re
    
    # Split by sentence endings
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    chunks = []
    for i in range(0, len(sentences), sentences_per_chunk):
        chunk = ' '.join(sentences[i:i + sentences_per_chunk])
        chunks.append(chunk)
    
    return chunks

