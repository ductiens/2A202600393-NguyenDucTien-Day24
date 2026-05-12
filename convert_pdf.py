"""
Convert PDF files to Markdown using Microsoft's MarkItDown library.

Usage:
    # Convert all PDFs in data/ directory
    python convert_pdf.py

    # Convert a specific PDF file
    python convert_pdf.py path/to/file.pdf

    # Convert with custom output directory
    python convert_pdf.py --output-dir ./output

Install:
    pip install "markitdown[pdf]"
"""

import argparse
import glob
import os
import sys
import time


def convert_pdf_to_markdown(pdf_path: str, output_dir: str | None = None) -> str | None:
    """
    Convert a single PDF file to Markdown using MarkItDown.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to save the .md file. Defaults to same directory as PDF.

    Returns:
        Path to the output markdown file, or None if conversion failed.
    """
    try:
        from markitdown import MarkItDown
    except ImportError:
        print("ERROR: markitdown is not installed.")
        print('  Install with: pip install "markitdown[pdf]"')
        sys.exit(1)

    if not os.path.isfile(pdf_path):
        print(f"  SKIP: File not found: {pdf_path}")
        return None

    # Determine output path
    basename = os.path.splitext(os.path.basename(pdf_path))[0]
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{basename}.md")
    else:
        output_path = os.path.join(os.path.dirname(pdf_path), f"{basename}.md")

    print(f"  Converting: {os.path.basename(pdf_path)}")
    start = time.perf_counter()

    try:
        md = MarkItDown()
        result = md.convert(pdf_path)
        text = result.text_content

        if not text or not text.strip():
            print(f"  WARN: No text extracted from {os.path.basename(pdf_path)}")
            return None

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        elapsed = time.perf_counter() - start
        line_count = len(text.strip().splitlines())
        char_count = len(text)
        print(f"  OK: {os.path.basename(output_path)} ({line_count} lines, {char_count:,} chars, {elapsed:.1f}s)")
        return output_path

    except Exception as e:
        print(f"  ERROR: Failed to convert {os.path.basename(pdf_path)}: {e}")
        return None


def convert_all_pdfs(data_dir: str, output_dir: str | None = None) -> list[str]:
    """
    Convert all PDF files in a directory to Markdown.

    Args:
        data_dir: Directory containing PDF files.
        output_dir: Directory to save .md files. Defaults to same as data_dir.

    Returns:
        List of paths to successfully converted markdown files.
    """
    pdf_files = sorted(glob.glob(os.path.join(data_dir, "*.pdf")))

    if not pdf_files:
        print(f"No PDF files found in {data_dir}")
        return []

    print(f"Found {len(pdf_files)} PDF file(s) in {data_dir}\n")

    converted = []
    for pdf_path in pdf_files:
        result = convert_pdf_to_markdown(pdf_path, output_dir=output_dir)
        if result:
            converted.append(result)
        print()

    return converted


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF files to Markdown using Microsoft MarkItDown"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Path to a specific PDF file. If not provided, converts all PDFs in data/ directory.",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="Output directory for .md files. Defaults to same directory as input.",
    )
    parser.add_argument(
        "--data-dir", "-d",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"),
        help="Data directory to scan for PDFs (default: ./data)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("PDF to Markdown Converter (MarkItDown)")
    print("=" * 60)
    print()

    start = time.time()

    if args.input:
        # Convert a single file
        result = convert_pdf_to_markdown(args.input, output_dir=args.output_dir)
        converted = [result] if result else []
    else:
        # Convert all PDFs in data directory
        converted = convert_all_pdfs(args.data_dir, output_dir=args.output_dir)

    elapsed = time.time() - start
    print("=" * 60)
    print(f"Done: {len(converted)} file(s) converted in {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
