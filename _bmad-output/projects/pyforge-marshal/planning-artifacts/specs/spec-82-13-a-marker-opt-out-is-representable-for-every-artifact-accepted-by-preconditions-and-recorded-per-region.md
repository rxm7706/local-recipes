---
title: '82.13: A marker opt-out is representable for every artifact, accepted by preconditions, and recorded per region'
type: 'fix'
created: '2026-10-02'
status: 'in-progress'
baseline_revision: 'dfd5482b46238c5745573fbfccd19e439f99e8df'
review_loop_iteration: 2
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
- `seed/verbs/adopt.py:1008-1012` and `seed/verbs/update.py:1038-1039` -- `read_state`, then `build_plan(opted_out=frozenset(state.opted_out))`: the plan sees only RECORDED opt-outs. `seed/detect/optout.py:79-93` (module docstring, the "sequencing contract") says a mutating verb records every pair `opt_outs_to_record` returns and persists it BEFORE it plans; no verb does (`record_opt_out` and `opt_outs_to_record` have no production caller). Both verbs write state only after a successful non-empty apply (`adopt._build_state_after_apply` `:924`, `update._build_state_after_apply` `:936`), carrying `state.opted_out` forward unchanged.
- `seed/verbs/update.py:427-502` -- `_wholesale_regenerate_actions` names EVERY declared region of every managed hybrid record in `chosen_anchor`, and `_update_commit` inserts or substitutes each one: the path that re-inserts an opted-out region. `deferred-work-ledger.md:1903` (DW-FU-11-4, `NEEDS-DECISION`) asks whether it should; the contract's Always bullet answers that for opted-out regions.
- `docs/managed-region-contract.md` (package root) -- the contract page for managed regions; the FR-112 paragraph is where the opt-out behaviour is stated for operators.
- `seed/verbs/adopt.py:1085-1099` and `seed/verbs/update.py:1107-1128` -- `run_adopt`/`run_update` rebind `state` to the in-memory state returned by `_state_with_opt_outs`; `_build_state_after_apply` (`adopt.py` ~`:996`, `update.py` ~`:960`) builds `prior_by_id` from that rebound state, so for an old-shape record (one span, now dropped) the replaced record is `None`. `_managed_artifact_after_apply` (`adopt.py` ~`:905`, `update.py` ~`:895`) names regions from `action.chosen_anchor` plus `prior`'s spans; a hybrid `Action` with `chosen_anchor == ()` is legal (`plan/build.py` `_pendency` keeps it when `retained` is non-empty and nothing is pending), so both are empty and it raises `InternalError`. Pass 1 removed the baseline's check that every region the action named is present after the write.
- `seed/verbs/update.py:397-445` -- `_region_shas_for_record` reads `repo_root / artifact.path` for every declared region with no recorded span, and `_managed_records` runs before the `escaping_ids` filter in `run_update`: for an old-shape state with an escaping hybrid path the escaped file is read (a Story 82.11 invariant: never read).
- `docs/managed-region-contract.md` (package root) -- the 82.13 paragraph says deleting some markers "opts out exactly those regions" without the old-shape and empty-plan conditions, and cites the older marshal's `state-invalid` remedy as "re-runs `marshal seed adopt`", which cannot work (`run_adopt` reads state unguarded and does not downgrade `StateInvalid`). `finding-remedy-reference.md` and `adoption-guide.md` advertise `--reinstate`, which no verb or CLI declares yet (Story 10.6, DW-FU-8-5-4).

## Tasks & Acceptance

**Execution:**
- `seed/model/manifest.py` -- one module constant for the artifact-id grammar (a token with no whitespace and no `#`); `ManifestEntry.__post_init__` raises `ValueError` after `_require_text` strips, saying the id must carry no whitespace and no `#` and quoting it. `legacy_of` and `legacy[].id` are not touched.
- `seed/state/schema.json` -- a `$defs/artifactId` (`^[^\s#]+(?![\s\S])`, the `(?![\s\S])` terminator every anchored pattern here uses); `managed[].id` refs it; the `opted_out` description now says the artifact half is that same grammar and drops the "deliberately as permissive" claim. The `opted_out.items` pattern is unchanged (the store reads it). A test pins the three spellings (schema `artifactId`, the `opted_out` artifact half, the manifest constant) to agree on one probe set.
- `seed/state/schema.json` and `seed/state/store.py` -- per-region spans. `RegionSpanRecord` gains `body_sha` (the region body's `hash_content`, the shape `body_sha` already has). `ManagedArtifact.inserted_region_span` becomes `inserted_region_spans: tuple[RegionSpanRecord, ...]`: non-empty iff the class is `hybrid-managed-region`; span names unique within one artifact (`_reject_duplicates`); a hybrid's `body_sha` equals its first span's `body_sha` (`__post_init__` raises otherwise). Wire: `to_json_dict` always writes `inserted_region_spans` (array; `[]` for a non-hybrid). The schema accepts exactly one of `inserted_region_spans` (new) and `inserted_region_span` (object or null, the old shape, read-only), each coupled to `class` as the `if/then/else` couples the old one. `from_json_dict` reads the old object as a one-element list whose `body_sha` is the artifact's. `$id` stays `seed-state.v1`; reading never rejects an old file, and the next `write_state` rewrites it in the new shape.
- `seed/state/store.py` -- `_without_region_claim` drops only the named span from a matching hybrid entry (rebuilding it with the remaining spans; its `body_sha` follows the new first span) and drops the entry when none remain; a whole-file claim and another id's claim stay untouched. Rewrite the `record_opt_out` docstring's "UNREACHABLE" paragraph, the `ManagedArtifact` docstring and the `:183` comment.
- `seed/detect/optout.py` -- `_claims_region` matches any recorded span by name; add `opted_out_regions(entries_and_texts, state) -> frozenset[tuple[str, str]]` (pure: the caller supplies each hybrid entry with its file text) returning every `(artifact_id, region)` `classify_regions` answers `OPTED_OUT` for, recorded and derived alike. Rewrite the module docstring's one-span limitation, the `_disposition` "looser grammar" paragraph and the `region_findings` comment.
- `seed/verbs/preconditions.py` -- `check_preconditions(..., opted_out: frozenset[tuple[str, str]] = frozenset())`; rung 6 passes it to `_managed_divergences` and `_region_divergences`: a recorded region ABSENT from the parsed spans whose `(artifact_id, name)` is in the set is no divergence. A region present in the file is still hash-checked, an unparseable file is still a divergence, the unrecorded-present loop is unchanged, and `force` keeps its meaning. The module still imports nothing from `seed.state`. Update the module and function docstrings: a caller passes the opt-out set beside `managed`.
- `seed/verbs/adopt.py` and `seed/verbs/update.py` -- (a) `_managed_records` builds `region_shas` from every recorded span (`update._region_shas_for_record` keeps its synthesized current-hash pairs, now only for a declared region with no recorded span, i.e. an old-shape state, and says so); (b) `_build_state_after_apply` takes the replaced records from the state AS READ (kept before the in-memory opt-out recording; the in-memory state still supplies the carried-over records and `opted_out`), and `_managed_artifact_after_apply` records, for a hybrid entry, every declared region PRESENT in the file after the write when a replaced record exists at the same `path` (that record's installer is the tool, so its siblings are the tool's), or else only the regions `action.chosen_anchor` named; each with its own offsets and `hash_content` of its body read back from the file, in declared order. It raises `InternalError` (naming them) when a region `action.chosen_anchor` named is absent after the write, even if other regions were recorded (restoring the check pass 1 dropped), and returns `None` when nothing is named and no declared region is present (the artifact is no longer claimed: every region was deleted); `_build_state_after_apply` omits a `None` record; (c) before `build_plan`, compute the run's opt-out pairs with `opted_out_regions` over the hybrid manifest entries and their file text (skip `escaping_ids`; read each file with the module's `_read_text_or_blank`), record the DERIVED ones in memory with `record_opt_out` (`opt_outs_to_record`; the sequencing contract in `detect/optout.py`'s module docstring), and give ONE resulting set to `build_plan(opted_out=frozenset(state'.opted_out))` and, as pairs, to `check_preconditions(opted_out=...)`; when the run writes state (after a non-empty apply, as today) it writes that state', so the derived opt-outs are recorded with it, and a dry run, `check` and an empty-plan run write nothing; (d) drop the "ONE `inserted_region_span`" comments.
- `seed/verbs/check.py` -- check every recorded span of a hybrid record against its own `body_sha`; update the three docstring mentions.
- Tests -- one new test per AC below, each failing when its fix is reverted, plus: duplicate span names in one artifact and duplicate ids across artifacts both raise; the old-shape file reads, writes back new, and re-reads equal; a corrupted new shape (a hybrid with `[]`, a non-hybrid with a span, a first-span `body_sha` mismatch) is `StateInvalid`; `record_opt_out` of one of two regions keeps the other's claim and `clear_opt_out` mirrors it; rung 6 on a recorded region that is PRESENT and modified still refuses while an opted-out pair is in the set; `init` still passes `managed=()`. Retarget the two "at most one span" tests and the two "as permissive" tests to the new behavior; migrate every `inserted_region_span=` construction (add `body_sha` to hybrid spans, equal to the artifact's).
- `deferred-work-ledger.md` -- close DW-FU-8-5-2, DW-FU-8-5-5 and DW-FU-8-5-6 (`status: closed`, a `resolved: 2026-10-02 (marshal Story 82.13, spec-pyforge-marshal CAP-11 CAP-17) ...` line each saying what shipped).
- `seed/verbs/update.py` -- `_wholesale_regenerate_actions` takes the opt-out pairs: a region in the set is not named in `chosen_anchor`, and a hybrid record whose every declared region is in it gets no wholesale action (its record is carried over untouched, so rung 6 and `check` still see it). Only OPTED-OUT regions change; `state.skips` and the `skips` half of DW-FU-11-4 are untouched.
- `docs/managed-region-contract.md` -- one paragraph: deleting some of an artifact's markers opts out exactly those regions, and `adopt` and `update` neither refuse the run nor re-insert them (asserted by the mutating-run tests below, not by prose alone); no hard-coded region count; and a plain statement that state written by this release is not readable by an older marshal (the schema is closed and the package version is unchanged, so `seed_model_version` cannot tell the two apart; the older marshal reports `state-invalid`, whose remedy re-runs `adopt`). No file, spec, docstring or ledger line claims `seed_model_version` identifies the writing release.
- Tests, review pass 1 -- (i) mutating runs for BOTH verbs (`run_adopt(apply=True, yes=True)`, `run_update(run=True, yes=True)`) over a DERIVED opt-out and a RECORDED opt-out: afterwards the deleted region's markers are still absent from the file, the written state's `opted_out` holds its key and `managed[]` holds no span for it, a surviving sibling region's span and hash are intact, and no `--force` was passed; (ii) `update --run` with one of two regions recorded-opted-out regenerates the sibling and leaves the opted-out region deleted, and a hybrid artifact with every declared region opted out has no wholesale action; (iii) a hybrid entry whose path is an escaping symlink through both verbs, with a spy on each module's `_read_text_or_blank` asserting the escaped path is never read and `escape_findings` naming it (Story 82.11); (iv) `test_force_still_discards_a_hand_edit_beside_an_opt_out` becomes a mutating `--force` run asserting the hand-edited sibling is rewritten and the opted-out region stays deleted; (v) the init test asserts `managed=()` without pinning the call's keyword shape, and the import-guard test also refuses `from .. import state`; (vi) the claim-dropped rung-6 test says in its docstring that it pins the outcome, and the claim-present and derived tests pin the skip; (vii) both `InternalError` messages use `sorted(named)` and name only the regions the action named.
- `deferred-work-ledger.md`, review pass 1 -- the DW-FU-8-5-5 `resolved:` line says `adopt` and `update` honour the opt-out set in their plan as well as at rung 6; DW-FU-11-4 gains one `verified: 2026-10-02 -- NARROWED -- ...` line (its status stays `NEEDS-DECISION`): the opted-out half is settled by Story 82.13 and only the `skips` half remains open.
- `seed/verbs/update.py` -- `run_update` drops `escaping_ids` records BEFORE `_managed_records` runs (filter `state.managed`, or pass `escaping_ids` in), so `_region_shas_for_record` never reads an escaping hybrid's path, for old-shape state too.
- `docs/managed-region-contract.md`, review pass 2 -- the 82.13 paragraph states: the opt-out holds region by region for state written by this release, while a state written before it attests to one region per artifact until the next applying run rewrites the record (`update` rewrites every declared region); a derived opt-out is recorded by the run that writes state, so an empty-plan run records nothing and the region stays derived while its claim matches the manifest path; the older-marshal break names its true remedy (upgrade that marshal; restoring the file only helps if you also restore the older marshal's own write) and drops the claim that re-running `adopt` recovers; there is no reinstate verb yet (Story 10.6), restoring the markers by hand makes the region present again, `update` records it and `adopt` refuses an artifact whose other regions are recorded with "present in the file but never recorded" until `--force` (pinned by the test below).
- Tests, review pass 2 -- (i) mutating `run_adopt(apply=True, yes=True)` and `run_update(run=True, yes=True)` over a state seeded through the old-shape helper (`_as_old_shape`, so the legacy `inserted_region_span` is what is on disk) whose only recorded region's markers are deleted, siblings present, no `--force`: the run completes, the markers stay absent, the written state holds the opt-out key, records every present sibling with its own offsets and hash, and a later `check` and `update --run` are clean; (ii) both regions of a two-region artifact deleted plus another artifact's non-empty apply, through each verb: the written state holds both keys and neither region is re-inserted; (iii) direct tests of both `_managed_artifact_after_apply` helpers: a named region absent after the write raises `InternalError` naming it although the replaced record carried others, and a claimed artifact with nothing present returns `None`; (iv) an escaping hybrid path with an old-shape state through `run_update`, with a spy on `_read_text_or_blank`, never read; (v) hand-restoring the markers after a recorded opt-out on a multi-region artifact, through both verbs, pins what each does (`update` records the region, `adopt` refuses at rung 6 without `--force`); (vi) `test_a_state_in_the_old_one_span_shape_is_rewritten_in_full_by_the_next_update` seeds the legacy shape through `_as_old_shape` and asserts the per-span hashes; the shipped-manifest opt-out test stops hard-coding `agents-md`'s 3 and `claude-md`'s 2 regions and asserts that some shipped hybrid entry declares more than one.
- `deferred-work-ledger.md`, review pass 2 -- the DW-FU-11-4 line added in pass 1 follows the row's own conventions: an em dash, the status vocabulary the other `verified:` lines use (`NEEDS-DECISION`), placed after the older `verified:` lines, citing a `path:line`; the row's `decision:` text is narrowed to the `state.skips` half, since Story 82.13 answers the opted-out half.
- `spec-pyforge-marshal` and `spec-pyforge-core` `.memlog.md` -- name every changed governed path (`python _bmad/scripts/memlog.py append`, one `--workspace` each), then run `python scripts/spec_surface_reconcile.py` and add any Spec it still names. Never `--write-baseline`.

**Acceptance Criteria:**
- Given a manifest entry whose id contains a space or `#`, when `load_manifest` runs, then it raises `ManifestError` whose text starts with that id and states the rule; a padded id (`" foo "`) still loads as `foo`.
- Given each id in the shipped `templates/manifest.yaml`, when `record_opt_out` runs for each of its regions and the state is written and read back, then it validates; and an id with a space is refused at the manifest, so the state never holds one (`managed[].id` with a space or `#` fails the schema as `StateInvalid`).
- Given state whose `opted_out` holds `<id>#<region>` (claim still present, or dropped) and a file whose markers for that region were deleted, when `run_adopt` or `run_update` runs without `--force`, then rung 6 raises nothing for that region; the same holds when nothing is recorded and the opt-out is only derived (claim present, markers gone). `run_init` passes `managed=()` and is unaffected. A second, hand-edited region of the same file still refuses.
- Given a hybrid artifact with two declared regions installed by `adopt`, when both regions' markers are deleted and detection runs, `opt_outs_to_record` is fed to `record_opt_out`, and the state is written and read back, then both regions classify `OPTED_OUT`, `state.opted_out` holds both keys, and `build_plan` plans no insertion for either.
- Given a fresh `adopt` of an artifact with three declared regions, when state is written, then `managed[]` holds one entry with three spans, each with its own `body_sha`, and a later `update` or `check` finds no divergence.
- Given a state file in the old one-span shape, when it is read, then it loads as a one-region list with the artifact's `body_sha`, and the next `write_state` emits `inserted_region_spans`.
- Given each fix reverted in turn, when its new test runs, then it fails.
- Given a DERIVED opt-out (claim present, markers deleted, nothing recorded) and a RECORDED opt-out, when `run_adopt(apply=True)` or `run_update(run=True)` runs without `--force`, then the deleted region's markers are still absent afterwards, the written state's `opted_out` holds its key, `managed[]` holds no span for it, and a surviving sibling region keeps its span and hash.
- Given a hybrid artifact with two declared regions of which one is opted out and one is present, when `run_update(run=True)` runs, then the present region is regenerated, the opted-out region is not re-inserted, and state records the opt-out exactly once.
- Given a hybrid artifact whose every declared region is opted out, when `update` plans, then no wholesale action names that artifact and its record is carried over.
- Given a hybrid entry whose path resolves outside the repo, when `adopt` or `update` runs, then its file is never read for opt-outs.
- Given a state in the OLD one-span shape whose only recorded region's markers were deleted while sibling regions are present, when `run_adopt(apply=True)` or `run_update(run=True)` runs without `--force`, then it completes, the markers stay absent, the written state holds the opt-out key and records every present sibling with its own hash, and nothing raises.
- Given a hybrid action that names a region which is absent from the file after the write, when state is built, then it raises `InternalError` naming that region even if the replaced record carried other regions.
- Given a replaced record whose every declared region is now absent from the file and an action naming none, when state is built, then the artifact has no record and the written state is valid.
- Given an old-shape state and a hybrid entry whose path resolves outside the repo, when `update` runs, then the escaped path is never read.

## Spec Change Log

### 2026-10-02 -- review pass 1 (bad_spec, iteration 1)

- **Triggering finding:** all four layers found, independently, that a mutating `adopt --apply` or `update --run` now
  re-inserts a region the operator deleted on purpose, where the baseline refused it at rung 6. Two of them reproduced it
  by running both verbs against a repo with deleted markers (a derived opt-out) and, for `update`, against a recorded
  opt-out beside a surviving sibling span. Verified in the diff: `run_adopt` and `run_update` hand `build_plan` only
  `frozenset(state.opted_out)`, `update._wholesale_regenerate_actions` names every declared region without reading any
  opt-out, and `_managed_artifact_after_apply` rebuilds a touched record from the file alone. Every new opt-out test is a
  dry run.
- **Root cause (outside the `<intent-contract>`):** the Design Notes ("Out of scope, tracked") and the Tasks left the plan
  side to another story (DW-FU-11-4, `NEEDS-DECISION`) and scoped the fix to rung 6. The contract does not: its Always
  bullet ("An opt-out stays permanent until an explicit reinstate"), its Approach, CAP-11 ("later runs respect it") and AC 4
  ("neither is planned for insertion") need the mutating verbs to hold the opt-out. Passing rung 6 without that turns an
  accidental refusal into a silent undo of FR-112, and per-region retention newly makes it reachable for a RECORDED
  opt-out on `update`. The Design Notes also said `seed_model_version` records which release wrote a state file; it reads
  the installed package version, `0.1.0` before and after, so it cannot.
- **Amended:** Code Map (verb ordering, the sequencing contract, DW-FU-11-4); Tasks (adopt and update record derived
  opt-outs in memory before they plan and give the plan and rung 6 one set; `update`'s wholesale pass honours it; the wire
  break stated honestly; mutating-run, escaping-entry and test-hygiene tests; ledger lines); four acceptance bullets;
  Design Notes (the wire-shape claim, replacing "Out of scope, tracked" with why rung 6 alone is not enough and with
  DW-FU-11-4's opted-out half). The `<intent-contract>` is unchanged. `baseline_revision` stays `dfd5482b46` so the next
  review diff is the whole story.
- **Known-bad state avoided:** excusing a deleted region at rung 6 without the plan honouring it (a silent re-insert of an
  opt-out, with no `--force` prompt); a derived opt-out that evaporates on the next state write because the touched
  record is rebuilt from the file; an opt-out key and a managed span coexisting for one region.
- **KEEP (worked in pass 1, must survive re-derivation; reference implementation: `git diff dfd5482b46 99cf0a50d8`):**
  - `ManifestEntry.id` rejects whitespace and `#` after the strip (`ARTIFACT_ID_PATTERN`); `state/schema.json`
    `$defs/artifactId` for `managed[].id` only; the `opted_out` description corrected; `legacy[]` ids untouched.
  - Per-region state: `RegionSpanRecord.body_sha`; `ManagedArtifact.inserted_region_spans` (non-empty iff hybrid, unique
    names, a hybrid's `body_sha` equals its first span's); the wire array `inserted_region_spans`; the schema `oneOf` the
    new key or the old read-only `inserted_region_span`; the old shape reads as a one-region list; `to_json_dict` always
    writes the new shape; `_without_region_claim` drops one span, and the entry only when none remain.
  - `detect/optout.py`: `_claims_region` over any span; `opted_out_regions(entries_and_texts, state)`.
  - `preconditions.py`: the `opted_out` keyword (a frozenset of pairs), excusing an ABSENT region only; it imports nothing
    from `seed.state`.
  - `adopt` and `update`: `region_shas` from every span; `_managed_artifact_after_apply` records every declared present
    region the action named or the replaced record (same path) carried; `check.py` checks every span against its own hash.
  - The pass-1 tests and mutation evidence (the new `test_seed_verbs_region_opt_out.py`, the retargeted tests), extended
    by the groups under Tasks.

### 2026-10-02 -- review pass 2 (bad_spec, iteration 2)

- **Triggering finding:** the Edge Case Hunter and the Verification Gap Reviewer each found, and reproduced by running both
  verbs, that a mutating `adopt --apply` or `update --run` over a state in the OLD one-span shape (every repo adopted before
  this story) whose only recorded region was deleted, with sibling regions still present, exits 10 after it has written:
  `InternalError: no managed region of 'HYBRID.md' was found to record immediately after the write (action named [])`.
  Verified by reading: `_state_with_opt_outs` records the derived opt-out, `store._without_region_claim` drops the artifact's
  record when its LAST span goes, `plan/build.py::_pendency` still keeps a hybrid `Action` with `chosen_anchor == ()` (nothing
  pending, but `retained`, the siblings, is non-empty), and `_managed_artifact_after_apply` then has `prior=None` (the record
  is gone from the in-memory state) and names nothing, so it records nothing and raises. Plan and other artifacts are written,
  state is not, and every retry and `--force` fails the same way; the baseline refused this state cleanly at rung 6 (exit 3).
  Every pass-1 test starts from NEW-shape state, where a sibling's span keeps the record alive.
- **Root cause (outside the `<intent-contract>`):** the Tasks defined the replaced record (`prior`) as the one in the state
  AFTER the in-memory opt-out recording, and let a hybrid record claim only regions the action named or that record carried.
  For an old-shape record the recording removes it whole, so there is nothing left to claim the siblings with. The contract's
  Approach reads the old shape as a one-region list, which makes it the common state, and the pass-1 Tasks and tests
  exercised only the new one.
- **Amended:** Code Map (the replaced-record rule, the escaping read in `update._managed_records`, the contract-page claims);
  Tasks (the rule below, restored per-region guard, the escaping read, six tests, the contract page, the DW-FU-11-4 line);
  four acceptance bullets; Design Notes. The `<intent-contract>` is unchanged. `baseline_revision` stays `dfd5482b46`.
  The rule: `_build_state_after_apply` takes the replaced records from the state AS READ (before the in-memory recording),
  `_managed_artifact_after_apply` claims every declared region present in the file when that record exists, raises only when
  the action named a region that is absent after the write, and returns no record at all (the artifact is no longer claimed)
  when nothing it could claim is present.
- **Known-bad state avoided:** an exit-10 crash after a partial write on the most common legacy state, caused by a lawful FR-112
  deletion; a hybrid record with no span (the store refuses it); sibling regions silently dropping out of management.
- **KEEP (worked in pass 2, must survive re-derivation; reference implementation: `git diff dfd5482b46 2d9ea56211`):**
  - Everything listed under pass 1's KEEP, unchanged.
  - `_state_with_opt_outs` in both verbs (derived opt-outs recorded in memory before the plan; ONE set for the plan, rung 6
    and the written state); `update._wholesale_regenerate_actions(..., opted_out)` skipping opted-out regions and an
    all-opted-out record; `detect.optout.opted_out_regions`; rung 6 excusing an ABSENT region only.
  - The tests added in pass 2 (`tests/unit/test_seed_verbs_region_opt_out.py`: mutating runs over derived and recorded
    opt-outs for both verbs, empty-plan writes no state, every-region-opted-out has no wholesale action, mutating `--force`,
    the escaping-hybrid read spy, the seam test) and their mutation evidence, extended by the groups under Tasks.

## Design Notes

- **Why each span carries its own `body_sha`.** Rung 6 compares a region body to a recorded hash per region (`ManagedRecord.region_shas` is already plural); with one artifact-level `body_sha` the sibling regions have nothing to compare against, which is why `update.py::_region_shas_for_record` invents "current" hashes for them. Recording a hash per span removes that invention for every state written from now on; it stays only for an old one-span state. The hybrid artifact's own `body_sha` is kept (required by the schema, read by nothing for hybrids) as the first span's, enforced, so it cannot disagree.
- **The wire shape.** A new key beside the old one, rather than a retyped `inserted_region_span`, keeps the old shape readable by name and keeps the `if/then/else` coupling honest. State written by this release is not readable by an older marshal (its schema has `additionalProperties: false`), and nothing in the file says which release wrote it: `seed_model_version` is the installed package version, which this story does not bump. The older marshal reports `state-invalid`. That is the cost of "writes the new shape", and `docs/managed-region-contract.md` says so.
- **The opt-out set is pairs, not keys.** `preconditions.py` must not import `seed.state` and must not re-spell the `<id>#<region>` key; `opt_outs_to_record` already returns plain pairs for the same reason. `opted_out_regions` goes through `classify_regions`, so a RECORDED opt-out (rung 2, no file needed) and a DERIVED one (rung 3, claim survives, markers gone) are one answer, and the verbs need no second spelling of either. A derived opt-out is the real FR-112 scenario: no mutating verb records one yet (`classify_regions`/`record_opt_out` have no verb caller), so a rung 6 that read `state.opted_out` alone would still refuse it.
- **Rung 6 skips only an ABSENT region.** A region the file still contains is hash-checked as before; `classify_regions` already says what is in the file wins over what state believes, so this never weakens detection of a modified region.
- **Why rung 6 alone is not enough.** Before this story rung 6 refused a repo with deleted markers, which blocked a re-insert by accident. Excusing the deletion there while the plan still builds from `state.opted_out` alone (and `update`'s wholesale pass names every declared region) turns that refusal into a silent undo of FR-112 with no `--force` prompt (review pass 1: four layers, two by running both verbs). Per-region retention makes it worse on `update`: a recorded opt-out no longer drops the whole entry when a sibling span remains, so the wholesale pass finds the entry and re-inserts the region. The opt-out set is therefore ONE set, read by the plan and by rung 6 alike, and a mutating verb records the derived pairs in memory before it plans (`detect/optout.py`'s sequencing contract). The recording is what makes a derived opt-out permanent: `_managed_artifact_after_apply` rebuilds a touched artifact's record from what is in the file, so a derived opt-out whose claim is rebuilt away would otherwise evaporate on the next write and the region come back a run later.
- **DW-FU-11-4's opted-out half.** That row asks whether `update`'s wholesale regenerate should refresh a region the operator opted out of. The contract answers it for opted-out regions (Always: permanent until an explicit reinstate; CAP-11: later runs respect it), so the wholesale pass honours the set. Its `skips` half is another question and stays `NEEDS-DECISION`.
- **What a rebuilt hybrid record claims.** `_build_state_after_apply` replaces a touched id's record outright, so the new one must carry what the old one attested to. An old-shape record names ONE region although `adopt` installed all of them in one action, so "the regions the replaced record carried" is too few: a deleted recorded region leaves nothing to name its present siblings (the pass-2 wedge, where the in-memory opt-out had dropped the record entirely). The replaced record is therefore read from the state AS READ, and its existence at the same `path` is what says the tool installed this file: every declared region present after the write is claimed, each at its current hash. A region a human put there is never claimed when no record existed. Under `--force` a sibling this run did not rewrite is adopted as it stands (the operator chose to discard hand-edits, and before this story that sibling was never recorded; `update` synthesised its current hash for rung 6 anyway). Nothing present and nothing named means no claim: every region was deleted, which is FR-112, not an error; a region the action NAMED and the file lacks is the real error (`insert_region` failed). `legacy[]` ids keep their grammar. The architecture spine, `epics.md` and `SPEC.md` still name `inserted_region_span` as the S-10.2 shape and are not edited here (a Spec is never hand-edited, and a spine edit ripples the planning chain); the stale wording is a recorded deferral.

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

### 2026-10-02 -- Review pass 1
- verdicts: 30 findings -- high 10, medium 7, low 10, false 3, maybe-false 0
- findings:
  - Blind Hunter
    - `[high]` `[bad_spec]` A mutating `adopt --apply` / `update --run` silently re-inserts a deleted region: rung 6 now passes a derived opt-out while `build_plan` gets only `state.opted_out` and `update`'s wholesale pass names every region; every new opt-out test is a dry run -- verified in the diff, and reproduced by two later layers running both verbs where baseline `dfd5482b46` refused at rung 6. Amendment: Tasks (derived opt-outs recorded in memory before planning, one set for the plan and rung 6, the wholesale pass honours it), the acceptance bullets, Design Notes.
    - `[medium]` `[bad_spec]` The ledger closes DW-FU-8-5-5 (high) while its headline scenario still contradicts for derived opt-outs, with no DW row for the residual -- verified: the pass-1 `resolved:` text and Auto Run Result admit it; it disappears once the verbs honour the set. Amendment: Tasks (the `resolved:` line states the plan honours the set).
    - `[low]` `[patch]` The wire format breaks under an unchanged `$id` and `seed_model_version` cannot tell releases apart -- verified: `pyproject.toml` version is `0.1.0` and `seed_model_version()` reads the installed version; the contract mandates the new shape, so the fix is to drop the false claim and document the break. Carried into Tasks (the contract page) and the Design Notes.
    - `[low]` `[defer]` AD-58 (`ARCHITECTURE-SPINE.md:1065`), `epics.md:2352` and `SPEC.md:1127` still name `inserted_region_span` -- verified by grep; the fix is a spine edit that ripples the planning chain (spine, then epics currency) and a Spec is never hand-edited. Recorded for the finalize pass.
    - `[low]` `[reject]` `_opted_out_pairs` and `_managed_artifact_after_apply` are copied between `adopt.py` and `update.py`, and each verb re-reads every hybrid file -- these modules mirror each other on purpose (`update` already says "Mirrors adopt's identical helper" for `_read_text_or_blank`), a shared home adds surface, and one more read of a handful of files costs nothing measurable.
    - `[false]` `[reject]` Under `--force` a hand-edited sibling is recorded at its current hash and goes silent -- before this change the sibling was never recorded, `update._region_shas_for_record` synthesised its current hash for rung 6, and `check` hashed only the one recorded span, so a hand-edit to a sibling was never reported; recording it adds protection for later edits, and `--force` means discard hand-edits.
    - `[medium]` `[patch]` `test_force_still_discards_a_hand_edit_beside_an_opt_out` is a dry run asserting only that nothing raises -- verified by reading it. Carried into Tasks (a mutating `--force` run with an outcome assertion).
    - `[low]` `[patch]` Two tests are brittle: `"opted_out" not in kwargs` pins an incidental call shape, and the import-walk guard misses `from .. import state` -- verified. Carried into Tasks.
    - `[low]` `[reject]` A hybrid's `body_sha` is a denormalised copy of its first span's -- the schema requires `body_sha` for every class and the old shape's read path supplies it; deriving it changes the wire contract this story keeps stable, and the invariant is enforced and tested once.
    - `[medium]` `[bad_spec]` `managed-region-contract.md` says deleting some markers opts out exactly those regions and that `adopt`/`update` do not refuse it, and hard-codes the region count of `AGENTS.md` -- true only once the plan honours the set (same root cause as the first row). Amendment: Tasks (the contract page states the verified mutating-run behaviour, no hard-coded count).
    - `[low]` `[reject]` The grammar pin's probe set has no non-ASCII or control whitespace -- the schema is only validated by Python `jsonschema`/`re` in-process (`store._validator`), and Python's `\s` on a `str` is `str.isspace()`, the test `_require_text` strips with, so the three spellings cannot diverge; more probes buy nothing.
    - `[low]` `[patch]` The `InternalError` message in `adopt._managed_artifact_after_apply` has a redundant list comprehension and says "action named" for names carried from the prior record -- verified. Carried into Tasks.
  - Edge Case Hunter
    - `[high]` `[bad_spec]` `update --run` re-inserts a RECORDED opt-out when a sibling span keeps the entry alive: the wholesale pass names every declared region and never reads the set (probe confirmed by two layers; at baseline `record_opt_out` dropped the whole entry, so `update` skipped the artifact) -- a regression this change introduces on the recorded path. Amendment: Tasks (the wholesale pass honours the set) and the acceptance bullets.
    - `[high]` `[bad_spec]` A derived opt-out reaches `build_plan` and the wholesale pass unrecorded; record it before planning -- same root cause and amendment as the first row.
    - `[medium]` `[bad_spec]` The contract page claims opt-outs hold under `update --run` -- false until the wholesale pass honours the set. Amendment: same as the contract-page row above.
    - `[medium]` `[bad_spec]` The closed DW-FU-8-5-5 row's residual is understated: it names only the derived path, while the recorded `update` path regresses too -- verified by the probe in the first row of this layer. Amendment: Tasks (ledger line).
    - `[high]` `[bad_spec]` The contract's "an opt-out stays permanent until an explicit reinstate" is not delivered for `update --run` -- same defect as the first row of this layer; the spec's scoping, not the intent, left it out.
    - `[low]` `[patch]` An older marshal reading new state fails with a generic `StateInvalid` and no hint -- same finding, verdict and carry as the wire-format row above.
    - `[false]` `[reject]` Existing state with a whitespace-or-`#` `managed[].id` becomes unreadable with no migration -- the contract's Approach states this outcome ("a state file carrying such an id reads as `state-invalid`"), and no manifest id in the fleet carries one.
    - `[low]` `[defer]` AD-58 text in the spine and `SPEC.md` still names the old field -- same finding and disposition as the AD-58 row above.
  - Verification Gap
    - `[high]` `[bad_spec]` Mutating `adopt --apply` / `update --run` over an opt-out is unverified and rung 6 no longer stops it; the retargeted adopt tests no longer pin a marker deletion -- pre-verified by the layer (it ran both verbs). Amendment: the acceptance bullets and Tasks (mutating-run tests for both verbs over derived and recorded opt-outs).
    - `[medium]` `[patch]` The escaping-entry guard in both `_opted_out_pairs` helpers has no test: removing it left 1854 unit tests green -- pre-verified by the layer. Carried into Tasks (an escaping hybrid entry through both verbs with a read spy, Story 82.11).
    - `[high]` `[bad_spec]` (other) A derived opt-out is not passed to `build_plan`; baseline refused, the change re-inserts -- same defect and amendment as the first row of this log.
    - `[high]` `[bad_spec]` (other) `update --run` after a recorded opt-out leaves both an `opted_out` key and a managed span for the region -- same defect as the edge-case row on the recorded path. Amendment: an acceptance bullet requires the key and no span.
  - Intent Alignment
    - `[medium]` `[bad_spec]` AC 3 is exercised only by non-mutating library calls, with no mutating-run or CLI-level test -- same gap and amendment as the verification-gap row.
    - `[high]` `[bad_spec]` AC 4's "detection runs and the state is written and read back" happens only in a hand-composed test; no verb records a derived opt-out and `adopt` feeds `build_plan` only `state.opted_out` -- the root of the first row. Amendment: Tasks (the verbs apply the sequencing contract).
    - `[high]` `[bad_spec]` `update`'s recorded opt-outs clear rung 6 while the plan still names the region (DW-FU-11-4) -- same as the edge-case recorded-path row. Amendment: Tasks (wholesale pass) and the DW-FU-11-4 note.
    - `[high]` `[bad_spec]` Net change on the mutating path: the rung-6 refusal that blocked a re-insert by accident is gone and the run re-inserts, on a path no new test exercises -- same as the first row.
    - `[low]` `[patch]` `test_a_recorded_opt_out_with_its_claim_dropped_is_not_refused_without_force` passes without the rung-6 skip, since the dropped claim leaves nothing for rung 6 to compare -- verified by reading it; the claim-present and derived tests cover that mutant, so it is a weak pin, not a coverage gap. Carried into Tasks (its docstring says what it pins).
    - `[false]` `[reject]` The retargeted adopt tests (`--skip`, re-apply) edit a region body instead of deleting markers -- that is the intended consequence of the story (a marker deletion is no longer a rung-6 refusal); the refusal they keep is on a hand-edited body, which still refuses.

### 2026-10-02 -- Review pass 2
- verdicts: 27 findings -- high 4, medium 4, low 17, false 1, maybe-false 1
- findings:
  - Blind Hunter
    - `[low]` `[patch]` An old-shape state keeps the one-region limit until its next write, and the contract page's "opts out exactly those regions" says nothing of it -- verified: `detect/optout.py` already says the old limit holds until the next write; a doc overclaim, not a code defect. Carried into Tasks (the contract page).
    - `[low]` `[patch]` The older-marshal downgrade remedy is circular (restoring from version control returns the same file; `run_adopt` reads state unguarded and does not downgrade `StateInvalid`), and the break has no version marker -- verified by reading `run_adopt`; the marker is the contract's own choice (the new shape is written, `$id` stays), so the fix is the true remedy in the doc. Carried into Tasks (the contract page). Same finding as the Verification Gap's doc-remedy row.
    - `[low]` `[defer]` `--reinstate` is advertised (`finding-remedy-reference.md`, `adoption-guide.md`, the contract page) though no verb declares it -- pre-existing: the flag is Story 10.6's surface and DW-FU-8-5-4 tracks the missing `clear_opt_out` caller. This story's paragraph states the manual path (Tasks). Named blocker: Story 10.6.
    - `[medium]` `[patch]` Hand-restoring markers after a recorded opt-out is untested and `adopt` and `update` disagree on it (`adopt` builds `region_shas` from recorded spans only and refuses with "present in the file but never recorded"; `update` synthesises the current hash) -- verified in `adopt._managed_records` and `update._region_shas_for_record`; newly reachable because a sibling span now keeps the record alive. The verb-level reinstate is Story 10.6; the smallest fix is a test pinning both behaviours and the doc line. Carried into Tasks.
    - `[low]` `[patch]` A derived opt-out is persisted only by a run that writes state, so an empty-plan run leaves it derived and a later manifest path move would resurrect the region -- verified against the spec's own Tasks ("as today"); the contract page promises permanence without the condition. Carried into Tasks (the contract page states it).
    - `[low]` `[reject]` Mutating runs record a permanent opt-out without naming it, and a file replaced by unrelated content reads as a deliberate opt-out -- rung 3 is Story 8.5's own derivation (FR-112: deleting the markers IS the opt-out; `check` already reports it as `opted-out` INFO and the confirm prompt shows a plan with no insertion); the recording is what the module's sequencing contract asks a verb to do, and a result field adds public surface for a low-likelihood case.
    - `[low]` `[defer]` carried: AD-58 in `ARCHITECTURE-SPINE.md:1065`, `epics.md:2352` and `SPEC.md:1127` still name `inserted_region_span`; the `epics.md` Story 82.13 body predates the plan-side scope -- a spine and epics edit ripples the planning chain and a Spec is never hand-edited; recorded under `deferred` at finalize.
    - `[low]` `[patch]` The DW-FU-11-4 `verified:` line uses ASCII `--`, a status outside the row's vocabulary and an order the other multi-`verified:` rows do not use, and the row's `decision:` text is stale -- verified against the ledger. Carried into Tasks (the ledger line).
    - `[low]` `[patch]` `test_a_state_in_the_old_one_span_shape_is_rewritten_in_full_by_the_next_update` builds its "old shape" with `dataclasses.replace(..., inserted_region_spans=spans[:1])`, which `write_state` writes in the NEW shape, and asserts names only -- verified by reading it. Carried into Tasks.
    - `[low]` `[patch]` A shipped-manifest test hard-codes `agents-md` 3 and `claude-md` 2 regions and breaks on a legitimate manifest change -- verified. Carried into Tasks.
    - `[maybe-false]` `[reject]` The "equivalent mutant" claim for F15 is shown only for a hybrid entry -- the reviewer names no concrete mutant; for a same-id whole-file claim `remaining` and `inserted_region_spans` are both empty, so `_without_region_claim` keeps it, and `test_record_opt_out_leaves_a_whole_file_claim_on_the_same_id_untouched` exists. Evidence-text only, low if true.
    - `[low]` `[reject]` The spec cites an auto-checkpoint SHA as its durable reference and transient mutants sit in branch history -- the checkpoints are the harness's own on every dispatch branch (the base history carries many `wip: ... (auto-checkpoint)` commits); the SHA is a re-derivation aid within this run, not a durable reference.
    - `[low]` `[reject]` carried: `_state_with_opt_outs` and `_managed_artifact_after_apply` are near-copies in `adopt.py` and `update.py` and no longer identical -- they differ on the guarded read (`update` reads through `_read_materialized_text`) before this story; the verbs mirror each other on purpose and a shared home adds surface.
  - Edge Case Hunter
    - `[high]` `[bad_spec]` An old-shape state whose only recorded region was deleted makes `adopt --apply`/`update --run` exit 10 after writing, state never written, repeating on every run -- verified by reading (`_without_region_claim` drops the record, `_pendency` keeps an `Action` with `chosen_anchor == ()`, `prior=None`, nothing named) and reproduced by two layers; baseline refused at rung 6. Amendment: Tasks (the replaced-record rule, a `None` record) and the acceptance bullets.
    - `[high]` `[bad_spec]` The AC "derived opt-out, apply run, markers stay absent and state holds the key" does not hold for that state; the "next update rewrites old state in full" claim is wrong for it -- same defect and amendment as the row above.
    - `[medium]` `[patch]` Pass 1 removed the per-region `InternalError` ("region ... not found immediately after insertion"): the check now fires only when NO region is recorded, so a failed insert goes unreported when a prior record carries others -- verified in both `_managed_artifact_after_apply` helpers. Carried into Tasks (restore the check for every region the action names).
    - `[medium]` `[patch]` `update._managed_records` runs before the `escaping_ids` filter and `_region_shas_for_record` reads the file for any declared region with no recorded span, so an old-shape state with an escaping hybrid reads the escaped path -- verified by reading `run_update` (the filter follows the call) and by the layer's spy; narrower than at baseline (a fully recorded new-shape state reads nothing) but Story 82.11's invariant is "never read". Carried into Tasks.
  - Verification Gap
    - `[high]` `[bad_spec]` A mutating `adopt --apply`/`update --run` over a pre-82.13 one-span state whose recorded region was deleted is untested; no test starts from a state whose only recorded span is the deleted one while a sibling is present -- pre-verified (the layer ran both verbs). Amendment: the first acceptance bullet and Tasks test (i).
    - `[high]` `[bad_spec]` (other) The defect behind that gap: a lawful FR-112 deletion in the most common legacy shape turns an exit-3 refusal into an exit-10 crash with a half-applied repo, behind a misleading "broken installation" remedy -- same defect and amendment as the first Edge Case row.
    - `[low]` `[patch]` (other) The contract page's older-marshal remedy ("re-runs `marshal seed adopt`") cannot work because `run_adopt` reads state unguarded -- same finding, verdict and carry as the Blind Hunter downgrade row.
  - Intent Alignment
    - `[low]` `[reject]` AC 3 and AC 4 are tested through the verb functions and the library, with no `cli/seed.py` argv test -- the CLI wrappers parse argv and call the same `run_*` functions (`test_seed_cli_seed_update.py` already pins the argv path); the contract's surface is the verb behaviour, so a CLI-level duplicate adds no protection.
    - `[low]` `[reject]` In the verbs the rung-6 skip never decides the outcome, because the derived pair is recorded (the claim dropped) before the records are built; two tests say so in their docstrings -- true and intended: the skip is a gate for any state that holds both the key and the claim (a hand-written or pre-recording one), pinned at the seam and by the claim-present verb test, and a mutant ignoring the set is killed there.
    - `[low]` `[reject]` `init` is unchanged and its only new test is a spy on `managed=()` -- `init` reads no state and passes `managed=()`, so rung 6 has no record to excuse; the spy pins that, and there is nothing for `init` to honour.
    - `[medium]` `[patch]` No test shows a verb writing, to disk, a state with BOTH deleted regions opted out (the nearest verb test asserts that an empty plan writes no state; the both-deleted test composes the library by hand) -- verified by reading the tests. Carried into Tasks test (ii).
    - `[low]` `[reject]` The diff adds per-span `body_sha`, the `check.py` change, the DW-FU-11-4 line, a `--force` reversal and a contract paragraph beyond the intent's text -- each follows from it: per-region state needs a per-region hash, `check` must read every span, the wholesale pass is the path that would re-insert an opted-out region, and a deleted region staying deleted under `--force` is what "permanent until an explicit reinstate" means. Descriptive, not a defect.
    - `[low]` `[reject]` The tests that fail when the rung-6 skip is reverted are the seam and claim-present tests, not the production-shaped verb tests -- the same fact as the rung-6 row above; the mutation criterion is met (a mutant ignoring the set is killed).
    - `[false]` `[reject]` The cited green runs are the author's own and were not re-run -- they were re-run by the orchestrator from the run worktree with exit codes read directly (`pyforge-marshal-test` 10784 passed, `pyforge-deps-test` 130 passed, `lint-types` 0, `spec_surface_reconcile.py` 0).

## Auto Run Result

Pass 2 was reviewed and sent back (`bad_spec`, iteration 2): see the Spec Change Log. The pass-2 result is superseded; the next pass rewrites this section.
