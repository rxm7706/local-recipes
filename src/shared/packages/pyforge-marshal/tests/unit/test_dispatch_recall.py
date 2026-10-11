"""Story 93.1: factory dispatch recall wiring (AC1, AC3, AC5)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
from test_dispatch import FakeBuildHarness, FakeFs, FakeProcess, FakeVcs, _init_git_repo

from pyforge.marshal.adapters.scribe_cli import ScribeRecallOutcome
from pyforge.marshal.cli import dispatch as dispatch_module
from pyforge.marshal.cli.dispatch import run_dispatch
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import policy
from pyforge.marshal.core.recall_feedback import RECALL_FEEDBACK_HEADER
from pyforge.marshal.core.verdict import EXIT_OK

_STORY = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
_BINDING = (
    "\n\n## Verification\n\n- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass\n"
)


class _FakeScribeCli:
    def __init__(self, outcome: ScribeRecallOutcome) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, object]] = []

    def recall(self, *, repo_root: Path, query: str, scope: str | None = None, mode: str = "planning", **_kw):
        self.calls.append({"repo_root": repo_root, "query": query, "scope": scope, "mode": mode})
        return self.outcome


def _compose_with_recall(monkeypatch: pytest.MonkeyPatch, slug: str, *, enabled: bool) -> None:
    project = {"context": {"recall": {"enabled": enabled, "aggressiveness": "medium"}}}
    effective, _ = policy.compose(project_slug=slug, project=project, flags={})
    monkeypatch.setattr(dispatch_module, "_compose_policy", lambda _slug, flags=None: effective)


def _setup_story(tmp_path: Path, slug: str) -> None:
    _init_git_repo(tmp_path, scope_slug=slug)
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{_STORY}.md").write_text(
        f"---\ndifficulty: medium\n---\n# spec\n{_BINDING}",
        encoding="utf-8",
    )


def test_dispatch_appends_grounded_recall_and_journals_disposition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    slug = "pyforge-marshal"
    _setup_story(tmp_path, slug)
    _compose_with_recall(monkeypatch, slug, enabled=True)
    scribe = _FakeScribeCli(
        ScribeRecallOutcome(
            ok=True,
            grounded=True,
            text="always reconcile memlog",
            citation=".claude/memory/feedback/example.md",
        )
    )
    monkeypatch.setattr("pyforge.marshal.adapters.harness_bmadloop.ScribeCli", lambda: scribe)
    harness = FakeBuildHarness()
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        argparse.Namespace(slug=slug, story=_STORY, format="json"),
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=harness,
        process=FakeProcess(),
    )
    assert code == EXIT_OK
    assert len(scribe.calls) == 1
    assert scribe.calls[0]["mode"] == "memory"
    assert scribe.calls[0]["scope"] is None
    prompt = harness.calls[0].get("recall_block") or ""
    assert RECALL_FEEDBACK_HEADER in str(prompt)
    assert "Source: .claude/memory/feedback/example.md" in str(prompt)
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["recall"]["attempted"] is True
    assert payload["data"]["recall"]["outcome"] == "grounded"


def test_dispatch_recall_failure_warns_and_still_launches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    slug = "pyforge-marshal"
    _setup_story(tmp_path, slug)
    _compose_with_recall(monkeypatch, slug, enabled=True)
    monkeypatch.setattr(
        "pyforge.marshal.adapters.harness_bmadloop.ScribeCli",
        lambda: _FakeScribeCli(ScribeRecallOutcome(ok=False, reason="timeout")),
    )
    harness = FakeBuildHarness()
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        argparse.Namespace(slug=slug, story=_STORY, format="json"),
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=harness,
        process=FakeProcess(),
    )
    assert code == EXIT_OK
    assert harness.calls[0].get("recall_block") in (None, "")
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["recall"]["outcome"] == "failed"
    assert any(f["code"] == "MRS-DISP-064" for f in payload["findings"])
