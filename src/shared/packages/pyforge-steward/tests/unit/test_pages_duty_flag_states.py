"""Story 102.3 (CAP-168 / feature-flag-governance CAP-4): the pages duty in both flag states."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states, flagd_tree

from pyforge.steward import pages_duty
from pyforge.steward.pages_duty import BUILD_ARGV, EXIT_PAGES_REFUSAL, PagesDeps, run_build

_FLAG = "pyforge.steward.pages_duty"

flag_provider = make_flag_provider_fixture()


@dataclass
class _Proc:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


@flag_states(_FLAG)
def test_build_dry_run_follows_the_flag(flag_provider: dict[str, bool], tmp_path: Path) -> None:
    calls: list[list[str]] = []
    written: list[Path] = []

    def runner(argv: list[str], cwd: Path) -> _Proc:
        calls.append(list(argv))
        return _Proc()

    deps = PagesDeps(
        root=tmp_path,
        runner=runner,
        flag_on=lambda: flag_provider[_FLAG],
        registry_verdict=lambda: ("live", ""),
        write_fleet_status=lambda root: written.append(root) or root,
    )
    result = run_build(deps, dry_run=True)
    assert calls == [] and written == []  # a dry run runs nothing in either state
    if flag_provider[_FLAG]:
        assert result.ok is True
        assert result.details["argv"] == [list(BUILD_ARGV)]
    else:
        assert result.ok is False
        assert result.details["exit_code"] == EXIT_PAGES_REFUSAL
        assert _FLAG in result.summary


@flag_states("pyforge.steward.pages_duty")
def test_the_production_flag_read_follows_the_tree(
    flag_provider: dict[str, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The duty's real read (`_production_deps`, `read_boolean` over the flagd tree), not a lambda."""
    enabled = flag_provider["pyforge.steward.pages_duty"]
    tree = flagd_tree(tmp_path, {"pyforge.steward.pages_duty": "on" if enabled else "off"})
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    monkeypatch.delenv("PYFORGE_ENVIRONMENT", raising=False)
    assert pages_duty._production_deps(tmp_path).flag_on() is enabled
