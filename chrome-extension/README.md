# Chrome Extension Setup

## Installation

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome-extension` folder
5. The extension should now be installed

## Icon Files

You need to create icon files for the extension:
- `icon16.png` (16x16 pixels)
- `icon48.png` (48x48 pixels)
- `icon128.png` (128x128 pixels)

You can use any image editor or online tool to create these icons. Place them in this directory.

## Usage

1. Make sure the Python backend server is running (see main README)
2. The extension will automatically start tracking page visits
3. Click the extension icon to manage the blocklist
4. Pages matching blocklist patterns will not be indexed

## Blocklist Format

- One URL pattern per line
- Supports substring matching (e.g., `example.com`)
- Supports regex patterns (e.g., `/^https:\/\/.*\.google\.com/`)
- Regex patterns must start and end with `/`

