"""
Chat API routes module
Handles all chat-related endpoints
"""

from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
import json
import asyncio
import logging
import datetime
import re
from typing import List, Optional

from services.chat_service import ChatService
from vector_store.faiss_index import VectorStore
from config import (
    PDF_DIR, INDEX_PATH, METADATA_PATH
)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# Global instances (will be initialized on startup)
vector_store: VectorStore = None
chat_service: ChatService = None

logger = logging.getLogger(__name__)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    history: List[ChatMessage] = Field(default_factory=list)
    doc_target: Optional[str] = None

class ExportRequest(BaseModel):
    title: str
    messages: list

def set_services(v_store: VectorStore, c_service: ChatService):
    """Set the services from an external initializer (e.g. server.py)"""
    global vector_store, chat_service
    vector_store = v_store
    chat_service = c_service

def initialize_services():
    """Initialize the vector store and chat service for API usage"""
    global vector_store, chat_service
    if vector_store is None or chat_service is None:
        logger.info("Initializing system for API...")
        # Import here to avoid circular imports
        from core.initialization import initialize_system
        loop = asyncio.get_event_loop()
        # Execute the heavy initialization in a threadpool to not block asyncio
        vector_store, num_files, num_chunks = loop.run_until_complete(
            loop.run_in_executor(None, initialize_system)
        )
        chat_service = ChatService(vector_store)
        logger.info(f"System initialized! Loaded {num_files} files with {num_chunks} chunks.")


def _parse_doc_date(value: str):
    if not value or value == "UNKNOWN":
        return None
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.datetime.strptime(value.title(), fmt)
        except ValueError:
            continue
    return None


def _select_latest_doc_name(metadata, session_id: str = None):
    latest_doc = None
    latest_date = None

    for item in metadata:
        item_session = item.get("session_id")
        if session_id and item_session and item_session != session_id:
            continue

        doc_name = item.get("doc_name")
        if not doc_name:
            continue

        parsed_date = _parse_doc_date(item.get("doc_date"))
        if parsed_date is None:
            continue

        if latest_date is None or parsed_date >= latest_date:
            latest_doc = doc_name
            latest_date = parsed_date

    if latest_doc:
        return latest_doc

    # Fall back to the most recently seen document in the current scope.
    for item in reversed(metadata):
        item_session = item.get("session_id")
        if session_id and item_session and item_session != session_id:
            continue
        doc_name = item.get("doc_name")
        if doc_name:
            return doc_name

    return None


def _resolve_document_mention(query: str, known_docs):
    for doc in sorted(list(known_docs), key=len, reverse=True):
        doc_no_ext = doc.replace('.pdf', '')
        mention_with_ext = f"@{doc}"
        mention_without_ext = f"@{doc_no_ext}"

        if re.search(rf"{re.escape(mention_with_ext)}\b", query, flags=re.IGNORECASE):
            cleaned = re.sub(rf"{re.escape(mention_with_ext)}\b", '', query, flags=re.IGNORECASE).strip()
            return doc, cleaned
        if re.search(rf"{re.escape(mention_without_ext)}\b", query, flags=re.IGNORECASE):
            cleaned = re.sub(rf"{re.escape(mention_without_ext)}\b", '', query, flags=re.IGNORECASE).strip()
            return doc, cleaned

    return None, query

@router.post("")
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for processing user queries"""
    query = request.query
    session_id = request.session_id
    history = request.history
    doc_target = request.doc_target
    
    # Ensure services are initialized
    if vector_store is None or chat_service is None:
        initialize_services()
        
    # Extract file mention (@filename) intelligently by checking known docs
    doc_name_filter = None
    summarize_keywords = ["summarize", "summarise", "summary", "recap", "tl;dr", "what is this", "what is the content", "about this file", "what's in this"]
    is_summarize = any(word in query.lower() for word in summarize_keywords)

    if vector_store and '@' in query:
        # Get unique document names from vector store metadata
        # Also filter by session_id to only check relevant docs
        known_docs = set()
        for m in vector_store.metadata:
            item_session = m.get("session_id")
            if not session_id or not item_session or item_session == session_id:
                known_docs.add(m.get("doc_name"))

        doc_name_filter, query = _resolve_document_mention(query, known_docs)

    if is_summarize and not doc_name_filter and vector_store:
        scoped_docs = []
        seen_docs = set()
        for item in vector_store.metadata:
            item_session = item.get("session_id")
            if session_id and item_session and item_session != session_id:
                continue
            doc_name = item.get("doc_name")
            if doc_name and doc_name not in seen_docs:
                scoped_docs.append(doc_name)
                seen_docs.add(doc_name)

        summary_hints = ("latest", "newest", "recent", "last", "this file", "this document", "the filing")
        if len(scoped_docs) == 1 or any(hint in query.lower() for hint in summary_hints):
            doc_name_filter = _select_latest_doc_name(vector_store.metadata, session_id=session_id)

    if doc_target == "latest" and vector_store:
        doc_name_filter = _select_latest_doc_name(vector_store.metadata, session_id=session_id)
        if doc_name_filter:
            logger.info(f"Explicit latest-document target selected: {doc_name_filter}")
                
    if doc_name_filter:
        logger.info(f"File mention detected. Filtering search to: {doc_name_filter}")
    
    # Sync settings from settings_routes
    from api_routes.settings_routes import current_settings
    chat_service.update_settings(
        top_k=current_settings.top_k,
        threshold=current_settings.threshold,
        temperature=current_settings.temperature
    )
    
    # Special case: very short queries with a file mention are usually asking "what is this"
    if doc_name_filter and len(query.strip()) < 10:
        is_summarize = True
        
    if is_summarize and doc_name_filter:
        logger.info(f"Summarization intent detected for {doc_name_filter}. Retrieving all chunks.")
        search_results = chat_service.retrieve_all_document_chunks(doc_name_filter, query=query)
    else:
        search_results = chat_service.retrieve_relevant_documents(query, session_id=session_id, doc_name=doc_name_filter)
    
    if not search_results:
        async def mock_stream():
            msg = "The provided documents do not contain information regarding this query."
            if doc_name_filter:
                # If we had a doc filter but found nothing, it means the relevance was too low
                msg = f"I couldn't find relevant information in '{doc_name_filter}' for that specific query. Please try asking a more specific question about its contents."
            yield "data: " + json.dumps({"type": "chunk", "content": msg}) + "\n\n"
        return StreamingResponse(mock_stream(), media_type="text/event-stream")

    # Build RAG prompt
    if is_summarize and doc_name_filter:
        prompt = chat_service.build_summary_rag_prompt(query, doc_name_filter, search_results)
    else:
        prompt = chat_service.build_rag_prompt(query, search_results)

    # Format citations for the frontend
    citations = chat_service.format_citations(search_results)

    # Convert history
    history_dicts = [{"role": h.role, "content": h.content} for h in history]

    async def generate():
        # 1. Send citations immediately
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"
        
        # 2. Stream generation from generator.py
        async for chunk in chat_service.generate_answer_stream(prompt, history=history_dicts):
            if chunk:
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        
        # 3. Send done signal
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session's documents from the vector store and disk."""
    import os
    import shutil
    from config import PDF_DIR, INDEX_PATH, METADATA_PATH

    # Ensure services are initialized
    if vector_store is None:
        initialize_services()

    # Remove from FAISS index
    if vector_store:
        if vector_store.remove_session(session_id):
            vector_store.save(INDEX_PATH, METADATA_PATH)

    # Remove the session directory from the file system
    session_dir = os.path.join(PDF_DIR, session_id)
    if os.path.exists(session_dir):
        try:
            shutil.rmtree(session_dir)
            logger.info(f"Deleted session directory: {session_dir}")
        except Exception as e:
            logger.error(f"Failed to delete session directory {session_dir}: {e}")

    return {"message": f"Deleted session {session_id}."}

@router.post("/export")
async def export_report(request: ExportRequest):
    """Export chat conversation as markdown report"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"# FinChat Institutional Intelligence Report\n"
    report += f"**Subject:** {request.title}\n"
    report += f"**Generated:** {timestamp}\n"
    report += f"---\n\n"
    
    for msg in request.messages:
        role = "ANALYST" if msg['role'] == 'user' else "FINCHAT AI"
        content = msg['html'].replace('<p>', '').replace('</p>', '\n\n').replace('<br>', '\n')
        # Clean up citation spans if they were saved in HTML
        import re
        content = re.sub(r'<span.*?>\[S(\d+)\]</span>', r'[Source \1]', content)
        report += f"### {role}\n{content.strip()}\n\n"
        
    report += f"---\n*FinChat Analyst Protocol • v2.6.3*"
    
    filename = f"analysis_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    file_path = f"/tmp/{filename}"
    with open(file_path, "w") as f:
        f.write(report)
        
    return FileResponse(file_path, media_type="text/markdown", filename=filename)
