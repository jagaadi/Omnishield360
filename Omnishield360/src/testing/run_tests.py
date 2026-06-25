"""
OmniShield 360 - Automated Scenario Test Runner
Loads all 5 scenarios from test-fixtures.json and runs them against main().
Verifies expected status and risk tier for each path.
Run with: python src/testing/run_tests.py
"""

import json
import sys
import os

# Add root to path so imports work from this location
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from main import main

FIXTURES_PATH = os.path.join(os.path.dirname(__file__), "test-fixtures.json")

GREEN = "\033[92m"
RED   = "\033[91m"
CYAN  = "\033[96m"
RESET = "\033[0m"
BOLD  = "\033[1m"


def run_all_scenarios():
    with open(FIXTURES_PATH) as f:
        data = json.load(f)

    scenarios = data["scenarios"]
    passed = 0
    failed = 0

    print(f"\n{BOLD}{CYAN}═══════════════════════════════════════════════════════{RESET}")
    print(f"{BOLD}{CYAN}   OmniShield 360 — Full Scenario Test Suite{RESET}")
    print(f"{BOLD}{CYAN}═══════════════════════════════════════════════════════{RESET}\n")

    for scenario in scenarios:
        sid         = scenario["id"]
        description = scenario["description"]
        inputs      = scenario["inputs"]
        exp_status  = scenario["expected_status"]
        exp_tier    = scenario["expected_risk_tier"]

        print(f"{BOLD}▶ {sid}{RESET}")
        print(f"  {description}")
        print(f"  {'─'*55}")

        result = main(inputs)

        actual_status = result.get("status", "")
        actual_tier   = result.get("risk_tier", "")

        status_ok = actual_status == exp_status
        tier_ok   = actual_tier == exp_tier

        if status_ok and tier_ok:
            print(f"  {GREEN}✅ PASSED{RESET}  Status: {actual_status} | Risk: {actual_tier}")
            passed += 1
        else:
            print(f"  {RED}❌ FAILED{RESET}")
            if not status_ok:
                print(f"     Status   → Expected: {exp_status} | Got: {actual_status}")
            if not tier_ok:
                print(f"     RiskTier → Expected: {exp_tier}   | Got: {actual_tier}")
            failed += 1

        print()

    print(f"{BOLD}{CYAN}═══════════════════════════════════════════════════════{RESET}")
    total = passed + failed
    colour = GREEN if failed == 0 else RED
    print(f"{colour}{BOLD}  Results: {passed}/{total} passed | {failed} failed{RESET}")
    print(f"{BOLD}{CYAN}═══════════════════════════════════════════════════════{RESET}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_all_scenarios()
