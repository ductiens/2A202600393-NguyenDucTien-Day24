"""Threshold gate for Phase A metrics (used by CI workflow)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_thresholds(values: list[str]) -> dict[str, float]:
    parsed = {}
    for v in values:
        if "=" not in v:
            raise ValueError(f"Invalid threshold format: {v}")
        k, raw = v.split("=", 1)
        parsed[k.strip()] = float(raw.strip())
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--summary-path",
        default="phase-a/ragas_summary.json",
        help="Path to ragas summary json",
    )
    parser.add_argument(
        "--threshold",
        nargs="+",
        default=[
            "faithfulness=0.85",
            "answer_relevancy=0.80",
            "context_precision=0.70",
            "context_recall=0.75",
        ],
        help="Metric thresholds in key=value format",
    )
    args = parser.parse_args()

    thresholds = parse_thresholds(args.threshold)
    summary = json.loads(Path(args.summary_path).read_text(encoding="utf-8"))
    failed = []
    for metric, target in thresholds.items():
        score = float(summary.get(metric, 0.0))
        print(f"{metric}: score={score:.4f}, target={target:.4f}")
        if score < target:
            failed.append((metric, score, target))

    if failed:
        print("\nEval gate failed:")
        for metric, score, target in failed:
            print(f"- {metric}: {score:.4f} < {target:.4f}")
        return 1
    print("\nEval gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

