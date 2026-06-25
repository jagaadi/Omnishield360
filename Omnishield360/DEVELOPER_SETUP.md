# Developer Setup & Installation Guide

**Author and owner:** [Aditya Panigrahy](https://www.linkedin.com/in/aditya-narayan-panigrahy/)  
**Repository:** [jagaadi/Omnishield360](https://github.com/jagaadi/Omnishield360)  
**Event:** UiPath AgentHack 2026

---

## 🛠️ Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| uv | latest | `pip install uv` |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| UiPath CLI (`uip`) | latest | `npm install -g @uipath/cli` |
| Git | any | [git-scm.com](https://git-scm.com) |

---

## 📥 1. Clone & Initialize

```bash
git clone https://github.com/jagaadi/Omnishield360.git
cd Omnishield360

# Create virtual environment and install all dependencies
pip install uv
uv venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
uv pip install -e .
```

---

## ▶️ 2. Run Locally (No Cloud Required)

```bash
# Run Maestro Case contract tests and all 7 claim scenarios
python -m unittest discover -s src/testing -p "test_*.py"
python src/testing/run_tests.py

# Run the agent directly with a custom input
python main.py
```

---

## 🔑 3. Environment Variables (for Cloud Integration)

Create a `.env` file in the project root (never commit this file):

```env
UIPATH_CLIENT_ID=your_client_id_here
UIPATH_CLIENT_SECRET=your_client_secret_here
UIPATH_TENANT_NAME=YourTenantName
UIPATH_FOLDER_NAME=Healthcare_Operations_Prod
UIPATH_USER_KEY=your_user_key_here
```

Get these values from:  
**UiPath Automation Cloud → Admin → External Applications → Add Application**  
Required OAuth Scopes: `OR.Assets.Write`, `OR.Assets.Read`, `OR.Execution.Write`, `OR.Folders.Read`

---

## 📦 4. Pack & Publish to UiPath Orchestrator

```bash
# 1. Authenticate CLI with your Labs tenant
uip login

# 2. Initialize project binding
uipath init

# 3. Verify CLI installation
uipath -lv

# 4. Package into NuGet archive
uipath pack

# 5. Publish to Orchestrator tenant feed
uipath publish

# 6. Trigger a run via REST API (headless)
curl -X POST "https://cloud.uipath.com/odata/Jobs/UiPath.Serverless.StartJob" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-UIPATH-OrganizationUnitId: YOUR_FOLDER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "startInfo": {
      "ReleaseKey": "YOUR_RELEASE_KEY",
      "Strategy": "ModernJobsCount",
      "JobsCount": 1,
      "InputArguments": "{\"active_claim_payload\":{\"claim_id\":\"CLM-TEST-001\",\"ssn_tokenized\":\"994-00-1234\",\"billing_action_type\":\"PAYMENT_MISS_ALERT\"}}"
    }
  }'
```

---

## 👁️ 5. Monitor Execution in Orchestrator

1. Log into **UiPath Automation Cloud**
2. Open your folder: `Healthcare_Operations_Prod`
3. Go to **Monitoring → Jobs**
4. Click your run → **View Logs** to stream live `print()` output
5. For case-level tracking: **Maestro → Cases → search by claim_id**

---

## 🔄 6. Build the Maestro Case Plan

1. Open Studio Web and create a **Case Management Project**
2. Configure the Wait for Connector trigger
3. Map `claimId` as the external case key
4. Build the stages from `case-models/omnishield360-case-plan.json`
5. Attach the coded functions mapped in `uipath.json`
6. Configure Action apps, SLAs, re-entry, retries, and Case App
7. Use `process-models/process-model.bpmn` only as an optional Agentic Process task
