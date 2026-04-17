"""
Documents API routes module
Handles all document-related endpoints (upload, list, delete, stats)
"""

from fastapi import APIRouter, Request, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
import os
import logging
from services.document_service import DocumentService
from api_routes.vector_store_ref import set_vector_store, get_vector_store
from config import CHUNK_SIZE, CHUNK_OVERLAP

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

# Global document service instance
document_service: DocumentService = None

logger = logging.getLogger(__name__)

def set_document_service(service: DocumentService):
    """Set the document service reference"""
    global document_service
    document_service = service

@router.post("/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...), session_id: str = None):
    """Upload a PDF document"""
    if document_service is None:
        return {"error": "Document service not initialized"}
    
    # Read file content
    contents = await file.read()
    
    # Use document service for upload
    result = document_service.upload_document(contents, file.filename, session_id=session_id)
    
    # If successful, trigger re-initialization or fast indexing
    if "message" in result:
        from api_routes.vector_store_ref import get_vector_store
        vector_store = get_vector_store()
        if session_id and vector_store:
            # Fast index for session specific
            background_tasks.add_task(_index_subupload, file.filename, contents, session_id, vector_store)
        else:
            background_tasks.add_task(_reinitialize_system)
    
    return result

from core.progress import global_progress, set_progress

@router.get("/progress")
async def get_progress():
    """Get the current progress of background tasks"""
    return global_progress

async def _index_subupload(filename: str, contents: bytes, session_id: str, vector_store):
    from ingestion.pdf_parser import extract_pdf_pages_from_bytes
    from embeddings.embedder import embed_passages
    import asyncio
    loop = asyncio.get_event_loop()
    
    def process():
        set_progress("indexing", f"Extracting {filename}...", 10)
        pages = extract_pdf_pages_from_bytes(contents, filename, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        for page in pages:
            page['session_id'] = session_id
        
        if not pages: 
            set_progress("idle", "System ready.", 100)
            return
        
        texts = [page["text"] for page in pages]
        
        def progress_cb(current, total):
            pct = 20 + (70 * current / total)
            set_progress("embedding", f"Embedding chunk {current} of {total}...", round(pct, 1))
            
        embeddings = embed_passages(texts, progress_callback=progress_cb)
        
        set_progress("indexing", "Saving index...", 95)
        vector_store.add(embeddings, pages)
        set_progress("idle", "System ready.", 100)
    
    await loop.run_in_executor(None, process)

@router.get("")
async def list_documents(session_id: str = None):
    """List all uploaded documents"""
    if document_service is None:
        return []
    
    return document_service.list_documents(session_id=session_id)

@router.delete("/{filename}")
async def delete_document(filename: str, background_tasks: BackgroundTasks):
    """Delete a document"""
    if document_service is None:
        return {"error": "Document service not initialized"}
    
    # Use document service for deletion
    result = document_service.delete_document(filename)
    
    # If successful, remove from vector store and save
    if "message" in result:
        background_tasks.add_task(_fast_delete_document, filename)
    
    return result

async def _fast_delete_document(filename: str):
    from api_routes.vector_store_ref import get_vector_store
    from config import INDEX_PATH, METADATA_PATH
    import asyncio
    loop = asyncio.get_event_loop()
    
    def process():
        set_progress("indexing", f"Removing {filename} from index...", 50)
        vector_store = get_vector_store()
        if vector_store:
            if vector_store.remove_document(filename):
                vector_store.save(INDEX_PATH, METADATA_PATH)
        set_progress("idle", "System ready.", 100)
        
    await loop.run_in_executor(None, process)

@router.get("/portfolio/stats")
async def get_portfolio_stats():
    """Get portfolio statistics"""
    if document_service is None:
        return {
            "document_count": 0,
            "total_size_mb": 0,
            "unique_entities": [],
            "last_updated": ""
        }
    
    return document_service.get_portfolio_stats()

async def _reinitialize_system():
    """Background task to reinitialize the system"""
    # Import here to avoid circular imports
    from core.initialization import initialize_system
    from services.chat_service import ChatService
    import asyncio
    import api_routes.chat_routes as chat_routes_module
    from api_routes.vector_store_ref import set_vector_store
    
    loop = asyncio.get_event_loop()
    vector_store, num_files, num_chunks = await loop.run_in_executor(None, initialize_system)
    
    if vector_store:
        set_vector_store(vector_store)
        chat_routes_module.set_services(vector_store, ChatService(vector_store))
        
    logger.info(f"System re-initialized! Loaded {num_files} files with {num_chunks} chunks.")
