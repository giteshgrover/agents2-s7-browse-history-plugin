"""
Backend server for Chrome extension to handle FAISS indexing
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
import os
import json
import logging
import sys
from pathlib import Path

# Add backend directory to path if needed
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from indexer.faiss_indexer import FAISSIndexer
from agent.agent import run_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Browse History Indexer Backend")

# Enable CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize FAISS indexer
logger.info("Initializing FAISS indexer...")
try:
    indexer = FAISSIndexer()
    logger.info(f"FAISS indexer initialized successfully. Index path: {indexer.index_path}")
    logger.info(f"Current index size: {indexer.get_index_size()} vectors")
except Exception as e:
    logger.error(f"Failed to initialize FAISS indexer: {e}", exc_info=True)
    raise

class PageData(BaseModel):
    url: str
    title: str
    description: Optional[str] = ""
    text: str
    timestamp: str

class IndexResponse(BaseModel):
    success: bool
    message: str
    chunks_added: int



@app.get("/health")
async def health():
    """Health check endpoint"""
    index_size = indexer.get_index_size()
    logger.debug(f"Health check requested. Index size: {index_size}")
    return {"status": "healthy", "index_size": index_size}

@app.post("/index", response_model=IndexResponse)
async def index_page(page_data: PageData):
    """
    Index a page's content using FAISS
    """
    logger.info(f"Received indexing request for URL: {page_data.url}")
    logger.info(f"Page title: {page_data.title}, Text length: {len(page_data.text)} characters")
    logger.debug(f"Page description: {page_data.description}")
    logger.debug(f"Page text: {page_data.text}")
    
    try:
        chunks_added = indexer.add_page(
            url=page_data.url,
            title=page_data.title,
            description=page_data.description or "",
            text=page_data.text,
            timestamp=page_data.timestamp
        )
        
        logger.info(f"Successfully indexed {page_data.url} - Added {chunks_added} chunks. Total index size: {indexer.get_index_size()}")
        
        return IndexResponse(
            success=True,
            message=f"Successfully indexed {page_data.url}",
            chunks_added=chunks_added
        )
    except Exception as e:
        logger.error(f"Error indexing page {page_data.url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search(query: str, top_k: int = 5):
    """
    Search the FAISS index
    """
    logger.info(f"Search request received - Query: '{query}', Top K: {top_k}")
    agent_query = f"""Search the user input '{query}' to find the top {top_k} browsing history results of the user"""
    results = await run_agent(agent_query, top_k)
    return {"results": results}
    
    # try:
    #     results = indexer.search(query, top_k=top_k)
    #     logger.info(f"Search completed - Found {len(results)} results for query: '{query}'")
        
    #     if results:
    #         logger.debug(f"Top result: {results[0].get('title', 'N/A')} (distance: {results[0].get('distance', 'N/A'):.4f})")
        
    #     return {"results": results}
    # except Exception as e:
    #     logger.error(f"Error searching index with query '{query}': {e}", exc_info=True)
    #     raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def stats():
    """
    Get indexing statistics
    """
    logger.debug("Stats request received")
    stats_data = {
        "index_size": indexer.get_index_size(),
        "total_pages": indexer.get_total_pages(),
        "index_path": indexer.index_path
    }
    logger.info(f"Stats: {stats_data['total_pages']} pages, {stats_data['index_size']} vectors")
    return stats_data

@app.on_event("startup")
async def startup_event():
    """Log server startup"""
    logger.info("=" * 60)
    logger.info("Browse History Indexer Backend Server Starting")
    logger.info("=" * 60)
    logger.info(f"Server will be available at http://0.0.0.0:8000")
    logger.info(f"API documentation available at http://localhost:8000/docs")
    logger.info(f"Current index size: {indexer.get_index_size()} vectors")
    logger.info(f"Total pages indexed: {indexer.get_total_pages()}")
    logger.info("=" * 60)
    logger.info("Starting agent...")

@app.on_event("shutdown")
async def shutdown_event():
    """Log server shutdown"""
    logger.info("Server shutting down...")
    logger.info(f"Final index size: {indexer.get_index_size()} vectors")

if __name__ == "__main__":
    logger.info("Starting server with uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)

