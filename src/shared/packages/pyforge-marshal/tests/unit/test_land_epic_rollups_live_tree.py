"""Story 83.21's AC 3, judged by Doctor's own ``ledger-regression`` command over the promotion commit.

Story 116.1 (spec-pyforge-marshal:CAP-305): the test moved here from ``test_land_epic_rollups.py``, marked
``live_tree``. It used to ``importorskip`` ``pyforge.doctor``, which the marshal env does not carry, so it skipped
in marshal's own suite. It now runs Doctor's documented command module the way Story 115.2's adapter does -- a
``python -c`` bootstrap that puts this tree's ``src/shared/packages/pyforge-doctor/src`` first on ``sys.path`` and
runs ``pyforge.doctor.sources`` as ``__main__`` -- with the estate's primary clone as its working directory (Doctor
judges the repo it is invoked from). No marshal test imports ``pyforge.doctor``. The estate and the finalize are
``test_land_epic_rollups.py``'s own; the rule-level twin of this check stays there.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_land_epic_rollups import _ac3_finalize, _git

pytestmark = pytest.mark.live_tree

#: This tree's Doctor source, put first on ``sys.path`` by the bootstrap.
_DOCTOR_SOURCE = Path(__file__).resolve().parents[6] / "src" / "shared" / "packages" / "pyforge-doctor" / "src"

#: Doctor's documented command module (the one the ``ledger-regression-check`` task runs), as ``__main__``.
_DOCTOR_BOOTSTRAP = (
    "import runpy, sys; "
    f"sys.path.insert(0, {str(_DOCTOR_SOURCE)!r}); "
    "runpy.run_module('pyforge.doctor.sources', run_name='__main__', alter_sys=True)"
)


def test_ledger_regression_reports_ok_over_the_ac3_promotion_commit(tmp_path: Path, monkeypatch) -> None:
    """AC 3, through the ``ledger-regression`` detector itself (Doctor's command, ``--json``) over the
    promotion commit's own range: exit 0 and one ``ok`` row that compared one ledger. A tree without Doctor's
    source fails here (the command exits non-zero), never skips."""
    _origin, primary, parent, commit = _ac3_finalize(tmp_path, monkeypatch)
    _git(primary, "fetch", "origin", "main")

    result = subprocess.run(
        [sys.executable, "-c", _DOCTOR_BOOTSTRAP, "ledger-regression", "--base", parent, "--head", commit, "--json"],
        cwd=primary,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )

    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    rows = json.loads(result.stdout)
    assert len(rows) == 1, rows
    [row] = rows
    assert row["status"] == "ok", row["message"]
    assert row["evidence"]["ledgers_compared"] == 1
