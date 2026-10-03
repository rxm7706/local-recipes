"""Unit tests for `run_verify_commands_only` (Story 51.1, CAP-4).

`dispatch_land.py`'s merge-tree preview check re-runs a station's own
`verify_commands` against a throwaway worktree via this function --
deliberately WITHOUT `evaluate_dispatch_verification`'s scope/spec-binding/
cross-surface layers (those diff against a merge-base-aware `base...HEAD`
range that does not transfer to a merge-tree preview; see the spec's Design
Notes). These tests exercise `run_verify_commands_only` directly against a
`FakeProcess`, independent of `execute_dispatch_land`'s own fixtures in
`test_dispatch_landing.py`.

Story 53.1 (spec-53-1, CAP-261a): unlike those layers, the S-13.7 guard is
filesystem-state-based, not a `base...HEAD` diff, so it DOES transfer to a
merge-tree preview worktree -- `run_verify_commands_only` now appends it the
same way `evaluate_dispatch_verification` does, via
`_verify_commands_with_surface_guard`.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.core.process import ProcessResult

from pyforge.marshal.adapters.harness_bmadloop import _SURFACE_RECONCILE_COMMAND
from pyforge.marshal.core import policy
from pyforge.marshal.core.model import Severity
from pyforge.marshal.dispatch_verify import run_verify_commands_only

MARSHAL_COVERAGE_GATE = "pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate"

# Story 79.2 (spec-79-2): the derived hygiene lane, pinned as a literal so
# deleting the derivation fails these tests rather than silently updating them.
LINT_TYPES = "pixi run --frozen -e pyforge-guild lint-types"

# Story 83.2 (spec-83-2): the derived whole-tree check commands, pinned as
# literals so deleting the derivation fails these tests.
PYFORGE_CORE_TEST = "pixi run --frozen -e pyforge-core pyforge-core-test"
DEFERRED_WORK_CHECK = "pixi run --frozen -e pyforge-guild deferred-work-check"


class FakeProcess:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], Path]] = []

    def run(self, tokens, *, cwd: Path):
        self.calls.append((list(tokens), cwd))
        if tokens and tokens[0] == "false":
            return ProcessResult(returncode=1, stdout="", stderr="boom")
        return ProcessResult(returncode=0, stdout="ok", stderr="")


def _effective(commands: list[str]):
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={"verify_commands": commands}, flags={})
    return effective


def test_run_verify_commands_only_reports_pass_and_fail(tmp_path: Path) -> None:
    worktree = tmp_path / "preview"
    worktree.mkdir()
    process = FakeProcess()
    reports, findings, preview_findings = run_verify_commands_only(
        _effective(["true", "false"]), process=process, worktree=worktree
    )
    assert [report["command"] for report in reports] == [
        "true",
        "false",
        _SURFACE_RECONCILE_COMMAND,
        LINT_TYPES,
        PYFORGE_CORE_TEST,
        DEFERRED_WORK_CHECK,
    ]
    assert reports[0]["returncode"] == 0
    assert reports[1]["returncode"] == 1
    assert preview_findings == ()
    assert len(findings) == 1
    assert findings[0].code == "MRS-GATE-001"
    assert all(cwd == worktree for _tokens, cwd in process.calls)


def test_run_verify_commands_only_all_green_has_no_findings(tmp_path: Path) -> None:
    worktree = tmp_path / "preview"
    worktree.mkdir()
    process = FakeProcess()
    reports, findings, preview_findings = run_verify_commands_only(
        _effective(["true", "echo ok"]), process=process, worktree=worktree
    )
    assert len(reports) == 6  # 2 station commands + 4 derived commands
    assert findings == ()
    assert preview_findings == ()


def test_run_verify_commands_only_empty_commands_still_runs_the_derived_commands(
    tmp_path: Path,
) -> None:
    """Story 53.1: a merge-tree preview is gated on S-13.7 exactly like a
    real dispatch verification pass, even for a station with no declared
    ``verify_commands`` of its own."""
    worktree = tmp_path / "preview"
    worktree.mkdir()
    process = FakeProcess()
    reports, findings, preview_findings = run_verify_commands_only(_effective([]), process=process, worktree=worktree)
    assert [report["command"] for report in reports] == [
        _SURFACE_RECONCILE_COMMAND,
        LINT_TYPES,
        PYFORGE_CORE_TEST,
        DEFERRED_WORK_CHECK,
    ]
    assert findings == ()
    assert preview_findings == ()
    assert process.calls == [
        (_SURFACE_RECONCILE_COMMAND.split(), worktree),
        (LINT_TYPES.split(), worktree),
        (PYFORGE_CORE_TEST.split(), worktree),
        (DEFERRED_WORK_CHECK.split(), worktree),
    ]


class _PreviewChangedFilesVcs:
    def __init__(self, *, preview_changed: tuple[str, ...] | None, raise_on_preview: bool) -> None:
        self._preview_changed = preview_changed
        self._raise_on_preview = raise_on_preview

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]:
        if self._raise_on_preview:
            raise RuntimeError("git diff failed in preview")
        assert self._preview_changed is not None
        return self._preview_changed


def test_run_verify_commands_only_derives_coverage_gate_from_preview_diff(tmp_path: Path) -> None:
    preview = tmp_path / "preview"
    preview.mkdir()
    marshal_src = "src/shared/packages/pyforge-marshal/src/pyforge/marshal/x.py"
    vcs = _PreviewChangedFilesVcs(preview_changed=(marshal_src,), raise_on_preview=False)
    process = FakeProcess()
    reports, findings, preview_findings = run_verify_commands_only(
        _effective(["true"]),
        process=process,
        worktree=preview,
        repo_root=tmp_path,
        vcs=vcs,
    )
    commands = [report["command"] for report in reports]
    assert MARSHAL_COVERAGE_GATE in commands
    assert findings == ()
    assert preview_findings == ()


def test_run_verify_commands_only_falls_back_to_story_changed_files(tmp_path: Path) -> None:
    preview = tmp_path / "preview"
    preview.mkdir()
    marshal_src = "src/shared/packages/pyforge-marshal/src/pyforge/marshal/x.py"
    vcs = _PreviewChangedFilesVcs(preview_changed=None, raise_on_preview=True)
    process = FakeProcess()
    reports, findings, preview_findings = run_verify_commands_only(
        _effective(["true"]),
        process=process,
        worktree=preview,
        repo_root=tmp_path,
        vcs=vcs,
        story_changed_files=(marshal_src,),
    )
    commands = [report["command"] for report in reports]
    assert MARSHAL_COVERAGE_GATE in commands
    assert findings == ()
    assert any(f.code == "MRS-GATE-009" and f.severity is Severity.WARN for f in preview_findings)


def test_run_verify_commands_only_refuses_when_changed_files_unresolved(tmp_path: Path) -> None:
    preview = tmp_path / "preview"
    preview.mkdir()
    vcs = _PreviewChangedFilesVcs(preview_changed=None, raise_on_preview=True)
    process = FakeProcess()
    _reports, findings, preview_findings = run_verify_commands_only(
        _effective(["true"]),
        process=process,
        worktree=preview,
        repo_root=tmp_path,
        vcs=vcs,
        story_changed_files=None,
    )
    assert findings == ()
    assert any(f.code == "MRS-GATE-009" and f.severity is Severity.ERROR for f in preview_findings)
