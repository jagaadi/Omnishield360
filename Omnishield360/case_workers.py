"""
UiPath Coded Agent entry points used as workers inside Maestro Case stages.

These functions deliberately do not move the case between stages. Each worker
returns a case write-back patch and a recommendation; Maestro Case rules,
personas, SLAs, and human actions retain lifecycle authority.
"""

from __future__ import annotations

from typing import Any

from src.agents.cob_engine import run_cob_check
from src.agents.compliance import run_death_master_audit
from src.agents.deduplication import run_fraud_check
from src.agents.judge import run_judge_review
from src.agents.medical_necessity import run_medical_necessity_check
from src.agents.pcp_referral import run_pcp_referral_check
from src.agents.pii_masker import mask_phi_data_v2
from src.agents.streaming import stream_document_understanding
from src.case_management import build_case_task_result
from src.integrations.ehr_client import sync_to_core_system
from src.workflows.schemas import ValidationError, validate_inputs


def _human_task(
    *,
    title: str,
    persona: str,
    reason: str,
    priority: str = "high",
) -> dict[str, str]:
    return {
        "title": title,
        "persona": persona,
        "reason": reason,
        "priority": priority,
    }


def intake_assessment(inputs: dict[str, Any]) -> dict[str, Any]:
    """Worker for the Intake & Triage primary stage."""
    try:
        validated = validate_inputs(inputs)
    except ValidationError as exc:
        return build_case_task_result(
            task="intake_assessment",
            outcome="HUMAN_ACTION_REQUIRED",
            case_patch={
                "intakeStatus": "SCHEMA_REJECTED",
                "validationRequired": True,
                "riskTier": "MEDIUM",
                "exceptionCode": exc.code,
                "exceptionField": exc.field,
            },
            recommended_action="START_REQUEST_INFORMATION_STAGE",
            evidence=[str(exc)],
            human_task=_human_task(
                title="Correct claim intake data",
                persona="Intake Specialist",
                reason=exc.message,
            ),
        )

    claim = validated["active_claim_payload"]
    raw_chart = validated["raw_chart_data"]
    monitor, confidence = stream_document_understanding(
        raw_chart,
        validated["mock_ocr_confidence"],
    )
    if confidence < 0.85:
        return build_case_task_result(
            task="intake_assessment",
            outcome="HUMAN_ACTION_REQUIRED",
            case_patch={
                "claimId": claim["claim_id"],
                "externalCaseKey": claim["claim_id"],
                "intakeStatus": "VALIDATION_REQUIRED",
                "ocrConfidence": confidence,
                "validationRequired": True,
                "riskTier": "MEDIUM",
            },
            recommended_action="CREATE_DOCUMENT_VALIDATION_ACTION",
            evidence=[f"Minimum OCR confidence {confidence:.3f} is below 0.850."],
            human_task=_human_task(
                title="Validate low-confidence claim document",
                persona="Intake Specialist",
                reason="Document Understanding confidence is below threshold.",
            ),
        )

    masked = mask_phi_data_v2(raw_chart)
    summary = monitor.summary()
    return build_case_task_result(
        task="intake_assessment",
        outcome="COMPLETED",
        case_patch={
            "claimId": claim["claim_id"],
            "externalCaseKey": claim["claim_id"],
            "intakeStatus": "VERIFIED",
            "ocrConfidence": confidence,
            "validationRequired": False,
            "anonymizedChartData": masked.anonymized_text,
            "phiTokenCount": len(masked.token_map),
            "riskTier": "LOW",
        },
        recommended_action="COMPLETE_INTAKE_STAGE",
        evidence=[
            f"OCR samples={summary['samples']}, minimum={summary['min']:.3f}.",
            f"PHI tokens isolated={len(masked.token_map)}.",
        ],
    )


def clinical_assessment(inputs: dict[str, Any]) -> dict[str, Any]:
    """Worker for the Clinical Review primary stage."""
    claim = inputs.get("active_claim_payload", {}) or {}
    chart = str(inputs.get("anonymized_chart_data", ""))
    referral = run_pcp_referral_check(claim)
    if not referral["referral_found"]:
        return build_case_task_result(
            task="clinical_assessment",
            outcome="WAITING_EXTERNAL_EVENT",
            case_patch={
                "clinicalStatus": "AWAITING_REFERRAL",
                "referralStatus": "MISSING",
                "riskTier": "MEDIUM",
            },
            recommended_action="START_REQUEST_INFORMATION_STAGE",
            evidence=["No active PCP referral was found."],
            human_task=_human_task(
                title="Monitor provider referral request",
                persona="Clinical Coordinator",
                reason="Case is waiting for an external referral event.",
                priority="normal",
            ),
        )

    necessity = run_medical_necessity_check(claim, chart)
    if not necessity["approved"]:
        return build_case_task_result(
            task="clinical_assessment",
            outcome="HUMAN_ACTION_REQUIRED",
            case_patch={
                "clinicalStatus": "DIRECTOR_REVIEW",
                "referralStatus": "VERIFIED",
                "necessityStatus": "REVIEW_REQUIRED",
                "necessityConfidence": necessity["confidence"],
                "riskTier": "MEDIUM",
            },
            recommended_action="CREATE_CLINICAL_DIRECTOR_ACTION",
            evidence=[necessity["reasoning"], *necessity["flags"]],
            human_task=_human_task(
                title="Medical necessity decision",
                persona="Clinical Director",
                reason=necessity["reasoning"],
            ),
        )

    return build_case_task_result(
        task="clinical_assessment",
        outcome="COMPLETED",
        case_patch={
            "clinicalStatus": "APPROVED",
            "referralStatus": "VERIFIED",
            "necessityStatus": "APPROVED",
            "necessityConfidence": necessity["confidence"],
        },
        recommended_action="COMPLETE_CLINICAL_STAGE",
        evidence=[
            f"Referral verified: {referral.get('referral_id')}.",
            necessity["reasoning"],
        ],
    )


def adjudication_assessment(inputs: dict[str, Any]) -> dict[str, Any]:
    """Worker for the Investigation & Adjudication primary stage."""
    claim = inputs.get("active_claim_payload", {}) or {}
    ledger = inputs.get("historical_claims_database", []) or []
    if run_fraud_check(claim, ledger):
        return build_case_task_result(
            task="adjudication_assessment",
            outcome="INTERRUPTING_HOLD",
            case_patch={
                "adjudicationStatus": "FRAUD_HOLD",
                "duplicateDetected": True,
                "riskTier": "HIGH",
            },
            recommended_action="START_FRAUD_HOLD_STAGE",
            evidence=["Duplicate claim fingerprint or soft-match detected."],
            human_task=_human_task(
                title="Investigate duplicate claim",
                persona="Fraud Investigator",
                reason="Automated duplicate analysis found a billing anomaly.",
            ),
        )

    cob = run_cob_check(claim)
    if cob["dual_coverage_detected"]:
        return build_case_task_result(
            task="adjudication_assessment",
            outcome="HUMAN_ACTION_REQUIRED",
            case_patch={
                "adjudicationStatus": "COB_REVIEW",
                "duplicateDetected": False,
                "cobReviewRequired": True,
                "cobDetails": cob,
                "riskTier": "MEDIUM",
            },
            recommended_action="CREATE_COB_SPECIALIST_ACTION",
            evidence=[
                f"COB rule={cob['rule_applied']}.",
                f"Payer order={cob.get('payer_order', [])}.",
            ],
            human_task=_human_task(
                title="Confirm coordination of benefits",
                persona="COB Specialist",
                reason="Multiple active coverage plans require accountable review.",
            ),
        )

    return build_case_task_result(
        task="adjudication_assessment",
        outcome="COMPLETED",
        case_patch={
            "adjudicationStatus": "CLEARED",
            "duplicateDetected": False,
            "cobReviewRequired": False,
        },
        recommended_action="COMPLETE_ADJUDICATION_STAGE",
        evidence=["Duplicate analysis clear.", "Single coverage confirmed."],
    )


def compliance_assessment(inputs: dict[str, Any]) -> dict[str, Any]:
    """Worker for the Resolution & Settlement compliance gate."""
    claim = inputs.get("active_claim_payload", {}) or {}
    claim_id = str(claim.get("claim_id", "UNKNOWN"))
    is_deceased = run_death_master_audit(
        str(claim.get("ssn_tokenized", "")),
        claim_id,
        str(claim.get("billing_action_type", "STANDARD")),
    )
    if is_deceased:
        return build_case_task_result(
            task="compliance_assessment",
            outcome="INTERRUPTING_HOLD",
            case_patch={
                "complianceStatus": "LEGAL_HOLD",
                "legalHold": True,
                "riskTier": "CRITICAL",
            },
            recommended_action="START_LEGAL_ESTATES_HOLD_STAGE",
            evidence=["Death-file match with restricted outbound billing action."],
            human_task=_human_task(
                title="Legal Estates disposition",
                persona="Legal Estates Specialist",
                reason="A deceased-member match requires human-controlled disposition.",
            ),
        )

    return build_case_task_result(
        task="compliance_assessment",
        outcome="COMPLETED",
        case_patch={
            "complianceStatus": "CLEARED",
            "legalHold": False,
        },
        recommended_action="RUN_CASE_JUDGE",
        evidence=["Death-file compliance gate clear."],
    )


def judge_assessment(inputs: dict[str, Any]) -> dict[str, Any]:
    """Agent-as-Judge worker; humans retain authority over conflicts."""
    claim_id = str(inputs.get("claim_id", "UNKNOWN"))
    evidence_chain = inputs.get("evidence_chain", []) or []
    candidate = inputs.get("candidate_result", {}) or {}
    verdict = run_judge_review(claim_id, evidence_chain, candidate)
    if verdict["escalate"]:
        return build_case_task_result(
            task="judge_assessment",
            outcome="HUMAN_ACTION_REQUIRED",
            case_patch={
                "judgeStatus": "CONFLICT",
                "judgeConflicts": verdict["conflicts"],
                "settlementApprovalRequired": True,
                "riskTier": "MEDIUM",
            },
            recommended_action="CREATE_CASE_MANAGER_REVIEW_ACTION",
            evidence=verdict["conflicts"],
            human_task=_human_task(
                title="Resolve agent decision conflict",
                persona="Senior Case Manager",
                reason=verdict["narrative"],
            ),
        )

    return build_case_task_result(
        task="judge_assessment",
        outcome="COMPLETED",
        case_patch={
            "judgeStatus": "CONSISTENT",
            "judgeConflicts": [],
        },
        recommended_action="REQUEST_SETTLEMENT_APPROVAL",
        evidence=[verdict["narrative"]],
    )


def settlement_sync(inputs: dict[str, Any]) -> dict[str, Any]:
    """
    API workflow guard for final synchronization.

    Maestro must map the completed human approval into settlement_approved.
    The worker refuses to sync when that accountable decision is absent.
    """
    claim_id = str(inputs.get("claim_id", "UNKNOWN"))
    approved = inputs.get("settlement_approved") is True
    if not approved:
        return build_case_task_result(
            task="settlement_sync",
            outcome="HUMAN_ACTION_REQUIRED",
            case_patch={
                "settlementStatus": "APPROVAL_REQUIRED",
                "syncStatus": "BLOCKED",
            },
            recommended_action="CREATE_SETTLEMENT_APPROVAL_ACTION",
            evidence=["Settlement approval is absent or false."],
            human_task=_human_task(
                title="Approve claim settlement",
                persona="Claims Adjuster",
                reason="A human-controlled settlement decision is required before sync.",
            ),
        )

    sync = sync_to_core_system(
        claim_id,
        "APPROVED_FOR_INTEGRATION",
        payload=inputs.get("approved_payload", {}) or {},
    )
    return build_case_task_result(
        task="settlement_sync",
        outcome="COMPLETED",
        case_patch={
            "settlementStatus": "APPROVED",
            "syncStatus": "SYNCED" if sync.get("synced") else "STAGED",
            "outcome": "APPROVED",
        },
        recommended_action="COMPLETE_RESOLUTION_STAGE",
        evidence=["Human settlement approval received.", f"Sync target={sync['target']}."],
    )
