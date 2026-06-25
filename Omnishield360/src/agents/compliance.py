"""
OmniShield 360 - Anti-Litigation Compliance Shield
Cross-references member identities against the Social Security Death Master File (SSDI/DMF).
If matched, triggers UiPath Cloud Asset circuit-breaker to freeze all outbound billing pipelines.
Protects the organization from FDCPA / TCPA class-action lawsuits.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Mock SSDI registry — replace with live DMF clearinghouse API in production
# ---------------------------------------------------------------------------
_MOCK_SSDI_REGISTRY = {
    "994-00-1234",   # Scenario 3 test case
    "994-00-5678",
}

# Billing actions that legally cannot be sent to a deceased estate
_HIGH_RISK_BILLING_ACTIONS = {
    "PAYMENT_MISS_ALERT",
    "COLLECTIONS_DISPATCH",
    "AUTO_DEBIT_RETRY",
    "FINAL_NOTICE",
}

# Default TTL for the global breaker flag. Estate reconciliation is a real
# administrative task that can take days — 1h default is short enough to avoid
# freezing legitimate post-mortem work, long enough to catch the bad actors.
DEFAULT_BREAKER_TTL_SECONDS = int(os.getenv("UIPATH_BREAKER_TTL_SECONDS", "3600"))

# In-memory idempotency: tracks claim IDs we've already frozen in this process,
# so repeat runs of the same payload don't re-write the assets or re-open the
# legal action center task.
_FROZEN_CLAIMS: set[str] = set()


def _call_ssdi_api(ssn_token: str) -> bool:
    """
    Production stub: replace with authenticated HTTP call to a trusted
    DMF clearinghouse (e.g., LexisNexis, Equifax Deceased Verification API).
    """
    return ssn_token in _MOCK_SSDI_REGISTRY


def _cloud_asset_set(name: str, value: str) -> bool:
    """Write a single Cloud Asset; returns True on success, False on graceful fallback."""
    try:
        from uipath.platform import UiPath

        sdk = UiPath()
        folder = os.getenv("UIPATH_FOLDER_NAME", "Healthcare_Operations_Prod")
        sdk.assets.set_value(name=name, value=value, folder_path=folder)
        return True
    except Exception as e:
        print(f"[COMPLIANCE] ⚠️  Cloud Asset '{name}' write failed ({e}). Local fallback.")
        return False


def _write_cloud_circuit_breaker(claim_id: str) -> None:
    """
    Writes a CLAIM-SCOPED emergency asset in addition to the global flag.

    The global `Outbound_Billing_Circuit_Breaker` flag is shared across all claims
    and is bounded by a TTL. The per-claim flag
    `Outbound_Billing_Circuit_Breaker_{claim_id}` is permanent and is the
    authoritative "this specific claim must not be billed" marker that other
    workers can poll.

    Idempotent: calling this twice for the same claim_id is a no-op.
    """
    if claim_id in _FROZEN_CLAIMS:
        print(f"[COMPLIANCE] Breaker already active for {claim_id} (idempotent skip).")
        return
    _FROZEN_CLAIMS.add(claim_id)

    folder = os.getenv("UIPATH_FOLDER_NAME", "Healthcare_Operations_Prod")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=DEFAULT_BREAKER_TTL_SECONDS)

    # 1. Per-claim scoped flag — permanent until the legal team manually clears it.
    per_claim_asset = f"Outbound_Billing_Circuit_Breaker_{claim_id}"
    per_claim_ok = _cloud_asset_set(per_claim_asset, "TRUE")

    # 2. Global flag — short-lived; affects only new outbound pipelines.
    global_ok = _cloud_asset_set("Outbound_Billing_Circuit_Breaker", "TRUE")

    # 3. TTL marker — downstream workers can re-check the gate after this time.
    ttl_ok = _cloud_asset_set(
        "Outbound_Billing_Circuit_Breaker_Expires_At",
        expires_at.isoformat(),
    )

    if per_claim_ok and global_ok and ttl_ok:
        print(
            f"[COMPLIANCE] ✅ Circuit breaker ACTIVE (Claim: {claim_id}, folder: {folder}, "
            f"TTL: {expires_at.isoformat()})"
        )


def _write_audit_log(claim_id: str, message: str) -> None:
    """
    Streams a warning entry directly to UiPath Orchestrator log panel.
    Falls back to local print when cloud is unavailable.
    """
    try:
        from uipath.platform import UiPath

        sdk = UiPath()
        folder = os.getenv("UIPATH_FOLDER_NAME", "Healthcare_Operations_Prod")
        sdk.logs.write_warning(
            folder_path=folder,
            message=f"[OmniShield360 COMPLIANCE] Claim: {claim_id} | {message}",
        )
    except Exception:
        print(f"[AUDIT LOG] WARNING | Claim: {claim_id} | {message}")


def _write_legal_estates_action(claim_id: str, message: str) -> None:
    """
    Creates an Action Center task for the Legal Estates Unit so they see the
    halt the moment it fires. Includes a binder reference (claim_id +
    timestamp) so the audit binder can be assembled in one click.
    """
    binder_ref = f"OMNI-BINDER-{claim_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    try:
        from uipath.platform import UiPath

        sdk = UiPath()
        folder = os.getenv("UIPATH_FOLDER_NAME", "Healthcare_Operations_Prod")
        sdk.actions.create(
            folder_path=folder,
            action={
                "title": f"[LEGAL ESTATES] Deceased member halt — {claim_id}",
                "priority": "high",
                "status": "open",
                "data": {
                    "claim_id": claim_id,
                    "binder_ref": binder_ref,
                    "message": message,
                    "triggered_at": datetime.now(timezone.utc).isoformat(),
                },
            },
        )
        print(f"[COMPLIANCE] ✅ Legal Estates action created (binder: {binder_ref})")
    except Exception as e:
        print(f"[COMPLIANCE] ⚠️  Legal Estates action failed ({e}). Binder: {binder_ref}")


def run_death_master_audit(patient_ssn: str, claim_id: str, billing_action: str = "STANDARD") -> bool:
    """
    Main compliance gate.
    Returns True if member is deceased AND a high-risk billing action is attempted.
    Side effects: writes claim-scoped + global circuit-breaker assets, audit log,
    and Action Center task for Legal Estates on match.
    """
    is_deceased = _call_ssdi_api(patient_ssn)

    if not is_deceased:
        return False

    # Member IS deceased — check if the triggering action is legally restricted
    if billing_action in _HIGH_RISK_BILLING_ACTIONS or billing_action == "STANDARD":
        _write_cloud_circuit_breaker(claim_id)
        halt_message = (
            "SSDI registry match confirmed. Automated outbound billing pipeline terminated. "
            "Case routed to Legal Estates Unit to prevent FDCPA/TCPA exposure."
        )
        _write_audit_log(claim_id, halt_message)
        _write_legal_estates_action(claim_id, halt_message)
        return True

    # Deceased but action is informational only — flag but do not hard-stop
    print(f"[COMPLIANCE] Advisory: Member {claim_id} matched on SSDI. Action '{billing_action}' permitted with legal review.")
    return False
