"""Full guardrail stack integration and latency benchmark."""

from __future__ import annotations

import asyncio
import csv
import time
from pathlib import Path
from statistics import quantiles

from input_guard import InputGuard, refusal_message
from output_guard import OutputGuard


def rag_pipeline_sync(query: str) -> str:
    q = (query or "").lower()
    if "nghi phep" in q and "bao nhieu" in q:
        return "Nhan vien chinh thuc duoc nghi phep nam 12 ngay moi nam."
    if "tham nien" in q:
        return "Moi 5 nam tham nien se duoc cong them 1 ngay nghi phep."
    if "khong luong" in q:
        return "Nghi phep khong luong toi da 30 ngay moi nam."
    if "mat khau" in q:
        return "Mat khau he thong phai thay doi moi 90 ngay va bat buoc MFA."
    if "du lieu ca nhan" in q:
        return "Yeu cau du lieu ca nhan duoc tiep nhan boi bo phan Phap che va Bao ve du lieu."
    return "Toi can them ngu canh de tra loi chinh xac."


async def rag_pipeline_async(query: str) -> str:
    return rag_pipeline_sync(query)


async def guarded_pipeline(user_input: str, in_guard: InputGuard, out_guard: OutputGuard):
    timings = {}

    t0 = time.perf_counter()
    sanitize_task = asyncio.create_task(in_guard.sanitize_async(user_input))
    topic_task = asyncio.create_task(in_guard.check_topic_async(user_input))
    inj_task = asyncio.create_task(in_guard.detect_injection_async(user_input))
    sanitized, pii_meta = await sanitize_task
    topic_decision = await topic_task
    inj_decision = await inj_task
    timings["L1"] = (time.perf_counter() - t0) * 1000

    if not topic_decision.ok or not inj_decision.ok:
        return refusal_message(), timings, False, pii_meta

    t0 = time.perf_counter()
    answer = await rag_pipeline_async(sanitized)
    timings["L2"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    out_decision = await out_guard.check_async(sanitized, answer)
    timings["L3"] = (time.perf_counter() - t0) * 1000
    timings["L3_model"] = out_decision.latency_ms

    if not out_decision.is_safe:
        return refusal_message(), timings, False, pii_meta
    return answer, timings, True, pii_meta


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    q = quantiles(values, n=100, method="inclusive")
    idx = max(0, min(99, int(p) - 1))
    return q[idx]


async def benchmark(queries: list[str], out_path: Path) -> dict:
    in_guard = InputGuard()
    out_guard = OutputGuard()
    rows = []

    for i, q in enumerate(queries, start=1):
        t_start = time.perf_counter()
        _, timings, allowed, pii_meta = await guarded_pipeline(q, in_guard, out_guard)
        total_ms = (time.perf_counter() - t_start) * 1000
        rows.append(
            {
                "request_id": i,
                "query": q[:120],
                "L1_ms": round(timings.get("L1", 0.0), 4),
                "L2_ms": round(timings.get("L2", 0.0), 4),
                "L3_ms": round(timings.get("L3", 0.0), 4),
                "total_ms": round(total_ms, 4),
                "allowed": allowed,
                "pii_hits": len(pii_meta.get("findings", [])),
            }
        )

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    l1 = [r["L1_ms"] for r in rows]
    l2 = [r["L2_ms"] for r in rows]
    l3 = [r["L3_ms"] for r in rows]
    total = [r["total_ms"] for r in rows]
    return {
        "n_requests": len(rows),
        "L1_P50": percentile(l1, 50),
        "L1_P95": percentile(l1, 95),
        "L1_P99": percentile(l1, 99),
        "L2_P50": percentile(l2, 50),
        "L2_P95": percentile(l2, 95),
        "L2_P99": percentile(l2, 99),
        "L3_P50": percentile(l3, 50),
        "L3_P95": percentile(l3, 95),
        "L3_P99": percentile(l3, 99),
        "TOTAL_P50": percentile(total, 50),
        "TOTAL_P95": percentile(total, 95),
        "TOTAL_P99": percentile(total, 99),
    }

