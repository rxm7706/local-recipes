---
title: Wasm Analytics Stack
created: 2026-07-25
updated: 2026-08-04
status: final
currency_review: Reviewed 2026-08-04 — spec/brief timestamp bump was structural (project relocation / memlog story-completion recording), not content drift; PRD unchanged.
---

# PRD: Wasm Analytics Stack
*Working title — confirm.*

## 0. Document Purpose

This PRD is written for the Architecture stage that follows it directly (this
chain runs PRD → Architecture only; no epics/stories decomposition yet — this is
a far-horizon project whose stories will be decomposed fresh when scheduled), and
for any human reviewer deciding whether to schedule the build. It is structured
around a single, concrete seed use case (defined in `## 2 Target User` and
realized end-to-end in `## 4 Features`), not a general-purpose platform vision —
the brief this PRD builds on (`../../briefs/brief-wasm-analytics-stack-2026-07-25/brief.md`)
already made that scoping call explicit, and this PRD does not re-litigate it.
This PRD also builds directly on two research reports produced alongside the
brief — `../../research/technical-python-in-wasm-analytics-research-2026-07-25.md`
(the Python-in-WASM maturity verdict) and
`../../research/domain-sandboxed-analytics-deployments-research-2026-07-25.md`
(comparable production Wasm-sandboxing deployments) — both of which this PRD
treats as load-bearing, not background reading: several FRs below are scoped the
way they are *because* the research shows the alternative is not currently
buildable.

## 1. Vision

Wasm Analytics Stack lets a regulated or hardened enterprise accept
user-uploaded data into an analytical pipeline without widening the trust
boundary of the pipeline's own code. A user uploads an Excel file; before that
file's contents touch anything else, a purpose-built validation step — compiled
to a genuine WASI Preview 2 component and run under Wasmtime, not just another
function in the same trusted process — checks it. Only validated rows ever reach
`dlt` ingestion, DuckDB Bronze, and the `dbt-duckdb` Silver/Gold transforms. Every
stage of that journey, from the browser to the Gold table, carries a live OTel
trace and an OpenLineage provenance record, natively, not bolted on after the
fact. And the whole thing — API, WASI component, ingestion, transformation — runs
through exactly one toolchain (Pixi) and is provably identical whether it's
running on a laptop, inside a `podman --read-only --user 1001` digital twin, or
inside a real OpenShift cluster under Restricted SCC.

What makes this worth building now, rather than as a plain OCP-hardened pipeline
with no Wasm layer at all: the sandboxing claim is mechanically verifiable, not
aspirational. The project's own research (§ Risk and Mitigations) is explicit that
most of the WASI-component ecosystem is not yet ready for C-extension-heavy data
libraries — so this PRD does not claim a fully Wasm-sandboxed DuckDB pipeline.
It claims a narrower, provably-true thing: the one place untrusted input first
touches the system is sandboxed at the code level, verified by an automated gate,
and everything downstream of that point runs on an already-hardened, already
well-understood OCP process boundary. That is a smaller claim than the April 2026
architecture gist this project descends from made — and, per the research, the
larger claim is not buildable with today's ecosystem.

## 2. Target User

### 2.1 Jobs To Be Done

- **As a platform/data engineer at a regulated enterprise**, I need to let
  business users upload data into an analytical pipeline without giving
  uploaded-file-derived logic the same trust level as the pipeline's own code.
- **As the same engineer**, I need one command sequence that behaves identically
  whether I run it on my laptop, in a Podman digital twin, or in the real OCP
  cluster — so "works in dev" and "works in prod" are the same claim, verified
  the same way.
- **As a security/compliance reviewer**, I need the pipeline's sandboxing claim
  to be something I can point an automated gate at, not something I have to take
  on the architecture document's word.
- **As a data consumer** (an analyst querying Gold tables, out of this PRD's V1
  scope but a stated future user), I need to trust that what reached Gold passed
  through a validated, traceable, lineage-recorded path.

### 2.2 Non-Users (v1)

- End users who need a query/dashboard interface onto Gold tables — V1 ships no
  read surface at all (see § 6.2 Out of Scope); this is an ingestion+transform
  pipeline, not yet an analytics product a business user opens directly.
- Teams whose source data is not file-upload-shaped (streaming sources, API
  pulls, database CDC) — V1's WASI validation boundary is scoped to the
  file-upload trust-boundary problem specifically.
- Teams on Kubernetes distributions other than OpenShift, or without a
  Restricted-SCC-equivalent hardening requirement — the value proposition is
  specific to that posture; a generic K8s deployment would carry the WASI
  sandboxing cost without the OCP-hardening context that motivates it.

### 2.3 Key User Journeys

- **UJ-1. Marcus uploads a weekly Excel report and finds out, in seconds, that
  three rows are malformed — before anything downstream ever sees them.**
  - **Persona + context:** Marcus, a business analyst at a regulated
    financial-services company, produces a weekly headcount-and-cost Excel
    report by hand and needs it in the shared analytical warehouse without
    filing a ticket with the platform team.
  - **Entry state:** authenticated via the enterprise OIDC provider (OpenShift
    identity), browser session, no prior interaction with this pipeline today.
  - **Path:** Marcus opens the upload page, selects `headcount-2026-w30.xlsx`,
    and submits. The FastAPI endpoint accepts the file and hands it to the
    WASI-sandboxed validation component. The component checks structure
    (expected columns present, types coherent) and data quality (no
    negative headcounts, no duplicate department keys) — entirely inside its
    own sandboxed boundary, with no filesystem or network access beyond what
    its WIT interface explicitly grants.
  - **Climax:** three rows fail validation (a department key typo, a negative
    cost value). Marcus sees a precise, row-level error message within seconds —
    the file was never partially ingested, and the 47 valid rows are queued
    separately from the 3 rejected ones pending his fix.
  - **Resolution:** Marcus corrects the three rows in Excel and re-uploads; this
    time all 50 rows pass, and `dlt` ingests them into DuckDB Bronze. Marcus
    never sees or cares that any of this happened inside a Wasm sandbox — from
    his side it's just "the upload told me exactly what was wrong."
  - **Edge case:** if the uploaded file isn't valid `.xlsx` at all (corrupted,
    wrong format), the WASI component rejects it before `dlt` or DuckDB are ever
    invoked — the failure is contained at the validation boundary, not
    discovered three stages downstream.

- **UJ-2. Elena verifies a new build behaves identically in her laptop's digital
  twin and in the OCP cluster, then traces one Bronze row all the way to Gold.**
  - **Persona + context:** Elena, a platform engineer, is validating a pipeline
    change before it ships to the regulated-enterprise OCP cluster she's
    responsible for.
  - **Entry state:** local checkout, Pixi installed, no cluster access needed
    for the first half of this journey.
  - **Path:** Elena runs `pixi run build` (compiles the WASI validation
    component alongside the rest of the stack), then `podman-compose up` to
    bring up the digital twin under `--read-only --user 1001` — the same
    security context Restricted SCC enforces in OCP. She re-runs UJ-1's upload
    scenario against the digital twin and confirms identical behavior. Satisfied,
    she deploys the same artifact to the OCP cluster via the GitOps pipeline.
  - **Climax:** in the OCP cluster, she pulls up Marquez and searches for
    Marcus's `headcount-2026-w30.xlsx` upload by trace ID (captured from the
    original OTel span at the FastAPI boundary). She sees the full lineage:
    upload → validation (pass) → Bronze row → Silver transform → Gold table,
    each hop timestamped and column-level-attributed.
  - **Resolution:** Elena has verified, without guessing, that dev/twin/prod
    parity holds and that the lineage claim is real, not documented-but-untested.
  - **Edge case:** if the digital twin and the OCP cluster ever disagree (e.g. a
    dependency resolves differently), that disagreement is itself the signal
    the one-toolchain claim exists to prevent — Elena's workflow should make
    such drift visible immediately, not silently.

## 3. Glossary

- **WASI Preview 2 component** — a WebAssembly module compiled against the WASI
  0.2/0.3 component-model spec, with an explicit WIT-defined interface
  (capabilities) rather than ambient system access. This project's validation
  logic is one.
- **Wasmtime** — the Bytecode Alliance's WASI-component host runtime; hosts the
  validation component both in the digital twin and in OCP.
- **componentize-py** — the Bytecode Alliance tool that compiles a Python
  application into a WASI Preview 2 component. Per the technical research, its
  Python surface is restricted: no dynamic runtime imports, and C-extension
  support is real but shallow (works for SQLite3, `.abi3.so`-recognized native
  extensions in some cases; does not work for numpy/pandas/pyarrow without an
  unmaintained community wheel-build project this PRD does not depend on).
- **Isolation-Verification Gate** — this project's mechanical proof (an
  automated Wasmtime-host smoke test) that the validation component's sandbox
  boundary holds — the pattern is adapted from `pyforge-atlas` story G1's
  `wasm-smoke` gate, which proved a browser-hosted Wasm artifact made zero
  non-loopback network requests.
- **Digital twin** — the local/CI verification environment: the same container
  images and security context (`podman --read-only --user 1001`) as the OCP
  deployment, run outside a real cluster.
- **Restricted SCC** — OpenShift's Restricted Security Context Constraint:
  non-root UID 1001, read-only root filesystem, no privilege escalation. The
  hard deployment constraint for every container in this project, WASI-sandboxed
  or not.
- **Bronze / Silver / Gold** — the medallion data-layering convention: Bronze is
  raw-but-validated ingested data (DuckDB table, written by `dlt`), Silver is
  cleaned/conformed, Gold is business-ready/aggregated (both written by
  `dbt-duckdb`).
- **`dlt` (data load tool)** — the Python ingestion library moving validated rows
  from the FastAPI upload path into DuckDB Bronze. Runs as a conventional,
  Restricted-SCC-hardened process — not a WASI component (§ Risk and
  Mitigations explains why).
- **`dbt-duckdb`** — the `dbt` adapter targeting DuckDB, running the
  Bronze→Silver→Gold SQL transformations. Also a conventional process, not a
  WASI component, for the same DuckDB-dependency reason as `dlt`.
- **OTel span** — a single traced operation (an OpenTelemetry unit of work),
  emitted at each pipeline stage and correlated by a shared trace ID originating
  at the browser (W3C Trace Context).
- **OpenLineage facet** — a structured provenance record (who/what/when
  transformed which columns) emitted by `dlt` and `dbt` to Marquez.
- **Marquez** — the OpenLineage-compatible metadata/lineage service this project
  emits facets to and queries lineage from (UJ-2).
- **Vector sidecar** — the per-pod telemetry-forwarding sidecar aggregating OTel
  spans before they leave the pod.
- **WIT interface** — the WebAssembly Interface Type definition declaring
  exactly what a WASI component may import/export; the validation component's
  entire capability surface is enumerated here, nothing implicit.

## 4. Features

### 4.1 Authenticated Upload & WASI-Sandboxed Validation

**Description:** The system's entire trust-boundary-crossing surface for V1.
A business user (Marcus, UJ-1) authenticates via the enterprise OIDC provider,
uploads an Excel file to a FastAPI endpoint, and the file's bytes are handed to
a `componentize-py`-compiled WASI Preview 2 component running under Wasmtime —
not to any code sharing a trust boundary with the rest of the pipeline. The
component's WIT interface grants it exactly the capability to receive bytes and
return a structured validation result; nothing else. `[ASSUMPTION]` The
component receives a pre-parsed, plain-Python-object representation of the
spreadsheet (rows as dicts/lists of scalars) rather than raw Excel bytes or an
Arrow buffer — per the technical research, there is no confirmed
`pyarrow`-in-WASI path and no Arrow-maintained WASM/WASI interchange primitive,
so the parsing step (turning `.xlsx` bytes into rows) happens in conventional,
non-sandboxed code immediately before the WASI boundary, and only the
structural/data-quality *checks themselves* run inside the sandbox.

**Functional Requirements:**

#### FR-1: Authenticated Excel Upload

A business user can upload an `.xlsx` file via `POST /upload/excel` after
authenticating through the enterprise OIDC/OAuth2 provider. Realizes UJ-1.

**Consequences (testable):**
- Unauthenticated requests receive HTTP 401 before the upload body is read.
- A successfully authenticated upload returns a tracking/trace ID the client can
  use to poll validation status.
- The endpoint enforces a maximum file size (`[ASSUMPTION]` exact limit is an
  open question — see § 8).

#### FR-2: WASI-Sandboxed Structural & Data-Quality Validation

The system validates every uploaded file's structure (expected columns present,
types coherent) and data quality (domain-specific rules, e.g. no negative
values in numeric fields expected to be non-negative) inside a WASI Preview 2
component, before any row reaches `dlt` or DuckDB. Realizes UJ-1.

**Consequences (testable):**
- The validation component's WIT interface declares no filesystem or network
  import beyond what's explicitly required for the check itself (ideally none).
- A file that fails structural validation (wrong columns, unreadable as tabular
  data) is rejected in full — zero rows reach Bronze.
- A file that passes structural validation but fails row-level data-quality
  checks reports failures per-row, without blocking the rows that did pass
  (partial acceptance, per UJ-1's resolution beat).
- The validation component's Python dependency surface contains no
  `numpy`/`pandas`/`pyarrow`/`pydantic` import — enforced at build time (FR-13).

**Out of Scope:**
- Semantic/business-rule validation beyond structural + declared data-quality
  rules (e.g. cross-referencing an uploaded headcount against an external HR
  system) — V1's validation is self-contained to the file's own contents.

#### FR-3: Validation Failure Handling & Surfacing

A user whose upload contains invalid rows receives a precise, row-level error
report and can resubmit corrected data without re-uploading valid rows twice.
Realizes UJ-1.

**Consequences (testable):**
- Each rejected row's error message names the specific column/rule that failed.
- Valid rows from a partially-failing upload are queued for ingestion (FR-4)
  independently of the rejected rows' resolution.

#### FR-4: Validated-Row Ingestion to DuckDB Bronze

Rows that pass validation are ingested into a DuckDB Bronze table via `dlt`,
running as a conventional Restricted-SCC-hardened process (not a WASI
component — see § Risk and Mitigations for why). Realizes UJ-1.

**Consequences (testable):**
- No row reaches Bronze without having passed FR-2's validation.
- `dlt`'s schema inference records the Bronze table schema derived from the
  validated rows, available for the transformation stage (FR-5).

**Feature-specific NFRs:**
- Validation latency: the WASI component's check must complete within a bound
  tight enough that UJ-1's "within seconds" claim holds for a
  realistically-sized weekly report (`[ASSUMPTION]` exact row-count/latency
  target is an open question — see § 8).

### 4.2 Bronze → Silver → Gold Transformation

**Description:** Once validated data lands in Bronze, `dbt-duckdb` transforms it
through Silver (cleaned/conformed) to Gold (business-ready), with every
transformation's column-level lineage captured, not just the transformation's
success/failure. This feature is entirely conventional-process-hosted (not
Wasm-sandboxed) per the technical research's finding that DuckDB has no WASI
build.

**Functional Requirements:**

#### FR-5: `dbt-duckdb` Transformation Pipeline

The system runs a `dbt-duckdb` project transforming Bronze tables into Silver
and Gold layers on a defined schedule/trigger. Realizes UJ-2.

**Consequences (testable):**
- Every `dbt run` invocation is traceable to the Bronze table state (and,
  transitively, the upload event) it consumed.
- Silver/Gold table schemas are declared in the `dbt` project, not inferred
  ad hoc.

#### FR-6: Column-Level Lineage Emission

Every `dbt` model emits column-level lineage (which Silver/Gold columns derive
from which Bronze columns, through which transformation) as an OpenLineage
facet. Realizes UJ-2.

**Consequences (testable):**
- A lineage query for any Gold column returns its full upstream column chain
  back to the originating Bronze column.

#### FR-7: `dbt test` Quality Gate

Every transformation run is gated by `dbt test` — schema and data-quality tests
declared per model — and a failing test blocks promotion of that model's output
to the next layer.

**Consequences (testable):**
- A `dbt run` with a failing test does not update the corresponding Silver/Gold
  table; the prior good state remains queryable.

### 4.3 End-to-End Observability & Provenance

**Description:** OTel tracing and OpenLineage provenance are native to every
stage, correlated by one trace ID originating at the browser, so a single
lookup (UJ-2) reconstructs the full journey of any row from upload to Gold.

**Functional Requirements:**

#### FR-8: W3C Trace Context Propagation

A W3C Trace Context originating in the browser upload request is propagated
through the FastAPI endpoint, the WASI validation component invocation, `dlt`
ingestion, and every `dbt` model run touching that data. Realizes UJ-2.

**Consequences (testable):**
- The trace ID returned to the client at upload time (FR-1) is the same trace
  ID attached to that upload's eventual Gold-table lineage record.

#### FR-9: OTel Span Emission at Every Stage

Each pipeline stage (API request, validation, ingestion, each `dbt` model run)
emits its own OTel span, tagged with the shared trace ID, to a per-pod Vector
sidecar.

**Consequences (testable):**
- A trace query for any upload's trace ID returns spans for every stage the
  upload passed through, with no gap in the chain.

#### FR-10: OpenLineage Facet Emission to Marquez

`dlt` and `dbt` emit OpenLineage facets (dataset-level and column-level) to
Marquez on every run. Realizes UJ-2.

**Consequences (testable):**
- Marquez's UI/API returns the full Bronze→Silver→Gold lineage graph for any
  ingested dataset.

#### FR-11: Vector Sidecar Telemetry Aggregation

A Vector sidecar aggregates OTel spans within each pod before forwarding
externally, so no pipeline component needs its own direct external telemetry
egress.

**Consequences (testable):**
- No pipeline container process other than the Vector sidecar holds an
  external network egress path for telemetry.

### 4.4 Mechanically-Verified WASI Sandbox Isolation

**Description:** The project's core differentiating claim — that the validation
component is genuinely sandboxed — is proven by an automated gate, not asserted
by a design document. This directly answers the domain research's finding that
comparable production Wasm-sandboxing deployments treat this as a first-class
concern, and mirrors the `pyforge-atlas` G1 precedent of a mechanical,
gate-enforced isolation proof.

**Functional Requirements:**

#### FR-12: Isolation-Verification Gate

An automated gate runs the compiled validation component under a Wasmtime host
configured with only the WIT-declared capabilities and asserts no capability
beyond that declared set is reachable (e.g. no filesystem write, no network
egress, if none are declared). Realizes UJ-2 (the compliance-reviewer JTBD in
§ 2.1).

**Consequences (testable):**
- The gate fails if the component attempts any host interaction beyond its
  declared WIT imports.
- The gate is non-hollow: deliberately widening the component's declared
  capabilities without a corresponding WIT change causes the gate to fail (the
  gate must prove it's checking something, not always passing).

#### FR-13: WASI Component Dependency Audit

A build-time check enforces that the validation component's Python source
imports nothing from a denylist (`numpy`, `pandas`, `pyarrow`, `pydantic`, any
other C-extension-backed or `componentize-py`-unproven package), failing the
build if violated.

**Consequences (testable):**
- Adding a denylisted import to the validation component's source fails
  `pixi run build`, not just a later runtime error.

### 4.5 One Toolchain: Local Dev, Digital Twin, Production OCP

**Description:** Pixi orchestrates every build/verify/deploy step; the same
commands run identically on a laptop, in the Podman digital twin, and (via
GitOps) in the OpenShift cluster — the parity UJ-2 exercises directly.

**Functional Requirements:**

#### FR-14: Pixi-Orchestrated Build

`pixi install` and `pixi run build` produce every artifact the pipeline needs,
including the compiled WASI validation component, from a single toolchain
definition. Realizes UJ-2.

**Consequences (testable):**
- A clean checkout, `pixi install && pixi run build`, produces a runnable
  digital twin with no manual steps outside Pixi.

#### FR-15: Podman Digital-Twin Parity

`podman-compose up` brings up the full pipeline locally under
`--read-only --user 1001` — the same security context OCP Restricted SCC
enforces — so a failure under Restricted SCC is caught before deployment, not
after. Realizes UJ-2.

**Consequences (testable):**
- Every container in the digital twin starts successfully as non-root UID 1001
  with a read-only root filesystem; any component that requires writable
  storage does so only via an explicitly mounted volume, never the rootfs.

#### FR-16: OpenShift Restricted SCC Compliant Deployment

The production deployment (via GitOps/Helm) runs under OpenShift's Restricted
SCC with no exceptions requested.

**Consequences (testable):**
- The Helm chart's pod security context matches Restricted SCC's requirements
  exactly (non-root UID 1001, `readOnlyRootFilesystem: true`, no privilege
  escalation) — no `anyuid` or other elevated SCC binding required.

#### FR-17: Persistent Storage via ReadWriteOnce PVC

DuckDB's on-disk state (Bronze/Silver/Gold) is backed by a `ReadWriteOnce` PVC
mounted at a defined path, consistent between the digital twin and OCP.

**Consequences (testable):**
- Pipeline restarts do not lose previously-ingested Bronze/Silver/Gold data;
  state survives pod recreation as long as the PVC persists.

## 5. Non-Goals (Explicit)

- This project does not build a general-purpose Wasm-sandboxing framework for
  arbitrary third-party logic — the WASI component boundary in V1 is scoped
  exclusively to the Excel-upload validation step.
- This project does not attempt to run `dlt`, `dbt`, or DuckDB itself inside a
  WASI Preview 2 sandbox — the technical research found this blocked at the
  DuckDB-dependency level, not a scoping choice to revisit without new upstream
  evidence.
- This project does not ship a browser-side query/dashboard surface in V1 (that
  would reuse the `pyforge-atlas` G1 DuckDB-WASM/Pyodide pattern directly rather
  than reinvent it, per the brief's Vision section, but is explicitly out of
  this PRD).
- This project does not become a general ingestion platform supporting arbitrary
  source types in V1 — Excel upload is the only ingestion path.

## 6. MVP Scope

### 6.1 In Scope

- FastAPI upload endpoint with OIDC authentication (FR-1).
- `componentize-py`-compiled WASI Preview 2 validation component with a
  mechanically-verified isolation gate (FR-2, FR-3, FR-12, FR-13).
- `dlt` ingestion to DuckDB Bronze (FR-4).
- `dbt-duckdb` Bronze→Silver→Gold with column-level lineage and `dbt test`
  gating (FR-5, FR-6, FR-7).
- End-to-end OTel tracing + OpenLineage provenance to Marquez via a Vector
  sidecar (FR-8 through FR-11).
- One Pixi toolchain spanning local dev, Podman digital twin, and OCP
  deployment, with Restricted SCC compliance in both the digital twin and
  production (FR-14 through FR-17).

### 6.2 Out of Scope for MVP

- Any WASI-sandboxed execution of `dlt`, `dbt`, or DuckDB — deferred
  indefinitely pending upstream WASI support for DuckDB's native engine (not a
  near-term v2 item; see § Risk and Mitigations).
- Apache Arrow buffers as the host↔WASI-component interchange format —
  deferred pending a confirmed `pyarrow`-in-WASI path or an Arrow-maintained
  WASM/WASI interchange primitive.
- A browser-side dashboard/read surface onto Gold tables — v2, would follow the
  `pyforge-atlas` G1 DuckDB-WASM/Pyodide pattern. `[NOTE FOR PM]` this is the
  most natural v2 candidate and should be revisited once V1's ingestion path is
  stable, since G1 already de-risked most of the technical approach.
- Multi-source ingestion beyond Excel (streaming, API pull, CDC) — v2+.
- Multi-tenant Unity Data Stack platform integration — v2+, tracked as a
  kinship, not a commitment.
- Migration to `dbt Fusion` (the Rust engine) — blocked until it gains a DuckDB
  adapter; tracked as a watch item, not scheduled.

## 7. Success Metrics

**Primary**
- **SM-1**: The seed use case (Excel upload → WASI-validated → DuckDB Bronze →
  Silver/Gold via `dbt`) completes successfully, with identical behavior, in
  all three environments (laptop, Podman digital twin, OCP cluster). Validates
  FR-1 through FR-17.
- **SM-2**: The Isolation-Verification Gate (FR-12) passes on every build and
  demonstrably fails when the validation component's declared capability
  surface is deliberately widened without a corresponding WIT change (the
  non-hollow-gate test). Validates FR-12, FR-13.

**Secondary**
- **SM-3**: 100% of pipeline stages (API, validation, ingestion, each `dbt`
  model run) emit a correlated OTel span and, where applicable, an OpenLineage
  facet — verified by a single trace-ID lookup returning the full chain with no
  gaps. Validates FR-8 through FR-11.
- **SM-4**: Zero Restricted SCC exceptions requested in the production Helm
  deployment. Validates FR-16.

**Counter-metrics (do not optimize)**
- **SM-C1**: Validation-component build complexity (lines of workaround code
  needed to satisfy `componentize-py`'s import/dependency constraints) should
  not be optimized away by simply widening the denylist (FR-13) to let more
  through — a growing denylist-workaround footprint is a signal to reconsider
  the WASI-sandboxing bet (§ Kill Criteria in the brief), not a target to
  minimize by weakening the boundary. Counterbalances SM-1/SM-2.
- **SM-C2**: Upload-validation latency should not be optimized by moving checks
  out of the WASI sandbox back into the trusted process — that would satisfy a
  speed metric while quietly defeating FR-2's entire purpose. Counterbalances
  SM-1.

## 8. Open Questions

1. Exact maximum upload file size and expected weekly row-count/latency budget
   for FR-1/FR-2's "within seconds" claim (UJ-1) — needs a concrete number
   before Architecture can size the validation component's performance budget.
2. Which specific regulatory framework(s), if any, this deployment must satisfy
   beyond "Restricted SCC + OIDC" (HIPAA, PCI-DSS, SOX, none) — the Dream and
   gist name the posture generically ("regulated enterprise") without a named
   framework; § Compliance and Regulatory below is written generically pending
   this answer.
3. Whether `componentize-py`'s runtime-import restriction (all imports must
   resolve at build time — technical research § 2) forces any redesign of the
   validation component's rule-configuration mechanism (e.g. if validation
   rules were meant to be dynamically loaded per file-type, that pattern may
   not work as-is).
4. Operational ownership: who is on-call for this pipeline in production, and
   what SLA (if any) applies to validation/ingestion latency — not addressed in
   the Dream or brief; needed before Architecture commits to a specific
   deployment topology (§ Operational Requirements is intentionally thin
   pending this).
5. Whether the WASI Isolation-Verification Gate (FR-12) needs to run on every
   CI build or only on validation-component-touching changes — an
   Architecture/CI-design question, not a product one, but affects the build
   pipeline's shape.

## 9. Assumptions Index

- § 4.1 — the validation component receives pre-parsed plain-Python data
  (rows as dicts/scalars), not raw Excel bytes or an Arrow buffer, because no
  confirmed `pyarrow`-in-WASI or Arrow-WASM-interchange path exists.
- § 4.1 FR-1 — exact max upload file size is unset pending § 8 Q1.
- § 4.1 FR-2 (feature-specific NFR) — exact validation-latency target is unset
  pending § 8 Q1.

---

## Cross-Cutting NFRs

- **Security.** Every container non-root UID 1001, read-only rootfs (Restricted
  SCC, FR-16). The WASI validation component's capability surface is
  WIT-declared and mechanically checked (FR-12) — no ambient filesystem/network
  access. OIDC authentication gates the only external-input entry point
  (FR-1). No pipeline component other than the Vector sidecar holds external
  telemetry egress (FR-11).
- **Portability / Air-gap compatibility.** `[ASSUMPTION]` Per this repo's
  established `enterprise-airgap` posture (kinship named in the Dream), the
  stack's dependencies (Pixi packages, the DuckDB Parquet-extension-style
  vendoring pattern `pyforge-atlas` G1 already established) should be
  air-gap-routable through an internal mirror/Artifactory, not hardcoded to
  reach the public internet at build or run time. Architecture should treat
  this as a hard constraint on dependency-fetch design, not an afterthought.
- **Reliability.** Digital-twin/production parity (FR-15) exists specifically
  so that a Restricted-SCC-incompatible change is caught locally, not in
  production.
- **Observability.** 100% span/facet coverage is itself an NFR restated as
  SM-3 — not aspirational, gate-checked.

## Constraints and Guardrails

- **Safety (sandbox boundary).** The WASI component's WIT interface is the
  single source of truth for what the validation logic can touch — any
  capability not explicitly declared there must not be reachable, enforced by
  FR-12's gate.
- **Dependency guardrail.** FR-13's denylist (no `numpy`/`pandas`/`pyarrow`/
  `pydantic` inside the WASI component) is a hard guardrail, not a style
  preference — per the technical research, violating it means shipping a
  component that either fails to build under `componentize-py` or depends on
  the unmaintained `dicej/wasi-wheels` project this PRD explicitly does not
  rely on.
- **Cost.** `[ASSUMPTION]` No cost ceiling was stated in the Dream or brief;
  Fermyon Spin's cited production case (batch order processing, 60% compute
  cost reduction — domain research § 1) is weak positive evidence Wasm
  sandboxing is not inherently a cost tax, but no cost budget is set here.

## Risk and Mitigations

*(carried forward from the brief's Known Risks section, restated against this
PRD's FRs)*

| Risk | Mitigation | Related FRs |
|---|---|---|
| The WASI-component ecosystem is ahead of typical Python production usage — this project pushes the frontier, per the domain research (only 1 of 3 comparable deployments offers Python as first-class). | Keep the WASI component's Python surface deliberately narrow (validation logic only, denylist-enforced). | FR-2, FR-13 |
| `componentize-py`'s own limitations are real: no dynamic runtime imports, `pydantic` support still open/unresolved upstream. | Audit the validation component's dependency surface at Architecture time, not discovered at build time; no `pydantic` inside the sandbox. | FR-13, § 8 Q3 |
| Component Model 1.0 itself is not yet finalized (WASI 0.3 shipped June 2026; 1.0 still roadmap). | Pin Wasmtime and `componentize-py` versions deliberately; treat a future spec-breaking change as a budgeted risk. | FR-14 |
| `wasi-threads` was removed from Wasmtime (47.0.0, 2026-07-20) — no mature multi-threaded execution model inside a WASI component today. | Design the validation component single-threaded, async-if-needed via WASI 0.3 primitives. | FR-2 |
| The April 2026 source gist's "Arrow buffers across the Wasm boundary" claim has no supporting implementation found anywhere. | This PRD does not repeat that claim — FR-2 is scoped to plain-Python-object validation. | FR-2 |

## Integration and Dependencies

- **Enterprise OIDC/identity provider** — FR-1's authentication path; specific
  provider (Keycloak, Red Hat SSO, other) not yet named — Architecture
  decision.
- **Marquez** — the OpenLineage-compatible lineage service FR-10 emits to; this
  PRD assumes it is deployed alongside the pipeline, not a pre-existing
  enterprise service — Architecture should confirm.
- **Vector** — the telemetry sidecar (FR-11); assumed deployed per-pod.
- **`pyforge-atlas` (kinship, not a dependency)** — this PRD's Isolation-
  Verification Gate (FR-12) and future v2 dashboard both directly reuse
  patterns G1 already shipped; no code dependency in V1, but architecture
  should consult G1's implementation, not re-derive its gate design from
  scratch.
- **Unity Data Stack (kinship, future)** — the innersource platform this
  project could eventually run on top of; no integration in V1.

## Data Governance

- **Layering as classification boundary.** Bronze holds validated-but-raw data;
  Silver/Gold hold conformed/business-ready data. `[ASSUMPTION]` No explicit
  data-classification (PII, confidential, etc.) scheme is defined in the Dream
  or brief — Architecture should treat this as an open question if the seed
  use case's actual data (headcount/cost, per UJ-1) turns out to carry PII,
  which would add retention/access-control requirements not currently
  specified.
- **Lineage retention.** OpenLineage facets accumulate in Marquez
  indefinitely by default; a retention policy is not specified — open question
  for Architecture/Ops.
- **Storage retention.** Bronze/Silver/Gold data persists on the PVC (FR-17)
  until explicitly purged; no retention/deletion policy specified in this PRD.

## Compliance and Regulatory

`[ASSUMPTION]` No specific named regulatory framework (HIPAA, PCI-DSS, SOX,
GDPR) is stated in the Dream, gist, or brief — the posture is described
generically as "regulated enterprise" / "hardened enterprise." This PRD treats
Restricted SCC compliance (FR-16) and OIDC-gated access (FR-1) as the concrete,
verifiable compliance baseline, and defers naming a specific framework to
§ 8 Q2. If a specific framework is named later, it will likely add requirements
(audit-log retention, specific encryption-at-rest guarantees) not yet captured
here.

## Operational Requirements

`[ASSUMPTION]` Not addressed in the Dream or brief and left intentionally thin
pending § 8 Q4 (operational ownership/SLA). No SLA, RTO/RPO, or support-tier
commitment is made in this PRD. Architecture should not assume a specific
uptime target without this being resolved first.
