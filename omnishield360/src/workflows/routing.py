"""Routing helpers that translate decision outputs into workflow actions."""

from __future__ import annotations

from typing import Any


def route_agent_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return a lightweight routing contract for downstream workflow steps."""
    status = result.get("status", "")
    next_action = result.get("next_action", "")

    route_map = {
        "SUSPENDED_DATA_REMEDIATION": "VALIDATION_QUEUE",
        "SUSPENDED_AWAITING_REFERRAL": "PROVIDER_OUTREACH_QUEUE",
        "SUSPENDED_DUPLICATE_CLAIM": "FRAUD_REVIEW_QUEUE",
        "SUSPENDED_DUAL_COVERAGE": "COB_REVIEW_QUEUE",
        "HALTED_COMPLIANCE_BREACH": "LEGAL_ESTATES_QUEUE",
        "APPROVED_FOR_INTEGRATION": "SYNC_QUEUE",
    }

    route = route_map.get(status, "DEFAULT_ROUTING")
    requires_human = status in {
        "SUSPENDED_DATA_REMEDIATION",
        "SUSPENDED_AWAITING_REFERRAL",
        "SUSPENDED_DUPLICATE_CLAIM",
        "SUSPENDED_DUAL_COVERAGE",
        "HALTED_COMPLIANCE_BREACH",
    }

    return {
        "route": route,
        "status": status,
        "next_action": next_action,
        "requires_human_review": requires_human,
    }
