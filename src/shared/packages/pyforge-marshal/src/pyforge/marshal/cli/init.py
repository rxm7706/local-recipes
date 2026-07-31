"""``marshal init`` (Stories 1.4/1.5, FR-1/FR-2/FR-3, AD-11/AD-21) --
provisions an isolated loop home: a git worktree at
``<loop-home-root>/<slug>`` on branch ``loop/<slug>``, carrying its own BMAD
active-project marker (``_bmad/custom/.active-project``),
``_bmad-output/planning-artifacts`` symlink, and a backlink from the home's
gitignored Tier-3 execution-artifact store
(``_bmad-output/projects/<slug>/implementation-artifacts``) to the main
checkout's canonical copy of the same path. Idempotent (AD-21,
reconcile-then-act): each of the four steps (worktree, tier3_backlink,
symlink, marker) is checked against real state via
``ports.VcsPort``/``ports.FsPort`` before any write is attempted, so a
re-run against an already-converged home performs zero writes and still
exits 0.

Ports this ``git worktree`` provisioning logic from ``scripts/bmad-loop-worktree``
(the ``home_path``/``loop_home_root``/``provision`` functions) plus the
marker/symlink primitives and ``ensure_tier3_backlink`` from
``scripts/bmad-switch`` into Marshal's own ``VcsPort``/``FsPort`` seam,
rather than shelling out to either script -- see ``ports/vcs.py``/
``ports/fs.py`` and the spec's Design Notes for why (the AD-11
write-boundary meta-test needs every write observable through Marshal's own
ports). Deliberately simplified relative to the reference scripts: no
legacy sibling-repo layout (the spec's own Boundaries & Constraints -- "do
not reinvent the sibling-repo layout"), and no top-level
``implementation-artifacts`` compatibility symlink (that lives in
``bmad-switch``'s separate ``repoint_links`` function, shared with
``planning-artifacts``, and stays out of this story's ``tier3_backlink``
scope -- see Story 1.5's spec Design Notes).

Slug shape validation reuses ``core.policy._is_valid_project_slug`` directly
(a deliberate cross-module private import within this package, per the
spec's own instruction) rather than a second regex.

``repo_common_root`` is resolved from the CURRENT WORKING DIRECTORY -- a
CLI-boundary read, like ``cli/config.py``'s own ``BMAD_ACTIVE_PROJECT`` env
read -- so ``marshal init`` works whether invoked from the main checkout or
from inside another linked worktree. ``BMAD_LOOP_HOME_ROOT`` is read the
same way (mirrors the reference script's own env var), then anchored to an
ABSOLUTE path (review finding: a relative override would be resolved
against ``repo_root`` by ``git -C`` but against the CWD by ``LocalFs``,
splitting the two writers across different homes).

Ordering: the ``tier3_backlink`` step runs right after the in-home project
gate and BEFORE the marker/symlink desync check (mirrors
``scripts/bmad-switch``'s own call order: ``ensure_tier3_backlink`` runs
before ``repoint_links``) -- it is entirely independent of the
``planning-artifacts`` marker/symlink pair and their desync guard, which
stays scoped to that pair exactly as Story 1.4 left it. Within the
marker/symlink pair, the DESYNC check runs before any write in this
invocation (a prior partial failure left the two naming different slugs, or
a symlink target this command never shaped -- ``MRS-INIT-003``, blocking);
the symlink is written BEFORE the marker (mirrors ``scripts/bmad-switch``'s
own ordering rationale -- the marker must never advance past a symlink that
failed to move). Once provisioning begins, each of the four steps reports
exactly one of ``done``/``skipped``/``failed`` in the envelope's
``data.steps``; an unattempted step (because an earlier step failed or
blocked) reports ``failed`` too, since it did not converge either. The
pre-provisioning gates (malformed slug, unknown project, repo-root
resolution failure) exit BEFORE ``data.steps`` exists -- their envelopes
carry no ``steps`` key at all.

``MRS-INIT-001`` (malformed slug, including slug shapes git rejects as a
branch-name component) and ``MRS-INIT-002`` (unknown project) classify
``Verdict.UNEVALUABLE`` and are checked before any write is attempted --
-001 before any I/O at all. ``MRS-INIT-003`` (desync), ``MRS-INIT-004``
(any git/filesystem operation failure, including resolving the repo root
itself, plus the blocking in-home check that the provisioned tree really
contains the project the symlink is about to target), and ``MRS-INIT-005``
(a real, non-empty directory already occupies the local Tier-3 path,
refusing the backlink) classify ``Verdict.ERROR``.

Story 1.6 adds a second, entirely READ-ONLY command in this same module,
``marshal homes`` (``add_homes_subparser``/``run_homes``, FR-4/FR-8): it
takes no slug argument, auto-discovers every ``loop/<slug>`` worktree via
``VcsPort.list_worktrees``, gathers each home's (and the main checkout's
own) marker/symlink/Tier-3-backlink state via ``FsPort``, and hands that
plain data to the new pure ``core/status.py`` module, which computes the
isolation checks and builds the response. ``run_homes`` performs the SAME
kind of CLI-boundary I/O ``run_init`` does (``Path.cwd()``,
``repo_common_root``) but never writes -- proven by
``tests/meta/test_ad11_write_boundary.py``'s recording-fake extension.
Its own three codes, ``MRS-HOMES-001`` (a home's or the main checkout's
marker/symlink/branch-derived-slug agreement check failed), ``MRS-HOMES-002``
(a home's Tier-3 backlink realpath does not match its canonical store), and
``MRS-HOMES-003`` (a ``git``/filesystem operation failed while gathering
state), all classify ``Verdict.ERROR`` -- see ``core/status.py``'s own
docstring for the full isolation-check design, and this story's spec's
Design Notes for why this command lives here rather than in a new
``cli/status.py`` (reserved for a later, broader fleet-visibility story).
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
from collections.abc import Mapping
from pathlib import Path

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.vcs_git import GitVcs, VcsCommandError
from ..core import policy, status
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.fs import FsPort
from ..ports.vcs import VcsPort, WorktreeEntry
from .config import _suppress_downstream_pipe_close

ENV_LOOP_HOME_ROOT = "BMAD_LOOP_HOME_ROOT"

_STEP_NAMES: tuple[str, ...] = ("worktree", "tier3_backlink", "symlink", "marker")


def add_init_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``init`` subcommand on ``main.py``'s subparser tree."""
    parser = subparsers.add_parser(
        "init",
        help="Provision an isolated loop home for a BMAD project (AD-11/AD-21).",
        description=(
            "Idempotently provisions a git worktree at "
            "<loop-home-root>/<slug> on branch loop/<slug>, with its own "
            "active-project marker, planning-artifacts symlink, and a "
            "backlink from its gitignored Tier-3 implementation-artifacts "
            "store to the main checkout's canonical copy. "
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


def add_homes_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``homes`` subcommand on ``main.py``'s subparser tree
    (Story 1.6, FR-4/FR-8). No slug argument -- full enumeration only."""
    parser = subparsers.add_parser(
        "homes",
        help="List every discovered loop home and verify isolation (FR-4/FR-8).",
        description=(
            "Auto-discovers every loop/<slug> git worktree, verifies each "
            "home's marker/symlink/branch-derived slug agree and its "
            "Tier-3 backlink resolves to the canonical store, and reports "
            "the main checkout's own marker/symlink self-consistency. "
            "Read-only -- never writes a marker, symlink, or backlink."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.set_defaults(handler=run_homes)


def _loop_home_root() -> Path:
    override = os.environ.get(ENV_LOOP_HOME_ROOT)
    root = Path(override).expanduser() if override else Path.home() / ".bmad-loops"
    if not root.is_absolute():
        # Anchor once, here: `git -C <repo_root> worktree add` resolves a
        # relative home against repo_root while LocalFs resolves against
        # the CWD -- left relative, the two writers land in DIFFERENT
        # directories and the command exits 0 over a split-brain home
        # (review finding).
        root = Path.cwd() / root
    return root


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

    # The shared shape check admits '.' freely, but the slug is also
    # interpolated into the branch name loop/<slug>, and git refuses a ref
    # component that starts/ends with '.', contains '..', or ends '.lock'
    # (review finding: those slugs died later as an opaque MRS-INIT-004
    # from git's own stderr instead of this crisp pre-I/O rejection). A
    # git-ref constraint on TOP of the shared check, not a second slug
    # regex -- the spec's single-shape-check rule still holds.
    if (
        slug.startswith(".")
        or slug.endswith(".")
        or ".." in slug
        or slug.endswith(".lock")
    ):
        findings.append(
            Finding(
                code="MRS-INIT-001",
                severity=Severity.ERROR,
                message=(
                    f"project slug {slug!r} is not usable as the git branch "
                    f"loop/{slug} -- a branch-name component must not start "
                    "or end with '.', contain '..', or end with '.lock'"
                ),
            )
        )
        return _emit(args, data, findings)

    try:
        invocation_dir = Path.cwd()
    except OSError as exc:
        # A deleted CWD (routine around concurrent worktree teardown) must
        # report through the envelope, not escape as a raw traceback
        # (review finding: Path.cwd() raises OSError, which the
        # VcsCommandError catch below never covered).
        findings.append(_op_failed_finding(f"resolving the current working directory: {exc}"))
        return _emit(args, data, findings)
    try:
        repo_root = vcs.repo_common_root(invocation_dir)
    except VcsCommandError as exc:
        findings.append(_op_failed_finding(f"resolving the repo root: {exc}"))
        return _emit(args, data, findings)
    data["repo_root"] = str(repo_root)

    # Checks the planning-artifacts subdirectory itself, not just its parent
    # project dir (review finding: checking only the parent let a project
    # missing planning-artifacts pass this gate, and the symlink step below
    # would then happily create a DANGLING link -- mirrors
    # scripts/bmad-switch's own repoint_links, which validates each
    # symlink's target directory before ever writing the link). This is the
    # cheap fail-fast against the MAIN CHECKOUT's working tree; the
    # authoritative gate against the tree the symlink actually resolves in
    # (the home's own checkout) runs after the worktree step below.
    planning_dir = repo_root / "_bmad-output" / "projects" / slug / "planning-artifacts"
    if not fs.is_dir(planning_dir):
        findings.append(
            Finding(
                code="MRS-INIT-002",
                severity=Severity.ERROR,
                message=(
                    f"no such BMAD project: {slug!r} -- {planning_dir} does "
                    "not exist in the main checkout"
                ),
                path=str(planning_dir),
            )
        )
        return _emit(args, data, findings)

    try:
        home = _home_path(slug)
    except (RuntimeError, OSError) as exc:
        # Path.home()/expanduser raise RuntimeError when HOME is
        # unresolvable (cron/systemd -- exactly Marshal's unattended
        # context), and the relative-override anchor's Path.cwd() can raise
        # OSError; both must land in the envelope (review finding).
        findings.append(_op_failed_finding(f"resolving the loop-home root: {exc}"))
        return _emit(args, data, findings)
    branch = f"loop/{slug}"
    data["home"] = str(home)
    data["branch"] = branch
    steps: dict[str, str] = {name: "failed" for name in _STEP_NAMES}
    data["steps"] = steps

    # --- step: worktree (reconcile-then-act against git's own truth) -------
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

    # --- in-home project gate: BLOCKING, before the symlink can dangle ------
    # The pre-flight above checked the MAIN CHECKOUT's tree, but the symlink
    # written below resolves inside the HOME's tree -- content from a fresh
    # mint of `main` or a pre-existing loop/<slug> branch, either of which
    # can lack the project even when the main checkout has it (review
    # finding: an uncommitted brand-new project -- exactly when init first
    # runs -- passed the pre-flight and exited 0 with a DANGLING symlink).
    home_planning_dir = home / "_bmad-output" / "projects" / slug / "planning-artifacts"
    if not fs.is_dir(home_planning_dir):
        findings.append(
            _op_failed_finding(
                f"the home's checked-out tree has no _bmad-output/projects/"
                f"{slug}/planning-artifacts (looked at {home_planning_dir}) "
                "-- the project exists in the main checkout but not in the "
                "tree the symlink would resolve in (uncommitted project, or "
                f"a stale {branch} branch); commit the project to main (or "
                "update the loop branch) and re-run"
            )
        )
        return _emit(args, data, findings)

    # --- step: tier3_backlink (Story 1.5) ------------------------------------
    # Symlinks the home's gitignored Tier-3 store to the main checkout's
    # canonical copy at the same repo-relative path (ports
    # scripts/bmad-switch::ensure_tier3_backlink). Runs before the
    # marker/symlink pair below and is entirely independent of their desync
    # guard -- this backlink has its own convergence check.
    canonical = repo_root / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    local = home / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    try:
        tier3_link_target = fs.read_symlink_target(local)
    except FsError as exc:
        findings.append(_op_failed_finding(f"reading tier-3 backlink state: {exc}"))
        return _emit(args, data, findings)

    if tier3_link_target == canonical and fs.is_dir(canonical):
        # Converged: matching symlink target AND the canonical directory
        # still present -- zero further FsPort calls (AD-21/NFR-7's
        # idempotency bar).
        steps["tier3_backlink"] = "skipped"
    else:
        if tier3_link_target is None and fs.is_dir(local):
            # A real (non-symlink) directory already sits at `local` -- only
            # a STALE EMPTY one may be cleared to make way for the backlink;
            # a real, non-empty one is a safe refusal (MRS-INIT-005), not a
            # failure (mirrors ensure_tier3_backlink's own any(iterdir())
            # check, plus this repo's own live incident: a BMAD write-skill
            # populated the local Tier-3 path before the backlink existed).
            try:
                removed = fs.remove_empty_dir(local)
            except FsError as exc:
                findings.append(
                    _op_failed_finding(f"removing stale tier-3 directory {local}: {exc}")
                )
                return _emit(args, data, findings)
            if not removed:
                findings.append(
                    Finding(
                        code="MRS-INIT-005",
                        severity=Severity.ERROR,
                        message=(
                            f"{local} is a real, non-empty directory -- "
                            f"refusing to replace it with a backlink to "
                            f"{canonical}; move its contents into that "
                            "canonical directory by hand (creating it if "
                            "absent), remove the then-empty local "
                            "directory, and re-run"
                        ),
                        path=str(local),
                    )
                )
                return _emit(args, data, findings)

        try:
            fs.ensure_dir(canonical)
            fs.repoint_symlink_atomic(local, canonical)
            steps["tier3_backlink"] = "done"
        except FsError as exc:
            findings.append(_op_failed_finding(str(exc)))
            return _emit(args, data, findings)

    # --- desync check: BLOCKING, before any further write -------------------
    marker_path = home / "_bmad" / "custom" / ".active-project"
    link_path = home / "_bmad-output" / "planning-artifacts"

    try:
        marker_slug = _slug_from_marker(fs.read_text(marker_path))
        raw_link_target = fs.read_symlink_target(link_path)
        link_slug = _slug_from_symlink_target(raw_link_target)
    except FsError as exc:
        findings.append(_op_failed_finding(f"reading marker/symlink state: {exc}"))
        return _emit(args, data, findings)

    if raw_link_target is not None and link_slug is None:
        # A symlink that EXISTS but whose target this command never shaped
        # (absolute path, wrong depth) is evidence of hand configuration,
        # not partial convergence -- repointing it would be exactly the
        # silent overwrite MRS-INIT-003 exists to refuse (review finding:
        # the both-slugs-parse desync check below silently skipped this).
        findings.append(
            Finding(
                code="MRS-INIT-003",
                severity=Severity.ERROR,
                message=(
                    f"unrecognized planning-artifacts symlink target "
                    f"{str(raw_link_target)!r} in {home} -- expected "
                    "projects/<slug>/planning-artifacts; refusing to "
                    "repoint a link this command did not shape; resolve "
                    "by hand before re-running"
                ),
                path=str(link_path),
            )
        )
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

    # --- step: symlink, written BEFORE the marker -----------------------------
    if link_slug == slug:
        steps["symlink"] = "skipped"
    else:
        target = Path("projects") / slug / "planning-artifacts"
        try:
            fs.repoint_symlink_atomic(link_path, target)
            steps["symlink"] = "done"
        except FsError as exc:
            findings.append(_op_failed_finding(str(exc)))
            return _emit(args, data, findings)

    # --- step: marker -----------------------------------------------------------
    if marker_slug == slug:
        steps["marker"] = "skipped"
    else:
        try:
            fs.write_text_atomic(marker_path, slug + "\n")
            steps["marker"] = "done"
        except FsError as exc:
            findings.append(_op_failed_finding(str(exc)))
            return _emit(args, data, findings)

    # shlex.quote keeps the line directly pasteable even when the home path
    # needs shell quoting (a BMAD_LOOP_HOME_ROOT override containing a
    # space); it is a no-op for the common unspaced path, and the slug's
    # charset never needs quoting (review finding).
    data["launch_line"] = (
        f"cd {shlex.quote(str(home))} && export BMAD_ACTIVE_PROJECT={shlex.quote(slug)}"
    )
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


# =====================================================================
# ``marshal homes`` (Story 1.6, FR-4/FR-8) -- read-only, never writes.
# =====================================================================


def _homes_op_failed_finding(message: str) -> Finding:
    return Finding(code="MRS-HOMES-003", severity=Severity.ERROR, message=message)


def _gather_home_facts(entry: WorktreeEntry, repo_root: Path, fs: FsPort) -> status.HomeFacts:
    """Reads ONE ``loop/<slug>`` worktree's raw state via ``FsPort`` --
    ``entry.branch`` is guaranteed ``loop/``-prefixed by ``run_homes``'s own
    discovery filter before this is ever called."""
    assert entry.branch is not None  # narrows for the type checker; see docstring
    slug = entry.branch.removeprefix("loop/")
    marker_path = entry.path / "_bmad" / "custom" / ".active-project"
    link_path = entry.path / "_bmad-output" / "planning-artifacts"
    tier3_local_path = (
        entry.path / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    )
    tier3_canonical_path = (
        repo_root / "_bmad-output" / "projects" / slug / "implementation-artifacts"
    )

    marker_text = fs.read_text(marker_path)
    symlink_target = fs.read_symlink_target(link_path)
    # A real (non-symlink) directory or file at the planning-artifacts path
    # is NOT "symlink absent" -- it means writes no longer reach the
    # canonical project tree. Same occupancy distinction as the Tier-3 probe
    # below, applied to the OTHER symlink this command checks (review
    # finding: previously read as benign absence).
    link_occupied = symlink_target is None and fs.exists(link_path)
    # Genuinely NOTHING at the local Tier-3 path (no symlink, no directory,
    # no file) has no realpath worth comparing -- None mirrors "absence is
    # not a violation" (core/status.py's own docstring). A REAL, non-symlink
    # occupant there is a distinct third state, not absence: a DIRECTORY is
    # exactly what init's own MRS-INIT-005 refuses to silently replace, and
    # a plain FILE blocks any future backlink the same way (review finding:
    # the first occupancy fix probed is_dir only, leaving the file case read
    # as absence) -- either means Tier-3 is NOT single-sourced for this
    # home. Resolving it anyway (it resolves to itself, since there is no
    # link to follow) lets the ordinary realpath comparison below catch the
    # divergence as MRS-HOMES-002 rather than this being silently reported
    # as clean (review finding).
    tier3_local_target = fs.read_symlink_target(tier3_local_path)
    tier3_occupied = tier3_local_target is not None or fs.exists(tier3_local_path)
    tier3_local_realpath = fs.resolve_path(tier3_local_path) if tier3_occupied else None
    tier3_canonical_realpath = fs.resolve_path(tier3_canonical_path)
    # A backlink that resolves to the RIGHT path can still dangle: the
    # canonical store itself may have been deleted after provisioning.
    # init's own convergence check has always required is_dir(canonical);
    # gather the same fact so core/status can name that state instead of
    # blessing it (review finding).
    tier3_canonical_is_dir = fs.is_dir(tier3_canonical_path)

    return status.HomeFacts(
        path=entry.path,
        branch=entry.branch,
        marker_text=marker_text,
        symlink_target=symlink_target,
        tier3_local_realpath=tier3_local_realpath,
        tier3_canonical_realpath=tier3_canonical_realpath,
        link_occupied=link_occupied,
        tier3_canonical_is_dir=tier3_canonical_is_dir,
    )


def _gather_main_checkout_facts(
    main_entry: WorktreeEntry, repo_root: Path, fs: FsPort
) -> status.MainCheckoutFacts:
    """Reads the main checkout's own raw state via ``FsPort``. Sub-paths are
    built from ``repo_root`` (not ``main_entry.path``) -- both name the same
    directory, but ``repo_root`` is this module's one authoritative value for
    it everywhere else."""
    marker_path = repo_root / "_bmad" / "custom" / ".active-project"
    link_path = repo_root / "_bmad-output" / "planning-artifacts"
    marker_text = fs.read_text(marker_path)
    symlink_target = fs.read_symlink_target(link_path)
    # Same occupancy probe as _gather_home_facts (review finding): a real
    # directory materialized where the main checkout's planning-artifacts
    # symlink belongs is the hand-configuration state the two-way rule
    # exists to name, not benign absence.
    link_occupied = symlink_target is None and fs.exists(link_path)
    return status.MainCheckoutFacts(
        path=repo_root,
        branch=main_entry.branch,
        marker_text=marker_text,
        symlink_target=symlink_target,
        link_occupied=link_occupied,
    )


def run_homes(
    args: argparse.Namespace,
    *,
    vcs: VcsPort | None = None,
    fs: FsPort | None = None,
) -> int:
    vcs = vcs if vcs is not None else GitVcs()
    fs = fs if fs is not None else LocalFs()

    findings: list[Finding] = []
    data: dict[str, object] = {}

    try:
        invocation_dir = Path.cwd()
    except OSError as exc:
        findings.append(
            _homes_op_failed_finding(f"resolving the current working directory: {exc}")
        )
        return _emit_homes(args, data, findings)
    try:
        repo_root = vcs.repo_common_root(invocation_dir)
    except VcsCommandError as exc:
        findings.append(_homes_op_failed_finding(f"resolving the repo root: {exc}"))
        return _emit_homes(args, data, findings)

    try:
        worktrees = vcs.list_worktrees(repo_root)
    except VcsCommandError as exc:
        findings.append(_homes_op_failed_finding(f"listing worktrees: {exc}"))
        return _emit_homes(args, data, findings)

    # Identify the main checkout by REALPATH (not a raw-string/ordinal
    # assumption about git's own listing order) -- every OTHER loop/<slug>
    # entry becomes a home candidate; anything else (a detached-HEAD
    # worktree, an unrelated hand-made linked worktree) is neither.
    try:
        repo_root_realpath = fs.resolve_path(repo_root)
        main_entry: WorktreeEntry | None = None
        home_entries: list[WorktreeEntry] = []
        for entry in worktrees:
            if fs.resolve_path(entry.path) == repo_root_realpath:
                main_entry = entry
            elif entry.branch is not None and entry.branch.startswith("loop/"):
                home_entries.append(entry)
    except FsError as exc:
        findings.append(_homes_op_failed_finding(f"resolving worktree paths: {exc}"))
        return _emit_homes(args, data, findings)

    if main_entry is None:
        findings.append(
            _homes_op_failed_finding(
                f"'git worktree list' for {repo_root} did not include an "
                "entry for the main checkout itself"
            )
        )
        return _emit_homes(args, data, findings)

    try:
        gathered_home_facts: list[status.HomeFacts] = []
        for entry in home_entries:
            # git still registers the worktree, but its directory may have
            # been deleted by hand rather than via `git worktree remove`
            # (mirrors run_init's own identical guard for the same known
            # failure mode). Every FsPort read below would silently return
            # None for a missing path, misreporting a genuinely stale/
            # prunable home as a harmless "never provisioned" one (review
            # finding) -- named as its own finding instead, and excluded
            # from data.homes rather than gathered.
            if not fs.is_dir(entry.path):
                findings.append(
                    _homes_op_failed_finding(
                        f"git still registers a worktree for {entry.branch} at "
                        f"{entry.path}, but that directory does not exist on "
                        "disk (a stale/prunable entry) -- run "
                        "'git worktree prune'"
                    )
                )
                continue
            gathered_home_facts.append(_gather_home_facts(entry, repo_root, fs))
        home_facts = tuple(gathered_home_facts)
        main_facts = _gather_main_checkout_facts(main_entry, repo_root, fs)
    except FsError as exc:
        findings.append(_homes_op_failed_finding(f"reading loop-home state: {exc}"))
        return _emit_homes(args, data, findings)

    evaluation = status.evaluate_homes(home_facts, main_facts)
    data["homes"] = [dict(row) for row in evaluation.homes]
    data["main_checkout"] = dict(evaluation.main_checkout)
    findings.extend(evaluation.findings)

    return _emit_homes(args, data, findings)


def _render_text_homes(data: Mapping[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14), matching ``_render_text``'s own
    convention for ``init``."""
    lines = ["homes:"]
    for row in data.get("homes", []):
        lines.append(f"  {row['slug']} ({row['path']}):")
        lines.append(f"    branch: {row['branch']}")
        lines.append(f"    active_project: {row['active_project']}")
        lines.append(f"    desynced: {row['desynced']}")
    if "main_checkout" in data:
        row = data["main_checkout"]
        lines.append(f"main_checkout ({row['path']}):")
        lines.append(f"  branch: {row['branch']}")
        lines.append(f"  active_project: {row['active_project']}")
        lines.append(f"  desynced: {row['desynced']}")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)


def _emit_homes(args: argparse.Namespace, data: dict[str, object], findings: list[Finding]) -> int:
    verdict_value = compute_verdict(tuple(findings))
    envelope = build_envelope(
        command="homes", verdict=verdict_value, data=data, findings=tuple(findings)
    )
    # Same flush + broken-pipe-suppression convention as _emit (init's own)
    # and cli/config.py::run_config.
    try:
        if args.format == "json":
            print(json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True), flush=True)
        else:
            print(_render_text_homes(envelope.data, envelope.findings), flush=True)
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)
