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

Story 28.9 added ``retrieve`` (the planning-graph layer). Story 46.1
(spec-pyforge-marshal CAP-192) adds ``bootstrap`` and ``pack`` -- a bare
clone fetches or rebuilds the shared substrate, and a producer writes the
deterministic pair it fetches. Both live in ``cli/context_bootstrap.py``;
this module only registers them. Story 46.2 (spec-pyforge-marshal CAP-192)
adds ``bundle`` -- the canonical, digest-pinned context bundle extending
Story 28.8's declaration half (``core/context_bundle.py``): no scribe
subprocess, so two harnesses on the same commit produce byte-identical
bundles deterministically.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pyforge.core.atomic_write import atomic_write_text

from ..adapters.scribe_cli import ScribeCli
from ..core import context_bundle
from ..core import derived_context as derived
from ..core import planning_graph as planning
from ..core.model import Finding, Severity, build_envelope
from ..core.policy import _is_valid_project_slug
from ..core.verdict import compute_verdict, exit_code_for
from .config import _suppress_downstream_pipe_close, repo_root
from .context_bootstrap import add_substrate_parsers
from .seed import _resolve_project_slug, resolve_context_layers

#: The declaration could not be resolved at all (malformed slug or epic, or
#: no planning-artifacts directory to list). UNEVALUABLE.
_MRS_CTX_UNEVALUABLE = "MRS-CTX-001"
#: An ENABLED layer degraded to Story 28.8's epic-context-file fallback.
_MRS_CTX_DEGRADED = "MRS-CTX-002"
#: Planning-graph retrieval degraded (Story 28.9). WARN, never blocking.
_MRS_PLAN_DEGRADED = "MRS-PLAN-001"

#: Derived, gitignored home for the declaration manifest -- alongside the
#: rest of this repo's per-station derived data, never a tracked artifact.
_MANIFEST_DIR_RELPATH = ".claude/data/pyforge-marshal/derived-context"


def add_context_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register ``context`` with its nested ``refresh``, ``retrieve``,
    ``bundle``, ``bootstrap`` and ``pack`` actions."""
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
            "behavior is unchanged. `bootstrap` / `pack` (Story 46.1) fetch-or-"
            "rebuild the shared substrate into a bare clone and write the pair "
            "it fetches."
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
        help=("Repo root to operate on (default: this checkout). Fixtures pass an isolated tree; live runs omit this."),
    )
    refresh.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    refresh.set_defaults(handler=run_context_refresh)

    retrieve = context_sub.add_parser(
        "retrieve",
        help="Retrieve scoped planning context for one epic story (Story 28.9).",
        description=(
            "The planning-graph layer: answer with a bounded graph query when "
            "Scribe's recall grammar is available, or report "
            "epic-context-fallback so step-01 uses Story 28.8's distill path. "
            "The story contract spec is never substituted -- retrieval scopes "
            "planning context only."
        ),
    )
    retrieve.add_argument(
        "--project",
        default=None,
        metavar="SLUG",
        help=(
            "Project slug (default: BMAD_ACTIVE_PROJECT, then the repo's "
            "active-project marker). Never scripts/bmad-switch."
        ),
    )
    retrieve.add_argument(
        "--epic",
        required=True,
        metavar="N",
        help="Epic number whose planning context is being retrieved.",
    )
    retrieve.add_argument(
        "--story",
        default=None,
        metavar="M",
        help="Optional story number within the epic (narrows the query).",
    )
    retrieve.add_argument(
        "--root",
        default=None,
        metavar="PATH",
        help=("Repo root to operate on (default: this checkout). Fixtures pass an isolated tree; live runs omit this."),
    )
    retrieve.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    retrieve.set_defaults(handler=run_context_retrieve)

    bundle = context_sub.add_parser(
        "bundle",
        help="Assemble the canonical, digest-pinned context bundle for one epic (Story 46.2).",
        description=(
            "Assembles the declared derived-context artifacts plus the "
            "resolved derived-context/planning-graph layer config into one "
            "canonical, JSON-safe bundle, sha256-hashed over its sorted-key "
            "serialization. No scribe subprocess: two harnesses on the same "
            "commit produce byte-identical bundles deterministically. "
            "`--expect-digest` compares against a prior harness's recorded "
            "digest; a mismatch is a named MRS-CTX-008 WARN finding, never "
            "silent."
        ),
    )
    bundle.add_argument(
        "--project",
        default=None,
        metavar="SLUG",
        help=(
            "Project slug (default: BMAD_ACTIVE_PROJECT, then the repo's "
            "active-project marker). Never scripts/bmad-switch."
        ),
    )
    bundle.add_argument(
        "--epic",
        required=True,
        metavar="N",
        help="Epic number whose context bundle is being assembled.",
    )
    bundle.add_argument(
        "--root",
        default=None,
        metavar="PATH",
        help=("Repo root to operate on (default: this checkout). Fixtures pass an isolated tree; live runs omit this."),
    )
    bundle.add_argument(
        "--expect-digest",
        default=None,
        metavar="SHA256",
        help="A prior harness's recorded bundle digest to compare against (optional).",
    )
    bundle.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    bundle.set_defaults(handler=run_context_bundle)

    # Story 46.1 (spec-pyforge-marshal CAP-192): the substrate bootstrap and
    # its producer, owned by cli/context_bootstrap.py.
    add_substrate_parsers(context_sub)


def _listing(directory: Path) -> tuple[str, ...]:
    """Plain filenames directly inside ``directory`` -- ``()`` when it does
    not exist or cannot be read. Shallow, matching the skill's own "List
    files in {{.planning_artifacts}}" step; an unreadable directory is a
    missing source set, never a crash."""
    try:
        return tuple(sorted(entry.name for entry in directory.iterdir() if entry.is_file()))
    except OSError:
        return ()


def run_context_refresh(args: argparse.Namespace, *, scribe: ScribeCli | None = None) -> int:
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
        planning_spec_filenames=_listing(root / derived.planning_specs_relpath(slug)),
        implementation_filenames=_listing(root / derived.implementation_artifacts_relpath(slug)),
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
        atomic_write_text(manifest_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
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

    outcome = (scribe if scribe is not None else ScribeCli()).refresh(repo_root=root, manifest_path=manifest_path)
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
    freshness = derived.resolve_freshness(declarations, refreshed=outcome.refreshed, skipped=outcome.skipped)
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


def run_context_retrieve(args: argparse.Namespace, *, scribe: ScribeCli | None = None) -> int:
    """CLI entry for ``marshal context retrieve``. ``scribe`` is an
    injection seam so tests drive the grammar without a real install."""
    findings: list[Finding] = []
    root = Path(args.root).resolve() if args.root else repo_root()
    epic = str(args.epic).strip()
    story = str(args.story).strip() if args.story else None

    layers = resolve_context_layers(root, args.project)
    layer = layers.get(planning.PLANNING_GRAPH_LAYER)
    enabled = planning.layer_enabled(layer)
    slug = _resolve_project_slug(root, args.project)
    fallback_path = derived.epic_context_output_relpath(slug, epic) if slug and derived.valid_epic(epic) else None
    data: dict[str, object] = {
        "epic": epic,
        "story": story,
        "layer": {
            "name": planning.PLANNING_GRAPH_LAYER,
            "enabled": enabled,
            "aggressiveness": planning.layer_aggressiveness(layer),
        },
        "mode": planning.MODE_EPIC_CONTEXT_FALLBACK,
        "grounded": False,
        "text": None,
        "citation": None,
        "fallback": fallback_path,
        "tokens_saved": None,
        "contract_note": (
            "The story contract spec and acceptance criteria must still be "
            "read verbatim -- retrieval scopes planning context only."
        ),
    }

    if not enabled:
        return _emit_retrieve(args, findings, data)

    if not slug or not derived.valid_epic(epic):
        findings.append(
            Finding(
                code=_MRS_CTX_UNEVALUABLE,
                severity=Severity.ERROR,
                message=(
                    f"cannot retrieve planning context for project {slug!r} "
                    f"epic {epic!r} -- a usable project slug and a plain "
                    "epic number are both required; Story 28.8's "
                    "epic-context-file fallback applies"
                ),
                path=str(root),
            )
        )
        return _emit_retrieve(args, findings, data)

    data["project"] = slug
    query = planning.build_routing_query(project_slug=slug, epic=epic, story=story)
    data["query"] = query

    outcome = (scribe if scribe is not None else ScribeCli()).recall(repo_root=root, query=query, scope=slug)
    if not outcome.ok:
        findings.append(
            Finding(
                code=_MRS_PLAN_DEGRADED,
                severity=Severity.WARN,
                message=str(outcome.reason),
                path=str(root),
            )
        )
        return _emit_retrieve(args, findings, data)

    mode = planning.resolve_retrieval_mode(layer_enabled=True, recall_ok=True, grounded=outcome.grounded)
    data["mode"] = mode
    data["grounded"] = outcome.grounded
    if outcome.grounded:
        data["text"] = outcome.text
        data["citation"] = outcome.citation
        data["tokens_saved"] = planning.estimate_tokens_saved(mode=mode)
    else:
        findings.append(
            Finding(
                code=_MRS_PLAN_DEGRADED,
                severity=Severity.WARN,
                message=(
                    "scribe recall returned no grounded answer (including "
                    "when the only candidates were stale) -- Story 28.8's "
                    "epic-context-file fallback applies"
                ),
                path=str(root),
            )
        )
    return _emit_retrieve(args, findings, data)


def _emit_retrieve(args: argparse.Namespace, findings: list[Finding], data: dict[str, object]) -> int:
    verdict = compute_verdict(findings)
    envelope = build_envelope(
        command="context retrieve",
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
            _print_retrieve_text(data, findings, envelope.verdict)
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def _print_retrieve_text(data: dict[str, object], findings: list[Finding], verdict: object) -> None:
    layer = data.get("layer") or {}
    print(
        f"context retrieve epic={data.get('epic')} story={data.get('story')} "
        f"layer={planning.PLANNING_GRAPH_LAYER} "
        f"enabled={layer.get('enabled') if isinstance(layer, dict) else None} "
        f"mode={data.get('mode')} grounded={data.get('grounded')} "
        f"verdict={verdict}"
    )
    if data.get("mode") == planning.MODE_GRAPH and data.get("text"):
        print("context:")
        print(data["text"])
        if data.get("citation"):
            print(f"[source: {data['citation']}]")
    elif data.get("fallback"):
        print(f"fallback: {data['fallback']}")
    if data.get("tokens_saved") is not None:
        print(f"tokens_saved: {data['tokens_saved']}")
    for finding in findings:
        print(f"{finding.code} {finding.severity.value}: {finding.message}")


def _resolvable(slug: str, epic: str) -> bool:
    """Whether a declaration can be built at all. The slug check is
    ``core/policy.py``'s own single-path-segment rule (the SAME one every
    other command applies before interpolating a slug into a path); the
    epic check is ``core/derived_context.py``'s."""
    return bool(slug) and _is_valid_project_slug(slug) and derived.valid_epic(epic)


def _emit(args: argparse.Namespace, findings: list[Finding], data: dict[str, object]) -> int:
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


def _print_text(data: dict[str, object], findings: list[Finding], verdict: object) -> None:
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


def run_context_bundle(args: argparse.Namespace) -> int:
    """CLI entry for ``marshal context bundle`` (Story 46.2, spec-pyforge-
    marshal CAP-192). Assembles the canonical, digest-pinned context bundle
    for one epic from already-declared, already-resolved data only -- no
    scribe subprocess, so two harnesses on the same commit produce
    byte-identical bundles deterministically."""
    findings: list[Finding] = []
    root = Path(args.root).resolve() if args.root else repo_root()
    epic = str(args.epic).strip()
    expect_digest = (args.expect_digest or "").strip() or None

    layers = resolve_context_layers(root, args.project)
    derived_layer = layers.get(derived.DERIVED_CONTEXT_LAYER)
    planning_layer = layers.get(planning.PLANNING_GRAPH_LAYER)
    data: dict[str, object] = {
        "epic": epic,
        "digest": None,
        "expect_digest": expect_digest,
        "match": None,
        "bundle": None,
    }

    slug = _resolve_project_slug(root, args.project)
    data["project"] = slug
    if not _resolvable(slug, epic):
        findings.append(
            Finding(
                code=_MRS_CTX_UNEVALUABLE,
                severity=Severity.ERROR,
                message=(
                    f"cannot assemble a context bundle for project {slug!r} "
                    f"epic {epic!r} -- a usable project slug and a plain "
                    "epic number are both required; no bundle/digest computed"
                ),
                path=str(root),
            )
        )
        return _emit_bundle(args, findings, data)

    planning_dir = root / derived.planning_artifacts_relpath(slug)
    if not planning_dir.is_dir():
        findings.append(
            Finding(
                code=_MRS_CTX_UNEVALUABLE,
                severity=Severity.ERROR,
                message=(
                    f"no planning-artifacts directory at {planning_dir!s} -- "
                    "there is nothing to declare as a source; no bundle/"
                    "digest computed"
                ),
                path=str(planning_dir),
            )
        )
        return _emit_bundle(args, findings, data)

    declarations = derived.declare_derived_context(
        project_slug=slug,
        epic=epic,
        planning_filenames=_listing(planning_dir),
        planning_spec_filenames=_listing(root / derived.planning_specs_relpath(slug)),
        implementation_filenames=_listing(root / derived.implementation_artifacts_relpath(slug)),
    )
    bundle = context_bundle.assemble_bundle(
        epic=epic,
        derived_context_layer=derived_layer,
        planning_graph_layer=planning_layer,
        declarations=declarations,
    )
    digest = context_bundle.bundle_digest(bundle)
    data["bundle"] = bundle
    data["digest"] = digest

    if expect_digest:
        match = expect_digest.lower() == digest.lower()
        data["match"] = match
        if not match:
            findings.append(context_bundle.digest_mismatch_finding(epic=epic, expected=expect_digest, computed=digest))
    return _emit_bundle(args, findings, data)


def _emit_bundle(args: argparse.Namespace, findings: list[Finding], data: dict[str, object]) -> int:
    verdict = compute_verdict(findings)
    envelope = build_envelope(
        command="context bundle",
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
            _print_bundle_text(data, findings, envelope.verdict)
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def _print_bundle_text(data: dict[str, object], findings: list[Finding], verdict: object) -> None:
    print(
        f"context bundle epic={data.get('epic')} digest={data.get('digest')} "
        f"expect_digest={data.get('expect_digest')} match={data.get('match')} "
        f"verdict={verdict}"
    )
    bundle = data.get("bundle")
    if isinstance(bundle, dict):
        derived_ctx = bundle.get("derived_context") or {}
        planning_ctx = bundle.get("planning_graph") or {}
        if isinstance(derived_ctx, dict):
            print(
                f"derived_context: enabled={derived_ctx.get('enabled')} "
                f"aggressiveness={derived_ctx.get('aggressiveness')}"
            )
            declarations = derived_ctx.get("declarations")
            if isinstance(declarations, list) and declarations:
                print("declarations:")
                for declaration in declarations:
                    if not isinstance(declaration, dict):
                        continue
                    print(f"  - {declaration.get('name')} ({len(declaration.get('sources') or [])} declared source(s))")
        if isinstance(planning_ctx, dict):
            print(
                f"planning_graph: enabled={planning_ctx.get('enabled')} "
                f"aggressiveness={planning_ctx.get('aggressiveness')}"
            )
    for finding in findings:
        print(f"{finding.code} {finding.severity.value}: {finding.message}")
