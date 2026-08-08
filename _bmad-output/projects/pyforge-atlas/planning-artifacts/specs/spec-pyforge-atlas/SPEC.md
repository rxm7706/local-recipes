---
id: SPEC-pyforge-atlas
spec: pyforge-atlas
status: shipped
shipped_scope_note: |
  `shipped` = the 32 stories merged (PRs #69-#102, 2026-07-17/18). It does NOT mean every
  attended boundary event is discharged: the credentialed parity run + legacy retirement
  (DW-B4-2), the F1 cold/warm benchmark (DW-F1-1), and the live Dagster daemon (DW-C1-1,
  DW-G3, DW-H4) are all still outstanding. See § Success signal. Added 2026-07-27 per
  AUD-ATLAS-047 / AUD-ATLAS-049.
owner-dream: docs/dreams/pyforge-atlas.md
covers-dreams:
  - docs/dreams/unity-data-stack.md    # folded in 2026-08-02 as CAP-18..26 (see below); satisfies INV-1 for this Dream
  - docs/dreams/wasm-analytics-stack.md # folded in 2026-08-02 as CAP-27..31 (see below); satisfies INV-1 for this Dream
program: regenerable-factory
# consolidated: 2026-08-02 — this Spec also carries spec-unity-data-stack and
# spec-wasm-analytics-stack (per explicit user override of the dream-level-only
# consolidation convention; see docs/dreams/pyforge-atlas.md § The estate Atlas
# hosts). Their capabilities/constraints/non-goals/success-signal/assumptions/
# open-questions are folded in below under "Satellite:" subsections with
# CAP-n renumbered to continue this Spec's sequence (CAP-18..26 Unity,
# CAP-27..31 Wasm). `surface`, `program`, and `owner-dream` above describe the
# PRIMARY Atlas Spec only — neither satellite has shipped code, so neither
# contributes to `surface` (see each satellite's own surface note, preserved
# in its folded-in section, and its `Satellite: Unity Data Stack` /
# `Satellite: Wasm Analytics Stack` frontmatter block below).
surface:
  - src/shared/packages/pyforge-atlas/**               # the shipped package: conf/, src/pyforge/atlas/, tests/, wasm/
  - src/prototype/packages/pyforge-atlas-kedro-viz/**  # the generated dependency-free DAG mirror (tools/regenerate_from_atlas.py) — moves only when the real DAG moves
companions:
  - signals.md               # the 23 ported phases -> nodes, the 3 additive riders, the Warden boundary on signals
  - catalog-contract.md      # 7 pipelines x 86 datasets, every declared TTL, the two freshness clocks, identity + join keys
  - degradation-contract.md  # the 3 markers, the fixed policy mapping, the frozen exit projection
  - gate-contract.md         # the 7 gates, what each proves and what each refuses to do
  - constitution-provenance.md  # [Unity satellite, folded in 2026-08-02] the 14-Article Constitution map + the 8 required amendments
sources:
  - ../../../../../../docs/dreams/pyforge-atlas.md
  - ../../../../../../docs/dreams/pyforge-charter.md   # § 3 Atlas — the station's standing mandate
  - ../../../../../../docs/specs/cfe-atlas-datapipeline-kedro-migration.md   # LEGACY Tier-1 intake spec (v5.6, status: shipped) — the requirements contract this Spec distils; absorbed and superseded, not adopted
  - ../../prds/prd-pyforge-atlas-2026-07-17/prd.md          # chain: FR-1..FR-22, SM-1..SM-12 + SM-C1..SM-C4, the § 5 non-goal boundary (also carries the Unity + Wasm satellite PRDs verbatim since 2026-08-02)
  - ../../prds/prd-pyforge-atlas-2026-07-17/addendum.md     # chain: intake reconciliations
  - ../../architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md  # chain: AD-1..AD-23, the conventions table, stack, structural seed (also carries the Unity + Wasm satellite spines, renumbered AD-24..56, since 2026-08-02)
  - ../../epics.md                                          # chain: 9 epics / 32 stories with their binding ACs and delivery records
  - ../../../../pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md  # cross-project: owns the ComplianceReport contract this project's policy gate validates against by import
  - ../../briefs/brief-pyforge-atlas-2026-07-25/brief.md    # also carries the Unity + Wasm satellite briefs verbatim since 2026-08-02
  - ../../research/domain-dependency-intelligence-ecosystem-observability-research-2026-07-25.md
  - ../../research/technical-kedro-dagster-duckdb-stack-currency-research-2026-07-25.md
  - ../../../../../../docs/dreams/unity-data-stack.md       # [Unity satellite] archived 2026-08-02, narrative absorbed into pyforge-atlas.md
  - ../../../../../../archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/briefs/brief-unity-data-stack-2026-07-25/brief.md         # [Unity satellite, moved to archive/ 2026-08-02]
  - ../../../../../../archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/briefs/brief-unity-data-stack-2026-07-25/addendum.md      # [Unity satellite, moved to archive/ 2026-08-02]
  - ../../../../../../archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-unity-data-stack-2026-07-25/prd.md               # [Unity satellite, moved to archive/ 2026-08-02]
  - ../../../../../../archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-unity-data-stack-2026-07-25/addendum.md          # [Unity satellite, moved to archive/ 2026-08-02]
  - ../../../../../../docs/dreams/wasm-analytics-stack.md   # [Wasm satellite] archived 2026-08-02, narrative absorbed into pyforge-atlas.md
  - ../../../../../../archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/briefs/brief-wasm-analytics-stack-2026-07-25/brief.md     # [Wasm satellite, moved to archive/ 2026-08-02]
  - ../../../../../../archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-wasm-analytics-stack-2026-07-25/prd.md           # [Wasm satellite, moved to archive/ 2026-08-02]
open_questions: []   # all four of the PRIMARY Atlas Spec's own OQs resolved 2026-07-25 — see § Resolved questions. The two satellites carry their own unresolved open questions — see § Open Questions (satellites), not invented away by this consolidation.
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

> **Consolidated 2026-08-02** — see
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md` and
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`
> for the original standalone documents (moved there intact, not deleted).
> This Spec now also carries the Unity Data Stack and Wasm
> Analytics Stack Spec contracts, folded in as `Satellite:` subsections
> under each of the five fields below, with `CAP-n` renumbered to continue
> this Spec's sequence (`CAP-18`..`CAP-26` Unity, `CAP-27`..`CAP-31` Wasm)
> and cross-referenced `AD-n` renumbered to match the merged
> `ARCHITECTURE-SPINE.md` (`AD-24`..`AD-46` Unity, `AD-47`..`AD-56` Wasm).
> Each satellite's own `FR-n`/`SM-n` numbering (local to its own PRD) is
> **not** renumbered and stays independent of the primary Spec's `FR-1`..`FR-22`.

# Atlas — the intelligence layer an agent workforce can extend

## Why

The Navigator's mandate is *chart the dependencies, map the world, define the floor* — and
the map has to stay drawn by agents, not heroes. The legacy `cf_atlas` orchestrator did ship
real signal for years: 23 cataloged phases building a database over the conda-forge feedstock
population (19,726 at the 2026-07-16 full-population run) — versions, downloads, maintainers,
vulnerabilities, readiness — read through 28 bespoke CLIs and 23 atlas-relevant MCP tools.
Its cost was never acute; it was **chronic and compounding**. Every new phase hand-rolled its
own checkpointing, TTL gating, and backoff. Data lineage lived in one developer's head.
Execution was observable only through stdout. Ad-hoc questions required hand-written SQL
against a single SQLite file. A 1800-second coarse timeout could silently drop a phase and
score the run green.

The load-bearing justification was never performance — it is **agent-maintainability**.
As the factory's workforce shifted from one developer occasionally touching this code to
loop-driven agents adding phase 24 unattended, a ~10,000-line procedural monolith became the
single largest risk to the whole packaging factory's autonomy story. The answer is a
declarative DAG small enough, pure enough, and contract-guarded enough that an agent can add
a signal by writing a node and declaring its datasets, inheriting checkpointing, TTL, backoff,
validation, lineage, and scheduling for free — verified by deterministic fixture gates rather
than tribal knowledge.

The performance story is told honestly and deliberately under-claimed: the cold rebuild is
network-bound, so the win is **incremental re-materialization**, query-time analytics, and
Parquet reads — never an engine-swap cold-start miracle. Atlas is conda-forge-only by name,
serving one operator and one agent workforce; that narrowness is the design, not a gap to
close later.

**2026-08-02 consolidation.** Atlas's project tree also plans two adjacent,
substantial platform initiatives — Unity Data Stack (an enterprise
innersource Python monorepo platform) and Wasm Analytics Stack (a
WASI-sandboxed analytical pipeline for hardened OpenShift) — neither a
capability of the `cf_atlas` pipeline described above, each its own
initiative with its own Why, Capabilities, Constraints, Non-goals, Success
signal, and Assumptions. Both were seeded 2026-07-23 and planned to
PRD + Architecture depth by 2026-07-25; neither has epics/stories or code
yet. Per an explicit user decision on 2026-08-02 (overriding this repo's
default dream-level-only consolidation convention), their full Spec/PRD/
Architecture chains were folded into this station's single Spec/PRD/
Architecture rather than kept as separate chains under the same project
tree. Their content appears below as `Satellite:` subsections under each of
this document's five fields.

## Capabilities

- **CAP-1 — the DAG is the orchestrator**
  - **intent:** Every unit of ingestion or compute is a pure function with declared inputs and
    outputs, and execution order is resolved from the dependency graph rather than called
    procedurally.
  - **success:** The 23 legacy phases run as DAG-resolved nodes across exactly seven typed
    domain pipelines (`core`, `pypi_intelligence`, `vulnerability`, `vcs_health`,
    `universal_sbom`, `seed_gaps`, `derived_artifacts`); each dataset has exactly one producing
    pipeline and consumers reference it by catalog name; the former unregistered side-effect
    (per-version download history) is an explicit node with declared outputs; and the legacy
    per-phase engineering contracts survive the port with their fixtures carried over green.

- **CAP-2 — all IO is catalog-declared, all credentials are host-scoped**
  - **intent:** No node function contains data-access logic, and a credential reaches only the
    host it belongs to.
  - **success:** Every source and output is an entry in `conf/base/catalog.yml`; a static gate
    proves no inline IO remains in node bodies; all 20 `resolve_*_urls`-style override points
    survive as dataset-level endpoint config so an enterprise mirror substitutes without code
    change; and a non-JFrog host provably never receives the JFrog API header — closing the
    legacy global-injection defect rather than porting it.

- **CAP-3 — incremental state is a dataset concern, not a node concern**
  - **intent:** Freshness, resumption, and re-fetch decisions belong to one reusable dataset
    class, so no node ever re-implements them.
  - **success:** `IncrementalParquetDataset` round-trips `*_fetched_at` TTL state; stale rows
    re-fetch and fresh rows skip, proven by unit test; TTLs are declared **per dataset** in the
    catalog (7 d, 30 d, 1 d, 90 d, … — never a global constant); the bespoke `phase_state`
    checkpoint table is deleted, with resumability supplied by the runner plus persisted
    intermediate datasets.

- **CAP-4 — one execution plane, orchestrated and budgeted**
  - **intent:** The operator watches scheduled, retried, per-node-budgeted runs instead of
    tailing stdout, and every entry point rides identical machinery.
  - **success:** The DAG compiles to a single Dagster repository; schedules encode the
    operations cadence table; the three bootstrap profiles (`maintainer` / `admin` /
    `consumer`) exist as named job configurations with explicit run-config beating profile
    defaults; timeouts and retry budgets are **per node**, so an overrunning node can no longer
    abort its siblings — the coarse-cap silent-drop class is structurally retired; the
    highest-cost phase stays admin-config-only behind an explicit enable flag and is never a
    default schedule; and structural lineage renders in the browser via a dedicated task.

- **CAP-5 — event-driven ingestion on the same plane**
  - **intent:** Upstream release activity can pull the pipeline forward incrementally instead
    of waiting for the next scheduled tick.
  - **success:** Sensors watch upstream release feeds and turn a detected event into exactly
    one run request against the *existing* incremental job — no parallel execution path; no
    event yields an explicit skip reason; the decision logic is orchestrator-free and
    unit-testable from a simulated event; and sensors enumerate under the definitions dry-run
    gate.

- **CAP-6 — one engine for compute, graph, and vector**
  - **intent:** Analytical compute, graph traversal, and semantic retrieval all run in the same
    store, over the same canonical files.
  - **success:** Partitioned Parquet is the canonical persistence format and DuckDB the only
    engine — analytical queries, recursive-CTE graph traversal, and `vss` vector similarity
    alike; a grep gate proves no SQLite read or write path survives anywhere in the migrated
    surface; and a similarity query returns ranked results from the same store, with the
    embedding strategy and offline extension provisioning resolved rather than assumed.

- **CAP-7 — retirement earned by recorded parity, not asserted**
  - **intent:** The legacy orchestrator is retired only against evidence a human signed.
  - **success:** A fixture-based, loop-callable parity harness compares migrated Parquet
    outputs against the legacy database tables and reports zero material drift on the
    actionable-package view family (exact row count and value parity; timestamp- and
    ordering-only differences documented benign); the evidence is recorded with human sign-off
    at an attended boundary event; and only then are the legacy orchestrator and its
    checkpoint table marked for retirement.

- **CAP-8 — the read surface is declared once and consumed everywhere**
  - **intent:** Metric logic lives in exactly one place, and every read surface — page,
    natural-language query, agent read — translates through it.
  - **success:** Staleness, adoption stage, feedstock health, and maintainer-role facts are
    declared as semantic-layer dimensions and measures over the catalog (Ibis → DuckDB), with a
    metric-parity gate proving they answer as the legacy CLIs did; **8 dashboard pages ship**
    (the live-confirmed core) plus factory-status, each honest about its state — grounded,
    BSL-wired shell, or no-BSL-model shell — while the **full 28-CLI page inventory is
    CIS-two-spine deferred** (`DW-D2-1`) *(corrected 2026-07-27, `AUD-ATLAS-041`: this clause
    previously claimed all 28 were answerable)*; a natural-language query returns a chart
    grounded in declared metrics; and its language backend routes through repo model-backend
    configuration, never a hardcoded public endpoint.

- **CAP-9 — agents trigger and read the pipeline natively**
  - **intent:** An authoring or execution agent can run a named pipeline and read the resulting
    dataset without a load-bearing plugin between it and the data.
  - **success:** The atlas-relevant MCP tools are authored directly over session and catalog
    APIs and work with the third-party MCP plugin absent; a tool call triggers a named pipeline
    and another reads its output dataset; tool bodies carry dataset passthrough and triggers
    only — no metric or business logic; and a triggered run inherits the same budgets, hooks,
    profiles, and lineage as a scheduled one.

- **CAP-10 — one structured channel between agents**
  - **intent:** Insights, contract violations, and policy breaches move between the analytical
    agent and the recipe-authoring agent as structured payloads, never as prose.
  - **success:** The analytical agent hands a typed payload to the authoring agent over a
    single A2A surface whose schemas live in one module — the sole source for both alerts and
    insights; validation failures and policy breaches raise on that same channel; and payloads
    that feed authoring decisions carry their build timestamp.

- **CAP-11 — bad data halts before it persists**
  - **intent:** A malformed upstream payload stops the run rather than quietly landing in the
    store.
  - **success:** Inline dataframe contracts run behind one validator-agnostic after-node hook;
    a malformed-payload fixture raises a native exception that propagates to the orchestrator,
    halts the pipeline, and raises an A2A alert; and swapping or adding a second validator
    backend requires no node change, proven with a stub validator.

- **CAP-12 — every run is traceable to the API call**
  - **intent:** A failure or a slow run is diagnosable from recorded lineage and traces rather
    than reconstructed by reading source.
  - **success:** Every node emits lineage events carrying rows, latency, and cache hits, and
    participates in an end-to-end trace that resolves down to named API calls; emitted-event
    and span fixtures are the gate assets that prove it.

- **CAP-13 — any manifest becomes one comparable inventory, behind one exit code**
  - **intent:** CI consumes one schema-validated artifact and one exit code instead of scraping
    CLI text.
  - **success:** Every supported manifest format normalizes to CycloneDX preserving the
    `cfe:*` property namespace and the `?channel=conda-forge` qualifier; a bare requirements
    file resolves to a full transitive set with resolution depth and fan-out recorded (offline:
    marked unresolved); the full-universe BOM (~856k components) is a catalog dataset under the
    freshness contract; a matching run reproduces the six-bucket classification on a fixture
    inventory; and one terminal node — the single producer — assembles the four-axis compliance
    report and exits on the frozen convention, halting the orchestrator and alerting on breach.

- **CAP-14 — new signals ride in additively, with their failure modes fixture-pinned**
  - **intent:** A newly ingested signal reaches the read surface without renegotiating the
    migration's parity scope, and without repeating a known measurement error.
  - **success:** Conda-native advisories are ingested by batched query with a bounded detail
    fetch and matched **by package name**, so an advisory tagged with a foreign ecosystem still
    matches its conda package; `fix_available` is tri-state and unknown never collapses to
    false; no surface conflates version currency with security currency; packaging velocity
    derives from the existing join with no new fetch, gated to upstream releases within 90 days
    and computed against **first availability** of the matched version; and migration readiness
    is a four-way split driven by upstream category lists, so a new upstream migration needs
    zero code change and inferred membership is always labeled inferred.

- **CAP-15 — the derived layer regenerates and refuses to go stale**
  - **intent:** Reports and exports are downstream nodes of the rebuild, and a consumer can
    never silently read an old one.
  - **success:** Derived datasets (purl exports, universe BOM, freshness reports) re-run after
    every rebuild and consumers enforce the 14-day dataset-level freshness contract, refusing
    stale input exactly as the legacy gate did; the four seed-gap suggesters are strictly
    read-only report nodes whose byte-identical-seed guarantee survives as a pipeline test; and
    the three separately-built external stores refresh as scheduled assets with retries and
    observability, never written from anywhere else.

- **CAP-16 — the read surface runs with no backend at all**
  - **intent:** The intelligence surface is portable to a browser against a static host.
  - **success:** The dashboard and semantic layer load and query client-side over Parquet
    pulled by HTTP Range from a static host; a headless browser gate loads the built artifact,
    asserts **zero non-loopback requests**, and fails on an in-page error rather than passing
    silently; and the emitter is host-agnostic so an enterprise mirror substitutes for the
    default host.

- **CAP-17 — the knowledge factory maintains itself and never writes back**
  - **intent:** Agent crews compile, lint, publish, and answer over a wiki built from pipeline
    outputs, without becoming a second writer into pipeline data.
  - **success:** The three-stage `raw/ → compiled/ → outputs/` tree exists with a layout
    contract and a traversal guard; the five personas resolve through the customization layers
    and the workforce stays frozen at five (an overlay may refine, never rename or add); the
    compile, lint, and question-answer crews run end-to-end on a fixture wiki; source staleness
    markers are carried forward into compiled output so republication never launders freshness;
    the CMS sync is idempotent by content hash against a mock API; and the crews are triggered
    by the same orchestration plane through assets, a weekly schedule, and a new-file sensor.

### Satellite: Unity Data Stack capabilities

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`
> (status at fold-in: `draft`), renumbered `CAP-1`..`CAP-9` → `CAP-18`..`CAP-26`.
> Success clauses reference this satellite's own `FR-n` (local to
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-unity-data-stack-2026-07-25/prd.md`) and cross-reference `AD-n`
> renumbered to match the merged `ARCHITECTURE-SPINE.md`.

- **CAP-18**
  - **intent:** A platform engineer declares one Workspace root — platform matrix, channels, system-requirement floors, and the set of Packages — from which Environments compose from named Features with no inherited bloat, and every Package carries a declared owner.
  - **success:** FR-1–9 hold: adding a Package requires editing exactly one place; no dependency version string is duplicated; a minimal Environment's installed size is measured against a documented ceiling and a regression fails the gate; Stages are modelled separately from Environments so the number of distinct solves is bounded by genuine dependency variation, not Stage naming (AD-27).
- **CAP-19**
  - **intent:** The Workspace produces one authoritative Workspace Lock covering native and Python packages together, reproducing an Environment offline on every declared platform, with a derived standards-format export and an air-gapped Offline Bundle, and credentials that are host-scoped and never appear in a URL or argument.
  - **success:** FR-10–17 hold: multi-platform coverage is proven by materialization, never assumed (FR-11); the Exported Lock is generated from, and drift-checked against, one pinned Workspace Lock commit SHA, failing the gate on mismatch (FR-12, resolves PRD OQ-1 via AD-25).
- **CAP-20**
  - **intent:** A developer runs one command that executes every check CI executes — lint, format, type checking, coverage thresholds, security scanning, and a tagged behavioural-test tier — with pre-commit mirroring a fast subset.
  - **success:** FR-18–25 hold: a parity check asserts the local and CI check-sets are identical and fails on divergence (AD-32); coverage that decreases relative to the base branch fails the gate.
- **CAP-21**
  - **intent:** Every Constitution Mandate is classified, machine-readably, as a Platform Invariant (no override) or a Domain Default (Domain-overridable with a recorded decision); violations name the clause they violate; amendment is a governed, versioned process.
  - **success:** FR-26–32 hold: an unclassified Mandate, or an override with no linked decision record, fails the Quality Gate (AD-31); the Constitution carries semver, ratified/amended/next-review dates; a coverage report distinguishes automatically-enforced Mandates from human-review-only ones.
- **CAP-22**
  - **intent:** Every Package names a Trusted Committer accountable for reviewing outside contributions, an outside contributor finds a documented path to contribute to code they don't own, and branch/commit/merge conventions are enforced automatically.
  - **success:** FR-33–38 hold: a Package with no Trusted Committer fails the gate; a scaffolded Package or Data Product passes the Quality Gate immediately with no manual fixes (FR-37); cross-team contribution rate and an internal-fork counter-signal are both measured (FR-38).
- **CAP-23**
  - **intent:** Every built artifact carries a versioned SBOM with a populated dependency graph (runtime-scoped and full variants) and a build-provenance attestation, continuously gated against exploitation-aware vulnerability data through one schema-validated Compliance Report, with baselining/grandfathering and opt-in remediation proposals.
  - **success:** FR-39–47 hold, delivered by **integrating** `pyforge-warden` (already a strict superset of the intake approach) rather than reimplementing it; SBOM generation runs against the built artifact and a test asserts a populated transitive dependency edge (AD-34); an artifact with no provenance attestation cannot be promoted to any Stage whose policy requires approval (AD-35).
- **CAP-24**
  - **intent:** Each Domain owns Data Products layered Raw → Curated → Consumption, with an enforced naming convention, a structured metadata contract, and versioned schema contracts; one reference Domain (`customer`) is implemented end to end as the pattern others follow.
  - **success:** FR-48–54 hold: a schema change that breaks a declared consumer is detected before merge, requiring a version increment and migration note (FR-52, AD-39); the reference Domain exercises all three Layers, publishes a contract, and passes every gate — its structure is exactly what the FR-37 scaffolding templates generate.
- **CAP-25**
  - **intent:** Every capability available with public network access is available in Air-Gap Mode (or declares why not); deployment is declarative and environment-promoted under Stage policy; secrets are never committed and are validated present at service startup; a Stage's Data Classification bounds which datastores and network posture it may be configured against.
  - **success:** FR-55–58 hold: a parity test enumerates capabilities and asserts each works air-gapped, targeting 100% with declared exceptions (SM-6); a secret-shaped string committed to the repository fails an automated check (FR-57).
- **CAP-26**
  - **intent:** A developer starts, stops, and inspects the full local service stack — aggregate and per-service — with single commands, and the Workspace names a small, stable public task API.
  - **success:** FR-59–60 hold: status reports actual service health, not process existence; removing or renaming a public task is a breaking change requiring a decision record.

### Satellite: Wasm Analytics Stack capabilities

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`
> (status at fold-in: `final`), renumbered `CAP-1`..`CAP-5` → `CAP-27`..`CAP-31`.
> Success clauses reference this satellite's own `FR-n` (local to
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-wasm-analytics-stack-2026-07-25/prd.md`) and cross-reference `AD-n`
> renumbered to match the merged `ARCHITECTURE-SPINE.md`.

- **CAP-27**
  - **intent:** A business user uploads an `.xlsx` file via an OIDC-authenticated FastAPI endpoint, and its structure and data quality are checked inside a genuine WASI Preview 2 sandbox before any row reaches ingestion, with row-level failures reported precisely and valid rows queued independently of rejected ones.
  - **success:** FR-1–4 hold: an unauthenticated request receives HTTP 401 before the upload body is read; a structurally-invalid file is rejected in full (zero rows reach Bronze); each rejected row's error names the specific column/rule that failed without blocking rows that passed; no row reaches DuckDB Bronze via `dlt` without having passed validation.
- **CAP-28**
  - **intent:** `dbt-duckdb` transforms Bronze into schema-declared Silver and Gold models, emits column-level lineage for every model, and a failing `dbt test` blocks promotion of that model's output to the next layer.
  - **success:** FR-5–7 hold: every `dbt run` is traceable to the Bronze table state it consumed; a lineage query for any Gold column returns its full upstream column chain back to Bronze; a `dbt run` with a failing test does not update the corresponding table and the prior good state remains queryable.
- **CAP-29**
  - **intent:** One W3C trace ID, minted once at the browser/API boundary, correlates OTel spans and OpenLineage facets across every pipeline stage to Marquez via a per-pod Vector sidecar, so a single trace-ID lookup reconstructs the full upload-to-Gold journey with no gaps.
  - **success:** FR-8–11 hold: the trace ID returned to the client at upload time is the same one attached to that upload's eventual Gold-table lineage record; a trace query for any upload returns spans for every stage it passed through with no gap; Marquez returns the full Bronze→Silver→Gold lineage graph; no pipeline container other than the Vector sidecar holds an external telemetry egress path.
- **CAP-30**
  - **intent:** An automated, non-hollow gate mechanically proves the WASI validation component cannot reach any capability beyond its WIT-declared surface, and a build-time check blocks denylisted imports from ever entering the component's dependency closure.
  - **success:** FR-12–13 hold: the gate fails on any host interaction beyond the component's declared WIT imports; deliberately widening the component's declared capabilities without a corresponding WIT change makes the gate fail, proving it checks something rather than always passing; adding a denylisted import (`numpy`, `pandas`, `pyarrow`, `pydantic`, or any other C-extension-backed or `componentize-py`-unproven package) fails `pixi run build`, not a later runtime error.
- **CAP-31**
  - **intent:** One Pixi toolchain builds every artifact the pipeline needs, including the compiled WASI component, and the same security context runs identically under a Podman digital twin and OpenShift Restricted SCC, with DuckDB state persisted via a `ReadWriteOnce` PVC at a consistent mount path.
  - **success:** FR-14–17 hold: a clean checkout plus `pixi install && pixi run build` produces a runnable digital twin with no manual steps outside Pixi; every container starts as non-root UID 1001 with a read-only root filesystem in both the digital twin and OCP; the Helm chart's security context matches Restricted SCC exactly with no `anyuid` or other elevated binding requested; pipeline restarts do not lose previously-ingested Bronze/Silver/Gold data.

## Constraints

- **Atlas measures; Warden judges.** An upstream-maintenance signal
  (OpenSSF-Scorecard class) is a **Warden axis**, never an Atlas gate — Atlas may
  join and expose it as a feed, but the verdict is not Atlas's to render.
  `pyforge-warden` already names six axes (hygiene · security · license ·
  currency · provenance · **maintenance**), gating the first four in v1. This is
  the Charter's *the hand that builds is never the gate that judges* applied to
  signals: it rules out scoring or thresholding any maintenance metric here.
  *(Resolved 2026-07-25 from the Warden contract; no operator decision required.)*

- **The DAG is the single source of truth; every orchestration and surface plugin is
  replaceable glue.** Pipeline structure, node logic, and dataset declarations live only in the
  Kedro project. The Dagster binding, the MCP plugin, and the semantic-layer binding are thin
  adapters a single story could swap without touching nodes or catalog — the named exit ramps
  are recorded. No node, dataset, hook, or MCP module may import the orchestrator's or the
  plugin's APIs, enforced by an import-direction meta-test shipped with the catalog gate. This
  is why a single-maintainer plugin is an acceptable dependency and not an existential one.
- **One execution plane.** Budgets (per-node timeout and retry), validation hooks, lineage and
  trace instrumentation, and profile definitions are declared in run configuration, so every
  entry point — scheduled job, sensor, MCP trigger, CLI — executes the identical named pipeline
  with identical machinery; an MCP trigger names a profile explicitly or inherits `maintainer`.
  **Run admission IS implemented** *(shipped 2026-07-29, Story 10.6, closing `DW-AD23-1` /
  `AUD-ATLAS-046`; it was correctly recorded as unimplemented between 2026-07-27 and then)*. A
  dataset has one writing run at a time: `pyforge.atlas.admission.RunAdmissionHooks`, registered
  in `settings.HOOKS`, takes one OS file lock per output dataset in `before_pipeline_run` and
  releases in both `after_pipeline_run` and `on_pipeline_error`. Two concurrent triggers of the
  same dataset set — an MCP trigger racing a CLI run, or two MCP triggers — are rejected fast
  with a typed error naming the holder, or retried to a finite deadline if the run explicitly asked for a bounded wait (a poll on the lock — no queue, no ordering or fairness guarantee)
  (`--params admission_wait_seconds=<n>`); they are never interleaved. Granularity is the
  pipeline's declared output set — concretely `pipeline.all_outputs()`, a deliberate superset that
  includes in-run intermediates because over-locking fails safe — so genuinely disjoint pipelines
  still run concurrently. The
  `in_process` executor in `conf/base/dagster.yml` remains what serializes ops *within* a single
  run — a different property, and on the Dagster plane a load-bearing one (`DW-AD23-2`). Four
  boundaries stand: file locks are single-machine (NFS `flock` is unreliable); release on the
  Dagster plane is process-local, and a *failed* Dagster run releases nothing in-process at all
  (its `on_pipeline_error` fires in the daemon, not the run worker); because kedro calls
  `before_pipeline_run` outside its `try` with admission dispatched first, a later before-hook
  that raises leaves the locks held until the process exits — as does a non-`Exception` exit
  from the runner, which kedro's `except Exception` does not catch and which therefore reaches
  neither `on_pipeline_error` nor `after_pipeline_run` — an availability wedge for the
  long-lived MCP server, not a correctness hole; and unlinking a lock file out from under its
  holder does not free that holder's flock, so the next acquirer takes a fresh inode at the
  same path — two writers, silently. That last one is a property of `flock`, not a
  configuration choice, and `DW-AD23-3` removed the routine way to trigger it: the store is
  the data tree's SIBLING (`<data_root>.locks`), not its child, so `rm -rf data/` cannot reach
  it, and a `PYFORGE_ATLAS_LOCK_ROOT` that would put it back inside is refused.
  Admission's first-dispatch position is enforced
  by `@hook_impl(tryfirst=True)`, not by its place in the `settings.HOOKS` tuple, which
  entry-point plugins would otherwise outrank.
- **No data-access logic in a node body, ever.** Sources, outputs, credentials, endpoints, and
  physical layout are catalog concerns; nodes are pure functions taking and returning
  dataframes. Credentials attach to a dataset's destination host only. Nodes carry no retries,
  no backoff, and no checkpointing — those are dataset and orchestrator concerns.
- **Offline degradation is skip-and-mark-stale, never raise.** When its endpoint is
  unreachable, an external-source node skips gracefully, **keeps the last-good dataset intact**
  (it never writes an empty dataset over it), and stamps a machine-readable staleness marker in
  dataset metadata. Consumers surface the marker and apply the freshness contract: data stale
  beyond its bound degrades the affected read or policy axis to `indeterminate`, never a silent
  pass. The consumer profile is fully offline by design. New external sources bind the standard
  rate-limit discipline: concurrency cap, `Retry-After` plus jittered backoff, remaining quota
  surfaced to the schedule.
- **New-signal datasets are additive riders and are excluded from the parity gate.** Parity
  compares legacy-surface outputs only; the conda-native vulnerability, velocity, and
  migration-readiness datasets are never parity-gated, and a parity delay does not block them.
  Their correctness is held instead by fixture-enforced binding guards — one per measured
  failure mode. The three riders and their pinned failure modes: `signals.md`.
- **Velocity qualifies on a 90-day window and computes against first availability.** A
  version-unchanged package whose upstream release is older than 90 days is excluded
  (`release_lag_qualifies = false`) — the guard against the false "half the channel is behind"
  reading. Lag is computed against the **minimum per-build repodata timestamp** for the matched
  version, never the latest upload, so a rebuild of the same version inside the window cannot
  shift the measurement. Both failure modes are fixture-pinned.
- **`version_status.v2.json` is deliberately excluded** from the migration-readiness ingest.
  Readiness is driven by the upstream `status/` category lists plus per-migration detail, so a
  new upstream migration requires zero code change; the aggregate file is not a source, and
  `not-in-tracker` membership is always labeled **inferred**, never reported as confirmed
  tracker status.
- **Seven closed domain pipelines; the producer owns the dataset.** The pipeline set is fixed.
  Each dataset has exactly one producing pipeline; a new signal joins its assigned pipeline,
  never a new ad-hoc one. Two pipelines writing one dataset is the failure this rules out.
  Allocation, every declared TTL, and the two freshness clocks: `catalog-contract.md`.
- **One store, one engine.** Partitioned Parquet is canonical and DuckDB is the only compute,
  graph, and vector engine — no separate graph, vector, or dataframe engine is reintroduced,
  and no dual store survives. Performance claims stay honestly scoped: incremental
  re-materialization is the headline; cold-start is benchmarked, never promised.
- **The legacy behavioral contracts bind the ports.** The shipped, fixture-guarded behaviors
  port intact with their fixtures green — the two-layer query-cost gate, the single-worker
  token bucket, provenance discipline on download sources, the serial gate, dedicated-feedstock
  attribution, no-clobber writeback, the KEV overlay and score-type unwrap, the `cfe:*`
  namespace and channel qualifier (never stripped), percentile normalization, view-validity
  discipline, and the single-write-path property. A story instruction never overrides these.
  The per-phase port map and the four contracts most often misread: `signals.md`.
- **The semantic layer is the single translation interface.** Metrics and dimensions are
  declared once; read surfaces consume them and never write raw SQL against the store. Catalog
  dataset passthrough for agent reads is not a metric surface and computes nothing. MCP tool
  bodies carry no metric or business logic — metric semantics live in exactly one place per era,
  with the parity gate anchoring the handover.
- **Validation is validator-agnostic and version-capped by policy.** Inline dataframe contracts
  are the primary layer; the boundary validator participates only behind the same hook and only
  at its pinned version — the cap is a policy statement, not merely a pin, and no story may
  depend on features above it. The validator-integration plugins are banned. A contract
  violation raises a native exception; the policy gate fails with identical semantics.
- **One frozen exit-code convention, one report producer.** Exit 0 pass / 1 policy-fail / 2
  error over the closed enum `{0, 1, 2, 130}`, with `indeterminate` projecting to 1, everywhere
  a CLI or gate exits. The compliance report is Warden's four-axis schema **unmodified and
  consumed by import** through an optional extra — never a vendored copy, so drift is impossible
  by construction. Exactly one terminal node assembles every report; upstream pipelines produce
  inputs and never assemble. Absent the extra, the gate node fails with an explicit install
  hint while every other pipeline runs.
- **Exactly one cross-package code edge, and it points one way.** This project may depend on
  `pyforge-warden` only through the optional gate extra; `pyforge-warden` never imports this
  package. Warden's consumption of atlas *data* is data-level and optional-if-present. Both
  tools install and run independently.
- **Gates are fixtures, never credentials — and are never weakened.** Every wave's first
  deliverable is its own deterministic gate; all gates are fixture-based, non-credentialed, run
  frozen, and live in the tracked test tree, never in the gitignored runtime data directory.
  The verify set grows and never shrinks. Gates are never weakened, removed, or demoted from
  attended to unattended to raise the autonomy share — attended boundary events are features,
  not friction. Credentialed runs are attended-only. The enumerated set — what each gate proves
  and what each refuses to do: `gate-contract.md`.
- **Pipeline snapshots are advisory, never authoritative for authoring.** Before acting, the
  recipe-authoring loop re-verifies live; no surface may position its datasets as a substitute
  for that check, and payloads feeding authoring decisions carry their build timestamp.
- **The factory layer consumes; it never writes atlas data.** Wiki and CMS components read
  pipeline outputs through the catalog and semantic layer and write only the wiki tree and the
  CMS; wiki outputs carry their source datasets' staleness markers forward, so republication
  never launders freshness.
- **Scope is closed at the committed source set.** New external data sources beyond the
  committed set are out of the migration's universe; candidate feeds are recorded, never
  committed, and promotion requires measured evidence becoming a requirement and a story.
  Static seeds, template trees, live authoring-time fetches, and user-supplied inputs are
  declared **inputs**, never pipeline products.
- **Identity and format conventions are fixed and non-negotiable.** Conda purls carry the
  channel qualifier; the `cfe:*` property namespace is preserved; versions compare by PEP 440;
  percentiles are stored on one scale; all timestamps normalize to epoch seconds **at the
  dataset boundary** (millisecond repodata values convert once). Canonical join keys are
  `conda_name` (plus feedstock attribution where it applies), `pypi_name`, and
  `(conda_name, advisory_id)`; the name-mapping dataset is the only bridge; **purls are
  interchange identity and never internal join keys**. Full identity table: `catalog-contract.md`.
- **Dataset schema evolution is additive-first.** New columns are nullable; a breaking change
  to a persisted dataset requires, in the same story, a catalog version note plus a migration
  node or re-materialization plus updated contracts and fixtures. No global schema-version
  constant returns.
- **Three degradation markers, never interchanged:** `stale` (dataset freshness) · `unresolved`
  (a resolver could not run) · `not-applicable` (nothing existed to assess). The policy mapping
  is fixed: `not-applicable` reports not-applicable; `unresolved` or stale-beyond-contract
  routes to `indeterminate`. Full projection and the Warden boundary: `degradation-contract.md`.
- **Conda-forge-only, pixi-managed, py3.14-floored provisioning.** Every component is
  conda-forge-sourced, pixi-managed, and scaffolded by the project generator; no standalone
  binaries and no JVM. Two PyPI-sourced components are **recorded exceptions** with packaging
  them as a candidate task — no further PyPI additions without the same recorded treatment. The
  package ships its own lean environment so loop worktrees never materialize the repo's fat
  environment, and any dependency change updates the library catalog in the same change.
- **Tracked config versus local config is a hard boundary.** Base configuration is tracked;
  local configuration holds credentials and is gitignored. Explicit environment or run-config
  always beats a profile default.
- **This Spec governs its code surface.** A change under the declared surface that does not
  move this Spec's memlog is a checker finding — the migration's code cannot drift out from
  under its contract. Behavioral change flows through this project's BMAD chain (stories,
  correct-course), and the chain companions above carry the per-requirement detail this
  contract compresses.
- **Conda-forge work inside this surface is skill-governed.** Any story touching recipe code or
  the packaging skill invokes the `conda-forge-expert` skill, and an effort closes with its
  retrospective — the repo's standing Rules 1 and 2, which this contract does not override.

### Satellite: Unity Data Stack constraints

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`,
> with `AD-n` renumbered to match the merged `ARCHITECTURE-SPINE.md`.

- **One authoritative lock (AD-25):** exactly one Workspace Lock (conda+PyPI together) is authoritative and committed; every other lock artifact (Exported Lock, Offline Bundle) is generated from it and drift-checked against one pinned commit SHA per release — never hand-edited, never a second resolution input.
- **Materialized coverage, never inferred (AD-26):** for every declared platform × every deployable Environment, a gate materializes the Environment from the lock and fails if it cannot; coverage is reported per platform, never as a single boolean.
- **One-way dependency direction (AD-30):** dependencies flow shared → platform-infrastructure → domain, never upward or sideways between Domains; a Domain consumes another Domain's *published* Data Product/API only, never its Package or datastore directly; a cycle detector runs in the Quality Gate.
- **Every Mandate machine-classified (AD-31):** each Constitution Mandate carries a stable identifier and a classification of exactly `platform-invariant` or `domain-default`; an unclassified Mandate, or a check with no declared Mandate, fails the Quality Gate.
- **Tasks, not inline commands (AD-32):** every gate check is a named task with a globally unique name; CI invokes task names only — no inline tool invocation, no inline installation, no environment mutation; a parity check and a name-uniqueness check both run in the gate.
- **Host-scoped credentials (AD-33):** credentials live only in the credential store or masked runner inputs; no committed file contains a credential-bearing URL in any form; no process receives a credential as a command-line argument; a request attaches a credential only when its host matches.
- **Lean-by-declaration Environments (AD-36):** every deployable Environment inherits no default dependency set and composes only what it names; installed size is measured against a recorded ceiling and a regression fails the gate (exempt: the FR-7 compatibility-detection Environment, explicitly non-deployable).
- **One accountable station per plane (AD-40):** each plane and cross-cutting concern resolves to exactly one pyforge-crew station (Marshal / Atlas / Warden / Mason / Steward / Doctor / Scribe / Herald); an unowned capability, or one claimed by two stations, is a defect — full map in the architecture-spine companion.
- **The Constitution's 14 Articles are the requirement spine.** Every FR traces to an Article or to its explicit disposition; 8 amendments are required before re-ratification. Full Article map and the 8 amendments are in `constitution-provenance.md` — not restated here.
- **The intake toolchain spec's flagship lock command does not exist:** `pdm export --format pylock --override-platform=...` has no such flag on `pdm export` (verified 2026-07-25); that exact mechanism cannot be reused as written, and PEP 751 itself does not guarantee multi-platform coverage — this is the empirical grounding for AD-25/AD-26 replacing an unverified format guarantee with gate-verified materialization. Detail in `constitution-provenance.md`.
- **Compliance by integration, not reimplementation (AD-29):** the compliance capability is `pyforge-warden`, consumed as a CLI in its own lean, isolated Environment — never imported as a library, never invoked only in CI; the gate's exit code derives from its Compliance Report file.
- **Python targets revised (Constitution Art. XIV amendment):** primary targets are 3.13 and 3.14; 3.12 is legacy-consumer-only (security-phase upstream); 3.15 first-releases 2026-10-01 and must be planned for inside this horizon.

### Satellite: Wasm Analytics Stack constraints

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`,
> with `AD-n` renumbered to match the merged `ARCHITECTURE-SPINE.md`.

- **Maturity verdict (the project's central scoping fact):** DuckDB's native engine has no WASI build and no WASI roadmap upstream, so `dlt`, `dbt-duckdb`, and DuckDB itself cannot run inside a genuine WASI component today. The WASI sandbox is therefore scoped narrowly to the pure-Python upload-validation step only; a future `wasm32-wasi` build target for ingestion or transform requires an ADR amendment citing new upstream evidence, not an incremental extension of this project.
- **AD-47, trust-boundary data shape:** the validation component's WIT interface accepts and returns only primitive/record types (strings, numbers, booleans, lists, records) — never a host-shared-memory or buffer type. No Arrow buffers, no raw Excel bytes cross the WIT boundary; Excel bytes are parsed into rows entirely outside the sandbox, before the WIT call.
- **AD-48, denylist is a build gate:** `pixi run build` runs a static-import-scan against the validation component's source and its resolved dependency closure, failing the build — not merely a policy or PR-review expectation — on any denylisted import, direct or transitive.
- **AD-50, the isolation gate must be non-hollow:** it ships with a meta-test from its first version — deliberately widening the component's declared WIT capabilities without a matching interface change must make the gate fail — and it runs on every build.
- **AD-51, one trace-ID field:** `upload_trace_id` is always the bare 32-hex-character W3C trace-id (never the full `traceparent` string, never a UUID, never dashed), minted once at FastAPI ingress, and is never conflated with OpenLineage's own separately-minted `runId`.
- **AD-52, one securityContext, two consumers:** a single canonical security-context definition is authored once under `deploy/`; the Helm chart and the Podman compose file both consume it via a generation step, neither hand-authors its own copy.
- **AD-53, DuckDB single-writer:** each validated upload triggers exactly one `dlt` load followed by exactly one `dbt run` scoped to that load — 1:1, never batched — both invoked sequentially by the same owning process; a move to concurrent or batched transforms is a scope change requiring an ADR amendment.
- **AD-54, air-gap-routable dependency fetch:** every build-time fetch (Pixi packages, DuckDB extensions, the `componentize-py`/Wasmtime toolchain) routes through the configured channel/mirror; no build script hardcodes a public URL.
- **AD-55, synchronous upload:** `POST /upload/excel` blocks through parsing, WASI validation, and returns the full per-row result in one HTTP response; the returned trace ID is a correlation handle for observability/lineage lookups, not a polling handle — there is no V1 polling endpoint.
- **AD-56, authentication at the ingress boundary:** OIDC token validation happens at a sidecar/gateway boundary in front of `apps/api/`, never embedded per-request inside the application code itself.

### Reconciliation notes (2026-08-02 consolidation)

No contradiction was found between the primary Atlas contract and either
satellite's non-goals/constraints — the three bodies of work govern
disjoint code surfaces (Atlas: `src/shared/packages/pyforge-atlas/**`;
Unity: `constitution.md`/`config/**`/`templates/**` at an as-yet-unbuilt
repository root; Wasm: `apps/**`/`deploy/**` at an as-yet-unbuilt repository
root), so no rule in one binds code the other two own. One difference is
worth naming explicitly rather than leaving implicit: **the three bodies of
work commit to three different Python floors** — Atlas is conda-forge-only,
pixi-managed, and **py3.14-floored** (exact-minor pinned, shipped); Unity's
Constitution Art. XIV amendment targets **primary 3.13/3.14, 3.12
legacy-consumer-only**; Wasm's host/pipeline processes pin **3.12** as a
deliberately conservative, explicitly revisitable stability floor (nothing
in its pinned dependency set forces it). This is not a conflict to resolve
— each project owns its own environment and dependency closure — but a
reader of this merged Spec should not assume one floor applies across all
three.

## Non-goals

- **A public, versioned API tier** — access is agent-mediated (MCP + `a2a`) and
  no HTTP surface exists. **Deferred, not refused**: it is committed as a real
  future capability, tracked as **DC-1** in the PRD § 6.4. Non-goal *for this
  scope*, not forever.
- **Live production bring-ups** — Dagster daemon, MinIO/PostgreSQL servers, live
  Wagtail, agno LLM synthesis, and the production `vss` retriever each ship a
  seam and run against local/embedded defaults. Tracked as **DC-2…DC-6** in the
  PRD § 6.4. *(Each was properly deferred at build time — `DW-C1-1`/`DW-G3`,
  `DW-H1`…`DW-H4`. The live Tier-3 ledger is truncated to 9 and gitignored, but the
  complete set of **52** is consolidated and tracked at
  `planning-artifacts/deferred-work-ledger.md`; DC-2…DC-6 are the contract-level
  re-statement of the six that outlived the migration.)*

- **A separate graph, vector, or dataframe engine** — one engine, by decision, not by omission.
- **Continued SQLite and hand-rolled checkpoint-table orchestration.**
- **Standalone binaries or JVM dependencies**, and any non-conda-forge provisioning path
  outside the two recorded exceptions.
- **An alternative agent framework** — the BMAD method governs execution.
- **New external data sources beyond the committed set**, and any candidate-feed promotion
  without measured evidence. Do not ship "more sources" to look busier.
- **A metadata backend swap to the upstream GraphQL API** (a recorded hook only, for the
  deferred full yanked-status detection).
- **A public OSV-format export feed and public dashboard productization** — demand is feeds over
  pages; the single factory-status page is the intentionally narrow public surface and does not
  grow.
- **Enterprise manifest generation as a deliverable** — the graph enables it; this does not
  build it.
- **Spreadsheet tabs and project boards as SBOM-intake formats.**
- **Building the compliance-report schema** — it is Warden's contract, consumed by import.
- **Rewriting the recipe-authoring skill itself.**
- **Chasing cold-start wall-clock**, raising the autonomy share by weakening gates, growing the
  signal count for its own sake, or growing dashboard breadth — the four standing anti-metrics.
- **Live authoring-time fetches as pipeline data** — transactional by nature, and pipeline
  snapshots never substitute for the authoring loop's live re-verification.
- **The upstream-discovery surface** — trending and org-audit ingestion is a separate Spec in
  this project (`spec-upstream-discovery`) and was never absorbed into this migration's stories.
- **A unified observation view** across the loop TUI, the BMAD artifact dashboards, and the
  pipeline UIs — three deliberately unjoined planes.

### Satellite: Unity Data Stack non-goals

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`.

- Unity is not an Internal Developer Portal — no catalog UI, no service-discovery portal; it emits catalog-consumable facts, an adopter running Backstage integrates rather than migrates.
- Unity is not a build-graph engine — no attempt to out-cache Pants, Bazel, or Nx on fine-grained caching or remote execution; orthogonal and unwinnable.
- Unity does not maintain a second registry of truth — manifests are the source; catalogs, ownership maps, and portal feeds are all derived.
- Unity is not a product to be sold — it is a platform an enterprise runs.
- Unity does not replace a Domain's judgement about its own data models — global interoperability concerns are Platform Invariants, local modelling is a Domain Default.
- Unity does not target SLSA Build L3 in v1 — L1 mandatory, L2 goal; L3 needs hardened builders, deferred.
- Unity does not perform data-content inspection in v1 — Data Classification is enforced at the configuration boundary only (which datastore, which network), not content-level PII detection/masking/deletion.
- Unity is not a general-purpose polyglot monorepo — Python-first by mandate.
- Bootstrapping new Unity instances — depends on `pyforge-genesis`, unbuilt; a v2 dependency.
- Local Kubernetes development — the required cluster tool isn't available through the mandated channel on every platform; the intake root's documented stub stands.

### Satellite: Wasm Analytics Stack non-goals

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`.

- A general-purpose Wasm-sandboxing framework for arbitrary third-party logic — the WASI boundary in v1 is scoped exclusively to the Excel-upload validation step.
- Running `dlt`, `dbt`, or DuckDB itself inside a WASI Preview 2 sandbox — blocked at the DuckDB-dependency level per the technical research, not a scoping choice to revisit without new upstream evidence.
- Apache Arrow buffers as the host↔WASI-component interchange format — deferred pending a confirmed `pyarrow`-in-WASI path or an Arrow-maintained WASM/WASI interchange primitive.
- A browser-side query/dashboard surface onto Gold tables — v2, would reuse the `pyforge-atlas` G1 DuckDB-WASM/Pyodide pattern directly rather than reinvent it.
- A general ingestion platform for arbitrary source types — Excel upload is the only ingestion path in v1.
- Multi-tenant Unity Data Stack platform integration — a kinship, not a v1 commitment.
- Migration to `dbt Fusion` (the Rust engine) — blocked until it gains a DuckDB adapter; a watch item, not scheduled.

## Success signal

An agent adds a new signal by writing a node, declaring its datasets, and attaching a
contract — and inherits checkpointing, TTL, backoff, scheduling, validation, lineage, and
tracing without writing one line of any of them. That is the whole bet, and it is proven
mechanically rather than asserted.

Six deterministic, non-credentialed, fixture-based gates hold the contract, each shipped as its
wave's first deliverable and never weakened afterward: `kedro-test` (unit and contract
fixtures, including the namespace-package import smoke), `kedro-catalog-check` (the catalog
resolves; **no inline IO** survives in node bodies; the import-direction ban holds; the 20
override points and per-host credential scoping are asserted), `parity-diff` (fixture mode
in-loop, credentialed full run at the attended boundary), `dagster-dryrun` (definitions load;
jobs, schedules, and sensors enumerate without live execution), `bsl-metric-check` (declared
metrics answer as the legacy CLIs did), and `wasm-smoke` (a headless browser loads the built
artifact, asserts zero non-loopback requests, and fails on an in-page error). Beside them: a
grep gate proving no SQLite path survives the migrated surface, exit-code and schema fixtures on
the policy gate, a byte-identical-seed test on the read-only suggesters, and one fixture per
named measurement failure mode on the new signals.

The shipped evidence: **32 of 32 stories across Waves 0 and A–H, merged through PRs #69–#102,
2026-07-17/18** (#74 and #89 in that range belong to other efforts; #103 is the CFE Rule-2 retro
closeout and #105 a follow-up review sweep) — the parity **harness** delivered and
fixture-green, three new
signals landed through declared machinery with zero hand-written checkpoint code, and every
loop-driven story executed without a gate being removed to get there.

**What `shipped` does and does not mean** *(added 2026-07-27, `AUD-ATLAS-047` / `AUD-ATLAS-049`)*.
`status: shipped` means **the 32 stories merged** — not that every attended boundary event has
been discharged. Three remain outstanding as of 2026-07-27:

- **The credentialed parity run, operator sign-off, and legacy retirement have not occurred.**
  `conda_forge_atlas.py` remains live at ~402 KB; the retirement gate refuses fixture mode by
  design (`DW-B4-2`). This section previously read "parity recorded and signed before the legacy
  orchestrator retired" — that was an overclaim.
- **The F1 cold/warm benchmark was never run** (`DW-F1-1`). The DuckDB-singularity half of F1
  shipped; the performance half did not. Per SM-3 the pass threshold must be fixed in the story
  spec *before* the benchmark runs.
- **The live Dagster daemon has never ticked** a schedule or sensor (`DW-C1-1`, `DW-G3`,
  `DW-H4`); definitions build and validate offline only.

### Satellite: Unity Data Stack success signal

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`
> (status: planning-complete, unscheduled — no epics/stories/code yet; SM-n
> below is local to `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-unity-data-stack-2026-07-25/prd.md`).

Onboarding: a new engineer reaches a running local stack with a passing package test using only written documentation, in under an hour, single-digit commands (SM-1). Cross-team reuse — the innersource proof — trends up (contributions merged into Packages the contributor doesn't own) while the internal-fork counter-metric does not rise in step (SM-2 vs. SM-C1); if it stays near zero, the platform has failed at its premise regardless of technical quality. Reproducibility is verified, not assumed: 100% of declared platforms materialize every Environment from the lock, online and offline (SM-4). Compliance latency — time from vulnerability publication to a determination of estate impact — is measured in minutes, ahead of the EU CRA's 2026-09-11 reporting-obligation deadline (SM-5). Air-gap parity reaches 100% of enumerated capabilities, with any exception explicitly declared, never silently degraded (SM-6).

### Satellite: Wasm Analytics Stack success signal

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`
> (status: planning-complete, unscheduled — no epics/stories/code yet; SM-n
> below is local to `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-wasm-analytics-stack-2026-07-25/prd.md`; `CAP-27`
> below was `CAP-1` in the standalone document).

The seed use case — Excel upload → WASI-validated → DuckDB Bronze → Silver/Gold via `dbt`, traced end-to-end — runs correctly and identically under `podman --read-only --user 1001` locally and under real OpenShift Restricted SCC, with the WASI validation component's sandboxing mechanically verified, not just asserted (SM-1). The Isolation-Verification Gate passes on every build and demonstrably fails when the component's declared capability surface is deliberately widened without a corresponding WIT change — the non-hollow-gate proof (SM-2). The project ships zero claims beyond what the technical research verified as buildable today. Two counter-metrics guard against gaming the primary signals: growing workaround complexity in the denylist (SM-C1) is a signal to reconsider the WASI-sandboxing bet, not a target to minimize by weakening the boundary; and upload-validation latency must never be optimized by moving checks out of the sandbox back into the trusted process (SM-C2), which would defeat CAP-27's entire purpose.

## Assumptions

- The story set is **complete** (32/32, 2026-07-18), so this contract is written in the present
  tense as a standing description of what Atlas is, not a plan for building it.
- The stack bets remain current: a 2026-07-25 currency review found every component actively
  maintained with no deprecations. The orchestration binding's single-maintainer bus factor is a
  confirmed **watch item**, not an active problem — the recorded exit ramps are the standing
  mitigation, and the replaceable-glue constraint is what makes them cheap.
- Scope discipline — conda-forge-only, one operator plus an agent workforce — is a deliberate
  design choice validated against the general-purpose cross-ecosystem comparables, not a gap.
  Those platforms are architectural reference points only; Atlas is internal and non-commercial.
- Several capabilities ship their **decision logic and seams** with live bring-up deliberately
  deferred and recorded: the persistent orchestration daemon, the object-store and database
  servers behind the factory layer, the live CMS transport, agent-LLM synthesis in the crews,
  and the production embedding retriever. Each is injectable, offline by default, and gated by
  fixtures — the contract is that the seam exists and defaults safe, not that the service is
  running.
- The prototype DAG mirror inside the surface is **generated, not hand-maintained**; it moves
  only when the real pipeline structure moves, which is exactly when this contract should move
  too.

### Satellite: Unity Data Stack assumptions

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`.
> `AD-25` below (was `AD-2`) is renumbered to match the merged
> `ARCHITECTURE-SPINE.md`; unresolved items are carried to
> § Open Questions (satellites) below.

- **Pixi-primary lock architecture:** the Workspace Lock (`pixi.lock`) is authoritative; `pylock.toml` is a derived PEP 751 export; offline deployment uses `pixi-pack`/`pixi-unpack`. Conda-native resolution is the differentiator and the alternative (PDM/PEP-751-primary) would discard it. This is the architecture's resolution (AD-25) but see § Open Questions (satellites) — it still needs explicit human ratification.
- V1 targets SLSA Build L1 mandatory, L2 (signed provenance from a hosted build platform) as the goal; L3 is out of scope.
- V1 delivers the Domain pattern plus one worked reference Domain (`customer`); the remaining ten Domains are adoption work, not build work — see § Open Questions (satellites), this changes MVP effort by an order of magnitude if wrong.
- Data Classification is enforced at the configuration boundary; content-level inspection is deferred to v2.
- Primary Python targets are 3.13 and 3.14; 3.12 is legacy-only; 3.15 (2026-10-01) must be planned for inside this horizon.

### Satellite: Wasm Analytics Stack assumptions

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`.

- Python 3.12 is chosen as a conservative stability floor for host/pipeline processes, even though nothing in the pinned dependency set (`dlt`/`dbt-core`/`dbt-duckdb`/`duckdb` all support through 3.14) forces it — revisitable.
- Marquez's actual deployed image/version needs re-verification at implementation time; its last GitHub release tag (0.50.0, 2024-10-24) is stale relative to active repo development, and Marquez ships primarily via Docker/Maven rather than GitHub release tags.
- No cost ceiling, no air-gap-routing detail beyond the general `enterprise-airgap` posture, and no SLA/RTO/RPO commitment is stated in the founding Dream or brief; none should be assumed by downstream work until resolved.

## Resolved questions

All four closed **2026-07-25**; `open_questions[]` is empty. Recorded here rather
than deleted, so the disposition is auditable. (This section covers the
**primary** Atlas Spec only — the two satellites carry their own,
still-open questions; see § Open Questions (satellites) at the end of this
document.)

- **Does Atlas expose a public, versioned API tier?** → **Yes, eventually.**
  Deferred as a real capability, *not* closed as a non-goal. Tracked **DC-1**
  (PRD § 6.4). Today: MCP (11 tools) + `a2a`, both agent-mediated; no HTTP
  surface exists. Landed in § Non-goals as a scope-bounded non-goal.
- **Where does an upstream-maintenance signal live?** → **A Warden axis**, not an
  Atlas feed. Resolved from the Warden contract itself; no operator decision was
  needed. Landed in § Constraints.
- **What closes the deferred live bring-ups?** → **Tracked deferral.** The five
  become **DC-2…DC-6** (PRD § 6.4) — owned and visible, not scheduled. Landed in
  § Non-goals. *Correction on the record:* the first pass claimed they appeared in
  no ledger. They did — `DW-C1-1`/`DW-G3`/`DW-H1`…`DW-H4`. The Tier-3 ledger is
  **truncated to 9** and gitignored, so the deferrals were honest and their *live*
  record was lost — but the full set was recovered into Tier-2. *Second correction
  (2026-07-27):* the run log's index of "54" double-counted two aliases
  (`DW-A2-P4` → `DW-B5-3`, `DW-D2` → `DW-D2-2`). The true count is **52**, all
  present in `planning-artifacts/deferred-work-ledger.md`. Nothing was lost.
- **Do the 8 optional per-epic retrospectives run?** → **They run.** Not waived.
  Sprint-status carries 9 retro entries — 8 `optional`, 1 `done` (epic-9). The
  CFE Rule-2 retro landed separately as v8.79.0; these 8 are additive. Process
  disposition only — bends no design decision, so it lands in no kernel field.

## Open Questions (satellites)

Unlike the primary Atlas Spec's `open_questions[]` (empty — all resolved,
see § Resolved questions above), both satellites carry genuinely open
questions, honestly preserved rather than silently resolved by this
2026-08-02 consolidation. Neither is invented away here.

### Satellite: Unity Data Stack open questions

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-unity-data-stack/SPEC.md`.
> `AD-25`/`AD-31` below (was `AD-2`/`AD-8`) are renumbered to match the
> merged `ARCHITECTURE-SPINE.md`.

- **Lock authority (blocks everything):** is the Workspace Lock authoritative with the PEP 751 export derived, or the reverse, or split by tier? The architecture (AD-25) already resolves this as workspace-lock-primary and this Spec carries it as an assumption, but it still requires explicit **human confirmation** before any build work begins — it has not yet been independently ratified.
- **V1 Domain count (order-of-magnitude sizing):** does v1 ship the pattern plus one worked Domain, or all eleven? Carried as an assumption above but not confirmed at sign-off.
- **Platform Invariant vs. Domain Default classification:** AD-31 supplies the classification *mechanism*, but which specific Mandates get which classification is an unresolved sign-off decision — it directly determines whether Unity is genuinely federated/innersource (Data Mesh principle 4) or centrally imposed in practice.
- **Governance boundary:** where does the Constitution's spec-kit governance end and this repo's BMAD planning chain begin? Both are live simultaneously; unresolved, and the two risk drifting independently without an explicit decision.

### Satellite: Wasm Analytics Stack open questions

> Folded in verbatim 2026-08-02 from `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wasm-analytics-stack/SPEC.md`.
> `AD-55` below (was `AD-9`) is renumbered to match the merged
> `ARCHITECTURE-SPINE.md`.

- **Upload size / latency budget:** exact maximum upload file size and the expected weekly row-count/latency budget for the "within seconds" claim — needed before Architecture can size the validation component's performance envelope; a large-enough file may force revisiting the synchronous-upload design (AD-55) via ADR amendment.
- **Named regulatory framework:** which specific framework(s), if any, this deployment must satisfy beyond Restricted SCC + OIDC (HIPAA, PCI-DSS, SOX, none) — a named framework would likely add audit-log retention and encryption-at-rest requirements not yet captured.
- **`componentize-py` rule-configuration redesign:** does the build-time-only import restriction force a redesign of the validation component's rule-configuration mechanism, if rules were meant to be dynamically loaded per file-type?
- **Operational ownership:** who is on-call for this pipeline in production, and what SLA (if any) applies to validation/ingestion latency — needed before Architecture commits to a specific deployment topology.
- **Data classification and retention:** no scheme (PII, confidential) is defined for Bronze/Silver/Gold or Marquez's lineage history; if the seed use case's actual data (headcount/cost) carries PII, this adds retention/access-control requirements not currently specified.

