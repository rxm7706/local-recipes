---
marp: true
paginate: true
size: 16:9
title: Wasm Analytics Stack — a second boundary, where it counts
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:26px; }
  h1 { letter-spacing:-0.02em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.01em; color:#201e1d; }
  strong { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  section.dark { background:#201e1d; color:#f3f2f2; }
  section.dark h1, section.dark h2, section.dark h3, section.dark code { color:#f3f2f2; }
  section.dark strong { color:#ec3013; }
  hr { border:none; border-top:3px solid #201e1d; margin:.4em 0; }
  table { font-size:.72em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- 01 · Cover -->

WASM ANALYTICS STACK · sandboxed pipelines for the hardened enterprise · PyForge · Dream: `docs/dreams/wasm-analytics-stack.md`

# a second boundary,<br>where it counts.

Excel upload → **WASI-sandboxed validation** → `dlt` into DuckDB Bronze → `dbt` Silver/Gold, every hop traced by OTel and lineaged by OpenLineage, on **one Pixi toolchain** from laptop to Podman twin to OpenShift Restricted SCC.

| Sandbox | Scope | Contract | Depth |
| --- | --- | --- | --- |
| WASI Preview 2 · Wasmtime | upload validation only | 5 CAP · 17 FR · 10 AD | PRD + architecture |

---

<!-- _class: dark -->

## The maturity verdict — verified 2026-07-25

# dlt, dbt and DuckDB cannot run in a WASI component today

**0** — issues mentioning WASI in `duckdb/duckdb`. The core engine both `dbt-duckdb` and `dlt`'s DuckDB destination sit on has **never had the question asked upstream**.
**2024-12** — the last movement on `dicej/wasi-wheels`, the ecosystem's only WASI-wheel source for this class of library, **explicitly disclaimed by its own author** as a proof-of-concept. It contains no `pyarrow` and no `duckdb` at all.
**1 of 3** — production Wasm-sandboxing platforms (Spin, Fluvio, Shopify Functions) that offer Python at all.

Not a scoping preference. A **blocked dependency**.

---

<!-- _class: dark -->

## Act I

# The gap that remains

Restricted SCC gives **process** isolation, not **code** isolation. The Python process inside a hardened pod still has the whole language surface available to anything running inside it — **and nothing separates the pipeline's own code from logic derived from an uploaded file.**

---

## The scope that survives — AD-3's three lanes

| Lane | What runs there | Why |
| --- | --- | --- |
| **Conventional processes** | `dlt` · `dbt-duckdb` · DuckDB | Blocked at the DuckDB-dependency level. No `wasm32-wasi` build target without an ADR amendment citing new upstream evidence |
| **The WASI sandbox** | Upload validation — pure Python | `componentize-py` is viable for pure-Python logic today. **The one place untrusted input first touches the system** |
| **Deferred to v2** | Browser read surface onto Gold | DuckDB-WASM + Pyodide — an **Emscripten** target, not WASI. Shipped by PyForge Atlas G1; reused, not reinvented |

A smaller claim than the April 2026 gist made — and, per the research, the larger claim is **not buildable with today's ecosystem**.

---

<!-- _class: dark -->

## Act II

# The seed use case

One spreadsheet, one trace ID, five stages. **Excel upload is the only ingestion path in v1** — and every architecture decision is scoped to it.

---

## Upload → validate → Bronze → Gold

`FastAPI` (OIDC at the gateway; 401 before the body is read) → **WASI validate** (zero rows reach Bronze from a structurally invalid file) → `dlt` → Bronze → `dbt-duckdb` Silver/Gold (a failing `dbt test` leaves the prior good state queryable) → column-level lineage back to Bronze.

**AD-1** — primitives and records only across the WIT boundary: no shared memory, no Arrow buffers, no raw Excel bytes. Parsing happens outside the sandbox.
**AD-9** — the upload is **synchronous**; the returned `upload_trace_id` correlates, it does not poll. There is no v1 polling endpoint.
**AD-7** — DuckDB is single-writer: one upload → exactly one `dlt` load → exactly one `dbt run`, sequentially, from the same owning process.

---

## The gate must be able to fail

**AD-4 — the meta-test, from version one.** The gate runs the compiled component under a Wasmtime host granted **only its WIT-declared capabilities** and fails on any host interaction beyond them. Then it proves itself: widening the declared capability surface without a matching WIT change **must make the gate fail**. A gate that always passes is not a gate.

**AD-2 — the denylist is a build gate.** `pixi run build` runs a static import scan over source **and resolved closure**, failing on `numpy`, `pandas`, `pyarrow`, `pydantic` or any other C-extension-backed or `componentize-py`-unproven import — direct or transitive, at build time, not as a later runtime error.

---

## One trace ID. One security context.

**AD-5** — `upload_trace_id` is always the **bare 32-hex W3C trace-id**: never the full `traceparent`, never a UUID, never dashed. Minted once at ingress, carried into the `dlt` load package, passed to `dbt` as a var, attached as a custom OpenLineage facet — and never conflated with OpenLineage's own `runId`. Only the Vector sidecar holds an external telemetry egress path.

**AD-6** — one canonical `securityContext` authored once under `deploy/`; the Helm chart and the Podman compose file both **generate** from it. Neither hand-authors a copy — two copies drifting apart is precisely what would silently defeat the parity claim.

---

## One toolchain, three environments

**Local dev** — `pixi install && pixi run build` compiles the WASI component alongside everything else, with no manual steps outside Pixi.
**Podman digital twin** — `--read-only --user 1001`, the same security context OCP enforces, so a Restricted-SCC-incompatible change is caught locally.
**OpenShift Restricted SCC** — non-root UID 1001, read-only rootfs, no privilege escalation, **zero SCC exceptions requested**.

DuckDB state mounts at the **same path** from a `ReadWriteOnce`-shaped volume in all three; only the backing implementation changes. **AD-8:** every build-time fetch routes through the configured mirror — no build script hardcodes a public URL.

---

<!-- _class: lead -->

## The discipline

# This project ships zero claims beyond what its own research verified as buildable today.

**SM-C1** — a growing denylist-workaround footprint is a signal to reconsider the bet, never to weaken the boundary.
**SM-C2** — validation latency must never improve by moving checks **out of the sandbox**.
**Planning depth** — PRD + architecture only. No epics, no stories; they decompose fresh when scheduled.

Wasm Analytics Stack · PyForge · Dream to Code
