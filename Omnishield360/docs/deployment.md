# Deployment Guide

## 1. Local validation
1. Install dependencies with `pip install -e .` or `uv pip install -e .`
2. Run contract tests with `python -m unittest discover -s src/testing -p "test_*.py"`
3. Run the scenario suite with `python src/testing/run_tests.py`
4. Validate the repo with `python scripts/validate_deployment.py`
5. Use `python main.py` only as a local compatibility/demo execution

## 2. Environment configuration
1. Copy [.env.example](../.env.example) to `.env`
2. Replace the placeholder values with your real UiPath credentials
3. Keep the file local and never commit it

Example values:
- `UIPATH_CLIENT_ID` = your UiPath external application client ID
- `UIPATH_CLIENT_SECRET` = your UiPath external application client secret
- `UIPATH_TENANT_NAME` = your UiPath tenant name
- `UIPATH_FOLDER_NAME` = the target Orchestrator folder
- `UIPATH_USER_KEY` = your UiPath authentication key

## 3. Strict deployment validation
Run the following before you publish:

```bash
python scripts/validate_deployment.py --strict
```

This checks that the repo artifacts exist and that the cloud credentials are configured.

## 4. Package and publish
1. Install the UiPath CLI with `npm install -g @uipath/cli`
2. Authenticate with `uip login`
3. Package with `uipath pack`
4. Publish with `uipath publish`
5. Confirm the generated package appears in your tenant feed

## 5. Orchestrator setup
- Create a Case Management project in Studio Web.
- Configure a Wait for Connector trigger whose payload becomes the case fields.
- Map `claimId` as the external case key.
- Build primary/secondary stages from
  [the Case Plan specification](../case-models/omnishield360-case-plan.json).
- Bind the published worker functions from [uipath.json](../uipath.json).
- Configure Action apps, retries, idempotency, SLAs, escalations, re-entry, and
  Case App.
- Publish, deploy, and activate the Case Plan in the target folder.

## 6. CI/CD
The workflow in [.github/workflows/deploy.yml](../.github/workflows/deploy.yml) runs tests on pull requests and publishes on pushes to `main` when the required secrets are configured.
