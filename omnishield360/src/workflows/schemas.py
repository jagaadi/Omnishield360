"""Schema helpers for standardizing agent inputs and outputs."""

from __future__ import annotations

from typing import Any


def normalize_inputs(inputs: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize runtime inputs so the agent has a stable contract."""
    raw = inputs or {}
    active_claim = raw.get("active_claim_payload", {}) or {}
    return {
        "raw_chart_data": raw.get("raw_chart_data", ""),
        "active_claim_payload": active_claim,
        "historical_claims_database": raw.get("historical_claims_database", []),
        "mock_ocr_confidence": float(raw.get("mock_ocr_confidence", 1.0)),
        "billing_action_type": raw.get("billing_action_type", "STANDARD"),
    }


def validate_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Validate the normalized payload and return a safe copy."""
    normalized = normalize_inputs(inputs)
    active_claim = normalized["active_claim_payload"]

    if not isinstance(normalized["historical_claims_database"], list):
        raise ValueError("historical_claims_database must be a list")

    if not isinstance(active_claim, dict):
        raise ValueError("active_claim_payload must be a JSON object")

    return normalized


def build_result(
    *,
    claim_id: str,
    status: str,
    risk_tier: str,
    stage: str,
    message: str,
    next_action: str,
    human_review_required: bool = False,
    evidence: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a consistent output payload used by the workflow and tests."""
    result = {
        "claim_id": claim_id,
        "status": status,
        "risk_tier": risk_tier,
        "stage": stage,
        "message": message,
        "next_action": next_action,
        "human_review_required": human_review_required,
        "evidence": evidence or [],
    }

    if extra:
        result.update(extra)

    return result
