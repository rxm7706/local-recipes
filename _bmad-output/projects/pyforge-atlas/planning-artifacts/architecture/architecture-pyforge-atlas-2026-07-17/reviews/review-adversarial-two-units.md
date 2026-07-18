# Adversarial Two-Units Review — ARCHITECTURE-SPINE.md

**Lens**: construct two units one level down (waves/stories) that each obey every AD to the
letter yet still build incompatibly. Every pair found is a hole to close with a new or
tightened AD.

**Target**: `ARCHITECTURE-SPINE.md` (cf_atlas Kedro/Dagster/DuckDB migration, draft 2026-07-17)
**Grounding**: spec `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` v5.6 (§ 5.2, § 9, § 10, § 11)
**Reviewer**: adversarial-two-units lens, Reviewer Gate
**Date**: 2026-07-17

**Verdict**: The spine is unusually tight on *what* is banned (engines, plugins, writers)
but leaves five load-bearing seams where two letter-compliant stories diverge: run
admission (two mutation paths into one dataset), the ComplianceReport's home (two ADs
claim it), metric ownership across the B→D wave gap, entity join keys, and the physical
meaning of "mark stale." Two findings are CRITICAL. All are closable with one new AD and
four tightenings; none invalidates the paradigm.

---

## F1 — CRITICAL — Two sanctioned mutation paths into the same datasets (B3 MCP triggers × C1 Dagster runs)

**The two compliant units.**

- *Unit A (Story B3)*: builds `run_vulnerability_pipeline` as an MCP tool calling Kedro
  session APIs directly. Fully compliant: AD-7 *requires* MCP tools be authored over
  Kedro session/catalog APIs; AD-1 *forbids* any MCP tool from importing Dagster APIs.
  So the tool starts a bare `KedroSession.run()`.
- *Unit B (Story C1)*: compiles the same DAG into the Dagster repo; per AD-6, per-node
  timeouts, retries, and schedules live **only** there.

**The incompatibility.** Two distinct executors can now run the vulnerability pipeline
concurrently — a Dagster-scheduled daily run and an agent's MCP-triggered run — and both
write the *same* Parquet datasets. AD-3's "one producing pipeline per dataset" is
satisfied to the letter (it is the same pipeline!) while the actual hazard — two
*runner instances* mutating one `IncrementalParquetDataset` partition — is unaddressed.
Worse, the MCP path structurally *cannot* inherit AD-6's protections: timeouts/retries
are declared in the Dagster layer that AD-1 bans the MCP surface from touching. So every
MCP-triggered run is an untimed, unretried, unscheduled writer — precisely the
"1800 s coarse-cap class" failure family AD-6 exists to kill, reintroduced through the
AD-7 door. It also runs outside the Dagster UI, weakening AC-3's "phase state observable"
claim for half the run population.

**Close with a new AD (run admission & write locking).** Options, pick one and bind it:
(a) MCP triggers never execute — they enqueue a run request (file/db marker) that a
Dagster sensor picks up (keeps AD-1 intact: the sensor imports Dagster, the tool doesn't);
(b) a catalog-level advisory run-lock per pipeline (single-writer lease) that *both*
executors acquire, plus per-node timeout budgets declared in Kedro config (`parameters*.yml`)
so both executors read the same budgets and AD-6 becomes "Dagster *enforces*, config
*declares*". Either way, state explicitly: **at most one live writer per pipeline at a
time; timeout/retry budgets are declared in the Kedro layer, enforced by whichever
executor runs.** Story B3's AC ("BMAD agents can trigger a named pipeline") must name the
admission mechanism.

---

## F2 — CRITICAL — The ComplianceReport has two homes and two owners (B7/F4 `universal_sbom` × AD-15 `derived_artifacts`)

**The two compliant units.**

- *Unit A (Story F4)*: implements the FR-18 gate + report assembly as the
  `universal_sbom` pipeline's **terminal node**, per AD-12 and the Capability Map row
  "FR-16/18 hygiene node + policy gate → `universal_sbom` terminal nodes". The report is
  produced **per invocation**, against a user-supplied project manifest (scan-project
  style) — it cannot be anything else, since its subject arrives at call time.
- *Unit B (a derived-artifacts story reading AD-15)*: AD-15 explicitly binds
  "`export-purls`, `universe-sbom`, seed-gap reports, **`ComplianceReport`**, their
  consumers" and rules "derived-layer datasets are downstream nodes of the rebuild and
  **re-run after every rebuild**". A story implementing AD-15 to the letter therefore
  registers `compliance_report` as a `derived_artifacts` dataset regenerated per rebuild
  — with no project input in scope.

**The incompatibility.** Two pipelines each have an AD-backed claim to produce a dataset
named ComplianceReport — a direct violation of AD-3's producer-owns rule, manufactured
*by the ADs themselves*. And they disagree about its nature: per-rebuild (AD-15) vs
per-invocation (AD-12/F4). AD-19's scope note ("user-supplied inputs are declared inputs,
never pipeline products") supports Unit A, but AD-15's list supports Unit B; a loop-driven
story will not adjudicate this.

Secondary seam inside the same report: AD-12 says `security` comes "from
`inventory-match`/`cve`" — an unresolved *or*. Story B7 (Wave B) ports inventory-match's
six-bucket matcher with its shipped security semantics; Story F4 (Wave F) fills the
security axis. Two implementations can each pick a different source (matcher output vs
direct `cve`/KEV datasets) and disagree on a KEV-affecting-current verdict while both
citing AD-12.

**Close by tightening AD-12 + AD-15.** (1) ComplianceReport is the **per-invocation
output of the FR-18 terminal gate in `universal_sbom`** — strike it from AD-15's dataset
list; what AD-15 governs is the *atlas-side inputs* the gate consumes (universe BOM,
vuln datasets), which carry the 14-day refuse-stale contract into the gate as
`indeterminate`, not as a regenerated report. (2) Resolve the *or*: the `security` axis
is assembled from the inventory-match matcher's output joined with the `cve`/KEV/EPSS
datasets — one assembly node, owned by F4; B7 owns bucket semantics only, never report
assembly.

---

## F3 — HIGH — Metric logic gets two owners across the B→D wave gap (B3 MCP reads × D1 BSL), and AD-10's `v_*` views are a third

**The two compliant units.**

- *Unit A (Story B3, Wave B)*: must expose dataset reads to agents **two waves before
  BSL exists** (D1). AD-8 bans "raw SQL against Parquet/DuckDB" — but B3 reads via
  Kedro catalog APIs (AD-7's *required* path), which is not raw SQL. To answer anything
  useful (staleness, health, behind-upstream), B3 computes derived metrics in tool code.
  Letter-compliant with AD-7, AD-8, AD-11.
- *Unit B (Story D1, Wave D)*: declares the same metrics as BSL models, per AD-8, gated
  by `bsl-metric-check` fixtures that check BSL against **legacy CLI outputs** — not
  against B3's tool implementations.

**The incompatibility.** From Wave D onward there are two live definitions of staleness /
adoption-stage / feedstock-health — B3's imperative ones and D1's declarative ones — and
nothing forces convergence: `bsl-metric-check` compares BSL to legacy CLIs, so both
implementations can pass their gates while disagreeing with each other. This is exactly
the "28-CLI-era re-fragmentation" AD-8 names as its threat, rebuilt inside the migration.
Third owner: AD-10 requires the `v_pypi_intelligence_valid` / `v_current_version_vulns`
**view discipline** to survive the port (B2), so the validity predicates also exist as
DuckDB views — and a surface reading those views is arguably "raw SQL" banned by AD-8,
while *not* reading them arguably breaks AD-10. Two stories can go opposite ways, each
waving an AD.

**Close by tightening AD-8.** Add: (1) **pre-D1 MCP reads are passthrough only** — B3
may expose datasets and latest-report artifacts verbatim but may not compute derived
metrics; metric-bearing tools are deferred to Wave D or re-pointed at BSL by a named D-wave
task (make it an explicit AC of D1). (2) The ported `v_*` views are the **physical
bindings BSL models are declared over** — one definition site; AD-10's view discipline is
satisfied *through* BSL, and direct view reads by surfaces are banned like raw SQL.
(3) Fix the DuckDB attach/schema naming for those views in Consistency Conventions so
B2 and D1 agree on where they live.

---

## F4 — HIGH — No canonical entity join keys: five stories can key "the same package" five ways (B1/B2 × B8/B9/B10)

**The two (of several) compliant units.**

- *Unit A (Story B2)*: produces the Phase H dataset in `pypi_intelligence`, naturally
  keyed by `pypi_name` (it is the PyPI skew phase). Naming convention satisfied
  (`<domain>_<entity>` snake_case); nothing more is demanded.
- *Unit B (Story B9)*: in `vcs_health`, consumes B2's Phase H dataset cross-pipeline
  (the spine's own worked example of AD-3 consumption) and joins it to conda-side
  datasets keyed by `conda_name` — or by `feedstock`, which is *not* the same thing
  (the B.5 `_pick_feedstock` umbrella-vs-dedicated contract in AD-10 exists precisely
  because feedstock ≠ package).

**The incompatibility.** The Consistency Conventions fix dataset *names* and the purl
*string format*, but never the **join-key identity** for package-keyed rows. Compliant
choices in the field: `feedstock` (B1 core), `conda_name` (B8's AC: "`conda_name`,
`advisory_id`, `modified`"), conda purl (spec § 5.2 says `basilisk_vulns` is "keyed by
conda PURL" — already contradicting B8's AC inside one story), `pypi_name` (B2),
normalized-vs-raw PyPI names (PEP 503). Every cross-pipeline edge in the spine's DAG
diagram (PYPI→VCS, PYPI→VULN, VULN→SBOM, →DER) is a potential silent-join-loss seam, and
parity (B4) won't catch B8/B9/B10 because AD-14 exempts them from parity.

**Close with a new Consistency Convention (or sub-rule of AD-3).** Declare the canonical
entity-key columns once: `feedstock`, `conda_name`, `pypi_name` (normalization rule
stated), `purl` (CEP-63 + `?channel=conda-forge`) — and require every catalog dataset to
declare its key column(s) in catalog metadata (alongside the existing layer tag).
Cross-pipeline consumption is legal **only on declared keys**; translations between key
domains happen only via the mapping datasets owned by `core`/`pypi_intelligence`
(B.5 attribution, Phase C mapping), never by ad-hoc joins in a consuming node. Reconcile
B8's purl-vs-conda_name discrepancy explicitly.

---

## F5 — HIGH — "Skip and mark stale" has no defined mechanism; an offline run can read as "zero vulnerabilities" (B8/B10 × F4 gate)

**The two compliant units.**

- *Unit A (Story B8)*: offline consumer profile — the Basilisk node "skips gracefully and
  marks its dataset stale" (AD-13, verbatim). A legitimate implementation: write an
  **empty** `basilisk_vulns` partition and set a stale marker in dataset metadata.
- *Unit B (Story F4)*: the FR-18 gate computes the `security` axis from the vuln
  datasets. It reads `basilisk_vulns`, finds zero advisories for the project's packages,
  and — per AD-12's frozen semantics — exits 0 (pass). `indeterminate → 1` never fires
  because nothing told the gate the input was stale rather than clean.

**The incompatibility.** Both units are letter-perfect; composed, an air-gapped CI run
green-lights a project the online run would fail. The root hole: AD-13 never defines what
"mark stale" physically is — options in play are (a) empty dataset + flag, (b) carry
forward last-good data + flag, (c) leave `*_fetched_at` old and let TTL semantics imply
staleness. Options (a) and (b) produce *opposite* downstream row populations; option (c)
collides with AD-5, where an old `fetched_at` *triggers refetch* rather than signaling
"known stale, tolerated". B10 could pick (b) while B8 picks (a) — both compliant,
behaviorally incoherent across the same profile.

**Close by tightening AD-13 (+ a hook in AD-12).** Fix the mechanism: skip-and-mark-stale
means **carry forward the last-good data unchanged** and surface a dataset-level
staleness fact (e.g. `stale: true` + `stale_since`) that `IncrementalParquetDataset`
owns and every consumer can read — never an empty write, never silent TTL aging. And in
AD-12: any axis whose contributing dataset is stale beyond its declared TTL degrades that
axis to `indeterminate` (exit 1) unless policy explicitly waives it. Fixture: offline B8
skip → F4 gate exits 1, not 0.

---

## F6 — MEDIUM — Timestamp convention covers only `*_fetched_at`; B1's repodata port × B9's lag math is a 1000× landmine

**The two compliant units.**

- *Unit A (Story B1)*: ports Phase B/F and persists conda repodata `timestamp` values
  verbatim — which are **epoch milliseconds** in most builds and epoch *seconds* in some
  older ones (a well-known repodata inconsistency). The convention ("timestamps as epoch
  seconds in `*_fetched_at`") is untouched: this column is not a `*_fetched_at`.
- *Unit B (Story B9)*: computes `release_lag_hours` = first availability (AD-14: "min
  per-build repodata timestamp") minus Phase H's `upload_time_iso_8601` (an ISO-8601
  *string*, possibly parsed naive). Letter-compliant with AD-14.

**The incompatibility.** Seconds-assumed math over millisecond values is a 1000× error;
mixed s/ms rows corrupt the *min* aggregation itself (a ms value never wins a min against
an s value), so `release_lag_hours` silently keys off the wrong build. Naive-vs-aware
ISO parsing adds a ±tz-offset error. B9's calibration AC ("median ≈ 9 h... not a hard
gate") is explicitly soft, so it won't reliably catch this.

**Close by tightening the Identity & formats convention.** All persisted *event*
timestamps (not just `*_fetched_at`) are normalized at ingestion to one declared form —
UTC epoch seconds (or ISO-8601 UTC; pick one) — via a single named normalizer that
handles the repodata ms/s heuristic; a mixed-unit repodata fixture is mandatory in B1's
node suite; B9's AC gains "lag computed over normalized timestamps, fixture includes a
millisecond-unit build".

---

## F7 — MEDIUM — Profile semantics live in two config planes evaluated at different times (C1 job configs × A2/B8 dataset config), and MCP-triggered runs have no profile at all

**The two compliant units.**

- *Unit A (Story C1)*: implements `maintainer`/`admin`/`consumer` as **Dagster job
  configurations** (AD-6, verbatim), resolved when Dagster launches a run.
- *Unit B (Stories A2/B8/B10)*: implement endpoint routing and offline behavior as
  **dataset-level config** (AD-2/AD-13, verbatim), reading `BASILISK_BASE_URL`-style env
  at catalog-load time with `os.environ.setdefault` precedence (Conventions).

**The incompatibility.** Two resolution planes, two evaluation times. A consumer-profile
Dagster run whose offline-ness lives in run-config does not automatically reach the
dataset that decides live-vs-skip from process env at catalog load — so a "consumer" job
can perform live fetches while both stories pass their own gates. Compounding F1: an
MCP-triggered bare-Kedro run bypasses Dagster job configs entirely — which profile does
it run under? The spine never says; the answer today is "whatever the process env
happens to be", i.e. profile-nondeterminism on exactly the surface agents use.

**Close by tightening AD-6.** Profiles materialize in exactly one place: as **Kedro
runtime parameters** (conf + env), which the Dagster adapter *injects* from job config —
Dagster job configs are projections of Kedro profiles, never a second source of truth.
One documented resolution order (explicit run-config/env → profile default), evaluated
once per run, visible to datasets. MCP-triggered runs (per F1's admission mechanism)
must name a profile explicitly; default `consumer` (fail-safe offline) if unnamed.

---

## F8 — MEDIUM — Nobody owns the physical Parquet layout the WASM bundle needs (B1/B2 write layout × G1/G2/D2 read layout)

**The two compliant units.**

- *Unit A (Stories B1/B2)*: choose write-optimized partitioning — hive-style partition
  dirs per phase/date, many small files, whatever suits incremental re-materialization.
  AD-4 ("partitioned Parquet is canonical") is satisfied; no convention constrains
  partition columns, row-group size, or file counts.
- *Unit B (Stories G1/G2)*: duckdb-wasm over **HTTP Range** against a static host —
  a workload that wants few, large, well-row-grouped files with tight footer metadata;
  hive trees of small partitions are pathological over Range requests. AD-21 satisfied:
  static Parquet, zero backend, host-agnostic emitter.

**The incompatibility.** Both compliant; composed, `wasm-smoke` (G1) either fails against
the pipeline's native layout or G2 quietly invents a re-chunking step that no story owns
and no AD sanctions — an unowned transformation of canonical data on the publish path.
D2's dashboard (server-side DuckDB) and G1 (Range-limited WASM) may also want different
layouts of the *same* datasets, pulling B-wave layout choices in two directions.

**Close by tightening AD-21 (+ one convention row).** Declare the **publish bundle a
derived dataset of the `derived_artifacts` pipeline** — the emitter re-materializes
pipeline Parquet into a WASM-optimized layout (its schema identical, its physical layout
its own contract, gated by `wasm-smoke`); the pipeline's internal layout is never the
published interface. Add a Conventions row: partition columns are declared per dataset
in catalog metadata (they are part of the dataset's contract, not an implementation whim).

---

## F9 — MEDIUM — Marker-taxonomy fragmentation: six vocabularies for "data isn't right", no mapping (B7 × B8 × AD-12/13/15 × Conventions)

Compliant units can each pick a different marker for materially the same condition:
`unresolved` (B7's offline BOM), `stale` (AD-13/AD-15), `unknown` (B8's tri-state
`fix_available`), `not-applicable` (AD-12 axes), `last_error` columns (Conventions),
`indeterminate` (AD-12 verdict lattice). Nothing maps condition → marker → gate/render
semantics. Concrete pair: B7 marks an offline-unresolved BOM `unresolved` (spec-mandated);
the FR-18 gate must decide whether `unresolved` hygiene input is `not-applicable`
(pass-shaped, AD-12's "source-less inputs" rule) or `indeterminate` (fail-shaped) —
both readings are defensible, and D2's pages vs B3's MCP reads can render the same row
differently. **Close with a Conventions table**: one row per condition (never-fetched /
fetched-stale / fetch-failed-this-run / not-resolvable / not-applicable-by-construction),
its canonical marker, and its mandated projection into the AD-12 verdict lattice and the
read surfaces. Cheap to write now; unmergeable to retrofit after B and F wave stories
ship their own dialects.

---

## F10 — LOW — A2A alert obligations predate the A2A channel, and payload-schema ownership is unassigned (AD-9 Wave-B binding × E1)

AD-9 binds "contract violation → Dagster halts → **A2A alert**" for *every node writing a
persisted dataset* — live from Wave B — but the channel is built in E1 (Wave E) and its
transport is explicitly Deferred. Two compliant units: Wave-B/C stories emit alerts into
whatever interim shim each invents; E1 later defines the real payload schema in `a2a/`.
Result: two alert dialects on what AD-20 calls "the sole structured channel", plus
unowned schema versioning between F2's contract-violation alerts, F4's policy-breach
alerts, and the analytical agent's insight payloads. **Close by tightening AD-20**: the
`a2a/` schema directory is the single payload registry from Wave B (schemas exist before
transport; pre-E1 emission is a structured no-op/log-queue against those schemas), and
E1 owns schema versioning; F2/F4 alerts are instances of one alert schema, not siblings.

---

## F11 — LOW — Wave-H wiki republication launders staleness (H2/H3 crews × derived-artifacts freshness)

Compliant pair: the `derived_artifacts` pipeline enforces refuse-stale at 14 days
(AD-15); an H2 compile crew reads the same data via BSL (AD-22, letter-perfect) and bakes
it into `wiki/compiled/` + Wagtail pages, which then serve it **indefinitely** — the
freshness contract does not survive republication. AD-17's timestamp rule covers
"payloads/pages that feed authoring decisions"; a wiki page dodges that wording right up
until the H2 Oracle Q&A crew answers an authoring agent's question from compiled content
— at which point stale data feeds authoring with no timestamp, violating AD-17's intent
while every letter held. **Close by extending AD-22**: any factory output embedding atlas
data carries the source build timestamp, and H4's sensors include a derived-dataset-
refresh trigger so recompilation follows rebuilds; Oracle answers cite the embedded
timestamp.

---

## Summary of required spine changes

| # | Severity | Seam (units) | Fix |
|---|---|---|---|
| F1 | CRITICAL | B3 MCP trigger × C1 Dagster run | **New AD**: run admission + single-writer lease; timeout budgets declared in Kedro config |
| F2 | CRITICAL | F4 gate × AD-15 derived list (and B7 × F4 security axis) | Tighten AD-12/AD-15: ComplianceReport is per-invocation, `universal_sbom`-owned; strike from AD-15; resolve the security-source *or* |
| F3 | HIGH | B3 pre-BSL reads × D1 BSL × AD-10 views | Tighten AD-8: passthrough-only pre-D1; `v_*` views are BSL's physical bindings; fix view naming |
| F4 | HIGH | B2 Phase H × B9 join (and B8 purl-vs-name) | New convention: canonical entity keys declared in catalog metadata; joins only on declared keys |
| F5 | HIGH | B8/B10 offline skip × F4 gate | Tighten AD-13: stale = carry-forward + surfaced marker; stale security axis → `indeterminate` |
| F6 | MEDIUM | B1 repodata ms × B9 lag math | Tighten Conventions: all event timestamps normalized UTC at ingestion; ms/s fixture |
| F7 | MEDIUM | C1 job configs × A2/B8 dataset env | Tighten AD-6: profiles = Kedro runtime params, Dagster projects them; MCP runs name a profile |
| F8 | MEDIUM | B1/B2 layout × G1/G2 Range reads | Tighten AD-21: publish bundle is a derived dataset (emitter re-chunks); partition columns in catalog metadata |
| F9 | MEDIUM | unresolved/stale/unknown/not-applicable/last_error/indeterminate | New Conventions table: condition → marker → verdict-lattice projection |
| F10 | LOW | AD-9 Wave-B alerts × E1 channel | Tighten AD-20: `a2a/` schemas precede transport; E1 owns versioning |
| F11 | LOW | H2/H3 wiki republication × AD-15 freshness | Extend AD-22: embedded build timestamps + rebuild-triggered recompile |

The paradigm, layer map, and ban-lists hold under attack; the holes are all at the
*shared-shape* level (keys, markers, timestamps, one report, one lock) — exactly the
level the next artifact (epics/stories) will freeze, so these should land in the spine
before `bmad-create-epics-and-stories` runs.
