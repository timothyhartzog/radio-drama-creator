"""Enhanced text extraction supporting Calibre/textract in addition to native readers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Generator

from .utils.shell_utils import check_if_calibre_is_installed, run_shell_command


def extract_text_from_book_using_calibre(book_path: str) -> str:
    """Extract text from a book using Calibre's ebook-convert utility."""
    if not check_if_calibre_is_installed():
        raise RuntimeError(
            "Calibre is not installed. Install it from https://calibre-ebook.com/"
        )
    result = run_shell_command(f'ebook-convert "{book_path}" /dev/stdout --txt-output')
    return result.stdout


def extract_text_from_book_using_textract(book_path: str) -> str:
    """Extract text from a book using the textract library."""
    try:
        import textract
    except ImportError as exc:
        raise RuntimeError(
            "textract is not installed. Install with: pip install textract"
        ) from exc
    raw = textract.process(book_path)
    return raw.decode("utf-8", errors="ignore")


def extract_main_content(
    text: str,
    start_marker: str = "PROLOGUE",
    end_marker: str = "ABOUT THE AUTHOR",
) -> str:
    """Extract the main content of a book between two markers (case-insensitive)."""
    lower = text.lower()
    start_idx = lower.find(start_marker.lower())
    end_idx = lower.rfind(end_marker.lower())

    if start_idx == -1:
        start_idx = 0
    if end_idx == -1 or end_idx <= start_idx:
        end_idx = len(text)

    return text[start_idx:end_idx].strip()


def normalize_line_breaks(text: str) -> str:
    """Normalize inconsistent line breaks into clean paragraphs."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fix_unterminated_quotes(text: str) -> str:
    """Fix unterminated quotes in text."""
    lines = text.split("\n")
    fixed_lines = []
    for line in lines:
        open_count = line.count("\u201c") + line.count('"')
        close_count = line.count("\u201d") + line.count('"')
        if open_count > close_count:
            line = line + "\u201d"
        fixed_lines.append(line)
    return "\n".join(fixed_lines)


def process_book_and_extract_text(
    book_path: str, text_decoding_option: str = "textract"
) -> Generator[str, None, None]:
    """Extract and clean text from a book file.

    Yields status messages as processing progresses.
    """
    yield f"Starting text extraction from: {book_path}"

    if text_decoding_option == "calibre":
        yield "Using Calibre for extraction..."
        raw_text = extract_text_from_book_using_calibre(book_path)
    else:
        yield "Using textract for extraction..."
        raw_text = extract_text_from_book_using_textract(book_path)

    yield f"Extracted {len(raw_text)} characters of raw text."

    yield "Normalizing line breaks..."
    text = normalize_line_breaks(raw_text)

    yield "Extracting main content..."
    text = extract_main_content(text)

    yield "Fixing unterminated quotes..."
    text = fix_unterminated_quotes(text)

    output_path = "converted_book.txt"
    Path(output_path).write_text(text, encoding="utf-8")
    yield f"Saved processed text to {output_path} ({len(text)} characters)."
    yield "Text extraction complete."
