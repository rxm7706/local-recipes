"""Unit tests for `run_verify_commands_only` (Story 51.1, CAP-4).

`dispatch_land.py`'s merge-tree preview check re-runs a station's own
`verify_commands` against a throwaway worktree via this function --
deliberately WITHOUT `evaluate_dispatch_verification`'s scope/spec-binding/
cross-surface layers (those diff against a merge-base-aware `base...HEAD`
range that does not transfer to a merge-tree preview; see the spec's Design
Notes). These tests exercise `run_verify_commands_only` directly against a
`FakeProcess`, independent of `execute_dispatch_land`'s own fixtures in
`test_dispatch_landing.py`.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.core.process import ProcessResult
from pyforge.marshal.core import policy
from pyforge.marshal.dispatch_verify import run_verify_commands_only


class FakeProcess:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], Path]] = []

    def run(self, tokens, *, cwd: Path):
        self.calls.append((list(tokens), cwd))
        if tokens and tokens[0] == "false":
            return ProcessResult(returncode=1, stdout="", stderr="boom")
        return ProcessResult(returncode=0, stdout="ok", stderr="")


def _effective(commands: list[str]):
    effective, _ = policy.compose(
        project_slug="pyforge-marshal", project={"verify_commands": commands}, flags={}
    )
    return effective


def test_run_verify_commands_only_reports_pass_and_fail(tmp_path: Path) -> None:
    worktree = tmp_path / "preview"
    worktree.mkdir()
    process = FakeProcess()
    reports, findings = run_verify_commands_only(
        _effective(["true", "false"]), process=process, worktree=worktree
    )
    assert [report["command"] for report in reports] == ["true", "false"]
    assert reports[0]["returncode"] == 0
    assert reports[1]["returncode"] == 1
    assert len(findings) == 1
    assert findings[0].code == "MRS-GATE-001"
    assert all(cwd == worktree for _tokens, cwd in process.calls)


def test_run_verify_commands_only_all_green_has_no_findings(tmp_path: Path) -> None:
    worktree = tmp_path / "preview"
    worktree.mkdir()
    process = FakeProcess()
    reports, findings = run_verify_commands_only(
        _effective(["true", "echo ok"]), process=process, worktree=worktree
    )
    assert len(reports) == 2
    assert findings == ()


def test_run_verify_commands_only_empty_commands_is_a_noop(tmp_path: Path) -> None:
    worktree = tmp_path / "preview"
    worktree.mkdir()
    process = FakeProcess()
    reports, findings = run_verify_commands_only(
        _effective([]), process=process, worktree=worktree
    )
    assert reports == ()
    assert findings == ()
    assert process.calls == []
