"""
Configuration module for FinChat application
Centralizes all configuration settings
"""

import os
from pathlib import Path
from typing import Set

# Base directories
BASE_DIR: Path = Path(__file__).parent
DATA_DIR: Path = BASE_DIR / "data"
PDF_DIR: Path = DATA_DIR / "pdfs"
INDEX_PATH: Path = BASE_DIR / "faiss.index"
METADATA_PATH: Path = BASE_DIR / "metadata.pkl"

# Application settings
APP_TITLE: str = "FinChat API"
APP_VERSION: str = "2.6.3"

# RAG Configuration
INITIAL_K: int = 50          # Initial retrieval count
FINAL_TOP_K: int = 5         # Final reranked results count
DEFAULT_THRESHOLD: float = 0.05 # Relevance score threshold (permissive with sigmoid)
DEFAULT_TEMPERATURE: float = 0.2 # Lower temperature for better financial precision

# PDF Processing
CHUNK_SIZE: int = 1000
CHUNK_OVERLAP: int = 200

# Model Configuration
EMBEDDING_MODEL: str = "BAAI/bge-base-en-v1.5"
RERANKER_MODEL: str = "BAAI/bge-reranker-base"
LLAMA_SERVER_URL: str = "http://127.0.0.1:8080/v1/chat/completions"

# Embedding dimensions (BGE base)
EMBEDDING_DIM: int = 768

# File processing limits
MAX_FILE_SIZE_MB: int = 50
ALLOWED_EXTENSIONS: Set[str] = {".pdf"}

# Logging
LOG_LEVEL: str = "INFO"
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Development settings
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", 8000))