"""Smoke test — the package imports and the REAL CLI surface answers
(updated for Story 1.2).

The scaffold-era "returns 0 no matter what" contract is retired with the
stub: an empty-dir scan is honestly ``not-applicable`` (exit 0) and a bare
invocation is a usage error (exit 2, never 0).
"""

import pyforge.warden
from pyforge.warden.cli import main


def test_version_exposed():
    assert pyforge.warden.__version__ == "0.1.0"


def test_scan_of_empty_dir_exits_zero(tmp_path):
    assert main(["scan", str(tmp_path)]) == 0


def test_bare_invocation_is_a_usage_error():
    assert main([]) == 2
