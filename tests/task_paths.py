# -*- coding: utf-8 -*-
"""Shared helpers for resolving skill task directories."""

from __future__ import annotations

import os
from pathlib import Path


def get_task_base_dir() -> Path:
    """Resolve the canonical shared task root."""

    env_value = os.environ.get("TASK_BASE_DIR")
    if env_value:
        return Path(env_value).expanduser().resolve()

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "shared" / "tasks"
        if candidate.exists() and (parent / "workspace-main").exists():
            return candidate

    return here.parents[4] / "shared" / "tasks"


def resolve_task_dir(task_id: str, task_dir: str | os.PathLike[str] | None = None) -> Path:
    """Resolve a task directory from either an explicit path or task id."""

    if task_dir:
        return Path(task_dir).expanduser().resolve()
    return get_task_base_dir() / task_id


def ensure_task_dir(task_id: str, task_dir: str | os.PathLike[str] | None = None) -> Path:
    """Resolve and create a task directory."""

    resolved = resolve_task_dir(task_id, task_dir)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved
