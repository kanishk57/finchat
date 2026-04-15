# FinChat Features

Comprehensive capabilities of the Minimal Analyst Terminal:

## 🔍 Retrieval & Search Protocol
- **Hybrid Search**: Fuses BM25 keyword matching with FAISS semantic vector search for balanced retrieval.
- **Cross-Encoder Reranking**: Integrates `BAAI/bge-reranker-base` to score and refine top results.
- **Protocol Tuning**: Real-time adjustment of RAG parameters including Top-K, thresholding, and temperature.

## 📄 Ingestion & Management
- **Interactive Knowledge Base**: Full CRUD support for institutional PDFs via the browser interface.
- **Background Re-indexing**: Automated vector store updates upon new file uploads or redactions.
- **Metadata Extraction**: Automatic capture of filing dates and page-level source tracking.

## 🤖 LLM & Generation
- **Real-time SSE Streaming**: Immediate response feedback with dynamic message animations.
- **Gemma-3 Optimized**: Prompt templates specifically engineered for high-precision financial synthesis.
- **Robust Source Attribution**: Integrated citation mapping that survives page refreshes and session restarts.

## 🌐 Analyst Terminal (UI/UX)
- **Minimalist Light Theme**: High-contrast, Helvetica Neue aesthetic optimized for readability.
- **Integrated Verification**: Built-in PDF previewer that opens to the exact page cited by the AI.
- **Portfolio Analytics**: Aggregated dashboard showing asset volume and unique entities.
- **Institutional Reporting**: One-click export of analysis sessions into formatted Markdown reports.

## 🛠️ Infrastructure & Stability
- **Multi-Chat Persistence**: Local ledger management with auto-titling and session persistence.
- **Localized Assets**: Local Tailwind CSS and Material Icons for fast, CDN-independent deployment.
- **Automated Lifecycle**: `run.sh` manages backend server health and vector store loading.
