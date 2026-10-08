"""Story 67.3 (fnd:CAP-13): tests for scripts/sbom_gap_derive.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
GAPS_DOC = REPO_ROOT / "docs" / "foundry" / "sbom-gaps.md"


def _load():
    spec = importlib.util.spec_from_file_location(
        "sbom_gap_derive", SCRIPTS / "sbom_gap_derive.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sbom_gap_derive"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def test_pixi_task_registered() -> None:
    text = (REPO_ROOT / "pixi.toml").read_text(encoding="utf-8")
    assert "[feature.guild-tasks.tasks.sbom-gaps-check]" in text


def test_live_document_matches_derivation() -> None:
    assert mod.check_gaps_document() == []


def test_derivation_includes_named_residual_features() -> None:
    gaps = mod.derive_gap_features()
    assert "conda-smithy" in gaps
    assert "python-agent-platform" in gaps


def test_check_reds_on_missing_row(tmp_path: Path) -> None:
    doc = tmp_path / "sbom-gaps.md"
    doc.write_text(
        mod.render_gaps_markdown().replace("`feature:conda-smithy`", "`feature:REMOVED`"),
        encoding="utf-8",
    )
    findings = mod.check_gaps_document(doc_path=doc)
    assert any("feature:conda-smithy" in f for f in findings)


def test_check_reds_on_stale_row(tmp_path: Path) -> None:
    base = mod.render_gaps_markdown()
    stale = base + "\n| `pin:__stale__` | pin | won't-do | stale | steward |\n"
    doc = tmp_path / "sbom-gaps.md"
    doc.write_text(stale, encoding="utf-8")
    findings = mod.check_gaps_document(doc_path=doc)
    assert any("__stale__" in f for f in findings)


def test_check_reds_on_new_fat_only_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = mod._load_pixi()
    lr = data["feature"]["local-recipes"]["dependencies"]
    lr = dict(lr)
    lr["brand-new-fat-only-pin-67-3"] = ">=1.0"
    data["feature"]["local-recipes"]["dependencies"] = lr
    monkeypatch.setattr(mod, "_load_pixi", lambda: data)
    findings = mod.check_gaps_document(data=data, doc_path=GAPS_DOC)
    assert any("brand-new-fat-only-pin-67-3" in f for f in findings)


def test_check_reds_when_feature_outside_sbom_added(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = mod._load_pixi()
    data["feature"]["brand-new-feature-gap-67-3"] = {"dependencies": {"python": "3.14.*"}}
    monkeypatch.setattr(mod, "_load_pixi", lambda: data)
    findings = mod.check_gaps_document(data=data, doc_path=GAPS_DOC)
    assert any("brand-new-feature-gap-67-3" in f for f in findings)


def test_parse_gaps_document_roundtrip() -> None:
    sample = mod.render_gaps_markdown()
    rows = mod.parse_gaps_document(sample)
    assert rows["feature:conda-smithy"].disposition == "upstream"
    assert rows["feature:conda-smithy"].owner == "mason"
