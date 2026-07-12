---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
inputDocuments:
  - planning-artifacts/prd.md
  - planning-artifacts/architecture.md
  - planning-artifacts/implementation-readiness-report-2026-07-11.md
  - docs/specs/python-deptry-osv-scanner.md
---

# python-deptry-osv-scanner - Epic Breakdown

## Overview

Complete epic and story breakdown for **python-deptry-osv-scanner** — a non-interactive CI/CD security-gate CLI that unifies dependency-hygiene (deptry) + known-vulnerability scanning (osv-scanner) into one schema-validated report behind one exit code, for Python projects sourced from PyPI **or** conda-forge. Decomposed from the completed PRD (FR1–FR31 + 22 NFRs) and the completed architecture (§ Core Architectural Decisions / § Project Structure / § Implementation Patterns). **No UX** (non-interactive CLI). Epics are **vertical slices that ship end-to-end value** — the technical layers E1–E4 map *across* the slices (per the readiness report's Epic-Quality flags).

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

**B. Dependency-Hygiene** — FR8 hygiene findings (unused/missing/transitive/misplaced), PyPI+conda · FR9 honor `[tool.deptry]` ignores.

**C. Vulnerability** — FR10 vuln findings (advisory/affected-fixed/severity), actionable · FR11 offline/air-gapped DB, offline-by-default, records source+timestamp · FR12 detect **stale DB** → degrade verdict · FR13 unresolved version → **vulnerability-indeterminate** + name-level CVE tier (mapped-but-unversioned → "carries known critical CVEs"); guardrail: coverage improves only by resolving or name-level flagging, never by assuming a version.

**D. Honest Coverage & Reporting** — FR14 schema-validated report (status/severity/schema_version/coverage/error_kind) · FR15 **split hygiene vs vuln coverage** · FR16 partial coverage → qualified verdict, never bare "clean" · FR17 human + machine report, every blocking finding actionable.

**E. Policy Gate & Verdict** — FR18 gate on content+severity (vuln axis default critical; **hygiene axis separate — DEP001 blocks by default (mapping-confidence-gated), DEP002/3/4 warn**) · FR19 minimum coverage-floor gate (default OFF) · FR20 verdict-composition (lattice `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable` + separate exit; indeterminate → non-zero) · FR21 detect engine presence/version + typed error_kinds routed to owner, never silent PASS · FR22 no-meaningful-scan → non-passing, never clean · FR23 warn-only mode.

**F. Waivers & Bypass** — FR24 auditable expiring waiver (reason/authorizer/expiry), read-not-written · FR25 re-block on expiry + flag for review · FR26 validate waiver schema, reject malformed/malicious.

**G. SBOM & Machine Contract** — FR27 CycloneDX 1.6 SBOM (source-registry purls, self-declared partiality) · FR28 stable exit-code contract.

**H. CLI Operation & Configuration** — FR29 one non-interactive command → one exit code · FR30 dual `[tool.python-deptry-osv-scanner]` config (pyproject+pixi, per-key precedence, owns hygiene→status + CVSS-threshold tables) · FR31 `--version`/`--help` stable contract.

### NonFunctional Requirements

- **C0 — Gate-Integrity invariant (cross-cutting acceptance property):** never false-green; N adversarial fixtures → 0 exit-0.
- **Reliability:** NFR-R1 corpus 0 uncaught exceptions (~1,950 files) · R2 ratcheted unparseable-rate baseline · R3a no repo/host mutation · R3b two-tier determinism (decision-deterministic default; byte-identical `--deterministic`) · R5 bounded engine timeout.
- **Security:** S1 no execution of untrusted input (AST-denylist, no jinja-render, safe_load only) · S2 no silent egress (socket guard) · S3 waiver untrusted + least-privilege · S4 no repo writes + secure temp · S5 ReDoS/resource bound · S6 engine-input purity (no requirements/argv injection) · S7 output neutralization (schema-aware encoder) · S8 trusted-input integrity (fresh+authentic DB).
- **Performance:** NFR-P-warm (overhead ≤ ~2s p95, engines-stubbed) · P-cold (cacheable first-run DB) · P-concurrency (engines parallel, no shared state, O(project)).
- **Interoperability:** I1 schema conformance (report JSON schema, CycloneDX 1.6, purl) · I2 schema-version field + frozen exit enum `{0,1,2,130}` · I3 machine-output purity (stdout = one doc or empty).
- **Usability:** U1 actionable diagnostics (fail-with-a-fix) · U2 safe-by-default + warn-only on-ramp.
- **Portability:** C1 Python ≥ 3.12; engines on PATH in a tested version range; pixi ≥ 0.72.2.

### Additional Requirements

*From the architecture (§ Core Architectural Decisions / § Project Structure / § Implementation Patterns) + the readiness report — these shape the epic/story design:*

- **Greenfield scaffold EXISTS** at `src/shared/packages/python-deptry-osv-scanner/` (pixi build member, `cli.py` stub, 2 smoke tests green). Epic 1 Story 1 = **complete-the-scaffold** (wire the pipeline into the stub + add the targeted deps + stand up the test harness), **not** create-from-template.
- **Targeted runtime deps** (relax `dependencies = []`): PyYAML (`safe_load`/`safe_dump`), packaging, cyclonedx-python-lib, jsonschema; engines deptry + osv-scanner as conda run-deps.
- **The single shared spine:** ONE `ResolvedInventory` + `Component{name,version|None,ecosystem,pypi_identity|None,purl,provenance:[(manifest,section)],hygiene_covered,vuln_matchable,indeterminate_reason|None}`; canonical StrEnums (`Status`/`ErrorKind`/`WithholdReason`/`Ecosystem`); the verdict lattice + exit projection owned solely by `verdict.py`. Established in the first slice; every later slice builds on it.
- **The `_engine_env()` normalization helper + pure-JSON stdout seam** — build in the first engine-integration slice (cheap-now, ruinous-to-retrofit).
- **Bundled `data/conda_pypi_map.json` asset** — generate from the atlas `export-purls` conda↔pypi TSVs (powers the Gap-C `pypi_identity` predicate that prevents the silent `pytorch`→`torch` false-green).
- **The E1 extraction is non-rendering parse-as-data** + a **supported-construct matrix** (compiler/stdlib→build-tool-exclude, pin_subpackage→internal-exclude, selectors→union+mark, expr-logic→degrade) — an owned deliverable.
- **4 first-story open items** (readiness gap analysis): (a) generate the conda→pypi map from the atlas; (b) pick the name-mapping confidence threshold (DEP001 block vs warn); (c) pick the coverage denominator formula; (d) confirm the osv offline-DB provisioning mechanism.
- **Cross-cutting acceptance gates applied to EVERY story** (not a single "do security" story): **C0** (false-green=0 on the slice's fixtures) · **C0c — socket-deny (NFR-S2, no silent egress):** a deny-by-default socket harness landed in 1.1b — any egress during a scan is a hard test failure — self-enforcing for every future engine, plus visible ACs on 1.3b (osv/DB) + 2.2a (extraction) · **verdict.py sole-ownership guard** (a grep/static check fails CI if any module other than `verdict.py` references the exit literals `{1,2,130}` or the rung ordering — stories *feed* rungs, only verdict.py *projects*) · the **NFR-S\*** suite (AST-denylist for any new `extract/` module, output-neutralization, engine-input purity, ReDoS bound) · **NFR-R1/R2** (0 uncaught exceptions + ratcheted rate on any new corpus surface) · **NFR-R3b** (twice-run byte-identical in `--deterministic`) · **differential-oracle** (E1 dep-set ⊇ rattler-build/conda-build render; *skip-if-renderer-unavailable* at fixture scale in 2.2a, matured to corpus scale in 5.2).

### UX Design Requirements

**N/A** — non-interactive CI CLI; no human-UI surface. The human-facing affordances (actionable diagnostics, warn-only on-ramp, `--version`/`--help`) are owned as FR17/FR23/FR31 + NFR-U1/U2, not as UX artifacts.

### FR Coverage Map

`FR1,2,4,8,9,10,14,17,18,20,21,22,28,29,31` → **E1** · `FR3,5,6,7,11,12,13,15,16` → **E2** · `FR19,23,24,25,26,30` → **E3** · `FR27` → **E4** · *(NFR-driven: U1,U2,P-*,R2,C1)* → **E5**. All 31 FRs covered; dependencies strictly backward (E1 → E2 → E3/E4 → E5). *(Post-roundtable corrections: FR1 → its own Story 1.6; FR9 realized in 1.2 (E1), not E3; FR15 realized in 2.3 (E2), not E1; FR24 tagged in 3.2. Story-level FR→AC tags are authoritative over this epic-level summary.)*

**Recommended wedge-first build order** *(delivery sequence — the diamond; epics remain value-groupings, deps stay backward):* `1.1a → 1.1b → 1.2 (deptry) → 1.6 (discovery) → 2.1 (map + pypi_identity → indeterminate = the wedge demo) → 2.2a (extraction + oracle) → 1.3a (OSV spike) → 1.3b (osv) → 2.4 (name-level CVE) → 1.4 (gate) → 1.5a/1.5b (report) → 2.2b/2.3 → E3 → E4 → E5`. A conda maintainer sees differentiated value (`scan recipe.yaml → honest indeterminate-or-clean`) by ~step 5, not step 8. The two data-provisioning spikes (OSV-DB, conda→pypi map) are hit early, not stacked at the midpoint; the map generation runs as a **parallel read-only atlas data task**.

**Execution model (2026-07-12 — "Option B", `docs/specs/bmad-loop-adoption.md`):** these stories run **loop-driven** — `bmad-loop` v0.8.1 orchestrating `bmad-dev-auto` sessions. Each story is converted to a dev-auto spec whose contract is this document's **Given/When/Then ACs, preserved verbatim**; the loop's deterministic `[verify]` command is the scanner's own test suite (`pixi run -e python-deptry-osv-scanner python-deptry-osv-scanner-test` — the 1.1b harness + C0a/C0c gates thereby police every later story mechanically); gates graduate `per-story-spec-approval` (1.1a/1.1b contract freeze) → `per-epic` (Epic 2+) → revisit `none` for the tail; the sprint feed is `sprint-status.yaml` (`bmad-sprint-planning`); CRITICAL escalations pause the run for `bmad-loop-resolve`.

## Epic List

*Vertical-slice epics (architecture complete). Stress-tested via [A] dependency-mapping + a party-mode roundtable (PM/Dev/Architect), then a **full restructure** the roundtable mandated: the risky work is split into single-agent-sized stories (keystone 1.1→1.1a/1.1b; the two data-provisioning **spikes extracted** — OSV-DB as 1.3a, conda→pypi map as a parallel task; the 2.2 extractor split 2.2a/2.2b; FR1 discovery promoted to its own Story 1.6; the report split 1.5a/1.5b) while the **commodity tail shrinks** (4.2 dissolved into conformance tests; E4/E5 kept lean). **20 stories.** E1 remains a **contract-first walking skeleton, not a foundation dump** — the `Component` record + `ComplianceReport` schema + full 7-rung lattice are frozen WHOLE in 1.1a (field shape/type/optionality frozen now; two enums' variant-sets may grow **additively** in E2, safe because 1.1a's projection treats any unknown match-level → `indeterminate`, never `clean`). Cross-cutting gates (C0a/C0b/C0c, verdict.py sole-ownership guard, NFR-S\*, corpus 0-exceptions, differential-oracle) are per-story acceptance gates, not a separate epic.*

### Epic 1: Spine + PyPI engine (walking skeleton)
A maintainer gates a **PyPI project** end-to-end — unified deptry+osv verdict + one exit code — while the run establishes the shared spine as a *vertical slice* (never "build the spine" as infra). **4 E1 definition-of-done conditions (roundtable-mandated):** (1) **interface-first** — `extract`/`routing`/`engine`/`vuln-strategy`/`Policy` are plugin/strategy interfaces, PyPI is the first registered impl; (2) the **`Component` record + `ComplianceReport` JSON schema + full 7-rung verdict lattice are frozen WHOLE in 1.1a** (all fields present with honest non-degenerate PyPI values; two enums may grow additively in E2 under a conservative projection); later epics are **producers, never editors**; (3) **C0a (projection-safety)** owned + tested against the projection directly, gated on every epic; the `indeterminate` rung ships as a **proven-total socket**; (4) the **regression-harness skeleton hoisted to 1.1b** (2 PyPI fixtures + the C0c socket-deny harness). **Internally gated:** cluster-1 (1.1a model+lattice → 1.1b interfaces+null engine, green) **before** cluster-2 (1.2 deptry → 1.3a/1.3b osv).
**Stories (9):** 1.1a frozen contract + lattice + C0a · 1.1b interfaces + null engine + harness + C0c · 1.2 deptry · 1.3a OSV-DB spike · 1.3b osv · 1.4 gate + verdict · 1.5a typed errors + no-scan guard · 1.5b report renderers · 1.6 discovery (FR1).
**FRs covered:** FR1, FR2, FR4, FR8, FR9, FR10, FR14, FR17, FR18, FR20, FR21, FR22, FR28, FR29, FR31

### Epic 2: The conda/pixi source-manifest wedge
A conda-feedstock/pixi maintainer gets the gate on their **source** manifest (recipe.yaml/meta.yaml/environment.yml/pixi.toml) — the differentiated value no incumbent delivers (**beachhead value; pulled as early as possible**). Registers the conda+pixi extractors behind E1's interfaces; the **non-rendering parse-as-data + supported-construct matrix**; generates the **conda→pypi map from the atlas** *(CFE Rule 1)*; the `pypi_identity` predicate + confidence threshold; the **`indeterminate` PRODUCER + C0b (withhold-completeness)**; the name-level CVE tier; the **differential-oracle**. Ships red-by-design `indeterminate` exits without needing E3's waivers.
**Stories (5):** 2.1 conda→pypi map + pypi_identity · 2.2a non-rendering extraction + oracle · 2.2b full construct-matrix · 2.3 split coverage + indeterminate producer (C0b) · 2.4 name-level CVE tier + stale-DB + non-merge.
**FRs covered:** FR3, FR5, FR6, FR7, FR11, FR12, FR13, FR15, FR16

### Epic 3: Policy control + auditable waivers + warn-only
A team tunes the gate and files auditable, expiring, time-boxed exceptions without lying about coverage. Makes E1's `Policy` interface **configurable + waivable** — per-repo config precedence, coverage-floor gate, the DEP001-block confidence threshold; waivers-as-code (read-not-written, expiry re-block, review routing); the warn-only adoption mode.
**Stories (3):** 3.1 configurable policy · 3.2 auditable expiring waivers (FR24) · 3.3 waiver-expiry re-block + warn-only.
**FRs covered:** FR19, FR23, FR24, FR25, FR26, FR30

### Epic 4: Machine contract + CycloneDX SBOM
The CI pipeline / cf_atlas consumes a stable, versioned report **and** an honest CycloneDX 1.6 SBOM. `sbom.py` as a **separate read-only projection over the frozen inventory** (source-registry purls, self-declared partiality). *(**Dissolved 4.2** per the roundtable: schema-conformance is asserted by a test in 1.1a, not built as a story; pure-JSON hardening lives in 1.5b's renderer. E4 = the one genuinely-additive value story.)*
**Stories (1):** 4.1 CycloneDX 1.6 SBOM + S7 adversarial-encoding neutralization. *(NFR-I1/I2 → 1.1a+1.1b; NFR-I3 → 1.5b.)*
**FRs covered:** FR27

### Epic 5: Fleet-readiness & adoption on-ramp
The gate survives 20k-repo deployment and a maintainer adopts it without a day-one red storm. The **actionable-diagnostics** pass (fail-with-a-fix; a new `--explain`/remediation capability) + safe-by-default fail-closed posture; then the fleet-scale hardening gate — P-concurrency, deterministic exit matrix under load, the **corpus-ratchet + differential-oracle maturation across all formats** (corpus-provisioning is its first task). Determinism itself threads as a per-story acceptance gate everywhere, not a terminal epic. Defends the `gate-disabled = 0` anti-metric.
**Stories (2):** 5.1 actionable diagnostics + safe-by-default · 5.2 fleet determinism + corpus-ratchet + oracle maturation.
**FRs covered:** *(NFR: U1, U2, P-warm/cold/concurrency, R2, R5, C1)*

---

## Epic 1: Spine + PyPI engine (walking skeleton)

Establish the contract-first spine and gate a PyPI project end-to-end. Cluster-1 (1.1a model+lattice → 1.1b interfaces + C0a/C0c vs a null engine) must be green before cluster-2 (real engines). Every story ends in something runnable; the record + `ComplianceReport` schema + 7-rung lattice are frozen **whole** in 1.1a.

### Story 1.1a: Frozen contract, verdict lattice & projection-safety (C0a)

As a **tool maintainer**,
I want the `ResolvedInventory`/`Component` model, the `ComplianceReport` JSON schema, and the full 7-rung verdict lattice with its exit projection frozen and unit-proven — pure data + ordering, zero I/O,
So that every later engine and format is a *producer* against a stable contract that never needs a schema-breaking retrofit.

**Acceptance Criteria:**

**Given** the `Component` record, **When** it is defined, **Then** it carries the **full frozen field set** — `ecosystem` enum `{pypi,conda}` **closed** *(corrected 2026-07-12: pixi is a manifest format, not an ecosystem — the pixi fact lives in `provenance`)*, `provenance` a **list** of `(manifest,section)`, and `version|None`, `pypi_identity|None`, `identity_source`, `mapping_confidence`, `cve_match_level`, `extraction_mode`, `hygiene_covered`, `vuln_matchable`, `indeterminate_reason|None` all present with declared type + optionality. **And** every field's shape/type/optionality is frozen now; the two growable enums (`cve_match_level`, `WithholdReason`/`indeterminate_reason`) are declared with a conservative starter set (widening is additive, never a schema-break). **And** every non-clean status carries **`status.driver`** (axis + finding id) as part of the frozen report schema — an exit that can't say *why* is an incoherent contract (added 2026-07-12 per arch).

**Given** the report schema, **When** it is frozen, **Then** it is **producer-agnostic** (the Kedro FR-16/FR-18 atlas gate is this schema's second producer): vuln-data provenance is generic (`{source, snapshot_at, max_age_ok}` — never `osv_db_*`-named fields), **optional KEV/EPSS slots** exist (v1 never populates them; the atlas producer will), severity carries **both** a normalized tier and the raw evidence (CVSS vector string or database label), and findings/coverage are keyed by an **open `axis` mechanism** (`hygiene`/`vulnerability` now; a license/SAST axis lands additively, never a schema-break). *(Added 2026-07-12 per readiness Major 1.)*

**Given** the finding model, **When** it is frozen, **Then** every finding carries a **stable, deterministic finding-ID** (scheme documented in the schema: `vuln:<advisory-id>:<pkg>@<ver>` · `hygiene:<DEP-code>:<module-or-pkg>` · `indeterminate:<reason>:<pkg>`) — waiver matching across runs (E3) depends on it — **And** the waiver-scope decision is recorded: **all three finding families are waivable-with-expiry** (an auditable, time-boxed acceptance; the graduated path for unscannable deps). *(Added 2026-07-12 per readiness Major 1.)*

**Given** the committed `ComplianceReport` JSON schema, **When** a minimal report is validated, **Then** it conforms; it carries `schema_version` and the exit enum is the frozen closed set `{0,1,2,130}` (**FR28** — tagged 2026-07-12; folds NFR-I1/I2 — the dissolved 4.2 conformance assertion lives here).

**Given** `verdict.py`, **When** C0a is tested against the projection **directly**, **Then** the projection is **total** over all 7 rungs (`error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`), every non-clean rung maps to non-zero (**`indeterminate` → exit 1**, pinned 2026-07-12; `error` → 2, reserved for operational failure), and an unknown/weaker `cve_match_level` projects **toward `indeterminate`, never `clean`** (the additive-growth safety rule). **And** a guard test asserts an all-clean inventory produces zero `indeterminate` (the socket is proven-total, not dead).

**Given** the repo, **When** the **verdict.py sole-ownership guard** runs, **Then** CI fails if any module other than `verdict.py` references the exit literals `{1,2,130}` or the rung ordering (stories *feed* rungs; only `verdict.py` *projects*).

### Story 1.1b: Interfaces, null engine, regression harness & socket-deny (C0c)

As a **tool maintainer**,
I want the plugin/strategy interfaces wired to a null engine, the minimum regression harness, and a deny-by-default socket harness — proven end-to-end,
So that the skeleton runs `scan → report → deterministic exit` and every future engine inherits the security + false-green gates for free.

**Acceptance Criteria:**

**Given** the completed scaffold, **When** `scan <trivial-dir>` runs with a **null engine**, **Then** it emits a schema-valid minimal `ComplianceReport` (from 1.1a) to stdout and exits per the projection. **And** `extract`/`routing`/`engine`/`vuln-strategy`/`Policy` exist as interfaces with the null engine as the only registered impl (**interface-first**). **And** a **trivial single-manifest discovery stub** ships here (enough for `scan <dir>` to locate one manifest) — completed/replaced by Story 1.6's full FR1 discovery (stub ownership noted 2026-07-12).

**Given** `tests/conformance/`, **When** the harness runs, **Then** it has **2 PyPI fixtures** (one clean → green, one false-green sentinel → ≥1 finding) and asserts **0 uncaught exceptions + false-green=0 + exit-code-matches**. **And** the asset-loading plumbing + a stub `data/conda_pypi_map.json` exist. *(Both fixtures are PyPI — no conda fixture here, to avoid pulling 2.1's identity map into E1.)*

**Given** the **C0c socket-deny harness**, **When** any scan runs under test, **Then** any outbound socket attempt is a **hard test failure** (deny-by-default) — enforcing NFR-S2 for the null engine and every future engine without re-litigation.

### Story 1.2: deptry as the first engine (hygiene findings)

As a **PyPI-world developer**,
I want deptry wired in as the first real engine so my project's hygiene findings surface,
So that I get dependency-hygiene results from one command.
*(Off the OSV critical path — proceeds in parallel with the 1.3a spike.)*

**Acceptance Criteria:**

**Given** a PyPI project with a missing/unused dependency, **When** I run `scan .`, **Then** deptry runs via `_engine_env()` (temp-file output, `NO_COLOR=1`, `stdin=DEVNULL`, argv-only) and its DEP001–005 findings land in the `ResolvedInventory` (FR8, and FR4 native-parser delegation). **And** deptry's exit code is **never** the gate — the verdict reads report content.

**Given** deptry emits chatty/ANSI output, **When** captured, **Then** stdout stays a single valid JSON document (the pure-JSON stdout seam) and diagnostics go to stderr. **And** the ratchet mechanism (`unparseable_rate` baseline) is introduced.

**Given** a project with a `[tool.deptry]` config, **When** scanned, **Then** those ignores are honored (FR9). **And** the C0c socket-deny gate holds (deptry runs with no egress). **And** DEP005's actual semantics are **verified against the pinned deptry range** (the pinned-contract label "unused-dev" may itself be wrong) and a DEP005 → `warn` row is added to the ConfigLoader hygiene policy table (added 2026-07-12).

### Story 1.3a: OSV-DB offline provisioning spike (decision + fixture DB)

As a **tool maintainer**,
I want the osv offline-DB provisioning mechanism decided and a hermetic fixture DB produced,
So that 1.3b, 2.4, and CI have a bounded, reproducible vulnerability-data substrate instead of an open research question buried in a delivery story.

**Acceptance Criteria:**

**Given** the offline-first constraint (NFR-S2/S8), **When** the spike concludes, **Then** a **decision record** documents the chosen mechanism (bundled-conda-DB vs `--offline` + a provisioned local DB), how "stale" is defined (feeds FR12), and the trust-anchor/authenticity check (NFR-S8). **And** a **hermetic fixture DB** the conformance harness can consume offline is produced.

**Given** the decision, **When** downstream stories consume it, **Then** it explicitly gates **1.3b** (osv engine) and **2.4** (stale-DB semantics) — and **not** 1.2 (deptry has no OSV surface).

**Given** a workstation cold start (no DB provisioned — persona P8), **When** the spike decides the provisioning UX, **Then** the decision record also covers (added 2026-07-12): the fail-loud + **actionable-nudge** message (how to provision / `--db-path`); whether an explicit **online opt-in** query mode ships in v1 (the PRD's "opt-in, never silent" path — currently unowned) or v1 is offline-only-everywhere with trivial provisioning; the concrete **engine version ranges** to pin (NFR-C1) + the version-detection mechanism; reuse of the in-repo **`update-cve-db`** offline-OSV provisioning surface vs a new downloader; an env-var **mirror override** for the DB fetch (JFrog/air-gap discipline); and verification of osv's `--lockfile=<parser>:<path>` override (may remove the `requirements.txt` temp-name constraint). The decision record also names the **env distribution channels**: `pixi global install` (online) · **pixi-pack/unpack** (air-gapped single-archive bundle — scanner + engines + DB) · **nebi push/pull** for nebi-adopted teams (OCI registries; alpha — a candidate, not the recommended primary path for a security gate) (added 2026-07-12).

### Story 1.3b: osv-scanner as the second engine (vulnerability findings)

As a **PyPI-world developer**,
I want osv-scanner wired in so known CVEs in my locked dependencies surface alongside hygiene,
So that one gate covers both signals.

**Acceptance Criteria:**

**Given** the 1.3a fixture DB, **When** a lockfile with a known-vulnerable pin is scanned, **Then** osv runs offline through `_engine_env()`, its advisory + CVSS severity lands in the inventory (FR10), merged into the **same** `ResolvedInventory` as deptry's findings. **And** osv exit `1` (vulns-found) is read as content, `127`→engine-error, `128`→no-packages — never a silent pass.

**Given** the offline posture, **When** osv runs, **Then** the **C0c socket-deny gate holds** — osv performs **no silent DB fetch** during a scan (explicit NFR-S2 AC on the DB-access surface); the report records the DB source + timestamp (FR11).

### Story 1.4: Severity gate + verdict composition end-to-end

As a **PyPI-world developer**,
I want the gate to fail my build on real problems and pass when clean, via one composed exit code,
So that CI has one trustworthy signal.

**Acceptance Criteria:**

**Given** the `Policy` interface with a hardcoded-sane default, **When** a critical CVE is present, **Then** the vuln axis emits `policy-violation` and the verdict projects exit **1** (FR18/FR20). **And** a missing dependency (DEP001) blocks by default on a high-confidence mapping; DEP002/3/4 → `warn`.

**Given** a **synthetic `indeterminate` fixture component**, **When** the verdict composes, **Then** the `indeterminate` composition path (the highest-risk never-false-green path) is proven **in E1** — `indeterminate` outranks `warn`/`clean` and projects non-zero — even though the first real producer is 2.3. **And** clean hygiene + no vulns → status `clean`, exit **0**; no story outside `verdict.py` computes the projection.

### Story 1.5a: Typed errors & the no-scan guard (the fail-closed net)

As a **platform engineer**,
I want failures typed + routed and a run that scanned nothing to fail-closed,
So that a red gate is diagnosable and "found nothing" can never masquerade as "clean."

**Acceptance Criteria:**

**Given** a missing/incompatible engine, **When** scanned, **Then** a typed `error_kind` routed to its owner (engine-unavailable/crash/output-unrecognized) is emitted and exit is **2** — never a silent pass (FR21). **And** an engine that exceeds its bounded timeout yields a typed `timeout` error, not a hang (NFR-R5).

**Given** a run that scanned nothing meaningful, **When** it completes, **Then** the status is non-passing, **never `clean`** (FR22).

### Story 1.5b: Human & machine report renderers

As a **platform engineer**,
I want both a human summary and a machine report from one run,
So that a person can read the result and the pipeline gets a stable contract.

**Acceptance Criteria:**

**Given** `--format text` (default) vs `--format json`, **When** run, **Then** a human summary (findings + verdict) or a single valid JSON `ComplianceReport` is emitted respectively (FR17/FR14). **And** `--version`/`--help` are a stable contract (FR31); FR29 one-command→one-exit-code holds.

**Given** `--format json` under a chatty-engine + pseudo-TTY fixture, **When** captured, **Then** stdout is a single valid document or empty — never contaminated (NFR-I3, folded from the dissolved 4.2).

### Story 1.6: Manifest discovery, deterministic selection & the resolved scan set (FR1)

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

**Given** a **low-confidence** identity (below the chosen threshold), **When** classified, **Then** it resolves to **`indeterminate`, not a silent clean** (ties the threshold decision back to 1.1a's lattice).

**Given** a `pixi.lock` or `conda-lock.yml` (the **vuln hero path**), **When** extracted via `extract/lockfiles.py`, **Then** the **locked closure** lands in the inventory with exact `==` versions, manager-aware routing (conda vs pip rows → the correct ecosystem), `vuln_matchable=true` where `pypi_identity` resolves, and coverage marked `locked-closure`; fixtures include the **URL-basename pitfall** (a subdir segment must never be mis-captured as a package name — a documented shipped-parser regression). *(Ownership added 2026-07-12 per readiness Major 2 — previously unowned.)* **And** `extract/lockfiles.py` is validated against **py-rattler's `LockFile`** parse as a *test-side* oracle (never a runtime dependency — the lean-dep policy holds; added 2026-07-12).

### Story 2.2a: Non-rendering extraction (common case) + differential-oracle

As a **conda/pixi maintainer**,
I want my source manifests' common-case dependency set extracted without a resolved environment, validated against a real render,
So that I can scan my source recipe pre-build with confidence it isn't silently dropping deps.

**Acceptance Criteria:**

**Given** a common-case `recipe.yaml`/`meta.yaml`/`environment.yml`/`pixi.toml`, **When** extracted, **Then** it is **parse-as-data, never rendered** — the extract module imports no execution primitive and no `jinja2` (S1 AST-denylist) — and its deps land in the inventory (**FR3** — tagged 2026-07-12). **And** pixi extraction covers the `[feature.*]` and `[target.*]` tables (provenance-tagged) beyond the base sections. **And** `run_constrained:`/`run_constraints:` entries are **constraints, not dependencies** — excluded or ingested as `provenance: constraint` (out of vuln matching + SBOM counts), matching the shipped `scan_project` semantics (added 2026-07-12). **And** the C0c socket-deny gate holds (extraction performs no egress — explicit NFR-S2 AC).

**Given** the **differential-oracle**, **When** it runs on the fixture corpus, **Then** the non-rendering dep-set ⊇ the rattler-build/conda-build render (modulo name-only-marked), with 0 uncaught exceptions. **And** the oracle is **skip-if-renderer-unavailable** (fixture scale here; matured to corpus scale in 5.2) so 2.2a never hard-blocks on renderer provisioning.

### Story 2.2b: The full supported-construct matrix (ratcheted)

As a **conda/pixi maintainer with a Jinja-heavy recipe**,
I want selectors, templating, multi-output, and pin_subpackage handled by an explicit, tested matrix,
So that a complex recipe degrades honestly instead of silently mis-extracting.

**Acceptance Criteria:**

**Given** the construct matrix, **When** a recipe uses them, **Then** `compiler()`/`stdlib()` → build-tool-exclude, `pin_subpackage()` → internal-exclude, `# [sel]`/`if-then-else` → **union both branches + mark**, expression-logic → degrade to name-only+marked (FR5). **And** each rule is ratcheted against the 2.2a differential-oracle (a matrix regression fails CI).

### Story 2.3: Honest split coverage + the indeterminate producer (C0b)

As a **conda/pixi maintainer**,
I want a truthful verdict that never claims "clean" for deps it couldn't assess,
So that a green check is trustworthy.

**Acceptance Criteria:**

**Given** a manifest where some deps resolve and some don't, **When** reported, **Then** coverage is **split** into hygiene vs vulnerability dimensions (FR15) and a partial result renders a **qualified verdict** ("clean at N%"), never bare "clean" (FR16). **And** the coverage marks `direct-only` vs `locked-closure` (a loose manifest lists direct deps only; transitive vulns invisible without a lockfile).

**Given** a name-only / range / unmapped dep, **When** classified, **Then** it becomes `indeterminate` with a `WithholdReason` (`no-version`/`unmapped-ecosystem`/`native-nonpypi`/`range-only`) and is **never dropped or defaulted to clean** (C0b — FR13); the verdict exits **red-by-design** without needing E3's waivers. **And** an empty extraction is distinguished from "deps present but unresolved" (FR6).

**Given** a manifest-only repo with **no adjacent Python source** (the fleet's majority shape — feedstocks), **When** the hygiene axis runs, **Then** hygiene coverage is honestly **`not-applicable`/skipped, the reduced scope recorded — never a 100%-DEP002 noise wall** — matching Kedro FR-16's already-specced semantics for this schema's second producer. *(Added 2026-07-12 per readiness Major 3.)*

### Story 2.4: Name-level CVE tier + stale-DB + cross-ecosystem non-merge

As a **conda/pixi maintainer**,
I want a risk signal for my unpinned deps and honesty about the vuln-data freshness,
So that "vuln-coverage 12%" becomes an actionable worry-list, not a dead end.
*(Consumes the 1.3a provisioning decision for its stale-DB semantics.)*

**Acceptance Criteria:**

**Given** a mapped-but-unversioned dep, **When** the name-level tier runs, **Then** it flags whether the package carries **any known critical CVE across any version** ("pin/lock to prove immunity") — never assuming a version (FR13 guardrail).

**Given** an offline DB older than `--db-max-age` (per the 1.3a definition of "stale"), **When** scanned, **Then** the verdict is **degraded / a `vuln-data-stale` signal** emitted — never a confident clean (FR12); the report records the DB source + timestamp (FR11).

**Given** the same package name in a conda manifest AND a PyPI manifest, **When** inventoried, **Then** they stay **distinct per-ecosystem components** — no silent merge (FR7).

---

## Epic 3: Policy control + auditable waivers + warn-only

Make E1's `Policy` interface configurable + waivable, and add the adoption on-ramp.

### Story 3.1: Configurable policy (the ConfigLoader)

As a **team lead**,
I want to tune the gate per-repo without editing the tool,
So that the gate fits our risk posture.

**Acceptance Criteria:**

**Given** a `[tool.python-deptry-osv-scanner]` table in `pyproject.toml` and/or `pixi.toml`, **When** loaded, **Then** config resolves with **per-key precedence** (pyproject wins; conflicts surfaced to stderr, never fail the build) and CLI flags override (FR30).

**Given** config values, **When** applied, **Then** `--fail-on`, the CVSS thresholds, the DEP001-block confidence threshold, and the coverage-floor (`--fail-under-coverage`, default off) all move the verdict (FR18/FR19); a config-key type error → typed `config-validation` error. **And** the hygiene→status + CVSS-threshold tables live in the `ConfigLoader`.

### Story 3.2: Auditable expiring waivers

As a **developer under deadline**,
I want to file an auditable, time-boxed exception for a finding,
So that I can ship without lying about the risk.

**Acceptance Criteria:**

**Given** `--bypass --reason "<text>"`, **When** run, **Then** a `.python-deptry-osv-scanner-waivers.yaml` stanza (reason + authorizer + expiry — FR24) is emitted via `safe_dump` for the human to commit — the tool **never writes the repo** (NFR-S4); the reason round-trips safely (no YAML injection). **And** a valid waiver → status `bypassed`, exit 0, `review_required: true`.

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

The CI pipeline / cf_atlas consumes an honest SBOM. *(Schema-stability + pure-JSON hardening were dissolved into 1.1a's conformance test + 1.5b's renderer.)*

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

**Given** any non-zero exit, **When** the human report is emitted, **Then** it names the offending package(s), the finding (advisory id + severity + fixed-version, or the hygiene rule), the source manifest + location, and a remediation path — surfaced as **concrete remediation content in the report/diagnostics**, not a re-wrap of 1.5a's typed errors and **not a new subcommand** (an `explain` verb stays post-v1 per the PRD; reworded 2026-07-12) (NFR-U1 — "fail with a fix").

**Given** zero configuration, **When** the tool runs, **Then** the default posture is secure (block critical, expiring waivers, unknown-engine → fail-loud, air-gap explicit) paired with the warn-only on-ramp so day-one debt doesn't trigger a mass-disable (NFR-U2).

**Given** a developer workstation (P8 — added 2026-07-12), **When** the adoption docs land, **Then** they cover the local install story (`pixi global install` / the local channel now; **pixi-pack** bundles for air-gap; **nebi** for nebi-adopted teams — incl. the `nebi pull` → `scan .` pattern and versioned-env report diffing; conda-forge per OD5), the recommended first contact (`scan . --warn-only` at a terminal — per the spec's honest-adoption statement), and the `doctor`-style self-check disposition (v1-if-cheap, reusing FR21's detection logic; else explicitly named post-v1).

### Story 5.2: Fleet-scale validation + corpus/oracle maturation

As a **platform engineer deploying across 20k repos**,
I want the gate deterministic, parallel, and provably robust at scale,
So that it never flaps and I never have to disable it.

**Acceptance Criteria:**

**Given** the corpus-provisioning task (its **first** step — harvest + pin the ~1,950-file corpus so 5.2's gates aren't silently absorbing a fixture-harvesting spike), **When** it completes, **Then** the corpus is a committed, versioned fixture set **augmented with a small adversarial out-of-repo recipe set** (exotic selectors, `{% for %}`, unicode, oversized files — sourced in part from **`prefix-dev/rattler-build-parser-tests`**, the renderer's own parser-stress corpus; the in-repo corpus is a friendly, CFE-curated distribution; added 2026-07-12).

**Given** the two engines, **When** a scan runs, **Then** deptry + osv run **in parallel** with no shared mutable state, per-invocation cost O(project) not O(fleet), and our overhead ≤ ~2s p95 on the reference corpus (engines-stubbed), **measured on a named reference machine recorded with the result** (NFR-P-warm/concurrency).

**Given** the full corpus, **When** the regression gate runs, **Then** **0 uncaught exceptions**, a **committed ratcheted `unparseable_rate` baseline** (CI fails on regression), the **differential-oracle passes across all formats** at corpus scale, and twice-run is byte-identical in `--deterministic` (NFR-R1/R2/R3b). **And** an out-of-range engine version fails loud (NFR-C1). **And** the **dogfood gate** holds (spec DoD): the tool runs clean on this repo's own `pixi.toml`/`pyproject.toml` via a committed `pixi run` task — exit 0 on the known-clean state, non-zero on a seeded-violation fixture (added 2026-07-12).
