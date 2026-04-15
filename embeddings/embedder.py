import os

# Suppress HuggingFace and Transformers verbose logging/warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TQDM_DISABLE"] = "1" # Disable TQDM progress bars globally

import transformers
transformers.logging.set_verbosity_error()

# Import our model manager
from models.model_manager import get_embedding_model, get_reranker_model

def embed_passages(texts, batch_size=32, progress_callback=None):
    """
    Embed document chunks (passages) in batches.
    Automatically adds 'passage:' prefix for BGE model.
    """
    # Get model from manager
    model_instance = get_embedding_model()
    
    formatted_texts = ["passage: " + text for text in texts]
    total_texts = len(formatted_texts)
    
    # Process in batches to prevent memory thrashing and improve speed
    all_embeddings = []
    for i in range(0, total_texts, batch_size):
        batch = formatted_texts[i:i + batch_size]
        batch_embeddings = model_instance.encode(
            batch,
            normalize_embeddings=True,
            show_progress_bar=False,
            device='cuda' if transformers.is_torch_available() and __import__('torch').cuda.is_available() else 'cpu'
        )
        all_embeddings.extend(batch_embeddings)
        
        if progress_callback:
            progress_callback(min(i + batch_size, total_texts), total_texts)

    return all_embeddings


def embed_query(query):
    """
    Embed user query.
    Automatically adds 'query:' prefix for BGE model.
    """
    # Get model from manager
    model_instance = get_embedding_model()
    
    formatted_query = "query: " + query

    embedding = model_instance.encode(
        [formatted_query],
        normalize_embeddings=True,
        show_progress_bar=False
    )[0]

    return embedding


def rerank_results(query, results, top_n=5):
    """
    Use Cross-Encoder to rerank initial retrieval results.
    """
    import numpy as np
    
    # Get reranker model from manager
    reranker_model_instance = get_reranker_model()
    
    if not results:
        return []
    
    # Prepare pairs for cross-encoder
    pairs = [[query, r["text"]] for r in results]
    
    # Get relevance scores
    scores = reranker_model_instance.predict(pairs)
    
    # Sigmoid function to normalize scores to [0, 1]
    def sigmoid(x):
        return 1 / (1 + np.exp(-x))
    
    # Add scores to results and sort
    for i, score in enumerate(scores):
        results[i]["rerank_score"] = float(sigmoid(score))
        
    # Sort by rerank_score descending
    sorted_results = sorted(results, key=lambda x: x["rerank_score"], reverse=True)
    
    return sorted_results[:top_n]
