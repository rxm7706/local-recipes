"""Story 31.1 — class-keyed playbook is the operator path (CAP-1).

Locks three contracts: `steward provision --help` names the playbook;
the playbook's six rows list pixi, cited native wire, and steward surface;
native-wire fragments are citations of install-matrix.md, never invented.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pyforge.steward.cli import INSTALL_CLASS_PLAYBOOK, build_parser
from pyforge.steward.provision import _SKIPPED_MODULES, _SUPPORTED_MODULES

_SIX_PIECES = (
    "bmad-method",
    "bmad-loop",
    "bmad-module-skill-forge",
    "bmad-labs-skills",
    "bmad-dashboard",
    "bmad-module-template",
)

# Native install commands (not every backtick — bins, ellipses, and prose
# citations of the matrix stay in the playbook as commentary). Inventing a
# new npx/uv/corepack/pnpm/cd command fails the citation lock.
_NATIVE_CMD = re.compile(r"`((?:npx |uv tool install |corepack |pnpm |cd )[^`]+)`")

# One matrix-owned native phrase each piece must carry (install-matrix.md).
_REQUIRED_CITATIONS = {
    "bmad-method": "npx bmad-method install",
    "bmad-loop": 'uv tool install "bmad-loop[tui]',
    "bmad-module-skill-forge": "npx bmad-module-skill-forge install",
    "bmad-labs-skills": "npx skills add bmad-labs/skills",
    "bmad-dashboard": "corepack prepare pnpm@10.26.2",
    "bmad-module-template": "Use this template",
}


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pixi.toml").is_file() and (parent / "_bmad-output").is_dir():
            return parent
    raise AssertionError("could not locate repository root from test file")


def _playbook_path() -> Path:
    path = _repo_root() / INSTALL_CLASS_PLAYBOOK
    assert path.is_file(), f"missing class-keyed playbook: {INSTALL_CLASS_PLAYBOOK}"
    return path


def _matrix_path() -> Path:
    return (
        _repo_root()
        / "_bmad-output/projects/pyforge-steward/planning-artifacts/specs"
        / "spec-bmad-suite-channel-product/install-matrix.md"
    )


def _playbook_data_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        if cells[0].startswith("---") or cells[0] == "Piece":
            continue
        rows.append(cells)
    return rows


def test_provision_help_names_the_class_keyed_playbook(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["provision", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "install-class-playbook.md" in out
    assert "spec-bmad-suite-install-class-wiring" in out
    assert INSTALL_CLASS_PLAYBOOK in out
    assert "class-keyed playbook" in out


def test_provision_help_does_not_invent_native_commands(capsys):
    """CLI help is a pointer. Native wire lives in the playbook, cited from the matrix."""
    with pytest.raises(SystemExit):
        build_parser().parse_args(["provision", "--help"])
    out = capsys.readouterr().out
    assert "npx " not in out
    assert "uv tool install" not in out


def test_playbook_cites_install_matrix_and_lists_six_classes():
    playbook = _playbook_path().read_text(encoding="utf-8")
    matrix = _matrix_path().read_text(encoding="utf-8")
    assert "install-matrix.md" in playbook
    rows = _playbook_data_rows(playbook)
    found = " ".join(row[0] for row in rows)
    for piece in _SIX_PIECES:
        assert piece in found, f"playbook missing piece {piece}"
        matching = [row for row in rows if piece in row[0]]
        assert matching, f"no table row for {piece}"
        row = matching[0]
        pixi, native, steward = row[2], row[3], row[4]
        assert pixi, f"{piece}: empty pixi/PATH cell"
        assert native, f"{piece}: empty native-wire cell"
        assert steward, f"{piece}: empty steward-surface cell"
        required = _REQUIRED_CITATIONS[piece]
        assert required in native, f"{piece}: native-wire missing matrix citation {required!r}"
        assert required in matrix, f"{piece}: required citation missing from install-matrix.md"
        for fragment in _NATIVE_CMD.findall(native):
            assert fragment in matrix, f"{piece}: invented native fragment {fragment!r} is not in install-matrix.md"


def test_supported_modules_unchanged_skf_not_a_module(capsys):
    assert set(_SUPPORTED_MODULES) == {
        "bmb",
        "cis",
        "manticore",
        "tea",
        "utility-skills",
    }
    assert "skf" not in _SUPPORTED_MODULES
    assert "wds" in _SKIPPED_MODULES
    with pytest.raises(SystemExit):
        build_parser().parse_args(["provision", "--help"])
    help_text = capsys.readouterr().out
    assert "skf" not in help_text
    assert "WDS" in help_text or "wds" in help_text.lower()
