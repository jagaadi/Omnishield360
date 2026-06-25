"""
OmniShield 360 - PCP Referral Verification Crawler
Checks the EHR ledger for an active Primary Care Physician referral
linked to the incoming claim before specialist billing is permitted.
"""


# ---------------------------------------------------------------------------
# Mock EHR referral database — replace with live Epic/Cerner API call
# ---------------------------------------------------------------------------
_MOCK_EHR_REFERRALS = {
    "CLM-2026-0001": {"referral_id": "REF-8821", "pcp": "Dr. Aisha Patel",  "active": True},
    "CLM-2026-0002": {"referral_id": "REF-9031", "pcp": "Dr. Marcus Webb",  "active": True},
    "CLM-2026-0003": {"referral_id": "REF-7210", "pcp": "Dr. Linda Torres", "active": True},
    "CLM-2026-0004": {"referral_id": "REF-6601", "pcp": "Dr. James Park",   "active": True},
    "CLM-2026-0005": {"referral_id": "REF-5501", "pcp": "Dr. Priya Nair",   "active": True},
    "CLM-2026-0006": {"referral_id": "REF-9910", "pcp": "Dr. James Park",   "active": True},
    # CLM-2026-0099 intentionally absent to test the missing-referral path
}


def run_pcp_referral_check(active_claim: dict) -> dict:
    """
    Looks up whether a valid PCP referral exists for this claim.
    In production: replace mock lookup with authenticated EHR REST API call.

    Returns:
        dict with keys: referral_found (bool), referral_id (str), pcp_name (str)
    """
    claim_id = active_claim.get("claim_id", "")
    policy_types = active_claim.get("policy_types", [])

    # Dental and Accident policies typically don't require PCP referrals
    exempt_policies = {"DENTAL", "ACCIDENT"}
    if any(p in exempt_policies for p in policy_types):
        print(f"[PCP] Policy type exempt from referral requirement: {policy_types}")
        return {"referral_found": True, "referral_id": "EXEMPT", "pcp_name": "N/A"}

    record = _MOCK_EHR_REFERRALS.get(claim_id)

    if record and record.get("active"):
        return {
            "referral_found": True,
            "referral_id": record["referral_id"],
            "pcp_name": record["pcp"]
        }

    return {
        "referral_found": False,
        "referral_id": None,
        "pcp_name": None
    }
