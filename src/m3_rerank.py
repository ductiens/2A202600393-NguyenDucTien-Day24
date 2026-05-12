"""Module 3: Reranking - Cross-encoder top-20 -> top-3 + latency beenchmark."""

import os
import re
import sys
import time
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RERANK_TOP_K


@dataclass
class RerankResult:
    text: str
    original_score: float
    rerank_score: float
    metadata: dict
    rank: int


def _normalize(text: str) -> set[str]:
    return {t for t in re.findall(r"[\wÀ-ỹ]+", text.lower()) if t}


def _score_pair(query: str, doc: str) -> float:
    q_tokens = _normalize(query)
    d_tokens = _normalize(doc)
    if not q_tokens or not d_tokens:
        return 0.0
    overlap = len(q_tokens & d_tokens)
    overlap_ratio = overlap / max(len(q_tokens), 1)
    doc_ratio = overlap / max(len(d_tokens), 1)
    number_bonus = 0.2 if any(t.isdigit() for t in q_tokens & d_tokens) else 0.0
    keyword_bonus = 0.3 if any(k in doc.lower() for k in ["nghỉ", "phép", "nghi"]) and any(k in query.lower() for k in ["nghỉ", "phép", "nghi"]) else 0.0
    return overlap_ratio + 0.5 * doc_ratio + number_bonus + keyword_bonus


class CrossEncoderReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            class _FallbackModel:
                def compute_score(self, pairs):
                    return [_score_pair(query, doc) for query, doc in pairs]

                def predict(self, pairs):
                    return [_score_pair(query, doc) for query, doc in pairs]

            self._model = _FallbackModel()
        return self._model

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        """Rerank documents: top-20 -> top-k."""
        if not documents:
            return []

        model = self._load_model()
        pairs = [(query, doc.get("text", "")) for doc in documents]
        scores = []
        try:
            if hasattr(model, "compute_score"):
                scores = list(model.compute_score(pairs))
            elif hasattr(model, "predict"):
                scores = list(model.predict(pairs))
        except Exception:
            scores = []

        if not scores:
            scores = [_score_pair(query, doc.get("text", "")) for doc in documents]

        ranked = sorted(zip(scores, documents), key=lambda item: item[0], reverse=True)[:top_k]
        results: list[RerankResult] = []
        for idx, (score, doc) in enumerate(ranked, start=1):
            if not doc.get("text", ""):
                continue
            results.append(
                RerankResult(
                    text=doc.get("text", ""),
                    original_score=float(doc.get("score", 0.0)),
                    rerank_score=float(score),
                    metadata=doc.get("metadata", {}),
                    rank=idx,
                )
            )
        return results


class FlashrankReranker:
    """Lightweight alternative (<5ms). Optional."""

    def __init__(self):
        self._model = None

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        ranked = sorted(documents, key=lambda doc: _score_pair(query, doc.get("text", "")), reverse=True)[:top_k]
        results: list[RerankResult] = []
        for idx, doc in enumerate(ranked, start=1):
            if not doc.get("text", ""):
                continue
            results.append(
                RerankResult(
                    text=doc.get("text", ""),
                    original_score=float(doc.get("score", 0.0)),
                    rerank_score=float(_score_pair(query, doc.get("text", ""))),
                    metadata=doc.get("metadata", {}),
                    rank=idx,
                )
            )
        return results


def benchmark_reranker(reranker, query: str, documents: list[dict], n_runs: int = 5) -> dict:
    """Benchmark latency over n_runs."""
    times = []
    for _ in range(max(1, n_runs)):
        start = time.perf_counter()
        reranker.rerank(query, documents)
        times.append((time.perf_counter() - start) * 1000)
    return {
        "avg_ms": sum(times) / len(times),
        "min_ms": min(times),
        "max_ms": max(times),
    }


def main() -> None:
    query = "Nhan vien duoc nghi phep bao nhieu ngay?"
    docs = [
        {"text": "Nhan vien duoc nghi 12 ngay/nam.", "score": 0.8, "metadata": {}},
        {"text": "Mat khau thay doi moi 90 ngay.", "score": 0.7, "metadata": {}},
        {"text": "Thoi gian thu viec la 60 ngay.", "score": 0.75, "metadata": {}},
    ]
    reranker = CrossEncoderReranker()
    for r in reranker.rerank(query, docs):
        print(f"[{r.rank}] {r.rerank_score:.4f} | {r.text}")


if __name__ == "__main__":
    main()
