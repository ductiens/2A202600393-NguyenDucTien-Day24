"""Run all production release phases (A/B/C) end-to-end."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.production.data_utils import ROOT_DIR
from src.production.phase_a_ragas import run_phase_a
from src.production.phase_b_judge import run_phase_b
from src.production.phase_c_guardrails import run_phase_c

MASTER_REPORT_PATH = ROOT_DIR / "reports" / "production_release_report.json"


def run_all() -> dict:
    phase_a = run_phase_a()
    phase_b = run_phase_b()
    phase_c = run_phase_c()

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase_a": {
            "engine": phase_a["engine"],
            "aggregate": phase_a["aggregate"],
            "mean_score": phase_a["mean_score"],
        },
        "phase_b": {
            "cohen_kappa": phase_b["cohen_kappa"],
            "raw_agreement": phase_b["raw_agreement"],
            "position_flip_rate": phase_b["position_flip_rate"],
            "swap_and_average_enabled": phase_b["swap_and_average_enabled"],
        },
        "phase_c": {
            "blocked_count": phase_c["blocked_count"],
            "pii_detection_hit_count": phase_c["pii_detection_hit_count"],
            "topic_block_count": phase_c["topic_block_count"],
            "unsafe_output_count": phase_c["unsafe_output_count"],
        },
    }
    MASTER_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    MASTER_REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    report = run_all()
    print("Production release suite complete.")
    print(f"- Master report: {MASTER_REPORT_PATH}")
    print(f"- Phase A mean: {report['phase_a']['mean_score']:.4f}")
    print(f"- Phase B kappa: {report['phase_b']['cohen_kappa']:.4f}")
    print(f"- Phase C blocked: {report['phase_c']['blocked_count']}")


if __name__ == "__main__":
    main()

