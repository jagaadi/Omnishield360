@echo off
setlocal

REM OmniShield 360 - Deployment Starter
REM This batch file helps you begin the deployment flow safely.

color 0B
echo.
echo ==========================================================
echo OmniShield 360 - Deployment Starter
echo ==========================================================
echo.

echo [1/5] Checking repository setup...
python scripts\validate_deployment.py
if errorlevel 1 (
    echo.
    echo Repository validation failed.
    echo Please fix the setup before continuing.
    pause
    exit /b 1
)

echo.
echo [2/5] Running test scenarios...
python src\testing\run_tests.py
if errorlevel 1 (
    echo.
    echo Tests failed. Please resolve issues before deployment.
    pause
    exit /b 1
)

echo.
echo [3/5] Running compile check...
python -m compileall .
if errorlevel 1 (
    echo.
    echo Compile check failed.
    pause
    exit /b 1
)

echo.
echo [4/5] Deployment steps ready.
set /p run_publish="Do you want to continue with UiPath authentication and publish? (y/n): "
if /I not "%run_publish%"=="y" (
    echo.
    echo Skipping publish.
    echo Run these later if needed:
    echo   uip login
    echo   uipath pack
    echo   uipath publish
    pause
    exit /b 0
)

echo.
echo [5/5] Authenticating with UiPath...
uip login
if errorlevel 1 (
    echo.
    echo UiPath login failed.
    echo Check your credentials and try again.
    pause
    exit /b 1
)

echo.
echo Packaging the project...
uipath pack
if errorlevel 1 (
    echo.
    echo Packaging failed.
    pause
    exit /b 1
)

echo.
echo Publishing the package...
uipath publish
if errorlevel 1 (
    echo.
    echo Publish failed.
    pause
    exit /b 1
)

echo.
echo Deployment flow completed successfully.
echo Next actions:
echo - Open UiPath Automation Cloud
echo - Go to Automations > Processes
echo - Bind the package to the correct folder/runtime
echo - Run the process with a JSON payload

echo.
pause
exit /b 0
