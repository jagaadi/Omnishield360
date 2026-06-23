"""
OmniShield 360 - Anti-Fraud Duplicate Claim Analyzer
O(n) hash-based algorithm to detect duplicate billing submissions
across procedure codes, provider IDs, and service dates.
"""

import hashlib
from datetime import datetime


def _build_claim_fingerprint(claim: dict) -> str:
    """
    Creates a deterministic SHA-256 fingerprint from the key billing dimensions.
    Two claims are duplicates if they share: CPT code + Provider ID + Service Date + Member ID.
    """
    raw = "|".join([
        str(claim.get("cpt_code", "")),
        str(claim.get("provider_id", "")),
        str(claim.get("service_date", "")),
        str(claim.get("member_id", "")),
    ])
    return hashlib.sha256(raw.encode()).hexdigest()


def run_fraud_check(active_claim: dict, historical_ledger: list) -> bool:
    """
    Checks if the incoming claim is a duplicate of any record in the historical ledger.

    Args:
        active_claim:      The incoming claim payload dict from Orchestrator inputs.
        historical_ledger: List of past claim dicts loaded from Data Fabric / storage bucket.

    Returns:
        True if duplicate detected, False if claim is unique.
    """
    if not historical_ledger:
        return False

    incoming_fingerprint = _build_claim_fingerprint(active_claim)

    # Build a set of existing fingerprints — O(n) lookup
    historical_fingerprints = {
        _build_claim_fingerprint(past_claim)
        for past_claim in historical_ledger
    }

    if incoming_fingerprint in historical_fingerprints:
        print(f"[DEDUPLICATION] Duplicate fingerprint matched: {incoming_fingerprint[:16]}...")
        return True

    # Secondary soft-match: same provider + same member within 24 hours (different CPT)
    for past in historical_ledger:
        if (
            past.get("provider_id") == active_claim.get("provider_id")
            and past.get("member_id") == active_claim.get("member_id")
        ):
            try:
                past_date = datetime.strptime(str(past.get("service_date", "")), "%Y-%m-%d")
                curr_date = datetime.strptime(str(active_claim.get("service_date", "")), "%Y-%m-%d")
                delta_hours = abs((curr_date - past_date).total_seconds() / 3600)
                if delta_hours < 24:
                    print(f"[DEDUPLICATION] Soft-match: Same provider/member within 24hrs. Flagging for review.")
                    return True
            except ValueError:
                pass

    return False
