# Deployment Guide

## 1. Local validation
1. Install dependencies with `pip install -e .` or `uv pip install -e .`
2. Run the scenario suite with `python src/testing/run_tests.py`
3. Validate the repo with `python scripts/validate_deployment.py`
4. Use `python main.py` for local sample execution

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
- Create or select the target folder
- Bind the published package to the correct process
- Configure queue triggers and runtime settings
- Add required secrets in the environment or vault layer
- Verify the process input schema matches [uipath.json](../uipath.json)

## 6. CI/CD
The workflow in [.github/workflows/deploy.yml](../.github/workflows/deploy.yml) runs tests on pull requests and publishes on pushes to `main` when the required secrets are configured.
