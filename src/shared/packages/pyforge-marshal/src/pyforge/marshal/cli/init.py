"""``marshal init`` (Story 1.4, FR-1/FR-2, AD-11/AD-21) -- provisions an
isolated loop home: a git worktree at ``<loop-home-root>/<slug>`` on branch
``loop/<slug>``, carrying its own BMAD active-project marker
(``_bmad/custom/.active-project``) and ``_bmad-output/planning-artifacts``
symlink. Idempotent (AD-21, reconcile-then-act): each of the three steps
(worktree, symlink, marker) is checked against real state via
``ports.VcsPort``/``ports.FsPort`` before any write is attempted, so a
re-run against an already-converged home performs zero writes and still
exits 0.

Ports this ``git worktree`` provisioning logic from ``scripts/bmad-loop-worktree``
(the ``home_path``/``loop_home_root``/``provision`` functions) plus the
marker/symlink primitives from ``scripts/bmad-switch`` into Marshal's own
``VcsPort``/``FsPort`` seam, rather than shelling out to either script --
see ``ports/vcs.py``/``ports/fs.py`` and the spec's Design Notes for why
(the AD-11 write-boundary meta-test needs every write observable through
Marshal's own ports). Deliberately simplified relative to the reference
scripts: no legacy sibling-repo layout (the spec's own Boundaries &
Constraints -- "do not reinvent the sibling-repo layout"), and no Tier-3
backlink (that is Story 1.5's ``ensure_tier3_backlink`` surface, out of
scope here -- a fresh home carries only the ``planning-artifacts`` symlink).

Slug shape validation reuses ``core.policy._is_valid_project_slug`` directly
(a deliberate cross-module private import within this package, per the
spec's own instruction) rather than a second regex.

``repo_common_root`` is resolved from the CURRENT WORKING DIRECTORY -- a
CLI-boundary read, like ``cli/config.py``'s own ``BMAD_ACTIVE_PROJECT`` env
read -- so ``marshal init`` works whether invoked from the main checkout or
from inside another linked worktree. ``BMAD_LOOP_HOME_ROOT`` is read the
same way (mirrors the reference script's own env var).

Ordering: the marker/symlink DESYNC check runs before any write in this
invocation (a prior partial failure left the two naming different slugs --
``MRS-INIT-003``, blocking); the symlink is written BEFORE the marker
(mirrors ``scripts/bmad-switch``'s own ordering rationale -- the marker must
never advance past a symlink that failed to move). Each of the three steps
reports exactly one of ``done``/``skipped``/``failed`` in the envelope's
``data.steps``; an unattempted step (because an earlier step failed or
blocked) reports ``failed`` too, since it did not converge either.

``MRS-INIT-001`` (malformed slug) and ``MRS-INIT-002`` (unknown project)
classify ``Verdict.UNEVALUABLE`` and involve NO I/O at all -- checked before
``repo_common_root`` is even resolved for -001, and before any worktree/
marker/symlink write for -002. ``MRS-INIT-003`` (desync) and
``MRS-INIT-004`` (any git/filesystem operation failure, including
resolving the repo root itself) classify ``Verdict.ERROR``.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from pathlib import Path

from ..adapters.fs_local import FsWriteError, LocalFs
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import policy
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.fs import FsPort
from ..ports.vcs import VcsPort
from .config import _suppress_downstream_pipe_close

ENV_LOOP_HOME_ROOT = "BMAD_LOOP_HOME_ROOT"

_STEP_NAMES: tuple[str, ...] = ("worktree", "symlink", "marker")


def add_init_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``init`` subcommand on ``main.py``'s subparser tree."""
    parser = subparsers.add_parser(
        "init",
        help="Provision an isolated loop home for a BMAD project (AD-11/AD-21).",
        description=(
            "Idempotently provisions a git worktree at "
            "<loop-home-root>/<slug> on branch loop/<slug>, with its own "
            "active-project marker and planning-artifacts symlink. "
            "Re-running against an already-converged home performs zero "
            "writes and exits 0."
        ),
    )
    parser.add_argument("slug", help="The BMAD project slug to provision a loop home for.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.set_defaults(handler=run_init)


def _loop_home_root() -> Path:
    override = os.environ.get(ENV_LOOP_HOME_ROOT)
    return Path(override).expanduser() if override else Path.home() / ".bmad-loops"


def _home_path(slug: str) -> Path:
    return _loop_home_root() / slug


def _slug_from_marker(text: str | None) -> str | None:
    if text is None:
        return None
    value = text.strip()
    return value or None


def _slug_from_symlink_target(target: Path | None) -> str | None:
    """Parse ``projects/<slug>/planning-artifacts`` (mirrors
    ``scripts/bmad-switch``'s ``read_link_slugs``) -- any other shape
    (missing, absolute, wrong depth) is unrecognized, not a slug."""
    if target is None:
        return None
    parts = target.parts
    if len(parts) == 3 and parts[0] == "projects" and parts[2] == "planning-artifacts":
        return parts[1]
    return None


def _op_failed_finding(message: str) -> Finding:
    return Finding(code="MRS-INIT-004", severity=Severity.ERROR, message=message)


def run_init(
    args: argparse.Namespace,
    *,
    vcs: VcsPort | None = None,
    fs: FsPort | None = None,
) -> int:
    vcs = vcs if vcs is not None else GitVcs()
    fs = fs if fs is not None else LocalFs()

    slug = args.slug
    findings: list[Finding] = []
    data: dict[str, object] = {"slug": slug}

    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-INIT-001",
                severity=Severity.ERROR,
                message=(
                    f"malformed project slug {slug!r} -- must be one safe "
                    "path segment (letters, digits, '.', '_', '-'; not '.' "
                    "or '..'; at most 255 characters)"
                ),
            )
        )
        return _emit(args, data, findings)

    try:
        repo_root = vcs.repo_common_root(Path.cwd())
    except VcsCommandError as exc:
        findings.append(_op_failed_finding(f"resolving the repo root: {exc}"))
        return _emit(args, data, findings)
    data["repo_root"] = str(repo_root)

    # Checks the planning-artifacts subdirectory itself, not just its parent
    # project dir (review finding: checking only the parent let a project
    # missing planning-artifacts pass this gate, and the symlink step below
    # would then happily create a DANGLING link -- mirrors
    # scripts/bmad-switch's own repoint_links, which validates each
    # symlink's target directory before ever writing the link).
    planning_dir = repo_root / "_bmad-output" / "projects" / slug / "planning-artifacts"
    if not fs.is_dir(planning_dir):
        findings.append(
            Finding(
                code="MRS-INIT-002",
                severity=Severity.ERROR,
                message=(
                    f"no such BMAD project: {slug!r} -- {planning_dir} does "
                    "not exist on main"
                ),
                path=str(planning_dir),
            )
        )
        return _emit(args, data, findings)

    home = _home_path(slug)
    branch = f"loop/{slug}"
    data["home"] = str(home)
    data["branch"] = branch
    steps: dict[str, str] = {name: "failed" for name in _STEP_NAMES}
    data["steps"] = steps

    # --- step 1: worktree (reconcile-then-act against git's own truth) ------
    try:
        existing = vcs.worktree_path_for_branch(repo_root, branch)
    except VcsCommandError as exc:
        findings.append(_op_failed_finding(f"resolving worktree state for {branch}: {exc}"))
        return _emit(args, data, findings)

    if existing is not None and existing.resolve() == home.resolve():
        # git still registers the worktree, but its directory may have been
        # deleted by hand rather than via `git worktree remove` (this repo's
        # own history has hit exactly that -- a failed removal still
        # de-registers). Trusting git's record alone would silently write
        # the marker/symlink into a phantom, non-functioning path.
        if not fs.is_dir(home):
            findings.append(
                _op_failed_finding(
                    f"git still registers a worktree for {branch} at {home}, "
                    "but that directory does not exist on disk (a stale/"
                    "prunable entry) -- run 'git worktree prune' and re-run "
                    "marshal init"
                )
            )
            return _emit(args, data, findings)
        steps["worktree"] = "skipped"
    elif existing is not None:
        findings.append(
            _op_failed_finding(
                f"branch {branch} is already checked out at {existing}, "
                f"expected {home} -- refusing to attempt a second worktree "
                "for the same branch"
            )
        )
        return _emit(args, data, findings)
    else:
        try:
            vcs.add_worktree(repo_root, home, branch, base="main")
            steps["worktree"] = "done"
        except VcsCommandError as exc:
            findings.append(_op_failed_finding(str(exc)))
            return _emit(args, data, findings)

    # --- desync check: BLOCKING, before any further write -------------------
    marker_path = home / "_bmad" / "custom" / ".active-project"
    link_path = home / "_bmad-output" / "planning-artifacts"

    try:
        marker_slug = _slug_from_marker(fs.read_text(marker_path))
        link_slug = _slug_from_symlink_target(fs.read_symlink_target(link_path))
    except FsWriteError as exc:
        findings.append(_op_failed_finding(f"reading marker/symlink state: {exc}"))
        return _emit(args, data, findings)

    if marker_slug is not None and link_slug is not None and marker_slug != link_slug:
        findings.append(
            Finding(
                code="MRS-INIT-003",
                severity=Severity.ERROR,
                message=(
                    f"marker/symlink desync in {home}: marker says "
                    f"{marker_slug!r} but planning-artifacts symlink says "
                    f"{link_slug!r} -- a prior partial failure left them "
                    "disagreeing; resolve by hand before re-running"
                ),
                path=str(home),
            )
        )
        return _emit(args, data, findings)

    # --- step 2: symlink, written BEFORE the marker --------------------------
    if link_slug == slug:
        steps["symlink"] = "skipped"
    else:
        target = Path("projects") / slug / "planning-artifacts"
        try:
            fs.repoint_symlink_atomic(link_path, target)
            steps["symlink"] = "done"
        except FsWriteError as exc:
            findings.append(_op_failed_finding(str(exc)))
            return _emit(args, data, findings)

    # --- step 3: marker -------------------------------------------------------
    if marker_slug == slug:
        steps["marker"] = "skipped"
    else:
        try:
            fs.write_text_atomic(marker_path, slug + "\n")
            steps["marker"] = "done"
        except FsWriteError as exc:
            findings.append(_op_failed_finding(str(exc)))
            return _emit(args, data, findings)

    data["launch_line"] = f"cd {home} && export BMAD_ACTIVE_PROJECT={slug}"
    return _emit(args, data, findings)


def _render_text(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching ``cli/config.py``'s own
    ``_render_text`` convention."""
    lines = [f"init: {data['slug']}"]
    if "home" in data:
        lines.append(f"home: {data['home']}")
    if "branch" in data:
        lines.append(f"branch: {data['branch']}")
    if "steps" in data:
        lines.append("steps:")
        for name in _STEP_NAMES:
            lines.append(f"  {name}: {data['steps'][name]}")
    if "launch_line" in data:
        lines.append(f"launch: {data['launch_line']}")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)


def _emit(args: argparse.Namespace, data: dict[str, object], findings: list[Finding]) -> int:
    verdict_value = compute_verdict(tuple(findings))
    envelope = build_envelope(
        command="init", verdict=verdict_value, data=data, findings=tuple(findings)
    )
    # flush=True + the broken-pipe guard mirror cli/config.py::run_config
    # exactly -- see that function's comment for the full rationale (stdout
    # is block-buffered when piped/redirected, so an un-flushed write never
    # touches the fd inside this guard).
    try:
        if args.format == "json":
            print(json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True), flush=True)
        else:
            print(_render_text(envelope.data, envelope.findings), flush=True)
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)
