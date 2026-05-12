"""Shared helpers for production release pipelines."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_TEST_DATA_PATH = ROOT_DIR / "data" / "test_data.json"
DEFAULT_FALLBACK_SET_PATH = ROOT_DIR / "test_set.json"
DEFAULT_HUMAN_LABEL_PATH = ROOT_DIR / "data" / "human_labels.json"


def _normalize_item(raw: dict[str, Any], idx: int) -> dict[str, Any]:
    question = str(raw.get("question", "")).strip()
    ground_truth = str(raw.get("ground_truth", "")).strip()
    answer = str(raw.get("answer", "")).strip() or ground_truth
    contexts = raw.get("retrieved_contexts", raw.get("contexts", []))
    if not isinstance(contexts, list):
        contexts = [str(contexts)]
    contexts = [str(c).strip() for c in contexts if str(c).strip()]
    if not contexts and ground_truth:
        contexts = [ground_truth]

    candidate_a = str(raw.get("candidate_a", answer)).strip() or answer
    candidate_b = str(raw.get("candidate_b", ground_truth)).strip() or ground_truth
    human_preference = str(raw.get("human_preference", "")).upper().strip()
    if human_preference not in {"A", "B", "TIE"}:
        human_preference = "TIE"

    return {
        "id": str(raw.get("id", f"sample_{idx}")),
        "question": question,
        "ground_truth": ground_truth,
        "retrieved_contexts": contexts,
        "answer": answer,
        "candidate_a": candidate_a,
        "candidate_b": candidate_b,
        "human_preference": human_preference,
    }


def _load_json(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array.")
    if not payload:
        raise ValueError(f"{path} is empty.")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError(f"{path} must contain array[object].")
    return payload


def load_test_data(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load normalized test records for all production phases."""
    target = Path(path) if path else DEFAULT_TEST_DATA_PATH
    if target.exists():
        data = _load_json(target)
        return [_normalize_item(item, idx) for idx, item in enumerate(data, start=1)]

    # Fallback for older repos that only have test_set.json.
    fallback = _load_json(DEFAULT_FALLBACK_SET_PATH)
    normalized = []
    for idx, item in enumerate(fallback, start=1):
        question = str(item.get("question", "")).strip()
        ground_truth = str(item.get("ground_truth", "")).strip()
        normalized.append(
            {
                "id": f"fallback_{idx}",
                "question": question,
                "ground_truth": ground_truth,
                "retrieved_contexts": [ground_truth] if ground_truth else [],
                "answer": ground_truth,
                "candidate_a": ground_truth,
                "candidate_b": "Khong co thong tin.",
                "human_preference": "A",
            }
        )
    return normalized


def load_human_labels(path: str | Path | None = None) -> dict[str, str]:
    """Return a map sample_id -> human preference label (A/B/TIE)."""
    target = Path(path) if path else DEFAULT_HUMAN_LABEL_PATH
    if not target.exists():
        return {}

    raw = _load_json(target)
    labels: dict[str, str] = {}
    for row in raw:
        sample_id = str(row.get("id", "")).strip()
        label = str(row.get("human_preference", "")).upper().strip()
        if sample_id and label in {"A", "B", "TIE"}:
            labels[sample_id] = label
    return labels

