"""Story 103.2 — batch mode and JSON report for bmad_suite_metapackage.py (AC1–AC5)."""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

SUITE_RECIPE = """\
schema_version: 1
context:
  name: bmad-suite
  version: "2026.10.1"
package:
  name: ${{ name }}
  version: ${{ version }}
build:
  number: 0
requirements:
  # GENERATED-BEGIN: suite-run-requirements (bmad_suite_metapackage.py — do not edit by hand)
  run:
    - bmad-method >=6.12.2
    - bmad-loop >=0.12.0
    - bmad-module-skill-forge >=3.0.0
  # GENERATED-END: suite-run-requirements
tests:
  - script:
      - echo ok
"""

MANIFEST = """\
members:
  - name: bmad-method
  - name: bmad-loop
  - name: bmad-module-skill-forge
"""


def _member_recipe(version: str, registry: str = "github") -> str:
    return f"""\
schema_version: 1
context:
  name: pkg
  version: "{version}"
extra:
  cfe-upstream-registry: {registry}
  cfe-upstream-name: org/pkg
build:
  number: 0
"""


def _mini_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    suite = root / "recipes" / "bmad-suite"
    suite.mkdir(parents=True)
    (suite / "suite-members.yaml").write_text(MANIFEST, encoding="utf-8")
    (suite / "recipe.yaml").write_text(SUITE_RECIPE, encoding="utf-8")
    for name, ver, reg in (
        ("bmad-method", "6.12.1", "npm"),
        ("bmad-loop", "0.12.0", "github"),
        ("bmad-module-skill-forge", "2.2.0", "npm"),
    ):
        d = root / "recipes" / name
        d.mkdir(parents=True)
        (d / "recipe.yaml").write_text(_member_recipe(ver, reg), encoding="utf-8")
    return root


def _journal(tmp_path: Path, moves: list[dict], *, name: str = "journal.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps({"moves": moves}), encoding="utf-8")
    return path


def _arm_network_raises(mod, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("network forbidden in batch mode")

    monkeypatch.setattr(mod, "_fetch_json", boom)
    monkeypatch.setattr(mod, "_fetch_pypi_latest", boom)
    monkeypatch.setattr(mod, "_fetch_npm_latest", boom)
    monkeypatch.setattr(mod, "_fetch_github_latest", boom)
    if mod.get_latest_github_release is not None:
        monkeypatch.setattr(mod, "get_latest_github_release", boom)


def test_ac1_batch_mode_no_lookup(load_module, tmp_path, monkeypatch):
    mod = load_module("bmad_suite_metapackage.py")
    root = _mini_root(tmp_path)
    journal = _journal(
        tmp_path,
        [{"package": "bmad-method", "from": "6.12.0", "to": "6.12.2"}],
    )
    _arm_network_raises(mod, monkeypatch)
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.generate(root, journal=journal, as_json=True, dry_run=True)
    report = json.loads(buf.getvalue())
    assert all(m["fallback"] is False for m in report["members"])


def test_ac2_floor_rules(load_module, tmp_path, monkeypatch):
    mod = load_module("bmad_suite_metapackage.py")
    root = _mini_root(tmp_path)
    _arm_network_raises(mod, monkeypatch)

    journal_method = _journal(
        tmp_path,
        [
            {"package": "bmad-method", "from": "6.12.0", "to": "6.12.2"},
            {"package": "mybmad-dashboard", "from": "0.1.0", "to": "0.1.0"},
        ],
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.generate(root, journal=journal_method, as_json=True, dry_run=True)
    by_name = {m["name"]: m for m in json.loads(buf.getvalue())["members"]}
    assert by_name["bmad-method"]["floor"] == "6.12.2"
    assert by_name["bmad-method"]["source"] == "batch-move"
    assert by_name["bmad-loop"]["floor"] == "0.12.0"
    assert by_name["bmad-loop"]["source"] == "suite-floor"

    monkeypatch.setattr(mod, "_fetch_github_latest", lambda _p: "0.13.2")
    buf_loop = io.StringIO()
    with redirect_stdout(buf_loop):
        mod.generate(root, journal=journal_method, as_json=True, dry_run=True)
    assert json.loads(buf_loop.getvalue())["members"][1]["floor"] == "0.12.0"

    journal_dup = _journal(
        tmp_path,
        [
            {"package": "bmad-loop", "from": "0.12.0", "to": "0.13.0"},
            {"package": "bmad-loop", "from": "0.12.0", "to": "0.13.2"},
        ],
    )
    buf_dup = io.StringIO()
    with redirect_stdout(buf_dup):
        mod.generate(root, journal=journal_dup, as_json=True, dry_run=True)
    loop_row = next(m for m in json.loads(buf_dup.getvalue())["members"] if m["name"] == "bmad-loop")
    assert loop_row["floor"] == "0.13.2"
    assert loop_row["source"] == "batch-move"

    # suite floor above recipe, not moving
    suite = root / "recipes" / "bmad-suite" / "recipe.yaml"
    text = suite.read_text(encoding="utf-8").replace(">=6.12.2", ">=6.12.2")
    (root / "recipes" / "bmad-method" / "recipe.yaml").write_text(
        _member_recipe("6.12.1", "npm"), encoding="utf-8"
    )
    journal_empty = _journal(tmp_path, [], name="empty.json")
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.generate(root, journal=journal_empty, as_json=True, dry_run=True)
    m = {r["name"]: r for r in json.loads(buf.getvalue())["members"]}
    assert m["bmad-method"]["floor"] == "6.12.2"
    assert m["bmad-method"]["source"] == "suite-floor"

    # recipe above suite floor
    suite.write_text(
        text.replace("bmad-module-skill-forge >=3.0.0", "bmad-module-skill-forge >=2.2.0"),
        encoding="utf-8",
    )
    (root / "recipes" / "bmad-module-skill-forge" / "recipe.yaml").write_text(
        _member_recipe("2.3.0", "npm"), encoding="utf-8"
    )
    buf2 = io.StringIO()
    with redirect_stdout(buf2):
        mod.generate(root, journal=journal_empty, as_json=True, dry_run=True)
    m2 = {r["name"]: r for r in json.loads(buf2.getvalue())["members"]}
    assert m2["bmad-module-skill-forge"]["floor"] == "2.3.0"
    assert m2["bmad-module-skill-forge"]["source"] == "member-recipe"


def test_ac3_json_report_shape_and_dry_run(load_module, tmp_path, monkeypatch):
    mod = load_module("bmad_suite_metapackage.py")
    root = _mini_root(tmp_path)
    journal = _journal(tmp_path, [])
    _arm_network_raises(mod, monkeypatch)
    before_bytes = (root / "recipes" / "bmad-suite" / "recipe.yaml").read_bytes()
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.generate(root, journal=journal, as_json=True, dry_run=True)
    out = buf.getvalue()
    assert "bmad-suite metapackage" not in out
    report = json.loads(out)
    assert report["written"] is False
    assert (root / "recipes" / "bmad-suite" / "recipe.yaml").read_bytes() == before_bytes
    keys = {"name", "registry", "recipe_version", "moved_to", "floor_before", "floor", "source", "fallback"}
    assert len(report["members"]) == 3  # noqa: PLR2004
    for row in report["members"]:
        assert set(row) == keys


def test_ac4_hand_path_fallback_flags(load_module, tmp_path, monkeypatch):
    mod = load_module("bmad_suite_metapackage.py")
    root = _mini_root(tmp_path)

    monkeypatch.setattr(mod, "_fetch_github_latest", lambda _p: None)
    buf = io.StringIO()
    with redirect_stdout(buf):
        mod.generate(root, as_json=True, dry_run=True)
    loop = next(m for m in json.loads(buf.getvalue())["members"] if m["name"] == "bmad-loop")
    assert loop["source"] == "recipe-floor"
    assert loop["fallback"] is True

    (root / "recipes" / "bmad-method" / "recipe.yaml").write_text(
        _member_recipe("6.12.1", "pypi"), encoding="utf-8"
    )
    monkeypatch.setattr(mod, "_fetch_pypi_latest", lambda _p: None)
    monkeypatch.setattr(mod, "_fetch_npm_latest", lambda _p: "9.0.0")
    buf2 = io.StringIO()
    with redirect_stdout(buf2):
        mod.generate(root, as_json=True, dry_run=True)
    method = next(m for m in json.loads(buf2.getvalue())["members"] if m["name"] == "bmad-method")
    assert method["source"] == "npm"
    assert method["fallback"] is True

    monkeypatch.setattr(mod, "_fetch_github_latest", lambda _p: "0.11.0")
    buf3 = io.StringIO()
    with redirect_stdout(buf3):
        mod.generate(root, as_json=True, dry_run=True)
    loop2 = next(m for m in json.loads(buf3.getvalue())["members"] if m["name"] == "bmad-loop")
    assert loop2["source"] == "github+floor"
    assert loop2["fallback"] is False

    buf4 = io.StringIO()
    with redirect_stdout(buf4):
        mod.generate(root, offline=True, as_json=True, dry_run=True)
    off = next(m for m in json.loads(buf4.getvalue())["members"] if m["name"] == "bmad-loop")
    assert off["source"] == "offline"
    assert off["fallback"] is False


def test_ac8_mutation_batch_must_not_call_fetcher(load_module, tmp_path, monkeypatch):
    mod = load_module("bmad_suite_metapackage.py")
    root = _mini_root(tmp_path)
    journal = _journal(tmp_path, [{"package": "bmad-method", "from": "1", "to": "2"}])
    called = {"n": 0}
    real = mod._fetch_github_latest

    def wrapped(*a, **k):
        called["n"] += 1
        return real(*a, **k)

    monkeypatch.setattr(mod, "_fetch_github_latest", wrapped)
    mod.generate(root, journal=journal, as_json=True, dry_run=True)
    assert called["n"] == 0
