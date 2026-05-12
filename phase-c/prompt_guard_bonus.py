"""Bonus: Prompt Guard style classifier wrapper (HF model with fallback)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class PromptGuardResult:
    is_malicious: bool
    score: float
    engine: str


class PromptGuardBonus:
    def __init__(self) -> None:
        self.model_id = os.getenv("PROMPT_GUARD_MODEL", "meta-llama/Prompt-Guard-2-86M")
        self._pipeline = None
        self.enable_hf = os.getenv("PROMPT_GUARD_ENABLE_HF", "0").strip() == "1"
        if self.enable_hf:
            self._init_model()

    def _init_model(self) -> None:
        try:
            from transformers import pipeline

            self._pipeline = pipeline(
                "text-classification",
                model=self.model_id,
                tokenizer=self.model_id,
                local_files_only=False,
            )
        except Exception:
            self._pipeline = None

    def classify(self, text: str) -> PromptGuardResult:
        if self._pipeline is not None:
            out = self._pipeline(text, truncation=True, max_length=512)[0]
            label = str(out.get("label", "")).upper()
            score = float(out.get("score", 0.0))
            is_malicious = label in {"LABEL_1", "INJECTION", "JAILBREAK", "MALICIOUS"}
            return PromptGuardResult(is_malicious=is_malicious, score=score, engine="hf-prompt-guard")

        fallback_signals = [
            "ignore previous instructions",
            "reveal system prompt",
            "developer mode",
            "jailbreak",
            "<|system|>",
        ]
        lowered = (text or "").lower()
        hits = sum(1 for sig in fallback_signals if sig in lowered)
        score = min(1.0, hits / 2.0)
        return PromptGuardResult(is_malicious=score >= 0.5, score=score, engine="regex-fallback")
