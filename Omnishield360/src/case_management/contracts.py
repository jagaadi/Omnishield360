"""Stable task I/O contracts used by Maestro Case worker tasks."""

from __future__ import annotations

from typing import Any, Literal

TaskOutcome = Literal[
    "COMPLETED",
    "HUMAN_ACTION_REQUIRED",
    "WAITING_EXTERNAL_EVENT",
    "INTERRUPTING_HOLD",
    "FAILED",
]


def build_case_task_result(
    *,
    task: str,
    outcome: TaskOutcome,
    case_patch: dict[str, Any],
    recommended_action: str,
    evidence: list[str] | None = None,
    human_task: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build the write-back contract for a Maestro Case task.

    Workers return decisions and case-field updates. Maestro Case—not the
    worker—owns stage activation, re-entry, SLAs, and final lifecycle control.
    """
    result: dict[str, Any] = {
        "task": task,
        "outcome": outcome,
        "case_patch": case_patch,
        "recommended_action": recommended_action,
        "evidence": evidence or [],
    }
    if human_task:
        result["human_task"] = human_task
    return result
