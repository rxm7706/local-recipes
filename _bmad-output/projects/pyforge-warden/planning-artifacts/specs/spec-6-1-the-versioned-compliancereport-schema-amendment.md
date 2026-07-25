<!-- RECOVERED 2026-07-25 from Claude Code session transcript e35cde46-7b89-45b5-b4c0-0a317a766344.jsonl (~/.claude/projects); this is the ORIGINAL spec incl. its dev/review narrative, not an epics.md regeneration. -->
---
title: 'The versioned ComplianceReport schema amendment (Story 6.1)'
type: 'feature'
created: '2026-07-18'
status: 'draft'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/finding-id-verdict-encoding-decision.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/implementation-artifacts/epic-6-context.md'
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** Epic 6 adds two new producer axes (license, currency) plus KEV/EPSS gates, baseline suppression, and a fix-PR actuator. Each needs a schema-validated place to write in the frozen v1 `ComplianceReport`, but the contract (`models.py` + `report-schema.json`) has no slots for them and no way to key policy/waiver/baseline matching on the new axes without smuggling through free-text `indeterminate:` tokens. Without one deliberate amendment, every producer story would drift the schema ad hoc.

**Approach:** Land the ONE sanctioned, additive `schema_version` bump (`1.0.0` → `1.1.0`, staying inside `_SCHEMA_VERSION_RE`) that admits everything Epic 6 needs — implementing story 6.10's decision record verbatim (no new design decisions on its four pinned questions) and mechanically adding the remaining AC-listed slots by mirroring shipped patterns (`vuln_data` provenance, `AxisCoverage`, the `kev`/`epss` Finding slots). 6.1 defines the slots and re-closes; the producers (6.2–6.9) populate them later. The amendment is behavior-neutral for shipped E1–E4 scans.

## Boundaries & Constraints

**Always:**
- Additive-only. `additionalProperties` stays open everywhere (never add `additionalProperties: false`) so `test_additive_extra_fields_still_validate` keeps passing and a pre-amendment consumer keeps validating. `schema_version` stays `1.x` (`_SCHEMA_VERSION_RE` honored, not widened).
- The two new `Component` fields (`license_covered`, `currency_covered`) are **defaultless** on the frozen dataclass (mirroring the existing 13 fields), so every construction site must pass them explicitly — a `_merge_group` omission is a loud `TypeError` by design. `_fold_bare` builds via `dataclasses.replace`, which has NO such guard: both new fields MUST appear in its `replace()` call or the bare record's value is silently dropped.
- New-coverage fields are set to `True` (behavior-neutral: "not axis-uncovered") at every production and test construction site and default `True` in `conftest.make_component`, so shipped fixtures never flip and byte-determinism (twice-run identical) holds. Producers (6.2/6.3) set `False` later; 6.1's `DefaultPolicy` uncovered-license/currency blocks land INERT.
- Policy/waiver/baseline matching keys ONLY on schema-validated typed fields (the closed verdict enums, the finding-ID families), never on free-text `indeterminate:` reason tokens.
- `verdict.py` remains the sole owner of the composed `Status` lattice (the verdict-sole-ownership meta-test must still pass). `LicenseVerdict`/`CurrencyVerdict` are `Finding`-level inputs, NOT a second lattice, and are NOT added to the growable-enum list.
- Every new finding-ID family and coherence rule lands in BOTH the Python model (`models.py` `__post_init__` + `waiver.py`'s mirror tuple) AND `report-schema.json`, matching the shipped `vuln:`/`hygiene:` pair exactly.

**Block If:**
- A shipped E1–E4 conformance fixture cannot be kept green by additive/mechanical means alone (would signal the amendment is not behavior-neutral — a real design conflict, not a mechanical edit).
- The decision record's pinned shape (a grammar, enum, or coherence clause) cannot be applied as written because the live code has diverged from its cited anchors in a way that changes intent — surface it, do not improvise a producer-side workaround.

**Never:**
- No producer logic. 6.1 emits no `license:`/`currency:` findings, populates no license/currency/KEV/EPSS provenance, computes no `gating` bool, adds no `config.py` policy property (`license_policy`/`currency_policy` are 6.2/6.3), designs no `baseline.py` (6.8), and opens no PRs (6.9). It only reserves and validates the slots.
- No second suppression path — `suppressions[]` is the one echo channel; baseline's half (`origin: "baseline"`) is 6.8.
- No `over-lag` as a 4th `CurrencyVerdict` member (it is an id-grammar reason token only, verdict `supported`; escalation is a separate numeric `lag` check owned by 6.5).
- No `additionalProperties: false`; no renaming `vuln_data` or any shipped field.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Shipped scan, post-amendment | Any E1–E4 target, default flags | Same `status`/`exit_code`/`findings`; `coverage[]` now also carries `license` + `currency` rows (`deps_assessed=0`); `schema_version="1.1.0"`; new optional sections absent/null | No error |
| Pre-amendment consumer reads post-amendment report | Old validator, new report | Validates (additive; `additionalProperties` open) | No error |
| Mis-axed license/currency finding | `Finding(id="license:…", axis="hygiene")` | Rejected at `ComplianceReport.__post_init__` AND schema validation | `ValueError` (Python) / schema violation (`render_json`) |
| Coverage claim for an unregistered axis | An `EngineResult.coverage` names an axis ∉ `_REPORT_AXES` | Hard fail (F6) — never silently dropped | `ValueError` in `assemble_report` |
| `_fold_bare` AND-flip | `concrete.license_covered=True`, `bare.license_covered=False` | Folded result `license_covered is False` | Flip-detecting meta-test guards omission |
| Applied waiver, JSON output | `--format json` with an applied waiver | `report.suppressions[]` carries one `{finding_id, origin:"waiver", …}`; `render_json` echoes it | No error |
| Duplicate/dangling suppression | Two `suppressions[]` with same `finding_id`, or a `finding_id` ∉ `findings[]` | Rejected at `ComplianceReport.__post_init__` | `ValueError` |
| `license:` finding without `license` sub-object | `id="license:…"` but no `license` key (a future producer bug) | Rejected by coherence clause `then.required:["license"]` | schema violation |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/src/pyforge/warden/models.py` -- the frozen contract: enums, `AXIS_*`, `_FINDING_ID_FAMILIES` (46-50), `Finding` (kev/epss slots), `ComplianceReport` + `__post_init__` coherence (371-441), `to_json_dict`/`_finding_dict`/`_finding_sort_key`/`_coverage_sort_key`. THE core edit.
- `src/pyforge/warden/data/report-schema.json` -- the JSON-Schema mirror validated at `render_json`; `$defs.finding` (with `id.anyOf` + `allOf` coherence pair 320-339), top-level structure.
- `src/pyforge/warden/inventory.py` -- `Component` (13-field defaultless frozen dataclass, 69-91); `_merge_group` (defaultless `Component(...)` call, 349-371); `_fold_bare` (`replace()`, 468-478).
- `src/pyforge/warden/interfaces.py` -- `_sanitize_id_segment` (119-138); `DefaultPolicy.evaluate` per-component loop with the `hygiene_covered`→`uncovered` block (375-388) + the `indeterminate:{token}:{subject}` id builder/dedupe (404-424).
- `src/pyforge/warden/report.py` -- `REPORT_SCHEMA_VERSION` (143), `_REPORT_AXES` (148), `assemble_report` coverage build (231-261), `render_json` validate (319-320).
- `src/pyforge/warden/extract/_identity.py` (7 `Component(...)` sites: 171,228,253,268,292,481,501) + `extract/pyproject.py` (3 sites: 137,164,184) -- production constructors.
- `src/pyforge/warden/waiver.py` -- local `_FINDING_ID_FAMILIES` mirror (72-76); `WaiverNotice` (133-141, the `SuppressedFinding` shape source); `apply_waivers` (exact-string match).
- `src/pyforge/warden/cli.py` -- `apply_waivers` (823) → `assemble_report` (859) → `render_json(report)` (911, no waivers today) / `render_text(…, applied_waivers=…)` (918-927).
- `tests/unit/test_models.py` (exact-13 meta-test 194-212; epss validation; `_sample_component` 126), `tests/unit/test_vuln.py` (inline `Component` 362), `tests/unit/test_inventory.py` (merge/fold), `tests/unit/test_interfaces_and_null_engine.py` (policy loop), `tests/conftest.py` (`make_component` 33-75), `tests/conformance/test_report_schema.py` (additive-fields 238; schema conformance), `tests/unit/test_report.py` + `tests/conformance/test_scan_harness.py` (coverage-row assertions).

## Tasks & Acceptance

**Execution:** (dependency order — `models.py` first; the decision record's "How Story 6.1 applies this" § is the exact per-file map, cross-referenced below)

- [ ] `models.py` -- Add `AXIS_LICENSE="license"` / `AXIS_CURRENCY="currency"` (mirror 35-37). Extend `_FINDING_ID_FAMILIES` (46-50) with `re.compile(r"license:[^:\n]+:.+@.+")` and `re.compile(r"currency:(eol|over-lag|unknown):.+@.+")` (§§1–2). Add two CLOSED `StrEnum`s `LicenseVerdict{allowed,denied,unknown}` / `CurrencyVerdict{supported,eol,unknown}` — NOT in the growable list (§3). Add `LicenseInfo{expression:str, family:str|None, verdict:LicenseVerdict}` and `CurrencyInfo{verdict:CurrencyVerdict, latest:str|None, lag:int|None, eol_date:str|None, tier:str|None}` Finding sub-object dataclasses; add optional `license: LicenseInfo|None=None`, `currency: CurrencyInfo|None=None`, `kev_date: str|None=None` to `Finding` and change `epss: float|None` → `epss: Epss|None=None` with new `Epss{score:float, percentile:float}` (both in [0,1]); update `Finding.__post_init__` to validate the object instead of the float. Add `SuppressedFinding{finding_id:str, origin:str, reason:str, authorized_by:str|None, expires_at:str|None}` (reuse `WaiverNotice`'s fields, `id`→`finding_id`; `origin` closed to `{"baseline","waiver"}`, validated in `__post_init__`; §5.1). Add optional `ComplianceReport` fields (all defaulted so `assemble_report` keeps working): `suppressions: tuple[SuppressedFinding,...]=()`, `license_data`/`currency_data`/`kev_data`/`epss_data: FeedProvenance|None=None` (new `FeedProvenance{source,snapshot_at,max_age_ok}` reusing `VulnData`'s shape+`__post_init__`; leave `vuln_data:VulnData` untouched), `gating` (see AxisCoverage below), `actuation: object|None=None` (reserved open slot, always `None` in 6.1). Extend `ComplianceReport.__post_init__` (371-441) with the two id-prefix↔axis clauses (§5.4a) and the `suppressions[]`↔`findings[]` cross-ref + uniqueness checks (§5.5). Add `gating: bool=False` to `AxisCoverage`. Extend `to_json_dict`/`_finding_dict`/`_coverage_dict` to render every new key; extend `_finding_sort_key` None-safe for the new fields; add `_suppressed_finding_sort_key` (mirror `_coverage_sort_key`) to order `suppressions[]`. -- Rationale: the contract core; all other edits mirror this.
- [ ] `report-schema.json` -- Widen `$defs.finding.id.anyOf` with `^license:[^:\n]+:[^\n]+@[^\n]+$` and `^currency:(eol|over-lag|unknown):[^\n]+@[^\n]+$`; add the `license`/`currency` Finding sub-object schemas + `kev_date` + the `epss` object shape `{score,percentile}` (§5.3); add the FOUR coherence `allOf` entries — (a) id-prefix↔axis for license/currency, (b) id-reason↔verdict with `then.required:[<subobj>]`, (c) currency-provenance completeness narrowing `latest`/`lag`/`eol_date` to non-null for `eol`/`over-lag` (§5.4a/b/c); add `$defs.suppressedFinding` + top-level optional `suppressions` array; add top-level optional `license_data`/`currency_data`/`kev_data`/`epss_data` (each `oneOf[null, {source,snapshot_at,max_age_ok}]`, mirroring `vuln_data`'s if/then), optional `gating` on `$defs.axisCoverage`, and an optional open `actuation` object. Do NOT set `additionalProperties:false` anywhere. -- Rationale: the validator half; `render_json` raises if a rendered field isn't admitted.
- [ ] `report.py` -- Bump `REPORT_SCHEMA_VERSION` `"1.0.0"`→`"1.1.0"` (143). Widen `_REPORT_AXES` (148) to `(AXIS_HYGIENE, AXIS_VULNERABILITY, AXIS_LICENSE, AXIS_CURRENCY)`. In `assemble_report`, after building `assessed_by_axis` (232-238), add the F6 guard: any axis in `assessed_by_axis` not in `_REPORT_AXES` raises `ValueError` (never silent-drop). -- Rationale: register the axes (else coverage is dropped) + close F6.
- [ ] `inventory.py` -- Add `license_covered: bool` / `currency_covered: bool` to `Component` (defaultless, appended after `vuln_matchable`). Add both to `_merge_group`'s `Component(...)` call as pure `all(...)` ANDs (mirror `hygiene_covered`). Add `license_covered = concrete.license_covered and bare.license_covered` (+ currency) to `_fold_bare` and include both in its `replace()` call (§4). -- Rationale: the two new coverage fields + their Gap-B merge/fold rules.
- [ ] `interfaces.py` -- Import `AXIS_LICENSE`/`AXIS_CURRENCY`. In `DefaultPolicy.evaluate`'s per-component loop, alongside the `hygiene_covered` block (375-388), add two blocks appending `(Status.INDETERMINATE, "uncovered-license", AXIS_LICENSE, <msg>)` / `("uncovered-currency", AXIS_CURRENCY, <msg>)` — tokens MUST be axis-qualified (NOT bare `"uncovered"`) to avoid the `indeterminate:{token}:{subject}` id collision at line 405 (§4). -- Rationale: lands the uncovered-finding mechanism (inert in 6.1; producers set the fields `False` later).
- [ ] `extract/_identity.py` + `extract/pyproject.py` -- Add `license_covered=True, currency_covered=True` to all 10 `Component(...)` sites. -- Rationale: defaultless fields require explicit values; `True` = behavior-neutral pre-producer.
- [ ] `waiver.py` -- Widen the local `_FINDING_ID_FAMILIES` (72-76) with the same two regexes as `models.py` (§5.6), so `license:`/`currency:` findings are waivable. -- Rationale: keep the mirror tuple in lockstep in the same commit.
- [ ] `cli.py` -- Convert `applied_waivers` (823) → `tuple[SuppressedFinding{origin:"waiver"}]` and thread it into `assemble_report` (new defaulted `suppressions: Sequence[SuppressedFinding]=()` param on `assemble_report`) so `render_json` echoes them (§5.6). -- Rationale: today waivers echo in `render_text` only; wire the JSON half (baseline half is 6.8).
- [ ] `tests/unit/test_models.py` + `tests/unit/test_vuln.py` + `tests/conftest.py` -- Update the exact-N meta-test (194-212): add the two field entries and bump `13`→`15` (and the "13-field" docstrings); add `license_covered=True, currency_covered=True` to `_sample_component` (126) and the inline `Component` (test_vuln.py:362); add the two params (default `True`) to `make_component` (33-75). Update the epss unit tests for the `{score,percentile}` object shape. -- Rationale: the meta-test uses `==` exact-dict + `len==15`; construction sites need the new fields.
- [ ] `tests/unit/test_inventory.py` -- Add the flip-detecting fold meta-test: `concrete.license_covered=True` + `bare.license_covered=False` ⇒ folded `license_covered is False` (and the currency twin) — fails if the field is omitted from `_fold_bare`'s `replace()` (§4). -- Rationale: guards the silent-carry-over pitfall.
- [ ] `tests/conformance/test_report_schema.py` + `tests/unit/test_report.py` + `tests/conformance/test_scan_harness.py` + `tests/unit/test_interfaces_and_null_engine.py` -- Update coverage-row assertions for the two new `_REPORT_AXES` entries; add positive/negative schema cases for the new families + coherence clauses (mis-axed reject; `license:` without `license` sub-object reject; `suppressions[]` round-trip); keep `test_additive_extra_fields_still_validate` unchanged and passing. -- Rationale: the amendment adds coverage rows + new validation surface.

**Acceptance Criteria:**
- Given a shipped E1–E4 target under default flags, when scanned post-amendment, then `status`, `exit_code`, and `findings` are byte-identical to pre-amendment except `schema_version` is `"1.1.0"` and `coverage[]` gains `license`/`currency` rows with `deps_assessed=0`; a second `--deterministic` run is byte-identical to the first (NFR-R3b).
- Given a pre-amendment consumer, when it validates a post-amendment report, then validation passes (`test_additive_extra_fields_still_validate` preserved) — the amendment is additive-only.
- Given a `Finding` whose id begins `license:`/`currency:` but whose `axis` disagrees, when the report is constructed or rendered, then both `ComplianceReport.__post_init__` and `render_json`'s schema validation reject it.
- Given an `EngineResult` reporting coverage for an axis not in `_REPORT_AXES`, when `assemble_report` runs, then it raises rather than silently dropping the claim (F6).
- Given `_fold_bare` with a `True` concrete and a `False` bare coverage field, when it folds, then the result is `False` (conservative AND); the flip-detecting meta-test fails if a new field is omitted from `replace()`.
- Given an applied waiver and `--format json`, when the report is emitted, then `suppressions[]` carries one `{finding_id, origin:"waiver", reason, authorized_by, expires_at}` and `render_json` validates; a dangling or duplicate `suppressions[].finding_id` is rejected at construction.
- Given the full suite, when `pixi run -e pyforge-warden pyforge-warden-test` runs, then it is green (the exact-N meta-test now asserts 15; the verdict-sole-ownership and socket-deny meta-tests still pass).

## Design Notes

The 1068-line decision record (`finding-id-verdict-encoding-decision.md`, in `context:`) is the authoritative source for the four spike-pinned shapes and their verbatim regexes/JSON — implement it without new design decisions. This spec adds the remaining AC-listed slots by mirroring shipped patterns. Key non-obvious points:

- **Behavior-neutrality is the whole game.** The amendment must not change any shipped verdict. That forces `license_covered`/`currency_covered=True` everywhere in 6.1 (nothing sets `False`), the uncovered blocks land inert, and the new report sections stay `None`/`()`/absent. The only visible deltas are `schema_version` and the two extra `coverage[]` rows.
- **`epss` redefinition is safe only because it is unpopulated.** No shipped report sets `epss`, so changing `float|None`→`Epss{score,percentile}|None` breaks nothing at runtime; only the epss unit tests move to the object shape. This is the one non-purely-additive field change, and the AC mandates it.
- **Axis-qualified uncovered tokens (§4).** `interfaces.py` builds `finding_id = f"indeterminate:{token}:{subject}"` and dedupes on that exact string. Bare `"uncovered"` for all three axes would collide onto one id and silently swallow two axes. Use `uncovered-license`/`uncovered-currency`; leave hygiene's bare `"uncovered"` unchanged.
- **`_merge_group` vs `_fold_bare` asymmetry (§4).** `_merge_group` uses a full defaultless `Component(...)` (omission = loud `TypeError`); `_fold_bare` uses `replace()` (omission = silent carry-over). Both new fields go in the `replace()` call; the flip test proves it.
- **`origin`, not `source` (§5.1).** The suppression discriminator is `origin` (`source` already means `VulnData.source` and feed-provenance elsewhere). `authorized_by`/`expires_at` are nullable on `SuppressedFinding` (baselines are bulk-accepted) even though `WaiverEntry` requires them.
- **Coherence `then` must `require` the sub-object key.** JSON-Schema `properties` is vacuous on an absent key — clause (b)/(c) `then` branches must list `required:["license"]`/`["currency"]` and, for (c), narrow `latest`/`lag`/`eol_date` types to exclude `null`, mirroring `vuln_data.max_age_ok`'s existing if/then.
- **Deferred by design (do not implement):** `config.py` `license_policy`/`currency_policy` + `gating` computation → 6.2/6.3/6.5; baseline `origin:"baseline"` echo + `baseline.py` → 6.8; producer emission of any `license:`/`currency:` finding or feed provenance → 6.2–6.7; `actuation` content → 6.9.

## Verification

**Commands:**
- `pixi run -e pyforge-warden pyforge-warden-test` -- expected: full suite green; the exact-N `Component` meta-test passes at 15 fields; `test_additive_extra_fields_still_validate`, `test_verdict_sole_ownership`, and `test_socket_deny_alive` all pass.
- `pixi run -e pyforge-warden python -c "import json,jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('src/shared/packages/pyforge-warden/src/pyforge/warden/data/report-schema.json')))"` -- expected: the amended schema is itself a valid Draft 2020-12 document (no typos in the new `$defs`/`allOf`).
- `pixi run -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/conformance/test_report_schema.py -q` -- expected: schema-conformance (additive-fields, new families, coherence rejects) green.
