import os
import re
from pypdf import PdfReader

def chunk_text(text, chunk_size=1000, overlap=200):
    """
    Split text into chunks by characters, trying to respect sentence boundaries.
    """
    # Simple recursive splitting logic
    # First, split by double newlines (paragraphs)
    # Then by single newlines, then by periods.
    
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end >= len(text):
            chunks.append(text[start:].strip())
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

    return chunks


def extract_pdf_pages(paths, chunk_size=1000, overlap=200):
    """
    Extracts text from a list of PDF paths and returns chunked documents.
    """
    if isinstance(paths, str):
        paths = [paths]
        
    all_documents = []
    
    for path in paths:
        if not os.path.exists(path):
            continue
            
        reader = PdfReader(path)
        doc_name = os.path.basename(path)

        for page_index, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text or not text.strip():
                continue

            # Clean up whitespace but keep some structure
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n\n', text)

            chunks = chunk_text(text, chunk_size, overlap)

            for chunk_index, chunk in enumerate(chunks):
                # Contextual Enrichment: Prepend metadata to the text itself
                # This helps the Bi-Encoder and Reranker distinguish between files/pages
                contextual_text = f"[Document: {doc_name} | Page: {page_index+1}] {chunk}"
                
                all_documents.append({
                    "doc_name": doc_name,
                    "page_number": page_index + 1,
                    "chunk_id": f"{doc_name}_{page_index+1}_{chunk_index}",
                    "text": contextual_text
                })

    return all_documents