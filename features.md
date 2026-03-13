# FinChat Features

Currently implemented features in this RAG system:

## 🔍 Retrieval & Search
- **Hybrid Search**: Combines BM25 keyword search with FAISS semantic vector search.
- **Cross-Encoder Reranking**: Uses `BAAI/bge-reranker-base` for high-precision result scoring.
- **Multi-File Support**: Automatically scans and indexes all PDF files in the `data/pdfs/` directory.

## 📄 Ingestion & Parsing
- **Semantic Chunking**: Intelligent text splitting that respects sentence boundaries and maintains context overlap.
- **Multi-PDF Parsing**: Extracts text and metadata (page numbers, filenames) from multiple documents.

## 🤖 LLM & Generation
- **Real-time Streaming**: Tokens are streamed directly from the LLM via SSE for immediate feedback.
- **Gemma-3 Optimized**: Configured with chat templates specifically for Gemma-3 models.
- **Source Attribution**: Prompt engineering ensures the assistant cites sources (e.g., [Source 1]) in its answers.

## 🌐 Web Interface (Gemini-Style)
- **Responsive Layout**: Full-page design with a collapsible sidebar for mobile and desktop.
- **Multi-Chat Sessions**: Create and manage multiple independent conversations.
- **Auto-Title Generation**: Automatically names chat sessions based on the user's first query.
- **Local Persistence**: Full chat history and session states are saved to `localStorage`.
- **Premium Aesthetics**: Glassmorphism, smooth animations, and optimized typography.

## 🛠️ Infrastructure
- **Automatic Server Management**: `run.sh` handles starting and health-checking the `llama-server` in the background.
- **Vector Store Persistence**: FAISS index and BM25 metadata are saved to disk for fast subsequent loads.
