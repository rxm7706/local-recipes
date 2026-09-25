"""Unit tests for ``marshal factory dispatch`` (Story 22.1)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult
from scope_triangle import point_scope_triangle

from pyforge.marshal.cli.dispatch import (
    _surface_session_precondition_findings,
    dispatch_once,
    resolve_max_parallel,
    run_dispatch,
)
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import policy
from pyforge.marshal.core.dispatch_landing import DispatchLandingVerdict
from pyforge.marshal.core.model import Severity
from pyforge.marshal.core.status import FleetHomeFacts, build_fleet_row
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.ports.build_harness import (
    DispatchLaunchResult,
    HarnessCandidateSkip,
    HarnessResolution,
)
from pyforge.marshal.ports.fs import AdvisoryLock


def _init_git_repo(path: Path, *, scope_slug: str | None = None) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "dispatch@test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "dispatch"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    if scope_slug is not None:
        point_scope_triangle(path, scope_slug)
        os.environ["BMAD_ACTIVE_PROJECT"] = scope_slug


class FakeFs:
    def __init__(self) -> None:
        self.dirs: set[Path] = set()
        self.files: dict[Path, str] = {}
        self.appended: list[tuple[Path, str, bool]] = []

    def is_dir(self, path: Path) -> bool:
        return path in self.dirs

    def ensure_dir(self, path: Path) -> None:
        self.dirs.add(path)

    def create_dir_exclusive(self, path: Path) -> None:
        self.dirs.add(path)

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        self.appended.append((path, line, fsync))

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.files[path] = content

    def read_text(self, path: Path) -> str | None:
        return self.files.get(path)

    def acquire_advisory_lock(self, path: Path, *, timeout_s: float) -> AdvisoryLock:
        # Story 22.11: `dispatch --stories` delegates to `run_fleet_drain`,
        # which acquires the fleet-wide cycle lock -- a no-op fake, matching
        # `test_dispatch_fleet.py`'s own `FakeFs`.
        return AdvisoryLock(path=path.with_suffix(path.suffix + ".lock"), handle=None)

    def release_advisory_lock(self, lock: AdvisoryLock) -> None:
        pass


class FakeVcs:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.added: list[tuple[Path, Path, str, str]] = []
        # Story 22.9: which branches git already has, and where each is
        # checked out -- the two facts branch resolution reads.
        self.branches: set[str] = set()
        self.worktrees: dict[str, Path] = {}

    def repo_common_root(self, _cwd: Path) -> Path:
        return self.repo_root

    def branch_exists(self, _repo_root: Path, branch: str) -> bool:
        return branch in self.branches or branch in self.worktrees

    def worktree_path_for_branch(self, _repo_root: Path, branch: str) -> Path | None:
        return self.worktrees.get(branch)

    def add_worktree(self, repo_root: Path, home: Path, branch: str, *, base: str) -> None:
        self.added.append((repo_root, home, branch, base))
        self.worktrees[branch] = home
        home.mkdir(parents=True, exist_ok=True)

    def worktree_head_sha(self, _worktree: Path) -> str:
        return "baseline0001"

    def changed_files(self, _repo_root: Path, _worktree_path: Path, *, base: str) -> tuple[str, ...]:
        return ()

    def worktree_unified_patch(self, _worktree_path: Path, *, baseline_sha: str) -> str:
        return ""

    # Story 51.9: simulate a clean, unmoved local `main` by default, so the
    # campaign's ledger reads keep going through the local `HarnessPort`
    # read unchanged for every pre-existing test in this file.
    def has_uncommitted_changes(self, _worktree_path: Path) -> bool:
        return False

    def resolve_ref(self, _repo_root: Path, _ref: str) -> str:
        return self.worktree_head_sha(_repo_root)


class FakeBuildHarness:
    def __init__(self, *, present: bool = True, pid: int = 4242) -> None:
        self.present = present
        self.pid = pid
        self.calls: list[dict[str, object]] = []
        self.preference_seen: tuple[str, ...] | None = None

    def binary_present(self, preference=(), repo_root=None) -> HarnessResolution:
        self.preference_seen = tuple(preference)
        if not self.present:
            return HarnessResolution(
                profile=None,
                skipped=tuple(
                    HarnessCandidateSkip(profile=name, reason=f"binary {name!r} not found on PATH")
                    for name in preference
                ),
            )
        chosen = next(iter(preference), "claude")
        return HarnessResolution(profile=chosen, binary_path=f"/usr/bin/{chosen}")

    def dispatch(self, worktree: Path, **kwargs) -> DispatchLaunchResult:
        self.calls.append({"worktree": worktree, **kwargs})
        resolution = kwargs.get("resolution")
        return DispatchLaunchResult(
            pid=self.pid,
            command=("fake-harness",),
            model=kwargs.get("model"),
            budget_env=dict(kwargs.get("budget_env") or {}),
            profile=resolution.profile if resolution is not None else None,
        )


class FakeProcess:
    def __init__(self, *, alive: bool = True, session_check_returncode: int = 0) -> None:
        self.alive = alive
        # Story 63.4: dispatch_once shells `steward session check --json`
        # right after repo_root resolves. Default 0 ("ok") keeps every
        # pre-existing fixture behaviour byte-identical -- no unexpected
        # MRS-DISP-049 finding unless a test opts in.
        self.session_check_returncode = session_check_returncode
        self.run_calls: list[list[str]] = []

    def is_alive(self, _pid: int) -> bool:
        return self.alive

    def spawn_detached(self, argv, *, cwd: Path, log_path: Path) -> int:
        return 4243

    def run(self, argv, *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
        self.run_calls.append(list(argv))
        return ProcessResult(returncode=self.session_check_returncode, stdout="", stderr="")


def test_surface_session_precondition_findings_ok_returns_none(tmp_path: Path) -> None:
    process = FakeProcess(session_check_returncode=0)
    finding = _surface_session_precondition_findings(process=process, repo_root=tmp_path)
    assert finding is None
    assert process.run_calls == [
        ["pixi", "run", "--frozen", "-e", "pyforge-guild", "steward", "session", "check", "--json"]
    ]


def test_surface_session_precondition_findings_names_non_ok_findings(tmp_path: Path) -> None:
    class Proc:
        def run(self, argv, *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
            payload = json.dumps(
                {
                    "ok": False,
                    "findings": [
                        {"name": "gh-auth", "ok": False},
                        {"name": "pixi-guild", "ok": True},
                    ],
                }
            )
            return ProcessResult(returncode=1, stdout=payload, stderr="")

    finding = _surface_session_precondition_findings(process=Proc(), repo_root=tmp_path)
    assert finding is not None
    assert finding.code == "MRS-DISP-049"
    assert finding.severity is Severity.WARN
    assert "gh-auth" in finding.message
    assert "pixi-guild" not in finding.message


def test_surface_session_precondition_findings_unparseable_output_uses_tail(tmp_path: Path) -> None:
    class Proc:
        def run(self, argv, *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
            return ProcessResult(returncode=1, stdout="not json", stderr="traceback\nlast line")

    finding = _surface_session_precondition_findings(process=Proc(), repo_root=tmp_path)
    assert finding is not None
    assert finding.code == "MRS-DISP-049"
    assert "last line" in finding.message


def test_surface_session_precondition_findings_process_error_warns(tmp_path: Path) -> None:
    class Proc:
        def run(self, argv, *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
            raise ProcessError("steward is not on PATH")

    finding = _surface_session_precondition_findings(process=Proc(), repo_root=tmp_path)
    assert finding is not None
    assert finding.code == "MRS-DISP-049"
    assert finding.severity is Severity.WARN
    assert "could not run" in finding.message


def test_dispatch_once_surfaces_mrs_disp_049_when_session_check_non_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 63.4 review finding (Verification Gap #1): the ``_surface_session_precondition_findings``
    unit is covered directly above, but its wiring into ``dispatch_once`` --
    the call site an operator actually drives -- was never exercised
    end-to-end. This proves a non-ok ``steward session check`` verdict
    reaches ``attempt.findings`` through the real ``dispatch_once`` call,
    not only through the isolated helper."""
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"

    class NonOkSessionProcess(FakeProcess):
        def run(self, argv, *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
            self.run_calls.append(list(argv))
            payload = json.dumps({"ok": False, "findings": [{"name": "gh-auth", "ok": False}]})
            return ProcessResult(returncode=1, stdout=payload, stderr="")

    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=NonOkSessionProcess(),
    )
    [finding] = [f for f in attempt.findings if f.code == "MRS-DISP-049"]
    assert finding.severity is Severity.WARN
    assert "gh-auth" in finding.message


def test_resolve_story_spec_path_finds_tracked_spec(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    spec = specs / f"spec-{story}.md"
    spec.write_text("---\ndifficulty: medium\n---\n", encoding="utf-8")
    resolved = dispatch_core.resolve_story_spec_path(tmp_path, slug, story)
    assert resolved == spec


class _FakeVcsForSpecTextAtRef:
    """A minimal ``VcsPort`` double: ``file_text_at_ref`` looks up canned
    content keyed by the exact ``(ref, path)`` pair it was called with --
    review finding for Story 51.7/CAP-255: ``spec_text_at_ref`` itself
    (the impure half every ``corroborated_merged_story_keys`` caller
    shares) had no direct test at all before this."""

    def __init__(self, content_by_ref_path: dict[tuple[str, str], str]) -> None:
        self._content = content_by_ref_path

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str) -> str | None:
        return self._content.get((ref, path))


def test_spec_text_at_ref_reads_the_resolved_path_at_the_given_ref(tmp_path: Path) -> None:
    """The local working tree only resolves the spec's stable PATH; the
    CONTENT returned is whatever the ref holds there -- proving the two
    halves (local path resolution, ref-scoped content read) are wired
    together correctly, not just each independently correct."""
    slug = "pyforge-doctor"
    story = "27-4"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    spec = specs / f"spec-{story}-mint.md"
    spec.write_text("---\nstatus: ready\n---\n", encoding="utf-8")
    rel_path = spec.relative_to(dispatch_core.canonical_repo_root(tmp_path)).as_posix()
    vcs = _FakeVcsForSpecTextAtRef({("origin/main", rel_path): "---\nstatus: done\n---\n"})
    assert dispatch_core.spec_text_at_ref(vcs, tmp_path, slug, story) == "---\nstatus: done\n---\n"


def test_spec_text_at_ref_none_when_no_local_candidate_resolves(tmp_path: Path) -> None:
    vcs = _FakeVcsForSpecTextAtRef({})
    assert dispatch_core.spec_text_at_ref(vcs, tmp_path, "pyforge-doctor", "27-4") is None


def test_spec_text_at_ref_none_when_ref_has_no_such_path(tmp_path: Path) -> None:
    """A spec minted after ``ref`` was fetched (or never fetched at all):
    the local candidate resolves but the ref has nothing there -- fails
    closed, never falling back to the local working tree's own copy."""
    slug = "pyforge-doctor"
    story = "27-4"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}-mint.md").write_text("---\nstatus: ready\n---\n", encoding="utf-8")
    vcs = _FakeVcsForSpecTextAtRef({})
    assert dispatch_core.spec_text_at_ref(vcs, tmp_path, slug, story) is None


def test_build_fleet_row_surfaces_live_dispatch(tmp_path: Path) -> None:
    facts = FleetHomeFacts(
        slug="pyforge-marshal",
        branch="loop/pyforge-marshal",
        has_run=False,
        dispatch_story="22-1-example",
        dispatch_engine_alive=True,
        dispatch_elapsed_seconds=12.5,
        dispatch_run_id="pyforge-marshal-20260823T000000000Z-deadbeef",
    )
    row, finding = build_fleet_row(facts)
    assert finding is None
    assert row["state"] == "running"
    assert row["current_story"] == "22-1-example"
    assert row["elapsed_seconds"] == 12.5


def test_run_dispatch_journals_and_returns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    spec = specs / f"spec-{story}.md"
    spec.write_text("---\ndifficulty: medium\n---\n# spec\n", encoding="utf-8")

    fs = FakeFs()
    vcs = FakeVcs(tmp_path)
    harness = FakeBuildHarness()
    process = FakeProcess()

    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=fs,
        vcs=vcs,
        build_harness=harness,
        process=process,
    )
    assert code == EXIT_OK
    assert harness.calls
    assert harness.calls[0]["project_slug"] == slug
    assert fs.appended
    assert any("dispatch-launch" in line for _, line, _ in fs.appended)


def test_run_dispatch_surfaces_the_context_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Story 28.1 (SPEC-marshal-token-economy CAP-1): `dispatch_once`'s
    returned AND journaled data both carry the SAME `context` payload
    `core/policy.py::resolve_context_layers` computes -- the one
    composition site both `render_policy_toml` (bmad-loop spin) and this
    engine (factory dispatch) resolve from. Story 33.2 enables layers in the
    tracked marshal-policy.toml; this test pins an explicit layers-off
    composition to preserve the absent-block contract."""
    import json

    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.core import policy

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    spec = specs / f"spec-{story}.md"
    spec.write_text("---\ndifficulty: medium\n---\n# spec\n", encoding="utf-8")

    effective, _ = policy.compose(project_slug=slug, project={}, flags={})
    monkeypatch.setattr(
        dispatch_module,
        "_compose_policy",
        lambda _slug, flags=None: effective,
    )

    fs = FakeFs()
    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=fs,
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert code == EXIT_OK
    expected = {layer: {"enabled": False, "aggressiveness": "medium"} for layer in policy.CONTEXT_LAYER_NAMES}
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["context"] == expected
    launch_lines = [line for _, line, _ in fs.appended if "dispatch-launch" in line]
    assert any(json.loads(line)["payload"].get("context") == expected for line in launch_lines)


def test_compose_policy_on_real_repo_enables_all_context_layers_for_dispatch() -> None:
    """Story 33.2 (CAP-1): factory dispatch reads the tracked marshal-policy.toml
    and resolves all five context layers enabled via the single composition site.

    Story 46.4: pyforge-marshal's own marshal-policy.toml no longer declares a
    `[context]` block at all -- the 4 harness-agnostic layers now come from
    the repo-default `_bmad-output/policy-defaults.toml`, and `wire`'s value
    passes through `resolve_context_layers` as the raw `"auto"` tri-state
    (unresolved at this composition-time call site -- no harness profile is
    in scope here yet)."""
    from pyforge.marshal.cli.dispatch import _compose_policy
    from pyforge.marshal.core import policy

    repo_root = Path(__file__).resolve().parents[6]
    policy_path = repo_root / "_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml"
    if not policy_path.is_file():
        pytest.skip("marshal-policy.toml not present in this checkout")

    effective = _compose_policy("pyforge-marshal")
    resolved = policy.resolve_context_layers(effective)
    assert set(resolved) == set(policy.CONTEXT_LAYER_NAMES)
    for layer in policy.CONTEXT_LAYER_NAMES:
        if layer == "wire":
            assert resolved[layer] == {"enabled": "auto", "aggressiveness": "medium"}
            continue
        assert resolved[layer] == {"enabled": True, "aggressiveness": "medium"}


def test_run_dispatch_refuses_missing_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session"
    args = argparse.Namespace(slug=slug, story=story, format="text")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(present=False),
        process=FakeProcess(),
    )
    assert code != EXIT_OK


def _enable_wire_layer(monkeypatch: pytest.MonkeyPatch, slug: str) -> None:
    """Compose the SAME `EffectivePolicy` the real code composes, but with a
    declared `[context] wire` layer -- the conventional project-policy file
    `_compose_policy` reads lives at a module-derived repo path no test may
    write to, so the composition is redirected, never faked."""
    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.core import policy

    effective, _ = policy.compose(
        project_slug=slug,
        project={"context": {"wire": {"enabled": True, "aggressiveness": "high"}}},
        flags={},
    )
    monkeypatch.setattr(
        dispatch_module,
        "_compose_policy",
        lambda _slug, flags=None: effective,
    )


def test_dispatch_hands_the_launch_seam_only_the_wire_layer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Story 28.2 (SPEC-marshal-token-economy CAP-2): the wire entry of the
    SAME `[context]` payload Story 28.1 resolves is what reaches
    `BuildHarnessPort.dispatch` -- one composition site, and only the layer
    this seam implements (the launch has no business reading a layer it
    cannot apply)."""
    import json

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "28-2-wire-compression-at-the-harness-seam"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")

    _enable_wire_layer(monkeypatch, slug)
    harness = FakeBuildHarness()
    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    assert (
        run_dispatch(
            args,
            fs=FakeFs(),
            vcs=FakeVcs(tmp_path),
            build_harness=harness,
            process=FakeProcess(),
        )
        == EXIT_OK
    )
    payload = json.loads(capsys.readouterr().out)
    expected = {"enabled": True, "aggressiveness": "high"}
    assert harness.calls[0]["wire_layer"] == expected
    assert payload["data"]["context"]["wire"] == expected


def test_dispatch_journals_and_echoes_what_the_wire_layer_did(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """ "Was this session wrapped?" is a RECORDED fact of every dispatch --
    echoed in `data` and journaled in the launch outcome entry -- rather
    than an inference from an argv nobody kept. An APPLIED layer raises no
    finding: nothing degraded."""
    import json

    from pyforge.marshal.core.harness_profile import WireWrap

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "28-2-wire-compression-at-the-harness-seam"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")

    store = str(tmp_path / "wt" / ".marshal" / "wire")

    class WrappingHarness(FakeBuildHarness):
        def dispatch(self, worktree: Path, **kwargs) -> DispatchLaunchResult:
            result = super().dispatch(worktree, **kwargs)
            return DispatchLaunchResult(
                pid=result.pid,
                command=result.command,
                model=result.model,
                budget_env=result.budget_env,
                profile=result.profile,
                wire=WireWrap(
                    applied=True,
                    argv_prefix=("/bin/headroom", "wrap", "claude", "--"),
                    store_dir=store,
                    aggressiveness="high",
                ),
            )

    _enable_wire_layer(monkeypatch, slug)
    fs = FakeFs()
    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    assert (
        run_dispatch(
            args,
            fs=fs,
            vcs=FakeVcs(tmp_path),
            build_harness=WrappingHarness(),
            process=FakeProcess(),
        )
        == EXIT_OK
    )
    payload = json.loads(capsys.readouterr().out)
    expected = {
        "applied": True,
        "reason": None,
        "store_dir": store,
        "aggressiveness": "high",
    }
    assert payload["data"]["wire"] == expected
    assert [f for f in payload["findings"] if f["code"] == "MRS-DISP-033"] == []
    launch_lines = [line for _, line, _ in fs.appended if "dispatch-launch" in line]
    assert any(json.loads(line)["payload"].get("wire") == expected for line in launch_lines)


def test_dispatch_reports_a_degraded_wire_layer_as_a_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """CAP-2's graceful-degradation AC at the report boundary: the layer
    disabling itself is NAMED (`MRS-DISP-033`), and it is a WARN over a
    session that is already live and unwrapped -- never a refusal, never
    silence."""
    import json

    from pyforge.marshal.core.harness_profile import WireWrap

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "28-2-wire-compression-at-the-harness-seam"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")

    reason = "wire-compression wrapper binary 'headroom' did not resolve"

    class DegradingHarness(FakeBuildHarness):
        def dispatch(self, worktree: Path, **kwargs) -> DispatchLaunchResult:
            result = super().dispatch(worktree, **kwargs)
            return DispatchLaunchResult(
                pid=result.pid,
                command=result.command,
                model=result.model,
                budget_env=result.budget_env,
                profile=result.profile,
                wire=WireWrap(applied=False, reason=reason, aggressiveness="high"),
            )

    _enable_wire_layer(monkeypatch, slug)
    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=DegradingHarness(),
        process=FakeProcess(),
    )
    # WARN, so the dispatch still succeeds -- the run is live and unwrapped
    assert code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    [finding] = [f for f in payload["findings"] if f["code"] == "MRS-DISP-033"]
    assert finding["severity"] == "warn"
    assert finding["message"] == reason
    assert payload["data"]["wire"]["applied"] is False
    assert payload["data"]["wire"]["reason"] == reason


def test_dispatch_with_no_wire_decision_reports_the_layer_as_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A harness that returns no wire decision at all (the port's field is
    optional) still yields a stated disposition rather than a missing key --
    and raises nothing, because nothing was enabled."""
    import json

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "28-2-wire-compression-at-the-harness-seam"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")

    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    assert (
        run_dispatch(
            args,
            fs=FakeFs(),
            vcs=FakeVcs(tmp_path),
            build_harness=FakeBuildHarness(),
            process=FakeProcess(),
        )
        == EXIT_OK
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["wire"] == {
        "applied": False,
        "reason": None,
        "store_dir": None,
        "aggressiveness": None,
    }
    assert [f for f in payload["findings"] if f["code"] == "MRS-DISP-033"] == []


def test_dispatch_wire_payload_has_exactly_the_single_spellings_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """``WireWrap.journal_payload()`` is the ONE spelling of this payload,
    on both engines. The expected key set is derived FROM that method rather
    than restated here, so adding a field to ``WireWrap`` fails this test
    the moment a call site hand-spells the shape instead of projecting it --
    the drift a literal dict makes silent."""
    import json

    from pyforge.marshal.core.harness_profile import WireWrap

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "28-2-wire-compression-at-the-harness-seam"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")

    fs = FakeFs()
    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    assert (
        run_dispatch(
            args,
            fs=fs,
            vcs=FakeVcs(tmp_path),
            build_harness=FakeBuildHarness(),
            process=FakeProcess(),
        )
        == EXIT_OK
    )
    expected_fields = set(WireWrap(applied=False).journal_payload())
    payload = json.loads(capsys.readouterr().out)
    assert set(payload["data"]["wire"]) == expected_fields
    launch_lines = [line for _, line, _ in fs.appended if "dispatch-launch" in line]
    journaled = [json.loads(line)["payload"]["wire"] for line in launch_lines if "wire" in json.loads(line)["payload"]]
    assert journaled and all(set(entry) == expected_fields for entry in journaled)


def test_dispatch_states_the_wire_disposition_even_when_the_launch_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """``ports/build_harness.py`` promises the wire disposition is "a
    recorded fact of every dispatch", and ``cli/spin.py`` echoes its own
    unconditionally -- but the ``BuildHarnessError`` branch returns without
    ever reaching a launch result, so the key went missing from precisely
    the envelope an operator most wants to inspect. A consumer reading
    ``data["wire"]`` unguarded broke on the failure case alone."""
    import json

    from pyforge.marshal.adapters.harness_bmadbuild import BuildHarnessError

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "28-2-wire-compression-at-the-harness-seam"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")

    class FailingHarness(FakeBuildHarness):
        def dispatch(self, worktree: Path, **kwargs) -> DispatchLaunchResult:
            raise BuildHarnessError("cannot launch session harness: boom")

    _enable_wire_layer(monkeypatch, slug)
    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FailingHarness(),
        process=FakeProcess(),
    )
    assert code != EXIT_OK  # the launch genuinely failed
    payload = json.loads(capsys.readouterr().out)
    assert [f for f in payload["findings"] if f["code"] == "MRS-DISP-008"]
    assert payload["data"]["wire"] == {
        "applied": False,
        "reason": None,
        "store_dir": None,
        "aggressiveness": None,
    }


def test_run_dispatch_carries_profile_and_reports_skips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Story 22.8: the envelope names the resolved profile; every skipped
    preference candidate surfaces as a structured MRS-DISP-027 WARN."""
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "22-8-the-session-harness-is-profile-driven-across-agent-clis"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")

    import json

    from pyforge.marshal.cli.dispatch import _compose_policy
    from pyforge.marshal.ports.build_harness import (
        HarnessCandidateSkip as Skip,
    )
    from pyforge.marshal.ports.build_harness import (
        HarnessResolution as Resolution,
    )

    class SkippingHarness(FakeBuildHarness):
        def binary_present(self, preference=(), repo_root=None):
            self.preference_seen = tuple(preference)
            return Resolution(
                profile="claude",
                binary_path="/usr/bin/claude",
                skipped=(Skip(profile="cursor", reason="authcheck exited 1 (auth required)"),),
            )

    harness = SkippingHarness()
    args = argparse.Namespace(slug=slug, story=story, format="json", harness=None)
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=harness,
        process=FakeProcess(),
    )
    assert code == EXIT_OK
    effective = _compose_policy(slug)
    assert harness.preference_seen == tuple(effective.harness_preference.value)
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["harness_profile"] == "claude"
    skips = [f for f in payload["findings"] if f["code"] == "MRS-DISP-027"]
    assert len(skips) == 1 and "cursor" in skips[0]["message"]
    assert harness.calls and harness.calls[0]["resolution"].profile == "claude"


def test_run_dispatch_refusal_names_every_candidate_tried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """MRS-DISP-003 must say what was tried and why each candidate was
    skipped -- the 2026-08-27 silent cursor-auth death, made loud."""
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "22-8-the-session-harness-is-profile-driven-across-agent-clis"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")

    import json

    from pyforge.marshal.cli.dispatch import _compose_policy

    args = argparse.Namespace(slug=slug, story=story, format="json", harness=None)
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(present=False),
        process=FakeProcess(),
    )
    assert code != EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    refusals = [f for f in payload["findings"] if f["code"] == "MRS-DISP-003"]
    assert len(refusals) == 1
    message = refusals[0]["message"]
    assert "no dispatchable session-harness profile" in message
    effective = _compose_policy(slug)
    for name in effective.harness_preference.value:
        assert name in message


# --------------------------------------------------------------------------
# Story 22.9: a dispatch branch names its station
# --------------------------------------------------------------------------


_ATLAS = "pyforge-atlas"
_DOCTOR = "pyforge-doctor"
_SHARED_STORY = "20-1-a-story-key-two-stations-both-happen-to-use"
_SHARED_FEED_KEY = "20.1"


def _seed_spec(repo_root: Path, slug: str, story: str) -> Path:
    specs = dispatch_core.planning_specs_dir(repo_root, slug)
    specs.mkdir(parents=True, exist_ok=True)
    spec = specs / f"spec-{story}.md"
    spec.write_text("---\ndifficulty: medium\n---\n# spec\n", encoding="utf-8")
    return spec


def _dispatch(
    repo_root: Path,
    slug: str,
    story: str,
    *,
    vcs: FakeVcs,
    monkeypatch: pytest.MonkeyPatch,
) -> int:
    """Run one dispatch and RETURN ITS EXIT CODE.

    The code is the assertion that keeps ``MRS-DISP-030``'s ERROR tier
    honest: without it, downgrading that code to WARN in ``verdict.py``
    would leave a dispatch that provisioned nothing exiting 0 with the
    whole suite still green.
    """
    point_scope_triangle(repo_root, slug)
    os.environ["BMAD_ACTIVE_PROJECT"] = slug
    _seed_spec(repo_root, slug, story)
    monkeypatch.chdir(repo_root)
    args = argparse.Namespace(slug=slug, story=story, format="json")
    return run_dispatch(
        args,
        fs=FakeFs(),
        vcs=vcs,
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )


def test_dispatch_branch_carries_its_station() -> None:
    assert dispatch_core.dispatch_worktree_branch(_ATLAS, "20.2") == "dispatch/pyforge-atlas/20.2"
    assert dispatch_core.legacy_dispatch_worktree_branch("20.2") == "marshal/20.2"


def test_dispatch_branch_requires_its_station() -> None:
    """The pre-22.9 one-argument call must not silently keep working."""
    with pytest.raises(TypeError):
        dispatch_core.dispatch_worktree_branch("20.2")  # type: ignore[call-arg]


def test_two_stations_sharing_a_story_key_never_reuse_one_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The motivating defect: ``_ensure_dispatch_worktree`` resolved by
    branch name, so a station-less ``marshal/20.1`` handed the second
    station the first station's tree. Two stations, one story key, zero
    reuse -- collision is impossible by construction."""
    _init_git_repo(tmp_path)
    vcs = FakeVcs(tmp_path)
    _dispatch(tmp_path, _ATLAS, _SHARED_STORY, vcs=vcs, monkeypatch=monkeypatch)
    _dispatch(tmp_path, _DOCTOR, _SHARED_STORY, vcs=vcs, monkeypatch=monkeypatch)

    branches = [branch for _root, _home, branch, _base in vcs.added]
    homes = [home for _root, home, _branch, _base in vcs.added]
    assert branches == [
        dispatch_core.dispatch_worktree_branch(_ATLAS, _SHARED_FEED_KEY),
        dispatch_core.dispatch_worktree_branch(_DOCTOR, _SHARED_FEED_KEY),
    ]
    assert len(set(branches)) == 2
    assert len(set(homes)) == 2


def test_legacy_branch_at_this_stations_worktree_is_still_resolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """An in-flight run started before 22.9 keeps its ``marshal/<key>``
    branch: git has it checked out at THIS station's dispatch worktree, so
    it is attributable and reused -- under a loud MRS-DISP-031 advisory,
    never silently."""
    import json

    _init_git_repo(tmp_path)
    vcs = FakeVcs(tmp_path)
    legacy = dispatch_core.legacy_dispatch_worktree_branch(_SHARED_FEED_KEY)
    ours = dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, _SHARED_FEED_KEY)
    ours.mkdir(parents=True)
    vcs.worktrees[legacy] = ours

    code = _dispatch(tmp_path, _ATLAS, _SHARED_STORY, vcs=vcs, monkeypatch=monkeypatch)
    payload = json.loads(capsys.readouterr().out)

    assert code == EXIT_OK  # MRS-DISP-031 is an advisory, never a refusal
    assert vcs.added == []  # the existing tree was reused, not re-provisioned
    assert payload["data"]["branch"] == legacy
    assert payload["data"]["worktree_path"] == str(ours)
    advisories = [f for f in payload["findings"] if f["code"] == "MRS-DISP-031"]
    assert len(advisories) == 1
    assert legacy in advisories[0]["message"]


def test_legacy_branch_of_another_station_is_refused_land_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """The refusal names the legacy branch and the land-first remedy --
    never a silent reuse of another station's tree."""
    import json

    _init_git_repo(tmp_path)
    vcs = FakeVcs(tmp_path)
    legacy = dispatch_core.legacy_dispatch_worktree_branch(_SHARED_FEED_KEY)
    theirs = dispatch_core.dispatch_worktree_path(tmp_path, _DOCTOR, _SHARED_FEED_KEY)
    theirs.mkdir(parents=True)
    vcs.worktrees[legacy] = theirs

    code = _dispatch(tmp_path, _ATLAS, _SHARED_STORY, vcs=vcs, monkeypatch=monkeypatch)
    payload = json.loads(capsys.readouterr().out)

    assert code != EXIT_OK
    assert vcs.added == []
    refusals = [f for f in payload["findings"] if f["code"] == "MRS-DISP-030"]
    assert len(refusals) == 1
    message = refusals[0]["message"]
    assert legacy in message
    assert str(theirs) in message
    assert "Land that branch first" in message
    # No session was launched off another station's tree.
    assert "session_pid" not in payload["data"]


def test_preserved_legacy_branch_without_a_worktree_is_refused_not_stranded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A preserved ``marshal/<key>`` branch (pushed 2026-08-27, no worktree)
    cannot be attributed to a station, so dispatch refuses with the
    land-first remedy rather than minting a fresh branch beside it and
    stranding the work."""
    import json

    _init_git_repo(tmp_path)
    vcs = FakeVcs(tmp_path)
    legacy = dispatch_core.legacy_dispatch_worktree_branch(_SHARED_FEED_KEY)
    vcs.branches.add(legacy)

    code = _dispatch(tmp_path, _ATLAS, _SHARED_STORY, vcs=vcs, monkeypatch=monkeypatch)
    payload = json.loads(capsys.readouterr().out)

    assert code != EXIT_OK
    assert vcs.added == []
    refusals = [f for f in payload["findings"] if f["code"] == "MRS-DISP-030"]
    assert len(refusals) == 1
    assert legacy in refusals[0]["message"]
    assert "Land that branch first" in refusals[0]["message"]


def test_station_scoped_branch_wins_over_a_same_key_legacy_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Once a station has migrated, an unrelated station's leftover legacy
    branch under the same key neither blocks it nor is adopted by it."""
    import json

    _init_git_repo(tmp_path)
    vcs = FakeVcs(tmp_path)
    branch = dispatch_core.dispatch_worktree_branch(_ATLAS, _SHARED_FEED_KEY)
    ours = dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, _SHARED_FEED_KEY)
    ours.mkdir(parents=True)
    vcs.worktrees[branch] = ours
    vcs.branches.add(dispatch_core.legacy_dispatch_worktree_branch(_SHARED_FEED_KEY))

    _dispatch(tmp_path, _ATLAS, _SHARED_STORY, vcs=vcs, monkeypatch=monkeypatch)
    payload = json.loads(capsys.readouterr().out)

    assert payload["data"]["branch"] == branch
    assert [f["code"] for f in payload["findings"] if f["code"].startswith("MRS-DISP-03")] == []


class RecordingVcs(FakeVcs):
    """``FakeVcs`` that records every ``is_branch_merged`` question asked."""

    def __init__(self, repo_root: Path) -> None:
        super().__init__(repo_root)
        self.merge_checked: list[str] = []

    def changed_files(self, _repo_root: Path, _worktree: Path, *, base: str):
        return ()

    def is_branch_merged(self, _repo_root: Path, branch: str, *, into: str) -> bool:
        self.merge_checked.append(branch)
        return False

    def commit_subjects(self, _repo_root: Path, _ref: str):
        return ()


def test_every_branch_consumer_agrees_on_the_one_derivation(tmp_path: Path) -> None:
    """Worktree provisioning, the completion supervisor's git facts, and
    landing must all render the SAME branch for the same station+story."""
    from pyforge.marshal.cli.dispatch import _ensure_dispatch_worktree
    from pyforge.marshal.dispatch_supervisor.__main__ import gather_dispatch_git_facts

    expected = dispatch_core.dispatch_worktree_branch(_ATLAS, _SHARED_FEED_KEY)

    # 1. worktree provisioning
    provision_vcs = RecordingVcs(tmp_path)
    provisioned = _ensure_dispatch_worktree(provision_vcs, tmp_path, _ATLAS, _SHARED_FEED_KEY)
    assert provisioned.branch == expected
    assert [b for _r, _h, b, _base in provision_vcs.added] == [expected]

    # 2. the completion supervisor's git facts (feeds the CAP-2 zombie
    #    refusal and the CAP-5 in-flight guard). The branch must EXIST for
    #    the supervisor to ask about it at all -- see the sibling test that
    #    pins the never-ask-about-a-missing-branch rule.
    facts_vcs = RecordingVcs(tmp_path)
    facts_vcs.branches.add(expected)
    gather_dispatch_git_facts(
        facts_vcs,
        fs=FakeFs(),
        repo_root=tmp_path,
        worktree=dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, _SHARED_FEED_KEY),
        story_key=_SHARED_FEED_KEY,
        project_slug=_ATLAS,
        baseline_head_sha="baseline0001",
        merge_subject_template="Story {key}",
    )
    assert facts_vcs.merge_checked == [expected]

    # 3. landing pushes that same branch (covered live by
    #    tests/unit/test_dispatch_landing.py's push assertion)
    land_vcs = RecordingVcs(tmp_path)
    land_vcs.branches.add(expected)
    assert (
        dispatch_core.resolve_dispatch_branch(
            land_vcs, tmp_path, slug=_ATLAS, story_key=_SHARED_FEED_KEY
        ).effective_branch
        == expected
    )


def test_git_facts_never_ask_about_a_branch_the_resolver_did_not_resolve(
    tmp_path: Path,
) -> None:
    """`is_branch_merged` shells `git merge-base --is-ancestor`, which exits
    128 on a missing ref -- `GitVcs` turns that into `VcsCommandError`, the
    supervisor loop swallows it and `continue`s inside `while True`, and the
    run spins forever without ever being judged complete. So when the
    resolver resolved nothing, the question is never asked: a branch that
    does not exist is not merged."""
    from pyforge.marshal.dispatch_supervisor.__main__ import gather_dispatch_git_facts

    # The refusal state: no station-scoped branch, and the legacy branch is
    # checked out at ANOTHER station's worktree.
    vcs = RecordingVcs(tmp_path)
    vcs.worktrees[dispatch_core.legacy_dispatch_worktree_branch(_SHARED_FEED_KEY)] = (
        dispatch_core.dispatch_worktree_path(tmp_path, _DOCTOR, _SHARED_FEED_KEY)
    )
    resolution = dispatch_core.resolve_dispatch_branch(vcs, tmp_path, slug=_ATLAS, story_key=_SHARED_FEED_KEY)
    assert resolution.refusal is not None and resolution.resolved is None

    facts = gather_dispatch_git_facts(
        vcs,
        fs=FakeFs(),
        repo_root=tmp_path,
        worktree=dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, _SHARED_FEED_KEY),
        story_key=_SHARED_FEED_KEY,
        project_slug=_ATLAS,
        baseline_head_sha="baseline0001",
        merge_subject_template="Story {key}",
    )
    assert facts.branch_merged is False
    assert vcs.merge_checked == []

    # Same rule for the plain "no branch exists yet / already retired" case.
    fresh = RecordingVcs(tmp_path)
    fresh_facts = gather_dispatch_git_facts(
        fresh,
        fs=FakeFs(),
        repo_root=tmp_path,
        worktree=dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, _SHARED_FEED_KEY),
        story_key=_SHARED_FEED_KEY,
        project_slug=_ATLAS,
        baseline_head_sha="baseline0001",
        merge_subject_template="Story {key}",
    )
    assert fresh_facts.branch_merged is False
    assert fresh.merge_checked == []


class AlwaysMergedVcs(RecordingVcs):
    """`is_branch_merged` always says yes -- mirrors `git merge-base
    --is-ancestor branch into`'s trivially-true answer the instant a
    dispatch branch is forked from `into`'s current tip, before any real
    commit lands. `worktree_head_sha` is settable so a test can control
    whether the branch has actually diverged from its launch baseline."""

    def __init__(self, repo_root: Path, *, head_sha: str = "baseline0001") -> None:
        super().__init__(repo_root)
        self._head_sha = head_sha

    def is_branch_merged(self, _repo_root: Path, branch: str, *, into: str) -> bool:
        self.merge_checked.append(branch)
        return True

    def worktree_head_sha(self, _worktree: Path) -> str:
        return self._head_sha


def test_branch_merged_ignores_ancestry_when_the_branch_has_not_diverged(
    tmp_path: Path,
) -> None:
    """A freshly-provisioned dispatch branch equals `into`'s own tip, so
    `git merge-base --is-ancestor` trivially answers "yes, merged" before
    the dispatched session has done any work -- confirmed live in
    `journal.jsonl` for three real dispatches (2026-08-28), each recording
    `branch_merged: true` ~2 seconds after launch with `changed_paths: []`
    and `current_head_sha == baseline_head_sha`. `branch_merged` must not
    trust that "yes" until the branch has actually diverged from its own
    launch baseline -- otherwise `dispatch-resume`/`dispatch-attach` can
    never recover a dispatch's supervision for its entire lifetime, since
    `resolve_dispatch_session_verdict` trusts any journaled COMPLETED
    verdict without re-deriving it."""
    from pyforge.marshal.dispatch_supervisor.__main__ import gather_dispatch_git_facts

    branch = dispatch_core.dispatch_worktree_branch(_ATLAS, _SHARED_FEED_KEY)
    vcs = AlwaysMergedVcs(tmp_path, head_sha="baseline0001")
    vcs.branches.add(branch)

    facts = gather_dispatch_git_facts(
        vcs,
        fs=FakeFs(),
        repo_root=tmp_path,
        worktree=dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, _SHARED_FEED_KEY),
        story_key=_SHARED_FEED_KEY,
        project_slug=_ATLAS,
        baseline_head_sha="baseline0001",
        merge_subject_template="Story {key}",
    )

    # the ancestry question still gets asked (existing branch-derivation
    # callers rely on the ask itself)...
    assert vcs.merge_checked == [branch]
    # ...but its "yes" is not trusted with zero real divergence.
    assert facts.branch_merged is False


def test_branch_merged_trusts_ancestry_once_the_branch_has_diverged(
    tmp_path: Path,
) -> None:
    """Once the branch carries real commits past its launch baseline, a
    genuine "merged" ancestry answer is trusted again -- this is not a
    blanket distrust of `is_branch_merged`, only a guard against its
    vacuously-true answer at zero divergence."""
    from pyforge.marshal.dispatch_supervisor.__main__ import gather_dispatch_git_facts

    branch = dispatch_core.dispatch_worktree_branch(_ATLAS, _SHARED_FEED_KEY)
    vcs = AlwaysMergedVcs(tmp_path, head_sha="deadbeef0002")
    vcs.branches.add(branch)

    facts = gather_dispatch_git_facts(
        vcs,
        fs=FakeFs(),
        repo_root=tmp_path,
        worktree=dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, _SHARED_FEED_KEY),
        story_key=_SHARED_FEED_KEY,
        project_slug=_ATLAS,
        baseline_head_sha="baseline0001",
        merge_subject_template="Story {key}",
    )

    assert facts.branch_merged is True


class _SubjectsVcs(RecordingVcs):
    """``RecordingVcs`` whose ``commit_subjects`` returns caller-supplied
    subjects, for exercising ``merged_story_keys``'s templated-shape path
    end to end through ``gather_dispatch_git_facts``."""

    def __init__(self, repo_root: Path, subjects: tuple[str, ...]) -> None:
        super().__init__(repo_root)
        self._subjects = subjects

    def commit_subjects(self, _repo_root: Path, _ref: str):
        return self._subjects


def test_gather_dispatch_git_facts_does_not_leak_another_stations_templated_key(
    tmp_path: Path,
) -> None:
    """Story 35.1 (spec-marshal-templated-merge-subject-cross-project-
    collision CAP-1): reproduces the exact live false-positive class from
    2026-09-11's doctor Epic 22 dispatch -- a bare "Merge {key} into main"
    subject from ANOTHER station (here, marshal's own historical "22.11")
    must not report `story_merged_on_main: True` for atlas's own,
    never-merged "22.11". `_load_known_story_keys` reads atlas's own
    tracked ledger from the fake filesystem; that ledger does not contain
    "22.11", so the templated match is correctly excluded."""
    from pyforge.marshal.dispatch_supervisor.__main__ import gather_dispatch_git_facts

    subjects = ("Merge 22.11 into main",)
    vcs = _SubjectsVcs(tmp_path, subjects)

    ledger_path = tmp_path / "_bmad-output" / "projects" / _ATLAS / "planning-artifacts" / "sprint-status-ledger.yaml"
    fs = FakeFs()
    fs.files[ledger_path] = "development_status:\n  1-1-atlas-owns-story: done\n  epic-1: done\n"

    facts = gather_dispatch_git_facts(
        vcs,
        fs=fs,
        repo_root=tmp_path,
        worktree=dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, "22.11"),
        story_key="22.11",
        project_slug=_ATLAS,
        baseline_head_sha="baseline0001",
        merge_subject_template="Merge {key} into main",
    )

    assert facts.story_merged_on_main is False


def test_gather_dispatch_git_facts_still_recognizes_the_project_own_templated_key(
    tmp_path: Path,
) -> None:
    """The corroboration signal must not become a blanket denial: once
    atlas's own tracked ledger names "22.11" as one of ITS stories, the
    identical templated merge subject IS trusted for atlas."""
    from pyforge.marshal.dispatch_supervisor.__main__ import gather_dispatch_git_facts

    subjects = ("Merge 22.11 into main",)
    vcs = _SubjectsVcs(tmp_path, subjects)

    ledger_path = tmp_path / "_bmad-output" / "projects" / _ATLAS / "planning-artifacts" / "sprint-status-ledger.yaml"
    fs = FakeFs()
    fs.files[ledger_path] = "development_status:\n  22-11-atlas-owns-this-one: done\n"

    facts = gather_dispatch_git_facts(
        vcs,
        fs=fs,
        repo_root=tmp_path,
        worktree=dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, "22.11"),
        story_key="22.11",
        project_slug=_ATLAS,
        baseline_head_sha="baseline0001",
        merge_subject_template="Merge {key} into main",
    )

    assert facts.story_merged_on_main is True


def test_gather_dispatch_git_facts_missing_ledger_fails_closed(
    tmp_path: Path,
) -> None:
    """No ledger on disk (not yet provisioned, or an unrelated read
    failure) must degrade to trusting NOTHING from the templated shape --
    the safe direction, mirroring today's fix rather than reopening the
    original unscoped bug as an error-path fallback."""
    from pyforge.marshal.dispatch_supervisor.__main__ import gather_dispatch_git_facts

    subjects = ("Merge 22.11 into main",)
    vcs = _SubjectsVcs(tmp_path, subjects)
    fs = FakeFs()

    facts = gather_dispatch_git_facts(
        vcs,
        fs=fs,
        repo_root=tmp_path,
        worktree=dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, "22.11"),
        story_key="22.11",
        project_slug=_ATLAS,
        baseline_head_sha="baseline0001",
        merge_subject_template="Merge {key} into main",
    )

    assert facts.story_merged_on_main is False


def test_branch_and_worktree_path_sanitize_the_key_identically(
    tmp_path: Path,
) -> None:
    """Attribution compares a branch-derived decision against a path-derived
    location, so the two must sanitize the story key the same way. Real keys
    render untouched; a key needing sanitization still agrees."""
    for key in ("22.9", "20.2", "12.1"):
        assert dispatch_core.dispatch_worktree_branch(_ATLAS, key) == (f"dispatch/{_ATLAS}/{key}")
        assert dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, key).name == (f"dispatch-{_ATLAS}-{key}")

    dirty = "20.1 rc/1"
    branch = dispatch_core.dispatch_worktree_branch(_ATLAS, dirty)
    worktree = dispatch_core.dispatch_worktree_path(tmp_path, _ATLAS, dirty)
    # One key, one segment on both sides -- no stray path/ref separator.
    assert branch == f"dispatch/{_ATLAS}/20.1-rc-1"
    assert worktree.name == f"dispatch-{_ATLAS}-20.1-rc-1"

    # And the two still agree at the attribution site: a legacy branch
    # checked out at THIS station's (sanitized) worktree path resolves.
    vcs = RecordingVcs(tmp_path)
    legacy = dispatch_core.legacy_dispatch_worktree_branch(dirty)
    vcs.worktrees[legacy] = worktree
    resolution = dispatch_core.resolve_dispatch_branch(vcs, tmp_path, slug=_ATLAS, story_key=dirty)
    assert resolution.refusal is None
    assert resolution.resolved == legacy
    assert resolution.legacy is True


def test_traversal_segments_can_never_escape_the_branch_name() -> None:
    """A slug or key carrying `..` or `/` neither splits the ref into extra
    components nor traverses -- this is now the single security-relevant
    derivation site."""
    assert dispatch_core.dispatch_worktree_branch("..", "..") == "dispatch/project/story"
    # `git check-ref-format` rejects `..` anywhere in a ref, so the dot run
    # collapses rather than surviving inside a segment.
    assert dispatch_core.dispatch_worktree_branch("a/../b", "1.2") == "dispatch/a-.-b/1.2"
    assert dispatch_core.dispatch_worktree_branch(_ATLAS, "") == f"dispatch/{_ATLAS}/story"
    assert dispatch_core.legacy_dispatch_worktree_branch("..") == "marshal/story"
    # ... and no rendered segment ever carries a traversal or a separator.
    for segment in dispatch_core.dispatch_worktree_branch("../x", "../y").split("/"):
        assert ".." not in segment and segment not in (".", "")


def test_only_one_dispatch_branch_derivation_site() -> None:
    """AC-3's guard: fail on a SECOND site that builds a dispatch branch
    string. ``core/dispatch.py`` owns both the station-scoped and the legacy
    spellings; anywhere else must import them."""
    import re

    import pyforge.marshal

    package_file = pyforge.marshal.__file__
    assert package_file is not None
    package_dir = Path(package_file).resolve().parent
    owner = package_dir / "core" / "dispatch.py"

    # Two shapes a second derivation site can take:
    # (a) a quoted literal that OPENS with a branch prefix and interpolates
    #     -- f"dispatch/{slug}...", f"marshal/{key}", "marshal/%s" % key --
    #     but NOT a path such as ".marshal/plan.json", which does not start
    #     with the prefix;
    # (b) referencing a branch-prefix constant and rebuilding the name from
    #     it -- either marshal's own private aliases or `pyforge.core.
    #     landing_evidence.DISPATCH_BRANCH_PREFIX`, which owns the literal
    #     for BOTH packages (marshal mints these branches, pyforge-core's
    #     landing grammar recognizes them).
    derivation = re.compile(
        r"""["'](?:dispatch|marshal)/(?:\{|%s)"""
        r"""|_?(?:LEGACY_)?DISPATCH_BRANCH_PREFIX"""
    )

    offenders = sorted(
        str(path.relative_to(package_dir))
        for path in package_dir.rglob("*.py")
        if path != owner and derivation.search(path.read_text(encoding="utf-8"))
    )
    assert offenders == [], (
        "dispatch branch names must be derived only by "
        f"core/dispatch.py::dispatch_worktree_branch; second site(s) in {offenders}"
    )
    # The guard genuinely fires on every shape it claims to catch, and does
    # not fire on the `.marshal/` state-dir paths that live all over seed/.
    for caught in (
        'f"dispatch/{slug}/{story_key}"',
        'f"marshal/{story_key}"',
        '"marshal/%s" % story_key',
        'f"{_DISPATCH_BRANCH_PREFIX}/{slug}/{key}"',
        "_LEGACY_DISPATCH_BRANCH_PREFIX",
        "from pyforge.core.landing_evidence import DISPATCH_BRANCH_PREFIX",
    ):
        assert derivation.search(caught), caught
    assert derivation.search('".marshal/plan.json"') is None


# --------------------------------------------------------------------------
# Story 22.11: `dispatch <slug> --stories k1,k2,...` chains an explicit
# sequence via the same machinery `drain` uses (FR-193 CAP-10)
# --------------------------------------------------------------------------


class _FakeLedgerHarness:
    """``HarnessPort.ledger_story_statuses`` over an in-memory ledger."""

    def __init__(self, ledgers: dict[str, tuple[tuple[str, str], ...]]) -> None:
        self.ledgers = ledgers

    def ledger_story_statuses(self, path: Path) -> tuple[tuple[str, str], ...]:
        slug = path.parent.parent.name
        return self.ledgers.get(slug, ())


def test_dispatch_refuses_when_neither_story_nor_stories_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import json

    _init_git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    args = argparse.Namespace(slug="pyforge-marshal", story=None, stories=None, format="json")
    code = run_dispatch(
        args, fs=FakeFs(), vcs=FakeVcs(tmp_path), build_harness=FakeBuildHarness(), process=FakeProcess()
    )
    assert code != EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert any(f["code"] == "MRS-DISP-032" for f in payload["findings"])


def test_dispatch_refuses_when_both_story_and_stories_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import json

    _init_git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    args = argparse.Namespace(slug="pyforge-marshal", story="22-11-fleet", stories="22-11-fleet", format="json")
    code = run_dispatch(
        args, fs=FakeFs(), vcs=FakeVcs(tmp_path), build_harness=FakeBuildHarness(), process=FakeProcess()
    )
    assert code != EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert any(f["code"] == "MRS-DISP-032" for f in payload["findings"])


def test_dispatch_stories_dispatches_the_first_key_in_the_given_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`dispatch <slug> --stories a,b` reuses `run_fleet_drain`'s own
    chaining/preflight/journal machinery -- no second implementation."""
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    _seed_spec(tmp_path, slug, "22-11-fleet")
    _seed_spec(tmp_path, slug, "22-12-next")
    monkeypatch.chdir(tmp_path)
    harness = _FakeLedgerHarness({slug: (("22-11-fleet", "backlog"), ("22-12-next", "backlog"))})
    build_harness = FakeBuildHarness()
    args = argparse.Namespace(
        slug=slug,
        story=None,
        stories="22-12-next,22-11-fleet",
        format="json",
        max_in_flight=1,
    )
    code = run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=build_harness,
        process=FakeProcess(),
        harness=harness,
    )
    assert code == EXIT_OK
    assert build_harness.calls
    assert build_harness.calls[0]["story_key"] == "22.12"


def test_dispatch_stories_refuses_an_unknown_key_before_any_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import json

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    _seed_spec(tmp_path, slug, "22-11-fleet")
    monkeypatch.chdir(tmp_path)
    harness = _FakeLedgerHarness({slug: (("22-11-fleet", "backlog"),)})
    vcs = FakeVcs(tmp_path)
    build_harness = FakeBuildHarness()
    args = argparse.Namespace(slug=slug, story=None, stories="22-11-fleet,99-9-ghost", format="json")
    code = run_dispatch(args, fs=FakeFs(), vcs=vcs, build_harness=build_harness, process=FakeProcess(), harness=harness)
    assert code != EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert any(f["code"] == "MRS-DISP-032" for f in payload["findings"])
    # Nothing was provisioned: no worktree add, no session launch.
    assert vcs.added == []
    assert build_harness.calls == []


_DONE_SPEC = "---\nstatus: done\nfollowup_review_recommended: false\ndifficulty: medium\n---\n# spec\n"
_READY_SPEC = "---\nstatus: ready-for-dev\ndifficulty: medium\n---\n# spec\n"


def _write_worktree_spec(repo: Path, slug: str, story: str, text: str) -> Path:
    from pyforge.marshal.core.identity import normalize, render_feed_key

    specs = dispatch_core.planning_specs_dir(repo, slug)
    specs.mkdir(parents=True, exist_ok=True)
    spec = specs / f"spec-{story}.md"
    spec.write_text(_READY_SPEC, encoding="utf-8")
    feed = render_feed_key(normalize(story))
    worktree = dispatch_core.dispatch_worktree_path(repo, slug, feed)
    dest = worktree / spec.relative_to(repo)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return worktree


def test_done_spec_does_not_launch_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 29.2: worktree spec done + follow-up false → 0 harness launches."""
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "13-2-recipe-refresh"
    worktree = _write_worktree_spec(tmp_path, slug, story, _DONE_SPEC)
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=harness,
        process=FakeProcess(),
    )
    assert harness.calls == []
    assert attempt.data.get("session_pid") is None
    codes = [f.code for f in attempt.findings]
    assert "MRS-DISP-040" in codes
    assert any("awaiting-operator" in f.message for f in attempt.findings)
    assert any(str(worktree) in f.message for f in attempt.findings)


_BLOCKED_SPEC = (
    '---\nstatus: blocked\nblocking_condition: "awaiting operator review"\ndifficulty: medium\n---\n# spec\n'
)


def test_blocked_spec_does_not_relaunch_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 51.4: worktree spec status: blocked -> MRS-DISP-045, 0 launches, no CAP-4 land attempt."""
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "13-2-recipe-refresh"
    _write_worktree_spec(tmp_path, slug, story, _BLOCKED_SPEC)
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=harness,
        process=FakeProcess(),
    )
    assert harness.calls == []
    assert attempt.data.get("harness_blocked_no_relaunch") is True
    assert attempt.data.get("land_verdict") is None
    codes = [f.code for f in attempt.findings]
    assert "MRS-DISP-045" in codes
    [finding] = [f for f in attempt.findings if f.code == "MRS-DISP-045"]
    assert "status: blocked" in finding.message
    assert "awaiting operator review" in finding.message


def test_dirty_pr_land_fail_names_pr_and_does_not_relaunch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """41.2-shaped: DIRTY PR → MRS-DISP-040 names the PR, launch count 0."""
    from pyforge.marshal.cli import dispatch as dispatch_module

    slug = "pyforge-steward"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "41-2-query-plane"
    _write_worktree_spec(tmp_path, slug, story, _DONE_SPEC)
    pr_url = "https://github.com/rxm7706/local-recipes/pull/1017"
    monkeypatch.setattr(
        dispatch_module,
        "_attempt_harness_done_cap4",
        lambda **_kwargs: (DispatchLandingVerdict.REFUSED, pr_url, None),
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=harness,
        process=FakeProcess(),
    )
    assert harness.calls == []
    [finding] = [f for f in attempt.findings if f.code == "MRS-DISP-040"]
    assert "1017" in finding.message
    assert "CHAIN" in finding.message


def test_harness_done_lands_via_cap4_without_second_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When CAP-4 can land, no second session and no MRS-DISP-040."""
    from pyforge.marshal.cli import dispatch as dispatch_module

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "29-2-cap4-only"
    _write_worktree_spec(tmp_path, slug, story, _DONE_SPEC)
    monkeypatch.setattr(
        dispatch_module,
        "_attempt_harness_done_cap4",
        lambda **_kwargs: (DispatchLandingVerdict.LANDED, "PR #9", None),
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=harness,
        process=FakeProcess(),
    )
    assert harness.calls == []
    assert attempt.data["land_verdict"] == "landed"
    assert all(f.code != "MRS-DISP-040" for f in attempt.findings)


def test_followup_true_still_launches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "29-1-followup"
    followup = "---\nstatus: done\nfollowup_review_recommended: true\ndifficulty: medium\n---\n# spec\n"
    _write_worktree_spec(tmp_path, slug, story, followup)
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=harness,
        process=FakeProcess(),
    )
    assert harness.calls


def test_relocated_spec_path_maps_primary_tree_onto_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    wt = tmp_path / "wt"
    rel = Path("_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-42-5.md")
    (repo / rel).parent.mkdir(parents=True)
    (wt / rel).parent.mkdir(parents=True)
    (repo / rel).write_text("primary\n", encoding="utf-8")
    (wt / rel).write_text("worktree\n", encoding="utf-8")
    relocated = dispatch_core.relocated_spec_path(repo / rel, repo, wt)
    assert relocated == (wt / rel).resolve()
    assert relocated.read_text(encoding="utf-8") == "worktree\n"


def test_relocated_spec_path_keeps_already_worktree_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    wt = tmp_path / "wt"
    rel = Path("specs/spec.md")
    (wt / rel).parent.mkdir(parents=True)
    target = wt / rel
    target.write_text("ok\n", encoding="utf-8")
    assert dispatch_core.relocated_spec_path(target, repo, wt) == target.resolve()


def test_relocated_spec_path_rejects_unrelated_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="neither under worktree"):
        dispatch_core.relocated_spec_path(
            tmp_path / "other" / "spec.md",
            tmp_path / "repo",
            tmp_path / "wt",
        )


# --- Story 33.6: dispatch retry floor-raise (spec-adaptive-model-tiering CAP-2) ---


def test_dispatch_escalates_model_after_prior_failed_attempts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Prior failed runs >= max_dev_attempts floor-raise dev -> review on launch."""
    import json

    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.cli.dispatch import _count_prior_failed_dispatch_attempts
    from pyforge.marshal.core import policy
    from pyforge.marshal.core.dispatch_completion import DispatchSessionVerdict
    from pyforge.marshal.core.identity import normalize, render_feed_key
    from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write

    def _seed_failed_run(run_id: str) -> None:
        run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        intent = prepare_for_write(
            build_entry(
                id=JournalEntryId("w", 0),
                ts="2026-09-01T00:00:00.000Z",
                run_id=run_id,
                kind=dispatch_core.KIND_DISPATCH_LAUNCH,
                phase=Phase.INTENT,
                payload={"story_key": feed},
            )
        ).line
        completion_intent = prepare_for_write(
            build_entry(
                id=JournalEntryId("w", 2),
                ts="2026-09-01T00:01:00.000Z",
                run_id=run_id,
                kind=dispatch_core.KIND_DISPATCH_COMPLETION,
                phase=Phase.INTENT,
                payload={"verdict": DispatchSessionVerdict.FAILED.value},
            )
        ).line
        completion_outcome = prepare_for_write(
            build_entry(
                id=JournalEntryId("w", 3),
                ts="2026-09-01T00:01:01.000Z",
                run_id=run_id,
                kind=dispatch_core.KIND_DISPATCH_COMPLETION,
                phase=Phase.OUTCOME,
                intent_id=JournalEntryId("w", 2),
                payload={"verdict": DispatchSessionVerdict.FAILED.value, "ok": True},
            )
        ).line
        (run_dir / "journal.jsonl").write_text(
            intent + "\n" + completion_intent + "\n" + completion_outcome + "\n",
            encoding="utf-8",
        )

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "33-6-adaptive-tiering"
    feed = render_feed_key(normalize(story))
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"spec-{story}.md").write_text(_READY_SPEC, encoding="utf-8")

    effective, _ = policy.compose(
        project_slug=slug,
        project={
            "model_tier_map": {
                # Story 51.5 (CAP-253): claude's own default/alias ids --
                # any OTHER string here now trips the widened MRS-DISP-043
                # uncatalogued-model guard, which this fixture (adaptive
                # tiering escalation, unrelated to model-provider matching)
                # has no catalog declared to satisfy.
                "medium": {"dev": "sonnet", "review": "opus"},
            }
        },
        flags={"max_dev_attempts": 2},
    )
    monkeypatch.setattr(
        dispatch_module,
        "_compose_policy",
        lambda _slug, flags=None: effective,
    )

    for run_id in ("run-fail-1", "run-fail-2"):
        _seed_failed_run(run_id)

    class JournalFs(FakeFs):
        def read_text(self, path: Path) -> str | None:
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                return self.files.get(path)

    fs = JournalFs()
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=fs,
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert _count_prior_failed_dispatch_attempts(fs, tmp_path, slug, feed) == 2
    assert attempt.data.get("escalated") is True
    assert attempt.data.get("from_model") == "sonnet"
    assert attempt.data.get("to_model") == "opus"
    assert attempt.data.get("model") == "opus"
    assert not [f for f in attempt.findings if f.code == "MRS-DISP-043"]
    launch_lines = [line for _, line, _ in fs.appended if "dispatch-launch" in line]
    intent = json.loads(launch_lines[0])
    assert intent["payload"]["escalated"] is True
    assert intent["payload"]["from_model"] == "sonnet"
    assert intent["payload"]["to_model"] == "opus"
    assert attempt.data.get("session_pid") == 4242


def test_dispatch_does_not_escalate_on_first_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 33.6: zero prior failures keeps the base dev model."""
    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.core import policy

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "33-6-first-attempt"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"spec-{story}.md").write_text(_READY_SPEC, encoding="utf-8")

    effective, _ = policy.compose(
        project_slug=slug,
        project={
            "model_tier_map": {
                # Story 51.5 (CAP-253): see the sibling escalation test --
                # claude's own default/alias ids avoid tripping the widened
                # MRS-DISP-043 uncatalogued-model guard.
                "medium": {"dev": "sonnet", "review": "opus"},
            }
        },
        flags={"max_dev_attempts": 2},
    )
    monkeypatch.setattr(
        dispatch_module,
        "_compose_policy",
        lambda _slug, flags=None: effective,
    )
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert attempt.data.get("model") == "sonnet"
    assert "escalated" not in attempt.data
    assert not [f for f in attempt.findings if f.code == "MRS-DISP-043"]


def test_dispatch_drops_a_tier_mapped_model_catalogued_under_a_different_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """2026-09-12 (dispatch-tier-routing-fails-safe): the dispatch engine's
    own counterpart to render_policy_toml's provider-mismatch guard on the
    spin engine. `dev = "composer-2.5-fast"` carries no explicit harness,
    so it was resolved BEFORE the live binary+authcheck walk below ran --
    when the declared cost catalog says that model belongs to `cursor` but
    the walk (here `FakeBuildHarness`, which always lands on the first
    `harness_preference` entry, `claude`) resolves a DIFFERENT provider,
    the model override must be dropped rather than launch `claude` with a
    model it was never meant to receive. MRS-DISP-043 records why."""
    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.core import policy

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "33-6-cross-provider-mismatch"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"spec-{story}.md").write_text(_READY_SPEC, encoding="utf-8")

    effective, _ = policy.compose(
        project_slug=slug,
        project={
            "model_tier_map": {
                "medium": {"dev": "composer-2.5-fast"},
            },
            "model_cost_catalog": {
                "providers": {
                    "cursor": {
                        "models": {
                            "composer-2.5-fast": {
                                "input_per_million": 3.0,
                                "output_per_million": 15.0,
                            },
                        },
                    },
                },
            },
        },
        flags={},
    )
    monkeypatch.setattr(
        dispatch_module,
        "_compose_policy",
        lambda _slug, flags=None: effective,
    )
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert attempt.data.get("harness_profile") == "claude"
    assert attempt.data.get("model") is None
    assert "escalated" not in attempt.data
    assert "resolved_models" not in attempt.data or "dev" not in attempt.data["resolved_models"]
    mismatch_findings = [f for f in attempt.findings if f.code == "MRS-DISP-043"]
    assert len(mismatch_findings) == 1
    assert mismatch_findings[0].severity is Severity.WARN


def test_dispatch_drops_a_tier_mapped_model_catalogued_under_no_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 51.5 (CAP-253): `provider_declaring_model` returns `None` both
    for a genuinely uncatalogued/foreign model id AND, by documented design,
    for a harness's own default/alias id (`sonnet`/`opus`/`haiku`) -- the
    catalog is a declared PRICE snapshot, not a model registry. The ORIGINAL
    guard only fired on a cross-provider mismatch, so a plainly foreign or
    mistyped model id (here `gpt-9-turbo-nonexistent`, declared by no
    provider and not one of marshal's own tier ids) silently reached launch
    unchanged. A `model_cost_catalog` IS declared here (for an unrelated
    model) so this exercises "catalogued under no provider despite a
    declared catalog" specifically -- not the no-catalog-at-all case, which
    must stay silent (see the sibling test below). It must now raise
    MRS-DISP-043 and have its override dropped, exactly like the
    cross-provider case above -- before any live launch."""
    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.core import policy

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "51-5-uncatalogued-model"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"spec-{story}.md").write_text(_READY_SPEC, encoding="utf-8")

    effective, _ = policy.compose(
        project_slug=slug,
        project={
            "model_tier_map": {
                "medium": {"dev": "gpt-9-turbo-nonexistent"},
            },
            "model_cost_catalog": {
                "providers": {
                    "anthropic": {
                        "models": {
                            "claude-opus-4": {
                                "input_per_million": 15.0,
                                "output_per_million": 75.0,
                            },
                        },
                    },
                },
            },
        },
        flags={},
    )
    monkeypatch.setattr(
        dispatch_module,
        "_compose_policy",
        lambda _slug, flags=None: effective,
    )
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert attempt.data.get("harness_profile") == "claude"
    assert attempt.data.get("model") is None
    assert "escalated" not in attempt.data
    assert "resolved_models" not in attempt.data or "dev" not in attempt.data["resolved_models"]
    uncatalogued_findings = [f for f in attempt.findings if f.code == "MRS-DISP-043"]
    assert len(uncatalogued_findings) == 1
    assert uncatalogued_findings[0].severity is Severity.WARN
    assert "gpt-9-turbo-nonexistent" in uncatalogued_findings[0].message
    assert "no known provider" in uncatalogued_findings[0].message
    assert "declared cost catalog" in uncatalogued_findings[0].message


def test_dispatch_tier_mapped_model_with_no_declared_catalog_at_all_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 51.5 (CAP-253) regression: most real stations (cursor-only
    `harness_preference`, no `model_cost_catalog` block at all -- the shape
    every one of pyforge-atlas/-mason/-scribe/-warden's real
    `marshal-policy.toml` uses) never declare a catalog. `catalog_declared`
    is `False` there, so `provider_declaring_model` returns `None` for
    EVERY model, correctly-matched ones included. A correctly tier-mapped,
    correctly resolved cursor model must NOT be flagged uncatalogued or
    have its override dropped in that shape -- there is nothing to compare
    against when no catalog was ever declared."""
    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.core import policy

    slug = "pyforge-atlas"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "51-5-no-catalog-preserved"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"spec-{story}.md").write_text(_READY_SPEC, encoding="utf-8")

    effective, _ = policy.compose(
        project_slug=slug,
        project={
            "harness_preference": ["cursor"],
            "model_tier_map": {
                "medium": {"dev": {"harness": "cursor", "model": "composer-2.5-fast"}},
            },
        },
        flags={},
    )
    monkeypatch.setattr(
        dispatch_module,
        "_compose_policy",
        lambda _slug, flags=None: effective,
    )
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert attempt.data.get("harness_profile") == "cursor"
    assert attempt.data.get("model") == "composer-2.5-fast"
    assert not [f for f in attempt.findings if f.code == "MRS-DISP-043"]


def test_dispatch_tier_mapped_sonnet_on_claude_is_byte_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 51.5 (CAP-253): the widened MRS-DISP-043 guard must not flag a
    harness's own default/alias model id. `sonnet` on `claude` (the
    `FakeBuildHarness` default) is never catalogued by design -- it must
    stay byte-identical to pre-fix behavior: no MRS-DISP-043 finding at
    all, and the model override survives unchanged."""
    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.core import policy

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "51-5-sonnet-byte-identical"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"spec-{story}.md").write_text(_READY_SPEC, encoding="utf-8")

    effective, _ = policy.compose(
        project_slug=slug,
        project={
            "model_tier_map": {
                "medium": {"dev": "sonnet"},
            },
        },
        flags={},
    )
    monkeypatch.setattr(
        dispatch_module,
        "_compose_policy",
        lambda _slug, flags=None: effective,
    )
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert attempt.data.get("harness_profile") == "claude"
    assert attempt.data.get("model") == "sonnet"
    assert not [f for f in attempt.findings if f.code == "MRS-DISP-043"]


def test_dispatch_tier_mapped_haiku_on_claude_is_byte_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 51.5 (CAP-253): `haiku` is the third member of
    `HARNESS_DEFAULT_MODEL_IDS` alongside `sonnet`/`opus` -- exercised here
    the same way the sonnet case above is, so the widened guard's silence
    on all three harness-default ids is actually verified, not just
    asserted in a docstring."""
    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.core import policy

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "51-5-haiku-byte-identical"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"spec-{story}.md").write_text(_READY_SPEC, encoding="utf-8")

    effective, _ = policy.compose(
        project_slug=slug,
        project={
            "model_tier_map": {
                "medium": {"dev": "haiku"},
            },
        },
        flags={},
    )
    monkeypatch.setattr(
        dispatch_module,
        "_compose_policy",
        lambda _slug, flags=None: effective,
    )
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert attempt.data.get("harness_profile") == "claude"
    assert attempt.data.get("model") == "haiku"
    assert not [f for f in attempt.findings if f.code == "MRS-DISP-043"]


def test_dispatch_explicit_harness_flag_outranks_tier_map_harness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 50.3 (CAP-246): the 2026-09-18 incident. herald's tier map names
    an inline `{harness = "cursor", model = "grok-4.6"}` dev entry; an
    EXPLICIT `--harness claude` must still win the walk -- Story 28.11's
    tier-map-leads rule may not override a flag the operator actually typed.
    The tier map names no model for `claude`, so the pre-existing
    MRS-DISP-043 fails-safe (2026-09-12) fires and drops the override
    (never a foreign `grok-4.6` handed to the `claude` CLI) -- but it must
    ALSO clear the LOCAL `model` used by the intent journal entry and the
    live `build_harness.dispatch(model=..., ...)` call, not just the
    envelope's `data["model"]`, or the drop is cosmetic and the launch still
    ships the foreign model id."""
    import json

    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.core import policy

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "50-3-explicit-harness-flag"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"spec-{story}.md").write_text(_READY_SPEC, encoding="utf-8")

    effective, _ = policy.compose(
        project_slug=slug,
        project={
            "model_tier_map": {
                "medium": {"dev": {"harness": "cursor", "model": "grok-4.6"}},
            },
            "model_cost_catalog": {
                "providers": {
                    "cursor": {
                        "models": {
                            "grok-4.6": {
                                "input_per_million": 3.0,
                                "output_per_million": 15.0,
                            },
                        },
                    },
                },
            },
        },
        flags={"harness_preference": ("claude",)},
    )
    assert effective.harness_preference.layer is policy.PolicyLayer.FLAG
    monkeypatch.setattr(
        dispatch_module,
        "_compose_policy",
        lambda _slug, flags=None: effective,
    )
    monkeypatch.chdir(tmp_path)
    build_harness = FakeBuildHarness()
    fs = FakeFs()
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=fs,
        vcs=FakeVcs(tmp_path),
        build_harness=build_harness,
        process=FakeProcess(),
    )
    assert attempt.data.get("harness_profile") == "claude"
    # The walk itself never let cursor lead: `--harness claude` alone was
    # handed to `binary_present`, unchanged by the tier map's cursor entry.
    assert build_harness.preference_seen == ("claude",)
    assert attempt.data.get("model") is None
    mismatch_findings = [f for f in attempt.findings if f.code == "MRS-DISP-043"]
    assert len(mismatch_findings) == 1
    assert mismatch_findings[0].severity is Severity.WARN
    # The live launch call -- not just the envelope -- must never receive
    # the foreign `grok-4.6` model id.
    assert build_harness.calls[-1]["model"] is None
    # The entry actually PERSISTED to the journal must be equally clean --
    # not just the in-memory `attempt.data` envelope -- or the drop is
    # cosmetic in exactly the disk-durable record an operator would read.
    launch_lines = [line for _, line, _ in fs.appended if "dispatch-launch" in line]
    assert launch_lines
    journaled_payload = json.loads(launch_lines[0])["payload"]
    assert journaled_payload.get("model") is None
    assert "escalated" not in journaled_payload
    assert "from_model" not in journaled_payload
    assert "to_model" not in journaled_payload


def test_dispatch_tier_map_leads_without_an_explicit_harness_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 50.3 (CAP-246): the flip side -- with no `--harness` flag at
    all, resolution stays byte-identical to Story 28.11's existing
    behavior: the tier map's declared harness still leads the walk, and its
    matching model still applies cleanly."""
    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.core import policy

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "50-3-tier-map-still-leads"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"spec-{story}.md").write_text(_READY_SPEC, encoding="utf-8")

    effective, _ = policy.compose(
        project_slug=slug,
        project={
            "model_tier_map": {
                "medium": {"dev": {"harness": "cursor", "model": "grok-4.6"}},
            },
            "model_cost_catalog": {
                "providers": {
                    "cursor": {
                        "models": {
                            "grok-4.6": {
                                "input_per_million": 3.0,
                                "output_per_million": 15.0,
                            },
                        },
                    },
                },
            },
        },
        flags={},
    )
    assert effective.harness_preference.layer is not policy.PolicyLayer.FLAG
    monkeypatch.setattr(
        dispatch_module,
        "_compose_policy",
        lambda _slug, flags=None: effective,
    )
    monkeypatch.chdir(tmp_path)
    build_harness = FakeBuildHarness()
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=build_harness,
        process=FakeProcess(),
    )
    assert attempt.data.get("harness_profile") == "cursor"
    assert build_harness.preference_seen is not None
    assert build_harness.preference_seen[0] == "cursor"
    assert attempt.data.get("model") == "grok-4.6"
    assert not [f for f in attempt.findings if f.code == "MRS-DISP-043"]
    assert build_harness.calls[-1]["model"] == "grok-4.6"


def test_dispatch_failure_count_resets_after_completed_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 33.6: a COMPLETED dispatch breaks the prior-failure streak."""
    from pyforge.marshal.cli import dispatch as dispatch_module
    from pyforge.marshal.cli.dispatch import _count_prior_failed_dispatch_attempts
    from pyforge.marshal.core import policy
    from pyforge.marshal.core.dispatch_completion import DispatchSessionVerdict
    from pyforge.marshal.core.identity import normalize, render_feed_key
    from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write

    def _seed_run(run_id: str, verdict: DispatchSessionVerdict) -> None:
        run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        intent = prepare_for_write(
            build_entry(
                id=JournalEntryId("w", 0),
                ts="2026-09-01T00:00:00.000Z",
                run_id=run_id,
                kind=dispatch_core.KIND_DISPATCH_LAUNCH,
                phase=Phase.INTENT,
                payload={"story_key": feed},
            )
        ).line
        completion_intent = prepare_for_write(
            build_entry(
                id=JournalEntryId("w", 2),
                ts="2026-09-01T00:01:00.000Z",
                run_id=run_id,
                kind=dispatch_core.KIND_DISPATCH_COMPLETION,
                phase=Phase.INTENT,
                payload={"verdict": verdict.value},
            )
        ).line
        completion_outcome = prepare_for_write(
            build_entry(
                id=JournalEntryId("w", 3),
                ts="2026-09-01T00:01:01.000Z",
                run_id=run_id,
                kind=dispatch_core.KIND_DISPATCH_COMPLETION,
                phase=Phase.OUTCOME,
                intent_id=JournalEntryId("w", 2),
                payload={"verdict": verdict.value, "ok": True},
            )
        ).line
        (run_dir / "journal.jsonl").write_text(
            intent + "\n" + completion_intent + "\n" + completion_outcome + "\n",
            encoding="utf-8",
        )

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "33-6-reset-after-complete"
    feed = render_feed_key(normalize(story))
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True, exist_ok=True)
    (specs / f"spec-{story}.md").write_text(_READY_SPEC, encoding="utf-8")

    _seed_run("run-1-fail", DispatchSessionVerdict.FAILED)
    _seed_run("run-2-complete", DispatchSessionVerdict.COMPLETED)
    _seed_run("run-3-fail", DispatchSessionVerdict.FAILED)

    effective, _ = policy.compose(
        project_slug=slug,
        project={
            "model_tier_map": {
                # Story 51.5 (CAP-253): see the sibling escalation tests --
                # claude's own default/alias ids avoid tripping the widened
                # MRS-DISP-043 uncatalogued-model guard.
                "medium": {"dev": "sonnet", "review": "opus"},
            }
        },
        flags={"max_dev_attempts": 2},
    )
    monkeypatch.setattr(
        dispatch_module,
        "_compose_policy",
        lambda _slug, flags=None: effective,
    )

    class JournalFs(FakeFs):
        def read_text(self, path: Path) -> str | None:
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                return self.files.get(path)

    fs = JournalFs()
    assert _count_prior_failed_dispatch_attempts(fs, tmp_path, slug, feed) == 1

    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=fs,
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    assert attempt.data.get("model") == "sonnet"
    assert "escalated" not in attempt.data
    assert not [f for f in attempt.findings if f.code == "MRS-DISP-043"]


def test_resolve_max_parallel_ignores_seed_max_parallel() -> None:
    """Story 33.8: factory cap reads dispatch only, not scm max_parallel."""
    effective, _ = policy.compose(
        project_slug="acme",
        project={"max_parallel": 4},
        flags={},
    )
    assert effective.seed_view()["max_parallel"].value == 4
    assert resolve_max_parallel(effective) == 1


def test_resolve_max_parallel_cli_override_wins() -> None:
    effective, _ = policy.compose(
        project_slug="acme",
        project={"dispatch": {"max_parallel": 1}},
        flags={},
    )
    assert resolve_max_parallel(effective, cli_override=2) == 2


# --------------------------------------------------------------------------
# Story 33.9: verify_scope at factory dispatch
# --------------------------------------------------------------------------


def test_dispatch_refuses_triangle_drift_before_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    point_scope_triangle(tmp_path, "pyforge-steward")
    os.environ["BMAD_ACTIVE_PROJECT"] = slug
    story = "33-9-scope-guard"
    _seed_spec(tmp_path, slug, story)
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    [finding] = [f for f in attempt.findings if f.code == "MRS-DISP-041"]
    assert "expected 'pyforge-marshal'" in finding.message
    assert "marker='pyforge-steward'" in finding.message


def test_dispatch_refuses_bmad_active_project_env_disagreement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    os.environ["BMAD_ACTIVE_PROJECT"] = "pyforge-atlas"
    story = "33-9-env-guard"
    _seed_spec(tmp_path, slug, story)
    monkeypatch.chdir(tmp_path)
    attempt = dispatch_once(
        slug=slug,
        story=story,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(),
    )
    [finding] = [f for f in attempt.findings if f.code == "MRS-DISP-041"]
    assert "pyforge-marshal" in finding.message
    assert "pyforge-atlas" in finding.message


def test_format_scope_drift_matches_bmad_switch_shape() -> None:
    from pyforge.marshal.scope import ScopeDrift, format_scope_drift

    drift = ScopeDrift(
        expected="project-a",
        marker="project-b",
        planning_artifacts="project-b",
        implementation_artifacts="project-b",
    )
    text = format_scope_drift(drift)
    assert text.startswith("scope drift:")
    assert "expected 'project-a'" in text
    assert "marker='project-b'" in text
