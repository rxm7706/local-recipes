"""``marshal adapters`` (Story 6.2, FR-41, AD-12/AD-36) -- a NEW top-level
command group, its first action ``sync`` (PRD UJ-5:
"``marshal adapters sync`` projects the 89 skills into the tree that
adapter expects"). Mirrors the Consistency Conventions table's own already
-declared shape (``adapters <sub>: sync|probe|conform|matrix|check``) --
``probe``/``conform``/``matrix``/``check`` are later Epic-6 stories' own
additions to this SAME nested parser, not this story's scope.

``run_adapters_sync`` projects this project's canonical skill tree
(``core.skill_projection.CANONICAL_SKILL_TREE_REL``, ``.claude/skills``)
into every OTHER tree a CONFIGURED adapter declares
(``HarnessPort.adapter_skill_trees`` -- every profile
``bmad_loop.adapters.profile.load_profiles`` resolves for the loop home,
packaged plus any project-local overlay, never only the one home's own
active ``[adapter].name``; see ``core/skill_projection.py``'s own
docstring for why). One directory symlink per DISTINCT declared tree value
(never per adapter, and never per skill) is the whole mechanism (AD-36's
declared, one-row-today ``(platform -> mechanism)`` table); a small,
gitignored derived-artifact manifest (``.bmad-loop/skill-projection.json``,
the SAME AD-12/AD-35 precedent ``.bmad-loop/policy.toml`` already
established) records which trees were projected, so a later run whose
configured-adapter set has SHRUNK can detect and remove the now-stale
tree -- the one thing a self-converging directory symlink cannot signal on
its own (see this story's own spec Design Notes).

Order of operations (``run_adapters_sync``): slug shape (``MRS-ADP-001``)
-> loop home provisioned (``MRS-ADP-002``) -> canonical tree presence
(``MRS-ADP-003``, non-blocking: stale-removal still proceeds even when
canonical is missing) -> ``HarnessPort.adapter_skill_trees``
(``MRS-ADP-004``) -> read + parse the manifest (``MRS-ADP-009`` on
malformed JSON, degrades to "nothing previously projected") ->
``core.skill_projection.plan_projection`` (``MRS-ADP-005`` if the resolved
platform has no declared mechanism-table row) -> execute each tree's
create/update/unchanged decision against live filesystem state
(``MRS-ADP-006``/``007`` per tree, isolated -- one tree's failure never
aborts another's) -> execute stale-tree removal, re-verified live before
any delete (``MRS-ADP-007``/``008`` per tree) -> write the manifest ONLY
if its computed content actually changed (``MRS-ADP-010`` on failure,
degrades gracefully) -> envelope build/print/exit.

Story 6.3 (FR-42, AD-31/AD-36) adds a second, READ-ONLY action, ``conform``
(``run_adapters_conform`` / ``marshal adapters conform <slug>``), plus the
shared helper both it and ``cli/init.py::run_preflight`` call,
``gather_conformance_findings``. Neither calls ``repoint_symlink_atomic``,
``remove_symlink``, ``ensure_dir``, or ``write_text_atomic`` -- detecting
drift never repairs it. ``gather_conformance_findings`` reuses
``plan_projection`` (the SAME desired-tree computation ``sync`` uses) and
``_confine_skill_trees``/``_read_manifest`` (extracted/reused from
``run_adapters_sync`` verbatim) to read each in-scope tree's live symlink
state, then hands it to ``core.conformance.evaluate_conformance`` for the
LINK-TARGET IDENTITY check that module's own docstring describes. Reuses
``MRS-ADP-001/002/003/004/005/009/011`` verbatim for the preconditions it
shares with ``sync`` (AD-31's own ``MRS-DEPLOY-003`` precedent: the same
code, the same tier, a second call site); the one wholly new code,
``MRS-CONFORM-001`` (``Verdict.ERROR``), reports drift (added/removed/
modified, folded into one code per the ``MRS-GATE-001`` "one code, several
triggering shapes" precedent). See the story's own spec Design Notes for
why ``cli/init.py`` -- not named in the epics doc's own coarse ``Surface``
line -- is touched anyway: "runs as part of preflight" is only satisfiable
there, via a LOCAL import (``cli/deploy.py``'s own established pattern) to
avoid the load-time circular import ``cli/adapters.py``'s own
module-level ``from .init import _home_path`` would otherwise create.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadloop import BmadLoopHarness, HarnessError
from ..core import policy
from ..core.conformance import STATUS_LINK_TARGET_CONFIRMED, TreeLiveState, evaluate_conformance
from ..core.model import Finding, Severity, build_envelope
from ..core.skill_projection import CANONICAL_SKILL_TREE_REL, plan_projection
from ..core.verdict import compute_verdict, exit_code_for
from ..ports.fs import FsPort
from ..ports.harness import HarnessPort
from .config import _suppress_downstream_pipe_close
from .init import _home_path

if TYPE_CHECKING:
    from ..core.context import MarshalContext

_MANIFEST_RELPATH = (".bmad-loop", "skill-projection.json")


def add_adapters_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``adapters`` subcommand on ``main.py``'s subparser
    tree, with a nested ``sync`` action (mirrors ``cli/spin.py``'s own
    ``factory``/``spin``/``attach`` nested-action shape). ``probe``/
    ``conform``/``matrix``/``check`` are later stories' own additions to
    this SAME nested parser."""
    parser = subparsers.add_parser(
        "adapters",
        help="Project the canonical skill tree into every configured adapter's own tree (FR-41).",
        description=(
            "Skill-tree projection and (in later stories) adapter probing/"
            "conformance: 'marshal adapters sync' makes the canonical "
            "skill tree available in every tree a configured adapter "
            "declares (AD-12/AD-36)."
        ),
    )
    adapters_subparsers = parser.add_subparsers(dest="adapters_command", required=True)

    sync_parser = adapters_subparsers.add_parser(
        "sync",
        help="Project the canonical skill tree into every configured adapter's declared tree.",
        description=(
            "Reads every configured adapter's declared skill_tree "
            "(bmad_loop.adapters.profile.load_profiles), repoints one "
            "directory symlink per distinct non-canonical tree at the "
            "canonical .claude/skills, and removes any previously "
            "projected tree no configured adapter declares any more."
        ),
    )
    sync_parser.add_argument("slug", help="The BMAD project slug whose loop home to sync.")
    sync_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    sync_parser.set_defaults(handler=run_adapters_sync)

    conform_parser = adapters_subparsers.add_parser(
        "conform",
        help="Detect drift between the canonical skill tree and every projected adapter tree (FR-42).",
        description=(
            "Read-only: asserts LINK-TARGET IDENTITY for the symlink "
            "projection mechanism (the only one this project supports, "
            "AD-36) -- reports added/removed/modified per adapter tree; "
            "never mutates anything (use 'marshal adapters sync' to "
            "converge)."
        ),
    )
    conform_parser.add_argument("slug", help="The BMAD project slug whose loop home to check.")
    conform_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    conform_parser.set_defaults(handler=run_adapters_conform)


def _render_text(data: dict[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints (AD-14)."""
    lines = [f"adapters sync -- canonical={data.get('canonical')}"]
    projections = data.get("projections")
    if isinstance(projections, list):
        for entry in projections:
            if not isinstance(entry, dict):
                continue
            tree = entry.get("tree", "?")
            action = entry.get("action", "?")
            mechanism = entry.get("mechanism", "?")
            adapter_names = entry.get("adapters", [])
            lines.append(
                f"  {action:9} {tree:24} mechanism={mechanism} "
                f"adapters={','.join(adapter_names) if isinstance(adapter_names, list) else adapter_names}"
            )
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)


def _render_text_conform(data: dict[str, object], findings: tuple[Finding, ...]) -> str:
    """A pure projection of the SAME envelope ``data``/``findings`` the
    ``--format json`` path prints, mirroring ``_render_text``'s own shape
    (AD-14)."""
    lines = [
        f"adapters conform -- canonical={data.get('canonical')} "
        f"mechanism={data.get('platform_mechanism')}"
    ]
    checks = data.get("checks")
    if isinstance(checks, list):
        for entry in checks:
            if not isinstance(entry, dict):
                continue
            status = entry.get("status", "?")
            tree = entry.get("tree", "?")
            detail = entry.get("detail", "")
            lines.append(f"  {status:24} {tree:24} {detail}")
    unevaluated = data.get("unevaluated_trees")
    if isinstance(unevaluated, list) and unevaluated:
        lines.append(f"unevaluated: {', '.join(unevaluated)}")
    if findings:
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)


def _emit(
    args: argparse.Namespace,
    data: dict[str, object],
    findings: list[Finding],
    *,
    command: str = "adapters sync",
    renderer: Callable[[dict[str, object], tuple[Finding, ...]], str] = _render_text,
) -> int:
    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command=command,
        verdict=verdict_value,
        data=data,
        data_version=1,
        findings=tuple(findings),
    )
    if args.format == "json":
        rendered = json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True)
    else:
        rendered = renderer(envelope.data, envelope.findings)
    try:
        print(rendered, flush=True)
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def _rel_path(home: Path, rel: str) -> Path:
    """``rel`` is always project-relative and forward-slash-separated
    (``CLIProfile.skill_tree``'s own documented shape) -- ``Path(rel)``
    parses it correctly on POSIX, the only platform this story's own
    mechanism table declares a row for."""
    return home / Path(rel)


def _read_manifest(fs: FsPort, manifest_path: Path, findings: list[Finding]) -> dict[str, object]:
    raw = fs.read_text(manifest_path)
    if raw is None:
        return {"canonical": CANONICAL_SKILL_TREE_REL, "projected": {}}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        findings.append(
            Finding(
                code="MRS-ADP-009",
                severity=Severity.WARN,
                message=(
                    f"skill-projection manifest {str(manifest_path)!r} is not valid JSON "
                    f"({exc}) -- treated as 'nothing previously projected'. IF A STALE "
                    "projected tree exists on disk from before this manifest was "
                    "corrupted, it will NOT be detected or cleaned up this run (there is "
                    "no record of it to compare against) -- inspect "
                    f"{str(manifest_path)!r} by hand, or any previously-projected tree "
                    "under this loop home, before assuming this run's cleanup was "
                    "complete. A fresh manifest will be written reflecting only what "
                    "this run itself projects."
                ),
                path=str(manifest_path),
            )
        )
        return {"canonical": CANONICAL_SKILL_TREE_REL, "projected": {}}
    if not isinstance(parsed, dict) or not isinstance(parsed.get("projected"), dict):
        findings.append(
            Finding(
                code="MRS-ADP-009",
                severity=Severity.WARN,
                message=(
                    f"skill-projection manifest {str(manifest_path)!r} does not carry the "
                    "expected {'projected': {...}} shape -- treated as 'nothing "
                    "previously projected'. IF A STALE projected tree exists on disk "
                    "from before this manifest lost its shape, it will NOT be detected "
                    "or cleaned up this run (there is no record of it to compare "
                    f"against) -- inspect {str(manifest_path)!r} by hand, or any "
                    "previously-projected tree under this loop home, before assuming "
                    "this run's cleanup was complete. A fresh manifest will be written "
                    "reflecting only what this run itself projects."
                ),
                path=str(manifest_path),
            )
        )
        return {"canonical": CANONICAL_SKILL_TREE_REL, "projected": {}}
    return parsed


def _confine_skill_trees(
    skill_trees: Mapping[str, str],
    home: Path,
    home_resolved: Path,
    fs: FsPort,
) -> tuple[dict[str, str], list[Finding]]:
    """An adapter-declared ``skill_tree`` (including one from a
    project-local ``.bmad-loop/profiles/*.toml`` overlay -- untrusted
    relative to the packaged profiles) is never trusted unconfined.
    ``home / Path(rel)`` for an ABSOLUTE ``rel`` discards ``home`` entirely
    (Python's own ``Path.__truediv__`` semantics), and a ``..``-laden
    relative value can walk out from under ``home`` just as easily -- both
    would otherwise let a caller create/repoint a symlink (``run_adapters_
    sync``) or read a live symlink's state (``gather_conformance_findings``)
    anywhere this process can reach, with none of ``MRS-ADP-001``'s
    slug-shape scrutiny. Every declared tree is confined here, ONCE, before
    any of it reaches ``plan_projection`` -- an offending tree is skipped
    (never aborts the whole run) and named in a registered finding
    (``MRS-ADP-011``, extracted from ``run_adapters_sync`` verbatim so
    ``gather_conformance_findings`` shares the identical check, Story
    6.3)."""
    findings: list[Finding] = []
    safe_skill_trees: dict[str, str] = {}
    for adapter_name, tree in skill_trees.items():
        if Path(tree).is_absolute():
            findings.append(
                Finding(
                    code="MRS-ADP-011",
                    severity=Severity.WARN,
                    message=(
                        f"adapter {adapter_name!r} declares an absolute "
                        f"skill_tree {tree!r} -- refusing to project outside "
                        "the loop home; this tree is skipped"
                    ),
                )
            )
            continue
        try:
            candidate_resolved = fs.resolve_path(home / Path(tree))
        except FsError as exc:
            findings.append(
                Finding(
                    code="MRS-ADP-011",
                    severity=Severity.WARN,
                    message=(
                        f"adapter {adapter_name!r}'s declared skill_tree "
                        f"{tree!r} could not be resolved: {exc} -- this "
                        "tree is skipped"
                    ),
                )
            )
            continue
        if candidate_resolved != home_resolved and home_resolved not in candidate_resolved.parents:
            findings.append(
                Finding(
                    code="MRS-ADP-011",
                    severity=Severity.WARN,
                    message=(
                        f"adapter {adapter_name!r} declares a skill_tree "
                        f"{tree!r} that resolves outside the loop home "
                        f"({candidate_resolved}) -- refusing to project "
                        "outside it; this tree is skipped"
                    ),
                )
            )
            continue
        safe_skill_trees[adapter_name] = tree
    return safe_skill_trees, findings


def run_adapters_sync(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    harness: HarnessPort | None = None,
    context: MarshalContext | None = None,
) -> int:
    # Story 5.6's own "resolved once at the front door, accepted but
    # deliberately unused" precedent (see cli/spin.py::run_spin) -- this
    # command identifies its project via a positional slug, exactly like
    # factory spin/land, not via --project.
    del context
    fs = fs if fs is not None else LocalFs()
    harness = harness if harness is not None else BmadLoopHarness()

    slug = args.slug
    findings: list[Finding] = []
    data: dict[str, object] = {"slug": slug, "canonical": CANONICAL_SKILL_TREE_REL}

    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-ADP-001",
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
        home = _home_path(slug)
    except (RuntimeError, OSError) as exc:
        findings.append(
            Finding(
                code="MRS-ADP-002",
                severity=Severity.ERROR,
                message=f"resolving the loop-home root: {exc}",
            )
        )
        return _emit(args, data, findings)
    data["home"] = str(home)

    if not fs.is_dir(home):
        findings.append(
            Finding(
                code="MRS-ADP-002",
                severity=Severity.ERROR,
                message=(
                    f"loop home not provisioned: {str(home)!r} is not a directory "
                    f"-- run 'marshal init {slug}' first"
                ),
                path=str(home),
            )
        )
        return _emit(args, data, findings)

    canonical_dir = _rel_path(home, CANONICAL_SKILL_TREE_REL)
    canonical_present = fs.is_dir(canonical_dir)
    if not canonical_present:
        findings.append(
            Finding(
                code="MRS-ADP-003",
                severity=Severity.ERROR,
                message=(
                    f"canonical skill tree {str(canonical_dir)!r} does not exist -- "
                    "no tree will be projected this run (stale-entry cleanup still proceeds)"
                ),
                path=str(canonical_dir),
            )
        )

    try:
        skill_trees = harness.adapter_skill_trees(home)
    except HarnessError as exc:
        findings.append(
            Finding(
                code="MRS-ADP-004",
                severity=Severity.ERROR,
                message=f"cannot enumerate configured adapters: {exc}",
            )
        )
        return _emit(args, data, findings)

    home_resolved = fs.resolve_path(home)
    safe_skill_trees, confinement_findings = _confine_skill_trees(skill_trees, home, home_resolved, fs)
    findings.extend(confinement_findings)
    skill_trees = safe_skill_trees

    manifest_path = _rel_path(home, "/".join(_MANIFEST_RELPATH))
    manifest = _read_manifest(fs, manifest_path, findings)
    previously_projected = frozenset(manifest.get("projected", {}))

    plan = plan_projection(
        skill_trees,
        canonical=CANONICAL_SKILL_TREE_REL,
        previously_projected=previously_projected,
        platform_name=os.name,
    )
    data["platform_mechanism"] = plan.platform_mechanism

    projections: list[dict[str, object]] = []
    new_projected: dict[str, object] = dict(manifest.get("projected", {}))

    if plan.unsupported_trees:
        findings.append(
            Finding(
                code="MRS-ADP-005",
                severity=Severity.WARN,
                message=(
                    f"no declared projection mechanism for platform {os.name!r} -- "
                    f"trees not projected this run: {', '.join(plan.unsupported_trees)}"
                ),
            )
        )
        for tree in plan.unsupported_trees:
            projections.append(
                {"tree": tree, "adapters": [], "mechanism": None, "action": "skipped-unsupported-platform"}
            )

    if canonical_present:
        for action in plan.to_project:
            tree_path = _rel_path(home, action.tree)
            desired_target_str = os.path.relpath(str(canonical_dir), start=str(tree_path.parent))
            current_target = fs.read_symlink_target(tree_path)
            entry: dict[str, object] = {
                "tree": action.tree,
                "adapters": list(action.adapters),
                "mechanism": plan.platform_mechanism,
            }
            if current_target is not None and str(current_target) == desired_target_str:
                entry["action"] = "unchanged"
                new_projected[action.tree] = {
                    "mechanism": plan.platform_mechanism,
                    "target": desired_target_str,
                }
            elif current_target is None and fs.exists(tree_path):
                entry["action"] = "conflict"
                findings.append(
                    Finding(
                        code="MRS-ADP-007",
                        severity=Severity.WARN,
                        message=(
                            f"{str(tree_path)!r} exists and is not a symlink -- refusing "
                            "to project the canonical skill tree over it"
                        ),
                        path=str(tree_path),
                    )
                )
            else:
                try:
                    fs.ensure_dir(tree_path.parent)
                    fs.repoint_symlink_atomic(tree_path, Path(desired_target_str))
                except FsError as exc:
                    entry["action"] = "failed"
                    findings.append(
                        Finding(
                            code="MRS-ADP-006",
                            severity=Severity.ERROR,
                            message=f"cannot project {action.tree!r}: {exc}",
                            path=str(tree_path),
                        )
                    )
                else:
                    entry["action"] = "created" if current_target is None else "updated"
                    new_projected[action.tree] = {
                        "mechanism": plan.platform_mechanism,
                        "target": desired_target_str,
                    }
            projections.append(entry)

    for tree in plan.to_remove:
        tree_path = _rel_path(home, tree)
        current_target = fs.read_symlink_target(tree_path)
        if current_target is None:
            # `read_symlink_target` probes `is_symlink()` (lstat -- never
            # follows), so `None` here means genuinely nothing at this
            # path at all -- not merely a dangling link. See the branch
            # below for why a dangling link is handled differently (review
            # finding: this used to be tested with `fs.exists()`, which
            # FOLLOWS symlinks and returns False for a dangling one too,
            # so a dangling projected symlink was silently untracked here
            # without ever being removed -- an unrecoverable leak, since
            # popping it from the manifest meant no future run would ever
            # revisit it).
            new_projected.pop(tree, None)
            projections.append({"tree": tree, "adapters": [], "mechanism": None, "action": "already-absent"})
            continue
        live_exists = fs.exists(tree_path)  # follows the symlink; False iff dangling
        resolves_to_canonical = live_exists and fs.resolve_path(tree_path) == fs.resolve_path(
            canonical_dir
        )
        if live_exists and not resolves_to_canonical:
            # A LIVE symlink pointing somewhere else entirely -- possibly
            # hand-modified by the operator. Never touched.
            findings.append(
                Finding(
                    code="MRS-ADP-007",
                    severity=Severity.WARN,
                    message=(
                        f"stale projected tree {str(tree_path)!r} no longer resolves to "
                        "the canonical skill tree -- refusing to remove it (kept "
                        "in the manifest so it is re-flagged next run)"
                    ),
                    path=str(tree_path),
                )
            )
            projections.append({"tree": tree, "adapters": [], "mechanism": None, "action": "conflict-kept"})
            continue
        # Either it resolves to canonical, or it is DANGLING (`live_exists`
        # is False) -- both are safe to remove: a symlink that resolves
        # nowhere cannot be pointing at real content worth preserving, so
        # it is never left as a permanent, un-revisitable leak the way
        # `already-absent` handling used to leave it.
        try:
            fs.remove_symlink(tree_path)
        except FsError as exc:
            findings.append(
                Finding(
                    code="MRS-ADP-008",
                    severity=Severity.ERROR,
                    message=f"cannot remove stale projected tree {tree!r}: {exc}",
                    path=str(tree_path),
                )
            )
            projections.append({"tree": tree, "adapters": [], "mechanism": None, "action": "failed"})
        else:
            new_projected.pop(tree, None)
            projections.append({"tree": tree, "adapters": [], "mechanism": None, "action": "removed"})

    data["projections"] = projections

    new_manifest = {"canonical": CANONICAL_SKILL_TREE_REL, "projected": new_projected}
    if new_manifest != manifest:
        try:
            fs.ensure_dir(manifest_path.parent)
            fs.write_text_atomic(manifest_path, json.dumps(new_manifest, indent=2, sort_keys=True) + "\n")
        except FsError as exc:
            findings.append(
                Finding(
                    code="MRS-ADP-010",
                    severity=Severity.WARN,
                    message=(
                        f"skill-projection manifest could not be written: {exc} -- the "
                        "live symlinks are already correct; only next run's staleness "
                        "bookkeeping degrades"
                    ),
                    path=str(manifest_path),
                )
            )

    return _emit(args, data, findings)


def gather_conformance_findings(
    home: Path,
    *,
    fs: FsPort,
    harness: HarnessPort,
) -> tuple[dict[str, object], list[Finding]]:
    """Story 6.3 (FR-42, AD-31/AD-36): the READ-ONLY "does the live
    filesystem still satisfy the current projection plan" check -- shared by
    the standalone ``marshal adapters conform <slug>`` verb
    (``run_adapters_conform``) AND ``marshal preflight``'s own additional
    step (``cli/init.py::run_preflight``, via a local import to avoid a
    load-time circular dependency). Never mutates anything -- no
    ``repoint_symlink_atomic``/``remove_symlink``/manifest-write call
    anywhere in this function, unlike ``run_adapters_sync``.

    Returns ``(data, findings)`` rather than emitting an envelope itself --
    the two callers wrap it differently (a standalone envelope vs folding
    into ``marshal preflight``'s own).

    Deliberately gathers the DESIRED-tree plan (``plan_projection``, exactly
    like ``sync``) BEFORE ever probing the canonical tree's own presence --
    unlike ``run_adapters_sync``, which is a deliberately-invoked, standalone
    command where an unconditional canonical-presence check is cheap and
    always relevant. This function's SECOND call site is
    ``cli/init.py::run_preflight``, invoked far more often and for many
    projects that configure no non-default adapter at all; probing canonical
    presence before knowing whether anything is even in scope to check would
    surface a spurious ``MRS-ADP-003`` on every such run. When nothing is
    desired AND nothing was previously tracked, this function returns
    immediately with empty ``checks``/``unevaluated_trees`` and no
    findings -- the AC's own "runs... whenever a non-default adapter is
    configured" made literal."""
    findings: list[Finding] = []
    data: dict[str, object] = {}

    try:
        skill_trees = harness.adapter_skill_trees(home)
    except HarnessError as exc:
        findings.append(
            Finding(
                code="MRS-ADP-004",
                severity=Severity.ERROR,
                message=f"cannot enumerate configured adapters: {exc}",
            )
        )
        return data, findings

    try:
        home_resolved = fs.resolve_path(home)
    except FsError as exc:
        findings.append(
            Finding(
                code="MRS-ADP-004",
                severity=Severity.ERROR,
                message=f"cannot resolve the loop home's own realpath to confine configured adapters: {exc}",
            )
        )
        return data, findings

    safe_skill_trees, confinement_findings = _confine_skill_trees(skill_trees, home, home_resolved, fs)
    findings.extend(confinement_findings)

    manifest_path = _rel_path(home, "/".join(_MANIFEST_RELPATH))
    manifest = _read_manifest(fs, manifest_path, findings)
    previously_projected = frozenset(manifest.get("projected", {}))

    plan = plan_projection(
        safe_skill_trees,
        canonical=CANONICAL_SKILL_TREE_REL,
        previously_projected=previously_projected,
        platform_name=os.name,
    )
    data["platform_mechanism"] = plan.platform_mechanism

    if not plan.to_project and not plan.unsupported_trees and not previously_projected:
        # Nothing desired, nothing tracked -- no non-default adapter is
        # configured (or ever was), so there is nothing this check could
        # possibly assess, let alone fail. Never probes canonical presence
        # for this case (see this function's own docstring).
        data["checks"] = []
        data["unevaluated_trees"] = []
        return data, findings

    canonical_dir = _rel_path(home, CANONICAL_SKILL_TREE_REL)
    if not fs.is_dir(canonical_dir):
        # Non-blocking (mirrors `run_adapters_sync`'s identical canonical-
        # missing handling): the identity check below is a pure STRING
        # comparison against the computed canonical-relative target, so it
        # needs no real canonical content to proceed.
        findings.append(
            Finding(
                code="MRS-ADP-003",
                severity=Severity.ERROR,
                message=(
                    f"canonical skill tree {str(canonical_dir)!r} does not exist -- "
                    "drift cannot be meaningfully assessed against it, but the "
                    "link-target identity check still proceeds"
                ),
                path=str(canonical_dir),
            )
        )

    desired_adapters_by_tree = {action.tree: action.adapters for action in plan.to_project}
    # `plan.to_project` and `plan.unsupported_trees` are mutually exclusive
    # (`plan_projection` populates exactly one, never both, depending on
    # whether the platform's mechanism resolved) -- their union is always
    # the FULL desired-tree set regardless of mechanism resolution. Using
    # `desired_adapters_by_tree` alone here would silently be empty
    # whenever the mechanism is unsupported (Story 6.2's own contract:
    # `to_project` comes back `()` in that case), undercounting `all_trees`
    # exactly when the branch below needs it to be complete.
    desired_trees = set(desired_adapters_by_tree) | set(plan.unsupported_trees)
    all_trees = sorted(desired_trees | previously_projected)

    if plan.platform_mechanism is None:
        # Review finding (Edge Case Hunter): `plan.unsupported_trees` alone
        # under-reports here -- Story 6.2's own `plan_projection` scopes it
        # to the CURRENTLY DESIRED set only. A tree that is
        # previously-projected but no longer desired by any configured
        # adapter would silently vanish from both this finding AND
        # `unevaluated_trees` if only `plan.unsupported_trees` were used --
        # a real, previously-projected tree's live symlink state never read
        # or compared, yet reported exactly like "nothing to check" (empty
        # checks, empty unevaluated_trees) -- precisely the "clean for a
        # check that structurally cannot fail" shape this whole story
        # exists to forbid. `all_trees` (desired UNION previously-projected,
        # already computed above) is the complete set this check would
        # otherwise assess.
        if all_trees:
            findings.append(
                Finding(
                    code="MRS-ADP-005",
                    severity=Severity.WARN,
                    message=(
                        f"no declared projection mechanism for platform {os.name!r} -- "
                        f"link-target identity cannot be checked this run for: "
                        f"{', '.join(all_trees)}"
                    ),
                )
            )
        data["checks"] = []
        data["unevaluated_trees"] = all_trees
        return data, findings

    live_states: list[TreeLiveState] = []
    unreadable_trees: list[str] = []
    for tree in all_trees:
        tree_path = _rel_path(home, tree)
        expected_target = os.path.relpath(str(canonical_dir), start=str(tree_path.parent))
        # Review finding (Blind Hunter): unlike every other `FsError`-raising
        # call in this module, this one was unguarded -- an unsearchable
        # ancestor directory (a real, documented `LocalFs.read_symlink_
        # target`/`exists` failure mode on this package's own Python 3.12
        # floor) would propagate a raw `FsError` straight out of this
        # function. Since `gather_conformance_findings` now runs
        # UNCONDITIONALLY as part of `marshal preflight` (this story's own
        # AC), that would crash the entire preflight command instead of
        # degrading to a finding -- directly defeating this story's "runs
        # unconditionally, never crashes" design. One tree's I/O failure is
        # isolated here, never aborting the rest (mirrors this module's own
        # per-tree isolation convention elsewhere).
        try:
            raw_target = fs.read_symlink_target(tree_path)
            live_exists = fs.exists(tree_path)
        except FsError as exc:
            findings.append(
                Finding(
                    code="MRS-ADP-012",
                    severity=Severity.ERROR,
                    message=(
                        f"cannot read live symlink state for {tree!r}: {exc} -- "
                        "link-target identity not evaluated this run"
                    ),
                    path=str(tree_path),
                )
            )
            unreadable_trees.append(tree)
            continue
        live_states.append(
            TreeLiveState(
                tree=tree,
                adapters=tuple(desired_adapters_by_tree.get(tree, ())),
                desired=tree in desired_adapters_by_tree,
                previously_projected=tree in previously_projected,
                live_target=str(raw_target) if raw_target is not None else None,
                live_exists=live_exists,
                expected_target=expected_target,
            )
        )

    report = evaluate_conformance(live_states, mechanism=plan.platform_mechanism)
    data["checks"] = [
        {"tree": check.tree, "adapters": list(check.adapters), "status": check.status, "detail": check.detail}
        for check in report.checks
    ]
    # `unreadable_trees` (an I/O failure reading this tree's own live
    # symlink state, already reported via MRS-ADP-012 above) is a tree
    # `evaluate_conformance` never saw at all -- it must be named here too,
    # not just the ones the mechanism-specific check itself could not
    # evaluate, or a read failure would silently vanish from this report's
    # own accounting the same way the Edge Case Hunter finding above named.
    data["unevaluated_trees"] = sorted(set(report.unevaluated_trees) | set(unreadable_trees))

    if report.unevaluated_trees:
        findings.append(
            Finding(
                code="MRS-ADP-005",
                severity=Severity.WARN,
                message=(
                    "link-target identity could not be evaluated for: "
                    f"{', '.join(report.unevaluated_trees)}"
                ),
            )
        )

    drift = [check for check in report.checks if check.status != STATUS_LINK_TARGET_CONFIRMED]
    if drift:
        summary = "; ".join(f"{check.tree} ({check.status}: {check.detail})" for check in drift)
        findings.append(
            Finding(
                code="MRS-CONFORM-001",
                severity=Severity.ERROR,
                message=f"projection drift detected for {len(drift)} tree(s): {summary}",
            )
        )

    return data, findings


def run_adapters_conform(
    args: argparse.Namespace,
    *,
    fs: FsPort | None = None,
    harness: HarnessPort | None = None,
    context: MarshalContext | None = None,
) -> int:
    del context
    fs = fs if fs is not None else LocalFs()
    harness = harness if harness is not None else BmadLoopHarness()

    slug = args.slug
    findings: list[Finding] = []
    data: dict[str, object] = {"slug": slug, "canonical": CANONICAL_SKILL_TREE_REL}

    if not policy._is_valid_project_slug(slug):
        findings.append(
            Finding(
                code="MRS-ADP-001",
                severity=Severity.ERROR,
                message=(
                    f"malformed project slug {slug!r} -- must be one safe "
                    "path segment (letters, digits, '.', '_', '-'; not '.' "
                    "or '..'; at most 255 characters)"
                ),
            )
        )
        return _emit(args, data, findings, command="adapters conform", renderer=_render_text_conform)

    try:
        home = _home_path(slug)
    except (RuntimeError, OSError) as exc:
        findings.append(
            Finding(
                code="MRS-ADP-002",
                severity=Severity.ERROR,
                message=f"resolving the loop-home root: {exc}",
            )
        )
        return _emit(args, data, findings, command="adapters conform", renderer=_render_text_conform)
    data["home"] = str(home)

    if not fs.is_dir(home):
        findings.append(
            Finding(
                code="MRS-ADP-002",
                severity=Severity.ERROR,
                message=(
                    f"loop home not provisioned: {str(home)!r} is not a directory "
                    f"-- run 'marshal init {slug}' first"
                ),
                path=str(home),
            )
        )
        return _emit(args, data, findings, command="adapters conform", renderer=_render_text_conform)

    conform_data, conform_findings = gather_conformance_findings(home, fs=fs, harness=harness)
    data.update(conform_data)
    findings.extend(conform_findings)

    return _emit(args, data, findings, command="adapters conform", renderer=_render_text_conform)
