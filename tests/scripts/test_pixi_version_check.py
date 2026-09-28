"""Tests for scripts/pixi_version_check.py's pixi-upper-bound pass and the
pyforge-mason registry site (mason Story 20.1, spec-pyforge-mason CAP-30).

Operator ruling 2026-09-28: "we should loosen pyforge-mason to be >=0.80.0
with no cap -- we don't need to cap pixi in any station / environment". The
check must fail when any pixi dependency spec in the root pixi.toml (every
feature) or a src/shared/packages/*/pixi.toml / pyproject.toml carries an
upper bound; these tests plant each kind in a scratch tree and read the exit
code. Stdlib + pytest only: this file runs in the dependency-free `pyforge-ci`
environment (`pyforge-doctor-scripts-test`).
"""

from __future__ import annotations

import dataclasses
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import pixi_version_check as m  # noqa: E402  (sys.path must be set up first)
import pixi_version_registry as registry  # noqa: E402

MASON_SITE = "pyforge-mason [package.run-dependencies] pixi floor"


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _clean_tree(root: Path) -> Path:
    _write(root, "pixi.toml", """
[workspace]
requires-pixi = ">=0.80.0"

[feature.python.dependencies]
pixi = ">=0.80.0"
pixi-build-python = "0.*"          # a different package: never matched as pixi

[feature.guild.target.linux-64.dependencies]
pixi = { version = ">=0.80.0,!=0.80.1", channel = "conda-forge" }

[dependencies]
pixi = "*"
""")
    _write(root, "src/shared/packages/pyforge-demo/pixi.toml", """
[package]
name = "pyforge-demo"

[package.run-dependencies]
pixi = ">=0.80.0"
pixi-build-rattler-build = "==0.4.6"
""")
    _write(root, "src/shared/packages/pyforge-demo/pyproject.toml", """
[project]
name = "pyforge-demo"
dependencies = ["pixi>=0.80", "pixie==1.0"]

[project.optional-dependencies]
tools = ["pixi >0.79 ; python_version >= '3.12'"]
""")
    return root


def _run_main(monkeypatch: pytest.MonkeyPatch, root: Path) -> int:
    monkeypatch.setattr(m, "CAP_SCAN_ROOT", root)
    monkeypatch.setattr(sys, "argv", ["pixi-version-check"])
    return m.main()


def test_live_repo_is_clean():
    findings, stats = m.run()
    assert findings == [], findings
    assert stats["manifests_scanned"] > 1


def test_mason_run_dep_is_a_registered_floor_site():
    site = next(s for s in registry.SITES if s.name == MASON_SITE)
    assert site.kind == "floor" and not site.derived
    versions, existed = registry.read_versions(site)
    assert existed and versions == [registry.master_version()]


@pytest.mark.parametrize("spec", [">=0.80.0", ">0.79", ">=0.80.0,!=0.80.1", "!=0.80.1", "*", "", ">= 0.80.0",
                                  {"version": ">=0.80.0"}, {"channel": "conda-forge"}])
def test_uncapped_specs_have_no_capping_clause(spec):
    assert m.capping_clauses(spec) == []


@pytest.mark.parametrize("spec", [">=0.80.0,<0.81", "<0.81", "<=0.81", "==0.80.0", "0.80.0", "0.80.*", "==0.80.*",
                                  "~=0.80", "=0.80", "===0.80.0", "^0.80", ">=0.80|<0.81", "@ https://example/pixi.whl",
                                  {"version": ">=0.80.0,<0.81"}, {"git": "https://example/pixi.git"}])
def test_capped_specs_are_caught(spec):
    assert m.capping_clauses(spec) != []


def test_a_clean_tree_passes(monkeypatch, tmp_path, capsys):
    assert _run_main(monkeypatch, _clean_tree(tmp_path)) == 0
    assert "no pixi spec is capped" in capsys.readouterr().out


def test_planted_caps_fail_the_check(monkeypatch, tmp_path, capsys):
    root = _clean_tree(tmp_path)
    _write(root, "pixi.toml", """
[workspace]
requires-pixi = ">=0.80.0"

[feature.python.dependencies]
pixi = ">=0.80.0,<0.81"

[feature.guild.target.linux-64.dependencies]
pixi = { version = "0.80.*" }
""")
    _write(root, "src/shared/packages/pyforge-demo/pixi.toml", """
[package.run-dependencies]
pixi = "==0.80.0"
""")
    _write(root, "src/shared/packages/pyforge-demo/pyproject.toml", """
[project]
dependencies = ["pixi>=0.80,<0.81; python_version >= '3.12'"]

[project.optional-dependencies]
tools = ["pixi~=0.80"]

[dependency-groups]
dev = ["pixi (<=0.81)"]
""")
    assert _run_main(monkeypatch, root) == 1
    out = capsys.readouterr().out
    assert out.count("pixi-upper-bound") == 6
    findings, _ = m.run()
    sites = sorted(f["site"] for f in findings if f["kind"] == "pixi-upper-bound")
    assert sites == [
        "pixi.toml [feature.guild.target.linux-64.dependencies.pixi]",
        "pixi.toml [feature.python.dependencies.pixi]",
        "src/shared/packages/pyforge-demo/pixi.toml [package.run-dependencies.pixi]",
        "src/shared/packages/pyforge-demo/pyproject.toml [dependency-groups.dev]",
        "src/shared/packages/pyforge-demo/pyproject.toml [project.dependencies]",
        "src/shared/packages/pyforge-demo/pyproject.toml [project.optional-dependencies.tools]",
    ]


def test_a_capped_requires_pixi_fails(monkeypatch, tmp_path):
    root = _clean_tree(tmp_path)
    _write(root, "pixi.toml", '[workspace]\nrequires-pixi = ">=0.80.0,<0.81"\n')
    assert _run_main(monkeypatch, root) == 1


def test_an_unreadable_manifest_is_a_finding(monkeypatch, tmp_path):
    root = _clean_tree(tmp_path)
    _write(root, "src/shared/packages/pyforge-demo/pixi.toml", "[package\npixi = \n")
    assert _run_main(monkeypatch, root) == 1
    findings, _ = m.run()
    assert [f["kind"] for f in findings] == ["manifest-unreadable"]


def test_a_recapped_mason_pin_also_trips_its_registry_site(monkeypatch, tmp_path):
    site = next(s for s in registry.SITES if s.name == MASON_SITE)
    text, n = re.subn(r'^pixi = ">=([0-9.]+)"', r'pixi = ">=\1,<9"', site.path.read_text(encoding="utf-8"),
                      count=1, flags=re.MULTILINE)
    assert n == 1
    recapped = _write(tmp_path, "mason-pixi.toml", text)
    monkeypatch.setattr(m, "SITES", (dataclasses.replace(site, path=recapped),))
    monkeypatch.setattr(m, "CAP_SCAN_ROOT", _clean_tree(tmp_path / "tree"))
    findings, _ = m.run()
    assert [(f["kind"], f["site"]) for f in findings] == [("hit-count-drift", MASON_SITE)]
