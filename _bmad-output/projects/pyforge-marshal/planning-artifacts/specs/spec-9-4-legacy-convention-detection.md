---
title: 'Story 9.4: Legacy convention detection'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: '57e972bc089f3ad14d0ffebc2feabb8ac9848c95'
baseline_revision: '744a0ee3bd29f82bea07de40e718a62f17119786'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** S-9.2's classifier has no producing path for `ArtifactState.PRESENT_LEGACY` yet, so
a manifest entry marking itself superseded (`legacy_of: <successor-id>`) is classified by its
ordinary class rules and can be targeted by a future plan action -- exactly the "adopting the
model destroys a live legacy convention" failure AD-59 exists to prevent.

**Approach:** Extend `seed/detect/inventory.py`: when a `legacy_of`-bearing entry's path is
present, classify it `present-legacy` unconditionally (before any class-specific structural
check), collect it into a new `Inventory.legacy: tuple[LegacyRecord, ...]`, and add two small
consumers: `effective_never_write()` (folds legacy paths into the manifest's `never_write` set)
and `legacy_findings()` (one INFO `legacy-present` `Finding` per legacy record, naming the
successor).

## Boundaries & Constraints

**Always:**
- A present entry with `legacy_of is not None` classifies `present-legacy`, regardless of its
  `artifact_class` (including a `hybrid-managed-region` entry whose declared regions would
  otherwise make it `present-divergent` -- legacy content is never write-inspected once
  recognized, matching AD-59's "never written to").
- An absent `legacy_of`-bearing entry stays `absent` -- legacy classification requires presence.
- `Inventory` gains `legacy: tuple[LegacyRecord, ...]`, one `LegacyRecord(entry_id, path,
  legacy_of)` per entry classified `present-legacy`, built by `classify()` in the same single
  walk (no second pass, no extra filesystem access beyond what `_classify_entry` already does).
- `effective_never_write(manifest, inventory) -> frozenset[str]` returns
  `manifest.never_write` union every `LegacyRecord.path` -- the primitive a later plan builder
  (S-9.6) consumes so no `Action` targets a legacy artifact.
- `legacy_findings(inventory) -> tuple[Finding, ...]` returns one `Finding.new(Severity.INFO,
  FindingType.LEGACY_PRESENT, record.path, message)` per `LegacyRecord`, with `message` naming
  both the artifact path and `record.legacy_of` (the successor id) -- never `HARD`/`DRIFT`.
- The canonical worked example (AD-59 / epics AC) is proven by a self-contained test fixture
  using the real manifest's own ids -- `specs-dir-legacy` (`docs/specs/`) with `legacy_of:
  "planning-artifacts-symlink"` -- not by editing the shipped `templates/manifest.yaml`.

**Block If:** None -- AD-59/FR-81 and S-9.2's existing classifier fully specify this behavior;
nothing here requires human input.

**Never:**
- No `.marshal/seed-state.yml` read or write -- `state/store.py` does not exist yet (a later
  epic); `LegacyRecord` is the pure in-memory precursor a future state store serializes into
  `state.legacy[]`, mirroring S-9.3's own `recorded_sha`-is-a-parameter precedent.
- No automated Tier-1 -> Tier-2 migration logic of any kind (AD-59, explicitly out of V1).
- No edit to `seed/templates/manifest.yaml` -- wiring `legacy_of` onto the real `specs-dir-legacy`
  entry is a separate follow-up (this story's own Surface is `inventory.py`/`findings.py` only);
  see Design Notes.
- No `Action`/plan-exclusion logic -- S-9.6 (`Deps: S-9.2, S-9.3, S-9.4`) consumes
  `effective_never_write()`/`Inventory.legacy`; this story only produces them.
- No change to `ArtifactState`, `FindingType`, or `REMEDIES` -- `PRESENT_LEGACY` and
  `LEGACY_PRESENT` already exist (S-9.2/S-9.1); this story adds their first producing call site.
- No `check`/CLI rendering of `legacy_findings()`'s output -- a later epic's renderer.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Legacy artifact present | whole-file entry, `legacy_of="succ"`, path exists | `present-legacy`; one `LegacyRecord` in `Inventory.legacy` | No error |
| Legacy artifact absent | `legacy_of="succ"`, path does not exist | `absent`; no `LegacyRecord` | No error |
| Legacy hybrid-region, regions missing | `legacy_of` set, `hybrid-managed-region`, declared region not found | `present-legacy` (never `present-divergent` -- legacy short-circuits the structural check) | No error |
| Referenced entry with `legacy_of` set | `artifact_class=referenced`, `legacy_of="succ"` | `present-conformant` (referenced is never materialized; legacy_of not consulted) | No error |
| Canonical worked example | `id=specs-dir-legacy`, `path="docs/specs/"`, `legacy_of="planning-artifacts-symlink"`, dir present | `present-legacy`; `legacy_findings()` message names `planning-artifacts-symlink` | No error |
| No legacy entries in manifest | every entry's `legacy_of is None` | `Inventory.legacy == ()`; `legacy_findings()` returns `()` | No error |
| `effective_never_write` with a present legacy artifact | manifest `never_write=("a/*",)`, one `LegacyRecord(path="docs/specs/")` | returns `frozenset({"a/*", "docs/specs/"})` | No error |
| Multiple legacy entries | two entries, both present with `legacy_of` set | two `LegacyRecord`s, in manifest entry order; two INFO findings | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/inventory.py` -- MODIFIED:
  `_classify_entry` gains the legacy short-circuit; new `LegacyRecord` frozen dataclass;
  `Inventory.legacy` field; `classify()` populates it; new `effective_never_write()` and
  `legacy_findings()` functions.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/findings.py` -- reference
  only: `Finding`, `FindingType.LEGACY_PRESENT`, `Severity.INFO` consumed, not modified (already
  complete from S-9.1).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/manifest.py` -- reference
  only: `ManifestEntry.legacy_of` already exists and validates (S-9.3).
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_inventory.py` -- MODIFIED: add
  legacy-related cases to the existing suite (same module, same file S-9.2 already owns).

## Tasks & Acceptance

**Execution:**
- [x] `seed/detect/inventory.py` -- add `LegacyRecord(entry_id, path, legacy_of)` frozen
  dataclass and `Inventory.legacy: tuple[LegacyRecord, ...]` field.
- [x] same file -- in `_classify_entry`, after the presence check and before the
  `HYBRID_MANAGED_REGION` structural branch, short-circuit to `ArtifactState.PRESENT_LEGACY`
  when `entry.legacy_of is not None`.
- [x] same file -- in `classify()`, build `Inventory.legacy` from every entry whose computed
  state is `PRESENT_LEGACY` (single pass, reusing the already-computed classifications).
- [x] same file -- add `effective_never_write(manifest, inventory) -> frozenset[str]`.
- [x] same file -- add `legacy_findings(inventory) -> tuple[Finding, ...]`, importing `Finding`/
  `FindingType`/`Severity` from `.findings`.
- [x] `tests/unit/test_seed_detect_inventory.py` -- cover every I/O Matrix row, including the
  canonical `specs-dir-legacy`/`planning-artifacts-symlink` worked example.

**Acceptance Criteria:**
- Given a manifest entry carrying `legacy_of: <successor-id>`, when detect finds it present,
  then it is classified `present-legacy` and captured in `Inventory.legacy`.
- Given a present `present-legacy` artifact, when `effective_never_write` is called, then its
  path is included in the returned set alongside the manifest's own `never_write` patterns.
- Given `Inventory.legacy`, when `legacy_findings` is called, then each record yields exactly one
  `Finding` at `Severity.INFO` with `type=FindingType.LEGACY_PRESENT`, whose message names the
  successor id -- never `HARD` or `DRIFT`.
- Given the canonical `docs/specs/*.md` case (fixture ids `specs-dir-legacy` ->
  `planning-artifacts-symlink`), when classified, then the artifact is preserved (never read for
  content, never targeted), recorded, and its successor named.
- Given this story's full diff, when grepped, then no migration logic, state-file I/O, or
  `templates/manifest.yaml` edit is present.

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass (Blind Hunter + Edge Case Hunter, parallel, no shared context)
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 0, low 4)
- defer: 0
- reject: 9: (high 0, medium 0, low 9)
- addressed_findings:
  - `[low]` `[patch]` Blind Hunter: `test_multiple_legacy_entries_yield_records_and_findings_in_manifest_order`
    only ever included legacy entries, so a bug that reordered `Inventory.legacy` relative to a
    non-legacy entry (rather than relative to other legacy entries) would pass undetected. Added
    `test_legacy_records_ordered_correctly_when_interleaved_with_non_legacy_entries`, asserting
    both `Inventory.legacy` and `Inventory.classifications` order with a non-legacy entry
    interleaved between two legacy ones.
  - `[low]` `[patch]` Blind Hunter: `_referenced`'s signature was left as one long line while
    `_whole_file`/`_hybrid` were reflowed across multiple lines when they grew a `legacy_of`
    kwarg, an inconsistency introduced within this same diff. Reflowed `_referenced` to match.
  - `[low]` `[patch]` Blind Hunter: `test_canonical_specs_dir_legacy_worked_example` asserted
    `legacy_findings()`'s message only via `in` substring checks, which would still pass if the
    message were reordered or otherwise degraded. Replaced with one exact `==` assertion against
    the full message string.
  - `[low]` `[patch]` Blind Hunter: `test_effective_never_write_unions_manifest_patterns_with_legacy_paths`
    only exercised disjoint `never_write`/legacy-path inputs, leaving the "union, not
    concatenation" claim partially unproven. Added
    `test_effective_never_write_dedupes_when_legacy_path_already_in_never_write`, where the
    legacy path is already literally present in `never_write`.
  - `[reject]` Blind Hunter: flagged `FindingType.LEGACY_PRESENT`/`REMEDIES` and
    `ManifestEntry.legacy_of` as "unverified dependencies" absent from the diff. Both were
    verified to already exist (from prior stories S-9.1/S-9.3, out of this diff's own scope) by
    reading the live files and by the full suite passing (3800/3800).
  - `[reject]` Blind Hunter + Edge Case Hunter: `assert entry.legacy_of is not None` in
    `classify()` is stripped under `-O`/`PYTHONOPTIMIZE`. This is type-narrowing for a state this
    module already guarantees by construction (the only path to `PRESENT_LEGACY` sets it), and
    matches this exact file's own pre-existing precedent (`assert entry.format is not None` in
    `_classify_hybrid`) -- not a new pattern this diff introduced.
  - `[reject]` Blind Hunter: `Inventory` gained a defaultless `legacy` field, a theoretical
    breaking change to direct `Inventory(...)` construction. Verified empirically (`grep`) that
    no call site anywhere in `src/` or `tests/` constructs `Inventory(...)` directly outside
    `classify()` itself -- zero actual blast radius.
  - `[reject]` Blind Hunter + Edge Case Hunter: no cycle guard (`legacy_of` self-reference or
    A->B->A chains) and no referential check that `legacy_of` names a real manifest id. Neither
    is in this story's or S-9.5's AC; a malformed manifest is caught by human review of the
    manifest diff (the file's own established philosophy, per `model/manifest.py`'s docstring),
    and neither failure mode crashes or silently corrupts data -- out of this story's scope, not
    a defect it introduced.
  - `[reject]` Blind Hunter + Edge Case Hunter: `effective_never_write` trusts its
    `manifest`/`inventory` arguments are a matched pair, with no cross-check. Matches this
    package's established purity convention (`hashes.py`'s own "caller-supplied parameter, not
    re-verified" precedent) -- caller-pairing correctness is S-9.6's job as the function's actual
    consumer, not this story's.
  - `[reject]` Blind Hunter: raw legacy paths (e.g. `docs/specs/`) mix with glob-style
    `never_write` patterns in the same returned set with no documented reconciliation. This
    mixing is pre-existing in `manifest.never_write` itself (already a mix of literal and glob
    entries before this story); how a consumer treats the union is S-9.6's documented job, not
    this story's.
  - `[reject]` Blind Hunter: docstring claims about matching `hashes.py`'s own import/construction
    precedent were "unverifiable" since `hashes.py` wasn't in the diff shown to the reviewer.
    Verified directly against the live file: `hashes.py` does import `from .findings import
    Finding, FindingType, Severity` and construct via `Finding.new`, exactly as claimed.

### 2026-08-14 — Review pass (fresh pass, spec status was `done`)

Before this pass, the run's branch had been reset back to a point before Story 9.4's committed
work (reflog: `reset: moving to 26102ea12c`, discarding the `merge origin/main` + epic-9-chain
merge + the story-9.4 commit itself). The story-9.4 commit (`a71b81c4cf`) survived on the
run's auto-preserved `attempt-preserve/20260813-094919-bfcb-a71b81c4` branch and was a clean
fast-forward ahead of this branch's post-reset `HEAD`, so it was restored via `git merge
--ff-only` (no conflicts, no data loss) before this review pass ran, per the fleet-wide
non-destructive-recovery standing policy. Verified restored state matches the spec's prior
`Auto Run Result` exactly: `pyforge-marshal-test` 3800 passed / 9 deselected, targeted
`test_seed_detect_inventory.py` 56 passed, both before and after this pass's own patch below.

- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 1: (high 0, medium 0, low 1)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[low]` `[patch]` Blind Hunter: `test_canonical_specs_dir_legacy_worked_example`'s docstring
    claims to use "the real manifest's own ids" but built its fixture with
    `ArtifactClass.COPIED_MANAGED`, while the shipped `templates/manifest.yaml`'s real
    `specs-dir-legacy` entry is `generated-derived`. Functionally inert (the legacy short-circuit
    is class-agnostic for any non-`referenced` class), but the "canonical worked example" claim
    should be fully accurate, not just id-accurate. Changed the fixture to
    `ArtifactClass.GENERATED_DERIVED` to match the real entry.
  - `[low]` `[defer]` Blind Hunter: `epics.md` Story 9.4's AC literally names a glob
    (`docs/specs/*.md` present ⇒ preserved, recorded) for the canonical worked example, but
    `_classify_entry`'s presence check (`Path.exists()`) never glob-expands `path` -- a future
    manifest author who took that AC wording literally would get a silent `absent`
    misclassification. Both the real manifest and this story's own spec already correctly use
    the bare directory `docs/specs/` instead (pre-existing, non-globbing presence-check semantics
    unchanged since S-9.2), so nothing is actually broken -- only the AC prose is stale. Filed
    `DW-FU-9-4` in `deferred-work.md` for a future editorial pass over Epic 9's AC wording; out of
    this story's Surface (`inventory.py`/`findings.py`, not `epics.md`).
  - `[reject]` Blind Hunter + Edge Case Hunter: no `legacy_of` referential-integrity check (dangling
    successor id, self-reference, or a cycle). Exact repeat of the prior pass's rejection --
    neither this story's nor S-9.5's AC requires it; a malformed manifest is caught by human
    review of the manifest diff, and neither failure mode crashes or corrupts data. Same reasoning
    holds unchanged.
  - `[reject]` Blind Hunter + Edge Case Hunter: `effective_never_write` trusts its `manifest`/
    `inventory` arguments are a matched pair, with no cross-check. Exact repeat of the prior pass's
    rejection -- matches this package's established purity convention (`hashes.py`'s own
    caller-supplied-parameter precedent); caller-pairing correctness is S-9.6's job.
  - `[reject]` Blind Hunter: `effective_never_write` mixes glob-style `never_write` patterns with
    literal legacy paths in one flat set, with no documented reconciliation. Exact repeat of the
    prior pass's rejection -- this mixing is pre-existing in `manifest.never_write` itself; how a
    consumer treats the union is S-9.6's documented job, not this story's.
  - `[reject]` Blind Hunter + Edge Case Hunter: bare `assert entry.legacy_of is not None` in
    `classify()` is stripped under `-O`/`PYTHONOPTIMIZE`. Exact repeat of the prior pass's
    rejection -- type-narrowing for a state this module already guarantees by construction,
    matching this exact file's own pre-existing `_classify_hybrid` precedent.
  - `[reject]` Edge Case Hunter: `Inventory` gaining a defaultless `legacy` field is a theoretical
    breaking change to direct `Inventory(...)` construction. Exact repeat of the prior pass's
    rejection -- re-verified empirically (`grep`) that `Inventory(...)` is still constructed
    nowhere in `src/` or `tests/` except inside `classify()` itself.
  - `[reject]` Edge Case Hunter: `legacy_of=""` (empty string) is not guarded at the
    `_classify_entry` call site, only `is not None`. Verified false against the live code:
    `model/manifest.py`'s `_require_text` already rejects a blank or whitespace-only `legacy_of`
    in `ManifestEntry.__post_init__` (lines 357-359), so `""` can never reach `_classify_entry`.
  - `[reject]` Edge Case Hunter: `legacy_findings()`'s message f-string doesn't escape apostrophes
    in `path`/`legacy_of`. This is a plain human-readable `Finding.message`, not embedded in
    JSON/shell/HTML where escaping matters, and both fields are manifest-controlled (git-reviewed)
    -- not a real defect.
  - `[reject]` Blind Hunter: no structural (type-level) guarantee that `Inventory.legacy` agrees
    with `Inventory.classifications` -- enforced only procedurally, inside `classify()`. Matches
    this file's own established convention: `Classification`/`LegacyRecord` both explicitly carry
    zero `__post_init__` validation because they are `classify()`'s pure computed output, not a
    new pattern this diff introduces.

## Design Notes

**Why `templates/manifest.yaml` is not wired here.** The real `specs-dir-legacy` entry (path
`docs/specs/`) is the live Tier-1 case AD-59's worked example names, and marking it
`legacy_of: planning-artifacts-symlink` would turn this feature on for this repo. This story's
own epics Surface line names only `inventory.py`/`findings.py`, and its AC says the canonical
case is "covered by test" -- not "wired into the shipped manifest". Deferring the manifest edit
also avoids a premature product decision this story doesn't need to make: `check`/`adopt` don't
exist yet (Epic 10), so flipping the real manifest now has no observable effect and only adds
diff surface unrelated to this story's engine capability. Flagged here for whichever story wires
`check`/`adopt` end-to-end to revisit.

**Why the legacy short-circuit runs before, not after, the hybrid-region structural check.**
AD-59 frames `present-legacy` as "never written to" -- Genesis stops caring about a legacy
artifact's internal structure once recognized, so a `hybrid-managed-region` entry that also
carries `legacy_of` must not fall through to `present-divergent` for a missing declared region;
the legacy state is unconditional on presence alone.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** Extended `seed/detect/inventory.py`'s classifier so a manifest entry carrying
`legacy_of` classifies `present-legacy` unconditionally once present (ahead of every
class-specific structural rule), is collected into a new `Inventory.legacy` in the same single
walk, and feeds two new consumers: `effective_never_write()` (folds legacy paths into the
manifest's `never_write` set) and `legacy_findings()` (one INFO `legacy-present` `Finding` per
record, naming the successor).

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/inventory.py` -- `LegacyRecord`
  dataclass, `Inventory.legacy` field, the legacy short-circuit in `_classify_entry`, `classify()`
  updated to build `Inventory.legacy` in its existing single pass, `effective_never_write()`,
  `legacy_findings()`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_inventory.py` -- 10 new tests
  covering every I/O Matrix row plus the two interleaving/dedup cases added during review.

**Review findings breakdown:** 13 distinct findings (Blind Hunter + Edge Case Hunter, parallel,
no shared context) -- 4 low-severity patches applied (test-coverage gaps: missing interleaved-
order test, one substring-only message assertion, one missing never_write-overlap case; plus one
cosmetic signature-formatting inconsistency), 9 rejected (2 verified false against the live
codebase -- claimed-missing S-9.1/S-9.3 dependencies that already exist; the rest verified
out-of-scope or matching this file's own established precedent). 0 deferred, 0 intent gaps, 0
bad-spec loopbacks.

**Verification performed:** `pixi run -e pyforge-marshal pyforge-marshal-test` -- 3800 passed, 9
deselected (was 3798 before the two review-added tests). Targeted
`test_seed_detect_inventory.py` -- 56 passed (was 46 before this story, +10). `ruff check` on
both changed files -- all checks passed. `tests/meta` (716 tests, incl. AD-3/AD-4 import-boundary
contracts) verified green, confirming the new `detect/inventory.py -> detect/findings.py` sibling
import violates no module-dependency rule.

**Residual risks:** None blocking. Two rejected review findings (no cross-entry `legacy_of`
referential-integrity check; no cycle guard for a malformed `A->B->A` chain) are real but
out-of-scope gaps a future manifest-validation story (in S-9.5's territory, or later) could close
-- neither crashes or silently corrupts data today. The real `templates/manifest.yaml` still has
no `legacy_of`-bearing entry (a deliberate scope decision, see Design Notes); wiring it is a
follow-up for whichever story turns on `check`/`adopt` end-to-end.

---

**2026-08-14 recovery + fresh review pass.** This dev-auto worktree's branch was found reset
past its recorded `baseline_revision`, back to the worktree's very creation point (`git reflog`:
`reset: moving to 26102ea12c`), discarding the `merge origin/main` step, the epic-9-chain merge,
and this story's own commit (`a71b81c4cf`) -- all previously reviewed and verified `done`, per
the section above. The story commit survived on the run's auto-preserved
`attempt-preserve/20260813-094919-bfcb-a71b81c4` branch and was a clean fast-forward ahead of the
reset `HEAD`, so it was restored via `git merge --ff-only` (zero conflicts, zero data loss) rather
than re-implemented, per the fleet's non-destructive-escalation-recovery standing policy. Restored
state was verified to reproduce the original `pyforge-marshal-test` (3800/9) and targeted-suite
(56 passed) results exactly before this pass's own review ran.

A second, independent Blind Hunter + Edge Case Hunter pass then ran fresh (no prior-pass context)
against the same `baseline_revision`-relative diff, per this workflow's `done`-spec re-invocation
rule. Of 10 distinct findings: 1 low-severity patch applied (`test_canonical_specs_dir_legacy_worked_example`
now uses `ArtifactClass.GENERATED_DERIVED`, matching the real manifest's actual `specs-dir-legacy`
class rather than an arbitrary stand-in), 1 low-severity item deferred (`DW-FU-9-4` --
`epics.md`'s Story 9.4 AC prose names a glob the presence-check semantics can't honor; the real
manifest and this story's own spec already sidestep it correctly, only the AC wording is stale),
and 8 rejected (6 exact repeats of findings the original pass already adjudicated with unchanged
reasoning; 2 newly verified false against the live code -- `legacy_of=""` is already rejected by
`model/manifest.py`'s `_require_text`, and apostrophe-escaping in a plain human-readable
`Finding.message` is not a real defect). Post-patch: `pyforge-marshal-test` still 3800 passed / 9
deselected; targeted suite still 56 passed; `ruff check` clean. No follow-up review recommended --
this pass's only code change was one functionally-inert test-fixture class swap.
