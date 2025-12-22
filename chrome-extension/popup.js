// Popup script for managing blocklist

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
      statusDiv.textContent = '✓ Backend connected';
      statusDiv.style.color = 'green';
    } else {
      throw new Error('Backend not responding');
    }
  } catch (error) {
    statusDiv.textContent = '✗ Backend not connected. Make sure the Python server is running.';
    statusDiv.style.color = 'red';
  }
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await loadBlocklist();
  await checkBackend();
  
  document.getElementById('saveBlocklist').addEventListener('click', saveBlocklist);
  
  // Check backend every 5 seconds
  setInterval(checkBackend, 5000);
});

