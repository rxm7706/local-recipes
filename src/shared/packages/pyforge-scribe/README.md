# pyforge-scribe

Direct-capture CLI for checked-in team memory. `scribe capture` writes a
decision, ADR, or piece of project state straight into `.claude/memory/`
the moment it's made — append-only, no clobber, visible to every
teammate and every agent session from then on (fixing the duplicated
-rediscovery pain that motivated this project; see
`d43899c1cb`).

**Status:** build skeleton + Wave 1 (Story 1.1) — package scaffold and
direct capture only. `scribe graph compile` and `scribe recall` exist as
harmless stub subcommands so the CLI's top-level shape never changes
between epics; their real implementation is Epic 2 (Story 2.1+). See
[`_bmad-output/projects/pyforge-scribe/planning-artifacts/`](../../../../_bmad-output/projects/pyforge-scribe/planning-artifacts/)
for the full spec.

## Develop

Run from the repository root (the parent pixi workspace):

```bash
pixi run -e pyforge-scribe scribe capture --type project --text "..."
pixi run -e pyforge-scribe pyforge-scribe-test  # run the test suite
```

The `pyforge-scribe` environment is lean by design (`no-default-feature`):
it carries only the built package plus its runtime deps (`typer`,
`pydantic`) and a test runner.

## `scribe capture`

```bash
scribe capture --type <feedback|project|reference> --text "<raw text>"
```

Writes a new file under `.claude/memory/<type>/` (frontmatter
`name`/`description`/`metadata.type`, matching the CURRENT live
auto-memory schema — see `.claude/memory/README.md`) and appends one
index line to `.claude/memory/MEMORY.md`. A slug collision appends a
numeric suffix rather than overwriting the original. No network calls;
no file outside `.claude/memory/` is ever touched.

`scribe graph compile [--nightly]` and `scribe recall <query>` are
present but not yet implemented (Epic 2) — they parse their arguments,
print a "not yet implemented" notice to stderr, and exit `0` without
touching the filesystem.
