# FinChat Project Report

## 1. Scope

This document covers the implemented FinChat application as it exists in this repository.
It describes the backend, frontend, AI pipeline, API surface, storage, and developer utilities.
It excludes unimplemented ideas and only lists behavior present in the codebase.

## 2. Product Summary

FinChat is a financial document analysis workspace built around retrieval-augmented generation.
It ingests PDFs, indexes them with a hybrid search stack, reranks retrieved chunks, and streams cited answers back to the user.

The project exposes two runtime modes:

- Web application via FastAPI and a browser UI.
- Console application via `main.py`.

## 3. Repository Layout

### 3.1 Root Entry Points

- `server.py`: primary FastAPI web server.
- `main.py`: console RAG loop.
- `config.py`: central configuration values.
- `README.md`: high-level project summary.

### 3.2 Core Packages

- `api_routes/`: HTTP route modules.
- `services/`: business logic for chat and documents.
- `core/`: startup, progress, and shared helpers.
- `embeddings/`: embedding and reranking helpers.
- `ingestion/`: PDF parsing and chunking.
- `llm/`: context assembly and generation.
- `models/`: typed response models.
- `vector_store/`: FAISS and BM25 storage layer.

### 3.3 Frontend Assets

- `app/static/index.html`: app shell and modal markup.
- `app/static/script-v2.js`: client-side behavior.
- `app/static/tailwind.min.js`: local Tailwind runtime.

### 3.4 Utility Scripts

- `test_reranker.py`: sample reranker probe.
- `test_reranker_2.py`: second reranker probe.
- `logging_config.py`: logging setup.
- `core/io_utils.py`: stdout/stderr suppression helper.

## 4. Runtime Modes

### 4.1 Web Mode

`server.py` creates the FastAPI application, mounts routes, serves static files, and initializes the RAG stack on startup.

### 4.2 Console Mode

`main.py` launches an interactive terminal session that accepts queries, retrieves context, reranks results, builds a prompt, and streams the model output.

## 5. System Architecture

### 5.1 High-Level Flow

1. PDFs are discovered from `data/pdfs/`.
2. Files are parsed into page-level chunks.
3. Chunks are embedded and indexed in FAISS.
4. BM25 is built from the same text corpus.
5. Queries are embedded and searched across both retrievers.
6. Results are reranked by a cross-encoder.
7. The selected context is assembled into a prompt.
8. The LLM responds through the configured llama.cpp endpoint.
9. The frontend streams citations and answer chunks over SSE.

### 5.2 Main Components

- FastAPI web layer.
- Chat and document service layer.
- Hybrid vector store.
- PDF parsing and chunking pipeline.
- Sentence-transformer embedding and reranking.
- llama.cpp-backed answer generation.
- Browser UI with session persistence and citation inspection.

## 6. Configuration

All application configuration is centralized in `config.py`.

| Key | Value | Purpose |
|---|---:|---|
| `APP_TITLE` | `FinChat API` | API title |
| `APP_VERSION` | `2.6.3` | App version string |
| `INITIAL_K` | `50` | Initial retrieval depth |
| `FINAL_TOP_K` | `5` | Final reranked context size |
| `DEFAULT_THRESHOLD` | `0.05` | Minimum rerank score |
| `DEFAULT_TEMPERATURE` | `0.1` | Default generation temperature |
| `CHUNK_SIZE` | `1000` | PDF chunk size |
| `CHUNK_OVERLAP` | `200` | Chunk overlap |
| `EMBEDDING_MODEL` | `BAAI/bge-base-en-v1.5` | Bi-encoder |
| `RERANKER_MODEL` | `BAAI/bge-reranker-base` | Cross-encoder |
| `LLAMA_SERVER_URL` | `http://127.0.0.1:8080/v1/chat/completions` | LLM endpoint |
| `EMBEDDING_DIM` | `768` | FAISS vector dimension |
| `MAX_FILE_SIZE_MB` | `50` | Upload limit |
| `ALLOWED_EXTENSIONS` | `{'.pdf'}` | Supported uploads |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |

## 7. Backend Startup

### 7.1 `server.py`

The web server does the following:

- Creates the FastAPI app.
- Adds permissive CORS middleware.
- Mounts `app/static/` under `/static`.
- Mounts `data/pdfs/` under `/pdfs`.
- Serves the root HTML document from `/`.
- Adds a no-cache middleware for all responses.
- Loads the RAG system on startup.
- Instantiates and injects the chat and document services.

### 7.2 Startup Initialization

On startup, the app:

- Loads the embedding and reranker models.
- Scans the PDF directory.
- Loads an existing FAISS index when present.
- Rebuilds the index if the file set changed.
- Installs the active vector store into the route layer.
- Installs the document service into the document routes.

## 8. Core Initialization Pipeline

Implemented in `core/initialization.py`.

### 8.1 Responsibilities

- Load models.
- Discover documents.
- Load or rebuild the vector index.
- Produce startup progress updates.
- Return the vector store plus file/chunk counts.

### 8.2 Startup Behavior

- Shows a Rich console status indicator.
- Uses `core.progress.set_progress()` to expose startup state.
- Reuses an existing FAISS index when the current PDF set matches the indexed document set.
- Rebuilds embeddings when the document set changes or persistence is unavailable.

### 8.3 Prompt Helper

`build_prompt(query, retrieved_results)` delegates context formatting to `llm.context_builder.build_context()` and returns the final prompt body.

## 9. PDF Ingestion

Implemented in `ingestion/pdf_parser.py`.

### 9.1 File Parsing

`extract_pdf_pages()`:

- Accepts one or many PDF file paths.
- Verifies file existence.
- Verifies `.pdf` extension.
- Reads each document with `pypdf.PdfReader`.
- Uses file modification time as the document date.
- Extracts text page by page.

### 9.2 Byte Upload Parsing

`extract_pdf_pages_from_bytes()`:

- Parses uploaded file bytes directly.
- Produces the same chunk dictionary structure used by disk-based ingestion.
- Assigns a current date string when the upload comes from the browser.

### 9.3 Text Cleaning

- Collapses repeated spaces and tabs.
- Normalizes blank lines.
- Preserves light structure for downstream retrieval.

### 9.4 Chunking

`chunk_text()`:

- Splits text by character length.
- Uses overlap between consecutive chunks.
- Prefers sentence-like breakpoints near the chunk boundary.
- Drops tiny fragments below the minimum threshold.

### 9.5 Chunk Metadata

Each emitted chunk carries:

- `doc_name`
- `doc_date`
- `page_number`
- `chunk_id`
- `text`

The text itself is contextually enriched with document and page labels.

## 10. Embeddings and Reranking

Implemented in `embeddings/embedder.py` and `models/model_manager.py`.

### 10.1 Model Manager

`ModelManager` loads and caches:

- `BAAI/bge-base-en-v1.5`
- `BAAI/bge-reranker-base`

It also:

- Lazily loads the models.
- Silences model-loading noise.
- Exposes singleton getters for both models.

### 10.2 Embedding Passages

`embed_passages()`:

- Adds the `passage:` prefix required by the BGE model.
- Batches inputs for stability.
- Normalizes embeddings.
- Chooses CUDA when available, otherwise CPU.
- Invokes an optional progress callback.

### 10.3 Embedding Queries

`embed_query()`:

- Adds the `query:` prefix.
- Returns a normalized query vector.

### 10.4 Cross-Encoder Reranking

`rerank_results()`:

- Builds query/passage pairs.
- Scores them with the cross-encoder.
- Applies sigmoid normalization.
- Stores `rerank_score` on each result.
- Sorts descending by rerank score.
- Returns the top N results.

## 11. Vector Store

Implemented in `vector_store/faiss_index.py`.

### 11.1 Storage Model

- FAISS `IndexFlatIP` for semantic retrieval.
- BM25 over tokenized document text for lexical retrieval.
- Metadata array stored alongside both retrieval systems.

### 11.2 Add Flow

`add()`:

- Converts embeddings to `float32`.
- L2-normalizes embeddings.
- Adds them to FAISS.
- Extends metadata.
- Rebuilds BM25 from the full metadata corpus.

### 11.3 Removal Flow

The store supports removal by:

- document name
- session id

Both removal paths:

- Select matching chunk indices.
- Remove them from FAISS.
- Filter the metadata list.
- Rebuild BM25 or clear it when empty.

### 11.4 Retrieval

`search_semantic()`:

- Normalizes the query vector.
- Searches the FAISS index.
- Expands the search window when filtering is requested.
- Filters by session id and document name when provided.

`search_bm25()`:

- Tokenizes the query.
- Scores against the BM25 corpus.
- Filters by session id and document name when provided.

`search_hybrid()`:

- Runs both semantic and BM25 search.
- Deduplicates by `chunk_id`.
- Merges the two result sets.
- Slightly boosts duplicate hits.

### 11.5 Persistence

`save()` writes:

- FAISS index to disk.
- Metadata and BM25 tokens to a pickle file.

`load()` restores both from disk when files exist.

## 12. Chat Service Layer

Implemented in `services/chat_service.py`.

### 12.1 Service State

The chat service keeps the current RAG settings in memory:

- `top_k`
- `threshold`
- `temperature`

### 12.2 Document Retrieval

`retrieve_relevant_documents()`:

- Builds a query embedding.
- Runs hybrid retrieval.
- Reranks the initial result set.
- Applies the configured threshold.
- Converts results to `SearchResult` models.

If a `doc_name` filter exists, the effective threshold is relaxed to support vague file-specific questions.

### 12.3 Full-Document Retrieval

`retrieve_all_document_chunks()`:

- Collects every chunk for one document.
- Samples long documents from the beginning, middle, and end.
- Deduplicates sampled chunk ids.
- Returns the sampled chunks as `SearchResult` objects.

### 12.4 Prompt Building

`build_rag_prompt()`:

- Converts `SearchResult` objects back into dictionaries.
- Preserves optional score fields.
- Delegates to `core.initialization.build_prompt()`.

### 12.5 Streaming Generation

`generate_answer_stream()`:

- Uses the current service temperature unless overridden.
- Streams output from `llm.generator.generate_answer()`.

### 12.6 Citations

`format_citations()`:

- Converts search results into frontend-friendly citation objects.
- Includes doc name, doc date, page, text, and relevance.

## 13. LLM Generation Layer

Implemented in `llm/generator.py`.

### 13.1 Prompt Strategy

The generator uses a system prompt that:

- Requests precise analytical behavior.
- Requests deduplicated citations.
- Pushes grouped sourcing by filename or document title.
- Encourages direct output without filler.

### 13.2 Message Preparation

Before sending the request, the code:

- Cleans history content.
- Strips HTML tags from stored messages.
- Forces the first message to be user-originated.
- Merges consecutive same-role messages.
- Prepends the system prompt to the first user message.

### 13.3 Primary Request

The main request uses the v1 chat-completions endpoint at `LLAMA_SERVER_URL` with:

- messages
- max_tokens
- temperature
- top_p
- top_k
- stream enabled

### 13.4 Fallback Path

If the v1 endpoint fails, the code retries with the older `/completion` endpoint and a flattened prompt format.

### 13.5 Streaming Parse

The generator reads SSE-style lines, parses JSON payloads, and yields content chunks to the caller.

## 14. API Surface

All main routes are mounted under `/api/v1`.

### 14.1 Chat Routes

**Base:** `/api/v1/chat`

| Method | Path | Behavior |
|---|---|---|
| POST | `/api/v1/chat` | Streams citations and answer chunks for a query |
| DELETE | `/api/v1/chat/session/{session_id}` | Removes a session’s chunks from index and disk |
| POST | `/api/v1/chat/export` | Exports a conversation as markdown |

#### POST `/api/v1/chat`

Request body:

- `query`
- `session_id` optional
- `history` optional list of `{ role, content }`

Implemented behavior:

- Initializes services if needed.
- Detects `@filename` mentions.
- Filters retrieval to the referenced document when present.
- Detects summarize-style queries.
- Retrieves all chunks for document summaries.
- Otherwise runs standard retrieval.
- Sends citations immediately over SSE.
- Streams generated answer chunks.
- Sends a final done event.

#### DELETE `/api/v1/chat/session/{session_id}`

- Removes the session’s vectors from the store.
- Saves the updated index and metadata.
- Deletes the session directory from `data/pdfs/<session_id>` when present.

#### POST `/api/v1/chat/export`

- Converts the stored HTML conversation into markdown.
- Rewrites citation spans into source labels.
- Writes the report to `/tmp`.
- Returns the file as a downloadable markdown response.

### 14.2 Document Routes

**Base:** `/api/v1/documents`

| Method | Path | Behavior |
|---|---|---|
| POST | `/api/v1/documents/upload` | Uploads a PDF |
| GET | `/api/v1/documents` | Lists documents |
| DELETE | `/api/v1/documents/{filename}` | Deletes a document |
| GET | `/api/v1/documents/progress` | Returns indexing progress |
| GET | `/api/v1/documents/portfolio/stats` | Returns portfolio stats |

#### POST `/api/v1/documents/upload`

Implemented behavior:

- Accepts a PDF upload.
- Supports optional `session_id`.
- Saves the file globally or into a session subdirectory.
- For session uploads, triggers fast sub-indexing.
- For global uploads, triggers full system reinitialization.

#### GET `/api/v1/documents`

- Returns all global documents.
- Includes session documents when `session_id` is supplied.
- Removes filename collisions by preferring session-scoped files.

#### DELETE `/api/v1/documents/{filename}`

- Deletes a global document or the first matching session-scoped copy.
- Triggers index cleanup in the background when successful.

#### GET `/api/v1/documents/progress`

- Returns the shared progress object used by the frontend.

#### GET `/api/v1/documents/portfolio/stats`

- Returns count, total size, detected uppercase entities, and last updated date.

### 14.3 Settings Routes

**Base:** `/api/v1/settings`

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/v1/settings` | Returns current settings |
| POST | `/api/v1/settings` | Updates current settings |

Implemented settings fields:

- `top_k`
- `threshold`
- `temperature`

### 14.4 Root and Static Routes

Implemented in `server.py`:

- `GET /` -> `app/static/index.html`
- `/static/*` -> static assets
- `/pdfs/*` -> PDF files

### 14.5 Response Middleware

All HTTP responses include no-cache headers:

- `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`
- `Pragma: no-cache`
- `Expires: 0`

## 15. Shared Route Infrastructure

### 15.1 Router Package

`api_routes/__init__.py` exports:

- `chat_router`
- `docs_router`
- `settings_router`

### 15.2 Vector Store Reference

`api_routes/vector_store_ref.py` holds a global store reference so background route tasks can access the active index.

## 16. Data and Persistence

### 16.1 On-Disk Storage

- PDFs live under `data/pdfs/`.
- Session-specific PDFs live under `data/pdfs/<session_id>/`.
- FAISS index lives at `faiss.index`.
- Index metadata lives at `metadata.pkl`.

### 16.2 Browser Storage

The frontend stores:

- session history
- pin state
- current session id
- UI collapse state

### 16.3 In-Memory State

- Current settings live in `api_routes/settings_routes.current_settings`.
- Progress lives in `core.progress.global_progress`.
- The active vector store lives in the route module reference.

### 16.4 Temporary Files

- Exported markdown reports are written to `/tmp` before download.

## 17. Frontend Architecture

Implemented in `app/static/index.html` and `app/static/script-v2.js`.

### 17.1 App Shell

The UI is structured as a chat application shell with:

- a left sidebar
- a main chat canvas
- a fixed composer area
- modal overlays for history, settings, stats, vault, and citation inspection

### 17.2 Sidebar

Implemented sidebar sections:

- Brand / status header
- New analysis action
- Session search
- Chats list
- Knowledge vault summary
- Tools section
- System health footer

### 17.3 Session Manager

The sidebar session stack supports:

- switching sessions
- pinning sessions
- renaming sessions
- deleting sessions
- filtering by search text

### 17.4 Knowledge Vault

The vault section and modal provide:

- document count
- storage size
- tracked entities count
- upload buttons
- document listing
- per-document deletion
- background indexing progress

### 17.5 Tools

Implemented tools:

- retrieval settings
- markdown export

### 17.6 Health Footer

The footer displays:

- current model/connection status
- index progress state
- active session summary

### 17.7 Header

The header shows:

- FinChat breadcrumb
- active analysis title
- session status chip
- vault status chip
- mobile sidebar toggle

### 17.8 Welcome Surface

The welcome panel contains quick-start analysis prompts.

### 17.9 Chat Composer

The composer supports:

- text input with auto-resize
- enter-to-send
- shift+enter for new lines
- session upload attachment button
- send button
- `@filename` mention support

### 17.10 Mention Dropdown

When the user types `@`, the composer shows matching documents from the current session and lets the user insert a full document mention.

### 17.11 Verification Panel

The citation panel includes:

- PDF iframe preview
- highlighted excerpt
- metadata details
- close action

### 17.12 History Modal

The history modal mirrors the session manager in a larger overlay for review and cleanup.

### 17.13 Settings Modal

The settings modal exposes sliders for:

- top-k retrieval
- relevance threshold
- model temperature

### 17.14 Stats Modal

The stats modal displays:

- document count
- total storage
- last updated date
- tracked entity chips

### 17.15 Knowledge Vault Modal

The vault modal displays:

- upload controls
- progress bar
- document list

### 17.16 Drag-and-Drop Uploads

Both the main canvas and vault modal accept PDF drag-and-drop and route dropped files to the correct upload flow.

### 17.17 Toasts

The frontend shows temporary toast notifications for upload, delete, export, and error states.

## 18. Frontend State and Behavior

### 18.1 Session Persistence

The client stores chat sessions in `localStorage` under `finchat_sessions_v6`.

### 18.2 UI Persistence

The sidebar collapse state is stored under `finchat_ui_v1`.

### 18.3 Session Schema

Stored sessions include:

- id
- title
- pinned
- createdAt
- updatedAt
- messages

### 18.4 Message Schema

Each message stores:

- id
- role
- html
- citations

### 18.5 Client-Side Controls

The UI supports:

- new chat creation
- session switching
- session pin/rename/delete
- vault opening
- upload initiation
- settings changes
- stats refresh
- export download

### 18.6 Keyboard Handling

- `Enter` submits the prompt.
- `Shift+Enter` inserts a newline.
- `Esc` closes the mention dropdown.
- `Ctrl/Cmd+K` creates a new analysis session.

### 18.7 Streaming Rendering

The frontend consumes SSE messages and handles:

- citation payloads
- text chunks
- completion signals

## 19. Frontend Layout and Responsiveness

### 19.1 Desktop

- Sidebar is visible by default.
- Sidebar can collapse to a narrow rail.
- Main content shifts to respect sidebar width.

### 19.2 Mobile

- Sidebar slides in from the left.
- Backdrop blocks the main canvas.
- A mobile menu button opens the drawer.
- A close button dismisses the drawer.

### 19.3 Composer and Panels

- Composer remains pinned near the bottom.
- Modal overlays use centered panels with scrollable content.
- The PDF preview panel uses a split layout on large screens and stacked layout on smaller screens.

## 20. Request and Response Details

### 20.1 Chat SSE Events

The chat endpoint emits these event types:

- `citations`
- `chunk`
- `done`

### 20.2 Export Response

The export endpoint returns a markdown file response with a timestamped filename.

### 20.3 Progress Response

The progress endpoint returns the live global state object:

- `status`
- `message`
- `progress`

## 21. Logging

### 21.1 Application Logging

`logging_config.py` sets:

- root logging configuration
- optional file logging
- compact structured formatting
- lower verbosity for HTTP and ML libraries

### 21.2 Noisy Model Loads

`core/io_utils.py` provides a context manager that suppresses stdout/stderr while loading models.

## 22. Auxiliary Scripts

### 22.1 Reranker Probes

`test_reranker.py` and `test_reranker_2.py` are small local validation scripts that:

- load the reranker model
- score sample query/passage pairs
- print raw and sigmoid-normalized scores

### 22.2 Console Mode

`main.py` provides a minimal terminal interface that:

- initializes the system
- retrieves and reranks context
- prints source tables
- streams the answer text

## 23. Typed Models

### 23.1 SearchResult

`models/search_result.py` defines the result schema used by retrieval and citations.

Fields:

- `doc_name`
- `doc_date`
- `page_number`
- `chunk_id`
- `text`
- `score`
- `search_type`
- `rerank_score`

### 23.2 SearchResults

`SearchResults` is a container model with:

- `results`
- `total`
- `query`

## 24. File Responsibility Map

- `server.py`: web application bootstrap.
- `main.py`: console query loop.
- `config.py`: central configuration.
- `core/initialization.py`: startup and index build/load.
- `core/progress.py`: live progress state.
- `core/io_utils.py`: output suppression helper.
- `ingestion/pdf_parser.py`: PDF parsing and chunking.
- `embeddings/embedder.py`: embedding and reranking.
- `models/model_manager.py`: ML model lifecycle.
- `models/search_result.py`: typed result schemas.
- `vector_store/faiss_index.py`: hybrid search and persistence.
- `services/chat_service.py`: chat business logic.
- `services/document_service.py`: upload/list/delete/stats logic.
- `llm/context_builder.py`: prompt context formatting.
- `llm/generator.py`: LLM request handling.
- `api_routes/chat_routes.py`: chat endpoints.
- `api_routes/docs_routes.py`: document endpoints.
- `api_routes/settings_routes.py`: settings endpoints.
- `api_routes/vector_store_ref.py`: global store reference.
- `logging_config.py`: logging setup.
- `app/static/index.html`: UI shell and modal structure.
- `app/static/script-v2.js`: all frontend behavior.

## 25. Implemented Feature Inventory

### 25.1 Retrieval

- Hybrid FAISS + BM25 retrieval.
- Query embedding with BGE.
- Cross-encoder reranking.
- Threshold filtering.
- Session-aware filtering.
- Document-name filtering through `@filename` mentions.

### 25.2 Generation

- Streaming responses.
- History-aware prompts.
- System prompt injection.
- v1 API request with fallback to older completion endpoint.

### 25.3 Document Management

- PDF upload.
- Session-scoped document upload.
- Global document upload.
- Document listing.
- Document deletion.
- Background reindexing.
- Fast subupload indexing.

### 25.4 Session Management

- Browser session persistence.
- New session creation.
- Session switching.
- Pinning.
- Renaming.
- Deleting.
- Search/filter.

### 25.5 Citations and Verification

- Immediate citation delivery.
- Clickable citation chips.
- PDF preview by page.
- Metadata display.
- Source excerpt display.

### 25.6 Reporting and Export

- Markdown export of conversations.
- Timestamped downloadable reports.

### 25.7 Status and Progress

- Startup progress.
- Upload indexing progress.
- Frontend progress bar.
- Connection/status chips.

### 25.8 Interface Polish

- Collapsible sidebar.
- Mobile drawer.
- Drag-and-drop upload targets.
- Toast notifications.
- Responsive modals.

## 26. Notes on Current Operation

- The application is designed around local files and a local llama.cpp server.
- The PDF preview uses the browser to open the mounted PDF path.
- The browser session is the source of truth for chat history in the UI.
- The backend index is the source of truth for retrieval.

## 27. Summary

FinChat implements a complete local RAG workflow for financial PDFs.
It covers ingestion, indexing, retrieval, reranking, citation formatting, streaming generation, document management, session management, export, and a responsive browser UI.
