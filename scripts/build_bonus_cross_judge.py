"""Bonus: Cross-judge protocol (+3) for Phase B."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
PHASE_B_DIR = ROOT / "phase-b"
PAIRWISE_PATH = PHASE_B_DIR / "pairwise_results.csv"
ABSOLUTE_PATH = PHASE_B_DIR / "absolute_scores.csv"
OUT_CSV = PHASE_B_DIR / "cross_judge_results.csv"
OUT_MD = PHASE_B_DIR / "cross_judge_report.md"


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _judge2_length_calibrated(row: dict) -> str:
    """A simple second judge to diversify decisions from judge-1.

    Judge-2 starts from score_a/score_b, then applies a small verbosity penalty
    to whichever candidate is much longer.
    """
    score_a = float(row["score_a"])
    score_b = float(row["score_b"])
    len_a = int(row["len_a"])
    len_b = int(row["len_b"])

    # Penalize very long answers to reduce verbosity bias.
    if len_a > len_b * 1.6:
        score_a -= 0.08
    if len_b > len_a * 1.6:
        score_b -= 0.08

    if abs(score_a - score_b) <= 0.04:
        return "TIE"
    return "A" if score_a > score_b else "B"


def main() -> None:
    pairwise = _read_csv(PAIRWISE_PATH)
    absolute = _read_csv(ABSOLUTE_PATH)
    abs_map = {x["id"]: x for x in absolute}

    out_rows = []
    agree = 0
    ensemble_agree_j1 = 0
    ensemble_agree_j2 = 0

    for row in pairwise:
        j1 = row["winner_after_swap"].upper()
        j2 = _judge2_length_calibrated(row)

        # Ensemble: majority vote among {j1, j2, absolute overall heuristic}.
        abs_row = abs_map[row["id"]]
        overall = float(abs_row["overall"])
        if overall >= 4.0:
            j3 = "A"
        elif overall <= 2.5:
            j3 = "B"
        else:
            j3 = "TIE"

        votes = [j1, j2, j3]
        labels = ("A", "B", "TIE")
        counts = {lb: votes.count(lb) for lb in labels}
        ensemble = max(labels, key=lambda lb: counts[lb])

        if j1 == j2:
            agree += 1
        if ensemble == j1:
            ensemble_agree_j1 += 1
        if ensemble == j2:
            ensemble_agree_j2 += 1

        out_rows.append(
            {
                "id": row["id"],
                "question": row["question"],
                "judge_1_swap": j1,
                "judge_2_length_calibrated": j2,
                "judge_3_absolute_proxy": j3,
                "ensemble_winner": ensemble,
                "len_a": row["len_a"],
                "len_b": row["len_b"],
            }
        )

    _write_csv(OUT_CSV, out_rows)

    n = len(out_rows)
    summary = {
        "num_samples": n,
        "j1_j2_agreement_rate": round(agree / n if n else 0.0, 4),
        "ensemble_vs_j1_agreement_rate": round(ensemble_agree_j1 / n if n else 0.0, 4),
        "ensemble_vs_j2_agreement_rate": round(ensemble_agree_j2 / n if n else 0.0, 4),
    }

    lines = [
        "# Bonus: Cross-Judge Protocol",
        "",
        "This report compares multi-judge agreement and an ensemble winner.",
        "",
        "## Setup",
        "- Judge 1: Swap-and-average pairwise winner from Phase B.",
        "- Judge 2: Length-calibrated variant to reduce verbosity bias.",
        "- Judge 3: Proxy from absolute score overall band.",
        "- Ensemble: Majority vote across 3 judges.",
        "",
        "## Metrics",
        f"- Samples: {summary['num_samples']}",
        f"- Judge1 vs Judge2 agreement: {summary['j1_j2_agreement_rate']:.2%}",
        f"- Ensemble vs Judge1 agreement: {summary['ensemble_vs_j1_agreement_rate']:.2%}",
        f"- Ensemble vs Judge2 agreement: {summary['ensemble_vs_j2_agreement_rate']:.2%}",
        "",
        "## Artifact",
        f"- `phase-b/{OUT_CSV.name}`",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    # Also store a compact JSON for dashboards/audit
    (PHASE_B_DIR / "cross_judge_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("Bonus cross-judge artifacts generated.")
    print(f"- {OUT_CSV}")
    print(f"- {OUT_MD}")
    print(f"- {PHASE_B_DIR / 'cross_judge_summary.json'}")


if __name__ == "__main__":
    main()

