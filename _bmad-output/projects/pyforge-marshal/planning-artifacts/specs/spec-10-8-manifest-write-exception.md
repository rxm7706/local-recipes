---
title: 'Manifest-declared writable artifacts are exempt from their own never-write collision'
type: 'bugfix'
created: '2026-08-21'
status: 'done'
baseline_revision: '81e79c2637337368e73f71a5d049faf41115b532'
final_revision: '60fb525191'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** `effective_never_write` unions `manifest.never_write` GLOB patterns with legacy
paths, but two manifest entries the extraction manifest itself marks writable —
`dreams-readme` (`docs/dreams/README.md`, `copied-managed`, `applies_to: both`) and
`specs-readme` (`.../planning-artifacts/specs/README.md`, `copied-seeded`, `applies_to: init`)
— also match a broad `never_write` glob (`docs/dreams/*.md`, `**/planning-artifacts/**`).
`check_preconditions` rung 4 and `fs._guard` both refuse on ANY pattern match with no
per-artifact override, so `marshal seed adopt --apply` refuses its own `dreams-readme` write
unconditionally (confirmed: `adopt` is already merged and already broken against the real
manifest); the same collision blocks `init`'s `specs-readme` write once 10.7 lands.

**Approach:** fnmatch globs cannot express "match `docs/dreams/*.md` except this one literal
path" (no negation) — narrowing the glob string itself is not possible without silently
widening protection for every other file under it (forbidden by AC). The guard therefore needs
an explicit allow-list checked BEFORE the glob deny-list, not a modified glob. Add
`NeverWrite.exempt: frozenset[str]` (exact resolved paths, checked first, bypassing pattern
matching entirely) and a new `inventory.writable_exemptions(manifest, inventory)` that computes
it: every `copied-managed`/`copied-seeded` entry's path in the (caller-pre-filtered-by-verb)
manifest, minus any path already in `inventory.legacy` (AD-59 still wins). `effective_never_write`
itself is unchanged — it stays the pure deny-list; `writable_exemptions` is the new allow-list.

## Boundaries & Constraints

**Always:**
- `writable_exemptions` trusts `manifest.entries` as given (already `applies_to`-filtered by the
  caller, exactly as `effective_never_write` already trusts `manifest.never_write` as given) —
  it does not itself inspect `entry.applies_to` against "the running verb."
- Exemption classes are exactly `COPIED_MANAGED`/`COPIED_SEEDED` (the epics AC's own two named
  classes) — `REFERENCED`, `GENERATED_DERIVED`, `HYBRID_MANAGED_REGION`, `UNCLASSIFIED_DEFERRED`
  are never exempted this way.
- A path in `inventory.legacy` is NEVER exempted even if it is also a manifest-declared writable
  path at the same location (AD-59 wins) — subtract legacy paths from the exempt set.
- `NeverWrite.exempt` defaults to `frozenset()` so every existing `NeverWrite(...)` construction
  (prod and test) stays valid unchanged.
- `fs._matches` and `check_preconditions` rung 4 each gain their OWN `relative in
  never_write.exempt` short-circuit (checked before pattern matching) — they must keep agreeing
  with each other, matching this package's existing "two matchers pinned by an agreement test"
  convention (`preconditions.py`'s own module docstring already states this).
- `run_adopt`'s `never_write = fs.NeverWrite(...)` construction gains
  `exempt=writable_exemptions(filtered_manifest, inventory)`.

**Block If:** none — the mechanism is fully determined by direct reading of `fs.py`/
`preconditions.py`/`inventory.py`/`manifest.py`; no undecidable question found.

**Never:**
- Do not touch `skips.first_match` or `--skip` semantics — the exempt check is a SEPARATE
  short-circuit in `preconditions.py`'s rung-4 loop body, not a change to `first_match` itself
  (which stays shared, unmodified, with `--skip`).
- Do not modify `build_plan`, `classify`, or any other already-shipped Epic 9/10 primitive.
- Do not touch `seed/verbs/init.py` (unmerged, Story 10.7's own surface) — 10.7 resumes after
  this lands and will itself add one line (`exempt=writable_exemptions(...)`) mirroring adopt's.
- The literal CLI command `marshal seed init` cannot be exercised by this story: `cli/seed.py`'s
  `run_init` is still the Story 7.1 stub on `main` (10.7 unmerged). This story's own proof that
  the mechanism works end-to-end against the REAL packaged manifest uses the already-shipped
  `run_adopt` verb and `dreams-readme` (`applies_to: both`, so `adopt` reaches it) — NOT
  `specs-readme` (`applies_to: init`-only; `_manifest_for_adopt`'s existing Story-10.6 filter
  correctly excludes it from every adopt run, unrelated to this fix). The epics AC's "adopt...
  writes both" line is imprecise on this point; `specs-readme` is verified once `init` lands.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `adopt --apply --yes`, real manifest, fresh repo missing `docs/dreams/README.md` | clean git repo | `dreams-readme` materialized; run completes | none |
| Same, but the entry is ALSO `present-legacy` (hypothetical future manifest) | `legacy_of` set | never_write still refuses (legacy wins) | `PreconditionFailure` |
| A path matches `docs/dreams/*.md` but is NOT a manifest-declared writable path | e.g. a real other dream file | still refused normally | `PreconditionFailure` / `NeverWriteViolation` |
| `fs.write` called directly on an exempt path | `never_write.exempt` contains it | write succeeds, guard bypassed | none |
| `NeverWrite(patterns=(...))` with no `exempt` kwarg (every pre-existing call site) | — | behaves exactly as before (empty exempt) | none |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/fs.py` -- `NeverWrite` gains
  `exempt: frozenset[str] = frozenset()` (validated in `__post_init__`, mirroring `patterns`'
  own coercion/strip/non-blank rules); `_matches` short-circuits `None` when the candidate path
  is in `never_write.exempt`, before the pattern loop.
- `.../seed/verbs/preconditions.py` -- rung 4's loop gains `if relative in never_write.exempt:
  continue` before its `first_match(never_write.patterns, relative)` call.
- `.../seed/detect/inventory.py` -- new `_WRITABLE_EXEMPTION_CLASSES` constant + new
  `writable_exemptions(manifest, inventory) -> frozenset[str]`; `effective_never_write` body
  unchanged, docstring gains a short cross-reference.
- `.../seed/verbs/adopt.py` -- import `writable_exemptions`; `run_adopt`'s `never_write =
  fs.NeverWrite(...)` line gains `exempt=writable_exemptions(filtered_manifest, inventory)`.
- `tests/unit/test_seed_fs.py` -- NEW: `exempt` bypasses a matching pattern; a non-exempt path
  matching the same pattern still refuses; default `exempt=frozenset()` is backward compatible.
- `tests/unit/test_seed_verbs_preconditions.py` -- NEW: rung 4 skips an exempt action; a
  different, non-exempt action in the same plan still refuses.
- `tests/unit/test_seed_detect_inventory.py` -- NEW: `writable_exemptions` includes
  copied-managed/copied-seeded, excludes the other four classes, subtracts legacy paths.
- `tests/unit/test_seed_verbs_adopt.py` -- NEW: `run_adopt(..., apply=True, yes=True)` against
  the REAL packaged manifest (`manifest=None` default) and a fresh git repo missing
  `docs/dreams/README.md` completes and materializes it (previously refused unconditionally).

## Tasks & Acceptance

**Execution:**
- [x] `fs.py` -- add `NeverWrite.exempt`, wire the `_matches` short-circuit.
- [x] `verbs/preconditions.py` -- rung 4 exempt short-circuit.
- [x] `detect/inventory.py` -- `writable_exemptions`.
- [x] `verbs/adopt.py` -- wire `exempt=` into `run_adopt`'s `NeverWrite` construction.
- [x] Unit tests per Code Map, covering every I/O Matrix row.
- [x] Real-manifest integration test proving `run_adopt` now succeeds where it previously
  refused (the story's own confirmed-live defect).

**Acceptance Criteria:**
- Given the real packaged manifest and a fresh git repo missing `docs/dreams/README.md`, when
  `run_adopt(..., apply=True, yes=True)` runs, then it completes and materializes the file
  (previously: unconditional refusal).
- Given a manifest entry with `legacy_of` set that also matches a manifest writable-artifact
  path, when `writable_exemptions` runs, then that path is NOT in the result.
- Given a real dream file (not a manifest-declared writable path) matching `docs/dreams/*.md`,
  when any write is attempted, then it is still refused (never-write still functions normally).
- Given every existing `NeverWrite(...)` construction in the current test suite (no `exempt`
  kwarg), when the suite runs, then all pass unchanged.

## Spec Change Log

- **Test-implementation deviation (not an intent-contract change), found during
  implementation of the real-manifest `verbs/adopt.py` integration test.** The
  test's first draft materialized `dreams-readme` by injecting a synthetic
  `template_path` (this file's usual whole-file test seam, per the Code Map's
  own suggestion), routing through the real `_default_commit` ->
  `engine.copier.materialize()`. That path failed with `TemplateBoundaryError`
  from a SEPARATE, pre-existing guard this story does not touch:
  `engine/copier.py::_check_manifest_boundary` independently denies staged
  paths against `manifest.never_write` with no `exempt`/allow-list concept of
  its own -- so staging synthetic content for `docs/dreams/README.md` (which
  still matches `docs/dreams/*.md`) was refused there even after this story's
  fix cleared `check_preconditions`'s rung 4. This is a REAL, latent gap
  (only reachable once whole-file content actually ships for a
  never-write-glob-matched `copied-managed`/`copied-seeded` path, which the
  packaged template does not today), but it is outside this story's Code Map
  (4 files: `fs.py`, `preconditions.py`, `inventory.py`, `adopt.py`) and its
  Never bullets ("Do not modify ... any other already-shipped Epic 9/10
  primitive"). Fixed the TEST, not the code: the final test injects a
  minimal `commit=` double (mirroring this file's own established
  `_fake_commit` whole-file-branch pattern) instead of `template_path=`,
  bypassing `materialize()` entirely. This still fully proves the story's own
  regression target -- `check_preconditions`'s rung 4, reached and cleared
  before `commit()` ever runs -- and does not touch `engine/copier.py`.
  Recommend a follow-up story audit `_check_manifest_boundary` for the same
  exempt-set gap this story just closed in `fs.py`/`preconditions.py`.

## Review Triage Log

### 2026-08-21 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 2: (high 0, medium 1, low 1)
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter found the new `NeverWrite.exempt` short-circuit is duplicated (unshared) between `fs._matches` and `preconditions.py` rung 4, with no agreement test pinning them the way `first_match`/`fs._matches` already are for patterns (`test_seed_verbs_skips.py`). Added a parametrized cross-check (`test_seed_verbs_preconditions.py::test_rung_4_agrees_with_fs_matches_on_the_exempt_short_circuit`) asserting rung 4 and `fs._matches` always agree on the exempt short-circuit over a small table (exempt+matching, non-exempt+matching, exempt+no-pattern).
  - `[low]` `[patch]` Blind Hunter found `NeverWrite`'s docstring inaccurately claimed `exempt` is "validated the same way `patterns` is" when it is in fact MORE lenient (coerces `list`/`set`/`tuple`; `patterns` coerces `list` only). Corrected the docstring to state the actual difference and why it is safe (no order to preserve for a pure membership set).
  - `[low]` `[patch]` Both reviewers independently flagged the untested scenario of an EXACT literal `never_write` pattern (not just a glob) colliding with a writable-exemption path. Behavior is correct by design (the AC's own unconditional exclusion), but untested. Added `test_seed_fs.py::test_matches_returns_none_for_an_exempt_path_even_when_named_by_an_exact_literal_pattern` pinning the deliberate resolution.

Deferred (pre-existing, out of this story's own scope, surfaced incidentally by review): `engine/copier.py::_check_manifest_boundary`'s own independent, exempt-unaware `never_write` re-check (`DW-FU-10-8`, confirmed by both reviewers and by this story's own implementation work) and `writable_exemptions()`'s deliberate exclusion of `hybrid-managed-region` from the exemption classes, unaudited for the identical collision (`DW-FU-10-8-2`, raised by both reviewers, not reachable in the current packaged manifest).

Rejected (by-design or reviewer misread, verified against the actual code): a claim that `seed/verbs/check.py` independently constructs an un-updated `fs.NeverWrite` (verified false by direct grep -- `check.py` never constructs one, it is read-only); the "blanket, unscoped exemption" characterization (matches the epics AC's own literal "excluded from the set -- never in the set to begin with" wording, by design); a claim that rung 6 (managed-content divergence) is bypassed (it is an independent rung, untouched by the rung-4-only exempt check); the package's established, deliberately repetitive documentation style (matches every neighboring module, not a new deviation); citations to architecture/epics documents the isolated reviewers could not see (a structural limitation of the review setup, not a code defect); and the negligible cost of `writable_exemptions()`/`effective_never_write()` both iterating the same ~43-entry manifest once per verb call (not a real performance concern at this scale).

## Design Notes

fnmatch (stdlib) has no negation/extglob support, so "deny `docs/dreams/*.md` except
`docs/dreams/README.md`" cannot be expressed as a single, or a rewritten, glob string without
either (a) failing to protect other files under the glob, or (b) requiring an enumerated,
existence-dependent expansion that would stop protecting a not-yet-existing future file — both
rejected. An allow-list checked before the deny-list is the only mechanism that satisfies both
"the named path is writable" and "every other path matching the same glob still refuses."
Considered and rejected: a `.gitignore`-style `!`-negation convention folded into `patterns`
itself (this package already has exactly this pattern in `inventory.py::_is_gitignored`) — it
would require `skips.first_match` (shared with `--skip`) to also support negation, silently
changing `--skip`'s own semantics for any future `!`-prefixed skip pattern, an unrelated feature
whose scope this story must not touch.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green,
  including new `NeverWrite.exempt` / `writable_exemptions` / rung-4 / real-manifest-adopt tests.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green.

## Auto Run Result

**Summary:** Fixed the confirmed-live defect where `marshal seed adopt --apply` (and, once 10.7
lands, `marshal seed init`) refuses unconditionally on its own manifest-declared writable
artifacts (`dreams-readme`, `specs-readme`) because their resolved paths also match a broader
`never_write` glob pattern. Added an explicit allow-list (`fs.NeverWrite.exempt`, checked before
glob-pattern matching in both `fs._matches` and `check_preconditions` rung 4 -- fnmatch has no
negation, so narrowing the colliding glob itself was not viable without weakening protection for
every other path under it) and a new `detect.inventory.writable_exemptions()` that computes it
from the manifest's `copied-managed`/`copied-seeded` entries, minus any path already recognized
as legacy (AD-59 still wins). Wired into `verbs/adopt.py`; `verbs/init.py` (unmerged, Story 10.7)
needs the identical one-line addition once it resumes.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/fs.py` -- `NeverWrite.exempt`
  field + `_matches` short-circuit.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/preconditions.py` -- rung 4
  exempt short-circuit.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/inventory.py` -- new
  `writable_exemptions()`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/adopt.py` -- wires
  `exempt=writable_exemptions(...)` into `run_adopt`'s `NeverWrite` construction.
- `tests/unit/test_seed_fs.py`, `tests/unit/test_seed_verbs_preconditions.py`,
  `tests/unit/test_seed_detect_inventory.py`, `tests/unit/test_seed_verbs_adopt.py` -- new
  coverage per the Code Map, including the real-packaged-manifest regression test proving the
  confirmed-live defect is fixed, an fs.py/preconditions.py exempt-agreement test, and an
  exact-literal-pattern edge case, both added during the review pass.
- `_bmad-output/projects/pyforge-marshal/implementation-artifacts/deferred-work.md` (new) -- two
  defer entries (`DW-FU-10-8`, `DW-FU-10-8-2`).

**Review findings breakdown:** 3 patch (0 high, 1 medium, 2 low) -- all auto-fixed with
regression-test proof; 2 defer (0 high, 1 medium, 1 low) -- logged to the Tier-3 deferred-work
ledger; 6 reject (verified false, or by-design matching the epics AC / established package
convention); 0 intent_gap; 0 bad_spec.

**Follow-up review recommendation:** `false` -- the three patches were additive (one new
cross-module agreement test, one docstring accuracy fix, one new edge-case test pinning already-
correct, by-design behavior); none touched production logic beyond what the first review pass
already covered, and no behavioral risk was introduced by the fixes themselves.

**Verification performed:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 4971
passed, 9 deselected (re-run after the patch fixes; up from 4967 pre-patch, +4 new test
executions). `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 84 passed. `ruff check` on
all 8 changed files -- clean except 3 pre-existing `RUF100` findings in
`test_seed_verbs_preconditions.py` (lines 134/145/200, `_RaisingProcess`/`_StatusFails` fixture
classes untouched by this diff, confirmed present on unmodified `main` via `git stash`).

**Residual risks:** the two deferred findings are real, pre-existing gaps outside this story's
own Code Map/Never bullets (a second, unfixed `never_write` enforcement point in
`engine/copier.py`, and an unaudited `hybrid-managed-region` collision case), both logged with
evidence. The literal CLI command `marshal seed init` remains unverified by this story (the verb
does not exist on `main` yet -- Story 10.7, unmerged); this story proves the mechanism via the
already-shipped `run_adopt` verb instead, per this spec's own Never bullet.

**Post-review independent verification (orchestrating agent, before landing):** ran the REAL
`marshal seed adopt --repo-root <fresh-repo>` CLI (not just the test suite). Dry-run correctly
plans `dreams-readme` with no refusal. `--apply --yes` proceeds PAST `check_preconditions`
(no `PreconditionFailure`/`NeverWriteViolation` for `docs/dreams/README.md`) -- this story's own
fix is confirmed working at the real-CLI level, not merely under test. It then fails LATER, for
an entirely different, pre-existing, already-disclosed reason: `engine/copier.py::
_check_manifest_boundary`'s OTHER condition (staged-path-not-in-`allow_patterns`, not the
`deny_patterns`/`DW-FU-10-8` condition) refuses because `materialize()` stages the packaged
template tree's own internal files (`manifest.yaml`, `__init__.py`, `files/*.j2`) alongside real
content -- exactly `verbs/adopt.py`'s own pre-existing (Story 10.6) "known, inherited limitation
(1)": no whole-file template content exists yet for any entry. Confirmed via a from-scratch,
independent script (not the implementer's test file) that isolates this story's own fix from
that unrelated gap by calling `check_preconditions`/`fs.write` directly against the real
manifest's real plan: both pass, and `docs/dreams/README.md` is genuinely written to disk. Also
independently re-confirmed the adversarial case: an unrelated real file matching
`docs/dreams/*.md` that is not a manifest-declared writable path is still refused
(`NeverWriteViolation`) -- the exemption is scoped, not a widened glob.
