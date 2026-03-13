# FinChat: Premium Financial Intelligence

A high-performance Retrieval-Augmented Generation (RAG) system tailored for financial analysis. This project uses a "Retrieve-then-Rerank" architecture with a modern, Gemini-style web interface.

## 🚀 Key Features

### Intelligence Engine
- **Hybrid Search**: Combines Dense Retrieval (BAAI/bge-base-en-v1.5) with Sparse Retrieval (BM25).
- **Cross-Encoder Reranking**: Uses `BAAI/bge-reranker-base` for high-precision result filtering.
- **Semantic Chunking**: Intelligent PDF parsing that respects context and boundaries.
- **Source Attribution**: Automatically cites sources (e.g., [Source 1]) with direct PDF links.

### Modern Web Interface
- **Gemini-Style UI**: Full-page, edge-to-edge layout with a responsive sidebar and floating input dock.
- **Multi-Session Logic**: Create, save, and switch between multiple independent chat sessions.
- **Local Persistence**: Chat history is automatically saved to `localStorage`, surviving page reloads.
- **Premium Aesthetics**: High-end glassmorphism, smooth micro-animations, and intentional typography.

## 🛠️ Architecture

1.  **Ingestion**: `pypdf` extracts text -> Semantic splitter creates overlap-aware chunks.
2.  **Indexing**: Chunks embedded via BGE-Base and stored in FAISS + BM25.
3.  **Backend**: FastAPI server handles the RAG pipeline and streams responses via Server-Sent Events (SSE).
4.  **Frontend**: Vanilla JS/CSS implementation with a responsive sidebar and persistence engine.

## 📋 Prerequisites

- Python 3.10+
- `llama.cpp` server (managed automatically by `run.sh`)

## ⚙️ Setup & Running

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Prepare Data**:
   Place your financial PDFs in `data/pdfs/`.

3. **Run the Application**:
   Use the optimized execution script:
   ```bash
   ./run.sh
   ```
   This script will check your environment, start the `llama-server` in the background, and launch the web interface at `http://localhost:8000`.

## 📄 Project Structure

- `main.py`: Core RAG logic and CLI entry point.
- `server.py`: FastAPI server for the web interface.
- `app/static/`: Frontend assets (Gemini-style CSS, JS, HTML).
- `embeddings/`: Bi-Encoder and Cross-Encoder model definitions.
- `vector_store/`: Hybrid FAISS + BM25 implementation.
- `llm/`: Prompt construction and LLM API client.
- `run.sh`: Automated execution script for the entire stack.

## 🔍 Optimization Notes

- **Retrieve-then-Rerank**: We retrieve 15 documents initially and rerank to the top 5 to eliminate hallucinations.
- **Streamed Reasoning**: Responses are streamed to the UI as they are generated for a responsive feel.
- **Persistence**: Sidebars auto-populate session titles based on conversation context.
