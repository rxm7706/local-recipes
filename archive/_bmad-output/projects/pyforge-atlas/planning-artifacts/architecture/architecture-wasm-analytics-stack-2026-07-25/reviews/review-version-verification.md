---
title: 'Review — Version & Reality-Check Verification'
target: ARCHITECTURE-SPINE.md (Wasm Analytics Stack)
lens: 'Verify every committed decision was web-researched or reality-checked rather than asserted from training data'
reviewer_date: '2026-07-25'
---

# Review: Version & Reality-Check Verification

## Scope & Methodology

I independently re-verified the spine's `## Stack` table and the technical claims
in AD-3 and AD-4 against **live sources** — not by re-trusting the spine's own
citations or the technical research report's citations. WebSearch was available
this session (unlike the sessions that produced the spine and the research
report, both of which flagged WebSearch as unavailable and fell back to
WebFetch/`gh api`). I used WebFetch against:

- PyPI JSON API (`pypi.org/pypi/<pkg>/json`) for every Python-package version claim.
- GitHub Releases/Tags REST API (`api.github.com/repos/<org>/<repo>/releases`)
  for every non-PyPI-authoritative or date-bearing claim (Pixi, Vector, Wasmtime
  engine, dbt-core, DuckDB, dlt, componentize-py, Marquez).
- GitHub Search Issues API for the DuckDB-WASI claim underpinning AD-3.
- Direct issue fetches for two of the research report's cited
  `componentize-py` issues, to confirm they are real and not fabricated
  citations.

## Overall Verdict

Every one of the 12 pinned Stack versions and the central "DuckDB has no WASI
build/roadmap" claim in AD-3 independently re-verified as accurate against live
sources as of 2026-07-25 — this is an unusually well-grounded stack table (several
pins track releases from literally 1–9 days before the spine's own authoring
date) — but two committed claims fall short of the lens: the `Python 3.12` host
pin carries no citation/rationale and sits two minor versions behind current
stable despite the pinned host libraries themselves declaring support through
3.14, and AD-4's "adapted from pyforge-atlas story G1's wasm-smoke design"
overstates technical continuity with a gate that is architecturally unrelated
(browser/Playwright/Emscripten vs. Wasmtime-host/WIT-capability).

## Findings

### Finding 1 (Medium) — `Python 3.12` host pin has no citation and is unverified against current/library-declared support

**Location:** Stack table, row `Python (host/pipeline processes: API, dlt, dbt-duckdb)`.

Every other fully-pinned row in the Stack table carries evidence of having been
checked against a live source at authoring time (the table's own header comment
claims PyPI JSON API + GitHub Releases API verification, and my independent
re-check confirms this for all 11 non-Marquez rows — see Verified-Correct
Spot-Checks below). The `Python 3.12` row is the one exception: no patch version,
no comment, no rationale for why the host processes (FastAPI/dlt/dbt-duckdb —
none of which run under WASI) are pinned two minor versions behind current.

Independently verified via `python.org/downloads`: as of 2026-07-25 the latest
overall stable is **Python 3.14.6** (2026-06-10), latest 3.13.x is **3.13.14**
(2026-06-10), latest 3.12.x is **3.12.13** (2026-03-03). Both host-side
dependencies pinned in the same table already declare support through 3.14 per
their own PyPI package metadata (`dlt` and `dbt-core` PyPI pages both state
Python 3.10–3.14 support). So the constraint isn't "the pinned libraries can't
run on anything newer" — nothing in the spine or its sources establishes *why*
3.12 was chosen over 3.13 or 3.14 for the host processes. This is exactly the
asserted-not-researched pattern the lens is checking for: it may well be a
deliberate, defensible conservatism call (e.g. avoiding bleeding-edge Python for
an OCP Restricted-SCC base-image lineage), but that reasoning isn't recorded
anywhere, unlike every other version decision in the same table.

**Recommendation:** Either cite the constraint that actually forces 3.12 (RHEL/UBI
base image Python availability, a dependency that caps at 3.12, etc.) or bump the
pin and note why 3.12 was rejected.

### Finding 2 (Medium) — AD-4's "adapted from pyforge-atlas story G1's wasm-smoke design" overstates technical continuity

**Location:** AD-4 rule text.

AD-4 says: *"The gate (a Wasmtime-host smoke test, adapted from `pyforge-atlas`
story G1's `wasm-smoke` design) must include a meta-test: deliberately widening
the component's declared WIT capabilities without a matching interface change
must make the gate fail."*

I read the actual G1 story spec/dev-narrative
(`_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md`).
G1's real `wasm-smoke` gate is a **Playwright + headless-Chromium** test against
a **browser-hosted DuckDB-WASM artifact** (Emscripten compilation target, per the
research report's own § 5) that proves a no-backend/offline claim by asserting
**zero non-loopback network requests** are made (including Web-Worker traffic).
It involves no Wasmtime host, no WIT interface, and no component-capability
model whatsoever — it is architecturally a different sandbox lane from the one
AD-4 governs (Wasmtime/WASI-Preview-2/`componentize-py`, per the same research
report's own § 3 distinction between the Pyodide/Emscripten lane and the
WASI-component lane).

The only thing that genuinely transfers from G1 to AD-4 is a **design
philosophy** — "prove the isolation property is actually enforced, don't just
prove the artifact instantiates/loads" (G1: block+assert zero real network
calls; AD-4: widen capabilities and assert the gate now fails). That's a
legitimate and well-motivated reuse of an idea. But "adapted from ... design" is
stronger than that — it reads as if there's reusable G1 test *mechanism* (fixture
harness, assertion pattern, tooling) to build AD-4's gate from, and there isn't;
a builder who goes looking at G1's Playwright/Chromium harness for a template
will find nothing applicable to a Wasmtime-host component test.

**Recommendation:** Reword to something like *"in the spirit of `pyforge-atlas`
story G1's `wasm-smoke` non-hollow-gate principle (prove the isolation property,
not just that the artifact loads) — the mechanism itself does not transfer, since
G1 gates a browser/Emscripten artifact via network-request blocking, not a
Wasmtime-host WASI component via capability introspection."*

### Finding 3 (Low) — `dbt-duckdb` 1.10.1 / `dbt-core` 1.12.0 compatibility not cross-checked

**Location:** Stack table, `dbt-core` and `dbt-duckdb` rows.

`dbt-core` 1.12.0 (confirmed released 2026-07-16, 9 days before this spine) and
`dbt-duckdb` 1.10.1 (confirmed released 2026-02-17 — its latest release, ~5
months earlier, per both PyPI and the `duckdb/dbt-duckdb` GitHub releases list)
are both individually the latest available release of each package, so the
pins themselves are correct. But the pairing's *compatibility* wasn't
independently verified anywhere in the spine or research report — `dbt-duckdb`
1.10.1's own package metadata declares an open-ended floor ("targets dbt-core
1.8.x and above"), which on paper covers 1.12.0, but no `dbt-duckdb` release has
shipped since dbt-core 1.10, 1.11, or 1.12 landed, so the pairing is unexercised
by the adapter's own release history. This is lower severity than Findings 1–2
because it doesn't contradict any source — it's a gap the spine's own Marquez
row shows the authors know how to flag (a "verify at implementation time" note)
that wasn't applied here.

**Recommendation:** A one-line implementation-time check (`dbt debug` against a
real DuckDB target on 1.12.0 + dbt-duckdb 1.10.1) before treating this pairing as
load-bearing, or a short note in Stack acknowledging the gap the way the Marquez
row already does.

## Verified-Correct Spot-Checks (supporting the overall verdict)

All independently re-confirmed via live PyPI JSON / GitHub Releases / GitHub
Search APIs on 2026-07-25:

| Claim | Independent check | Result |
|---|---|---|
| FastAPI 0.140.0 | GitHub `tiangolo/fastapi` latest release | Confirmed, published 2026-07-24 |
| `dlt` 1.29.1 | GitHub `dlt-hub/dlt` latest release | Confirmed, published 2026-07-24 |
| `dbt-core` 1.12.0 | GitHub `dbt-labs/dbt-core` latest release | Confirmed, published 2026-07-16 |
| `dbt-duckdb` 1.10.1 | GitHub `duckdb/dbt-duckdb` releases list | Confirmed latest, published 2026-02-17 |
| DuckDB 1.5.5 | GitHub `duckdb/duckdb` latest release | Confirmed, published 2026-07-22 |
| `componentize-py` 0.25.0 | GitHub `bytecodealliance/componentize-py` releases | Confirmed, published 2026-07-07 (matches research's own citation exactly) |
| Wasmtime Python bindings 47.0.1 | GitHub `bytecodealliance/wasmtime-py` tags | Confirmed, latest tag |
| Wasmtime engine 47.0.0 (context for above) | GitHub release notes | Confirmed published 2026-07-20; release notes do state wasi-threads/`wasi-common` removal, matching the research report's claim verbatim |
| `opentelemetry-sdk` 1.44.0 | GitHub `open-telemetry/opentelemetry-python` releases | Confirmed, published 2026-07-16 |
| `openlineage-python` 1.52.0 | GitHub `OpenLineage/OpenLineage` releases | Confirmed, published 2026-07-23 |
| Vector 0.57.0 | GitHub `vectordotdev/vector` releases | Confirmed, published 2026-07-14 (note: the repo's GitHub "latest release" API endpoint actually resolves to an internal `vdev-*` sub-tool tag, not the product version — the spine's 0.57.0 is correct; a naive "latest release" lookup would have been misled) |
| Pixi 0.73.0 | GitHub `prefix-dev/pixi` latest release | Confirmed, published 2026-07-15 |
| Marquez staleness hedge | GitHub `MarquezProject/marquez` latest release + repo `pushed_at` | Confirmed exactly: tag `0.50.0` published 2024-10-24; repo last pushed 2026-07-23. The spine's hedge (defer to implementation-time image-tag check) is the correct call, not a gap. |
| AD-3: "DuckDB has no WASI build/roadmap" | GitHub Search Issues API, `repo:duckdb/duckdb WASI` | Confirmed: `total_count: 0` |
| Research citation: componentize-py issue #92 (NumPy ImportError) | Direct issue fetch | Confirmed real, title/topic matches research's characterization |
| Research citation: componentize-py issue #137 (pydantic support) | Direct issue fetch | Confirmed real, open, topic matches |
| Research citation: `dicej/wasi-wheels` unmaintained | Repo metadata fetch | Confirmed: description states "(Unmaintained)"; last push 2025-10-20 |

No fabricated citations were found in either the spine or the technical research
report among the items checked.

## Items Not Independently Re-Verified

- `opentelemetry-sdk`/`openlineage-python`/`dbt-core` exact patch-to-patch
  interoperability (e.g. whether 1.44.0 SDK + whatever `dlt`/`dbt` instrumentation
  hooks are used at implementation time actually initialize cleanly together) —
  out of scope for a version-existence check; flagged only as a normal
  implementation-time integration risk, not a spine defect.
- WasmEdge/jco WASI Preview 2/3 support level — the research report itself
  already flags this as an open, unverified question (not asserted), so it is
  not a finding against the spine; it correctly inherits the hedge.
- `componentize-py`'s exact CPython-WASI build's supported Python source version
  (independent of the host's `Python 3.12` pin in Finding 1) — not verified here;
  the two are architecturally separate CPython builds and conflating them would
  be a false equivalence.
