"""Tests for scripts/realization_register_check.py (Story 100.5)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
import yaml

pytest.importorskip("jsonschema")

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import realization_register_check as check_mod  # noqa: E402
from realization_register_lib import load_register  # noqa: E402


def test_register_passes_on_tree() -> None:
    findings, code = check_mod.check(REPO_ROOT)
    assert code == 0, findings


def test_missing_bmad_loop_row_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = load_register(REPO_ROOT)
    data = copy.deepcopy(data)
    data["rows"] = [r for r in data["rows"] if r.get("package") != "bmad-loop"]
    reg = tmp_path / "docs" / "governance" / "realization-register.yaml"
    reg.parent.mkdir(parents=True)
    reg.write_text(yaml.dump(data), encoding="utf-8")
    schema = REPO_ROOT / "docs/governance/realization-register.schema.json"
    (tmp_path / "docs/governance/realization-register.schema.json").write_text(
        schema.read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(
        check_mod,
        "required_coverage_packages",
        lambda _root: {"bmad-loop", "bmad-method"},
    )
    findings, code = check_mod.check(tmp_path)
    assert code == 1
    assert any("bmad-loop" in f for f in findings)


def test_undeclared_bmad_row_fails(tmp_path: Path) -> None:
    data = load_register(REPO_ROOT)
    data = copy.deepcopy(data)
    data["rows"].append(
        {
            "package": "bmad-fictional-package",
            "env": "pyforge-guild",
            "class": "module",
            "realize": {"steps": []},
            "probe": {"expect": "exit-0", "command": ["true"]},
            "test": "pyforge-steward-test",
            "owner": "pyforge-steward",
            "authority": "test",
        }
    )
    reg = tmp_path / "docs" / "governance" / "realization-register.yaml"
    reg.parent.mkdir(parents=True)
    reg.write_text(yaml.dump(data), encoding="utf-8")
    schema = REPO_ROOT / "docs/governance/realization-register.schema.json"
    (tmp_path / "docs/governance/realization-register.schema.json").write_text(
        schema.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "pixi.toml").write_text((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    findings, code = check_mod.check(tmp_path)
    assert code == 1
    assert any("bmad-fictional-package" in f for f in findings)
