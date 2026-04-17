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

    def _rebuild_bm25(self):
        if self.metadata:
            self.corpus_tokens = [self._tokenize(m["text"]) for m in self.metadata]
            self.bm25 = BM25Okapi(self.corpus_tokens)
        else:
            self.corpus_tokens = []
            self.bm25 = None

    def _remove_indices(self, indices_to_remove):
        if not indices_to_remove:
            return False

        indices = sorted(set(indices_to_remove))
        sel = faiss.IDSelectorBatch(np.array(indices, dtype="int64"))
        self.index.remove_ids(sel)

        removed = set(indices)
        self.metadata = [m for i, m in enumerate(self.metadata) if i not in removed]
        self._rebuild_bm25()
        return True

    def _tokenize(self, text):
        return text.lower().split()

    def add(self, embeddings, metadata_list):
        embeddings = np.array(embeddings).astype("float32")
        faiss.normalize_L2(embeddings)

        self.index.add(embeddings)
        self.metadata.extend(metadata_list)
        
        # Update BM25
        self._rebuild_bm25()

    def remove_document(self, doc_name):
        """Removes all chunks associated with a specific document from the index and metadata."""
        indices_to_remove = [i for i, m in enumerate(self.metadata) if m.get("doc_name") == doc_name]
        return self._remove_indices(indices_to_remove)

    def remove_session(self, session_id):
        """Removes all chunks associated with a specific session_id from the index and metadata."""
        indices_to_remove = [i for i, m in enumerate(self.metadata) if m.get("session_id") == session_id]
        return self._remove_indices(indices_to_remove)

    def prune_missing_documents(self, existing_doc_names):
        """Remove any documents that are no longer present on disk."""
        existing_doc_names = set(existing_doc_names)
        stale_doc_names = {
            m.get("doc_name") for m in self.metadata
            if m.get("doc_name") not in existing_doc_names
        }

        if not stale_doc_names:
            return []

        indices_to_remove = [
            i for i, m in enumerate(self.metadata)
            if m.get("doc_name") in stale_doc_names
        ]
        if self._remove_indices(indices_to_remove):
            return sorted(stale_doc_names)
        return []

    def clear(self):
        """Reset the store to an empty index."""
        self.index = faiss.IndexFlatIP(self.dim)
        self.metadata = []
        self._rebuild_bm25()

    def search_semantic(self, query_embedding, k=5, threshold=0.0, session_id=None, doc_name=None):
        query_embedding = np.array([query_embedding]).astype("float32")
        faiss.normalize_L2(query_embedding)

        # Search more results initially to allow for filtering
        search_k = k * 10 if (session_id or doc_name) else k
        scores, indices = self.index.search(query_embedding, search_k)
        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or score < threshold:
                continue
                
            item = self.metadata[idx].copy()
            item_session = item.get("session_id")
            
            # Filter logic: include if item is global (None) or belongs to current session
            if session_id and item_session and item_session != session_id:
                continue
                
            # Filter logic: doc_name match
            if doc_name and item.get("doc_name") != doc_name:
                continue

            item["score"] = float(score)
            item["search_type"] = "semantic"
            results.append(item)
            
            if len(results) >= k:
                break

        return results

    def search_bm25(self, query, k=5, session_id=None, doc_name=None):
        if not self.bm25:
            return []
            
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        top_n = np.argsort(scores)[::-1]
        
        results = []
        for idx in top_n:
            if scores[idx] <= 0:
                continue
                
            item = self.metadata[idx].copy()
            item_session = item.get("session_id")
            
            # Filter logic
            if session_id and item_session and item_session != session_id:
                continue
                
            # Filter logic: doc_name match
            if doc_name and item.get("doc_name") != doc_name:
                continue
                
            item["score"] = float(scores[idx])
            item["search_type"] = "bm25"
            results.append(item)
            
            if len(results) >= k:
                break
            
        return results

    def search_hybrid(self, query, query_embedding, k=10, semantic_weight=0.7, session_id=None, doc_name=None):
        """
        Combine BM25 and Semantic search.
        Since reranking will follow, we return a merged list.
        """
        semantic_results = self.search_semantic(query_embedding, k=k, session_id=session_id, doc_name=doc_name)
        keyword_results = self.search_bm25(query, k=k, session_id=session_id, doc_name=doc_name)
        
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
        faiss.write_index(self.index, str(index_path))

        with open(str(metadata_path), "wb") as f:
            pickle.dump({
                "metadata": self.metadata,
                "corpus_tokens": self.corpus_tokens
            }, f)

    def load(self, index_path, metadata_path):
        if not os.path.exists(str(index_path)) or not os.path.exists(str(metadata_path)):
            return False

        self.index = faiss.read_index(str(index_path))

        with open(str(metadata_path), "rb") as f:
            data = pickle.load(f)
            self.metadata = data["metadata"]
            self.corpus_tokens = data.get("corpus_tokens", [])
            
        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)

        return True
