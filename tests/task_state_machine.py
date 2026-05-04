# -*- coding: utf-8 -*-
"""
Centralized task state machine for crash recovery and step orchestration.

Persists step status to task_state.json with atomic writes.
Master Agent should call this at each step boundary to enable
resume-from-checkpoint after session interruptions.
"""

from __future__ import annotations

import json
import os
import time
from enum import Enum
from pathlib import Path
from typing import Optional


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# Canonical step execution order
STEP_SEQUENCE = [
    "step_1",
    "step_2",
    "step_3",
    "step_4a",
    "step_4b",
    "step_4c",
    "step_4d",
    "step_7",
    "step_8",
    "step_9",
    "step_9_5",
    "step_10",
    "step_10_5",
    "step_11",
]

# Step dependency overrides (default: previous step in sequence)
# step_4b and step_4c both depend on step_4a (can run in parallel)
# step_4d depends on step_4b AND step_4c
# step_7 depends on step_3 (not step_4d), allowing parallel execution with Step 4
# step_8 depends on step_4a AND step_7, allowing visual analysis to run before step_4d
STEP_DEPS = {
    "step_4b": ["step_4a"],
    "step_4c": ["step_4a"],
    "step_4d": ["step_4b", "step_4c"],
    "step_7": ["step_3"],
    "step_8": ["step_4a", "step_7"],
}

MAX_RETRY_PER_STEP = 3


class TaskStateMachine:
    """Persistent state machine backed by task_state.json."""

    def __init__(self, task_dir: str | Path):
        self.task_dir = Path(task_dir)
        self.state_path = self.task_dir / "task_state.json"
        self.state = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                # State file itself corrupted – start fresh but log
                backup = str(self.state_path) + f".bad.{int(time.time())}"
                try:
                    os.rename(self.state_path, backup)
                except OSError:
                    pass
                print(f"[WARN] task_state.json corrupted, reset. Backup: {backup}")

        return {
            "steps": {
                s: {"status": StepStatus.PENDING.value, "attempts": 0}
                for s in STEP_SEQUENCE
            },
            "created_at": time.time(),
            "last_updated": time.time(),
        }

    def _save(self):
        """Atomic write via rename."""
        tmp = str(self.state_path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(self.state_path))

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_status(self, step: str) -> StepStatus:
        info = self.state["steps"].get(step, {})
        return StepStatus(info.get("status", "pending"))

    def get_retry_count(self, step: str) -> int:
        return self.state["steps"].get(step, {}).get("attempts", 0)

    def get_resume_point(self) -> Optional[str]:
        """Return the first non-SUCCESS step, or None if all done."""
        for step in STEP_SEQUENCE:
            if self.get_status(step) != StepStatus.SUCCESS:
                return step
        return None

    def is_complete(self) -> bool:
        return self.get_resume_point() is None

    def can_proceed(self, step: str) -> tuple[bool, str]:
        """Check if all dependencies for *step* are satisfied."""
        if step not in self.state["steps"]:
            return False, f"Unknown step: {step}"

        idx = STEP_SEQUENCE.index(step)
        deps = STEP_DEPS.get(step)

        if deps is None:
            # Default: depend on previous step in sequence
            if idx == 0:
                return True, "OK"
            deps = [STEP_SEQUENCE[idx - 1]]

        for dep in deps:
            if self.get_status(dep) != StepStatus.SUCCESS:
                return False, f"依赖 {dep} 未完成 (当前: {self.get_status(dep).value})"

        return True, "OK"

    def can_retry(self, step: str) -> bool:
        return self.get_retry_count(step) < MAX_RETRY_PER_STEP

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def mark(
        self,
        step: str,
        status: StepStatus,
        error: str | None = None,
    ):
        """Update step status and persist."""
        if step not in self.state["steps"]:
            self.state["steps"][step] = {"status": "pending", "attempts": 0}

        entry = self.state["steps"][step]
        entry["status"] = status.value

        if status == StepStatus.RUNNING:
            entry["attempts"] = entry.get("attempts", 0) + 1
            entry["started_at"] = time.time()
        elif status in (StepStatus.SUCCESS, StepStatus.FAILED):
            entry["finished_at"] = time.time()

        if error:
            entry["last_error"] = error

        self.state["last_updated"] = time.time()
        self._save()

    def reset_step(self, step: str):
        """Reset a step to PENDING with zero attempts (for manual recovery)."""
        if step in self.state["steps"]:
            self.state["steps"][step] = {
                "status": StepStatus.PENDING.value,
                "attempts": 0,
            }
            self.state["last_updated"] = time.time()
            self._save()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Human-readable summary for logging/debugging."""
        lines = ["Task State Machine Summary:"]
        for step in STEP_SEQUENCE:
            info = self.state["steps"].get(step, {})
            status = info.get("status", "pending")
            attempts = info.get("attempts", 0)
            error = info.get("last_error", "")
            marker = {"success": "[OK]", "failed": "[FAIL]", "running": "[..]", "skipped": "[SKIP]"}.get(
                status, "[  ]"
            )
            line = f"  {marker} {step}: {status} (attempts: {attempts})"
            if error:
                line += f" | error: {error[:80]}"
            lines.append(line)
        return "\n".join(lines)


# ------------------------------------------------------------------
# CLI helper: python scripts/task_state_machine.py <taskDir> [status|resume|reset <step>]
# ------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python task_state_machine.py <taskDir> [status|resume|reset <step>]")
        raise SystemExit(1)

    task_dir = sys.argv[1]
    sm = TaskStateMachine(task_dir)

    cmd = sys.argv[2] if len(sys.argv) > 2 else "status"

    if cmd == "status":
        print(sm.summary())
    elif cmd == "resume":
        rp = sm.get_resume_point()
        if rp:
            print(f"Resume from: {rp}")
        else:
            print("All steps complete.")
    elif cmd == "reset" and len(sys.argv) > 3:
        step = sys.argv[3]
        sm.reset_step(step)
        print(f"Reset {step} to PENDING")
        print(sm.summary())
    else:
        print(sm.summary())
