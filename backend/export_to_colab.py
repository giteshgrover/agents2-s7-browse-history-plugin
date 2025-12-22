"""
Script to export FAISS index for use in Google Colab
"""

import os
import shutil
import zipfile
from pathlib import Path

def export_to_colab(index_path: str = "faiss_index", output_path: str = "faiss_index_colab.zip"):
    """
    Export FAISS index and metadata to a zip file for Google Colab
    
    Args:
        index_path: Path to the FAISS index directory
        output_path: Path to save the zip file
    """
    if not os.path.exists(index_path):
        print(f"Error: Index path '{index_path}' does not exist")
        return None
    
    # Create zip file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(index_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(index_path))
                zipf.write(file_path, arcname)
    
    print(f"Successfully exported index to {output_path}")
    print(f"File size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
    return output_path

if __name__ == "__main__":
    import sys
    index_path = sys.argv[1] if len(sys.argv) > 1 else "faiss_index"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "faiss_index_colab.zip"
    export_to_colab(index_path, output_path)

