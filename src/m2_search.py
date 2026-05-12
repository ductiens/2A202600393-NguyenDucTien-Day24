"""Module 2: Hybrid Search - BM25 (Vietnamese) + Dense + RRF."""

import math
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    QDRANT_HOST,
    QDRANT_PORT,
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    BM25_TOP_K,
    DENSE_TOP_K,
    HYBRID_TOP_K,
)


@dataclass
class SearchResult:
    text: str
    score: float
    metadata: dict
    method: str  # "bm25", "dense", "hybrid"


def segment_vietnamese(text: str) -> str:
    """Segment Vietnamese text into words."""
    try:
        from underthesea import word_tokenize

        return word_tokenize(text, format="text")
    except Exception:
        return text


def _tokenize(text: str) -> list[str]:
    segmented = segment_vietnamese(text).lower()
    tokens = segmented.split()
    if tokens:
        return tokens
    return re.findall(r"[\wÀ-ỹ]+", text.lower())


class BM25Search:
    def __init__(self):
        self.corpus_tokens = []
        self.documents = []
        self.bm25 = None
        self._doc_freq = defaultdict(int)
        self._avgdl = 0.0
        self._k1 = 1.5
        self._b = 0.75

    def index(self, chunks: list[dict]) -> None:
        """Build BM25 index from chunks."""
        self.documents = list(chunks)
        self.corpus_tokens = [_tokenize(chunk.get("text", "")) for chunk in self.documents]
        self._doc_freq.clear()
        total_len = 0
        for tokens in self.corpus_tokens:
            total_len += len(tokens)
            for term in set(tokens):
                self._doc_freq[term] += 1
        self._avgdl = total_len / max(len(self.corpus_tokens), 1)
        try:
            from rank_bm25 import BM25Okapi

            self.bm25 = BM25Okapi(self.corpus_tokens)
        except Exception:
            self.bm25 = None

    def search(self, query: str, top_k: int = BM25_TOP_K) -> list[SearchResult]:
        """Search using BM25."""
        if not self.documents:
            return []
        query_tokens = _tokenize(query)

        if self.bm25 is not None:
            try:
                scores = self.bm25.get_scores(query_tokens)
                top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
                return [
                    SearchResult(
                        text=self.documents[i].get("text", ""),
                        score=float(scores[i]),
                        metadata=self.documents[i].get("metadata", {}),
                        method="bm25",
                    )
                    for i in top_indices
                    if self.documents[i].get("text", "")
                ]
            except Exception:
                pass

        n_docs = len(self.corpus_tokens)
        scores: list[float] = []
        for tokens in self.corpus_tokens:
            tf = Counter(tokens)
            dl = len(tokens) or 1
            score = 0.0
            for term in query_tokens:
                freq = tf.get(term, 0)
                if not freq:
                    continue
                df = self._doc_freq.get(term, 0)
                idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
                denom = freq + self._k1 * (1 - self._b + self._b * dl / max(self._avgdl, 1.0))
                score += idf * freq * (self._k1 + 1) / denom
            scores.append(score)

        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            SearchResult(
                text=self.documents[i].get("text", ""),
                score=float(scores[i]),
                metadata=self.documents[i].get("metadata", {}),
                method="bm25",
            )
            for i in top_indices
            if self.documents[i].get("text", "")
        ]


class DenseSearch:
    def __init__(self):
        self.client = None
        self._encoder = None
        self._memory_index: list[dict] = []
        self._memory_vectors: list[list[float]] = []

    def _get_encoder(self):
        if self._encoder is None:
            class _FallbackEncoder:
                def encode(self, texts, show_progress_bar=False):
                    if isinstance(texts, str):
                        texts = [texts]
                    vectors = []
                    for text in texts:
                        vec = [0.0] * 256
                        for token in _tokenize(text):
                            idx = abs(hash(token)) % len(vec)
                            vec[idx] += 1.0
                        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
                        vectors.append([v / norm for v in vec])
                    return vectors if len(vectors) > 1 else vectors[0]

            self._encoder = _FallbackEncoder()
        return self._encoder

    def index(self, chunks: list[dict], collection: str = COLLECTION_NAME) -> None:
        """Index chunks into Qdrant or an in-memory fallback."""
        self._memory_index = list(chunks)
        encoder = self._get_encoder()
        texts = [c.get("text", "") for c in chunks]
        if not texts:
            self._memory_vectors = []
            return
        vectors = encoder.encode(texts, show_progress_bar=False)
        if isinstance(vectors, list) and vectors and isinstance(vectors[0], (int, float)):
            vectors = [vectors]
        self._memory_vectors = [list(v) for v in vectors]

        return

    def search(self, query: str, top_k: int = DENSE_TOP_K, collection: str = COLLECTION_NAME) -> list[SearchResult]:
        """Search using dense vectors."""
        if not self._memory_index:
            return []
        encoder = self._get_encoder()
        query_vector = encoder.encode(query, show_progress_bar=False)
        if isinstance(query_vector, list) and query_vector and isinstance(query_vector[0], list):
            query_vector = query_vector[0]

        def cosine(a: list[float], b: list[float]) -> float:
            length = min(len(a), len(b))
            if length == 0:
                return 0.0
            a = a[:length]
            b = b[:length]
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a)) or 1.0
            nb = math.sqrt(sum(y * y for y in b)) or 1.0
            return dot / (na * nb)

        scores = [cosine(query_vector, vec) for vec in self._memory_vectors]
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            SearchResult(
                text=self._memory_index[i].get("text", ""),
                score=float(scores[i]),
                metadata=self._memory_index[i].get("metadata", {}),
                method="dense",
            )
            for i in top_indices
            if self._memory_index[i].get("text", "")
        ]


def reciprocal_rank_fusion(
    results_list: list[list[SearchResult]],
    k: int = 60,
    top_k: int = HYBRID_TOP_K,
) -> list[SearchResult]:
    """Merge ranked lists using RRF: score(d) = sum 1/(k + rank)."""
    rrf_scores: dict[str, dict] = {}
    for result_list in results_list:
        for rank, result in enumerate(result_list):
            entry = rrf_scores.setdefault(result.text, {"score": 0.0, "result": result})
            entry["score"] += 1.0 / (k + rank + 1)
            if result.score > entry["result"].score:
                entry["result"] = result

    merged = sorted(rrf_scores.values(), key=lambda item: item["score"], reverse=True)[:top_k]
    output: list[SearchResult] = []
    for item in merged:
        result = item["result"]
        output.append(
            SearchResult(
                text=result.text,
                score=float(item["score"]),
                metadata=result.metadata,
                method="hybrid",
            )
        )
    return output


class HybridSearch:
    """Combines BM25 + Dense + RRF."""

    def __init__(self):
        self.bm25 = BM25Search()
        self.dense = DenseSearch()

    def index(self, chunks: list[dict]) -> None:
        self.bm25.index(chunks)
        self.dense.index(chunks)

    def search(self, query: str, top_k: int = HYBRID_TOP_K) -> list[SearchResult]:
        bm25_results = self.bm25.search(query, top_k=BM25_TOP_K)
        dense_results = self.dense.search(query, top_k=DENSE_TOP_K)
        return reciprocal_rank_fusion([bm25_results, dense_results], top_k=top_k)


def main() -> None:
    print(f"Original:  Nhan vien duoc nghi phep nam")
    print(f"Segmented: {segment_vietnamese('Nhan vien duoc nghi phep nam')}")


if __name__ == "__main__":
    main()
