"""pyforge.scribe.cli — the `scribe` CLI (FR-14, AD-7).

The CLI is the sole public contract: `capture` (direct write, Wave 1, or
`--promote` scan-classify-propose-confirm, Story 1.3), `graph compile
[--nightly]` and `recall <query>` (harmless stub subcommands so the
top-level shape never changes between epics — Epic 2 owns their real
implementation). Other components integrate with Scribe via this CLI, never
by importing internal modules directly (AD-7).
"""

from __future__ import annotations

from pathlib import Path

import typer

from pyforge.scribe.capture import capture as capture_write
from pyforge.scribe.models import CaptureType
from pyforge.scribe.promote import (
    PromotionProposal,
    apply_promotion,
    classify_and_draft,
    default_user_local_root,
)

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
    for result in results:
        typer.echo(f"promoted: {result.path}")


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
    """Stub — Epic 2 (Story 2.1+) owns the real graph-compile projection builder."""
    typer.echo("scribe graph compile: not yet implemented", err=True)


@app.command("recall")
def recall_cmd(
    query: str = typer.Argument(..., help="Natural-language question to recall an answer for."),
) -> None:
    """Stub — Epic 2 (Story 2.1+) owns the real, cited recall query path."""
    typer.echo("scribe recall: not yet implemented", err=True)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
