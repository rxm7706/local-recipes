"""Tests for scripts/platform_ci_test_requirements_check.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "platform_ci_test_requirements_check.py"


def _import_module():
    spec = importlib.util.spec_from_file_location(
        "platform_ci_test_requirements_check", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["platform_ci_test_requirements_check"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _import_module()


def test_live_repo_is_clean():
    findings, stats = mod.run()
    assert stats["requirements_pins"] == stats["pixi_pins"]
    assert findings == []


def test_parse_requirements_merges_includes_and_overrides(tmp_path):
    base = tmp_path / "base.txt"
    prod = tmp_path / "production.txt"
    local = tmp_path / "local.txt"
    base.write_text("django==5.1.11\n")
    prod.write_text("-r base.txt\npsycopg[c]==3.2.9\n")
    local.write_text("-r production.txt\npsycopg[binary]==3.2.9\n")

    pins = mod._parse_requirements_file(local)
    assert set(pins) == {"django", "psycopg"}
    assert pins["psycopg"].extras == ("binary",)
    assert pins["django"].version == "5.1.11"


def test_detects_version_mismatch(tmp_path, monkeypatch):
    req_dir = tmp_path / "requirements"
    req_dir.mkdir()
    (req_dir / "base.txt").write_text("django==5.1.11\n")
    (req_dir / "production.txt").write_text("-r base.txt\n")
    (req_dir / "local.txt").write_text("-r production.txt\n")

    pixi = tmp_path / "pixi.toml"
    pixi.write_text(
        """
[feature.platform-ci-test.pypi-dependencies]
django = "==5.1.12"
"""
    )

    monkeypatch.setattr(mod, "LOCAL_FILE", req_dir / "local.txt")
    monkeypatch.setattr(mod, "MANIFEST", pixi)

    findings, _ = mod.run()
    assert any(f["kind"] == "version-mismatch" and f["package"] == "django" for f in findings)


def test_detects_missing_in_pixi(tmp_path, monkeypatch):
    req_dir = tmp_path / "requirements"
    req_dir.mkdir()
    (req_dir / "base.txt").write_text("django==5.1.11\n")
    (req_dir / "production.txt").write_text("-r base.txt\n")
    (req_dir / "local.txt").write_text("-r production.txt\n")

    pixi = tmp_path / "pixi.toml"
    pixi.write_text("[feature.platform-ci-test.pypi-dependencies]\n")

    monkeypatch.setattr(mod, "LOCAL_FILE", req_dir / "local.txt")
    monkeypatch.setattr(mod, "MANIFEST", pixi)

    findings, _ = mod.run()
    assert findings == [
        {
            "kind": "missing-in-pixi",
            "package": "django",
            "detail": "requirements pin django==5.1.11 has no "
            "[feature.platform-ci-test.pypi-dependencies] entry",
        }
    ]


def test_include_cycle_raises(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("-r b.txt\n")
    b.write_text("-r a.txt\n")
    with pytest.raises(RuntimeError, match="cycle"):
        mod._parse_requirements_file(a)


def test_fix_rewrites_drifted_pypi_block(tmp_path, monkeypatch):
    req_dir = tmp_path / "requirements"
    req_dir.mkdir()
    (req_dir / "base.txt").write_text("django==5.1.11\n")
    (req_dir / "production.txt").write_text("-r base.txt\n")
    (req_dir / "local.txt").write_text("-r production.txt\n")

    pixi = tmp_path / "pixi.toml"
    pixi.write_text(
        "[feature.platform-ci-test.pypi-dependencies]\n"
        'django = "==5.1.12"\n\n'
        "[feature.other.pypi-dependencies]\n"
        'leftover = "==1.0.0"\n'
    )

    monkeypatch.setattr(mod, "REQUIREMENTS_ROOT", req_dir)
    monkeypatch.setattr(mod, "LOCAL_FILE", req_dir / "local.txt")
    monkeypatch.setattr(mod, "BASE_FILE", req_dir / "base.txt")
    monkeypatch.setattr(mod, "PRODUCTION_FILE", req_dir / "production.txt")
    monkeypatch.setattr(mod, "MANIFEST", pixi)

    assert mod.fix_manifest() is True
    findings, _ = mod.run()
    assert findings == []
    assert 'django = "==5.1.11"' in pixi.read_text()
    assert "[feature.other.pypi-dependencies]" in pixi.read_text()
