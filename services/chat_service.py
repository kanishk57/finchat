"""
Chat Service Layer
Contains business logic for chat operations, separated from API concerns
"""

from typing import List, Dict, Any, AsyncGenerator
import json
import asyncio
import logging

from core.initialization import build_prompt
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
    
    def retrieve_all_document_chunks(self, doc_name: str) -> List[SearchResult]:
        """
        Retrieve all chunks for a specific document (used for summarization).
        If document is large, sample chunks to provide a representative overview.
        """
        logger.info(f"Retrieving chunks for document: {doc_name}")
        
        all_chunks = [
            m for m in self.vector_store.metadata 
            if m.get("doc_name") == doc_name
        ]
        
        # Limit to 50 chunks to avoid overwhelming the LLM
        # If document is longer, sample from start, middle, and end
        limit = 50
        if len(all_chunks) > limit:
            logger.info(f"Document {doc_name} has {len(all_chunks)} chunks. Sampling {limit} chunks for summarization.")
            
            # Take first 20 (Intro/Table of contents)
            # Take middle 15 (Financials/Operations)
            # Take last 15 (Risk/Footnotes)
            start_chunks = all_chunks[:20]
            
            middle_start = len(all_chunks) // 2 - 7
            middle_chunks = all_chunks[middle_start:middle_start + 15]
            
            end_chunks = all_chunks[-15:]
            
            # Combine and deduplicate just in case (though unlikely with these ranges)
            sampled_chunks = start_chunks + middle_chunks + end_chunks
            
            # Deduplicate by chunk_id
            seen_ids = set()
            all_chunks = []
            for chunk in sampled_chunks:
                if chunk["chunk_id"] not in seen_ids:
                    all_chunks.append(chunk)
                    seen_ids.add(chunk["chunk_id"])
        
        # Convert to SearchResult objects
        search_results = []
        for res in all_chunks:
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
        for i, result in enumerate(search_results, 1):
            citations.append({
                "ref": i,
                "doc_name": result.doc_name,
                "doc_date": result.doc_date or 'N/A',
                "page": result.page_number,
                "text": result.text,
                "relevance": round(result.rerank_score or 0, 4)
            })
        return citations