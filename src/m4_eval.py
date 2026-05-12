"""Module 4: RAGAS Evaluation - 4 metrics + failure analysis."""

import json
import os
import re
import sys
from dataclasses import dataclass
from statistics import mean

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON."""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        fixed = raw.replace("\\n", "\n").replace(",\n]", "\n]")
        fixed = fixed.replace(",]", "]")
        return json.loads(fixed)


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[\wÀ-ỹ]+", text.lower()) if t}


def _jaccard(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _heuristic_eval(question: str, answer: str, contexts: list[str], ground_truth: str) -> EvalResult:
    context_text = " ".join(contexts)
    faithfulness = min(1.0, 0.4 + 0.6 * _jaccard(answer, context_text))
    answer_relevancy = _jaccard(question, answer)
    context_precision = sum(_jaccard(question, c) for c in contexts) / max(len(contexts), 1)
    context_recall = max(_jaccard(ground_truth, context_text), _jaccard(ground_truth, answer))
    return EvalResult(
        question=question,
        answer=answer,
        contexts=contexts,
        ground_truth=ground_truth,
        faithfulness=float(faithfulness),
        answer_relevancy=float(answer_relevancy),
        context_precision=float(context_precision),
        context_recall=float(context_recall),
    )


def evaluate_ragas(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
) -> dict:
    """Run heuristic evaluation with the same output shape as RAGAS."""
    per_question: list[EvalResult] = []
    for question, answer, ctxs, gt in zip(questions, answers, contexts, ground_truths):
        per_question.append(_heuristic_eval(question, answer, ctxs, gt))

    if not per_question:
        return {
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "per_question": [],
        }

    return {
        "faithfulness": float(mean(r.faithfulness for r in per_question)),
        "answer_relevancy": float(mean(r.answer_relevancy for r in per_question)),
        "context_precision": float(mean(r.context_precision for r in per_question)),
        "context_recall": float(mean(r.context_recall for r in per_question)),
        "per_question": per_question,
    }


def _diagnose(metric: str, score: float) -> tuple[str, str]:
    if metric == "faithfulness" and score < 0.85:
        return "LLM hallucinating", "Tighten prompt, lower temperature"
    if metric == "context_recall" and score < 0.75:
        return "Missing relevant chunks", "Improve chunking or add BM25"
    if metric == "context_precision" and score < 0.75:
        return "Too many irrelevant chunks", "Add reranking or metadata filter"
    if metric == "answer_relevancy" and score < 0.80:
        return "Answer does not match question", "Improve prompt template"
    return "General retrieval failure", "Inspect chunking, search, and generation"


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    scored = []
    for result in eval_results:
        avg_score = mean(
            [
                result.faithfulness,
                result.answer_relevancy,
                result.context_precision,
                result.context_recall,
            ]
        )
        scored.append((avg_score, result))

    scored.sort(key=lambda item: item[0])
    failures = []
    for _, result in scored[:bottom_n]:
        metrics = {
            "faithfulness": result.faithfulness,
            "answer_relevancy": result.answer_relevancy,
            "context_precision": result.context_precision,
            "context_recall": result.context_recall,
        }
        worst_metric = min(metrics, key=metrics.get)
        score = metrics[worst_metric]
        diagnosis, fix = _diagnose(worst_metric, score)
        failures.append(
            {
                "question": result.question,
                "worst_metric": worst_metric,
                "score": float(score),
                "diagnosis": diagnosis,
                "suggested_fix": fix,
            }
        )
    return failures


def save_report(results: dict, failures: list[dict], path: str = "ragas_report.json"):
    """Save evaluation report to JSON."""
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


def main() -> None:
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")


if __name__ == "__main__":
    main()
