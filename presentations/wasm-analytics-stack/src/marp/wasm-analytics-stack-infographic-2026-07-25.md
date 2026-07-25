---
marp: true
paginate: true
size: 16:9
title: Wasm Analytics Stack — the stack, at a glance
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:25px; }
  h1 { letter-spacing:-0.02em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.01em; color:#201e1d; }
  strong { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  section.dark { background:#201e1d; color:#f3f2f2; }
  section.dark h1, section.dark h2, section.dark code { color:#f3f2f2; }
  section.dark strong { color:#ec3013; }
  hr { border:none; border-top:3px solid #201e1d; margin:.4em 0; }
  table { font-size:.74em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- _class: lead -->

# Wasm Analytics Stack
## Sandboxed pipelines for the hardened enterprise — at a glance

Let user-uploaded data into a hardened analytical pipeline **without widening the trust boundary of the pipeline's own code** — with the sandboxing claim **mechanically verified, not asserted**.

---

<!-- _class: dark -->

## The maturity verdict — the central scoping fact

**0** issues mentioning WASI in `duckdb/duckdb` — the question has never been asked upstream.
**2024-12** — the last movement on `dicej/wasi-wheels`, unmaintained and disclaimed by its own author. No `pyarrow`, no `duckdb` in it at all.
**1 of 3** production Wasm-sandboxing platforms offer Python at all.

**`dlt`, `dbt` and DuckDB cannot run inside a genuine WASI component today** — the sandbox is therefore scoped to the pure-Python upload-validation step only.

---

## AD-3 · the three-lane split

| Lane | What runs there | Why |
| --- | --- | --- |
| **Conventional processes** | `dlt` · `dbt-duckdb` · DuckDB | Blocked at the DuckDB-dependency level; no `wasm32-wasi` target without an ADR amendment |
| **The WASI sandbox** | Upload validation, pure Python | `componentize-py` is viable here today — the one place untrusted input first lands |
| **Deferred to v2** | Browser read surface onto Gold | DuckDB-WASM + Pyodide — **Emscripten**, not WASI. Shipped by Atlas G1; reused, not reinvented |

---

## The pipeline, and the four decisions

`FastAPI` → **WASI validate** → `dlt` → Bronze → `dbt-duckdb` → Silver/Gold → column-level lineage.

**AD-1** primitives and records only across the WIT boundary — no Arrow buffers, no raw Excel bytes.
**AD-9** synchronous upload; the trace ID correlates, it does not poll.
**AD-7** DuckDB is single-writer: one upload → one `dlt` load → one `dbt run`, same owning process.
**AD-5** one `upload_trace_id`, the bare 32-hex W3C trace-id, never conflated with OpenLineage's `runId`.

---

## The gate must be able to fail

**AD-4** — the Isolation-Verification Gate runs the component under a Wasmtime host granted **only its WIT-declared capabilities**, and ships from version one with a meta-test: widening the declared surface without a matching WIT change **must make the gate fail**.

**AD-2** — the dependency denylist is a **build gate**: `numpy`, `pandas`, `pyarrow`, `pydantic` fail `pixi run build`, direct or transitive — not a policy, not a PR-review expectation.

---

<!-- _class: dark -->

## One toolchain, three environments

**1** Pixi toolchain · **1001** non-root UID with read-only rootfs · **0** Restricted SCC exceptions · **RWO** one mount contract, only the backing differs.

# Ships zero claims beyond what the research verified as buildable.

PRD + architecture depth — stories decompose fresh when scheduled.
