"""
OmniShield 360 - Main Coded Agent Entrypoint
Author: Genius
Hackathon: UiPath AgentHack 2026 - Track 1: Agentic Case Management
"""

import json
from src.agents.compliance import run_death_master_audit
from src.agents.deduplication import run_fraud_check
from src.agents.pcp_referral import run_pcp_referral_check
from src.agents.cob_engine import run_cob_check
from src.agents.pii_masker import mask_phi_data
from src.integrations.audit_client import write_audit_event
from src.integrations.ehr_client import sync_to_core_system
from src.integrations.notifications import dispatch_notification
from src.workflows.routing import route_agent_result
from src.workflows.schemas import build_result, validate_inputs


def main(inputs: dict) -> dict:
    """
    Core entrypoint for OmniShield 360 Coded Agent.
    Governed and triggered by UiPath Automation Cloud Orchestrator.
    Every print() statement streams to the Orchestrator Jobs log panel.
    """

    print("[OmniShield 360] ========== INITIALIZING OPERATIONAL RUN ==========")

    validated = validate_inputs(inputs)
    raw_chart_text = validated["raw_chart_data"]
    active_claim = validated["active_claim_payload"]
    historical_ledger = validated["historical_claims_database"]
    ocr_confidence = validated["mock_ocr_confidence"]
    billing_action = validated["billing_action_type"]

    claim_id = active_claim.get("claim_id", "UNKNOWN")
    patient_ssn = active_claim.get("ssn_tokenized", "")

    # ─── STAGE 1: OCR CONFIDENCE GATE ────────────────────────────────────────
    print(f"[STAGE 1] OCR Confidence Score: {ocr_confidence}")
    if ocr_confidence < 0.85:
        print("[STAGE 1] Low-confidence extraction detected. Routing to Validation Station (HITL).")
        result = build_result(
            claim_id=claim_id,
            status="SUSPENDED_DATA_REMEDIATION",
            risk_tier="MEDIUM",
            stage="Stage 1 - Intake",
            message="Handwritten form confidence below threshold. Human validation required.",
            next_action="ROUTE_TO_VALIDATION_STATION",
            human_review_required=True,
            evidence=["OCR confidence below threshold"],
        )
        write_audit_event(claim_id, "OCR_LOW_CONFIDENCE", result["message"])
        dispatch_notification(claim_id, result["message"], channel="action_center")
        return result

    # ─── STAGE 1b: PII MASKING ────────────────────────────────────────────────
    print("[STAGE 1] Running in-flight PII masking via AI Trust Layer simulation...")
    anonymized_text, token_map = mask_phi_data(raw_chart_text)
    print(f"[STAGE 1] Anonymization complete. Tokens mapped: {len(token_map)}")

    # ─── STAGE 2: PCP REFERRAL CHECK ─────────────────────────────────────────
    print("[STAGE 2] Checking PCP referral linkage in EHR ledger...")
    pcp_result = run_pcp_referral_check(active_claim)
    if not pcp_result["referral_found"]:
        print("[STAGE 2] PCP referral missing. Triggering provider outreach notification.")
        result = build_result(
            claim_id=claim_id,
            status="SUSPENDED_AWAITING_REFERRAL",
            risk_tier="MEDIUM",
            stage="Stage 2 - Clinical Care",
            message="No active PCP referral found. Provider notification dispatched.",
            next_action="NOTIFY_PCP_CLINIC",
            human_review_required=True,
            evidence=["Missing PCP referral"],
        )
        write_audit_event(claim_id, "PCP_MISSING", result["message"])
        dispatch_notification(claim_id, result["message"], channel="provider_outreach")
        return result
    print("[STAGE 2] PCP referral confirmed.")

    # ─── STAGE 3a: DUPLICATE CLAIM AUDIT ─────────────────────────────────────
    print("[STAGE 3] Running anti-fraud duplicate billing audit...")
    is_duplicate = run_fraud_check(active_claim, historical_ledger)
    if is_duplicate:
        print("[STAGE 3] DUPLICATE DETECTED. Suspending for auditor reconciliation.")
        result = build_result(
            claim_id=claim_id,
            status="SUSPENDED_DUPLICATE_CLAIM",
            risk_tier="HIGH",
            stage="Stage 3 - Claims Adjudication",
            message="Duplicate billing anomaly confirmed. Routing to specialized audit queue.",
            next_action="ROUTE_TO_FRAUD_AUDITOR",
            human_review_required=True,
            evidence=["Duplicate claim fingerprint matched"],
        )
        write_audit_event(claim_id, "DUPLICATE_CLAIM", result["message"])
        dispatch_notification(claim_id, result["message"], channel="fraud_queue")
        return result
    print("[STAGE 3] No duplicate detected. Proceeding.")

    # ─── STAGE 3b: COORDINATION OF BENEFITS ──────────────────────────────────
    print("[STAGE 3] Evaluating dual-coverage Coordination of Benefits (COB)...")
    cob_result = run_cob_check(active_claim)
    if cob_result["dual_coverage_detected"]:
        print("[STAGE 3] Dual coverage detected. Applying Birthday Rule liability split.")
        result = build_result(
            claim_id=claim_id,
            status="SUSPENDED_DUAL_COVERAGE",
            risk_tier="MEDIUM",
            stage="Stage 3 - COB Engine",
            message=f"COB applied. Primary payer: {cob_result['primary_payer']}. Secondary claim dispatched.",
            next_action="DISPATCH_SECONDARY_CLAIM",
            human_review_required=True,
            evidence=[f"COB rule applied: {cob_result.get('rule_applied')}"],
            extra={"cob_details": cob_result},
        )
        write_audit_event(claim_id, "COB_DETECTED", result["message"])
        dispatch_notification(claim_id, result["message"], channel="cob_queue")
        return result

    # ─── STAGE 4: DECEASED LIST COMPLIANCE SHIELD ────────────────────────────
    print("[STAGE 4] Running Anti-Litigation Compliance Shield (SSDI / Death Master File check)...")
    is_deceased = run_death_master_audit(patient_ssn, claim_id, billing_action)
    if is_deceased:
        print("[CRITICAL] SSDI match confirmed. Circuit breaker activated. All outbound pipelines frozen.")
        result = build_result(
            claim_id=claim_id,
            status="HALTED_COMPLIANCE_BREACH",
            risk_tier="CRITICAL",
            stage="Stage 4 - Risk & Legal",
            message="FDCPA/TCPA anti-litigation shield triggered. Routing to Legal Estates Unit.",
            next_action="ROUTE_TO_LEGAL_ESTATES",
            human_review_required=True,
            evidence=["SSDI/deceased compliance match detected"],
        )
        write_audit_event(claim_id, "COMPLIANCE_HALT", result["message"])
        dispatch_notification(claim_id, result["message"], channel="legal_estates")
        return result
    print("[STAGE 4] Compliance check passed. Member cleared.")

    # ─── SUCCESS PATH ─────────────────────────────────────────────────────────
    print("[OmniShield 360] ✅ All gates cleared. Dispatching to core ledger integration.")
    result = build_result(
        claim_id=claim_id,
        status="APPROVED_FOR_INTEGRATION",
        risk_tier="LOW",
        stage="Resolution",
        message="Claim fully verified. Syncing to Epic/Facets/QNXT via API Workflow.",
        next_action="SYNC_TO_CORE_SYSTEM",
        extra={
            "anonymized_payload": anonymized_text,
        },
    )
    route_agent_result(result)
    sync_to_core_system(claim_id, result["status"], payload=result)
    write_audit_event(claim_id, "APPROVED", result["message"])
    return result


if __name__ == "__main__":
    # Local debug run — simulates Orchestrator input injection
    import json
    sample = {
        "raw_chart_data": "Patient Name: Jane Smith. DOB: 11/20/1992. Diagnosis: Post-Acute Cardiac Evaluation.",
        "active_claim_payload": {
            "claim_id": "CLM-2026-0001",
            "ssn_tokenized": "000-00-0000",
            "policy_types": ["CRITICAL_ILLNESS"],
            "billing_action_type": "STANDARD"
        },
        "historical_claims_database": [],
        "mock_ocr_confidence": 0.98
    }
    result = main(sample)
    print("\n[LOCAL DEBUG OUTPUT]")
    print(json.dumps(result, indent=2))
