"""
Module 5: Enrichment Pipeline
==============================
Enrich chunks before embedding: Summarize, HyQA, Contextual Prepend, Auto Metadata.

Test: pytest tests/test_m5.py
"""

import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY


@dataclass
class EnrichedChunk:
    """Chunk that has been enriched."""
    original_text: str
    enriched_text: str
    summary: str
    hypothesis_questions: list[str]
    auto_metadata: dict
    method: str  # "contextual", "summary", "hyqa", "full"


def summarize_chunk(text: str) -> str:
    """Create a short extractive summary."""
    sentences = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
    if not sentences:
        return text.strip()[:200]
    summary = ". ".join(sentences[:2]).strip()
    if summary and not summary.endswith((".", "!", "?")):
        summary += "."
    return summary


def generate_hypothesis_questions(text: str, n_questions: int = 3) -> list[str]:
    """Generate questions that the chunk could answer."""
    lowered = text.lower()
    questions: list[str] = []
    if "nghỉ phép" in lowered or "nghi phep" in lowered:
        questions.extend(
            [
                "Nhân viên được nghỉ phép bao nhiêu ngày mỗi năm?",
                "Số ngày nghỉ phép có thay đổi theo thâm niên không?",
                "Điều kiện xin nghỉ phép là gì?",
            ]
        )
    elif "mật khẩu" in lowered or "mat khau" in lowered:
        questions.extend(
            [
                "Mật khẩu phải thay đổi bao lâu một lần?",
                "Chính sách mật khẩu yêu cầu gì?",
                "Ai chịu trách nhiệm đặt lại mật khẩu?",
            ]
        )
    else:
        questions.extend(
            [
                "Đoạn văn này nói về vấn đề gì?",
                "Thông tin chính của đoạn văn là gì?",
                "Đoạn này trả lời câu hỏi nào?",
            ]
        )
    return questions[:max(1, n_questions)]


def contextual_prepend(text: str, document_title: str = "") -> str:
    """Prepend a short context line to the chunk."""
    if document_title:
        context = f"Trich tu tai lieu {document_title}."
    else:
        context = "Trich doan van lien quan trong tai lieu."
    return f"{context}\n\n{text}"


def extract_metadata(text: str) -> dict:
    """Extract simple metadata heuristically."""
    lowered = text.lower()
    if any(ch in lowered for ch in ["ă", "â", "đ", "ê", "ô", "ơ", "ư", "á", "à", "ả", "ã", "ạ"]):
        language = "vi"
    else:
        language = "en"

    if "nghỉ phép" in lowered or "nghi phep" in lowered:
        category = "hr"
        topic = "nghi phep"
    elif "mật khẩu" in lowered or "mat khau" in lowered:
        category = "it"
        topic = "mat khau"
    elif "bảo vệ dữ liệu" in lowered or "du lieu" in lowered:
        category = "policy"
        topic = "bao ve du lieu"
    else:
        category = "general"
        topic = "general"

    entities = []
    for token in ("12", "30", "60", "90"):
        if token in lowered:
            entities.append(token)

    return {
        "topic": topic,
        "entities": entities,
        "category": category,
        "language": language,
    }


def enrich_chunks(
    chunks: list[dict],
    methods: list[str] | None = None,
) -> list[EnrichedChunk]:
    """
    Run enrichment pipeline on a list of chunks.
    """
    if methods is None:
        methods = ["contextual", "hyqa", "metadata"]

    enriched = []
    method_label = "+".join(methods)

    for chunk in chunks:
        text = chunk.get("text", "")
        metadata = chunk.get("metadata", {})
        summary = summarize_chunk(text) if ("summary" in methods or "full" in methods) else ""
        questions = generate_hypothesis_questions(text) if ("hyqa" in methods or "full" in methods) else []
        enriched_text = (
            contextual_prepend(text, metadata.get("source", ""))
            if ("contextual" in methods or "full" in methods)
            else text
        )
        auto_meta = extract_metadata(text) if ("metadata" in methods or "full" in methods) else {}
        enriched.append(
            EnrichedChunk(
                original_text=text,
                enriched_text=enriched_text,
                summary=summary,
                hypothesis_questions=questions,
                auto_metadata={**metadata, **auto_meta},
                method=method_label,
            )
        )

    return enriched


def _safe_text(value) -> str:
    return str(value).encode("ascii", "ignore").decode("ascii")


def main() -> None:
    sample = (
        "Nhan vien chinh thuc duoc nghi phep nam 12 ngay lam viec moi nam. "
        "So ngay nghi phep tang them 1 ngay cho moi 5 nam tham nien cong tac."
    )

    print("=== Enrichment Pipeline Demo ===\n")
    print(f"Original: {_safe_text(sample)}\n")
    print(f"Summary: {_safe_text(summarize_chunk(sample))}\n")
    print(f"HyQA questions: {_safe_text(generate_hypothesis_questions(sample))}\n")
    print(f"Contextual: {_safe_text(contextual_prepend(sample, 'So tay nhan vien'))}\n")
    print(f"Auto metadata: {_safe_text(extract_metadata(sample))}")


if __name__ == "__main__":
    main()
