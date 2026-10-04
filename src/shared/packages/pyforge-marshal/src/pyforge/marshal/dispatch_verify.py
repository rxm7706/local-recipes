"""Independent dispatch verification via Epic 2 gate objects (Story 22.3).

Impure edge for the dispatch supervisor: runs verify commands and scope
checks against a dispatch worktree. Session self-reports are never verdict
inputs. Lives outside ``cli/`` so ``dispatch_supervisor`` may import it
(AD-9).
"""

from __future__ import annotations

import importlib.util
import os
import shlex
import signal
import sys
import time
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pyforge.core.flags import FlagConfigError, read_boolean
from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from .adapters.harness_bmadloop import _SURFACE_RECONCILE_COMMAND
from .adapters.vcs_git import VcsCommandError
from .core import dispatch as dispatch_core
from .core import gate, journal, policy, spec_binding
from .core.commit_vcs import CommittingVcs
from .core.dispatch_ruff_format import (
    DispatchRuffFormatResult,
    apply_dispatch_ruff_format_before_verify,
)
from .core.dispatch_verification import (
    BranchCommitAttribution,
    findings_for_commit_attribution_violations,
    reclassify_pre_existing_gate_findings,
)
from .core.dispatch_verify_fix import VERIFY_FIX_LOOP_FLAG_KEY
from .core.egress import to_redacted_text
from .core.identity import StoryKey, render_feed_key
from .core.model import Envelope, Finding, Severity, Status, build_envelope, status_for
from .core.policy import EffectivePolicy
from .core.refs import ORIGIN_MAIN
from .core.spec_surface import SurfaceParseError, parse_declared_surface
from .core.verdict import compute_verdict
from .ports.vcs import VcsPort

_SCOPE_BASE = ORIGIN_MAIN  # Story 60.1 (CAP-270): the full refname, never a short name a local ref can shadow
_SHELL_METACHARACTERS = frozenset("&|<>;()")
_COMMIT_LOG_FIELD_SEP = "\x1f"
_COMMIT_LOG_RECORD_SEP = "\x1e"
_COMMIT_MSG_HOOK_CACHE: dict[tuple[Path, Path | None], object] = {}


def _load_commit_msg_hook_module(worktree: Path, *, repo_root: Path | None = None) -> object | None:
    """Load ``scripts/commit_msg_hook.py`` from ``worktree`` (Story 83.17).

    Reuses the hook module's ``offending_lines`` so dispatch verification and
    the ``commit-msg`` hook can never drift on what counts as attribution."""
    cache_key = (worktree, repo_root)
    cached = _COMMIT_MSG_HOOK_CACHE.get(cache_key)
    if cached is not None:
        return cached
    script: Path | None = None
    for root in (worktree, repo_root):
        if root is None:
            continue
        candidate = root / "scripts" / "commit_msg_hook.py"
        if candidate.is_file():
            script = candidate
            break
    if script is None:
        return None
    spec = importlib.util.spec_from_file_location(
        f"_dispatch_verify_commit_msg_hook_{script}",
        script,
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _COMMIT_MSG_HOOK_CACHE[cache_key] = module
    return module


def _parse_branch_commits_from_log(stdout: str) -> tuple[tuple[str, str, str], ...]:
    """Parse ``git log --format=%H%x1f%s%x1f%B%x1e`` output into commit tuples."""
    if not stdout:
        return ()
    records: list[tuple[str, str, str]] = []
    for chunk in stdout.split(_COMMIT_LOG_RECORD_SEP):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        parts = chunk.split(_COMMIT_LOG_FIELD_SEP, 2)
        if len(parts) != 3:
            continue
        sha, subject, body = parts
        if sha:
            records.append((sha, subject, body))
    return tuple(records)


def check_branch_commit_attribution(
    *,
    worktree: Path,
    process: ProcessPort,
    repo_root: Path | None = None,
    base: str = _SCOPE_BASE,
) -> tuple[tuple[Finding, ...], dict[str, object]]:
    """Story 83.17: refuse when any commit on ``base...HEAD`` carries attribution."""
    hook = _load_commit_msg_hook_module(worktree, repo_root=repo_root)
    if hook is None:
        return (
            (
                Finding(
                    code="MRS-GATE-009",
                    severity=Severity.ERROR,
                    message=(
                        "dispatch commit-attribution check could not load "
                        "scripts/commit_msg_hook.py from the worktree"
                    ),
                ),
            ),
            {"checked": False, "reason": "commit_msg_hook.py missing"},
        )
    rev_range = f"{base}...HEAD"
    try:
        result = process.run(
            [
                "git",
                "-C",
                str(worktree),
                "log",
                rev_range,
                f"--format=%H{_COMMIT_LOG_FIELD_SEP}%s{_COMMIT_LOG_FIELD_SEP}%B{_COMMIT_LOG_RECORD_SEP}",
            ],
            cwd=worktree,
        )
    except ProcessError as exc:
        return (
            (
                Finding(
                    code="MRS-GATE-009",
                    severity=Severity.ERROR,
                    message=f"dispatch commit-attribution check could not read {rev_range!r}: {exc}",
                ),
            ),
            {"checked": False, "reason": str(exc), "rev_range": rev_range},
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return (
            (
                Finding(
                    code="MRS-GATE-009",
                    severity=Severity.ERROR,
                    message=(
                        f"dispatch commit-attribution check could not read {rev_range!r} "
                        f"(exit {result.returncode}): {detail}"
                    ),
                ),
            ),
            {"checked": False, "reason": detail, "rev_range": rev_range},
        )
    offending: list[BranchCommitAttribution] = []
    for sha, subject, body in _parse_branch_commits_from_log(result.stdout):
        hits = hook.offending_lines(body)
        if hits:
            offending.append((sha, subject, tuple(hits)))
    findings = findings_for_commit_attribution_violations(tuple(offending))
    return (
        findings,
        {
            "checked": True,
            "rev_range": rev_range,
            "commits_scanned": len(_parse_branch_commits_from_log(result.stdout)),
            "violations": len(findings),
        },
    )


def _run_verify_command(
    command: str,
    *,
    process: ProcessPort,
    worktree: Path,
    failure_prefix: str = "verify command",
) -> tuple[dict[str, object], Finding | None]:
    """Run one tokenized verify command and classify its outcome."""
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return gate.classify_outcome(
            command,
            None,
            failure_code="MRS-GATE-003",
            failure_reason=f"cannot parse {failure_prefix} {command!r}: {exc}",
        )
    shell_chars = _bare_shell_metacharacters(command)
    if shell_chars:
        return gate.classify_outcome(
            command,
            None,
            failure_code="MRS-GATE-003",
            failure_reason=(
                f"{failure_prefix} {command!r} uses shell syntax "
                f"({', '.join(repr(c) for c in shell_chars)}) "
                "but verify commands are never run through a shell"
            ),
        )
    try:
        result = process.run(tokens, cwd=worktree)
    except ProcessError as exc:
        return gate.classify_outcome(
            command,
            None,
            failure_code="MRS-GATE-002",
            failure_reason=f"{failure_prefix} {command!r} could not be run: {exc}",
        )
    return gate.classify_outcome(command, result)


def _bare_shell_metacharacters(command: str) -> list[str]:
    found: list[str] = []
    in_single = False
    in_double = False
    escaped = False
    for char in command:
        if escaped:
            escaped = False
            continue
        if in_single:
            if char == "'":
                in_single = False
            continue
        if char == "\\":
            escaped = True
            continue
        if in_double:
            if char == '"':
                in_double = False
            continue
        if char == "'":
            in_single = True
            continue
        if char == '"':
            in_double = True
            continue
        if char in _SHELL_METACHARACTERS:
            found.append(char)
    return found


#: Story 79.2 (spec-79-2, CAP-261a): the hygiene lane every dispatch
#: verification runs, whatever a station's own ``verify_commands`` say.
#: ``dispatch/*`` branches skip ``pr-preflight`` (the supervisor gates them),
#: and ``lint-types`` is in neither a station's ``verify_commands`` nor the
#: ``detectors-ci`` merge gate -- so scribe Story 25.1 landed code that
#: ``ruff format`` rewrites, and ``lint-types`` stayed red on ``main``
#: (DW-OPS-2026-10-01-2). The same "derive, don't declare" rule as
#: ``_SURFACE_RECONCILE_COMMAND``: one constant, folded in at use time, never
#: written into eight stations' ``marshal-policy.toml``. Only ``pyforge-guild``
#: exists at runtime (``AGENTS.md`` § Running and verifying), so the command is
#: the same for every station.
_LINT_TYPES_COMMAND = "pixi run --frozen -e pyforge-guild lint-types"

#: Story 83.2 (spec-83-2): the pyforge-core test suite every dispatch
#: verification runs, deriving it the same way as the surface guard and
#: lint-types. This ensures that stories changing core internals are
#: gated on the core suite that would catch breakage.
_PYFORGE_CORE_TEST_COMMAND = "pixi run --frozen -e pyforge-core pyforge-core-test"

#: Story 83.2 (spec-83-2): the deferred work check every dispatch
#: verification runs, ensuring uncited verified: lines are caught.
#: Both commands are seconds-long and folded in after deduplication.
_DEFERRED_WORK_CHECK_COMMAND = "pixi run --frozen -e pyforge-guild deferred-work-check"

#: Story 83.12 (spec-83-12): station packages whose ``src/`` a story touches
#: run that station's CI-mirroring coverage gate here -- never pyforge-core
#: (no ``pyforge-core-coverage-gate`` task) and never a station the diff did
#: not touch.
_STATION_PACKAGE_SRC_PARTS = ("src", "shared", "packages")
#: The eight Dream/TEA stations in ``scripts/coverage_gate.py`` ``STATIONS``
#: (``pyforge-core`` / testing-kit are not coverage-gate stations).
_COVERAGE_GATE_STATION_SLUGS: frozenset[str] = frozenset(
    f"pyforge-{name}"
    for name in (
        "atlas",
        "doctor",
        "herald",
        "marshal",
        "mason",
        "scribe",
        "steward",
        "warden",
    )
)


def _coverage_gate_command_for_station(station_slug: str) -> str:
    return f"pixi run --frozen -e {station_slug} {station_slug}-coverage-gate"


def coverage_gate_commands_for_changed_files(changed_files: tuple[str, ...]) -> tuple[str, ...]:
    """Derive ``pyforge-<station>-coverage-gate`` commands from touched station ``src/`` paths."""
    touched_slugs: set[str] = set()
    for path in changed_files:
        parts = Path(path).parts
        if len(parts) < 5:
            continue
        if parts[0:3] != _STATION_PACKAGE_SRC_PARTS:
            continue
        station_slug = parts[3]
        if station_slug not in _COVERAGE_GATE_STATION_SLUGS:
            continue
        if parts[4] != "src":
            continue
        touched_slugs.add(station_slug)
    return tuple(_coverage_gate_command_for_station(slug) for slug in sorted(touched_slugs))


#: Story 83.2 (spec-83-2): ``deferred_work_intake.py --fix`` refused or could
#: not run immediately before verification -- GATE_FAILED, naming the script's
#: own refusal (never the post-merge ``MRS-DISP-047`` WARN tier).
PRE_VERIFICATION_DEFERRED_WORK_INTAKE_CODE = "MRS-GATE-018"

#: ``deferred_work_intake.py``'s ``--project`` flag takes the short slug.
_PROJECT_SLUG_PREFIX = "pyforge-"


def _deferred_work_ledger_rel(project_slug: str) -> str:
    return f"_bmad-output/projects/{project_slug}/planning-artifacts/deferred-work-ledger.md"


def run_pre_verification_deferred_work_intake(
    *,
    process: ProcessPort,
    committing_vcs: CommittingVcs,
    worktree: Path,
    project_slug: str,
) -> Finding | None:
    """Story 83.2 (spec-83-2): promote this session's spec-frontmatter
    ``deferred:`` rows into the tracked ledger on the story branch BEFORE
    the derived ``deferred-work-check`` runs.

    Returns ``None`` on a clean run or when the intake changed nothing.
    Commits the ledger onto the story branch when ``--fix`` writes new rows."""
    short_slug = project_slug.removeprefix(_PROJECT_SLUG_PREFIX)
    ledger_rel = _deferred_work_ledger_rel(project_slug)
    ledger_path = worktree / ledger_rel
    try:
        original_text = ledger_path.read_text(encoding="utf-8") if ledger_path.is_file() else None
    except OSError as exc:
        return Finding(
            code=PRE_VERIFICATION_DEFERRED_WORK_INTAKE_CODE,
            severity=Severity.ERROR,
            message=f"pre-verification deferred-work intake could not read {ledger_rel!r}: {exc}",
            path=ledger_rel,
        )
    script = worktree / "scripts" / "deferred_work_intake.py"
    try:
        result = process.run(
            [sys.executable, str(script), "--fix", "--project", short_slug],
            cwd=worktree,
        )
    except ProcessError as exc:
        return Finding(
            code=PRE_VERIFICATION_DEFERRED_WORK_INTAKE_CODE,
            severity=Severity.ERROR,
            message=f"pre-verification deferred-work intake could not run for {short_slug!r}: {exc}",
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return Finding(
            code=PRE_VERIFICATION_DEFERRED_WORK_INTAKE_CODE,
            severity=Severity.ERROR,
            message=(
                f"pre-verification deferred-work intake refused (exit {result.returncode}) for {short_slug!r}: {detail}"
            ),
        )
    try:
        new_text = ledger_path.read_text(encoding="utf-8") if ledger_path.is_file() else None
    except OSError as exc:
        return Finding(
            code=PRE_VERIFICATION_DEFERRED_WORK_INTAKE_CODE,
            severity=Severity.ERROR,
            message=(f"pre-verification deferred-work intake could not read {ledger_rel!r} after run: {exc}"),
            path=ledger_rel,
        )
    if new_text == original_text:
        return None
    try:
        committing_vcs.commit_paths(
            worktree,
            (ledger_path,),
            to_redacted_text(f"marshal: pre-verification deferred-work intake for {short_slug!r}"),
        )
    except VcsCommandError as exc:
        return Finding(
            code=PRE_VERIFICATION_DEFERRED_WORK_INTAKE_CODE,
            severity=Severity.ERROR,
            message=(
                f"pre-verification deferred-work intake wrote {ledger_rel!r} but could not commit "
                f"on the story branch: {exc}"
            ),
            path=ledger_rel,
        )
    return None


def _verify_commands_with_surface_guard(
    effective: EffectivePolicy,
    *,
    changed_files: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    """Story 53.1 (spec-53-1, CAP-261a): the S-13.7 guard, appended to a
    dispatch session's own effective verify commands the SAME way
    ``harness_bmadloop.render_policy_toml`` appends it to a loop home's
    ``verify.commands`` -- one constant
    (``adapters.harness_bmadloop._SURFACE_RECONCILE_COMMAND``), two
    adapters. De-duplicated first so an operator who already declared the
    guard in a station's ``marshal-policy.toml`` (never the intended path --
    see that constant's own docstring, "derive, don't declare") still runs
    it exactly once. The membership test collapses whitespace
    (``" ".join(command.split())``) the same way ``gate.check_spec_binding``
    does, so a station-declared guard that differs only in spacing still
    de-duplicates instead of running twice.

    Story 79.2 (spec-79-2): ``_LINT_TYPES_COMMAND`` is derived here too, last,
    by the same append-after-dedupe rule -- the ONE place the derived commands
    are folded in, so every station's dispatch verification runs ``lint-types``
    exactly once, after its own ``verify_commands`` and the guard, even when
    the station already lists it. A red result is an ordinary
    ``MRS-GATE-001`` (``verify command '<command>' exited N``), so the refusal
    names ``lint-types`` with no new finding code. The name stays
    ``_verify_commands_with_surface_guard`` (three callers use it); it now
    folds in every derived command, not the guard alone.

    Story 83.2 (spec-83-2): ``_PYFORGE_CORE_TEST_COMMAND`` and
    ``_DEFERRED_WORK_CHECK_COMMAND`` are derived here too, appended after
    the same dedupe rule, so every station's dispatch verification runs
    the checks that read the whole tree exactly once.

    Story 83.12 (spec-83-12): when ``changed_files`` is supplied, each
    station whose ``src/shared/packages/pyforge-<station>/src/`` the story
    touched gets that station's ``pyforge-<station>-coverage-gate`` command,
    once, in sorted slug order. Omit ``changed_files`` (or pass an empty
    tuple) when the diff is not yet known -- pre-launch binding in
    ``cli/drain_plan.py`` -- so no coverage gate is derived.

    Unlike the loop adapter, this is not a rendered file an operator can
    read before a run starts -- it is folded in at USE time, right before
    the commands actually execute and before ``check_spec_binding`` sees
    them, so a dispatch session is gated on the guard exactly like a loop
    session even though nothing in ``marshal-policy.toml`` ever declares
    it."""
    coverage_derived = coverage_gate_commands_for_changed_files(changed_files or ())
    derived = (
        _SURFACE_RECONCILE_COMMAND,
        _LINT_TYPES_COMMAND,
        _PYFORGE_CORE_TEST_COMMAND,
        _DEFERRED_WORK_CHECK_COMMAND,
        *coverage_derived,
    )
    normalized_derived = {" ".join(command.split()) for command in derived}
    verify = [c for c in effective.verify_commands.value if " ".join(c.split()) not in normalized_derived]
    verify.extend(derived)
    return tuple(verify)


def run_verify_commands_only(
    effective: EffectivePolicy,
    *,
    process: ProcessPort,
    worktree: Path,
    repo_root: Path | None = None,
    vcs: VcsPort | None = None,
    story_changed_files: tuple[str, ...] | None = None,
) -> tuple[tuple[dict[str, object], ...], tuple[Finding, ...], tuple[Finding, ...]]:
    """Story 51.1: loop ``effective.verify_commands.value`` through the same
    per-command classification (``_run_verify_command``/``gate.classify_outcome``)
    ``evaluate_dispatch_verification`` uses, WITHOUT its scope/spec-binding/
    cross-surface layers -- those diff against ``base...HEAD`` (merge-base
    aware) and do not transfer to a merge-tree preview worktree (see spec
    Design Notes). Used by ``dispatch_land.py`` to re-run verification
    against the tree ``git merge-tree --write-tree`` would actually produce
    before landing, when the branch's baseline is behind ``origin/main``. No
    ``no_commands_configured_finding`` here regardless of ``verify_commands``;
    that policy-level warning belongs to the branch's own verification pass,
    not this preview re-run.

    Story 53.1 (spec-53-1): routed through ``_verify_commands_with_surface_guard``
    like every other verify-command consumer, not the raw policy value --
    unlike the scope/spec-binding/cross-surface layers, the S-13.7 guard is
    filesystem-state-based (it reads whatever tree it runs in and compares
    to a stored baseline), not a ``base...HEAD`` git diff, so the rationale
    that excludes those layers from a merge-tree preview does not extend to
    it: a merge-tree preview worktree is exactly the tree the guard needs to
    check before landing. As a result this can no longer return two empty
    tuples -- the derived guard (and, Story 79.2, ``lint-types``) is always
    present.

    Story 83.12 (spec-83-12): when ``repo_root`` and ``vcs`` are supplied,
    changed files against ``origin/main`` in the preview worktree drive the
    same per-station coverage-gate derivation as
    ``evaluate_dispatch_verification``. When resolution fails, fall back to
    ``story_changed_files`` from the dispatch worktree (never silently skip
    gates); if neither is available, refuse with ``MRS-GATE-009``."""
    changed_files: tuple[str, ...] = ()
    preview_findings: list[Finding] = []
    if repo_root is not None and vcs is not None:
        try:
            changed_files = vcs.changed_files(repo_root, worktree, base=_SCOPE_BASE)
        except Exception as exc:
            if story_changed_files is not None:
                changed_files = story_changed_files
                preview_findings.append(
                    Finding(
                        code="MRS-GATE-009",
                        severity=Severity.WARN,
                        message=(
                            "merge-tree preview could not resolve changed files; "
                            f"using the story worktree diff instead: {exc}"
                        ),
                    )
                )
            else:
                preview_findings.append(
                    Finding(
                        code="MRS-GATE-009",
                        severity=Severity.ERROR,
                        message=f"merge-tree preview could not resolve changed files: {exc}",
                    )
                )
    command_reports: list[dict[str, object]] = []
    command_findings: list[Finding] = []
    for command in _verify_commands_with_surface_guard(effective, changed_files=changed_files):
        report, finding = _run_verify_command(command, process=process, worktree=worktree)
        command_reports.append(report)
        if finding is not None:
            command_findings.append(finding)
    return tuple(command_reports), tuple(command_findings), tuple(preview_findings)


def compose_dispatch_policy(slug: str, repo_root: Path) -> EffectivePolicy:
    """Compose policy from the conventional project path (no cli import)."""
    candidate = (
        dispatch_core.canonical_repo_root(repo_root)
        / "_bmad-output"
        / "projects"
        / slug
        / "planning-artifacts"
        / "marshal-policy.toml"
    )
    project_data: dict[str, object] = {}
    if candidate.is_file():
        try:
            project_data = dict(tomllib.loads(candidate.read_text()))
        except OSError, UnicodeDecodeError, tomllib.TOMLDecodeError:
            project_data = {}
    effective, _findings = policy.compose(project_slug=slug, project=project_data, flags={})
    return effective


def resolve_spec_text_for_story(repo_root: Path, project_slug: str, story_key: StoryKey) -> str | None:
    """Read tracked spec text for ``story_key`` (best-effort)."""
    spec_path = dispatch_core.resolve_story_spec_path(repo_root, project_slug, render_feed_key(story_key))
    if spec_path is None:
        return None
    try:
        return spec_path.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return None


def evaluate_dispatch_verification(
    *,
    project_slug: str,
    story_key: StoryKey,
    worktree: Path,
    repo_root: Path,
    effective: EffectivePolicy,
    spec_text: str | None,
    process: ProcessPort,
    vcs: VcsPort,
    committing_vcs: CommittingVcs | None = None,
) -> Envelope:
    """Run Epic 2 gate objects against a dispatch worktree (CAP-3)."""
    findings: list[Finding] = []
    data: dict[str, object] = {
        "slug": project_slug,
        "story": str(story_key),
        "worktree": str(worktree),
        "scope": "dispatch-worktree",
    }

    if committing_vcs is not None:
        intake_finding = run_pre_verification_deferred_work_intake(
            process=process,
            committing_vcs=committing_vcs,
            worktree=worktree,
            project_slug=project_slug,
        )
        data["pre_verification_deferred_work_intake"] = (
            None if intake_finding is None else intake_finding.to_json_dict()
        )
        if intake_finding is not None:
            findings.append(intake_finding)

    attribution_findings, attribution_report = check_branch_commit_attribution(
        worktree=worktree,
        process=process,
        repo_root=repo_root,
        base=_SCOPE_BASE,
    )
    findings.extend(attribution_findings)
    data["commit_attribution_check"] = attribution_report

    scope_changed_files: tuple[str, ...] = ()
    scope_effective_surface: tuple[str, ...] = ()
    scope_check_completed = False
    scope_changed_resolved = False
    try:
        scope_changed_files = vcs.changed_files(repo_root, worktree, base=_SCOPE_BASE)
        scope_changed_resolved = True
    except Exception as exc:
        findings.append(
            Finding(
                code="MRS-GATE-009",
                severity=Severity.ERROR,
                message=(f"dispatch scope check could not resolve changed files for {story_key}: {exc}"),
            )
        )
        data["scope_check"] = {"checked": False, "reason": str(exc)}

    commands = _verify_commands_with_surface_guard(effective, changed_files=scope_changed_files)
    command_reports: list[dict[str, object]] = []
    # Story 53.1 / 79.2: `commands` can no longer be empty -- the S-13.7 guard
    # and `lint-types` are unconditionally appended above, so a station with a
    # bare `verify_commands = []` now runs those two alone rather than nothing.
    # This mirrors `harness_bmadloop.render_policy_toml`, which has never
    # checked for emptiness before appending it either. The `not commands`
    # branch stays as defensive dead code (never reachable today) rather
    # than being deleted, so a future change to
    # `_verify_commands_with_surface_guard` that CAN yield an empty tuple
    # keeps reporting `MRS-GATE-004` instead of silently losing it.
    if not commands:
        if status_for(compute_verdict(findings)) is Status.OK:
            findings.append(gate.no_commands_configured_finding())
    else:
        for command in commands:
            report, finding = _run_verify_command(command, process=process, worktree=worktree)
            command_reports.append(report)
            if finding is not None:
                findings.append(finding)
    data["commands"] = command_reports

    if scope_changed_resolved:
        changed = scope_changed_files
        policy_surface = gate.resolve_policy_surface(effective.epic_surfaces.value, story_key.epic, project_slug)
        try:
            spec_surface = parse_declared_surface(spec_text) if spec_text is not None else None
        except SurfaceParseError as exc:
            findings.append(
                Finding(
                    code="MRS-GATE-009",
                    severity=Severity.ERROR,
                    message=(
                        f"dispatch scope check could not evaluate {story_key}: malformed surface declaration: {exc}"
                    ),
                )
            )
            data["scope_check"] = {"checked": False, "reason": str(exc)}
        else:
            effective_surface = gate.compute_effective_surface(policy_surface, spec_surface)
            seed_frozen = effective.seed_view()["frozen_surfaces"].value
            empty_fold = journal.FoldResult(entries=(), open_intents=(), orphaned_outcomes=(), quarantined=())
            frozen_paths = empty_fold.live_frozen_surfaces(seed_frozen)
            # Story 28.15 (CAP-17): the SAME mode-application function
            # `cli/gate.py::_run_scope_check` uses -- this safety-relevant
            # branching lives in exactly one place, never duplicated per
            # call site (`core/gate.py::check_scope_with_mode`'s own
            # docstring).
            scope_violation_mode = effective.scope_violation_mode.value
            scope_findings = gate.check_scope_with_mode(
                effective_surface, frozen_paths, changed, mode=scope_violation_mode
            )
            advisory_paths = tuple(
                finding.path
                for finding in scope_findings
                if finding.code in gate._SCOPE_VIOLATION_ADVISORY_CODES.values() and finding.path
            )
            if advisory_paths and scope_violation_mode == "warn":
                widened_surface = gate.widen_effective_surface_with_paths(effective_surface, advisory_paths)
                if widened_surface != effective_surface:
                    recheck_findings = gate.check_scope_with_mode(
                        widened_surface,
                        frozen_paths,
                        changed,
                        mode=scope_violation_mode,
                    )
                    if not any(finding.severity is Severity.ERROR for finding in recheck_findings):
                        effective_surface = widened_surface
                    else:
                        scope_findings = recheck_findings
            findings.extend(scope_findings)
            scope_changed_files = changed
            scope_effective_surface = effective_surface
            scope_check_completed = True
            data["scope_check"] = {
                "checked": True,
                "story": str(story_key),
                "mode": scope_violation_mode,
                "effective_surface": list(effective_surface),
                "changed_files": list(changed),
                "violations": len(scope_findings),
            }

    if command_reports and scope_check_completed:
        # Story 79.2: the derived `lint-types` lane never reaches the 28.22
        # pre-existing reclassifier -- dropping its report leaves the reclassifier
        # no output to read for that command, so its MRS-GATE-001 stands. The
        # lane runs ruff/mypy per package (cwd = the package dir), so every path
        # in its output is package-relative (`src/pyforge/scribe/catalog.py`) and
        # can never match the story's repo-relative changed files: "outside the
        # story's blast radius" is meaningless here, and a red `lint-types` must
        # refuse the landing (spec-79-2 AC2), never downgrade to MRS-GATE-014.
        # Story 83.2: the same reasoning applies to the derived whole-tree check
        # commands -- they read the whole tree and their failures must refuse.
        # Story 83.12: per-station coverage gates measure touched modules in
        # the station env; their output paths do not belong in blast-radius
        # reclassification either.
        derived_commands = {
            _SURFACE_RECONCILE_COMMAND,
            _LINT_TYPES_COMMAND,
            _PYFORGE_CORE_TEST_COMMAND,
            _DEFERRED_WORK_CHECK_COMMAND,
            *coverage_gate_commands_for_changed_files(scope_changed_files),
        }
        reclassifiable_reports = tuple(
            report for report in command_reports if report.get("command") not in derived_commands
        )
        findings = list(
            reclassify_pre_existing_gate_findings(
                tuple(findings),
                command_reports=reclassifiable_reports,
                changed_files=scope_changed_files,
                effective_surface=scope_effective_surface,
                project_slug=project_slug,
            )
        )

    if spec_text is not None:
        declared_commands = spec_binding.parse_success_signal(spec_text)
        # Story 53.1 / 79.2: bind against the SAME widened `commands` the loop
        # above actually ran, not the bare station policy -- the derived
        # S-13.7 guard and `lint-types` are extra `policy_commands` entries no
        # tracked spec has to declare, and `check_spec_binding`'s
        # one-directional comparison already treats an undeclared extra as
        # implicit, never a finding (see its own docstring). A spec that does
        # declare one of them still binds: it is among the widened commands.
        # This keeps "what ran" and "what was checked" the same tuple.
        binding_findings = gate.check_spec_binding(declared_commands, commands)
        findings.extend(binding_findings)
        data["spec_binding"] = {
            "story": str(story_key),
            "declared_commands": (list(declared_commands) if declared_commands is not None else None),
            "violations": len(binding_findings),
        }

    cross_surface_command = gate.shared_surface_verify_command()
    cross_surface_touched = scope_check_completed and gate.changed_files_touch_shared_surface(scope_changed_files)
    if cross_surface_touched:
        cross_report, cross_finding = _run_verify_command(
            cross_surface_command,
            process=process,
            worktree=worktree,
            failure_prefix="cross-surface verify command",
        )
        if cross_finding is not None:
            if cross_finding.code == "MRS-GATE-001":
                cross_finding = Finding(
                    code=gate.CROSS_SURFACE_GATE_CODE,
                    severity=cross_finding.severity,
                    message=cross_finding.message.replace("verify command", "cross-surface verify command"),
                )
            findings.append(cross_finding)
        data["cross_surface_check"] = {
            "checked": True,
            "command": cross_surface_command,
            "touched_paths": [
                path
                for path in scope_changed_files
                if path == gate.SHARED_SURFACE_PREFIX.rstrip("/") or path.startswith(gate.SHARED_SURFACE_PREFIX)
            ],
            "report": cross_report,
        }
    else:
        data["cross_surface_check"] = {
            "checked": False,
            "reason": ("scope check incomplete" if not scope_check_completed else "diff does not touch shared surface"),
        }

    verdict_value = compute_verdict(findings)
    return build_envelope(
        command="dispatch verify",
        verdict=verdict_value,
        data=data,
        findings=tuple(findings),
    )


def run_dispatch_ruff_format_before_verify(
    *,
    worktree: Path,
    repo_root: Path,
    vcs: CommittingVcs,
    process: ProcessPort,
) -> DispatchRuffFormatResult:
    """Story 83.9 entry: format only the story's changed ``.py`` files before verify."""
    return apply_dispatch_ruff_format_before_verify(
        worktree=worktree,
        repo_root=repo_root,
        vcs=vcs,
        process=process,
    )


# --------------------------------------------------------------------------
# Story 85.1 (spec-pyforge-marshal:CAP-286): the verification-refusal fix
# turn's impure edge -- the flag read, the fix session's wait and its stop.
# The decision and the prompt stay pure in ``core/dispatch_verify_fix.py``;
# the launch is ``BmadBuildHarness.dispatch_verify_fix``. Dormant while
# ``pyforge.marshal.verify_fix_loop`` is off in every environment.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcessWaitResult:
    exited: bool
    returncode: int | None


@dataclass(frozen=True)
class TerminateProcessGroupResult:
    """Outcome of stopping a fix session's process group (Story 85.3)."""

    signalled_term: bool
    signalled_kill: bool
    reaped: bool
    returncode: int | None


TERMINATE_GRACE_SECONDS = 5.0


def verify_fix_loop_enabled(*, repo_root: Path) -> tuple[bool, str | None]:
    """Read the fix-loop flag; ``(False, reason)`` when the flag tree is invalid."""
    flags_path = repo_root / "src/platform/config/flags.json"
    try:
        return read_boolean(VERIFY_FIX_LOOP_FLAG_KEY, default=False, flags_path=flags_path), None
    except FlagConfigError as exc:
        return False, str(exc)


def _is_zombie(pid: int) -> bool:
    """``True`` when ``/proc`` reports ``pid`` exited and awaiting its parent's reap (state ``Z``)."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    # The state follows the parenthesised command name, which may itself hold spaces or parentheses.
    close = stat.rfind(")")
    return close != -1 and stat[close + 2 : close + 3] == "Z"


def dispatch_session_alive(process: ProcessPort, pid: int, *, launched_at: datetime | None) -> bool:
    """Story 83.1/85.3: the original dispatch session's liveness, with the same zombie and pid-reuse guards as a
    fix session's -- the tick loop and every CLI reader judge it by this one check."""
    return fix_session_alive(process, pid, launched_at=launched_at)


def fix_session_alive(process: ProcessPort, pid: int, *, launched_at: datetime | None) -> bool:
    """True while a journaled fix session runs (Story 85.2): the pid exists and has not exited (a zombie only awaits
    its parent's reap -- ``ProcessPort.is_alive`` counts it alive, a waiting successor must not) AND, when the
    launch time is known, its process started within ``PID_START_TOLERANCE_SECONDS`` of that launch -- Story 83.1's
    guard, so a pid the host has since reused for an unrelated process never reads as the turn still running."""
    if not process.is_alive(pid) or _is_zombie(pid):
        return False
    if launched_at is None:
        return True
    return dispatch_core.pid_start_matches_launch(process.process_start_time(pid), launched_at)


def wait_for_process(
    process: ProcessPort,
    pid: int,
    *,
    timeout_s: float,
    poll_s: float = 1.0,
    on_poll: Callable[[], None] | None = None,
    launched_at: datetime | None = None,
) -> ProcessWaitResult:
    """Wait until ``pid`` exits or ``timeout_s`` elapses.

    A child of this process is reaped with ``waitpid(WNOHANG)``, so an exited-but-unreaped child is not treated
    as still alive (Story 85.1 review H2), and its exit code is read. A pid that is NOT this process's child --
    the fix session a killed supervisor launched, waited on by its successor (Story 85.2 review H1) -- makes
    ``waitpid`` raise ``ChildProcessError``; from then on it is judged by ``fix_session_alive`` (existence plus
    the start-time check against ``launched_at``), and its exit code is unknowable (``returncode=None``).
    """
    deadline = time.monotonic() + timeout_s
    is_child = True
    while True:
        if is_child:
            try:
                reaped, status = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                is_child = False
            except OSError:
                return ProcessWaitResult(exited=False, returncode=None)
            else:
                if reaped == pid:
                    return ProcessWaitResult(exited=True, returncode=os.waitstatus_to_exitcode(status))
        if not is_child and not fix_session_alive(process, pid, launched_at=launched_at):
            return ProcessWaitResult(exited=True, returncode=None)
        if time.monotonic() >= deadline:
            return ProcessWaitResult(exited=False, returncode=None)
        if on_poll is not None:
            on_poll()
        time.sleep(poll_s)


def _session_group(pid: int) -> int | None:
    """``pid``'s process group when signalling the whole group is safe, else ``None``: never a group id ``<= 1``
    (0 addresses this process's own group -- a kernel thread reports pgid 0 -- and 1 is init's) and never this
    process's own group, which would stop the supervisor itself (Story 85.2)."""
    try:
        pgid = os.getpgid(pid)
    except OSError:
        return None
    if pgid <= 1 or pgid == os.getpgrp():
        return None
    return pgid


def _signal_session_stop(pid: int, pgid: int | None, sig: int) -> bool:
    """Send ``sig`` to the session's group ``pgid``, or to ``pid`` alone when there is no safe group."""
    if pgid is not None:
        try:
            os.killpg(pgid, sig)
            return True
        except OSError:
            pass
    try:
        os.kill(pid, sig)
    except OSError:
        return False
    return True


def _group_has_members(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _try_reap_pid(pid: int) -> tuple[bool, int | None]:
    try:
        reaped, status = os.waitpid(pid, os.WNOHANG)
    except OSError:
        return False, None
    if reaped == pid:
        return True, os.waitstatus_to_exitcode(status)
    return False, None


def _wait_leader_exit(pid: int, proc: ProcessPort, *, deadline: float, poll_s: float) -> tuple[bool, bool, int | None]:
    """Wait until the leader is reaped (our child) or gone, or ``deadline`` passes: ``(exited, reaped, code)``."""
    while True:
        reaped, code = _try_reap_pid(pid)
        if reaped:
            return True, True, code
        if not proc.is_alive(pid) or _is_zombie(pid):
            reaped, code = _try_reap_pid(pid)
            return True, reaped, code
        if time.monotonic() >= deadline:
            return False, False, None
        time.sleep(poll_s)


def terminate_process_group(
    pid: int,
    *,
    grace_s: float = TERMINATE_GRACE_SECONDS,
    process: ProcessPort | None = None,
) -> TerminateProcessGroupResult:
    """Stop a fix session's process group: SIGTERM, a bounded wait, SIGKILL, and reap (Story 85.1/85.3).

    Story 85.2: the pid also comes off a journal a restarted supervisor reads, so a pid that is a process-group
    address (``<= 0``) or init is never signalled, and a session whose group is unsafe to signal
    (``_session_group``) is signalled alone. Story 85.3 (landing review M1): the group id is read BEFORE the
    SIGTERM, so once the leader has exited -- it may obey SIGTERM while a child ignores it -- any member left in
    that group is still found (``killpg(pgid, 0)``) and SIGKILLed."""
    if pid <= 1:
        return TerminateProcessGroupResult(signalled_term=False, signalled_kill=False, reaped=False, returncode=None)
    proc = process if process is not None else PosixProcess()
    pgid = _session_group(pid)
    signalled_term = _signal_session_stop(pid, pgid, signal.SIGTERM)
    exited, reaped, code = _wait_leader_exit(pid, proc, deadline=time.monotonic() + grace_s, poll_s=0.05)
    signalled_kill = False
    if not exited:
        signalled_kill = _signal_session_stop(pid, pgid, signal.SIGKILL)
        exited, reaped, code = _wait_leader_exit(pid, proc, deadline=time.monotonic() + grace_s, poll_s=0.1)
    if not reaped:
        reaped, late_code = _try_reap_pid(pid)
        code = late_code if reaped else code
    if pgid is not None and _group_has_members(pgid):
        # The leader is gone but its group is not: a member that ignored SIGTERM outlives it.
        try:
            os.killpg(pgid, signal.SIGKILL)
            signalled_kill = True
        except OSError:
            pass
    return TerminateProcessGroupResult(
        signalled_term=signalled_term,
        signalled_kill=signalled_kill,
        reaped=reaped,
        returncode=code,
    )
