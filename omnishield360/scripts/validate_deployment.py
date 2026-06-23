"""Validate deployment prerequisites for OmniShield 360.

This script checks that the repository contains the expected deployment
artifacts and that the required environment variables are defined.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STRICT_MODE = "--strict" in sys.argv
EXPECTED_FILES = [
    REPO_ROOT / "main.py",
    REPO_ROOT / "pyproject.toml",
    REPO_ROOT / "uipath.json",
    REPO_ROOT / ".github" / "workflows" / "deploy.yml",
    REPO_ROOT / "docs" / "deployment.md",
    REPO_ROOT / "docs" / "security.md",
]

REQUIRED_ENV_VARS = [
    "UIPATH_CLIENT_ID",
    "UIPATH_CLIENT_SECRET",
    "UIPATH_TENANT_NAME",
    "UIPATH_FOLDER_NAME",
    "UIPATH_USER_KEY",
]


def check_file(path: Path) -> bool:
    if path.exists():
        print(f"[OK] Found {path.relative_to(REPO_ROOT)}")
        return True
    print(f"[MISSING] Missing {path.relative_to(REPO_ROOT)}")
    return False


def check_env(strict: bool) -> bool:
    all_good = True
    for name in REQUIRED_ENV_VARS:
        value = os.getenv(name)
        if value and value.strip():
            print(f"[OK] {name} is configured")
        else:
            if strict:
                print(f"[ERROR] {name} is not set")
                all_good = False
            else:
                print(f"[OPTIONAL] {name} is not set (needed only for cloud deployment)")
    return all_good


def main() -> int:
    print("OmniShield 360 deployment validation")
    print(f"Strict mode: {'enabled' if STRICT_MODE else 'disabled'}")
    print("=" * 40)

    file_checks = [check_file(path) for path in EXPECTED_FILES]
    env_ok = check_env(STRICT_MODE)

    print("=" * 40)
    if all(file_checks) and (env_ok or not STRICT_MODE):
        print("Deployment prerequisites look ready.")
        return 0

    print("Some deployment prerequisites are still missing.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
