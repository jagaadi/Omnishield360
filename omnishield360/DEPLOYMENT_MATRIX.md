# Enterprise vs. Test Deployment Matrix

**Author:** Genius | OmniShield 360

---

## 📊 Environment Comparison

| Attribute | 🧪 Local / QA Sandbox | 🏢 Enterprise Production |
|---|---|---|
| **Execution Host** | Developer Machine / venv | UiPath Serverless Linux Python Pods |
| **Orchestrator Folder** | `Workspace_Genius` (Personal) | `Healthcare_Operations_Prod` (Modern) |
| **Data Source** | `test-fixtures.json` stubs | Encrypted Data Fabric Entities |
| **Credentials** | `.env` file | UiPath CyberArk / HashiCorp Vault |
| **Trigger** | `python main.py` / `uipath run` | Webhook Events / Maestro Case Signals |
| **PII Isolation** | Simulation stubs | UiPath AI Trust Layer inline proxy |
| **Logging** | Terminal stdout | Orchestrator Job Log Stream |
| **Deployment** | Manual CLI pack/publish | GitHub Actions CI/CD (auto on push) |

---

## 🛠️ Enterprise Deployment Steps

### Step 1 — Lock Dependencies
```bash
uv pip compile pyproject.toml -o requirements.lock
uipath pack --version 1.0.26 --output ./builds/
```

### Step 2 — Publish to Tenant Feed
```bash
# Pushes to shared enterprise package feed (not personal workspace)
uipath publish --package ./builds/omnishield360.1.0.26.nupkg --feed Tenant
```

### Step 3 — Bind to Serverless Process in Orchestrator
1. **Automation Cloud → Automations → Processes → Add Process**
2. Select the published package from Tenant feed
3. Assign to folder: `Healthcare_Operations_Prod`
4. Set Runtime: **Serverless (Linux Python)**
5. Add Input Schema from `uipath.json`

### Step 4 — GitHub Actions Auto-Deploy (on `main` push)
The `.github/workflows/deploy.yml` pipeline handles this automatically:
```
Code Push → Unit Tests → uipath pack → uipath publish → Orchestrator
```

Add these secrets to your GitHub repository settings:
```
UIPATH_CLIENT_ID
UIPATH_CLIENT_SECRET
UIPATH_USER_KEY
UIPATH_TENANT_NAME
```

---

## 👁️ Monitoring & Status in Orchestrator

```
Automation Cloud
  └── Monitoring
        └── Jobs
              └── OmniShield360 Run
                    ├── Status: Running / Successful / Faulted
                    ├── Duration & Container Metrics
                    └── View Logs → Live print() stream
```

**Maestro Case view:**
```
Maestro
  └── Cases
        └── Search by claim_id (e.g., CLM-2026-0003)
              ├── Stage Timeline (visual state transitions)
              ├── Variables Panel (risk_tier, status, circuit_breaker flag)
              └── HITL Task Banner (if human action required)
```
