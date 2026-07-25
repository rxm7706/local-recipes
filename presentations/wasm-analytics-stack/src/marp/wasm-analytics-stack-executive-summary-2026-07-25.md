---
marp: true
paginate: true
size: 16:9
title: Wasm Analytics Stack — Executive Summary
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:26px; }
  h1 { letter-spacing:-0.02em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.01em; color:#201e1d; }
  strong { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  hr { border:none; border-top:3px solid #201e1d; margin:.4em 0; }
  table { font-size:.8em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- _class: lead -->

WASM ANALYTICS STACK · sandboxed pipelines for the hardened enterprise · `docs/dreams/wasm-analytics-stack.md`
**Restricted SCC gives process isolation, not code isolation**

# A second boundary, exactly where it counts.

### Verified, not asserted. Scoped, not inherited.

An Excel upload is checked inside a genuine WASI Preview 2 component under Wasmtime before any row reaches `dlt`, DuckDB Bronze, or the `dbt-duckdb` Silver/Gold transforms — every hop carrying one OTel trace and one OpenLineage record, on one Pixi toolchain that runs identically on a laptop, in a Podman digital twin, and under OpenShift Restricted SCC.

---

## The maturity verdict — read this first

**DuckDB has no WASI build and no WASI roadmap.** A search of `duckdb/duckdb` for "WASI" returns **zero** issues — the question has never been asked upstream. `dlt`'s DuckDB destination and `dbt-duckdb` both inherit that blocker.

**The only community WASI-wheel project is unmaintained.** `dicej/wasi-wheels` is explicitly disclaimed by its own author as a proof-of-concept "not to be relied on for anything serious"; its pandas build has not moved since **December 2024**, and it contains no `pyarrow` and no `duckdb` at all.

**So the sandbox is scoped narrowly and deliberately** to the pure-Python upload-validation step. `dlt`, `dbt` and DuckDB run as conventional Restricted-SCC-hardened processes. That is a smaller claim than the source gist made — and the only one the evidence supports.

---

## Why it matters — three outcomes

**A real trust boundary at the real risk point**
The one place untrusted input first touches the system runs inside a WIT-declared capability sandbox — not just another function in the same trusted process.

**A gate that can fail**
The Isolation-Verification Gate ships with a meta-test from version one: widening the component's declared capabilities without a matching WIT change must make the gate fail. Alongside it, the dependency denylist is a build gate — `numpy`, `pandas`, `pyarrow`, `pydantic` fail `pixi run build`, direct or transitive.

**Parity you can check, not assume**
One canonical `securityContext`, two consumers: the Helm chart and the Podman compose file both generate from it. Non-root UID 1001, read-only rootfs, zero SCC exceptions, one mount contract across all three environments.

---

## The numbers

| Metric | Value |
| --- | --- |
| Capabilities · requirements · architecture decisions | **5 · 17 · 10** |
| DuckDB upstream issues mentioning WASI | **0** |
| SM-4 · Restricted SCC exceptions requested | **0** |
| SM-3 · pipeline stages emitting a correlated span, no gaps | **100%** |
| Claims beyond what research verified as buildable | **0** |

---

<!-- _class: lead -->

## The discipline

A growing denylist-workaround footprint is a signal to reconsider the bet, not to weaken the boundary. Validation latency must never improve by moving checks back out of the sandbox.

**Ships zero claims beyond what the research verified.**

Wasm Analytics Stack · PyForge · Dream to Code
