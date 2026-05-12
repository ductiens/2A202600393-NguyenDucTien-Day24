"""Phase A: Automated RAGAS evaluation on test_data.json."""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from src.m4_eval import evaluate_ragas as heuristic_evaluate_ragas
from src.production.data_utils import ROOT_DIR, load_test_data

REPORT_PATH = ROOT_DIR / "reports" / "phase_a_ragas_report.json"


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _run_real_ragas(samples: list[dict[str, Any]]) -> dict[str, Any]:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.run_config import RunConfig

    try:
        from ragas.metrics import answer_relevancy
    except Exception:
        from ragas.metrics import answer_relevance as answer_relevancy
    from ragas.metrics import context_precision, context_recall, faithfulness

    dataset = Dataset.from_dict(
        {
            "question": [x["question"] for x in samples],
            "answer": [x["answer"] for x in samples],
            "contexts": [x["retrieved_contexts"] for x in samples],
            "ground_truth": [x["ground_truth"] for x in samples],
        }
    )

    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        run_config=RunConfig(timeout=25, max_retries=1, max_wait=3, max_workers=4),
        raise_exceptions=False,
        show_progress=False,
    )
    result_dict = result.to_dict() if hasattr(result, "to_dict") else dict(result)
    aggregate = {
        "faithfulness": _safe_float(result_dict.get("faithfulness")),
        "answer_relevancy": _safe_float(result_dict.get("answer_relevancy")),
        "context_precision": _safe_float(result_dict.get("context_precision")),
        "context_recall": _safe_float(result_dict.get("context_recall")),
    }
    if any(math.isnan(x) or x <= 0.0 for x in aggregate.values()):
        raise RuntimeError("RAGAS returned invalid/empty metric values.")

    per_question = []
    if hasattr(result, "to_pandas"):
        frame = result.to_pandas()
        for i, row in frame.iterrows():
            per_question.append(
                {
                    "id": samples[i]["id"],
                    "question": samples[i]["question"],
                    "faithfulness": _safe_float(row.get("faithfulness")),
                    "answer_relevancy": _safe_float(row.get("answer_relevancy")),
                    "context_precision": _safe_float(row.get("context_precision")),
                    "context_recall": _safe_float(row.get("context_recall")),
                }
            )
    return {"engine": "ragas", "aggregate": aggregate, "per_question": per_question}


def _run_fallback(samples: list[dict[str, Any]], reason: str) -> dict[str, Any]:
    scores = heuristic_evaluate_ragas(
        questions=[x["question"] for x in samples],
        answers=[x["answer"] for x in samples],
        contexts=[x["retrieved_contexts"] for x in samples],
        ground_truths=[x["ground_truth"] for x in samples],
    )
    per_question = []
    for item in scores.get("per_question", []):
        per_question.append(
            {
                "question": item.question,
                "faithfulness": item.faithfulness,
                "answer_relevancy": item.answer_relevancy,
                "context_precision": item.context_precision,
                "context_recall": item.context_recall,
            }
        )
    return {
        "engine": "heuristic_fallback",
        "fallback_reason": reason,
        "aggregate": {
            "faithfulness": _safe_float(scores.get("faithfulness")),
            "answer_relevancy": _safe_float(scores.get("answer_relevancy")),
            "context_precision": _safe_float(scores.get("context_precision")),
            "context_recall": _safe_float(scores.get("context_recall")),
        },
        "per_question": per_question,
    }


def run_phase_a(test_data_path: str | None = None) -> dict[str, Any]:
    samples = load_test_data(test_data_path)

    ragas_mode = os.getenv("RAGAS_MODE", "auto").strip().lower()
    if ragas_mode == "heuristic":
        result = _run_fallback(samples, reason="RAGAS_MODE=heuristic")
    else:
        try:
            result = _run_real_ragas(samples)
        except Exception as exc:
            result = _run_fallback(samples, reason=str(exc))

    aggregate = result["aggregate"]
    result["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    result["num_samples"] = len(samples)
    result["mean_score"] = mean(aggregate.values()) if aggregate else 0.0

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    result = run_phase_a()
    print("Phase A complete.")
    print(f"- Engine: {result['engine']}")
    print(f"- Samples: {result['num_samples']}")
    for metric, score in result["aggregate"].items():
        print(f"- {metric}: {score:.4f}")
    print(f"- Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
