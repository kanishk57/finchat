import os
import re
import logging
import datetime
from typing import List, Dict, Union
from pypdf import PdfReader
from pypdf.errors import PdfReadError
import io

logger = logging.getLogger(__name__)

def extract_pdf_pages_from_bytes(contents: bytes, doc_name: str, chunk_size=1000, overlap=200):
    all_documents = []
    
    try:
        reader = PdfReader(io.BytesIO(contents))
        doc_date = datetime.datetime.now().strftime('%b %d, %Y').upper()
        
        for page_index, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text or not text.strip(): continue
            
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n\n', text)
            chunks = chunk_text(text, chunk_size, overlap)
            
            if not chunks: continue
            
            for chunk_index, chunk in enumerate(chunks):
                contextual_text = f"[Document: {doc_name} | Page: {page_index+1}] {chunk}"
                all_documents.append({
                    "doc_name": doc_name,
                    "doc_date": doc_date,
                    "page_number": page_index + 1,
                    "chunk_id": f"{doc_name}_{page_index+1}_{chunk_index}",
                    "text": contextual_text
                })
    except Exception as e:
        logger.error(f"Error parsing PDF bytes for {doc_name}: {str(e)}")
        
    return all_documents

def chunk_text(text, chunk_size=1000, overlap=200):
    """
    Split text into chunks by characters, trying to respect sentence boundaries.
    
    Args:
        text: Input text to chunk
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or not isinstance(text, str):
        logger.warning("Invalid text input for chunking")
        return []
    
    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end >= len(text):
            chunk = text[start:].strip()
            if len(chunk) > 50: # Skip very small fragments
                chunks.append(chunk)
            break
            
        # Try to find a good breaking point near the end of the chunk
        # Look for period, exclamation, question mark, or newline within the last 150 chars
        search_range = text[max(start, end - 150):end + 50]
        break_points = list(re.finditer(r'[\.\!\?\n]', search_range))
        
        if break_points:
            # Pick the last break point before the limit if possible, or the first after
            best_break = -1
            for m in reversed(break_points):
                if m.start() + max(start, end - 150) <= end:
                    best_break = m.start() + max(start, end - 150) + 1
                    break
            
            if best_break != -1:
                end = best_break
        
        chunk = text[start:end].strip()
        if len(chunk) > 50: # Skip very small fragments
            chunks.append(chunk)
            
        start = end - overlap
        
        # Prevent infinite loop
        if start >= end:
            break
    
    logger.debug(f"Created {len(chunks)} chunks from text of length {len(text)}")
    return chunks


def extract_pdf_pages(paths, chunk_size=1000, overlap=200):
    """
    Extracts text from a list of PDF paths and returns chunked documents.
    
    Args:
        paths: List of PDF file paths or single path
        chunk_size: Target size for each text chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of document dictionaries with metadata and text
    """
    if isinstance(paths, str):
        paths = [paths]
    
    all_documents = []
    
    for path in paths:
        # Validate file existence
        if not os.path.exists(path):
            logger.warning(f"PDF file not found: {path}")
            continue
            
        # Validate file extension
        if not path.lower().endswith('.pdf'):
            logger.warning(f"File is not a PDF: {path}")
            continue
        
        try:
            reader = PdfReader(path)
        except PdfReadError as e:
            logger.error(f"Failed to read PDF {path}: {str(e)}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error reading PDF {path}: {str(e)}")
            continue
            
        doc_name = os.path.basename(path)
        
        try:
            mod_time = os.path.getmtime(path)
            doc_date = datetime.datetime.fromtimestamp(mod_time).strftime('%b %d, %Y').upper()
        except OSError as e:
            logger.warning(f"Could not get modification time for {path}: {str(e)}")
            doc_date = "UNKNOWN"
        
        # Process each page
        for page_index, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if not text or not text.strip():
                    logger.debug(f"No text extracted from page {page_index+1} in {doc_name}")
                    continue
                
                # Clean up whitespace but keep some structure
                text = re.sub(r'[ \t]+', ' ', text)
                text = re.sub(r'\n\s*\n', '\n\n', text)
                
                # Chunk the text
                chunks = chunk_text(text, chunk_size, overlap)
                
                if not chunks:
                    logger.debug(f"No chunks created from page {page_index+1} in {doc_name}")
                    continue
                
                # Process each chunk
                for chunk_index, chunk in enumerate(chunks):
                    # Contextual Enrichment: Prepend metadata to the text itself
                    # This helps the Bi-Encoder and Reranker distinguish between files/pages
                    contextual_text = f"[Document: {doc_name} | Page: {page_index+1}] {chunk}"
                    
                    all_documents.append({
                        "doc_name": doc_name,
                        "doc_date": doc_date,
                        "page_number": page_index + 1,
                        "chunk_id": f"{doc_name}_{page_index+1}_{chunk_index}",
                        "text": contextual_text
                    })
                    
            except Exception as e:
                logger.error(f"Error processing page {page_index+1} in {doc_name}: {str(e)}")
                continue
    
    logger.info(f"Extracted {len(all_documents)} document chunks from {len(paths)} PDF files")
    return all_documents