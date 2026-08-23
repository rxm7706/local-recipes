"""Regression pins for scripts/promote_sprint_status.py (Story 15.2 / FR-139)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "promote_sprint_status.py"


def _load():
    spec = importlib.util.spec_from_file_location("_promote_sprint_status", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_regressions_refuses_done_to_backlog():
    mod = _load()
    lost = mod.regressions(
        {"1-1-foo": "done", "1-2-bar": "backlog"},
        {"1-1-foo": "backlog", "1-2-bar": "backlog"},
    )
    assert lost == [("1-1-foo", "done", "backlog")]


def test_regressions_refuses_dropping_a_done_key():
    mod = _load()
    lost = mod.regressions(
        {"1-1-foo": "done"},
        {"1-2-bar": "backlog"},
    )
    assert lost == [("1-1-foo", "done", "<absent>")]


def test_regressions_allows_backlog_to_done():
    mod = _load()
    assert mod.regressions(
        {"1-1-foo": "backlog"},
        {"1-1-foo": "done"},
    ) == []


def test_main_refuses_downgrade_without_allow_regression(tmp_path, monkeypatch, capsys):
    mod = _load()
    projects = tmp_path / "_bmad-output" / "projects" / "pyforge-fixture"
    feed_dir = projects / "implementation-artifacts"
    plan_dir = projects / "planning-artifacts"
    feed_dir.mkdir(parents=True)
    plan_dir.mkdir(parents=True)
    (feed_dir / "sprint-status.yaml").write_text(
        "development_status:\n  1-1-foo: backlog\n", encoding="utf-8"
    )
    (plan_dir / "sprint-status-ledger.yaml").write_text(
        mod.render("fixture", "x", {"1-1-foo": "done"}), encoding="utf-8"
    )
    (projects / "planning-artifacts" / "epics.md").write_text("# e\n", encoding="utf-8")

    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    # Bypass generate.PROJECT_SOURCES discovery — inject a one-key map.
    class _Gen:
        PROJECT_SOURCES = {"fixture": str(
            Path("_bmad-output/projects/pyforge-fixture/implementation-artifacts/sprint-status.yaml")
        )}
        _KEY_SLUG_OVERRIDE = {"fixture": "pyforge-fixture"}

        @staticmethod
        def parse_sprint_status(path):
            return mod._load_generate().parse_sprint_status(path)

    monkeypatch.setattr(mod, "_load_generate", lambda: _Gen())
    # parse_sprint_status still needs the real generate helper
    real = importlib.util.spec_from_file_location(
        "_gen", REPO / "docs" / "dashboard" / "generate.py"
    )
    assert real and real.loader
    gen_mod = importlib.util.module_from_spec(real)
    # Avoid full generate import side effects: use script's own tiny parser via regressions path
    def _parse(path):
        text = Path(path).read_text(encoding="utf-8")
        out = {}
        in_block = False
        for raw in text.splitlines():
            if raw.startswith("development_status:"):
                in_block = True
                continue
            if not in_block:
                continue
            if raw and not raw.startswith((" ", "\t")):
                break
            line = raw.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
        return out

    _Gen.parse_sprint_status = staticmethod(_parse)

    rc = mod.main(["--project", "fixture"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "REFUSED" in out
    assert "1-1-foo" in out
    # Twin unchanged
    twin = plan_dir / "sprint-status-ledger.yaml"
    assert "1-1-foo: done" in twin.read_text(encoding="utf-8")
