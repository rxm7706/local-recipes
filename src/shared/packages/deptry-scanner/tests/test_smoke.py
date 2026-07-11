"""Smoke test — verifies the package builds and imports in the pixi env.

Replaced/expanded by the real E1-E4 suites (bmad-quick-dev): extractor unit
tests across all five manifest types, runner tests, and report-schema
validation.
"""

import deptry_scanner
from deptry_scanner.cli import main


def test_version_exposed():
    assert deptry_scanner.__version__ == "0.1.0"


def test_cli_entrypoint_returns_zero():
    assert main([]) == 0
