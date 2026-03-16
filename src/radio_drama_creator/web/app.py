"""FastAPI application for the Radio Drama Creator web interface."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..config import AppConfig
from ..metadata import get_ebook_metadata_with_cover
from ..mlx_registry import available_model_presets
from ..model_manager import (
    check_model_downloaded,
    delete_model,
    download_model,
    get_cache_summary,
    get_model_info_from_hub,
    list_local_models,
)
from ..pipeline import run_pipeline
from ..utils.audio_utils import convert_audio_file_formats
from ..utils.shell_utils import (
    check_if_calibre_is_installed,
    check_if_ffmpeg_is_installed,
)

logger = logging.getLogger("radio_drama_creator.web")

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".rtf", ".doc", ".docx", ".epub"}
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_OUTPUT_FORMATS = {"mp3", "wav", "opus", "flac", "aac", "pcm", "m4a"}
ALLOWED_BACKENDS = {"heuristic", "mlx"}
ALLOWED_RENDERERS = {"script", "say", "mlx_audio"}

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
# Global error handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return structured JSON errors."""
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "error_type": type(exc).__name__,
        },
    )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_file_id(file_id: str) -> Path:
    """Validate a file_id and return the path, or raise HTTPException."""
    if not file_id or not file_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid file ID.")
    matches = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matches:
        raise HTTPException(status_code=404, detail="Uploaded file not found.")
    return matches[0]


def _validate_job_id(job_id: str) -> dict:
    """Validate a job_id and return job data, or raise HTTPException."""
    if not job_id or not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid job ID.")
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    return _jobs[job_id]


def _sanitize_filename(filename: str) -> str:
    """Strip path components to prevent directory traversal."""
    return Path(filename).name


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page with the production form."""
    try:
        presets = available_model_presets()
    except Exception:
        presets = {"script": [], "tts": [], "vision": []}
    return templates.TemplateResponse("index.html", {
        "request": request,
        "script_presets": [p.key for p in presets.get("script", [])],
        "tts_presets": [p.key for p in presets.get("tts", [])],
        "genres": [
            "mystery", "thriller", "romance", "sci-fi", "horror",
            "comedy", "drama", "noir", "western", "fantasy",
        ],
        "renderers": sorted(ALLOWED_RENDERERS),
    })


@app.get("/catalog", response_class=HTMLResponse)
async def catalog(request: Request):
    """Function and task catalog page."""
    return templates.TemplateResponse("catalog.html", {"request": request})


@app.get("/models", response_class=HTMLResponse)
async def models_page(request: Request):
    """Model manager page."""
    return templates.TemplateResponse("models.html", {"request": request})


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
    try:
        presets = available_model_presets()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load presets: {exc}")
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

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 100 MB size limit.")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    file_id = uuid.uuid4().hex[:12]
    save_path = UPLOAD_DIR / f"{file_id}{ext}"
    try:
        save_path.write_bytes(content)
    except OSError as exc:
        logger.error("Failed to save upload: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    logger.info("Uploaded %s as %s (%d bytes)", file.filename, file_id, len(content))
    return {"file_id": file_id, "filename": file.filename, "path": str(save_path)}


@app.get("/api/metadata/{file_id}")
async def get_metadata(file_id: str):
    """Extract metadata from an uploaded ebook."""
    file_path = _validate_file_id(file_id)
    try:
        metadata = get_ebook_metadata_with_cover(str(file_path))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not extract metadata: {exc}")
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
    file_path = _validate_file_id(file_id)

    # Validate inputs
    if script_backend not in ALLOWED_BACKENDS:
        raise HTTPException(status_code=400, detail=f"Invalid backend '{script_backend}'.")
    if renderer not in ALLOWED_RENDERERS:
        raise HTTPException(status_code=400, detail=f"Invalid renderer '{renderer}'.")
    scenes = max(1, min(scenes, 20))
    lines_per_scene = max(1, min(lines_per_scene, 50))
    tone = tone[:200]

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
    logger.info("Starting job %s for file %s", job_id, file_id)

    try:
        package = run_pipeline(str(file_path), str(job_output), config)
        _jobs[job_id]["status"] = "complete"
        _jobs[job_id]["result"] = package.to_dict()
        logger.info("Job %s completed successfully", job_id)
        return {"job_id": job_id, "status": "complete", "output_dir": str(job_output)}
    except FileNotFoundError as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        raise HTTPException(status_code=404, detail=f"Source file error: {exc}")
    except ValueError as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        raise HTTPException(status_code=422, detail=f"Validation error: {exc}")
    except Exception as exc:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(exc)
        logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Check the status of a production job."""
    return _validate_job_id(job_id)


@app.get("/api/jobs/{job_id}/files")
async def list_job_files(job_id: str):
    """List output files for a completed job."""
    job = _validate_job_id(job_id)
    job_dir = Path(job["output_dir"])
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
    job = _validate_job_id(job_id)
    safe_name = _sanitize_filename(filename)
    file_path = Path(job["output_dir"]) / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    # Ensure the resolved path is within the job output directory
    try:
        file_path.resolve().relative_to(Path(job["output_dir"]).resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path.")
    return FileResponse(str(file_path), filename=safe_name)


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
    job = _validate_job_id(job_id)
    output_format = output_format.lower().strip()
    if output_format not in ALLOWED_OUTPUT_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{output_format}'. Allowed: {', '.join(sorted(ALLOWED_OUTPUT_FORMATS))}",
        )

    job_dir = Path(job["output_dir"])
    safe_name = _sanitize_filename(filename)
    source = job_dir / safe_name
    if not source.exists():
        raise HTTPException(status_code=404, detail="Source file not found.")

    stem = source.stem
    input_fmt = source.suffix.lstrip(".")
    try:
        convert_audio_file_formats(input_fmt, output_format, str(job_dir), stem)
    except FileNotFoundError:
        raise HTTPException(status_code=422, detail="ffmpeg not found. Install ffmpeg to convert audio.")
    except Exception as exc:
        logger.error("Audio conversion failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}")

    return {"converted": f"{stem}.{output_format}"}


# ---------------------------------------------------------------------------
# Character Identification
# ---------------------------------------------------------------------------

@app.post("/api/identify-characters")
async def identify_characters(
    file_id: str = Form(...),
    protagonist: str = Form(""),
):
    """Run character identification on an uploaded book."""
    from ..book_extraction import process_book_and_extract_text
    from ..character_identification import identify_characters_and_output_book_to_jsonl

    file_path = _validate_file_id(file_id)
    messages: list[str] = []

    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            for msg in process_book_and_extract_text(str(file_path), "calibre"):
                messages.append(msg)
            converted = Path("converted_book.txt")
            if not converted.exists():
                raise HTTPException(status_code=422, detail="Text extraction failed - no output produced.")
            text = converted.read_text(encoding="utf-8", errors="ignore")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Text extraction failed: {exc}")

    if not text.strip():
        raise HTTPException(status_code=422, detail="No readable text found in document.")

    try:
        for msg in identify_characters_and_output_book_to_jsonl(
            text, protagonist.strip() or "Protagonist", output_dir=str(UPLOAD_DIR)
        ):
            messages.append(msg)
    except Exception as exc:
        logger.error("Character identification failed: %s", exc, exc_info=True)
        messages.append(f"Character identification error: {exc}")

    chars_file = UPLOAD_DIR / "characters_info.json"
    characters = []
    if chars_file.exists():
        try:
            characters = json.loads(chars_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            messages.append("Warning: Could not parse character results file.")

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
    file_path = _validate_file_id(file_id)

    if method not in ("native", "calibre", "textract"):
        raise HTTPException(status_code=400, detail=f"Unknown extraction method '{method}'.")

    if method == "native":
        from ..ingest import load_document
        try:
            chunks = load_document(str(file_path))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        text = " ".join(c.text for c in chunks)
        return {"method": "native", "char_count": len(text), "preview": text[:2000]}
    else:
        from ..book_extraction import process_book_and_extract_text
        try:
            messages = list(process_book_and_extract_text(str(file_path), method))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Extraction failed: {exc}")
        converted = Path("converted_book.txt")
        text = converted.read_text(encoding="utf-8", errors="ignore") if converted.exists() else ""
        return {"method": method, "messages": messages, "char_count": len(text), "preview": text[:2000]}


# ---------------------------------------------------------------------------
# Model Manager
# ---------------------------------------------------------------------------

@app.get("/api/models/local")
async def list_local():
    """List all locally downloaded models."""
    models = list_local_models()
    summary = get_cache_summary()
    return {
        "models": [m.to_dict() for m in models],
        "summary": summary,
    }


@app.get("/api/models/registry")
async def list_registry():
    """List all registry presets with local download status."""
    presets = available_model_presets()
    result = {}
    for role, items in presets.items():
        result[role] = []
        for p in items:
            result[role].append({
                "key": p.key,
                "repo": p.repo,
                "family": p.family,
                "role": p.role,
                "notes": p.notes,
                "sample_rate": p.sample_rate,
                "downloaded": check_model_downloaded(p.repo),
            })
    return result


@app.get("/api/models/info/{repo_id:path}")
async def model_hub_info(repo_id: str):
    """Fetch model info from HuggingFace Hub without downloading."""
    if not repo_id or len(repo_id) > 200:
        raise HTTPException(status_code=400, detail="Invalid repo ID.")
    info = get_model_info_from_hub(repo_id)
    if "error" in info:
        raise HTTPException(status_code=422, detail=info["error"])
    return info


@app.post("/api/models/download")
async def download_model_endpoint(repo_id: str = Form(...)):
    """Download a model from HuggingFace Hub."""
    if not repo_id or len(repo_id) > 200:
        raise HTTPException(status_code=400, detail="Invalid repo ID.")

    messages = list(download_model(repo_id))
    success = any("complete" in m.lower() for m in messages)
    if not success:
        raise HTTPException(status_code=500, detail=messages[-1] if messages else "Download failed")
    return {"status": "downloaded", "repo_id": repo_id, "messages": messages}


@app.post("/api/models/delete")
async def delete_model_endpoint(repo_id: str = Form(...)):
    """Delete a model from the local cache."""
    if not repo_id or len(repo_id) > 200:
        raise HTTPException(status_code=400, detail="Invalid repo ID.")

    result = delete_model(repo_id)
    if result["status"] == "error":
        raise HTTPException(status_code=422, detail=result["detail"])
    return result


# ---------------------------------------------------------------------------
# Fine-Tuning (LoRA)
# ---------------------------------------------------------------------------

FINETUNE_DIR = Path(tempfile.gettempdir()) / "radio_drama_finetune"
FINETUNE_DIR.mkdir(parents=True, exist_ok=True)

_finetune_jobs: dict[str, dict] = {}


@app.get("/finetune", response_class=HTMLResponse)
async def finetune_page(request: Request):
    """Fine-tuning workflow page."""
    presets = available_model_presets()
    return templates.TemplateResponse("finetune.html", {
        "request": request,
        "script_presets": [
            {"key": p.key, "repo": p.repo, "notes": p.notes}
            for p in presets.get("script", [])
        ],
    })


@app.post("/api/finetune/upload-data")
async def finetune_upload_data(file: UploadFile = File(...)):
    """Upload a training JSONL file for fine-tuning."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected.")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".jsonl", ".json"}:
        raise HTTPException(status_code=400, detail="Only .jsonl or .json files are accepted.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty.")
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 100 MB limit.")

    # Validate JSONL structure
    lines = content.decode("utf-8", errors="replace").strip().splitlines()
    valid_count = 0
    for i, line in enumerate(lines[:5]):
        try:
            obj = json.loads(line)
            if "messages" in obj or "text" in obj or ("prompt" in obj and "completion" in obj):
                valid_count += 1
            else:
                raise HTTPException(
                    status_code=422,
                    detail=f"Line {i+1}: Expected 'messages', 'text', or 'prompt'+'completion' keys.",
                )
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail=f"Line {i+1}: Invalid JSON — {exc}")

    if valid_count == 0:
        raise HTTPException(status_code=422, detail="No valid training examples found.")

    data_id = uuid.uuid4().hex[:12]
    data_dir = FINETUNE_DIR / data_id
    data_dir.mkdir(parents=True, exist_ok=True)

    # Split: 90% train, 10% valid
    split_idx = max(1, int(len(lines) * 0.9))
    (data_dir / "train.jsonl").write_text("\n".join(lines[:split_idx]) + "\n", encoding="utf-8")
    (data_dir / "valid.jsonl").write_text("\n".join(lines[split_idx:]) + "\n", encoding="utf-8")

    return {
        "data_id": data_id,
        "total_examples": len(lines),
        "train_examples": split_idx,
        "valid_examples": len(lines) - split_idx,
        "data_dir": str(data_dir),
    }


@app.post("/api/finetune/start")
async def finetune_start(
    data_id: str = Form(...),
    base_model: str = Form("mlx-community/Qwen3-8B-4bit"),
    adapter_name: str = Form("radio_drama"),
    lora_rank: int = Form(16),
    iterations: int = Form(600),
    batch_size: int = Form(2),
    learning_rate: float = Form(1e-5),
    num_layers: int = Form(16),
    mask_prompt: bool = Form(True),
    grad_checkpoint: bool = Form(True),
):
    """Start a LoRA fine-tuning job using mlx_lm.lora."""
    # Validate data_id
    if not data_id or not data_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid data ID.")
    data_dir = FINETUNE_DIR / data_id
    if not (data_dir / "train.jsonl").exists():
        raise HTTPException(status_code=404, detail="Training data not found. Upload data first.")

    # Validate params
    lora_rank = max(4, min(lora_rank, 64))
    iterations = max(10, min(iterations, 5000))
    batch_size = max(1, min(batch_size, 16))
    num_layers = max(4, min(num_layers, 32))
    learning_rate = max(1e-7, min(learning_rate, 1e-3))
    if not base_model or len(base_model) > 200:
        raise HTTPException(status_code=400, detail="Invalid base model.")

    # Sanitize adapter name
    adapter_name = "".join(c for c in adapter_name if c.isalnum() or c in "_-")[:50] or "adapter"
    adapter_path = FINETUNE_DIR / "adapters" / adapter_name
    adapter_path.mkdir(parents=True, exist_ok=True)

    job_id = uuid.uuid4().hex[:12]
    log_path = FINETUNE_DIR / f"{job_id}.log"

    cmd = [
        "mlx_lm.lora",
        "--model", base_model,
        "--data", str(data_dir),
        "--train",
        "--batch-size", str(batch_size),
        "--iters", str(iterations),
        "--num-layers", str(num_layers),
        "--learning-rate", str(learning_rate),
        "--lora-rank", str(lora_rank),
        "--adapter-path", str(adapter_path),
    ]
    if mask_prompt:
        cmd.append("--mask-prompt")
    if grad_checkpoint:
        cmd.append("--grad-checkpoint")

    _finetune_jobs[job_id] = {
        "status": "running",
        "base_model": base_model,
        "adapter_name": adapter_name,
        "adapter_path": str(adapter_path),
        "data_id": data_id,
        "config": {
            "lora_rank": lora_rank,
            "iterations": iterations,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "num_layers": num_layers,
            "mask_prompt": mask_prompt,
            "grad_checkpoint": grad_checkpoint,
        },
        "log_path": str(log_path),
        "log_lines": [],
        "loss_history": [],
    }

    def _run_training():
        try:
            with open(log_path, "w") as log_file:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                for line in proc.stdout:
                    line = line.rstrip("\n")
                    log_file.write(line + "\n")
                    log_file.flush()
                    job = _finetune_jobs[job_id]
                    job["log_lines"].append(line)
                    # Keep last 200 lines in memory
                    if len(job["log_lines"]) > 200:
                        job["log_lines"] = job["log_lines"][-200:]
                    # Parse loss values from mlx_lm output
                    if "train loss" in line.lower() or "val loss" in line.lower():
                        job["loss_history"].append(line)

                proc.wait()
                if proc.returncode == 0:
                    _finetune_jobs[job_id]["status"] = "complete"
                else:
                    _finetune_jobs[job_id]["status"] = "error"
                    _finetune_jobs[job_id]["error"] = f"Process exited with code {proc.returncode}"
        except FileNotFoundError:
            _finetune_jobs[job_id]["status"] = "error"
            _finetune_jobs[job_id]["error"] = (
                "mlx_lm not installed. Run: pip install mlx-lm"
            )
        except Exception as exc:
            _finetune_jobs[job_id]["status"] = "error"
            _finetune_jobs[job_id]["error"] = str(exc)

    thread = threading.Thread(target=_run_training, daemon=True)
    thread.start()

    return {"job_id": job_id, "status": "running", "adapter_path": str(adapter_path)}


@app.get("/api/finetune/status/{job_id}")
async def finetune_status(job_id: str):
    """Get the status and logs of a fine-tuning job."""
    if not job_id or not job_id.isalnum():
        raise HTTPException(status_code=400, detail="Invalid job ID.")
    if job_id not in _finetune_jobs:
        raise HTTPException(status_code=404, detail="Fine-tuning job not found.")
    job = _finetune_jobs[job_id]
    return {
        "status": job["status"],
        "base_model": job["base_model"],
        "adapter_name": job["adapter_name"],
        "adapter_path": job["adapter_path"],
        "config": job["config"],
        "log_lines": job["log_lines"][-50:],
        "loss_history": job["loss_history"],
        "error": job.get("error"),
    }


@app.get("/api/finetune/adapters")
async def list_adapters():
    """List available LoRA adapters."""
    adapters_dir = FINETUNE_DIR / "adapters"
    if not adapters_dir.exists():
        return {"adapters": []}
    adapters = []
    for d in sorted(adapters_dir.iterdir()):
        if d.is_dir():
            files = list(d.iterdir())
            size_bytes = sum(f.stat().st_size for f in files if f.is_file())
            has_weights = any(f.suffix == ".safetensors" for f in files)
            adapters.append({
                "name": d.name,
                "path": str(d),
                "files": len(files),
                "size_mb": round(size_bytes / (1024 * 1024), 1),
                "has_weights": has_weights,
            })
    return {"adapters": adapters}


@app.post("/api/finetune/test")
async def finetune_test(
    base_model: str = Form(...),
    adapter_path: str = Form(...),
    prompt: str = Form(...),
    max_tokens: int = Form(512),
):
    """Test a LoRA adapter by generating text."""
    if not prompt or len(prompt) > 2000:
        raise HTTPException(status_code=400, detail="Prompt must be 1-2000 characters.")
    max_tokens = max(16, min(max_tokens, 2048))

    # Validate adapter_path is within our finetune directory
    adapter = Path(adapter_path)
    try:
        adapter.resolve().relative_to(FINETUNE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid adapter path.")
    if not adapter.exists():
        raise HTTPException(status_code=404, detail="Adapter not found.")

    cmd = [
        "mlx_lm.generate",
        "--model", base_model,
        "--adapter-path", str(adapter),
        "--prompt", prompt,
        "--max-tokens", str(max_tokens),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Generation failed: {result.stderr[:500]}",
            )
        return {"output": result.stdout, "adapter_path": str(adapter)}
    except FileNotFoundError:
        raise HTTPException(status_code=422, detail="mlx_lm not installed. Run: pip install mlx-lm")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Generation timed out (120s limit).")


@app.post("/api/finetune/fuse")
async def finetune_fuse(
    base_model: str = Form(...),
    adapter_path: str = Form(...),
    output_name: str = Form("fused_model"),
):
    """Fuse a LoRA adapter permanently into the base model."""
    adapter = Path(adapter_path)
    try:
        adapter.resolve().relative_to(FINETUNE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid adapter path.")
    if not adapter.exists():
        raise HTTPException(status_code=404, detail="Adapter not found.")

    output_name = "".join(c for c in output_name if c.isalnum() or c in "_-")[:50] or "fused_model"
    save_path = FINETUNE_DIR / "fused" / output_name
    save_path.mkdir(parents=True, exist_ok=True)

    cmd = [
        "mlx_lm.fuse",
        "--model", base_model,
        "--adapter-path", str(adapter),
        "--save-path", str(save_path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Fuse failed: {result.stderr[:500]}",
            )
        return {
            "status": "fused",
            "save_path": str(save_path),
            "output": result.stdout[:500],
        }
    except FileNotFoundError:
        raise HTTPException(status_code=422, detail="mlx_lm not installed. Run: pip install mlx-lm")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Fuse timed out (10 min limit).")


def create_app() -> FastAPI:
    """Factory function returning the configured FastAPI app."""
    return app
