#!/bin/bash

# Setup script for Browse History Indexer

echo "Setting up Browse History Indexer..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Install Python dependencies
echo "Installing Python dependencies..."

# Check if uv is available
if command -v uv &> /dev/null; then
    echo "Using uv for faster installation..."
    uv pip install -r requirements.txt
else
    echo "Using pip (consider installing uv for faster installs: curl -LsSf https://astral.sh/uv/install.sh | sh)"
    pip install -r requirements.txt
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p faiss_index
mkdir -p chrome-extension

# Check for icon files
if [ ! -f "chrome-extension/icon16.png" ] || [ ! -f "chrome-extension/icon48.png" ] || [ ! -f "chrome-extension/icon128.png" ]; then
    echo ""
    echo "⚠️  WARNING: Icon files are missing!"
    echo "Please create the following icon files in chrome-extension/:"
    echo "  - icon16.png (16x16 pixels)"
    echo "  - icon48.png (48x48 pixels)"
    echo "  - icon128.png (128x128 pixels)"
    echo ""
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Create icon files for the Chrome extension (see chrome-extension/README.md)"
echo "2. Start the backend server:"
echo "   - Using uv: uv run python main.py"
echo "   - Using python: python main.py"
echo "3. Load the Chrome extension (see chrome-extension/README.md)"
echo "4. Start browsing - pages will be automatically indexed!"

