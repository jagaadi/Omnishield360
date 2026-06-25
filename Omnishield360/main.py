"""
OmniShield 360 - Main Coded Agent Entrypoint
Author and owner: Aditya Panigrahy
Repository: https://github.com/jagaadi/Omnishield360
Hackathon: UiPath AgentHack 2026 - Track 1: Agentic Case Management
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# ── ── Resolve fixtures relative to this file's location ── ──
_SRC_DIR = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, os.path.dirname(__file__))

from src.agents.compliance import run_death_master_audit
from src.agents.deduplication import run_fraud_check
from src.agents.judge import run_judge_review
from src.agents.medical_necessity import run_medical_necessity_check
from src.agents.pcp_referral import run_pcp_referral_check
from src.agents.cob_engine import run_cob_check
from src.agents.pii_masker import mask_phi_data_v2
from src.agents.streaming import stream_document_understanding
from src.integrations.audit_client import write_audit_event
from src.integrations.ehr_client import sync_to_core_system
from src.integrations.notifications import dispatch_notification
from src.observability import new_trace_id, span
from src.workflows.routing import route_agent_result
from src.workflows.schemas import ValidationError, build_result, validate_inputs


def _load_scenario(scenario_id: str) -> dict | None:
    """Load a named scenario from src/testing/test-fixtures.json."""
    fixtures_path = os.path.join(_SRC_DIR, "testing", "test-fixtures.json")
    if not os.path.exists(fixtures_path):
        print(f"[CLI] ⚠️  fixtures not found at {fixtures_path}")
        return None
    with open(fixtures_path) as f:
        data = json.load(f)
    for scenario in data.get("scenarios", []):
        if scenario["id"] == scenario_id:
            return scenario["inputs"]
    print(f"[CLI] ❌ Scenario '{scenario_id}' not found in fixtures.")
    print(f"[CLI] Available: {[s['id'] for s in data.get('scenarios', [])]}")
    return None


def main(inputs: dict) -> dict:
    """
    Core entrypoint for OmniShield 360 Coded Agent.
    Governed and triggered by UiPath Automation Cloud Orchestrator.
    Every print() statement streams to the Orchestrator Jobs log panel.
    """
    new_trace_id()
    print("[OmniShield 360] ========== INITIALIZING OPERATIONAL RUN ==========")

    # ── Evidence chain — feeds the Agent-as-Judge layer ─────────────────
    evidence_chain: list[dict] = []

    # ── Schema validation (fail-loud, route to validation queue) ─────────
    try:
        validated = validate_inputs(inputs)
    except ValidationError as ve:
        print(f"[SCHEMA] ❌ ValidationError: {ve.code} | field={ve.field} | {ve.message}")
        result = build_result(
            claim_id=str((inputs or {}).get("active_claim_payload", {}).get("claim_id", "UNKNOWN")),
            status="SUSPENDED_SCHEMA_VALIDATION",
            risk_tier="MEDIUM",
            stage="Stage 0 - Schema Validation",
            message=f"Input schema rejected: {ve.message}",
            next_action="ROUTE_TO_VALIDATION_QUEUE",
            human_review_required=True,
            evidence=[f"{ve.code}: {ve.field}"],
            extra={"validation_error": ve.to_dict()},
        )
        write_audit_event(result["claim_id"], "SCHEMA_REJECTED", result["message"])
        dispatch_notification(result["claim_id"], result["message"], channel="validation_queue")
        return result

    raw_chart_text = validated["raw_chart_data"]
    active_claim = validated["active_claim_payload"]
    historical_ledger = validated["historical_claims_database"]
    ocr_confidence = validated["mock_ocr_confidence"]
    billing_action = validated["billing_action_type"]

    claim_id = active_claim.get("claim_id", "UNKNOWN")
    patient_ssn = active_claim.get("ssn_tokenized", "")

    # ─── STAGE 1: OCR CONFIDENCE GATE (streaming) ────────────────────────
    with span("stage.ocr.stream", claim_id=claim_id) as s:
        _monitor, gate_confidence = stream_document_understanding(raw_chart_text, ocr_confidence, threshold=0.85)
        s.set("gate_confidence", gate_confidence)
    evidence_chain.append({"stage": "stage.1.ocr", "risk": "LOW" if gate_confidence >= 0.85 else "MEDIUM", "summary": f"min_confidence={gate_confidence:.3f}"})

    if gate_confidence < 0.85:
        print("[STAGE 1] Low-confidence extraction detected. Routing to Validation Station (HITL).")
        result = build_result(
            claim_id=claim_id,
            status="SUSPENDED_DATA_REMEDIATION",
            risk_tier="MEDIUM",
            stage="Stage 1 - Intake",
            message="Handwritten form confidence below threshold. Human validation required.",
            next_action="ROUTE_TO_VALIDATION_STATION",
            human_review_required=True,
            evidence=[f"OCR streaming min={gate_confidence:.3f} < 0.85"],
        )
        write_audit_event(claim_id, "OCR_LOW_CONFIDENCE", result["message"])
        dispatch_notification(claim_id, result["message"], channel="action_center")
        return result

    # ─── STAGE 1b: PII MASKING (position-indexed) ────────────────────────
    with span("stage.pii.mask", claim_id=claim_id) as s:
        masked = mask_phi_data_v2(raw_chart_text)
        anonymized_text, token_map = masked.anonymized_text, masked.token_map
        s.set("tokens_mapped", len(token_map))
    print(f"[STAGE 1] Anonymization complete. Tokens mapped: {len(token_map)}")

    # ─── STAGE 2: PCP REFERRAL CHECK ─────────────────────────────────────
    with span("stage.pcp.referral", claim_id=claim_id) as s:
        pcp_result = run_pcp_referral_check(active_claim)
        s.set("referral_found", pcp_result["referral_found"])
    if not pcp_result["referral_found"]:
        print("[STAGE 2] PCP referral missing. Triggering provider outreach notification.")
        evidence_chain.append({"stage": "stage.2.pcp", "risk": "MEDIUM", "summary": "Missing PCP referral"})
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

    # ─── STAGE 2b: MEDICAL NECESSITY CHECK (LLM-powered, cached) ────────
    with span("stage.medical.necessity", claim_id=claim_id) as s:
        necessity = run_medical_necessity_check(active_claim, anonymized_text)
        s.set("approved", necessity["approved"])
        s.set("confidence", necessity["confidence"])
    if not necessity["approved"] and necessity["confidence"] >= 0.5:
        print(f"[STAGE 2] ⚠️  Medical necessity review failed: {necessity['reasoning']}")
        evidence_chain.append({"stage": "stage.2.necessity", "risk": "MEDIUM", "summary": necessity["reasoning"]})
        result = build_result(
            claim_id=claim_id,
            status="SUSPENDED_MEDICAL_NECESSITY",
            risk_tier="MEDIUM",
            stage="Stage 2 - Medical Necessity",
            message=f"AI medical necessity review failed: {necessity['reasoning']}",
            next_action="ROUTE_TO_CLINICAL_DIRECTOR",
            human_review_required=True,
            evidence=[f"AI confidence: {necessity['confidence']:.0%}", f"Flags: {necessity['flags']}"],
        )
        write_audit_event(claim_id, "NECESSITY_FAILED", result["message"])
        dispatch_notification(claim_id, result["message"], channel="clinical_director")
        return result
    print(f"[STAGE 2] Medical necessity: approved (confidence {necessity['confidence']:.0%}).")

    # ─── STAGE 3a: DUPLICATE CLAIM AUDIT ─────────────────────────────────
    with span("stage.fraud.duplicate", claim_id=claim_id) as s:
        is_duplicate = run_fraud_check(active_claim, historical_ledger)
        s.set("is_duplicate", is_duplicate)
    if is_duplicate:
        print("[STAGE 3] DUPLICATE DETECTED. Suspending for auditor reconciliation.")
        evidence_chain.append({"stage": "stage.3.fraud", "risk": "HIGH", "summary": "Duplicate fingerprint matched"})
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

    # ─── STAGE 3b: COORDINATION OF BENEFITS (plan-aware ordering) ─────────
    with span("stage.cob.engine", claim_id=claim_id) as s:
        cob_result = run_cob_check(active_claim)
        s.set("dual_coverage", cob_result["dual_coverage_detected"])
        s.set("payer_count", cob_result.get("payer_count", 0))
    if cob_result["dual_coverage_detected"]:
        payer_count = cob_result.get("payer_count", 2)
        print(f"[STAGE 3] {payer_count}-way coverage detected. Applying plan-aware COB rules.")
        evidence_chain.append({
            "stage": "stage.3.cob",
            "risk": "MEDIUM",
            "summary": f"{payer_count} plans, primary={cob_result['primary_payer']}",
        })
        result = build_result(
            claim_id=claim_id,
            status="SUSPENDED_DUAL_COVERAGE",
            risk_tier="MEDIUM",
            stage="Stage 3 - COB Engine",
            message=(
                f"COB applied ({cob_result['rule_applied']}). "
                f"Primary: {cob_result['primary_payer']}. "
                f"Secondary: {cob_result.get('secondary_payer')}. "
                f"Tertiary: {cob_result.get('tertiary_payer')}."
            ),
            next_action="DISPATCH_SECONDARY_CLAIM",
            human_review_required=True,
            evidence=[f"COB rule applied: {cob_result.get('rule_applied')}"],
            extra={"cob_details": cob_result},
        )
        write_audit_event(claim_id, "COB_DETECTED", result["message"])
        dispatch_notification(claim_id, result["message"], channel="cob_queue")
        return result

    # ─── STAGE 4: DECEASED LIST COMPLIANCE SHIELD ────────────────────────
    with span("stage.compliance.deceased", claim_id=claim_id) as s:
        is_deceased = run_death_master_audit(patient_ssn, claim_id, billing_action)
        s.set("is_deceased", is_deceased)
    if is_deceased:
        print("[CRITICAL] SSDI match confirmed. Circuit breaker activated. All outbound pipelines frozen.")
        evidence_chain.append({"stage": "stage.4.compliance", "risk": "CRITICAL", "summary": "SSDI match — circuit breaker fired"})
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

    # ─── AGENT-AS-JUDGE: cross-stage consistency review ──────────────────
    with span("stage.judge.review", claim_id=claim_id) as s:
        candidate = build_result(
            claim_id=claim_id,
            status="APPROVED_FOR_INTEGRATION",
            risk_tier="LOW",
            stage="Resolution",
            message="Claim fully verified. Syncing to Epic/Facets/QNXT via API Workflow.",
            next_action="SYNC_TO_CORE_SYSTEM",
            evidence=[
                "OCR streaming gate passed (min sample ≥ 0.85).",
                "PCP referral present in EHR.",
                "Medical necessity approved (clinical documentation supports billed procedure).",
                "Anti-fraud duplicate check passed (fingerprint unique).",
                "Single-coverage path (no COB split required).",
                "SSDI/Death Master File clear (member alive).",
            ],
            extra={"anonymized_payload": anonymized_text},
        )
        judge_verdict = run_judge_review(claim_id, evidence_chain, candidate)
        s.set("consistent", judge_verdict["consistent"])
        s.set("escalate", judge_verdict["escalate"])

    if judge_verdict["escalate"]:
        print(f"[JUDGE] ⚠️  Escalating: {judge_verdict['narrative']}")
        result = build_result(
            claim_id=claim_id,
            status="SUSPENDED_JUDGE_REVIEW",
            risk_tier="MEDIUM",
            stage="Stage 5 - Judge Review",
            message=f"Agent-as-Judge escalated: {judge_verdict['narrative']}",
            next_action="ROUTE_TO_CLINICAL_DIRECTOR",
            human_review_required=True,
            evidence=[f"Judge conflict: {c}" for c in judge_verdict["conflicts"]],
            extra={"judge_verdict": judge_verdict},
        )
        write_audit_event(claim_id, "JUDGE_ESCALATED", result["message"])
        dispatch_notification(claim_id, result["message"], channel="clinical_director")
        return result
    print(f"[JUDGE] ✅ {judge_verdict['narrative']}")

    # ─── SUCCESS PATH ────────────────────────────────────────────────────
    print("[OmniShield 360] ✅ All gates cleared. Dispatching to core ledger integration.")

    # ── PHI restoration uses position-indexed restore (no collision risk) ──
    restored_chart = masked.restore()
    print(
        "[OmniShield 360] PHI restored locally. "
        f"Secure boundary maintained ({len(restored_chart)} characters)."
    )

    result = candidate
    route_agent_result(result)
    sync_to_core_system(claim_id, result["status"], payload=result)
    write_audit_event(claim_id, "APPROVED", result["message"])
    return result


# ── ── CLI entrypoint ── ──
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OmniShield 360 — UiPath Coded Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                          # run hardcoded sample
  python main.py --scenario SCENARIO_03_COMPLIANCE...   # run named fixture
  python main.py --scenario SCENARIO_01_HAPPY_PATH_ELECTRONIC
        """,
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Run a specific scenario from src/testing/test-fixtures.json by ID",
    )
    args = parser.parse_args()

    if args.scenario:
        inputs = _load_scenario(args.scenario)
        if inputs is None:
            sys.exit(1)
        print(f"[CLI] ▶ Running scenario: {args.scenario}\n")
    else:
        # Hardcoded sample — mirrors Orchestrator input injection
        inputs = {
            "raw_chart_data": "Patient Name: Jane Smith. DOB: 11/20/1992. Diagnosis: Post-Acute Cardiac Evaluation.",
            "active_claim_payload": {
                "claim_id": "CLM-2026-0001",
                "ssn_tokenized": "000-00-0000",
                "member_id": "MBR-001",
                "provider_id": "PRV-999",
                "cpt_code": "99213",
                "service_date": "2026-06-01",
                "policy_types": ["CRITICAL_ILLNESS"],
                "billing_action_type": "STANDARD",
                "coverage_plans": [
                    {
                        "payer_name": "BlueCross",
                        "holder_dob": "03/15/1985",
                        "plan_start_date": "01/01/2020",
                    }
                ],
            },
            "historical_claims_database": [],
            "mock_ocr_confidence": 0.98,
        }
        print("[CLI] ▶ Running default sample payload\n")

    result = main(inputs)
    print("\n[OUTPUT]")
    print(json.dumps(result, indent=2))
