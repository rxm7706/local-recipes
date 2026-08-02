---
title: "Station — Complete Epics & Stories (Ready for Development)"
status: ready-for-development
created: 2026-08-02
updated: 2026-08-02
note: "Stories extracted from epics.md; acceptance criteria in Given/When/Then format"
---

# Epics & Stories (Derived from epics.md)

**Source:** [epics.md](epics.md) — automatically derived for reference and test architecture tracking.

**See also:**
- `epics.md` — Complete epic breakdown
- `test-architecture.md` — Test strategy for all stories
- `architecture/` — Detailed architectural specifications

---
## Epic List

*Vertical-slice epics (architecture complete). Stress-tested via [A] dependency-mapping + a party-mode roundtable (PM/Dev/Architect), then a **full restructure** the roundtable mandated: the risky work is split into single-agent-sized stories (keystone 1.1→1.1/1.2; the two data-provisioning **spikes extracted** — OSV-DB as 1.4, conda→pypi map as a parallel task; the 2.2 extractor split 2.2/2.3; FR1 discovery promoted to its own Story 1.9; the report split 1.7/1.8) while the **commodity tail shrinks** (4.2 dissolved into conformance tests; E4/E5 kept lean). **31 stories** (2026-07-15: +Epic 6; 2026-07-16 D12 + reviewer gates: Epic 6 grown to 6.1–6.10, story 2.6 split from 2.1 — axis gates, EPSS, baseline & grandfathering, fix-PR actuator all v1; story **0.1** — the spec-first replan of this document set — was executed 2026-07-15/16 and is recorded, not scheduled; `sprint-status.yaml` regeneration via `bmad-sprint-planning` is a follow-on once this replan merges). E1 remains a **contract-first walking skeleton, not a foundation dump** — the `Component` record + `ComplianceReport` schema + full 7-rung lattice are frozen WHOLE in 1.1 (field shape/type/optionality frozen now; two enums' variant-sets may grow **additively** in E2, safe because 1.1's projection treats any unknown match-level → `indeterminate`, never `clean`). Cross-cutting gates (C0a/C0b/C0c, verdict.py sole-ownership guard, NFR-S\*, corpus 0-exceptions, differential-oracle) are per-story acceptance gates, not a separate epic.*

### Epic 1: Spine + PyPI engine (walking skeleton)
A maintainer gates a **PyPI project** end-to-end — unified deptry+osv verdict + one exit code — while the run establishes the shared spine as a *vertical slice* (never "build the spine" as infra). **4 E1 definition-of-done conditions (roundtable-mandated):** (1) **interface-first** — `extract`/`routing`/`engine`/`vuln-strategy`/`Policy` are plugin/strategy interfaces, PyPI is the first registered impl; (2) the **`Component` record + `ComplianceReport` JSON schema + full 7-rung verdict lattice are frozen WHOLE in 1.1** (all fields present with honest non-degenerate PyPI values; two enums may grow additively in E2 under a conservative projection); later epics are **producers, never editors**; (3) **C0a (projection-safety)** owned + tested against the projection directly, gated on every epic; the `indeterminate` rung ships as a **proven-total socket**; (4) the **regression-harness skeleton hoisted to 1.2** (2 PyPI fixtures + the C0c socket-deny harness). **Internally gated:** cluster-1 (1.1 model+lattice → 1.2 interfaces+null engine, green) **before** cluster-2 (1.3 deptry → 1.4/1.5 osv).
**Stories (9):** 1.1 frozen contract + lattice + C0a · 1.2 interfaces + null engine + harness + C0c · 1.3 deptry · 1.4 OSV-DB spike · 1.5 osv · 1.6 gate + verdict · 1.7 typed errors + no-scan guard · 1.8 report renderers · 1.9 discovery (FR1).
**FRs covered:** FR1, FR2, FR4, FR8, FR9, FR10, FR14, FR17, FR18, FR20, FR21, FR22, FR28, FR29, FR31

### Epic 2: The conda/pixi source-manifest wedge
A conda-feedstock/pixi maintainer gets the gate on their **source** manifest (recipe.yaml/meta.yaml/environment.yml/pixi.toml) — the differentiated value no incumbent delivers (**beachhead value; pulled as early as possible**). Registers the conda+pixi extractors behind E1's interfaces; the **non-rendering parse-as-data + supported-construct matrix**; generates the **conda→pypi map from the atlas** *(CFE Rule 1)*; the `pypi_identity` predicate + confidence threshold; the **`indeterminate` PRODUCER + C0b (withhold-completeness)**; the name-level CVE tier; the **differential-oracle**. Ships red-by-design `indeterminate` exits without needing E3's waivers.
**Stories (6):** 2.1 conda→pypi map + pypi_identity · 2.2 non-rendering extraction + oracle · 2.3 full construct-matrix · 2.4 split coverage + indeterminate producer (C0b) · 2.5 name-level CVE tier + stale-DB + non-merge · 2.6 lockfile extraction (locked-closure hero path; split from 2.1, 2026-07-16).
**FRs covered:** FR3, FR5, FR6, FR7, FR11, FR12, FR13, FR15, FR16

### Epic 3: Policy control + auditable waivers + warn-only
A team tunes the gate and files auditable, expiring, time-boxed exceptions without lying about coverage. Makes E1's `Policy` interface **configurable + waivable** — per-repo config precedence, coverage-floor gate, the DEP001-block confidence threshold; waivers-as-code (read-not-written, expiry re-block, review routing); the warn-only adoption mode.
**Stories (3):** 3.1 configurable policy · 3.2 auditable expiring waivers (FR24) · 3.3 waiver-expiry re-block + warn-only.
**FRs covered:** FR19, FR23, FR24, FR25, FR26, FR30

### Epic 4: Machine contract + CycloneDX SBOM
The CI pipeline / cf_atlas consumes a stable, versioned report **and** an honest CycloneDX 1.6 SBOM. `sbom.py` as a **separate read-only projection over the frozen inventory** (source-registry purls, self-declared partiality). *(**Dissolved 4.2** per the roundtable: schema-conformance is asserted by a test in 1.1, not built as a story; pure-JSON hardening lives in 1.8's renderer. E4 = the one genuinely-additive value story.)*
**Stories (1):** 4.1 CycloneDX 1.6 SBOM + S7 adversarial-encoding neutralization. *(NFR-I1/I2 → 1.1+1.2; NFR-I3 → 1.8.)*
**FRs covered:** FR27

### Epic 5: Fleet-readiness & adoption on-ramp
The gate survives 20k-repo deployment and a maintainer adopts it without a day-one red storm. The **actionable-diagnostics** pass (fail-with-a-fix; a new `--explain`/remediation capability) + safe-by-default fail-closed posture; then the fleet-scale hardening gate — P-concurrency, deterministic exit matrix under load, the **corpus-ratchet + differential-oracle maturation across all formats** (corpus-provisioning is its first task). Determinism itself threads as a per-story acceptance gate everywhere, not a terminal epic. Defends the `gate-disabled = 0` anti-metric.
**Stories (2):** 5.1 actionable diagnostics + safe-by-default · 5.2 fleet determinism + corpus-ratchet + oracle maturation. *(The corpus-ratchet here = NFR-R2's unparseable-rate ratchet — distinct from the v1.x baseline & grandfathering ratchet.)*
**FRs covered:** *(NFR: U1, U2, P-warm/cold/concurrency, R2, R5, C1)*

### Epic 6: Multi-axis expansion — license, currency, KEV/EPSS & adoption (added 2026-07-15; re-baselined 2026-07-16, D12)
The gate becomes the spec's four-axis v1 **with its gates**: license + currency ship their full gates **flag-activated** (unconfigured → visible `warn`, never a silent clean; configured → `policy-violation`/`indeterminate`), security gains the **CISA-KEV and EPSS gates** with honest feed-absence semantics, and adoption gains **baseline & grandfathering** (gate NEW findings only) plus the opt-in **fix-PR actuator**. Executes the **one sanctioned schema amendment** (6.1 — every other story stays a producer against the frozen contract), registers the two new axis producers behind E1's existing `Engine` seam (no new interface — the axis is an open string), wires the two-mode policy, and closes the **engine version-range distribution gate**. Delivery: after E4, before E5 (E5's fleet validation then covers all four axes).
**Stories (10):** 6.10 amendment design spike (runs first — the 1.4-spike precedent) · 6.1 versioned schema amendment · 6.2 license axis + gate flags · 6.3 currency axis + gate flags · 6.4 KEV feed + gate · 6.5 two-mode policy integration · 6.6 engine version-range pinning · 6.7 EPSS feed + `--min-epss` · 6.8 baseline & grandfathering · 6.9 fix-PR actuator.
**FRs covered:** FR32–FR40 *(+ NFR-S9; NFR-C1's distribution gate)*

---

## Epic 1: Spine + PyPI engine (walking skeleton)

Establish the contract-first spine and gate a PyPI project end-to-end. Cluster-1 (1.1 model+lattice → 1.2 interfaces + C0a/C0c vs a null engine) must be green before cluster-2 (real engines). Every story ends in something runnable; the record + `ComplianceReport` schema + 7-rung lattice are frozen **whole** in 1.1.

### Story 1.1: Frozen contract, verdict lattice & projection-safety (C0a)

As a **tool maintainer**,
I want the `ResolvedInventory`/`Component` model, the `ComplianceReport` JSON schema, and the full 7-rung verdict lattice with its exit projection frozen and unit-proven — pure data + ordering, zero I/O,
So that every later engine and format is a *producer* against a stable contract that never needs a schema-breaking retrofit.

**Acceptance Criteria:**

**Given** the `Component` record, **When** it is defined, **Then** it carries the **full frozen field set** — `ecosystem` enum `{pypi,conda}` **closed** *(corrected 2026-07-12: pixi is a manifest format, not an ecosystem — the pixi fact lives in `provenance`)*, `provenance` a **list** of `(manifest,section)`, and `version|None`, `pypi_identity|None`, `identity_source`, `mapping_confidence`, `cve_match_level`, `extraction_mode`, `hygiene_covered`, `vuln_matchable`, `indeterminate_reason|None` all present with declared type + optionality. **And** every field's shape/type/optionality is frozen now; the two growable enums (`cve_match_level`, `WithholdReason`/`indeterminate_reason`) are declared with a conservative starter set (widening is additive, never a schema-break). **And** every non-clean status carries **`status.driver`** (axis + finding id) as part of the frozen report schema — an exit that can't say *why* is an incoherent contract (added 2026-07-12 per arch).

**Given** the report schema, **When** it is frozen, **Then** it is **producer-agnostic** (the Kedro FR-16/FR-18 atlas gate is this schema's second producer): vuln-data provenance is generic (`{source, snapshot_at, max_age_ok}` — never `osv_db_*`-named fields), **optional KEV/EPSS slots** exist (*amended 2026-07-15, story-0.1 replan: v1 populates the bare `kev` bool via story 6.4 — FR36/D3 superseded the "v1 never populates them" clause; `kev_date` + the `epss` object ride 6.1's amendment*), severity carries **both** a normalized tier and the raw evidence (CVSS vector string or database label), and findings/coverage are keyed by an **open `axis` mechanism** (`hygiene`/`vulnerability` now; a license/SAST axis lands additively, never a schema-break). *(Added 2026-07-12 per readiness Major 1.)*

**Given** the finding model, **When** it is frozen, **Then** every finding carries a **stable, deterministic finding-ID** (scheme documented in the schema: `vuln:<advisory-id>:<pkg>@<ver>` · `hygiene:<DEP-code>:<module-or-pkg>` · `indeterminate:<reason>:<pkg>`) — waiver matching across runs (E3) depends on it — **And** the waiver-scope decision is recorded: **all three finding families are waivable-with-expiry** (an auditable, time-boxed acceptance; the graduated path for unscannable deps). *(Added 2026-07-12 per readiness Major 1.)*

**Given** the committed `ComplianceReport` JSON schema, **When** a minimal report is validated, **Then** it conforms; it carries `schema_version` and the exit enum is the frozen closed set `{0,1,2,130}` (**FR28** — tagged 2026-07-12; folds NFR-I1/I2 — the dissolved 4.2 conformance assertion lives here).

**Given** `verdict.py`, **When** C0a is tested against the projection **directly**, **Then** the projection is **total** over all 7 rungs (`error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`), every non-clean rung maps to non-zero (**`indeterminate` → exit 1**, pinned 2026-07-12; `error` → 2, reserved for operational failure), and an unknown/weaker `cve_match_level` projects **toward `indeterminate`, never `clean`** (the additive-growth safety rule). **And** a guard test asserts an all-clean inventory produces zero `indeterminate` (the socket is proven-total, not dead).

**Given** the repo, **When** the **verdict.py sole-ownership guard** runs, **Then** CI fails if any module other than `verdict.py` invokes an exit primitive with a guarded exit value (the literals `{1,2,130}`, a module-level constant bound to one, or a string argument — `sys.exit("msg")` exits 1) or materializes the rung ORDERING as an ordered sequence literal (the lattice order or its exact reverse) (stories *feed* rungs; only `verdict.py` *projects*). *(Amended 2026-07-13, story 1.1 follow-up review: `models.py` legitimately declares the closed exit-code SET and the `Status` members for report validation — the guard targets projection behavior, not declaration.)*

### Story 1.2: Interfaces, null engine, regression harness & socket-deny (C0c)

As a **tool maintainer**,
I want the plugin/strategy interfaces wired to a null engine, the minimum regression harness, and a deny-by-default socket harness — proven end-to-end,
So that the skeleton runs `scan → report → deterministic exit` and every future engine inherits the security + false-green gates for free.

**Acceptance Criteria:**

**Given** the completed scaffold, **When** `scan <trivial-dir>` runs with a **null engine**, **Then** it emits a schema-valid minimal `ComplianceReport` (from 1.1) to stdout and exits per the projection. **And** `extract`/`routing`/`engine`/`vuln-strategy`/`Policy` exist as interfaces with the null engine as the only registered impl (**interface-first**). **And** a **trivial single-manifest discovery stub** ships here (enough for `scan <dir>` to locate one manifest) — completed/replaced by Story 1.9's full FR1 discovery (stub ownership noted 2026-07-12).

**Given** `tests/conformance/`, **When** the harness runs, **Then** it has **2 PyPI fixtures** (one clean → green, one false-green sentinel → ≥1 finding) and asserts **0 uncaught exceptions + false-green=0 + exit-code-matches**. **And** the asset-loading plumbing + a stub `data/conda_pypi_map.json` exist. *(Both fixtures are PyPI — no conda fixture here, to avoid pulling 2.1's identity map into E1.)*

**Given** the **C0c socket-deny harness**, **When** any scan runs under test, **Then** any outbound socket attempt is a **hard test failure** (deny-by-default) — enforcing NFR-S2 for the null engine and every future engine without re-litigation.

### Story 1.3: deptry as the first engine (hygiene findings)

As a **PyPI-world developer**,
I want deptry wired in as the first real engine so my project's hygiene findings surface,
So that I get dependency-hygiene results from one command.
*(Off the OSV critical path — proceeds in parallel with the 1.4 spike.)*

**Acceptance Criteria:**

**Given** a PyPI project with a missing/unused dependency, **When** I run `scan .`, **Then** deptry runs via `_engine_env()` (temp-file output, `NO_COLOR=1`, `stdin=DEVNULL`, argv-only) and its DEP001–005 findings land in the `ResolvedInventory` (FR8, and FR4 native-parser delegation). **And** deptry's exit code is **never** the gate — the verdict reads report content.

**Given** deptry emits chatty/ANSI output, **When** captured, **Then** stdout stays a single valid JSON document (the pure-JSON stdout seam) and diagnostics go to stderr. **And** the ratchet mechanism (`unparseable_rate` baseline) is introduced.

**Given** a project with a `[tool.deptry]` config, **When** scanned, **Then** those ignores are honored (FR9). **And** the C0c socket-deny gate holds (deptry runs with no egress). **And** DEP005's actual semantics are **verified against the pinned deptry range** (the pinned-contract label "unused-dev" may itself be wrong) and a DEP005 → `warn` row is added to the ConfigLoader hygiene policy table (added 2026-07-12).

### Story 1.4: OSV-DB offline provisioning spike (decision + fixture DB)

As a **tool maintainer**,
I want the osv offline-DB provisioning mechanism decided and a hermetic fixture DB produced,
So that 1.5, 2.5, and CI have a bounded, reproducible vulnerability-data substrate instead of an open research question buried in a delivery story.

**Acceptance Criteria:**

**Given** the offline-first constraint (NFR-S2/S8), **When** the spike concludes, **Then** a **decision record** documents the chosen mechanism (bundled-conda-DB vs `--offline` + a provisioned local DB), how "stale" is defined (feeds FR12), and the trust-anchor/authenticity check (NFR-S8). **And** a **hermetic fixture DB** the conformance harness can consume offline is produced. **And** the decision record documents the **DB size + cache-key contract** so runs #2..N are warm and air-gapped mode is pre-provisioned/fail-loud (NFR-P-cold — owned here).

**Given** the decision, **When** downstream stories consume it, **Then** it explicitly gates **1.5** (osv engine) and **2.5** (stale-DB semantics; ref corrected 2026-07-16 post-renumber) — and **not** 1.3 (deptry has no OSV surface).

**Given** a workstation cold start (no DB provisioned — persona P8), **When** the spike decides the provisioning UX, **Then** the decision record also covers (added 2026-07-12): the fail-loud + **actionable-nudge** message (how to provision / `--db-path`); whether an explicit **online opt-in** query mode ships in v1 (the PRD's "opt-in, never silent" path — currently unowned) or v1 is offline-only-everywhere with trivial provisioning; the concrete **engine version ranges** to pin (NFR-C1) + the version-detection mechanism; reuse of the in-repo **`update-cve-db`** offline-OSV provisioning surface vs a new downloader; an env-var **mirror override** for the DB fetch (JFrog/air-gap discipline); and verification of osv's `--lockfile=<parser>:<path>` override (may remove the `requirements.txt` temp-name constraint). The decision record also names the **env distribution channels**: `pixi global install` (online) · **pixi-pack/unpack** (air-gapped single-archive bundle — scanner + engines + DB) · **nebi push/pull** for nebi-adopted teams (OCI registries; alpha — a candidate, not the recommended primary path for a security gate) (added 2026-07-12).

### Story 1.5: osv-scanner as the second engine (vulnerability findings)

As a **PyPI-world developer**,
I want osv-scanner wired in so known CVEs in my locked dependencies surface alongside hygiene,
So that one gate covers both signals.

**Acceptance Criteria:**

**Given** the 1.4 fixture DB, **When** a lockfile with a known-vulnerable pin is scanned, **Then** osv runs offline through `_engine_env()`, its advisory + CVSS severity lands in the inventory (FR10), merged into the **same** `ResolvedInventory` as deptry's findings. **And** the synthesized osv input is a **pure data projection** (NFR-S6): any line starting with `-`, or carrying a URL / VCS ref / path / env-marker we did not author, is rejected or neutralized; manifest-derived values never become CLI flags. **And** osv exit `1` (vulns-found) is read as content, `127`→engine-error, `128`→no-packages — never a silent pass.

**Given** the offline posture, **When** osv runs, **Then** the **C0c socket-deny gate holds** — osv performs **no silent DB fetch** during a scan (explicit NFR-S2 AC on the DB-access surface); the report records the DB source + timestamp (FR11).

### Story 1.6: Severity gate + verdict composition end-to-end

As a **PyPI-world developer**,
I want the gate to fail my build on real problems and pass when clean, via one composed exit code,
So that CI has one trustworthy signal.

**Acceptance Criteria:**

**Given** the `Policy` interface with a hardcoded-sane default, **When** a critical CVE is present, **Then** the vuln axis emits `policy-violation` and the verdict projects exit **1** (FR18/FR20). **And** a missing dependency (DEP001) blocks by default on a high-confidence mapping; DEP002–005 → `warn`. *(Confirmed by owner 2026-07-15 against the spec's transient "all hygiene warns" wording — DEP001-blocks stands as the POST-2.1 default; the spec was aligned. Shipped status, precisely: story 1.3's `DEFAULT_HYGIENE_POLICY` has DEP001–005 all `warn` — DEP001 deliberately warns until story 2.1 ships the mapping-confidence gate that activates the block.)*

**Given** a **synthetic `indeterminate` fixture component**, **When** the verdict composes, **Then** the `indeterminate` composition path (the highest-risk never-false-green path) is proven **in E1** — `indeterminate` outranks `warn`/`clean` and projects non-zero — even though the first real producer is 2.4 (ref corrected 2026-07-16 post-renumber). **And** clean hygiene + no vulns → status `clean`, exit **0**; no story outside `verdict.py` computes the projection.

### Story 1.7: Typed errors & the no-scan guard (the fail-closed net)

As a **platform engineer**,
I want failures typed + routed and a run that scanned nothing to fail-closed,
So that a red gate is diagnosable and "found nothing" can never masquerade as "clean."

**Acceptance Criteria:**

**Given** a missing/incompatible engine, **When** scanned, **Then** a typed `error_kind` routed to its owner (engine-unavailable/crash/output-unrecognized) is emitted and exit is **2** — never a silent pass (FR21). **And** an engine that exceeds its bounded timeout yields a typed `timeout` error, not a hang (NFR-R5).

**Given** a run that scanned nothing meaningful, **When** it completes, **Then** the status is non-passing, **never `clean`** (FR22).

### Story 1.8: Human & machine report renderers

As a **platform engineer**,
I want both a human summary and a machine report from one run,
So that a person can read the result and the pipeline gets a stable contract.

**Acceptance Criteria:**

**Given** `--format text` (default) vs `--format json`, **When** run, **Then** a human summary (findings + verdict) or a single valid JSON `ComplianceReport` is emitted respectively (FR17/FR14). **And** `--version`/`--help` are a stable contract (FR31); FR29 one-command→one-exit-code holds.

**Given** `--format json` under a chatty-engine + pseudo-TTY fixture, **When** captured, **Then** stdout is a single valid document or empty — never contaminated (NFR-I3, folded from the dissolved 4.2).

### Story 1.9: Manifest discovery, deterministic selection & the resolved scan set (FR1)

As a **maintainer with several manifests in one repo**,
I want the tool to discover, classify, and deterministically select what it scans — and tell me what it chose,
So that a wrong-but-quiet manifest choice can never produce a false-green.

**Acceptance Criteria:**

**Given** a tree with multiple candidate manifests, **When** `scan <path>` runs, **Then** discovery + classification + **precedence is total and deterministic** — the same tree yields the same resolved scan set every time (FR1) — and each dependency source-section routes to the correct extractor (FR2).

**Given** the resolved scan set, **When** the report is emitted, **Then** it is a **first-class field** on `ResolvedInventory` (an operator sees *what was scanned*, never infers it).

**Given** discovery finds **nothing parseable while Python signals are present**, **When** it resolves, **Then** it is an **`error` (exit 2, per PRD D2 fail-closed)** routed to the developer; **Given** discovery is **ambiguous or partial** (candidates found, selection/parse uncertain), **Then** it becomes **`indeterminate` (exit 1), never `clean`** — the load-bearing AC that makes discovery a gate, not cosmetics. *(Split corrected 2026-07-12 to align with D2 — different failure classes, different owners.)*

---

**Given** a monorepo sweep with Python signals but an empty extraction, **When** `--allow-empty` is passed, **Then** the exit downgrades to 0 with `coverage: none` recorded — the status channel stays honest (never `clean`) — and without the flag the run stays fail-closed (FR22's one sanctioned empty-extraction downgrade — D2; owned here).

## Epic 2: The conda/pixi source-manifest wedge

Deliver the beachhead value: gate a conda/pixi **source** manifest that no incumbent parses. Registers conda+pixi extractors behind E1's interfaces; introduces the `indeterminate` producer + C0b + the differential-oracle.

### Story 2.1: conda→pypi map + the ecosystem-identity predicate

As a **conda/pixi maintainer**,
I want my conda dependencies mapped to their PyPI identity (or honestly withheld),
So that vulnerability matching can't silently misfire on a name mismatch.

**Acceptance Criteria:**

**Given** the atlas `export-purls` conda↔pypi TSVs, **When** the map generator runs *(invoke `conda-forge-expert` — CFE Rule 1; runs as a **parallel read-only data task**, so 2.1 consumes a finished `data/conda_pypi_map.json`)*, **Then** a bundled map with a stable schema is produced, **preserving the per-pair `match_source` + `match_confidence` columns** (never flattened to name→name — the DEP001-block and identity-trust rules read these provenance tiers: `parselmouth`/`recipe_source_url` → block-eligible/trusted, `name_coincidence` → warn, `none` → withheld); `prefix-dev/purl-associator` serves as a second corroborator (added 2026-07-12). **And** the generator supports a **parselmouth-direct refresh mode** (consume `prefix-dev/parselmouth`'s published mapping artifacts — pixi's own default `conda-pypi-map` source) so non-atlas organizations can regenerate the bundled map (added 2026-07-12).

**Given** a conda component, **When** its `pypi_identity` is resolved, **Then** it is taken from pixi.lock `pypi:` / explicit PyPI sections / the map (with a confidence value); an unmapped or `native-nonpypi` package resolves to `None` and is **withheld from osv** (never fed under the conda name) — closing the silent `pytorch`→`torch` false-green. **And** `vuln_matchable = (pypi_identity ≠ None) AND version==X.Y.Z`.

**Given** a **low-confidence** identity (below the chosen threshold), **When** classified, **Then** it resolves to **`indeterminate`, not a silent clean** (ties the threshold decision back to 1.1's lattice). **And** landing the confidence gate **activates hygiene's DEP001 block-on-high-confidence** — upgrading story 1.3's deliberate all-`warn` `DEFAULT_HYGIENE_POLICY` to the Gap-A decision (DEP001 blocks on a trusted mapping; ambiguous → `warn`).

*(Lockfile extraction moved to Story 2.6, 2026-07-16 — the 2026-07-12 Major-2 bolt-on made 2.1 a two-session story; readiness Major-3 split.)*

### Story 2.2: Non-rendering extraction (common case) + differential-oracle

As a **conda/pixi maintainer**,
I want my source manifests' common-case dependency set extracted without a resolved environment, validated against a real render,
So that I can scan my source recipe pre-build with confidence it isn't silently dropping deps.

**Acceptance Criteria:**

**Given** a common-case `recipe.yaml`/`meta.yaml`/`environment.yml`/`pixi.toml`, **When** extracted, **Then** it is **parse-as-data, never rendered** — the extract module imports no execution primitive and no `jinja2` (S1 AST-denylist) — and its deps land in the inventory (**FR3** — tagged 2026-07-12). **And** pixi extraction covers the `[feature.*]` and `[target.*]` tables (provenance-tagged) beyond the base sections. **And** `run_constrained:`/`run_constraints:` entries are **constraints, not dependencies** — excluded or ingested as `provenance: constraint` (out of vuln matching + SBOM counts), matching the shipped `scan_project` semantics (added 2026-07-12). **And** the C0c socket-deny gate holds (extraction performs no egress — explicit NFR-S2 AC). **And** with adjacent Python source present, deptry consumes the synthesized front-door so **hygiene findings surface for the conda-sourced project too** (FR8's conda half — was implicit). **And** extraction is **line-bounded with a per-line byte cap + a total manifest-size cap**, and no compiled pattern carries nested unbounded quantifiers (NFR-S5 — statically asserted).

**Given** the **differential-oracle**, **When** it runs on the fixture corpus, **Then** the non-rendering dep-set ⊇ the rattler-build/conda-build render (modulo name-only-marked), with 0 uncaught exceptions. **And** the oracle is **skip-if-renderer-unavailable** (fixture scale here; matured to corpus scale in 5.2) so 2.2 never hard-blocks on renderer provisioning.

### Story 2.3: The full supported-construct matrix (ratcheted)

As a **conda/pixi maintainer with a Jinja-heavy recipe**,
I want selectors, templating, multi-output, and pin_subpackage handled by an explicit, tested matrix,
So that a complex recipe degrades honestly instead of silently mis-extracting.

**Acceptance Criteria:**

**Given** the construct matrix, **When** a recipe uses them, **Then** `compiler()`/`stdlib()` → build-tool-exclude, `pin_subpackage()` → internal-exclude, `# [sel]`/`if-then-else` → **union both branches + mark**, expression-logic → degrade to name-only+marked (FR5). **And** each rule is ratcheted against the 2.2 differential-oracle (a matrix regression fails CI).

### Story 2.4: Honest split coverage + the indeterminate producer (C0b)

As a **conda/pixi maintainer**,
I want a truthful verdict that never claims "clean" for deps it couldn't assess,
So that a green check is trustworthy.

**Acceptance Criteria:**

**Given** a manifest where some deps resolve and some don't, **When** reported, **Then** coverage is **split** into hygiene vs vulnerability dimensions (FR15) and a partial result renders a **coverage-qualified verdict governed by the FR20 lattice** (partial vuln coverage ⇒ `indeterminate`, non-zero), never bare "clean" — the retired "clean at N%" phrasing is outlawed by FR16 (wording aligned 2026-07-16). **And** the coverage marks `direct-only` vs `locked-closure` (a loose manifest lists direct deps only; transitive vulns invisible without a lockfile).

**Given** a name-only / range / unmapped dep, **When** classified, **Then** it becomes `indeterminate` with a `WithholdReason` (`no-version`/`unmapped-ecosystem`/`native-nonpypi`/`range-only`) and is **never dropped or defaulted to clean** (C0b — FR13); the verdict exits **red-by-design** without needing E3's waivers. **And** an empty extraction is distinguished from "deps present but unresolved" (FR6).

**Given** a manifest-only repo with **no adjacent Python source** (the fleet's majority shape — feedstocks), **When** the hygiene axis runs, **Then** hygiene coverage is honestly **`not-applicable`/skipped, the reduced scope recorded — never a 100%-DEP002 noise wall** — matching Kedro FR-16's already-specced semantics for this schema's second producer. *(Added 2026-07-12 per readiness Major 3.)*

### Story 2.5: Name-level CVE tier + stale-DB + cross-ecosystem non-merge

As a **conda/pixi maintainer**,
I want a risk signal for my unpinned deps and honesty about the vuln-data freshness,
So that "vuln-coverage 12%" becomes an actionable worry-list, not a dead end.
*(Consumes the 1.4 provisioning decision for its stale-DB semantics.)*

**Acceptance Criteria:**

**Given** a mapped-but-unversioned dep, **When** the name-level tier runs, **Then** it flags whether the package carries **any known critical CVE across any version** ("pin/lock to prove immunity") — never assuming a version (FR13 guardrail).

**Given** an offline DB older than `--db-max-age` (per the 1.4 definition of "stale"), **When** scanned, **Then** the run routes to **`indeterminate` (exit 1) with a typed `vuln-data-stale` driver** — never a confident clean, never a silent 0 (FR12, aligned 2026-07-16 with NFR-S8 + C0); the report records the DB source + timestamp (FR11).

**Given** the same package name in a conda manifest AND a PyPI manifest, **When** inventoried, **Then** they stay **distinct per-ecosystem components** — no silent merge (FR7).

---

### Story 2.6: Lockfile extraction — the locked-closure vuln hero path (split from 2.1, 2026-07-16)

As a **maintainer with a committed lockfile**,
I want the locked closure extracted with exact versions,
So that the vuln axis scans proof, not guesses (FR3/FR13 substrate; the vuln hero path).

**Acceptance Criteria:**

**Given** a `pixi.lock` or `conda-lock.yml` (the **vuln hero path**), **When** extracted via `extract/lockfiles.py`, **Then** the **locked closure** lands in the inventory with exact `==` versions, manager-aware routing (conda vs pip rows → the correct ecosystem), `vuln_matchable=true` where `pypi_identity` resolves, and coverage marked `locked-closure`; fixtures include the **URL-basename pitfall** (a subdir segment must never be mis-captured as a package name — a documented shipped-parser regression). *(Ownership added 2026-07-12 per readiness Major 2 — previously unowned.)* **And** `extract/lockfiles.py` is validated against **py-rattler's `LockFile`** parse as a *test-side* oracle (never a runtime dependency — the lean-dep policy holds; added 2026-07-12).

**Given** the standing cross-cutting gates, **When** this story lands, **Then** C0/C0c and the NFR-S* suite hold on the new `extract/lockfiles.py` surface (AST-denylist; no execution of untrusted input; line/size bounds per NFR-S5).

## Epic 3: Policy control + auditable waivers + warn-only

Make E1's `Policy` interface configurable + waivable, and add the adoption on-ramp.

### Story 3.1: Configurable policy (the ConfigLoader)

As a **team lead**,
I want to tune the gate per-repo without editing the tool,
So that the gate fits our risk posture.

**Acceptance Criteria:**

**Given** a `[tool.pyforge-warden]` table in `pyproject.toml` and/or `pixi.toml`, **When** loaded, **Then** config resolves with **per-key precedence** (pyproject wins; conflicts surfaced to stderr, never fail the build) and CLI flags override (FR30).

**Given** config values, **When** applied, **Then** `--fail-on`, the CVSS thresholds, the DEP001-block confidence threshold, and the coverage-floor (`--fail-under-coverage`, default off) all move the verdict (FR18/FR19 — incl. FR19's repurposed roles: the under-`--warn-only` coverage guardrail and the ceiling on waived-away `indeterminate` surface); a config-key type error → typed `config-validation` error. **And** the hygiene→status + CVSS-threshold tables live in the `ConfigLoader`.

### Story 3.2: Auditable expiring waivers

As a **developer under deadline**,
I want to file an auditable, time-boxed exception for a finding,
So that I can ship without lying about the risk.

**Acceptance Criteria:**

**Given** `--bypass --reason "<text>"`, **When** run, **Then** a `.warden-waivers.yaml` stanza (reason + authorizer + expiry — FR24) is emitted via `safe_dump` for the human to commit — the tool **never writes the repo** (NFR-S4); the reason round-trips safely (no YAML injection). **And** a valid waiver → status `bypassed`, exit 0, `review_required: true`.

**Given** a malformed or wildcard-over-broad waiver, **When** read, **Then** it is schema-validated and rejected (FR26); waivers are least-privilege (specific id+package+ecosystem) and every applied waiver is echoed in output (NFR-S3). **And** the waiver file carries an in-file **`version:`** key; an unknown/future version is rejected with a typed error, never guessed (added 2026-07-12 per PRD CLI § contract stability).

### Story 3.3: Waiver expiry + warn-only adoption on-ramp

As a **conda/pixi maintainer adopting the gate**,
I want expired waivers to re-block and a warn-only first-run mode,
So that suppression can't rot silently and I can adopt without a day-one red wall.

**Acceptance Criteria:**

**Given** a waiver past its `expires_at`, **When** the next scan runs, **Then** the finding **re-blocks** (exit 1) and applied/expired waivers are flagged for review (FR25). *(Waiver expiry changes the input rung; `verdict.py` still owns the projection.)*

**Given** `--warn-only`, **When** run on a repo with pre-existing findings, **Then** findings surface as `warn`, exit **0**, and the report nudges how to graduate to an enforcing gate (FR23); this defends the `gate-disabled = 0` anti-metric.

---

## Epic 4: Machine contract + CycloneDX SBOM

The CI pipeline / cf_atlas consumes an honest SBOM. *(Schema-stability + pure-JSON hardening were dissolved into 1.1's conformance test + 1.8's renderer.)*

### Story 4.1: CycloneDX SBOM emission

As a **CI pipeline / SBOM consumer**,
I want an honest CycloneDX SBOM of the resolved inventory,
So that I can feed downstream supply-chain tooling.

**Acceptance Criteria:**

**Given** `--sbom-output <file>`, **When** a scan completes, **Then** a schema-valid **CycloneDX 1.6** BOM is emitted via cyclonedx-python-lib as a **read-only projection over the frozen inventory** — source-registry-correct purls (`pkg:pypi/…` vs `pkg:conda/…?channel=`), **self-declared partiality** when coverage < 100% (FR27). **And** `len(SBOM.components) == inventory_count` (root excluded).

**Given** an adversarial component name (control chars, `</script>`, purl-reserved), **When** serialized, **Then** the schema-aware encoder neutralizes it (NFR-S7) — the tool is never an injection vector against a downstream consumer.

**Given** the estate SBOM conventions, **When** the BOM is emitted, **Then** conda↔pypi identity is expressed via the **`cfe:*` property namespace** (`cfe:pypi_purl`, `cfe:match_source`, `cfe:match_confidence` on the conda component), purls follow **G98 normalization** (lowercase, `_`→`-`, dots preserved; `?channel=` qualifier on conda purls), and the **round-trip holds**: `scan-project --sbom-in <our-BOM>` ingests cleanly. *(Added 2026-07-12 per readiness/X7 — three SBOM producers share these conventions.)*

---

## Epic 5: Fleet-readiness & adoption on-ramp

Survive fleet deployment and make adoption stick; defend the anti-metric.

### Story 5.1: Actionable diagnostics & safe-by-default posture

As a **maintainer whose build just went red**,
I want the failure to tell me how to fix it, not just that it failed,
So that I fix the finding instead of disabling the gate.

**Acceptance Criteria:**

**Given** any non-zero exit, **When** the human report is emitted, **Then** it names the offending package(s), the finding (advisory id + severity + fixed-version, or the hygiene rule), the source manifest + location, and a remediation path — surfaced as **concrete remediation content in the report/diagnostics**, not a re-wrap of 1.7's typed errors and **not a new subcommand** (an `explain` verb stays post-v1 per the PRD; reworded 2026-07-12) (NFR-U1 — "fail with a fix").

**Given** zero configuration, **When** the tool runs, **Then** the default posture is secure (block critical, expiring waivers, unknown-engine → fail-loud, air-gap explicit) paired with the warn-only on-ramp so day-one debt doesn't trigger a mass-disable (NFR-U2).

**Given** a developer workstation (P8 — added 2026-07-12), **When** the adoption docs land, **Then** they cover the local install story (`pixi global install` / the local channel now; **pixi-pack** bundles for air-gap; **nebi** for nebi-adopted teams — incl. the `nebi pull` → `scan .` pattern and versioned-env report diffing; conda-forge per OD5), the recommended first contact (`scan . --warn-only` at a terminal — per the spec's honest-adoption statement), and the **`warden scan --doctor` self-check — committed to v1** (D8, 2026-07-15): a *flag on the one frozen verb* (never a subcommand, no prompts) re-exposing FR21's engine/DB detection; its output honors NFR-I3 and its exit codes stay inside the frozen `{0,1,2,130}` enum (0 = environment healthy; 2 with a typed `error_kind` = engine/DB problem found; never 1 — doctor reports operability, not policy).

### Story 5.2: Fleet-scale validation + corpus/oracle maturation

As a **platform engineer deploying across 20k repos**,
I want the gate deterministic, parallel, and provably robust at scale,
So that it never flaps and I never have to disable it.

**Acceptance Criteria:**

**Given** the corpus-provisioning task (its **first** step — harvest + pin the ~1,950-file corpus so 5.2's gates aren't silently absorbing a fixture-harvesting spike), **When** it completes, **Then** the corpus is a committed, versioned fixture set **augmented with a small adversarial out-of-repo recipe set** (exotic selectors, `{% for %}`, unicode, oversized files — sourced in part from **`prefix-dev/rattler-build-parser-tests`**, the renderer's own parser-stress corpus; the in-repo corpus is a friendly, CFE-curated distribution; added 2026-07-12).

**Given** the registered axis producers (deptry + osv, plus the E6 license/currency producers once landed — widened 2026-07-15), **When** a scan runs, **Then** all axes run **in parallel** with no shared mutable state, per-invocation cost O(project) not O(fleet), and our overhead ≤ ~2s p95 on the reference corpus (engines-stubbed), **measured on a named reference machine recorded with the result** (NFR-P-warm/concurrency).

**Given** the full corpus, **When** the regression gate runs, **Then** **0 uncaught exceptions**, a **committed ratcheted `unparseable_rate` baseline** (CI fails on regression), the **differential-oracle passes across all formats** at corpus scale, and twice-run is byte-identical in `--deterministic` (NFR-R1/R2/R3b). **And** an out-of-range engine version fails loud (NFR-C1). **And** the **dogfood gate** holds (spec DoD): the tool runs clean on this repo's own `pixi.toml`/`pyproject.toml` via a committed `pixi run` task — exit 0 on the known-clean state, non-zero on a seeded-violation fixture (added 2026-07-12).


---

## Epic 6: Multi-axis expansion — license, currency, KEV/EPSS & adoption (added 2026-07-15; re-baselined 2026-07-16, D12)

The spec's four-axis v1 **with its gates**, delivered after E4 and before E5. One sanctioned schema amendment (6.1) unlocks the two new axis producers **with their flag-activated gates** (6.2/6.3, registered behind E1's existing `Engine` seam — the axis is an open string, no new interface work per OD7), the KEV feed + gate (6.4), the two-mode policy wiring (6.5), the engine version-range distribution gate (6.6), the EPSS feed + `--min-epss` gate (6.7), baseline & grandfathering (6.8), and the opt-in fix-PR actuator (6.9). Every story carries the standing cross-cutting gates (C0, C0c socket-deny, verdict.py sole-ownership, NFR-S*, NFR-R3b). Contract source: `docs/specs/pyforge-warden.md` §§ Reconciliation (D12), FR-K1/FR-L*/FR-C*/FR-B1/FR-A1 (canonical FR32–FR40), Release map.

### Story 6.1: The versioned `ComplianceReport` schema amendment

As the **owner of the frozen report contract**,
I want the one deliberate, versioned amendment that admits the new axes,
So that axes 3+4 and full KEV land without ad-hoc schema drift (FR38).

**Acceptance Criteria:**

**Given** the frozen v1 contract (story 1.1), **When** the amendment lands, **Then** `schema_version` bumps additively (staying `1.x` — `models.py`'s `_SCHEMA_VERSION_RE` pattern is honored, not widened), adding: a per-axis `gating` bool (computed by `config.py`, the single writer); `license` + `currency` report sections each carrying per-section coverage + provenance (FR15's widened per-axis form) (`{source, snapshot_at, max_age_ok}` — the bundled-data age fields, NFR-S9); **the license/currency finding-ID families + typed verdict encoding** (schema-validated fields — policy tables, waivers, and baselines key ONLY on these, never on free-text `indeterminate:` reason tokens); **the post-verdict `actuation` section** (FR40's slot); **the suppression rung-discriminator** (waiver-vs-baseline echo); `kev_date` on findings; `epss` widened to `{score, percentile}`; and per-feed KEV/EPSS provenance. **And** `report.py`'s assembly fails loud on a coverage claim for an unregistered axis (never a silent drop). **And** this story is a **HARD sprint dependency: no 6.x producer story may start before 6.1 is DONE**, and **6.1 itself is HARD-gated on story 6.10's decision record being DONE** — both gates encoded mechanically in `sprint-status.yaml` at regeneration (not a recommendation; numeric key order does NOT express this). **And** the coordinated update set is exactly: `report-schema.json` · `models.py` (+ `to_json_dict` render + sort keys) · `report.py` runtime self-validation + `_REPORT_AXES` · the exact-13 `Component` test (widened deliberately, with Gap-B merge/fold semantics defined for every new `Component` field) · fixtures. **And** no other story widens the schema — the producer re-closes behind this amendment (asserted by the conformance suite).

**Given** a pre-amendment consumer reading a post-amendment report, **When** it validates, **Then** additive-only compatibility holds (the existing `test_additive_extra_fields_still_validate` property is preserved) and byte-identical determinism (`--deterministic`) still holds across the widened field set (NFR-R3b).

### Story 6.2: License axis producer + gate flags (Axis 3)

As a **compliance-conscious maintainer**,
I want every resolved component to carry an honest SPDX license verdict, gateable the moment I configure a policy,
So that license exposure is visible by default and blockable in v1 (FR32/FR33 — D12).

**Acceptance Criteria:**

**Given** a conda component with `about: license:` in its recipe, **When** the axis runs, **Then** the license normalizes to an SPDX expression via `license-expression` **pre-build** (no install), with `license_family` + `source` recorded and verdict `allowed | denied | unknown` (FR32). **And** the producer registers behind the existing `Engine` seam with `axis="license"` — no new interface. **And** the standing cross-cutting gates hold on the new surface (C0 on the story's fixtures; C0c socket-deny; NFR-S* on any parsing it adds).

**Given** a bare uninstalled PyPI manifest and no license policy flags, **When** the axis runs, **Then** every unresolvable component is `unknown` — surfaced per FR37 via the `warn` rung (never a silent clean, never an unconfigured red gate) — and the axis's `AxisCoverage` reports honest `deps_assessed`/`deps_total`. **And** an installed/locked env resolves PyPI licenses via `importlib.metadata` (PEP 639 `License-Expression`, legacy `License`, trove classifiers). **And** no source scanning occurs (ScanCode-class deep-scan stays deferred).

**Given** `--allow-licenses` and/or `--deny-licenses` (FR33 — v1, D12), **When** either flag is set, **Then** the flags **parse into the FR30 ConfigLoader policy tables** (CLI overrides config, per-key precedence) and `config.py` flips the license axis's `gating` bool — **this story's producer never feeds a rung above `warn`** — and 6.2 **delivers** the no-Status-above-warn producer meta-test as a parameterized suite over every registered axis producer (6.3 registers into it); the actual escalation (denied → `policy-violation`, unknown → `indeterminate`, never a silent clean) is **asserted end-to-end in story 6.5**, which solely owns it.

### Story 6.3: Currency axis producer + gate flags (Axis 4)

As a **platform owner tracking supportability**,
I want tiered, age-honest currency verdicts for components and the Python runtime, gateable the moment I configure a policy,
So that EOL exposure is visible by default and blockable in v1 (FR34/FR35 — D12).

**Acceptance Criteria:**

**Given** the bundled LTS registry (`src/pyforge/warden/data/lts-registry.yaml`, loaded via `importlib.resources`, regenerated from the CFE source copy), **When** a verdict derives from bundled data, **Then** it carries the registry's build-time `snapshot_at` and a `max_age_ok` verdict against a configurable max-age (default 180 days) — a stale bundled registry can never silently report `supported` (NFR-S9).

**Given** edge mode (no atlas, offline default), **When** the tier ladder runs (LTS registry → cached endoflife.date → N/N-1 from channel data → `unknown`), **Then** tiers whose data is absent degrade to a **visible** `unknown` (FR37 `warn` rung), the per-mode tier matrix is honored, and the **ADD/UPDATE availability-at-N/N-1 finding is omitted with a coverage note** (fleet-mode only — it requires the estate's policy tier via `inventory-match`). **And** `runtime_python` currency is a first-class field. **And** the endoflife.date fetch follows the `_http.py` mirror-override pattern: offline default, opt-in online, never silent (NFR-S2).

**Given** `--max-lag` / `--require-lts` / `--fail-on-eol` (FR35 — v1, D12), **When** any flag is set, **Then** the flags **parse into the FR30 ConfigLoader tables** and `config.py` flips the currency axis's `gating` bool — **this story's producer never feeds a rung above `warn`** (producer meta-test); escalation (`eol`/over-lag → `policy-violation`, `unknown` → `indeterminate`, **freshness-preconditioned**: a stale bundled registry under an active currency policy → `indeterminate`, never a pass — NFR-S9) is **asserted end-to-end in story 6.5**. **And** this story consumes `feeds.py` (6.4's skeleton) for the endoflife cache — it builds no private cache and computes no staleness itself.

### Story 6.4: KEV feed provisioning, enrichment & the `--fail-on-kev` gate

As a **security engineer**,
I want the gate to block known-exploited vulnerabilities with honest feed semantics,
So that a KEV listing can never be silently missed (FR36).

**Acceptance Criteria:**

**Given** a provisioned KEV feed (cache layout, lifecycle, and max-age policy documented — the OSV-DB provisioning decision record `osv-db-offline-provisioning-decision.md` is the template), **When** a security finding matches a KEV-listed advisory on a pinned version, **Then** the finding carries `kev: true` (+ `kev_date` post-6.1) and the verdict blocks (`--fail-on-kev` is in the FR18 default) — exit 1. **And** this story delivers the **`feeds.py` skeleton** (ONE cache layout + ONE provenance shape + staleness/max-age defaults living in `feeds.py`, overridable only via the FR30 ConfigLoader) that 6.3 and 6.7 consume — axes never compute staleness. **And** KEV/EPSS enrichment mutates findings at exactly one pipeline position: inside the vuln producer, before policy dedup. **And** this story ships a **hermetic fixture KEV feed** (the 1.4 fixture-DB precedent) wired into the test harness, so the default-on `--fail-on-kev` policy never flips shipped E1/E2 fixtures to `indeterminate`. **And** the KEV tier's opt-out is named and testable: the FR30 config key `policy.fail_on_kev = false` (config/table-driven — the coarse `--no-fail-on-*` flag family stays retired), which makes the no-KEV-policy branch reachable.

**Given** an absent or stale KEV snapshot **while a KEV-blocking policy is in effect**, **When** the scan runs, **Then** the verdict is **`indeterminate` with a KEV-provenance driver** — the gate never silently no-ops (the review-T1 fix). **And** with **no** KEV policy in effect, null slots gate on CVSS as before. **And** the report's per-feed KEV provenance (`{source, snapshot_at, max_age_ok}`) makes `kev: null` (feed absent) distinguishable from "assessed, not KEV-listed". **And** feed fetch is offline-default / opt-in-online / never silent (NFR-S2).

### Story 6.5: Two-mode policy integration (unconfigured visibility + flag-activated gating)

As the **owner of the never-false-green invariant**,
I want unconfigured-axis verdicts visible without blocking AND configured axes gating in the same release,
So that `gating: false` is honesty, not invisibility, and a configured policy actually blocks (FR37 + FR33/FR35 — D12).

**Acceptance Criteria:**

**Given** an axis with `gating: false` (unconfigured license/currency), **When** a component's verdict is `unknown`, `denied`, or `eol`, **Then** the policy feeds a **`warn` rung** whose driver names the axis + finding — status `warn` (not `clean`), exit 0 — and a clean run on gating axes with any non-gating unknowns can never render status `clean`. **And** `--warn-as-error` escalates these to non-zero for strict shops. **And** this story **solely owns the escalation mapping** for axes 3/4 (producers are meta-tested to never feed above `warn`; both modes proven by running the identical fixture set and diffing only rungs/exit). **And** the tighten-only rule is applied as redefined by the architecture (2026-07-16): the shipped 1.2 `indeterminate` backstop is a **placeholder, not a floor** — the axis's defined mapping (warn unconfigured / gate configured) supersedes it for that axis; the C0 bound (never toward `clean`) is the invariant; verdict.py sole-ownership guard passes.

**Given** an axis whose policy flags are configured (FR33/FR35 — v1, D12), **When** `gating` flips true for that axis, **Then** the same outcomes escalate (`denied`/`eol` → `policy-violation`, `unknown` → `indeterminate`) **with no producer changes** — the escalation is a policy-table change only, proven by running the identical fixture set in both modes and diffing only the rungs/exit.

### Story 6.6: Engine version-range pinning (the distribution gate)

As the **release owner**,
I want the engine run-deps constrained to tested version ranges,
So that publishing can't ship the fleet-wide false-error the ranges exist to prevent (NFR-C1).

**Acceptance Criteria:**

**Given** `src/shared/packages/pyforge-warden/pixi.toml` (run-deps `deptry = "*"`, `osv-scanner = "*"` today), **When** this story lands, **Then** both engines carry a **tested version range** (per NFR-C1: a range, not an exact pin — the engines come from feedstocks), the range choice is recorded with its compatibility evidence (deptry output schema; osv `--format json` shape + exit-code contract), and an out-of-range engine at runtime fails loud via FR21's typed `engine-unavailable`/incompatible error. **And** internal JFrog v1 publish and public v1.x publish are both blocked until this story is DONE (the D6 gate) — encoded mechanically as a release-gate row in `sprint-status.yaml` and a checkbox in the spec DoD (its mechanical homes, not process prose). **And** the story is the recorded owner of `pixi.toml:32-33` — closing the review-T-a finding that no story owned the mitigation. **And** the standing cross-cutting gates hold (C0 fixtures unaffected by the range change; twice-run determinism NFR-R3b).

### Story 6.7: EPSS feed + the `--min-epss` gate

As a **security engineer prioritizing by exploit likelihood**,
I want EPSS scores on findings and a probability-threshold gate with honest feed semantics,
So that exploit-likely vulnerabilities block and a missing feed can never fake a pass (FR36 — D12).

**Acceptance Criteria:**

**Given** a provisioned FIRST EPSS feed (cache layout, lifecycle, max-age policy — story 6.4's KEV feed work is the direct template, one shared `feeds.py` layer; this story builds no private cache and computes no staleness itself), **When** a security finding matches, **Then** it carries `epss {score, percentile}` (post-6.1 schema) with per-feed provenance `{source, snapshot_at, max_age_ok}`, and `--min-epss <0..1>` blocks at/above the threshold (`policy-violation`).

**Given** an absent or stale EPSS snapshot **while `--min-epss` is set**, **When** the scan runs, **Then** the verdict is **`indeterminate`** with an EPSS-provenance driver — the mirrored FR-K1 absence rule: an active policy never silently no-ops. **And** with no `--min-epss` set, null `epss` slots change nothing (CVSS/KEV gate as before). **And** feed fetch is offline-default / opt-in-online / never silent (NFR-S2).

### Story 6.8: Baseline & grandfathering (gate new findings only)

As a **maintainer adopting the gate over existing debt**,
I want to accept today's findings in a committed, expiring baseline and block only new ones,
So that day-one debt doesn't force disabling the gate — and nothing is silently suppressed (FR39 — D12).

**Acceptance Criteria:**

**Given** `--baseline .warden-baseline.yaml` (committed, schema-validated — malformed → typed `config-validation` error, never a guess), **When** the scan runs, **Then** findings whose **stable finding IDs** (the full finding-ID grammar — 1.1's three families **plus 6.1's license/currency families**; the same key waiver matching uses) appear in the baseline do not block; **NEW findings gate normally**; every applied baseline entry is **echoed in the report** carrying the 6.1 **suppression rung-discriminator** marking it `baseline` (vs `waiver`) — loud, `bypassed`-style; C0 holds: a baselined run can never render `clean`, and the baseline can never mask an `error`.

**Given** a baseline entry past its `expires_at` (waiver-identical semantics), **When** the scan runs, **Then** the finding **re-blocks** until fixed or re-accepted. **And** the tool only ever **reads** the baseline (NFR-R3a/S4); `--baseline-emit` prints a candidate stanza for the human to commit — the tool never writes the repo. **And** baseline entries are a **second input to 3.2's suppression engine** — one engine, no parallel suppression path; baseline + waiver interaction is deterministic (waiver wins where both match — one suppression, echoed once, discriminated per 6.1).

### Story 6.9: Fix-PR actuator (opt-in remediation PRs)

As a **platform engineer running the gate at fleet scale**,
I want findings to open remediation PRs automatically when I opt in,
So that the gate drives fixes, not just red builds (FR40 — D12).

**Acceptance Criteria:**

**Given** `--open-fix-prs` with forge credentials provided via environment (never flags), **When** the verdict has been composed (exit code fixed), **Then** `cli.py` — the sole invoker — runs the actuator, **then** assembles + emits the final report including the `actuation` section (6.1's slot; content in the NFR-R3b volatile-field set): order = compose verdict → actuate → assemble → emit. PRs open via the forge API — security findings → upgrade-to-fixed-version PRs; hygiene unused-dependency findings → removal PRs — with the finding ID + report excerpt in the PR body. **And** the scanned working tree is **never written** (NFR-R3a asserted by the harness); the actuator is the **only** component permitted forge egress, and the C0c socket-deny carve-out applies **only to the real path under the flag** (landed in this story, never a global loosening), inert without the flag.

**Given** `--fix-prs-dry-run`, **When** the actuator runs, **Then** it shares the real code path up to the egress seam, writes its intent into the same `actuation` report section (stdout stays ONE pure document, NFR-I3), and **opens no sockets** (the carve-out does not apply to dry-run). **And** a failed PR-open is recorded in the `actuation` section + stderr — **never an FR20 rung**; verdict, status, and exit code unchanged. **And** duplicate protection: an existing open PR for the same finding ID is detected and skipped, never re-opened.

### Story 6.10: Amendment design spike — finding-ID families, verdict encoding, rung-discriminator & fold semantics (decision record)

As the **owner of the one sanctioned schema amendment**,
I want the amendment's unspecified shapes pinned in a decision record before 6.1 freezes them,
So that the HARD-gate story is a mechanical schema bump, not design work on the critical path (the story-1.4 spike precedent).

**Acceptance Criteria:**

**Given** the 6.1 scope list, **When** the spike completes, **Then** a committed decision record (planning-artifacts) pins: the **license/currency finding-ID family grammars** (single-line, colon-delimited, injective — same rules as the three shipped families) and the **typed verdict encoding** (schema-validated fields policy/waivers/baselines key on); the **suppression rung-discriminator** shape (a closed `baseline | waiver` marker on echoed suppressions); and the **Gap-B merge/fold table** for every new `Component` field (conservative C0 semantics per field, `_merge_group`/`_fold_bare` positions named).

**Given** the decision record, **When** 6.1 executes, **Then** 6.1 implements it without new design decisions — 6.1 remains the sole schema writer and the HARD gate (one amendment, one bump; this spike changes no code and no schema).


