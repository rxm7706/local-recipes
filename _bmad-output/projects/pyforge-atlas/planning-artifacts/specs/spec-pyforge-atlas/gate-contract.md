# The gate contract — what holds the promise mechanically

Companion to `SPEC.md`. The kernel's Constraints declare that gates are fixture-based and
never credentialed, that the verify set grows and never shrinks, and that a gate is never
weakened, removed, or demoted from attended to unattended to raise the autonomy share. This
file holds the table that constraint compresses: every gate task, the pixi feature that holds it,
the test path it runs, what it actually asserts, and its network and credential posture.

"Gates are never weakened" is unenforceable against an unenumerated set. This file is the
enumeration, so a weakening is a visible diff rather than an absence nobody notices.

Every gate below is **offline, non-credentialed, `--frozen`, and lives in the tracked test
tree** — never in the gitignored runtime data directory. Offline means no non-loopback request:
the browser and HTTP Range gates serve over loopback only. Each wave's first deliverable is its
own gate.

---

## The gate tasks

Test paths are relative to the package, `src/shared/packages/pyforge-atlas/`. Run a gate as
`pixi run --frozen -e <feature> <task>`: each feature named here is also an environment of the
same name. The `local-recipes` rows, and the three tasks below the table, stay in
`feature.local-recipes`: moving them to `feature.pyforge-atlas` is an estate change steward
declined for 2026-11-10 (steward Story 124.1), and it stays open as `DW-atlas-46-1-4`.

| Gate (pixi task) | pixi feature (env) | Test path | Origin | What it proves |
|---|---|---|---|---|
| `pyforge-atlas-test` | `pyforge-atlas` | `tests/unit` and `tests/meta` (not `slow`, not `live_tree`), then the rest of `tests` (not `live_tree`) | Story 32.2; split by steward Story 124.1 | The package half: every module that judges the package alone — import smokes, the Kedro namespace seam, the scaffold layout, the nodes, datasets and pipelines on fixtures. Its first segment writes the coverage report `pyforge-atlas-coverage-gate` judges |
| `pyforge-atlas-live-test` | `pyforge-atlas` | `tests/unit` and `tests/meta` (`live_tree`, not `slow`), then the rest of `tests` (`live_tree`), then the repository's inventory quartet tests (Story 27.1: `scripts/tests` and the root packaging handoff test) | steward Story 124.1 | The live-tree half: every module that reads outside the package (`pixi.toml`, the workflows, `scripts/`, the planning tree, other stations), so it fires on what it reads |
| `kedro-catalog-check` | `pyforge-atlas` | `tests/unit/catalog` | Wave A (Story A2) | The catalog resolves offline with stub credentials; **no inline IO** survives in package code; the import-direction ban holds; naming, layer, TTL, and path conventions hold; the per-pipeline dataset counts hold; the **27 endpoint override points** (19 legacy, 2 from Story 21.4, 5 from Story 23.1, 1 reserved) and **per-host credential scoping** are asserted |
| `parity-diff` | `pyforge-atlas` | `tests/unit/parity` | Wave B (Story B1) | Each migrated node's output frame matches its captured legacy snapshot (fixture mode) |
| `dagster-dryrun` | `pyforge-atlas` | `tests/unit/orchestration` | Wave C (Story C1) | Definitions build; schedules enumerate; jobs resolve; **each op carries its own timeout**; Phase P is admin-only; profile precedence holds |
| `bsl-metric-check` | `pyforge-atlas` | `tests/unit/semantic` | Wave D (Story D1) | Each core metric, declared once as Ibis→DuckDB, answers as the legacy CLI did |
| `dashboard-dryrun` | `local-recipes` | `tests/integration/dashboard` | Wave D (Story D2) | The Vizro dashboard object builds offline (no server, no `.run()`) with each expected page at a stable id and title, its pages BSL-driven, the factory-status page carrying a build timestamp; the same suite runs a Playwright end-to-end and ARIA navigation check against a real local server, so it is loopback-only rather than server-free |
| `vizro-ai-dryrun` | `local-recipes` | `tests/unit/nl` | Wave D (Story D3) | The `query_vizro_ai` MCP tool is registered and, with no backend configured, returns the structured not-configured advisory: no network, no crash, no hard-coded public host |
| `duckdb-singularity` | `pyforge-atlas` | `tests/unit/singularity` | Wave F (Story F1) | **No `sqlite3` read or write path** survives anywhere in the migrated surface, and the `duckdb-server` launch site is one |
| `wasm-smoke` | `local-recipes` | `tests/integration/wasm` | Wave G (Story G1) | Headless Chromium loads the built artifact (`wasm-build` first) and queries it **client-side with no backend**, with **zero non-loopback requests** |
| `publish-range` | `local-recipes` | `tests/integration/publish` | Wave G (Story G2) | The emitted static-host layout is consumed through HTTP Range: a 206 reading strictly fewer bytes than the whole file, the chunk path found from the manifest and matching its checksums, host-agnostic, the metric answer correct over the range-served Parquet. httpfs loads offline from cache: it skips when unprovisioned locally and fails under CI |
| `query-plane-parity` | `pyforge-atlas` | `tests/unit/query_plane` | Story 20.2 | An identical fixture query set answers row for row through the library face and the HTTP/Arrow face; a seeded divergence proves the gate bites; the stack-down path is marked `not-applicable`, never a silent pass |
| `kedro-test` | `pyforge-atlas` | none of its own | Wave A; an alias since Story 32.2 | The alias of the whole suite: its `depends-on` runs `pyforge-atlas-test` and `pyforge-atlas-live-test`, so existing callers keep working; the canonical names are those two |

`tests/meta/test_catalog_contract.py` derives the gate set from `pixi.toml` — every task, in any
feature, whose command runs pytest over this package's tests — and holds this table to it: one
row per task, with its feature and every test path its command names. A `pixi.toml` edit that
adds, moves or re-points a gate reds that test until the row follows.

> **Kernel wording note.** `SPEC.md` § Success signal says "six deterministic gates … beside
> them a grep gate proving no SQLite path survives", and gives `kedro-catalog-check` 20 override
> points. That is the wave-era narrative: every row above is a registered `pixi.toml` task,
> `duckdb-singularity` included, and the catalog gate now pins 27. This table is the precise set.

## What each gate refuses to do

The negative half of a gate's contract is as binding as the positive half — several of these
gates exist specifically to *stop short* of something.

- **`parity-diff` runs fixture mode in-loop only.** The full credentialed live-parity run —
  exact row-count and value parity on the `v_actionable_packages` view family — is the
  **attended B4 event** with human sign-off. B1 builds the machinery and seeds the conda-side
  fixtures, B2 adds PyPI and vulnerability fixtures, B3 completes the harness, B4 runs it
  credentialed. The gate never reads the operator's runtime data directory.
- **`dagster-dryrun` loads definitions only.** No live daemon, no scheduled run. Attended
  bring-up is deliberately deferred and recorded.
- **`duckdb-singularity` pins its one exception.** Exactly one legacy-SQLite reader survives —
  the credentialed parity comparator — and it is pinned to `tests/`
  (`tests/unit/parity/parity_runner.py`), never `src/`. The cold-start and warm-incremental
  benchmark is the **attended** half.
- **`bsl-metric-check` is anchored by an independent re-implementation.** The metric parity
  check does not compare the implementation to itself; the oracle was re-derived separately, on
  purpose, because a self-comparing parity test proves nothing.
- **`wasm-smoke` fails on an in-page error.** It does not merely check that the page loaded. It
  blocks and asserts zero non-loopback requests — the offline/no-CDN proof — waits for the
  in-browser DuckDB-WASM query to reach ready, and treats an in-page error as a failure rather
  than passing silently.

## Tasks that run no pytest

Three of the seven atlas tasks in `feature.local-recipes` run no test, so they are not gates; each
runs in the env its feature names.

- `wasm-build` (`local-recipes`) is a **build step**, and the one place build-time network
  access is allowed: it npm-installs the WASM bundle and esbuild, bundles the browser ESM, copies
  the MVP wasm module and worker, and **vendors the matching parquet extension locally** so the
  runtime never reaches `extensions.duckdb.org`.
- `publish` (`local-recipes`) emits the host-agnostic static-host layout — chunked Parquet and a
  single-owner `manifest.json` — for the demo dataset into a gitignored directory. The live
  GitHub Pages publish is the attended boundary event (`DW-G2`).
- `dashboard-serve` (`local-recipes`) serves the Vizro dashboard locally, in the foreground on
  `127.0.0.1:8050`, through the same `build_dashboard()` the dashboard gate builds offline. It is
  how you look at the dashboard, not a proof that it builds.

The distinction is the contract: **build time may touch the network; the artifact it produces
runs fully offline.** `wasm-smoke` proves the second half for the WASM artifact and
`publish-range` for the published layout.

## Attended boundary events are features

Three things are deliberately attended and credentialed rather than automated:

| Event | Why it stays attended |
|---|---|
| The B4 credentialed parity run | Retirement of the legacy orchestrator is earned against evidence a human signed, not asserted |
| The cold-start benchmark | A performance claim needs a witness; the honest headline is incremental re-materialization, never a cold-start miracle |
| Live service bring-ups | Each ships a seam that defaults safe; the contract is that the seam exists, not that a service is running |

These are **features, not friction**. A gate is never demoted from attended to unattended to
raise the autonomy share — that trade converts a real guarantee into a number on a dashboard.

> **None of these three has occurred as of 2026-07-27** (`AUD-ATLAS-047`, `AUD-ATLAS-049`).
> The parity harness is fixture-green but the credentialed run and sign-off have not happened,
> so the legacy orchestrator is **not** retired (`DW-B4-2`); the cold/warm benchmark has never
> run (`DW-F1-1`); no live service has been brought up (`DW-C1-1`, `DW-G3`, `DW-H4`). The table
> above lists what the events *are*, not what has been done — read it as outstanding work.

## The standing anti-metrics

Four things the gate set exists to *not* optimize, restated here because gates are where the
temptation lands:

1. Chasing cold-start wall-clock.
2. Raising the autonomy share by weakening gates.
3. Growing the signal count for its own sake.
4. Growing dashboard breadth.

A change that moves one of these up while moving a gate down is a contract breach regardless of
how the numbers read.
