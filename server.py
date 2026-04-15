from fastapi import FastAPI, Request, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio
import os
import logging

from api_routes.chat_routes import router as chat_router
from api_routes.docs_routes import router as docs_router
from api_routes.settings_routes import router as settings_router
import api_routes.chat_routes as chat_routes_module
import api_routes.docs_routes as docs_routes_module

# Import services for dependency injection
from services.chat_service import ChatService
from services.document_service import DocumentService
from vector_store.faiss_index import VectorStore
from logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)
from config import (
    PDF_DIR, INDEX_PATH, METADATA_PATH, 
    INITIAL_K as CONFIG_INITIAL_K, 
    FINAL_TOP_K as CONFIG_FINAL_TOP_K,
    DEFAULT_THRESHOLD, DEFAULT_TEMPERATURE,
    EMBEDDING_DIM, LLAMA_SERVER_URL,
    MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS,
    DEBUG, HOST, PORT
)
from core.initialization import initialize_system

app = FastAPI(title="FinChat API", version="2.6.3")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers with versioning
app.include_router(chat_router)
app.include_router(docs_router)
app.include_router(settings_router)

# Set vector store reference for docs routes
from api_routes.vector_store_ref import set_vector_store
set_vector_store(None)  # Will be updated on startup

@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.get("/")
async def read_index():
    """Serve the main frontend application"""
    return FileResponse('app/static/index.html')

# Ensure static directory exists
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Mount the PDF directory so they can be viewed in the browser
os.makedirs("data/pdfs", exist_ok=True)
app.mount("/pdfs", StaticFiles(directory="data/pdfs"), name="pdfs")

vector_store = None
chat_service = None
document_service = None

@app.on_event("startup")
async def startup_event():
    global vector_store, chat_service, document_service
    logger.info("Initializing system for API...")
    loop = asyncio.get_event_loop()
    # Execute the heavy initialization in a threadpool to not block asyncio
    vector_store, num_files, num_chunks = await loop.run_in_executor(None, initialize_system)
    logger.info(f"System initialized! Loaded {num_files} files with {num_chunks} chunks.")
    # Initialize services
    chat_service = ChatService(vector_store)
    document_service = DocumentService()
    
    # Inject dependencies properly
    set_vector_store(vector_store)  # Fixes the NameError
    chat_routes_module.set_services(vector_store, chat_service)
    docs_routes_module.set_document_service(document_service)

class ChatRequest(BaseModel):
    query: str

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
