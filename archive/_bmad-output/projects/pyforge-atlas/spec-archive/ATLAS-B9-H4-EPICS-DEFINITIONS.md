# pyforge-atlas — B9–H4 story definitions (epics.md, verbatim)

> The 20 stories from Waves B9→H4 that were **never** emitted as individual
> story files (those waves ran through the in-session agent loop, not
> `bmad-create-story`). This is their authoritative Tier-2 spec content,
> extracted **verbatim** from
> `_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md`, plus the
> matching `deferred-work.md` (DW-*) ledger entries. No fabrication — every line
> below is copied from a real planning artifact.
>
> Generated: 2026-07-25. For the full-detail B1–B8 story files see
> `ATLAS-BMAD-SPECS-CONSOLIDATED.md`.

---

## Story B9

### Story B9 (3.9): Release-to-availability velocity columns

As the operator,
I want `release_lag_hours` + `release_lag_qualifies` derived on the Phase H join with the 90-day recency gate,
So that packaging velocity is measurable without the false "47% behind" failure mode.

**Acceptance Criteria:** (spec § 9 Story B9, binding)

**Given** Phase H's retained per-release `upload_time_iso_8601`
**When** the column pair is derived
**Then** it exists on the Phase H join dataset with no new external fetch introduced
**And** the rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`)
**And** lag is computed against first availability of the matched version (minimum per-build repodata `timestamp`), fixture-enforced: a second build of the same version inside the window does not shift `release_lag_hours`
**And** a population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate); the two coincident 83.7% measurements re-verify against the § 15 evidence gists.

- **FRs:** FR-20.
- **Invariants:** AD-14 (never `latest_conda_upload`; not parity-gated), AD-3 (lives in `vcs_health`), timestamp convention (epoch seconds at ingest — repodata ms converted at the dataset boundary).
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (both failure-mode fixtures).
- **Depends on:** B2 (Phase H dataset); NOT gated on B4 parity.

---

## Story B10

### Story B10 (3.10): Migration-readiness datasets + classification node

As the operator,
I want conda-forge-bot-data `status/` category lists and per-migration detail ingested with a readiness-classification node,
So that migration readiness (e.g. python314) is a queryable four-way split with blocker labels and volume ranking.

**Acceptance Criteria:** (spec § 9 Story B10, binding)

**Given** the `status/` category lists and `migration_json/<name>.json` detail
**When** the datasets + classification node land
**Then** the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
**And** for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
**And** the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
**And** the downloads join yields a top-unmigrated-by-volume ranking
**And** all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

---

## Story C1

### Story C1 (4.1): Integrate `kedro-dagster` for scheduling + execution

As the operator,
I want the Kedro DAG compiled into a Dagster repository with schedules, retries, profiles, and per-node timeouts,
So that I watch runs in the Dagster UI and the 1800 s silent-phase-drop defect is structurally retired.

**Acceptance Criteria:** (spec § 9 Story C1, binding)

**Given** the migrated Kedro DAG
**When** `kedro-dagster` compiles it
**Then** schedules exist as Dagster Schedules encoding the `guides/atlas-operations.md` cadence table (bootstrap weekly; F/H/K/L/E.5 + G-after-vdb daily; E/J/M every 6 h; N hourly per maintainer; refresh assets weekly)
**And** the three bootstrap profiles (maintainer / admin / consumer) exist as named Dagster job configurations with the guide's override precedence (explicit run-config/env beats profile defaults)
**And** retries + phase state are observable in the Dagster UI
**And** timeouts are per-node: a cold-run Phase R overrun can no longer abort Phase F/K/N — the legacy 1800 s `cf_atlas_core` defect is demonstrably retired
**And** a `dagster-dryrun` verify task exists (definitions load, schedules enumerate — no live execution); the schedule bring-up itself is an attended event (Q2)
**And** Phase P stays `PHASE_P_ENABLED=1`, admin-config-only, never a default schedule.

- **FRs:** FR-6.
- **Invariants:** AD-6, AD-1 (`kedro-dagster` is replaceable glue; no upward imports), AD-23 (one execution plane; run admission serializes per dataset set).
- **Mode:** ATTENDED (bring-up boundary event — one of the five § 2.5 attended events; the `dagster-dryrun` gate it builds is loop-consumable thereafter).
- **Gating question:** **Q2** — default adopted (above); re-verify the Dagster bet at wave start (release cadence under Prefect, `kedro-dagster` compatibility, Components/Prefect-deployer ramps).
- **Verify gate:** **builds `dagster-dryrun`**.
- **Depends on:** Epic 3 complete (nodes + refresh assets to schedule).

**Deferred-work ledger (C1):**

## DW-C1-1 — the live Dagster schedule bring-up (ATTENDED, Q2) — DEFERRED to the wave-boundary event
- source_spec: `c1-integrate-kedro-dagster-for-scheduling-execution.md`
  summary: C1 shipped the offline glue (`orchestration/definitions.py`) + the `dagster-dryrun` gate (definitions load, schedules enumerate, jobs resolve, per-op timeout tags, Phase-P admin-only) — all verified with NO live execution. The actual schedule BRING-UP is the attended Q2 boundary: standing up a Dagster daemon (`dagster dev -m pyforge.atlas.orchestration.definitions`), turning the schedules RUNNING (they ship with no `default_status=RUNNING`, so nothing auto-starts), and observing real retries/phase-state in the UI. Do NOT weaken the dryrun gate to unattended-execute (NFR-12).
  evidence: `dagster definitions validate -m pyforge.atlas.orchestration.definitions` passes offline; `tests/orchestration/test_definitions_dryrun.py` (19) + the AD-1 import-ban (`tests/catalog/test_no_inline_io.py`) are the loop-consumable gate. `defs = build_definitions()` builds under blocked sockets (no network IO at import).

## DW-C1-2 — per-op runtime ENFORCEMENT + profile-config run-wiring are bring-up concerns (structural-only in C1)
- source_spec: `c1-integrate-kedro-dagster-for-scheduling-execution.md`
  summary: Two AC surfaces are STRUCTURAL in C1 and become operative only at the live bring-up (both reviewer-flagged, recorded not faked):
    (a) **Per-op timeout ENFORCEMENT.** Each op carries an independent `dagster/max_runtime` tag (the monolith is gone — no job/run-level timeout anywhere), but `dagster/max_runtime` is Dagster's run-monitoring tag, enforced by the DAEMON at bring-up. Today's operative isolation (a Phase-R overrun can't abort F/K/N) comes from JOB SEPARATION — Phase R rides only the weekly `bootstrap_data` job, F/K/N have their own scheduled jobs — not from the tag. Per-op runtime capping arrives with the daemon.
    (b) **Profile precedence run-wiring.** `resolve_profile_config` (maintainer/admin/consumer, precedence: run-config > env > profile default) is a verified pure function but is NOT yet attached to any job as `RunConfig`/`default_config`; a real run does not yet consume it. Wiring the resolved profile config into the job run-config is a bring-up step.
    Also deferred: the kedro-dagster `before/after_pipeline_run` hook ops exist only on the translated base graph and are filtered out of the derived/scheduled jobs — confirm at bring-up whether per-run session hooks are needed on the scheduled jobs or are intentionally base-only.
  evidence: `test_timeouts_are_not_a_single_monolith` + `test_every_op_has_its_own_timeout` prove the structural side; `resolve_profile_config` is exercised only by the gate, and `build_definitions` does not call it (structural-scope, by design for the attended C1 boundary).

---

## Story C2

### Story C2 (4.2): Integrate `kedro-viz` + expose a pixi task

As the operator,
I want the topological DAG rendered by `kedro-viz` behind a dedicated pixi task,
So that I inspect dataset schemas and lineage in the browser instead of reading orchestrator source.

**Acceptance Criteria:** (spec § 9 Story C2, binding)

**Given** the compiled DAG
**When** `pixi run viz` executes
**Then** it launches the Kedro-Viz server
**And** operators can inspect dataset schemas + data lineage in the browser.

- **FRs:** FR-6 (structural observability), whole-migration AC-3.
- **Invariants:** AD-1, AD-6.
- **Mode:** LOOP-E.
- **Gating question:** none (Q2 drained at C1).
- **Verify gate:** `dagster-dryrun` + `kedro-test` (existing gates; viz task smoke lands in the pixi task inventory).
- **Depends on:** C1.

---

## Story D1

### Story D1 (5.1): Define the Boring Semantic Layer (BSL) models

As a downstream consumer (page, MCP read, agent),
I want the 28 read CLIs' metric logic declared once as BSL dimensions + measures over the catalog (Ibis → DuckDB),
So that every read surface translates through one semantic interface with proven metric parity.

**Acceptance Criteria:** (spec § 9 Story D1, binding)

**Given** the metric/business logic embedded in the 28 read CLIs
**When** the BSL models are declared
**Then** BSL declares the core metrics (staleness, adoption stage, feedstock health, …)
**And** maintainer-role facts (`package_maintainers ⋈ maintainers`) are first-class BSL dimensions — the raw-SQL JOINs live consumers write today become declared queries
**And** the BSL layer is the single translation interface for downstream consumers
**And** a `bsl-metric-check` verify task exists: metric-parity fixtures proving BSL answers match the legacy CLI outputs for the core metrics (the AD-7 metric-semantics handover anchor).

- **FRs:** FR-8.
- **Invariants:** AD-8, AD-4 (Ibis → DuckDB only).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** **builds `bsl-metric-check`**.
- **Depends on:** Epic 4 (stable orchestrated datasets); B4 (canonical Parquet store).

---

## Story D2

### Story D2 (5.2): Build the Vizro dashboard + port the 28 CLIs to pages

As the operator,
I want a BSL-driven Vizro app reproducing the 28 read CLIs as pages, including a factory-status page,
So that every read-only question is answerable from a page meeting the agent-legibility bar.

**Acceptance Criteria:** (spec § 9 Story D2, binding)

**Given** the D1 BSL models and the CIS two-spine design specs
**When** the Vizro app is built
**Then** a Vizro dashboard serves the core KPIs currently locked in CLIs
**And** a "factory status" page reads the BMAD artifact state (sprint-status.yaml, epics frontmatter, `bmad-drift-check --specs` JSON) — agent-readable per § 13.2
**And** each read-only legacy CLI question is answerable from a Vizro page, where for the three FR-9 exceptions (`add-handoff`, `inventory-match`, `library-futures`) "answerable" means the latest-report artifact is surfaced read-only — the bar covers all 28
**And** the live-confirmed consumer set ports first: `behind-upstream`, `query-atlas`, `whodepends`, `feedstock-health`, `my-feedstocks`, `detail-cf-atlas`, `staleness-report`
**And** pages meet the § 2.1 agent-legibility bar (semantic HTML, ARIA, deterministic layouts; NFR-8) and public-facing breadth stays at the factory-status page (SM-C4).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-17 (authoring-feeding pages carry build timestamps).
- **Mode:** DEV-AUTO (visual judgment, § 9 preamble).
- **Gating question:** none.
- **Verify gate:** `bsl-metric-check` (+ `kedro-test`); D2 page inventory detail resolves in the CIS specs (Spine Deferred).
- **Depends on:** D1.

**Deferred-work ledger (D2):**

## DW-D2-1 — the full 28-page Vizro inventory is CIS-two-spine deferred
- source_spec: `d2-build-the-vizro-dashboard-port-the-28-clis.md`
  summary: D2 shipped the buildable core — the BSL-driven Vizro app framework, the AC's live-confirmed-first pages (behind-upstream / query-atlas / whodepends / feedstock-health / my-feedstocks / detail-cf-atlas / staleness-report), and the fully-specified factory-status page — all routed through the D1 semantic models (AD-8). The FULL 28-page inventory + each page's detailed design is blocked on the **CIS two-spine specs** (`DESIGN.md` + `EXPERIENCE.md`, § 84) which are NOT yet produced (Spine-Deferred). Producing them (the CIS Carson/Maya planning pass) is the precondition; the remaining pages port against them. Do NOT expand the page set past the live-confirmed core without the CIS spine.
  evidence: D2 AC "Given the D1 BSL models AND the CIS two-spine design specs"; verify-gate note "D2 page inventory detail resolves in the CIS specs (Spine Deferred)". The dashboard-dryrun gate asserts the shipped pages build offline + are BSL-driven; it does not assert 28-page completeness.

## DW-D2-2 — shell pages await their composed-store materialization (staleness / query-atlas / detail-cf-atlas / behind-upstream / whodepends)
- source_spec: `d2-build-the-vizro-dashboard-port-the-28-clis.md`
  summary: Several core pages are BSL-WIRED SHELLS: the loader queries the correct D1 semantic model, but the composed Parquet store that model binds to (e.g. a `semantic_packages` primary output joining the per-metric columns) is not materialized as a single dataset yet, so the page renders empty against the live catalog until that store lands. The loaders are honest (empty BSL query, never fabricated rows). Materializing the composed store (a small kedro node emitting the semantic-input Parquet) wires the live data. Pages backed by an existing single dataset (feedstock-health → core_feedstock_health; my-feedstocks → vcs_package_maintainers) are already live.
  evidence: `dashboard/data.py` shell loaders are grouped under a "BSL-wired SHELL pages (composed store not yet materialized — DW-D2)" banner; each returns an empty typed frame via `_bsl_query_or_empty` when the store is absent.

## DW-D2-3 — DEV-AUTO visual verification of the rendered UI (headless container cannot)
- source_spec: `d2-build-the-vizro-dashboard-port-the-28-clis.md`
  summary: D2 is a DEV-AUTO (visual-judgment) story. The dashboard-dryrun gate verifies the Dashboard OBJECT builds offline + structural agent-legibility (stable page id/title, deterministic layout, semantic factory-status table, AD-17 stamp), but the in-container run cannot VISUALLY verify the rendered browser UI (no display, no `app.run()`). The human/visual pass — actual `pixi run dashboard` render, the §2.1 semantic-HTML/ARIA browser-agent navigation check — is the deferred DEV-AUTO verification.
  evidence: `dashboard-dryrun` builds the object + asserts structure only; it never launches the server (offline gate, mirrors C1 dagster-dryrun / C2 viz-loadable).

---

## Story D3

### Story D3 (5.3): Integrate Vizro-AI + expose the NL interface as an MCP tool

As a CFE authoring agent (and the operator),
I want a Vizro-AI natural-language query field and a `query_vizro_ai` MCP tool over the BSL knowledge graph,
So that ad-hoc questions need no SQL and are callable from Claude Code.

**Acceptance Criteria:** (spec § 9 Story D3, binding)

**Given** the D1 BSL graph and the D2 dashboard
**When** Vizro-AI is integrated
**Then** a natural-language query (e.g. the § 4.3 example) returns a generated chart/insight
**And** the `query_vizro_ai` MCP tool is callable from Claude Code
**And** the LLM backend routes through repo model-backend configuration — never a hardcoded public endpoint (Q3 default).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-7 (MCP body carries no metric logic).
- **Mode:** ATTENDED (backend boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q3** (Vizro-AI LLM backend) — § 11 default adopted: route through repo model-backend configuration; defining the `_http.py`-analog LLM routing chain is the real work; bounds: no litellm (py3.14 floor), copilot-api bridge ineligible, llama.cpp/ollama/mlx-lm in-env.
- **Verify gate:** `bsl-metric-check` (existing; NL path verified at the attended event).
- **Depends on:** D1, D2.

**Deferred-work ledger (D3):**

## DW-D3-1 — the live Vizro-AI NL→chart backend bring-up (ATTENDED, Q3) — DEFERRED to the wave-boundary event
- source_spec: `d3-vizro-ai-nl-interface-query-vizro-ai-mcp-tool.md`
  summary: D3 shipped the buildable-now half — the thin `query_vizro_ai` MCP tool (AD-7), the `pyforge.atlas.nl` seam (backend resolver + BSL-grounded context), its registration (tools.py + server.py + audit.NL_INTERFACE_TOOLS + the mcp package export), and the `vizro-ai-dryrun` gate — all offline with NO live LLM call. The actual live Vizro-AI NL→chart invocation is the **attended Q3 backend event**: it happens only once a model backend is configured through repo model-backend config (`OPENAI_BASE_URL`+`OPENAI_API_KEY` or `ANTHROPIC_BASE_URL`+`ANTHROPIC_API_KEY` — Q3 §11 default, BINDING; never a hardcoded public endpoint). In-container with no backend configured the tool returns a structured `backend-not-configured` advisory; with a backend configured it returns a `backend-configured-live-call-deferred` receipt naming the repo-config endpoint but STILL makes no live call. At the event: configure the backend env, instantiate the Vizro-AI NL agent against the resolved backend + the BSL-grounded context (`build_bsl_context`), invoke NL→chart, and replace the deferred receipt's `chart: None` with the generated chart/insight. The `vizro_ai` top-level `VizroAI` entrypoint is absent in the pinned 0.4.1 (only `vizro_ai.agents.chart_agent`, a pydantic-ai Agent needing a backend), so the live-entrypoint wiring is finalized at the event; the import stays lazy+guarded in `nl/query.py` (AD-1: only `nl/` imports `vizro_ai`). Do NOT weaken the `vizro-ai-dryrun` gate to unattended-execute, and do NOT bake a public endpoint in (NFR-12 / Q3 §11).
  evidence: `tests/nl/test_query_vizro_ai_dryrun.py` proves the tool is registered + callable, the unconfigured path returns the advisory with no network (sockets blocked), a configured `OPENAI_BASE_URL` is the endpoint used, no host-bearing URL literal exists in the resolver (Q3 §11), the tool body is AD-7-thin, and the NL context is BSL-grounded (AD-8). `nl/query.py::query_vizro_ai` returns `chart=None` in both paths; `vizro_ai_available()` is a guarded probe. Mirrors the C1 dagster-schedule bring-up (DW-C1-1) and the B5/B7/B8 injected-fetcher deferrals.

## DW-D3-2 — the dashboard NL query field (the D2 Vizro dashboard's NL entry point) — DEFERRED (carries DW-D3-1 + the CIS spine)
- source_spec: `d3-vizro-ai-nl-interface-query-vizro-ai-mcp-tool.md`
  summary: D3 delivers the NL interface as an MCP tool (`query_vizro_ai`) — the agent-facing surface. The other NL surface, a natural-language query FIELD embedded in the D2 Vizro dashboard (a user types a question on a page and gets a generated chart), is DEFERRED: it depends on the live Vizro-AI backend (DW-D3-1) AND on the CIS two-spine design specs that gate the dashboard's page design (DW-D2-1). When both land, add the NL field as a dashboard component that calls the same `pyforge.atlas.nl` seam (so the MCP tool and the dashboard field share one backend-routing + BSL-grounding path, never a second execution plane — AD-23). Until then the dashboard ships without an NL field.
  evidence: D3's shipped surface is the MCP tool only (`server.py` `query_vizro_ai` @mcp.tool + `tools.query_vizro_ai`); `dashboard/app.py` is unchanged by D3 (no NL component added). The shared seam (`pyforge.atlas.nl`) is deliberately UI-agnostic so the dashboard field can reuse it at the event.

## DW-D3-1 — the live LLM backend + Vizro-AI NL invocation (ATTENDED, Q3) — DEFERRED
- source_spec: `d3-integrate-vizro-ai-nl-interface-mcp-tool.md`
  summary: D3 shipped the offline-buildable half: the thin `query_vizro_ai` MCP tool (AD-7 — delegates to the `nl/` seam), the backend-config RESOLVER that reads the LLM endpoint ONLY from repo model-backend env config (OPENAI_BASE_URL/OPENAI_API_KEY or ANTHROPIC_BASE_URL/key — Q3 §11, never a hardcoded public endpoint), the BSL-grounded NL context (D1 semantic models/metrics, AD-8), and the structured "backend not configured" advisory that the in-container default returns (no network, no live LLM, no fabricated chart). The ACTUAL live NL→chart invocation — instantiating Vizro-AI against a configured backend and returning a generated chart/insight — is the attended Q3 bring-up: configure the repo model-backend (a local OpenAI-compatible bridge per docs/copilot-to-api.md), then the deferred code path (guarded, lazy `import vizro_ai` in `nl/query.py`) runs. Do NOT wire a public endpoint or weaken the "no host-bearing URL literal" gate (NFR-12 / Q3).
  evidence: `vizro-ai-dryrun` gate asserts the tool is registered+callable, the unconfigured path degrades with no socket, the resolver reads from env + carries NO host-bearing URL literal (AST scan over backend.py AND query.py), and the tool body stays AD-7-thin. `from vizro_ai import VizroAI` does not resolve in this version — the live entrypoint is discovered + imported lazily at the attended event.

## DW-D3-2 — the Vizro-AI NL query FIELD in the dashboard UI — DEFERRED (DEV-AUTO / with D2)
- source_spec: `d3-integrate-vizro-ai-nl-interface-mcp-tool.md`
  summary: D3 delivers the NL surface as an MCP tool (callable from Claude Code). Surfacing the same NL query as an interactive FIELD in the D2 Vizro dashboard is deferred with the D2 CIS-two-spine page work (DW-D2-1) + its live LLM backend (DW-D3-1) — it needs both the rendered dashboard breadth and a configured backend, and the visual verification is the DEV-AUTO pass D2 defers.
  evidence: D3 AC "a Vizro-AI natural-language query field AND a query_vizro_ai MCP tool"; the MCP tool is shipped, the in-UI field rides on D2's deferred CIS-spine dashboard breadth.

---

## Story E1

### Story E1 (6.1): Implement the A2A communication interfaces

As a CFE authoring agent,
I want a structured A2A surface between the cf_atlas analytical agent and the conda-forge execution agents,
So that insights, contract violations, and policy breaches arrive as structured payloads, not prose.

**Acceptance Criteria:** (spec § 9 Story E1, binding)

**Given** the two agents (cf_atlas analytical, `conda-forge-expert` authoring)
**When** the A2A surface is built
**Then** the `cf_atlas` analytical agent can hand a structured payload to the `conda-forge-expert` agent (publish/subscribe or direct-message — transport resolves in this story's spec, Spine Deferred)
**And** payload schemas live in the `a2a/` module — the single schema source for alerts and insights (AD-20)
**And** payloads feeding authoring decisions carry their build timestamp (AD-17).

- **FRs:** FR-11.
- **Invariants:** AD-20 (sole structured inter-agent channel), AD-17.
- **Mode:** LOOP-E.
- **Gating question:** none (A2A transport is a story-spec decision, not a Q-gate).
- **Verify gate:** existing gates + payload round-trip fixture in `kedro-test`.
- **Depends on:** B3 (MCP surface), Epic 5 (BSL insights to carry).

**Deferred-work ledger (E1):**

## DW-E1-1 — the live cross-process A2A wire (a running fasta2a server / broker) — DEFERRED
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story E1, FR-11)
  summary: E1 shipped the load-bearing, buildable-now half of the A2A surface — the `a2a/` module as the SINGLE payload schema source (AD-20: one discriminated family for both insights and alerts, no second dialect), the AD-17-stamped builders (`build_insight_payload` referencing a BSL metric by `semantic.METRIC_PROVENANCE` id per AD-8 / `build_alert_payload`), the exact payload↔`a2a.types.Message` serialize/deserialize round-trip (canonical JSON inside a real a2a-sdk DataPart — protobuf Struct would floatify ints, so JSON preserves the payload EXACTLY), and the resolved transport: **direct in-process message-passing** (`hand_off` → `AuthoringInbox`) proving the cf_atlas-analytical → conda-forge-expert-authoring direction offline + deterministically. The genuine cross-process wire — standing up a live `fasta2a` (FastAPI-style A2A) server or an A2A broker between two OS processes so the two agents exchange messages over a bound socket — is DEFERRED: it needs a bound socket + a second process, neither of which comes up offline in-container, and faking a broker would be dishonest (mirrors the DW-C1-1 live-Dagster-schedule and DW-D3-1 live-LLM-backend attended bring-ups). Because the message ENVELOPE is already the real a2a-sdk `Message`, the follow-up is a delivery-substrate swap (`inbox.receive(msg)` → an HTTP/broker `send`), not a schema change. Do NOT weaken the offline round-trip/hand-off gate to unattended-execute a live server.
  evidence: `tests/a2a_surface/test_a2a_payloads.py` drives the whole surface against the in-process hand-off — `test_insight_round_trip_is_exact` / `test_alert_round_trip_is_exact` (exact incl. AD-17 stamp, no int→float drift, unicode), `test_analytical_to_authoring_hand_off` (ordered exact delivery to the authoring inbox), the AD-20 single-schema-source scans (`test_ad20_no_competing_payload_schema_outside_a2a`, `test_ad20_only_a2a_schema_subclasses_the_base`) + `tests/catalog/test_no_inline_io.py::test_a2a_sdk_only_in_a2a_layer` (only `a2a/` imports the a2a SDK), AD-17 (`test_ad17_stamp_required_and_injected`, `test_ad17_stamp_on_the_wire_envelope`), AD-8 (`test_ad8_insight_metric_must_be_a_bsl_identifier`), and the degrade-not-crash edges (unknown kind / malformed JSON / non-JSON-native field / missing payload part). No socket is bound and no second process is spawned in any test (AD-11 / offline).

---

## Story E2

### Story E2 (6.2): Integrate OpenLineage + OpenTelemetry

As the operator,
I want Kedro nodes, Dagster runs, and DuckDB queries instrumented with OpenLineage and OTel,
So that lineage, per-node metrics, and end-to-end traces are observable down to specific API calls.

**Acceptance Criteria:** (spec § 9 Story E2, binding)

**Given** the compiled DAG and hooks layer
**When** instrumentation lands
**Then** lineage + per-node metrics (rows, latency, cache hits) are captured via OpenLineage
**And** end-to-end distributed traces are visible via OTel down to specific API calls
**And** emitted-event/span fixtures are this story's gate assets (AD-20 — fixture-verified, since Wave E has no new named gate).

- **FRs:** FR-12.
- **Invariants:** AD-20, AD-6 (hooks declared in run config — every entry point inherits them, AD-23).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** existing gates + emitted-event/span fixtures in `kedro-test`.
- **Depends on:** C1 (Dagster runs to instrument).

**Deferred-work ledger (E2):**

## DW-E2-1 — the live OTel collector + OpenLineage backend wiring (env-driven) — DEFERRED
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story E2, FR-12)
  summary: E2 shipped the load-bearing, buildable-now half of the observability surface — the `observability.py` module as the SINGLE instrumentation seam (AD-6/AD-23: `openlineage`/`opentelemetry` confined there by `test_observability_libs_only_in_observability`), a Kedro Hooks impl (`AtlasObservabilityHooks`) declared ONCE in `settings.HOOKS` so EVERY entry point inherits it (a `kedro run` natively, a Dagster run via C1's `KedroProjectTranslator` → `KedroSession.run`), emitting per-node OpenLineage RunEvents (START/COMPLETE/FAIL) with input/output dataset lineage + the rows/latency/cache-hit metric facets (`OutputStatisticsOutputDatasetFacet.rowCount` + the custom `AtlasNodeMetricsRunFacet`), and an OTel span tree (pipeline → node → per-dataset read/write "API-call" spans). Nodes stay pure DataFrame→DataFrame (AD-2/AD-6) — all instrumentation is in the hook layer. Both backends are INJECTABLE and default to no-op/offline: `tracer_provider=None` → a local `TracerProvider` with no exporter (spans dropped, no network, never set globally); `openlineage_client=None` → OL emission skipped. The ACTUAL live wiring — a real OTLP endpoint (`OTEL_EXPORTER_OTLP_ENDPOINT` + a `BatchSpanProcessor`/`OTLPSpanExporter`) and a real OpenLineage backend URL/transport (`OPENLINEAGE_URL` → an `HttpTransport`) resolved from env at run bring-up — is DEFERRED: no collector/backend comes up offline in-container, and emitting to a fake endpoint would be dishonest (mirrors the DW-C1-1 live-Dagster-schedule and DW-D3-1 live-LLM-backend attended bring-ups). Because the emitters are already injectable, the follow-up is a substrate swap (construct an env-driven provider/client in `settings.py` or a factory and inject it), not an instrumentation change. Do NOT wire a live endpoint into the default path or weaken the offline fixture gate to require a backend.
  evidence: `tests/observability/test_observability_fixtures.py` drives a real two-node SequentialRunner pipeline (plus the pipeline-level hooks, as KedroSession fires them) with an in-memory OTel span exporter + a capturing OpenLineage client (`make_capturing_client`) and asserts the emitted event/span SHAPE — START+COMPLETE per node, input/output lineage edges, shared runId, the rowCount + rows/latency(`>=0`)/cache-hit facets, and the nested pipeline→node→dataset span tree in one trace — these captured fixtures ARE the gate (AD-20). Edge cases proven: `on_node_error` emits FAIL + closes the span (no leak, ERROR status), no-input/output nodes, empty-frame rows=0, non-DataFrame output degrades (rowCount omitted, no crash), the None-captor default path runs the full lifecycle without emitting/crashing, nested pipeline frames close without leaking, and no now()/uuid leaks into any asserted field. `test_no_inline_io.py::test_observability_libs_only_in_observability` pins the single-seam containment. `AtlasObservabilityHooks.__getstate__` drops the un-deepcopyable OTel tracer so C1's translator can deep-copy the settings HOOKS (the copy rebuilds a lazy default tracer). No socket is bound and no exporter reaches a network in any test (offline).

## DW-E2-2 — Dagster-plane observability inheritance verification + span-key footgun (bring-up)
- source_spec: `e2-integrate-openlineage-opentelemetry.md`
  summary: The AD-23 claim "the Dagster plane inherits the settings-registered observability hook, nested" is verified for the KEDRO plane (fixture gate) but NOT yet for the Dagster plane — the C1 live bring-up (DW-C1-1) is where a real kedro-dagster run confirms parent→node→dataset span nesting + cache_hits survive the translator's per-run hook deepcopy. The deepcopy asymmetry (a dropped OTel provider) is FIXED in E2 (`__deepcopy__` shares _provider + _ol by reference; regression test `test_deepcopy_preserves_injected_backends_no_otel_ol_asymmetry`), so a future injected exporter reaches both planes — but the end-to-end Dagster-plane assertion still rides on the deferred daemon bring-up. Also latent (Reviewer-B finding 2): `_nodes` is keyed by `node.name`; two in-flight runs of the same node name would overwrite/leak state — impossible under Kedro's unique-names-per-pipeline + DAG-ordered runners today, but a `(node.name, run_id)` key would remove the footgun if a future runner violated that. Not reachable now.
  evidence: E2 gate drives a SequentialRunner + manual before/after_pipeline_run; `dagster definitions validate` passes but does not RUN nodes. Thread-safety: `_nodes`/`produced` are unlocked — correct under SequentialRunner + C1 in_process executor (DAG-ordered), a ThreadRunner/ParallelRunner would need locking.

## DW-E2-3 — AtlasNodeMetricsRunFacet provenance stamp (cosmetic)
- source_spec: `e2-integrate-openlineage-opentelemetry.md`
  summary: The custom `atlasNodeMetrics` run facet is emitted without an explicit `producer=PRODUCER`, so its `_producer` defaults to the OpenLineage library URI rather than the project PRODUCER every other emitted facet carries (Reviewer-A nice-to-have). Cosmetic — the metric VALUES (rows/latency_ms/cache_hits) are correct; only the facet's provenance-stamp URI differs. Left untouched to avoid perturbing the attrs RunFacet inheritance; revisit if lineage-provenance consistency is ever asserted.
  evidence: `AtlasNodeMetricsRunFacet` construction on the COMPLETE event does not pass producer; the standard rowCount + errorMessage facets do.

---

## Story F1

### Story F1 (7.1): Complete the DuckDB consolidation + prove the cold-start claim

As the operator,
I want all legacy-`cf_atlas.db` residue migrated or deleted and the performance claims honestly benchmarked,
So that DuckDB/Parquet is the sole store and AC-7's claims are evidence, not promises.

**Acceptance Criteria:** (spec § 9 Story F1, binding)

**Given** B4's legacy retirement and the Wave-A-onward Parquet path
**When** the residue cleanup + benchmark run
**Then** no SQLite read or write path remains anywhere in the migrated surface (grep-gated: no `sqlite3` import outside the retired legacy tree)
**And** the attended benchmark records both a warm incremental refresh (the headline — only affected nodes re-run) and the cold full-build wall-clock vs the legacy 3–4 h network-bound baseline, with evidence recorded per AC-7's honest scoping
**And** the pass threshold was fixed in this story's spec **before** the benchmark ran (SM-3); pass is adjudicated at the attended event by operator sign-off.

- **FRs:** FR-5.
- **Invariants:** AD-4 (grep gate), AD-19, SM-C1 (do not chase cold-start).
- **Mode:** ATTENDED (benchmark boundary event — one of the five § 2.5 attended events). **Keystone story — pre-flight budget raise + `dev_stall_grace_s` raise (AD-18/Spine).**
- **Gating question:** none (threshold is a story-spec decision, Spine Deferred).
- **Verify gate:** grep gate + `kedro-test`; benchmark evidence at the attended event; wave-boundary `test-all`.
- **Depends on:** B4 (retirement decided), Epics 4–6 (surfaces that might still read legacy).

**Deferred-work ledger (F1):**

## DW-F1-1 — the cold-start / warm-incremental benchmark (ATTENDED, SM-3) — DEFERRED
- source_spec: `f1-complete-the-duckdb-consolidation-prove-the-cold-start-claim.md`
  summary: F1 shipped the always-on offline half — the DuckDB-singularity grep gate
    (`tests/singularity`, pixi `duckdb-singularity`): NO sqlite3 path in the migrated
    surface (FR-5/AD-4), the one legacy-SQLite reader pinned to tests/ (the B4 credentialed
    comparator reading the OLD store to retire it). The PERFORMANCE half — the attended
    benchmark recording (a) the warm incremental refresh headline (only affected nodes
    re-run) and (b) the cold full-build wall-clock vs the legacy 3-4 h network-bound baseline
    — is the ATTENDED boundary event (one of the five § 2.5 attended events). Per SM-3 the
    pass THRESHOLD must be fixed in this story's spec BEFORE the benchmark runs, and pass is
    adjudicated by operator sign-off (AD-19). Do NOT chase cold-start (SM-C1 — the headline is
    warm-incremental; cold is network-bound and not the win). Keystone-story pre-flight
    (budget + dev_stall_grace_s raise) applies at the attended run, not in-loop.
  evidence: the grep gate is green offline; there is no in-container way to run a credentialed
    full cold build (no operator runtime data, AD-11). B4 retirement (DW-B4-2) is the
    precondition — legacy is not marked retired until its credentialed parity + sign-off land.

---

## Story F2

### Story F2 (7.2): Implement the data-validation hook and inline Pandera contracts

As the operator,
I want inline pandera contracts behind a validator-agnostic `AfterNodeRunHook` with version-capped GX as boundary layer,
So that bad data halts the pipeline before persisting, with an A2A alert.

**Acceptance Criteria:** (spec § 9 Story F2, binding)

**Given** a malformed-payload fixture (e.g. PyPI JSON missing a version field)
**When** the node runs under the validation hook
**Then** the validation failure halts execution by raising a native Python exception
**And** the failure propagates to Dagster, halting the pipeline and raising an A2A alert
**And** the hook interface is validator-agnostic: swapping/adding the GX backend requires no node changes (fixture-proven with a stub second validator)
**And** GX participates only at conda-forge 1.18.2 (no ≥1.19 features); the `kedro-great-expectations`/`kedro-pandera` plugins are banned (AD-9).

- **FRs:** FR-10.
- **Invariants:** AD-9, AD-20 (alert channel), AD-23 (hook rides every entry point).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (halt fixture + stub-validator fixture).
- **Depends on:** E1 (A2A alert channel), C1 (Dagster halt propagation).

**Deferred-work ledger (F2):**

## DW-F2-1 — the Great Expectations boundary adapter (version-capped at cf 1.18.2) — DEFERRED
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story F2, FR-10, AD-9)
  summary: F2 shipped the load-bearing, buildable-now half of the data-validation surface — `validation.py` as the SINGLE validation seam: a validator-agnostic `Validator` protocol (a backend REPORTS `ContractViolation`s, never halts itself, so the hook owns the raise+alert in ONE place and a new backend needs ZERO node/hook edits — AC-3), the shipped inline `PanderaValidator` (per-dataset `DataFrameSchema` registry `DEFAULT_CONTRACTS`, declared as DATA never inline in nodes), and `DataValidationHooks` registered ONCE in `settings.HOOKS` (AD-23) so EVERY entry point validates — firing in `after_node_run`, the verified kedro-1.5.0 pre-persist point (`Task._call_node_run` calls `after_node_run` with the full outputs dict BEFORE the runner save loop), raising a native `DataContractViolation` that halts before ANY output persists and, on the way out, emits an `AtlasAlert` on E1's real A2A channel (AD-20, `build_alert_payload` → injected `alert_sink` → `hand_off`/`AuthoringInbox`). The DEFERRED half is the **Great Expectations boundary adapter**: AD-9 caps GX at conda-forge **1.18.2** semantics (no ≥1.19 features), but the in-env GX is **1.19.0** and cannot be *statically guaranteed* to stay within 1.18.2-only features, so — per AD-9's explicit preference — the shipped hook path imports **NO** `great_expectations` at all. `GreatExpectationsBoundaryValidator` is a protocol-conforming STUB (its `check` raises `NotImplementedError` with this DW note) that proves the seam ACCEPTS a GX backend with zero node changes; the real adapter is deferred to an environment where GX is pinned to 1.18.2, at which point the stub is replaced by a 1.18.2-feature-only adapter and slotted into the same `validators=[...]` list — no node/hook change (the point of the seam). The `kedro-great-expectations` / `kedro-pandera` plugins stay BANNED everywhere (the hook is hand-rolled). Do NOT import GX into the shipped path or lift the 1.18.2 cap to unblock this.
  evidence: `tests/validation/test_validation_hook.py` drives a real one-node SequentialRunner pipeline with a persistence-tracking dataset and asserts the F2 behaviours: a malformed payload (PyPI frame missing `version`) HALTS via a native `DataContractViolation` with the output NOT persisted (save loop never ran), emitting an `AtlasAlert` (severity critical + rule `pandera_schema` + evidence naming the column) delivered over the real A2A channel (`hand_off` → `AuthoringInbox`, round-trip-identical); a valid payload passes AND persists (no false halt); a STUB second validator halts the SAME node with zero node edits (AC-3 validator-agnosticism), and a stub-only config proves pandera is not special; the GX boundary stub raises with the 1.18.2 DW note; `test_no_inline_io.py::test_banned_validation_plugins_nowhere` + `test_no_great_expectations_in_shipped_validation_path` pin AD-9. Edge cases proven: no registered contract → pass-through; non-frame output skips gracefully (no crash); empty-frame conformant passes / missing-column halts; a broken validator halts loudly (never silently passes bad data); the default no-op sink and a RAISING sink both never mask the halt; a multi-output node halts before ANY output persists; the default hook is deepcopy-safe (C1 translator copies `settings.HOOKS`); and co-registration with the E2 observability hook still halts order-independently. `DEFAULT_CONTRACTS` ships EMPTY (machinery + seam, nothing speculative) so the settings-armed hook can never false-halt a real run until a contract is declared. No socket is bound and no network is touched in any test (offline).

## DW-F2-2 — wire a real A2A alert_sink into the shipped validation hook (gated on F4's first contract)
- source_spec: `f2-data-validation-hook-inline-pandera-contracts.md`
  summary: F2's `settings.HOOKS` constructs `DataValidationHooks()` with NO `alert_sink`, so a
    production contract violation halts correctly (data never persists) and BUILDS the AtlasAlert
    (carried on the raised `DataContractViolation.alert`) but does NOT DELIVER it on the A2A
    channel — delivery is proven only in the gate via an injected sink. This is MOOT today
    (`DEFAULT_CONTRACTS` is empty — no violation can fire), but the moment F4 registers the first
    real pandera contract, a production halt would drop the AD-20 alert. Wiring an offline-safe
    default sink (e.g. an AuthoringInbox-backed hand_off, NOT a networked sink — that would break
    the AD offline-import guarantee) into `settings.HOOKS` is therefore a GATING step of F4 (its
    ComplianceReport/policy-breach path raises "identical failure semantics to an FR-10
    violation"). Reviewer-A S1.
  evidence: `DataValidationHooks.__init__(alert_sink=None)` → `_halt` skips delivery when
    `_sink is None`; the raised exception carries `.alert`, so nothing is lost at the raise site,
    only unconsumed. Both reviewers flagged; the _build_alert robustness fix (JSON-native evidence
    + rule fallback) landed in F2 so a real sink can't be crashed by a third-party backend.

---

## Story F3

### Story F3 (7.3): Implement Vector Similarity Search (RAG) via DuckDB `vss`

As a CFE authoring agent,
I want RAG embeddings + similarity search via DuckDB's `vss` extension,
So that semantic retrieval over embedded artifacts runs in the same single engine.

**Acceptance Criteria:** (spec § 9 Story F3, binding)

**Given** embedded artifacts in the DuckDB store
**When** a similarity query runs
**Then** it returns ranked results from DuckDB via `vss`
**And** the embedding model/strategy and offline `vss` extension provisioning (default network `INSTALL` collides with AD-13 for the consumer profile) are resolved in this story's spec (Spine Deferred).

- **FRs:** FR-5.
- **Invariants:** AD-4, AD-13 (offline provisioning tension — must resolve, not ignore).
- **Mode:** LOOP-E.
- **Gating question:** none (embedding strategy is a story-spec decision).
- **Verify gate:** `kedro-test` (ranked-results fixture).
- **Depends on:** F1 (consolidated store).

**Deferred-work ledger (F3):**

## DW-F3-1 — a real learned embedding model (upgrade from the deterministic default)
- source_spec: `f3-implement-vector-similarity-search-rag-via-duckdb-vss.md`
  summary: F3's default embedder is a deterministic, offline, dependency-light feature-hash
    (hashing-trick) vectorizer — it proves the DuckDB `vss` RANKING mechanism (which is what F3
    ships) with no model download and no network, and is stable across processes/machines
    (hashlib, never Python's salted hash()). A real LEARNED embedding model (e.g.
    sentence-transformers) is the semantic-quality upgrade: it is heavy and may need a
    model download / network, so it is DEFERRED. The seam is ready — `DuckdbVssRagStore(embedder=…)`
    accepts any object with an int `dim` + `embed(text)->list[float]`; the ranking still runs in
    DuckDB regardless of embedder, so the upgrade requires NO store/query change. Wire it when a
    conda-forge-provisioned model + an embedding-provisioning story lands.
  evidence: `rag/embedding.py::HashingEmbedder` is the default; `Embedder` is a Protocol; the
    gate proves ranked results are deterministic under the hash embedder (a learned model would
    change the vectors, not the ranking mechanism).

## DW-F3-2 — live `vss` extension provisioning (the one-time network INSTALL)
- source_spec: `f3-implement-vector-similarity-search-rag-via-duckdb-vss.md`
  summary: The consumer path is offline: it only `LOAD`s `vss` from the pre-provisioned local
    extension cache and raises `VssNotProvisionedError` (naming the provisioning step) if absent
    — never a silent network `INSTALL` (AD-13). The one-time `INSTALL vss` (network) lives ONLY
    in the explicit, attended `rag.provision_vss(connection)`, which the consumer path never
    calls. In THIS container vss is already cached (v1.5.4), so the offline LOAD works; a fresh
    air-gapped/enterprise environment must run `provision_vss` (or ship the vendored extension
    to the DuckDB extension dir) once, attended, before the RAG surface is usable. That
    provisioning-in-a-clean-environment step is the deferred/attended piece.
  evidence: `rag/store.py::load_vss_offline` (offline LOAD or VssNotProvisionedError) vs
    `provision_vss` (the only INSTALL); the rag gate proves the consumer path makes no network call.

---

## Story F4

### Story F4 (7.4): Dependency-hygiene node + unified CI policy gate

As CI,
I want the deptry hygiene node and the converged four-axis policy gate as the Universal SBOM pipeline's terminal stage,
So that one schema-validated `ComplianceReport` and one frozen exit code replace CLI scraping.

**Acceptance Criteria:** (spec § 9 Story F4, binding)

**Given** the B7 SBOM pipeline and the F2 validation machinery
**When** the hygiene node + policy gate land
**Then** an injected unused-dependency fixture yields a schema-valid hygiene finding in the `ComplianceReport` artifact (source-less inputs report `not-applicable`, never failure — FR-16)
**And** a policy breach (e.g. `max_critical=0` violated, or a KEV-affecting-current hit) exits with the frozen contract codes (1 policy-fail / 2 error), halts Dagster, and raises an A2A alert — identical failure semantics to an FR-10 violation
**And** the assembled report validates against the four-axis `ComplianceReport` schema (hygiene + security populated; license/currency from atlas-native data or `not-applicable`), with the F4 terminal node as the single producer (AD-12)
**And** the `inventory-match` exit-code flip lands with its one-release deprecation window (`INVENTORY_MATCH_LEGACY_EXIT=1`); CI consumers see the frozen convention
**And** the report schema matches `pyforge-warden.md`'s `ComplianceReport` **by import** *(correct-course 2026-07-17)* — the gate node validates against `pyforge.warden`'s schema module via the `pyforge-atlas[gate]` extra, never a vendored copy (AD-12 schema-by-import); absent the extra, the gate node fails with an explicit install hint while all other pipelines run (independence preserved) — so the planned promotion (MCP tool + pixi CLI) requires no schema change.

- **FRs:** FR-16, FR-18, FR-10.
- **Invariants:** AD-12 (single producer; scope split; degradation-vocabulary mapping), AD-9, AD-20, AD-15.
- **Mode:** LOOP-S (unattended assumption — see Decisions § D-6: the exit-code flip + frozen convention warrant per-story spec approval).
- **Gating question:** none.
- **Verify gate:** `kedro-test` (schema fixtures + exit-code fixtures + `not-applicable` fixture).
- **Depends on:** B7 (intake + matcher), F2 (validation machinery).

---

## Story G1

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

**Deferred-work ledger (G1):**

## DW-G1-1 — full Vizro-AI dashboard RENDERED inside Pyodide (the heavy read-surface half)
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

## DW-G1-2 — heavy WASM build assets are gitignored; CI must run `wasm-build` before `wasm-smoke`
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

---

## Story G2

### Story G2 (8.2): Emit Parquet artifacts to a static web host

As a dashboard consumer,
I want Parquet artifacts published to a static host and pulled via HTTP Range,
So that the WASM runtime reads live data with zero backend.

**Acceptance Criteria:** (spec § 9 Story G2, binding)

**Given** the G1 WASM runtime
**When** the emitter publishes
**Then** Parquet artifacts are published to the static host (Q4 default: GitHub Pages) and consumed by the WASM runtime via HTTP Range
**And** the emitter is host-agnostic so an enterprise mirror can substitute (Q4)
**And** the published artifact layout (chunking, manifest) has a single owner: this emitter (Spine convention).

- **FRs:** FR-14.
- **Invariants:** AD-21, AD-2 (mirror substitution).
- **Mode:** ATTENDED (publish boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q4** (WASM artifact host) — § 11 default adopted: GitHub Pages public path; emitter host-agnostic.
- **Verify gate:** **consumes `wasm-smoke`** (against the published artifact at the attended event; fixture-hosted in-loop).
- **Depends on:** G1.

**Deferred-work ledger (G2):**

## DW-G2-1 — the LIVE GitHub Pages publish is the ATTENDED boundary event (not automated)
- source_spec: `g2-emit-parquet-artifacts-to-a-static-web-host.md`
  summary: G2 ships the host-agnostic EMITTER (`pyforge.atlas.publish.emit_static_site`) — it
    writes the chunked-Parquet + single-owner `manifest.json` LAYOUT to a target directory ("the
    static host filesystem"), and the `publish-range` gate PROVES that layout is consumed via HTTP
    Range (206 partial reads, footer + row groups only) by a DuckDB httpfs client over a loopback
    host. What is DEFERRED is the LIVE publish: pushing the emitted directory to a real static host
    (Q4 default: GitHub Pages `gh-pages` / an enterprise mirror) is one of the five § 2.5 ATTENDED
    boundary events — it needs credentials + a chosen host + a human at the wheel, so it is never
    run in-loop. The emitter is host-agnostic by construction (target is a PATH; the base URL is a
    runtime arg to `chunk_url`, no `github.io` anywhere in the emit logic — AD-2), so the attended
    step is purely "serve/push this directory" with zero code change to substitute a mirror.
    Wiring the browser G1 page to consume the emitted manifest layout over Range (today it fetches
    a single whole Parquet via `fetch().arrayBuffer()`) is the same attended event's follow-on.
  evidence: `src/pyforge/atlas/publish/emitter.py` (`emit_static_site` writes to a dir, relative
    manifest paths, `chunk_url(base_url, path)` composes the runtime host); `python -m
    pyforge.atlas.publish` emits to a gitignored `_site/`; `tests/publish/test_emit_range.py`
    fixture-hosts on loopback and asserts NO live publish. No push/credential/host code exists.

## DW-G2-2 — DuckDB `httpfs` must be provisioned once (offline-LOAD in the Range gate)
- source_spec: `g2-emit-parquet-artifacts-to-a-static-web-host.md`
  summary: The `publish-range` gate's Range consumer is a native DuckDB `httpfs` client (the same
    engine + Range mechanism DuckDB-WASM uses in the browser). Like `vss` (DW-F3-2), DuckDB's
    default `INSTALL httpfs` hits the network, which collides with the offline invariant — so the
    gate LOADs httpfs from the local extension cache with autoinstall/autoload DISABLED. If httpfs
    is not provisioned, the gate SKIPS locally with the provisioning step named (a legitimate
    not-provisioned skip, DISTINCT from the range-read-actually-failed case, which always FAILS),
    and under CI / `PUBLISH_RANGE_REQUIRED=1` it FAILS instead of passing having verified nothing.
    A fresh air-gapped/CI environment must run `INSTALL httpfs;` once (attended, network) to
    populate the cache before the gate can run offline — mirrors the vss provisioning story.
  evidence: `tests/publish/test_emit_range.py::_offline_httpfs_connection` (autoinstall/autoload
    off → LOAD-from-cache → skip-or-fail on failure, `_publish_required()`); the container's cache
    already carries `httpfs.duckdb_extension` (v1.5.4) so the gate runs GREEN here.

## DW-G2-2 — migrate the G1 wasm/ runtime to consume the emitter's manifest (single-owner completion)
- source_spec: `g2-emit-parquet-artifacts-to-a-static-web-host.md`
  summary: G2's emitter is the single owner of the PUBLISHED-site layout (chunked Parquet +
    manifest.json), READ by the publish Range gate. But G1's wasm/ runtime shipped first and
    fetches a FLAT `./core_feedstock_health.parquet` (its own build.py produces that flat file) —
    it does NOT read manifest.json / chunk_url yet, so it is a SECOND, independent layout for the
    same data (Reviewer-A). Completing the single-owner invariant = migrating G1's index.html to
    load the manifest + compose chunk URLs via chunk_url (and having build.py emit via the
    emitter). Deferred because it re-touches the G1 WASM artifact + its ~41 MB bundle rebuild
    (DW-G1-2 CI build step) and is best done with the live-publish bring-up (DW-G2-1). Until then
    the emitter/gate own the published layout; G1 remains an independent dev artifact.
  evidence: `wasm/index.html` hardcodes `fetch("./core_feedstock_health.parquet")`;
    `wasm/build.py::_csv_to_parquet` produces the flat file; the emitter produces
    `core_feedstock_health/core_feedstock_health-0000.parquet` + `manifest.json`. The publish gate
    IS a manifest consumer (proves the layout); G1 is not yet.

---

## Story G3

### Story G3 (8.3): Implement Dagster Sensors for near-real-time ingestion

As the operator,
I want the pipeline event-driven via Dagster Sensors on upstream events (PyPI/GitHub webhooks or RSS),
So that ingestion is near-real-time and incremental instead of purely scheduled.

**Acceptance Criteria:** (spec § 9 Story G3, binding)

**Given** the C1 Dagster repository
**When** a simulated upstream event fires
**Then** it triggers the relevant pipeline incrementally via a Dagster Sensor
**And** the event-source choice (webhooks vs RSS) and the persistent-daemon question it drags in (Q2 revisit condition) are resolved and recorded in this story's spec (Spine Deferred).

- **FRs:** FR-6, spec § 5.9.
- **Invariants:** AD-6, AD-23 (sensor-triggered runs ride the same job machinery), AD-5 (incremental via the dataset class).
- **Mode:** LOOP-E.
- **Gating question:** Q2 revisit condition only (daemon footprint — resolves here if sensors require it; not a blocking Q-gate).
- **Verify gate:** `dagster-dryrun` (sensors enumerate) + simulated-event fixture in `kedro-test`.
- **Depends on:** C1, G2 (per § 14 wave order).
- **DELIVERED (2026-07-18 — closes Wave G):** two sensors (`pypi_release_sensor` → Phase H, `vcs_release_sensor` → Phase K) added to C1's `defs` via `orchestration/event_source.py` (dagster-free logic) + `build_upstream_sensor` in `orchestration/definitions.py`; a simulated event → one `RunRequest` for the existing incremental job (AD-23/AD-5), no-event → `SkipReason`. Event source = RSS/poll cursor (not webhooks); live daemon deferred (DW-G3). Gate `test_definitions_dryrun.py` +12; AD-1 import-ban + `dagster definitions validate` green. See spec § 5.9 / Q2.

**Deferred-work ledger (G3):**

## DW-G3 — the live Dagster sensor DAEMON bring-up (ATTENDED, Q2) — DEFERRED to the wave-boundary event
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story G3, § 5.9, FR-6)
  summary: G3 shipped the BUILDABLE half of event-driven ingestion — the sensor DEFINITIONS +
    their eval logic, wired into C1's `defs`, all verified with NO live execution and NO network.
    `orchestration/event_source.py` (dagster-free event parse + monotonic-`seq` cursor dedupe +
    run/skip DECISION, so AD-1's "only definitions.py imports dagster" rule holds) + `UPSTREAM_SENSORS`
    / `build_upstream_sensor` in `orchestration/definitions.py` add two sensors to
    `dg.Definitions(..., sensors=[...])`: `pypi_release_sensor` → the existing `phase_h_pypi_versions`
    job, `vcs_release_sensor` → the existing `phase_k_vcs_upstream` job (AD-23 — each yields a
    `RunRequest` for a job C1 already built; NO second execution plane), both targeting the two
    upstream surfaces A3 flipped to `IncrementalParquetDataset` (AD-5 — the sensor only TRIGGERS;
    the run re-fetches only TTL-stale rows). Event source = **RSS/poll cursor (resolved over webhooks
    — a webhook needs an always-on bound public ingress, the Q2 daemon-footprint cost, and can't be
    exercised offline); the source is INJECTABLE and defaults to an offline no-op (`offline_event_source`
    → `[]`)**, so a built `defs` carries NO network dependency. Sensors ship `default_status=STOPPED` —
    nothing auto-starts. The ACTUAL bring-up is the attended Q2 boundary: standing up a
    `dagster-daemon`, turning the sensors RUNNING, injecting the LIVE RSS/poll feed readers
    (PyPI `updates.xml`, per-repo `releases.atom`) in place of the offline no-op, and observing real
    incremental runs fire. Do NOT weaken the dryrun gate to unattended-execute a live daemon or bind a
    socket (NFR-12). Mirrors DW-C1-1 (live schedule bring-up) and DW-D3-1 (live LLM backend).
  evidence: `dagster definitions validate -m pyforge.atlas.orchestration.definitions` passes offline;
    `tests/orchestration/test_definitions_dryrun.py` (+12: sensors enumerate + target real jobs, a
    simulated event via `build_sensor_context` + an injected fixture source → one `RunRequest` for the
    right incremental job with the cursor advancing, no-event/duplicate/malformed/raising → `SkipReason`,
    `default_status=STOPPED`, offline-default-is-no-op) + the AD-1 import-ban (`tests/catalog/test_no_inline_io.py`,
    now covering `orchestration/event_source.py` via rglob — it imports no dagster). The live feed
    readers do not exist in-package (injected, mirroring the B5/B7/B8 injected-fetcher deferrals).

---

## Story H1

### Story H1 (9.1): Scaffold the Karpathy Wiki folder structure and Agent Personas

As the operator,
I want the `wiki/raw/ → compiled/ → outputs/` tree and the 5 BMAD personas (Ingester, Compiler, Linker, Linter, Oracle) defined,
So that the knowledge-base factory has its storage shape and workforce.

**Acceptance Criteria:** (spec § 9 Story H1, binding)

**Given** the scaffolded project
**When** the wiki scaffold lands
**Then** the three-stage wiki tree exists with a scaffold-layout test
**And** the 5 persona definitions resolve through the § 2 customization layers
**And** PostgreSQL/MinIO storage services are conda-forge-provisioned per AD-16 (MinIO server provisioning resolved as this story's precondition).

- **FRs:** FR-22(a).
- **Invariants:** AD-22, AD-16.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** scaffold-layout test + persona-resolution test in `kedro-test`.
- **Depends on:** Epic 8 complete (wave order); pipeline outputs to consume exist from Epic 3+.
- **DELIVERED (2026-07-18 — opens Wave H):** new `pyforge.atlas.factory` package. `factory/wiki.py` = the single-owner `raw/→compiled/→outputs/` layout contract (`WIKI_STAGES`/`WikiLayout`/`scaffold_wiki`) with a per-segment `stage_path` traversal guard enforcing the AD-22 write-boundary; `factory/personas.py` = the 5 § 2.2 personas + `resolve_personas(*overlays)` (BMAD customization layers, highest-priority-last; overlay may only refine — unknown name / rename rejected; workforce frozen at five); `factory/storage.py` = env-driven resolver defaulting to the OFFLINE filesystem backend (MinIO selected only when `ATLAS_WIKI_S3_ENDPOINT` set; host-agnostic AD-2). MinIO/PostgreSQL SERVER bring-up DEFERRED (DW-H1). Gate `tests/factory/` (26). AD-1 import-ban green. PR #99.

**Deferred-work ledger (H1):**

## DW-H1 — the MinIO/PostgreSQL SERVER provisioning + bring-up (ATTENDED) — DEFERRED to the H1 precondition event
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story H1, § 7.4, FR-22(a))
  summary: H1 shipped the BUILDABLE half of the Karpathy-wiki storage layer — the layout contract
    (`factory/wiki.py`: `WIKI_STAGES` + `WikiLayout` + `scaffold_wiki`, the SINGLE owner of the
    `raw/ → compiled/ → outputs/` tree), the five § 2.2 personas + their BMAD customization-layer
    resolution (`factory/personas.py`), and the storage-backend RESOLVER (`factory/storage.py`),
    all offline. The architecture (ARCHITECTURE-SPINE § "Factory layer") records that **only the
    MinIO Python SDK is in-env today — the MinIO/PostgreSQL SERVERS are not provisioned**, and calls
    that server bring-up the H1 precondition (Spine "Deferred"). H1's code therefore DEFAULTS to the
    plain local filesystem (`resolve_storage_config()` → `backend="filesystem"` when
    `ATLAS_WIKI_S3_ENDPOINT` is empty/unset) and never opens a connection; a MinIO backend is
    selected ONLY when an endpoint is explicitly configured (host-agnostic, AD-2 — no host is
    hardcoded). The ACTUAL deferred bring-up: provision the conda-forge MinIO + PostgreSQL servers
    (precedent: MyBMAD's per-user PostgreSQL in the `bmad-ui` env), create the wiki bucket, wire the
    live `minio` SDK client from the resolved config, and run the crews against the object store
    instead of the local dir. Do NOT weaken any gate to stand up a server unattended or bind a
    socket (NFR-12). Mirrors DW-C1-1 / DW-G3 (live daemon bring-up) and DW-D3-1 (live backend).
  evidence: `factory/storage.py::resolve_storage_config` returns `filesystem` with no network
    touch when the endpoint env is absent (`tests/factory/test_personas.py` storage cases:
    default-is-filesystem, empty-env-is-unset, configured-endpoint-selects-minio,
    both-keys-required-for-credentials). Only `minio` the SDK is importable in-env; no server
    process runs. The AD-16 pixi.toml line ships `minio >=7.2.20` (SDK) + `psycopg2 >=2.9.12`
    (driver) — the SDKs, not the servers.

---

## Story H2

### Story H2 (9.2): Implement Agno Compilation, Linting, and Q&A Crews

As the operator,
I want `agno` crews that compile raw docs, lint the wiki, and answer questions,
So that the wiki maintains itself with agent labor.

**Acceptance Criteria:** (spec § 9 Story H2, binding)

**Given** the H1 scaffold and a fixture wiki
**When** each crew runs end-to-end
**Then** compile transforms raw → compiled, lint reports violations, and Q&A answers grounded in compiled content
**And** wiki outputs carry their source datasets' staleness markers forward (AD-13/AD-22 — republication never launders freshness).

- **FRs:** FR-22(b).
- **Invariants:** AD-22, AD-13.
- **Mode:** DEV-AUTO (spec § 9 explicit: crew design needs judgment).
- **Gating question:** none (crew design detail is a story-spec decision, Spine Deferred).
- **Verify gate:** crews-on-fixture-wiki tests in `kedro-test`.
- **Depends on:** H1.
- **DELIVERED (2026-07-18):** `factory/crews.py` — `CompileCrew` (raw→compiled, per-doc-resilient, forwards source staleness from BOTH the inline `stale:` frontmatter AND the `.staleness.json` sidecar into compiled frontmatter + a visible body banner — AD-13/AD-22, republication never launders freshness), `LintCrew` (reports `missing-frontmatter`/`missing-title`/`empty-body`/`broken-link` [path-resolved, recursive]/`laundered-staleness`/`malformed-frontmatter`; never raises), `QACrew` (grounded answers over compiled content; deterministic keyword retriever + extractive synthesizer defaults). agno-Agent/LLM synthesis + F3-vss production retriever are injectable seams, offline by default — live bring-up DEFERRED (DW-H2). Gate `tests/factory/test_crews.py` (26). AD-1 import-ban green (yaml+stdlib only). An independent adversarial review found 2 MUST-FIX (inline-staleness laundering; lint/QA crash-on-malformed) + 1 SHOULD-FIX (leaf-only broken-link) — all fixed + regression-tested before merge.

**Deferred-work ledger (H2):**

## DW-H2 — the live `agno`-Agent / LLM synthesis + F3-vss production retriever bring-up (ATTENDED) — DEFERRED
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story H2, § 7.3, FR-22(b))
  summary: H2 shipped the three wiki crews (`factory/crews.py`: `CompileCrew`, `LintCrew`,
    `QACrew`) with their DETERMINISTIC cores running fully offline on a fixture wiki — the real
    raw→compiled→answer flow, staleness propagation, and lint rules all exercised with NO network
    and NO model. Two production seams are INJECTABLE and default to the offline path, so the
    live bring-up is the attended deferral (mirrors DW-D3-1 LLM backend + DW-F3-2 vss provisioning):
    (1) **the `agno`-Agent / LLM synthesis** — `CompileCrew`'s `enricher` and `QACrew`'s
    `synthesizer` default to offline determinism (identity enrich; extractive answer). Standing up
    a real `agno` Agent over a resolved model backend (`pyforge.atlas.nl.backend.resolve_backend`
    — repo model-backend routing, env-driven, never a hardcoded endpoint) and running the crews
    through it is the deferred generative path; (2) **the F3 vss production retriever** —
    `QACrew`'s `retriever` defaults to the offline deterministic keyword-overlap ranker; the
    production retriever is `rag.store.DuckdbVssRagStore.similarity_search` (AD-4 single engine)
    wrapped to the `Retriever` signature, which needs the vss extension provisioned (DW-F3-2). Do
    NOT weaken the H2 gate to call a live model or bind a socket (NFR-12).
  evidence: `factory/crews.py` imports only `yaml` + stdlib + `.wiki` (AD-1 import-ban green over
    the new module); `tests/factory/test_crews.py` exercises compile/lint/Q&A + staleness
    propagation offline (26 crew tests). `Enricher`/`Synthesizer`/`Retriever` are the injectable
    seams; their defaults (`_identity_enricher`, `_extractive_synthesizer`, `keyword_retriever`)
    are offline. No `agno` Agent is constructed and no model/vss is loaded in-package.

---

## Story H3

### Story H3 (9.3): Integrate La Suite Docs REST API Sync

As the operator,
I want `LaSuiteClient` + `WikiSyncer` pushing compiled wiki files to the Layer-1 CMS via the Wagtail/Django REST API,
So that humans read the factory's knowledge in the presentation layer.

**Acceptance Criteria:** (spec § 9 Story H3, binding)

**Given** the H2 compiled wiki output and a mock Wagtail API
**When** the sync runs
**Then** a round-trip fixture test passes against the mock (push, update, idempotent re-push).

- **FRs:** FR-22(c).
- **Invariants:** AD-22 (writes only wiki/CMS; idempotent re-push).
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** mock-Wagtail round-trip fixture in `kedro-test`.
- **Depends on:** H1, H2.
- **DELIVERED (2026-07-18):** `factory/lasuite.py` — `LaSuiteClient` (create/update/get/list over the Wagtail/Django REST shape; clear `LaSuiteError` on non-2xx AND on a 2xx-without-id, per § 2.1) + `WikiSyncer` (idempotent **outputs/**→CMS push keyed by content sha: new→create, changed→update, unchanged→SKIP with NO remote call). CMS source is `outputs/` (the Oracle's final reports, per the H1 layout contract + § 7.4), not internal `compiled/` (`source_stage` override available). Transport is the injected `opener` seam — package code holds no HTTP client (AC-2, no-inline-IO gate green); the default opener refuses clearly. Mapping sidecar lives at the wiki ROOT (AD-22), written ATOMICALLY (tmp+os.replace) and corruption-loud on load. Verified against an in-memory mock Wagtail (push/update/idempotent-re-push/mapping-resume). Live Wagtail server + httpx opener bring-up DEFERRED (DW-H3). Independent review found 3 SHOULD-FIX (malformed-2xx KeyError; non-atomic sidecar write; compiled-vs-outputs contract contradiction) + NITs — all fixed + regression-tested. Gate `tests/factory/test_lasuite.py`.

**Deferred-work ledger (H3):**

## DW-H3 — the live La Suite/Wagtail SERVER + credential + httpx opener bring-up (ATTENDED) — DEFERRED
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story H3, § 7.1, FR-22(c))
  summary: H3 shipped the BUILDABLE half of the CMS sync — `factory/lasuite.py`: `LaSuiteClient`
    (create/update/get/list over the Wagtail/Django REST shape) + `WikiSyncer` (idempotent
    compiled-wiki → CMS push keyed by content digest: new→create, changed→update,
    unchanged→SKIP-with-no-remote-call, § 2.1 idempotent-first), verified end-to-end against an
    IN-MEMORY mock Wagtail (push / update / idempotent re-push round-trip, mapping-resume) with NO
    network. The transport is the injected `opener` seam — package code holds NO HTTP client (AC-2,
    enforced by the no-inline-IO gate), exactly like the B5/B7/B8 dataset `refresher`/`fetcher`
    injection. The ACTUAL bring-up is attended: provision the conda-forge Wagtail + django-lasuite
    server (+ PostgreSQL/MinIO from DW-H1), mint an API token, construct the live httpx-backed
    `opener` OUTSIDE package code (a script / the C1 Dagster resource), set `LASUITE_BASE_URL` +
    `LASUITE_API_TOKEN` (host-agnostic, AD-2 — never hardcoded), and run `WikiSyncer.sync_all()`
    against the real CMS. Do NOT weaken the gate to import httpx into package code or bind a socket
    (AC-2 / NFR-12). Mirrors DW-D3-1 (live LLM backend) and DW-C1-1 (live daemon).
  evidence: `factory/lasuite.py` imports only stdlib + `.crews`/`.wiki` (no httpx — the
    no-inline-IO gate `tests/catalog/test_no_inline_io.py` is green over it); the default
    `_unconfigured_opener` raises a clear "no CMS transport injected … inject the live httpx opener
    at the attended bring-up (DW-H3)" rather than reaching for the network.
    `tests/factory/test_lasuite.py` proves the round-trip + idempotency (zero remote calls on an
    unchanged re-push) + mapping-resume against the mock opener. `resolve_lasuite_config` returns
    `None` unless BOTH env vars are set.

---

## Story H4

### Story H4 (9.4): Orchestrate Crews via Dagster

As the operator,
I want Dagster assets, sensors (new raw files), and schedules (weekly linting) triggering the Agno crews autonomously,
So that the factory layer runs itself.

**Acceptance Criteria:** (spec § 9 Story H4, binding)

**Given** the H2 crews and the C1 Dagster repository
**When** the assets/sensors/schedules land
**Then** an asset dry-run enumerates the crew assets
**And** a simulated new-raw-file event triggers the compile crew via a Sensor.

- **FRs:** FR-22(d), FR-6.
- **Invariants:** AD-22, AD-6, AD-23.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** `dagster-dryrun` (crew assets enumerate) + simulated-trigger fixture.
- **Depends on:** H1, H2, H3; C1.
- **DELIVERED (2026-07-18 — closes Wave H + the migration):** the Wave-H crews run on C1's single Dagster plane (AD-6/AD-23). `orchestration/definitions.py` gains crew ASSETS (`compiled_wiki` → CompileCrew, `wiki_lint_report` → LintCrew, `deps=[compiled_wiki]`), their asset-jobs (`wiki_compile_job`/`wiki_lint_job`), a weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`, § 7.2), and the new-raw-file compile SENSOR (`wiki_raw_file_sensor` → `wiki_compile_job`, ships STOPPED). The raw-scan + cursor-dedupe DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds; only definitions.py imports dagster). `dagster definitions validate` green; a simulated new-raw-file event (injected lister + `build_sensor_context`) → one `RunRequest` for the compile job. Live daemon + wiki-store bring-up DEFERRED (DW-H4). Gate `test_definitions_dryrun.py` H4 section (+12; C1/G3 invariants scoped to kedro op-jobs via `_kedro_jobs`). Independent review found 1 SHOULD-FIX (`_decode_cursor` crashed on a valid-JSON-but-nested cursor, breaking its "never a crash" contract) — fixed (filter to str inside the guard) + regression-tested; the `_kedro_jobs` scoping was verified NOT to weaken any C1/G3 guard.

**Deferred-work ledger (H4):**

## DW-H4 — the live factory-crew daemon bring-up (sensor RUNNING + weekly lint + live wiki store) (ATTENDED) — DEFERRED
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story H4, § 7.2, FR-22(d)/FR-6)
  summary: H4 shipped the BUILDABLE half of the factory orchestration — the crew ASSETS
    (`compiled_wiki`, `wiki_lint_report`), their asset-jobs (`wiki_compile_job`, `wiki_lint_job`),
    the weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`), and the new-raw-file compile
    SENSOR (`wiki_raw_file_sensor`) — all wired into C1's `defs` on the SAME Dagster plane
    (AD-6/AD-23; no second scheduler) and verified OFFLINE: `dagster definitions validate` passes,
    the assets enumerate, and a simulated new-raw-file event (injected `raw_lister` +
    `build_sensor_context`) yields one `RunRequest` for the compile job (dedupe/degrade covered).
    The raw-scan DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds;
    only `definitions.py` imports dagster). The ACTUAL bring-up is the attended Q2/daemon event:
    stand up a `dagster-daemon`, turn `wiki_raw_file_sensor` RUNNING against the LIVE wiki store
    (the DW-H1 MinIO/PostgreSQL + `ATLAS_WIKI_ROOT`), let the weekly lint schedule fire, and observe
    real compile/lint crew runs materialize the assets. The sensor ships `default_status=STOPPED`
    (nothing auto-starts). Do NOT weaken the dryrun gate to unattended-execute a live daemon or bind
    a socket (NFR-12). Mirrors DW-C1-1 (live schedule) + DW-G3 (live sensor daemon).
  evidence: `orchestration/wiki_events.py` imports only stdlib (AD-1 import-ban green over it);
    `dagster definitions validate -m pyforge.atlas.orchestration.definitions` passes offline;
    `tests/orchestration/test_definitions_dryrun.py` H4 section (+12: assets enumerate, crew jobs
    resolve, weekly lint schedule, sensor targets the compile job, simulated new-raw-file →
    RunRequest, no-new-file/already-seen → SkipReason, lister-error degrades, ships STOPPED, +
    wiki_events unit tests). The live wiki store is DW-H1; the crews' agno/LLM synthesis is DW-H2.

---
