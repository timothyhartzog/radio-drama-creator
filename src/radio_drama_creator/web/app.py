"""FastAPI application for the Radio Drama Creator web interface."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..config import AppConfig
from ..metadata import get_ebook_metadata_with_cover
from ..mlx_registry import available_model_presets
from ..pipeline import run_pipeline
from ..utils.audio_utils import convert_audio_file_formats, merge_chapters_to_m4b
from ..utils.shell_utils import (
    check_if_calibre_is_installed,
    check_if_ffmpeg_is_installed,
)

app = FastAPI(
    title="Radio Drama Creator",
    description="Turn documents into golden-age style radio dramas",
    version="0.1.0",
)

TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

UPLOAD_DIR = Path(tempfile.gettempdir()) / "radio_drama_uploads"
OUTPUT_DIR = Path(tempfile.gettempdir()) / "radio_drama_output"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_jobs: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page with the production form."""
    presets = available_model_presets()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "script_presets": [p.key for p in presets["script"]],
        "tts_presets": [p.key for p in presets["tts"]],
        "genres": [
            "mystery", "thriller", "romance", "sci-fi", "horror",
            "comedy", "drama", "noir", "western", "fantasy",
        ],
        "renderers": ["script", "say", "mlx_audio"],
    })


# ---------------------------------------------------------------------------
# Health / Status
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    """System health check."""
    return {
        "status": "ok",
        "calibre_installed": check_if_calibre_is_installed(),
        "ffmpeg_installed": check_if_ffmpeg_is_installed(),
    }


@app.get("/api/models")
async def list_models():
    """List available MLX model presets."""
    presets = available_model_presets()
    return {
        role: [{"key": p.key, "repo": p.repo, "notes": p.notes} for p in items]
        for role, items in presets.items()
    }


# ---------------------------------------------------------------------------
# Book Upload & Metadata
# ---------------------------------------------------------------------------

@app.post("/api/upload")
async def upload_book(file: UploadFile = File(...)):
    """Upload a book/document for processing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected.")

    file_id = uuid.uuid4().hex[:12]
    ext = Path(file.filename).suffix
    save_path = UPLOAD_DIR / f"{file_id}{ext}"
    with open(save_path, "wb") as fh:
        shutil.copyfileobj(file.file, fh)

    return {"file_id": file_id, "filename": file.filename, "path": str(save_path)}


@app.get("/api/metadata/{file_id}")
async def get_metadata(file_id: str):
    """Extract metadata from an uploaded ebook."""
    matches = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="File not found.")
    metadata = get_ebook_metadata_with_cover(str(matches[0]))
    return metadata


# ---------------------------------------------------------------------------
# Production Pipeline
# ---------------------------------------------------------------------------

@app.post("/api/produce")
async def produce_radio_drama(
    file_id: str = Form(...),
    genre: str = Form("mystery"),
    scenes: int = Form(3),
    lines_per_scene: int = Form(8),
    script_backend: str = Form("heuristic"),
    script_preset: str = Form("qwen3-8b"),
    renderer: str = Form("script"),
    tts_preset: str = Form("dia-1.6b"),
    tone: str = Form("suspenseful, theatrical, intimate"),
):
    """Run the full radio drama production pipeline."""
    matches = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Uploaded file not found.")

    source_path = str(matches[0])
    job_id = uuid.uuid4().hex[:12]
    job_output = OUTPUT_DIR / job_id
    job_output.mkdir(parents=True, exist_ok=True)

    config = AppConfig()
    config.style.genre = genre
    config.style.scenes = scenes
    config.style.lines_per_scene = lines_per_scene
    config.style.tone = tone
    config.models.script_backend = script_backend
    config.models.script_preset = script_preset
    config.audio.renderer = renderer
    config.audio.tts_preset = tts_preset

    _jobs[job_id] = {"status": "running", "output_dir": str(job_output)}

    try:
        package = run_pipeline(source_path, str(job_output), config)
        _jobs[job_id]["status"] = "complete"
        _jobs[job_id]["result"] = package.to_dict()
        return {"job_id": job_id, "status": "complete", "output_dir": str(job_output)}
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Check the status of a production job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _jobs[job_id]


@app.get("/api/jobs/{job_id}/files")
async def list_job_files(job_id: str):
    """List output files for a completed job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_dir = Path(_jobs[job_id]["output_dir"])
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Output directory missing.")
    files = [
        {"name": f.name, "size": f.stat().st_size}
        for f in sorted(job_dir.iterdir())
        if f.is_file()
    ]
    return {"job_id": job_id, "files": files}


@app.get("/api/jobs/{job_id}/download/{filename}")
async def download_file(job_id: str, filename: str):
    """Download a specific output file."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    file_path = Path(_jobs[job_id]["output_dir"]) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(str(file_path), filename=filename)


# ---------------------------------------------------------------------------
# Audio Format Conversion
# ---------------------------------------------------------------------------

@app.post("/api/convert")
async def convert_audio(
    job_id: str = Form(...),
    filename: str = Form(...),
    output_format: str = Form(...),
):
    """Convert an output audio file to another format."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_dir = Path(_jobs[job_id]["output_dir"])
    source = job_dir / filename
    if not source.exists():
        raise HTTPException(status_code=404, detail="Source file not found.")

    stem = source.stem
    input_fmt = source.suffix.lstrip(".")
    try:
        convert_audio_file_formats(input_fmt, output_format, str(job_dir), stem)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {"converted": f"{stem}.{output_format}"}


# ---------------------------------------------------------------------------
# Character Identification (from audiobook-creator)
# ---------------------------------------------------------------------------

@app.post("/api/identify-characters")
async def identify_characters(
    file_id: str = Form(...),
    protagonist: str = Form(""),
):
    """Run character identification on an uploaded book."""
    from ..book_extraction import process_book_and_extract_text
    from ..character_identification import identify_characters_and_output_book_to_jsonl

    matches = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="File not found.")

    source_path = str(matches[0])
    messages = []

    try:
        text = Path(source_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        for msg in process_book_and_extract_text(source_path, "calibre"):
            messages.append(msg)
        text = Path("converted_book.txt").read_text(encoding="utf-8", errors="ignore")

    for msg in identify_characters_and_output_book_to_jsonl(
        text, protagonist or "Protagonist", output_dir=str(UPLOAD_DIR)
    ):
        messages.append(msg)

    chars_file = UPLOAD_DIR / "characters_info.json"
    characters = []
    if chars_file.exists():
        characters = json.loads(chars_file.read_text(encoding="utf-8"))

    return {"messages": messages, "characters": characters}


# ---------------------------------------------------------------------------
# Book Text Extraction
# ---------------------------------------------------------------------------

@app.post("/api/extract-text")
async def extract_text(
    file_id: str = Form(...),
    method: str = Form("native"),
):
    """Extract text from an uploaded book using the specified method."""
    matches = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="File not found.")

    source_path = str(matches[0])

    if method == "native":
        from ..ingest import load_document
        chunks = load_document(source_path)
        text = " ".join(c.text for c in chunks)
        return {"method": "native", "char_count": len(text), "preview": text[:2000]}
    else:
        from ..book_extraction import process_book_and_extract_text
        messages = list(process_book_and_extract_text(source_path, method))
        text = Path("converted_book.txt").read_text(encoding="utf-8", errors="ignore") if Path("converted_book.txt").exists() else ""
        return {"method": method, "messages": messages, "char_count": len(text), "preview": text[:2000]}


def create_app() -> FastAPI:
    """Factory function returning the configured FastAPI app."""
    return app
