"""
Initialization Module
Handles system initialization including model loading, document processing, and vector store creation
"""

import os
import sys
import time
import glob
from typing import Tuple
from rich.console import Console
from rich.status import Status

from ingestion.pdf_parser import extract_pdf_pages
from embeddings.embedder import embed_passages
from models.model_manager import load_models
from vector_store.faiss_index import VectorStore
from config import (
    PDF_DIR as DATA_PDF_DIR,
    INITIAL_K,
    FINAL_TOP_K,
    DEFAULT_THRESHOLD as THRESHOLD,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_DIM,
    INDEX_PATH,
    METADATA_PATH
)

console = Console()

# Override PDF_DIR to match expected format (trailing slash)
PDF_DIR = str(DATA_PDF_DIR) + "/"


def build_prompt(query, retrieved_results):
    """Build the prompt for the LLM with retrieved context"""
    from llm.context_builder import build_context
    
    context = build_context(retrieved_results)
    return f"{query}\n\nContext Chunks:\n{context}"


from core.progress import set_progress

def initialize_system() -> Tuple[VectorStore, int, int]:
    """
    Initialize the FinChat system:
    1. Load AI models
    2. Discover PDF documents
    3. Create/load vector store with embeddings
    
    Returns:
        Tuple of (vector_store, num_files, num_chunks)
    """
    # Use a single status context for the whole startup to prevent flickering
    with console.status("[bold green]Starting FinChat Engine...", spinner="aesthetic") as status:
        
        # 1. Weights Loading
        set_progress("indexing", "Loading AI models...", 5)
        status.update("[bold green]Loading AI models & weights (BGE-Base)...")
        load_models()
        
        # 2. Document Discovery
        set_progress("indexing", "Scanning data directory...", 10)
        status.update("[bold blue]Scanning data directory...")
        pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
        if not pdf_files:
            console.print(f"[bold yellow]Warning:[/bold yellow] No PDFs found in {PDF_DIR}, starting with empty store.")
            set_progress("idle", "System ready.", 100)
            return VectorStore(EMBEDDING_DIM), 0, 0

        # 3. Indexing Logic
        vector_store = None
        FORCE_REBUILD = False
        pages = []
        num_chunks = 0

        if os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH):
            vector_store = VectorStore(EMBEDDING_DIM)
            if vector_store.load(INDEX_PATH, METADATA_PATH):
                indexed_docs = {m["doc_name"] for m in vector_store.metadata}
                current_docs = {os.path.basename(f) for f in pdf_files}
                if indexed_docs != current_docs:
                    status.update("[bold yellow]Change detected. Rebuilding index...")
                    FORCE_REBUILD = True
                else:
                    status.update("[bold green]Found existing index. Skipping rebuild...")
                    num_chunks = len(vector_store.metadata)
            else:
                FORCE_REBUILD = True
        else:
            FORCE_REBUILD = True

        if FORCE_REBUILD:
            set_progress("indexing", f"Analyzing {len(pdf_files)} documents...", 20)
            status.update(f"[bold blue]Analyzing {len(pdf_files)} documents...")
            pages = extract_pdf_pages(pdf_files, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
            num_chunks = len(pages)
            
            set_progress("embedding", "Generating embeddings...", 30)
            status.update("[bold cyan]Generating embeddings (this may take a minute)...")
            texts = [page["text"] for page in pages]
            
            def progress_cb(current, total):
                pct = 30 + (60 * current / total)
                set_progress("embedding", f"Embedding chunk {current} of {total}...", round(pct, 1))

            # Use batching logic configured in embedder.py
            embeddings = embed_passages(texts, progress_callback=progress_cb)
            
            set_progress("indexing", "Saving index...", 95)
            vector_store = VectorStore(len(embeddings[0]))
            vector_store.add(embeddings, pages)
            vector_store.save(INDEX_PATH, METADATA_PATH)
            
    set_progress("idle", "System ready.", 100)
    return vector_store, len(pdf_files), num_chunks
