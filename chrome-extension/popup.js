// Popup script for managing blocklist and search

const BACKEND_URL = 'http://localhost:8000';
const BLOCKLIST_KEY = 'blocklist';

// Load and display blocklist
async function loadBlocklist() {
  const result = await chrome.storage.local.get([BLOCKLIST_KEY]);
  const blocklist = result[BLOCKLIST_KEY] || [];
  document.getElementById('blocklist').value = blocklist.join('\n');
}

// Save blocklist
async function saveBlocklist() {
  const textarea = document.getElementById('blocklist');
  const lines = textarea.value.split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0);
  
  await chrome.storage.local.set({ [BLOCKLIST_KEY]: lines });
  
  const statusDiv = document.getElementById('status');
  statusDiv.textContent = `Saved ${lines.length} blocklist entries`;
  statusDiv.className = 'status success';
  
  setTimeout(() => {
    statusDiv.textContent = '';
    statusDiv.className = '';
  }, 3000);
}

// Check backend connection
async function checkBackend() {
  const statusDiv = document.getElementById('backendStatus');
  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    if (response.ok) {
      const data = await response.json();
      statusDiv.textContent = `✓ Backend connected (${data.index_size || 0} vectors indexed)`;
      statusDiv.style.color = 'green';
      return true;
    } else {
      throw new Error('Backend not responding');
    }
  } catch (error) {
    statusDiv.textContent = '✗ Backend not connected. Make sure the Python server is running.';
    statusDiv.style.color = 'red';
    return false;
  }
}

// Perform search
async function performSearch() {
  const queryInput = document.getElementById('searchQuery');
  const topKInput = document.getElementById('topK');
  const searchBtn = document.getElementById('searchBtn');
  const resultsDiv = document.getElementById('searchResults');
  const statusDiv = document.getElementById('searchStatus');
  
  const query = queryInput.value.trim();
  const topK = parseInt(topKInput.value) || 5;
  
  if (!query) {
    statusDiv.textContent = 'Please enter a search query';
    statusDiv.className = 'status error';
    setTimeout(() => {
      statusDiv.textContent = '';
      statusDiv.className = '';
    }, 3000);
    return;
  }
  
  // Disable search button and show loading
  searchBtn.disabled = true;
  resultsDiv.innerHTML = '<div class="loading">Searching...</div>';
  statusDiv.textContent = '';
  
  try {
    const response = await fetch(`${BACKEND_URL}/search?query=${encodeURIComponent(query)}&top_k=${topK}`);
    
    if (!response.ok) {
      throw new Error(`Search failed: ${response.statusText}`);
    }
    
    const data = await response.json();
    const results = data.results || [];
    
    // Display results
    if (results.length === 0) {
      resultsDiv.innerHTML = '<div class="no-results">No results found</div>';
      statusDiv.textContent = 'No matching pages found';
      statusDiv.className = 'status info';
    } else {
      resultsDiv.innerHTML = '';
      results.forEach((result, index) => {
        const resultItem = createResultElement(result, index + 1);
        resultsDiv.appendChild(resultItem);
      });
      statusDiv.textContent = `Found ${results.length} result(s)`;
      statusDiv.className = 'status success';
    }
  } catch (error) {
    console.error('Search error:', error);
    resultsDiv.innerHTML = '';
    statusDiv.textContent = `Search failed: ${error.message}`;
    statusDiv.className = 'status error';
  } finally {
    searchBtn.disabled = false;
  }
}

// Create result element
function createResultElement(result, rank) {
  const div = document.createElement('div');
  div.className = 'result-item';
  
  const title = document.createElement('div');
  title.className = 'result-title';
  title.textContent = result.title || 'Untitled';
  div.appendChild(title);
  
  const url = document.createElement('div');
  url.className = 'result-url';
  url.textContent = result.url;
  div.appendChild(url);
  
  if (result.chunk_text) {
    const snippet = document.createElement('div');
    snippet.className = 'result-snippet';
    // Show first 150 characters of chunk
    const snippetText = result.chunk_text.length > 150 
      ? result.chunk_text.substring(0, 150) + '...'
      : result.chunk_text;
    snippet.textContent = snippetText;
    div.appendChild(snippet);
  }
  
  const meta = document.createElement('div');
  meta.className = 'result-meta';
  const metaText = [];
  if (result.distance !== undefined) {
    metaText.push(`Distance: ${result.distance.toFixed(4)}`);
  }
  if (result.timestamp) {
    const date = new Date(result.timestamp);
    metaText.push(`Visited: ${date.toLocaleDateString()}`);
  }
  if (result.chunk_index !== undefined && result.total_chunks !== undefined) {
    metaText.push(`Chunk ${result.chunk_index + 1}/${result.total_chunks}`);
  }
  meta.textContent = metaText.join(' • ');
  div.appendChild(meta);
  
  // Make clickable to open URL
  div.addEventListener('click', () => {
    chrome.tabs.create({ url: result.url });
  });
  
  return div;
}

// Handle Enter key in search input
function handleSearchKeyPress(event) {
  if (event.key === 'Enter') {
    performSearch();
  }
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await loadBlocklist();
  await checkBackend();
  
  // Set up event listeners
  document.getElementById('saveBlocklist').addEventListener('click', saveBlocklist);
  document.getElementById('searchBtn').addEventListener('click', performSearch);
  document.getElementById('searchQuery').addEventListener('keypress', handleSearchKeyPress);
  
  // Check backend every 5 seconds
  setInterval(checkBackend, 5000);
});

