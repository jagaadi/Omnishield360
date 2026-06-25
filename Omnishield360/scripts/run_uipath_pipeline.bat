@echo off
setlocal

REM OmniShield 360 UiPath deployment pipeline
REM Run this from the repository root

echo.
echo ==========================================================
echo OmniShield 360 - UiPath Deployment Pipeline
echo ==========================================================
echo.

REM 1) Validate local repo setup
python scripts\validate_deployment.py
if errorlevel 1 (
    echo.
    echo Validation failed. Please fix the repo setup before continuing.
    pause
    exit /b 1
)

echo.
REM 2) Run scenario tests
python src\testing\run_tests.py
if errorlevel 1 (
    echo.
    echo Scenario tests failed. Please fix the issues before packaging.
    pause
    exit /b 1
)

echo.
REM 3) Compile the project to confirm syntax validity
python -m compileall .
if errorlevel 1 (
    echo.
    echo Compile check failed.
    pause
    exit /b 1
)

echo.
REM 4) Ask the user for deployment confirmation
set /p confirm="Do you want to package and publish to UiPath now? (y/n): "
if /I not "%confirm%"=="y" (
    echo.
    echo Skipping package/publish step.
    echo You can run the following manually later:
    echo   uip login
    echo   uipath pack
    echo   uipath publish
    pause
    exit /b 0
)

echo.
REM 5) Package the solution
uipath pack
if errorlevel 1 (
    echo.
    echo Packaging failed.
    pause
    exit /b 1
)

echo.
REM 6) Publish to UiPath
uipath publish
if errorlevel 1 (
    echo.
    echo Publish failed.
    pause
    exit /b 1
)

echo.
REM 7) Final instructions
echo Packaging and publish completed.
echo Next steps:
echo 1. Open UiPath Automation Cloud
echo 2. Go to Automations > Processes
echo 3. Create or update the process using the published package
echo 4. Bind the process to the correct folder and runtime
echo 5. Run the process with the JSON payload from src\testing\test-fixtures.json

echo.
pause
exit /b 0
