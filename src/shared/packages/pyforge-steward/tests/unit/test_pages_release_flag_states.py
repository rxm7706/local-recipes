"""Story 102.5 (CAP-168 / feature-flag-governance CAP-4): the release asset in both flag states.

The flag reaches the deploy job the way the workflow carries it: ``pages_artifact_download.py
--flag-env`` prints ``PYFORGE_PAGES_DUTY=1|0``, the build job exports it as ``pages_duty``, and the
asset steps' ``if:`` (``pages.RELEASE_ASSET_IF``) is evaluated by ``pages.release_asset_runs``.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

from pyforge.steward import pages

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

flag_provider = make_flag_provider_fixture()

_FLAG = "pyforge.steward.pages_duty"
_SCRIPT = Path(__file__).resolve().parents[6] / "scripts" / "pages_artifact_download.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("pages_artifact_download_release_under_test", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@flag_states(_FLAG)
def test_the_release_asset_follows_the_flag(flag_provider: dict[str, bool], tmp_path: Path, capsys) -> None:
    def gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
        raise AssertionError(f"--flag-env makes no gh call: {argv}")

    enabled = flag_provider[_FLAG]
    assert _load_script().main(["--flag-env"], runner=gh, flag_on=enabled, root=tmp_path) == 0
    exported = capsys.readouterr().out.strip()
    assert exported in ("PYFORGE_PAGES_DUTY=1", "PYFORGE_PAGES_DUTY=0")
    pages_duty = exported.split("=", 1)[1]

    runs_on_main = pages.release_asset_runs(pages_duty=pages_duty, event_name="push")
    assert runs_on_main is enabled  # on: the step would run; off: its if: skips it
    assert pages.release_asset_runs(pages_duty=pages_duty, event_name="pull_request") is False
