// Content script to extract text content from pages
// This script runs in the page context

(function() {
  'use strict';
  
  // Mark that content script has run
  if (window.browseHistoryIndexerLoaded) {
    return;
  }
  window.browseHistoryIndexerLoaded = true;
  
  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'extractContent') {
      const content = extractTextContent();
      sendResponse(content);
    }
    return true; // Keep channel open for async response
  });
  
  function extractTextContent() {
    try {
      // Remove script and style elements
      const scripts = document.querySelectorAll('script, style, noscript, iframe');
      scripts.forEach(el => el.remove());
      
      // Get main content areas
      const mainContent = document.querySelector('main, article, [role="main"]') || 
                          document.querySelector('.content, #content') ||
                          document.body;
      
      // Extract text
      const text = mainContent.innerText || mainContent.textContent || '';
      
      // Get page metadata
      const title = document.title || '';
      const description = document.querySelector('meta[name="description"]')?.content || '';
      const keywords = document.querySelector('meta[name="keywords"]')?.content || '';
      
      return {
        text: text.trim(),
        title: title.trim(),
        description: description.trim(),
        keywords: keywords.trim(),
        url: window.location.href,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      console.error('Error extracting content:', error);
      return null;
    }
  }
})();

