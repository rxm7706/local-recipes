# The gate contract — what holds the promise mechanically

Companion to `SPEC.md`. The kernel's Constraints declare that gates are fixture-based and
never credentialed, that the verify set grows and never shrinks, and that a gate is never
weakened, removed, or demoted from attended to unattended to raise the autonomy share. This
file holds the table that constraint compresses: every gate, its command, what it actually
asserts, and its network and credential posture.

"Gates are never weakened" is unenforceable against an unenumerated set. This file is the
enumeration, so a weakening is a visible diff rather than an absence nobody notices.

Every gate below is **offline, non-credentialed, `--frozen`, and lives in the tracked test
tree** — never in the gitignored runtime data directory. Each wave's first deliverable is its
own gate.

---

## The seven gates

| Gate (pixi task) | Wave | Command | What it proves |
|---|---|---|---|
| `kedro-test` | A | `pytest …/tests -q` | `pyforge.atlas` import smokes, the Kedro namespace seam, and the scaffold layout hold |
| `kedro-catalog-check` | A | `pytest …/tests/catalog -q` | The catalog resolves offline with stub credentials; **no inline IO** survives in node bodies; the import-direction ban holds; naming, layer, TTL, and path conventions hold; the **20 override points** and **per-host credential scoping** are asserted |
| `parity-diff` | B | `pytest …/tests/parity -q` | Each migrated node's output frame matches its captured legacy snapshot (fixture mode) |
| `dagster-dryrun` | C | `pytest …/tests/orchestration -q` | Definitions build; schedules enumerate; jobs resolve; **each op carries its own timeout**; Phase P is admin-only; profile precedence holds |
| `bsl-metric-check` | D | `pytest …/tests/semantic -q` | Each core metric, declared once as Ibis→DuckDB, answers as the legacy CLI did |
| `duckdb-singularity` | F | `pytest …/tests/singularity -q` | **No `sqlite3` read or write path** survives anywhere in the migrated surface |
| `wasm-smoke` | G | Playwright headless Chromium | The built artifact loads and queries **client-side with no backend**, with **zero non-loopback requests** |

The test tree carries **78 test modules across 20 directories**, mapped to the pipelines and
features they guard.

> **Kernel wording note.** `SPEC.md` § Success signal says "six deterministic gates … beside
> them a grep gate proving no SQLite path survives." In the shipped `pixi.toml` all **seven**
> are first-class registered tasks, `duckdb-singularity` included. The kernel's prose is a
> narrative grouping, not a different set; this table is the precise one.

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
  the credentialed parity comparator — and it is pinned to `tests/`, never `src/`. The
  cold-start and warm-incremental benchmark is the **attended** half.
- **`bsl-metric-check` is anchored by an independent re-implementation.** The metric parity
  check does not compare the implementation to itself; the oracle was re-derived separately, on
  purpose, because a self-comparing parity test proves nothing.
- **`wasm-smoke` fails on an in-page error.** It does not merely check that the page loaded. It
  blocks and asserts zero non-loopback requests — the offline/no-CDN proof — waits for the
  in-browser DuckDB-WASM query to reach ready, and treats an in-page error as a failure rather
  than passing silently.

## Build steps are not gates

`wasm-build` is a **build step**, not a verify gate, and it is the one place build-time network
access is allowed: it npm-installs the WASM bundle and esbuild, bundles the browser ESM, copies
the MVP wasm module and worker, and **vendors the matching parquet extension locally** so the
runtime never reaches `extensions.duckdb.org`.

The distinction is the contract: **build time may touch the network; the artifact it produces
runs fully offline.** `wasm-smoke` is what proves the second half.

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
