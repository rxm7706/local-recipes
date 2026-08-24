---
title: 'Story 9.5: Manifest coverage check'
type: 'feature'
created: '2026-08-14'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: '24e401be14ed2e561ec2603adfbf4020d55fbf43'
baseline_revision: '57e972bc089f3ad14d0ffebc2feabb8ac9848c95'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `ManifestEntry.__post_init__` (S-7.4/7.5) already coerces `artifact_class` through
`ArtifactClass(...)` and requires a non-blank `rationale` on every entry, but that guarantee is
implicit and procedural -- nothing yet gives coverage its own explicit, testable, independently
verifiable definition the way `bmad_drift_check.py`'s (now `pyforge.doctor.sources.factory`'s)
`check_coverage` does for repo files (AD-54). Without it, SC-10's "100% manifest coverage" claim
rests entirely on the loader never having a bug, with no second, decoupled gate and no counts a
future report renderer can consume.

**Approach:** Add `coverage_findings(manifest) -> tuple[Finding, ...]` and
`coverage_counts(manifest) -> dict[str, int]` to `seed/detect/inventory.py`, mirroring the
`effective_never_write()`/`legacy_findings()` split S-9.4 already established: two small pure
functions over a `Manifest`, no `Inventory`/`repo_root` needed (coverage is intrinsic to the
manifest, not the target repo). Both explicitly re-verify `entry.artifact_class`/`entry.rationale`
rather than trusting the loader's guarantee -- defense in depth, matching this package's own
`Finding.__post_init__` remedy-validation stance.

## Boundaries & Constraints

**Always:**
- `coverage_findings(manifest: Manifest) -> tuple[Finding, ...]`: one `Finding.new(Severity.HARD,
  FindingType.UNCOVERED, entry.path, message)` per entry that fails coverage, in manifest entry
  order (matching `legacy_findings`'s own ordering convention).
- An entry fails coverage when EITHER: `entry.artifact_class` is not a genuine `ArtifactClass`
  member (checked via `isinstance`/membership, never assumed from the field's static type -- the
  defensive re-check this story exists to add), OR `entry.artifact_class is
  ArtifactClass.UNCLASSIFIED_DEFERRED` and `entry.rationale.strip()` is empty.
- Every other entry (a real class, and -- for `unclassified-deferred` -- a non-blank rationale)
  passes coverage and produces no finding.
- `coverage_counts(manifest: Manifest) -> dict[str, int]`: one bucket per class actually present,
  keyed by wire value (`entry.artifact_class.value`, e.g. `"copied-managed"`); an entry that fails
  coverage is counted under the literal key `"uncovered"` instead. Sparse (`Counter`-style, no
  zero-padded classes), matching `test_packaged_manifest_class_counts_match_the_spec_exactly`'s
  own `Counter(...)` convention. `sum(coverage_counts(manifest).values()) ==
  len(manifest.entries)` always holds.
- The real shipped `templates/manifest.yaml` (S-7.5) passes `coverage_findings` with zero
  findings, asserted by a new test in `test_seed_templates_manifest.py` -- the CI gate the AC
  requires ("a manifest edit that drops coverage fails CI").
- Both functions are read-only, pure, and import nothing beyond this module's existing
  `.findings`/`..model.manifest` imports.

**Block If:** None -- FR-69/SC-10 and S-9.1's `FindingType.UNCOVERED` (with its `REMEDIES` entry
already naming exactly this story's two failure modes) fully specify this behavior.

**Never:**
- No change to `ArtifactClass`, `FindingType`, `REMEDIES`, or `ManifestEntry.__post_init__` --
  `UNCOVERED` and its remedy already exist (S-9.1); this story adds its first producing call site.
- No repo-target/`Inventory` involvement -- coverage is a property of the manifest alone, unlike
  `classify()`'s per-entry filesystem check.
- No `unclassified-deferred` referential/count ceiling (e.g. "at most N deferred entries") --
  out of the AC.
- No change to `seed/model/manifest.py` -- investigation confirmed `rationale`/`artifact_class`
  are already unconditionally validated there; this story's checks are a deliberately redundant
  second gate, not a loader fix.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| All entries validly classed | mix of the 6 real classes, `unclassified-deferred` entries carry rationale | `coverage_findings` returns `()`; `coverage_counts` sums to `len(entries)` | No error |
| Forced invalid class | one entry's `artifact_class` force-set (`object.__setattr__`) to a raw string outside `ArtifactClass` | one `uncovered` HARD finding for that entry; counted under `"uncovered"` | No error |
| Deferred entry, forced blank rationale | `unclassified-deferred` entry, `rationale` force-set to `""`/whitespace | one `uncovered` HARD finding | No error |
| Deferred entry, real rationale | `unclassified-deferred`, non-blank rationale | no finding; counted under `"unclassified-deferred"` | No error |
| Multiple uncovered entries | two entries fail coverage for different reasons | two findings, manifest entry order | No error |
| Empty manifest | `entries == ()` | `coverage_findings` returns `()`; `coverage_counts` returns `{}` | No error |
| Real packaged manifest | `templates/manifest.yaml`, 43 entries | `coverage_findings` returns `()`; counts match `EXPECTED_CLASS_COUNTS` | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/inventory.py` -- MODIFIED:
  add `coverage_findings()` and `coverage_counts()`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/findings.py` -- reference
  only: `FindingType.UNCOVERED`, its `REMEDIES` entry, `Finding.new` consumed, not modified
  (already complete from S-9.1).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/model/manifest.py` -- reference
  only: `ArtifactClass`, `ManifestEntry.rationale` already validate; not modified.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_inventory.py` -- MODIFIED: add
  synthetic edge-case coverage tests (same module S-9.2/9.4 already own).
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_templates_manifest.py` -- MODIFIED: add
  the real-manifest CI-enforcing coverage test.

## Tasks & Acceptance

**Execution:**
- [x] `seed/detect/inventory.py` -- add `coverage_findings(manifest) -> tuple[Finding, ...]`,
  iterating `manifest.entries` in order, emitting one `uncovered` HARD `Finding` per entry that
  fails either coverage rule above.
- [x] same file -- add `coverage_counts(manifest) -> dict[str, int]`, bucketing every entry by
  class wire-value or `"uncovered"`.
- [x] `tests/unit/test_seed_detect_inventory.py` -- cover every I/O Matrix synthetic-state row.
- [x] `tests/unit/test_seed_templates_manifest.py` -- add the real-packaged-manifest coverage
  regression test (zero findings; counts match `EXPECTED_CLASS_COUNTS`).

**Acceptance Criteria:**
- Given a manifest entry with an unrecognized or missing class, when `coverage_findings` runs,
  then it yields exactly one `uncovered` HARD `Finding` naming that entry.
- Given an `unclassified-deferred` entry with a blank rationale, when `coverage_findings` runs,
  then it yields exactly one `uncovered` HARD `Finding`; given a non-blank rationale, then no
  finding is produced for that entry.
- Given the real packaged `templates/manifest.yaml`, when `coverage_findings` runs in this
  package's own test suite, then it returns zero findings -- so a future manifest edit that drops
  coverage fails CI.
- Given any manifest, when `coverage_counts` runs, then the returned counts sum to
  `len(manifest.entries)` exactly.

## Spec Change Log

## Review Triage Log

### 2026-08-14 — Review pass (Blind Hunter + Edge Case Hunter, parallel, no shared context)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 0, low 3)
- defer: 1: (high 0, medium 0, low 1)
- reject: 6: (high 0, medium 0, low 6)
- addressed_findings:
  - `[low]` `[patch]` Edge Case Hunter: `_uncovered_reason`'s `entry.rationale.strip()` had no type guard,
    asymmetric with the `isinstance` guard on `artifact_class` -- a `rationale` force-set to `None`
    raised `AttributeError` instead of producing an `uncovered` `Finding`, undermining the function's
    own stated "defense in depth" purpose. Added an `isinstance(entry.rationale, str)` guard alongside
    the existing blank check, and a new regression test
    (`test_coverage_findings_flags_a_deferred_entry_with_a_forced_non_str_rationale`).
  - `[low]` `[patch]` Blind Hunter: the two force-set-state tests asserted only `finding.path`/`"a" in
    finding.message` -- a substring trivially satisfied by "artifact_class"/"valid"/etc. regardless of
    whether `entry.id` was actually included, so swapping the two reason strings would go undetected.
    Replaced both with exact `==` assertions against the real message text.
  - `[low]` `[patch]` Blind Hunter: `coverage_counts()` hand-rolled `counts.get(key, 0) + 1` where
    `collections.Counter` already does the identical job, and the sibling test file this same diff
    touches already uses `Counter(...)` for the equivalent per-class tally. Rewrote to build from
    `Counter`, still returning a plain `dict[str, int]` (`Counter` is a `dict` subclass; the annotated
    return type is unchanged).
  - `[defer]` Blind Hunter (deduplicated from three related observations): `_uncovered_reason`'s two
    failure conditions are already fully and unconditionally enforced by `ManifestEntry.__post_init__`
    (S-7.4/7.5), so no manifest built through normal construction can ever make `coverage_findings`
    return non-empty, and the new CI-gate test on the real manifest is consequently near-tautological;
    separately, the check only validates a *declared* entry's internal shape, never reconciling against
    `Inventory`/the target repo, so it cannot catch the arguably more valuable "repo artifact absent
    from the manifest" or "entry class doesn't match reality on disk" readings of SC-10. Verified true
    against the live code (`model/manifest.py`'s `__post_init__`), and faithful to epics.md Story 9.5's
    literal, planning-approved AC -- not a defect this diff introduced, so not fixed here. Filed
    `DW-FU-9-5` in `deferred-work.md` for a future architecture-level look (possibly alongside S-9.6's
    plan builder or a later report-renderer story).
  - `[reject]` Blind Hunter: `coverage_counts()`'s literal `"uncovered"` bucket key could theoretically
    collide with a future `ArtifactClass` member given the identical wire value. `ArtifactClass` is this
    same codebase's own closed, reviewed enum (6 members today) -- purely theoretical, no real trigger
    path, matching this package's own precedent for rejecting no-blast-radius theoretical findings.
  - `[reject]` Blind Hunter: `coverage_counts()` returns a bare mutable `dict` rather than an immutable
    type (`REMEDIES`/`Inventory`/`LegacyRecord` precedent). Nothing internally caches or reuses this
    dict across calls, so external mutation has zero effect on the module's own invariants -- no real
    blast radius, and in tension with this same pass's own `Counter`-simplification patch (`Counter` is
    itself mutable).
  - `[reject]` Blind Hunter: `coverage_findings`/`coverage_counts` each independently loop over
    `manifest.entries`, in tension with this module's "walked once, cached" discipline. That discipline
    (NFR-P1/P2) is specifically about `_walk_tree`'s expensive filesystem I/O; `manifest.entries` is an
    in-memory tuple of 43 real-world items, so two O(n) passes over it is not the same concern and not
    measurably different from one -- a misapplied precedent.
  - `[reject]` Blind Hunter: no production call site yet consumes `coverage_findings`/`coverage_counts`.
    Precedented and expected -- identical to S-9.4's own `legacy_findings` situation (primitive now, a
    later story's `check`/plan-builder is the consumer), not a defect.
  - `[reject]` Blind Hunter: the module docstring's "S-9.5 adds this module's second and last [`Finding`
    construction]" is an unenforced claim about the future. Accurate as of this diff, and this exact
    diff itself demonstrates the convention is self-maintaining (it corrected S-9.4's own now-stale
    "only" claim to "first") -- not a new risk this diff introduces.
  - `[reject]` Blind Hunter: both coverage failure modes collapse into the same `Severity.HARD`/
    `FindingType.UNCOVERED`, with no structured way to distinguish "invalid class" from "blank
    deferral rationale". Matches epics.md's own explicit AC wording (one `uncovered` HARD finding for
    both cases) and `FindingType.UNCOVERED`'s already-singular S-9.1 definition -- spec-compliant by
    design, not a gap.

### 2026-08-14 — Review pass (Blind Hunter + Edge Case Hunter, parallel, no shared context; fresh
pass on a `done` spec per workflow routing, run after this story's implementation was recovered
from a preserved branch following an unrelated worktree reset -- the code under review is
byte-identical to the prior pass's final state)
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 2: (high 0, medium 0, low 2)
- reject: 6: (high 0, medium 0, low 6)
- addressed_findings:
  - `[low]` `[patch]` Blind Hunter: `test_coverage_findings_flags_a_deferred_entry_with_a_forced_non_str_rationale`
    was the only one of the three force-set-state tests that didn't assert `finding.path` -- both
    sibling tests (`..._invalid_artifact_class`, `..._forced_blank_rationale`) do. Added the missing
    `assert finding.path == "a.txt"`.
  - `[defer]` Blind Hunter: a second, independent review pass re-derived the same structural
    observation already filed as `DW-FU-9-5` (coverage is nearly unreachable via real construction,
    since `ManifestEntry.__post_init__` plus `_build_entry`'s own earlier coercion already close both
    failure modes) -- corroborating, not superseding, the existing entry. Per this workflow's
    instruction not to dedupe defer findings against the existing ledger, filed fresh as `DW-FU-9-5-2`.
  - `[defer]` Blind Hunter: `coverage_findings`/`coverage_counts` only see `Manifest.entries`, which
    `load_manifest` has already filtered to the manifest's own declared `model_version` via
    `in_range(...)` -- a staged (future `since`) or retired (past `until`) entry's corrupted
    `artifact_class`/`rationale` produces no signal. Consistent with S-7.4's pre-existing
    version-filtering design and this story's own "manifest alone, no repo-target" boundary, but in
    tension with FR-69's "every artifact" framing; a genuinely new angle not previously filed. Filed
    `DW-FU-9-5-3`.
  - `[reject]` Edge Case Hunter (independently corroborated by Blind Hunter): `_uncovered_reason`'s
    blank-rationale check only fires when `entry.artifact_class is ArtifactClass.UNCLASSIFIED_DEFERRED`,
    so a rationale force-corrupted on one of the other 5 classes goes unflagged even though
    `ManifestEntry.__post_init__` requires a non-blank rationale unconditionally on every class.
    Verified against the intent contract's own literal wording ("OR `entry.artifact_class is
    ArtifactClass.UNCLASSIFIED_DEFERRED` and `entry.rationale.strip()` is empty") -- this is the
    deliberate, spec-approved boundary, not a gap; the `Never` bullets bar expanding it here.
  - `[reject]` Blind Hunter + Edge Case Hunter (independently, same finding): `coverage_findings`
    passes `entry.path` straight into `Finding.new` with no defensive guard, unlike the `isinstance`
    guards on `artifact_class`/`rationale`; a force-corrupted blank `entry.path` would make
    `Finding.__post_init__` raise instead of reporting that entry as uncovered. Reachable only via the
    same double bypass (frozen-dataclass `object.__setattr__`) already established as no-blast-radius
    in this file's prior pass, and `coverage_findings` has zero production callers today (confirmed by
    grep) -- matches this package's own precedent for rejecting theoretical, no-real-trigger-path
    findings under this exact threat model.
  - `[reject]` Blind Hunter: `coverage_counts()` collapsing both failure reasons into one literal
    `"uncovered"` bucket loses the "invalid class" vs "blank rationale" distinction. Re-litigates a
    finding already rejected in the prior pass on identical grounds -- matches the intent contract's
    explicit Always bullet, spec-compliant by design.
  - `[reject]` Blind Hunter: neither function is wired into a CLI command or renderer yet, and unlike
    S-9.4's `legacy_findings` docstring, S-9.5's new docstring paragraph names no future consumer.
    Re-litigates the prior pass's rejected "no production call site yet" finding with a cosmetic
    documentation twist; adding a forward reference to a not-yet-existing consumer would itself be
    speculative content this codebase's conventions disfavor.
  - `[reject]` Blind Hunter: the "why `isinstance`, not truthiness" justification is written out in
    near-full prose across the module docstring, `_uncovered_reason`'s docstring, and two test
    docstrings. Matches this package's demonstrated house style of exhaustive per-function docstrings
    (see `model/manifest.py`, `detect/hashes.py`) rather than an accidental drift risk unique to this
    diff -- a style preference, not a defect.
  - `[reject]` Blind Hunter: `coverage_counts`'s sparse, never-zero-padded output means two manifests
    (or the same manifest before/after an edit) can produce dicts with different key sets, requiring
    callers to treat an absent key as zero. Matches the intent contract's explicit Always bullet
    ("Sparse ... no zero-padded classes") verbatim -- spec-compliant by design.

## Design Notes

**Why this duplicates a guarantee the loader already provides.** `ManifestEntry.__post_init__`
already makes an invalid class or blank rationale impossible to construct through
`load_manifest`. This story's checks are deliberately redundant: SC-10's "100% coverage" claim
should not rest on one code path never having a bug, matching AD-54's own precedent (a
second, independent gate) and this package's established "structural guarantee is not enough,
verify explicitly" convention (`Finding.__post_init__`'s remedy check). Tests reach the
otherwise-unreachable failure branches the same way `test_seed_model_version.py` already does:
`object.__setattr__` on an already-constructed frozen dataclass, forcing a post-construction state
`__post_init__` itself would have rejected.

**Function split, not one combined dataclass.** Mirrors S-9.4's own `effective_never_write()` /
`legacy_findings()` precedent -- two small, independently testable pure functions over the same
input, rather than a new `CoverageReport` wrapper type the AC does not ask for.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: full suite passes.
- `pixi run -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_inventory.py src/shared/packages/pyforge-marshal/tests/unit/test_seed_templates_manifest.py -q` -- expected: all pass, no regressions.

## Auto Run Result

Status: done

**Summary:** Added `coverage_findings(manifest)` and `coverage_counts(manifest)` to
`seed/detect/inventory.py` -- S-9.5's own explicit, independently testable second gate on SC-10's
"100% manifest coverage" claim. An entry fails coverage when its `artifact_class` isn't a genuine
`ArtifactClass` member, or it is `unclassified-deferred` with a blank/non-str `rationale`; every
other entry passes. Both functions share one private `_uncovered_reason()` definition so they can
never drift on what "covered" means, mirroring the `effective_never_write()`/`legacy_findings()`
split S-9.4 already established. The real packaged `templates/manifest.yaml` now has a CI-enforced
regression test asserting zero coverage findings and exact per-class counts.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/inventory.py` --
  `_uncovered_reason()`, `coverage_findings()`, `coverage_counts()` (`Counter`-built), module
  docstring extended.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_inventory.py` -- 7 new tests
  covering every I/O Matrix synthetic-state row plus the review-added non-str-rationale guard.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_templates_manifest.py` -- 2 new tests
  (zero findings on the real manifest; counts match `EXPECTED_CLASS_COUNTS`, derived not
  hand-duplicated).

**Review findings breakdown (first pass):** 10 distinct findings after dedup (Blind Hunter + Edge
Case Hunter, parallel, no shared context) -- 3 low-severity patches applied (an asymmetric
defensive-guard gap that let a force-set `None` rationale crash instead of reporting `uncovered`;
two weak substring-only test assertions strengthened to exact matches; a hand-rolled counter loop
simplified to `Counter`), 1 deferred (`DW-FU-9-5`: the coverage check is structurally redundant with
`ManifestEntry.__post_init__`'s pre-existing validation and doesn't reconcile against the target
repo -- real, faithful to the epics AC as given, not this diff's defect, flagged for a future
architecture-level look), 6 rejected (theoretical-only or no-blast-radius concerns, a misapplied
"walked once" precedent, and two findings that directly contradicted the epics AC's own explicit
design). 0 intent gaps, 0 bad-spec loopbacks.

**Recovery note (2026-08-14):** after the first review pass reached `done`, this worktree's branch
was reset behind the commit (`edd3a0ef98`) by an unrelated event elsewhere in the same bmad-loop
run (the ATTENTION log for run `20260813-094919-bfcb` shows a chain of prior epic-8/epic-9 stories
all deferring at landing on an identical "spec baseline does not match orchestrator-recorded
baseline" condition). The commit survived on this run's auto-preserve safety net
(`attempt-preserve/20260813-094919-bfcb-edd3a0ef`) and was recovered here via a clean `git merge
--ff-only` (HEAD was a strict ancestor of the preserved tip, zero conflicts, zero data loss) before
re-running this workflow's `done`-spec routing, which always re-reviews from scratch.

**Review findings breakdown (second pass, fresh, no shared context with the first):** 9 distinct
findings (Blind Hunter + Edge Case Hunter) -- 1 low-severity patch applied (a copy-paste gap: the
non-str-rationale force-set test was the only one of its three-test sibling group not asserting
`finding.path`), 2 deferred (`DW-FU-9-5-2`: independent re-derivation of the same structural
redundancy already in `DW-FU-9-5`, filed fresh per this workflow's no-dedupe instruction rather than
consolidated; `DW-FU-9-5-3`: a new angle -- `load_manifest`'s pre-existing `since`/`until`
version-filtering makes a staged/retired entry's corrupted class/rationale invisible to coverage at
the manifest's own declared version), 6 rejected (a rationale-scoping question and an unguarded
`entry.path` crash risk that both match the intent contract's literal, deliberate design under the
established no-blast-radius/force-set-bypass precedent, plus four findings that re-litigated
already-rejected first-pass territory on identical spec-compliance grounds). 0 intent gaps, 0
bad-spec loopbacks. Both passes' findings converge on the same conclusion: the implementation is
spec-compliant; every non-cosmetic gap traces to the intent contract's own deliberate scope, not to
a defect in this diff.

**Verification performed:** `pixi run -e pyforge-marshal pyforge-marshal-test` -- 3809 passed, 9
deselected (unchanged from the first pass; the second pass's only code change is one added
assertion in an existing test, not a new test). Targeted `test_seed_detect_inventory.py` +
`test_seed_templates_manifest.py` -- 83 passed. `ruff check` on `inventory.py` and both touched test
files -- all checks passed.

**Residual risks:** None blocking. `DW-FU-9-5`, `DW-FU-9-5-2`, and `DW-FU-9-5-3` (filed above) are
real, out-of-scope architectural questions for a later story, not defects in this diff. The coverage
check has no production call site yet (CLI/`check`/plan-builder wiring is a later epic's job,
matching S-9.4's `legacy_findings` precedent).
