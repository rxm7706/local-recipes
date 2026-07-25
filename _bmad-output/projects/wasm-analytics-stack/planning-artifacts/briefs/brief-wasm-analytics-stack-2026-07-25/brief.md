---
title: "Product Brief: Wasm Analytics Stack"
status: "draft"
created: "2026-07-25"
updated: "2026-07-25"
inputs:
  - "docs/dreams/wasm-analytics-stack.md (the Dream)"
  - "docs/intake/gists/wasm-first-analytical-data-stack-ocp-ready/gistfile1.txt (2026-04-19 architecture README — primary intake)"
  - "docs/dreams/sentinel.md + docs/intake/sentinel/COMMIT_MSG.txt (ADR-037/038/039 — WASM branch, all-local airgap, split airgap bundle)"
  - "docs/dreams/unity-data-stack.md (the platform this stack would live on)"
  - "docs/dreams/enterprise-airgap.md (the deployment posture)"
  - "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-g1-compile-the-intelligence-layer-to-pyodide-duckdb-wasm.md (shipped sibling proof)"
  - "_bmad-output/projects/wasm-analytics-stack/planning-artifacts/research/technical-python-in-wasm-analytics-research-2026-07-25.md"
  - "_bmad-output/projects/wasm-analytics-stack/planning-artifacts/research/domain-sandboxed-analytics-deployments-research-2026-07-25.md"
project_slug: "wasm-analytics-stack"
---

# Product Brief: Wasm Analytics Stack

## Executive Summary

Wasm Analytics Stack is a modern analytical data pipeline — ingest via **dlt**,
transform via **dbt-duckdb**, observe via native **OpenTelemetry** tracing and
**OpenLineage** provenance — built to run natively hardened on Red Hat OpenShift
under **Restricted SCC** (non-root UID 1001, read-only rootfs), with one **Pixi**
toolchain bridging local development, Podman "digital twin" verification, and
production OCP, all validated through the same command path before a single line
ships to a cluster.

Its differentiating bet, carried from the April 2026 architecture gist that seeded
this Dream, is that the analytical/validation logic sitting closest to untrusted
input (the seed use case: a user-uploaded Excel file, ingested via FastAPI) runs
inside a genuine **WASI Preview 2 sandbox**, not just an OCP-hardened process — a
second, language-level isolation boundary underneath the platform-level one.
**[ASSUMPTION]** This is the Dream's most novel claim and, per the technical
research completed alongside this brief, the one requiring the most honesty: the
WASI-component ecosystem has matured meaningfully since April 2026, but the
specific dependency this project's seed use case needs most — DuckDB's native
engine, inherited by both `dlt`'s DuckDB destination and `dbt-duckdb` — has **no
WASI build and no WASI roadmap anywhere upstream**. The brief below scopes V1
around what the research shows is actually buildable today (a narrow,
pure-Python WASI validation layer plus a conventionally-hosted DuckDB pipeline),
rather than repeating the gist's un-re-verified "Python-Wasm validates via Arrow
buffers" step as settled fact.

The product exists because two things are already true in this workspace and
nowhere else combines them: (1) a shipped, in-repo proof that Python analytical
logic *can* run zero-backend in a WASM-family sandbox — `pyforge-atlas` story G1
(DuckDB-WASM + Pyodide, browser-side, merged PR #96, 2026-07-18) — and (2) a
fully-specified, OCP-hardened enterprise deployment posture already documented for
this repo's other projects (`docs/dreams/enterprise-airgap.md`,
`docs/reference/enterprise-deployment.md`). Wasm Analytics Stack is the first
project to combine both: a real data pipeline, not a read-only dashboard, running
under the strictest OCP security profile, with Wasm sandboxing applied exactly
where the research shows it is defensible today.

## The Problem

Enterprises running regulated or hardened Kubernetes/OpenShift environments face a
specific, recurring tension when they want to let less-trusted logic (a
user-uploaded file, a third-party transformation rule, an analyst's ad hoc
validation script) into an otherwise locked-down data pipeline:

1. **Restricted SCC gives you process isolation, not code isolation.** A pod
   running as non-root UID 1001 with a read-only rootfs is meaningfully hardened
   against *escape*, but the Python process inside that pod still has the full
   language surface available to anything that runs inside it — there is no
   second boundary between "the pipeline's own trusted code" and "logic derived
   from a file a user just uploaded." **[ASSUMPTION]** This is the gap the Dream's
   WASI-sandboxing bet targets; the domain research below confirms other
   production platforms (Shopify Functions, Fermyon Spin) solve exactly this
   problem by compiling the untrusted-input-adjacent logic to a Wasm sandbox with
   its own, narrower capability grants — a pattern this project can adopt.
2. **Observability and lineage are usually bolted on, not native.** Data teams
   commonly wire OTel tracing and OpenLineage provenance in after the fact, per
   pipeline, inconsistently. The cost is invisible until an audit or an incident
   needs the trace and it doesn't exist end-to-end (browser upload → API →
   ingestion → transform).
3. **Local dev, container verification, and production drift apart.** Without one
   toolchain spanning all three, "works on my machine" and "works in the OCP
   digital twin" and "works in the actual cluster" are three separate, drifting
   claims. The gist's own framing ("Pixi bridging local dev, Podman digital twins,
   and production OCP") names this directly.

The cost of the status quo: teams either accept the weaker isolation (trusted-code
and untrusted-input-derived-code share one process boundary) or hand-roll a
sandboxing layer per project, with no shared toolchain, no shared observability
convention, and no shared "verify locally the same way CI/prod will" loop.

## The Solution

A layered pipeline, scoped to a single, concrete seed use case first (per the
Dream): a user uploads an Excel file; FastAPI (OIDC-protected) receives it; a
narrow, pure-Python validation stage — compiled via `componentize-py` to a real
WASI Preview 2 component and run under Wasmtime — checks the file's structure and
data quality before anything else touches it; `dlt` then ingests the validated
rows into a DuckDB **Bronze** table; `dbt-duckdb` transforms Bronze → Silver →
Gold with column-level lineage; every stage emits OTel spans and OpenLineage
facets to a Vector sidecar / Marquez, respectively; the whole thing runs identically
under `podman --read-only --user 1001` locally and under OpenShift Restricted SCC
in production, driven by one Pixi toolchain (`pixi run build`, `pixi run test`,
`podman-compose up` for the digital twin).

**[ASSUMPTION] The one deliberate correction to the April 2026 gist, driven by
this brief's research:** the gist's step 2 ("Python-Wasm module validates data
quality via Apache Arrow in-memory buffers") is scoped down. The WASI component
validates using plain Python data structures (rows/dicts, or a pre-parsed scalar
representation) — not Arrow buffers, and not anything touching `numpy`/`pandas`
inside the sandbox — because the research found no working `pyarrow`-in-WASI
precedent anywhere (zero GitHub issues even attempting it) and no Arrow-maintained
WASM/WASI interchange primitive to build on. `dlt`'s ingestion and `dbt-duckdb`'s
transform stay conventional, sandboxed-by-OCP-process (not by Wasm), because
DuckDB's native engine has no WASI build. This is a smaller claim than the gist
made, but a claim this project can actually ship and defend.

## What Makes This Different

| Dimension | Generic OCP-hardened data pipeline | Browser-only Wasm analytics (e.g. plain DuckDB-WASM dashboards) | **Wasm Analytics Stack** |
|---|---|---|---|
| Process-level hardening (Restricted SCC) | ✓ | N/A (client-side) | ✓ |
| A second, code-level sandboxing boundary around untrusted-input-adjacent logic | ✗ | N/A | ✓ (WASI component, scoped to pure-Python validation) |
| Native OTel + OpenLineage, not bolted on | Varies | ✗ | ✓ |
| One toolchain: local dev = digital twin = production | Varies | N/A | ✓ (Pixi + Podman + OCP) |
| Honest about Wasm ecosystem maturity for the data-stack dependencies (DuckDB, dbt, dlt) | N/A | N/A | ✓ (this brief scopes to what's provably buildable, not the full April-2026 gist claim) |

**[ASSUMPTION]** There is no technology moat here in the sense of a novel
algorithm; the differentiation is disciplined scoping — building the part of the
"Python-in-Wasm for data" story that the ecosystem actually supports today (a
narrow validation-layer sandbox, per the domain research's Shopify-Functions/
Fermyon-Spin comparables), instead of over-claiming the part it doesn't (a fully
Wasm-sandboxed DuckDB pipeline). The honest framing is itself the pitch: most
"Wasm-first data stack" narratives in 2026 (including this project's own seed
gist) understate how far C-extension-heavy data libraries lag pure Rust/JS
Wasm-sandboxing use cases — this project is built with that gap named up front,
not discovered in production.

## Who This Serves

**Primary user — the platform/data engineering team inside a regulated or
hardened enterprise running OpenShift.** Needs to let business users (or partner
teams) upload data (starting with Excel) into an analytical pipeline without
widening the trust boundary of the pipeline's own trusted code. Success looks
like: an Excel upload is validated inside a real sandbox boundary before it ever
reaches the ingestion layer, the whole round trip is traced and lineage-tracked
without custom instrumentation work, and the same `pixi run` commands that pass
locally are what CI and the OCP deployment run.

**Secondary user — a security/compliance reviewer auditing the pipeline.** Cares
that "sandboxed" is a verifiable claim, not marketing — per the `pyforge-atlas`
G1 precedent, the right proof shape is a headless-browser (or, here, a
Wasmtime-host) smoke test that asserts the sandbox's claimed isolation
mechanically (e.g. no filesystem/network access beyond what the WIT interface
explicitly grants), not just a design document asserting it.

**Tertiary user — a future Unity Data Stack tenant.** Per the kinship to
`docs/dreams/unity-data-stack.md`, this project is a candidate first
"vertical application" on that platform's shared innersource toolchain — the
Pixi-orchestrated, OCP-hardened pattern this project establishes is meant to be
reusable, not bespoke to the Excel-upload seed use case.

## Success Criteria

**Primary criterion:** the seed use case (Excel upload → validated → DuckDB
Bronze → Silver/Gold via dbt → traced end-to-end) runs correctly, identically,
under `podman --read-only --user 1001` locally and under real OpenShift
Restricted SCC — with the WASI validation component's sandboxing mechanically
verified (not just asserted), the same way `pyforge-atlas` G1's `wasm-smoke` gate
mechanically proves its own no-backend claim.

Supporting criteria:

| Metric | Target | Why this matters |
|---|---|---|
| Excel upload → validated Bronze row, end-to-end | Runs identically local / Podman digital twin / OCP | Proves the one-toolchain claim, not just three separately-tested environments |
| WASI validation sandbox isolation | Mechanically verified via an automated gate (Wasmtime-host smoke test) | An unverified "it's sandboxed" claim is exactly the gap this project exists to close |
| OTel trace + OpenLineage facet coverage | 100% of pipeline stages (API → dlt → dbt) emit both | Native observability is a stated non-negotiable of the Dream |
| Restricted SCC compliance | Zero violations (non-root UID 1001, read-only rootfs) in both digital twin and OCP | The deployment posture is the point of the project, not an afterthought |
| Honesty about scope | Zero shipped claims beyond what the technical research verified as buildable | Directly answers the CLAUDE.md instruction to re-verify spec claims, not propagate the gist's un-re-verified ones |

## Scope

**V1 (this brief's scope) — the seed use case only:**
- FastAPI `POST /upload/excel` (OIDC-protected).
- A `componentize-py`-compiled, pure-Python WASI Preview 2 component validating
  the upload's structure/data quality (no numpy/pandas/pyarrow inside the
  sandbox — see § The Solution).
- `dlt` ingestion of validated rows into DuckDB **Bronze**, run as a
  conventionally-hosted (Restricted-SCC-process-sandboxed, not Wasm-sandboxed)
  stage.
- `dbt-duckdb` transforms Bronze → Silver → Gold with column-level lineage.
- OTel tracing (W3C Trace Context propagated browser → API → pipeline) +
  OpenLineage facets emitted by `dlt` and `dbt` to a Vector sidecar / Marquez.
- One Pixi toolchain: `pixi install`, `pixi run build` (incl. the WASI
  component), `podman-compose up` for the OCP digital twin.
- A mechanical isolation-verification gate for the WASI component (the
  `wasm-smoke`-style proof from `pyforge-atlas` G1, adapted to a server-side
  Wasmtime host rather than a headless browser).

**Explicitly out of V1:**
- Any WASI-sandboxed DuckDB, `dbt`, or `dlt`-DuckDB-destination execution — the
  research shows this is blocked at the DuckDB dependency, not a scoping choice
  to revisit lightly.
- Apache Arrow buffers as the host↔component interchange — plain
  Python/JSON-shaped data only, per the same research finding.
- The full Vizro/Pyodide in-browser dashboard render (deferred in `pyforge-atlas`
  G1 itself as `DW-G1-1`) — V1 read access to Gold tables is out of this brief's
  scope entirely; a future browser-side read surface would reuse G1's pattern
  directly, not reinvent it.
- Multi-source ingestion beyond Excel, multi-tenant Unity Data Stack integration,
  and the dbt Fusion (Rust) engine migration path — all named as V2+/watch items
  below, not committed.

## Vision

**[ASSUMPTION]** If the seed use case ships and the WASI validation boundary
proves both real (mechanically verified) and maintainable (doesn't become a
`componentize-py`-limitations tax the team regrets), this becomes the reference
pattern for "let untrusted input into a hardened OCP pipeline" across every
project in this workspace that needs it — a reusable Wasm-sandboxed validation
primitive, not a one-off. Longer-term, two watch items from the research could
reshape the roadmap materially: (1) if `dbt Fusion` (the Rust rewrite, in Beta as
of this research) gains a DuckDB adapter, the transform layer's own
WASI-portability story changes completely, since Rust compiles to WASI far more
cleanly than CPython; (2) if DuckDB itself ever ships a WASI build (no evidence
found that this is even being discussed upstream today), the entire "Bronze on
DuckDB, sandboxed" claim from the original April 2026 gist becomes buildable as
originally imagined, rather than the narrower V1 this brief scopes. Neither is a
V1 dependency; both are why the architecture stage should keep the DuckDB-facing
layer's interfaces clean enough to swap later without a rewrite.

## Known Risks

- **The WASI-component ecosystem is genuinely ahead of most Python usage today —
  this project would be pushing the frontier, not adopting an established
  pattern.** The domain research found only one of three comparable production
  Wasm-sandboxing deployments (Fermyon Spin) offers Python as a first-class
  option at all; Shopify Functions explicitly recommends Rust over any
  alternative for reliability under load. **Mitigation:** V1 keeps the WASI
  component's Python surface deliberately small (validation logic only, no
  C-extensions) — the exact shape the research shows is actually proven to work
  (`componentize-py`'s SQLite3-in-CPython-WASI and `.abi3.so`-recognition
  progress) rather than the exact shape that isn't (numpy/pandas via the
  unmaintained `wasi-wheels` project).
- **`componentize-py`'s own limitations are real, not hypothetical.** Dynamic
  runtime imports don't work (must resolve at build time); `pydantic` support is
  still an open, unresolved issue as of this research. **Mitigation:** the
  validation component's dependency surface must be audited against this
  constraint during Architecture, not discovered at build time — no `pydantic`
  inside the sandbox until upstream support lands, or hand-roll a plain-dataclass
  validation layer instead.
- **Component Model 1.0 itself is not yet finalized.** WASI 0.3 (native async)
  shipped in June 2026, but the roadmap to a stable 1.0 spec is still in
  progress per the Bytecode Alliance's own public talks. **Mitigation:** pin
  Wasmtime and `componentize-py` versions deliberately (not "latest"), and treat
  a spec-level breaking change as a known, budgeted-for risk during the
  Architecture and build phases, not a surprise.
- **wasi-threads was removed from Wasmtime (47.0.0, 2026-07-20), not merely
  unsupported.** There is no mature multi-threaded execution model inside a WASI
  component today. **Mitigation:** the validation component must be designed as
  single-threaded, async-if-needed (via the new WASI 0.3 primitives) — this
  should be an explicit Architecture-stage constraint, not an implicit
  assumption.
- **The gist this Dream was seeded from is three months stale on exactly the
  claims that matter most.** Its "Apache Arrow buffers across the Wasm boundary"
  step has no supporting implementation anywhere found in this research.
  **Mitigation:** this brief already corrects that claim (§ The Solution); the
  PRD and Architecture stages must not silently re-inherit it from the gist
  without re-reading this brief and its underlying research report first.

## Kill Criteria

**[ASSUMPTION]** Given this project has not yet had a build phase to generate
real usage/dogfooding signal, kill criteria are scoped to the validation-spike
level rather than a shipped-product level: if, during Architecture or an early
build spike, the `componentize-py`-compiled validation component cannot be made
to satisfy the mechanical isolation-verification gate (§ Success Criteria) within
a reasonable spike budget, OR if the WASI component's maintenance burden (working
around `componentize-py`'s import/library limitations) exceeds the value of the
extra sandboxing boundary versus simply running the same validation logic as a
normal, Restricted-SCC-hardened process step, the project should drop the
WASI-sandboxing claim entirely and ship the pipeline as a conventional
OCP-hardened data stack — still valuable (native OTel/OpenLineage + one
toolchain), just without the Wasm differentiation this brief leads with.
