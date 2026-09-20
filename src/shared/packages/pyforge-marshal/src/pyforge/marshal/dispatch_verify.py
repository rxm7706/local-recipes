"""Independent dispatch verification via Epic 2 gate objects (Story 22.3).

Impure edge for the dispatch supervisor: runs verify commands and scope
checks against a dispatch worktree. Session self-reports are never verdict
inputs. Lives outside ``cli/`` so ``dispatch_supervisor`` may import it
(AD-9).
"""

from __future__ import annotations

import shlex
import tomllib
from pathlib import Path

from pyforge.core.process import ProcessError, ProcessPort

from .adapters.harness_bmadloop import _SURFACE_RECONCILE_COMMAND
from .core import dispatch as dispatch_core
from .core import gate, journal, policy, spec_binding
from .core.dispatch_verification import reclassify_pre_existing_gate_findings
from .core.identity import StoryKey, render_feed_key
from .core.model import Envelope, Finding, Severity, Status, build_envelope, status_for
from .core.policy import EffectivePolicy
from .core.spec_surface import SurfaceParseError, parse_declared_surface
from .core.verdict import compute_verdict
from .ports.vcs import VcsPort

_SCOPE_BASE = "origin/main"
_SHELL_METACHARACTERS = frozenset("&|<>;()")


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


def _verify_commands_with_surface_guard(
    effective: EffectivePolicy,
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

    Unlike the loop adapter, this is not a rendered file an operator can
    read before a run starts -- it is folded in at USE time, right before
    the commands actually execute and before ``check_spec_binding`` sees
    them, so a dispatch session is gated on the guard exactly like a loop
    session even though nothing in ``marshal-policy.toml`` ever declares
    it."""
    normalized_guard = " ".join(_SURFACE_RECONCILE_COMMAND.split())
    verify = [c for c in effective.verify_commands.value if " ".join(c.split()) != normalized_guard]
    verify.append(_SURFACE_RECONCILE_COMMAND)
    return tuple(verify)


def run_verify_commands_only(
    effective: EffectivePolicy, *, process: ProcessPort, worktree: Path
) -> tuple[tuple[dict[str, object], ...], tuple[Finding, ...]]:
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
    tuples -- the guard is always present."""
    command_reports: list[dict[str, object]] = []
    findings: list[Finding] = []
    for command in _verify_commands_with_surface_guard(effective):
        report, finding = _run_verify_command(command, process=process, worktree=worktree)
        command_reports.append(report)
        if finding is not None:
            findings.append(finding)
    return tuple(command_reports), tuple(findings)


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
) -> Envelope:
    """Run Epic 2 gate objects against a dispatch worktree (CAP-3)."""
    findings: list[Finding] = []
    data: dict[str, object] = {
        "slug": project_slug,
        "story": str(story_key),
        "worktree": str(worktree),
        "scope": "dispatch-worktree",
    }

    commands = _verify_commands_with_surface_guard(effective)
    command_reports: list[dict[str, object]] = []
    scope_changed_files: tuple[str, ...] = ()
    scope_effective_surface: tuple[str, ...] = ()
    scope_check_completed = False
    # Story 53.1: `commands` can no longer be empty -- the S-13.7 guard is
    # unconditionally appended above, so a station with a bare
    # `verify_commands = []` now runs the guard alone rather than nothing.
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

    try:
        changed = vcs.changed_files(repo_root, worktree, base=_SCOPE_BASE)
    except Exception as exc:
        findings.append(
            Finding(
                code="MRS-GATE-009",
                severity=Severity.ERROR,
                message=(f"dispatch scope check could not resolve changed files for {story_key}: {exc}"),
            )
        )
        data["scope_check"] = {"checked": False, "reason": str(exc)}
    else:
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
        findings = list(
            reclassify_pre_existing_gate_findings(
                tuple(findings),
                command_reports=tuple(command_reports),
                changed_files=scope_changed_files,
                effective_surface=scope_effective_surface,
                project_slug=project_slug,
            )
        )

    if spec_text is not None:
        declared_commands = spec_binding.parse_success_signal(spec_text)
        # Story 53.1: bind against the SAME widened `commands` the loop
        # above actually ran, not the bare station policy -- the derived
        # S-13.7 guard is an extra `policy_commands` entry no tracked spec
        # declares, and `check_spec_binding`'s one-directional comparison
        # already treats an undeclared extra as implicit, never a finding
        # (see its own docstring). Binding against the narrower
        # `effective.verify_commands.value` would work too (the guard is
        # never in `declared_commands` either), but this keeps "what ran"
        # and "what was checked" the same tuple.
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
