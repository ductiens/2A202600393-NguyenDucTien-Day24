"""Output guardrails including Llama Guard 3 API mode + deterministic fallback."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class OutputDecision:
    is_safe: bool
    label: str
    reason: str
    latency_ms: float
    engine: str


class OutputGuard:
    """Llama Guard 3 wrapper (Groq API) with local fallback classifier."""

    def __init__(self, groq_api_key: str | None = None) -> None:
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("LLAMA_GUARD_MODEL", "llama-guard-3-8b")
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def _rule_classifier(self, user_input: str, agent_response: str) -> OutputDecision:
        start = time.perf_counter()
        text = f"{user_input}\n{agent_response}".lower()
        patterns = {
            "UNSAFE_VIOLENCE": [r"\bgiet\b", r"tan cong", r"vu khi", r"che tao bom"],
            "UNSAFE_SELF_HARM": [r"tu tu", r"tu sat", r"tu huy"],
            "UNSAFE_HATE": [r"ky thi", r"thu han", r"phan biet"],
            "UNSAFE_CRIME": [r"hack", r"lua dao", r"rua tien", r"ma tuy"],
            "UNSAFE_SEXUAL": [r"khieu dam", r"noi dung tinh duc"],
        }
        for label, regs in patterns.items():
            for reg in regs:
                if re.search(reg, text):
                    latency_ms = (time.perf_counter() - start) * 1000
                    return OutputDecision(False, label, f"matched:{reg}", latency_ms, "rule-fallback")
        latency_ms = (time.perf_counter() - start) * 1000
        return OutputDecision(True, "SAFE", "no unsafe pattern", latency_ms, "rule-fallback")

    def _groq_llama_guard(self, user_input: str, agent_response: str) -> OutputDecision:
        start = time.perf_counter()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": agent_response},
            ],
            "temperature": 0,
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            normalized = content.lower()
            is_safe = ("safe" in normalized) and ("unsafe" not in normalized)
            label = "SAFE" if is_safe else "UNSAFE"
            latency_ms = (time.perf_counter() - start) * 1000
            return OutputDecision(is_safe, label, content[:300], latency_ms, "llama-guard-3-groq")
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, OSError) as exc:
            fallback = self._rule_classifier(user_input, agent_response)
            return OutputDecision(
                fallback.is_safe,
                fallback.label,
                f"groq_error:{type(exc).__name__}; {fallback.reason}",
                fallback.latency_ms,
                "rule-fallback",
            )

    def check(self, user_input: str, agent_response: str) -> OutputDecision:
        if self.groq_api_key:
            return self._groq_llama_guard(user_input, agent_response)
        return self._rule_classifier(user_input, agent_response)

    async def check_async(self, user_input: str, agent_response: str) -> OutputDecision:
        return self.check(user_input, agent_response)


class PromptGuardLite:
    """Bonus (+2) style prompt-injection classifier proxy."""

    def __init__(self) -> None:
        self._signals = [
            "ignore previous instructions",
            "reveal your system prompt",
            "developer mode",
            "do anything now",
            "jailbreak",
            "<|system|>",
        ]

    def classify(self, text: str) -> tuple[bool, float]:
        lowered = (text or "").lower()
        hits = sum(1 for sig in self._signals if sig in lowered)
        score = min(1.0, hits / 2.0)
        is_malicious = score >= 0.5
        return is_malicious, score

