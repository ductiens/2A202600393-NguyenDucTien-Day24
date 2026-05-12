"""
PDF Parser — Trích xuất text từ scanned PDF tiếng Việt.

- Nghị định 13/2023: Vision model (Groq), batch 4 trang/request
- BCTC (tờ khai thuế): Vision model (Groq), 1 request toàn bộ

Output: data/*.md để load_documents() trong m1_chunking.py đọc được.

Usage:
    python src/pdf_parser.py                     # parse cả 2, skip nếu đã tồn tại
    python src/pdf_parser.py --reparse           # force re-parse cả 2
    python src/pdf_parser.py --openrouter        # dùng OpenRouter thay Groq
"""

import base64
import os
import sys
from pathlib import Path

# Fix Windows console UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_DIR


# ── Helpers ───────────────────────────────────────────────────────────────────

def pdf_to_images(pdf_path: str, dpi: int = 200) -> list:
    """Convert PDF pages → list of PIL Images dùng PyMuPDF (không cần Poppler)."""
    import fitz
    from PIL import Image
    import io

    doc = fitz.open(pdf_path)
    zoom = dpi / 72  # 72 là DPI mặc định của PDF
    mat = fitz.Matrix(zoom, zoom)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("jpeg")))
        images.append(img)
    doc.close()
    return images


def image_to_base64(image) -> str:
    """PIL Image → base64 string (JPEG)."""
    import io
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ── Method 1: EasyOCR — Nghị định (văn bản thuần) ────────────────────────────

def parse_with_easyocr(pdf_path: str, dpi: int = 150) -> str:
    """
    Dùng EasyOCR để extract text từ scanned PDF tiếng Việt.
    Phù hợp với văn bản thuần túy, không có bảng phức tạp.
    """
    import gc
    import easyocr
    import numpy as np

    print("  [EasyOCR] Loading model (lần đầu mất ~30s)...")
    reader = easyocr.Reader(["vi", "en"], gpu=False)

    images = pdf_to_images(pdf_path, dpi=dpi)
    print(f"  [EasyOCR] Processing {len(images)} pages (dpi={dpi})...")

    full_text = []
    for i, img in enumerate(images):
        print(f"  [EasyOCR] Page {i+1}/{len(images)}...")
        # Giảm kích thước nếu ảnh quá lớn (tránh OOM)
        max_side = 2000
        w, h = img.size
        if max(w, h) > max_side:
            scale = max_side / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)))

        img_np = np.array(img)
        results = reader.readtext(img_np, detail=0, paragraph=True,
                                  canvas_size=1280, mag_ratio=1.5)
        page_text = "\n".join(results)
        full_text.append(f"<!-- Trang {i+1} -->\n{page_text}")

        # Giải phóng memory sau mỗi trang
        del img_np, img
        gc.collect()

    return "\n\n".join(full_text)


# ── Method 2: Vision Model — Nghị định (văn bản dài, batch theo trang) ───────

_TEXT_DOC_PROMPT = """\
Đây là trang {start}–{end} (trên tổng {total} trang) của Nghị định 13/2023/NĐ-CP \
về Bảo vệ dữ liệu cá nhân, bản scan tiếng Việt.

Yêu cầu:
1. Trích xuất TOÀN BỘ văn bản, đúng thứ tự, không bỏ sót điều khoản nào.
2. Dấu tiếng Việt phải chính xác (ví dụ: "đồng ý" không được viết thành "đồng~" hay "đồng*").
3. Giữ nguyên cấu trúc: "Chương X", "Điều X.", "Khoản X.", danh sách a) b) c).
4. Dùng Markdown: ## cho Chương, ### cho Điều, text thường cho nội dung.
5. Chỉ trả về nội dung đã trích xuất, không giải thích thêm.\
"""


def _call_groq_vision(client, images: list, prompt: str) -> str:
    """Gửi list ảnh + prompt tới Groq Vision, trả về text."""
    content = []
    for i, img in enumerate(images):
        content.append({"type": "text", "text": f"--- Trang {i+1}/{len(images)} ---"})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_to_base64(img)}"},
        })
    content.append({"type": "text", "text": prompt})

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": content}],
        max_tokens=8192,
    )
    return response.choices[0].message.content


def parse_nghi_dinh_groq(pdf_path: str, batch_size: int = 4) -> str:
    """
    Parse Nghị định bằng Groq Vision, batch {batch_size} trang/request.
    Kết quả sạch hơn EasyOCR vì model hiểu ngữ nghĩa tiếng Việt.
    """
    from groq import Groq
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY chưa được set trong .env")

    client = Groq(api_key=api_key)
    images = pdf_to_images(pdf_path, dpi=150)
    total = len(images)
    print(f"  [Groq Vision] {total} pages, batch_size={batch_size}...")

    parts = []
    for i in range(0, total, batch_size):
        batch = images[i : i + batch_size]
        start, end = i + 1, min(i + batch_size, total)
        print(f"  [Groq Vision] Pages {start}–{end}/{total}...")
        prompt = _TEXT_DOC_PROMPT.format(start=start, end=end, total=total)
        text = _call_groq_vision(client, batch, prompt)
        parts.append(text)

    return "\n\n".join(parts)


# ── Method 3: Vision Model — BCTC (bảng kéo dài nhiều trang) ─────────────────

_BCTC_PROMPT = """\
Đây là {n_pages} trang ảnh của một tờ khai thuế GTGT (Mẫu 01/GTGT) tiếng Việt \
bị scan thành ảnh.

Tờ khai có một bảng số liệu lớn BẮT ĐẦU ở trang 1 và TIẾP TỤC sang trang 2 — \
hai trang là một bảng liên tục, KHÔNG phải hai bảng riêng biệt.

Yêu cầu:
1. Trích xuất TOÀN BỘ nội dung văn bản theo đúng thứ tự xuất hiện.
2. Tái tạo bảng số liệu thành MỘT bảng Markdown duy nhất, \
   gộp dữ liệu từ cả {n_pages} trang (không lặp header bảng ở trang 2).
3. Số liệu (tiền VNĐ, mã số) phải chính xác tuyệt đối — \
   không làm tròn, không bỏ sót chữ số.
4. Giữ nguyên mã chỉ tiêu trong ngoặc vuông, ví dụ [21], [22], [23].
5. Chỉ trả về nội dung đã trích xuất, không giải thích thêm.\
"""


def parse_bctc_groq(pdf_path: str) -> str:
    """
    Gửi tất cả trang BCTC trong 1 request Groq Vision.
    Bảng số liệu kéo qua 2 trang → gộp thành 1 bảng Markdown.
    """
    from groq import Groq
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY chưa được set trong .env")

    images = pdf_to_images(pdf_path, dpi=200)
    n = len(images)
    print(f"  [Groq Vision] {n} pages, sending in 1 request...")

    # Ghép tất cả ảnh + prompt vào 1 message
    content = []
    for i, img in enumerate(images):
        content.append({
            "type": "text",
            "text": f"--- Trang {i+1}/{n} ---",
        })
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_to_base64(img)}"},
        })
    content.append({
        "type": "text",
        "text": _BCTC_PROMPT.format(n_pages=n),
    })

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": content}],
        max_tokens=8192,
    )
    return response.choices[0].message.content


def parse_bctc_openrouter(pdf_path: str) -> str:
    """
    Fallback: OpenRouter vision (google/gemini-flash-1.5 hoặc qwen/qwen-2-vl-7b).
    Gửi tất cả trang trong 1 request, gộp bảng 2 trang thành 1.
    """
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY chưa được set trong .env")

    images = pdf_to_images(pdf_path, dpi=200)
    n = len(images)
    print(f"  [OpenRouter Vision] {n} pages, sending in 1 request...")

    content = []
    for i, img in enumerate(images):
        content.append({
            "type": "text",
            "text": f"--- Trang {i+1}/{n} ---",
        })
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_to_base64(img)}"},
        })
    content.append({
        "type": "text",
        "text": _BCTC_PROMPT.format(n_pages=n),
    })

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    response = client.chat.completions.create(
        model="google/gemini-flash-1.5",
        messages=[{"role": "user", "content": content}],
        max_tokens=8192,
    )
    return response.choices[0].message.content


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_all(use_groq: bool = True) -> None:
    """Parse cả 2 file PDF và lưu ra data/*.md."""
    from dotenv import load_dotenv
    load_dotenv()

    nghi_dinh_pdf = os.path.join(DATA_DIR, "Nghi_dinh_so_13-2023_ve_bao_ve_du_lieu_ca_nhan_508ee.pdf")
    bctc_pdf = os.path.join(DATA_DIR, "BCTC.pdf")

    # ── Nghị định → EasyOCR ──
    out_nghi_dinh = os.path.join(DATA_DIR, "nghi_dinh_13_2023.md")
    if os.path.exists(out_nghi_dinh):
        print(f"[SKIP] {out_nghi_dinh} đã tồn tại.")
    else:
        print("\n[1/2] Parsing Nghị định 13/2023 bằng EasyOCR...")
        text = parse_with_easyocr(nghi_dinh_pdf)
        Path(out_nghi_dinh).write_text(text, encoding="utf-8")
        print(f"  → Saved: {out_nghi_dinh} ({len(text):,} chars)")

    # ── BCTC → Vision Model ──
    out_bctc = os.path.join(DATA_DIR, "bctc_q4_2024.md")
    if os.path.exists(out_bctc):
        print(f"[SKIP] {out_bctc} đã tồn tại.")
    else:
        print("\n[2/2] Parsing BCTC bằng Vision Model...")
        try:
            text = parse_bctc_groq(bctc_pdf) if use_groq else parse_bctc_openrouter(bctc_pdf)
        except Exception as e:
            print(f"  [WARN] Primary failed ({e}), thử OpenRouter...")
            text = parse_bctc_openrouter(bctc_pdf)

        Path(out_bctc).write_text(text, encoding="utf-8")
        print(f"  → Saved: {out_bctc} ({len(text):,} chars)")

    print("\n[DONE] Files saved to data/. load_documents() sẽ tự đọc *.md")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--openrouter", action="store_true",
                    help="Dùng OpenRouter thay vì Groq cho BCTC")
    args = ap.parse_args()
    parse_all(use_groq=not args.openrouter)
