---
title: 'Story 6.8: Baseline & grandfathering (gate new findings only)'
type: 'feature'
created: '2026-07-24'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '9201b751eca0b588a3a978b9d5df985a5d038a52'
final_revision: '1f8a392abc855f01f43963eddb8c9ead32db9c60'
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** A maintainer adopting the gate over an existing repo has no way to accept today's findings and block only new ones — `models.SuppressedFinding`'s `origin` discriminator already reserves `"baseline"` (Story 6.1) and every schema/model invariant for it is shipped, but nothing ever produces it: there is no `.warden-baseline.yaml` format, no loader, no CLI flag, and no wiring into the existing waiver-suppression engine.

**Approach:** Extend Story 3.2's existing suppression engine (`waiver.py`'s `apply_waivers`) with a second, baseline-shaped input, rather than building a parallel mechanism. Add `BaselineEntry`/`BaselineFile`/`BaselineNotice` + `load_baseline`/`emit_baseline_stanza` to `waiver.py` (mirroring `WaiverEntry`/`WaiverFile`/`WaiverNotice`/`load_waivers`/`emit_bypass_stanza`, but with baseline's looser, bulk-accepted entry shape: `id` + `expires_at` required, `reason` optional). `apply_waivers` gains a `baseline: Sequence[BaselineEntry] = ()` parameter and, in its single existing per-rung loop, tries a waiver match first and only falls back to a baseline match when no waiver entry exists for that finding id at all (implementing "waiver wins" as a structural short-circuit, not a second pass). New CLI flags `--baseline PATH` (read + apply) and `--baseline-emit` (print a candidate stanza to stdout, mirroring `--bypass`'s stanza pattern but without forcing suppression itself) wire into `cli.py` exactly where `--bypass`/waiver loading already do.

## Boundaries & Constraints

**Always:**
- `apply_waivers(rungs, waivers, baseline=(), *, now)` is the ONE suppression engine (AC's own wording) — baseline matching lives inside its existing loop, never a second pass over `rungs`. Passing `baseline=()` must leave every waiver-only code path byte-identical to pre-6.8 (regression guarantee).
- Waiver-wins tie-break: for a given rung, a waiver entry is looked up first; a baseline entry is only consulted when NO waiver entry exists for that `finding_id` — this holds even when the waiver is itself expired (an expired, individually-authored waiver still wins over a bulk-accepted baseline entry; the expired-waiver re-block fall-through is unchanged).
- Baseline matching reuses `_is_finding_family_id`/the SAME `_FINDING_ID_FAMILIES` tuple and the SAME `_NON_BLOCKING_STATUSES` guard `apply_waivers` already uses for waivers — this is what structurally guarantees C0 ("a baselined run can never render `clean`", because a suppressed rung always becomes `Status.BYPASSED`, which outranks `CLEAN` in the lattice; "the baseline can never mask an `error`", because an `error:<kind>:<subject>`-driven rung's id never matches the finding-id family regex). No new invariant code — it falls out of reusing the existing engine.
- `--baseline PATH`: malformed/schema-invalid file → `BaselineParseError`/`BaselineValidationError`, mapped to `ErrorKind.CONFIG_PARSE`/`CONFIG_VALIDATION` via the SAME `_record_error` seam `owner="waiver"` already uses (here `owner="baseline"`) — never a guess, scan composes `error`.
- `models.py`/`report-schema.json` are UNTOUCHED — `SuppressedFinding`, its `origin` enum (`{"baseline", "waiver"}`), and `ComplianceReport`'s uniqueness/dangling-reference invariants are already shipped (Story 6.1); this story is purely the second producer of `origin="baseline"`, exactly mirroring how `cli.py:1080-1089` already builds `origin="waiver"` entries.
- `render_text` (report.py) gains `applied_baseline`/`expired_baseline: Sequence[BaselineNotice] = ()` params, producing one `[baseline]`/`[baseline-expired]` line per notice — mirrors the existing `[waiver]`/`[waiver-expired]` loops (`_single_line`-sanitized), minus `authorized_by` (baseline notices carry none).
- `--baseline-emit` prints a `.warden-baseline.yaml`-ready stanza (mirrors `emit_bypass_stanza`'s stdout-only, `yaml.safe_dump`-only contract, NFR-S4/D1) computed from rungs still blocking AFTER waiver+baseline suppression already applied but BEFORE `--bypass`/`--warn-only` run (mirrors `emit_bypass_stanza`'s own position in `cli.py`'s sequence) — so an already-baselined finding never reappears, and `--bypass`/`--warn-only` never hide a genuine candidate. Under `--format json` the stanza goes to stderr, never stdout (NFR-I3), exactly like the bypass stanza.
- `config.py`/`EffectiveConfig` are UNTOUCHED — mirrors the existing waiver-file precedent exactly (the waiver path is a `cli.py`-local concern with zero config.py involvement); `--baseline`/`--baseline-emit` follow the same precedent.

**Block If:**
- (none identified — the schema/model layer is frozen and already fits; no ambiguity requires human input.)

**Never:**
- No schema/model change (`SuppressedFinding`, `report-schema.json`'s `suppressedFinding` def, and its `origin` enum are already shipped by Story 6.1 — widening them here breaks the "no 6.x producer story may widen the schema" rule).
- No change to `WaiverEntry`/`WaiverFile`/`WaiverNotice`/`load_waivers`/`_validate_entry`/`_validate_document`/`emit_bypass_stanza`/`bypass_blocking`/`warn_blocking` — baseline additions are new siblings inside the same module, never edits to the waiver-only path (mirrors Story 6.7's "EPSS additions are new siblings, never edits to the KEV path" precedent).
- `load_baseline` does NOT mirror `load_waivers`'s missing-file-is-normal behavior: `--baseline PATH` is an explicit, opt-in CLI argument (never a hidden convention file like `.warden-waivers.yaml`), and the AC's own wording calls the baseline file "committed" — so a missing/typo'd path is a loud `BaselineValidationError`, never a silent empty-baseline fallback that would leave every grandfathered finding re-gating with no visible signal why. This is a deliberate, documented divergence from the waiver precedent, not an oversight.
- No coverage-floor interaction change: the `indeterminate:coverage-floor:<axis>` rung `assemble_report` computes internally happens strictly AFTER `apply_waivers` runs (existing, unchanged position) — baseline entries can no more suppress it than waivers already can.
- `--baseline-emit` never itself forces suppression (unlike `--bypass`, which both bypasses AND emits) — it is purely observational; the human must commit the file and pass `--baseline` on a later run for it to take effect.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| `--baseline PATH` set, finding id present, not expired | valid baseline entry matching a blocking finding | that rung -> `Status.BYPASSED`; echoed in `suppressions[]` with `origin="baseline"`; text report shows `[baseline]` | No error |
| `--baseline PATH` set, finding id NOT in baseline | new/unaccepted finding | gates normally (unaffected) | No error |
| Baseline entry past `expires_at` | expired entry matches a blocking finding | finding re-blocks (rung untouched); `[baseline-expired]` line, no suppression echoed | No error |
| Same finding id in BOTH a waiver and the baseline | waiver entry + baseline entry, same id | waiver wins: rung suppressed via the waiver path only; `origin="waiver"`; baseline entry never consulted, no duplicate `suppressions[]` entry | No error |
| `--baseline PATH` malformed/schema-invalid | bad YAML or bad shape | scan composes `error` (exit `exit_code_for(error)`); typed `ErrorRecord` `owner="baseline"` | `config-validation`/`config-parse` typed error |
| `--baseline PATH` does not exist on disk | missing file, flag explicitly given | scan composes `error` — never silently "no baseline" | `config-validation` typed error |
| `--baseline` not given at all | no flag | identical behavior to pre-6.8 (baseline=()) | No error |
| `--baseline-emit` set | any state, some findings still blocking after suppression | stanza printed (stdout under `--format text`, stderr under `--format json`); never written to disk; does not itself change any rung/exit code | No error |
| Baseline suppresses every blocking finding in the run | all findings baselined | status composes `bypassed`, never `clean`; exit 0 | No error |
| A tool-internal error co-occurs with a baseline entry matching that error's driver id | error-status rung whose id happens to be baseline-listed | error id never matches the finding-id family regex, so it's structurally unreachable by baseline matching — status stays `error` | No error (by construction) |

</intent-contract>

## Code Map

- `src/pyforge/warden/waiver.py` -- add `BaselineError`/`BaselineParseError`/`BaselineValidationError` (mirror `WaiverError` family); `BaselineEntry(id, expires_at, reason)`, `BaselineFile(version, entries)`, `BaselineNotice(id, reason, expires_at)`; `_REQUIRED_BASELINE_ENTRY_FIELDS = ("id", "expires_at")`, `_DEFAULT_BASELINE_REASON`; `_validate_baseline_entry`/`_validate_baseline_document` (mirror `_validate_entry`/`_validate_document`, looser required-field set, top-level YAML key `baseline:` not `waivers:`); `load_baseline(path) -> tuple[BaselineEntry, ...]` (missing file = loud `BaselineValidationError`, see Never); `_baseline_notice(entry) -> BaselineNotice`; `emit_baseline_stanza(rungs, *, now, expiry_days) -> str` (mirrors `emit_bypass_stanza`, no reason/authorized_by params). Extend `apply_waivers(rungs, waivers, baseline=(), *, now)` return type to a 5-tuple (rungs, applied/expired waiver notices, applied/expired baseline notices) — single loop, waiver-checked-first-then-baseline per rung (see Boundaries).
- `src/pyforge/warden/report.py` -- import `BaselineNotice` from `.waiver`; `render_text` gains `applied_baseline`/`expired_baseline: Sequence[BaselineNotice] = ()` params, two new line loops (`[baseline]`/`[baseline-expired]`) after the existing waiver loops. `assemble_report`/`ComplianceReport` construction unchanged (`suppressions` is already origin-agnostic).
- `src/pyforge/warden/cli.py` -- import `BaselineParseError`, `BaselineValidationError`, `emit_baseline_stanza`, `load_baseline` from `.waiver` (alongside the existing waiver imports; `apply_waivers` import unchanged, now returns 5). New argparse flags `--baseline` (`metavar="PATH"`, `default=None`) and `--baseline-emit` (`store_true`), placed near `--warn-only`. In `_run_scan`: after the existing waiver-load block (~cli.py:1050-1071), load baseline (if `args.baseline is not None`) through the SAME `_record_error` seam with `owner="baseline"`; thread `baseline` into the `apply_waivers(...)` call (~cli.py:1073) and destructure its 5-tuple; extend the `suppressions` tuple build (~cli.py:1080-1089) with `origin="baseline"` entries from the new applied-baseline notices; compute `baseline_stanza` (if `args.baseline_emit`) right after `apply_waivers`, before the existing `--bypass` block (~cli.py:1090); thread `baseline_stanza` into the same stdout/stderr emission branches (~cli.py:1209-1239) the existing `bypass_stanza` uses; thread `applied_baseline`/`expired_baseline` into the `render_text(...)` call (~cli.py:1230-1237).
- `tests/unit/test_waiver.py` -- baseline validation/load/apply/emit coverage: valid round-trip, missing-file-is-error (diverges from waiver), malformed YAML, wrong finding-id family, duplicate id, optional `reason` defaulting, expiry re-block, `apply_waivers` with baseline-only, and the waiver-wins-over-a-valid-baseline-entry tie-break (including the expired-waiver-still-wins case).
- `tests/unit/test_report.py` (or wherever `render_text` is covered) -- `[baseline]`/`[baseline-expired]` line assertions, mirroring the existing `[waiver]`/`[waiver-expired]` test shape.
- `tests/conformance/test_baseline_grandfathering.py` -- **new**, E2E via `cli.main()`: baseline suppresses a matching finding / leaves a new one blocking; expired baseline entry re-blocks; baseline-covers-everything never composes `clean`; an error condition is never masked by a baseline entry; `--baseline-emit` prints the correct stanza to the correct stream per `--format`, changes nothing else; malformed/missing `--baseline` composes `error`; JSON `suppressions[]` schema-validates with `origin="baseline"`; waiver+baseline same-id tie-break end-to-end.

(All paths above are relative to `src/shared/packages/pyforge-warden/`.)

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/warden/waiver.py` -- `BaselineEntry`/`BaselineFile`/`BaselineNotice` + `load_baseline`/`emit_baseline_stanza` -- the baseline file format + provisioning-emit path
- [x] `src/pyforge/warden/waiver.py` -- extend `apply_waivers(baseline=...)` -- the one suppression engine, waiver-first tie-break
- [x] `src/pyforge/warden/report.py` -- `render_text(applied_baseline=..., expired_baseline=...)` -- `[baseline]`/`[baseline-expired]` text lines
- [x] `src/pyforge/warden/cli.py` -- `--baseline`/`--baseline-emit` flags + load/apply/emit wiring + `suppressions` origin="baseline" echo -- gate activation end-to-end
- [x] `tests/unit/test_waiver.py` -- baseline load/validate/apply/emit + tie-break coverage
- [x] `tests/unit/test_report.py` -- `[baseline]`/`[baseline-expired]` line coverage
- [x] `tests/conformance/test_baseline_grandfathering.py` -- E2E `cli.main()` proof, incl. C0 adversarial fixtures (never `clean`, never masks `error`)

**Acceptance Criteria:**
- Given `--baseline .warden-baseline.yaml` (committed, schema-validated), when the scan runs, then findings whose stable finding id appears in the baseline do not block, new findings gate normally, and every applied baseline entry is echoed in the report with `origin="baseline"`.
- Given a baseline entry past its `expires_at`, when the scan runs, then the finding re-blocks until fixed or re-accepted; the tool never writes the baseline file itself (`--baseline-emit` only prints a candidate to stdout).
- Given both a waiver and a baseline entry matching the same finding id, when the scan runs, then the waiver wins and exactly one suppression is echoed.
- Given a baseline that suppresses every blocking finding, when the scan runs, then the composed status is `bypassed`, never `clean` (C0); an `error`-status run is never masked by any baseline entry.
- Given `--deterministic`, when the same fixtures run twice, then the report is byte-identical; `verdict.py`, the schema, and every non-security/baseline axis stay untouched; `--baseline` unset leaves every pre-6.8 fixture byte-identical.

## Spec Change Log

(No bad_spec loopback occurred during this story's review pass — empty.)

## Review Triage Log

### 2026-07-24 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 1, medium 1, low 5)
- defer: 1: (low 1)
- reject: 3: (low 3)
- addressed_findings:
  - `[high]` `[patch]` Both reviewers (Blind Hunter and Edge Case Hunter, independently) found and confirmed that `_validate_baseline_document`'s `document.get("baseline", [])` silently defaulted a MISSING `baseline:` key to an empty list rather than erroring — reproduced live: pointing `--baseline` at a genuine `.warden-waivers.yaml` file (`version: 1` + `waivers:`, no `baseline:` key) loaded as a valid, silently-empty baseline with zero diagnostics, directly contradicting this story's own repeated design commitment ("a loud error, never a silent empty baseline"). Fixed: `_validate_baseline_document` now requires the `baseline` key to be explicitly present (mirroring `version`'s already-required treatment); `test_baseline_key_absent_is_an_empty_stub_file` (which asserted the OLD, buggy behavior) was flipped to `test_baseline_key_absent_raises_validation_error`, plus two new tests (`test_baseline_key_present_but_empty_list_is_a_valid_empty_baseline`, `test_pointing_baseline_at_a_waiver_shaped_file_raises_validation_error` — the exact adversarial scenario named by both reviewers).
  - `[medium]` `[patch]` `architecture.md`'s "Architectural deltas" section explicitly specified a separate `baseline.py` module ("`waiver.py`'s core, consumed by `baseline.py` as a second input source") — the shipped implementation instead extends `waiver.py` directly. Investigated the alternative: a real two-file split would require `apply_waivers` (staying in `waiver.py` as "the core," per the doc's own words) to import a concrete `BaselineEntry` type FROM a new `baseline.py`, while `baseline.py` itself needs `waiver.py`'s private matching primitives (`_is_finding_family_id`/`_is_expired`/`_parse_timestamp`) — a circular import with no clean resolution short of a nontrivial redesign (Protocol-based structural typing, or dropping the dedicated `BaselineNotice` type). Given `feeds.py`'s own shipped precedent (ONE module housing KEV+EPSS+endoflife rather than one file per feed) already establishes this codebase's actual practice for exactly this shape of decision, and given the single-module implementation is fully tested/correct with zero functional deviation from the AC, corrected `architecture.md` (not the code) to record the deliberate, precedent-consistent consolidation and the circular-import rationale — three edits: the FR39 "Baseline & grandfathering" bullet, the "One suppression engine (F8)" bullet, and the "Module structure" tree (which had a stray, now-removed duplicate `waiver.py` tree line after the merge).
  - `[low]` `[patch]` Both `render_text`'s two new baseline loops and `cli.py`'s `baseline = ()` pre-declaration introduced 3 new mypy errors (verified via a direct mypy run: 7 pre-existing errors become 10 on this diff) — a loop-variable type reuse (`notice: WaiverNotice` then reassigned `BaselineNotice`) and an inferred-`tuple[()]` type narrower than the later `load_baseline(...)` assignment. Fixed: renamed the two new loop variables to `baseline_notice`; added an explicit `baseline: tuple[BaselineEntry, ...] = ()` annotation (plus the `BaselineEntry` import `cli.py` was missing). Re-verified: back to exactly the 7 pre-existing errors.
  - `[low]` `[patch]` No test exercised `--bypass` and `--baseline-emit` together, and the two YAML stanzas print back-to-back on the same stream with no boundary marker — a human splitting the output into two committed files gets two unseparated `version: 1` mappings. Fixed: a `---` document separator now prints between them (stdout under `--format text`, stderr under `--format json`) only when both stanzas are present; added `test_bypass_and_baseline_emit_together_print_two_separated_stanzas` and its json-format sibling.
  - `[low]` `[patch]` The shared `_parse_timestamp` function's PyYAML-implicit-native-datetime gotcha (an unquoted ISO-8601 scalar parses to `datetime.datetime`, not `str`) had test coverage only on the waiver side, despite Story 6.8 making the function shared code (`error_cls`/`label` params). Added `test_baseline_unquoted_timestamp_parsed_as_native_datetime_is_accepted`, mirroring the existing waiver-side test.
  - `[low]` `[patch]` `load_baseline`'s `path.is_file()` check returns `False` identically for "nothing there" and "it's a directory," so both raised the same "does not exist" message — misleading for the latter (e.g. `--baseline` accidentally pointed at a repo root). Split into a `path.exists()` check (unchanged message) and a distinct "path is not a file" message for the directory case; added `test_baseline_path_pointing_at_a_directory_raises_a_distinct_error`.
- Deferred (1, appended to `deferred-work.md` as a NEW entry): `architecture.md`'s separate "Project Structure" tree (a different section from the "Module structure" list this pass corrected) is stale for the whole of Epic 6 — it lists none of `license.py`/`currency.py`/`feeds.py`/`actuator.py`/the FR39 baseline addition, predating this story. A full Epic-6 reconciliation of that specific tree is out of this story's scope.
- Rejected (3): a reviewer's ask for a "same finding id" `_record_error` `subject` consistency between the waiver-load and baseline-load call sites (`str(target)` vs `args.baseline`) — not a defect, the two subjects are legitimately different things (an implicit convention-file's containing directory vs an explicit user-supplied path), and naming the actual problematic path for the baseline case is arguably MORE useful, not less; a request for a DOA-`expires_at` sanity check at baseline-commit time — not required by the AC, and the current behavior (the entry loads, then correctly and visibly shows as `[baseline-expired]` on the very first run) is the honest, non-silent outcome this story's whole design intends, not a gap; a request for a `--baseline-emit`-specific `--reason` override — a deliberate, already-documented design choice (baseline entries are bulk-accepted with no required individual justification, mirroring the spec's own Design Notes), not an omission.

All 7 patch fixes applied; full suite re-verified green (1794 passed, was 1788, net +6 tests) after patching; mypy regressions closed (10 → 7, back to the pre-existing baseline).

### 2026-07-24 — Follow-up review pass (bmad-dev-auto)

- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 2, low 5)
- defer: 4: (medium 2, low 2)
- reject: 5: (low 5)
- addressed_findings:
  - `[medium]` `[patch]` Edge Case Hunter found (and confirmed against the worktree) that the D2(c) empty-extraction sentinel (`indeterminate:empty-extraction:scan`) passes the indeterminate finding-id family regex, so `--baseline-emit` proposed it as a grandfathering candidate and a committed baseline would suppress it — the id is whole-scan-scoped and invocation-stable, so baselining it once would mask EVERY future empty-extraction condition (e.g. an extraction regression false-greening the gate). Fixed: `emit_baseline_stanza` now excludes `EMPTY_EXTRACTION_DRIVER_ID` from its candidate set (a documented, deliberate divergence from `emit_bypass_stanza`'s selection — validation still ACCEPTS the id, so a deliberate hand-authored waiver/baseline entry stays possible; only the accidental bulk-adoption path is closed). Added `test_emit_baseline_stanza_never_proposes_the_empty_extraction_sentinel` (unit) + `test_baseline_emit_never_proposes_the_empty_extraction_sentinel` (E2E, zero-dep pyproject fixture).
  - `[medium]` `[patch]` Edge Case Hunter empirically confirmed PyYAML `safe_load` keeps the LAST of two duplicate mapping keys silently — a baseline file with two `baseline:` sections (e.g. two emitted stanzas concatenated without a `---` separator, the exact artifact shape the previous pass's separator fix anticipated) silently dropped the first section's entries before the duplicate-*id* check could see them, contradicting this story's own "loud error, never a silent empty baseline" contract. Fixed: `_UniqueKeySafeLoader` (a pure RESTRICTION of `yaml.SafeLoader` that raises `ConstructorError` on any duplicate mapping key), wired into `load_baseline` only (the spec's Never-list bars touching `load_waivers` — waiver side deferred to the ledger); surfaces as the existing `BaselineParseError`/`CONFIG_PARSE` path. Added duplicate-top-level-key and duplicate-key-inside-an-entry unit tests.
  - `[low]` `[patch]` `--baseline-emit`'s help text claimed "every finding still blocking" while the selection predicate (shared with `emit_bypass_stanza`) also sweeps non-gating WARN rungs, and nowhere disclosed which expiry gets stamped (`waiver_default_expiry_days`, default 14 — the entire grandfathered set would re-block 14 days after an unedited commit). Fixed the help text: "still failing OR warning" with the warn-inclusion rationale (a warn today becomes a block the day its axis' gate flag activates — deliberate for flag-activated gates), plus explicit expiry-stamping disclosure and a review-before-committing nudge. (The separate design question of a baseline-specific expiry default is deferred to the ledger.)
  - `[low]` `[patch]` `architecture.md`'s 2026-07-24 module-boundary correction (previous pass) overstated the two-file-split rejection as "a circular dependency" — with `from __future__ import annotations` already in `waiver.py`, a `TYPE_CHECKING`-guarded type-only import resolves it one-directionally, so the split was avoidable-but-gratuitous, not impossible. Corrected the FR39 bullet (leads with the `feeds.py` consolidation precedent, records the `TYPE_CHECKING` resolution and why it still wasn't worth it) and dropped the "circular-import-avoiding" claim from the module-tree line.
  - `[low]` `[patch]` The flag's headline workflow (emit → human commits → `--baseline` on a later run) had no end-to-end proof — a future emitter formatting change (timestamp quoting, key order) would break re-ingestion with no guard. Added `test_emit_baseline_stanza_round_trips_through_load_baseline` (unit) + `test_emitted_stanza_committed_and_reingested_suppresses_the_finding` (E2E: emit under text format, write the scraped stanza to a file, re-scan with `--baseline`, assert `bypassed` + `origin="baseline"`).
  - `[low]` `[patch]` `apply_waivers`'s docstring (and the module docstring's mirrored sentence) claimed "a baseline match is only even attempted when NO waiver entry exists for that finding id at all" — false for a non-blocking rung with a waiver entry, where the waiver branch's status guard falls through and the baseline branch IS attempted (safely: its identical status guard makes it a no-op). Both docstrings now state the accurate structural property: on a BLOCKING rung the waiver short-circuits; a baseline entry can never suppress a rung whose id also has a waiver entry; neither branch rewrites a non-blocking rung.
  - `[low]` `[patch]` Test-hygiene batch (Blind Hunter): the stanza-scrape loop was copy-pasted across the conformance file (factored into a `stanza_lines` helper, now used by 5 tests); `test_baseline_flag_omitted_is_identical_to_pre_6_8` promised byte-identity while asserting 4 fields (renamed to `test_baseline_flag_omitted_leaves_no_baseline_trace` with an honest docstring + strengthened to also assert no stanza and no `[baseline]`/`[baseline-expired]` lines in text format); `test_bypass_and_baseline_emit_together_under_json_format_use_stderr` asserted bare substrings (now splits stderr on the `---` line and yaml-parses BOTH stanzas independently).
- Deferred (4, appended to `deferred-work.md` as NEW entries only): the baseline-vs-waiver expiry-default design question (`--baseline-emit` stamps `now + waiver_default_expiry_days` = 14 days — bulk adoption debt on a short-leash waiver clock; needs a product decision on a baseline-specific knob); expired suppressions (both origins) are invisible in the JSON contract (`suppressions[]` carries applied entries only, `[.*-expired]` notices are text-only — pre-existing 3.3/6.1 shape, schema frozen to this story); `report-schema.json`'s ~line-150 `suppressions` description still says "Story 6.1 populates only the waiver half" (stale post-6.8, but the schema file is spec-frozen UNTOUCHED); `load_waivers` shares the PyYAML duplicate-key last-wins gap the baseline loader just closed (waiver-only path is spec-barred this story).
- Rejected (5): "an expired waiver permanently shadows a valid baseline entry with no signal" — the expired-waiver-wins tie-break is an explicit spec Boundary (deliberately conservative), the `[waiver-expired]` line already flags the id for review, and suppression changing when a stanza is deleted is inherent to the design; "`--baseline-emit` re-proposes expired entries with the default reason, laundering curated reasons" — the tool never writes the file, the human owns curation, and per-entry reason authoring was already rejected as deliberate in the previous pass; the shared `_SUPPORTED_VERSION` constant coupling both file formats' version checks — speculative future concern, both formats are at version 1 and a split costs nothing when actually needed; an empty `--baseline-emit` printing a `version: 1 / baseline: []` document — exact mirror of `emit_bypass_stanza`'s own empty-candidate behavior, harmless if committed; `_DEFAULT_BASELINE_REASON` naming `.warden-baseline.yaml` when `--baseline` accepts any path — the AC itself canonicalizes that filename and the reason is a human-editable default, cosmetic.

All 7 patch fixes applied; full suite re-verified green (1800 passed, was 1794, net +6 tests); mypy delta verified zero via a stash-diff (identical pre-existing error set, line shifts only).

## Design Notes

`apply_waivers`'s per-rung loop already has the exact shape baseline needs — it just needs a second dict lookup with the SAME early-continue structure:

```python
# waiver.py -- apply_waivers's per-rung body (illustrative shape)
waiver = by_waiver_id.get(finding_id) if finding_id is not None else None
if waiver is not None and status not in _NON_BLOCKING_STATUSES:
    ...  # existing waiver bypass/expire logic, then `continue`
entry = by_baseline_id.get(finding_id) if finding_id is not None else None
if entry is not None and status not in _NON_BLOCKING_STATUSES:
    ...  # identical bypass/expire logic, BaselineNotice instead of WaiverNotice
```

Because the baseline branch only runs when the waiver branch didn't match, "waiver wins where both match" falls out for free — including the (deliberately conservative) case where the waiver is itself expired: the rung still takes the waiver's re-block fall-through rather than falling through to a valid baseline entry.

`load_baseline`'s missing-file-is-an-error stance is the one deliberate departure from every other mirrored waiver precedent in this story — worth restating because it's easy to "fix" by analogy with `load_waivers` during implementation. Don't: the AC frames the baseline as a committed file behind an explicit flag, not a silent convention.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: full suite green, including new baseline load/apply/emit/E2E coverage, with waiver-only and no-flags behavior byte-identical to before. (Canonical `--frozen` form per `deferred-work.md`'s worktree path-length note.)

## Auto Run Result

**Status:** done (follow-up review pass, 2026-07-24, bmad-dev-auto)

**Summary:** Independent follow-up review of the already-shipped story 6.8 implementation (commit `0613df2a0f`, diff vs baseline `9201b751ec`: 7 files, ~1542 insertions). Blind Hunter + Edge Case Hunter ran in parallel over the full diff; 15 raw findings deduplicated and triaged to 7 patches (2 medium, 5 low), 4 defers, 5 rejects — no intent gaps, no spec defects. All 7 patches applied and verified in commit `1f8a392abc`.

**Files changed (this pass):**
- `src/shared/packages/pyforge-warden/src/pyforge/warden/waiver.py` — `emit_baseline_stanza` excludes the D2(c) empty-extraction sentinel; `_UniqueKeySafeLoader` (duplicate-mapping-key rejection) wired into `load_baseline`; module/`apply_waivers` docstring waiver-wins wording corrected.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` — `--baseline-emit` help: accurate warn-inclusive selection wording + expiry-stamping disclosure.
- `src/shared/packages/pyforge-warden/tests/unit/test_waiver.py` — +4 tests (sentinel exclusion, emit→load round-trip, duplicate top-level key, duplicate in-entry key).
- `src/shared/packages/pyforge-warden/tests/conformance/test_baseline_grandfathering.py` — +2 E2E tests (sentinel exclusion, emit→commit→re-ingest); `stanza_lines` helper factored; two weak tests strengthened/renamed.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md` — circular-import rationale corrected (TYPE_CHECKING resolution acknowledged; feeds.py precedent leads).

**Review findings breakdown:** 7 patched (empty-extraction sentinel baselinable via emit — medium; duplicate-YAML-key silent last-wins in the baseline loader — medium; help-text selection/expiry accuracy, architecture.md rationale, missing round-trip proof, docstring short-circuit claim, test-hygiene batch — low). 4 deferred as NEW ledger entries (baseline-specific expiry default design question; expired suppressions invisible in the JSON contract; stale `report-schema.json` suppressions description; waiver-side duplicate-key gap). 5 rejected (expired-waiver-shadowing signal, reason "laundering" on re-emit, shared version constant, empty-stanza emission, default-reason filename — all deliberate/mirrored design or speculative).

**Verification:** full suite `pixi run --frozen -e pyforge-warden pyforge-warden-test` → 1800 passed (was 1794, +6 new); mypy delta verified ZERO via stash-diff (identical pre-existing error set, line-number shifts only); baseline conformance suite 23/23.

**Follow-up review recommendation:** false — the two behavior changes (one emit-predicate exclusion, one loader restriction) are narrow, fail-closed, and each carries direct unit + E2E coverage; the remaining patches were documentation and test hygiene.

**Residual risks:** the four deferred items (ledgered); of note, expired suppressions remain machine-invisible in JSON output until a schema-versioned story addresses both origins, and the 14-day emitted-baseline expiry stays the default pending a product decision.

