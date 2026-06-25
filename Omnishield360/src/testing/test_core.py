"""Focused regression tests for the governance controls."""

from __future__ import annotations

import unittest
import json
from pathlib import Path

from case_workers import intake_assessment, settlement_sync
from src.agents.cob_engine import run_cob_check
from src.agents.judge import run_judge_review
from src.agents.pii_masker import mask_phi_data_v2
from src.agents.streaming import build_streaming_samples
from src.workflows.schemas import ValidationError, validate_inputs


def _valid_input() -> dict[str, object]:
    return {
        "raw_chart_data": "Patient Name: Jane Smith. DOB: 11/20/1992.",
        "active_claim_payload": {
            "claim_id": "CLM-TEST-001",
            "ssn_tokenized": "000-00-0000",
            "member_id": "MBR-001",
            "provider_id": "PRV-001",
            "cpt_code": "99213",
            "service_date": "2026-06-01",
            "policy_types": ["CRITICAL_ILLNESS"],
            "billing_action_type": "STANDARD",
            "coverage_plans": [
                {
                    "payer_name": "Plan A",
                    "holder_dob": "03/15/1985",
                    "plan_start_date": "01/01/2020",
                }
            ],
        },
        "historical_claims_database": [],
        "mock_ocr_confidence": 0.98,
    }


class GovernanceRegressionTests(unittest.TestCase):
    def test_phi_mask_round_trip_survives_multiple_replacement_lengths(self) -> None:
        original = (
            "Patient Name: Jane Smith. DOB: 11/20/1992. "
            "SSN: 123-45-6789. Phone: 212-555-0199."
        )
        masked = mask_phi_data_v2(original)
        self.assertNotIn("Jane Smith", masked.anonymized_text)
        self.assertEqual(masked.restore(), original)

    def test_missing_required_field_raises_structured_error(self) -> None:
        payload = _valid_input()
        active_claim = payload["active_claim_payload"]
        assert isinstance(active_claim, dict)
        del active_claim["claim_id"]

        with self.assertRaises(ValidationError) as caught:
            validate_inputs(payload)

        self.assertEqual(caught.exception.code, "MISSING_REQUIRED_FIELD")
        self.assertEqual(caught.exception.field, "claim_id")

    def test_billing_action_falls_back_to_claim_payload(self) -> None:
        validated = validate_inputs(_valid_input())
        self.assertEqual(validated["billing_action_type"], "STANDARD")

    def test_streaming_samples_are_deterministic(self) -> None:
        self.assertEqual(
            build_streaming_samples(0.96),
            build_streaming_samples(0.96),
        )

    def test_three_plan_cob_returns_full_order(self) -> None:
        payload = _valid_input()
        active_claim = payload["active_claim_payload"]
        assert isinstance(active_claim, dict)
        active_claim["coverage_plans"] = [
            {
                "payer_name": "September Plan",
                "covered_person_relationship": "DEPENDENT_CHILD",
                "holder_dob": "09/11/1980",
                "plan_start_date": "01/01/2019",
            },
            {
                "payer_name": "March Plan",
                "covered_person_relationship": "DEPENDENT_CHILD",
                "holder_dob": "03/15/1985",
                "plan_start_date": "01/01/2020",
            },
            {
                "payer_name": "July Plan",
                "covered_person_relationship": "DEPENDENT_CHILD",
                "holder_dob": "07/22/1975",
                "plan_start_date": "01/01/2018",
            },
        ]

        result = run_cob_check(active_claim)
        self.assertEqual(
            result["payer_order"],
            ["March Plan", "July Plan", "September Plan"],
        )
        self.assertEqual(result["rule_applied"], "COMMERCIAL_BIRTHDAY_RULE")

    def test_cms_msp_working_aged_large_employer_pays_before_medicare(self) -> None:
        active_claim = {
            "policy_types": ["MEDICARE", "EMPLOYER"],
            "coverage_plans": [
                {
                    "payer_name": "Medicare",
                    "payer_type": "MEDICARE",
                    "holder_dob": "01/01/1955",
                    "plan_start_date": "01/01/2020",
                },
                {
                    "payer_name": "Employer GHP",
                    "payer_type": "EMPLOYER_GHP",
                    "holder_dob": "12/31/1955",
                    "plan_start_date": "01/01/2018",
                },
            ],
            "coordination_context": {
                "beneficiary_age": 71,
                "current_employment": True,
                "employer_size": 20,
            },
        }
        result = run_cob_check(active_claim)
        self.assertEqual(result["rule_applied"], "CMS_MSP_EMPLOYER_PRIMARY")
        self.assertEqual(result["payer_order"], ["Employer GHP", "Medicare"])

    def test_cms_msp_small_employer_keeps_medicare_primary(self) -> None:
        active_claim = {
            "policy_types": ["MEDICARE", "EMPLOYER"],
            "coverage_plans": [
                {
                    "payer_name": "Employer GHP",
                    "payer_type": "EMPLOYER_GHP",
                    "holder_dob": "01/01/1955",
                    "plan_start_date": "01/01/2018",
                },
                {
                    "payer_name": "Medicare",
                    "payer_type": "MEDICARE",
                    "holder_dob": "12/31/1955",
                    "plan_start_date": "01/01/2020",
                },
            ],
            "coordination_context": {
                "beneficiary_age": 71,
                "current_employment": True,
                "employer_size": 19,
            },
        }
        result = run_cob_check(active_claim)
        self.assertEqual(result["rule_applied"], "CMS_MSP_MEDICARE_PRIMARY")
        self.assertEqual(result["payer_order"], ["Medicare", "Employer GHP"])

    def test_unknown_commercial_relationship_requires_contract_review(self) -> None:
        active_claim = {
            "policy_types": ["MEDICAL"],
            "coverage_plans": [
                {
                    "payer_name": "Plan A",
                    "holder_dob": "01/01/1980",
                    "plan_start_date": "01/01/2020",
                },
                {
                    "payer_name": "Plan B",
                    "holder_dob": "12/31/1980",
                    "plan_start_date": "01/01/2019",
                },
            ],
        }
        result = run_cob_check(active_claim)
        self.assertEqual(result["rule_applied"], "CONTRACT_RULES_REQUIRED")
        self.assertTrue(result["requires_specialist_review"])

    def test_judge_rejects_low_risk_human_review_conflict(self) -> None:
        result = {
            "status": "APPROVED_FOR_INTEGRATION",
            "risk_tier": "LOW",
            "human_review_required": True,
            "next_action": "SYNC_TO_CORE_SYSTEM",
            "evidence": ["All deterministic gates passed."],
        }
        verdict = run_judge_review("CLM-TEST-002", [], result)
        self.assertTrue(verdict["escalate"])
        self.assertTrue(any("R2" in item for item in verdict["conflicts"]))

    def test_maestro_case_plan_has_required_primary_and_secondary_stages(self) -> None:
        root = Path(__file__).resolve().parents[2]
        plan = json.loads(
            (root / "case-models" / "omnishield360-case-plan.json").read_text(
                encoding="utf-8"
            )
        )
        primary = {stage["name"] for stage in plan["primaryStages"]}
        secondary = {stage["name"] for stage in plan["secondaryStages"]}
        self.assertEqual(primary, {"Intake", "Review", "Settlement", "Closure"})
        self.assertTrue(
            {"Pending with Provider", "Fraud Hold", "Legal Estates Hold", "Denied", "Withdrawn"}
            .issubset(secondary)
        )
        self.assertEqual(plan["trigger"]["type"], "WAIT_FOR_CONNECTOR")

    def test_uipath_mapping_exposes_case_workers(self) -> None:
        root = Path(__file__).resolve().parents[2]
        mapping = json.loads((root / "uipath.json").read_text(encoding="utf-8"))
        functions = mapping["functions"]
        expected = {
            "intake_assessment",
            "clinical_assessment",
            "adjudication_assessment",
            "compliance_assessment",
            "judge_assessment",
            "settlement_sync",
        }
        self.assertTrue(expected.issubset(functions))

    def test_intake_worker_returns_case_patch_not_stage_transition(self) -> None:
        result = intake_assessment(_valid_input())
        self.assertEqual(result["outcome"], "COMPLETED")
        self.assertEqual(result["case_patch"]["intakeStatus"], "VERIFIED")
        self.assertNotIn("next_stage", result)

    def test_settlement_worker_requires_human_approval(self) -> None:
        result = settlement_sync(
            {"claim_id": "CLM-TEST-003", "settlement_approved": False}
        )
        self.assertEqual(result["outcome"], "HUMAN_ACTION_REQUIRED")
        self.assertEqual(result["case_patch"]["syncStatus"], "BLOCKED")
        self.assertEqual(result["human_task"]["persona"], "Claims Adjuster")


if __name__ == "__main__":
    unittest.main()
