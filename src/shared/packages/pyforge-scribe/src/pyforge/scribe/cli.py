"""pyforge.scribe.cli — the `scribe` CLI (FR-14, AD-7).

The CLI is the sole public contract: `capture` (direct write, Wave 1,
`--promote` scan-classify-propose-confirm, Story 1.3, or `--transcripts`
scan-propose-confirm over raw session transcripts, Story 3.1), `graph
compile [--nightly]` (Story 2.2/2.3 -- rebuilds the compiled graph,
unattended), `recall <query>` (Story 2.4 -- grounded, cited retrieval over
that compiled graph), and `index build|report|move-list|refresh` (Story 6.1
-- the graphify `compile_surface` extra's explicit ingest + report verbs;
Story 6.2 adds `refresh`, the cocoindex incremental-ingest extra's own
verb). Other components integrate with Scribe via this CLI, never by
importing internal modules directly (AD-7).
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pyforge.core.atomic_write import atomic_write_text

from pyforge.scribe import __version__
from pyforge.scribe.capture import capture as capture_write
from pyforge.scribe.compile import (
    CompileInProgressError,
    compile_graph,
    default_store_path,
)
from pyforge.scribe.extras.cocoindex_flow import (
    CocoindexUnavailableError,
    DerivedArtifact,
    cocoindex_extra_enabled,
    refresh_incremental,
)
from pyforge.scribe.extras.graphify import (
    DEFAULT_GRAPHIFY_TARGET,
    GraphifyUnavailableError,
    build_graph_report,
    ingest_repo,
)
from pyforge.scribe.extras.move_list import move_list_sources, scan_move_list
from pyforge.scribe.graph_store_plugins import open_graph_store
from pyforge.scribe.models import CaptureType
from pyforge.scribe.promote import (
    PromotionProposal,
    apply_promotion,
    classify_and_draft,
    default_user_local_root,
)
from pyforge.scribe.recall import answer as recall_answer
from pyforge.scribe.transcripts import (
    TranscriptScanProposal,
    default_transcript_root,
    scan_transcripts,
)

app = typer.Typer(
    name="scribe",
    help="Capture decisions directly into checked-in team memory (.claude/memory/).",
    no_args_is_help=True,
)
graph_app = typer.Typer(help="Knowledge-graph projection commands (Epic 2).")
app.add_typer(graph_app, name="graph")
index_app = typer.Typer(
    help=("graphify compile_surface ingest + report verbs (Story 6.1); cocoindex incremental refresh (Story 6.2).")
)
app.add_typer(index_app, name="index")

# Resolved relative to the current working directory at invocation time —
# `scribe` is always run from the repo root (never a hardcoded absolute
# path), matching capture.py's injectable-memory-root contract.
_MEMORY_ROOT = Path(".claude") / "memory"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"scribe {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show scribe's version and exit.",
    ),
) -> None:
    # No docstring on purpose: `typer.Typer(help=...)` above already sets the
    # app's help text; a callback docstring would shadow it. Purely additive
    # -- this callback exists only to host the eager `--version` option, and
    # `no_args_is_help=True` on `app` still governs bare `scribe` invocation.
    pass


@app.command("capture")
def capture_cmd(
    capture_type: CaptureType | None = typer.Option(
        None, "--type", help="Capture type: feedback | project | reference."
    ),
    text: str | None = typer.Option(None, "--text", help="Raw text to capture verbatim (FR-1)."),
    promote: bool = typer.Option(
        False,
        "--promote",
        help=(
            "Scan user-local auto-memory, classify each entry, and propose "
            "team-voice promotions -- proposal-then-confirm (Story 1.3)."
        ),
    ),
    transcripts: bool = typer.Option(
        False,
        "--transcripts",
        help=(
            "Scan raw session transcripts for un-curated decision/fact "
            "sentences and propose captures -- proposal-then-confirm "
            "(Story 3.1)."
        ),
    ),
    source: Path | None = typer.Option(
        None,
        "--source",
        help=(
            "Override the auto-detected user-local auto-memory directory "
            "(--promote) or session-transcript directory (--transcripts)."
        ),
    ),
) -> None:
    """Append a new record directly into `.claude/memory/<type>/` (AD-1), or
    with `--promote`, scan user-local auto-memory and propose promotions, or
    with `--transcripts`, scan raw session transcripts and propose captures."""
    if promote and transcripts:
        typer.echo("--transcripts is mutually exclusive with --promote", err=True)
        raise typer.Exit(code=2)

    if transcripts:
        if capture_type is not None or text is not None:
            typer.echo("--transcripts is mutually exclusive with --type/--text", err=True)
            raise typer.Exit(code=2)
        _run_transcripts(source)
        return

    if promote:
        if capture_type is not None or text is not None:
            typer.echo("--promote is mutually exclusive with --type/--text", err=True)
            raise typer.Exit(code=2)
        _run_promote(source)
        return

    if capture_type is None or text is None:
        typer.echo(
            "--type and --text are required unless --promote/--transcripts is set",
            err=True,
        )
        raise typer.Exit(code=2)

    try:
        result = capture_write(_MEMORY_ROOT, capture_type, text)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"captured: {result.path}")


def _run_promote(source: Path | None) -> None:
    """The `--promote` flow: scan, print the proposal, confirm, apply.

    Zero writes under `.claude/memory/` happen before the user answers the
    `typer.confirm()` prompt -- declining prints a cancellation notice and
    exits 0 with nothing written (FR-3).
    """
    source_root = source if source is not None else default_user_local_root()
    try:
        proposal = classify_and_draft(source_root, memory_root=_MEMORY_ROOT, repo_root=Path.cwd())
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    typer.echo(_render_proposal(proposal))

    if not proposal.promotable:
        typer.echo("Nothing to promote.")
        raise typer.Exit(code=0)

    if not typer.confirm("Write these promotions?"):
        typer.echo("Cancelled -- no files written.")
        raise typer.Exit(code=0)

    results = apply_promotion(_MEMORY_ROOT, proposal)
    for result, entry in zip(results, proposal.promotable):
        typer.echo(f"promoted: {result.path}")
        typer.echo(f"pointer-stub: {entry.source_path}")


def _render_proposal(proposal: PromotionProposal) -> str:
    """Plain-text rendering of a `PromotionProposal` for the confirm prompt:
    every entry's classification + reason, and for `team-relevant` entries,
    the target path, full rewritten content, and `MEMORY.md` index line."""
    lines = [f"Scanned {proposal.source_root}:"]
    counts: dict[str, int] = {}
    for entry in proposal.entries:
        counts[entry.classification] = counts.get(entry.classification, 0) + 1
        lines.append(f"  [{entry.classification}] {entry.source_path.name} -- {entry.reason}")
        if entry.classification == "team-relevant":
            lines.append(f"      -> {entry.target_path}")
            lines.append(f"      MEMORY.md line: {entry.memory_index_line}")
            lines.append("      --- rewritten content ---")
            for content_line in (entry.rewritten_text or "").splitlines():
                lines.append(f"      {content_line}")
            lines.append("      --------------------------")

    summary = ", ".join(f"{count} {classification}" for classification, count in sorted(counts.items()))
    noun = "entry" if len(proposal.entries) == 1 else "entries"
    lines.append(f"{len(proposal.entries)} {noun} scanned: {summary or 'none'}.")
    return "\n".join(lines)


def _run_transcripts(source: Path | None) -> None:
    """The `--transcripts` flow: scan, print the proposal, confirm, apply.

    Mirrors `_run_promote()` exactly: zero writes under `.claude/memory/`
    happen before the user answers the `typer.confirm()` prompt -- declining
    prints a cancellation notice and exits 0 with nothing written. Each
    accepted candidate is written via the same `capture()` path using the
    FULL sentence (`candidate.text`), never the truncated `candidate.snippet`.
    Unlike `_run_promote()`, there is no pointer-stub write-back: a session
    transcript is a historical log this package does not own and must never
    mutate (see transcripts.py's module docstring).
    """
    transcript_root = source if source is not None else default_transcript_root()
    try:
        proposal = scan_transcripts(transcript_root, memory_root=_MEMORY_ROOT)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    # Story 3.3 bound warnings (cap skips, per-file timeouts) -- surfaced the
    # same way `graph compile` reports its own, so a capped interactive scan
    # is never mistaken for a complete one. No cache here: the interactive
    # flow has no durable home for one (cache_path stays None).
    for warning in proposal.warnings:
        typer.echo(f"warning: {warning}", err=True)

    typer.echo(_render_transcript_proposal(proposal))

    if not proposal.candidates:
        typer.echo("Nothing to promote.")
        raise typer.Exit(code=0)

    if not typer.confirm("Write these captures?"):
        typer.echo("Cancelled -- no files written.")
        raise typer.Exit(code=0)

    for candidate in proposal.candidates:
        try:
            result = capture_write(_MEMORY_ROOT, candidate.capture_type, candidate.text)
        except (ValueError, TimeoutError) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=2) from exc
        typer.echo(f"captured: {result.path}")


def _render_transcript_proposal(proposal: TranscriptScanProposal) -> str:
    """Plain-text rendering of a `TranscriptScanProposal` for the confirm
    prompt: every candidate's transcript+position provenance
    (`<jsonl filename>:L<line number>` plus timestamp) and its truncated
    `snippet` -- never the full `text` (Boundaries & Constraints: "quote
    only a truncated snippet... never the full message")."""
    lines = [f"Scanned {proposal.transcript_root}:"]
    for candidate in proposal.candidates:
        lines.append(
            f"  [{candidate.capture_type}] {candidate.source_file.name}:L{candidate.line_number} "
            f"({candidate.timestamp})"
        )
        lines.append(f"      {candidate.snippet}")
    noun = "candidate" if len(proposal.candidates) == 1 else "candidates"
    lines.append(f"{len(proposal.candidates)} {noun} found.")
    return "\n".join(lines)


@graph_app.command("compile")
def graph_compile(
    nightly: bool = typer.Option(False, "--nightly", help="Run in unattended nightly mode."),
) -> None:
    """Rebuild the compiled knowledge graph from `.claude/memory/`,
    `.memlog.md` files, git history, retros, CHANGELOGs (Story 2.2/2.3), and
    un-curated session transcripts (Story 3.2; bounded per Story 3.3). Never
    prompts -- safe to run from cron with no human present; the documented
    nightly trigger is an opt-in operator crontab entry (see this package's
    `docs/cli-runbooks.md`). An overlapping run against the same store skips
    cleanly with exit 0 rather than double-writing."""
    try:
        result = compile_graph(memory_root=_MEMORY_ROOT, repo_root=Path.cwd(), nightly=nightly)
    except CompileInProgressError as exc:
        # Benign under a scheduler (Story 3.3): an overlapping cron firing
        # must not produce a non-zero exit / red cron mail -- mirror the
        # runbook cron line's own `flock -n` skip semantics.
        typer.echo(f"skipped: {exc}", err=True)
        raise typer.Exit(code=0) from exc
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    for warning in result.warnings:
        typer.echo(f"warning: {warning}", err=True)
    typer.echo(
        f"compiled {result.node_count} node(s), {result.invalidated_count} invalidated, "
        f"{result.stale_count} stale -> {result.store_path}"
    )


@app.command("recall")
def recall_cmd(
    query: str = typer.Argument(..., help="Natural-language question to recall an answer for."),
    semantic: bool = typer.Option(
        False,
        "--semantic",
        help=("Opt-in: rank by SHA-256 bag-of-concepts similarity (pgvector driver only; not embedding-model recall)."),
    ),
    scope: str = typer.Option(
        None,
        "--scope",
        help=(
            "Restrict candidates to one project's planning tree "
            "(_bmad-output/projects/<scope>/) plus that slug's Herald "
            "fact ledger (presentations/<scope>/facts.yaml). Lexical "
            "token-overlap alone has no notion of project (marshal "
            "Story 28.27; scribe Story 9.1)."
        ),
    ),
    kind: list[str] = typer.Option(
        None,
        "--kind",
        help=(
            "Restrict candidates to these GraphNode kinds (repeatable). "
            "Default omits code. Pass --kind code to search AST nodes only; "
            "combine kinds explicitly when you want more than one. "
            "Exclusive with --mode."
        ),
    ),
    surface: str | None = typer.Option(
        None,
        "--mode",
        help=(
            "Named candidate bag: planning (doc+memlog), memory, or code. "
            "Exclusive with --kind. Distinct from --semantic ranking."
        ),
    ),
) -> None:
    """Answer from the compiled graph with a resolvable citation, or report
    no grounded coverage (Story 2.4, AD-8) -- zero network calls (AD-6)."""
    repo_root = Path.cwd()
    store = open_graph_store(default_store_path(repo_root))
    mode = "semantic" if semantic else "lexical"
    kinds = frozenset(kind) if kind else None
    try:
        result = recall_answer(
            query,
            store,
            repo_root=repo_root,
            mode=mode,
            scope=scope,
            kinds=kinds,
            surface=surface,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    if result.grounded:
        typer.echo(result.text)
        typer.echo(f"[source: {result.citation}]")
    else:
        typer.echo("no grounded answer found")


def _index_artifact_path(repo_root: Path, name: str) -> Path:
    """Derived, gitignored home for `scribe index`'s own artifacts --
    alongside `graph.json` (AC3), never a foundry-root product dir."""
    return repo_root / ".claude" / "data" / "pyforge-scribe" / name


_TARGET_OPTION = typer.Option(
    None,
    "--target",
    help=(
        "Folder to ingest, repo-relative. Omit to walk the named list "
        "(src/shared/packages, src/platform, scripts) — not recipes/."
    ),
)

_DECLARE_OPTION = typer.Option(
    None,
    "--declare",
    help=(
        "Path to a caller-declared artifact manifest "
        '({"artifacts": [{"name", "sources", "output"}, ...]}) -- fingerprints '
        "each declared artifact's sources instead of scribe's own two "
        "graph/move-list registrations (Story 6.2 design)."
    ),
)


@index_app.command("build")
def index_build(target: Path | None = _TARGET_OPTION) -> None:
    """Ingest `target` with graphifyy and write GraphNodes through the
    persist port (`open_graph_store`) -- never a parallel store (Story 6.1,
    AC2). Omit `--target` to walk the named list (Story 15.1). Explicit
    and deliberate: unlike `scribe graph compile`'s automatic fan-in, this
    command does not consult `SCRIBE_GRAPHIFY_EXTRA`."""
    repo_root = Path.cwd()
    warnings: list[str] = []
    try:
        count = _write_graph_index(repo_root, target, warnings)
    except GraphifyUnavailableError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    for warning in warnings:
        typer.echo(f"warning: {warning}", err=True)
    typer.echo(f"indexed {count} code node(s) -> {default_store_path(repo_root)}")


@index_app.command("report")
def index_report(target: Path | None = _TARGET_OPTION) -> None:
    """Write a GRAPH_REPORT-style summary (incl. God-node findings) to a
    derived, gitignored artifact (Story 6.1, AC3)."""
    repo_root = Path.cwd()
    try:
        report_text = build_graph_report(repo_root, target=target)
    except (GraphifyUnavailableError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    report_path = _index_artifact_path(repo_root, "graph-report.md")
    atomic_write_text(report_path, report_text)
    typer.echo(f"wrote {report_path}")


@index_app.command("move-list")
def index_move_list() -> None:
    """Scan for the foundry-cutover move-list signals (host `import
    pyforge.*` sites, `sys.path` inserts, `five_tier` roots, CFE callers)
    and write the result to a derived, gitignored artifact (Story 6.1, AC3).
    Does not require graphifyy or `SCRIBE_GRAPHIFY_EXTRA`."""
    repo_root = Path.cwd()
    count = _write_move_list(repo_root)
    typer.echo(f"wrote {_index_artifact_path(repo_root, 'move-list.json')} ({count} finding(s))")


def _write_move_list(repo_root: Path) -> int:
    """Run the move-list scan and write it -- shared by `index move-list`
    and `index refresh`'s cocoindex-gated derive step (Story 6.2)."""
    findings = scan_move_list(repo_root)
    document = {
        "findings": [
            {
                "category": f.category,
                "path": f.path,
                "line": f.line,
                "snippet": f.snippet,
            }
            for f in findings
        ]
    }
    move_list_path = _index_artifact_path(repo_root, "move-list.json")
    atomic_write_text(move_list_path, json.dumps(document, indent=2, sort_keys=True) + "\n")
    return len(findings)


def _write_graph_index(repo_root: Path, target: Path | None, warnings: list[str]) -> int:
    """Ingest `target` with graphifyy and upsert through the persist port --
    shared by `index build` and `index refresh`'s cocoindex-gated derive
    step (Story 6.2). Raises `GraphifyUnavailableError` unchanged; callers
    decide how to report it."""
    nodes = ingest_repo(repo_root, target=target, warnings=warnings)
    store = open_graph_store(default_store_path(repo_root))
    for node in nodes:
        store.upsert_node(node)
    store.commit()
    return len(nodes)


@index_app.command("refresh")
def index_refresh(target: Path | None = _TARGET_OPTION, declare: Path | None = _DECLARE_OPTION) -> None:
    """Incrementally refresh Story 6.1's two derived artifacts -- the
    graphify-ingested code graph and the foundry-cutover move list -- via
    the cocoindex `compile_surface` extra (Story 6.2): an artifact whose
    declared sources are unchanged since the last `index refresh` is
    skipped entirely (AC2). Off by default (`SCRIBE_COCOINDEX_EXTRA` unset)
    this behaves exactly like running `index build` then `index move-list`
    -- both artifacts recomputed every time, no fingerprint index read or
    written (AC1).

    `--declare <manifest>` (marshal Story 28.28/CAP-5) bypasses both of the
    above entirely -- a caller hands its OWN "sources -> artifact"
    registrations instead of scribe's built-in two. Explicit invocation is
    already the opt-in (`cocoindex_extra_enabled`'s own contract), so this
    path never consults `SCRIBE_COCOINDEX_EXTRA`. Scribe does not know how
    to regenerate a caller's content -- that is the calling agent's own
    job -- so each declared artifact's `derive()` is a no-op: this verb
    only ever answers "did the declared sources change", tracked in a
    caller-namespaced index file (`_index_artifact_path`, alongside
    `graph.json`) that never shares state with the graph/move-list index
    `default_cocoindex_index_path` owns."""
    repo_root = Path.cwd()
    warnings: list[str] = []

    if declare is not None:
        _index_refresh_declared(repo_root, declare, warnings)
        return

    if not cocoindex_extra_enabled():
        try:
            graph_count = _write_graph_index(repo_root, target, warnings)
        except GraphifyUnavailableError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=2) from exc
        move_count = _write_move_list(repo_root)
        for warning in warnings:
            typer.echo(f"warning: {warning}", err=True)
        typer.echo(
            f"refreshed: graphify-ingest ({graph_count} node(s)), "
            f"move-list ({move_count} finding(s)) -- cocoindex extra off, full rebuild"
        )
        return

    graph_target = target if target is not None else DEFAULT_GRAPHIFY_TARGET
    # Per-artifact counts for the report line below, captured by each
    # derive() closure as it actually runs -- kept CLI-local (never threaded
    # through `DerivedArtifact`/`RefreshResult`, which stay opaque per the
    # Design Notes: the generic engine must not special-case its callers).
    counts: dict[str, str] = {}

    def _derive_move_list() -> None:
        counts["move-list"] = f"{_write_move_list(repo_root)} finding(s)"

    def _derive_graph_index() -> None:
        counts["graphify-ingest"] = f"{_write_graph_index(repo_root, target, warnings)} node(s)"

    artifacts = [
        DerivedArtifact(
            name="move-list",
            sources=tuple(move_list_sources(repo_root)),
            derive=_derive_move_list,
        ),
        DerivedArtifact(
            name="graphify-ingest",
            sources=(repo_root / graph_target,),
            derive=_derive_graph_index,
        ),
    ]
    try:
        result = refresh_incremental(repo_root, artifacts, warnings=warnings)
    except (GraphifyUnavailableError, CocoindexUnavailableError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    for warning in warnings:
        typer.echo(f"warning: {warning}", err=True)
    refreshed_desc = ", ".join(f"{name} ({counts[name]})" if name in counts else name for name in result.refreshed)
    typer.echo(
        f"refreshed: {refreshed_desc or '(none)'}; "
        f"skipped (unchanged): {', '.join(result.skipped) or '(none)'} "
        f"-> {result.index_path}"
    )


def _declared_artifacts_index_path(repo_root: Path) -> Path:
    """The `--declare` path's own fingerprint index -- namespaced apart
    from `default_cocoindex_index_path` (the graph/move-list index) so the
    two never read or clobber each other's entries."""
    return _index_artifact_path(repo_root, "declared-artifacts-index.json")


def _index_refresh_declared(repo_root: Path, manifest_path: Path, warnings: list[str]) -> None:
    """`index refresh --declare <manifest_path>` -- see `index_refresh`'s
    own docstring for the contract. Never raises past this function: a
    malformed manifest or an unavailable cocoindex both exit(2) with a
    message, matching the plain-refresh path's own failure shape."""
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        typer.echo(f"could not read declare manifest {manifest_path}: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    except ValueError as exc:
        typer.echo(f"declare manifest {manifest_path} is not valid JSON: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    raw_artifacts = document.get("artifacts") if isinstance(document, dict) else None
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        typer.echo(
            f"declare manifest {manifest_path} has no non-empty 'artifacts' list",
            err=True,
        )
        raise typer.Exit(code=2)

    artifacts: list[DerivedArtifact] = []
    for entry in raw_artifacts:
        name = entry.get("name") if isinstance(entry, dict) else None
        sources = entry.get("sources") if isinstance(entry, dict) else None
        if not isinstance(name, str) or not name or not isinstance(sources, list):
            typer.echo(
                f"declare manifest {manifest_path} has a malformed artifact entry "
                f"(needs a non-empty 'name' string and a 'sources' list): {entry!r}",
                err=True,
            )
            raise typer.Exit(code=2)
        artifacts.append(
            DerivedArtifact(
                name=name,
                sources=tuple(Path(source) for source in sources),
                derive=lambda: None,
            )
        )

    try:
        result = refresh_incremental(
            repo_root,
            artifacts,
            index_path=_declared_artifacts_index_path(repo_root),
            warnings=warnings,
        )
    except CocoindexUnavailableError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    for warning in warnings:
        typer.echo(f"warning: {warning}", err=True)
    typer.echo(
        f"refreshed: {', '.join(result.refreshed) or '(none)'}; "
        f"skipped (unchanged): {', '.join(result.skipped) or '(none)'} "
        f"-> {result.index_path}"
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
