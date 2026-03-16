"""Ebook metadata extraction utility.

Ported from audiobook-creator-mlx: utils/audiobook_utils.py (metadata portion).
"""

from __future__ import annotations

import os
from pathlib import Path


def get_ebook_metadata_with_cover(book_path: str) -> dict:
    """Extract metadata from an ebook and save its cover image.

    Returns dict containing the ebook's metadata.
    Requires the ebooklib package for EPUB files.
    """
    metadata: dict = {
        "title": "",
        "author": "",
        "language": "",
        "description": "",
        "cover_path": "",
    }

    ext = Path(book_path).suffix.lower()

    if ext == ".epub":
        try:
            from ebooklib import epub

            book = epub.read_epub(book_path)
            title = book.get_metadata("DC", "title")
            metadata["title"] = title[0][0] if title else ""

            creator = book.get_metadata("DC", "creator")
            metadata["author"] = creator[0][0] if creator else ""

            language = book.get_metadata("DC", "language")
            metadata["language"] = language[0][0] if language else ""

            description = book.get_metadata("DC", "description")
            metadata["description"] = description[0][0] if description else ""

            for item in book.get_items():
                if item.get_type() == 3:  # EPUB cover image type
                    cover_dir = os.path.dirname(book_path)
                    cover_path = os.path.join(cover_dir, "cover.jpg")
                    with open(cover_path, "wb") as fh:
                        fh.write(item.get_content())
                    metadata["cover_path"] = cover_path
                    break
        except ImportError:
            metadata["error"] = "ebooklib is required for EPUB metadata extraction."
        except Exception as exc:
            metadata["error"] = str(exc)

    elif ext == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(book_path)
            info = reader.metadata
            if info:
                metadata["title"] = info.title or ""
                metadata["author"] = info.author or ""
        except ImportError:
            metadata["error"] = "pypdf is required for PDF metadata extraction."
        except Exception as exc:
            metadata["error"] = str(exc)

    else:
        metadata["title"] = Path(book_path).stem
        metadata["note"] = f"Metadata extraction not supported for {ext} files."

    return metadata
