"""Story 28.9 (SPEC-marshal-token-economy CAP-6/CAP-13) -- ``marshal context
retrieve`` and the scribe recall seam."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.adapters import scribe_cli
from pyforge.marshal.adapters.scribe_cli import ScribeCli, ScribeRecallOutcome
from pyforge.marshal.cli import context as context_cli
from pyforge.marshal.core import derived_context as derived
from pyforge.marshal.core import planning_graph as planning
from pyforge.marshal.core.verdict import EXIT_OK

_SLUG = "pyforge-marshal"


class _FakeProcess:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[tuple[str, ...], Path, float | None]] = []

    def run(self, argv, *, cwd, timeout_s=None):
        self.calls.append((tuple(argv), Path(cwd), timeout_s))
        if self.error is not None:
            raise self.error
        return self.result


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(scribe_cli.shutil, "which", lambda _name: "/usr/bin/scribe")
    planning_dir = tmp_path / derived.planning_artifacts_relpath(_SLUG)
    _write(planning_dir / "epics.md", "# Epics\n")
    _write(planning_dir / "PRD.md", "# PRD\n")
    return tmp_path


def _declare_layer(repo: Path, *, enabled: bool) -> None:
    policy_path = repo / (f"_bmad-output/projects/{_SLUG}/planning-artifacts/marshal-policy.toml")
    _write(
        policy_path,
        f"[context.planning-graph]\nenabled = {str(enabled).lower()}\n",
    )


class TestScribeRecallAdapter:
    def test_grounded_recall_parses(self, tmp_path):
        process = _FakeProcess(
            ProcessResult(
                returncode=0,
                stdout="Scoped epic context.\n[source: epics.md:L10]\n",
                stderr="",
            )
        )
        outcome = ScribeCli(process).recall(
            repo_root=tmp_path,
            query="Epic 28 planning",
            binary_path="/usr/bin/scribe",
        )
        assert outcome == ScribeRecallOutcome(
            ok=True,
            grounded=True,
            text="Scoped epic context.",
            citation="epics.md:L10",
            argv=(
                "/usr/bin/scribe",
                "recall",
                "Epic 28 planning",
                "--mode",
                "planning",
            ),
        )

    def test_miss_is_ok_but_not_grounded(self, tmp_path):
        process = _FakeProcess(
            ProcessResult(
                returncode=0,
                stdout="no grounded answer found\n",
                stderr="",
            )
        )
        outcome = ScribeCli(process).recall(
            repo_root=tmp_path,
            query="Epic 28 planning",
            binary_path="/usr/bin/scribe",
        )
        assert outcome.ok is True
        assert outcome.grounded is False

    def test_missing_binary_degrades(self, tmp_path, monkeypatch):
        monkeypatch.setattr(scribe_cli.shutil, "which", lambda _name: None)
        outcome = ScribeCli().recall(repo_root=tmp_path, query="q")
        assert outcome.ok is False
        assert "planning-graph" in (outcome.reason or "")

    def test_non_zero_exit_degrades(self, tmp_path):
        process = _FakeProcess(ProcessResult(returncode=2, stdout="", stderr="graph not compiled\n"))
        outcome = ScribeCli(process).recall(
            repo_root=tmp_path,
            query="q",
            binary_path="/usr/bin/scribe",
        )
        assert outcome.ok is False

    def test_launch_failure_degrades(self, tmp_path):
        process = _FakeProcess(error=ProcessError("timeout"))
        outcome = ScribeCli(process).recall(
            repo_root=tmp_path,
            query="q",
            binary_path="/usr/bin/scribe",
        )
        assert outcome.ok is False


class TestContextRetrieveCli:
    def test_layer_off_reports_fallback_without_calling_scribe(self, repo: Path):
        _declare_layer(repo, enabled=False)
        process = _FakeProcess(ProcessResult(returncode=0, stdout="should not run\n", stderr=""))
        exit_code = context_cli.run_context_retrieve(
            _args(repo, epic="28", story="9"),
            scribe=ScribeCli(process),
        )
        assert exit_code == EXIT_OK
        assert process.calls == []

    def test_graph_mode_when_recall_grounds(self, repo: Path, capsys):
        _declare_layer(repo, enabled=True)
        process = _FakeProcess(
            ProcessResult(
                returncode=0,
                stdout="Bounded planning slice.\n[source: epics.md:L5]\n",
                stderr="",
            )
        )
        exit_code = context_cli.run_context_retrieve(
            _args(repo, epic="28", story="9", json=True),
            scribe=ScribeCli(process),
        )
        assert exit_code == EXIT_OK
        payload = json.loads(capsys.readouterr().out)
        assert payload["data"]["mode"] == planning.MODE_GRAPH
        assert payload["data"]["grounded"] is True
        assert payload["data"]["text"] == "Bounded planning slice."
        assert payload["data"]["tokens_saved"] == 109_500

    def test_stale_only_miss_falls_back_with_warn(self, repo: Path, capsys):
        _declare_layer(repo, enabled=True)
        process = _FakeProcess(
            ProcessResult(
                returncode=0,
                stdout="no grounded answer found\n",
                stderr="",
            )
        )
        exit_code = context_cli.run_context_retrieve(
            _args(repo, epic="28", story="9", json=True),
            scribe=ScribeCli(process),
        )
        assert exit_code == EXIT_OK
        payload = json.loads(capsys.readouterr().out)
        assert payload["data"]["mode"] == planning.MODE_EPIC_CONTEXT_FALLBACK
        assert any(f["code"] == "MRS-PLAN-001" for f in payload["findings"])

    def test_grammar_failure_falls_back(self, repo: Path, capsys):
        _declare_layer(repo, enabled=True)
        process = _FakeProcess(ProcessResult(returncode=2, stdout="", stderr="no graph\n"))
        context_cli.run_context_retrieve(
            _args(repo, epic="28", json=True),
            scribe=ScribeCli(process),
        )
        payload = json.loads(capsys.readouterr().out)
        assert payload["data"]["mode"] == planning.MODE_EPIC_CONTEXT_FALLBACK
        assert payload["data"]["fallback"].endswith("/epic-28-context.md")


def _args(repo: Path, *, epic: str, story: str | None = None, json: bool = False):
    import argparse

    return argparse.Namespace(
        root=str(repo),
        project=_SLUG,
        epic=epic,
        story=story,
        format="json" if json else "text",
    )
