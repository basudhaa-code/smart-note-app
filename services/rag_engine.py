import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class RAGEngine:
    def __init__(self):
        # Cache per document: { doc_id: { "vectorizer": TfidfVectorizer, "matrix": matrix, "chunks": chunks } }
        self._indices: Dict[str, Dict[str, Any]] = {}

    def index_document(self, doc_id: str, chunks: List[Dict[str, Any]]) -> None:
        """
        Indexes chunks of a document for semantic & lexical retrieval.
        """
        if not chunks:
            return

        texts = [chunk["text"] for chunk in chunks]
        
        # Sublinear tf scaling helps prevent repetitive words from dominating
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
            max_features=5000
        )
        
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
            self._indices[doc_id] = {
                "vectorizer": vectorizer,
                "matrix": tfidf_matrix,
                "chunks": chunks
            }
        except Exception as e:
            print(f"[RAGEngine] Failed to index doc {doc_id}: {e}")
            self._indices[doc_id] = {
                "vectorizer": None,
                "matrix": None,
                "chunks": chunks
            }

    def search(self, doc_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves the top-k most relevant chunks for a given query.
        """
        index_data = self._indices.get(doc_id)
        if not index_data:
            return []

        chunks = index_data["chunks"]
        vectorizer = index_data["vectorizer"]
        matrix = index_data["matrix"]

        if vectorizer is None or matrix is None or len(chunks) == 0:
            return chunks[:top_k]

        try:
            query_vec = vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, matrix).flatten()
            
            # Rank chunks
            ranked_indices = np.argsort(similarities)[::-1]
            
            results = []
            for idx in ranked_indices[:top_k]:
                score = float(similarities[idx])
                chunk_copy = dict(chunks[idx])
                chunk_copy["score"] = round(score, 4)
                results.append(chunk_copy)
                
            return results
        except Exception as e:
            print(f"[RAGEngine] Search error for doc {doc_id}: {e}")
            return chunks[:top_k]

    def build_context_prompt(self, relevant_chunks: List[Dict[str, Any]]) -> str:
        """
        Builds a structured prompt context block from retrieved chunks with explicit page tags.
        """
        if not relevant_chunks:
            return "No relevant excerpts found."

        context_blocks = []
        for i, chunk in enumerate(relevant_chunks, 1):
            page_num = chunk.get("page_num", "Unknown")
            text = chunk.get("text", "").strip()
            context_blocks.append(f"[Source Excerpt {i} | Page {page_num}]:\n{text}")

        return "\n\n".join(context_blocks)

# Global singleton
rag_engine = RAGEngine()
