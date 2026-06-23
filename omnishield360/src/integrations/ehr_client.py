"""Helpers for syncing claim outcomes to downstream clinical systems."""

from __future__ import annotations

from typing import Any


def sync_to_core_system(claim_id: str, status: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Placeholder integration point for EHR/core ledger sync."""
    return {
        "claim_id": claim_id,
        "status": status,
        "synced": True,
        "target": "EHR_OR_CORE_LEDGER",
        "payload": payload or {},
    }
