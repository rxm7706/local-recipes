---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/dreams/wasm-analytics-stack.md
  - docs/intake/gists/wasm-first-analytical-data-stack-ocp-ready/gistfile1.txt
  - docs/dreams/sentinel.md
  - docs/intake/sentinel/COMMIT_MSG.txt
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md
research_type: 'technical'
research_topic: 'The current (2026-07) state of Python-in-WASM for data/analytics workloads: WASI Preview 2/3 component model maturity, componentize-py, Pyodide vs. WASI components, dlt/dbt runnability in a WASI sandbox, DuckDB-WASM, and Arrow-WASM'
research_goals: 'Ground the wasm-analytics-stack PRD/architecture in verified 2026 facts (not the April 2026 gist''s assumptions) about whether Python-compiled WASI components can actually host the seed use case''s ingestion (dlt) and transformation (dbt-duckdb) logic, so the architecture proposes what is buildable today vs. what remains a bet on ecosystem maturation.'
user_name: Rxm7706
date: '2026-07-25'
web_research_enabled: true
source_verification: true
scope_note: 'WebSearch was unavailable this session (budget exhausted before this research began); all findings below are sourced via WebFetch against primary docs/specs and via the GitHub REST API (`gh api`, unauthenticated public search + repo/release/issue data) against upstream repos. Every claim is dated and sourced; anything not independently verifiable is flagged as unverified rather than asserted.'
---

# Research Report: Technical Research — Python-in-WASM for Data/Analytics Workloads

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Technical

---

## Research Overview

The April 2026 gist that seeded this Dream (`docs/intake/gists/wasm-first-analytical-data-stack-ocp-ready/`)
proposed a pipeline where Python analytical/validation logic runs as sandboxed WASI
components inside the ingestion path (`dlt` → DuckDB Bronze) and where Apache Arrow
in-memory buffers are the binary interchange between the FastAPI/Python host and the
Wasm module. This report re-verifies that premise against the ecosystem as it stands
today, three months later, using primary sources (upstream READMEs, release notes,
issue trackers, PyPI release metadata) rather than the gist's own claims.

**Headline finding:** the WASI Preview 2 component model itself has matured
meaningfully since April (WASI 0.3 shipped with native async, per wasmtime's own
release notes), but the specific data-stack dependencies the seed use case needs —
DuckDB's native engine, and by inheritance both `dbt-duckdb` and `dlt`'s DuckDB
destination — have **no WASI build, no WASI roadmap, and no GitHub issue evidence
anyone has even attempted one.** `componentize-py` (the Python→WASI-component
compiler) has made real, dated progress on native-extension support in general, but
the only community effort to produce WASI-targeted wheels for exactly this class of
library (`dicej/wasi-wheels`, which includes NumPy and pandas) is explicitly
unmaintained and disclaimed by its own author as a "do not rely on this for anything
serious" proof-of-concept, last touched December 2024. PyArrow and DuckDB have no
WASI wheel attempt at all, maintained or not.

The practical implication for the architecture stage: the ingest→transform→DuckDB
spine of the seed use case should NOT be architected as genuine WASI Preview 2
components today. What IS demonstrably buildable, matching a shipped in-repo
precedent (`pyforge-atlas` story G1), is a narrower split — ordinary sandboxed
processes for the DuckDB-touching pipeline, real WASI components only for
pure-Python (no C-extension) validation/business-logic units, and DuckDB-WASM +
Pyodide (Emscripten target, not WASI) for the browser-side read/analytics surface.
See § Maturity Verdict below for the full breakdown, and the PRD/Architecture
documents for how this reshapes the seed use case's design.

---

## 1. WASI Preview 2 / Component Model Maturity

WASI 0.2.0 has been the stable component-model target since **January 25, 2024**
(`component-model.bytecodealliance.org`) — a stable set of WIT interface definitions
components can target, with `>= v0.2.0` treated as a safe pin. As of mid-2026 this
foundation has moved forward on two fronts:

- **WASI 0.3.0 shipped and is now wasmtime's default.** Wasmtime 46.0.0 (released
  2026-06-22) release notes state directly: *"Wasmtime now supports WASI 0.3.0 by
  default and the `component-model-async` wasm feature is now enabled by default."*
  This closes one of the component model's longest-standing capability gaps — native
  async support for cross-component calls — which the April 2026 gist predates.
- **The Component Model spec itself is still pre-1.0.** Per Bytecode Alliance's
  articles index (accessed 2026-07-25), work toward a stable Component Model 1.0 is
  underway, with the roadmap presented at the February 2026 Plumbers Summit and
  March 2026's Wasm I/O conference — i.e. the foundational spec this whole
  architecture would rest on is still a moving target, not frozen, going into this
  project's build window.
- **wasi-threads was removed, not added.** Wasmtime 47.0.0 (released 2026-07-20)
  removed support for wasi-threads and the `wasi-common` crate entirely (per an
  associated RFC), in favor of the component model's own concurrency primitives
  (the WASI 0.3 async work above). This matters directly for a data-workload
  architecture: there is no mature, supported multi-threaded execution model inside
  a WASI component today — parallelism has to come from the async/component-call
  model, not from OS threads inside the sandbox.
- **Runtime landscape.** Wasmtime (Bytecode Alliance) is the reference host used by
  `componentize-py`'s own toolchain and is confirmed production-maturing at a fast
  release cadence (v45→v47 between May and July 2026 alone). This research did not
  find primary-source confirmation of WasmEdge's or jco's Preview 2/3 support level
  as of 2026-07 — **flagged as an open question**, not asserted either way; the
  architecture should default to Wasmtime as the host given it is what
  `componentize-py` itself targets and verifies against.

## 2. componentize-py: Status and C-Extension Support

`componentize-py` (Bytecode Alliance) compiles a Python application into a WASI
Preview 2 component by pairing WIT interface definitions with a CPython build
targeting `wasm32-wasip1`/`wasm32-wasip2`. Findings from its own README, release
history, and issue tracker (`gh api` against `bytecodealliance/componentize-py`,
accessed 2026-07-25):

- **Requires Python 3.10+.** Actively released — nine releases between
  2026-05-21 (v0.19.3) and 2026-07-07 (v0.25.0), roughly one every 1-2 weeks.
- **Known structural limitation, confirmed in the README:** *"the application can
  only import dependencies during build time, which means any imports used at
  runtime must be resolved at the top level of the application module"* — dynamic
  `importlib`-style runtime imports don't work (tracked as issue #23, still open).
- **Native-extension support has genuinely improved, with dated evidence:**
  - Issue #208, *"Recognize `.abi3.so` native extensions in linker scanner"* — closed.
  - Issue #100, *"Error when using native extensions built with maturin and pyo3"* — closed.
  - Issue #195, *"feat: add SQLite3 support to CPython WASI build"* — closed; SQLite3
    is now available inside the componentize-py CPython-WASI build itself.
  - Issue #143, *"unsupported export kind for memory: Memory when loading lxml
    build"* — closed (lxml, a C-extension-backed library, is a confirmed working
    case once the export-kind bug was fixed).
- **Still explicitly unsupported / open, as of 2026-07-25:** issue #137
  (`pydantic` support, open) and issue #141 (PyTorch support, open) — i.e. even
  common pure-ish-Python-with-a-compiled-core libraries the seed use case's FastAPI
  layer would likely want (`pydantic`) are not yet a solved case.
- **NumPy works, but only via community-built WASI wheels, not standard PyPI
  wheels.** Issue #92 documents this directly. A user hit `ImportError: Importing
  the numpy C-extensions failed`; the maintainer's response: *"Packages which
  contain native extensions (such as NumPy) must be built for WASI (i.e. the Mac,
  Windows, and Linux builds won't work). Some day, package maintainers will be able
  to publish WASI builds to pypi.org alongside the existing Mac, Windows, and Linux
  builds, but we're not there yet."* The working path requires downloading
  `numpy-wasi.tar.gz` from a separate community repo, `dicej/wasi-wheels`.
- **`dicej/wasi-wheels` is the ecosystem's only WASI-cross-compiled-wheel source for
  this class of library, and it is explicitly disclaimed as non-production.** Its
  README states verbatim: *"This project is an experimental proof-of-concept that
  Python packages containing native extensions can be cross-compiled for WASI and
  used with componentize-py. It is not being actively maintained; the packages are
  out-of-date with respect to their upstream versions, and might not even build
  anymore. Do not rely on these builds for anything serious."* Its package
  directory (`gh api repos/dicej/wasi-wheels/contents/`) contains: `aiohttp`,
  `charset_normalizer`, `frozenlist`, `greenlet`, `multidict`, `numpy`, `pandas`,
  `pydantic-core`, `regex`, `sqlalchemy`, `tiktoken`, `wrapt`, `yaml`, `yarl` — **no
  `pyarrow`, no `duckdb`.** The last commit touching the `pandas` build directory
  was 2024-12-09 (*"add wasm target to pandas' numpy npy-cpu header"*); the repo's
  last release tag (`v0.0.2`) is 2025-10-02. Nothing has moved on it in 2026.
- **`pandas` and `pyarrow`/`duckdb` mentions in componentize-py's own issue tracker:
  zero.** A `gh api search/issues` query for `pandas`, `pyarrow`, and `duckdb`
  against `bytecodealliance/componentize-py` each returned `total_count: 0` — no
  one has even opened an issue attempting either, unlike numpy (issue #92) or
  PyTorch (issue #141, open/unsupported).

## 3. Pyodide vs. Genuine WASI Preview 2 Components

These are two different compilation targets solving two different problems, and the
Dream's use case needs to be split across them rather than treated as one choice:

- **Compilation target.** Pyodide builds CPython for `wasm32-unknown-emscripten`.
  Per CPython's own platform-support PEP (PEP 11, accessed 2026-07-25):
  `wasm32-unknown-emscripten` is a **Tier 3** platform (contact: Russell
  Keith-Magee), while `wasm32-unknown-wasip1` (WASI Preview 1) became a **Tier 2**
  platform starting with Python 3.13 (*"WASI was a tier 3 platform for Python 3.11
  and 3.12, and became a tier 2 platform starting with Python 3.13"*) — i.e. CPython
  upstream itself now takes the WASI target more seriously (Tier 2: tested, but not
  release-blocking) than the Emscripten/Pyodide target (Tier 3: best-effort).
- **Deployment shape.** Pyodide explicitly targets *"the browser and Node.js"* (per
  the `pyodide/pyodide` repository description) — it is not a Wasmtime-hosted,
  capability-scoped WASI component; it's a full CPython build running under an
  Emscripten (browser) or Node.js sandbox. That sandbox model is real but different
  from — and generally weaker/less fine-grained than — the capability-based host
  isolation a WASI Preview 2 component gets under Wasmtime with an explicit,
  per-component set of granted imports.
- **Both are "meaningfully sandboxed" per CPython's own framing.** PEP 776 (the
  Emscripten Tier-3 platform-support PEP, accessed 2026-07-25) states: *"Emscripten
  and WASI are also the only supported platforms that offer any meaningful
  sandboxing"* — validating the Dream's underlying instinct (Wasm-family targets
  specifically buy real isolation that a plain container does not) without settling
  which of the two lanes fits this project.
- **Ecosystem package availability moved, but only on the Pyodide/Emscripten side,
  and only very recently.** `pandas` began publishing official
  `pyemscripten_2024_0_wasm32` wheels directly to PyPI starting with **version
  3.0.4, uploaded 2026-06-28** (verified via `pypi.org/pypi/pandas/json` release
  metadata) — after the April 2026 gist, a genuine "what changed" data point. As of
  today (2026-07-25), the same check against `numpy`, `pyarrow`, `duckdb`, and
  `polars` on PyPI found **zero** `emscripten`/`wasm`-tagged wheels for any of them
  in any release — NumPy remains distributed only through Pyodide's own
  package/lock build pipeline (not PyPI directly), and PyArrow/DuckDB/Polars have no
  wasm32 distribution on PyPI at all yet, official-Pyodide-recipe or otherwise.
- **Verdict for this project:** Pyodide is the mature, low-risk choice **for a
  browser-hosted or Node-hosted read/analytics surface** — exactly what
  `pyforge-atlas` story G1 already shipped (see § 8 below) — but it is the wrong
  tool for *"sandboxed analytical/validation logic running as a component inside
  the OCP pod, invoked by the ingestion path."* That job is squarely the
  WASI-Preview-2/`componentize-py`/Wasmtime lane, which § 2 shows is far less
  mature for anything beyond pure-Python logic.

## 4. Can dlt and dbt Actually Run Inside a WASI Preview 2 Sandbox Today?

**No — not the DuckDB-backed path this project's seed use case needs — and no one
appears to have tried.**

- **`dlt` (dlt-hub/dlt).** A `gh api search/issues` query for `wasm` against the
  repo returned 8 hits, every one of them about a browser-based **dashboard**
  experiment (a `marimo`-notebook-in-the-browser demo running via Pyodide/WASM —
  issues #3899/#3602 *"Experiments: wasm dashboard"*, #2841, #2832), not about
  running the ingestion pipeline itself inside a sandbox. dlt's only "wasm" story
  to date is a Pyodide-based UI demo for the dashboard, unrelated to the
  ingest-into-DuckDB path the seed use case needs sandboxed.
- **`dbt-core` (dbt-labs/dbt-core).** Two relevant, both closed:
  - Issue #5803, *"Run dbt on WebAssembly using Pyodide"* — an old exploratory PR
    that refactored dbt's HTTP and parallel-processing internals into swappable
    clients so dbt could run in-browser via Pyodide (a jaffle-shop/SQLite browser
    demo). This proves dbt-core *can* be made to run under Pyodide with source
    changes, but it is old, Emscripten/browser-targeted (not WASI), and not a
    currently-maintained, supported deployment target.
  - Issue #14056, *"[FEAT] WebAssembly (Wasm) compilation target"* — opened
    against the newer Rust-based dbt Fusion engine (*"Now that it's in Rust, can we
    compile it to WebAssembly?"*), and **auto-closed by dbt Labs' stale-issue bot
    after 90 days of no activity.** As of 2026-07-25 this is an acknowledged,
    unaddressed question, not a shipped or in-progress feature.
  - **`dbt-duckdb` (duckdb/dbt-duckdb):** zero issues mention `wasm` at all.
- **Major, dated finding not in the April 2026 gist: dbt Labs shipped a ground-up
  Rust rewrite of the dbt engine, `dbt Fusion`, now in Beta** (per the
  `dbt-labs/dbt-fusion` repository, accessed 2026-07-25 — *"a ground up, first
  principles rewrite of the dbt Core execution engine"* in Rust, currently Beta:
  *"Bugs and missing functionality compared to dbt Core will be resolved
  continuously"*). This matters because a Rust engine is architecturally far more
  WASI-component-friendly than CPython + C-extensions — but as of today it
  supports Snowflake, Databricks, BigQuery, and Redshift via Arrow Database
  Connector (ADBC) drivers, **explicitly no DuckDB adapter**, and **no
  WebAssembly/WASM/WASI target mentioned anywhere in its docs or issue tracker.**
  For this project's DuckDB-backed seed use case, Fusion is not an option today —
  worth tracking as a Year-2+ bet, not a Year-1 dependency.
- **Root blocker, confirmed at the source: DuckDB itself has no WASI build and no
  WASI roadmap.** A `gh api search/issues` query for `WASI` against `duckdb/duckdb`
  returned **zero** results — the core C++ engine both `dbt-duckdb` and `dlt`'s
  DuckDB destination depend on has never even had the question asked upstream.
  Since both the seed use case's transform layer (`dbt-duckdb`) and its bronze
  storage (`dlt` → DuckDB) sit directly on this dependency, **the ingest→transform
  spine cannot be a genuine WASI Preview 2 component today**, independent of
  whether `dlt`'s or `dbt`'s own Python code could theoretically be
  `componentize-py`-compiled.
- **What is plausible but undemonstrated:** the parts of `dlt` that are pure-Python
  (schema inference, extraction orchestration, config/state handling) do not
  inherently require a native DuckDB dependency until the DuckDB *destination*
  adapter is invoked — so a `componentize-py`-compiled dlt "extract + validate"
  stage feeding a conventionally-hosted (non-Wasm) DuckDB-writing stage is
  architecturally conceivable. No evidence was found that anyone has built or
  documented this split, so it should be treated as a design hypothesis to
  prototype, not a proven pattern.

## 5. DuckDB-WASM: Maturity, Target, and the WASI Question

DuckDB-WASM (`duckdb/duckdb-wasm`, accessed 2026-07-25) brings DuckDB's SQL/OLAP
engine to browsers and Node.js, based on DuckDB v1.5.4, tested against Chrome,
Firefox, Safari, and Node.js, with a live deployed shell at `shell.duckdb.org`. It
"speaks Arrow fluently" (reads Parquet/CSV/JSON, returns Arrow-format results) and
is the exact technology `pyforge-atlas` story G1 already shipped in production for
its in-browser read surface (see § 8).

- **Compilation target: Emscripten, not WASI.** The project's own README does not
  discuss WASI at all (confirmed via WebFetch of the README); its distribution
  model (browser + Node.js, extensions hosted at `extensions.duckdb.org`) matches
  the same Emscripten/browser lane as Pyodide, not the Wasmtime/WASI-component
  lane.
- **No bridge to the WASI-component pipeline.** There is no adapter or
  interoperability pattern connecting DuckDB-WASM (Emscripten) to a
  WASI-Preview-2-component-based pipeline — they are two separate, non-overlapping
  compilation targets. DuckDB-WASM is mature and shippable for the browser-side
  read/dashboard surface; it cannot serve as the "DuckDB running inside a
  Restricted-SCC WASI component on the server" piece the April 2026 gist's step 3
  implied.
- **Multithreading is explicitly experimental and off by default** in DuckDB-WASM
  per its own docs — a second, independent confirmation (alongside § 1's
  wasi-threads removal) that concurrency inside any Wasm-family sandbox in this
  ecosystem is immature across the board in 2026, not just on the WASI side.

## 6. Apache Arrow's WASM Story

No first-class, Arrow-maintained WASM/WASI interchange primitive was found. Arrow's
own JS documentation (`arrow.apache.org/docs/js/`, accessed 2026-07-25) does not
discuss a WASM build of Arrow C++ or the Arrow C Data Interface for WASM/WASI
host↔guest interchange; the only WASM-adjacent mention is a third-party project
(Perspective) that independently compiles Arrow C++ to WebAssembly for its own
browser visualization use — not something Arrow ships or supports as a general
component-boundary interchange format.

**Implication for the gist's step 2** ("Validate: Python-Wasm module validates data
quality via Apache Arrow in-memory buffers"): there is no confirmed off-the-shelf
implementation of this pattern to build on. It would need to be hand-built on top
of WIT-defined component interfaces (e.g. passing Arrow IPC-format bytes as an
opaque buffer across the component boundary, re-parsed with `pyarrow` on each
side) — and `pyarrow` itself is not confirmed to run inside a
`componentize-py`-built WASI component at all (§ 2: zero issues, neither a working
example nor a known failure — genuinely untested).

## 7. What Changed Since the April 2026 Gist — Summary

| Change | Date | Lane affected |
|---|---|---|
| WASI 0.3.0 ships, native async, wasmtime default | 2026-06-22 (wasmtime 46.0.0) | WASI component model (infra) |
| wasi-threads / wasi-common removed from wasmtime | 2026-07-20 (wasmtime 47.0.0) | WASI component model (infra) |
| Component Model 1.0 still roadmap-only, not shipped | as of Mar 2026 Wasm I/O talks | WASI component model (infra) |
| `componentize-py` v0.19.3 → v0.25.0, incl. `.abi3.so` recognition, pyo3/maturin fixes, in-tree SQLite3 | 2026-05-21 → 2026-07-07 | componentize-py |
| `dicej/wasi-wheels` (numpy/pandas WASI wheels) last touched, explicitly unmaintained | pandas dir: 2024-12-09; repo: 2025-10-02 | componentize-py + data libs (no movement) |
| `pandas` ships official `pyemscripten_2024_0_wasm32` wheels on PyPI | 2026-06-28 (pandas 3.0.4) | Pyodide/Emscripten lane only |
| `dbt Fusion` (Rust rewrite) reaches Beta; ADBC adapters for Snowflake/Databricks/BigQuery/Redshift; no DuckDB, no wasm target | ongoing through 2026, Beta as of 2026-07-25 | dbt (new lane, not yet usable for this project) |

Not found, despite searching: any movement on DuckDB-core WASI support, any
PyPI-published `pyarrow`/`duckdb`/`polars`/`numpy` wasm32 wheels, or any dlt/dbt
pipeline-execution (as opposed to dashboard-demo) WASI/Wasm sandboxing attempt.

## 8. In-Repo Precedent: pyforge-atlas Story G1

`pyforge-atlas` already shipped (merged PR #96, 2026-07-18) the exact pattern this
research independently arrives at as "what's actually buildable": a **DuckDB-WASM
+ browser** read surface, **not** a server-side WASI-sandboxed pipeline. Per its
recovered story spec
(`_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md`):
a static page fetches a Parquet file as bytes and runs `read_parquet(...)` inside
genuine DuckDB-WASM — "no server-side query, no API." Its `wasm-smoke` gate proves
the no-backend/offline claim by asserting **zero non-loopback network requests**
under headless Chromium (including Web-Worker traffic for both the `.wasm` module
and the vendored Parquet extension), and the DuckDB Parquet extension is **vendored
locally** rather than fetched from `extensions.duckdb.org` at runtime — a concrete,
reusable air-gap pattern this project's architecture should adopt directly for its
own read-surface. Deferred from G1 (not yet done): the full Vizro/Pyodide dashboard
render (currently a plain HTML table) — worth noting as the more complete
"Pyodide + DuckDB-WASM" precedent is itself still partial.

---

## Maturity Verdict

| Component | Verdict | Basis |
|---|---|---|
| **WASI Preview 2/3 component model** | **Viable foundation, still moving.** 0.2 stable since Jan 2024, 0.3 (async) shipped Jun 2026, Wasmtime is a maturing production host. Component Model 1.0 itself is not yet final. | wasmtime 46.0.0/47.0.0 release notes; component-model.bytecodealliance.org |
| **componentize-py** | **Viable for pure-Python logic only.** Real, dated progress on native-extension plumbing (.abi3.so, pyo3/maturin, in-tree SQLite3) but pydantic and PyTorch are still open/unsupported, and dynamic runtime imports remain restricted. | componentize-py README + issues #23, #100, #137, #141, #195, #208 |
| **Pyodide** | **Mature — for the browser/Node lane, not the server-sandboxing lane.** CPython Tier-3-platform, Emscripten target, distinct sandbox model from WASI components. Right tool for a dashboard/read surface (proven by G1); wrong tool for "runs inside the OCP pod as a WASI component." | PEP 11, PEP 776, pyodide/pyodide repo description |
| **dlt-in-WASI** | **Blocked for the DuckDB-backed path; unproven-but-plausible for pure-Python extract/validate stages.** dlt's only "wasm" work to date is a Pyodide browser dashboard demo, unrelated to sandboxing the pipeline itself. | dlt-hub/dlt issue search (8 hits, all dashboard-related) |
| **dbt-in-WASI** | **Blocked.** Python dbt-core+dbt-duckdb inherits DuckDB's non-WASI native engine; the WASI-friendlier Rust dbt Fusion engine has no DuckDB adapter and no wasm target as of today. | dbt-core #5803/#14056; dbt-labs/dbt-fusion repo |
| **DuckDB-WASM** | **Mature, but wrong lane for this question.** Emscripten/browser target, proven in production by pyforge-atlas G1; no WASI build exists or is planned per available evidence. | duckdb/duckdb-wasm README; pyforge-atlas G1 spec |
| **Arrow-WASM** | **Unproven / DIY.** No Arrow-maintained, general-purpose WASM/WASI host↔component interchange primitive found; the gist's "Arrow buffers across the Wasm boundary" step would be a from-scratch build on top of WIT, not an existing library. | arrow.apache.org/docs/js/ |

**Bottom line for the architecture stage:** do not architect the seed use case's
ingest (`dlt`) → transform (`dbt-duckdb`) → DuckDB (Bronze/Silver/Gold) spine as
WASI Preview 2 components — the blocking dependency (DuckDB's native engine) has no
WASI story anywhere in its own upstream tracker. What the current ecosystem state
supports, and what this project should actually build, is a three-lane split:
ordinary Restricted-SCC-hardened processes for the DuckDB-touching pipeline core;
real `componentize-py`-built WASI components only for genuinely pure-Python
validation/business-logic units at trust boundaries (e.g. the Excel-upload
validation step, kept free of numpy/pandas); and DuckDB-WASM + Pyodide in the
browser for the read/analytics surface, following the `pyforge-atlas` G1 pattern
(vendored extensions, zero-non-loopback-request proof) directly.

---

## Open Questions (carried to PRD/Architecture)

- Is a `componentize-py`-compiled, pure-Python (no numpy/pandas) validation stage —
  fed pre-parsed scalar/row data rather than an Arrow buffer — sufficient to satisfy
  the Dream's "sandboxed analytical/validation logic" goal, given the C-extension
  path is not viable? This reframes "Arrow buffer across the Wasm boundary" as a
  simplification, not a loss, but needs an explicit decision.
- WasmEdge's and jco's WASI Preview 2/3 support level as of 2026-07 is unverified in
  this research (no primary source found) — resolve before committing to a
  non-Wasmtime host, if one is ever considered.
- Should the architecture track `dbt Fusion` as a future migration path once/if it
  gains a DuckDB adapter, or treat the DuckDB dependency itself as the thing to
  reconsider (e.g. an ADBC-fronted warehouse Fusion already supports)? Deferred —
  the seed use case's DuckDB choice predates this research and is treated as fixed
  for V1.
- Whether a `dlt` "extract + pure-Python validate" / "load to DuckDB" split
  (§ 4, plausible-but-undemonstrated) is worth prototyping as a spike before the
  architecture commits to it as a real component boundary.

## Sources

- [WebAssembly Component Model — Introduction](https://component-model.bytecodealliance.org/)
- [Bytecode Alliance — Articles/News index](https://bytecodealliance.org/articles) (accessed 2026-07-25)
- [bytecodealliance/wasmtime — RELEASES.md (release-46.0.0 branch)](https://github.com/bytecodealliance/wasmtime/blob/release-46.0.0/RELEASES.md)
- [bytecodealliance/wasmtime — RELEASES.md (release-47.0.0 branch)](https://github.com/bytecodealliance/wasmtime/blob/release-47.0.0/RELEASES.md)
- [bytecodealliance/componentize-py — README](https://github.com/bytecodealliance/componentize-py/blob/main/README.md)
- [componentize-py issue #23 — runtime import restriction](https://github.com/bytecodealliance/componentize-py/issues/23)
- [componentize-py issue #92 — ImportError with NumPy / wasi-wheels](https://github.com/bytecodealliance/componentize-py/issues/92)
- [componentize-py issue #100 — native extensions built with maturin and pyo3](https://github.com/bytecodealliance/componentize-py/issues/100)
- [componentize-py issue #137 — pydantic support (open)](https://github.com/bytecodealliance/componentize-py/issues/137)
- [componentize-py issue #141 — PyTorch support (open)](https://github.com/bytecodealliance/componentize-py/issues/141)
- [componentize-py issue #143 — lxml build memory export fix](https://github.com/bytecodealliance/componentize-py/issues/143)
- [componentize-py issue #195 — SQLite3 support in CPython WASI build](https://github.com/bytecodealliance/componentize-py/issues/195)
- [componentize-py issue #208 — .abi3.so native extension recognition](https://github.com/bytecodealliance/componentize-py/issues/208)
- [dicej/wasi-wheels — README (explicit non-production disclaimer)](https://github.com/dicej/wasi-wheels)
- [PEP 11 — CPython platform support tiers (wasm32-unknown-wasip1 Tier 2, wasm32-unknown-emscripten Tier 3)](https://peps.python.org/pep-0011/)
- [PEP 776 — Emscripten platform support / sandboxing framing](https://peps.python.org/pep-0776/)
- [pyodide/pyodide — repository](https://github.com/pyodide/pyodide)
- [pandas on PyPI — release files (3.0.4/3.0.5 pyemscripten_2024_0_wasm32 wheels)](https://pypi.org/project/pandas/)
- [duckdb/duckdb-wasm — README](https://github.com/duckdb/duckdb-wasm)
- [Apache Arrow — JavaScript/WASM docs](https://arrow.apache.org/docs/js/)
- [dlt-hub/dlt — wasm-related issues (dashboard experiments)](https://github.com/dlt-hub/dlt/issues)
- [dbt-labs/dbt-core issue #5803 — Run dbt on WebAssembly using Pyodide](https://github.com/dbt-labs/dbt-core/issues/5803)
- [dbt-labs/dbt-core issue #14056 — [FEAT] WebAssembly (Wasm) compilation target](https://github.com/dbt-labs/dbt-core/issues/14056)
- [dbt-labs/dbt-fusion — repository (Beta, Rust rewrite, ADBC adapters)](https://github.com/dbt-labs/dbt-fusion)
- [duckdb/duckdb — issue search for "WASI" (zero results)](https://github.com/duckdb/duckdb/issues)

## Local (in-repo) sources consulted

- `docs/dreams/wasm-analytics-stack.md` — the Dream.
- `docs/intake/gists/wasm-first-analytical-data-stack-ocp-ready/gistfile1.txt` — the
  April 2026 architecture README/spec this research re-verifies.
- `docs/dreams/sentinel.md` + `docs/intake/sentinel/COMMIT_MSG.txt` — ADR-037/038/039
  (the WASM parallel branch, all-local airgap build, split airgap bundle) — kinship
  context for the airgap/OCP posture, not independently re-verified here.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md` —
  the shipped DuckDB-WASM/Pyodide precedent (§ 8).

## Methodology Note

WebSearch was unavailable for this research run (session budget exhausted before
this task began). All findings above were gathered via `WebFetch` against primary
documentation/spec pages and via the GitHub REST API (`gh api`, unauthenticated
public endpoints — repo metadata, release lists, issue/code search) against the
relevant upstream repositories. This skews the source mix toward primary
GitHub-hosted evidence (READMEs, release notes, issue threads) over secondary
commentary (blog posts, conference writeups) that a WebSearch-driven pass would
normally surface — flagged per § "What's not confirmed" items above (notably
WasmEdge/jco P2/P3 support level) rather than filled in from training-data recall.
