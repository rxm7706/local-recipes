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
program: regenerable-factory
surface:
  - src/shared/packages/pyforge-atlas/**               # the shipped package: conf/, src/pyforge/atlas/, tests/, wasm/
  - src/prototype/packages/pyforge-atlas-kedro-viz/**  # the generated dependency-free DAG mirror (tools/regenerate_from_atlas.py) — moves only when the real DAG moves
companions:
  - signals.md               # the 23 ported phases -> nodes, the 3 additive riders, the Warden boundary on signals
  - catalog-contract.md      # 7 pipelines x 86 datasets, every declared TTL, the two freshness clocks, identity + join keys
  - degradation-contract.md  # the 3 markers, the fixed policy mapping, the frozen exit projection
  - gate-contract.md         # the 7 gates, what each proves and what each refuses to do
sources:
  - ../../../../../../docs/dreams/pyforge-atlas.md
  - ../../../../../../docs/dreams/pyforge-charter.md   # § 3 Atlas — the station's standing mandate
  - ../../../../../../docs/specs/cfe-atlas-datapipeline-kedro-migration.md   # LEGACY Tier-1 intake spec (v5.6, status: shipped) — the requirements contract this Spec distils; absorbed and superseded, not adopted
  - ../../prds/prd-pyforge-atlas-2026-07-17/prd.md          # chain: FR-1..FR-22, SM-1..SM-12 + SM-C1..SM-C4, the § 5 non-goal boundary
  - ../../prds/prd-pyforge-atlas-2026-07-17/addendum.md     # chain: intake reconciliations
  - ../../architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md  # chain: AD-1..AD-23, the conventions table, stack, structural seed
  - ../../epics.md                                          # chain: 9 epics / 32 stories with their binding ACs and delivery records
  - ../../../../pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md  # cross-project: owns the ComplianceReport contract this project's policy gate validates against by import
  - ../../briefs/brief-pyforge-atlas-2026-07-25/brief.md
  - ../../research/domain-dependency-intelligence-ecosystem-observability-research-2026-07-25.md
  - ../../research/technical-kedro-dagster-duckdb-stack-currency-research-2026-07-25.md
open_questions: []   # all four resolved 2026-07-25 — see § Resolved questions
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

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
  run — a different property, and on the Dagster plane a load-bearing one (`DW-AD23-2`). Three
  boundaries stand: file locks are single-machine (NFS `flock` is unreliable); release on the
  Dagster plane is process-local; and because kedro calls `before_pipeline_run` outside its `try`
  with admission dispatched first, a later before-hook that raises leaves the locks held until the
  process exits — an availability wedge for the long-lived MCP server, not a correctness hole.
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

## Resolved questions

All four closed **2026-07-25**; `open_questions[]` is empty. Recorded here rather
than deleted, so the disposition is auditable.

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

