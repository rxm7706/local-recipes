---
title: 'Story G1 (8.1): Compile the intelligence layer to Pyodide / DuckDB-WASM'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #96 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Contract-spec — no original ever existed (corrected 2026-07-25).** This story
> (wave B9–H4) was built by the atlas migration's **in-session agent loop**, which —
> unlike `bmad-create-story` (used only for waves 0/A/B1–B8) — never emitted a per-story
> spec file. The atlas migration session (`01FYyQvBJuXwySiaMUUYCqBZ`) confirmed this
> exhaustively: no such file exists in `implementation-artifacts/`, `.bmad-loop/runs/`
> (which never existed for atlas), any git worktree, git history, or anywhere on disk.
> **Nothing was lost — there is no original to recover.** This file carries the
> load-bearing contract (Intent + Acceptance Criteria **verbatim** from the tracked
> `planning-artifacts/epics.md`) plus a dev narrative reconstructed from the merged record
> (the "Dev narrative" section below). A fuller BMAD-story-format reconstruction (Dev
> Agent Record + File List + Review Triage Log, built from the agent-loop transcripts) is
> at `../../spec-archive/retro-story-files/8-1-g1.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story G1 (8.1): Compile the intelligence layer to Pyodide / DuckDB-WASM

As a dashboard consumer,
I want the Vizro-AI dashboard + BSL layer running in-browser via Pyodide / DuckDB-WASM,
So that the intelligence surface needs no backend at all.

**Acceptance Criteria:** (spec § 9 Story G1, binding)

**Given** the D-wave dashboard + BSL layer
**When** the WASM build runs
**Then** the dashboard loads and queries run client-side in the browser with no backend
**And** a `wasm-smoke` verify task exists (Playwright headless load-and-query against the built artifact — Chromium pre-provisioned).

- **FRs:** FR-14.
- **Invariants:** AD-21, AD-11 (gate is the wave's first deliverable).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** **builds `wasm-smoke`**.
- **Depends on:** Epic 5 (dashboard + BSL), F1 (canonical store).

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] the dashboard loads and queries run client-side in the browser with no backend
- [x] a `wasm-smoke` verify task exists (Playwright headless load-and-query against the built artifact — Chromium pre-provisioned).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-14.
- **Invariants:** AD-21, AD-11 (gate is the wave's first deliverable).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** **builds `wasm-smoke`**.
- **Depends on:** Epic 5 (dashboard + BSL), F1 (canonical store).

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #96). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**Build-time network is allowed; runtime network is not.** `wasm-build` npm-installs
`@duckdb/duckdb-wasm` + esbuild, bundles the browser ESM (inlining apache-arrow), copies the
MVP wasm module and worker, and — the load-bearing step — **vendors the matching parquet
extension locally so the runtime never reaches `extensions.duckdb.org`**. The artifact it
produces runs fully offline. `wasm-smoke` is what proves the second half; the two tasks are
deliberately separate because they have opposite network postures.

**The gate blocks the network and asserts nothing was attempted.** It serves `wasm/build/`
over a **loopback** static host (a file server, not a backend), drives headless Chromium via
Playwright, and **blocks every non-loopback request while recording attempts** — so if the
artifact secretly needed a CDN, the assertion fails rather than the page quietly succeeding
on a machine that happens to have internet.

**An in-page error fails the test.** The gate waits for the in-browser DuckDB-WASM query to
reach `ready`; a blank page, a failed wasm instantiation, or an empty result flips it to
failure. This is the difference between "the page loaded" and "the engine ran," and only the
second one is worth asserting.

**It asserts a real answer, not just liveness.** The seed
(`wasm/data/feedstock_health.csv`) has `ci_red = ci_status IN ('failure','error')` — alpha,
gamma, epsilon → **3 red** out of five rows. The gate asserts that client-side result, so it
is checking D1 feedstock-health *semantics* computed in the browser, not merely that a query
returned something.

**Skip-to-green was closed deliberately.** Under `CI` or an explicit `WASM_SMOKE_REQUIRED=1`,
a missing browser or an unbuilt artifact **fails** rather than skips — a review finding
(Reviewer-A), and the right one: a gate that skips in CI exits 0 having verified nothing.
Locally it stays a skip with a "run `wasm-build` first" message, for convenience.

**Deferred:** the full Vizro-in-Pyodide render is DW-G1. G1 proves the engine and the query
run client-side; it does not render the dashboard in the browser.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-G1]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-G1]
- [Architecture: _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md]

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Delivery Record

<!-- DERIVED from the merged PR via `gh` on 2026-07-27. Exact, not reconstructed. -->

| | |
|---|---|
| Pull request | **#96** — story(G1): DuckDB-WASM in-browser read surface + wasm-smoke gate (FR-14) |
| Merged | 2026-07-18 |
| Diff | 10 files, +550 / -0 |
| Test files touched | 2 |

**Commits**

- `203be0c` story(G1): DuckDB-WASM in-browser read surface + wasm-smoke gate (FR-14)

**File list** *(exact, from the merged diff)*

```
  195 +     0 -  src/shared/packages/pyforge-atlas/tests/wasm/test_wasm_smoke.py
  142 +     0 -  src/shared/packages/pyforge-atlas/wasm/build.py
  109 +     0 -  src/shared/packages/pyforge-atlas/wasm/index.html
   64 +     0 -  src/shared/packages/pyforge-atlas/wasm/README.md
   11 +     0 -  src/shared/packages/pyforge-atlas/wasm/package.json
    9 +     0 -  pixi.toml
    9 +     0 -  src/shared/packages/pyforge-atlas/wasm/entry.mjs
    6 +     0 -  src/shared/packages/pyforge-atlas/wasm/data/feedstock_health.csv
    5 +     0 -  src/shared/packages/pyforge-atlas/wasm/.gitignore
    0 +     0 -  src/shared/packages/pyforge-atlas/tests/wasm/__init__.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `203be0c`** — story(G1): DuckDB-WASM in-browser read surface + wasm-smoke gate (FR-14)
  - Opens Wave G. The D-wave read surface's client-side QUERY runs IN-BROWSER with
  - ZERO backend via genuine DuckDB-WASM (AD-21). The wasm/ artifact is a static
  - page that fetches a Parquet file as bytes, registers it, and runs
  - read_parquet(...) inside the WASM engine — no server-side query, no API.
  - wasm-smoke gate (tests/wasm, AD-11 wave-first deliverable): launches the
  - PRE-PROVISIONED headless Chromium, loads the built artifact from a loopback
  - static file host, and PROVES the no-backend/offline claim by blocking + asserting
  - ZERO non-loopback requests (the offline proof genuinely covers Web-Worker
  - traffic — both the .wasm module and the vendored parquet extension fetch are
  - intercepted). It asserts the exact client-side query result (the ci_red count +
  - per-feedstock booleans), and is NON-HOLLOW: removing/malforming/emptying the
  - Parquet flips #status to error and FAILs the gate. The parquet extension is
  - vendored locally so the runtime never reaches extensions.duckdb.org.
  - wasm-build + wasm-smoke pixi tasks; build/ + node_modules/ (a ~41 MB .wasm)
  - are gitignored + reproducible from build.py.
  - Reviewer fixes (both in-loop reviewers): skip-to-green closed — under
  - WASM_SMOKE_REQUIRED/CI a missing browser or unbuilt artifact FAILs instead of
  - skipping (a misconfigured CI cannot pass having verified nothing); the loopback
  - allowlist parses the URL HOST (127.0.0.1/localhost/::1) instead of a substring
  - match (http://127.0.0.1.evil.example no longer slips the offline guard).
  - DEFERRED: the full Vizro/Pyodide dashboard RENDER in-browser (DW-G1-1 — the page
  - renders a plain HTML table, not the Vizro UI) and the CI wasm-build step for the
  - gitignored heavy assets (DW-G1-2). 683 passed (+1 headless-browser gate).

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#96`.

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #96: story(G1): DuckDB-WASM in-browser read surface + wasm-smoke gate (FR-14)

## Deferred Work (DW ledger)

### DW-G1-1 — full Vizro-AI dashboard RENDERED inside Pyodide (the heavy read-surface half)
- source_spec: `g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md`
  summary: G1 ships the LOAD-BEARING half of the acceptance criterion — the intelligence read
    surface's query runs CLIENT-SIDE in the browser with NO backend, on a GENUINE DuckDB-WASM
    engine reading a statically-hosted Parquet file (proven by the `wasm-smoke` Playwright gate).
    What is DEFERRED is compiling the full D2 Vizro-AI DASHBOARD (its Dash/Plotly page tree, the
    28-page inventory, the D3 NL query field) to run inside PYODIDE in the same page. That is the
    heaviest piece (Pyodide runtime + the vizro/dash/plotly wheel stack loaded in-browser) and is
    an attended bring-up: the in-container artifact exposes the BSL/DuckDB QUERY surface (the
    D1 `feedstock-health` semantics, `ci_red = ci_status IN ('failure','error')`), not the
    rendered Vizro component tree. Wire the Pyodide-hosted Vizro render when the browser wheel
    stack + a static-host budget (DW-G1-2) land; the query surface it will sit on is already proven.
  evidence: `wasm/index.html` runs a DuckDB-WASM `read_parquet` query and renders a plain HTML
    table (the query result), not a Vizro `Dashboard`; `tests/wasm/test_wasm_smoke.py` asserts the
    client-side query result, not a Vizro component tree. The D2 dashboard OBJECT itself is built +
    asserted OFFLINE by the separate `dashboard-dryrun` gate (server-side, Python) — G1 is the
    browser/no-backend half.

### DW-G1-2 — heavy WASM build assets are gitignored; CI must run `wasm-build` before `wasm-smoke`
- source_spec: `g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md`
  summary: The runtime artifact (`wasm/build/`) carries a ~40 MB DuckDB `.wasm` module, the
    esbuild bundle, the vendored parquet extension (~3 MB), and the demo Parquet — far too heavy to
    commit, so `wasm/build/` + `node_modules/` are gitignored. The `wasm-smoke` gate SKIPS with a
    "run `wasm-build` first" message when `wasm/build/` is absent (a legitimate not-built skip,
    DISTINCT from the browser-ran-but-failed case, which always FAILS). Consequence: a fresh
    clone / CI must run `pixi run -e local-recipes wasm-build` (BUILD-TIME network: npm + the
    DuckDB extension host) before `wasm-smoke`. Wiring `wasm-build` as an automatic CI pre-step
    (or hosting the pre-built artifact as a CI cache / G2 static-host output) is deferred to G2
    (Parquet-to-static-host), which owns the published-artifact surface. Until then the two-step
    build→verify is the documented local/CI flow.
  evidence: `wasm/.gitignore` ignores `build/` + `node_modules/`; `wasm/build.py` is the build
    step; `tests/wasm/test_wasm_smoke.py` `static_server` fixture `pytest.skip`s when
    `build/index.html` is absent. `wasm-build` uses the network (npm + `extensions.duckdb.org`
    via curl); `wasm-smoke` is offline (loopback static host + asserted zero external requests).
