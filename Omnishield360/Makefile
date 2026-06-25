.PHONY: install test typecheck validate compile check pack publish

PYTHON ?= python

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m unittest discover -s src/testing -p "test_*.py"
	$(PYTHON) src/testing/run_tests.py

typecheck:
	$(PYTHON) -m mypy

validate:
	$(PYTHON) scripts/validate_deployment.py

compile:
	$(PYTHON) -m compileall -q main.py src scripts

check: test typecheck validate compile

pack: check
	uipath pack

publish: pack
	uipath publish
