"""Notification helpers for provider and workflow communications."""

from __future__ import annotations


def dispatch_notification(claim_id: str, message: str, channel: str = "email") -> dict[str, str]:
    """Placeholder notification dispatcher used by routing logic."""
    return {
        "claim_id": claim_id,
        "channel": channel,
        "message": message,
        "status": "queued",
    }
