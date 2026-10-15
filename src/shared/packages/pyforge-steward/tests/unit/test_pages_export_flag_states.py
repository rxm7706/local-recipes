"""Story 102.4 (CAP-168 / feature-flag-governance CAP-4): the artifact download in both flag states."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

flag_provider = make_flag_provider_fixture()

_SCRIPT = Path(__file__).resolve().parents[6] / "scripts" / "pages_artifact_download.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("pages_artifact_download_flag_under_test", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@flag_states("pyforge.steward.pages_duty")
def test_the_download_follows_the_flag(flag_provider: dict[str, bool], tmp_path: Path, capsys) -> None:
    calls: list[list[str]] = []

    def gh(argv: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, json.dumps([]), "")

    enabled = flag_provider["pyforge.steward.pages_duty"]
    script = _load_script()
    env_file = tmp_path / "github_env"
    assert script.main(["--github-env", str(env_file)], runner=gh, flag_on=enabled, root=tmp_path) == 0
    assert script.main(["--flag-env"], runner=gh, flag_on=enabled, root=tmp_path) == 0
    out = capsys.readouterr().out
    if enabled:
        assert calls and calls[0][:3] == ["gh", "run", "list"]  # the selection runs
        assert env_file.read_text(encoding="utf-8") == "KEDRO_VIZ_EXPORT=absent\n"
        assert "PYFORGE_PAGES_DUTY=1" in out
    else:
        assert calls == []  # returns before any gh call
        assert not env_file.exists()
        assert "PYFORGE_PAGES_DUTY=0" in out
