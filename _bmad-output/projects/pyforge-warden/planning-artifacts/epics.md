---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
inputDocuments:
  - docs/specs/pyforge-warden.md
  - planning-artifacts/prd.md
  - planning-artifacts/architecture.md
  - planning-artifacts/implementation-readiness-report-2026-07-12.md
  - planning-artifacts/adversarial-review-pyforge-warden-spec-2026-07-15.md
replan:
  date: 2026-07-15
  story: "0.1"
  note: "Story-0.1 replan executed: Epic 6 (multi-axis expansion) added from the spec's v1 tier; the spec (docs/specs/pyforge-warden.md) is upstream and wins conflicts."
  rebaseline: "2026-07-16 (D12): v1 absorbs the axis gates (flag-activated), EPSS, baseline & grandfathering, fix-PR actuator — Epic 6 grows to stories 6.1-6.9 (FR32-FR40); 29 stories total."
---

# pyforge-warden - Epic Breakdown

## Overview

Complete epic and story breakdown for **pyforge-warden** — a non-interactive CI/CD security-gate CLI that unifies dependency-hygiene (deptry) + known-vulnerability scanning (osv-scanner) into one schema-validated report behind one exit code, for Python projects sourced from PyPI **or** conda-forge. Decomposed from the completed PRD (FR1–FR31 + 22 NFRs) and the completed architecture (§ Core Architectural Decisions / § Project Structure / § Implementation Patterns). **No UX** (non-interactive CLI). Epics are **vertical slices that ship end-to-end value** — the technical layers E1–E4 map *across* the slices (per the readiness report's Epic-Quality flags).

## Requirements Inventory

### Functional Requirements

**A. Manifest Discovery, Ingestion & Extraction**
- FR1: discover + classify candidate manifests under a path; deterministic selection/precedence; report the resolved scan set.
- FR2: classify each dependency *source section* (pixi `[dependencies]` vs `[pypi-dependencies]`; env.yml conda vs `- pip:`) → correct extractor.
- FR3: extract deps from conda/pixi **source** manifests without a resolved environment.
- FR4: delegate to engines' native parsers for PyPI inputs (no bespoke parsing).
- FR5: best-effort templating/selector eval; degrade to name-only+marked, never fail.
- FR6: per manifest, distinguish "no deps present" vs "deps present but unresolved."
- FR7: keep per-ecosystem attribution; no silent cross-ecosystem merge.

**B. Dependency-Hygiene (Axis 1)** — FR8 hygiene findings (unused/missing/transitive/misplaced), PyPI+conda · FR9 honor `[tool.deptry]` ignores.

**C. Vulnerability (Axis 2 — Security)** — FR10 vuln findings (advisory/affected-fixed/severity), actionable · FR11 offline/air-gapped DB, offline-by-default, records source+timestamp · FR12 detect **stale DB** → degrade verdict · FR13 unresolved version → **vulnerability-indeterminate** + name-level CVE tier (mapped-but-unversioned → "carries known critical CVEs"); guardrail: coverage improves only by resolving or name-level flagging, never by assuming a version.

**D. Honest Coverage & Reporting** — FR14 schema-validated report (status/severity/schema_version/coverage/error_kind) · FR15 **per-axis coverage** (one dimension per registered axis; v1: hygiene, vulnerability, license, currency — widened 2026-07-15) · FR16 partial coverage → qualified verdict, never bare "clean" · FR17 human + machine report, every blocking finding actionable.

**E. Policy Gate & Verdict** — FR18 gate on content+severity (vuln axis default critical **+ any CISA-KEV-listed advisory (FR36)**; **hygiene axis separate — DEP001 blocks by default (mapping-confidence-gated), DEP002/3/4 warn**) · FR19 minimum coverage-floor gate (default OFF) · FR20 verdict-composition (lattice `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable` + separate exit; indeterminate → non-zero) · FR21 detect engine presence/version + typed error_kinds routed to owner, never silent PASS · FR22 no-meaningful-scan → non-passing, never clean · FR23 warn-only mode.

**F. Waivers & Bypass** — FR24 auditable expiring waiver (reason/authorizer/expiry), read-not-written · FR25 re-block on expiry + flag for review · FR26 validate waiver schema, reject malformed/malicious.

**G. SBOM & Machine Contract** — FR27 CycloneDX 1.6 SBOM (source-registry purls, self-declared partiality) · FR28 stable exit-code contract.

**H. CLI Operation & Configuration** — FR29 one non-interactive command → one exit code · FR30 dual `[tool.pyforge-warden]` config (pyproject+pixi, per-key precedence, owns hygiene→status + CVSS-threshold tables) · FR31 `--version`/`--help` stable contract.

**I. License Axis (Axis 3 — added 2026-07-15; gate → v1 per D12)** — FR32 SPDX license enrichment (`license-expression`; conda `about:` pre-build + PyPI `importlib.metadata`; no source scan; unconfigured → `warn`) · FR33 *(v1, flag-activated)* `--allow/--deny-licenses` gate: denied → policy-violation, unknown → indeterminate.

**J. Currency Axis (Axis 4 — added 2026-07-15; gate → v1 per D12)** — FR34 tiered currency (bundled LTS registry → endoflife.date → N/N-1 → unknown; deps + `runtime_python`; per-mode tier matrix; bundled-data `snapshot_at`+`max_age_ok`; ADD/UPDATE fleet-only; unconfigured → `warn`) · FR35 *(v1, flag-activated)* `--max-lag`/`--require-lts`/`--fail-on-eol`, freshness-preconditioned.

**K. Security Enrichment & Axis Mechanics (added 2026-07-15; EPSS → v1 per D12 2026-07-16)** — FR36 KEV **+ EPSS** enrichment (`kev`,`kev_date`,`epss{score,percentile}`) + `--fail-on-kev` + `--min-epss` (both v1; absent/stale feed under an active policy → `indeterminate`, never a silent no-op; per-feed provenance) · FR37 unconfigured-axis visibility (`unknown`/`denied`/`eol` → `warn` rung, never silent clean; configuring an axis's flags activates its v1 gate) · FR38 the one versioned schema amendment (per-axis `gating` bool, license/currency sections, `kev_date`/`epss` object, per-feed provenance; `report.py` + schema + exact-13 test + fixtures).

**L. Adoption & Remediation (added 2026-07-16, D12)** — FR39 baseline & grandfathering (committed schema-validated `.warden-baseline.yaml`, finding-ID-keyed, waiver-identical expiry; gate blocks NEW findings only; applied entries echoed loud; read-not-written) · FR40 fix-PR actuator (opt-in `--open-fix-prs`, env credentials, post-verdict forge-API PRs — upgrade/removal; never writes the scanned tree; `--fix-prs-dry-run`).

### NonFunctional Requirements

- **C0 — Gate-Integrity invariant (cross-cutting acceptance property):** never false-green; N adversarial fixtures → 0 exit-0.
- **Reliability:** NFR-R1 corpus 0 uncaught exceptions (~1,950 files) · R2 ratcheted unparseable-rate baseline · R3a no repo/host mutation · R3b two-tier determinism (decision-deterministic default; byte-identical `--deterministic`) · R5 bounded engine timeout.
- **Security:** S1 no execution of untrusted input (AST-denylist, no jinja-render, safe_load only) · S2 no silent egress (socket guard) · S3 waiver untrusted + least-privilege · S4 no repo writes + secure temp · S5 ReDoS/resource bound · S6 engine-input purity (no requirements/argv injection) · S7 output neutralization (schema-aware encoder) · S8 trusted-input integrity (fresh+authentic DB) · **S9 bundled-data max-age (added 2026-07-15: `snapshot_at`+`max_age_ok` on LTS-registry/map-derived verdicts; stale bundled data never silently `supported`)**.
- **Performance:** NFR-P-warm (overhead ≤ ~2s p95, engines-stubbed) · P-cold (cacheable first-run DB) · P-concurrency (engines parallel, no shared state, O(project)).
- **Interoperability:** I1 schema conformance (report JSON schema, CycloneDX 1.6, purl) · I2 schema-version field + frozen exit enum `{0,1,2,130}` · I3 machine-output purity (stdout = one doc or empty).
- **Usability:** U1 actionable diagnostics (fail-with-a-fix) · U2 safe-by-default + warn-only on-ramp.
- **Portability:** C1 Python ≥ 3.12; engines on PATH in a tested version range; pixi ≥ 0.72.2.

### Additional Requirements

*From the architecture (§ Core Architectural Decisions / § Project Structure / § Implementation Patterns) + the readiness report — these shape the epic/story design:*

- **Greenfield scaffold EXISTS** at `src/shared/packages/pyforge-warden/` (pixi build member, `cli.py` stub, 2 smoke tests green). Epic 1 Story 1 = **complete-the-scaffold** (wire the pipeline into the stub + add the targeted deps + stand up the test harness), **not** create-from-template.
- **Targeted runtime deps** (relax `dependencies = []`): PyYAML (`safe_load`/`safe_dump`), packaging, cyclonedx-python-lib, jsonschema; engines deptry + osv-scanner as conda run-deps.
- **The single shared spine:** ONE `ResolvedInventory` + `Component{name,version|None,ecosystem,pypi_identity|None,purl,provenance:[(manifest,section)],hygiene_covered,vuln_matchable,indeterminate_reason|None}`; canonical StrEnums (`Status`/`ErrorKind`/`WithholdReason`/`Ecosystem`); the verdict lattice + exit projection owned solely by `verdict.py`. Established in the first slice; every later slice builds on it.
- **The `_engine_env()` normalization helper + pure-JSON stdout seam** — build in the first engine-integration slice (cheap-now, ruinous-to-retrofit).
- **Bundled `data/conda_pypi_map.json` asset** — generate from the atlas `export-purls` conda↔pypi TSVs (powers the Gap-C `pypi_identity` predicate that prevents the silent `pytorch`→`torch` false-green).
- **The E1 extraction is non-rendering parse-as-data** + a **supported-construct matrix** (compiler/stdlib→build-tool-exclude, pin_subpackage→internal-exclude, selectors→union+mark, expr-logic→degrade) — an owned deliverable.
- **4 first-story open items** (readiness gap analysis): (a) generate the conda→pypi map from the atlas; (b) pick the name-mapping confidence threshold (DEP001 block vs warn); (c) pick the coverage denominator formula; (d) confirm the osv offline-DB provisioning mechanism.
- **Cross-cutting acceptance gates applied to EVERY story** (not a single "do security" story): **C0** (false-green=0 on the slice's fixtures) · **C0c — socket-deny (NFR-S2, no silent egress):** a deny-by-default socket harness landed in 1.2 — any egress during a scan is a hard test failure — self-enforcing for every future engine, plus visible ACs on 1.5 (osv/DB) + 2.2 (extraction) · **verdict.py sole-ownership guard** (a static check fails CI if any module other than `verdict.py` invokes an exit primitive with a guarded exit value or materializes the rung ordering as an ordered sequence literal — stories *feed* rungs, only verdict.py *projects*; wording amended 2026-07-13, see story 1.1 AC 6) · the **NFR-S\*** suite (AST-denylist for any new `extract/` module, output-neutralization, engine-input purity, ReDoS bound) · **NFR-R1/R2** (0 uncaught exceptions + ratcheted rate on any new corpus surface) · **NFR-R3b** (twice-run byte-identical in `--deterministic`) · **differential-oracle** (E1 dep-set ⊇ rattler-build/conda-build render; *skip-if-renderer-unavailable* at fixture scale in 2.2, matured to corpus scale in 5.2).

### UX Design Requirements

**N/A** — non-interactive CI CLI; no human-UI surface. The human-facing affordances (actionable diagnostics, warn-only on-ramp, `--version`/`--help`) are owned as FR17/FR23/FR31 + NFR-U1/U2, not as UX artifacts.

### FR Coverage Map

`FR1,2,4,8,9,10,14,17,18,20,21,22,28,29,31` → **E1** · `FR3,5,6,7,11,12,13,15,16` → **E2** · `FR19,23,24,25,26,30` → **E3** · `FR27` → **E4** · **`FR32,33,34,35,36,37,38,39,40` (+ NFR-S9, NFR-C1's distribution gate) → E6 (added 2026-07-15; grown 2026-07-16 per D12)** · *(NFR-driven: U1,U2,P-*,R2,C1)* → **E5**. All 40 FRs covered; dependencies strictly backward in the delivery order (E1 → E2 → E3/E4 → **E6** → E5 — E6 consumes E1's frozen contract + E2's inventory and executes the one sanctioned schema amendment, 6.1, before E5's fleet validation). *(Post-roundtable corrections: FR1 → its own Story 1.9; FR9 realized in 1.3 (E1), not E3; FR15 realized in 2.4 (E2), not E1; FR24 tagged in 3.2. Story-level FR→AC tags are authoritative over this epic-level summary.)*

**Recommended wedge-first build order** *(delivery sequence — the diamond; epics remain value-groupings, deps stay backward):* `1.1 → 1.2 → 1.3 (deptry) → 1.9 (discovery) → 2.1 (map + pypi_identity → indeterminate = the wedge demo) → 2.2 (extraction + oracle) → 1.4 (OSV spike) → 1.5 (osv) → 2.5 (name-level CVE) → 1.6 (gate) → 1.7/1.8 (report) → 2.3/2.4 → E3 → E4 → **6.1 (schema amendment — HARD gate: no 6.x producer starts before it) → 6.4 (KEV + the feeds.py skeleton) → 6.2/6.3 (axis producers + flag parsing, parallel; 6.3 consumes feeds.py) → 6.5 (escalation, solely owned) → 6.7 (EPSS, consumes feeds.py) / 6.8 (baseline, extends the waiver suppression core) → 6.9 (fix-PR actuator) → 6.6 (engine ranges)** → E5`. A conda maintainer sees differentiated value (`scan recipe.yaml → honest indeterminate-or-clean`) by ~step 5, not step 8. The two data-provisioning spikes (OSV-DB, conda→pypi map) are hit early, not stacked at the midpoint; the map generation runs as a **parallel read-only atlas data task**.

**Execution model (2026-07-12 — "Option B", `docs/specs/bmad-loop-adoption.md`):** these stories run **loop-driven** — `bmad-loop` v0.8.1 orchestrating `bmad-dev-auto` sessions. Each story is converted to a dev-auto spec whose contract is this document's **Given/When/Then ACs, preserved verbatim**; the loop's deterministic `[verify]` command is the scanner's own test suite (`pixi run -e pyforge-warden pyforge-warden-test` — the 1.2 harness + C0a/C0c gates thereby police every later story mechanically); gates graduate `per-story-spec-approval` (1.1/1.2 contract freeze) → `per-epic` (Epic 2+) → revisit `none` for the tail; the sprint feed is `sprint-status.yaml` (`bmad-sprint-planning`); CRITICAL escalations pause the run for `bmad-loop-resolve`.

**Story renumber (2026-07-12):** bmad-loop's sprint parser requires pure-numeric `N.M` story keys, so the Phase-0 letter-suffixed IDs were renumbered (document order preserved): `1.1a→1.1 · 1.1b→1.2 · 1.2→1.3 · 1.3a→1.4 · 1.3b→1.5 · 1.4→1.6 · 1.5a→1.7 · 1.5b→1.8 · 1.6→1.9 · 2.2a→2.2 · 2.2b→2.3 · 2.3→2.4 · 2.4→2.5` (E3–E5 unchanged). Historical documents (the dated readiness reports, the Phase-0 gist) retain the old IDs — read them through this map.

## Epic List

*Vertical-slice epics (architecture complete). Stress-tested via [A] dependency-mapping + a party-mode roundtable (PM/Dev/Architect), then a **full restructure** the roundtable mandated: the risky work is split into single-agent-sized stories (keystone 1.1→1.1/1.2; the two data-provisioning **spikes extracted** — OSV-DB as 1.4, conda→pypi map as a parallel task; the 2.2 extractor split 2.2/2.3; FR1 discovery promoted to its own Story 1.9; the report split 1.7/1.8) while the **commodity tail shrinks** (4.2 dissolved into conformance tests; E4/E5 kept lean). **29 stories** (2026-07-15: +Epic 6; 2026-07-16 D12: Epic 6 grown to 6.1–6.9 — axis gates, EPSS, baseline & grandfathering, fix-PR actuator all v1; story **0.1** — the spec-first replan of this document set — was executed 2026-07-15/16 and is recorded, not scheduled; `sprint-status.yaml` regeneration via `bmad-sprint-planning` is a follow-on once this replan merges). E1 remains a **contract-first walking skeleton, not a foundation dump** — the `Component` record + `ComplianceReport` schema + full 7-rung lattice are frozen WHOLE in 1.1 (field shape/type/optionality frozen now; two enums' variant-sets may grow **additively** in E2, safe because 1.1's projection treats any unknown match-level → `indeterminate`, never `clean`). Cross-cutting gates (C0a/C0b/C0c, verdict.py sole-ownership guard, NFR-S\*, corpus 0-exceptions, differential-oracle) are per-story acceptance gates, not a separate epic.*

### Epic 1: Spine + PyPI engine (walking skeleton)
A maintainer gates a **PyPI project** end-to-end — unified deptry+osv verdict + one exit code — while the run establishes the shared spine as a *vertical slice* (never "build the spine" as infra). **4 E1 definition-of-done conditions (roundtable-mandated):** (1) **interface-first** — `extract`/`routing`/`engine`/`vuln-strategy`/`Policy` are plugin/strategy interfaces, PyPI is the first registered impl; (2) the **`Component` record + `ComplianceReport` JSON schema + full 7-rung verdict lattice are frozen WHOLE in 1.1** (all fields present with honest non-degenerate PyPI values; two enums may grow additively in E2 under a conservative projection); later epics are **producers, never editors**; (3) **C0a (projection-safety)** owned + tested against the projection directly, gated on every epic; the `indeterminate` rung ships as a **proven-total socket**; (4) the **regression-harness skeleton hoisted to 1.2** (2 PyPI fixtures + the C0c socket-deny harness). **Internally gated:** cluster-1 (1.1 model+lattice → 1.2 interfaces+null engine, green) **before** cluster-2 (1.3 deptry → 1.4/1.5 osv).
**Stories (9):** 1.1 frozen contract + lattice + C0a · 1.2 interfaces + null engine + harness + C0c · 1.3 deptry · 1.4 OSV-DB spike · 1.5 osv · 1.6 gate + verdict · 1.7 typed errors + no-scan guard · 1.8 report renderers · 1.9 discovery (FR1).
**FRs covered:** FR1, FR2, FR4, FR8, FR9, FR10, FR14, FR17, FR18, FR20, FR21, FR22, FR28, FR29, FR31

### Epic 2: The conda/pixi source-manifest wedge
A conda-feedstock/pixi maintainer gets the gate on their **source** manifest (recipe.yaml/meta.yaml/environment.yml/pixi.toml) — the differentiated value no incumbent delivers (**beachhead value; pulled as early as possible**). Registers the conda+pixi extractors behind E1's interfaces; the **non-rendering parse-as-data + supported-construct matrix**; generates the **conda→pypi map from the atlas** *(CFE Rule 1)*; the `pypi_identity` predicate + confidence threshold; the **`indeterminate` PRODUCER + C0b (withhold-completeness)**; the name-level CVE tier; the **differential-oracle**. Ships red-by-design `indeterminate` exits without needing E3's waivers.
**Stories (5):** 2.1 conda→pypi map + pypi_identity · 2.2 non-rendering extraction + oracle · 2.3 full construct-matrix · 2.4 split coverage + indeterminate producer (C0b) · 2.5 name-level CVE tier + stale-DB + non-merge.
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
**Stories (9):** 6.1 versioned schema amendment · 6.2 license axis + gate flags · 6.3 currency axis + gate flags · 6.4 KEV feed + gate · 6.5 two-mode policy integration · 6.6 engine version-range pinning · 6.7 EPSS feed + `--min-epss` · 6.8 baseline & grandfathering · 6.9 fix-PR actuator.
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

**Given** the offline-first constraint (NFR-S2/S8), **When** the spike concludes, **Then** a **decision record** documents the chosen mechanism (bundled-conda-DB vs `--offline` + a provisioned local DB), how "stale" is defined (feeds FR12), and the trust-anchor/authenticity check (NFR-S8). **And** a **hermetic fixture DB** the conformance harness can consume offline is produced.

**Given** the decision, **When** downstream stories consume it, **Then** it explicitly gates **1.5** (osv engine) and **2.4** (stale-DB semantics) — and **not** 1.3 (deptry has no OSV surface).

**Given** a workstation cold start (no DB provisioned — persona P8), **When** the spike decides the provisioning UX, **Then** the decision record also covers (added 2026-07-12): the fail-loud + **actionable-nudge** message (how to provision / `--db-path`); whether an explicit **online opt-in** query mode ships in v1 (the PRD's "opt-in, never silent" path — currently unowned) or v1 is offline-only-everywhere with trivial provisioning; the concrete **engine version ranges** to pin (NFR-C1) + the version-detection mechanism; reuse of the in-repo **`update-cve-db`** offline-OSV provisioning surface vs a new downloader; an env-var **mirror override** for the DB fetch (JFrog/air-gap discipline); and verification of osv's `--lockfile=<parser>:<path>` override (may remove the `requirements.txt` temp-name constraint). The decision record also names the **env distribution channels**: `pixi global install` (online) · **pixi-pack/unpack** (air-gapped single-archive bundle — scanner + engines + DB) · **nebi push/pull** for nebi-adopted teams (OCI registries; alpha — a candidate, not the recommended primary path for a security gate) (added 2026-07-12).

### Story 1.5: osv-scanner as the second engine (vulnerability findings)

As a **PyPI-world developer**,
I want osv-scanner wired in so known CVEs in my locked dependencies surface alongside hygiene,
So that one gate covers both signals.

**Acceptance Criteria:**

**Given** the 1.4 fixture DB, **When** a lockfile with a known-vulnerable pin is scanned, **Then** osv runs offline through `_engine_env()`, its advisory + CVSS severity lands in the inventory (FR10), merged into the **same** `ResolvedInventory` as deptry's findings. **And** osv exit `1` (vulns-found) is read as content, `127`→engine-error, `128`→no-packages — never a silent pass.

**Given** the offline posture, **When** osv runs, **Then** the **C0c socket-deny gate holds** — osv performs **no silent DB fetch** during a scan (explicit NFR-S2 AC on the DB-access surface); the report records the DB source + timestamp (FR11).

### Story 1.6: Severity gate + verdict composition end-to-end

As a **PyPI-world developer**,
I want the gate to fail my build on real problems and pass when clean, via one composed exit code,
So that CI has one trustworthy signal.

**Acceptance Criteria:**

**Given** the `Policy` interface with a hardcoded-sane default, **When** a critical CVE is present, **Then** the vuln axis emits `policy-violation` and the verdict projects exit **1** (FR18/FR20). **And** a missing dependency (DEP001) blocks by default on a high-confidence mapping; DEP002/3/4 → `warn`. *(Confirmed by owner 2026-07-15 against the spec's transient "all hygiene warns" wording — DEP001-blocks stands as the POST-2.1 default; the spec was aligned. Shipped status, precisely: story 1.3's `DEFAULT_HYGIENE_POLICY` has DEP001–005 all `warn` — DEP001 deliberately warns until story 2.1 ships the mapping-confidence gate that activates the block.)*

**Given** a **synthetic `indeterminate` fixture component**, **When** the verdict composes, **Then** the `indeterminate` composition path (the highest-risk never-false-green path) is proven **in E1** — `indeterminate` outranks `warn`/`clean` and projects non-zero — even though the first real producer is 2.3. **And** clean hygiene + no vulns → status `clean`, exit **0**; no story outside `verdict.py` computes the projection.

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

**Given** a `pixi.lock` or `conda-lock.yml` (the **vuln hero path**), **When** extracted via `extract/lockfiles.py`, **Then** the **locked closure** lands in the inventory with exact `==` versions, manager-aware routing (conda vs pip rows → the correct ecosystem), `vuln_matchable=true` where `pypi_identity` resolves, and coverage marked `locked-closure`; fixtures include the **URL-basename pitfall** (a subdir segment must never be mis-captured as a package name — a documented shipped-parser regression). *(Ownership added 2026-07-12 per readiness Major 2 — previously unowned.)* **And** `extract/lockfiles.py` is validated against **py-rattler's `LockFile`** parse as a *test-side* oracle (never a runtime dependency — the lean-dep policy holds; added 2026-07-12).

### Story 2.2: Non-rendering extraction (common case) + differential-oracle

As a **conda/pixi maintainer**,
I want my source manifests' common-case dependency set extracted without a resolved environment, validated against a real render,
So that I can scan my source recipe pre-build with confidence it isn't silently dropping deps.

**Acceptance Criteria:**

**Given** a common-case `recipe.yaml`/`meta.yaml`/`environment.yml`/`pixi.toml`, **When** extracted, **Then** it is **parse-as-data, never rendered** — the extract module imports no execution primitive and no `jinja2` (S1 AST-denylist) — and its deps land in the inventory (**FR3** — tagged 2026-07-12). **And** pixi extraction covers the `[feature.*]` and `[target.*]` tables (provenance-tagged) beyond the base sections. **And** `run_constrained:`/`run_constraints:` entries are **constraints, not dependencies** — excluded or ingested as `provenance: constraint` (out of vuln matching + SBOM counts), matching the shipped `scan_project` semantics (added 2026-07-12). **And** the C0c socket-deny gate holds (extraction performs no egress — explicit NFR-S2 AC).

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

**Given** a manifest where some deps resolve and some don't, **When** reported, **Then** coverage is **split** into hygiene vs vulnerability dimensions (FR15) and a partial result renders a **qualified verdict** ("clean at N%"), never bare "clean" (FR16). **And** the coverage marks `direct-only` vs `locked-closure` (a loose manifest lists direct deps only; transitive vulns invisible without a lockfile).

**Given** a name-only / range / unmapped dep, **When** classified, **Then** it becomes `indeterminate` with a `WithholdReason` (`no-version`/`unmapped-ecosystem`/`native-nonpypi`/`range-only`) and is **never dropped or defaulted to clean** (C0b — FR13); the verdict exits **red-by-design** without needing E3's waivers. **And** an empty extraction is distinguished from "deps present but unresolved" (FR6).

**Given** a manifest-only repo with **no adjacent Python source** (the fleet's majority shape — feedstocks), **When** the hygiene axis runs, **Then** hygiene coverage is honestly **`not-applicable`/skipped, the reduced scope recorded — never a 100%-DEP002 noise wall** — matching Kedro FR-16's already-specced semantics for this schema's second producer. *(Added 2026-07-12 per readiness Major 3.)*

### Story 2.5: Name-level CVE tier + stale-DB + cross-ecosystem non-merge

As a **conda/pixi maintainer**,
I want a risk signal for my unpinned deps and honesty about the vuln-data freshness,
So that "vuln-coverage 12%" becomes an actionable worry-list, not a dead end.
*(Consumes the 1.4 provisioning decision for its stale-DB semantics.)*

**Acceptance Criteria:**

**Given** a mapped-but-unversioned dep, **When** the name-level tier runs, **Then** it flags whether the package carries **any known critical CVE across any version** ("pin/lock to prove immunity") — never assuming a version (FR13 guardrail).

**Given** an offline DB older than `--db-max-age` (per the 1.4 definition of "stale"), **When** scanned, **Then** the verdict is **degraded / a `vuln-data-stale` signal** emitted — never a confident clean (FR12); the report records the DB source + timestamp (FR11).

**Given** the same package name in a conda manifest AND a PyPI manifest, **When** inventoried, **Then** they stay **distinct per-ecosystem components** — no silent merge (FR7).

---

## Epic 3: Policy control + auditable waivers + warn-only

Make E1's `Policy` interface configurable + waivable, and add the adoption on-ramp.

### Story 3.1: Configurable policy (the ConfigLoader)

As a **team lead**,
I want to tune the gate per-repo without editing the tool,
So that the gate fits our risk posture.

**Acceptance Criteria:**

**Given** a `[tool.pyforge-warden]` table in `pyproject.toml` and/or `pixi.toml`, **When** loaded, **Then** config resolves with **per-key precedence** (pyproject wins; conflicts surfaced to stderr, never fail the build) and CLI flags override (FR30).

**Given** config values, **When** applied, **Then** `--fail-on`, the CVSS thresholds, the DEP001-block confidence threshold, and the coverage-floor (`--fail-under-coverage`, default off) all move the verdict (FR18/FR19); a config-key type error → typed `config-validation` error. **And** the hygiene→status + CVSS-threshold tables live in the `ConfigLoader`.

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

**Given** the frozen v1 contract (story 1.1), **When** the amendment lands, **Then** `schema_version` bumps additively (staying `1.x` — `models.py`'s `_SCHEMA_VERSION_RE` pattern is honored, not widened), adding: a per-axis `gating` bool (computed by `config.py`, the single writer); `license` + `currency` report sections each carrying per-section coverage + provenance (`{source, snapshot_at, max_age_ok}` — the bundled-data age fields, NFR-S9); **the license/currency finding-ID families + typed verdict encoding** (schema-validated fields — policy tables, waivers, and baselines key ONLY on these, never on free-text `indeterminate:` reason tokens); **the post-verdict `actuation` section** (FR40's slot); **the suppression rung-discriminator** (waiver-vs-baseline echo); `kev_date` on findings; `epss` widened to `{score, percentile}`; and per-feed KEV/EPSS provenance. **And** `report.py`'s assembly fails loud on a coverage claim for an unregistered axis (never a silent drop). **And** this story is a **HARD sprint dependency: no 6.x producer story may start before 6.1 is DONE** (mechanical gate in the sprint feed, not a recommendation). **And** the coordinated update set is exactly: `report-schema.json` · `models.py` (+ `to_json_dict` render + sort keys) · `report.py` runtime self-validation + `_REPORT_AXES` · the exact-13 `Component` test (widened deliberately, with Gap-B merge/fold semantics defined for every new `Component` field) · fixtures. **And** no other story widens the schema — the producer re-closes behind this amendment (asserted by the conformance suite).

**Given** a pre-amendment consumer reading a post-amendment report, **When** it validates, **Then** additive-only compatibility holds (the existing `test_additive_extra_fields_still_validate` property is preserved) and byte-identical determinism (`--deterministic`) still holds across the widened field set (NFR-R3b).

### Story 6.2: License axis producer + gate flags (Axis 3)

As a **compliance-conscious maintainer**,
I want every resolved component to carry an honest SPDX license verdict, gateable the moment I configure a policy,
So that license exposure is visible by default and blockable in v1 (FR32/FR33 — D12).

**Acceptance Criteria:**

**Given** a conda component with `about: license:` in its recipe, **When** the axis runs, **Then** the license normalizes to an SPDX expression via `license-expression` **pre-build** (no install), with `license_family` + `source` recorded and verdict `allowed | denied | unknown` (FR32). **And** the producer registers behind the existing `Engine` seam with `axis="license"` — no new interface.

**Given** a bare uninstalled PyPI manifest and no license policy flags, **When** the axis runs, **Then** every unresolvable component is `unknown` — surfaced per FR37 via the `warn` rung (never a silent clean, never an unconfigured red gate) — and the axis's `AxisCoverage` reports honest `deps_assessed`/`deps_total`. **And** an installed/locked env resolves PyPI licenses via `importlib.metadata` (PEP 639 `License-Expression`, legacy `License`, trove classifiers). **And** no source scanning occurs (ScanCode-class deep-scan stays deferred).

**Given** `--allow-licenses` and/or `--deny-licenses` (FR33 — v1, D12), **When** either flag is set, **Then** the flags **parse into the FR30 ConfigLoader policy tables** (CLI overrides config, per-key precedence) and `config.py` flips the license axis's `gating` bool — **this story's producer never feeds a rung above `warn`** (the no-Status-above-warn producer meta-test passes); the actual escalation (denied → `policy-violation`, unknown → `indeterminate`, never a silent clean) is **asserted end-to-end in story 6.5**, which solely owns it.

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

**Given** a provisioned KEV feed (cache layout, lifecycle, and max-age policy documented — the OSV-DB provisioning decision record `osv-db-offline-provisioning-decision.md` is the template), **When** a security finding matches a KEV-listed advisory on a pinned version, **Then** the finding carries `kev: true` (+ `kev_date` post-6.1) and the verdict blocks (`--fail-on-kev` is in the FR18 default) — exit 1. **And** this story delivers the **`feeds.py` skeleton** (ONE cache layout + ONE provenance shape + staleness/max-age defaults living in `feeds.py`, overridable only via the FR30 ConfigLoader) that 6.3 and 6.7 consume — axes never compute staleness. **And** KEV/EPSS enrichment mutates findings at exactly one pipeline position: inside the vuln producer, before policy dedup.

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

**Given** `src/shared/packages/pyforge-warden/pixi.toml` (run-deps `deptry = "*"`, `osv-scanner = "*"` today), **When** this story lands, **Then** both engines carry a **tested version range** (per NFR-C1: a range, not an exact pin — the engines come from feedstocks), the range choice is recorded with its compatibility evidence (deptry output schema; osv `--format json` shape + exit-code contract), and an out-of-range engine at runtime fails loud via FR21's typed `engine-unavailable`/incompatible error. **And** internal JFrog v1 publish and public v1.x publish are both blocked until this story is DONE (the D6 gate). **And** the story is the recorded owner of `pixi.toml:32-33` — closing the review-T-a finding that no story owned the mitigation.

### Story 6.7: EPSS feed + the `--min-epss` gate

As a **security engineer prioritizing by exploit likelihood**,
I want EPSS scores on findings and a probability-threshold gate with honest feed semantics,
So that exploit-likely vulnerabilities block and a missing feed can never fake a pass (FR36 — D12).

**Acceptance Criteria:**

**Given** a provisioned FIRST EPSS feed (cache layout, lifecycle, max-age policy — story 6.4's KEV feed work is the direct template, one shared `feeds.py` layer), **When** a security finding matches, **Then** it carries `epss {score, percentile}` (post-6.1 schema) with per-feed provenance `{source, snapshot_at, max_age_ok}`, and `--min-epss <0..1>` blocks at/above the threshold (`policy-violation`).

**Given** an absent or stale EPSS snapshot **while `--min-epss` is set**, **When** the scan runs, **Then** the verdict is **`indeterminate`** with an EPSS-provenance driver — the mirrored FR-K1 absence rule: an active policy never silently no-ops. **And** with no `--min-epss` set, null `epss` slots change nothing (CVSS/KEV gate as before). **And** feed fetch is offline-default / opt-in-online / never silent (NFR-S2).

### Story 6.8: Baseline & grandfathering (gate new findings only)

As a **maintainer adopting the gate over existing debt**,
I want to accept today's findings in a committed, expiring baseline and block only new ones,
So that day-one debt doesn't force disabling the gate — and nothing is silently suppressed (FR39 — D12).

**Acceptance Criteria:**

**Given** `--baseline .warden-baseline.yaml` (committed, schema-validated — malformed → typed `config-validation` error, never a guess), **When** the scan runs, **Then** findings whose **stable finding IDs** (the `models.py` three-family grammar — the same key waiver matching uses) appear in the baseline do not block; **NEW findings gate normally**; every applied baseline entry is **echoed in the report** (loud, `bypassed`-style — C0 holds: a baselined run can never render `clean`, and the baseline can never mask an `error`).

**Given** a baseline entry past its `expires_at` (waiver-identical semantics), **When** the scan runs, **Then** the finding **re-blocks** until fixed or re-accepted. **And** the tool only ever **reads** the baseline (NFR-R3a/S4); `--baseline-emit` prints a candidate stanza for the human to commit — the tool never writes the repo. **And** baseline + waiver interaction is deterministic and documented (waiver wins where both match — one suppression, echoed once).

### Story 6.9: Fix-PR actuator (opt-in remediation PRs)

As a **platform engineer running the gate at fleet scale**,
I want findings to open remediation PRs automatically when I opt in,
So that the gate drives fixes, not just red builds (FR40 — D12).

**Acceptance Criteria:**

**Given** `--open-fix-prs` with forge credentials provided via environment (never flags), **When** the verdict has been composed (exit code fixed), **Then** `cli.py` — the sole invoker — runs the actuator, **then** assembles + emits the final report including the `actuation` section (6.1's slot; content in the NFR-R3b volatile-field set): order = compose verdict → actuate → assemble → emit. PRs open via the forge API — security findings → upgrade-to-fixed-version PRs; hygiene unused-dependency findings → removal PRs — with the finding ID + report excerpt in the PR body. **And** the scanned working tree is **never written** (NFR-R3a asserted by the harness); the actuator is the **only** component permitted forge egress, and the C0c socket-deny carve-out applies **only to the real path under the flag** (landed in this story, never a global loosening), inert without the flag.

**Given** `--fix-prs-dry-run`, **When** the actuator runs, **Then** it shares the real code path up to the egress seam, writes its intent into the same `actuation` report section (stdout stays ONE pure document, NFR-I3), and **opens no sockets** (the carve-out does not apply to dry-run). **And** a failed PR-open **never alters the verdict or exit code** — it surfaces as a typed warning in the report. **And** duplicate protection: an existing open PR for the same finding ID is detected and skipped, never re-opened.

