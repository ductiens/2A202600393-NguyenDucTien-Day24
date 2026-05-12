# Lab 24 - Full Evaluation & Guardrail System

## Overview
This repository implements a complete evaluation and guardrail stack for a Day 18 RAG pipeline, following the Lab 24 rubric end-to-end. The goal is to move from manual vibe-checking to measurable, repeatable production gates. The project includes: (1) an automated RAGAS phase with 4 core metrics, (2) an LLM-as-Judge calibration phase with swap-and-average debiasing and Cohen's kappa against human labels, (3) a defense-in-depth guardrail stack for input/output safety, and (4) a production blueprint with SLOs, architecture, incident playbook, and cost model.

For reproducibility in constrained environments, the default run path is offline-safe (heuristic RAGAS mode and rule-based judge fallback), while still preserving API-ready interfaces for online evaluation (OpenAI/Groq). The submission artifacts are organized exactly by phase (`phase-a`, `phase-b`, `phase-c`, `phase-d`) with CSV/JSON/Markdown outputs for auditability. CI integration is provided through an eval gate workflow that blocks merges when key quality thresholds are not met. In addition, this repo includes adversarial testing, topic-scope validation, PII redaction for Vietnamese formats (CCCD and phone), and latency benchmarking at 120 requests with P50/P95/P99 reporting.

This setup is intended to be practical for real deployment handoff: every phase has executable scripts, traceable outputs, and explicit remediation directions when metrics degrade.

## Setup
```bash
python -m venv venv
# Windows PowerShell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

## Run All Artifacts
```bash
python scripts/build_all_lab24.py
# or run phases separately:
python scripts/build_phase_a.py
python scripts/build_phase_b.py
python scripts/build_phase_c.py
python phase-b/kappa_analysis.py
```

## Results Summary
### Phase A (RAGAS)
- Test set: 50 questions (`simple=25`, `reasoning=13`, `multi_context=12`)
- Faithfulness: 0.7218
- Answer Relevancy: 0.4399
- Context Precision: 0.3035
- Context Recall: 0.9655
- Total eval cost (offline run): $0.00
- Failure clusters: 2 major clusters in `phase-a/failure_analysis.md`

### Phase B (LLM-Judge)
- Pairwise samples: 40
- Absolute scoring samples: 40
- Cohen's kappa vs human labels: 1.00 (`almost perfect`)
- Position bias mitigation: swap-and-average enabled
- Bias report: `phase-b/judge_bias_report.md`

### Phase C (Guardrails)
- PII recall: 100% (10-case test set includes edge cases)
- Topic validator accuracy: 90% on 20 inputs
- Adversarial detection: 95% (19/20)
- Legit false positive rate: 10% (1/10)
- Output unsafe detection: 80% (8/10), safe FP: 0%
- Latency benchmark: 120 requests, P95 L1=0.03ms, L3=0.01ms, Total=0.04ms
- Bonus: Prompt Guard integration wrapper + benchmark in `phase-c/prompt_guard_bonus_results.csv`

### Phase D (Blueprint)
- Document: `phase-d/blueprint.md`

## Deliverables Map
- Phase A: `phase-a/testset_v1.csv`, `phase-a/ragas_results.csv`, `phase-a/ragas_summary.json`, `phase-a/testset_review_notes.md`, `phase-a/failure_analysis.md`
- Phase B: `phase-b/pairwise_results.csv`, `phase-b/absolute_scores.csv`, `phase-b/human_labels.csv`, `phase-b/kappa_analysis.py`, `phase-b/kappa_analysis_output.json`, `phase-b/judge_bias_report.md`
- Phase C: `phase-c/input_guard.py`, `phase-c/output_guard.py`, `phase-c/full_pipeline.py`, `phase-c/pii_test_results.csv`, `phase-c/adversarial_test_results.csv`, `phase-c/latency_benchmark.csv`, `phase-c/output_guard_test_results.csv`
- Phase D: `phase-d/blueprint.md`
- CI Gate: `.github/workflows/eval-gate.yml`

## Bonus Artifacts
- Cross-judge protocol (+3): `phase-b/cross_judge_results.csv`, `phase-b/cross_judge_report.md`, `phase-b/cross_judge_summary.json`
- Prompt Guard integration (+2): `phase-c/prompt_guard_bonus.py`, `phase-c/prompt_guard_bonus_results.csv`
- Blog post draft (+2): `phase-d/blog_post_bonus.md`

## Demo Video
- Placeholder: `demo/demo-video.mp4` (add your final recording file here)
