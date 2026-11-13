# Public contract — Scribe

Companion to `SPEC.md` (CAP-4, amended 2026-11-10; FR-54; AD-7, the CLI is the sole public contract). It records
everything scribe serves to a caller: every CLI verb path and flag, the MCP tools, the feature-flag key, every
environment variable and every exit code. A second root that rebuilds scribe from its Spec rebuilds this surface.

The guard is `src/shared/packages/pyforge-scribe/tests/meta/test_public_contract.py`. It derives the code side (the
click tree of `pyforge.scribe.cli.app`; an AST scan of `typer.Exit(code=)` and of `os.environ` reads over the package
and the scripts `scripts/scribe_*.py` and `scripts/bmad_estate_check.py`; the string literals of the form
`pyforge.<station>.<name>` that name no module; the `*_TOOL` constants of django-scribe's `mcp_asgi.py`, read as text)
and fails, naming the item and its family, for each one present in the code and absent here. A change that adds a
verb, flag, tool, flag key, variable or exit code adds its row here in the same change.

How the test reads this file: only the table rows under the five `##` headings below, and only their first cell (the
second cell too, for the flags of a verb path and for an exit code), as backticked tokens. Prose is not read. Keep
the headings exact.

## CLI verbs and flags

The program is `scribe` (`[project.scripts] scribe = "pyforge.scribe.cli:main"`); the same tree is reached as
`pyforge scribe` through pyforge-core's `pyforge` dispatcher. Run it from the repository root. `--help` on every
command is Click's own and is not listed. The rows below are the five command groups `capture`, `recall`, `graph`,
`index` and `catalog`, one row per verb path.

| Verb path | Flags | Arguments | What it does |
|---|---|---|---|
| `scribe` | `--version`, `--install-completion`, `--show-completion` | — | The root group. `--version` prints `scribe <version>`; the two completion flags are typer's own. Bare `scribe` prints help. |
| `scribe capture` | `--type`, `--text`, `--promote`, `--transcripts`, `--source` | — | Appends a record to `.claude/memory/<type>/` (`--type` is `feedback`, `project` or `reference`; `--text` is kept verbatim) and prints `captured: <path>`. `--promote` proposes team-voice promotions of user-local auto-memory and `--transcripts` proposes captures from session transcripts, both proposal-then-confirm; `--source` overrides the scanned directory. `--promote` and `--transcripts` exclude each other and `--type`/`--text`. |
| `scribe recall` | `--semantic`, `--scope`, `--kind`, `--mode` | `QUERY` | Answers from the compiled graph with `[source: …]`, or prints `no grounded answer found`. The default bag omits `kind=code`; `--kind` (repeatable) and `--mode` (`planning`, `memory`, `code`) exclude each other; `--scope <slug>` admits one project's planning tree and its Herald fact ledger; `--semantic` selects ranking, not the bag. |
| `scribe graph compile` | `--nightly` | — | Rebuilds the compiled knowledge graph and never prompts; an overlapping run against the same store skips. |
| `scribe index build` | `--target` | — | Ingests the named target list (or `--target`) with graphifyy through the persist port `graph compile` uses; needs the `graphify` extra. |
| `scribe index report` | `--target` | — | Writes the GRAPH_REPORT-style summary to `.claude/data/pyforge-scribe/graph-report.md`. |
| `scribe index move-list` | — | — | **Retired with CAP-34** (2026-11-10): writes `.claude/data/pyforge-scribe/move-list.json`. The verb stays until a Story removes it. |
| `scribe index refresh` | `--target`, `--declare` | — | CAP-33: with `SCRIBE_COCOINDEX_EXTRA` on, skips a derived artifact whose sources are unchanged; off, runs `index build` then `index move-list`. `--declare <manifest>` tracks a caller's own registrations and never consults the switch. |
| `scribe catalog bmad-estate` | `--write`, `--check`, `--root`, `--output`, `--pipeline-truth` | — | CAP-32: prints, `--write`s or `--check`s `docs/reference/bmad-estate-llms-full.md`; behind the flag key below. `--write` and `--check` exclude each other. |

## MCP tools

Scribe's station face is `POST /stations/scribe/mcp` on the platform host. The host code is django-scribe's
(`src/shared/packages/django-scribe/src/django_scribe_portal/mcp_asgi.py`, built by django-pyforge's
`build_station_mcp_asgi`), under `spec-pyforge-unifying-strategy:CAP-20`; this package ships no MCP server. How to
start the host and send a request: `docs/how-to/reach-a-station-mcp-endpoint.md`.

| Tool | Kind | Takes | What it does |
|---|---|---|---|
| `start_recall` | MCP tool | `target` (the query), `assertion` | Starts a supervised recall run and returns `{"handle": …}` at once. |
| `get_recall` | MCP tool | `handle`, `assertion` | Returns the supervisor's record of that run. |
| `run_recall` | supervisor runner, not an MCP tool | the `start_recall` payload | django-pyforge's closed verb-table row: runs `scribe recall -- <query>` in `pyforge-guild`, passing `SCRIBE_GRAPH_DSN` through; a query is 1 to 2000 characters with no control character. |

## Feature-flag keys

| Key | Default | What it gates |
|---|---|---|
| `pyforge.scribe.bmad_estate_catalog` | on (kill switch) | `scribe catalog bmad-estate`. Off keeps the verb listed in `--help`, marked disabled, and refuses with exit 2. Read only through `pyforge.core.flags`; registered in `src/platform/config/flags.json`. |

## Environment variables

Truthy, for the two extra switches, is `1`, `true`, `yes` or `on`, case-insensitive. `scripts/scribe_pg.py` also sets
`PGPASSWORD` for its own `psql` child; it reads no such variable.

| Variable | Read by | Effect |
|---|---|---|
| `SCRIBE_GRAPHIFY_EXTRA` | package (`extras/graphify.py`); `scripts/scribe_nightly_trigger.py` sets it to `1` when unset | Truthy: `scribe graph compile` also ingests the graphify target list. Off by default (air-gap). `scribe index build` does not consult it. |
| `SCRIBE_COCOINDEX_EXTRA` | package (`extras/cocoindex_flow.py`) | Truthy: `scribe index refresh` skips an artifact whose sources are unchanged. Off by default. |
| `SCRIBE_GRAPH_DSN` | package (`graph_store_plugins.py`, `graph_store_pg.py`); passed through by `run_recall` | DSN of the PostgreSQL GraphStore; wins over `DATABASE_URL`. |
| `DATABASE_URL` | package (`graph_store_plugins.py`, `graph_store_pg.py`) | The DSN when `SCRIBE_GRAPH_DSN` is unset. |
| `PYFORGE_GRAPHSTORE_OWNER` | package (`graph_store_plugins.py`); `scripts/scribe_nightly_trigger.py`, `scripts/scribe_install_nightly_trigger.py` | The owner of hook `pyforge.scribe.graph_store`: `scribe` (default, flat file), `steward` (PostgreSQL with pgvector) or `atlas` (the query plane). The nightly trigger brings the local cluster up first when it is `steward`. |
| `QUERY_PLANE_DUCKDB` | package (`graph_store_plugins.py`) | The DuckDB file the `atlas` owner's plane store opens. |
| `PYFORGE_SCRIBE_TRIGGER_BACKEND` | `scripts/scribe_install_nightly_trigger.py` | The backend when `--backend` is absent: `crontab` (default), `systemd`, `apscheduler` or `supercronic`. |
| `SCRIBE_PG_SOCKET_DIR` | `scripts/scribe_pg.py` | The cluster's Unix-socket directory, made absolute; wins over `XDG_RUNTIME_DIR`. |
| `XDG_RUNTIME_DIR` | `scripts/scribe_pg.py` | When it is a directory the user owns, the socket goes in `$XDG_RUNTIME_DIR/scribe-pg`; else `/tmp/scribe-pg-<uid>`. |
| `PIXI_BIN` | `scripts/scribe_nightly_trigger.py` | The `pixi` binary the trigger runs `scribe-pg-up` with; else a `PATH` lookup. |
| `USER` | `scripts/scribe_install_nightly_trigger.py` | The account the `systemd` backend's linger check names. |
| `PYFORGE_FLAGS_PATH` | inherited through `pyforge.core.cutover_root` and `pyforge.core.flags` | The flag tree the kill-switch read uses. |
| `PYFORGE_ENVIRONMENT` | inherited through `pyforge.core.flags` | The environment overlay the flag tree is read under (`dev` when unset). |

## Exit codes

Click's own usage error is 2. A script's `argparse` usage error is also 2; the two nightly-trigger scripts have no
`argparse` parser (`scripts/scribe_install_nightly_trigger.py` reads its one flag, `--backend`, by hand).

| Program | Code | Meaning |
|---|---|---|
| `scribe` | `0` | Success; `--version`; a promotion or transcript scan with nothing to write, or declined; `graph compile` skipped because a run is in progress; `catalog bmad-estate --check` current. |
| `scribe` | `1` | `catalog bmad-estate --check` found drift; each drifted section is named. |
| `scribe` | `2` | Usage (Click's, mutually exclusive flags, a missing `--type`/`--text`, an unknown `--mode`) or could-not-run (a missing extra, an unreadable source, transcript or manifest, the kill switch off). |
| `scripts/scribe_pg.py` | `0` | `up` ready (idempotent, an existing server reused); `down` stopped or nothing to stop; `status`, always. |
| `scripts/scribe_pg.py` | `1` | A binary is missing, the server would not start or become ready, the socket path is unusable, or database or extension setup failed. |
| `scripts/scribe_pg.py` | `2` | Usage: the verb is not `up`, `down` or `status`. |
| `scripts/scribe_nightly_trigger.py` | `0` | The compile succeeded, or the PostgreSQL preflight refused cleanly (never red for that). Otherwise the compile's own code, unchanged. |
| `scripts/scribe_nightly_trigger.py` | `1` | The compile command could not be started. |
| `scripts/scribe_install_nightly_trigger.py` | `0` | The trigger is installed. |
| `scripts/scribe_install_nightly_trigger.py` | `1` | Refused or failed: an unknown backend, a missing prerequisite, or a write or service-manager step that failed. |
| `scripts/scribe_graph_freshness_check.py` | `0` | `graph.json` is present and fresh. |
| `scripts/scribe_graph_freshness_check.py` | `1` | `graph.json` is missing or older than the schedule's period (advisory, never a PR gate). |
| `scripts/bmad_estate_check.py` | `0` | The catalog matches its sources. |
| `scripts/bmad_estate_check.py` | `1` | At least one section drifted. |
| `scripts/bmad_estate_check.py` | `2` | Could not run: `pyforge.scribe` is not importable, or a source cannot be read. |
| `scripts/claude_instruction_mode_check.py` | `0` | `claude` is absent, or new enough with the pinned mode. |
| `scripts/claude_instruction_mode_check.py` | `1` | Advisory: `claude` is older than 2.1.277, or the mode is not the pinned one. |
| `scripts/claude_instruction_mode_check.py` | `2` | `claude --version` failed or its output could not be parsed. |
