"""pyforge.scribe.cli — the `scribe` CLI (FR-14, AD-7).

The CLI is the sole public contract: `capture` (real, Wave 1), `graph
compile [--nightly]` and `recall <query>` (harmless stub subcommands so
the top-level shape never changes between epics — Epic 2 owns their real
implementation). Other components integrate with Scribe via this CLI, never
by importing internal modules directly (AD-7).
"""

from __future__ import annotations

from pathlib import Path

import typer

from pyforge.scribe.capture import capture as capture_write
from pyforge.scribe.models import CaptureType

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
    capture_type: CaptureType = typer.Option(
        ..., "--type", help="Capture type: feedback | project | reference."
    ),
    text: str = typer.Option(..., "--text", help="Raw text to capture verbatim (FR-1)."),
) -> None:
    """Append a new record directly into `.claude/memory/<type>/` (AD-1)."""
    try:
        result = capture_write(_MEMORY_ROOT, capture_type, text)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    typer.echo(f"captured: {result.path}")


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
