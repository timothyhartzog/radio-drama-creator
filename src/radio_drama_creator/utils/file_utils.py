"""File and JSON handling utilities."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


def empty_file(file_name: str) -> None:
    """Clear a file's contents."""
    with open(file_name, "w") as fh:
        fh.truncate(0)


def empty_directory(directory_path: str) -> None:
    """Remove all files and subdirectories within a directory."""
    for entry in os.listdir(directory_path):
        entry_path = os.path.join(directory_path, entry)
        try:
            if os.path.isfile(entry_path) or os.path.islink(entry_path):
                os.unlink(entry_path)
            elif os.path.isdir(entry_path):
                shutil.rmtree(entry_path)
        except Exception as exc:
            print(f"Failed to delete {entry_path}: {exc}")


def read_json(filename: str) -> dict:
    """Load JSON data from a file."""
    with open(filename, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json_to_file(data: dict, file_name: str) -> None:
    """Write a JSON object to a file."""
    with open(file_name, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def write_jsons_to_jsonl_file(json_objects: list[dict], file_name: str) -> None:
    """Write a list of JSON objects to a JSONL file."""
    with open(file_name, "a", encoding="utf-8") as fh:
        for obj in json_objects:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def ensure_directory(path: str | Path) -> Path:
    """Create directory if it doesn't exist, return Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
