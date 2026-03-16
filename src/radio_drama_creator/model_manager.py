"""Local model manager for downloading, inspecting, and deleting MLX models.

Uses the Hugging Face Hub cache to manage models on disk.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

logger = logging.getLogger("radio_drama_creator.model_manager")


@dataclass
class LocalModel:
    """Represents a model stored in the local HF cache."""
    repo_id: str
    size_bytes: int
    nb_files: int
    last_accessed: float
    last_modified: float
    revisions: list[str]
    cache_path: str

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024 * 1024 * 1024)

    def to_dict(self) -> dict:
        return {
            "repo_id": self.repo_id,
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_mb, 1),
            "size_gb": round(self.size_gb, 2),
            "nb_files": self.nb_files,
            "last_accessed": self.last_accessed,
            "last_modified": self.last_modified,
            "revisions": self.revisions,
        }


def get_cache_dir() -> Path:
    """Return the HuggingFace Hub cache directory."""
    try:
        from huggingface_hub import constants
        return Path(constants.HF_HUB_CACHE)
    except (ImportError, AttributeError):
        return Path.home() / ".cache" / "huggingface" / "hub"


def list_local_models() -> list[LocalModel]:
    """List all models currently downloaded in the HF cache."""
    try:
        from huggingface_hub import scan_cache_dir
    except ImportError:
        logger.warning("huggingface_hub not installed")
        return []

    try:
        cache_info = scan_cache_dir()
    except Exception:
        return []

    models = []
    for repo in cache_info.repos:
        if repo.repo_type != "model":
            continue
        models.append(LocalModel(
            repo_id=repo.repo_id,
            size_bytes=repo.size_on_disk,
            nb_files=repo.nb_files,
            last_accessed=repo.last_accessed,
            last_modified=repo.last_modified,
            revisions=[r.commit_hash[:12] for r in repo.revisions],
            cache_path=str(repo.repo_path),
        ))

    models.sort(key=lambda m: m.size_bytes, reverse=True)
    return models


def get_cache_summary() -> dict:
    """Return a summary of the local model cache."""
    models = list_local_models()
    total_bytes = sum(m.size_bytes for m in models)
    cache_dir = get_cache_dir()

    # Get disk free space
    try:
        usage = shutil.disk_usage(str(cache_dir.parent))
        disk_free_gb = usage.free / (1024 ** 3)
        disk_total_gb = usage.total / (1024 ** 3)
    except OSError:
        disk_free_gb = 0
        disk_total_gb = 0

    return {
        "cache_dir": str(cache_dir),
        "total_models": len(models),
        "total_size_gb": round(total_bytes / (1024 ** 3), 2),
        "disk_free_gb": round(disk_free_gb, 1),
        "disk_total_gb": round(disk_total_gb, 1),
    }


def delete_model(repo_id: str) -> dict:
    """Delete a model from the local HF cache.

    Returns a dict with status and freed space.
    """
    try:
        from huggingface_hub import scan_cache_dir
    except ImportError:
        return {"status": "error", "detail": "huggingface_hub not installed"}

    try:
        cache_info = scan_cache_dir()
    except Exception as exc:
        return {"status": "error", "detail": f"Cache scan failed: {exc}"}

    target_repo = None
    for repo in cache_info.repos:
        if repo.repo_id == repo_id:
            target_repo = repo
            break

    if target_repo is None:
        return {"status": "error", "detail": f"Model '{repo_id}' not found in cache"}

    freed_bytes = target_repo.size_on_disk
    delete_strategy = cache_info.delete_revisions(
        *(r.commit_hash for r in target_repo.revisions)
    )

    logger.info("Deleting model %s (%d bytes)", repo_id, freed_bytes)
    delete_strategy.execute()

    return {
        "status": "deleted",
        "repo_id": repo_id,
        "freed_mb": round(freed_bytes / (1024 * 1024), 1),
        "freed_gb": round(freed_bytes / (1024 ** 3), 2),
    }


def download_model(repo_id: str) -> Generator[str, None, None]:
    """Download a model from HuggingFace Hub.

    Yields progress messages.
    """
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        yield "Error: huggingface_hub not installed. Run: pip install huggingface_hub"
        return

    yield f"Starting download: {repo_id}..."

    try:
        path = snapshot_download(
            repo_id,
            repo_type="model",
        )
        yield f"Download complete: {repo_id}"
        yield f"Stored at: {path}"
    except Exception as exc:
        yield f"Download failed: {exc}"


def check_model_downloaded(repo_id: str) -> bool:
    """Check if a model is already in the local cache."""
    models = list_local_models()
    return any(m.repo_id == repo_id for m in models)


def get_model_info_from_hub(repo_id: str) -> dict:
    """Fetch model metadata from HuggingFace Hub (without downloading)."""
    try:
        from huggingface_hub import model_info
    except ImportError:
        return {"error": "huggingface_hub not installed"}

    try:
        info = model_info(repo_id)
        # Estimate size from siblings
        total_size = 0
        file_count = 0
        if info.siblings:
            for s in info.siblings:
                if hasattr(s, "size") and s.size:
                    total_size += s.size
                file_count += 1

        return {
            "repo_id": repo_id,
            "author": info.author or "",
            "downloads": info.downloads or 0,
            "likes": info.likes or 0,
            "tags": info.tags or [],
            "pipeline_tag": info.pipeline_tag or "",
            "estimated_size_gb": round(total_size / (1024 ** 3), 2) if total_size else None,
            "file_count": file_count,
            "last_modified": info.last_modified.isoformat() if info.last_modified else None,
        }
    except Exception as exc:
        return {"error": str(exc)}
