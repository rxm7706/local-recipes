---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - docs/dreams/wasm-analytics-stack.md
  - _bmad-output/projects/wasm-analytics-stack/planning-artifacts/research/technical-python-in-wasm-analytics-research-2026-07-25.md
research_type: 'domain'
research_topic: 'Comparable production deployments of sandboxed-Wasm data/business-logic execution — what does the market actually ship today, and in which languages'
research_goals: 'Light domain-research pass (2-3 comparables) to check whether other production Wasm-sandboxing deployments corroborate or contradict the technical-research finding that Python-specific Wasm sandboxing lags Rust/JS in this ecosystem, and to surface any reusable deployment patterns for the wasm-analytics-stack architecture.'
user_name: Rxm7706
date: '2026-07-25'
web_research_enabled: true
source_verification: true
scope_note: 'LIGHT scope per task instructions — 2-3 comparables, not an exhaustive market scan. WebSearch was unavailable this session; sourced via WebFetch against each vendor''s own docs.'
---

# Research Report: Domain Research — Comparable Sandboxed-Wasm Deployments

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Domain (light)

---

## Research Overview

Three production deployments that sandbox untrusted or third-party logic via
WebAssembly were checked against their own current documentation, chosen to span
different shapes of the same problem this project has (running data/business logic
in a Wasm sandbox, invoked from a host application): a general-purpose serverless
platform (Fermyon Spin), a streaming-data transform platform (InfinyOn Fluvio
SmartModules), and an e-commerce logic-injection platform (Shopify Functions). All
three corroborate the technical-research report's finding: **production Wasm
sandboxing today is overwhelmingly Rust/JS-first; Python support, where it exists
at all, is a secondary or unmentioned option**, reinforcing that this project's
Python-specific componentize-py path is ahead of, not behind, typical market
practice — a risk to plan for, not a gap unique to this project.

## 1. Fermyon Spin — general-purpose Wasm serverless

Spin (CNCF project, `fermyon.com/spin`) is described as *"the developer tool for
building WebAssembly microservices and web applications,"* explicitly supporting
multiple languages including Python, alongside Go, JavaScript, Rust, and .NET, with
built-in SQLite, key/value store, HTTP-server, and Redis-trigger primitives. It is
the one comparable of the three that names Python as a first-class supported
language rather than omitting it. Notably, Spin's own marketing cites a real
data-adjacent production win: a customer *"cut compute cost by 60%"* running a
*"Kubernetes batch process of tens of thousands of orders"* on Spin — a genuine,
if thin, data point that Wasm sandboxing can be cost-effective for batch/analytical
workloads at scale, not just low-latency request handlers. Spin's own docs (as
fetched) did not specify which WASI version/component-model maturity level it
targets — worth a direct follow-up if Spin is ever evaluated as a host runtime
alternative to bare Wasmtime.

## 2. InfinyOn Fluvio SmartModules — streaming-data transform sandboxing

SmartModules (`infinyon.com`) are the closest domain comparable to this project's
"sandboxed analytical/validation logic" goal: per InfinyOn's own docs, *"InfinyOn
uses WebAssembly for data processing packages to implement nimble, secure, and
flexible components"* — transformation packages, described as comparable to
serverless functions, that run *"unbounded transformations on connectors to
collect and distribute data with deduplication, filters, flattening etc."*,
i.e. exactly the shape of a Wasm-sandboxed data-quality/validation step this
project needs for its Excel-upload path. **Python is not mentioned as a supported
SmartModule language** in the fetched documentation — the SmartModule Development
Kit (SMDK) page did not list language support explicitly, but the framing and
tooling names (SMDK, SmartModule Hub) read as Rust-first, consistent with the
technical report's finding that Rust is the default/primary language across this
whole ecosystem.

## 3. Shopify Functions — business-logic injection at scale

Shopify Functions (`shopify.dev/docs/apps/build/functions`) compile
merchant/developer-authored business logic to WebAssembly modules that Shopify's
backend invokes directly (JSON in, JSON out) for checkout/discount/shipping
customization — a production deployment at genuinely large scale (every Shopify
checkout). Supported languages are explicitly **Rust (recommended) and
JavaScript only**; Shopify's own docs go so far as to say *"Shopify strongly
recommends Rust as the most performant language choice to avoid your function
failing with large carts"* — an explicit performance/reliability argument for
Rust over the alternative, not just a tooling-maturity one. **No mention of Python
support anywhere** in the fetched documentation. This is the strongest signal of
the three that a large, security-conscious production Wasm-sandboxing deployment
did not consider Python viable enough to offer as an option at all.

## Cross-Comparable Pattern

| Deployment | Domain | Languages offered | Python? |
|---|---|---|---|
| Fermyon Spin | General serverless / microservices | Python, Go, JS, Rust, .NET | Yes — first-class |
| InfinyOn Fluvio SmartModules | Streaming-data transforms | Not specified (Rust-tooling-first framing) | Not confirmed |
| Shopify Functions | Business-logic injection at scale | Rust (recommended), JavaScript | No |

Only one of three comparables offers Python as a named, first-class option, and
even there, no data-workload-specific evidence (comparable to this project's
dlt/dbt/DuckDB stack) was found — Spin's cited production win is a generic batch
job, not a data-pipeline validation/transform step. This is consistent with, and
corroborates, the technical research's core finding: the Wasm-sandboxing
ecosystem's tooling and production track record is led by Rust and JavaScript,
with Python support present but immature and, for anything touching native
data-stack C-extensions (numpy/pandas/pyarrow/duckdb), effectively unproven anywhere
in production — this project would be pushing the frontier of Python-specific Wasm
sandboxing for data workloads, not adopting an established pattern.

## Implication for the Architecture

- Treat the "Python-compiled WASI component" pieces of this project's design as a
  **genuine R&D bet**, not a proven integration — consistent with the technical
  report's recommendation to scope WASI components narrowly (pure-Python
  validation logic only) rather than as the backbone of the pipeline.
  - Fallback precedent exists if the Python-Wasm bet underperforms: Shopify's own
    reasoning (Rust for reliability/performance under load) suggests a fallback
    path of hand-authoring the narrow, security-critical validation logic in Rust
    directly, compiled to a WASI component, if the componentize-py path proves too
    immature — worth naming as an explicit architecture fallback, not a default.
- Spin's cited cost-reduction win on a Kubernetes batch workload is weak but
  positive evidence that Wasm sandboxing (in general, language aside) is not
  inherently a performance tax for batch/analytical-shaped work — useful to cite
  in the PRD's risk section as a counter to "Wasm is only for tiny fast functions."

## Open Questions

- Fluvio SmartModules' actual language support matrix was not confirmed from the
  fetched page (docs page did not enumerate it) — worth a direct check against
  `fluvio.io`/the SMDK repo if InfinyOn's pattern becomes directly relevant to the
  architecture (e.g. if streaming/incremental ingestion is added later).
- No comparable was found for the specific "OpenShift Restricted SCC + WASI
  component" combination this project needs — all three comparables are the
  vendor's own managed runtime (Fermyon Cloud, InfinyOn Cloud, Shopify's backend),
  not a self-hosted-under-OCP deployment. This project may be genuinely novel on
  that specific combination; treat as a risk to validate early architecturally,
  not something to assume "someone else already solved."

## Sources

- [Fermyon Spin](https://www.fermyon.com/spin)
- [InfinyOn Fluvio — SmartModules overview](https://www.infinyon.com/docs/fluvio/smartmodules/overview/)
- [Shopify Functions — Build](https://shopify.dev/docs/apps/build/functions)

---

## Refreshed 2026-08-08 — subject archived-as-satellite; comparables unchanged

- **Status change (2026-08-02):** the Wasm Analytics Stack satellite this report supports was
  folded into Atlas's own brief/PRD/Architecture/Spec chain (`## Satellite:` sections within
  `CAP-18`..`CAP-31` / `AD-24`..`AD-56`; standalone folders preserved under `archive/`);
  `docs/dreams/wasm-analytics-stack.md` is archived/absorbed. **No epics, no stories, no code** —
  the three-comparable pattern (Spin / Fluvio SmartModules / Shopify Functions) and the
  "genuine R&D bet, scope WASI components narrowly" implication remain pre-build inputs,
  untested in the interval.
- **The in-repo precedent this report leans on (pyforge-atlas Story G1, Pyodide/DuckDB-WASM) is
  code-real but note the operating caveat** from
  `technical-atlas-post-ship-debt-and-cross-station-integration-research-2026-08-08.md`: the G1
  build exists and its `wasm-smoke` gate is green, but the surrounding intelligence surface it
  would serve is not yet the production data path — a satellite v2 dashboard reusing G1 should
  treat it as a proven *pattern*, not an operating *service*.
- Comparable currency was not re-verified in this pass (no new adoption decision is pending);
  re-run the currency sweep if and when the satellite is scheduled.
