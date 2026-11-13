# Herald's public contract

Companion to `SPEC.md`, added 2026-11-11 (Story 50.3; CAP-62, FR-14.1). It lists every surface a caller of herald can
touch: the CLI verbs and their arguments, the MCP tools of its host face, the feature-flag keys and repository keys it
reads, the environment variables the package and the docs-site build read, and the `HeraldError` classes with their
exit codes. A second root that rebuilds herald from its Spec reproduces this surface from this file.

This file is written by hand from the code; nothing generates it. The meta-test
`src/shared/packages/pyforge-herald/tests/meta/test_public_contract.py` derives each surface from the code and fails
in both directions: on a surface the code has and this file does not list, and on a row this file lists and the code
no longer has. A change to any surface edits the code and this file in the same change.

Reading the tables: the first column of each row names one item, in backticks, and the test reads that column. In
the CLI verb table, `<name>` is a required positional argument, `[name]` an optional one, `<name>...` one or more, and
an option is written with every spelling it accepts (`--json/-j`); `-h/--help` is on every parser and is not listed.
`—` means none.

## CLI verbs

The console script is `herald` (`pyforge.herald.cli:main`); `pyforge herald …` is the same grammar after `pyforge`.
The parser is `pyforge.herald.cli._build_parser()`. The CAP column names the capability of `SPEC.md` each verb
realizes; every capability that `cli.py` cites for a verb (its help, its handler's docstring and body) is one its row
names.

| Verb path | Arguments | CAP |
|---|---|---|
| `herald` | `--version` | — |
| `herald deck` | — | — |
| `herald deck seed` | `<slug>` `--repo-root` `--support-source-project` | CAP-1, CAP-4 |
| `herald deck pull` | `<slug>` `--repo-root` `--commit` `--target` | CAP-1, CAP-4 |
| `herald deck status` | `[slug]` `--repo-root` `--account` | CAP-4, CAP-29 |
| `herald deck watch` | `<slug>...` `--repo-root` `--interval` | CAP-4 |
| `herald deck push` | `<slug>` `--repo-root` `--prove` | CAP-4, CAP-34 |
| `herald deck publish` | `<slug>` `--repo-root` `--dry-run` | CAP-54, CAP-55 |
| `herald deck exports` | `<slug>` `--repo-root` `--json/-j` | CAP-54 |
| `herald deck sync-all` | `--slug` `--repo-root` `--dry-run` `--proof-dir` | CAP-31, CAP-36, CAP-50 |
| `herald deck qa` | `<slug>` `--repo-root` | CAP-26..CAP-28 |
| `herald deck pptx-spec` | `--template` `-o/--out` | CAP-41 |
| `herald deck pptx-fill` | `<content_plan>` `--template` `-o/--out` | CAP-40, CAP-41 |
| `herald deck pptx-native` | `<slug>` `--repo-root` | CAP-57 |
| `herald progress` | `[station]` `--json/-j` `--date-range` `--station/-s` `--update` `--list` `--shipped` `--compute-hours` `--token-spend` `--wall-clock-hours` `--unblock-narrative` | CAP-11 |
| `herald success` | `--json/-j` `--date-range` `--station/-s` `--repo-root` | CAP-12 |
| `herald success create` | `<project_name>` `--shipped-date` `--evidence-test-results` `--evidence-metrics` `--evidence-adoption` `--evidence-notice` | CAP-12 |
| `herald success review` | `<claim_id>` | CAP-12 |
| `herald success publish` | `<claim_id>` `--thesis` | CAP-12 |
| `herald success list` | `--status` | CAP-12 |
| `herald success get` | `<claim_id>` | CAP-12 |
| `herald success validate` | `[claim_id]` `--all` | CAP-12 |
| `herald notice` | `--json/-j` `--date-range` `--station/-s` | CAP-13 |
| `herald notice list` | `--json/-j` `--date-range` `--station/-s` `--category` `--status` | CAP-13 |
| `herald notice author` | `--type` `--component` `--what` `--why` `--migration` `--deadline` `--reason-link` `--publish` | CAP-13 |
| `herald notice publish` | `<component>` | CAP-13 |
| `herald notice get` | `<component>` | CAP-13 |
| `herald notice close` | `<component>` `--reason` | CAP-13 |
| `herald notice archive` | `--rename` | CAP-13 |
| `herald scheduler` | — | — |
| `herald scheduler run` | `--repo-root` `--out-dir` `--json/-j` | CAP-39 |

`herald deck` and `herald scheduler` take a verb and run nothing alone. `herald success` and `herald notice` with no
verb list, as `herald success list` and `herald notice list` do. `deck publish`, `deck exports` and `deck pptx-native`
stay listed in `--help` when their flag is off, marked disabled, and refuse with exit `2`.

## MCP tools

The host face is `POST /stations/herald/mcp`, served by `django_herald_portal.mcp_asgi.build_herald_mcp_asgi` in
`src/shared/packages/django-herald/`. Both tools take an `assertion`. Behind them, the supervisor runs herald's row of
the closed verb table under the runner key `run_notice`, which is not an MCP tool.

| Tool | What it does | CAP |
|---|---|---|
| `start_notice` | takes a `target` and returns a handle at once; the supervised run is `herald notice get <target>` | spec-pyforge-unifying-strategy:CAP-20 |
| `get_notice` | takes a `handle` and returns that supervised run | spec-pyforge-unifying-strategy:CAP-20 |

## Feature-flag keys

Every flag key herald reads, whatever its prefix: the `*_FLAG` constants in herald's source, and the key that opens
the doc comment of each flag reader `docs-site/src/lib/flags.ts` exports. The build hands the docs-site its flag
states as environment variables (see the next tables), which `python -m pyforge.herald.pages_env` and
`python -m pyforge.steward.marketplace_pages --flag-env` export. `envFlagOn` in `flags.ts` is the generic reader and
names no key.

| Key | Read by |
|---|---|
| `pyforge.herald.status_pages` | `status_pages.py` `STATUS_PAGES_FLAG`; `flags.ts` `statusPages()` |
| `pyforge.herald.ci_surfaces_tile` | `ci_surfaces_tile.py` `CI_SURFACES_TILE_FLAG`; `flags.ts` `ciSurfacesTile()` |
| `pyforge.herald.deck_publish` | `deck_publish.py` `DECK_PUBLISH_FLAG` (gates `deck publish` and `deck exports`) |
| `pyforge.herald.deck_export_native` | `pptx_native.py` `DECK_EXPORT_NATIVE_FLAG` (gates `deck pptx-native`) |
| `pyforge.herald.deck_viewer` | `twins.py` `DECK_VIEWER_FLAG` (`deck publish` uploads the HTML twins when it is on) |
| `pyforge.steward.marketplace_pages` | `flags.ts` `marketplacePages()`, as `PYFORGE_MARKETPLACE_PAGES` |

## Repository keys

A key herald reads from a repository file through a core seam, one row each. A herald module that imports
`pyforge.core.cutover_root` reads `roots.this` of `docs/governance/guild-roster.json` through it, and gains its row
here in the same change as the import. `local_ship.py` does (Story 52.2): the on-pr-close body names this checkout's
forge, read at call time from the nearest roster at or above the working directory (`main` reads its `--repo-root`);
an explicit `repo=` wins and reads no roster, and a missing roster or `roots.this` is the named `ForgeSlugError`
(`herald-ship-local` exits 1 before any POST). Herald reads no flag key for it and never calls `root_of_record()`.

| Key | File | Read through |
|---|---|---|
| `roots.this` | `docs/governance/guild-roster.json` | `pyforge.core.cutover_root.forge_slug_for`, in `local_ship.py` `this_forge_slug()` |

## Environment variables

Every environment variable herald reads. In the package (`src/shared/packages/pyforge-herald/src/pyforge/herald/`): a
literal read through `os.environ.get(…)`, `os.environ[…]` or `os.getenv(…)`, a literal read on a local bound to
`os.environ` or a copy of it, and every string constant whose name ends in `_ENV` or `_ENV_VAR`. In the docs-site
build (`docs-site/src`, `docs-site/scripts`, `docs-site/astro.config.mjs`): `process.env.X`, `process.env[CONST]`
resolved through the constant's `export const`, `env.X` on an injected env record whose default is `process.env`, and
the argument of `envFlagOn('X', …)`. Astro's build constants under `import.meta.env` are not environment reads.

| Variable | Reader | Read as |
|---|---|---|
| `HERALD_LIVE_SYNC_PROOF` | package `cli.py` | literal `os.environ.get`; `deck sync-all --proof-dir` runs only when it is `1` |
| `HERALD_TOKEN` | package `auth.py` | `TOKEN_ENV_VAR` |
| `HERALD_DESIGN_CREDENTIALS` | package `transport/mcp_transport.py` | `CREDENTIALS_PATH_ENV` |
| `HERALD_WEBHOOK_SECRET` | package `webhook.py`, `local_ship.py` | `SECRET_ENV_VAR`; literal `os.environ.get` |
| `HERALD_WEBHOOK_URL` | package `local_ship.py` | literal `os.environ.get` |
| `HERALD_REPO_ROOT` | package `webhook_host.py` | `REPO_ROOT_ENV_VAR` |
| `OBJECT_STORAGE_ENDPOINT_URL` | package `deck_store.py` | `ENDPOINT_URL_ENV` |
| `OBJECT_STORAGE_ACCESS_KEY` | package `deck_store.py` | `ACCESS_KEY_ENV` |
| `OBJECT_STORAGE_SECRET_KEY` | package `deck_store.py` | `SECRET_KEY_ENV` |
| `OBJECT_STORAGE_BUCKET` | package `deck_store.py` | `BUCKET_ENV` |
| `OBJECT_STORAGE_PREFIX` | package `deck_store.py` | `PREFIX_ENV` |
| `CONDA_PREFIX` | package `pptx_native.py` | literal `os.environ.get` |
| `NODE_PATH` | package `pptx_native.py` | literal read on a copy of `os.environ` |
| `PYFORGE_STATUS_PAGES` | docs-site `src/lib/flags.ts`, `scripts/pages.mts` | `envFlagOn` argument |
| `PYFORGE_CI_SURFACES_TILE` | docs-site `src/lib/flags.ts` | `envFlagOn` argument |
| `PYFORGE_MARKETPLACE_PAGES` | docs-site `src/lib/flags.ts`, `scripts/pages.mts` | `envFlagOn` argument |
| `PAGES_BUILD_INPUTS_DIR` | docs-site `src/lib/agent-surface.ts` | `process.env[INPUTS_DIR_ENV]` |
| `SITE_URL` | docs-site `src/lib/site-url.mjs` | `process.env.X` |
| `GITHUB_REPOSITORY` | docs-site `src/lib/site-url.mjs`, `src/lib/shelf.mjs`, `scripts/pages.mts`, `src/lib/marketplace.ts` | `process.env.X`; injected `env.X` |
| `GITHUB_SERVER_URL` | docs-site `src/lib/shelf.mjs`, `src/lib/marketplace.ts` | `process.env.X`; injected `env.X` |
| `GITHUB_SHA` | docs-site `src/lib/built-from.ts`, `src/lib/marketplace.ts` | injected `env.X` |
| `GITHUB_RUN_ID` | docs-site `src/lib/built-from.ts` | injected `env.X` |
| `PAGES_BUILT_AT` | docs-site `src/lib/built-from.ts`, `scripts/pages.mts` | injected `env.X` |
| `PAGES_HOST_BASE_URL` | docs-site `scripts/pages.mts` | injected `env.X` |
| `PAGES_HOST_BASE_PATH` | docs-site `scripts/pages.mts` | injected `env.X` |
| `HERALD_PAGES_REPO_ROOT` | docs-site `src/loaders/herald-pages-loader.ts`, `src/loaders/dossier-loader.ts`, `scripts/pages.mts` | `process.env.X`; injected `env.X` |
| `HERALD_PYTHON` | docs-site `src/loaders/dossier-loader.ts`, `scripts/pages.mts` | `process.env.X`; injected `env.X` |

## Error classes

Every class in `pyforge.herald.errors` that descends from `HeraldError`, with the exit code
`pyforge.herald.errors.exit_code_for` gives it. `pyforge.herald.cli.dispatch` is the one place that catches them: it
writes one line to stderr (one JSON object with `--json`) and returns the code.

| Class | Parent | Exit code |
|---|---|---|
| `HeraldError` | `PyforgeError` | 1 |
| `TransportError` | `HeraldError` | 4 |
| `AuthError` | `TransportError` | 4 |
| `TransportUnreachableError` | `TransportError` | 4 |
| `TransportCallError` | `TransportError` | 4 |
| `UnconditionalWriteError` | `TransportError` | 4 |
| `SeedConflictError` | `HeraldError` | 3 |
| `PullConflictError` | `HeraldError` | 3 |
| `ExportConflictError` | `HeraldError` | 3 |
| `ReadBackMismatchError` | `HeraldError` | 1 |
| `OperatorAuthorizationError` | `HeraldError` | 1 |
| `InvalidDateRangeError` | `HeraldError` | 1 |
| `EvidenceLinkError` | `HeraldError` | 1 |
| `ClaimNotFoundError` | `HeraldError` | 1 |
| `ClaimStateError` | `HeraldError` | 1 |
| `DeckPublishError` | `HeraldError` | 1 |
| `DeckUsageError` | `HeraldError` | 2 |
| `PptxTemplateError` | `HeraldError` | 1 |
| `InvalidContentPlanError` | `HeraldError` | 1 |
| `PaginationStalledError` | `HeraldError` | 1 |

## Exit codes

The closed set `herald` exits with.

| Code | Meaning |
|---|---|
| `0` | success; `--help` and `--version` |
| `1` | no command given; any `HeraldError` the exit-code map does not name |
| `2` | a usage error (argparse's own exit: unknown verb or flag, missing argument); `DeckUsageError`; a verb whose flag is off; `deck exports` without `--json` |
| `3` | a conflict: `SeedConflictError`, `PullConflictError`, `ExportConflictError` |
| `4` | a transport failure: `TransportError` and every class under it |

A subcommand interrupted by `KeyboardInterrupt` returns `130`, the shell's interrupt convention; it is not a herald
verdict and is outside the closed set.
