"""Story 67.2 (fnd:CAP-13): tests for scripts/sbom_laptop_gate.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytest.importorskip("yaml")
import yaml  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"


def _load():
    spec = importlib.util.spec_from_file_location(
        "sbom_laptop_gate", SCRIPTS / "sbom_laptop_gate.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sbom_laptop_gate"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


mod = _load()


def test_pixi_task_registered() -> None:
    text = (REPO_ROOT / "pixi.toml").read_text(encoding="utf-8")
    assert "[feature.guild-tasks.tasks.sbom-laptop-gate]" in text


def test_channel_audit_passes_on_live_lock() -> None:
    lockfile = yaml.safe_load((REPO_ROOT / "pixi.lock").read_text(encoding="utf-8"))
    findings = mod.channel_audit_findings(lockfile, platforms=["linux-64"])
    assert findings == []


def test_channel_audit_flags_off_channel_conda() -> None:
    lockfile = {
        "environments": {
            mod.SBOM_ENV: {
                "channels": [{"url": "https://conda.anaconda.org/conda-forge/"}],
                "packages": {
                    "linux-64": [
                        {
                            "conda": "https://evil.example.com/noarch/bad-1.0-h0_0.conda"
                        }
                    ]
                },
            }
        }
    }
    findings = mod.channel_audit_findings(lockfile, platforms=["linux-64"])
    assert len(findings) == 1 and "evil.example.com" in findings[0]


def test_channel_audit_flags_unlisted_pypi_wheel() -> None:
    lockfile = {
        "environments": {
            mod.SBOM_ENV: {
                "channels": [{"url": "https://conda.anaconda.org/conda-forge/"}],
                "packages": {
                    "linux-64": [
                        {
                            "pypi": "https://files.pythonhosted.org/packages/a/a/a/not_allowed-1.0-py3-none-any.whl"
                        }
                    ]
                },
            }
        }
    }
    findings = mod.channel_audit_findings(lockfile, platforms=["linux-64"])
    assert any("not_allowed" in f for f in findings)


def test_planted_missing_dependency_exits_nonzero_and_names_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PIXI_ENVIRONMENT_NAME", mod.SBOM_ENV)
    rc = mod.main(
        ["--lockfile", str(REPO_ROOT / "pixi.lock"), "--exclude-package", "httpx"]
    )
    assert rc == 1
    gaps = mod.import_gap_findings(exclude_packages=frozenset({"httpx"}))
    assert any("SBOM gap: httpx" in g for g in gaps)


def test_refuses_local_recipes_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIXI_ENVIRONMENT_NAME", mod.FORBIDDEN_ENV)
    rc = mod.main(["--lockfile", str(REPO_ROOT / "pixi.lock")])
    assert rc == 1
    assert "refuses" in mod.assert_sbom_environment() or ""


def test_live_import_probes_pass_in_current_env() -> None:
    """Matrix row: complete SBOM — probes succeed when packages are present."""
    pytest.importorskip("httpx")
    pytest.importorskip("pydantic")
    pytest.importorskip("jsonschema")
    gaps = mod.import_gap_findings()
    assert gaps == []
