"""
Module 1: Advanced Chunking Strategies
=======================================
Implement semantic, hierarchical, and structure-aware chunking.
Compare with basic chunking (baseline) to see improvement.

Test: pytest tests/test_m1.py
"""

import os
import sys
import glob
import math
import re
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    DATA_DIR,
    HIERARCHICAL_PARENT_SIZE,
    HIERARCHICAL_CHILD_SIZE,
    SEMANTIC_THRESHOLD,
)


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)
    parent_id: str | None = None


def load_documents(data_dir: str = DATA_DIR) -> list[dict]:
    """Load markdown, text, or PDF files from data/."""
    docs = []
    for pattern in ("*.md", "*.txt", "*.pdf"):
        for fp in sorted(glob.glob(os.path.join(data_dir, pattern))):
            text = ""
            if fp.lower().endswith(".pdf"):
                text = _extract_pdf_text(fp)
            else:
                with open(fp, encoding="utf-8") as f:
                    text = f.read()
            if text.strip():
                docs.append({"text": text, "metadata": {"source": os.path.basename(fp)}})
    return docs


def _extract_pdf_text(fp: str) -> str:
    """Extract text from PDF using local tooling only."""
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(fp)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if text.strip():
            return text
    except Exception:
        pass

    # OCR fallback if the environment has the required local packages/tools.
    try:
        import tempfile
        from pathlib import Path

        try:
            import fitz  # type: ignore
        except Exception:
            fitz = None

        try:
            import pytesseract  # type: ignore
        except Exception:
            pytesseract = None

        if fitz is None or pytesseract is None:
            return ""

        doc = fitz.open(fp)
        pages_text = []
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            with tempfile.TemporaryDirectory() as tmpdir:
                img_path = Path(tmpdir) / "page.png"
                pix.save(str(img_path))
                from PIL import Image

                img = Image.open(img_path)
                pages_text.append(pytesseract.image_to_string(img, lang="vie+eng"))
        return "\n".join(pages_text)
    except Exception:
        return ""


def chunk_basic(text: str, chunk_size: int = 500, metadata: dict | None = None) -> list[Chunk]:
    """
    Basic chunking: split by paragraph (\n\n).
    This is the baseline and not the target of this module.
    """
    metadata = metadata or {}
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current:
            chunks.append(Chunk(text=current.strip(), metadata={**metadata, "chunk_index": len(chunks)}))
            current = ""
        current += para + "\n\n"
    if current.strip():
        chunks.append(Chunk(text=current.strip(), metadata={**metadata, "chunk_index": len(chunks)}))
    return chunks


def chunk_semantic(
    text: str,
    threshold: float = SEMANTIC_THRESHOLD,
    metadata: dict | None = None,
) -> list[Chunk]:
    """
    Split text by sentence similarity.
    """
    metadata = metadata or {}
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n\n+", text) if s.strip()]
    if not sentences:
        return []

    def token_set(sentence: str) -> set[str]:
        return {t for t in re.findall(r"[\wÀ-ỹ]+", sentence.lower()) if t}

    def similarity(a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        inter = len(a & b)
        if not inter:
            return 0.0
        return inter / math.sqrt(len(a) * len(b))

    chunks: list[Chunk] = []
    current_group = [sentences[0]]
    prev_tokens = token_set(sentences[0])

    for sentence in sentences[1:]:
        tokens = token_set(sentence)
        if similarity(prev_tokens, tokens) < threshold and current_group:
            chunks.append(
                Chunk(
                    text=" ".join(current_group).strip(),
                    metadata={**metadata, "chunk_index": len(chunks), "strategy": "semantic"},
                )
            )
            current_group = []
        current_group.append(sentence)
        prev_tokens = tokens

    if current_group:
        chunks.append(
            Chunk(
                text=" ".join(current_group).strip(),
                metadata={**metadata, "chunk_index": len(chunks), "strategy": "semantic"},
            )
        )
    return chunks


def chunk_hierarchical(
    text: str,
    parent_size: int = HIERARCHICAL_PARENT_SIZE,
    child_size: int = HIERARCHICAL_CHILD_SIZE,
    metadata: dict | None = None,
) -> tuple[list[Chunk], list[Chunk]]:
    """
    Parent-child hierarchy: retrieve child, return parent for context.
    """
    metadata = metadata or {}
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs and text.strip():
        paragraphs = [text.strip()]

    parents: list[Chunk] = []
    children: list[Chunk] = []
    current_parts: list[str] = []
    current_len = 0

    def flush_parent() -> None:
        nonlocal current_parts, current_len
        if not current_parts:
            return
        pid = f"parent_{len(parents)}"
        parent_text = "\n\n".join(current_parts).strip()
        parents.append(
            Chunk(
                text=parent_text,
                metadata={**metadata, "chunk_type": "parent", "parent_id": pid},
                parent_id=pid,
            )
        )
        for start in range(0, len(parent_text), max(1, child_size)):
            child_text = parent_text[start : start + child_size].strip()
            if not child_text:
                continue
            children.append(
                Chunk(
                    text=child_text,
                    metadata={**metadata, "chunk_type": "child", "parent_id": pid},
                    parent_id=pid,
                )
            )
        current_parts = []
        current_len = 0

    for paragraph in paragraphs:
        if current_parts and current_len + len(paragraph) + 2 > parent_size:
            flush_parent()
        current_parts.append(paragraph)
        current_len += len(paragraph) + 2

    flush_parent()
    return parents, children


def chunk_structure_aware(text: str, metadata: dict | None = None) -> list[Chunk]:
    """
    Parse markdown headers and keep each section intact.
    """
    metadata = metadata or {}
    header_pattern = re.compile(r"(^#{1,6}\s+.+$)", re.MULTILINE)
    parts = header_pattern.split(text)
    chunks: list[Chunk] = []
    current_header = ""
    current_content = ""

    def append_section(header: str, content: str) -> None:
        body = "\n".join(part for part in [header, content.strip()] if part).strip()
        if body:
            chunks.append(
                Chunk(
                    text=body,
                    metadata={**metadata, "section": header.strip(), "strategy": "structure"},
                )
            )

    if len(parts) == 1:
        if text.strip():
            chunks.append(
                Chunk(
                    text=text.strip(),
                    metadata={**metadata, "section": "", "strategy": "structure"},
                )
            )
        return chunks

    for part in parts:
        if header_pattern.fullmatch(part or ""):
            if current_header or current_content.strip():
                append_section(current_header, current_content)
            current_header = part.strip()
            current_content = ""
        else:
            current_content += part

    append_section(current_header, current_content)
    return chunks


def compare_strategies(documents: list[dict]) -> dict:
    """
    Run all strategies on documents and compare.
    """

    def stats(chunks: list[Chunk]) -> dict:
        lengths = [len(c.text) for c in chunks if c.text]
        if not lengths:
            return {"num_chunks": 0, "avg_length": 0, "min_length": 0, "max_length": 0}
        return {
            "num_chunks": len(lengths),
            "avg_length": round(sum(lengths) / len(lengths), 2),
            "min_length": min(lengths),
            "max_length": max(lengths),
        }

    basic_chunks: list[Chunk] = []
    semantic_chunks: list[Chunk] = []
    parents: list[Chunk] = []
    children: list[Chunk] = []
    structure_chunks: list[Chunk] = []

    for doc in documents:
        text = doc.get("text", "")
        meta = doc.get("metadata", {})
        basic_chunks.extend(chunk_basic(text, metadata=meta))
        semantic_chunks.extend(chunk_semantic(text, metadata=meta))
        p, c = chunk_hierarchical(text, metadata=meta)
        parents.extend(p)
        children.extend(c)
        structure_chunks.extend(chunk_structure_aware(text, metadata=meta))

    results = {
        "basic": stats(basic_chunks),
        "semantic": stats(semantic_chunks),
        "hierarchical": {
            "num_parents": len(parents),
            "num_children": len(children),
            **stats(children),
        },
        "structure": stats(structure_chunks),
    }

    print("Strategy       | Chunks | Avg Len | Min | Max")
    print("-" * 50)
    for name in ["basic", "semantic", "hierarchical", "structure"]:
        stat = results[name]
        chunk_count = stat.get("num_chunks", stat.get("num_children", 0))
        print(
            f"{name:<13} | {chunk_count:>6} | {stat['avg_length']:>7} | "
            f"{stat['min_length']:>3} | {stat['max_length']:>3}"
        )
    return results


def main() -> None:
    docs = load_documents()
    print(f"Loaded {len(docs)} documents")
    if not docs:
        print("Warning: no extractable text found in data/. PDFs may be scanned images without OCR.")
    results = compare_strategies(docs)
    for name, stats in results.items():
        print(f"  {name}: {stats}")


if __name__ == "__main__":
    main()
