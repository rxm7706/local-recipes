"""Tests for scripts/pin_policy_check.py (Story 100.1 / CAP-167)."""
from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pin_policy"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pin_policy_check as check_mod  # noqa: E402
import pin_policy_lib as lib  # noqa: E402


def _load_check_source() -> str:
    return (SCRIPTS / "pin_policy_check.py").read_text(encoding="utf-8")


def test_no_hardcoded_exclude_list_in_checker() -> None:
    src = _load_check_source()
    assert "conda-libmamba-solver" not in src
    assert "--exclude conda-build" not in src


def test_diff_fixture_yields_nine_findings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base_text = (FIXTURES / "pixi.toml.base").read_text(encoding="utf-8")
    after_text = (FIXTURES / "pixi.toml.after").read_text(encoding="utf-8")
    policy = lib.load_policy(FIXTURES / "pin-policy.yaml")

    (tmp_path / "pixi.toml").write_text(after_text, encoding="utf-8")
    current = tomllib.loads(after_text)

    def fake_read(ref: str, root: Path = REPO_ROOT) -> tuple[dict | None, str | None]:
        assert ref == "base"
        return tomllib.loads(base_text), None

    monkeypatch.setattr(lib, "_read_manifest_at_ref", fake_read)
    findings, err = lib.check_diff(policy, "base", current, root=tmp_path)
    assert err is None
    kinds = sorted(f.kind for f in findings)
    assert kinds.count("lost-cap") == 5
    assert kinds.count("flattened-table") == 2
    assert kinds.count("lowered-floor") == 2
    assert len(findings) == 9


def test_diff_floor_only_rise_yields_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = {"version": 1, "defaults": {"pinning_strategy": "latest-up", "floors_never_lower": True}, "pointer": "", "holds": []}
    base = """
[feature.demo.dependencies]
boto3 = ">=1.43.75"
"""
    after = """
[feature.demo.dependencies]
boto3 = ">=1.43.106"
"""

    def fake_read(ref: str, root: Path = REPO_ROOT) -> tuple[dict | None, str | None]:
        return tomllib.loads(base), None

    monkeypatch.setattr(lib, "_read_manifest_at_ref", fake_read)
    findings, _ = lib.check_diff(policy, "base", tomllib.loads(after))
    assert findings == []


def test_diff_moved_hold_postgresql(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = lib.load_policy(FIXTURES / "pin-policy.yaml")
    base = (FIXTURES / "pixi.toml.base").read_text(encoding="utf-8")
    after = (FIXTURES / "pixi.toml.after").read_text(encoding="utf-8")

    def fake_read(ref: str, root: Path = REPO_ROOT) -> tuple[dict | None, str | None]:
        return tomllib.loads(base), None

    monkeypatch.setattr(lib, "_read_manifest_at_ref", fake_read)
    findings, _ = lib.check_diff(policy, "base", tomllib.loads(after))
    assert any(f.kind == "moved-hold" and f.package == "postgresql" for f in findings)


def test_check_undeclared_cap(tmp_path: Path) -> None:
    policy = {"version": 1, "defaults": {"pinning_strategy": "latest-up", "floors_never_lower": True}, "pointer": "x", "holds": []}
    manifest_text = """
# x
[feature.demo.dependencies]
pyjwt = ">=1.0,<3"
"""
    manifest = tomllib.loads(manifest_text)
    findings = lib.check_static(policy, manifest, manifest_text)
    assert any(f.kind == "undeclared-hold" and f.package == "pyjwt" for f in findings)


def test_check_dangling_hold(tmp_path: Path) -> None:
    policy = {
        "version": 1,
        "defaults": {"pinning_strategy": "latest-up", "floors_never_lower": True},
        "pointer": "x",
        "holds": [
            {
                "package": "ghost-pkg",
                "hold": "cap",
                "cap": "<2",
                "features": ["demo"],
                "reason": "r",
                "authority": "a",
                "owner": "o",
                "until": "u",
            }
        ],
    }
    manifest_text = "# x\n[feature.other.dependencies]\nfoo = \"*\"\n"
    findings = lib.check_static(policy, tomllib.loads(manifest_text), manifest_text)
    assert any(f.kind == "dangling-hold" for f in findings)


def test_until_unknown_is_warning_only() -> None:
    policy = {
        "version": 1,
        "defaults": {"pinning_strategy": "latest-up", "floors_never_lower": True},
        "pointer": "ok pointer",
        "holds": [
            {
                "package": "pyjwt",
                "hold": "cap",
                "cap": "<3",
                "features": ["demo"],
                "reason": "r",
                "authority": "a",
                "owner": "o",
                "until": "unknown",
            }
        ],
    }
    manifest_text = "# ok pointer\n[feature.demo.dependencies]\npyjwt = \">=1,<3\"\n"
    findings = lib.check_static(policy, tomllib.loads(manifest_text), manifest_text)
    assert all(f.severity == "warning" for f in findings if f.kind == "until-unknown")
    assert lib.exit_code_from_findings(findings) == 0


def test_fan_out_fixture_excludes_locked_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    station = tmp_path / "src/shared/packages/pyforge-marshal"
    station.mkdir(parents=True)
    (station / "pyproject.toml").write_text(
        '[project]\nname="pyforge-marshal"\ndependencies = ["bmad-loop>=0.11.0,<0.13"]\n',
        encoding="utf-8",
    )
    lock = {
        "environments": {
            "pyforge-marshal": {
                "packages": {
                    "linux-64": [
                        {"conda": "https://conda.anaconda.org/conda-forge/noarch/bmad-loop-0.13.0-pyh1_0.conda"}
                    ]
                }
            }
        }
    }
    lock_path = tmp_path / "pixi.lock"
    import yaml

    lock_path.write_text(yaml.dump(lock), encoding="utf-8")
    monkeypatch.setattr(lib, "LOCK_PATH", lock_path)
    findings = lib.check_fan_out(tmp_path, lock_path=lock_path)
    assert any(f.kind == "station-range-excludes" and f.package == "bmad-loop" for f in findings)


def test_render_command_main() -> None:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(sys, "argv", ["pin-policy-check", "--render-command"])
    # uses real policy on tree
    rc = check_mod.main()
    assert rc == 0


def test_stale_pointer_finding() -> None:
    policy = lib.load_policy(REPO_ROOT / "docs/governance/pin-policy.yaml")
    bad_text = "# wrong pointer\n[feature.python.dependencies]\npixi = \">=0.80.0\"\n"
    findings = lib.check_static(policy, tomllib.loads(bad_text), bad_text)
    assert any(f.kind == "stale-pointer" for f in findings)
