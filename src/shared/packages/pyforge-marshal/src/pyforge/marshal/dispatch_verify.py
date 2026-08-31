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

from .core import dispatch as dispatch_core
from .core import gate, journal, policy, spec_binding
from .core.identity import StoryKey, render_feed_key
from .core.model import Envelope, Finding, Severity, Status, build_envelope, status_for
from .core.policy import EffectivePolicy
from .core.spec_surface import SurfaceParseError, parse_declared_surface
from .core.verdict import compute_verdict
from .ports.vcs import VcsPort

_SCOPE_BASE = "origin/main"
_SHELL_METACHARACTERS = frozenset("&|<>;()")


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
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            project_data = {}
    effective, _findings = policy.compose(
        project_slug=slug, project=project_data, flags={}
    )
    return effective


def resolve_spec_text_for_story(
    repo_root: Path, project_slug: str, story_key: StoryKey
) -> str | None:
    """Read tracked spec text for ``story_key`` (best-effort)."""
    spec_path = dispatch_core.resolve_story_spec_path(
        repo_root, project_slug, render_feed_key(story_key)
    )
    if spec_path is None:
        return None
    try:
        return spec_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
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

    commands = effective.verify_commands.value
    command_reports: list[dict[str, object]] = []
    if not commands:
        if status_for(compute_verdict(findings)) is Status.OK:
            findings.append(gate.no_commands_configured_finding())
    else:
        for command in commands:
            try:
                tokens = shlex.split(command)
            except ValueError as exc:
                report, finding = gate.classify_outcome(
                    command,
                    None,
                    failure_code="MRS-GATE-003",
                    failure_reason=f"cannot parse verify command {command!r}: {exc}",
                )
            else:
                shell_chars = _bare_shell_metacharacters(command)
                if shell_chars:
                    report, finding = gate.classify_outcome(
                        command,
                        None,
                        failure_code="MRS-GATE-003",
                        failure_reason=(
                            f"verify command {command!r} uses shell syntax "
                            f"({', '.join(repr(c) for c in shell_chars)}) "
                            "but verify commands are never run through a shell"
                        ),
                    )
                else:
                    try:
                        result = process.run(tokens, cwd=worktree)
                    except ProcessError as exc:
                        report, finding = gate.classify_outcome(
                            command,
                            None,
                            failure_code="MRS-GATE-002",
                            failure_reason=(
                                f"verify command {command!r} could not be run: {exc}"
                            ),
                        )
                    else:
                        report, finding = gate.classify_outcome(command, result)
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
                message=(
                    f"dispatch scope check could not resolve changed files "
                    f"for {story_key}: {exc}"
                ),
            )
        )
        data["scope_check"] = {"checked": False, "reason": str(exc)}
    else:
        policy_surface = gate.resolve_policy_surface(
            effective.epic_surfaces.value, story_key.epic, project_slug
        )
        try:
            spec_surface = (
                parse_declared_surface(spec_text) if spec_text is not None else None
            )
        except SurfaceParseError as exc:
            findings.append(
                Finding(
                    code="MRS-GATE-009",
                    severity=Severity.ERROR,
                    message=(
                        f"dispatch scope check could not evaluate {story_key}: "
                        f"malformed surface declaration: {exc}"
                    ),
                )
            )
            data["scope_check"] = {"checked": False, "reason": str(exc)}
        else:
            effective_surface = gate.compute_effective_surface(
                policy_surface, spec_surface
            )
            seed_frozen = effective.seed_view()["frozen_surfaces"].value
            empty_fold = journal.FoldResult(
                entries=(), open_intents=(), orphaned_outcomes=(), quarantined=()
            )
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
            findings.extend(scope_findings)
            data["scope_check"] = {
                "checked": True,
                "story": str(story_key),
                "mode": scope_violation_mode,
                "effective_surface": list(effective_surface),
                "changed_files": list(changed),
                "violations": len(scope_findings),
            }

    if spec_text is not None:
        declared_commands = spec_binding.parse_success_signal(spec_text)
        binding_findings = gate.check_spec_binding(
            declared_commands, effective.verify_commands.value
        )
        findings.extend(binding_findings)
        data["spec_binding"] = {
            "story": str(story_key),
            "declared_commands": (
                list(declared_commands) if declared_commands is not None else None
            ),
            "violations": len(binding_findings),
        }

    verdict_value = compute_verdict(findings)
    return build_envelope(
        command="dispatch verify",
        verdict=verdict_value,
        data=data,
        findings=tuple(findings),
    )
