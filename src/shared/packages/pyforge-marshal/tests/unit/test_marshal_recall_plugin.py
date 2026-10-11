"""Story 93.1: marshal-recall bmad-loop plugin hook tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from bmad_loop.plugins.context import HookContext
from bmad_loop.plugins.model import PluginManifest

from pyforge.marshal.adapters.scribe_cli import ScribeRecallOutcome

_PLUGIN_PY = (
    Path(__file__).resolve().parents[2]
    / "src/pyforge/marshal/data/bmad_loop_plugins/marshal-recall/marshal_recall_plugin.py"
)


def _load_plugin_class():
    spec = importlib.util.spec_from_file_location("marshal_recall_plugin_under_test", _PLUGIN_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MarshalRecallPlugin


class _CountingScribe:
    def __init__(self) -> None:
        self.calls = 0

    def recall(self, **_kwargs):
        self.calls += 1
        return ScribeRecallOutcome(ok=True, grounded=True, text="hook body", citation="mem/x.md")


@pytest.fixture
def loop_home(tmp_path: Path) -> Path:
    home = tmp_path / "loop-home"
    home.mkdir()
    (home / "_bmad" / "custom").mkdir(parents=True)
    (home / "_bmad" / "custom" / ".active-project").write_text("pyforge-marshal", encoding="utf-8")
    bmad = home / ".bmad-loop"
    bmad.mkdir()
    (bmad / "policy.toml").write_text(
        '[context.recall]\nenabled = true\naggressiveness = "medium"\n',
        encoding="utf-8",
    )
    return home


def test_on_pre_session_appends_block_for_dev_then_review_reads_cache(
    loop_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scribe = _CountingScribe()
    monkeypatch.setattr("pyforge.marshal.adapters.harness_bmadloop.ScribeCli", lambda: scribe)
    plugin_cls = _load_plugin_class()
    plugin = plugin_cls(PluginManifest(name="marshal-recall"), {})
    ctx = HookContext(
        "pre_session",
        run_id="run-1",
        story_key="93-1-story",
        role="dev",
        worktree=str(loop_home),
        repo_root=str(loop_home),
        proposed_prompt="Base prompt.",
    )
    plugin.on_pre_session(ctx)
    assert scribe.calls == 1
    assert "hook body" in (ctx.proposed_prompt or "")
    ctx2 = HookContext(
        "pre_session",
        run_id="run-1",
        story_key="93-1-story",
        role="review",
        worktree=str(loop_home),
        repo_root=str(loop_home),
        proposed_prompt="Review prompt.",
    )
    plugin.on_pre_session(ctx2)
    assert scribe.calls == 1
    assert "hook body" in (ctx2.proposed_prompt or "")

    ctx3 = HookContext(
        "pre_session",
        run_id="run-1",
        story_key="93-1-story",
        role="dev",
        worktree=str(loop_home),
        repo_root=str(loop_home),
        proposed_prompt="Second dev attempt.",
    )
    plugin.on_pre_session(ctx3)
    assert scribe.calls == 1
    assert "hook body" in (ctx3.proposed_prompt or "")
