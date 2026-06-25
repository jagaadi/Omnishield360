"""Schema helpers for standardizing agent inputs and outputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Fields that must be present in active_claim_payload for the agent to make a safe
# decision. Missing fields default to "" or [] would silently pass a "not deceased"
# or "no PCP needed" verdict — exactly the kind of safe-default failure that
# produces a lawsuit in production. So we fail loud and route to a validation queue.
REQUIRED_PAYLOAD_FIELDS: tuple[str, ...] = (
    "claim_id",
    "ssn_tokenized",
    "policy_types",
    "billing_action_type",
    "cpt_code",
    "member_id",
    "provider_id",
    "service_date",
    "coverage_plans",
)


@dataclass(frozen=True)
class ValidationError(Exception):
    """Structured error returned by validate_inputs. Code is stable for routing."""
    code: str
    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} ({self.field}): {self.message}"

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "field": self.field, "message": self.message}


def normalize_inputs(inputs: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize runtime inputs so the agent has a stable contract."""
    raw = inputs or {}
    active_claim = raw.get("active_claim_payload", {}) or {}
    return {
        "raw_chart_data": raw.get("raw_chart_data", ""),
        "active_claim_payload": active_claim,
        "historical_claims_database": raw.get("historical_claims_database", []),
        "mock_ocr_confidence": float(raw.get("mock_ocr_confidence", 1.0)),
        "billing_action_type": raw.get(
            "billing_action_type",
            active_claim.get("billing_action_type", "STANDARD"),
        ),
    }


def validate_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Validate the normalized payload and return a safe copy.

    Raises:
        ValidationError: when a required field is missing or has the wrong type.
        The orchestrator (main.py) catches this and routes the claim to a schema
        validation queue instead of letting downstream agents see a half-empty
        record and silently rubber-stamp it.
    """
    normalized = normalize_inputs(inputs)
    active_claim = normalized["active_claim_payload"]

    if not isinstance(active_claim, dict):
        raise ValidationError(
            code="SCHEMA_INVALID",
            field="active_claim_payload",
            message="active_claim_payload must be a JSON object.",
        )

    if not isinstance(normalized["historical_claims_database"], list):
        raise ValidationError(
            code="SCHEMA_INVALID",
            field="historical_claims_database",
            message="historical_claims_database must be a list.",
        )

    for field_name in REQUIRED_PAYLOAD_FIELDS:
        if field_name not in active_claim:
            raise ValidationError(
                code="MISSING_REQUIRED_FIELD",
                field=field_name,
                message=f"Required field '{field_name}' is missing from active_claim_payload.",
            )

    if not isinstance(active_claim["policy_types"], list):
        raise ValidationError(
            code="SCHEMA_INVALID",
            field="policy_types",
            message="policy_types must be a list.",
        )

    if not isinstance(active_claim["coverage_plans"], list):
        raise ValidationError(
            code="SCHEMA_INVALID",
            field="coverage_plans",
            message="coverage_plans must be a list.",
        )

    confidence = normalized["mock_ocr_confidence"]
    if not 0.0 <= confidence <= 1.0:
        raise ValidationError(
            code="VALUE_OUT_OF_RANGE",
            field="mock_ocr_confidence",
            message="mock_ocr_confidence must be between 0.0 and 1.0.",
        )

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
    result: dict[str, Any] = {
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
