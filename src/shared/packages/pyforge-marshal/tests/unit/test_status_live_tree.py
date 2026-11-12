"""``marshal status --run`` over its default ports, read against this checkout.

Story 116.4 (spec-pyforge-marshal:CAP-305): the tree-read guard runs every package-half test off the tree (a working
directory outside the repository, ``cli/config.py`` anchored in a bare checkout). The default ``GitVcs`` reads the
repository of the working directory, so this test reports ``found`` only from inside this checkout; it moved here
from ``test_status.py``'s ``TestRunDetail``, marked ``live_tree``, and fails, never skips, outside it. Every other
test stays in ``test_status.py``, and this module imports the helpers both use from it by name.
"""

from __future__ import annotations

import pytest
from test_status import _args, _payload

from pyforge.marshal.cli import status as status_cli

pytestmark = pytest.mark.live_tree


class TestRunDetail:
    def test_run_status_with_default_ports_and_run_flag_does_not_crash(self, capsys):
        """Smoke test over the real GitVcs/LocalFs/BmadLoopHarness default
        construction path (mirrors ``TestRunStatus``'s own identical
        precedent) -- a run id naming nothing real for a project naming
        nothing real stays a clean, reportable 'not found', never a
        crash."""
        exit_code = status_cli.run_status(_args(project="no-such-project-xyz", run="no-such-run-xyz"))

        assert isinstance(exit_code, int)
        payload = _payload(capsys)
        assert payload["data"]["found"] is False
