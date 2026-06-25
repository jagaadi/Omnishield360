"""Audit log helpers for governance and compliance visibility."""

from __future__ import annotations

import os


def write_audit_event(claim_id: str, event_type: str, message: str) -> dict[str, str]:
    """
    Writes a structured audit event to UiPath Orchestrator log stream.
    Falls back gracefully to local print when cloud credentials are absent.
    """
    # Attempt real Orchestrator log write
    try:
        from uipath.platform import UiPath

        sdk = UiPath()
        folder = os.getenv("UIPATH_FOLDER_NAME", "Healthcare_Operations_Prod")
        sdk.logs.write_information(
            folder_path=folder,
            message=f"[OmniShield360] [{event_type}] Claim: {claim_id} | {message}",
        )
        print(f"[AUDIT] ✅ Event logged — {event_type} | claim: {claim_id}")
    except Exception as _e:
        # Local fallback: still prints so engineers can trace execution locally
        print(f"[AUDIT LOG] [{event_type}] Claim: {claim_id} | {message}")

    return {
        "claim_id": claim_id,
        "event_type": event_type,
        "message": message,
    }
