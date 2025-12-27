# memory.py

import numpy as np
import faiss
import requests
from typing import List, Optional, Literal
from pydantic import BaseModel
from datetime import datetime
import pdb
from agent.logger import logger


class MemoryItem(BaseModel):
    text: str
    type: Literal["preference", "tool_output", "fact", "query", "system"] = "fact"
    timestamp: Optional[str] = datetime.now().isoformat()
    tool_name: Optional[str] = None
    user_query: Optional[str] = None
    tags: List[str] = []
    session_id: Optional[str] = None

# Memory Manager itself is a Embedding based manager. When an item is added, it calculates and adds its embedding in a local faiss index (in memory)
class MemoryManager:
    def __init__(self, embedding_model_url="http://localhost:11434/api/embeddings", model_name="nomic-embed-text"):
        self.embedding_model_url = embedding_model_url
        self.model_name = model_name
        self.index = None
        self.data: List[MemoryItem] = []
        self.embeddings: List[np.ndarray] = []

    def _get_embedding(self, text: str) -> np.ndarray:
        try:
            response = requests.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": "nomic-embed-text",
                    "prompt": text
                }
            )
            pdb.set_trace()
            response.raise_for_status()
            return np.array(response.json()["embedding"], dtype=np.float32)
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Ollama at {self.embedding_model_url}. Is Ollama running? Error: {e}")
            raise RuntimeError(
                f"Could not connect to Ollama embedding service at {self.embedding_model_url}. "
                f"Please ensure Ollama is running (e.g., 'ollama serve') and the model '{self.model_name}' is available."
            ) from e
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            status_code = None
            try:
                if hasattr(e, 'response') and e.response is not None:
                    status_code = e.response.status_code
                    error_detail = f" Response: {e.response.text}"
            except:
                pass
            logger.error(f"Ollama API returned error {status_code or 'unknown'} for model '{self.model_name}'.{error_detail}")
            if status_code == 500:
                raise RuntimeError(
                    f"Ollama server returned 500 error. This usually means:\n"
                    f"1. The model '{self.model_name}' is not available. Try: 'ollama pull {self.model_name}'\n"
                    f"2. Ollama server has an internal error. Check Ollama logs.\n"
                    f"3. The request format is incorrect. Error details: {error_detail}"
                ) from e
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout connecting to Ollama at {self.embedding_model_url}")
            raise RuntimeError(f"Timeout waiting for Ollama embedding service. Is Ollama running?") from e

    def add(self, item: MemoryItem):
        emb = self._get_embedding(item.text)
        self.embeddings.append(emb)
        self.data.append(item)

        # Initialize or add to index
        if self.index is None:
            self.index = faiss.IndexFlatL2(len(emb))
        self.index.add(np.stack([emb]))

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        type_filter: Optional[str] = None,
        tag_filter: Optional[List[str]] = None,
        session_filter: Optional[str] = None
    ) -> List[MemoryItem]:
        if not self.index or len(self.data) == 0:
            return []

        query_vec = self._get_embedding(query).reshape(1, -1)
        D, I = self.index.search(query_vec, top_k * 2)  # Overfetch to allow filtering

        results = []
        for idx in I[0]:
            if idx >= len(self.data):
                continue
            item = self.data[idx]

            # Filter by type
            if type_filter and item.type != type_filter:
                continue

            # Filter by tags
            if tag_filter and not any(tag in item.tags for tag in tag_filter):
                continue

            # Filter by session
            if session_filter and item.session_id != session_filter:
                continue

            results.append(item)
            if len(results) >= top_k:
                break

        return results

    def bulk_add(self, items: List[MemoryItem]):
        for item in items:
            self.add(item)
