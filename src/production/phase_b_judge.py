"""Phase B: LLM-as-Judge with swap-and-average and Cohen's kappa calibration."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.production.data_utils import ROOT_DIR, load_human_labels, load_test_data

REPORT_PATH = ROOT_DIR / "reports" / "phase_b_judge_report.json"
LABEL_SET = ("A", "B", "TIE")


@dataclass
class JudgeOutput:
    winner: str
    score_a: float
    score_b: float
    rationale: str
    engine: str


def _normalize_label(label: str) -> str:
    label = str(label).upper().strip()
    return label if label in LABEL_SET else "TIE"


def _rule_based_pairwise(question: str, answer_a: str, answer_b: str, ground_truth: str) -> JudgeOutput:
    """Fallback judge when LLM endpoint is unavailable."""

    def overlap_score(text: str) -> float:
        gt_tokens = set(re.findall(r"\w+", ground_truth.lower()))
        ans_tokens = set(re.findall(r"\w+", text.lower()))
        if not gt_tokens or not ans_tokens:
            return 0.0
        return len(gt_tokens & ans_tokens) / len(gt_tokens)

    score_a = overlap_score(answer_a)
    score_b = overlap_score(answer_b)

    if abs(score_a - score_b) <= 0.05:
        winner = "TIE"
    else:
        winner = "A" if score_a > score_b else "B"

    rationale = (
        f"Rule judge based on overlap with reference. "
        f"question='{question[:80]}', score_a={score_a:.3f}, score_b={score_b:.3f}"
    )
    return JudgeOutput(winner=winner, score_a=score_a, score_b=score_b, rationale=rationale, engine="rule")


def _extract_json_block(content: str) -> dict[str, Any] | None:
    content = content.strip()
    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _llm_pairwise(question: str, answer_a: str, answer_b: str, ground_truth: str) -> JudgeOutput:
    judge_mode = os.getenv("JUDGE_MODE", "auto").strip().lower()
    if judge_mode == "rule":
        return _rule_based_pairwise(question, answer_a, answer_b, ground_truth)

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return _rule_based_pairwise(question, answer_a, answer_b, ground_truth)

    try:
        from openai import OpenAI

        timeout_sec = float(os.getenv("JUDGE_TIMEOUT_SEC", "3"))
        client = OpenAI(api_key=api_key, timeout=timeout_sec, max_retries=0)
        prompt = (
            "You are an impartial evaluator. Compare Candidate A and Candidate B.\n"
            "Judge factual correctness vs reference answer, completeness, and directness.\n"
            "Return strict JSON with keys: winner, score_a, score_b, rationale.\n"
            "winner must be one of A, B, TIE. score_a/score_b in [0,1].\n\n"
            f"Question: {question}\n"
            f"Reference answer: {ground_truth}\n"
            f"Candidate A: {answer_a}\n"
            f"Candidate B: {answer_b}\n"
        )
        response = client.chat.completions.create(
            model=os.getenv("JUDGE_MODEL", "gpt-4o-mini"),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content or "{}"
        payload = _extract_json_block(content) or {}
        winner = _normalize_label(payload.get("winner", "TIE"))
        score_a = float(payload.get("score_a", 0.5))
        score_b = float(payload.get("score_b", 0.5))
        rationale = str(payload.get("rationale", "")).strip()
        return JudgeOutput(winner=winner, score_a=score_a, score_b=score_b, rationale=rationale, engine="llm")
    except Exception:
        return _rule_based_pairwise(question, answer_a, answer_b, ground_truth)


def _swap_and_average(question: str, answer_a: str, answer_b: str, ground_truth: str) -> dict[str, Any]:
    forward = _llm_pairwise(question, answer_a, answer_b, ground_truth)
    backward = _llm_pairwise(question, answer_b, answer_a, ground_truth)

    # Map backward scores back to original A/B identity.
    score_a = (forward.score_a + backward.score_b) / 2.0
    score_b = (forward.score_b + backward.score_a) / 2.0

    if abs(score_a - score_b) <= 0.05:
        debiased_winner = "TIE"
    else:
        debiased_winner = "A" if score_a > score_b else "B"

    backward_mapped_winner = {"A": "B", "B": "A", "TIE": "TIE"}[backward.winner]
    position_flip = forward.winner != backward_mapped_winner

    return {
        "forward": forward,
        "backward": backward,
        "debiased_winner": debiased_winner,
        "debiased_score_a": score_a,
        "debiased_score_b": score_b,
        "position_flip": position_flip,
    }


def _cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    if len(labels_a) != len(labels_b) or not labels_a:
        return 0.0

    labels_a = [_normalize_label(x) for x in labels_a]
    labels_b = [_normalize_label(x) for x in labels_b]
    n = len(labels_a)
    observed = sum(1 for x, y in zip(labels_a, labels_b) if x == y) / n

    pe = 0.0
    for label in LABEL_SET:
        p_a = sum(1 for x in labels_a if x == label) / n
        p_b = sum(1 for x in labels_b if x == label) / n
        pe += p_a * p_b

    if abs(1 - pe) < 1e-12:
        return 1.0
    return (observed - pe) / (1 - pe)


def run_phase_b(test_data_path: str | None = None, human_label_path: str | None = None) -> dict[str, Any]:
    samples = load_test_data(test_data_path)
    human_label_map = load_human_labels(human_label_path)

    details = []
    judge_labels: list[str] = []
    human_labels: list[str] = []

    for sample in samples:
        swap_result = _swap_and_average(
            question=sample["question"],
            answer_a=sample["candidate_a"],
            answer_b=sample["candidate_b"],
            ground_truth=sample["ground_truth"],
        )
        winner = swap_result["debiased_winner"]
        judge_labels.append(winner)

        human_label = human_label_map.get(sample["id"], sample["human_preference"])
        human_labels.append(human_label)

        details.append(
            {
                "id": sample["id"],
                "question": sample["question"],
                "human_preference": human_label,
                "judge_debiased_winner": winner,
                "judge_debiased_score_a": swap_result["debiased_score_a"],
                "judge_debiased_score_b": swap_result["debiased_score_b"],
                "position_flip": swap_result["position_flip"],
                "forward_engine": swap_result["forward"].engine,
                "forward_winner": swap_result["forward"].winner,
                "backward_winner_raw": swap_result["backward"].winner,
            }
        )

    kappa = _cohen_kappa(judge_labels, human_labels)
    position_flip_rate = (
        sum(1 for item in details if item["position_flip"]) / len(details) if details else 0.0
    )
    agreement = (
        sum(1 for x, y in zip(judge_labels, human_labels) if _normalize_label(x) == _normalize_label(y))
        / len(details)
        if details
        else 0.0
    )

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "num_samples": len(samples),
        "swap_and_average_enabled": True,
        "cohen_kappa": kappa,
        "raw_agreement": agreement,
        "position_flip_rate": position_flip_rate,
        "details": details,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    report = run_phase_b()
    print("Phase B complete.")
    print(f"- Samples: {report['num_samples']}")
    print(f"- Cohen's kappa: {report['cohen_kappa']:.4f}")
    print(f"- Raw agreement: {report['raw_agreement']:.4f}")
    print(f"- Position flip rate: {report['position_flip_rate']:.4f}")
    print(f"- Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
