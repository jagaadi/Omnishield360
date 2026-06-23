"""Audit log helpers for governance and compliance visibility."""

from __future__ import annotations


def write_audit_event(claim_id: str, event_type: str, message: str) -> dict[str, str]:
    """Placeholder audit sink that can later be replaced by platform APIs."""
    return {
        "claim_id": claim_id,
        "event_type": event_type,
        "message": message,
    }
