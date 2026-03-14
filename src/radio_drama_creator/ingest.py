from __future__ import annotations

from pathlib import Path
import subprocess

from .models import DocumentChunk


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".rtf", ".doc", ".docx"}


def load_document(path: str, chunk_words: int = 240) -> list[DocumentChunk]:
    source = Path(path).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Document not found: {source}")

    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported document type {source.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    text = _read_document(source)
    cleaned = _normalize_text(text)
    if not cleaned:
        raise ValueError(f"No readable text found in {source}")

    words = cleaned.split()
    chunks: list[DocumentChunk] = []
    for index, start in enumerate(range(0, len(words), chunk_words)):
        slice_words = words[start : start + chunk_words]
        chunk_text = " ".join(slice_words)
        chunks.append(
            DocumentChunk(
                index=index,
                source_path=str(source),
                text=chunk_text,
                word_count=len(slice_words),
            )
        )
    return chunks


def _read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "PDF support requires the optional dependency `pypdf`. "
                "Install with `pip install .[pdf]`."
            ) from exc

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    result = subprocess.run(
        ["/usr/bin/textutil", "-convert", "txt", "-stdout", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r", "\n").split("\n")]
    merged = " ".join(line for line in lines if line)
    return " ".join(merged.split())
