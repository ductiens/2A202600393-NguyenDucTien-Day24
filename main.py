"""
Lab 18: Production RAG Pipeline
Main entry point.
Run the baseline, production pipeline, compare results, and write reports.
"""

import json
import os
import time


def main():
    print("=" * 60)
    print("LAB 18: PRODUCTION RAG PIPELINE")
    print("=" * 60)
    start = time.time()

    os.makedirs("reports", exist_ok=True)

    print("\nSTEP 1: Running Basic RAG Baseline...")
    print("-" * 40)
    from naive_baseline import main as run_baseline

    run_baseline()

    print("\nSTEP 2: Running Production Pipeline...")
    print("-" * 40)
    from src.pipeline import build_pipeline, evaluate_pipeline

    search, reranker = build_pipeline()
    evaluate_pipeline(search, reranker)

    for f in ["ragas_report.json", "naive_baseline_report.json"]:
        if os.path.exists(f):
            os.replace(f, f"reports/{f}")

    print("\nSTEP 3: Comparison")
    print("-" * 40)
    naive_path = "reports/naive_baseline_report.json"
    prod_path = "reports/ragas_report.json"

    if os.path.exists(naive_path) and os.path.exists(prod_path):
        with open(naive_path, encoding="utf-8") as f:
            naive = json.load(f)
        with open(prod_path, encoding="utf-8") as f:
            prod = json.load(f)

        print(f"\n{'Metric':<25} {'Basic':>8} {'Production':>12} {'Delta':>8}")
        print("-" * 55)
        for m in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
            n = naive.get("aggregate", {}).get(m, 0)
            p = prod.get("aggregate", {}).get(m, 0)
            d = p - n
            status = "OK" if p >= 0.75 else "WARN"
            print(f"{status} {m:<21} {n:>8.4f} {p:>12.4f} {d:>+8.4f}")

    print("\nSTEP 4: Running Production Release Suite (A/B/C)...")
    print("-" * 40)
    # Safe defaults for local/offline runs. Override in env for full online eval:
    # RAGAS_MODE=auto, JUDGE_MODE=auto
    os.environ.setdefault("RAGAS_MODE", "heuristic")
    os.environ.setdefault("JUDGE_MODE", "rule")

    release_ok = True
    try:
        from src.production.run_release_suite import run_all

        release = run_all()
        print(f"  Phase A mean score: {release['phase_a']['mean_score']:.4f}")
        print(f"  Phase B Cohen's kappa: {release['phase_b']['cohen_kappa']:.4f}")
        print(f"  Phase C blocked count: {release['phase_c']['blocked_count']}")
        print("  Report: reports/production_release_report.json")
    except Exception as exc:
        release_ok = False
        print(f"  WARN: release suite failed: {exc}")

    elapsed = time.time() - start
    print(f"\nTotal time: {elapsed:.1f}s")
    print("\nNext steps:")
    print("  1. Fill analysis/failure_analysis.md")
    print("  2. Fill analysis/group_report.md")
    print("  3. Write analysis/reflections/reflection_[Name].md")
    print("  4. Run: python check_lab.py")
    if release_ok:
        print("  5. Review: reports/production_release_report.json")
    else:
        print("  5. Re-run release suite: python -m src.production.run_release_suite")


if __name__ == "__main__":
    main()
