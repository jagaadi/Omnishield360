# OmniShield 360 — Deployment & Execution Checklist

## 1. Before You Start
- Make sure Python 3.11+ is installed.
- Install the project dependencies.
- Ensure the UiPath CLI is installed.
- Have your UiPath tenant credentials ready.

## 2. Local Setup
1. Copy `.env.example` to `.env`.
2. Fill in the required values:
   - `UIPATH_CLIENT_ID`
   - `UIPATH_CLIENT_SECRET`
   - `UIPATH_TENANT_NAME`
   - `UIPATH_FOLDER_NAME`
   - `UIPATH_USER_KEY`
3. Install dependencies:
   - `pip install -e .`
   - or `uv pip install -e .`
4. Run the scenario tests:
   - `python src/testing/run_tests.py`
5. Validate the deployment setup:
   - `python scripts/validate_deployment.py`

## 3. UiPath Authentication
1. Run `uip login`.
2. Confirm your tenant and folder are correct.
3. Verify the CLI is connected to the intended environment.

## 4. Package the Solution
1. Run `uipath pack`.
2. Confirm the build artifact is created successfully.
3. Save the package location for the publish step.

## 5. Publish to Orchestrator
1. Run `uipath publish`.
2. Confirm the package appears in the correct tenant feed.
3. Verify the package version you are publishing.

## 6. Create or Update the Process in Orchestrator
1. Open UiPath Automation Cloud.
2. Go to **Automations > Processes**.
3. Create a new process or select the published package.
4. Choose the correct folder.
5. Pick the correct runtime environment.
6. Confirm the input schema matches [uipath.json](../uipath.json).

## 7. Run the Process
1. Start the process manually or via a trigger.
2. Pass the JSON payload into the process.
3. Use data from [src/testing/test-fixtures.json](../src/testing/test-fixtures.json) for testing.

## 8. Monitor Execution
1. Open **Monitoring > Jobs**.
2. Check the status of each run.
3. Review logs for `print()` output and step transitions.
4. Verify the final result and routing behavior.

## 9. Maestro / Case Tracking
1. Open the case view for the related claim.
2. Check the stage timeline.
3. Review the output variables such as:
   - `status`
   - `risk_tier`
   - `next_action`
   - `human_review_required`
4. Route cases to human approval if needed.

## 10. Troubleshooting
- If authentication fails, check the tenant and credentials.
- If packaging fails, confirm the CLI is installed and the project builds.
- If the run fails, review the job logs and payload inputs.
- If the process does not start, check folder permissions and runtime setup.

## 11. Recommended Final Checklist
- Environment file is created and filled in.
- Tests run successfully.
- Package is built.
- Package is published.
- Process is bound in Orchestrator.
- Payload is valid.
- Logs are visible.
- Case flow is monitored in Maestro.
