# FinChat Implementation Report

## 1. Overview

**Project Name:** FinChat - Minimal Analyst Terminal  
**Type:** Retrieval-Augmented Generation (RAG) System for Financial Analysis  
**Purpose:** Institutional-grade document Q&A system that allows analysts to upload financial PDFs, query them via natural language, and receive cited answers from an LLM.

---

## 2. Tech Stack

### Core Backend
| Component | Technology |
|-----------|------------|
| Web Framework | FastAPI (async, uvicorn) |
| Vector Database | FAISS (Facebook AI Similarity Search) |
| Sparse Retrieval | BM25Okapi (rank-bm25) |
| Embedding Model | BAAI/bge-base-en-v1.5 (768-dim) |
| Reranker Model | BAAI/bge-reranker-base (Cross-Encoder) |
| LLM Inference | llama.cpp (served via REST API at localhost:8080) |
| PDF Processing | pypdf |
| Serialization | pickle, JSON |

### Frontend
| Component | Technology |
|-----------|------------|
| UI Framework | Vanilla JS + Tailwind CSS (localized) |
| Styling | Custom Tailwind with Helvetica Neue typography |
| Icons | Material Icons |
| Communication | Server-Sent Events (SSE) streaming |

### Infrastructure
| Component | Details |
|-----------|---------|
| Environment | Python virtualenv (venv/) |
| Package Manager | pip (requirements.txt) |
| Startup Script | run.sh |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FinChat Architecture                         │
└─────────────────────────────────────────────────────────────────────┘

   ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
   │   Frontend   │────▶│  FastAPI API  │────▶│  LLM Generator   │
   │  (HTML/JS)   │◀────│  (server.py)  │◀────│ (llama.cpp :8080)│
   └──────────────┘     └───────┬───────┘     └──────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    RAG Pipeline       │
                    │  ┌─────────────────┐  │
                    │  │  Vector Store   │  │
                    │  │ FAISS + BM25    │  │
                    │  └────────┬────────┘  │
                    │           │          │
                    │  ┌────────▼────────┐  │
                    │  │   Embedder      │  │
                    │  │ BGE + Reranker  │  │
                    │  └────────┬────────┘  │
                    │           │          │
                    │  ┌────────▼────────┐  │
                    │  │ PDF Parser      │  │
                    │  │ (pypdf)         │  │
                    │  └─────────────────┘  │
                    └───────────────────────┘
```

---

## 4. Data Pipelines

### 4.1 Ingestion Pipeline

```
PDF Files ──▶ pypdf Reader ──▶ Text Extraction ──▶ Chunking ──▶ Contextual Enrichment
                │                                    │                    │
                │                                    ▼                    ▼
                │                              chunk_text()        [Doc: X | Page: Y]
                │                                    │                    │
                ▼                                    ▼                    ▼
         Extract metadata                    1000 char chunks      Metadata dict
         (doc_name, page_number)              with overlap         with text
```

**Key Details:**
- Chunk size: 1000 characters
- Overlap: 200 characters
- Chunks enriched with `[Document: X | Page: Y]` prefix for better retrieval
- Output: List of dicts with keys: `doc_name`, `doc_date`, `page_number`, `chunk_id`, `text`

### 4.2 Indexing Pipeline

```
Chunks ──▶ BGE Embedder ──▶ Normalized Embeddings ──▶ FAISS Index (FlatIP)
   │                                                      │
   │                                                      ▼
   ▼                                              VectorStore object
BM25 Index (BM25Okapi) ◀── Tokenized corpus ◀─────────────┘
```

**Key Details:**
- Embedding model: `BAAI/bge-base-en-v1.5` (768 dimensions)
- FAISS index type: `IndexFlatIP` (Inner Product, with L2 normalization)
- BM25: Okapi implementation with corpus tokenization
- Serialization: FAISS index → `faiss.index`, Metadata → `metadata.pkl` (pickle)

### 4.3 Retrieval Pipeline (Query Flow)

```
User Query ──▶ BGE Query Embedder ──▶ Hybrid Search (Semantic + BM25)
                    │                        │
                    │                        ▼
                    │              ┌─────────────┬──────────────┐
                    │              │             │              │
                    ▼              ▼             ▼              ▼
             "query: {query}"   Semantic     BM25        Merge & Dedup
                               (FAISS)     (Okapi)     (by chunk_id)
                                    │             │
                                    └──────┬──────┘
                                           ▼
                                   Initial K results (default: 10)
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │  Cross-Encoder Rerank  │
                              │ BGE-Reranker-Base     │
                              └───────────┬────────────┘
                                          ▼
                                  Final Top-K (default: 3)
```

**Key Details:**
- Hybrid search weight: 70% semantic, 30% keyword (via additive scoring)
- Reranker: Cross-Encoder predicting relevance scores
- Final filtering: Relevance threshold (default: 0.3)

### 4.4 Generation Pipeline

```
Prompt Template ──▶ Context Building ──▶ LLM Request ──▶ Streaming Response
      │                     │                  │                │
      │                     ▼                  ▼                ▼
build_prompt()      context_builder    POST to :8080    SSE chunks
                     (format sources)   /v1/chat/       to frontend
                                      completions
```

**Prompt Structure:**
```
### INSTRUCTIONS
You are a highly precise Financial Analysis Assistant...

### CONSTRAINTS
- Cite every claim using [Source X] format
- Highlight discrepancies across documents
- If info not present, say so

### CONTEXT
[Source 1] Document: X, Page: Y
{text}
...

### USER QUERY
{query}

### ANALYSIS AND RESPONSE
```

---

## 5. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve index.html |
| GET | `/static/*` | Serve static assets |
| GET | `/pdfs/*` | Serve PDF files |
| POST | `/api/chat` | Main chat endpoint (SSE streaming) |
| POST | `/api/upload` | Upload PDF (background re-index) |
| GET | `/api/documents` | List indexed documents |
| DELETE | `/api/documents/{filename}` | Delete document |
| GET | `/api/portfolio/stats` | Get portfolio statistics |
| GET | `/api/settings` | Get current RAG settings |
| POST | `/api/settings` | Update Top-K, Threshold, Temperature |
| POST | `/api/export` | Export session as Markdown |

---

## 6. Key Components

### 6.1 VectorStore (`vector_store/faiss_index.py`)
- **Class:** `VectorStore`
- **Methods:**
  - `add(embeddings, metadata_list)` - Add vectors + metadata
  - `search_semantic(query_embedding, k, threshold)` - Dense retrieval
  - `search_bm25(query, k)` - Sparse retrieval
  - `search_hybrid(query, query_embedding, k)` - Combined search
  - `save(path, metadata_path)` - Persist to disk
  - `load(path, metadata_path)` - Load from disk

### 6.2 Embedder (`embeddings/embedder.py`)
- **Models:** `BAAI/bge-base-en-v1.5` (bi-encoder), `BAAI/bge-reranker-base` (cross-encoder)
- **Functions:**
  - `load_models()` - Lazy load global models
  - `embed_passages(texts, batch_size)` - Batch encode documents
  - `embed_query(query)` - Encode single query
  - `rerank_results(query, results, top_n)` - Cross-encoder reranking

### 6.3 Generator (`llm/generator.py`)
- **LLM Server:** `http://localhost:8080/v1/chat/completions`
- **Fallback:** `http://localhost:8080/completion` (older API)
- **Streaming:** Uses SSE with `stream: True`

### 6.4 Context Builder (`llm/context_builder.py`)
- Formats retrieved documents into prompt context
- Adds `[Source N]` labels for citation tracking

### 6.5 PDF Parser (`ingestion/pdf_parser.py`)
- Extracts text per page using `pypdf.PdfReader`
- Chunks text with sentence-aware splitting
- Enriches chunks with document/page metadata

---

## 7. Frontend Features

### UI Components
- **Sidebar:** Session history, Knowledge Base, Settings
- **Chat Area:** Message list with AI/user styling, streaming text display
- **Input Area:** Text input, file upload, parameter tuning
- **Verification Panel:** PDF viewer (iframe), citation context, metadata
- **Modals:** Settings (Top-K, Threshold, Temperature), Portfolio Stats, Knowledge Base

### Client-Side Logic (`script-v2.js`)
- SSE connection handling for streaming responses
- localStorage for session persistence
- Dynamic PDF viewer loading
- Citation clicking → loads exact page in verification panel
- Export generates Markdown report

---

## 8. Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `INITIAL_K` | 10 | Initial retrieval count before reranking |
| `FINAL_TOP_K` | 3 | Final context chunks sent to LLM |
| `THRESHOLD` | 0.3 | Minimum rerank score to include |
| `CHUNK_SIZE` | 1000 | Characters per PDF chunk |
| `OVERLAP` | 200 | Character overlap between chunks |
| `TEMPERATURE` | 0.7 | LLM generation temperature |

---

## 9. Initialization Flow

1. **Load Models** - BGE embedding + reranker (GPU if available, else CPU)
2. **Scan PDFs** - Check `data/pdfs/` for files
3. **Index Check** - If `faiss.index` + `metadata.pkl` exist:
   - Compare indexed docs vs current docs
   - Rebuild if mismatch, else skip
4. **Build Index** (if needed):
   - Extract & chunk all PDFs
   - Generate embeddings (batched)
   - Create FAISS + BM25 indexes
   - Serialize to disk

---

## 10. Running the System

### Prerequisites
- Python packages: `fastapi`, `uvicorn`, `faiss-cpu`, `rank-bm25`, `sentence-transformers`, `pypdf`, `torch`
- llama.cpp server running on port 8080 with loaded model weights

### Startup
```bash
./run.sh
# or manually:
# 1. Start llama.cpp server on :8080
# 2. uvicorn server:app --host 0.0.0.0 --port 8000
```

### Access
- Web UI: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

---

## 11. File Structure

```
finchat/
├── app/
│   ├── chatbot.py           # Empty placeholder
│   └── static/
│       ├── index.html        # Main UI
│       ├── script-v2.js      # Client logic
│       ├── tailwind.min.js   # Localized Tailwind
│       └── favicon.ico/svg
├── embeddings/
│   └── embedder.py           # BGE embedding & reranking
├── ingestion/
│   ├── pdf_parser.py         # PDF text extraction
│   └── audio_transcriber.py  # Placeholder (empty)
├── llm/
│   ├── context_builder.py    # Prompt formatting
│   └── generator.py          # LLM streaming client
├── vector_store/
│   └── faiss_index.py        # Hybrid vector store
├── data/
│   ├── pdfs/                 # Uploaded documents
│   └── audio/                # Audio files (unused)
├── models/                   # Model weights (external)
├── main.py                   # CLI entry point
├── server.py                 # FastAPI server
├── requirements.txt          # Dependencies
├── run.sh                    # Startup script
├── faiss.index               # Serialized vector index
└── metadata.pkl               # Serialized metadata
```

---

*Report generated from codebase analysis on April 2026*