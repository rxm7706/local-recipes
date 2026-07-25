---
id: SPEC-wasm-analytics-stack
surface:
  - apps/api/**                  # FastAPI ingress (not yet created)
  - apps/validate-component/**   # WIT interface + componentize-py WASI component
  - apps/ingest/**                # dlt pipeline -> DuckDB Bronze
  - apps/transform/**             # dbt-duckdb project
  - apps/observability/**         # OTel/OpenLineage/Vector wiring
  - deploy/**                     # security-context, helm, podman-compose
  - pixi.toml
companions:
  - ../../architecture/architecture-wasm-analytics-stack-2026-07-25/ARCHITECTURE-SPINE.md
sources:
  - ../../../../../../docs/dreams/wasm-analytics-stack.md
  - ../../briefs/brief-wasm-analytics-stack-2026-07-25/brief.md
  - ../../prds/prd-wasm-analytics-stack-2026-07-25/prd.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits. This project's planning ran PRD → Architecture only (no epics/stories yet) — a far-horizon effort whose stories decompose fresh when scheduled.

# Wasm Analytics Stack — WASI-sandboxed upload validation, seed use case

## Why

A vision to realize, scoped honestly against what its own research verified as buildable. Enterprises running regulated or hardened OpenShift environments need to let less-trusted logic — a user-uploaded Excel file — into an otherwise locked-down analytical pipeline, but Restricted SCC gives process isolation, not code isolation: the Python process inside a hardened pod still has the full language surface available to anything running inside it, with no second boundary between the pipeline's own trusted code and logic derived from an uploaded file. This project closes that gap for its seed use case — Excel upload → validate → ingest → transform — by compiling the validation step closest to untrusted input into a genuine WASI Preview 2 component, sandboxed under Wasmtime, with the isolation claim mechanically verified rather than merely asserted (the same discipline `pyforge-atlas` story G1 established for its own no-backend claim). The project descends from an April 2026 architecture gist that claimed more than today's ecosystem can deliver; this Spec corrects that claim rather than re-inheriting it, and the honest, narrower scope is itself the differentiator against generic OCP-hardened pipelines that skip the code-level sandboxing question entirely.

## Capabilities

- **CAP-1**
  - **intent:** A business user uploads an `.xlsx` file via an OIDC-authenticated FastAPI endpoint, and its structure and data quality are checked inside a genuine WASI Preview 2 sandbox before any row reaches ingestion, with row-level failures reported precisely and valid rows queued independently of rejected ones.
  - **success:** FR-1–4 hold: an unauthenticated request receives HTTP 401 before the upload body is read; a structurally-invalid file is rejected in full (zero rows reach Bronze); each rejected row's error names the specific column/rule that failed without blocking rows that passed; no row reaches DuckDB Bronze via `dlt` without having passed validation.
- **CAP-2**
  - **intent:** `dbt-duckdb` transforms Bronze into schema-declared Silver and Gold models, emits column-level lineage for every model, and a failing `dbt test` blocks promotion of that model's output to the next layer.
  - **success:** FR-5–7 hold: every `dbt run` is traceable to the Bronze table state it consumed; a lineage query for any Gold column returns its full upstream column chain back to Bronze; a `dbt run` with a failing test does not update the corresponding table and the prior good state remains queryable.
- **CAP-3**
  - **intent:** One W3C trace ID, minted once at the browser/API boundary, correlates OTel spans and OpenLineage facets across every pipeline stage to Marquez via a per-pod Vector sidecar, so a single trace-ID lookup reconstructs the full upload-to-Gold journey with no gaps.
  - **success:** FR-8–11 hold: the trace ID returned to the client at upload time is the same one attached to that upload's eventual Gold-table lineage record; a trace query for any upload returns spans for every stage it passed through with no gap; Marquez returns the full Bronze→Silver→Gold lineage graph; no pipeline container other than the Vector sidecar holds an external telemetry egress path.
- **CAP-4**
  - **intent:** An automated, non-hollow gate mechanically proves the WASI validation component cannot reach any capability beyond its WIT-declared surface, and a build-time check blocks denylisted imports from ever entering the component's dependency closure.
  - **success:** FR-12–13 hold: the gate fails on any host interaction beyond the component's declared WIT imports; deliberately widening the component's declared capabilities without a corresponding WIT change makes the gate fail, proving it checks something rather than always passing; adding a denylisted import (`numpy`, `pandas`, `pyarrow`, `pydantic`, or any other C-extension-backed or `componentize-py`-unproven package) fails `pixi run build`, not a later runtime error.
- **CAP-5**
  - **intent:** One Pixi toolchain builds every artifact the pipeline needs, including the compiled WASI component, and the same security context runs identically under a Podman digital twin and OpenShift Restricted SCC, with DuckDB state persisted via a `ReadWriteOnce` PVC at a consistent mount path.
  - **success:** FR-14–17 hold: a clean checkout plus `pixi install && pixi run build` produces a runnable digital twin with no manual steps outside Pixi; every container starts as non-root UID 1001 with a read-only root filesystem in both the digital twin and OCP; the Helm chart's security context matches Restricted SCC exactly with no `anyuid` or other elevated binding requested; pipeline restarts do not lose previously-ingested Bronze/Silver/Gold data.

## Constraints

- **Maturity verdict (the project's central scoping fact):** DuckDB's native engine has no WASI build and no WASI roadmap upstream, so `dlt`, `dbt-duckdb`, and DuckDB itself cannot run inside a genuine WASI component today. The WASI sandbox is therefore scoped narrowly to the pure-Python upload-validation step only; a future `wasm32-wasi` build target for ingestion or transform requires an ADR amendment citing new upstream evidence, not an incremental extension of this project.
- **AD-1, trust-boundary data shape:** the validation component's WIT interface accepts and returns only primitive/record types (strings, numbers, booleans, lists, records) — never a host-shared-memory or buffer type. No Arrow buffers, no raw Excel bytes cross the WIT boundary; Excel bytes are parsed into rows entirely outside the sandbox, before the WIT call.
- **AD-2, denylist is a build gate:** `pixi run build` runs a static-import-scan against the validation component's source and its resolved dependency closure, failing the build — not merely a policy or PR-review expectation — on any denylisted import, direct or transitive.
- **AD-4, the isolation gate must be non-hollow:** it ships with a meta-test from its first version — deliberately widening the component's declared WIT capabilities without a matching interface change must make the gate fail — and it runs on every build.
- **AD-5, one trace-ID field:** `upload_trace_id` is always the bare 32-hex-character W3C trace-id (never the full `traceparent` string, never a UUID, never dashed), minted once at FastAPI ingress, and is never conflated with OpenLineage's own separately-minted `runId`.
- **AD-6, one securityContext, two consumers:** a single canonical security-context definition is authored once under `deploy/`; the Helm chart and the Podman compose file both consume it via a generation step, neither hand-authors its own copy.
- **AD-7, DuckDB single-writer:** each validated upload triggers exactly one `dlt` load followed by exactly one `dbt run` scoped to that load — 1:1, never batched — both invoked sequentially by the same owning process; a move to concurrent or batched transforms is a scope change requiring an ADR amendment.
- **AD-8, air-gap-routable dependency fetch:** every build-time fetch (Pixi packages, DuckDB extensions, the `componentize-py`/Wasmtime toolchain) routes through the configured channel/mirror; no build script hardcodes a public URL.
- **AD-9, synchronous upload:** `POST /upload/excel` blocks through parsing, WASI validation, and returns the full per-row result in one HTTP response; the returned trace ID is a correlation handle for observability/lineage lookups, not a polling handle — there is no V1 polling endpoint.
- **AD-10, authentication at the ingress boundary:** OIDC token validation happens at a sidecar/gateway boundary in front of `apps/api/`, never embedded per-request inside the application code itself.

## Non-goals

- A general-purpose Wasm-sandboxing framework for arbitrary third-party logic — the WASI boundary in v1 is scoped exclusively to the Excel-upload validation step.
- Running `dlt`, `dbt`, or DuckDB itself inside a WASI Preview 2 sandbox — blocked at the DuckDB-dependency level per the technical research, not a scoping choice to revisit without new upstream evidence.
- Apache Arrow buffers as the host↔WASI-component interchange format — deferred pending a confirmed `pyarrow`-in-WASI path or an Arrow-maintained WASM/WASI interchange primitive.
- A browser-side query/dashboard surface onto Gold tables — v2, would reuse the `pyforge-atlas` G1 DuckDB-WASM/Pyodide pattern directly rather than reinvent it.
- A general ingestion platform for arbitrary source types — Excel upload is the only ingestion path in v1.
- Multi-tenant Unity Data Stack platform integration — a kinship, not a v1 commitment.
- Migration to `dbt Fusion` (the Rust engine) — blocked until it gains a DuckDB adapter; a watch item, not scheduled.

## Success signal

The seed use case — Excel upload → WASI-validated → DuckDB Bronze → Silver/Gold via `dbt`, traced end-to-end — runs correctly and identically under `podman --read-only --user 1001` locally and under real OpenShift Restricted SCC, with the WASI validation component's sandboxing mechanically verified, not just asserted (SM-1). The Isolation-Verification Gate passes on every build and demonstrably fails when the component's declared capability surface is deliberately widened without a corresponding WIT change — the non-hollow-gate proof (SM-2). The project ships zero claims beyond what the technical research verified as buildable today. Two counter-metrics guard against gaming the primary signals: growing workaround complexity in the denylist (SM-C1) is a signal to reconsider the WASI-sandboxing bet, not a target to minimize by weakening the boundary; and upload-validation latency must never be optimized by moving checks out of the sandbox back into the trusted process (SM-C2), which would defeat CAP-1's entire purpose.

## Assumptions

- Python 3.12 is chosen as a conservative stability floor for host/pipeline processes, even though nothing in the pinned dependency set (`dlt`/`dbt-core`/`dbt-duckdb`/`duckdb` all support through 3.14) forces it — revisitable.
- Marquez's actual deployed image/version needs re-verification at implementation time; its last GitHub release tag (0.50.0, 2024-10-24) is stale relative to active repo development, and Marquez ships primarily via Docker/Maven rather than GitHub release tags.
- No cost ceiling, no air-gap-routing detail beyond the general `enterprise-airgap` posture, and no SLA/RTO/RPO commitment is stated in the founding Dream or brief; none should be assumed by downstream work until resolved.

## Open Questions

- **Upload size / latency budget:** exact maximum upload file size and the expected weekly row-count/latency budget for the "within seconds" claim — needed before Architecture can size the validation component's performance envelope; a large-enough file may force revisiting the synchronous-upload design (AD-9) via ADR amendment.
- **Named regulatory framework:** which specific framework(s), if any, this deployment must satisfy beyond Restricted SCC + OIDC (HIPAA, PCI-DSS, SOX, none) — a named framework would likely add audit-log retention and encryption-at-rest requirements not yet captured.
- **`componentize-py` rule-configuration redesign:** does the build-time-only import restriction force a redesign of the validation component's rule-configuration mechanism, if rules were meant to be dynamically loaded per file-type?
- **Operational ownership:** who is on-call for this pipeline in production, and what SLA (if any) applies to validation/ingestion latency — needed before Architecture commits to a specific deployment topology.
- **Data classification and retention:** no scheme (PII, confidential) is defined for Bronze/Silver/Gold or Marquez's lineage history; if the seed use case's actual data (headcount/cost) carries PII, this adds retention/access-control requirements not currently specified.
