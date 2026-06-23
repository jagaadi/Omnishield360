# Deterministic Sandbox & Mock Testing Suite

**OmniShield 360** — Test every execution branch without live databases or paid APIs.

---

## ▶️ Run All 5 Scenarios (Automated)

```bash
python src/testing/run_tests.py
```

Expected output:
```
═══════════════════════════════════════════════════════
   OmniShield 360 — Full Scenario Test Suite
═══════════════════════════════════════════════════════

▶ SCENARIO_01_HAPPY_PATH_ELECTRONIC
  ✅ PASSED  Status: APPROVED_FOR_INTEGRATION | Risk: LOW

▶ SCENARIO_02_HANDWRITTEN_LOW_CONFIDENCE
  ✅ PASSED  Status: SUSPENDED_DATA_REMEDIATION | Risk: MEDIUM

▶ SCENARIO_03_COMPLIANCE_DECEASED_LITIGATION_SHIELD
  ✅ PASSED  Status: HALTED_COMPLIANCE_BREACH | Risk: CRITICAL

▶ SCENARIO_04_DUAL_COVERAGE_COB_BREAK
  ✅ PASSED  Status: SUSPENDED_DUAL_COVERAGE | Risk: MEDIUM

▶ SCENARIO_05_DUPLICATE_CLAIM_FRAUD
  ✅ PASSED  Status: SUSPENDED_DUPLICATE_CLAIM | Risk: HIGH

═══════════════════════════════════════════════════════
  Results: 5/5 passed | 0 failed
═══════════════════════════════════════════════════════
```

---

## 🎭 Scenario Profiles

### 🟢 Scenario 1 — Happy Path (Electronic Form)
**What it tests:** Perfect OCR confidence → all gates pass → ledger integration  
**Key inputs:** `mock_ocr_confidence: 0.98`, non-deceased SSN, no duplicates, single coverage  
**Expected:** `APPROVED_FOR_INTEGRATION` | Risk: `LOW`

```bash
# Trigger manually via Orchestrator REST API
uipath run main.py '{
  "mock_ocr_confidence": 0.98,
  "active_claim_payload": {
    "claim_id": "CLM-2026-0001",
    "ssn_tokenized": "000-00-0000",
    "policy_types": ["CRITICAL_ILLNESS"],
    "billing_action_type": "STANDARD"
  },
  "historical_claims_database": []
}'
```

---

### 🟡 Scenario 2 — Handwritten Low Confidence
**What it tests:** OCR score 0.62 forces Maestro to park the thread at Validation Station HITL  
**Expected:** `SUSPENDED_DATA_REMEDIATION` | Risk: `MEDIUM`

```bash
uipath run main.py '{
  "mock_ocr_confidence": 0.62,
  "active_claim_payload": {
    "claim_id": "CLM-2026-0002",
    "ssn_tokenized": "000-00-0001",
    "policy_types": ["ACCIDENT"],
    "billing_action_type": "STANDARD"
  },
  "historical_claims_database": []
}'
```

---

### 🔴 Scenario 3 — Anti-Litigation Deceased Shield ⚡ KEY DEMO
**What it tests:** SSN `994-00-1234` matches SSDI registry. Circuit breaker fires.  
All outbound billing frozen. Orchestrator asset `Outbound_Billing_Circuit_Breaker = TRUE` written.  
**Expected:** `HALTED_COMPLIANCE_BREACH` | Risk: `CRITICAL`

```bash
uipath run main.py '{
  "mock_ocr_confidence": 0.97,
  "active_claim_payload": {
    "claim_id": "CLM-2026-0003",
    "ssn_tokenized": "994-00-1234",
    "policy_types": ["CRITICAL_ILLNESS"],
    "billing_action_type": "PAYMENT_MISS_ALERT"
  },
  "historical_claims_database": []
}'
```

---

### 🔵 Scenario 4 — Dual Coverage / COB Split
**What it tests:** Two active policies trigger Birthday Rule evaluation.  
Primary payer determined. Secondary claim dispatched automatically.  
**Expected:** `SUSPENDED_DUAL_COVERAGE` | Risk: `MEDIUM`

```bash
uipath run main.py '{
  "mock_ocr_confidence": 0.95,
  "active_claim_payload": {
    "claim_id": "CLM-2026-0004",
    "ssn_tokenized": "000-00-0002",
    "policy_types": ["DENTAL", "CRITICAL_ILLNESS"],
    "billing_action_type": "STANDARD",
    "coverage_plans": [
      {"payer_name": "Cigna Dental", "holder_dob": "07/22/1988", "plan_start_date": "01/01/2022"},
      {"payer_name": "BlueCross CI",  "holder_dob": "09/11/1990", "plan_start_date": "03/01/2021"}
    ]
  },
  "historical_claims_database": []
}'
```

---

### 🟠 Scenario 5 — Duplicate Claim Fraud
**What it tests:** SHA-256 fingerprint matches historical ledger entry. Fraud gate suspends claim.  
**Expected:** `SUSPENDED_DUPLICATE_CLAIM` | Risk: `HIGH`

```bash
uipath run main.py '{
  "mock_ocr_confidence": 0.96,
  "active_claim_payload": {
    "claim_id": "CLM-2026-0005",
    "ssn_tokenized": "000-00-0003",
    "member_id": "MBR-005",
    "provider_id": "PRV-DUPL-99",
    "cpt_code": "99213",
    "service_date": "2026-05-15",
    "policy_types": ["ACCIDENT"],
    "billing_action_type": "STANDARD"
  },
  "historical_claims_database": [
    {
      "claim_id": "CLM-2026-0005-PREV",
      "member_id": "MBR-005",
      "provider_id": "PRV-DUPL-99",
      "cpt_code": "99213",
      "service_date": "2026-05-15"
    }
  ]
}'
```
