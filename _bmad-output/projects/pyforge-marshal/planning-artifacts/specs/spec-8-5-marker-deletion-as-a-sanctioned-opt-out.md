---
title: 'Story 8.5: Marker deletion as a sanctioned opt-out'
type: 'feature'
created: '2026-08-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
baseline_revision: '4397583a7687c989086673c1ac82cea94a531238'
final_revision: '331da09bcbb8bcf59da25dffc796036fd08bfea1'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md'
warnings: ['oversized']
difficulty: 'heavy'
---

<intent-contract>

## Intent

**Problem:** A maintainer who deletes a managed region's markers is today indistinguishable from
one who never had the region: `detect.inventory._classify_hybrid` collapses both to
`PRESENT_DIVERGENT`, `plan.build._chosen_anchor` schedules a re-insert for both, and nothing
consumes `state.opted_out` (shipped empty by S-10.2). FR-112 requires deletion to be a
*permanent, recorded* opt-out the tool thereafter respects.

**Approach:** Add the one join nothing owns yet -- a pure per-region classifier in `detect/` that
reads parsed spans plus recorded state and answers `PRESENT` / `OPTED_OUT` / `MISSING` -- backed
by an opt-out record API on `state/store.py`, and honoured by `build_plan` so an opted-out region
never becomes an insert action.

## Boundaries & Constraints

**Always:**
- `seed/state/store.py` gains four pure functions over the ALREADY-SHIPPED `opted_out` key (no
  twelfth state key; the eleven-key invariant and `schema.json` are untouched):
  `opt_out_key(artifact_id: str, region: str) -> str` renders `f"{artifact_id}#{region}"` and
  raises `ValueError` when the result does not match the packaged schema's own
  `properties.opted_out.items.pattern` (read via the existing `_load_schema()`, never a
  second hand-copied pattern, and never an import from `regions.markers` -- `store.py`'s import
  surface is AST-guarded); `is_opted_out(state, artifact_id, region) -> bool`;
  `record_opt_out(state, artifact_id, region) -> SeedState`; and
  `clear_opt_out(state, artifact_id, region) -> SeedState`. Both mutators are pure
  (`dataclasses.replace`, never in-place), idempotent, and keep `opted_out` sorted so two runs
  recording the same pairs in different orders write byte-identical state. All four are
  re-exported from `seed/state/__init__.py` (`__all__` kept sorted, matching the existing list).
- `record_opt_out` ALSO drops the artifact's `managed[]` claim for that region -- the
  `ManagedArtifact` whose `id == artifact_id` and whose `inserted_region_span.name == region`.
  Relinquishing the claim is what makes `clear_opt_out` real: leaving it would let the
  derivation below immediately re-derive the opt-out, so reinstate could never take effect.
  (`ManagedArtifact`'s span-present-iff-hybrid invariant forbids nulling the span in place, so
  the whole entry goes.)
- `seed/detect/optout.py` (NEW) owns the join. `RegionDisposition(StrEnum)` =
  `PRESENT`/`OPTED_OUT`/`MISSING` (kebab wire values, matching `ArtifactState`/`FindingType`);
  frozen `RegionStatus(artifact_id, path, region, disposition)`;
  `classify_regions(entry: ManifestEntry, text: str, state: SeedState | None) -> tuple[RegionStatus, ...]`
  in declared-region order; `region_findings(statuses) -> tuple[Finding, ...]`. Per declared
  region, in this order: name among `parse_regions(text, entry.format)` -> `PRESENT`; else
  `is_opted_out(state, entry.id, name)` -> `OPTED_OUT` (recorded opt-outs are sticky and survive
  the managed claim being gone); else state carries a `managed[]` entry for `entry.id` whose
  `inserted_region_span.name == name` -> `OPTED_OUT` (installed once, markers now deleted); else
  `MISSING`.
- `classify_regions` returns `()` for a non-`HYBRID_MANAGED_REGION` entry, and degrades to `()`
  on `RegionParseError`/`MarkerError`/`NotImplementedError` -- the identical "cannot safely
  re-parse, degrade rather than guess" rule `_classify_hybrid`/`_chosen_anchor` already apply.
  A structural defect must never retire a region.
- `region_findings` emits `Severity.INFO` + `FindingType.OPTED_OUT` for `OPTED_OUT`,
  `Severity.DRIFT` + `FindingType.MANAGED_REGION_MISSING` for `MISSING`, nothing for `PRESENT`.
  Built with `Finding.new` (never bare `Finding(...)`), message shaped `f"{path}#{region}: ..."`
  to match `detect/hashes.py`'s existing region-message convention. These are the first emitting
  call sites either type has ever had.
- `seed/detect/findings.py`'s `REMEDIES[FindingType.OPTED_OUT]` is corrected to name the real
  mechanism (`marshal seed adopt --reinstate <artifact>#<region>`) instead of the current
  "remove the skip glob from state", which points at the unrelated `state.skips` mechanism
  (PRD J4 lists opt-out and `skips[]` as distinct moves) and describes a glob that does not exist.
- `seed/plan/build.py` honours opt-outs without performing state I/O: `build_plan` gains a
  keyword-only `opted_out: frozenset[str] = frozenset()` of already-read
  `opt_out_key(...)` strings, threaded into region resolution. A HYBRID entry whose pending
  regions (declared, minus present, minus opted-out) are empty produces NO `Action` at all --
  for `PRESENT_DIVERGENT` and `ABSENT` alike -- and therefore no `artifact_hashes` entry.
  An unparseable file is never "zero pending" and keeps its `Action`. `chosen_anchor` lists only
  pending regions. `build.py` imports `opt_out_key` from `..state` (a legal downward edge) so
  the key is spelled once; its module docstring's stale "`seed/state/` is an empty stub" Never
  bullet is amended to the true, narrower claim: no state READ here, the key set is a parameter.

**Block If:** None -- FR-112, the epics AC, and the already-shipped S-8.4/S-9.x/S-10.2 primitives
fully determine this story; no decision requires human input.

**Never:**
- No CLI work. `--reinstate` is not declared as an argparse flag here: `cli/seed.py` is six
  print-only stubs with zero `add_argument` calls, and the flag belongs to S-10.6 (`adopt`, the
  mutating verb that "reinserts on the next apply"), with its cross-verb contract in S-12.5.
  This story ships the mechanism that flag will call.
- No new state key, no `schema.json` edit, no state-schema migration.
- No `eject` verb (AD-58 defers it to V1.x); no change to `regions/apply.py` (marker *removal* is
  the maintainer's own hand-edit, never something Genesis performs).
- No edit to `detect/inventory.py` or `detect/hashes.py` -- their per-file `ArtifactState` and
  their "no state read" boundaries stay exactly as shipped; the new per-region granularity lives
  beside them, not inside them.
- `detect/optout.py` never writes: it classifies and reports. Recording is `record_opt_out`
  returning a new `SeedState` for a future verb to persist via the existing `write_state`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Markers deleted (the AC's first test) | State has a `managed[]` entry for the artifact with `inserted_region_span.name == "tiers"`; file no longer contains the markers | `OPTED_OUT`; one INFO `opted-out` Finding | No error |
| Never installed (the AC's second test) | File never had the region; `state is None` or state has no managed record and no opt-out | `MISSING`; one DRIFT `managed-region-missing` Finding | No error |
| Already recorded | `state.opted_out` contains `"agents-md#tiers"`, no managed claim remains | `OPTED_OUT` (sticky) | No error |
| Region present | `parse_regions` finds the name | `PRESENT`; no Finding | No error |
| Unparseable file | Text has an unterminated region or fence | `classify_regions` returns `()`; the entry keeps its `Action` | Exception swallowed, degrade to `()` |
| Non-hybrid entry | `artifact_class` is not `hybrid-managed-region` | `()` | No error |
| Plan suppression | `PRESENT_DIVERGENT` hybrid whose only missing region is opted-out | No `Action`, no `artifact_hashes` entry | No error |
| Partial opt-out | Two declared regions, one opted-out, one missing | One `Action`; `chosen_anchor` names only the missing one | No error |
| Reinstate round-trip | `record_opt_out` then `clear_opt_out` | State equals the original minus the dropped `managed[]` entry; region re-classifies `MISSING` and is planned for insertion | No error |
| Malformed pair | `opt_out_key("a b", "tiers")` or `opt_out_key("agents-md", "Tiers")` | Raises | `ValueError` naming the offending pair |
| Idempotence | `record_opt_out` twice, or `clear_opt_out` on an absent pair | Second call returns an equal `SeedState` | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/state/store.py` -- MODIFY: add
  `opt_out_key`, `is_opted_out`, `record_opt_out`, `clear_opt_out` after `state_path`. No new
  key, no import added (`_load_schema` is already in this module).
- `.../seed/state/__init__.py` -- MODIFY: re-export the four, in sorted `__all__`.
- `.../seed/detect/optout.py` -- NEW: `RegionDisposition`, `RegionStatus`, `classify_regions`,
  `region_findings`. Imports `..model.manifest`, `..regions.parse`, `..regions.markers`,
  `..state`, `.findings` -- all legal downward edges.
- `.../seed/detect/findings.py` -- MODIFY: one string, `REMEDIES[FindingType.OPTED_OUT]`.
- `.../seed/plan/build.py` -- MODIFY: `build_plan`'s keyword-only `opted_out`, pending-region
  computation, hybrid zero-pending suppression, docstring amendment.
- `.../seed/detect/hashes.py`, `.../seed/detect/inventory.py`, `.../seed/regions/parse.py`,
  `.../seed/regions/apply.py` -- REFERENCE ONLY (message shape, degrade rule, `parse_regions`).
- `.../tests/unit/test_seed_state_store.py` -- MODIFY: the four helpers, including the malformed
  pair, idempotence, sorted-and-deduped `opted_out`, and the `managed[]` claim drop.
- `.../tests/unit/test_seed_detect_optout.py` -- NEW: every classification and finding row above,
  led by the AC's two contrasting tests.
- `.../tests/unit/test_seed_detect_findings.py` -- MODIFY: the corrected `OPTED_OUT` remedy.
- `.../tests/unit/test_seed_plan_build.py` -- MODIFY: suppression, partial opt-out, unparseable
  file keeps its action, and the default `opted_out=frozenset()` leaving existing behavior
  byte-identical.

## Tasks & Acceptance

**Execution:**
- [x] `seed/state/store.py` -- add the four opt-out functions; `opt_out_key` validates against
  the packaged schema's own pattern; `record_opt_out` appends (sorted, deduped) and drops the
  matching `managed[]` claim; `clear_opt_out` removes the pair.
- [x] `seed/state/__init__.py` -- re-export all four.
- [x] `seed/detect/optout.py` -- NEW: the four-rung classifier and the two-finding emitter, with
  the non-hybrid and parse-failure degrade guards.
- [x] `seed/detect/findings.py` -- correct the `OPTED_OUT` remedy to name `--reinstate`.
- [x] `seed/plan/build.py` -- thread `opted_out` through pending-region computation; suppress a
  hybrid entry's `Action` when nothing is pending; amend the stale Never bullet.
- [x] `tests/unit/test_seed_state_store.py` -- cover every store row of the I/O Matrix.
- [x] `tests/unit/test_seed_detect_optout.py` -- NEW: cover every classification/finding row,
  the AC's two contrasting tests first.
- [x] `tests/unit/test_seed_detect_findings.py` -- update the remedy assertion.
- [x] `tests/unit/test_seed_plan_build.py` -- cover suppression, partial opt-out, unparseable
  passthrough, and default-argument behavior preservation.

**Acceptance Criteria:**
- Given a repo where a previously-present managed region's markers have been deleted, when
  detection runs, then the region is classified `opted-out` and never `managed-region-missing`.
- Given that classification, when findings are emitted, then the opt-out reports at `INFO`
  severity and never `HARD` or `DRIFT`.
- Given an opt-out recorded in state, when a plan is built for a later run, then the region
  produces no insert action, so it is never reinserted.
- Given an opt-out cleared by `clear_opt_out`, when a plan is built, then the region is planned
  for insertion again -- the `--reinstate` path S-10.6 will call.
- Given a state document written after `record_opt_out`, when it is read back, then it round-trips
  through the existing schema unchanged and still carries exactly eleven top-level keys.
- Given the default `opted_out=frozenset()`, when `build_plan` runs, then its output is identical
  to the pre-story behavior for every existing case.

## Spec Change Log

### 2026-08-20 — Dev attempt 2: foreign spec-surface reconciliation (no intent change)

Attempt 1's implementation was complete and correct -- all nine tasks landed in
`e0e4321d3d`, and all three of the loop's verify commands pass on it *except*
`python scripts/spec_surface_reconcile.py`, which returned rc=1 on six
`ungoverned` findings. **None of the six belongs to this story.** They are the
conda-forge packaging-inventory operations quartet, added on `main` in
`0f0b75232e` / `9de01865ce` / `4397583a76` -- the last of which IS this story's
own `baseline_revision`, so every one of them predates the story commit. The
story's diff (9 files, all under `src/shared/packages/pyforge-marshal/`) has
zero path overlap with them.

The gate is repo-level and emits a single exit code, so "pre-existing, not
ours" is true but unlandable: the loop cannot proceed until rc=0. Reconciled by
adding six per-file entries to `scripts/spec_surface_allowlist.txt`.

Why the allowlist and nothing else:

- `ungoverned` is a **coverage** verdict computed live from spec surfaces plus
  the allowlist. `scripts/spec_surface_check.py --write-baseline` records
  **drift** state only and cannot clear a coverage finding, so no baseline was
  stamped and none would have helped. `scripts/.spec-surface-baseline.json` is
  untouched.
- No `surface:` can claim these paths today. A Tier-0 Dream exists
  (`docs/dreams/conda-forge-packaging-inventory-operations.md`, `status:
  dreamt`, `owner: atlas`) but has produced no Spec, and `SPEC_GLOB` only
  discovers `_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md`.
  Authoring that Spec is Dream->Spec chain work, not this story's.
  Precedent: `spec-surface-drift-reconciliation`'s own retired `assumptions:`
  entry, where the two `[ungoverned]` Charter files were allowlisted for the
  structurally identical reason.
- **Six exact per-file patterns, no glob.** The allowlist's own `scripts/`
  header records why the blanket `scripts/**` glob was split per-file on
  2026-08-08: `allow_hits` only reports a pattern matching *nothing*, so a
  too-broad glob is invisible by construction and silently absorbed 20 files,
  six of them detectors. A `conf/**` or
  `scripts/conda-forge-packaging-inventory-operations*` glob would re-introduce
  exactly that defect. Per-file keeps a future seventh file in this quartet a
  finding rather than a silent exemption.
- Each reason is written from the file's real module docstring and its real
  consumer, and states the exemption is NOT ownership -- deletable the moment
  that Dream's Spec declares a surface.

`scripts/spec_surface_allowlist.txt` is itself allowlisted ("the allowlist
cannot govern itself"), so this edit governs nothing and moves no contract
hash: no `.memlog.md` and no baseline required stamping.

**Intent contract untouched.** No file named in the Code Map was modified in
this attempt; the sole diff is the allowlist. Verification after the repair:
`pyforge-marshal-test` 4796 passed / 9 deselected, `pyforge-deps-test` 84
passed, `spec_surface_reconcile.py` rc=0 ("every tracked file governed or
allowlisted; no drift"), with no new `stale-allowlist` finding.

## Review Triage Log

### 2026-08-20 — Review pass 5 (follow-up review of a `done` spec)
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 1, medium 3, low 5)
- defer: 1
- reject: 9
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same root cause):
    `plan/build.py::_pendency`'s `retained` -- pass 4's own fix for the consent gate --
    measured "in the file" with `parse_regions`, the narrower question
    `detect/optout.py::marker_region_names` was added one layer up to stop asking. So a
    region sitting in the file inside a closed ``` fence, or one whose marker lines had
    picked up a trailing space, landed in `not_present`, `retained` came back `()`, and a
    fully-keyed entry was suppressed out of BOTH `actions` and `artifact_hashes`: the live
    region left the `RepoFingerprint` and `fingerprint_drift` reported `()` after its body
    was tampered with. This is the third consecutive pass in which the same defect --
    consent inferred rather than measured -- survived its own repair by being fixed at one
    call site and not its mirror, and it put the two layers back in the flat contradiction
    pass 4 closed (rung 1 answers `PRESENT` for that same region). Reachable by opting a
    region out and then running a formatter over the file. Fixed: `_marker_region_names` is
    promoted to public `marker_region_names` and `build.py` imports it (`plan -> detect` is
    a precedented edge -- the module already imports `detect.hashes`/`detect.inventory` --
    and a copy of the scan is what this story's Always bullets forbid); only `retained` is
    widened, never `pending`, since a region the parser cannot see is one an insertion
    still owes. Two parametrized regression tests plus a control proving genuinely-deleted
    markers are still suppressed; confirmed real by reverting the clause and watching both
    fail while the control passed.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, two routes to one
    root cause): `opt_outs_to_record` returned EVERY `OPTED_OUT` pair, rung 2's recorded
    ones included, on the stated argument that telling them apart would be "a second
    spelling of rung 2" and that `record_opt_out` is idempotent anyway. Both halves were
    false: asking rung 2's OWN function is not a second spelling of it, and the mutator is
    idempotent in the `opted_out` KEY while unconditional in the `managed[]` claim it
    drops. So feeding a rung-2 pair back through the module's own documented verb loop
    discarded a claim that was still standing, in exactly the two cases the rung-3 gates
    refuse to derive from -- a region physically present but invisible to `parse_regions`
    (its `body_sha` gone with the claim), and an entry whose manifest `path` had moved
    since the claim was recorded, where the path-blind `store.py::_without_region_claim`
    drops the claim describing the region still installed at the OLD path. Fixed:
    `opt_outs_to_record(statuses, state)` returns the DERIVED pairs only; a recorded pair
    needs no recording and is already in the key set the verb hands `build_plan`, so the
    sequencing contract loses nothing. Three tests; confirmed real by reverting the filter.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same root cause):
    `build_plan`'s `opted_out` element guard -- pass 3's own fix for the silent-suppression
    hazard -- tested only `isinstance(key, str)`, so every malformed key STRING sailed
    through, matched nothing and suppressed nothing: the identical silent failure, reached
    by the likelier input. `{'h#Tiers'}`, `{'h tiers'}` and a bare `{'h'}` were all accepted
    with no error at any layer, re-inserting a region FR-112 says must never be re-inserted.
    Fixed: a sixth public helper `state.is_opt_out_key` (the ASKING half for a key that
    arrives whole, where `opt_out_key_or_none` is the asking half for a pair in two pieces)
    keeps the grammar in one place, and the guard uses it. Four parametrized tests; confirmed
    real by reverting to the type test. Two honest limits recorded rather than papered over:
    the guard stops at the GRAMMAR, so the path form `region_findings` prints beside the key
    (`CLAUDE.md#tiers`) is itself grammatical and passes -- matching against `entries_by_id`
    would catch it but hard-fail the documented natural call on an orphaned key nothing
    prunes -- and one pre-existing test had to be re-fixtured because it asserted the
    inadmissible-element acceptance this finding is about.
  - `[medium]` `[patch]` Blind Hunter: `marker_region_names`'s docstring claimed
    "Over-detection here is free". It is not. Confirmed by execution: an indented Markdown
    code block demonstrating the marker grammar -- which `parse_regions` skips by design and
    `str.strip()` normalizes straight into recognition -- puts the region's own name in the
    scan on every run, so rung 3 can never fire for that artifact and marker deletion, the
    story's entire premise, is silently unavailable there with no diagnostic. The trade is
    still the right way round (under-detection retires a LIVE region), so the direction
    stands and the claim is corrected: over-detection is CHEAP, not free, with the failure
    it buys named. The mechanism is `DW-FU-8-5-11`.
  - `[low]` `[patch]` Edge Case Hunter: `_current_text` and `_read_text_or_blank` had zero
    call sites anywhere in `src/` or `tests/` -- pass 4 rewired every consumer onto the
    `_verbose` variants and left both wrappers standing, each calling its own `_verbose`
    twin and discarding the second value for nobody. Dead surface in a module that argues
    against speculative surface. Fixed: both removed, their docstrings' load-bearing content
    merged into the survivors, and the eight prose references across `build.py` and
    `optout.py` repointed.
  - `[low]` `[patch]` Blind Hunter: `_claims_region`'s docstring called its divergence from
    `_without_region_claim` "latent today (nothing derives an opt-out across a moved path any
    more)". Confirmed by execution to be LIVE: the gate governs rung 3 only, and
    `opt_outs_to_record` was handing rung-2 pairs into the path-blind filter. The patch above
    is what makes the word true; the docstring now says so, and records the pass it was wrong
    for rather than quietly deleting the claim.
  - `[low]` `[patch]` Blind Hunter: `_EMPTY_CATEGORIES`'s comment argued for "naming the
    class rather than the members that happened to be tried" while still not covering the
    class it implied -- `_has_content("⠀")` (BRAILLE PATTERN BLANK, `So`) and
    `_has_content("ㅤ")` (HANGUL FILLER, `Lo`) both return `True`, a fifth route to the
    outcome the guard has been widened for three times. Fixed by narrowing the CLAIM rather
    than widening the guard a fourth time: "invisible when rendered" is a property of a font,
    not a Unicode class, and has no closing move, while the question the guard actually asks
    -- is this the residue of a file having been emptied -- is closed by whitespace plus the
    whole `C` class. A Braille-blank-only file is content, and reading it as such is correct.
  - `[low]` `[patch]` Blind Hunter: two test docstrings written in this same story were
    already stale about the code they pin -- one still said `bool(text.strip())` "closes it"
    and one still said `_has_content` asks "by Unicode category (`Cc`/`Cf`)", both describing
    revisions superseded by later passes of the same effort. In a change whose central
    argument is that a second spelling drifts from the first, the narration had drifted from
    what it narrates. Fixed, each now naming the guard as it stands and the pass that widened
    it.
  - `[low]` `[patch]` Blind Hunter: `assert "the tool will not re-insert" in remedy` sat
    directly above `assert "while this opt-out stands the tool will not re-insert" in remedy`
    -- strictly implied by it, pinning nothing of its own. The same vacuity pass 4 removed
    from two other assertions in this file. Fixed: the implied one is gone and the comment
    records why.
  - `[defer]` Blind Hunter: the over-detection residual of the marker-grammar scan -- a
    marker-shaped line in ordinary prose permanently disables derived opt-out for that
    region. The OPPOSITE residual to `DW-FU-8-5-10` (which tracks under-detection), and it
    needs the same thing: fence- and indent-awareness that `regions/parse.py` has and
    `parse_marker_line` does not, i.e. the looser grammar S-8.2 owns. `regions/markers.py` is
    outside this story's Code Map and a second grammar in `optout.py` is an explicit
    Always-bullet violation. Recorded as `DW-FU-8-5-11`.
  - `[reject]` Edge Case Hunter: an `ABSENT` hybrid whose file APPEARS between `classify` and
    `build_plan`, with every declared region opted out, is suppressed and leaves the
    fingerprint, so `fingerprint_drift` no longer reports "was absent when the plan was built
    and something exists there now". Confirmed by execution, and specified: the
    `<intent-contract>` says a zero-pending hybrid produces no `Action` and no
    `artifact_hashes` entry "for `PRESENT_DIVERGENT` and `ABSENT` alike". It is also
    harmless in a way the high-severity finding above is not -- the fingerprint exists to
    validate a plan's ACTIONS, and a fully-opted-out entry has none, so there is no apply
    step for a stale fingerprint to wave through. The `retained` fix above is what keeps the
    distinction real: an entry that still holds managed content is no longer suppressible.
  - `[reject]` Blind Hunter: a suppressed entry vanishes from `plan.json` with no carrier,
    though `SkippedArtifact` already exists. Already tracked as `DW-FU-8-5`; routing it
    through that type was considered and rejected on the record (its third field is a
    `--skip` glob, and PRD J4 names opt-out and `skips[]` as distinct mechanisms), and a
    faithful fix extends `Plan`'s frozen JSON wire contract.
  - `[reject]` Blind Hunter + Edge Case Hunter: the `OPTED_OUT` remedy names
    `marshal seed adopt --reinstate`, which argparse rejects with exit 2. The exact string is
    fixed verbatim inside the read-only `<intent-contract>`; the flag is S-10.6's. Rejected
    for the fourth pass running on the same unchanged ground.
  - `[reject]` Blind Hunter: the declared `frozenset[str]` hint contradicts the documented
    and tested `Collection[str]` contract, with `# type: ignore[arg-type]` conceding it at
    the call sites. True, and the hint is contract-verbatim inside the `<intent-contract>`;
    pass 3 recorded the same reasoning when it widened the runtime guard.
  - `[reject]` Blind Hunter: the whole feature is inert -- no production caller, and the
    record-before-plan sequencing contract is enforced by prose alone. Rejected on scope for
    the fifth time; `cli/seed.py` and the verb layer are S-10.5/S-10.6's declared surface and
    an explicit Never bullet here.
  - `[reject]` Blind Hunter: `opted_out` keys are never pruned and an orphan is unreportable,
    `FindingType` being pinned at exactly twelve. Rejected on the same ground as pass 2 --
    nothing writes `opted_out` yet, so none can accumulate. Its one live consequence is now
    stated where it bites: the `is_opt_out_key` guard above deliberately does not check the
    artifact half against the manifest, precisely so an orphaned key cannot hard-fail the
    documented natural call.
  - `[reject]` Blind Hunter: the `opted-out` message and its remedy print the hedge clause
    twice in one report row, and the remedy's opening now differs from `LEGACY_PRESENT`'s.
    Both are pass-3 and pass-1 fixes respectively (the remedy was made to hedge BECAUSE it
    contradicted the message; the opening was reworded BECAUSE "no action required" preceded
    a command). Changing either back is oscillation, not repair.
  - `[reject]` Blind Hunter: `region_findings`'s `key_tail is None` branch is documented as
    unreachable and untested -- dead code in a module that argues against speculative
    surface. It is pass 4's deliberate defensive omission (omit the tail rather than guess
    it), of the same kind as `opt_out_key_or_none`'s own re-checks, and one line.
  - `[reject]` Blind Hunter: the diff carries the unrelated `scripts/spec_surface_allowlist.txt`
    change. Deliberate and documented in this spec's Spec Change Log; re-verified this pass,
    `python scripts/spec_surface_reconcile.py` exits 0.
  - `[reject]` Blind Hunter: `spec-surface` reports `drift-presumed: warn` for the new test
    path. Already tracked as `DW-FU-8-5-8`; warn-level and non-gating.

### 2026-08-20 — Review pass 4 (follow-up review of a `done` spec)
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 1, medium 3, low 5)
- defer: 1
- reject: 7
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same root cause):
    `_Pendency.retained` -- pass 3's own fix for the fingerprint regression -- was
    defeated by its own opted-out clause. `retained` was computed as "declared,
    present, AND not opted out", so a `CLAUDE.md` declaring `tiers` (present,
    conformant, tool-installed) and `model-badge` (absent), with BOTH keys recorded,
    produced `retained == ()` and the entry was suppressed anyway: the live `tiers`
    body left `artifact_hashes`, and `fingerprint_drift` reported `()` after that body
    was tampered with. This is pass 3's high-severity finding surviving its own repair
    -- the field measured consent against the key set rather than against the file, and
    `_is_fully_opted_out`'s consent argument was false on the surviving path for the
    third pass running. It also put the two layers in flat contradiction about one
    input: `optout.py` rung 1 answers `PRESENT` for that same region ("what is actually
    in the file wins over anything state believes"). Reachable by nothing worse than
    opting out and then `git checkout`-ing the file back. Fixed: `retained` is now
    simply the complement of `not_present` -- physical presence is the fact. Confirmed
    real by restoring the clause and watching the new test fail.
  - `[medium]` `[patch]` Edge Case Hunter: `_is_fully_opted_out` inferred consent from a
    file nobody could read. `_current_text` degrades a present-but-unreadable /
    non-UTF-8 / non-regular-file target to `""`, and `""` parses as "no region found",
    so every declared region landed in `not_present` and `retained` came back `()` --
    not because the file holds no managed content but because nothing could be MEASURED
    about it. A `PRESENT_DIVERGENT` `CLAUDE.md` written as non-UTF-8 bytes was suppressed
    on that reasoning and left the `RepoFingerprint` while its markers, for all this
    module knows, sat right there in it. Pass 3 rejected this finding on the argument
    that "the `retained` clause added above is what now makes that distinction
    reliable"; the finding above falsifies that premise, and the premise did not hold
    for unreadable text even after the repair, so the rejection is not inherited.
    Fixed: new `_current_text_verbose` returns `(text, content_known)` -- reusing the
    `(text, readable)` pair `fingerprint_drift` already consumes -- and suppression
    requires `content_known`. `ABSENT` stays suppressible (its `""` is `classify()`'s
    own reported truth, and the `<intent-contract>` names it explicitly). Confirmed real
    by reverting the gate and watching the new test fail.
  - `[medium]` `[patch]` Blind Hunter: rung 3's surviving-marker gate -- pass 3's fix for
    the fenced-region case -- closed only that case. It asks `parse_marker_line`, which
    GUARANTEES the exact canonical single-space grammar and nothing else:
    `_strip_delimiters` returns `None` ("ordinary content") for any other delimiter
    shape. So an intact, plainly-visible region whose marker lines had merely picked up
    a trailing space or an indent was invisible to `parse_regions` AND to the gate, and
    rung 3 read it as a deletion -- a live region retired permanently and its `body_sha`
    dropped with the claim, on a whitespace change an editor or formatter makes
    silently. Verified by execution for trailing space, indent, blockquote prefix and
    inner-space removal. Fixed as far as this story's surface allows: each line is asked
    twice, raw and `str.strip()`ed -- the SAME grammar after normalization, which is what
    `markers.py` says S-8.2 will do wholesale, never a second spelling of it here. Four
    parametrized tests; confirmed real by reverting the second ask. The inner-spacing and
    line-prefix variants need the looser grammar S-8.2 owns and are `DW-FU-8-5-10`.
  - `[medium]` `[patch]` Edge Case Hunter: `_EMPTY_CATEGORIES` named `Cc`/`Cf` only, so
    `_has_content("\U000f0000")` returned `True` and a file holding only private-use or
    unassigned code points still read as real content -- rung 3 retired every claimed
    region of it PERMANENTLY. That is the same outcome `bool(text)` and then
    `bool(text.strip())` had each been widened to close, reached by a fourth route, in a
    guard whose pass-3 rationale was explicitly "covering the class instead of the
    members that happened to be tried" -- and which still did not cover the class. Fixed:
    the whole `C` (Other) class, `Cc`/`Cf`/`Cs`/`Co`/`Cn`. Three parametrized tests;
    confirmed real by reverting. `Cs` is named for completeness but deliberately not
    tested: a lone surrogate cannot come off the strict-UTF-8 read path, and
    `regions/parse.py::_iter_lines` raises `UnicodeEncodeError` on it before
    `_has_content` is consulted -- discovered when the over-reaching test case failed,
    and recorded in both the code comment and the test.
  - `[low]` `[patch]` Edge Case Hunter: `clear_opt_out` sorted but did not DEDUPE what it
    kept, while `record_opt_out` normalized through a `set`.
    `SeedState.__post_init__` runs `_reject_duplicates` on `managed[].id` but not on
    `opted_out`, so a hand-built state can carry a repeated key -- and clearing an
    UNRELATED pair on such a state returned one whose surviving duplicates then failed
    `write_state`'s schema `uniqueItems` check: a reinstate that could not be persisted,
    reported against a key the caller never touched. Fixed: both mutators normalize
    identically. Confirmed real by reverting.
  - `[low]` `[patch]` Blind Hunter: `region_findings` hand-rendered the opt-out key as
    `f"{artifact_id}#{region}"`, in the module whose docstrings argue at length that the
    wire spelling must "live once for the whole package" and that a second spelling "is
    exactly what this story's Always bullets forbid". If the packaged schema's grammar
    moved, the message would silently print a token no `--reinstate` would accept, and
    the only assertion pins the literal so nothing would fail. Fixed: asked of
    `opt_out_key_or_none`, with the tail omitted rather than guessed at if it is ever
    `None` (unreachable today -- both rungs that can produce `OPTED_OUT` already gate on
    that same function).
  - `[low]` `[patch]` Blind Hunter: two assertions could not fail as written.
    `assert not opted.message.endswith("the tool will not re-insert this region")` is
    unfalsifiable because the message always ends with the `(opt-out key ...)` tail, so
    removing the hedge the test is named for would still have passed it; and
    `assert "Informational -- the tool will not re-insert" not in remedy` pinned the one
    exact prefix an earlier revision happened to use, which no plausible regression
    reproduces character-for-character. Fixed: both now assert what must stay true --
    that the promise is never made unhedged.
  - `[low]` `[patch]` Blind Hunter: `classify_regions` can raise a process-fatal
    `InternalError` (exit 10) out of a function whose "Degrading rather than guessing"
    section promises `()` on failure -- rung 3 reaches `opt_out_key_or_none`, which reads
    the packaged schema. `plan/build.py` documents that reachability for its own consumer;
    `optout.py` did not mention it at all. Fixed: the degrade rule now says explicitly
    that it covers every fact read about the REPO and not the one thing read about the
    install itself.
  - `[low]` `[patch]` Blind Hunter: two prose defects in `optout.py`'s module docstring --
    a 134-character line (a patch artifact: a parenthetical close followed by unrelated
    prose on the same physical line, in a file that wraps at ~76), and "Every one of
    those four conjuncts is a guard ... see `_has_content`, `_marker_region_names` and
    `_claims_region`", which names three references for four conjuncts and counts the
    claim itself as a guard. Fixed: the line is wrapped, and the claim is named as the
    rung's premise with each of the three actual guards pointing at the case it closes
    (including `opt_out_key_or_none`, which had no reference at all).
  - `[defer]` Blind Hunter: the residual half of the marker-grammar finding above -- an
    inner-spacing or non-whitespace-line-prefix variant still reads as a deletion.
    Needs the looser grammar `parse_marker_line`'s own docstring assigns to S-8.2, whose
    surface (`regions/markers.py`) is not in this story's Code Map, and hand-writing one
    in `optout.py` is an explicit Always-bullet violation. Recorded as `DW-FU-8-5-10`.
  - `[reject]` Blind Hunter: FR-112 is honoured for at most ONE deleted region per
    artifact, and the shipped manifest's two hybrid entries declare 3 and 2 regions.
    Real and well-evidenced, but already tracked as `DW-FU-8-5-6`; the fix is a
    `schema.json` edit plus a migration, both named verbatim in this story's Never
    bullets.
  - `[reject]` Blind Hunter + Edge Case Hunter: the `OPTED_OUT` remedy names
    `marshal seed adopt --reinstate`, which argparse rejects with exit 2. The exact
    string is fixed verbatim inside the read-only `<intent-contract>`; the flag is
    S-10.6's. Rejected for the third pass running on the same unchanged ground. Edge
    Case Hunter's proposed alternative (tell the operator to hand-edit
    `opted_out` in the state file) would contradict that frozen text.
  - `[reject]` Blind Hunter: an artifact id the `opted_out` grammar cannot spell yields a
    silent, unbreakable re-insertion loop with no diagnostic. Already tracked as
    `DW-FU-8-5-2`; surfacing it needs a thirteenth `FindingType` against a wire contract
    pinned at exactly twelve by an existing test.
  - `[reject]` Blind Hunter: `_without_region_claim` and `_claims_region` are two
    spellings of one predicate that already disagree, and both mutators carry an
    unchecked documented precondition. Both halves are already tracked --
    `DW-FU-8-5-9` and `DW-FU-8-5-4` -- and pass 3 widened the divergence deliberately
    and recorded why.
  - `[reject]` Blind Hunter: an absent artifact reports `managed-region-missing` once per
    declared region, up to four times, on top of the inventory layer's own
    `artifact-missing`. Which finding producers `check` calls for which artifact state,
    and how their output is de-duplicated for the operator, is its renderer's composition
    decision -- S-10.5's surface. Pass 1 rejected the equivalent never-adopted-repo
    finding on the same ground.
  - `[reject]` Blind Hunter: the whole feature is inert -- no production caller, and the
    record-before-plan sequencing contract is enforced by prose alone. Rejected on scope
    for the fourth time; `cli/seed.py` and the verb layer are S-10.5/S-10.6's declared
    surface and an explicit Never bullet here.
  - `[reject]` Blind Hunter: `optout.py` is ~half docstring and carries review
    archaeology ("An earlier revision claimed...") that will rot in shipped source. The
    density is this package's established house style -- every neighbouring module
    (`build.py`, `store.py`, `parse.py`) documents rejected alternatives the same way --
    and the archaeology is load-bearing here: three of this pass's four behavioural
    findings were regressions of an earlier pass's fix, which is precisely what those
    notes exist to prevent. The one actionable half (the wrap defect and the miscount) is
    patched above.
  - `[reject]` Blind Hunter: the diff carries an unrelated change
    (`scripts/spec_surface_allowlist.txt`). Deliberate, and documented in this spec's own
    Spec Change Log: the repo-level gate emits a single exit code, so the six pre-existing
    `ungoverned` findings had to be reconciled for the story to land at all. The block's
    factual claims were re-verified by the reviewer and check out.

### 2026-08-20 — Review pass 3 (follow-up review of a `done` spec)
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 2, medium 4, low 3)
- defer: 2
- reject: 8
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same root cause):
    `_is_fully_opted_out` fired on "every region a run OWES is opted out", not "every
    region is opted out" -- so a `CLAUDE.md` declaring `tiers` (present, conformant,
    tool-installed, NOT opted out) and `model-badge` (absent, opted out) owed nothing
    after opt-outs and vanished from BOTH `actions` and `artifact_hashes`. The file left
    the `RepoFingerprint` while a LIVE managed region sat inside it, and `fingerprint_drift`
    reported `()` after that region's body was hand-edited. This is pass 2's high-severity
    fingerprint regression one case further along: pass 2 protected the nothing-owed case
    and left the partially-owed one, and `_is_fully_opted_out`'s own consent argument
    ("no managed content left in it to drift") was simply false on the surviving path.
    Fixed: `_Pendency` gains a third fact, `retained` (declared regions present in the
    file and released by no opt-out), and suppression requires it empty -- so consent is
    measured rather than assumed. Confirmed real by reverting the clause and watching the
    new test fail.
  - `[high]` `[patch]` Edge Case Hunter: rung 3's premise is "the markers are GONE", but it
    was testing `parse_regions`'s narrower "no span was FOUND". `parse_regions` skips
    fenced lines BY DESIGN (a region's own body may document the marker grammar -- the AR-1
    corruption fence-awareness exists to prevent), so a real region a maintainer later
    wrapped in a closed ``` fence was invisible to it while sitting, markers and all, in
    the file: rung 3 read that as a deletion, classified `opted-out`, and
    `opt_outs_to_record` handed the pair over for PERMANENT recording. A live region
    silently retired -- the same outcome the empty-file and whitespace-only guards were
    added to prevent, reached by a third route. Fixed: `_marker_region_names` asks
    `markers.parse_marker_line` (the existing grammar, never a hand-written substring)
    whether any marker line for that name survives anywhere in the raw text, and rung 3
    stands down if one does. A malformed marker line is skipped rather than raised, so a
    fenced block documenting bad marker syntax cannot degrade the whole entry to `()`.
    Confirmed real by reverting the gate and watching the new test fail.
  - `[medium]` `[patch]` Edge Case Hunter: pass 2 widened the empty-file guard from
    `bool(text)` to `bool(text.strip())`, and `str.strip()` removes whitespace and nothing
    else -- so a file holding only a UTF-8 BOM (what `write_text("", encoding="utf-8-sig")`
    leaves behind), a zero-width space, or a NUL byte read back as non-empty and retired
    every claimed region of it permanently. Three bytes reopened the hole one byte had just
    closed. Fixed: `_has_content` tests by Unicode general category (`Cc`/`Cf`) as well as
    whitespace, covering the class instead of the members that happened to be tried. Four
    parametrized tests; confirmed real by reverting to `.strip()`.
  - `[medium]` `[patch]` Edge Case Hunter: `_claims_region` never compared the claim's
    recorded `path`. AD-55 makes `id`, not `path`, the stable address, so an entry's `path`
    can move while its `id` does not -- and matching on `id` alone derived an opt-out for a
    path that had never carried the region, after which `record_opt_out` would have dropped
    the claim describing the region still installed at the OLD path, leaving that one with
    no `body_sha` and nothing to rebuild it. Fixed: all three halves are now required, and
    a moved path falls through to `MISSING` -- the same non-destructive direction the other
    rung-3 gates take. The resulting divergence from `store.py::_without_region_claim`
    (which is handed no path) is deliberate and recorded as `DW-FU-8-5-9`.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same root cause):
    `build_plan`'s `opted_out` guard demanded `set`/`frozenset` and therefore rejected
    `tuple`, `list` and `dict.keys()` -- including `SeedState.opted_out`'s OWN declared
    type, so the natural `build_plan(m, i, opted_out=state.opted_out)` hard-failed -- while
    citing substring containment as the reason, which is false for all three (`in` is exact
    membership there). Meanwhile a `frozenset` of `(id, region)` PAIRS, the right container
    holding the wrong thing, was ACCEPTED and silently suppressed nothing: exactly the
    silent failure the guard exists to make loud. Fixed: the guard now tests the two things
    that actually go wrong -- `str`/`bytes` (the real substring hazard) and non-`str`
    elements -- and accepts any other `Collection`. The declared `frozenset[str]` hint is
    untouched (contract-verbatim).
  - `[medium]` `[patch]` Blind Hunter: `REMEDIES[FindingType.OPTED_OUT]` went on promising
    flatly that "the tool will not re-insert this region" -- the exact unconditional claim
    this same pass's `region_findings` message deliberately hedges to "while this opt-out
    stands", because a DERIVED opt-out under a read-only `check` is not durable until a
    mutating verb records it (FR-88). Remedy and message print as one report and
    contradicted each other. Fixed: the remedy hedges identically, with a test pinning it;
    the `--reinstate <artifact>#<region>` spelling the `<intent-contract>` fixes verbatim is
    preserved.
  - `[low]` `[patch]` Blind Hunter: `test_a_recorded_opt_out_is_sticky_once_the_managed_claim_is_gone`'s
    docstring named `record_opt_out`, which it never called -- it hand-built the state as
    `_state(opted_out=(...))`, whose `managed` DEFAULTS to `()`, so `assert state.managed == ()`
    asserted the fixture's own default and would have kept passing if the mutator stopped
    dropping claims entirely. The same vacuity this file congratulates itself on removing
    elsewhere. Fixed: driven through the real mutator.
  - `[low]` `[patch]` Blind Hunter: `optout.py`'s placement rationale claimed "an
    import-linter contract already forbids one direction of that edge" for the
    `regions`/`state` pair. Verified against `pyproject.toml`: the sole `regions` contract
    forbids `seed.regions -> seed.model.manifest` (Story 8.4's package-cycle guard) and says
    nothing about `state`. Fixed: the claim is corrected and the one mechanically-enforced
    half (store.py's AST-guarded import surface, which IS real) is separated from the half
    that rests on convention.
  - `[low]` `[patch]` Blind Hunter: `record_opt_out` carries `clear_opt_out`'s live-claim
    precondition exactly -- both drop the claim through the same unconditional
    `_without_region_claim`, and neither is given the file that distinguishes the two cases
    -- but only one of the two documented it. Fixed: the precondition is now stated on both,
    pointing at the same verb-side guard (`DW-FU-8-5-4`).
  - `[defer]` Blind Hunter: `pixi run -e local-recipes python -m pyforge.doctor.sources
    spec-surface` reports `drift-presumed: warn` for both new files under
    `pyforge-marshal/spec-pyforge-marshal` -- the memlog moved but does not name them.
    These two ARE this story's (it created both). Warn-level and non-gating
    (`spec_surface_reconcile.py` exits 0), 112 of the run's 114 such warns are a pre-existing
    backlog, and the remedy is a baseline stamp that would be dishonest before the tracked
    spec of record -- outside this story's Code Map, and frozen at the branch point in this
    worktree -- actually names the paths. Recorded as `DW-FU-8-5-8`.
  - `[defer]` Blind Hunter: `detect/optout.py::_claims_region` and
    `state/store.py::_without_region_claim` spell the same predicate twice with nothing
    pinning them equal, in a story whose docstrings argue at length against second
    spellings. This pass WIDENED the gap deliberately (the path conjunct above), because
    the mutators' `(state, artifact_id, region)` signature is contract-frozen and carries no
    path. Latent, not live. Recorded as `DW-FU-8-5-9`.
  - `[reject]` Edge Case Hunter: a binary/unreadable `PRESENT_DIVERGENT` file degrades to
    `""` in `_current_text`, so with every declared region recorded opted out it is
    suppressed and leaves the fingerprint -- where `optout.py` guards the identical `""`
    with `_has_content`. The two guards protect against different things: `optout.py`
    DERIVES an opt-out from a file and must never invent one; `build_plan` obeys a RECORDED
    one. With every declared region opted out, nothing is under management whether or not
    the file can be read, which is the consent distinction `_is_fully_opted_out` already
    draws -- and the `retained` clause added above is what now makes that distinction
    reliable.
  - `[reject]` Edge Case Hunter: a DERIVED opt-out is unreachable by `build_plan` in a
    read-only run, so `check` can report "opted out" while a plan built in the same breath
    schedules the re-insert. Pass 2 addressed this with the record-before-plan sequencing
    contract (`opt_outs_to_record` plus both modules' docstrings) and by hedging the
    message; FR-88 forbids `check` writing, so the residual is the requirement, not a defect.
  - `[reject]` Blind Hunter: opt-out suppression leaves no carrier in `plan.json`. Already
    tracked as `DW-FU-8-5`.
  - `[reject]` Blind Hunter + Edge Case Hunter: a manifest id the `opted_out` grammar
    cannot spell yields a permanent DRIFT loop with no diagnostic. The representability
    gap is already tracked as `DW-FU-8-5-2`; surfacing it needs a thirteenth `FindingType`
    against a wire contract pinned at exactly twelve.
  - `[reject]` Blind Hunter: a recorded region opt-out vetoes materializing an ABSENT
    hybrid file. Specified verbatim in the `<intent-contract>` ("for `PRESENT_DIVERGENT` and
    `ABSENT` alike") -- re-verified against the frozen text this pass, not inherited.
  - `[reject]` Blind Hunter + Edge Case Hunter: the `OPTED_OUT` remedy names
    `marshal seed adopt --reinstate`, which argparse rejects. The exact string is fixed
    verbatim inside the read-only `<intent-contract>`; the flag is S-10.6's.
  - `[reject]` Blind Hunter: the whole feature is inert -- no production caller. Rejected on
    scope for the third time; `cli/seed.py` and the verb layer are S-10.5/S-10.6's declared
    surface and an explicit Never bullet here.
  - `[reject]` Blind Hunter: `assert finding.severity is not Severity.HARD` / `is not
    Severity.DRIFT` are implied by the `is Severity.INFO` above them. True, and deliberate:
    they trace the AC's own wording ("reports at `INFO` severity and never `HARD` or
    `DRIFT`") onto the assertion that proves it.

### 2026-08-20 — Review pass (dev attempt 2)
- intent_gap: 0
- bad_spec: 0
- patch: 12: (high 2, medium 4, low 6)
- defer: 4
- reject: 11
- addressed_findings:
  - `[high]` `[patch]` Edge Case Hunter: rung 3's guard tested `bool(text)`, so the
    empty-file protection split on a SINGLE byte -- `""` re-offered the region (correct)
    while `"\n"` or `" "` derived a PERMANENT opt-out from the surviving claim. A botched
    script truncating `AGENTS.md` to a newline silently retired every claimed region of
    it, which is precisely the outcome pass 1 added the guard to prevent. Fixed:
    `bool(text.strip())` -- the guard asks "is there a FILE here to have deleted markers
    from", and a whitespace-only file answers that no. Three parametrized regression
    tests; confirmed real by reverting to `bool(text)` and watching all three fail.
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same root cause):
    rung 3 derived an opt-out from the raw `managed[].id`, which is the LOOSER grammar --
    `SeedState` accepts an id the `opted_out` item pattern rejects. So `opt_outs_to_record`
    could hand back a pair `record_opt_out` REFUSES, breaking the sanctioned verb sequence
    at the exact seam this module's own docstring documents and a test demonstrates. Three
    layers disagreed three ways on one id: rung 3 derived it, `build_plan` degraded it to
    not-opted-out and re-inserted the region anyway, and `record_opt_out` raised. Fixed:
    rung 3 gained the `opt_out_key_or_none` gate rung 2 already gets for free through
    `is_opted_out`, so all three apply the ONE grammar and an unspellable pair falls
    through to `MISSING` -- the non-destructive direction. Confirmed real by reverting the
    gate and watching both new tests fail.
  - `[medium]` `[patch]` Blind Hunter: the `opted-out` finding and its own remedy used
    different addressing. The message rendered `AGENTS.md#tiers` (path) while
    `REMEDIES[FindingType.OPTED_OUT]` told the operator to run
    `--reinstate <artifact>#<region>` with the opt-out KEY (`agents-md#tiers`), so the
    obvious copy-paste was the wrong token -- and `RegionStatus` carries both addresses
    precisely because they answer different questions, while `Finding` carries only
    `path`. Fixed: the contract-mandated `f"{path}#{region}: ..."` prefix is unchanged
    (`hashes.py` parity preserved) and the key is spelled in the tail, where the remedy
    can be acted on.
  - `[medium]` `[patch]` Blind Hunter: the same message promised "the tool will not
    re-insert this region" unconditionally, which is false for a DERIVED opt-out -- nothing
    is recorded, `build_plan` suppresses only on RECORDED keys, so a `check` reporting it
    followed by an `update` that does not record re-inserts the region. The same class of
    unprovable claim pass 1 correctly removed from `managed-region-missing`. Fixed: the
    promise is now scoped ("while this opt-out stands"), with a test asserting the
    unconditional form is gone.
  - `[medium]` `[patch]` Edge Case Hunter: `build_plan`'s `opted_out` had no runtime type
    check, and the failure mode is SILENT -- `in` against a bare `str` is substring
    containment, so one key passed as a string instead of a one-element set makes every
    key that is a substring of it read as opted out, dropping entries from `actions` AND
    `artifact_hashes` with no error at any layer. Fixed: a named `ValueError`, matching the
    defensive re-check `opt_out_key_or_none` already makes on its own two halves.
  - `[medium]` `[patch]` Blind Hunter: `clear_opt_out` drops the `managed[]` claim
    unconditionally (pass 1's fix, without which a derived opt-out could never be
    reinstated), so calling it on a region that is still PRESENT discards a live claim and
    its `body_sha` -- after which `check_managed_region` reports HARD
    `managed-region-modified` forever and `build_plan` plans no insertion to rebuild it,
    because the region IS present. Confirmed by execution. No state-only discriminator
    exists (the two cases differ only in the FILE, which this pure function never sees and
    the frozen signature cannot be given), so the guard belongs to the calling verb.
    Fixed as far as this story's surface allows: the precondition is documented on the
    function and pinned by a new test; the verb-side guard is `DW-FU-8-5-4`.
  - `[low]` `[patch]` Blind Hunter + Edge Case Hunter: `_opt_out_pattern`'s subscript chain
    into `properties.opted_out.items.pattern` raised a bare `KeyError`/`TypeError`, and
    `re.compile` a bare `re.error`, where both of `_schema_text`/`_load_schema`'s own
    failure modes are wrapped in an exit-10 `InternalError` with a reinstall remedy -- same
    corrupt install, two different exits, and reachable from `build_plan` through a
    function documented as degrading rather than crashing. Fixed, with three parametrized
    tests (key gone, uncompilable pattern, wrong shape).
  - `[low]` `[patch]` Blind Hunter: `build.py` claimed keeping the state read out
    "preserves S-9.6's purity property", which the new `opt_out_key_or_none` reach into the
    packaged schema makes false in letter. Fixed: narrowed to the true, narrower claim --
    no STATE read; packaged data is read once per process and identical for every caller,
    so determinism is untouched, but "pure" was too strong.
  - `[low]` `[patch]` Blind Hunter: `_pendency` claimed it makes the file "parsed exactly
    once per `build_plan` call rather than once per consumer" -- the pre-story code also
    parsed once per entry, so the duplication it describes never existed. Fixed to what
    the helper actually buys: one parse serving BOTH consumers, where adding the second
    would otherwise have doubled it.
  - `[low]` `[patch]` Blind Hunter: `_Pendency`'s docstring argues at length that dropping
    an entry from `artifact_hashes` blinds `fingerprint_drift` -- and the fully-opted-out
    branch then does exactly that without a word. Fixed: `_is_fully_opted_out` now states
    that it pays that cost knowingly, and why the two cases differ (consent), pointing at
    `DW-FU-8-5` for the part that is a real gap.
  - `[low]` `[patch]` Blind Hunter: `state/__init__.py` says "the five opt-out helpers"
    while `test_seed_state_store.py`'s `__all__` comment said "the group the four join".
    Fixed: the test comment names the five and why the fifth
    (`opt_out_key_or_none`, promoted to public by pass 1) is there.
  - `[low]` `[patch]` Blind Hunter: the `scripts/spec_surface_allowlist.txt` block header
    called the set a "quartet" while allowlisting six paths. Fixed in both sub-comments.
    (The same finding's claim that the commit message "admits the gate is still red" is
    rejected below -- the gate is rc=0.)
  - `[defer]` Blind Hunter: `verbs/preconditions.py` rung 6 refuses the exact repo state
    FR-112 declares lawful -- deleted markers raise `managed-content-modified` whose remedy
    tells the operator to `git checkout` the deletion away -- and nothing filters the
    managed set by opt-outs, though `skips.managed_after_skips` is the precedent for
    exactly that obligation. Confirmed by execution. `seed/verbs/` is outside this story's
    Code Map and the fix is the cross-verb contract S-12.5/S-10.6 own. Recorded as
    `DW-FU-8-5-5`.
  - `[defer]` Blind Hunter: state records at most one `inserted_region_span` per artifact,
    so a derived opt-out covers at most one of an artifact's declared regions and the
    siblings are re-offered for insertion -- FR-112 honoured for one region, silently
    undone for the rest. Pass 1 established the fact and documented it; this pass records
    it as the functional limit it is. The fix is a `schema.json` edit plus a migration,
    both named verbatim in this story's Never bullets. Recorded as `DW-FU-8-5-6`.
  - `[defer]` Edge Case Hunter: `RepoFingerprint` does not cover the `opted_out` set a plan
    was built against, so a plan outliving a `record_opt_out`/`clear_opt_out` still
    verifies clean. Extending it changes `Plan`'s frozen JSON wire contract -- the same
    objection that deferred `DW-FU-8-5`, but a distinct failure mode (that one is about a
    suppressed artifact leaving no trace IN the plan; this is the staleness check not
    seeing the input that suppressed it). Recorded as `DW-FU-8-5-7`.
  - `[defer]` Blind Hunter: `clear_opt_out`'s live-claim precondition needs a caller-side
    guard in the verb that will call it. Recorded as `DW-FU-8-5-4` (the patch above
    documents and pins it; only the guard is deferred).
  - `[reject]` Blind Hunter: the corrected `OPTED_OUT` remedy names `--reinstate`, a flag
    that exists nowhere. The exact string is specified verbatim inside this spec's own
    read-only `<intent-contract>`, quoting the epics AC; building the mechanism before its
    CLI is the epic's declared sequencing (S-10.6).
  - `[reject]` Blind Hunter: the shipped surface diverges from `epics.md`'s `Surface:`
    line (`regions/parse.py` untouched, `detect/optout.py` new). Both the relocation and
    its justification are inside the frozen `<intent-contract>` and the Design Notes; a
    `Surface:` amendment is an epics edit, not a code finding.
  - `[reject]` Blind Hunter: the whole feature is inert -- no production caller of
    `build_plan`, `classify_regions`, or `region_findings`. Pass 1 rejected this on scope
    and the reason still holds: `cli/seed.py` and the verb layer are S-10.5/S-10.6's
    declared surface and an explicit Never bullet here.
  - `[reject]` Blind Hunter: `_is_opted_out`'s grammar gate is redundant for schema-valid
    state and buys `build_plan` a packaged-data read plus an `InternalError` path. That
    indirection is pass 1's deliberate fix for a second spelling of the same rule, and
    "one spelling" is this story's own theme. The one actionable half -- the bare exception
    the chain could raise -- is patched above.
  - `[reject]` Blind Hunter: `opt_out_key`'s `ValueError` says "the rendered key does not
    match the pattern" even when the isinstance check fired and nothing was rendered.
    Verified by execution: the same message then enumerates "both halves must be str, the
    artifact half must carry no whitespace and no `#`, ...", so the real cause is named.
    Rewording it per-cause would fork one message into two for no gain in information.
  - `[reject]` Blind Hunter: orphaned `opted_out` keys (manifest entry renamed or removed)
    have no lifecycle, no pruning, and no detector. Unreachable: nothing writes `opted_out`
    yet, so none can accumulate; and surfacing them needs a thirteenth `FindingType`
    against a wire contract pinned at exactly twelve by an existing test.
  - `[reject]` Blind Hunter + Edge Case Hunter: `build_plan` suppresses an `ABSENT` hybrid
    whose only region is opted out, so the host file is never materialized, while
    `optout.py` refuses to derive an opt-out from the same empty text. The asymmetry is
    specified verbatim in the `<intent-contract>` ("for `PRESENT_DIVERGENT` and `ABSENT`
    alike") and is coherent: deriving from absence would INVENT an opt-out, honouring a
    RECORDED one over absence is obeying a stated fact.
  - `[reject]` Edge Case Hunter: an unparseable file yields `()` with no finding naming the
    parse failure. The degrade is contract-specified, and artifact-level parse reporting
    belongs to `detect/inventory.py`/`hashes.py`, which this story must not edit.
  - `[reject]` Edge Case Hunter: add `opt_outs_to_clear` so a region a human re-added by
    hand withdraws its recorded opt-out. Pass 1 rejected the equivalent rung reorder as a
    design change for a later story; a new public API to achieve it is more speculative,
    not less.
  - `[reject]` Blind Hunter: the allowlist commit message "admits the gate it exists to
    clear is still red". Factually wrong -- `python scripts/spec_surface_reconcile.py`
    exits 0 with "every tracked file governed or allowlisted; no drift".

### 2026-08-20 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 14: (high 3, medium 3, low 8)
- defer: 3
- reject: 7
- addressed_findings:
  - `[high]` `[patch]` Edge Case Hunter: the suppression rule fired whenever a hybrid entry's
    pending set was empty -- **including when nothing was missing in the first place**, and so
    under the DEFAULT `opted_out=frozenset()`. A `PRESENT_DIVERGENT` entry whose file already
    carried every declared region at build time (the classify/`build_plan` re-read window) used
    to produce an `Action` with `chosen_anchor=()`; it now vanished from BOTH `actions` and
    `artifact_hashes`, silently removing it from the `RepoFingerprint` and blinding
    `fingerprint_drift` to every later change to that file. Fixed: the single pendency helper now
    carries both facts (`_Pendency(not_present, pending)`), and `_is_fully_opted_out` requires a
    NON-EMPTY `not_present` -- so suppression fires only when opt-outs actually caused the
    emptiness, and the nothing-owed case keeps its pre-story behavior exactly. Parse-once and
    one-shared-verdict are preserved. One new regression test; confirmed real by reverting the
    guard and watching that test fail.
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same root cause):
    `classify_regions` derived a permanent opt-out from a `managed[]` claim without knowing
    whether the ARTIFACT was present, so an artifact whose file was deleted entirely -- caller
    passes `text=""`, the same `""` `plan/build.py::_current_text` produces for `ABSENT` --
    classified every claimed region `OPTED_OUT`. `rm AGENTS.md` silently and permanently retired
    the region. Fixed: rung 3 is gated on non-empty `text` (`derive_from_claim`), falling through
    to `MISSING`; rungs 1-2 are unchanged, so a RECORDED opt-out stays sticky. FR-112 sanctions
    deleting the MARKERS, not the file, and re-offering the region is the non-destructive
    direction. Confirmed real by reverting the gate and watching the new test fail.
  - `[high]` `[patch]` Edge Case Hunter: `clear_opt_out` was INERT for a derived opt-out, so
    `--reinstate` could never take effect for the AC's own headline scenario. Markers deleted +
    claim present + `opted_out` empty classifies `OPTED_OUT` (rung 3) without anything having
    been recorded; `clear_opt_out` then removed a key that was never there, rung 3 fired again,
    and the region was unreinstatable forever. Fixed: `clear_opt_out` now also drops the
    `managed[]` claim, through the same `_without_region_claim` filter `record_opt_out` uses
    (now spelled once) -- a no-op in the ordinary record-then-clear sequence, and the thing that
    makes the withdrawal real otherwise.
  - `[medium]` `[patch]` Edge Case Hunter: a non-`str` half rendered straight into the key --
    `opt_out_key(None, "tiers")` produced `"None#tiers"`, which MATCHES the schema pattern and
    would have been recorded as a permanent opt-out no artifact could ever clear. Fixed:
    `isinstance` guards on both halves before interpolation, matching this module's established
    defensive-recheck convention.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same root cause):
    `record_opt_out`'s docstring promised that "a region claim on a DIFFERENT region of it, is
    untouched", which is UNREACHABLE -- `SeedState.__post_init__` runs `_reject_duplicates` on
    `managed[].id`, so state records at most ONE `inserted_region_span` per artifact (verified by
    execution). Two tests asserting selective per-region matching therefore passed vacuously.
    Fixed: the false promise replaced with an honest statement of the one-span-per-artifact
    limit as a pre-existing S-10.2 property (the span half of the filter is defence in depth),
    a matching `optout.py` docstring paragraph so a reader is not misled into thinking rung 3
    covers every declared region, and both vacuous tests retargeted onto the constraint that is
    actually assertable plus the cross-ARTIFACT isolation that IS reachable.
  - `[medium]` `[patch]` Blind Hunter: the story's two halves disagreed with no stated contract
    binding them -- `classify_regions` DERIVES an opt-out from a claim while `build_plan`
    suppresses only on the RECORDED key set, so `check` could report "opted out" while a plan
    built in the same breath still scheduled the re-insert. Fixed: new
    `optout.opt_outs_to_record` makes the obligation mechanical, and both modules' docstrings now
    state the sequencing contract (a mutating verb records every returned pair before
    `build_plan`; a read-only `check` reports without recording, FR-88).
  - `[low]` `[patch]` Edge Case Hunter: both mutators, handed `read_state`'s `None`, raised a
    bare `AttributeError: 'NoneType' object has no attribute 'managed'`. Fixed: a named
    `ValueError` via `_require_state`, pointing at `read_state`. `is_opted_out`'s deliberate
    `None` tolerance is unchanged.
  - `[low]` `[patch]` Blind Hunter: `plan/build.py::_is_opted_out` re-implemented the store's own
    "inadmissible key means not-opted-out" rule with a local `try/except`, in a story whose
    docstrings argue at length against second spellings. Fixed: `_opt_out_key_or_none` promoted
    to a public `opt_out_key_or_none` and re-exported, `build.py` calls it. Its docstring's
    crash-proof promise also narrowed: the degradation covers the inadmissible-key case only, and
    a corrupt packaged schema is a loud `InternalError` (exit 10) by design.
  - `[low]` `[patch]` Blind Hunter: neither mutator refreshes `last_update`, and these are the
    module's first mutators, so they set the convention. Fixed by documentation: stamping belongs
    to the verb that persists the result (`write_state` does not stamp either).
  - `[low]` `[patch]` Blind Hunter: the `managed-region-missing` message claimed the region "was
    never installed" -- a fact the code cannot establish, since a region whose single claim slot
    is occupied by a sibling reports exactly that message despite having been installed. Fixed:
    the unprovable clause dropped.
  - `[low]` `[patch]` Blind Hunter: the corrected `OPTED_OUT` remedy was internally contradictory
    -- "Informational only, no action required" immediately followed by a command to run. Fixed:
    reworded so the informational statement and the optional reinstate path coexist; the
    `--reinstate` and `<artifact>#<region>` spellings (pinned by a test, verbatim from the epics
    AC) are preserved.
  - `[low]` `[patch]` Edge Case Hunter: `build.py`'s module docstring still asserted "Every entry
    that DOES qualify gets EXACTLY one `Action` -- there is no per-entry branching here that
    could ... skip one that qualifies", contradicted by the new suppression branch below it.
    Fixed, naming Story 8.5, matching how the `seed/state/` Never bullet was already amended.
  - `[low]` `[patch]` Blind Hunter: the new upward-import meta-test read `ast.ImportFrom.module`
    and ignored `node.level`, so for the relative imports the module actually uses it tested the
    STRIPPED name -- a future `from ...verbs import x` would have passed the guard that exists to
    forbid it. Fixed: `node.level` resolved via `importlib.util.resolve_name`, matched on package
    boundaries, with a positive assertion proving the resolution itself works.
  - `[low]` `[patch]` Blind Hunter: `test_the_default_empty_opted_out_leaves_output_byte_identical`
    compared `build_plan(m, i)` against `build_plan(m, i, opted_out=frozenset())` -- the
    parameter's own declared default, so both calls ran identical code and it proved nothing,
    while its docstring claimed it proved equivalence with the pre-story implementation. This is
    why the high-severity fingerprint regression above reached review. Fixed: retitled and
    reworded to what it actually proves, with a real regression test added for the behavior it
    had claimed to cover.
  - `[defer]` Blind Hunter + Edge Case Hunter: a fully-opted-out artifact vanishes from
    `plan.json` with no carrier recording why, the "lie by omission" `SkippedArtifact` exists to
    prevent. Deliberately NOT routed through `SkippedArtifact` (its third field is a `--skip`
    glob, and PRD J4 names opt-out and `skips[]` as distinct mechanisms); a faithful fix extends
    `Plan`'s frozen JSON wire contract, which is `plan/types.py`'s surface. Recorded as
    `DW-FU-8-5`.
  - `[defer]` Blind Hunter: the schema's `opted_out` artifact half is stricter than its own
    `managed[].id`, so a legally-named artifact can be impossible to opt out of -- pre-existing
    S-10.2, made observable by this story's first consumer of the field, and unfixable here
    (this story's Never bullets forbid a `schema.json` edit). Recorded as `DW-FU-8-5-2`.
  - `[defer]` Blind Hunter: `detect/inventory.py`'s docstring still says no state-store story
    exists, in a detect layer that now imports the state package -- pre-existing since S-10.2,
    and `inventory.py` is REFERENCE ONLY here. Recorded as `DW-FU-8-5-3`.
  - `[reject]` Blind Hunter: a never-adopted repo emits one DRIFT `managed-region-missing` per
    declared region. That IS the correct per-region classification (declared, not installed);
    which finding producers `check` calls for which artifact states is its renderer's composition
    decision, owned by S-10.5.
  - `[reject]` Blind Hunter: a RECORDED opt-out should outrank presence, so a region whose
    markers a human re-added by hand does not report `PRESENT` while the tool holds no claim on
    it. The rung ORDER is specified verbatim inside this spec's own `<intent-contract>`
    (presence first), which is read-only; and `PRESENT` is a defensible answer for text that is
    genuinely in the file. A reorder is a design change for a later story, not a patch.
  - `[reject]` Blind Hunter: a present-but-opted-out region loses hand-edit protection, since the
    claim is gone and `check_managed_region` can never run on it. That is precisely what opting
    out means under FR-112 -- the region has left the tool's supervision by the maintainer's own
    deliberate act.
  - `[reject]` Blind Hunter: `_opt_out_pattern`'s `lru_cache` defends against mutability but not
    staleness, unlike `_load_schema`'s deliberate non-caching. `_schema_text` is ALREADY
    `lru_cache(maxsize=1)`d process-wide, so the schema TEXT is pinned for the process regardless
    -- caching the compiled pattern introduces no staleness that does not already exist.
  - `[reject]` Blind Hunter: `opt_out_key`'s `ValueError` truncates the offending value through
    `_abbreviate` (120 chars). That is this module's established convention for interpolating
    caller-supplied values into every one of its error messages; a per-message exception would be
    the inconsistency.
  - `[reject]` Blind Hunter: `state` names two different types across the story (`ArtifactState`
    in `build.py`, `SeedState | None` in `optout.py`). `build.py`'s parameter name predates this
    story and is that module's own established spelling; renaming it would widen the diff into
    unrelated functions.
  - `[reject]` Blind Hunter: the whole feature is inert -- no production caller of `build_plan`,
    `classify_regions`, or `region_findings`, and nothing constructs a `ManagedArtifact` outside
    tests. True, and by design: `cli/seed.py` and the verb layer are S-10.5/S-10.6's declared
    surface and an explicit Never bullet of this spec. Building the mechanism before its CLI is
    the epic's own sequencing. (The one part of this finding that WAS actionable -- `build.py`
    describing that wiring in the present tense -- is patched above.)

## Design Notes

**Why the join lives in `detect/`, not in `regions/parse.py` as the epics' `Surface:` line says.**
The classification's two inputs sit in peer modules that must not import each other: `regions/`
is deliberately dependency-light and `store.py`'s import surface is AST-guarded. `detect/` is the
first layer above both (`cli -> verbs -> detect|plan -> model|state|regions`), and the AC's own
vocabulary (`opted-out` vs `managed-region-missing`) is `detect/findings.py`'s -- which
`regions/parse.py` cannot import upward at all. `parse.py` is therefore left untouched:
`parse_regions` already returns everything the classifier needs, and a pass-through helper added
only to satisfy a stale surface line would be speculative code.

**Why `record_opt_out` drops the `managed[]` claim.** With the claim retained, "installed once,
markers gone" re-derives the opt-out on every later run, so `clear_opt_out` could never take
effect and `--reinstate` would be inert. Dropping it is also the honest reading of AD-58:
`managed[]` is Genesis's claim on an artifact, and an opt-out relinquishes it. The next apply's
insertion re-establishes the claim.

**Why `MISSING` is DRIFT, not HARD or INFO.** `HARD` is reserved for corruption and refusals
(`managed-*-modified`, `never-write-violation`, `uncovered`); `INFO` for intentional, no-action
states (`legacy-present` per AD-59, and now `opted-out`). A declared region that is simply not
inserted yet is actionable and safe to fix -- its shipped remedy already says "Run `marshal seed
update` to re-insert" -- which is exactly the middle rung.

**Why `build_plan` takes a key set rather than reading state.** Keeping `build_plan` free of I/O
preserves S-9.6's purity property and its byte-identical-output determinism guarantee; the verb
layer (S-10.5/10.6) already owns reading state and will pass
`frozenset(state.opted_out)` straight through.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expect all tests pass, including
  the new `test_seed_detect_optout.py`.
- `pixi run -e local-recipes ruff check src/shared/packages/pyforge-marshal` -- expect no new
  finding categories versus the pre-change baseline.
- `pixi run -e local-recipes pyright src/shared/packages/pyforge-marshal` -- expect no growth
  beyond the existing accepted baseline (rescope to the changed files if the whole-package count
  is dominated by the known `tests/`-outside-`src/` resolution gap).
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`
  -- expect `Contracts: 4 kept, 0 broken` (no new edge from `regions` to `model.manifest`).


## Auto Run Result

**Status:** done (review pass 5 -- follow-up review of a `done` spec; no implementation loopback)

**Summary of implemented change.** No intent change and no re-derivation: this pass reviewed the
shipped story adversarially and landed nine patches over the opt-out classifier and the planner.
Three are behavioural, and all three are the same shape the previous two passes fixed -- a rule
applied at one call site and not at its mirror. (1) The planner's consent gate (`_Pendency.retained`)
measured "still in the file" with `parse_regions`, the narrower question `detect/optout.py` had
already been hardened to stop asking, so a fenced or whitespace-nudged live region let a fully-keyed
entry drop out of the `RepoFingerprint`. (2) `opt_outs_to_record` handed already-recorded pairs back
to `record_opt_out`, whose claim-drop is unconditional, discarding live and moved-path claims through
the module's own documented verb loop. (3) `build_plan`'s key-set guard tested element TYPE rather
than the key GRAMMAR, so every malformed key string failed open exactly as the non-`str` case it was
written to catch. The remaining six correct overclaiming or stale prose, and remove two dead helpers.

**Files changed** (8; no file outside the spec's Code Map):
- `seed/state/store.py` -- NEW `is_opt_out_key(key)`: the grammar's asking half for an
  already-rendered key, so the planner need not split one back into halves or reach into
  `_opt_out_pattern`.
- `seed/state/__init__.py` -- re-export it (sorted `__all__`); docstring now says six helpers, and
  says why three of the six are public.
- `seed/detect/optout.py` -- `_marker_region_names` promoted to public `marker_region_names`;
  `opt_outs_to_record` takes `state` and returns DERIVED pairs only; three docstrings corrected
  (`marker_region_names`'s "over-detection is free", `_claims_region`'s "latent today",
  `_EMPTY_CATEGORIES`'s implied closure over "invisible").
- `seed/plan/build.py` -- `retained` widened via `marker_region_names`; element guard asks
  `is_opt_out_key`; dead `_current_text` / `_read_text_or_blank` wrappers removed and their prose
  merged into the `_verbose` survivors.
- `tests/unit/test_seed_state_store.py` -- `is_opt_out_key` coverage (admit/refuse/one-grammar
  agreement); the re-export test now asserts six.
- `tests/unit/test_seed_detect_optout.py` -- the derived-vs-recorded split, plus the two
  claim-preservation regressions (parser-invisible region, moved path); two stale docstrings fixed.
- `tests/unit/test_seed_plan_build.py` -- marker-variance fingerprint regressions (fenced,
  trailing-space) with a genuinely-deleted control; inadmissible-key-string cases; one pre-existing
  test re-fixtured off an inadmissible element it had been asserting was accepted.
- `tests/unit/test_seed_detect_findings.py` -- drop an assertion strictly implied by the next one.

**Review findings breakdown.** 9 patched (1 high, 3 medium, 5 low), 1 deferred (`DW-FU-8-5-11`),
9 rejected. No `intent_gap`, no `bad_spec`, so `review_loop_iteration` stays 0 and no code was
reverted.

**Verification performed** (all from the run worktree):
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- **4852 passed, 9 deselected**
  (4796 before this pass; +56 new).
- Each behavioural fix confirmed real by REVERTING it and watching only the intended tests fail:
  `retained` -> both marker-variance tests fail, the genuinely-deleted control still passes;
  `opt_outs_to_record`'s filter -> all three new optout tests fail; the element guard -> all four
  key-string cases fail.
- `pixi run -e local-recipes ruff check --statistics src/shared/packages/pyforge-marshal` -- run
  against the working tree AND against the same files restored to `HEAD`: **byte-identical
  statistics**, so no new finding categories and no new count.
- `pixi run -e local-recipes pyright <the four changed src files>` -- **0 errors, 0 warnings**.
- `pixi run --frozen -e pyforge-marshal lint-imports ... --no-cache` -- **Contracts: 4 kept, 0
  broken**. The new `plan -> detect.optout` edge is legal and precedented (`build.py` already
  imports `detect.hashes` and `detect.inventory`).
- `python scripts/spec_surface_reconcile.py` -- **rc=0**, "every tracked file governed or
  allowlisted; no drift".

**Residual risks.**
- `opt_outs_to_record`'s signature changed (`(statuses)` -> `(statuses, state)`). It has no
  production caller yet -- `cli/seed.py` is still print-only stubs -- so nothing outside the tests
  breaks, but S-10.5/S-10.6 must pass state when they wire it up.
- The element guard stops at the grammar, by design: a well-formed key naming an artifact this
  manifest does not have still suppresses nothing silently. Closing it would hard-fail the
  documented natural call (`opted_out=state.opted_out`) on an orphaned key nothing prunes.
- `marker_region_names` now feeds two consumers, so its over-detection residual (`DW-FU-8-5-11`)
  reaches the planner too -- where it only ever KEEPS an entry and its fingerprint pair, which is
  the safe direction.
- The station could not be resolved cleanly when minting the deferral: `resolve_config.py` answered
  `pyforge-mason` (a stale `BMAD_ACTIVE_PROJECT`) while the destination resolves under
  `projects/pyforge-marshal/`. Treated as unknown per procedure and flagged with the
  `station-unresolved:` token; the id shape is identical for both branches and matches every sibling
  entry, so nothing was mis-minted.
