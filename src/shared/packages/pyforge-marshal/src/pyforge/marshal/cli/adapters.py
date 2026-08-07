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
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from ..adapters.fs_local import FsError, LocalFs
from ..adapters.harness_bmadloop import BmadLoopHarness, HarnessError
from ..core import policy
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


def _emit(args: argparse.Namespace, data: dict[str, object], findings: list[Finding]) -> int:
    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command="adapters sync",
        verdict=verdict_value,
        data=data,
        data_version=1,
        findings=tuple(findings),
    )
    if args.format == "json":
        rendered = json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True)
    else:
        rendered = _render_text(envelope.data, envelope.findings)
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

    # Review finding: an adapter-declared skill_tree (including one from a
    # project-local `.bmad-loop/profiles/*.toml` overlay -- untrusted
    # relative to the packaged profiles) was never confined to `home`.
    # `home / Path(rel)` for an ABSOLUTE `rel` discards `home` entirely
    # (Python's own `Path.__truediv__` semantics), and a `..`-laden
    # relative value can walk out from under `home` just as easily -- both
    # would make `run_adapters_sync` create/repoint a symlink anywhere this
    # process can write, with none of `MRS-ADP-001`'s slug-shape scrutiny.
    # Every declared tree is confined here, ONCE, before any of it reaches
    # `plan_projection` -- an offending tree is skipped (never aborts the
    # whole run, matching this module's own per-tree isolation-of-failure
    # convention) and named in a new registered finding.
    home_resolved = fs.resolve_path(home)
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
