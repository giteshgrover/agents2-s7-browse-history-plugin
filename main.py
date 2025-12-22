"""
Main entry point for the backend server
"""
import uvicorn
from backend.server import app

def main():
    """Start the FastAPI backend server"""
    print("Starting Browse History Indexer Backend Server...")
    print("Server will be available at http://localhost:8000")
    print("API docs available at http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
