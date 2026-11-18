"""Unit tests for ``scripts/docs_station_verify.py`` (doctor Story 60.2,
spec-pyforge-doctor CAP-84): docs/reference/station-verify-commands.md
generated from each station's ``marshal-policy.toml``.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest

pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _docs_gen_common as common
import docs_station_verify as m

_STAMP = {"derived_at": "2026-01-01T00:00:00", "tree": "deadbeef"}

_ALPHA = """\
# a comment naming verify_commands = ["not this"]
gate_mode = "none"
verify_commands = [
  "pixi run --frozen -e pyforge-alpha pyforge-alpha-test",
  "pixi run --frozen -e pyforge-ci pyforge-deps-test",
]

[epic_surfaces]
"1" = ["src/alpha/**"]
"""

_BETA = """\
verify_commands = ["pixi run -e pyforge-beta beta-test"]
"""


def _write_policy(root: Path, station: str, text: str) -> Path:
    path = root / m.PROJECTS_REL / f"pyforge-{station}" / m.POLICY_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_policies(root: Path) -> None:
    # Written out of order: the render sorts by station.
    _write_policy(root, "beta", _BETA)
    _write_policy(root, "alpha", _ALPHA)


def _row(content: str, station: str) -> str:
    return next(
        line for line in content.splitlines() if line.startswith(f"| {station} |")
    )


def test_render_lists_every_station_sorted_with_its_commands_verbatim(tmp_path: Path):
    _write_policies(tmp_path)

    content = m.render(tmp_path, _STAMP)

    assert content.index("| alpha |") < content.index("| beta |")
    assert _row(content, "alpha") == (
        "| alpha | `pixi run --frozen -e pyforge-alpha pyforge-alpha-test`"
        "<br>`pixi run --frozen -e pyforge-ci pyforge-deps-test` |"
    )
    assert _row(content, "beta") == "| beta | `pixi run -e pyforge-beta beta-test` |"
    assert "2 stations, as of this render." in content
    assert "not this" not in content


def test_render_reads_only_verify_commands_so_an_epic_surface_edit_changes_nothing(
    tmp_path: Path,
):
    """The reason the page is generated: minting an epic rewrites the policy
    file's ``[epic_surfaces]`` block, which this page does not mirror."""
    _write_policies(tmp_path)
    before = m.render(tmp_path, _STAMP)

    _write_policy(tmp_path, "alpha", _ALPHA + '"2" = ["src/alpha/new/**"]\n')

    assert m.render(tmp_path, _STAMP) == before


def test_render_names_the_stations_whose_commands_are_not_frozen(tmp_path: Path):
    _write_policies(tmp_path)

    content = m.render(tmp_path, _STAMP)

    assert (
        "Stations with a command that does not carry `--frozen`: `beta` (1 of 2)."
        in content
    )


def test_render_says_so_when_every_command_is_frozen(tmp_path: Path):
    _write_policy(tmp_path, "alpha", _ALPHA)

    content = m.render(tmp_path, _STAMP)

    assert "Every command in the table carries `--frozen`." in content
    assert "does not carry" not in content


def test_a_policy_with_no_verify_commands_still_gets_a_row(tmp_path: Path):
    _write_policy(tmp_path, "alpha", 'gate_mode = "none"\n')
    _write_policy(tmp_path, "beta", 'verify_commands = "not a list"\n')

    content = m.render(tmp_path, _STAMP)

    assert _row(content, "alpha") == "| alpha | *(none declared)* |"
    assert _row(content, "beta") == "| beta | *(none declared)* |"


def test_a_pipe_in_a_command_does_not_break_the_table(tmp_path: Path):
    _write_policy(tmp_path, "alpha", 'verify_commands = ["a | b"]\n')

    assert _row(m.render(tmp_path, _STAMP), "alpha") == "| alpha | `a \\| b` |"


def test_only_pyforge_projects_with_a_policy_file_are_listed(tmp_path: Path):
    _write_policies(tmp_path)
    (tmp_path / m.PROJECTS_REL / "pyforge-gamma" / "planning-artifacts").mkdir(
        parents=True
    )
    other = tmp_path / m.PROJECTS_REL / "other-project" / m.POLICY_REL
    other.parent.mkdir(parents=True)
    other.write_text('verify_commands = ["x"]\n', encoding="utf-8")

    assert list(m.station_commands(tmp_path)) == ["alpha", "beta"]


def test_no_projects_directory_renders_an_empty_table(tmp_path: Path):
    content = m.render(tmp_path, _STAMP)

    assert "0 stations, as of this render." in content


def test_a_policy_that_does_not_parse_raises_rather_than_dropping_the_row(
    tmp_path: Path,
):
    _write_policy(tmp_path, "alpha", "verify_commands = [\n")

    with pytest.raises(tomllib.TOMLDecodeError):
        m.render(tmp_path, _STAMP)


def test_render_is_deterministic(tmp_path: Path):
    _write_policies(tmp_path)

    assert m.render(tmp_path, _STAMP) == m.render(tmp_path, dict(_STAMP))


def test_main_write_then_check_roundtrip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _write_policies(tmp_path)
    monkeypatch.setattr(common, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(common, "head_stamp", lambda root, *scope: dict(_STAMP))

    monkeypatch.setattr(sys, "argv", ["docs_station_verify.py"])
    assert m.main() == 0
    page = tmp_path / "docs" / "reference" / "station-verify-commands.md"
    first = page.read_text(encoding="utf-8")
    assert first.startswith("<!-- GENERATED by scripts/docs_station_verify.py")
    assert "pixi run -e pyforge-guild docs-station-verify" in first
    assert "tree: deadbeef -->" in first

    # Idempotent: a second write on the unchanged tree is byte-identical.
    assert m.main() == 0
    assert page.read_text(encoding="utf-8") == first

    monkeypatch.setattr(sys, "argv", ["docs_station_verify.py", "--check"])
    assert m.main() == 0

    # An [epic_surfaces] edit leaves the page current ...
    _write_policy(tmp_path, "alpha", _ALPHA + '"2" = ["src/alpha/new/**"]\n')
    assert m.main() == 0

    # ... and a verify_commands edit, not yet regenerated, reds --check.
    _write_policy(tmp_path, "beta", 'verify_commands = ["pixi run -e b other"]\n')
    assert m.main() == 1

    monkeypatch.setattr(sys, "argv", ["docs_station_verify.py"])
    assert m.main() == 0
    assert "| beta | `pixi run -e b other` |" in page.read_text(encoding="utf-8")
