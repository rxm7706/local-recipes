"""pyforge.scribe.cli — the `scribe` CLI (FR-14, AD-7).

The CLI is the sole public contract: `capture` (direct write, Wave 1, or
`--promote` scan-classify-propose-confirm, Story 1.3), `graph compile
[--nightly]` (Story 2.2/2.3 -- rebuilds the compiled graph, unattended) and
`recall <query>` (Story 2.4 -- grounded, cited retrieval over that compiled
graph). Other components integrate with Scribe via this CLI, never by
importing internal modules directly (AD-7).
"""

from __future__ import annotations

from pathlib import Path

import typer

from pyforge.scribe.capture import capture as capture_write
from pyforge.scribe.compile import compile_graph, default_store_path
from pyforge.scribe.graph_store import FlatFileGraphStore
from pyforge.scribe.models import CaptureType
from pyforge.scribe.promote import (
    PromotionProposal,
    apply_promotion,
    classify_and_draft,
    default_user_local_root,
)
from pyforge.scribe.recall import answer as recall_answer

app = typer.Typer(
    name="scribe",
    help="Capture decisions directly into checked-in team memory (.claude/memory/).",
    no_args_is_help=True,
)
graph_app = typer.Typer(help="Knowledge-graph projection commands (Epic 2).")
app.add_typer(graph_app, name="graph")

# Resolved relative to the current working directory at invocation time —
# `scribe` is always run from the repo root (never a hardcoded absolute
# path), matching capture.py's injectable-memory-root contract.
_MEMORY_ROOT = Path(".claude") / "memory"


@app.command("capture")
def capture_cmd(
    capture_type: CaptureType | None = typer.Option(
        None, "--type", help="Capture type: feedback | project | reference."
    ),
    text: str | None = typer.Option(
        None, "--text", help="Raw text to capture verbatim (FR-1)."
    ),
    promote: bool = typer.Option(
        False,
        "--promote",
        help=(
            "Scan user-local auto-memory, classify each entry, and propose "
            "team-voice promotions -- proposal-then-confirm (Story 1.3)."
        ),
    ),
    source: Path | None = typer.Option(
        None,
        "--source",
        help="Override the auto-detected user-local auto-memory directory.",
    ),
) -> None:
    """Append a new record directly into `.claude/memory/<type>/` (AD-1), or
    with `--promote`, scan user-local auto-memory and propose promotions."""
    if promote:
        if capture_type is not None or text is not None:
            typer.echo("--promote is mutually exclusive with --type/--text", err=True)
            raise typer.Exit(code=2)
        _run_promote(source)
        return

    if capture_type is None or text is None:
        typer.echo("--type and --text are required unless --promote is set", err=True)
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


@graph_app.command("compile")
def graph_compile(
    nightly: bool = typer.Option(False, "--nightly", help="Run in unattended nightly mode."),
) -> None:
    """Rebuild the compiled knowledge graph from `.claude/memory/`,
    `.memlog.md` files, git history, retros, and CHANGELOGs (Story 2.2/2.3).
    Never prompts -- safe to run from cron/CI with no human present."""
    try:
        result = compile_graph(memory_root=_MEMORY_ROOT, repo_root=Path.cwd(), nightly=nightly)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    for warning in result.warnings:
        typer.echo(f"warning: {warning}", err=True)
    typer.echo(
        f"compiled {result.node_count} node(s), {result.invalidated_count} invalidated "
        f"-> {result.store_path}"
    )


@app.command("recall")
def recall_cmd(
    query: str = typer.Argument(..., help="Natural-language question to recall an answer for."),
) -> None:
    """Answer from the compiled graph with a resolvable citation, or report
    no grounded coverage (Story 2.4, AD-8) -- zero network calls (AD-6)."""
    repo_root = Path.cwd()
    store = FlatFileGraphStore(default_store_path(repo_root))
    result = recall_answer(query, store, repo_root=repo_root)
    if result.grounded:
        typer.echo(result.text)
        typer.echo(f"[source: {result.citation}]")
    else:
        typer.echo("no grounded answer found")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
