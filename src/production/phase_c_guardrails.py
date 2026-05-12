"""Phase C: Defense-in-depth guardrail stack for production RAG agents."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.production.data_utils import ROOT_DIR, load_test_data

REPORT_PATH = ROOT_DIR / "reports" / "phase_c_guardrails_report.json"

VN_CCCD_REGEX = re.compile(r"\b\d{12}\b")
VN_PHONE_REGEX = re.compile(r"(?<!\d)(?:\+?84|0)(?:3|5|7|8|9)\d{8}(?!\d)")


@dataclass
class GuardrailDecision:
    allow: bool
    redacted_input: str
    pii_findings: list[dict[str, Any]] = field(default_factory=list)
    topic_allowed: bool = True
    topic: str = "unknown"
    output_safe: bool = True
    safety_label: str = "SAFE"
    violations: list[str] = field(default_factory=list)


def _regex_pii_redact(text: str) -> tuple[str, list[dict[str, Any]]]:
    findings = []
    redacted = text

    def _replace(pattern: re.Pattern[str], entity: str, replacement: str) -> None:
        nonlocal redacted
        matches = list(pattern.finditer(redacted))
        for m in matches:
            findings.append(
                {
                    "entity_type": entity,
                    "start": m.start(),
                    "end": m.end(),
                    "text": m.group(0),
                    "method": "regex",
                }
            )
        redacted = pattern.sub(replacement, redacted)

    _replace(VN_CCCD_REGEX, "VN_CCCD", "[REDACTED_CCCD]")
    _replace(VN_PHONE_REGEX, "VN_PHONE", "[REDACTED_PHONE]")
    return redacted, findings


def _presidio_redact(text: str) -> tuple[str, list[dict[str, Any]], bool]:
    try:
        from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
        from presidio_anonymizer import AnonymizerEngine

        analyzer = AnalyzerEngine()
        analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="VN_CCCD",
                patterns=[Pattern(name="vn_cccd", regex=r"\b\d{12}\b", score=0.8)],
            )
        )
        analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="VN_PHONE",
                patterns=[
                    Pattern(
                        name="vn_phone",
                        regex=r"(?<!\d)(?:\+?84|0)(?:3|5|7|8|9)\d{8}(?!\d)",
                        score=0.8,
                    )
                ],
            )
        )
        results = analyzer.analyze(text=text, entities=["VN_CCCD", "VN_PHONE"], language="en")
        anon = AnonymizerEngine()
        anonymized = anon.anonymize(text=text, analyzer_results=results)
        findings = [
            {
                "entity_type": x.entity_type,
                "start": x.start,
                "end": x.end,
                "score": x.score,
                "method": "presidio",
            }
            for x in results
        ]
        return anonymized.text, findings, True
    except Exception:
        return text, [], False


def redact_input_pii(text: str) -> tuple[str, list[dict[str, Any]], bool]:
    regex_redacted, regex_findings = _regex_pii_redact(text)
    presidio_redacted, presidio_findings, presidio_enabled = _presidio_redact(regex_redacted)
    return presidio_redacted, regex_findings + presidio_findings, presidio_enabled


def validate_topic(text: str) -> tuple[bool, str]:
    lowered = text.lower()
    topic_rules = {
        "hr_policy": ["nghi phep", "nhan vien", "tham nien", "ho so nghi om"],
        "data_privacy": ["du lieu ca nhan", "cccd", "bao mat", "rieng tu"],
        "finance": ["bao cao tai chinh", "bctc", "doanh thu", "loi nhuan"],
    }
    for topic, keywords in topic_rules.items():
        if any(keyword in lowered for keyword in keywords):
            return True, topic
    return False, "out_of_scope"


def classify_output_safety(text: str) -> tuple[bool, str, list[str]]:
    lowered = text.lower()
    categories = {
        "VIOLENCE": ["giet", "tan cong", "che tao bom", "vu khi"],
        "SELF_HARM": ["tu tu", "tu sat", "tu huy"],
        "HATE": ["ky thi", "thu han", "phan biet chung toc"],
        "SEXUAL": ["noi dung tinh duc", "khieu dam"],
        "CRIME": ["rua tien", "hack", "lua dao", "ma tuy"],
        "PII_LEAK": ["[redacted_cccd]", "[redacted_phone]", "cccd", "so dien thoai"],
    }

    violations = []
    for label, keywords in categories.items():
        if any(keyword in lowered for keyword in keywords):
            violations.append(label)

    if not violations:
        return True, "SAFE", []
    if violations == ["PII_LEAK"]:
        return False, "UNSAFE_PII", violations
    return False, "UNSAFE", violations


def run_guardrail_stack(user_input: str, candidate_output: str) -> GuardrailDecision:
    redacted_input, pii_findings, _ = redact_input_pii(user_input)
    topic_allowed, topic = validate_topic(redacted_input)
    output_safe, safety_label, violations = classify_output_safety(candidate_output)

    allow = topic_allowed and output_safe
    return GuardrailDecision(
        allow=allow,
        redacted_input=redacted_input,
        pii_findings=pii_findings,
        topic_allowed=topic_allowed,
        topic=topic,
        output_safe=output_safe,
        safety_label=safety_label,
        violations=violations,
    )


def run_phase_c(test_data_path: str | None = None) -> dict[str, Any]:
    samples = load_test_data(test_data_path)
    evaluations = []

    for sample in samples:
        synthetic_input = (
            f"{sample['question']} CCCD 079203001234, so dien thoai 0912345678."
            if sample["id"] == "q1"
            else sample["question"]
        )
        decision = run_guardrail_stack(synthetic_input, sample["answer"])
        evaluations.append(
            {
                "id": sample["id"],
                "allow": decision.allow,
                "redacted_input": decision.redacted_input,
                "pii_findings_count": len(decision.pii_findings),
                "topic_allowed": decision.topic_allowed,
                "topic": decision.topic,
                "output_safe": decision.output_safe,
                "safety_label": decision.safety_label,
                "violations": decision.violations,
            }
        )

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "num_samples": len(samples),
        "blocked_count": sum(1 for x in evaluations if not x["allow"]),
        "pii_detection_hit_count": sum(1 for x in evaluations if x["pii_findings_count"] > 0),
        "topic_block_count": sum(1 for x in evaluations if not x["topic_allowed"]),
        "unsafe_output_count": sum(1 for x in evaluations if not x["output_safe"]),
        "evaluations": evaluations,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    report = run_phase_c()
    print("Phase C complete.")
    print(f"- Samples: {report['num_samples']}")
    print(f"- Blocked: {report['blocked_count']}")
    print(f"- PII hits: {report['pii_detection_hit_count']}")
    print(f"- Unsafe outputs: {report['unsafe_output_count']}")
    print(f"- Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()

