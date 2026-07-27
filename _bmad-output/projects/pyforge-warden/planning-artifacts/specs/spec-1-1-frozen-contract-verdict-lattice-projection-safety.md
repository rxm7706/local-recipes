<!-- RECOVERED 2026-07-25 from a surviving bmad-loop run worktree (.bmad-loop/runs/20260718-101504-2c07/worktrees/6-2-license-axis-producer-gate-flags/_bmad-output/implementation-artifacts/spec-1-1-frozen-contract-verdict-lattice-projection-safety.md); this is the ORIGINAL spec, not an epics.md regeneration. Promoted to tracked planning-artifacts/specs/ for durability. -->
---
title: 'Story 1.1: Frozen contract, verdict lattice & projection-safety (C0a)'
type: 'feature'
created: '2026-07-12'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
baseline_revision: 'c2605ff18723c3b6df64fbc55d615301fa62dcc2'
final_revision: 'afde40c0adef6a4bea716ee9dbd15c30ce905778'  # cherry-pick of 0a154c7a0e (original attempt commit, preserved on the bmad-loop run branch) onto the rebased mainline
review_loop_iteration: 1
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/python-deptry-osv-scanner/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/python-deptry-osv-scanner/implementation-artifacts/epic-1-context.md'
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** Every later engine, extractor, and report renderer of python-deptry-osv-scanner must build against one stable contract; if the `Component`/`ResolvedInventory` model, the `ComplianceReport` JSON schema, and the 7-rung verdict lattice are not frozen whole and unit-proven first, later epics become schema editors and the never-false-green (C0) guarantee reopens.

**Approach:** Deliver the pure-data contract layer into the existing scaffold at `src/shared/packages/python-deptry-osv-scanner/` — `models.py` (canonical StrEnums + report/finding types), `inventory.py` (the spine: `Component` + `ResolvedInventory` + identity/merge), `verdict.py` (sole owner of lattice + exit projection + `status.driver`), and `data/report-schema.json` — plus the unit/meta/conformance tests that prove projection totality (C0a) and the verdict.py sole-ownership guard. Zero I/O, no CLI wiring (that is Story 1.2).

## Boundaries & Constraints

**Always:**
- Pure data + ordering only: no network, no subprocess, no filesystem writes, no manifest reading in delivered modules. Tests may read the packaged schema via `importlib.resources`.
- All frozen dataclasses (`frozen=True`); all category values are `StrEnum` members defined once in `models.py` — never bare string literals.
- Only `verdict.py` defines the rung ordering and maps statuses/signals to exit codes. Everything else feeds rungs.
- Lattice order (fixed): `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`. Exit projection (locked): `{clean, not-applicable, bypassed} → 0`; `warn → 0` (configurable knob to make it non-zero); `policy-violation → 1`; `indeterminate → 1`; `error → 2`; SIGINT constant `130`. Canonical token is `warn` (not `warnings`).
- Growable-enum policy: ONLY `CveMatchLevel` and `WithholdReason` may widen (additively) later; the projection treats any unknown/weaker `cve_match_level` as `indeterminate`, never `clean`.
- Deterministic serialization: `to_json_dict()` sorts every list; JSON dumps with `sort_keys=True`; no `datetime.now()` anywhere in this story.
- Match existing scaffold style: `from __future__ import annotations`, full py3.12 type hints, snake_case/PascalCase.

**Block If:**
- A frozen-contract decision cannot be grounded in the architecture/epics/intake spec AND is not resolvable by the documented interpretations in Design Notes (e.g. planning docs are discovered to disagree on the lattice order or the exit enum itself).
- Freezing a field would require inventing semantics the planning docs never mention.

**Never:**
- Do not create `cli.py` wiring, `discovery.py`, `routing.py`, `extract/`, `engines.py`, `hygiene.py`, `vuln.py`, `report.py` (assembly), `sbom.py`, `waiver.py`, `config.py`, or `determinism.py` — those belong to Stories 1.2+.
- Do not modify the existing `cli.py` stub, `__init__.py` version, `tests/test_smoke.py`, `pyproject.toml`, or `pixi.toml` (deps are already declared).
- No new third-party dependencies beyond the declared four (PyYAML, packaging, cyclonedx-python-lib, jsonschema); none of them are needed at runtime in this story — `jsonschema` is used in tests only.
- No `jinja2` import anywhere; no editing of planning artifacts.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Projection totality (C0a) | every `Status` member | a defined exit code from `{0,1,2,130}`, per the locked table | unmapped member = test failure |
| Unknown match level | `cve_match_level` = an unrecognized future string | projects to `indeterminate`, never `clean` | never raises |
| Weaker match levels | `name-only`, `none` | `indeterminate` | — |
| Exact match level | `exact` | eligible for `clean` | — |
| All-clean guard | inventory of fully-resolved `exact` components | composed status `clean`, zero `indeterminate` (socket proven-total, not dead) | — |
| Compose ordering | rungs {`warn`, `indeterminate`} | `indeterminate` wins, its driver propagates | — |
| Compose empty | no rungs fed | `not-applicable` (nothing existed to scan), driver `None` | — |
| Merge: same identity | same `(eco,name,ver)` from `host:` and `run:` | ONE component, provenance list of 2 | — |
| Merge: bare + one concrete | `(name,None)` + exactly one `(name,ver)` | merged into the versioned component | — |
| Merge: bare + zero/≥2 concrete | `(name,None)` alone, or with 2 versions | bare stays a distinct `indeterminate` component — never guess-attribute | — |
| Merge: two versions | `(eco,name,1.0)` + `(eco,name,2.0)` | two distinct components, both kept | — |
| Schema: closed exit enum | report with `exit_code: 3` | schema validation FAILS | jsonschema error expected |
| Schema: driver required | non-clean status with `driver: null` | validation FAILS for `warn/bypassed/policy-violation/indeterminate/error`; null OK for `clean`/`not-applicable` | jsonschema error expected |
| Schema: additive growth | report with an extra unknown field | still validates (additive, never a break) | — |
| Determinism | `to_json_dict()` + `json.dumps(sort_keys=True)` twice | byte-identical | — |

</intent-contract>

## Code Map

- `src/shared/packages/python-deptry-osv-scanner/src/python_deptry_osv_scanner/__init__.py` -- exists; `__version__ = "0.1.0"`; do not touch
- `src/shared/packages/python-deptry-osv-scanner/src/python_deptry_osv_scanner/cli.py` -- existing stub returning 0; do not touch (1.2 wires it)
- `src/shared/packages/python-deptry-osv-scanner/src/python_deptry_osv_scanner/models.py` -- NEW: canonical enums + report/finding types
- `src/shared/packages/python-deptry-osv-scanner/src/python_deptry_osv_scanner/inventory.py` -- NEW: the spine (Component, ResolvedInventory, identity+merge, purl derivation)
- `src/shared/packages/python-deptry-osv-scanner/src/python_deptry_osv_scanner/verdict.py` -- NEW: sole owner of lattice + projection + driver
- `src/shared/packages/python-deptry-osv-scanner/src/python_deptry_osv_scanner/data/report-schema.json` -- NEW: the frozen ComplianceReport contract
- `src/shared/packages/python-deptry-osv-scanner/tests/` -- existing `test_smoke.py` (keep); add `unit/`, `meta/`, `conformance/`
- `pixi.toml` (repo root, lines 937–971) -- env + `python-deptry-osv-scanner-test` task (the verify gate); do not modify

## Tasks & Acceptance

**Execution:**
- [x] `…/python_deptry_osv_scanner/models.py` -- create canonical StrEnums: `Status` (7 rungs), `ErrorKind` {unparsable-manifest, engine-unavailable, engine-output-unrecognized, engine-output-unparseable, engine-execution-failed, engine-timeout, config-parse, config-validation, internal-error}, `WithholdReason` {no-version, unmapped-ecosystem, native-nonpypi, range-only} (growable), `Ecosystem` {pypi, conda} (closed), `CveMatchLevel` {exact, name-only, none} (growable), `IdentitySource` {native, lock, pypi-section, map, none}, `ExtractionMode` {parsed, name-only, union-marked, raw-malformed}, `SeverityTier` {critical, high, medium, low, none, unknown}; axis is an OPEN `str` with module constants `AXIS_HYGIENE = "hygiene"`, `AXIS_VULNERABILITY = "vulnerability"`. Frozen report types: `Severity(tier: SeverityTier, raw: str | None)`, `VulnData(source: str | None, snapshot_at: str | None, max_age_ok: bool | None)` (generic names ONLY — never engine-named), `StatusDriver(axis: str, finding_id: str)`, `Finding(id, axis, message, subject: str | None, severity: Severity | None, kev: bool | None = None, epss: float | None = None)` (KEV/EPSS declared, v1 never populates), `AxisCoverage(axis, manifests_found, manifests_parsed, deps_total, deps_assessed, resolution_depth: str | None)` (both denominator families as fields), `ErrorRecord(kind: ErrorKind, owner: str, message: str)`, `ScannedManifest(path: str, kind: str)`, `ComplianceReport(schema_version: str, tool_name, tool_version, status: Status, status_driver: StatusDriver | None, exit_code: int, findings, coverage, vuln_data, inventory_count: int, resolved_scan_set, errors)` with `to_json_dict()` (sorted lists, JSON-primitive values, status rendered as `{"value": …, "driver": …|null}`). Docstrings record: the finding-ID scheme (`vuln:<advisory-id>:<pkg>@<ver>` · `hygiene:<DEP-code>:<module-or-pkg>` · `indeterminate:<reason>:<pkg>`) and the waiver-scope decision (all three finding families are waivable-with-expiry) -- rationale: one canonical definition site, frozen whole.
- [x] `…/python_deptry_osv_scanner/inventory.py` -- create `PypiIdentity(name: str, version: str | None)`, `Provenance(manifest: str, section: str)`, and `Component` (frozen) with the FULL field set: `name: str`, `version: str | None`, `ecosystem: Ecosystem`, `pypi_identity: PypiIdentity | None`, `identity_source: IdentitySource`, `mapping_confidence: str | None` (carries the map's per-pair tier verbatim; vocabulary owned by Story 2.1), `cve_match_level: CveMatchLevel`, `extraction_mode: ExtractionMode`, `purl: str`, `provenance: tuple[Provenance, ...]`, `hygiene_covered: bool`, `vuln_matchable: bool`, `indeterminate_reason: WithholdReason | None`. Provide `identity(c) -> (Ecosystem, str, str | None)`; `derive_purl(ecosystem, name, version) -> str` (`pkg:pypi/<n>@<v>` / `pkg:conda/<n>@<v>`; version omitted when None; non-identity qualifiers are stripped before any comparison); `merge_components(components) -> tuple[Component, ...]` implementing the Gap-B rules (provenance-list union for same identity; `(name,None)` folds in ONLY when exactly one concrete version exists, else stays a distinct indeterminate; distinct versions stay distinct); `ResolvedInventory(components: tuple[Component, ...], resolved_scan_set: tuple[ScannedManifest, ...])` with post-merge `count` (root project never enters the inventory) -- rationale: identity + merge live ONLY here.
- [x] `…/python_deptry_osv_scanner/verdict.py` -- create the sole projection owner: private `_RUNG_ORDER` (the 7-rung lattice, strongest first); `compose(rungs: Iterable[tuple[Status, StatusDriver | None]]) -> tuple[Status, StatusDriver | None]` (highest rung wins; winner's driver propagates; empty input → `(not-applicable, None)`); `exit_code_for(status: Status, *, warn_is_error: bool = False) -> int` — TOTAL over all 7 rungs per the locked table; `EXIT_SIGINT = 130`; `match_level_rung(level: CveMatchLevel | str) -> Status` (`exact` → `clean`; `name-only`, `none`, and ANY unrecognized value → `indeterminate`) -- rationale: C0a lives here; every non-clean status carries `status.driver`.
- [x] `…/python_deptry_osv_scanner/data/report-schema.json` -- create JSON Schema (draft 2020-12) for `ComplianceReport`: required core {schema_version (semver string), tool {name, version}, status {value: 7-enum, driver: {axis, finding_id} | null}, exit_code: enum [0,1,2,130] (closed), findings[], coverage[] (keyed by open `axis` string), vuln_data {source, snapshot_at, max_age_ok — generic, nullable}, inventory_count: int ≥ 0, resolved_scan_set[] {path, kind}, errors[] {kind: ErrorKind enum, owner, message}}; conditional rule: `status.driver` must be non-null unless `status.value` ∈ {clean, not-applicable}; findings carry id (patterns per the three families), axis, message, optional severity {tier, raw}, optional kev/epss slots; `additionalProperties` left open (additive growth is never a schema break); descriptions record the finding-ID scheme + the waivable-with-expiry decision -- rationale: the producer-agnostic external contract, second producer = the atlas gate.
- [x] `…/tests/unit/test_models.py` -- enum canonical string values (all 7 `Status` tokens exact, `warn` not `warnings`; `Ecosystem` exactly {pypi, conda}), frozen-dataclass immutability, `Component` field-set introspection via `dataclasses.fields` (name + declared type/optionality for ALL 13 fields), KEV/EPSS present-but-None defaults -- rationale: the freeze is testable, not aspirational.
- [x] `…/tests/unit/test_inventory.py` -- unit-test every merge rule in the I/O matrix, provenance-list union, `derive_purl` forms, identity comparison ignoring purl qualifiers -- rationale: Gap-B rules are load-bearing for SBOM/report counts.
- [x] `…/tests/unit/test_verdict.py` -- C0a directly against the projection: parametrized totality over ALL `Status` members (no member unmapped); locked exit values incl. `indeterminate → 1`, `error → 2`; `warn_is_error` knob; compose ordering (indeterminate outranks warn; error outranks policy-violation); driver propagation (axis + finding id); empty compose → not-applicable; `match_level_rung` unknown/weaker → `indeterminate` never `clean`; the all-clean guard (all-`exact` inventory composes to `clean`, zero indeterminate) -- rationale: the story's core acceptance.
- [x] `…/tests/meta/test_verdict_sole_ownership.py` -- AST-scan every module in the package EXCEPT `verdict.py`: fail if (a) `sys.exit`/`os._exit`/`SystemExit` is called with an int literal in {1, 2, 130}, (b) any module imports a `_`-private name from `verdict`, or (c) any module contains an ordered sequence literal of all 7 `Status` tokens (the rung ordering); positively assert `verdict.py` itself defines `_RUNG_ORDER` + `exit_code_for` (guard is alive, not vacuous) -- rationale: stories feed rungs; only verdict.py projects.
- [x] `…/tests/conformance/test_report_schema.py` -- build a minimal `ComplianceReport` via `models.py`, validate `to_json_dict()` output against the packaged schema (`importlib.resources`, `jsonschema.validate`); negative cases: `exit_code: 3` rejected, non-clean status with null driver rejected; additive extra field accepted; `schema_version` present; twice-run `json.dumps(..., sort_keys=True)` byte-identical -- rationale: the dissolved Story 4.2 conformance assertion lives here (NFR-I1/I2, FR28).

**Acceptance Criteria:**

*(Story 1.1 ACs from epics.md, preserved verbatim — the contract of record.)*

**Given** the `Component` record, **When** it is defined, **Then** it carries the **full frozen field set** — `ecosystem` enum `{pypi,conda}` **closed** *(corrected 2026-07-12: pixi is a manifest format, not an ecosystem — the pixi fact lives in `provenance`)*, `provenance` a **list** of `(manifest,section)`, and `version|None`, `pypi_identity|None`, `identity_source`, `mapping_confidence`, `cve_match_level`, `extraction_mode`, `hygiene_covered`, `vuln_matchable`, `indeterminate_reason|None` all present with declared type + optionality. **And** every field's shape/type/optionality is frozen now; the two growable enums (`cve_match_level`, `WithholdReason`/`indeterminate_reason`) are declared with a conservative starter set (widening is additive, never a schema-break). **And** every non-clean status carries **`status.driver`** (axis + finding id) as part of the frozen report schema — an exit that can't say *why* is an incoherent contract (added 2026-07-12 per arch).

**Given** the report schema, **When** it is frozen, **Then** it is **producer-agnostic** (the Kedro FR-16/FR-18 atlas gate is this schema's second producer): vuln-data provenance is generic (`{source, snapshot_at, max_age_ok}` — never `osv_db_*`-named fields), **optional KEV/EPSS slots** exist (v1 never populates them; the atlas producer will), severity carries **both** a normalized tier and the raw evidence (CVSS vector string or database label), and findings/coverage are keyed by an **open `axis` mechanism** (`hygiene`/`vulnerability` now; a license/SAST axis lands additively, never a schema-break). *(Added 2026-07-12 per readiness Major 1.)*

**Given** the finding model, **When** it is frozen, **Then** every finding carries a **stable, deterministic finding-ID** (scheme documented in the schema: `vuln:<advisory-id>:<pkg>@<ver>` · `hygiene:<DEP-code>:<module-or-pkg>` · `indeterminate:<reason>:<pkg>`) — waiver matching across runs (E3) depends on it — **And** the waiver-scope decision is recorded: **all three finding families are waivable-with-expiry** (an auditable, time-boxed acceptance; the graduated path for unscannable deps). *(Added 2026-07-12 per readiness Major 1.)*

**Given** the committed `ComplianceReport` JSON schema, **When** a minimal report is validated, **Then** it conforms; it carries `schema_version` and the exit enum is the frozen closed set `{0,1,2,130}` (**FR28** — tagged 2026-07-12; folds NFR-I1/I2 — the dissolved 4.2 conformance assertion lives here).

**Given** `verdict.py`, **When** C0a is tested against the projection **directly**, **Then** the projection is **total** over all 7 rungs (`error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`), every non-clean rung maps to non-zero (**`indeterminate` → exit 1**, pinned 2026-07-12; `error` → 2, reserved for operational failure), and an unknown/weaker `cve_match_level` projects **toward `indeterminate`, never `clean`** (the additive-growth safety rule). **And** a guard test asserts an all-clean inventory produces zero `indeterminate` (the socket is proven-total, not dead).

**Given** the repo, **When** the **verdict.py sole-ownership guard** runs, **Then** CI fails if any module other than `verdict.py` invokes an exit primitive with a guarded exit value (the literals `{1,2,130}`, a module-level constant bound to one, or a string argument — `sys.exit("msg")` exits 1) or materializes the rung ORDERING as an ordered sequence literal (the lattice order or its exact reverse) (stories *feed* rungs; only `verdict.py` *projects*). *(Amended 2026-07-13, follow-up review D1: `models.py` legitimately declares the closed exit-code SET and the `Status` members for report validation — the guard targets projection behavior, not declaration; the original "references the exit literals" letter was unimplementable.)*

### Review Findings

*(Follow-up review 2026-07-13 — Blind Hunter + Edge Case Hunter + Acceptance Auditor over commit `afde40c0ad`; 31 raw findings, 22 unique after dedup: 1 decision-needed, 17 patch, 2 defer, 2 dismissed. Auditor AC verdict: 5 of 6.)*

- [x] [Review][Decision] AC 6 is unmeetable as verbatim-worded — `models.py` must reference the exit literals `{0,1,2,130}` for its own (prior-triage-endorsed) `__post_init__` exit-set validation, and `Status` necessarily declares its members in the lattice order; the delivered guard enforces task 8's narrower operationalization (exit-primitive calls + ordered sequence literals), so CI passes while the AC's letter ("references the exit literals or the rung ordering") is violated by `models.py:47,53-66`. Resolve by (a) amending the AC wording to task 8's operationalization, (b) restructuring so the literal set lives only in verdict.py (circular-import cost), or (c) recording it as a documented guard bound. — RESOLVED 2026-07-13: user chose (a); AC 6 amended here and in epics.md (AC + cross-cutting-gate blurb).
- [x] [Review][Patch] (high) Bare→concrete fold silently upgrades non-version-driven confidence — provenance-only fold keeps the concrete side's `hygiene_covered`/`extraction_mode`/`pypi_identity` even when the bare record was worse (raw-malformed, uncovered, conflicting identity); contradicts the C0 "merge never upgrades confidence" rule the same-identity path enforces [src/shared/packages/python-deptry-osv-scanner/src/python_deptry_osv_scanner/inventory.py:200]
- [x] [Review][Patch] (high) Ambiguity withhold leaves `vuln_matchable=True` with `pypi_identity=None` and no `WithholdReason` — violates the locked Gap-C predicate (`vuln_matchable = pypi_identity≠None AND version exact`); needs conservative recompute + an additive `WithholdReason` member for ambiguous identity [inventory.py:301 vs inventory.py:315]
- [x] [Review][Patch] (high) `derive_purl` mutates conda names (lowercase + `_`→`-`) — contradicts `canonical_name`'s conda no-op, collides genuinely distinct conda-forge packages (`typing_extensions` vs `typing-extensions`), and diverges from external conda purl practice incl. this repo's cfe-purls; wrong behavior is pinned by tests/unit/test_inventory.py:156 [inventory.py:122]
- [x] [Review][Patch] (medium) Raw-string `status`/`kind`/`tier` bypass the closed-set checks and crash later at `to_json_dict` (`AttributeError`) instead of a construction-time `ValueError` — StrEnum `==` lets plain strings through `__post_init__` [models.py:275, models.py:326, models.py:347, models.py:364]
- [x] [Review][Patch] (medium) status↔exit coherence enforced only in the schema, not in `ComplianceReport.__post_init__` — `status=error, exit_code=0` constructs cleanly [models.py:275]
- [x] [Review][Patch] (medium) `findings[].id` uniqueness unenforced (model + schema) — duplicate IDs break waiver matching and by-ID consumers [models.py:298]
- [x] [Review][Patch] (medium) Singleton merge group early-returns and bypasses the documented `""`→`None` version normalization + purl re-derivation — output shape depends on whether a duplicate existed in the feed [inventory.py:259]
- [x] [Review][Patch] (medium) `Component` has zero `__post_init__` invariants — `vuln_matchable=True` with `version=None`, `version=""`, and `name=""` all constructible, injecting every incoherence the merge layer avoids [inventory.py:56]
- [x] [Review][Patch] (low) `$`-anchored ID/semver regexes accept a trailing newline and `[^:]+` accepts embedded newlines — `\Z` + newline-excluding classes needed (model + mirrored schema patterns) [models.py:37]
- [x] [Review][Patch] (low) `bool` passes every numeric guard (`exit_code=True`, `epss=True`, count fields) then fails the schema as the wrong JSON type [models.py:276]
- [x] [Review][Patch] (low) `VulnData` lacks the `max_age_ok`⇒provenance implication the schema enforces [models.py:150]
- [x] [Review][Patch] (low) `PypiIdentity` conflict detection compares raw spellings, not PEP-503-canonical ones — `PyYAML` vs `pyyaml` triggers false ambiguity and drops resolved identity [inventory.py:310]
- [x] [Review][Patch] (low) `-0.0` vs `0.0` epss defeats the byte-identical serialization guarantee (sort keys compare equal, JSON renders differ) [models.py:406]
- [x] [Review][Patch] (low) `resolution_depth` became a closed vocabulary enforced with bare string literals instead of a StrEnum, in tension with the Always constraint [models.py:50]
- [x] [Review][Patch] (low) Sole-ownership guard misses `import sys as s; s.exit(2)` (Import aliases untracked) and `sys.exit("fatal")` (string arg exits 1) [tests/meta/test_verdict_sole_ownership.py:74]
- [x] [Review][Patch] (low) Rung-ordering detector drops non-Status elements before run-matching — interleaved token/description literals false-positive the guard [tests/meta/test_verdict_sole_ownership.py:203]
- [x] [Review][Patch] (low) `derive_purl` performs no percent-encoding of purl-reserved characters — RAW_MALFORMED names yield invalid/ambiguous purls that `strip_purl_qualifiers` then corrupts [inventory.py:119]
- [x] [Review][Defer] (medium) `status_driver.finding_id` has no referential integrity against `findings[]` — a driver may dangle [models.py:281] — deferred: error-driver grammar is owned by Story 1.7 and waiver-suppression semantics by Epic 3; blanket enforcement is not safely expressible in 1.1
- [x] [Review][Defer] (low) PEP-440-equal version spellings (`2.31` vs `2.31.0`) split identity, double-count, and fork finding IDs [inventory.py:94] — deferred: version canonicalization belongs to the extractor/producer stories (1.3+/2.x); changing frozen identity semantics needs spec grounding first

## Spec Change Log

## Review Triage Log

### 2026-07-13 — Follow-up review pass (Blind Hunter + Edge Case Hunter + Acceptance Auditor, deduplicated)
- raw findings: 31 (blind 13, edge 14, auditor 4) → 22 unique after 8 cross-layer merges
- decision_needed: 1 (AC 6 letter unimplementable → user chose: amend the AC wording; landed in spec + epics.md)
- patch: 17 (high 3, medium 5, low 9) — ALL applied + regression-tested; verify suite 156 → 180 tests, all green
- defer: 2 (driver referential integrity → Story 1.7/E3; PEP-440 version canonicalization → extractor stories) — in deferred-work.md
- dismiss: 2 (unicode casefold in canonical_name — name grammars are ASCII, distinct-stays-distinct is conservative; guard scanning the installed package — spec-mandated, verify gate rebuilds first)
- headline fixes: fold no longer upgrades non-version-driven confidence (C0); withheld identity now forces vuln_matchable=False + WithholdReason.AMBIGUOUS_IDENTITY (new additive member); conda purls verbatim (typing_extensions ≠ typing-extensions); Component/__post_init__ invariant suite (Gap-C predicate at construction); status↔exit coherence + raw-string enum coercion + finding-id uniqueness in ComplianceReport; \Z + no-newline regexes; bool rejection; VulnData provenance implication; -0.0 canonicalization; ResolutionDepth StrEnum; guard hardened (module aliases, string-arg exits, interleaved-literal false positive)

### 2026-07-12 — Review pass (Blind Hunter + Edge Case Hunter, deduplicated)
- intent_gap: 0
- bad_spec: 0
- patch: 19: (high 1, medium 7, low 11)
- defer: 1: (high 1)
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[high]` `[patch]` merge_components let the first-fed record win non-provenance field conflicts (feed-order-dependent, could silently upgrade cve_match_level → false-green) — replaced with group-wise, order-independent conservative reducers (least-confident match level, AND-ed coverage booleans, ambiguous pypi_identity withheld to None, most-degraded extraction_mode; fold keeps the concrete side); verified over all 5,040 permutations of a 7-record conflict set
  - `[medium]` `[patch]` PyPI identity ignored PEP 503 equivalence (Django/django never merged, inflating inventory_count) — identity key + derive_purl now canonicalize pypi names
  - `[medium]` `[patch]` to_json_dict sort keys omitted subject/severity/kev/epss (byte-identical claim broke for key-equal entries) — full rendered-tuple sort keys
  - `[medium]` `[patch]` model layer enforced none of its declared invariants — __post_init__ ValueError suite on ComplianceReport (exit set, non-clean-requires-driver, count ≥ 0, schema_version 1.x, unique coverage axes, finding-family↔axis), Finding (ID grammar, epss finite ∈ [0,1]), AxisCoverage (arithmetic coherence, depth vocabulary)
  - `[medium]` `[patch]` schema permitted incoherent status/exit pairs, unbounded epss, partial vuln_data provenance, free-text resolution_depth, family/axis mismatch — allOf status↔exit clauses, epss bounds, max_age_ok→source/snapshot_at if/then, resolution_depth enum, per-finding family→axis if/then; $id → urn; schema_version pinned to the 1.x major
  - `[medium]` `[patch]` error-driven verdicts had no legal driver ID and the conformance test abused the indeterminate family grammar — test uses an `error:`-style driver string; schema documents that the error-driver grammar is owned by Story 1.7
  - `[medium]` `[patch]` sole-ownership guard: five evasion vectors (import aliases, verdict-module aliases, dict-literal orderings, named-constant exits, keyword args) plus a false positive on any unordered full-status enumeration — detectors hardened; ordering now fires only on the exact lattice order or its reverse; bounds documented
  - `[medium]` `[patch]` compose raised bare KeyError on unknown status, tie-breaks leaked feed order — Status() coercion (fail-loud ValueError) + deterministic driver-first tie-break; exit_code_for coerces so raw "warn" respects warn_is_error
  - `[low]` `[patch]` derive_purl emitted non-canonical purls; "qualifiers stripped before comparison" was aspirational — canonical purl names per ecosystem; docstrings state the strip_purl_qualifiers rule
  - `[low]` `[patch]` empty-string version treated as concrete (phantom folds, `pkg:…@` purls) — normalized to None in identity/purl paths
  - `[low]` `[patch]` ResolvedInventory accepted pre-merge duplicates (inventory_count overstated) — __post_init__ duplicate-identity ValueError
  - `[low]` `[patch]` NaN/Infinity epss serialized as non-RFC-8259 JSON — finiteness + [0,1] validation
  - `[low]` `[patch]` schema_version pattern was major-version-blind and $id was a fake URL — 1.x pattern + urn $id
  - `[low]` `[patch]` cross-test `from test_inventory import make_component` sys.path coupling — factory moved to tests/conftest.py fixture
  - `[low]` `[patch]` conformance suite lacked rejection tests (unknown status token, unknown error kind, unknown severity tier, incoherent status/exit, out-of-range epss, partial vuln_data, depth typo, wrong-axis family) — all added
  - `[low]` `[patch]` no py.typed marker (typed contract invisible to downstream checkers) — added
  - (defer, high) the loop's unfrozen `[verify]` command fails environmentally in bmad-loop worktrees (pixi-build-python path-length panic; unfrozen re-solve rewrites pixi.lock with worktree paths) — recorded in deferred-work.md with the `--frozen` recommendation
  - (reject ×4) match_level_rung accepting the canonical raw token "exact" (by design; unknown-safe rule holds) · root-exclusion/EXIT_SIGINT enforcement (owned by Stories 4.1/1.7–1.8 by plan) · vuln_data "generic names" unenforceable in an open schema (design rule, not a validator) · Finding dataclass requiring subject/severity explicitly while the schema floors them optional (internal explicitness, not a defect)

## Design Notes

- **"Every non-clean rung maps to non-zero" (AC 5) is read as the blocking family** (`error`, `policy-violation`, `indeterminate`): the architecture's LOCKED projection table, the intake spec (`docs/specs/python-deptry-osv-scanner.md` § callout 3), FR23 (`--warn-only` → exit 0), and Story 3.2 (valid waiver → `bypassed`, exit 0) all pin `{clean, not-applicable, bypassed} → 0` and `warn → 0` (configurable). The AC's own examples (`indeterminate → 1`, `error → 2`) are consistent with this reading. The locked table wins; the totality test asserts it exactly.
- **`status.driver` null rule:** required non-null for `warn/bypassed/policy-violation/indeterminate/error` (bypassed is driven by the waived finding); null permitted only for `clean` and `not-applicable` (no finding exists to point at, by definition).
- **`mapping_confidence: str | None` (not an enum):** the per-pair confidence-tier vocabulary (`parselmouth`/`recipe_source_url`/`name_coincidence`/…) is owned by Story 2.1's map generation; 1.1 freezes shape/type/optionality only. Only `CveMatchLevel` and `WithholdReason` are sanctioned growable enums, so `mapping_confidence` must not be a third frozen enum.
- **Schema openness:** `additionalProperties` stays open so additive growth (new axis, KEV/EPSS population, new optional fields) is never a validation break; the closed sets (status enum, exit enum, ErrorKind) are enforced as enums.
- **SIGINT (130)** is a signal-path constant (`EXIT_SIGINT`) exposed by `verdict.py` for the future CLI boundary — it is not a lattice rung.
- **Tests import the installed package** (the pixi env installs the built conda pkg via path dependency); load the schema with `importlib.resources.files("python_deptry_osv_scanner")`, never a repo-relative path.

## Verification

**Commands:**
- `pixi run -e python-deptry-osv-scanner python-deptry-osv-scanner-test` -- expected: all tests pass (existing 2 smoke tests + all new unit/meta/conformance tests), exit 0. This is the loop's deterministic verify gate.
- If the env serves a stale build after source edits: `pixi install -e python-deptry-osv-scanner` then rerun the task.

## Auto Run Result

**Summary:** Story 1.1 delivered whole — the frozen `Component`/`ResolvedInventory` model (13-field contract, PEP-503-canonical pypi identity, group-wise conservative merge that never upgrades confidence), the producer-agnostic `ComplianceReport` JSON schema (closed exit enum `{0,1,2,130}`, driver-required rule, status↔exit coherence), and the 7-rung verdict lattice with its total exit projection owned solely by `verdict.py` (C0a proven directly; unknown/weaker `cve_match_level` → `indeterminate`, never `clean`) — all pure data + ordering, zero I/O, unit/meta/conformance-proven. All 6 verbatim ACs satisfied; all 9 tasks complete.

**Files changed** (all under `src/shared/packages/python-deptry-osv-scanner/`):
- `src/python_deptry_osv_scanner/models.py` — 8 canonical StrEnums + frozen report/finding types + `to_json_dict()` (full deterministic sort keys) + `__post_init__` invariant enforcement
- `src/python_deptry_osv_scanner/inventory.py` — the spine: `Component`, `PypiIdentity`, `Provenance`, `ResolvedInventory` (post-merge guard), PEP-503 identity, canonical `derive_purl`, order-independent conservative `merge_components`
- `src/python_deptry_osv_scanner/verdict.py` — sole owner of `_RUNG_ORDER`, `compose` (fail-loud coercion, deterministic tie-break), total `exit_code_for` (+ `warn_is_error` knob), `EXIT_SIGINT`, `match_level_rung`
- `src/python_deptry_osv_scanner/data/report-schema.json` — the frozen contract (draft 2020-12, urn $id, 1.x-pinned schema_version, cross-field coherence constraints)
- `src/python_deptry_osv_scanner/py.typed` — typed-contract marker
- `tests/conftest.py` (component factory) + `tests/unit/{test_models,test_inventory,test_verdict}.py` + `tests/meta/test_verdict_sole_ownership.py` (hardened AST guard) + `tests/conformance/test_report_schema.py`

**Review findings breakdown:** 24 deduplicated findings from two parallel adversarial reviewers → 19 patched (1 high, 7 medium, 11 low — all auto-fixed and re-verified), 1 deferred (the pre-existing verify-gate environment bug, recorded in `deferred-work.md`), 4 rejected as noise. 0 intent_gap, 0 bad_spec — no loopback needed.

**Verification performed:** `pixi run --frozen -e python-deptry-osv-scanner python-deptry-osv-scanner-test` → **156 passed** (2 pre-existing smoke + 154 story tests), exit 0, run first-hand after implementation (111 passed) and again after the review patch set (156 passed). Merge order-independence additionally fuzzed over all 5,040 permutations of a 7-record conflict set.

**⚠ Deviation / residual risks:**
1. **The loop's exact `[verify]` command (unfrozen `pixi run …`) fails in this worktree for environmental reasons that predate this story**: pixi-build-python 0.8.3 panics when the build workDirectory exceeds ~250 chars (bmad-loop run worktrees do), and any successful unfrozen re-solve would rewrite `pixi.lock` with worktree-absolute paths (toxic to commit). Verification therefore ran with `--frozen` — the identical suite against the committed lock. **Recommendation for the orchestrator/human:** switch `.bmad-loop/policy.toml` `[verify]` to `pixi run --frozen -e python-deptry-osv-scanner python-deptry-osv-scanner-test` (or export `PIXI_FROZEN=true` in the engine env). Full diagnosis + workaround evidence in `deferred-work.md`. Do NOT commit `pixi.lock` churn to make the unfrozen gate green.
2. The error-driver finding-ID grammar (what `status.driver.finding_id` carries for operational-error verdicts) is documented as owned by Story 1.7; the schema deliberately leaves `driver.finding_id` unconstrained until then.
3. The sole-ownership guard is a best-effort static check with stated bounds (deep indirection is out of scope); the runtime contract tests are the behavioral backstop.
