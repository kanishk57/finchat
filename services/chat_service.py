"""
Chat Service Layer
Contains business logic for chat operations, separated from API concerns
"""

from typing import List, Dict, Any, AsyncGenerator
import json
import asyncio
import logging
import re

from core.initialization import build_prompt, build_summary_prompt
from embeddings.embedder import embed_query, rerank_results
from vector_store.faiss_index import VectorStore
from llm.generator import generate_answer
from models.search_result import SearchResult
from config import (
    INITIAL_K as CONFIG_INITIAL_K,
    FINAL_TOP_K as CONFIG_TOP_K,
    DEFAULT_THRESHOLD, DEFAULT_TEMPERATURE
)

logger = logging.getLogger(__name__)

SUMMARY_PAGE_LIMIT = 12
SUMMARY_TOTAL_LIMIT = 16
SUMMARY_STOPWORDS = {
    "about", "this", "that", "with", "from", "what", "file", "document",
    "summarize", "summarise", "summary", "please", "there", "their", "would",
    "could", "should", "into", "across", "under", "have", "has", "had"
}


class ChatService:
    """Service class handling chat-related business logic"""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.settings = {
            "top_k": CONFIG_TOP_K,
            "threshold": DEFAULT_THRESHOLD,
            "temperature": DEFAULT_TEMPERATURE
        }
    
    def update_settings(self, top_k: int = None, threshold: float = None, temperature: float = None):
        """Update service settings"""
        if top_k is not None:
            self.settings["top_k"] = top_k
        if threshold is not None:
            self.settings["threshold"] = threshold
        if temperature is not None:
            self.settings["temperature"] = temperature
        logger.info(f"Updated chat service settings: {self.settings}")
    
    def retrieve_relevant_documents(self, query: str, session_id: str = None, doc_name: str = None) -> List[SearchResult]:
        """
        Retrieve and rank relevant documents for a query
        
        Args:
            query: User query string
            session_id: Optional session ID for subuploads
            doc_name: Optional document name filter
            
        Returns:
            List of SearchResult objects
        """
        logger.info(f"Retrieving documents for query: {query[:50]}... (Filter: {doc_name})")
        
        # Generate query embedding
        query_embedding = embed_query(query)
        
        # Initial hybrid retrieval
        initial_results = self.vector_store.search_hybrid(
            query, query_embedding, k=CONFIG_INITIAL_K, session_id=session_id, doc_name=doc_name
        )
        
        if not initial_results:
            logger.warning("No initial results found")
            return []
        
        # Rerank results
        final_results = rerank_results(
            query, initial_results, top_n=self.settings["top_k"]
        )
        
        # Apply threshold filter - use lower threshold if doc_name is specified
        effective_threshold = self.settings["threshold"]
        if doc_name:
            # If user explicitly mentioned a file, they are more likely to accept 
            # less "confident" matches for vague queries (like 'what is this about')
            effective_threshold = min(effective_threshold, 0.01)
            
        filtered_results = [
            res for res in final_results 
            if res.get('rerank_score', 0) >= effective_threshold
        ]
        
        logger.info(f"Retrieved {len(filtered_results)} relevant documents after filtering")
        
        # Convert to SearchResult objects
        search_results = []
        for i, res in enumerate(filtered_results, 1):
            search_results.append(SearchResult(
                doc_name=res['doc_name'],
                doc_date=res.get('doc_date'),
                page_number=res['page_number'],
                chunk_id=res['chunk_id'],
                text=res['text'],
                score=res.get('score'),
                search_type=res.get('search_type'),
                rerank_score=res.get('rerank_score')
            ))
        
        return search_results
    
    def _normalize_summary_text(self, text: str) -> str:
        text = re.sub(r'^\[Document:.*?\]\s*', '', text or '')
        text = re.sub(r'\s+', ' ', text).strip().lower()
        return text

    def _sample_evenly(self, items: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        if len(items) <= limit:
            return items
        if limit <= 1:
            return items[:1]

        selected = []
        seen = set()
        for i in range(limit):
            idx = round(i * (len(items) - 1) / (limit - 1))
            chunk_id = items[idx]["chunk_id"]
            if chunk_id in seen:
                continue
            selected.append(items[idx])
            seen.add(chunk_id)
        return selected

    def retrieve_all_document_chunks(self, doc_name: str, query: str = None) -> List[SearchResult]:
        """
        Retrieve representative chunks for a specific document (used for summarization).
        Uses one primary chunk per page plus a few keyword-matching chunks to avoid
        feeding heavily overlapping excerpts into the LLM.
        """
        logger.info(f"Retrieving chunks for document: {doc_name}")

        all_chunks = sorted([
            m for m in self.vector_store.metadata 
            if m.get("doc_name") == doc_name
        ], key=lambda item: (item.get("page_number", 0), item.get("chunk_id", "")))

        if not all_chunks:
            return []

        unique_page_chunks = []
        seen_pages = set()
        seen_texts = set()
        for chunk in all_chunks:
            page_number = chunk.get("page_number")
            normalized = self._normalize_summary_text(chunk.get("text", ""))
            if page_number in seen_pages or normalized in seen_texts:
                continue
            unique_page_chunks.append(chunk)
            seen_pages.add(page_number)
            seen_texts.add(normalized)

        selected_chunks = self._sample_evenly(unique_page_chunks, SUMMARY_PAGE_LIMIT)

        query_terms = []
        if query:
            query_terms = [
                term for term in re.findall(r'[a-zA-Z]{4,}', query.lower())
                if term not in SUMMARY_STOPWORDS
            ]

        if query_terms and len(selected_chunks) < SUMMARY_TOTAL_LIMIT:
            selected_ids = {chunk["chunk_id"] for chunk in selected_chunks}
            for chunk in all_chunks:
                if chunk["chunk_id"] in selected_ids:
                    continue
                normalized = self._normalize_summary_text(chunk.get("text", ""))
                if any(term in normalized for term in query_terms):
                    selected_chunks.append(chunk)
                    selected_ids.add(chunk["chunk_id"])
                if len(selected_chunks) >= SUMMARY_TOTAL_LIMIT:
                    break

        # Convert to SearchResult objects
        search_results = []
        for res in selected_chunks:
            search_results.append(SearchResult(
                doc_name=res['doc_name'],
                doc_date=res.get('doc_date'),
                page_number=res['page_number'],
                chunk_id=res['chunk_id'],
                text=res['text'],
                score=1.0,
                search_type="all_chunks",
                rerank_score=1.0
            ))
            
        return search_results

    def build_rag_prompt(self, query: str, search_results: List[SearchResult]) -> str:
        """
        Build RAG prompt from query and search results
        
        Args:
            query: User query
            search_results: List of relevant search results
            
        Returns:
            Formatted prompt string
        """
        # Convert SearchResult objects back to dict format for build_prompt
        results_dict = []
        for result in search_results:
            result_dict = {
                "doc_name": result.doc_name,
                "doc_date": result.doc_date,
                "page_number": result.page_number,
                "chunk_id": result.chunk_id,
                "text": result.text
            }
            # Add optional fields if present
            if result.score is not None:
                result_dict["score"] = result.score
            if result.search_type is not None:
                result_dict["search_type"] = result.search_type
            if result.rerank_score is not None:
                result_dict["rerank_score"] = result.rerank_score
                
            results_dict.append(result_dict)
        
        return build_prompt(query, results_dict)

    def build_summary_rag_prompt(self, query: str, doc_name: str, search_results: List[SearchResult]) -> str:
        """Build a stronger prompt for document summarization queries."""
        results_dict = []
        for result in search_results:
            result_dict = {
                "doc_name": result.doc_name,
                "doc_date": result.doc_date,
                "page_number": result.page_number,
                "chunk_id": result.chunk_id,
                "text": result.text
            }
            if result.score is not None:
                result_dict["score"] = result.score
            if result.search_type is not None:
                result_dict["search_type"] = result.search_type
            if result.rerank_score is not None:
                result_dict["rerank_score"] = result.rerank_score

            results_dict.append(result_dict)

        return build_summary_prompt(query, doc_name, results_dict)
    
    async def generate_answer_stream(
        self, 
        prompt: str, 
        temperature: float = None,
        history: list = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate answer stream from LLM
        
        Args:
            prompt: RAG prompt
            temperature: LLM temperature (uses service setting if not provided)
            history: Optional conversation history
            
        Yields:
            Chunks of generated text
        """
        temp = temperature if temperature is not None else self.settings["temperature"]
        
        logger.info(f"Generating answer stream with temperature: {temp}")
        
        # Import here to avoid circular imports
        from llm.generator import generate_answer
        
        for chunk in generate_answer(prompt, temperature=temp, history=history):
            if chunk:
                yield chunk
    
    def format_citations(self, search_results: List[SearchResult]) -> List[Dict[str, Any]]:
        """
        Format search results as citations for frontend
        
        Args:
            search_results: List of search results
            
        Returns:
            List of citation dictionaries
        """
        citations = []
        seen = set()
        for result in search_results:
            key = (result.doc_name, result.page_number)
            if key in seen:
                continue
            seen.add(key)
            citations.append({
                "ref": len(citations) + 1,
                "doc_name": result.doc_name,
                "doc_date": result.doc_date or 'N/A',
                "page": result.page_number,
                "text": result.text,
                "relevance": round(result.rerank_score or 0, 4)
            })
        return citations
