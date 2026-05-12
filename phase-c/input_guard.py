"""Input guardrails: PII redaction, topic validation, injection detection."""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass

VN_CCCD_REGEX = re.compile(r"\b\d{12}\b")
VN_PHONE_REGEX = re.compile(r"(?<!\d)(?:\+?84|0)(?:3|5|7|8|9)\d{8}(?!\d)")


@dataclass
class GuardDecision:
    ok: bool
    reason: str


class InputGuard:
    def __init__(self) -> None:
        self._injection_patterns = [
            re.compile(pat, re.IGNORECASE)
            for pat in [
                r"ignore (all )?(previous|prior) instructions",
                r"you are now",
                r"developer mode",
                r"dan mode",
                r"reveal (the )?system prompt",
                r"bypass safety",
                r"jailbreak",
                r"pretend to be",
                r"do anything now",
                r"output exactly",
                r"base64",
                r"decode this",
                r"<\|system\|>",
            ]
        ]

        self._topic_keywords = {
            "hr_policy": ["nghi phep", "nhan vien", "tham nien", "nghi om", "phe duyet"],
            "privacy": ["du lieu ca nhan", "cccd", "bao ve du lieu", "rieng tu"],
            "finance": ["bao cao tai chinh", "bctc", "doanh thu", "loi nhuan"],
            "it_policy": ["mat khau", "mfa", "bao mat he thong"],
        }

    def sanitize(self, text: str) -> tuple[str, dict]:
        started = time.perf_counter()
        if text is None:
            text = ""
        findings = []

        def replace_and_track(pattern: re.Pattern[str], label: str, repl: str, current: str) -> str:
            for m in pattern.finditer(current):
                findings.append({"entity": label, "text": m.group(0), "start": m.start(), "end": m.end()})
            return pattern.sub(repl, current)

        redacted = text
        redacted = replace_and_track(VN_CCCD_REGEX, "VN_CCCD", "[REDACTED_CCCD]", redacted)
        redacted = replace_and_track(VN_PHONE_REGEX, "VN_PHONE", "[REDACTED_PHONE]", redacted)

        latency_ms = (time.perf_counter() - started) * 1000
        return redacted, {"findings": findings, "latency_ms": latency_ms}

    async def sanitize_async(self, text: str) -> tuple[str, dict]:
        return self.sanitize(text)

    def check_topic(self, text: str) -> GuardDecision:
        lowered = (text or "").lower()
        for topic, kws in self._topic_keywords.items():
            if any(k in lowered for k in kws):
                return GuardDecision(True, f"in_scope:{topic}")
        return GuardDecision(False, "out_of_scope")

    async def check_topic_async(self, text: str) -> GuardDecision:
        return self.check_topic(text)

    def detect_injection(self, text: str) -> GuardDecision:
        lowered = (text or "").strip().lower()
        if not lowered:
            return GuardDecision(True, "empty_input")
        for pattern in self._injection_patterns:
            if pattern.search(lowered):
                return GuardDecision(False, f"injection_pattern:{pattern.pattern}")
        return GuardDecision(True, "no_injection_detected")

    async def detect_injection_async(self, text: str) -> GuardDecision:
        return self.detect_injection(text)

    def check(self, text: str) -> GuardDecision:
        redacted, _ = self.sanitize(text)
        inj = self.detect_injection(redacted)
        if not inj.ok:
            return inj
        topic = self.check_topic(redacted)
        if not topic.ok:
            return GuardDecision(False, "topic_blocked")
        return GuardDecision(True, "input_passed")

    async def check_async(self, text: str) -> GuardDecision:
        sanitize_task = asyncio.create_task(self.sanitize_async(text))
        inj_task = asyncio.create_task(self.detect_injection_async(text))
        redacted, _ = await sanitize_task
        inj = await inj_task
        if not inj.ok:
            return inj
        topic = await self.check_topic_async(redacted)
        if not topic.ok:
            return GuardDecision(False, "topic_blocked")
        return GuardDecision(True, "input_passed")


def refusal_message() -> str:
    return (
        "Xin loi, yeu cau nay nam ngoai pham vi tro giup an toan cua he thong. "
        "Vui long hoi ve chinh sach noi bo, du lieu ca nhan, hoac huong dan van hanh hop le."
    )

