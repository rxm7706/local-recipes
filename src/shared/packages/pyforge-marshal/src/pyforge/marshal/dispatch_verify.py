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
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pyforge.core.errors import PyforgeError
from pyforge.core.flags import FlagConfigError, read_boolean
from pyforge.core.process import PosixProcess, ProcessError, ProcessPort, ProcessResult

from .adapters.harness_bmadloop import _SURFACE_RECONCILE_COMMAND
from .adapters.session_group_psutil import PsutilSessionGroup, process_cmdline
from .adapters.vcs_git import VcsCommandError
from .core import dispatch as dispatch_core
from .core import gate, journal, policy, spec_binding
from .core.commit_vcs import CommittingVcs
from .core.dispatch_cfe_commit import (
    CFE_GIT_PATHSPECS,
    commit_pending_cfe_retro,
    findings_for_unsanctioned_cfe_entries,
    unsanctioned_cfe_entries,
)
from .core.dispatch_environment_yaml import (
    DispatchEnvironmentYamlResult,
    apply_dispatch_environment_yaml_before_verify,
)
from .core.dispatch_reverify import (
    GATE_DIGEST_FIELD,
    MAX_CHAIN_COMMITS,
    REASON_DIRTY_WORKTREE,
    REASON_GATE_SET_CHANGED,
    REASON_GIT_READ_FAILED,
    REASON_NO_VERIFIED_VERDICT,
    REASON_RECHECK_FAILED,
    ChainCommit,
    ReuseCandidate,
    ReuseDecision,
    ReuseFacts,
    declined,
    gate_set_digest,
    is_planning_path,
    judge_verdict_reuse,
    latest_reusable_verdict,
)
from .core.dispatch_ruff_format import (
    DispatchRuffFormatResult,
    apply_dispatch_ruff_format_before_verify,
)
from .core.dispatch_spec_frontmatter import (
    DispatchSpecFrontmatterResult,
    apply_dispatch_spec_frontmatter_before_verify,
    findings_for_spec_frontmatter_refusals,  # noqa: F401 — re-export for cli.dispatch
)
from .core.dispatch_verification import (
    BranchCommitAttribution,
    findings_for_commit_attribution_violations,
    reclassify_pre_existing_gate_findings,
)
from .core.dispatch_verify_fix import VERIFY_FIX_LOOP_FLAG_KEY
from .core.egress import to_redacted_text
from .core.harness_profile import HarnessProfileError, load_profiles
from .core.identity import StoryKey, render_feed_key
from .core.journal import FoldResult, JournalEntry, resolve_scope_violation_advisories_from_payload
from .core.model import Envelope, Finding, Severity, Status, build_envelope, status_for
from .core.policy import EffectivePolicy
from .core.refs import ORIGIN_MAIN
from .core.spec_surface import SurfaceParseError, parse_declared_surface
from .core.verdict import compute_verdict
from .ports.session_group import SessionGroupPort, SessionGroupReadError
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
                        "dispatch commit-attribution check could not load scripts/commit_msg_hook.py from the worktree"
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


def _parse_cfe_commits_from_log(stdout: str) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Parse ``git log --name-only --format=%x1e%H%x1f%s`` output into ``(sha, subject, files)``."""
    commits: list[tuple[str, str, tuple[str, ...]]] = []
    for chunk in stdout.split(_COMMIT_LOG_RECORD_SEP):
        header, _, rest = chunk.partition("\n")
        sha, sep, subject = header.partition(_COMMIT_LOG_FIELD_SEP)
        if not sep or not sha:
            continue
        files = tuple(line for line in rest.splitlines() if line.strip())
        commits.append((sha, subject, files))
    return tuple(commits)


def _cfe_check_read_failure(rev_range: str, detail: str) -> tuple[tuple[Finding, ...], dict[str, object]]:
    return (
        (
            Finding(
                code="MRS-GATE-009",
                severity=Severity.ERROR,
                message=f"dispatch CFE-surface commit check could not read {rev_range!r}: {detail}",
            ),
        ),
        {"checked": False, "reason": detail, "rev_range": rev_range},
    )


def check_unsanctioned_cfe_commits(
    *,
    worktree: Path,
    process: ProcessPort,
    base: str = _SCOPE_BASE,
) -> tuple[tuple[Finding, ...], dict[str, object]]:
    """Story 83.19: refuse when ``base..HEAD`` touches the CFE surface outside a sanctioned retro.

    The station guards' ``branch_diff_guard.unsanctioned_commits`` over the CFE surface, read
    through marshal's own process seam (a production station never imports the testing kit),
    so a dispatch branch the guards would refuse never reaches a push. A git read that fails
    refuses (``MRS-GATE-009``); it never reads as clean."""
    rev_range = f"{base}..HEAD"
    log_argv = [
        "git",
        "-C",
        str(worktree),
        "log",
        "--no-merges",
        "--full-diff",
        "--name-only",
        f"--format={_COMMIT_LOG_RECORD_SEP}%H{_COMMIT_LOG_FIELD_SEP}%s",
        rev_range,
        "--",
        *CFE_GIT_PATHSPECS,
    ]
    dirty_argv = ["git", "-C", str(worktree), "diff", "--name-only", "HEAD", "--", *CFE_GIT_PATHSPECS]
    outputs: list[str] = []
    for argv in (log_argv, dirty_argv):
        try:
            result = process.run(argv, cwd=worktree)
        except ProcessError as exc:
            return _cfe_check_read_failure(rev_range, str(exc))
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            return _cfe_check_read_failure(rev_range, f"exit {result.returncode}: {detail}")
        outputs.append(result.stdout)
    commits = _parse_cfe_commits_from_log(outputs[0])
    entries = unsanctioned_cfe_entries(commits, outputs[1].split())
    findings = findings_for_unsanctioned_cfe_entries(entries, base=base)
    return (
        findings,
        {
            "checked": True,
            "rev_range": rev_range,
            "commits_scanned": len(commits),
            "unsanctioned": entries,
        },
    )


def _normalize_verify_command(command: str) -> str:
    return " ".join(command.split())


def _argv_for_verify_execution(command: str, tokens: list[str]) -> list[str]:
    """Story 22.16 (spec-22-16): execute the S-13.7 guard with ``sys.executable``.

    The journaled / spec-binding command string stays plain
    ``python scripts/spec_surface_reconcile.py`` (``_SURFACE_RECONCILE_COMMAND``);
    only the argv passed to ``ProcessPort.run`` uses the supervisor's own
    interpreter so a PATH without a ``python`` shim cannot refuse a finished
    session at verification."""
    if _normalize_verify_command(command) == _normalize_verify_command(_SURFACE_RECONCILE_COMMAND):
        return [sys.executable, "scripts/spec_surface_reconcile.py"]
    return tokens


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
    argv = _argv_for_verify_execution(command, tokens)
    try:
        result = process.run(argv, cwd=worktree)
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


#: Story 83.23 (spec-83-23): cross-station ``tests/meta/`` contracts that scan
#: every station's ``src/`` (or all ``pyforge-*/src/``). Each entry is
#: ``(owning pixi env, repo-relative pytest path)`` -- run in the owner's env
#: because the doctor contracts import doctor-only fixtures.
_CROSS_STATION_META_TESTS: tuple[tuple[str, str], ...] = (
    (
        "pyforge-steward",
        "src/shared/packages/pyforge-steward/tests/meta/test_no_station_assumes_local_recipes.py",
    ),
    (
        "pyforge-doctor",
        "src/shared/packages/pyforge-doctor/tests/meta/test_coverage_gate_stays_outside_every_station.py",
    ),
    (
        "pyforge-doctor",
        "src/shared/packages/pyforge-doctor/tests/meta/test_flag_gate_stays_outside_every_station.py",
    ),
)


def _touches_any_station_package_src(changed_files: tuple[str, ...]) -> bool:
    """True when the diff touches any ``src/shared/packages/pyforge-*/src/`` tree.

    Story 83.23: wider than ``coverage_gate_commands_for_changed_files`` --
    ``pyforge-core`` and ``pyforge-testing-kit`` have no coverage gate but
    steward's meta-test reads their ``src/`` too."""
    for path in changed_files:
        parts = Path(path).parts
        if len(parts) < 5:
            continue
        if parts[0:3] != _STATION_PACKAGE_SRC_PARTS:
            continue
        if not parts[3].startswith("pyforge-"):
            continue
        if parts[4] != "src":
            continue
        return True
    return False


def cross_station_meta_test_commands_for_changed_files(
    changed_files: tuple[str, ...],
) -> tuple[str, ...]:
    """Derive per-owner ``pytest -q`` commands for cross-station meta-tests."""
    if not _touches_any_station_package_src(changed_files):
        return ()
    by_env: dict[str, list[str]] = {}
    for env, test_path in _CROSS_STATION_META_TESTS:
        by_env.setdefault(env, []).append(test_path)
    return tuple(
        f"pixi run --frozen -e {env} python -m pytest -q {' '.join(sorted(paths))}"
        for env, paths in sorted(by_env.items())
    )


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

    Story 83.23 (spec-83-23): when the diff touches any
    ``src/shared/packages/pyforge-*/src/`` path (including ``pyforge-core``
    and ``pyforge-testing-kit``), append each cross-station meta-test in its
    owning station's pixi env -- one ``pytest -q`` per owner, sorted by env.

    Unlike the loop adapter, this is not a rendered file an operator can
    read before a run starts -- it is folded in at USE time, right before
    the commands actually execute and before ``check_spec_binding`` sees
    them, so a dispatch session is gated on the guard exactly like a loop
    session even though nothing in ``marshal-policy.toml`` ever declares
    it."""
    coverage_derived = coverage_gate_commands_for_changed_files(changed_files or ())
    meta_derived = cross_station_meta_test_commands_for_changed_files(changed_files or ())
    derived = (
        _SURFACE_RECONCILE_COMMAND,
        _LINT_TYPES_COMMAND,
        _PYFORGE_CORE_TEST_COMMAND,
        _DEFERRED_WORK_CHECK_COMMAND,
        *coverage_derived,
        *meta_derived,
    )
    normalized_derived = {" ".join(command.split()) for command in derived}
    verify = [c for c in effective.verify_commands.value if " ".join(c.split()) not in normalized_derived]
    verify.extend(derived)
    return tuple(verify)


def verify_gate_set(effective: EffectivePolicy, *, changed_files: tuple[str, ...]) -> tuple[str, ...]:
    """Story 102.1 review fix 1: every gate command a full dispatch verification of ``changed_files`` runs, in order
    -- the station's own and the derived ``_verify_commands_with_surface_guard`` set, then the cross-surface rules the
    diff triggers -- so its digest (``core.dispatch_reverify.gate_set_digest``) moves whenever a policy edit or a
    derivation change would make a fresh verification run different gates."""
    commands = list(_verify_commands_with_surface_guard(effective, changed_files=changed_files))
    for rule in gate.cross_surface_rules_for_changed_files(changed_files):
        if rule.command not in commands:
            commands.append(rule.command)
    return tuple(commands)


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

        # Story 83.19: dispatch's own commits leave the CFE surface uncommitted; commit it here
        # once, as `retro(cfe):`, when the CFE CHANGELOG.md moves with it -- else refuse (Rule 2).
        try:
            dirty_paths = vcs.changed_files(repo_root, worktree, base="HEAD")
        except Exception as exc:
            findings.append(
                Finding(
                    code="MRS-GATE-009",
                    severity=Severity.ERROR,
                    message=f"dispatch CFE retro commit could not read the worktree's dirty paths: {exc}",
                )
            )
            data["cfe_retro_commit"] = {"checked": False, "reason": str(exc)}
        else:
            cfe_retro = commit_pending_cfe_retro(
                committing_vcs,
                worktree=worktree,
                changed_paths=dirty_paths,
                story_key=str(story_key),
                repo_root=repo_root,
            )
            data["cfe_retro_commit"] = {
                "checked": True,
                "committed": cfe_retro.committed,
                "paths": list(cfe_retro.paths),
            }
            if cfe_retro.finding is not None:
                findings.append(cfe_retro.finding)

    cfe_findings, cfe_report = check_unsanctioned_cfe_commits(worktree=worktree, process=process, base=_SCOPE_BASE)
    findings.extend(cfe_findings)
    data["cfe_unsanctioned_commits_check"] = cfe_report

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
    # Story 102.1 review fix 1: the digest of the gate set this verdict ran, journaled on its OUTCOME, so a later
    # re-landing can tell when the gates themselves moved (a policy edit, a derivation change) and re-verify.
    data[GATE_DIGEST_FIELD] = gate_set_digest(verify_gate_set(effective, changed_files=scope_changed_files))
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
        # Story 83.23: cross-station meta-tests read every station's ``src/``
        # and must refuse like the other whole-tree derived commands.
        derived_commands = {
            _SURFACE_RECONCILE_COMMAND,
            _LINT_TYPES_COMMAND,
            _PYFORGE_CORE_TEST_COMMAND,
            _DEFERRED_WORK_CHECK_COMMAND,
            *coverage_gate_commands_for_changed_files(scope_changed_files),
            *cross_station_meta_test_commands_for_changed_files(scope_changed_files),
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

    cross_surface_check_entries: list[dict[str, object]] = []
    if scope_check_completed:
        matched_cross_rules = gate.cross_surface_rules_for_changed_files(scope_changed_files)
        for rule in matched_cross_rules:
            cross_report, cross_finding = _run_verify_command(
                rule.command,
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
                if rule.rule_id == "environment-yaml" and cross_finding.code == gate.CROSS_SURFACE_GATE_CODE:
                    cross_finding = Finding(
                        code=gate.CROSS_SURFACE_GATE_CODE,
                        severity=cross_finding.severity,
                        message=(
                            f"{cross_finding.message} "
                            f"environment.yaml must match the pixi export; "
                            f"fix with: {gate.ENVIRONMENT_YAML_FIX_COMMAND}"
                        ),
                    )
                findings.append(cross_finding)
            cross_surface_check_entries.append(
                {
                    "rule_id": rule.rule_id,
                    "command": rule.command,
                    "touched_paths": list(gate.touched_paths_for_cross_surface_rule(scope_changed_files, rule)),
                    "report": cross_report,
                }
            )
    if cross_surface_check_entries:
        data["cross_surface_checks"] = cross_surface_check_entries
        if len(cross_surface_check_entries) == 1:
            only = cross_surface_check_entries[0]
            data["cross_surface_check"] = {
                "checked": True,
                "command": only["command"],
                "touched_paths": only["touched_paths"],
                "report": only["report"],
            }
        else:
            data["cross_surface_check"] = {
                "checked": True,
                "commands": [entry["command"] for entry in cross_surface_check_entries],
                "checks": cross_surface_check_entries,
            }
    else:
        data["cross_surface_check"] = {
            "checked": False,
            "reason": (
                "scope check incomplete" if not scope_check_completed else "diff does not touch any cross-surface rule"
            ),
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


def run_dispatch_environment_yaml_before_verify(
    *,
    worktree: Path,
    repo_root: Path,
    vcs: CommittingVcs,
    process: ProcessPort,
) -> DispatchEnvironmentYamlResult:
    """Story 91.1 entry: regenerate ``environment.yaml`` from exporter stdout before verify."""
    return apply_dispatch_environment_yaml_before_verify(
        worktree=worktree,
        repo_root=repo_root,
        vcs=vcs,
        process=process,
    )


def run_dispatch_spec_frontmatter_before_verify(
    *,
    worktree: Path,
    repo_root: Path,
    vcs: CommittingVcs,
    blame_vcs: VcsPort,
) -> DispatchSpecFrontmatterResult:
    """Story 96.1 entry: collapse repeated story-spec frontmatter keys before verify."""
    return apply_dispatch_spec_frontmatter_before_verify(
        worktree=worktree,
        repo_root=repo_root,
        vcs=vcs,
        blame_vcs=blame_vcs,
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


def landing_ci_pauses_enabled(*, repo_root: Path) -> tuple[bool, str | None]:
    """Read ``pyforge.marshal.landing_ci_pauses``; unreadable tree reads as off."""
    from .core.landing_ci_pauses import LANDING_CI_PAUSES_FLAG_KEY

    flags_path = repo_root / "src/platform/config/flags.json"
    try:
        return read_boolean(LANDING_CI_PAUSES_FLAG_KEY, default=False, flags_path=flags_path), None
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


_DEFAULT_SESSION_GROUP = PsutilSessionGroup()


@dataclass(frozen=True)
class DispatchSessionLiveness:
    """Story 92.1: dispatch session liveness, with the group read's error when that read failed."""

    alive: bool
    liveness_error: str | None = None


def _process_cmdline(pid: int) -> str | None:
    """The impure cmdline read behind the identity fallback; a unit test replaces it, never a real pid's."""
    return process_cmdline(pid)


def _cmdline_names_binary(pid: int, binary: str) -> bool:
    cmdline = _process_cmdline(pid)
    if not cmdline:
        return False
    name = Path(binary).name or binary
    return name in cmdline


def harness_binary_for_profile(profile_name: str | None, *, repo_root: Path | None) -> str | None:
    """Story 92.1: the ``binary`` a run's harness profile declares (packaged profiles, overlaid by
    ``repo_root``'s), or ``None`` when the run names no profile or the profile cannot be loaded -- the identity
    fallback then has no cmdline to match, and an unreadable start time reads not alive."""
    if not profile_name:
        return None
    try:
        profiles, _overlay_errors = load_profiles(repo_root)
    except HarnessProfileError, OSError:
        return None
    profile = profiles.get(profile_name)
    return profile.binary if profile is not None else None


def _member_started_with_session(start_time: float | None, launched_at: datetime | None) -> bool:
    """Story 92.1: a group member counts when it started at or after the launch, less Story 83.1's clock allowance,
    with no upper bound -- a child the session starts hours in is still the session. One that started earlier is
    another process."""
    if launched_at is None:
        return True
    if start_time is None:
        return False
    return start_time >= launched_at.timestamp() - dispatch_core.PID_START_TOLERANCE_SECONDS


def identity_checked_leader_alive(
    process: ProcessPort,
    pid: int,
    *,
    launched_at: datetime | None,
    harness_binary: str | None = None,
) -> bool:
    """Story 92.1: the answer when the group read failed -- the launched pid alone, with its identity checked.

    It must exist and not be a zombie, and it must be the launch's process: a start time inside Story 83.1's
    window, or, when the start time cannot be read, a cmdline naming the run's harness ``binary``. Anything
    else -- including an unreadable start time with no binary to match -- is not the session: a read error never
    degrades to alive."""
    if not process.is_alive(pid) or _is_zombie(pid):
        return False
    start_time = process.process_start_time(pid)
    if start_time is not None and launched_at is not None:
        return dispatch_core.pid_start_matches_launch(start_time, launched_at)
    if harness_binary and _cmdline_names_binary(pid, harness_binary):
        return True
    return False


def session_group_has_live_member(
    session_group: SessionGroupPort,
    session_leader_pid: int,
    *,
    launched_at: datetime | None,
    process: ProcessPort,
) -> tuple[bool, str | None]:
    """``(alive, read_error)``: alive when any non-zombie member of the launch's group started at or after the
    launch (Story 90.1/92.1). A failed read is ``(False, message)`` -- never alive."""
    try:
        members = tuple(session_group.iter_session_group_members(session_leader_pid))
    except SessionGroupReadError as exc:
        return False, str(exc)
    for member in members:
        if member.is_zombie:
            continue
        started_at = member.started_at
        if started_at is None:
            started_at = process.process_start_time(member.pid)
        if not _member_started_with_session(started_at, launched_at):
            continue
        return True, None
    return False, None


def assess_dispatch_session_liveness(
    process: ProcessPort,
    pid: int,
    *,
    launched_at: datetime | None,
    session_group: SessionGroupPort | None = None,
    harness_binary: str | None = None,
) -> DispatchSessionLiveness:
    """Story 83.1/90.1/92.1: is the dispatch session still running -- its leader, or any process of its group?

    1. A leader pid that exists, is not a zombie and has a readable start time outside Story 83.1's window is
       another process (pid reuse). The pid of a live process-group leader is never handed out again, so the
       session's own group has ended too: not alive, and the group is not read -- its members are the new
       process's.
    2. Otherwise the launch's process group is read (the session runs under ``start_new_session=True``, so its
       group id is the leader pid). A member that started at or after the launch keeps the session alive.
    3. When that read fails, the answer is the identity-checked leader (``identity_checked_leader_alive``), with
       the read's error carried for the heartbeat -- never "alive" for the error itself.
    4. A read that succeeded but found no member leaves Story 83.1's leader rule: an existing, non-zombie leader
       whose start time cannot be read (or whose launch is unknown) is judged by its existence."""
    leader_present = process.is_alive(pid) and not _is_zombie(pid)
    if leader_present and not dispatch_core.pid_start_matches_launch(process.process_start_time(pid), launched_at):
        return DispatchSessionLiveness(alive=False)
    port = session_group if session_group is not None else _DEFAULT_SESSION_GROUP
    group_alive, liveness_error = session_group_has_live_member(port, pid, launched_at=launched_at, process=process)
    if group_alive:
        return DispatchSessionLiveness(alive=True)
    if liveness_error is not None:
        return DispatchSessionLiveness(
            alive=identity_checked_leader_alive(process, pid, launched_at=launched_at, harness_binary=harness_binary),
            liveness_error=liveness_error,
        )
    return DispatchSessionLiveness(alive=leader_present)


def dispatch_session_alive(
    process: ProcessPort,
    pid: int,
    *,
    launched_at: datetime | None,
    session_group: SessionGroupPort | None = None,
    harness_binary: str | None = None,
) -> bool:
    """Story 83.1/90.1/92.1: dispatch session liveness -- ``assess_dispatch_session_liveness``'s answer alone."""
    return assess_dispatch_session_liveness(
        process,
        pid,
        launched_at=launched_at,
        session_group=session_group,
        harness_binary=harness_binary,
    ).alive


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


# --- Story 102.1 (spec-pyforge-marshal CAP-161): landing verdict reuse -------------------------------------------
#
# ``core.dispatch_reverify`` judges whether a re-landing may reuse its run's verified verdict; the functions below
# gather what that judgement reads and run what an exempt reuse still checks. They read git through the
# ``ProcessPort`` seam, as ``check_branch_commit_attribution`` above does, and every git call is a read:
# ``merge-tree --write-tree`` writes only unreferenced objects, as the landing's own merge preview already does. Only
# ``cli/dispatch.py``'s land-only path consults them, and only under the station policy
# ``dispatch.landing_reverify = "on-code-change"``; the supervisor reads ``verification_head_sha`` alone, to journal
# the head every verdict judged.

#: The narrow re-check's commands: the full verification's own planning-surface checks -- the S-13.7 guard (the
#: same ``gather_spec_surface`` verdict as ``spec-surface-check``) and ``deferred-work-check`` -- plus
#: ``story-status-check``. Never a station suite: those are what a reuse skips.
STORY_STATUS_CHECK_COMMAND = "pixi run --frozen -e pyforge-guild story-status-check"
REUSE_RECHECK_COMMANDS: tuple[str, ...] = (
    _SURFACE_RECONCILE_COMMAND,
    STORY_STATUS_CHECK_COMMAND,
    _DEFERRED_WORK_CHECK_COMMAND,
)

_GIT_TIMEOUT_S = 120.0


class _GitReadError(PyforgeError, Exception):
    """A git read this module needs did not answer; the reuse is declined (``git-read-failed``)."""


def _git(process: ProcessPort, worktree: Path, *args: str, ok_codes: tuple[int, ...] = (0,)) -> ProcessResult:
    argv = ["git", "-C", str(worktree), *args]
    try:
        result = process.run(argv, cwd=worktree, timeout_s=_GIT_TIMEOUT_S)
    except ProcessError as exc:
        raise _GitReadError(f"git {' '.join(args[:2])} could not run: {exc}") from exc
    if result.returncode not in ok_codes:
        detail = (result.stderr or result.stdout or "").strip()
        raise _GitReadError(f"git {' '.join(args[:2])} exited {result.returncode}: {detail}")
    return result


def _z_paths(stdout: str) -> tuple[str, ...]:
    return tuple(sorted({path for path in stdout.split("\0") if path}))


def _paths_between(process: ProcessPort, worktree: Path, old: str, new: str) -> tuple[str, ...]:
    """Every path that differs between two tree-ishes, both ends of a rename named (``--no-renames``)."""
    return _z_paths(_git(process, worktree, "diff", "--name-only", "--no-renames", "-z", old, new).stdout)


def _is_ancestor(process: ProcessPort, worktree: Path, ancestor: str, descendant: str) -> bool:
    result = _git(process, worktree, "merge-base", "--is-ancestor", ancestor, descendant, ok_codes=(0, 1))
    return result.returncode == 0


def _on_first_parent_chain(process: ProcessPort, worktree: Path, commit: str, base: str) -> bool:
    """Review fix 2 (PR #2238): ``commit`` is a state ``base`` was itself in -- on its first-parent chain, not merely
    an ancestor (a commit inside a branch main merged, say). The walk is bounded by ``commit``'s own parents, so it
    lists only main's first-parent commits since ``commit``."""
    if not _is_ancestor(process, worktree, commit, base):
        return False
    parents = _git(process, worktree, "rev-list", "--parents", "-n", "1", commit).stdout.split()[1:]
    args = ["rev-list", "--first-parent", base]
    if parents:
        args += ["--not", *parents]
    return commit in _git(process, worktree, *args).stdout.split()


def _replay_merge(process: ProcessPort, worktree: Path, first: str, second: str) -> tuple[str, tuple[str, ...]]:
    """The merge replayed: its tree's oid and the paths git reports conflicted (content, modify/delete and add/add
    alike). Exit 0 is clean and 1 conflicted, each with the tree oid first; a conflict that names no path cannot be
    judged, so it is a read failure, never a clean merge."""
    result = _git(
        process,
        worktree,
        "merge-tree",
        "--write-tree",
        "--name-only",
        "-z",
        "--no-messages",
        first,
        second,
        ok_codes=(0, 1),
    )
    fields = result.stdout.split("\0")
    tree = fields[0].strip()
    if not tree:
        raise _GitReadError(f"git merge-tree {first} {second} printed no tree")
    conflicts = tuple(sorted({path for path in fields[1:] if path}))
    if result.returncode == 1 and not conflicts:
        raise _GitReadError(f"git merge-tree {first} {second} reported a conflict that names no path")
    return tree, conflicts


def _first_parent_chain(
    process: ProcessPort, worktree: Path, verified_head: str, current_head: str, *, max_commits: int
) -> list[tuple[str, tuple[str, ...]]] | None:
    """``current_head``'s first-parent chain down to ``verified_head``, newest first, each ``(sha, parents)``; ``None``
    when ``verified_head`` is not on it or the chain is longer than ``max_commits``."""
    stdout = _git(
        process, worktree, "rev-list", "--first-parent", "--parents", f"{verified_head}..{current_head}"
    ).stdout
    chain: list[tuple[str, tuple[str, ...]]] = []
    for line in stdout.splitlines():
        parts = line.split()
        if not parts:
            continue
        chain.append((parts[0], tuple(parts[1:])))
        if len(chain) > max_commits:
            return None
    if not chain or not chain[-1][1] or chain[-1][1][0] != verified_head:
        return None
    return chain


def gather_reuse_facts(
    *,
    process: ProcessPort,
    worktree: Path,
    verified_head: str,
    current_head: str,
    story_spec_rel: str | None,
    base: str = ORIGIN_MAIN,
    max_commits: int = MAX_CHAIN_COMMITS,
) -> ReuseFacts:
    """What git says about the move from ``verified_head`` to ``current_head`` in ``worktree``.

    Raises ``_GitReadError`` when a read fails; ``attempt_verdict_reuse`` turns that into a declined reuse."""
    story_paths = _z_paths(
        _git(process, worktree, "diff", "--name-only", "--no-renames", "-z", f"{base}...{verified_head}").stdout
    )
    if verified_head == current_head:
        return ReuseFacts(
            verified_head=verified_head,
            current_head=current_head,
            story_paths=story_paths,
            chain=(),
            story_spec_rel=story_spec_rel,
        )
    walked = _first_parent_chain(process, worktree, verified_head, current_head, max_commits=max_commits)
    if walked is None:
        return ReuseFacts(
            verified_head=verified_head,
            current_head=current_head,
            story_paths=story_paths,
            chain=None,
            story_spec_rel=story_spec_rel,
        )
    chain: list[ChainCommit] = []
    for sha, parents in walked:
        changed = _paths_between(process, worktree, parents[0], sha)
        if len(parents) != 2:
            chain.append(ChainCommit(sha=sha, parents=parents, changed_paths=changed))
            continue
        on_main = _on_first_parent_chain(process, worktree, parents[1], base)
        conflicts: tuple[str, ...] = ()
        resolution: tuple[str, ...] = ()
        if on_main:
            replay_tree, conflicts = _replay_merge(process, worktree, parents[0], parents[1])
            resolution = _paths_between(process, worktree, replay_tree, sha)
        chain.append(
            ChainCommit(
                sha=sha,
                parents=parents,
                changed_paths=changed,
                second_parent_on_main=on_main,
                replay_conflicts=conflicts,
                resolution_paths=resolution,
            )
        )
    # Review fix 2: every non-planning path a merge brought from main must still read current main's content -- a
    # merge of a main commit later reverted, or a path main moved again since, is not the tree main would land.
    brought = {
        path
        for commit in chain
        if len(commit.parents) == 2
        for path in commit.changed_paths
        if not is_planning_path(path, story_spec_rel=story_spec_rel)
    }
    stale: tuple[str, ...] = ()
    if brought:
        stale = tuple(sorted(brought & set(_paths_between(process, worktree, current_head, base))))
    return ReuseFacts(
        verified_head=verified_head,
        current_head=current_head,
        story_paths=story_paths,
        chain=tuple(chain),
        story_spec_rel=story_spec_rel,
        stale_main_paths=stale,
    )


def verification_head_sha(vcs: object, worktree: Path) -> str | None:
    """The worktree ``HEAD`` a verification just judged, or ``None`` when the tree is dirty (the verdict then judged
    files no commit holds) or either read fails. Duck-typed on ``worktree_head_sha`` and
    ``has_uncommitted_changes`` so a port without them records no head instead of failing a verification."""
    head_of = getattr(vcs, "worktree_head_sha", None)
    dirty_of = getattr(vcs, "has_uncommitted_changes", None)
    if not callable(head_of) or not callable(dirty_of):
        return None
    try:
        if dirty_of(worktree):
            return None
        head = head_of(worktree)
    except Exception:  # a head we cannot read is a head we do not record, never a failed verdict
        return None
    return head if isinstance(head, str) and head else None


@dataclass(frozen=True)
class VerdictReuse:
    """One reuse attempt. ``reused`` is true only for an exempt decision whose narrow re-check was green; then
    ``candidate`` is the full verdict reused and ``current_head`` the head it now stands for. ``findings`` and
    ``verify_data`` are the narrow re-check's."""

    decision: ReuseDecision
    candidate: ReuseCandidate | None = None
    current_head: str | None = None
    findings: tuple[Finding, ...] = ()
    verify_data: Mapping[str, object] = field(default_factory=dict)
    recheck_green: bool = False

    @property
    def reused(self) -> bool:
        return self.decision.exempt and self.recheck_green and self.candidate is not None

    def declined_payload(self) -> dict[str, object] | None:
        """``{"reason", "detail"}`` for a declined reuse, else ``None``."""
        if self.reused:
            return None
        if self.decision.exempt:
            return {"reason": REASON_RECHECK_FAILED, "detail": _first_failure(self.findings)}
        return {"reason": self.decision.reason, "detail": self.decision.detail}


def _first_failure(findings: tuple[Finding, ...]) -> str:
    for finding in findings:
        if status_for(compute_verdict((finding,))) is not Status.OK:
            return f"{finding.code}: {finding.message}"
    return ""


def run_reuse_recheck(
    *,
    process: ProcessPort,
    worktree: Path,
    repo_root: Path,
    base: str = ORIGIN_MAIN,
) -> tuple[tuple[Finding, ...], dict[str, object]]:
    """The narrow re-check an exempt reuse still runs: the two commit checks over ``base...HEAD`` (the merge commits
    are new, and no reused verdict judged their messages or files) and ``REUSE_RECHECK_COMMANDS`` in the worktree."""
    findings: list[Finding] = []
    data: dict[str, object] = {}
    cfe_findings, cfe_report = check_unsanctioned_cfe_commits(worktree=worktree, process=process, base=base)
    findings.extend(cfe_findings)
    data["cfe_unsanctioned_commits_check"] = cfe_report
    attribution_findings, attribution_report = check_branch_commit_attribution(
        worktree=worktree, process=process, repo_root=repo_root, base=base
    )
    findings.extend(attribution_findings)
    data["commit_attribution_check"] = attribution_report
    reports: list[dict[str, object]] = []
    for command in REUSE_RECHECK_COMMANDS:
        report, finding = _run_verify_command(command, process=process, worktree=worktree)
        reports.append(report)
        if finding is not None:
            findings.append(finding)
    data["commands"] = reports
    return tuple(findings), data


def attempt_verdict_reuse(
    *,
    folded: FoldResult,
    run_id: str,
    worktree: Path,
    repo_root: Path,
    story_spec_rel: str | None,
    process: ProcessPort,
    vcs: object,
    sidecars: Mapping[str, str | None] | None = None,
    base: str = ORIGIN_MAIN,
    recheck: Callable[..., tuple[tuple[Finding, ...], dict[str, object]]] | None = None,
    current_gate_digest: str | None = None,
) -> VerdictReuse:
    """Story 102.1: whether this re-landing may reuse the run's verified verdict, and the narrow re-check if so.

    Declines (the caller re-verifies in full) on no reusable verdict, a gate set that moved since the verdict
    (review fix 1: ``current_gate_digest`` is the digest of ``verify_gate_set`` for the policy and diff a fresh
    verification would use now; a missing digest on either side declines), a dirty worktree, an unreadable head or
    git fact, any non-exempt move, or a red narrow re-check. Never raises for a git read; ``recheck`` defaults to
    ``run_reuse_recheck``."""
    resolved_sidecars = sidecars or {}

    def _advisories_of(entry: JournalEntry) -> tuple[Mapping[str, object], ...]:
        return tuple(resolve_scope_violation_advisories_from_payload(entry.payload, sidecars=resolved_sidecars))

    candidate = latest_reusable_verdict(folded, run_id, advisories_of=_advisories_of)
    if candidate is None:
        return VerdictReuse(
            decision=declined(
                REASON_NO_VERIFIED_VERDICT,
                "the run's latest verification OUTCOME is not a verified verdict with a recorded head",
            )
        )
    if candidate.gate_digest is None or current_gate_digest is None or candidate.gate_digest != current_gate_digest:
        return VerdictReuse(
            decision=declined(
                REASON_GATE_SET_CHANGED,
                f"the verdict ran gate set {candidate.gate_digest or 'unrecorded'}; "
                f"a fresh verification would run {current_gate_digest or 'an unknown set'}",
            ),
            candidate=candidate,
        )
    current_head = verification_head_sha(vcs, worktree)
    if current_head is None:
        return VerdictReuse(
            decision=declined(REASON_DIRTY_WORKTREE, f"worktree {worktree} is dirty or its head is unreadable"),
            candidate=candidate,
        )
    try:
        facts = gather_reuse_facts(
            process=process,
            worktree=worktree,
            verified_head=candidate.head_sha,
            current_head=current_head,
            story_spec_rel=story_spec_rel,
            base=base,
        )
    except _GitReadError as exc:
        return VerdictReuse(
            decision=declined(REASON_GIT_READ_FAILED, str(exc)), candidate=candidate, current_head=current_head
        )
    decision = judge_verdict_reuse(facts)
    if not decision.exempt:
        return VerdictReuse(decision=decision, candidate=candidate, current_head=current_head)
    run_recheck = recheck if recheck is not None else run_reuse_recheck
    findings, data = run_recheck(process=process, worktree=worktree, repo_root=repo_root, base=base)
    green = status_for(compute_verdict(tuple(findings))) is Status.OK
    return VerdictReuse(
        decision=decision,
        candidate=candidate,
        current_head=current_head,
        findings=tuple(findings),
        verify_data=data,
        recheck_green=green,
    )
