// Background service worker to track page visits

const BACKEND_URL = 'http://localhost:8000'; // Python backend URL
const BLOCKLIST_KEY = 'blocklist';

// Load blocklist from storage
async function loadBlocklist() {
  const result = await chrome.storage.local.get([BLOCKLIST_KEY]);
  return result[BLOCKLIST_KEY] || [];
}

// Check if URL is blocklisted
async function isBlocklisted(url) {
  const blocklist = await loadBlocklist();
  return blocklist.some(pattern => {
    try {
      // Support both exact matches and regex patterns
      if (pattern.startsWith('/') && pattern.endsWith('/')) {
        const regex = new RegExp(pattern.slice(1, -1));
        return regex.test(url);
      }
      return url.includes(pattern);
    } catch (e) {
      // If regex is invalid, treat as substring match
      return url.includes(pattern);
    }
  });
}

// Extract text content from page (will be done by content script)
async function extractPageContent(tabId) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tabId },
      function: extractTextContent
    });
    return results[0]?.result || null;
  } catch (error) {
    console.error('Error extracting content:', error);
    return null;
  }
}

// Function to extract text content (injected into page)
function extractTextContent() {
  // Remove script and style elements
  const scripts = document.querySelectorAll('script, style, noscript');
  scripts.forEach(el => el.remove());

  // Get main content areas
  const mainContent = document.querySelector('main, article, [role="main"]') || document.body;
  
  // Extract text
  const text = mainContent.innerText || mainContent.textContent || '';
  
  // Get page metadata
  const title = document.title || '';
  const description = document.querySelector('meta[name="description"]')?.content || '';
  
  return {
    text: text.trim(),
    title: title.trim(),
    description: description.trim(),
    url: window.location.href,
    timestamp: new Date().toISOString()
  };
}

// Send data to backend
async function sendToBackend(data) {
  try {
    const response = await fetch(`${BACKEND_URL}/index`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      throw new Error(`Backend error: ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('Successfully indexed page:', result);
    return result;
  } catch (error) {
    console.error('Error sending to backend:', error);
    // Store in local queue for retry
    const queue = await chrome.storage.local.get(['failedQueue']) || { failedQueue: [] };
    queue.failedQueue = queue.failedQueue || [];
    queue.failedQueue.push(data);
    await chrome.storage.local.set({ failedQueue: queue.failedQueue });
  }
}

// Process page visit
async function processPageVisit(tab) {
  if (!tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://')) {
    return;
  }

  const isBlocked = await isBlocklisted(tab.url);
  if (isBlocked) {
    console.log('Page is blocklisted:', tab.url);
    return;
  }

  // Wait a bit for page to load
  setTimeout(async () => {
    try {
      const content = await extractPageContent(tab.id);
      if (content && content.text) {
        await sendToBackend({
          url: tab.url,
          title: content.title,
          description: content.description,
          text: content.text,
          timestamp: content.timestamp
        });
      }
    } catch (error) {
      console.error('Error processing page:', error);
    }
  }, 2000); // Wait 2 seconds for page to fully load
}

// Listen for tab updates
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    await processPageVisit(tab);
  }
});

// Listen for tab activation (when user switches to a tab)
chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const tab = await chrome.tabs.get(activeInfo.tabId);
  if (tab.url && tab.status === 'complete') {
    await processPageVisit(tab);
  }
});

// Retry failed requests
async function retryFailedRequests() {
  const result = await chrome.storage.local.get(['failedQueue']);
  const queue = result.failedQueue || [];
  
  if (queue.length > 0) {
    console.log(`Retrying ${queue.length} failed requests`);
    const successful = [];
    
    for (const data of queue) {
      try {
        await sendToBackend(data);
        successful.push(data);
      } catch (error) {
        console.error('Retry failed:', error);
      }
    }
    
    // Remove successful items from queue
    const remaining = queue.filter(item => !successful.includes(item));
    await chrome.storage.local.set({ failedQueue: remaining });
  }
}

// Retry failed requests every 5 minutes
setInterval(retryFailedRequests, 5 * 60 * 1000);

// Initialize: load default blocklist if not exists
chrome.runtime.onInstalled.addListener(async () => {
  const result = await chrome.storage.local.get([BLOCKLIST_KEY]);
  if (!result[BLOCKLIST_KEY]) {
    // Default blocklist
    const defaultBlocklist = [
      'chrome://',
      'chrome-extension://',
      'about:',
      'file://'
    ];
    await chrome.storage.local.set({ [BLOCKLIST_KEY]: defaultBlocklist });
  }
});

