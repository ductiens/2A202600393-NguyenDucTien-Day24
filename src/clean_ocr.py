"""
Clean OCR errors in nghi_dinh_13_2023.md using LLM (text model, no vision).

Usage:
    python src/clean_ocr.py
"""

import os
import re
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR

INPUT_FILE   = os.path.join(DATA_DIR, "nghi_dinh_13_2023.md")
OUTPUT_FILE  = os.path.join(DATA_DIR, "nghi_dinh_13_2023.md")
PROGRESS_DIR = os.path.join(DATA_DIR, ".ocr_progress")  # lưu từng trang đã xử lý

_CLEAN_PROMPT = """\
Đoạn văn bản dưới đây được trích xuất từ Nghị định 13/2023/NĐ-CP bằng OCR, \
có thể chứa lỗi nhận dạng ký tự tiếng Việt.

Nhiệm vụ:
1. Sửa tất cả lỗi dấu tiếng Việt (ví dụ: "đồng~" → "đồng ý", "dược" → "được", "Ỉái" → "lái").
2. Xóa ký tự rác (ký tự lạ, %, ~, * xuất hiện giữa chữ tiếng Việt).
3. Tái cấu trúc thành Markdown sạch:
   - ## cho "Chương X"
   - ### cho "Điều X."
   - Danh sách a) b) c) giữ nguyên, mỗi mục xuống dòng riêng.
   - Khoản 1. 2. 3. xuống dòng riêng.
4. KHÔNG thêm, KHÔNG bỏ nội dung — chỉ sửa lỗi và format.
5. Chỉ trả về văn bản đã sửa, không giải thích.

Văn bản cần sửa:
{text}"""

SLEEP_BETWEEN_PAGES = 0.5  # OpenRouter không cần sleep nhiều
MAX_RETRIES = 5
OPENROUTER_MODEL = "google/gemini-2.0-flash-001"  # nhanh, rẻ, tiếng Việt tốt


def split_by_page(content: str) -> list[tuple[int, str]]:
    """Tách file theo marker <!-- Trang X -->, trả về list (page_num, text)."""
    parts = re.split(r"(<!-- Trang \d+ -->)", content)
    pages = []
    i = 1
    while i < len(parts):
        header = parts[i]
        body   = parts[i + 1] if i + 1 < len(parts) else ""
        num = int(re.search(r"\d+", header).group())
        pages.append((num, body.strip()))
        i += 2
    return pages


def clean_page(client, text: str) -> str:
    """Gọi OpenRouter với retry + backoff khi gặp 429."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[{"role": "user", "content": _CLEAN_PROMPT.format(text=text)}],
                max_tokens=4096,
                temperature=0,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            msg = str(e)
            if "429" in msg or "rate" in msg.lower():
                wait = 5 * attempt
                m = re.search(r"try again in (\d+(?:\.\d+)?)s", msg)
                if m:
                    wait = float(m.group(1)) + 1
                print(f" [429] chờ {wait:.0f}s (attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError(f"Vẫn lỗi sau {MAX_RETRIES} lần thử.")


def main():
    from dotenv import load_dotenv
    from openai import OpenAI
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY chưa set trong .env")

    content = Path(INPUT_FILE).read_text(encoding="utf-8")
    pages = split_by_page(content)
    total = len(pages)
    print(f"[clean_ocr] {total} pages found. Model: {OPENROUTER_MODEL}")

    os.makedirs(PROGRESS_DIR, exist_ok=True)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    for num, text in pages:
        cache_file = Path(PROGRESS_DIR) / f"page_{num:03d}.md"

        # Skip nếu đã xử lý
        if cache_file.exists():
            print(f"  Page {num:2d}/{total} [cached]")
            continue

        print(f"  Page {num:2d}/{total} cleaning...", end=" ", flush=True)

        if not text.strip():
            cache_file.write_text("", encoding="utf-8")
            print("(empty)")
            continue

        cleaned = clean_page(client, text)
        cache_file.write_text(cleaned, encoding="utf-8")
        print("done")

        time.sleep(SLEEP_BETWEEN_PAGES)

    # Gộp tất cả trang đã xử lý
    print("\nMerging pages...")
    parts = []
    for num, _ in pages:
        cache_file = Path(PROGRESS_DIR) / f"page_{num:03d}.md"
        cleaned = cache_file.read_text(encoding="utf-8").strip()
        if cleaned:
            parts.append(f"## Trang {num}\n\n{cleaned}")

    output = "\n\n---\n\n".join(parts)
    Path(OUTPUT_FILE).write_text(output, encoding="utf-8")
    print(f"[DONE] Saved to {OUTPUT_FILE} ({len(output):,} chars)")


if __name__ == "__main__":
    main()
