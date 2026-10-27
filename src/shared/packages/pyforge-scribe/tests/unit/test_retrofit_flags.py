"""Two-state test for scribe's CAP-7 retrofit kill switch (Epic 29; ``spec-feature-flag-governance`` CAP-7).

``pyforge.scribe.bmad_estate_catalog`` (spec-pyforge-scribe CAP-32, Story 29.1) runs ON and OFF through
``pyforge.testing_kit.flags.flag_states`` and a flagd FILE tree in the same state. OFF: `scribe catalog bmad-estate`
stays listed in `catalog --help` marked disabled (Q3) and refuses with exit 2 naming the flag. ON: it reads ON and
the listing carries no marker (the render itself is ``test_catalog_bmad_estate.py``'s business).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pyforge.core.flags import read_boolean
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.cli_runner import invoke_cli
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.scribe import cli

flag_provider = make_flag_provider_fixture()
KEY = "pyforge.scribe.bmad_estate_catalog"
_BOX = re.compile(r"[\u2500-\u257f]")  # rich draws the commands panel with box characters that split a wrapped line


def _flat(output: str) -> str:
    return " ".join(_BOX.sub(" ", output).split())


@flag_states("pyforge.scribe.bmad_estate_catalog")
def test_pyforge_scribe_bmad_estate_catalog(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    on = flag_provider[KEY]
    tree = flagd_tree(tmp_path, {KEY: "on" if on else "off"})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert read_boolean(cli.BMAD_ESTATE_CATALOG_FLAG_KEY, default=True, flags_path=tree) is on
    listing = _flat(invoke_cli(cli.main, ["catalog", "--help"]).output)
    assert "bmad-estate" in listing
    if on:
        assert f"flag {KEY} is off" not in listing
        assert cli._bmad_estate_switch_on() is True
        return
    assert f"[disabled: flag {KEY} is off]" in listing
    result = invoke_cli(cli.main, ["catalog", "bmad-estate", "--check", "--root", str(tmp_path)])
    assert result.exit_code == 2
    assert f"scribe: flag {KEY} is off" in result.output


def test_no_tree_reads_the_switch_on_without_a_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYFORGE_FLAGS_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    assert cli._bmad_estate_switch_on() is None
    listing = _flat(invoke_cli(cli.main, ["catalog", "--help"]).output)
    assert f"flag {KEY} is off" not in listing
