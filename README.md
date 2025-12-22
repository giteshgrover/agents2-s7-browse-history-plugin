# Browse History & Content Indexer

A Chrome extension that records visited page links (excluding blocklisted ones), extracts text content, chunks it, and indexes it using FAISS for semantic search.

## Features

- 🔍 **Automatic Page Tracking**: Records every page you visit (except blocklisted ones)
- 📝 **Content Extraction**: Extracts text content, title, and metadata from pages
- ✂️ **Smart Chunking**: Splits content into overlapping chunks for better indexing
- 🗂️ **FAISS Indexing**: Uses FAISS for efficient vector similarity search
- 🚫 **Blocklist Support**: Exclude specific URLs or patterns from indexing
- ☁️ **Colab Export**: Export index for use in Google Colab

## Architecture

The project consists of two main components:

1. **Chrome Extension** (`chrome-extension/`): Tracks page visits and extracts content
2. **Python Backend** (`backend/`): Handles text chunking and FAISS indexing

## Installation

### 1. Install Python Dependencies

**Using uv (recommended - faster):**

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv pip install -r requirements.txt
```

Or using uv with pyproject.toml:

```bash
uv pip install -e .
```

**Using pip (alternative):**

```bash
pip install -r requirements.txt
```

Or using pip with pyproject.toml:

```bash
pip install -e .
```

### 2. Install Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome-extension` folder
5. Create icon files (see `chrome-extension/README.md`)

### 3. Start the Backend Server

**Using uv:**

```bash
uv run python main.py
```

**Using standard Python:**

```bash
python main.py
```

Or:

```bash
cd backend
python server.py
```

The server will start at `http://localhost:8000`

## Usage

### Running the Extension

1. Make sure the backend server is running
2. Browse the web normally - the extension will automatically track pages
3. Click the extension icon to:
   - View backend connection status
   - Manage the blocklist

### Blocklist Management

The blocklist can be managed through the extension popup or by editing `chrome-extension/blocklist.json`.

**Blocklist Format:**
- One pattern per line
- Substring matching: `example.com` matches any URL containing "example.com"
- Regex patterns: `/^https:\/\/.*\.google\.com/` (must start and end with `/`)

**Default blocklist includes:**
- `chrome://`
- `chrome-extension://`
- `about:`
- `file://`

### API Endpoints

The backend provides the following endpoints:

- `GET /health` - Health check and index statistics
- `POST /index` - Index a page (called automatically by extension)
- `GET /search?query=<text>&top_k=<number>` - Search the index
- `GET /stats` - Get indexing statistics

### Exporting to Google Colab

1. Run the export script:

```bash
python backend/export_to_colab.py
```

This creates `faiss_index_colab.zip` containing the FAISS index and metadata.

2. Upload the zip file to Google Colab
3. Use the provided `colab_example.ipynb` notebook to load and search the index

## Project Structure

```
.
├── chrome-extension/          # Chrome extension files
│   ├── manifest.json         # Extension manifest
│   ├── background.js         # Service worker for tracking
│   ├── content.js            # Content script for extraction
│   ├── popup.html            # Extension popup UI
│   ├── popup.js              # Popup logic
│   ├── blocklist.json        # Default blocklist
│   └── README.md             # Extension setup guide
├── backend/                  # Python backend
│   ├── server.py             # FastAPI server
│   ├── faiss_indexer.py      # FAISS indexing logic
│   ├── chunking.py           # Text chunking utilities
│   └── export_to_colab.py    # Export script
├── colab_example.ipynb       # Google Colab example notebook
├── main.py                   # Main entry point
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## Configuration

### Chunking Parameters

Edit `backend/faiss_indexer.py` to adjust:
- `chunk_size`: Characters per chunk (default: 500)
- `chunk_overlap`: Overlap between chunks (default: 50)

### Embedding Model

The default model is `all-MiniLM-L6-v2`. To change it, modify `backend/faiss_indexer.py`:

```python
self.model = SentenceTransformer('your-model-name')
```

### Backend URL

To change the backend URL, edit `chrome-extension/background.js`:

```javascript
const BACKEND_URL = 'http://your-backend-url:8000';
```

## Development

### Testing the Backend

```bash
# Start server (using uv or python)
uv run python main.py
# or
python main.py

# Test health endpoint
curl http://localhost:8000/health

# Test search
curl "http://localhost:8000/search?query=your+query&top_k=5"
```

### Viewing API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

### Extension not tracking pages

1. Check that the backend server is running
2. Check browser console for errors (F12)
3. Verify backend URL in `background.js` matches your server
4. Check extension popup for connection status

### Backend connection errors

1. Ensure the server is running on port 8000
2. Check firewall settings
3. Verify CORS settings in `backend/server.py`

### FAISS index not updating

1. Check backend logs for errors
2. Verify write permissions in the index directory
3. Check disk space

## Dependencies

- **fastapi**: Web framework for the backend API
- **uvicorn**: ASGI server
- **sentence-transformers**: Text embeddings
- **faiss-cpu**: Vector similarity search
- **numpy**: Numerical operations
- **pydantic**: Data validation

## License

This project is provided as-is for educational and personal use.

## Notes

- The extension requires the backend server to be running
- First-time indexing may take longer as the embedding model downloads
- Large pages may take time to process
- The FAISS index grows over time - consider periodic cleanup or archiving

