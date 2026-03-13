import faiss
import numpy as np
import pickle
import os
from rank_bm25 import BM25Okapi


class VectorStore:
    def __init__(self, dim):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.metadata = []
        self.bm25 = None
        self.corpus_tokens = []

    def _tokenize(self, text):
        return text.lower().split()

    def add(self, embeddings, metadata_list):
        embeddings = np.array(embeddings).astype("float32")
        faiss.normalize_L2(embeddings)

        self.index.add(embeddings)
        self.metadata.extend(metadata_list)
        
        # Update BM25
        self.corpus_tokens = [self._tokenize(m["text"]) for m in self.metadata]
        self.bm25 = BM25Okapi(self.corpus_tokens)

    def search_semantic(self, query_embedding, k=5, threshold=0.0):
        query_embedding = np.array([query_embedding]).astype("float32")
        faiss.normalize_L2(query_embedding)

        scores, indices = self.index.search(query_embedding, k)
        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or score < threshold:
                continue

            item = self.metadata[idx].copy()
            item["score"] = float(score)
            item["search_type"] = "semantic"
            results.append(item)

        return results

    def search_bm25(self, query, k=5):
        if not self.bm25:
            return []
            
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        top_n = np.argsort(scores)[::-1][:k]
        
        results = []
        for idx in top_n:
            if scores[idx] <= 0:
                continue
            item = self.metadata[idx].copy()
            item["score"] = float(scores[idx])
            item["search_type"] = "bm25"
            results.append(item)
            
        return results

    def search_hybrid(self, query, query_embedding, k=10, semantic_weight=0.7):
        """
        Combine BM25 and Semantic search.
        Since reranking will follow, we return a merged list.
        """
        semantic_results = self.search_semantic(query_embedding, k=k)
        keyword_results = self.search_bm25(query, k=k)
        
        # Use a dict to deduplicate results by chunk_id
        merged = {}
        
        for r in semantic_results:
            merged[r["chunk_id"]] = r
            
        for r in keyword_results:
            if r["chunk_id"] not in merged:
                merged[r["chunk_id"]] = r
            else:
                # If already present, slightly boost score or just keep it
                merged[r["chunk_id"]]["score"] += 0.1 
                
        return list(merged.values())

    def save(self, index_path, metadata_path):
        faiss.write_index(self.index, index_path)

        with open(metadata_path, "wb") as f:
            pickle.dump({
                "metadata": self.metadata,
                "corpus_tokens": self.corpus_tokens
            }, f)

    def load(self, index_path, metadata_path):
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            return False

        self.index = faiss.read_index(index_path)

        with open(metadata_path, "rb") as f:
            data = pickle.load(f)
            self.metadata = data["metadata"]
            self.corpus_tokens = data.get("corpus_tokens", [])
            
        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)

        return True