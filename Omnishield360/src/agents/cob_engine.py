"""
OmniShield 360 - Coordination of Benefits (COB) Engine
Handles dual- and multi-insurance coverage scenarios using plan-aware ordering.

Rule summary:
  - Apply CMS Medicare Secondary Payer precedence when Medicare is present.
  - Apply the birthday rule among comparable commercial dependent plans.
  - Put Medicare supplemental coverage after Medicare.

This remains a decision-support engine. Production use must load the applicable
plan contract, state rule set, and current CMS coordination facts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse_dob(holder_dob: str) -> datetime:
    """Tolerant DOB parser. Falls back to far-future so unknown DOBs sort last."""
    try:
        return datetime.strptime(holder_dob, "%m/%d/%Y")
    except (ValueError, TypeError):
        return datetime(1900, 1, 1)


def _parse_plan_start(plan_start_date: str) -> datetime:
    """Tolerant plan-start parser. Falls back to epoch so unknown starts sort last."""
    try:
        return datetime.strptime(plan_start_date, "%m/%d/%Y")
    except (ValueError, TypeError):
        return datetime(2000, 1, 1)


def _sort_plans_naic(coverage_plans: list[dict]) -> list[dict]:
    """
    Apply the NAIC Model COB ordering.

    Sort key:  (month, day, plan_start) ascending — earlier DOB wins, ties broken
    by longer-held plan (earlier start_date wins).
    """
    def sort_key(plan: dict) -> tuple[int, int, datetime]:
        dob = _parse_dob(plan.get("holder_dob", ""))
        return (dob.month, dob.day, _parse_plan_start(plan.get("plan_start_date", "")))

    return sorted(coverage_plans, key=sort_key)


def _apply_birthday_rule(coverage_plans: list[dict]) -> dict:
    """
    Apply the NAIC Model COB Rule to an arbitrary number of plans.
    Returns the ordered payer list and the rule applied.
    """
    if not coverage_plans:
        return {
            "payer_order": [],
            "rule_applied": "NO_PLANS",
        }

    if len(coverage_plans) == 1:
        return {
            "payer_order": [coverage_plans[0]],
            "rule_applied": "SINGLE_COVERAGE",
        }

    if not all(
        plan.get("covered_person_relationship") == "DEPENDENT_CHILD"
        for plan in coverage_plans
    ):
        return {
            "payer_order": coverage_plans,
            "rule_applied": "CONTRACT_RULES_REQUIRED",
            "requires_specialist_review": True,
        }

    ordered = _sort_plans_naic(coverage_plans)
    return {
        "payer_order": ordered,
        "rule_applied": "COMMERCIAL_BIRTHDAY_RULE",
        "requires_specialist_review": False,
    }


def _apply_medicare_precedence(
    coverage_plans: list[dict[str, Any]],
    context: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Apply focused CMS Medicare Secondary Payer rules for working-aged and
    disabled beneficiaries with employer group coverage.

    CMS source:
    https://www.cms.gov/medicare/coordination-benefits-recovery/overview/secondary-payer
    """
    medicare = [p for p in coverage_plans if p.get("payer_type") == "MEDICARE"]
    employer = [p for p in coverage_plans if p.get("payer_type") == "EMPLOYER_GHP"]
    supplemental = [
        p
        for p in coverage_plans
        if p.get("payer_type") in {"MEDIGAP", "MEDICARE_SUPPLEMENT"}
    ]
    if not medicare:
        return None

    remaining = [
        p
        for p in coverage_plans
        if p not in medicare and p not in employer and p not in supplemental
    ]
    age = int(context.get("beneficiary_age", 0) or 0)
    employer_size = int(context.get("employer_size", 0) or 0)
    current_employment = bool(context.get("current_employment", False))
    disability = bool(context.get("disability_entitlement", False))

    required_context = {"beneficiary_age", "current_employment", "employer_size"}
    if employer and not required_context.issubset(context):
        return {
            "payer_order": coverage_plans,
            "rule_applied": "CMS_MSP_CONTEXT_REQUIRED",
            "requires_specialist_review": True,
        }

    employer_is_primary = current_employment and (
        (age >= 65 and employer_size >= 20)
        or (disability and employer_size >= 100)
    )

    commercial_order = _sort_plans_naic(employer + remaining)
    if employer_is_primary:
        ordered = commercial_order + medicare + supplemental
        rule = "CMS_MSP_EMPLOYER_PRIMARY"
    else:
        ordered = medicare + commercial_order + supplemental
        rule = "CMS_MSP_MEDICARE_PRIMARY"

    return {
        "payer_order": ordered,
        "rule_applied": rule,
        "requires_specialist_review": False,
    }


def run_cob_check(active_claim: dict) -> dict:
    """
    Detects multi-coverage and computes payer liability split.

    Returns:
        dict with: dual_coverage_detected (bool), primary_payer (str),
                   secondary_payer (str | None), tertiary_payer (str | None),
                   payer_count (int), rule_applied (str),
                   payer_order (list[dict]) — full ordered list, present only
                   when multi-coverage is detected.
    """
    policy_types = active_claim.get("policy_types", [])
    coverage_plans: list[dict[str, Any]] = active_claim.get("coverage_plans", []) or []

    if len(coverage_plans) < 2:
        primary = coverage_plans[0] if coverage_plans else None
        return {
            "dual_coverage_detected": False,
            "primary_payer": primary.get("payer_name", "N/A") if primary else "N/A",
            "secondary_payer": None,
            "tertiary_payer": None,
            "payer_count": len(coverage_plans),
            "rule_applied": "SINGLE_COVERAGE",
        }

    print(f"[COB] {len(coverage_plans)}-plan coverage detected. Applying plan-aware COB rules...")
    context = active_claim.get("coordination_context", {}) or {}
    result = _apply_medicare_precedence(coverage_plans, context)
    if result is None:
        result = _apply_birthday_rule(coverage_plans)
    payer_order = result["payer_order"]

    def _name(plan: dict | None) -> str | None:
        return plan.get("payer_name", "Unknown") if plan else None

    return {
        "dual_coverage_detected": True,
        "primary_payer": _name(payer_order[0]),
        "secondary_payer": _name(payer_order[1]) if len(payer_order) > 1 else None,
        "tertiary_payer": _name(payer_order[2]) if len(payer_order) > 2 else None,
        "payer_count": len(payer_order),
        "rule_applied": result["rule_applied"],
        "requires_specialist_review": result.get("requires_specialist_review", False),
        "payer_order": [_name(p) for p in payer_order],
        "policy_types": policy_types,
    }
