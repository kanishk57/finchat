import os
import sys
import logging
from contextlib import contextmanager

# Suppress HuggingFace and Transformers verbose logging/warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TQDM_DISABLE"] = "1" # Disable TQDM progress bars globally

@contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(os.devnull, 'w') as fnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = fnull
        sys.stderr = fnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

import transformers
transformers.logging.set_verbosity_error()

from sentence_transformers import SentenceTransformer, CrossEncoder

# Global variables for models
model = None
reranker_model = None

def load_models():
    """
    Explicitly load the embedding and reranker models in silence.
    """
    global model, reranker_model
    with suppress_stdout_stderr():
        if model is None:
            model = SentenceTransformer("BAAI/bge-base-en-v1.5")
        if reranker_model is None:
            reranker_model = CrossEncoder("BAAI/bge-reranker-base")

def embed_passages(texts, batch_size=32):
    """
    Embed document chunks (passages) in batches.
    Automatically adds 'passage:' prefix for BGE model.
    """
    if model is None:
        load_models()
        
    formatted_texts = ["passage: " + text for text in texts]
    
    # Process in batches to prevent memory thrashing and improve speed
    all_embeddings = []
    for i in range(0, len(formatted_texts), batch_size):
        batch = formatted_texts[i:i + batch_size]
        batch_embeddings = model.encode(
            batch,
            normalize_embeddings=True,
            show_progress_bar=False,
            device='cuda' if transformers.is_torch_available() and __import__('torch').cuda.is_available() else 'cpu'
        )
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


def embed_query(query):
    """
    Embed user query.
    Automatically adds 'query:' prefix for BGE model.
    """
    if model is None:
        load_models()
        
    formatted_query = "query: " + query

    embedding = model.encode(
        [formatted_query],
        normalize_embeddings=True,
        show_progress_bar=False
    )[0]

    return embedding


def rerank_results(query, results, top_n=5):
    """
    Use Cross-Encoder to rerank initial retrieval results.
    """
    if reranker_model is None:
        load_models()
        
    if not results:
        return []

    # Prepare pairs for cross-encoder
    pairs = [[query, r["text"]] for r in results]
    
    # Get relevance scores
    scores = reranker_model.predict(pairs)
    
    # Add scores to results and sort
    for i, score in enumerate(scores):
        results[i]["rerank_score"] = float(score)
        
    # Sort by rerank_score descending
    sorted_results = sorted(results, key=lambda x: x["rerank_score"], reverse=True)
    
    return sorted_results[:top_n]
    """
    Use Cross-Encoder to rerank initial retrieval results.
    """
    if not results:
        return []

    # Prepare pairs for cross-encoder
    pairs = [[query, r["text"]] for r in results]
    
    # Get relevance scores
    scores = reranker_model.predict(pairs)
    
    # Add scores to results and sort
    for i, score in enumerate(scores):
        results[i]["rerank_score"] = float(score)
        
    # Sort by rerank_score descending
    sorted_results = sorted(results, key=lambda x: x["rerank_score"], reverse=True)
    
    return sorted_results[:top_n]