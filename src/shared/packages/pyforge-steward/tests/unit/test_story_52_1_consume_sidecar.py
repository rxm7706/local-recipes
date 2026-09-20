"""Story 52.1 — template is authoring-only; mybmad is a consume sidecar."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from pyforge.steward.provision import (
    _SKIPPED_MODULES,
    _SUPPORTED_MODULES,
    ProvisionDuty,
    provision_module,
)

REGISTER_RELATIVE = (
    "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md"
)
LIFECYCLE_SPEC = "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/SPEC.md"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _full_namespace(**overrides):
    base = {
        "module": None,
        "env": None,
        "runner": None,
        "list": False,
        "verify": False,
        "list_modules": False,
        "json": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def test_register_row_11_is_authoring_tool_only() -> None:
    text = (_repo_root() / REGISTER_RELATIVE).read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| 11 |"))
    assert "wield (authoring tool only)" in row
    assert "steward / `bmad-builder`" in row
    assert "never `steward provision --module`" in row
    assert "skip (catalog row)" not in row


def test_register_row_13_is_consume_sidecar() -> None:
    text = (_repo_root() / REGISTER_RELATIVE).read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| 13 |"))
    assert "wield (sidecar: estate Postgres schema mybmad + estate OIDC)" in row
    assert "schema mybmad" in row
    assert "COMPONENT_OIDC_*" in row
    assert "DEV FALLBACK ONLY" in row
    assert "skip (opt-in operator view only)" not in row


def test_lifecycle_nongoals_name_authoring_tool_and_consume_sidecar() -> None:
    """SPEC.md was absorbed into spec-pyforge-steward (2026-09-17); nongoals
    live on the absorbing Spec + the adoption-register companion that stayed."""
    root = _repo_root()
    stub = (root / LIFECYCLE_SPEC).read_text(encoding="utf-8")
    assert "status: absorbed" in stub
    assert "absorbed-into: spec-pyforge-steward" in stub
    parent = (
        root / "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/" / "spec-pyforge-steward/SPEC.md"
    ).read_text(encoding="utf-8")
    register = (root / REGISTER_RELATIVE).read_text(encoding="utf-8")
    corpus = parent + "\n" + register
    assert "authoring tool" in corpus
    assert "consume sidecar" in corpus
    assert "mybmad-dashboard into the platform" not in corpus


def test_provision_refuses_module_template_as_module(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("pyforge.steward.provision.repo_root", lambda: tmp_path)
    for name in ("module-template", "bmad-module-template", "template"):
        result = ProvisionDuty().run(_full_namespace(module=name))
        assert result.ok is False, name
        assert "authoring tool only" in result.summary
        assert ".claude/skills/" in result.summary
        with pytest.raises(FileNotFoundError, match="authoring tool only"):
            provision_module(name, cwd=tmp_path)
        assert name not in _SUPPORTED_MODULES
        assert name in _SKIPPED_MODULES


def test_register_wired_column_still_template_na_and_mybmad_runnable() -> None:
    text = (_repo_root() / REGISTER_RELATIVE).read_text(encoding="utf-8")
    row_11 = next(line for line in text.splitlines() if line.startswith("| 11 |"))
    row_13 = next(line for line in text.splitlines() if line.startswith("| 13 |"))
    cells_11 = [c.strip() for c in row_11.strip("|").split("|")]
    cells_13 = [c.strip() for c in row_13.strip("|").split("|")]
    assert cells_11[3] == "n/a"
    assert cells_13[3] == "runnable"
    assert "not `/console/`" in row_13
