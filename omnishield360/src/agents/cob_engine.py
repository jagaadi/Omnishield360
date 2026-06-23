"""
OmniShield 360 - Coordination of Benefits (COB) Engine
Handles dual-insurance coverage scenarios using the statutory Birthday Rule
to determine primary vs. secondary payer liability.
"""

from datetime import datetime


def _apply_birthday_rule(plan_a: dict, plan_b: dict) -> dict:
    """
    Statutory Birthday Rule: the plan of the policyholder whose birthday
    (month + day) falls EARLIER in the calendar year pays first.
    If birthdays are the same day, the plan held LONGER is primary.
    """
    try:
        dob_a = datetime.strptime(plan_a.get("holder_dob", "01/01/1900"), "%m/%d/%Y")
        dob_b = datetime.strptime(plan_b.get("holder_dob", "01/01/1900"), "%m/%d/%Y")

        # Compare only month + day (ignore year)
        a_md = (dob_a.month, dob_a.day)
        b_md = (dob_b.month, dob_b.day)

        if a_md < b_md:
            return {"primary": plan_a, "secondary": plan_b, "rule_applied": "BIRTHDAY_RULE"}
        elif b_md < a_md:
            return {"primary": plan_b, "secondary": plan_a, "rule_applied": "BIRTHDAY_RULE"}
        else:
            # Same birthday — longer-held plan is primary
            start_a = datetime.strptime(plan_a.get("plan_start_date", "01/01/2000"), "%m/%d/%Y")
            start_b = datetime.strptime(plan_b.get("plan_start_date", "01/01/2000"), "%m/%d/%Y")
            if start_a <= start_b:
                return {"primary": plan_a, "secondary": plan_b, "rule_applied": "LONGER_HELD_PLAN"}
            else:
                return {"primary": plan_b, "secondary": plan_a, "rule_applied": "LONGER_HELD_PLAN"}
    except Exception as e:
        print(f"[COB] Birthday rule evaluation error: {e}. Defaulting to Plan A as primary.")
        return {"primary": plan_a, "secondary": plan_b, "rule_applied": "DEFAULT_FALLBACK"}


def run_cob_check(active_claim: dict) -> dict:
    """
    Detects dual-coverage and computes payer liability split.

    Returns:
        dict with: dual_coverage_detected (bool), primary_payer (str),
                   secondary_payer (str), rule_applied (str)
    """
    policy_types = active_claim.get("policy_types", [])
    coverage_plans = active_claim.get("coverage_plans", [])

    if len(coverage_plans) < 2:
        return {
            "dual_coverage_detected": False,
            "primary_payer": coverage_plans[0].get("payer_name", "N/A") if coverage_plans else "N/A",
            "secondary_payer": None,
            "rule_applied": "SINGLE_COVERAGE"
        }

    print(f"[COB] Dual coverage detected. Applying Birthday Rule across {len(coverage_plans)} plans...")
    result = _apply_birthday_rule(coverage_plans[0], coverage_plans[1])

    return {
        "dual_coverage_detected": True,
        "primary_payer": result["primary"].get("payer_name", "Plan A"),
        "secondary_payer": result["secondary"].get("payer_name", "Plan B"),
        "rule_applied": result["rule_applied"]
    }
