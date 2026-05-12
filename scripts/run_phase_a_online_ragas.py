"""Run online RAGAS scoring using OpenAI-backed metrics on Phase A dataset.

Input:
- phase-a/ragas_results.csv (expects question, answer, contexts, ground_truth)

Output:
- phase-a/ragas_results_online.csv
- phase-a/ragas_summary_online.json
"""

from __future__ import annotations

import ast
import csv
import json
import os
from pathlib import Path
from dotenv import load_dotenv


def parse_contexts(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return [str(x) for x in val]
    except Exception:
        pass
    try:
        val = ast.literal_eval(raw)
        if isinstance(val, list):
            return [str(x) for x in val]
    except Exception:
        pass
    return [raw]


def main() -> None:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for online RAGAS run.")

    root = Path(__file__).resolve().parents[1]
    in_csv = root / "phase-a" / "ragas_results.csv"
    out_csv = root / "phase-a" / "ragas_results_online.csv"
    out_summary = root / "phase-a" / "ragas_summary_online.json"

    rows = list(csv.DictReader(in_csv.open(encoding="utf-8")))
    if not rows:
        raise RuntimeError("phase-a/ragas_results.csv is empty.")

    dataset_rows = []
    for r in rows:
        dataset_rows.append(
            {
                "question": r["question"],
                "answer": r["answer"],
                "contexts": parse_contexts(r.get("contexts", "")),
                "ground_truth": r["ground_truth"],
            }
        )

    from datasets import Dataset
    from ragas import evaluate
    from ragas.run_config import RunConfig
    # ragas==0.4.x expects initialized metric objects from ragas.metrics
    from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

    # Provide an embeddings implementation compatible with RAGAS metric requirements.
    embeddings = None
    try:
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings(model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"))
    except Exception:
        try:
            from langchain_community.embeddings import OpenAIEmbeddings

            embeddings = OpenAIEmbeddings(model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"))
        except Exception:
            embeddings = None
    if embeddings is None:
        raise RuntimeError(
            "Could not initialize OpenAI embeddings for RAGAS. "
            "Install `langchain-openai` and ensure OPENAI_API_KEY is valid."
        )
    if not hasattr(embeddings, "embed_query"):
        raise RuntimeError(
            "OpenAI embeddings object does not expose embed_query(). "
            "Please use langchain-openai OpenAIEmbeddings."
        )

    ds = Dataset.from_list(dataset_rows)
    result = evaluate(
        ds,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        embeddings=embeddings,
        run_config=RunConfig(timeout=30, max_retries=1, max_wait=3, max_workers=4),
        raise_exceptions=False,
        show_progress=False,
    )

    # per-row
    frame = result.to_pandas()
    frame.to_csv(out_csv, index=False)

    # aggregate
    metric_cols = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    agg = {}
    for col in metric_cols:
        if col in frame.columns:
            agg[col] = float(frame[col].dropna().mean())
        else:
            agg[col] = 0.0
    summary = {
        "faithfulness": agg["faithfulness"],
        "answer_relevancy": agg["answer_relevancy"],
        "context_precision": agg["context_precision"],
        "context_recall": agg["context_recall"],
        "mode": "online_ragas",
        "source_csv": str(in_csv),
        "embedding_model": os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
    }
    out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Phase A online RAGAS completed.")
    print(f"- {out_csv}")
    print(f"- {out_summary}")


if __name__ == "__main__":
    main()
