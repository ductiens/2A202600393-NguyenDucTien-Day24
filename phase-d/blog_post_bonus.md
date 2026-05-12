# Bonus Blog Post Draft: From Vibe Checks to Production Guardrails (Lab 24)

> Suggested platform: Medium or dev.to  
> Suggested title: **How I Turned a Day-18 RAG Demo into a Production Eval + Guardrail Stack**

## 1) The Problem

Most student RAG systems work in demos but fail under real traffic.  
The gap is not only model quality; it is missing **measurement** and missing **defense**.

In this lab, I moved from manual “looks good” validation to a reproducible stack:
- automated eval gate,
- calibrated LLM judge,
- layered guardrails with adversarial testing,
- latency-aware blueprint.

## 2) What I Built

### Phase A - RAGAS Evaluation
- Generated and reviewed a 50-question testset (simple/reasoning/multi-context).
- Scored 4 core metrics: Faithfulness, Answer Relevancy, Context Precision, Context Recall.
- Clustered bottom failures and proposed technical fixes (retrieval depth, reranker, metadata filter).
- Added CI eval gate workflow for pull requests.

### Phase B - LLM-as-Judge + Calibration
- Implemented pairwise judge with **swap-and-average** to reduce position bias.
- Added absolute scoring rubric (accuracy, relevance, conciseness, helpfulness).
- Human-labeled sample set and computed **Cohen's kappa**.
- Quantified bias patterns and built a cross-judge bonus protocol.

### Phase C - Guardrails
- Input layer: VN PII redaction (CCCD + phone), topic scope validation, injection checks.
- Output layer: Llama-Guard-style moderation interface with fallback behavior.
- Adversarial suite (20 attacks) + legitimate suite (FP tracking).
- End-to-end latency benchmark with P50/P95/P99.

### Phase D - Blueprint
- SLO table with alert thresholds and severities.
- Architecture diagram (4 layers, defense-in-depth).
- Incident playbooks for quality drop, FP spike, and latency incident.
- Monthly cost estimate + optimization levers.

## 3) Lessons Learned

1. **Without eval, you cannot debug RAG.**  
   Metric decomposition exposed whether failures came from retrieval vs generation.

2. **LLM judge quality is not binary.**  
   Bias mitigation and calibration matter as much as the judge model itself.

3. **Guardrails are only real when measured.**  
   Detection rate, FP rate, and latency must be tracked together.

4. **Blueprints prevent operational panic.**  
   Predefined playbooks reduced uncertainty when metrics degrade.

## 4) What I Would Improve Next

- Add online tracing integration (LangSmith/Langfuse) for production telemetry.
- Replace fallback moderation with full managed Llama Guard endpoint in all environments.
- Extend cross-judge protocol with a third independent LLM evaluator.
- Add dashboard UX for non-technical stakeholders.

## 5) References / Artifacts

- `phase-a/`, `phase-b/`, `phase-c/`, `phase-d/`
- `.github/workflows/eval-gate.yml`
- `prompts.md`

If this post is published publicly, include screenshots of:
1. eval gate artifacts,
2. pairwise + kappa outputs,
3. adversarial test table,
4. latency benchmark summary.

