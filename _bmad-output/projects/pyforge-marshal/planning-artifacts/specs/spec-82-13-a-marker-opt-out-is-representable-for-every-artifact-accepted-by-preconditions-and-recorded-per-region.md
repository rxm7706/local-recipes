---
title: '82.13: A marker opt-out is representable for every artifact, accepted by preconditions, and recorded per region'
type: 'fix'
created: '2026-10-02'
status: 'in-review'
baseline_revision: 'dfd5482b46238c5745573fbfccd19e439f99e8df'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-8-5-marker-deletion-as-a-sanctioned-opt-out.md
warnings: [oversized]
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** FR-112 makes deleting a managed region's markers a permanent opt-out; three gaps (the Story 8.5 family) keep
it from holding end to end. Re-verified at HEAD a7cdb91fe4:

- `seed/state/schema.json` types `managed[].id` as `nonBlankString` (`:59`, pattern `\S`, so spaces and `#` are legal),
  while the `opted_out` item pattern is `^[^\s#]+#[a-z0-9][a-z0-9-]*` (`:78`). Its description (`:75`) claims the artifact
  half is "deliberately as permissive as managed[].id"; it is stricter, so `record_opt_out(state, "has a space", ...)`
  raises and a legally named artifact cannot be opted out. `ManifestEntry` requires only a non-blank id. No manifest id in
  the fleet trips it today; every real id is a slug (DW-FU-8-5-2).
- `seed/verbs/preconditions.py` never reads `opted_out` (zero occurrences); rung 6 reports a deleted region as
  "recorded managed region is missing from the file" (`:445`) under `managed-content-modified`, whose remedy tells the
  operator to revert the deletion or `--force`. `seed/verbs/adopt.py:1002-1003` already feeds `state.opted_out` to
  `build_plan`, and `adopt`, `update` (`:1061`) and `init` (`:484`) all call `check_preconditions`, so the two halves
  contradict each other on FR-112's own scenario (DW-FU-8-5-5).
- `managed[]` holds at most one entry per id (`seed/state/store.py:609`, `_reject_duplicates` at `:326`) and each entry
  exactly one nullable `inserted_region_span` (`schema.json:107`). A hybrid artifact with several declared regions can
  record one span, so `detect/optout.py` honours a deleted region's opt-out for at most one region and its siblings fall to
  `MISSING`, whose remedy re-inserts them (DW-FU-8-5-6).

**Approach:**

- One artifact-id grammar: `ManifestEntry.id` and `managed[].id` both reject whitespace and `#` (the `opted_out` artifact
  half's grammar, defined once in the schema and once in code); the schema description says so. A state file carrying such
  an id reads as `state-invalid`, as any schema violation does.
- Rung 6 skips a recorded region whose `<id>#<region>` is opted out, recorded in `state.opted_out` or derived by
  `detect/optout.py`; the verbs pass the opt-out set alongside the managed records.
- State records a span per installed region of a hybrid artifact (a list keyed by region name); the store reads the old
  one-span shape as a one-region list and writes the new shape, so a derived opt-out covers each deleted region on its
  own.

Ledger key: `82-13-a-marker-opt-out-is-representable-for-every-artifact-accepted-by-preconditions-and-recorded-per-region`.
Type / Effort / Deps: fix / L / 82.12.

### Living CAP citations

- `spec-pyforge-marshal` CAP-11 (deleting the markers is recorded as a permanent opt-out that later runs respect) and CAP-17
  (the genesis-owned state file), with Story 8.5 (FR-112; AD-58) and Story 10.2 (the state schema and store). Defects of
  shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given a manifest entry whose id contains a space or `#` When the manifest loads Then it fails with an error naming the entry
- Given every artifact id the shipped manifest declares When an opt-out is recorded for any of its regions Then the state validates
- Given a state whose `opted_out` holds `<id>#<region>` and a file whose region markers were deleted When `adopt`, `update` or `init` runs Then rung 6 does not report that region missing and no `--force` is needed
- Given a hybrid artifact with two declared regions whose markers were both deleted When detection runs and the state is written and read back Then both regions are opted out and neither is planned for insertion
- Given a state file in the old one-span shape When it is read Then it loads as a one-region list and the next write uses the new shape
- Given each fix reverted in turn When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** The state stays schema-validated at runtime (FR-104). An opt-out stays permanent until an explicit reinstate.
Close DW-FU-8-5-2, DW-FU-8-5-5 and DW-FU-8-5-6 in `deferred-work-ledger.md` when the story lands (status `closed`, a
`resolved:` line naming this story).

**Never:** Do not loosen the region-name grammar. Do not drop the old state shape without reading it. Do not change the
plan fingerprint, rung 5 or `--skip` (Story 82.12's surface).

</intent-contract>

## Code Map

Paths below are under `src/shared/packages/pyforge-marshal/`; `seed/` is `src/pyforge/marshal/seed/`. Line numbers are at HEAD `395393305b`.

- `seed/model/manifest.py:312-317` -- `ManifestEntry.__post_init__` runs `_require_text("id", ...)` (strips, non-blank only). `load_manifest` (`:612-616`) already prefixes any `ValueError` from `_build_entry` with the entry's raw id, so a new id check raises a `ManifestError` that names the entry with no loader change. Models: `tests/unit/test_seed_model_manifest.py:133` (duplicate id names it), `:303` (a path error names the id), `:1191` (a padded id is stripped, so it stays legal).
- `seed/state/schema.json:72-80` -- `opted_out`: item pattern `:78` (`^[^\s#]+#...`), description `:75` (the false "as permissive as managed[].id" claim). `:98-103` `nonBlankString`. `:104-168` `managedArtifact`: `required` `:107`, `if/then/else` on `class` `:109-118`, `id` `:120-123`, `body_sha` `:139-143`, `inserted_region_span` `:144-166`. `:169-182` `legacyArtifact` (its `id` stays `nonBlankString`).
- `seed/state/store.py` -- `RegionSpanRecord` `:341-397`; `ManagedArtifact` `:400-491` (`__post_init__` couples `class` to the span `:431-455`; `to_json_dict` `:457`; `from_json_dict` `:468`); `SeedState.__post_init__` `:584-629` (`_reject_duplicates` on `managed[].id` and `.path` `:609-613`); `_opt_out_pattern` `:723` (reads the schema's own `opted_out` pattern, unchanged); `_without_region_claim` `:899-919`; `record_opt_out` `:922-986` (its docstring `:944-958` says a second span per artifact is "UNREACHABLE"); `clear_opt_out` `:989-1061`; `read_state` `:1142` (schema validation `:1232-1241`, then `SeedState.from_json_dict` `:1243`); `write_state` `:1259` (validates the emitted document first). `seed/state/__init__.py` re-exports `RegionSpanRecord` and `ManagedArtifact`.
- `seed/detect/optout.py` -- module docstring "known limitation of rung 3: one recorded region span per artifact" `:95-105`; `_disposition` `:343-390` (docstring `:363-377` argues `managed[].id` is the "LOOSER grammar"); `_claims_region` `:393-437` (reads `artifact.inserted_region_span`); `classify_regions` `:440-499` (`OPTED_OUT` from rung 2, the recorded key, and rung 3, a surviving claim); `region_findings` comment `:572-578` (cites the one-span limit); `opt_outs_to_record` `:585-642`. The module is pure (`tests/meta/test_p03_detect_is_pure.py`): the caller passes `text` in.
- `seed/verbs/preconditions.py` -- module docstring rung 6 `:72-98`; `ManagedRecord` `:141-187` (`region_shas` is already plural; the module imports nothing from `seed.state`); `_region_divergences` `:405-466` (the "recorded managed region is missing from the file" divergence is `:443-452`; the unrecorded-present loop `:456-465`); `_managed_divergences` `:469-488`; `check_preconditions` `:491-701` (rung 6 `:679-701`; `force` returns before it).
- `seed/verbs/adopt.py` -- `_managed_records` `:561-592` (`region_shas` from the one span); `_managed_artifact_after_apply` `:856-921` (records the FIRST pending region only, comment `:883-888`); `_build_state_after_apply` `:924-965` (a touched id's old record is replaced, `:938-945`); `run_adopt` `:968-` (`read_state` `:1008`, `build_plan(opted_out=...)` `:1011-1012`, `escaping_ids` `:1024`, `managed_after_skips` `:1029`, `check_preconditions(` `:1037`).
- `seed/verbs/update.py` -- `_read_text_or_blank` `:326`; `_region_shas_for_record` `:336-393` (synthesizes a CURRENT-hash pair for every declared region state does not record, to stop multi-region entries refusing at rung 6); `_managed_records` `:396-424`; `_wholesale_regenerate_actions` `:427-502` (names EVERY declared region, never reads `opted_out`: DW-FU-11-4, `NEEDS-DECISION`, not this story); `_managed_artifact_after_apply` `:847-898` (first region only, comment `:866-871`); `run_update` `managed_after_skips` `:1120`, `check_preconditions(` `:1129`.
- `seed/verbs/init.py:517-524` -- `check_preconditions(..., managed=(), force=False)`: `init` reads no state, so rung 6 has no record to report. Unchanged.
- `seed/verbs/check.py:454-495` -- reads `record.inserted_region_span` to pick the region hash check; module docstring `:74`, `:82`, `:459` mention it. `check` writes nothing.
- `seed/plan/build.py:530-660` -- `build_plan(opted_out=frozenset[str])` suppresses insertion on the RECORDED keys only. Read-only here.
- Tests (about 80 references to the old field): `tests/unit/test_seed_state_store.py` (`:217` schema "as permissive" test, `:1339` key "as permissive" test, `:1606` the "at most one region span" test, schema `then/else` pin `:213-215`), `test_seed_detect_optout.py` (`:226` and `:245` pin the one-span limit), `test_seed_verbs_{preconditions,update,adopt,check,init}.py`, `test_seed_cli_seed_update.py`, `test_seed_model_manifest.py`, `test_seed_templates_manifest.py` (loads the shipped manifest through `importlib.resources`), `tests/meta/test_sc08_never_write_update_proof.py`.
- Shipped manifest `seed/templates/manifest.yaml` -- three real multi-region hybrid entries (`agents-md` 3 regions, `claude-md` 2, `projects-index` 2); the others declare one region. No id carries whitespace or `#`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- DW-FU-8-5-2 `:5525` (`status: open` `:5531`), DW-FU-8-5-5 `:5567` (`:5573`), DW-FU-8-5-6 `:5581` (`:5587`). A closed row to copy the shape of: the DW-10-4-5 row (`status: closed`, then a `resolved:` line, then `severity:`).

## Tasks & Acceptance

**Execution:**
- `seed/model/manifest.py` -- one module constant for the artifact-id grammar (a token with no whitespace and no `#`); `ManifestEntry.__post_init__` raises `ValueError` after `_require_text` strips, saying the id must carry no whitespace and no `#` and quoting it. `legacy_of` and `legacy[].id` are not touched.
- `seed/state/schema.json` -- a `$defs/artifactId` (`^[^\s#]+(?![\s\S])`, the `(?![\s\S])` terminator every anchored pattern here uses); `managed[].id` refs it; the `opted_out` description now says the artifact half is that same grammar and drops the "deliberately as permissive" claim. The `opted_out.items` pattern is unchanged (the store reads it). A test pins the three spellings (schema `artifactId`, the `opted_out` artifact half, the manifest constant) to agree on one probe set.
- `seed/state/schema.json` and `seed/state/store.py` -- per-region spans. `RegionSpanRecord` gains `body_sha` (the region body's `hash_content`, the shape `body_sha` already has). `ManagedArtifact.inserted_region_span` becomes `inserted_region_spans: tuple[RegionSpanRecord, ...]`: non-empty iff the class is `hybrid-managed-region`; span names unique within one artifact (`_reject_duplicates`); a hybrid's `body_sha` equals its first span's `body_sha` (`__post_init__` raises otherwise). Wire: `to_json_dict` always writes `inserted_region_spans` (array; `[]` for a non-hybrid). The schema accepts exactly one of `inserted_region_spans` (new) and `inserted_region_span` (object or null, the old shape, read-only), each coupled to `class` as the `if/then/else` couples the old one. `from_json_dict` reads the old object as a one-element list whose `body_sha` is the artifact's. `$id` stays `seed-state.v1`; reading never rejects an old file, and the next `write_state` rewrites it in the new shape.
- `seed/state/store.py` -- `_without_region_claim` drops only the named span from a matching hybrid entry (rebuilding it with the remaining spans; its `body_sha` follows the new first span) and drops the entry when none remain; a whole-file claim and another id's claim stay untouched. Rewrite the `record_opt_out` docstring's "UNREACHABLE" paragraph, the `ManagedArtifact` docstring and the `:183` comment.
- `seed/detect/optout.py` -- `_claims_region` matches any recorded span by name; add `opted_out_regions(entries_and_texts, state) -> frozenset[tuple[str, str]]` (pure: the caller supplies each hybrid entry with its file text) returning every `(artifact_id, region)` `classify_regions` answers `OPTED_OUT` for, recorded and derived alike. Rewrite the module docstring's one-span limitation, the `_disposition` "looser grammar" paragraph and the `region_findings` comment.
- `seed/verbs/preconditions.py` -- `check_preconditions(..., opted_out: frozenset[tuple[str, str]] = frozenset())`; rung 6 passes it to `_managed_divergences` and `_region_divergences`: a recorded region ABSENT from the parsed spans whose `(artifact_id, name)` is in the set is no divergence. A region present in the file is still hash-checked, an unparseable file is still a divergence, the unrecorded-present loop is unchanged, and `force` keeps its meaning. The module still imports nothing from `seed.state`. Update the module and function docstrings: a caller passes the opt-out set beside `managed`.
- `seed/verbs/adopt.py` and `seed/verbs/update.py` -- (a) `_managed_records` builds `region_shas` from every recorded span (`update._region_shas_for_record` keeps its synthesized current-hash pairs, now only for a declared region with no recorded span, i.e. an old-shape state, and says so); (b) `_managed_artifact_after_apply` records every region of the entry that is present in the file after the write and that the action named in `chosen_anchor` or the prior record for that id carried, each with the span offsets and `hash_content` of its body read back from the file; (c) before `check_preconditions`, compute `opted_out_regions` over the run's hybrid manifest entries (skip `escaping_ids`; read each file with the module's `_read_text_or_blank`) and pass it as `opted_out=`; (d) drop the "ONE `inserted_region_span`" comments.
- `seed/verbs/check.py` -- check every recorded span of a hybrid record against its own `body_sha`; update the three docstring mentions.
- Tests -- one new test per AC below, each failing when its fix is reverted, plus: duplicate span names in one artifact and duplicate ids across artifacts both raise; the old-shape file reads, writes back new, and re-reads equal; a corrupted new shape (a hybrid with `[]`, a non-hybrid with a span, a first-span `body_sha` mismatch) is `StateInvalid`; `record_opt_out` of one of two regions keeps the other's claim and `clear_opt_out` mirrors it; rung 6 on a recorded region that is PRESENT and modified still refuses while an opted-out pair is in the set; `init` still passes `managed=()`. Retarget the two "at most one span" tests and the two "as permissive" tests to the new behavior; migrate every `inserted_region_span=` construction (add `body_sha` to hybrid spans, equal to the artifact's).
- `deferred-work-ledger.md` -- close DW-FU-8-5-2, DW-FU-8-5-5 and DW-FU-8-5-6 (`status: closed`, a `resolved: 2026-10-02 (marshal Story 82.13, spec-pyforge-marshal CAP-11 CAP-17) ...` line each saying what shipped).
- `spec-pyforge-marshal` and `spec-pyforge-core` `.memlog.md` -- name every changed governed path (`python _bmad/scripts/memlog.py append`, one `--workspace` each), then run `python scripts/spec_surface_reconcile.py` and add any Spec it still names. Never `--write-baseline`.

**Acceptance Criteria:**
- Given a manifest entry whose id contains a space or `#`, when `load_manifest` runs, then it raises `ManifestError` whose text starts with that id and states the rule; a padded id (`" foo "`) still loads as `foo`.
- Given each id in the shipped `templates/manifest.yaml`, when `record_opt_out` runs for each of its regions and the state is written and read back, then it validates; and an id with a space is refused at the manifest, so the state never holds one (`managed[].id` with a space or `#` fails the schema as `StateInvalid`).
- Given state whose `opted_out` holds `<id>#<region>` (claim still present, or dropped) and a file whose markers for that region were deleted, when `run_adopt` or `run_update` runs without `--force`, then rung 6 raises nothing for that region; the same holds when nothing is recorded and the opt-out is only derived (claim present, markers gone). `run_init` passes `managed=()` and is unaffected. A second, hand-edited region of the same file still refuses.
- Given a hybrid artifact with two declared regions installed by `adopt`, when both regions' markers are deleted and detection runs, `opt_outs_to_record` is fed to `record_opt_out`, and the state is written and read back, then both regions classify `OPTED_OUT`, `state.opted_out` holds both keys, and `build_plan` plans no insertion for either.
- Given a fresh `adopt` of an artifact with three declared regions, when state is written, then `managed[]` holds one entry with three spans, each with its own `body_sha`, and a later `update` or `check` finds no divergence.
- Given a state file in the old one-span shape, when it is read, then it loads as a one-region list with the artifact's `body_sha`, and the next `write_state` emits `inserted_region_spans`.
- Given each fix reverted in turn, when its new test runs, then it fails.

## Spec Change Log

No bad_spec loopback yet.

## Design Notes

- **Why each span carries its own `body_sha`.** Rung 6 compares a region body to a recorded hash per region (`ManagedRecord.region_shas` is already plural); with one artifact-level `body_sha` the sibling regions have nothing to compare against, which is why `update.py::_region_shas_for_record` invents "current" hashes for them. Recording a hash per span removes that invention for every state written from now on; it stays only for an old one-span state. The hybrid artifact's own `body_sha` is kept (required by the schema, read by nothing for hybrids) as the first span's, enforced, so it cannot disagree.
- **The wire shape.** A new key beside the old one, rather than a retyped `inserted_region_span`, keeps the old shape readable by name and keeps the `if/then/else` coupling honest. State written by this release is not readable by an older marshal (its schema has `additionalProperties: false`); `seed_model_version` already records which release wrote the file. This is the cost of "writes the new shape".
- **The opt-out set is pairs, not keys.** `preconditions.py` must not import `seed.state` and must not re-spell the `<id>#<region>` key; `opt_outs_to_record` already returns plain pairs for the same reason. `opted_out_regions` goes through `classify_regions`, so a RECORDED opt-out (rung 2, no file needed) and a DERIVED one (rung 3, claim survives, markers gone) are one answer, and the verbs need no second spelling of either. A derived opt-out is the real FR-112 scenario: no mutating verb records one yet (`classify_regions`/`record_opt_out` have no verb caller), so a rung 6 that read `state.opted_out` alone would still refuse it.
- **Rung 6 skips only an ABSENT region.** A region the file still contains is hash-checked as before; `classify_regions` already says what is in the file wins over what state believes, so this never weakens detection of a modified region.
- **Out of scope, tracked.** `update`'s wholesale pass names every declared region and ignores `opted_out` (DW-FU-11-4, `NEEDS-DECISION`): AC 4's "not planned" is `build_plan`'s plan, which `adopt` and `update` both build first. A `--force` run records every region the action wrote or the prior record carried at its current hash, so an un-rewritten sibling that was hand-edited is adopted as the new baseline: the operator already chose to discard hand-edits, and before this story that sibling was not recorded at all. `legacy[]` ids keep their grammar; the architecture spine, `epics.md` and `SPEC.md` mention `inserted_region_span` as the S-10.2 shape and are not edited (a Spec is never hand-edited; the memlog carries the reconcile).

## Binding

Parent: Stories 8.5 and 10.2, `spec-pyforge-marshal` CAP-11 and CAP-17; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-13-a-marker-opt-out-is-representable-for-every-artifact-accepted-by-preconditions-and-recorded-per-region`.
Ledger status at mint: `backlog`.
Deps: 82.12 (both edit `seed/verbs/preconditions.py` and the verbs).
Closes: DW-FU-8-5-2, DW-FU-8-5-5, DW-FU-8-5-6.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run -e pyforge-guild lint-types` — expected: pass (ruff, `ruff format --check` and mypy over the `pyforge-*` packages; `AGENTS.md` § *Running and verifying*).
- `python scripts/spec_surface_reconcile.py` — expected: pass, once every changed governed path is named on the owning Spec's `.memlog.md` and each co-governor's (never `--write-baseline`).

## Review Triage Log

- No review has run yet.

## Auto Run Result

**Status:** in-review (implemented; adversarial review has not run)

**What changed.** Three defects of the Story 8.5 family, closed: DW-FU-8-5-2, DW-FU-8-5-5, DW-FU-8-5-6 (their rows in `deferred-work-ledger.md` are `closed` with a `resolved:` line).

- One artifact-id grammar (no whitespace, no `#`): `model/manifest.py::ARTIFACT_ID_PATTERN` checked in `ManifestEntry.__post_init__` after the strip, and `state/schema.json` `$defs/artifactId` for `managed[].id`; the `opted_out` description no longer claims the artifact half is "as permissive as managed[].id". `legacy[].id` and `legacy_of` are untouched.
- Per-region spans: `RegionSpanRecord` gains `body_sha`; `ManagedArtifact.inserted_region_span` became `inserted_region_spans` (non-empty iff hybrid, names unique, a hybrid's `body_sha` is its first span's); the wire shape is an array (`[]` for a non-hybrid); the schema accepts exactly one of the new key and the old one-span key (read-only), each coupled to `class`; the old shape reads as a one-region list and the next `write_state` emits the new one. `_without_region_claim` drops only the named span (the entry goes when none remain).
- `detect/optout.py`: `_claims_region` matches any recorded span; new `opted_out_regions(entries_and_texts, state)` (recorded and derived alike, pure).
- `verbs/preconditions.py`: `check_preconditions(..., opted_out=frozenset())`; rung 6 skips a recorded region ABSENT from the file whose pair is in the set. A present region is still hash-checked, an unparseable file is still a divergence, `force` and `init` are unchanged, and the module still imports nothing from `seed.state`.
- `verbs/adopt.py` and `verbs/update.py`: rung 6 gets `opted_out_regions` over the hybrid entries (never an escaping one); `region_shas` come from every recorded span; `_managed_artifact_after_apply` records every declared region present after the write that the action named or the replaced record (same `path`) carried, each with its own offsets and body hash. `update._region_shas_for_record` keeps its synthesized current-hash pairs only for a declared region with no recorded span (an old-shape state). `verbs/check.py` checks every recorded span against its own hash.
- Tests: a new `tests/unit/test_seed_verbs_region_opt_out.py` (both verbs, end to end) plus additions to the state-store, manifest, shipped-manifest, optout, preconditions and init tests; the two "at most one span" and two "as permissive" tests are retargeted, and every `inserted_region_span=` construction is migrated.

**Tests retargeted because they pinned the contradiction this story removes.** `test_hand_edited_managed_content_on_reapply_is_refused_without_force` and `test_skip_protects_a_hand_edited_artifact_from_rung_6_refusal` (`test_seed_verbs_adopt.py`) deleted the markers and expected a rung-6 refusal; they now hand-edit the region body with the markers intact. Two tests that built a manifest entry with the id `has a space` (`test_seed_detect_optout.py`, `test_seed_plan_build.py`) now overwrite the id after construction, since the manifest refuses it; they keep pinning the defence-in-depth gates in rung 3 and `build_plan`.

**Verification** (all from the run worktree, exit codes read directly).

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: 10770 passed, 1 skipped (10677 at the baseline).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`: 130 passed, 3 skipped.
- `pixi run -e pyforge-guild lint-types`: exit 0 (ruff, `ruff format --check`, mypy over the ten packages).
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate`: OK, 80% floor.
- `python scripts/spec_surface_reconcile.py`: exit 0; `spec-surface-check` names no drift once `spec-pyforge-marshal` and `spec-pyforge-core` memlogs name the changed governed paths (no `--write-baseline`).
- `deferred-work-check`, `story-status-check`, `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`, `ledger-regression-check`, `governance-currency`: exit 0.
- Mutation checks, each fix reverted in turn and only its tests failing: manifest id grammar; schema `managed[].id` ref; rung 6 ignoring the set; `adopt` and `update` not passing it; derived opt-outs left out of `opted_out_regions`; `adopt` and `update` recording only the first region; `adopt` and `update` not carrying the prior record; `_without_region_claim` dropping the whole entry; `_claims_region` matching the first span only; `check` checking the first span only; the old shape not reading; `adopt._managed_records` using one span; the first-span `body_sha` rule; the duplicate-span-name rule; the schema `oneOf`. One mutant survived once (`update` not carrying the prior record: the wholesale pass names every declared region, so no end-to-end run distinguishes it) and is now killed by a direct test of both `_managed_artifact_after_apply` helpers.

**Residual risks.**

- A DERIVED opt-out (markers gone, nothing recorded) now clears rung 6, but no mutating verb records it, `adopt` hands `build_plan` only `state.opted_out`, and `update`'s wholesale pass names every declared region (DW-FU-11-4, out of scope per the Design Notes): a mutating `adopt --apply` or `update --run` therefore re-inserts such a region rather than refusing. Before this story the refusal at rung 6 blocked that by accident (with a remedy that told the operator to undo the deletion). Recording the derivation in a verb is the follow-up; `--force` behaves as before.
- State written by this release is not readable by an older marshal (the schema is closed); `seed_model_version` records which release wrote it.
- `detect/optout.py::_claims_region` compares `path` and `state/store.py::_without_region_claim` does not (DW-FU-8-5-9, still open and untouched).
