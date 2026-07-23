"""Meta-test: the repo-wide spec-surface detector stays green.

spec-regenerable-factory CAP-3: every tracked file is governed by a spec
surface manifest or explicitly allowlisted, and no governed file drifted
without its spec's contract (memlog / sentinel) moving. This mirrors how
test_bmad_artifacts_in_sync.py enforces bmad-drift-check integrity.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
CHECKER = REPO_ROOT / "scripts" / "spec_surface_check.py"


def test_spec_surface_check_green():
    result = subprocess.run(
        [sys.executable, str(CHECKER)], capture_output=True, text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        "spec_surface_check reports findings — a tracked file is ungoverned "
        "or governed code drifted without its spec moving. Reconcile per the "
        "checker output (update the spec / bmad-spec re-derive, then "
        "--write-baseline; or add a reason-tagged allowlist entry):\n"
        + result.stdout + result.stderr
    )
