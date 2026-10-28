"""Development auto-reloader (polls file modification times; no dependencies)."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

SKIP_DIRS = {"__pycache__", "node_modules", "venv", "env", "build", "dist", "site-packages"}
WATCH_SUFFIXES = (".py",)


def snapshot(root: str | os.PathLike, suffixes: tuple[str, ...] = WATCH_SUFFIXES) -> dict[str, float]:
    """Map every watched file under ``root`` to its modification time."""
    result: dict[str, float] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.endswith(suffixes):
                path = os.path.join(dirpath, name)
                try:
                    result[path] = os.stat(path).st_mtime
                except OSError:
                    pass
    return result


def changed(old: dict[str, float], new: dict[str, float]) -> list[str]:
    """Paths added, removed or modified between two snapshots."""
    return sorted({p for p in old.keys() | new.keys() if old.get(p) != new.get(p)})


def run_with_reloader(argv: list[str], root: str | None = None, interval: float = 0.5) -> None:
    """Run ``python -m nexusserver <argv>`` in a child process and restart it on file changes."""
    root = root or os.getcwd()
    cmd = [sys.executable, "-m", "nexusserver", *argv]
    print(f"[nexusserver] reloader watching {Path(root)} (Ctrl+C to stop)", flush=True)
    child = subprocess.Popen(cmd)
    state = snapshot(root)
    # Make `kill <pid>` (SIGTERM) shut the child down too, instead of orphaning it.
    try:
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    except ValueError:  # not in the main thread
        pass
    try:
        while True:
            time.sleep(interval)
            if child.poll() is not None:
                code = child.returncode
                print(f"[nexusserver] server exited with code {code}; waiting for changes...", flush=True)
                while not changed(state, snapshot(root)):
                    time.sleep(interval)
            current = snapshot(root)
            diff = changed(state, current)
            if diff:
                print(f"[nexusserver] change detected in {os.path.relpath(diff[0], root)}; restarting", flush=True)
                state = current
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill()
                child = subprocess.Popen(cmd)
    except KeyboardInterrupt:
        pass
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
