# FinChat: Minimal Analyst Terminal

A high-performance, institutional-grade Retrieval-Augmented Generation (RAG) system tailored for precise financial analysis. FinChat features a "Retrieve-then-Rerank" architecture with a clean, minimal, Helvetica-based interface designed for deep focus and reliability.

## 🚀 Key Features

### ⚖️ Intelligence & RAG Protocol
- **Hybrid Search**: Combines Dense Retrieval (BAAI/bge-base-en-v1.5) with Sparse Retrieval (BM25).
- **Cross-Encoder Reranking**: Uses `BAAI/bge-reranker-base` for extreme precision.
- **Protocol Tuning**: Dynamic control over Top-K context, relevance thresholds, and LLM temperature.
- **Data Verification**: Integrated side panel for real-time document verification with PDF page rendering.

### 📁 Management & Reporting
- **Knowledge Base**: Interactive dashboard to list, search, and redact indexed institutional documents.
- **Instant Upload**: Direct PDF upload with automated background re-indexing.
- **Portfolio Stats**: Aggregated data visualization of indexed assets and detected entities.
- **Institutional Export**: Generate and download professional markdown reports of any analysis session.

### 🖋️ Minimalist Web Interface
- **Analyst UI**: A high-contrast, light-themed terminal optimized for readability using Helvetica Neue.
- **Multi-Session Logic**: Manage multiple independent ledgers with local persistence via `localStorage`.
- **Responsive Terminal**: Full-page layout with a collapsible sidebar and intelligent floating controls.
- **Production Optimized**: Localized Tailwind CSS and zero external dependencies for high stability.

## 🛠️ Architecture

1.  **Ingestion**: `pypdf` extracts text and metadata (filing dates, reliability) -> Semantic splitter creates contextual chunks.
2.  **Indexing**: Chunks embedded via BGE-Base and stored in a hybrid FAISS + BM25 vector store.
3.  **Backend**: FastAPI server manages the RAG pipeline, document management CRUD, and SSE streaming.
4.  **Frontend**: Clean Vanilla JS implementation with dynamic message animations and robust citation mapping.

## ⚙️ Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Prepare Data**:
   Place financial PDFs in `data/pdfs/` or use the in-app **Upload** tool.

3. **Run the Terminal**:
   ```bash
   ./run.sh
   ```
   Access the interface at `http://localhost:8000`.

## 🔍 Optimization Protocols

- **Retrieve-then-Rerank**: Initial 15-document retrieval refined to user-defined Top-K (default 3) to eliminate hallucinations.
- **Verification Loop**: Every AI claim is cited; clicking a citation opens the exact PDF page in the Verification Panel.
- **Persistence Layer**: Session titles auto-generate based on analysis context and persist across browser restarts.
