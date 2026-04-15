# FinChat

FinChat is a FastAPI-based RAG workspace for financial PDFs. It combines hybrid retrieval, reranking, and cited responses in a focused chat interface.

## Overview

- Hybrid search with FAISS and BM25
- Cross-encoder reranking for final context selection
- PDF upload, indexing, and session-scoped documents
- Citations with in-app PDF preview
- Persistent chat sessions in the browser

## Stack

- Backend: FastAPI, Python
- Retrieval: FAISS, BM25, sentence-transformers
- Parsing: `pypdf`
- Frontend: Vanilla JS, Tailwind
- LLM access: llama.cpp REST API

## Setup

```bash
pip install -r requirements.txt
```

Place PDFs in `data/pdfs/` or upload them from the app.

## Run

```bash
./run.sh
```

Open `http://localhost:8000`.

## Notes

- Search results are reranked before generation.
- Citations open the source PDF at the referenced page.
- Session state is stored locally in the browser.
