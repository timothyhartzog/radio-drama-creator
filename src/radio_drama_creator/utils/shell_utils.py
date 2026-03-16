"""System command execution and tool checks."""

from __future__ import annotations

import shutil
import subprocess
import sys


def check_if_calibre_is_installed() -> bool:
    """Check if Calibre's ebook-convert is available."""
    return shutil.which("ebook-convert") is not None or shutil.which("calibre") is not None


def check_if_ffmpeg_is_installed() -> bool:
    """Check if FFmpeg is available."""
    return shutil.which("ffmpeg") is not None


def check_if_ffprobe_is_installed() -> bool:
    """Check if ffprobe is available."""
    return shutil.which("ffprobe") is not None


def get_system_python_paths() -> list[str]:
    """Return list of directories containing system Python packages."""
    paths = []
    for base in ["/usr/lib", "/usr/local/lib", "/opt/homebrew/lib"]:
        for subdir in ["python3", f"python{sys.version_info.major}.{sys.version_info.minor}"]:
            candidate = f"{base}/{subdir}/site-packages"
            paths.append(candidate)
    return [p for p in paths if __import__("os").path.isdir(p)]


def run_shell_command(command: str) -> subprocess.CompletedProcess:
    """Execute a shell command with error handling."""
    try:
        return subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return run_shell_command_without_virtualenv(command)


def run_shell_command_without_virtualenv(command: str) -> subprocess.CompletedProcess:
    """Run a shell command without virtual environment dependencies."""
    import os

    env = os.environ.copy()
    system_paths = get_system_python_paths()
    if system_paths:
        env["PYTHONPATH"] = ":".join(system_paths)
    return subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
