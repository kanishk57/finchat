"""
Document Service Layer
Contains business logic for document operations, separated from API concerns
"""

import os
import glob
import re
import datetime
import logging
from typing import List, Dict, Any
from pathlib import Path

from config import (
    PDF_DIR, MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS
)

logger = logging.getLogger(__name__)


class DocumentService:
    """Service class handling document-related business logic"""
    
    def __init__(self, pdf_directory: str = PDF_DIR):
        self.pdf_directory = pdf_directory
        # Ensure directory exists
        os.makedirs(self.pdf_directory, exist_ok=True)
    
    def upload_document(self, file_content: bytes, filename: str, session_id: str = None) -> Dict[str, Any]:
        """
        Handle document upload
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            session_id: Optional session ID for subuploads
            
        Returns:
            Dictionary with upload result
        """
        logger.info(f"Processing upload for file: {filename} (Session: {session_id})")
        
        # Validate file type
        if not filename.lower().endswith(".pdf"):
            return {"error": "Only PDF files are supported."}
        
        # Validate file size
        if len(file_content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            return {"error": f"File size exceeds {MAX_FILE_SIZE_MB}MB limit"}
        
        # Save file
        target_dir = self.pdf_directory
        if session_id:
            target_dir = os.path.join(self.pdf_directory, session_id)
            os.makedirs(target_dir, exist_ok=True)
            
        file_path = os.path.join(target_dir, filename)
        try:
            with open(file_path, "wb") as f:
                f.write(file_content)
            logger.info(f"Successfully saved file: {filename}")
            return {
                "message": f"Successfully uploaded {filename}.",
                "filename": filename,
                "size": len(file_content)
            }
        except Exception as e:
            logger.error(f"Failed to save file {filename}: {str(e)}")
            return {"error": f"Failed to save file: {str(e)}"}
    
    def list_documents(self, session_id: str = None) -> List[Dict[str, Any]]:
        """
        List all uploaded documents (global and optionally session-specific)
        
        Returns:
            List of document information dictionaries
        """
        logger.info(f"Listing documents (Session: {session_id})")
        
        # Get global files
        files = glob.glob(os.path.join(self.pdf_directory, "*.pdf"))
        
        # Get session-specific files
        if session_id:
            session_dir = os.path.join(self.pdf_directory, session_id)
            if os.path.exists(session_dir):
                session_files = glob.glob(os.path.join(session_dir, "*.pdf"))
                files.extend(session_files)
                
        documents = []
        seen_filenames = set()
        
        for file_path in files:
            try:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                
                # If we have a duplicate filename, prefer the one in the session directory
                # (which would be added later in the list if we append session_files)
                is_session_file = session_id and session_id in file_path
                
                if file_name not in seen_filenames:
                    documents.append({
                        "name": file_name,
                        "size": file_size,
                        "path": file_path,
                        "source": "session" if is_session_file else "global"
                    })
                    seen_filenames.add(file_name)
                elif is_session_file:
                    # Replace global with session version if names collide
                    for doc in documents:
                        if doc['name'] == file_name:
                            doc['path'] = file_path
                            doc['size'] = file_size
                            doc['source'] = "session"
                            break
                            
            except Exception as e:
                logger.warning(f"Could not process file {file_path}: {str(e)}")
                continue
        
        logger.info(f"Found {len(documents)} documents")
        return documents
    
    def delete_document(self, filename: str) -> Dict[str, Any]:
        """
        Delete a document
        
        Args:
            filename: Name of file to delete
            
        Returns:
            Dictionary with deletion result
        """
        logger.info(f"Attempting to delete file: {filename}")
        
        # Search in global first, then in any session directory
        file_path = os.path.join(self.pdf_directory, filename)
        if not os.path.exists(file_path):
            # Try finding it in session subdirectories
            session_paths = glob.glob(os.path.join(self.pdf_directory, "*", filename))
            if session_paths:
                file_path = session_paths[0]
            else:
                logger.warning(f"File not found for deletion: {filename}")
                return {"error": "File not found."}
        
        try:
            os.remove(file_path)
            logger.info(f"Successfully deleted file: {filename}")
            return {"message": f"Deleted {filename}."}
        except Exception as e:
            logger.error(f"Failed to delete file {filename}: {str(e)}")
            return {"error": f"Failed to delete file: {str(e)}"}
    
    def get_portfolio_stats(self) -> Dict[str, Any]:
        """
        Get portfolio statistics (including all global and session files)
        
        Returns:
            Dictionary with portfolio statistics
        """
        logger.info("Calculating portfolio statistics")
        
        # Get all PDF files recursively in PDF_DIR
        files = glob.glob(os.path.join(self.pdf_directory, "**", "*.pdf"), recursive=True)
        total_size = sum(os.path.getsize(f) for f in files)
        
        # Simple heuristic for "companies": unique words in filenames
        companies = set()
        for f in files:
            name = os.path.basename(f).replace(".pdf", "")
            # Extract potential company name (e.g., "NVDA" from "SEC-10Q-NVDA-2023")
            parts = re.split(r'[-_ ]', name)
            for p in parts:
                if p.isupper() and len(p) >= 2:
                    companies.add(p)
        
        stats = {
            "document_count": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "unique_entities": list(companies),
            "last_updated": datetime.datetime.now().strftime("%b %d, %Y")
        }
        
        logger.info(f"Portfolio stats calculated: {stats}")
        return stats