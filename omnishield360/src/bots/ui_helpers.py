"""Utility helpers for bot-driven UI or desktop actions."""

from __future__ import annotations

from typing import Any


def execute_ui_step(step_name: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Placeholder function that models a bot execution step."""
    return {
        "step": step_name,
        "details": details or {},
        "completed": True,
    }
