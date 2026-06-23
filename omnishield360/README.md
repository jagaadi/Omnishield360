# OmniShield 360
### Adaptive Payer-Provider Lifecycle & Anti-Litigation Governance Desk

**Author:** Genius  
**Track:** UiPath AgentHack 2026 — Track 1: Agentic Case Management  
**Framework:** Pure Pro-Code | UiPath Coded Agents Python SDK + LangGraph  
**License:** Apache 2.0  

---

## 💡 Problem Statement

Healthcare payer operations lose millions annually due to **context complexity** and **compliance penalties** that rigid RPA and standard BPMN workflows cannot handle:

- Mixed-media intake (electronic forms + handwritten ambulance runsheets) breaks traditional parsers
- Multi-policy dual coverage (Coordination of Benefits) requires dynamic legal reasoning
- Automated billing engines lack guardrails — contacting deceased individuals triggers **FDCPA / TCPA class-action lawsuits** costing millions in settlements

**OmniShield 360** replaces brittle linear automation with an adaptive, code-first Coded Agent governed by UiPath Automation Cloud Orchestrator as the enterprise control plane.

---

## 🏗️ Architecture — 4-Stage Process Tree

```
[ROOT] UiPath Orchestrator — Execution & Governance Control Plane
│
├── [STAGE 1] Intake & Security Isolation
│     ├── Document Understanding IXP (OCR — Electronic + Handwriting)
│     ├── UiPath Validation Station HITL (Confidence < 85% gate)
│     ├── AI Trust Layer — In-Flight PII / PHI Masking (HIPAA)
│     └── API Workflow — Core EHR Sync (Epic / Facets / QNXT)
│
├── [STAGE 2] Clinical Care & Authorization Gates
│     ├── PCP Referral Verification Crawler  [src/agents/pcp_referral.py]
│     ├── Medical Necessity Validation (Agent Builder Low-Code Worker)
│     └── Clinical Director Sign-Off (UiPath Action Center HITL)
│
├── [STAGE 3] Complex Claims Adjudication
│     ├── Anti-Fraud Duplicate Audit  [src/agents/deduplication.py]  O(n) SHA-256
│     ├── Ambulance & Passport Claim Sorting
│     └── COB Engine — Birthday Rule Dual Coverage  [src/agents/cob_engine.py]
│
└── [STAGE 4] Risk Mitigation & Legal Defense
      ├── SSDI / Death Master File Shield  [src/agents/compliance.py]
      ├── Orchestrator Circuit-Breaker Asset (freezes all outbound billing)
      └── Legal Estates HITL + Arbitration Audit Binder
```

---

## 📁 Repository Structure

```
omnishield360-coded-agent/
│
├── main.py                          Core agent entrypoint (all stages)
├── pyproject.toml                   Python package config
├── uipath.json                      Orchestrator function mapping
├── .env.example                     Environment variable template
│
├── src/
│   ├── agents/
│   │   ├── compliance.py            SSDI / DMF anti-litigation shield
│   │   ├── deduplication.py         O(n) duplicate fraud detection
│   │   ├── pcp_referral.py          EHR referral verification
│   │   ├── cob_engine.py            Dual-coverage Birthday Rule engine
│   │   └── pii_masker.py            In-flight HIPAA PHI tokenization
│   ├── workflows/
│   │   ├── schemas.py               Standardized input/output schema
│   │   └── routing.py               Decision routing helpers
│   ├── integrations/
│   │   ├── ehr_client.py            EHR / core sync wrappers
│   │   ├── notifications.py         Notification dispatch helpers
│   │   └── audit_client.py          Audit logging helpers
│   ├── bots/
│   │   ├── ui_helpers.py            Bot-friendly UI utility helpers
│   │   └── retry_utils.py           Retry handling utilities
│   └── testing/
│       ├── test-fixtures.json       5 deterministic scenario payloads
│       └── run_tests.py             Automated test runner
│
├── docs/
│   ├── deployment.md                Deployment guide
│   ├── security.md                  Security & governance notes
│   └── runbooks.md                  Operational runbook
│
├── scripts/
│   └── validate_deployment.py       Checks deployment prerequisites
│
├── process-models/
│   ├── process-model.bpmn           Full BPMN 2.0 annotated process model
│   └── mock.json                    Studio Web mock override definitions
│
└── .github/workflows/
    └── deploy.yml                   CI/CD: test → pack → publish to Orchestrator
```

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/uipath-agenthack-omnishield360.git
cd uipath-agenthack-omnishield360

# 2. Install dependencies
pip install uv
uv venv && source .venv/bin/activate
uv pip install -e .

# 3. Copy environment template
cp .env.example .env

# 4. Run all 5 test scenarios
python src/testing/run_tests.py

# 5. Validate deployment prerequisites
python scripts/validate_deployment.py

# Optional: strict check for cloud deployment secrets
python scripts/validate_deployment.py --strict

# 6. Run the full batch deployment helper (Windows)
scripts\run_uipath_pipeline.bat

# 7. Run the deployment starter (recommended for a first deployment)
scripts\\start_deployment.bat

# 8. Run locally with a specific scenario
python main.py
```

---

## 🎭 5 Testable Scenarios

| # | ID | Expected Status | Risk |
|---|---|---|---|
| 1 | HAPPY_PATH_ELECTRONIC | `APPROVED_FOR_INTEGRATION` | LOW |
| 2 | HANDWRITTEN_LOW_CONFIDENCE | `SUSPENDED_DATA_REMEDIATION` | MEDIUM |
| 3 | **DECEASED_LITIGATION_SHIELD** | `HALTED_COMPLIANCE_BREACH` | **CRITICAL** |
| 4 | DUAL_COVERAGE_COB_BREAK | `SUSPENDED_DUAL_COVERAGE` | MEDIUM |
| 5 | DUPLICATE_CLAIM_FRAUD | `SUSPENDED_DUPLICATE_CLAIM` | HIGH |

---

## ☁️ Deploying to UiPath Orchestrator

Use this exact flow for a real deployment:

```bash
# 1. Create your real environment file
cp .env.example .env

# 2. Fill in the UiPath credentials in .env
#    (client ID, client secret, tenant name, folder name, user key)

# 3. Validate the setup
python scripts/validate_deployment.py --strict

# 4. Authenticate to UiPath
uip login

# 5. Package the project
uipath pack

# 6. Publish to your tenant feed
uipath publish
```

After publish:
1. Open **UiPath Automation Cloud**
2. Go to **Automations → Processes**
3. Select the published package
4. Bind it to the correct folder and runtime
5. Trigger the process with the JSON payload format used by the test fixtures

All `print()` output streams to **Monitoring → Jobs → View Logs**.

See [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md), [DEPLOYMENT_MATRIX.md](DEPLOYMENT_MATRIX.md), and [docs/deployment.md](docs/deployment.md) for full details.

---

## 🤖 UiPath for Coding Agents — Bonus Points

This solution was developed code-first using **Claude Code** via the UiPath CLI skills infrastructure:

```bash
uip skills install --agents claude
uipath codedagent init --template langgraph
```

AI assistance was used to design the O(n) SHA-256 deduplication algorithm, the regex-based PII tokenization engine, and the Birthday Rule COB logic.

---

## 📜 License

```
Copyright 2026 Genius

Licensed under the Apache License, Version 2.0
http://www.apache.org/licenses/LICENSE-2.0
```
