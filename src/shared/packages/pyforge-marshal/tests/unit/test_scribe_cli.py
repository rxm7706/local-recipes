"""Story 28.8 (SPEC-marshal-token-economy CAP-5) -- the scribe-CLI seam.

The layer's whole degradation contract lives here: EVERY way the grammar
can fail to answer must produce ``ok=False`` with a reason, never an
exception -- the spec's "an unavailable instrument disables its layer with
a named finding, never blocks a run".
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.adapters import scribe_cli
from pyforge.marshal.adapters.scribe_cli import ScribeCli, ScribeRefreshOutcome


class _FakeProcess:
    """A ``ProcessPort`` double: records the argv it was handed and returns
    a canned result (or raises a canned error)."""

    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[tuple[str, ...], Path, float | None]] = []

    def run(self, argv, *, cwd, timeout_s=None):
        self.calls.append((tuple(argv), Path(cwd), timeout_s))
        if self.error is not None:
            raise self.error
        return self.result


def _ok(stdout: str) -> ProcessResult:
    return ProcessResult(returncode=0, stdout=stdout, stderr="")


class TestBinaryResolution:
    def test_path_wins(self, monkeypatch, tmp_path):
        monkeypatch.setattr(scribe_cli.shutil, "which", lambda _name: "/usr/bin/scribe")
        assert ScribeCli().resolve_binary(tmp_path) == "/usr/bin/scribe"

    def test_falls_back_to_a_repo_pixi_env_bin_dir(self, monkeypatch, tmp_path):
        monkeypatch.setattr(scribe_cli.shutil, "which", lambda _name: None)
        bin_dir = tmp_path / ".pixi/envs/pyforge-scribe/bin"
        bin_dir.mkdir(parents=True)
        binary = bin_dir / "scribe"
        binary.write_text("#!/bin/sh\n")
        binary.chmod(0o755)
        assert ScribeCli().resolve_binary(tmp_path) == str(binary)

    def test_a_non_executable_candidate_does_not_resolve(self, monkeypatch, tmp_path):
        monkeypatch.setattr(scribe_cli.shutil, "which", lambda _name: None)
        bin_dir = tmp_path / ".pixi/envs/pyforge-scribe/bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "scribe").write_text("not executable\n")
        (bin_dir / "scribe").chmod(0o644)
        assert ScribeCli().resolve_binary(tmp_path) is None

    def test_no_repo_root_means_path_only(self, monkeypatch):
        monkeypatch.setattr(scribe_cli.shutil, "which", lambda _name: None)
        assert ScribeCli().resolve_binary(None) is None


class TestRefreshSuccess:
    def test_reports_the_grammars_own_two_name_lists(self, tmp_path):
        process = _FakeProcess(_ok("refreshed: a; skipped (unchanged): b -> /x/index.json\n"))
        outcome = ScribeCli(process).refresh(
            repo_root=tmp_path,
            manifest_path=tmp_path / "m.json",
            binary_path="/usr/bin/scribe",
        )
        assert outcome == ScribeRefreshOutcome(
            ok=True,
            refreshed=("a",),
            skipped=("b",),
            argv=(
                "/usr/bin/scribe",
                "index",
                "refresh",
                "--declare",
                str(tmp_path / "m.json"),
            ),
        )

    def test_runs_from_the_repo_root_with_a_bounded_timeout(self, tmp_path):
        process = _FakeProcess(_ok("refreshed: (none); skipped (unchanged): a"))
        ScribeCli(process).refresh(
            repo_root=tmp_path,
            manifest_path=tmp_path / "m.json",
            binary_path="/usr/bin/scribe",
        )
        _argv, cwd, timeout_s = process.calls[0]
        assert cwd == tmp_path
        assert timeout_s == scribe_cli._REFRESH_TIMEOUT_S

    def test_a_report_on_stderr_still_parses(self, tmp_path):
        process = _FakeProcess(
            ProcessResult(
                returncode=0,
                stdout="",
                stderr="refreshed: (none); skipped (unchanged): a\n",
            )
        )
        outcome = ScribeCli(process).refresh(
            repo_root=tmp_path,
            manifest_path=tmp_path / "m.json",
            binary_path="/usr/bin/scribe",
        )
        assert outcome.ok is True
        assert outcome.skipped == ("a",)


class TestRefreshDegradesNeverRaises:
    @pytest.fixture
    def manifest(self, tmp_path):
        return tmp_path / "m.json"

    def test_missing_binary(self, monkeypatch, tmp_path, manifest):
        monkeypatch.setattr(scribe_cli.shutil, "which", lambda _name: None)
        process = _FakeProcess(_ok("unused"))
        outcome = ScribeCli(process).refresh(repo_root=tmp_path, manifest_path=manifest)
        assert outcome.ok is False
        assert "did not resolve" in str(outcome.reason)
        assert "compile-on-hunch" in str(outcome.reason)
        assert process.calls == []

    def test_nonzero_exit_names_the_declaration_grammar_as_the_likely_gap(self, tmp_path, manifest):
        """A shipped scribe whose ``index refresh`` does not accept
        caller-declared artifacts exits non-zero -- the operator must be
        told that, not left with a silent no-op."""
        process = _FakeProcess(ProcessResult(returncode=2, stdout="", stderr="Error: No such option: --declare\n"))
        outcome = ScribeCli(process).refresh(repo_root=tmp_path, manifest_path=manifest, binary_path="/usr/bin/scribe")
        assert outcome.ok is False
        assert "No such option: --declare" in str(outcome.reason)
        assert "caller-declared artifacts" in str(outcome.reason)

    def test_launch_failure(self, tmp_path, manifest):
        process = _FakeProcess(error=ProcessError("boom"))
        outcome = ScribeCli(process).refresh(repo_root=tmp_path, manifest_path=manifest, binary_path="/usr/bin/scribe")
        assert outcome.ok is False
        assert "could not run" in str(outcome.reason)

    def test_clean_exit_with_no_report_line(self, tmp_path, manifest):
        process = _FakeProcess(_ok("all good\n"))
        outcome = ScribeCli(process).refresh(repo_root=tmp_path, manifest_path=manifest, binary_path="/usr/bin/scribe")
        assert outcome.ok is False
        assert "printed no" in str(outcome.reason)

    def test_every_degradation_carries_a_reason(self, tmp_path, manifest):
        for process in (
            _FakeProcess(ProcessResult(returncode=1, stdout="", stderr="")),
            _FakeProcess(error=ProcessError("x")),
            _FakeProcess(_ok("")),
        ):
            outcome = ScribeCli(process).refresh(
                repo_root=tmp_path,
                manifest_path=manifest,
                binary_path="/usr/bin/scribe",
            )
            assert outcome.ok is False
            assert outcome.reason


# The Block-If itself ("no `import cocoindex` anywhere in `pyforge.marshal`",
# and the pyforge-scribe SKILL.md's "the CLI is the public contract") is a
# PACKAGE-WIDE property, not this module's -- it is an AST guard over every
# module, in `tests/meta/test_no_engine_or_scribe_internals_import.py`.


class TestRebuild:
    """Story 46.1 (spec-pyforge-marshal CAP-192) -- ``rebuild`` runs one
    substrate member's scribe rebuild and, like every seam here, degrades to
    a reason instead of raising."""

    def test_runs_the_tail_from_the_repo_root(self, tmp_path):
        process = _FakeProcess(_ok("compiled\n"))
        outcome = ScribeCli(process).rebuild(
            repo_root=tmp_path, argv_tail=("graph", "compile", "--nightly"), binary_path="/usr/bin/scribe"
        )
        assert outcome.ok is True
        assert outcome.reason is None
        assert outcome.argv == ("/usr/bin/scribe", "graph", "compile", "--nightly")
        argv, cwd, timeout = process.calls[0]
        assert argv == outcome.argv
        assert cwd == tmp_path
        assert timeout == scribe_cli._REBUILD_TIMEOUT_S

    def test_unresolved_binary_names_where_it_looked(self, monkeypatch, tmp_path):
        monkeypatch.setattr(scribe_cli.shutil, "which", lambda _name: None)
        process = _FakeProcess(_ok(""))
        outcome = ScribeCli(process).rebuild(repo_root=tmp_path, argv_tail=("index", "refresh"))
        assert outcome.ok is False
        assert "did not resolve" in str(outcome.reason)
        assert process.calls == []

    def test_launch_failure_is_a_reason(self, tmp_path):
        process = _FakeProcess(error=ProcessError("timed out after 1800s"))
        outcome = ScribeCli(process).rebuild(
            repo_root=tmp_path, argv_tail=("index", "refresh"), binary_path="/usr/bin/scribe"
        )
        assert outcome.ok is False
        assert "could not run (timed out after 1800s)" in str(outcome.reason)

    def test_non_zero_exit_carries_the_last_output_line(self, tmp_path):
        process = _FakeProcess(ProcessResult(returncode=2, stdout="", stderr="progress\nError: graphifyy missing\n"))
        outcome = ScribeCli(process).rebuild(
            repo_root=tmp_path, argv_tail=("index", "refresh"), binary_path="/usr/bin/scribe"
        )
        assert outcome.ok is False
        assert "exited 2 (Error: graphifyy missing)" in str(outcome.reason)
