"""Story 22.17: harness-done land-only verification refusal reporting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError

from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli import dispatch as dispatch_module
from pyforge.marshal.cli.dispatch import dispatch_once, gather_dispatch_journal_facts
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write
from pyforge.marshal.core.model import Finding, Severity, build_envelope
from .test_dispatch import (
    FakeFs,
    FakeProcess,
    FakeVcs,
    _DONE_SPEC,
    _init_git_repo,
    _write_worktree_spec,
)

_PLATFORM_CI = "pixi run -e pyforge-guild platform-ci-local -- --test"


def _seed_launch_run(repo: Path, slug: str, *, run_id: str, story_key: str) -> Path:
    from pyforge.marshal.core.identity import render_feed_key

    feed = render_feed_key(dispatch_core.normalize(story_key))
    run_dir = dispatch_core.dispatch_run_dir(repo, slug, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    entry = build_entry(
        id=JournalEntryId("w", 0),
        ts="2026-10-07T12:00:00.000Z",
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.INTENT,
        payload={"story_key": feed, "harness_profile": "claude"},
    )
    (run_dir / "journal.jsonl").write_text(prepare_for_write(entry).line, encoding="utf-8")
    return run_dir


def _refused_verify_envelope() -> object:
    return build_envelope(
        command="dispatch verify",
        verdict="gate-failed",
        data={
            "commands": [
                {
                    "command": _PLATFORM_CI,
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "port 15432 already in use",
                }
            ],
        },
        findings=(
            Finding(
                code="MRS-GATE-001",
                severity=Severity.ERROR,
                message=f"verify command {_PLATFORM_CI!r} exited 1",
            ),
        ),
    )


def test_land_only_cli_names_the_failing_verify_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug = "pyforge-marshal"
    story = "22-17-cli-gate"
    _init_git_repo(tmp_path, scope_slug=slug)
    _write_worktree_spec(tmp_path, slug, story, _DONE_SPEC)
    monkeypatch.setattr(dispatch_module, "evaluate_dispatch_verification", lambda **_kwargs: _refused_verify_envelope())
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        process=FakeProcess(),
    )
    messages = " ".join(f.message for f in attempt.findings)
    assert _PLATFORM_CI in messages
    codes = {f.code for f in attempt.findings}
    assert "MRS-GATE-001" in codes
    assert "MRS-DISP-014" in codes
    assert "MRS-DISP-040" in codes
    assert attempt.data["land_verdict"] == "skipped-unverified"


@pytest.mark.parametrize(
    "exc",
    [
        ProcessError("boom", returncode=1),
        VcsCommandError("boom"),
        OSError("boom"),
        TypeError("boom"),
        AttributeError("boom"),
    ],
)
def test_land_only_exception_becomes_a_named_error_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exc: BaseException
) -> None:
    slug = "pyforge-marshal"
    story = "22-17-exception"
    _init_git_repo(tmp_path, scope_slug=slug)
    _write_worktree_spec(tmp_path, slug, story, _DONE_SPEC)

    def _raise(**_kwargs):
        raise exc

    monkeypatch.setattr(dispatch_module, "evaluate_dispatch_verification", _raise)
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        process=FakeProcess(),
    )
    assert attempt.data["land_verdict"] == "skipped-unverified"
    error_findings = [f for f in attempt.findings if f.code == "MRS-DISP-062"]
    assert len(error_findings) == 1
    assert type(exc).__name__ in error_findings[0].message
    assert "boom" in error_findings[0].message


def test_land_only_journals_dispatch_verification_on_prior_run_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = "pyforge-marshal"
    story = "22-17-journal"
    run_id = "pyforge-marshal-20261007T120000000Z-2217beef"
    _init_git_repo(tmp_path, scope_slug=slug)
    _write_worktree_spec(tmp_path, slug, story, _DONE_SPEC)
    run_dir = _seed_launch_run(tmp_path, slug, run_id=run_id, story_key=story)
    fs = FakeFs()
    fs.files[run_dir / "journal.jsonl"] = (run_dir / "journal.jsonl").read_text(encoding="utf-8")
    monkeypatch.setattr(dispatch_module, "evaluate_dispatch_verification", lambda **_kwargs: _refused_verify_envelope())
    monkeypatch.chdir(tmp_path)
    dispatch_once(
        slug=slug,
        story=story,
        fs=fs,
        vcs=FakeVcs(tmp_path),
        process=FakeProcess(),
    )
    journal_path = run_dir / "journal.jsonl"
    journal_text = fs.read_text(journal_path) or ""
    for path, line, _ in fs.appended:
        if path == journal_path:
            journal_text += line if line.endswith("\n") else line + "\n"
    fs.files[journal_path] = journal_text
    lines = [json.loads(line) for line in journal_text.splitlines() if line.strip()]
    verification_outcomes = [
        line
        for line in lines
        if line.get("kind") == dispatch_core.KIND_DISPATCH_VERIFICATION and line.get("phase") == "outcome"
    ]
    assert verification_outcomes
    payload = verification_outcomes[-1]["payload"]
    assert payload["verdict"] == "refused"
    assert payload["ok"] is False
    assert payload["failed_gate"] == "MRS-GATE-001"
    assert _PLATFORM_CI in (payload.get("failed_message") or "")
    facts = gather_dispatch_journal_facts(fs, run_dir, run_id)
    assert facts.verification_verdict == "refused"
    assert facts.verification_failed_gate == "MRS-GATE-001"
    assert _PLATFORM_CI in (facts.verification_failed_message or "")


def test_land_only_without_run_dir_still_reports_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug = "pyforge-marshal"
    story = "22-17-no-run"
    _init_git_repo(tmp_path, scope_slug=slug)
    _write_worktree_spec(tmp_path, slug, story, _DONE_SPEC)
    monkeypatch.setattr(dispatch_module, "evaluate_dispatch_verification", lambda **_kwargs: _refused_verify_envelope())
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        process=FakeProcess(),
    )
    assert any(f.code == "MRS-GATE-001" for f in attempt.findings)
    assert not any(f.code == "MRS-DISP-025" and "journal" in f.message.lower() for f in attempt.findings)


def test_land_only_pass_through_mutation_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Dropping verification findings from the merged envelope must break CLI output."""
    slug = "pyforge-marshal"
    story = "22-17-mutation"
    _init_git_repo(tmp_path, scope_slug=slug)
    _write_worktree_spec(tmp_path, slug, story, _DONE_SPEC)
    real = dispatch_module._verification_verdict_for_cap4

    def _strip_findings(**kwargs):
        cap4 = real(**kwargs)
        return dispatch_module.Cap4VerificationResult(
            verdict=cap4.verdict,
            findings=(),
            gate_envelope_verdict=cap4.gate_envelope_verdict,
            verify_data=cap4.verify_data,
        )

    monkeypatch.setattr(dispatch_module, "evaluate_dispatch_verification", lambda **_kwargs: _refused_verify_envelope())
    monkeypatch.setattr(dispatch_module, "_verification_verdict_for_cap4", _strip_findings)
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        process=FakeProcess(),
    )
    assert not any(f.code == "MRS-GATE-001" for f in attempt.findings)
