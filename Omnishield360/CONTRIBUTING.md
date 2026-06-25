# Contributing to OmniShield 360

OmniShield 360 is owned and maintained by
[Aditya Panigrahy](https://www.linkedin.com/in/aditya-narayan-panigrahy/).

Repository: [jagaadi/Omnishield360](https://github.com/jagaadi/Omnishield360)

## Reporting issues

Use the project’s
[GitHub issue tracker](https://github.com/jagaadi/Omnishield360/issues) for
bugs, feature proposals, and documentation corrections.

## Pull requests

1. Fork the repository and create a focused branch.
2. Run the regression and scenario suites.
3. Run strict typing and deployment validation.
4. Explain the business impact and any Maestro Case lifecycle changes.
5. Avoid committing credentials, PHI, tenant identifiers, or production data.

```bash
python -m unittest discover -s src/testing -p "test_*.py"
python src/testing/run_tests.py
python -m mypy
python scripts/validate_deployment.py
```

Unless explicitly stated otherwise, contributions submitted to this repository
are provided under the project’s Apache License, Version 2.0.
