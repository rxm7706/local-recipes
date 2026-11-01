# pyforge-scribe

General documentation (architecture, operations, how-tos): docs/MAP.md at the repository root.

Direct-capture CLI for checked-in team memory. `scribe capture` writes a
decision, ADR, or piece of project state straight into `.claude/memory/`
the moment it's made — append-only, no clobber, visible to every
teammate and every agent session from then on (fixing the duplicated
-rediscovery pain that motivated this project; see
`d43899c1cb`).

**Status:** all 9 stories shipped (2 epics) — capture, `scribe graph
compile`, and `scribe recall` are fully implemented (Epic 2 done). See
[`_bmad-output/projects/pyforge-scribe/planning-artifacts/`](../../../../_bmad-output/projects/pyforge-scribe/planning-artifacts/)
for the full spec.

## Develop

Run from the repository root (the parent pixi workspace):

```bash
pixi run -e pyforge-guild scribe capture --type project --text "..."
pixi run -e pyforge-guild scribe recall "why did we pin typer"
pixi run -e pyforge-scribe scribe graph compile
pixi run -e pyforge-scribe pyforge-scribe-test  # run the test suite
```

`scribe capture` and `scribe recall` run from the session default
environment, `pyforge-guild`, which carries the core package
(`spec-pyforge-scribe` CAP-28). The `pyforge-scribe` environment
(`no-default-feature`) adds the heavy compile extras (`graphifyy`,
`cocoindex`, `psycopg`) and the test runner: `scribe graph compile` with an
extra, `scribe index …` and the test suite run there.

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

`scribe graph compile [--nightly]` rebuilds the compiled graph, and
`scribe recall <query>` answers from it with a `[source: …]` citation or
says `no grounded answer found` (Epic 2).
