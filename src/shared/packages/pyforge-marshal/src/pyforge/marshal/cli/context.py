"""``marshal context`` (Story 28.8, SPEC-marshal-token-economy CAP-5) --
the ``derived-context`` layer's operator- and skill-facing surface.

One nested action, ``refresh``: answer whether an epic's derived planning
context (the ``epic-<N>-context.md`` distill and the previous-story
continuity distill) is still valid, so ``bmad-build-auto``'s
``step-01-clarify-and-route.md`` can stop deciding that on an mtime hunch.

The three outcomes, in the exact order the story's ACs name them:

* **Layer declared OFF** (the default -- Story 28.1's "absent block = every
  layer off"): report ``mode=compile-on-hunch`` and exit clean, having
  invoked nothing, written nothing, and read no planning document. Today's
  behavior is byte-identical, which is AC 3.
* **Layer ON and the scribe grammar answered**: report
  ``mode=incremental`` plus one ``fresh``/``stale`` row per declared
  artifact. ``fresh`` means the extra skipped it -- its declared sources
  are unchanged, so the iteration recompiles nothing (AC 1). ``stale``
  means the extra refreshed it -- exactly one recompute, and only for the
  artifact whose sources actually moved (AC 2).
* **Layer ON and the layer degraded**: report ``mode=compile-on-hunch``
  with a WARN ``MRS-CTX-002`` naming the reason. Never a blocked
  iteration -- the spec's own "an unavailable instrument disables its
  layer with a named finding" constraint.

This module owns the boundary I/O the two layers below it may not: listing
the planning/spec/implementation directories, writing the declaration
manifest, and resolving the composed policy. Every decision it makes is
delegated -- ``core/derived_context.py`` for the declaration and the
freshness mapping (pure), ``adapters/scribe_cli.py`` for the subprocess.
No fingerprint is ever computed here: the incremental engine is Scribe's
``compile_surface`` cocoindex extra, consumed strictly through the scribe
CLI grammar (this story's Block-If forbids importing cocoindex anywhere in
``pyforge.marshal``, and the pyforge-scribe SKILL.md forbids importing
``pyforge.scribe`` internals).

The manifest lands under ``.claude/data/pyforge-marshal/derived-context/``
-- blanket-gitignored (``.gitignore``'s ``.claude/data/``), derived, and
disposable, the same home Scribe gives its own fingerprint index. It is a
restatement of the declaration, never a store of record.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyforge.core.atomic_write import atomic_write_text

from ..adapters.scribe_cli import ScribeCli
from ..core import derived_context as derived
from ..core.model import Finding, Severity, build_envelope
from ..core.policy import _is_valid_project_slug
from ..core.verdict import compute_verdict, exit_code_for
from .config import _suppress_downstream_pipe_close, repo_root
from .seed import _resolve_project_slug, resolve_context_layers

#: The declaration could not be resolved at all (malformed slug or epic, or
#: no planning-artifacts directory to list). UNEVALUABLE.
_MRS_CTX_UNEVALUABLE = "MRS-CTX-001"
#: An ENABLED layer degraded to today's compile-on-hunch behavior, with a
#: reason. WARN, never blocking.
_MRS_CTX_DEGRADED = "MRS-CTX-002"

#: Derived, gitignored home for the declaration manifest -- alongside the
#: rest of this repo's per-station derived data, never a tracked artifact.
_MANIFEST_DIR_RELPATH = ".claude/data/pyforge-marshal/derived-context"


def add_context_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register ``context`` with its nested ``refresh`` action."""
    parser = subparsers.add_parser(
        "context",
        help=(
            "Derived planning-context freshness for the declared [context] "
            "pipeline (SPEC-marshal-token-economy CAP-5; Story 28.8)."
        ),
        description=(
            "The derived-context layer: report whether an epic's context and "
            "continuity distills still match their declared planning sources, "
            "so an iteration recompiles exactly when they changed. Freshness "
            "is answered by Scribe's compile_surface cocoindex extra through "
            "the `scribe index refresh` CLI grammar -- marshal declares the "
            "sources and renders the layer flag, never a second engine. With "
            "the layer declared off (the default), today's compile-on-hunch "
            "behavior is unchanged."
        ),
    )
    context_sub = parser.add_subparsers(dest="context_command", required=True)
    refresh = context_sub.add_parser(
        "refresh",
        help="Report derived-context freshness for one epic.",
        description=(
            "Resolves the declared [context] derived-context layer, declares "
            "the epic's derived artifacts and their planning sources, and "
            "reports one fresh/stale row per artifact. Exit code stays inside "
            "marshal's frozen domain; a degraded layer is a WARN finding, "
            "never a blocked iteration."
        ),
    )
    refresh.add_argument(
        "--project",
        default=None,
        metavar="SLUG",
        help=(
            "Project slug (default: BMAD_ACTIVE_PROJECT, then the repo's "
            "active-project marker). Never scripts/bmad-switch."
        ),
    )
    refresh.add_argument(
        "--epic",
        required=True,
        metavar="N",
        help="Epic number whose derived context is being checked.",
    )
    refresh.add_argument(
        "--root",
        default=None,
        metavar="PATH",
        help=(
            "Repo root to operate on (default: this checkout). Fixtures pass "
            "an isolated tree; live runs omit this."
        ),
    )
    refresh.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    refresh.set_defaults(handler=run_context_refresh)


def _listing(directory: Path) -> tuple[str, ...]:
    """Plain filenames directly inside ``directory`` -- ``()`` when it does
    not exist or cannot be read. Shallow, matching the skill's own "List
    files in {{.planning_artifacts}}" step; an unreadable directory is a
    missing source set, never a crash."""
    try:
        return tuple(sorted(entry.name for entry in directory.iterdir() if entry.is_file()))
    except OSError:
        return ()


def run_context_refresh(
    args: argparse.Namespace, *, scribe: ScribeCli | None = None
) -> int:
    """CLI entry for ``marshal context refresh``. ``scribe`` is an
    injection seam so tests drive the grammar without a real install."""
    findings: list[Finding] = []
    root = Path(args.root).resolve() if args.root else repo_root()
    epic = str(args.epic).strip()

    layers = resolve_context_layers(root, args.project)
    layer = layers.get(derived.DERIVED_CONTEXT_LAYER)
    enabled = derived.layer_enabled(layer)
    data: dict[str, object] = {
        "epic": epic,
        "layer": {
            "name": derived.DERIVED_CONTEXT_LAYER,
            "enabled": enabled,
            "aggressiveness": derived.layer_aggressiveness(layer),
        },
        "mode": derived.MODE_COMPILE_ON_HUNCH,
        "artifacts": [],
    }

    # AC 3: a declared-off layer reads no planning document, writes no
    # manifest, and invokes no grammar -- the whole point of "today's
    # behavior is unchanged" is that nothing new happens at all.
    if not enabled:
        return _emit(args, findings, data)

    slug = _resolve_project_slug(root, args.project)
    data["project"] = slug
    if not _resolvable(slug, epic):
        findings.append(
            Finding(
                code=_MRS_CTX_UNEVALUABLE,
                severity=Severity.ERROR,
                message=(
                    f"cannot declare derived context for project {slug!r} "
                    f"epic {epic!r} -- a usable project slug and a plain "
                    "epic number are both required; today's "
                    "compile-on-hunch behavior applies"
                ),
                path=str(root),
            )
        )
        return _emit(args, findings, data)

    planning_dir = root / derived.planning_artifacts_relpath(slug)
    if not planning_dir.is_dir():
        findings.append(
            Finding(
                code=_MRS_CTX_UNEVALUABLE,
                severity=Severity.ERROR,
                message=(
                    f"no planning-artifacts directory at {planning_dir!s} -- "
                    "there is nothing to declare as a source, so today's "
                    "compile-on-hunch behavior applies"
                ),
                path=str(planning_dir),
            )
        )
        return _emit(args, findings, data)

    declarations = derived.declare_derived_context(
        project_slug=slug,
        epic=epic,
        planning_filenames=_listing(planning_dir),
        planning_spec_filenames=_listing(
            root / derived.planning_specs_relpath(slug)
        ),
        implementation_filenames=_listing(
            root / derived.implementation_artifacts_relpath(slug)
        ),
    )
    data["declarations"] = [
        {
            "name": declaration.name,
            "sources": list(declaration.sources),
            "output": declaration.output,
        }
        for declaration in declarations
    ]

    manifest_path = root / _MANIFEST_DIR_RELPATH / f"{slug}-epic-{epic}.json"
    payload = derived.manifest_payload(declarations)
    try:
        atomic_write_text(
            manifest_path, json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )
    except OSError as exc:
        findings.append(
            Finding(
                code=_MRS_CTX_DEGRADED,
                severity=Severity.WARN,
                message=(
                    f"derived-context declaration manifest {manifest_path!s} "
                    f"could not be written ({exc}) -- the layer is off for "
                    "this iteration and today's compile-on-hunch behavior "
                    "applies"
                ),
                path=str(manifest_path),
            )
        )
        return _emit(args, findings, data)
    data["manifest"] = str(manifest_path)

    outcome = (scribe if scribe is not None else ScribeCli()).refresh(
        repo_root=root, manifest_path=manifest_path
    )
    if not outcome.ok:
        findings.append(
            Finding(
                code=_MRS_CTX_DEGRADED,
                severity=Severity.WARN,
                message=str(outcome.reason),
                path=str(root),
            )
        )
        return _emit(args, findings, data)

    data["mode"] = derived.MODE_INCREMENTAL
    freshness = derived.resolve_freshness(
        declarations, refreshed=outcome.refreshed, skipped=outcome.skipped
    )
    data["artifacts"] = [
        {
            "name": item.name,
            "state": item.state,
            "output": item.output,
            "sources": list(item.sources),
        }
        for item in freshness
    ]
    unanswered = [item.name for item in freshness if item.state == derived.STATE_UNKNOWN]
    if unanswered:
        # An artifact the extra named in neither list is a grammar contract
        # miss. Reported (WARN) rather than silently read as fresh: a wrong
        # "fresh" serves a stale distill, the failure this story removes.
        findings.append(
            Finding(
                code=_MRS_CTX_DEGRADED,
                severity=Severity.WARN,
                message=(
                    "the scribe refresh grammar answered for neither refreshed "
                    f"nor skipped on {unanswered!r} -- treat those artifacts as "
                    "needing recompilation"
                ),
                path=str(root),
            )
        )
    return _emit(args, findings, data)


def _resolvable(slug: str, epic: str) -> bool:
    """Whether a declaration can be built at all. The slug check is
    ``core/policy.py``'s own single-path-segment rule (the SAME one every
    other command applies before interpolating a slug into a path); the
    epic check is ``core/derived_context.py``'s."""
    return bool(slug) and _is_valid_project_slug(slug) and derived.valid_epic(epic)


def _emit(
    args: argparse.Namespace, findings: list[Finding], data: dict[str, object]
) -> int:
    verdict = compute_verdict(findings)
    envelope = build_envelope(
        command="context refresh",
        verdict=verdict,
        data=data,
        findings=tuple(findings),
    )
    try:
        if args.format == "json":
            print(
                json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True),
                flush=True,
            )
        else:
            _print_text(data, findings, envelope.verdict)
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def _print_text(
    data: dict[str, object], findings: list[Finding], verdict: object
) -> None:
    layer = data.get("layer") or {}
    print(
        f"context refresh epic={data.get('epic')} "
        f"layer={derived.DERIVED_CONTEXT_LAYER} "
        f"enabled={layer.get('enabled') if isinstance(layer, dict) else None} "
        f"mode={data.get('mode')} verdict={verdict}"
    )
    artifacts = data.get("artifacts")
    if isinstance(artifacts, list) and artifacts:
        print("artifacts:")
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            print(
                f"  - {artifact.get('state')}: {artifact.get('name')} "
                f"({len(artifact.get('sources') or [])} declared source(s))"
            )
    for finding in findings:
        print(f"{finding.code} {finding.severity.value}: {finding.message}")
