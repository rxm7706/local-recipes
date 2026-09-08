---
title: 'Explicit status-vocabulary translation (Epic 8 Story 8.6, pyforge-steward)'
type: 'feature'
created: '2026-08-13'
status: 'done'
baseline_revision: '4e2418749b2bf13bd7a0111f5b1036aede6a2b0f'
final_revision: 'ae47cd512cfc1ca4e5b613519e7826216be3a223'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Pushing a Jira status value onto GitHub (`reconcile`'s `push_to_github` branch,
which calls `update_project_item_field`) writes the raw Jira status string with zero
validation -- any string succeeds, so an unrecognized Jira status silently invents a GitHub
state instead of failing, violating AD-6 ("every status value crossing the boundary passes
through `value_translation`; an unmapped value is a hard, named, logged failure ... never
passed through"). The reverse direction (`push_to_jira` -> `transition_jira_issue`) already
hard-fails today when no Jira transition matches the pushed name (`sync.py:740-744`,
incidental but tested) -- confirmed working, out of scope.

**Approach:** Add an explicit, reviewable `status_mapping: dict[str, str]` (Jira status name ->
GitHub status field value) to `SyncConfig`/`load_config`, consulted only in `reconcile`'s
`push_to_github` write branch. A non-null target value absent from the mapping raises a new
named `SyncUnmappedStatusError`, caught by `reconcile`'s existing generic `except SyncError`
handling -- no new exception-handling plumbing.

## Boundaries & Constraints

**Always:**
- Add `status_mapping: dict[str, str] = field(default_factory=dict)` to `SyncConfig`
  (`sync.py:100-117`); load and validate it in `load_config` (`sync.py:143-206`) exactly like
  `user_mapping` -- must be a mapping or a named `SyncConfigError`, no further value-level
  validation (GitHub status option values and Jira status names are both operator-declared free
  text with no fixed enum to check against, unlike `field_overrides`' closed `_VALID_OVERRIDE_*`
  vocabulary).
- Consult `config.status_mapping` ONLY in the `push_to_github` write branch (`sync.py:963`,
  the call writing `config.github_status_field_id`) -- never the baseline-field write
  (`sync.py:989-992`, a JSON baseline string, not a status value, via the same
  `update_project_item_field` function).
- A `None` target value (an explicit clear, e.g. `test_field_cleared_on_jira_side_is_a_genuine_
  change_pushed_to_github`) bypasses the mapping lookup and writes `None` straight through
  unchanged -- a clear is not a status word to translate (matches jira:AD-10's existing "an absent
  key and an explicit null mean opposite things" precedent for treating `None` specially).
- A non-null target value with no `status_mapping` entry raises `SyncUnmappedStatusError`
  (new `SyncError` subclass, defined beside `SyncUnlinkedError` at `sync.py:221-224`) BEFORE
  calling `update_project_item_field` -- message format `"unmapped: jira status {value!r} has
  no status_mapping entry for github"` (mirrors `SyncUnlinkedError`'s `"unlinked: ..."`
  greppable-prefix convention). Caught by `reconcile`'s existing `except SyncError as exc:
  return DutyResult(ok=False, ...)` (`sync.py:970-971`) -- add no new try/except.
- After a successful `push_to_github` write, the GH-side baseline (`sync.py:979-983`) must
  record the TRANSLATED (actually-written) value, never the raw Jira value -- otherwise the
  next reconcile's `gh.status != gh_base` comparison permanently mismatches, a zero-loop
  regression (AD-5). The Jira-side baseline (`sync.py:984-988`) is unaffected: it still records
  `target_value` (= `jira.status`, untranslated), since Jira's own value did not change.
- Update the shared `CONFIG` fixture in `test_sync_reconcile_propagation.py` (`:31-40`) with an
  identity `status_mapping` covering its existing fixture vocabulary (`"To Do"`, `"In
  Progress"`, `"Blocked"` -- confirmed the closed set across every `push_to_github`-decision
  test in this file, including the `--schedule` batch tests) so every existing test keeps
  passing unchanged; `CONFIG_JIRA_WINS` (`:42-43`) inherits it via its existing dict-spread
  pattern.
- Add a `status_mapping: {}` section to `.steward/sync-config.example.yaml`, matching
  `field_overrides`/`user_mapping`'s comment style.

**Block If:** nothing identified -- config shape, exception pattern, and test fixtures all
follow direct, already-established precedent in this same module.

**Never:**
- Never add translation to the `push_to_jira` / `transition_jira_issue` direction -- out of
  scope per the correct-course decision (`sprint-change-proposal-2026-08-13.md` SS2); that
  direction already hard-fails via Jira's own transition-name lookup.
- Never change the decision logic (which side wins, whether a reconcile is a no-op) --
  translation only changes the value actually written to GitHub and the GH-side baseline
  recorded after a real write. The pre-write convergence check (`sync.py:930-933`) keeps
  comparing raw `target_value` to `gh.status`; a rare case where both sides changed to
  values that map to the same GitHub status is one avoidable extra write, not a correctness
  bug -- accepted, matching Story 8.5's own precedent of accepting a similar one-wasted-read
  tradeoff rather than adding new mechanism for it.
- Never validate `status_mapping`'s keys or values against a fixed vocabulary -- unlike
  `field_overrides`, there is no closed set of valid GitHub/Jira status names this module can
  check against.
- Never require `status_mapping` validation during a `--dry-run` -- dry-run returns before the
  write branch runs (`sync.py:938-946`), so it does not exercise translation; this is
  acceptable since a dry-run makes no write and "crossing the boundary" (AD-6) has not happened.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Mapped Jira status pushed to GitHub, translation differs from source | `jira.status="Closed"`, `status_mapping={"Closed": "Done", ...}` | `gh_status` field written as `"Done"`; GH baseline records `{"status": "Done"}`; Jira baseline records `{"status": "Closed"}` | No error expected |
| Unmapped Jira status pushed to GitHub | `jira.status="Triage"`, `status_mapping` has no `"Triage"` key | `DutyResult(ok=False, summary=...)` containing `"unmapped: jira status 'Triage' has no status_mapping entry for github"`; no GitHub write; neither baseline written | Named failure, matches `SyncUnlinkedError`'s existing pattern |
| Jira status explicitly cleared, pushed to GitHub | `jira.status=None` (cleared), any `status_mapping` | `gh_status` field written as `None`; both baselines record `{"status": None}` -- unchanged from current behavior | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- `SyncConfig` (`:100-117`):
  add `status_mapping` field. `load_config` (`:143-206`): load/validate `status_mapping` like
  `user_mapping` (`:190-192`, `:204`). New `SyncUnmappedStatusError(SyncError)` beside
  `SyncUnlinkedError` (`:221-224`). `reconcile`'s `push_to_github` write branch (`:962-970`) and
  the immediately-following baseline refresh (`:977-1005`): translate before writing, use the
  translated value for the GH baseline only. Module docstring (`:1-30`): mention
  `status_mapping` alongside `field_overrides`/`user_mapping`.
- `.steward/sync-config.example.yaml` -- add a `status_mapping: {}` section (comment style
  matching `field_overrides`/`user_mapping`, `:44-60`).
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_config.py` -- add
  `status_mapping` load/validation tests mirroring the existing `user_mapping` tests
  (`:49-64`, `:180-186`); update `test_happy_path_loads_a_fully_populated_config` to assert
  `config.status_mapping == {}`.
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` --
  add `status_mapping={"To Do": "To Do", "In Progress": "In Progress", "Blocked": "Blocked"}`
  to the shared `CONFIG` fixture (`:31-40`); add two new tests (translated write, unmapped
  hard-fail) near `test_jira_changed_github_did_not_pushes_to_github_and_refreshes_both_
  baselines` (`:209-229`), mirroring `test_no_matching_jira_transition_is_a_named_failure_not_
  a_guess`'s (`:369-391`) assertion pattern for the symmetric direction.

## Tasks & Acceptance

**Execution:**
- [x] `sync.py` -- `SyncConfig`: add `status_mapping: dict[str, str] = field(default_factory=dict)`.
- [x] `sync.py` -- `load_config`: load `document.get("status_mapping") or {}`, raise
  `SyncConfigError(f"{document_path}: 'status_mapping' must be a mapping")` if not a `dict`,
  pass `status_mapping=dict(status_mapping)` into the returned `SyncConfig`.
- [x] `sync.py` -- add `class SyncUnmappedStatusError(SyncError):` beside `SyncUnlinkedError`,
  docstring: "A non-null status value crossing into GitHub has no `status_mapping` entry."
- [x] `sync.py` -- `reconcile`'s `push_to_github` write branch: before calling
  `update_project_item_field`, if `target_value is not None`, look up
  `config.status_mapping.get(target_value)`; if `None` (unmapped), raise
  `SyncUnmappedStatusError(f"unmapped: jira status {target_value!r} has no status_mapping entry
  for github")`; otherwise write the mapped value and remember it for the baseline step below.
  If `target_value is None`, write `None` unchanged (no lookup).
- [x] `sync.py` -- baseline refresh: use the actually-written GitHub value (mapped, or `None`
  for a clear, or `target_value` unchanged when `decision != "push_to_github"`) for
  `new_gh_baseline`; leave `new_jira_baseline` keyed on `target_value` exactly as today.
- [x] `sync.py` -- module docstring: add `status_mapping` to the `field_overrides`/
  `user_mapping` mention.
- [x] `.steward/sync-config.example.yaml` -- add a commented `status_mapping: {}` section.
- [x] `test_sync_config.py` -- add `status_mapping` happy-path (loads a populated mapping) and
  must-be-a-mapping-error tests; update the fully-populated happy-path test's assertion to
  include `status_mapping == {}`.
- [x] `test_sync_reconcile_propagation.py` -- add `status_mapping` to the shared `CONFIG`
  fixture; add a test proving a differently-named Jira status translates to its mapped GitHub
  value (and that the GH/Jira baselines end up holding the translated/untranslated values
  respectively); add a test proving an unmapped Jira status fails named, with no GitHub write
  and no baseline change (mirroring the unlinked-item and no-matching-transition tests' shape).

**Acceptance Criteria:**
- Given a Jira status value with a configured `status_mapping` entry, when `reconcile` pushes
  it to GitHub, then GitHub's status field receives the mapped value, GitHub's baseline records
  that mapped value, and Jira's baseline records the original (untranslated) value.
- Given a Jira status value absent from `status_mapping`, when `reconcile` would push it to
  GitHub, then no GitHub write happens, neither baseline is written, and the result is
  `ok=False` with a summary containing `"unmapped: jira status <value> has no status_mapping
  entry for github"`.
- Given the full test suite, when `pixi run -e pyforge-steward pyforge-steward-test` runs, then
  it exits 0 including every existing and newly added test, with zero live network calls.

## Spec Change Log

### 2026-08-13 — Baseline metadata correction (dev-2 recovery)

The first dev attempt stamped `baseline_revision` to `124a143a1e` (the commit it created
mid-session to sync `planning-artifacts/epics.md`/`sprint-status-ledger.yaml` with main's Epic 8
correct-course, *before* recording the spec's baseline) instead of the true session-start commit
`4e2418749b2b`. The orchestrator's baseline gate compares `baseline_revision` against its own
recorded start commit and only tolerates the claimed value being an *older* ancestor (a
deferred-work-bundle adoption case); a self-created *newer* commit is a genuine mismatch, so it
retried the story from a clean worktree rather than a false positive in the implementation. The
implementation itself (both commits, `124a143a1e` + `85a60d06e6`) was already complete, reviewed,
and tested (632 passed) — preserved to `attempt-preserve/20260813-160412-936a-85a60d06` by the
orchestrator's auto-preserve-on-retry, and restored here via a plain `git merge --ff-only` (no
code changed). This entry corrects `baseline_revision` to the true `4e2418749b2b` so the gate
passes cleanly; `final_revision` (`85a60d06e6`) is unchanged.

## Review Triage Log

### 2026-08-13 — Review pass

Blind Hunter (`bmad-review-adversarial-general`) and Edge Case Hunter (`bmad-review-edge-case-hunter`)
ran independently, no shared context, against the diff since `baseline_revision`. Every finding
below was verified by hand against the actual worktree source before triage, not taken at face
value from either reviewer's report.

- intent_gap: 0
- bad_spec: 0
- patch: 4 (medium 2, low 2)
- defer: 2 (medium 1, low 1)
- reject: 5 (low 5)
- addressed_findings:
  - `[medium]` `[patch]` (Blind Hunter + Edge Case Hunter, corroborated) `status_mapping` had no
    value-type check -- a YAML gotcha (`Done: yes` -> `True`, `Done:` -> `None`) loaded silently
    and would only surface as a malformed GitHub GraphQL write, not a named config-time failure.
    The intent-contract's "no further value-level validation" bullet reads, together with its own
    justifying clause and this file's established `_require_section` precedent, as "no closed-
    vocabulary validation" -- not "no type safety" -- so a `str`/`str` type check on
    `status_mapping`'s keys/values is in scope, not a contract violation. Added the check plus two
    new `test_sync_config.py` tests (`Done: yes`, `Done:`).
  - `[medium]` `[patch]` (Edge Case Hunter) no test exercised `SyncUnmappedStatusError` composing
    with the `--schedule` batch dispatcher -- only single-pair `reconcile()` proved the failure
    mode. Added `test_schedule_batch_with_one_unmapped_status_among_linked_items_fails_only_that_
    entry`, mirroring Story 8.5's own unlinked-item batch-isolation test.
  - `[low]` `[patch]` (Blind Hunter) `sync-config.example.yaml`'s commented `status_mapping`
    sample was a pure identity map, contradicting its own motivating comment's "Done" vs "Closed"
    example. Changed the sample's third entry to `"Closed": "Done"`.
  - `[low]` `[patch]` (Blind Hunter) module docstring's Story-8.6 parenthetical left
    `makes the engine board-agnostic), a` orphaned on its own short line instead of being
    re-flowed. Fixed the line wrap.
  - `[medium]` `[defer]` (Blind Hunter + Edge Case Hunter, corroborated) `document.get("status_
    mapping") or {}` silently coerces a falsy-but-malformed value (`status_mapping: false`,
    `status_mapping: 0`) to `{}` before the `isinstance` check runs, bypassing `SyncConfigError`.
    Real, but an exact pre-existing pattern shared by `field_overrides` and `user_mapping`
    (verified: both use the identical `or {}` idiom) -- not novel to this story, and fixing it
    asymmetrically for only the newest field would leave the other two broken. Logged as
    `DW-FU-8-6` for a cross-cutting hardening pass over all three `or {}` config loads.
  - `[low]` `[defer]` (Blind Hunter) no operator-facing doc page outside the example YAML's
    comments covers `status_mapping`/`user_mapping`/`field_overrides` (README has zero mentions
    of any of the three). Pre-existing gap for all three fields, not introduced by this story.
    Logged as `DW-FU-8-6-2`.
  - reject (5, all low/noise, not actioned): `--dry-run` never exercises the `status_mapping`
    lookup (Blind Hunter + Edge Case Hunter, corroborated) -- matches this story's own frozen
    "Never" boundary (dry-run returns before the write branch; no boundary was crossed to
    validate); translation is wired one-way only, `push_to_jira` untouched (Blind Hunter) --
    matches the frozen "Never" boundary and the correct-course decision's explicit scope
    (`sprint-change-proposal-2026-08-13.md` §2); the pre-write convergence check compares an
    untranslated value (Edge Case Hunter) -- matches the frozen "Never" boundary's explicitly
    accepted one-wasted-write tradeoff; mapping a status to `""` is indistinguishable from a
    mistake (Blind Hunter) -- speculative, no concrete failure demonstrated, matches this
    module's own precedent of trusting operator-declared config; two directions raise two
    differently-shaped failures (`SyncUnmappedStatusError` vs the pre-existing `SyncAPIError`)
    (Blind Hunter) -- an inherent, accepted consequence of the same authorized scope boundary,
    not a defect in this story's own delivered direction.

**Re-verification after patches:** `pixi run -e pyforge-steward pyforge-steward-test` -- 632
passed, 0 failed, zero live network calls (629 baseline + 3 new: schedule-batch isolation,
non-string value, null value). `pixi run -e pyforge-steward pyforge-steward-dogfood` -- clean.
`ruff check` on all four touched files -- 3 pre-existing findings in `sync.py`'s import block
(unrelated to this diff, confirmed identical against `git show baseline_revision`), none
introduced by this diff.

### 2026-08-13 — Review pass (dev-2, post-recovery)

A second dev attempt recovered this story's already-complete, already-reviewed implementation
from an orchestrator auto-preserve after a baseline-metadata mismatch (see the Spec Change Log
entry above) and ran a fresh, independent review pass against the same diff, per this workflow's
`status: done` re-entry rule. Blind Hunter and Edge Case Hunter ran again, independently, no
shared context, no access to the prior pass's triage. Every finding below was verified by hand
against the actual worktree source (and, where relevant, the pre-story baseline via `git show`)
before triage.

- intent_gap: 0
- bad_spec: 0
- patch: 1 (medium 1)
- defer: 2 (low 2)
- reject: 9 (low 9)
- addressed_findings:
  - `[medium]` `[patch]` (Edge Case Hunter) `reconcile`'s returned `DutyResult.details["baseline"]`
    was hardcoded to the raw, untranslated `target_value` even on a translated `push_to_github`
    write -- correct on the actually-persisted GitHub baseline field (`new_gh_baseline`, which
    already used `github_write_value`), but a caller reading `result.details["baseline"]` instead
    of the transport would see the wrong value whenever translation changes the written status.
    Caused by this story (`target_value == github_write_value` always held before translation
    existed); not covered by the intent-contract's "Always" bullet, which only names the
    persisted GH-side write, not this returned-details mirror. Fixed `sync.py` to use
    `github_write_value`; added an assertion on `result.details["baseline"]` to the existing
    `test_mapped_jira_status_translates_before_writing_to_github` test. Zero regression risk:
    the only 3 pre-existing assertions on this field checked the `None` no-op case, never the
    populated-dict shape this change affects.
  - `[low]` `[defer]` (Blind Hunter) `sprint-change-proposal-2026-08-13.md` §2's stated rationale
    for why Story 8.5/8.6 needed no boundary amendment has the Jira↔GitHub write direction
    backwards relative to both the original `epics.md` audit note and the actual shipped code
    (verified against pre-story `sync.py` and `transition_jira_issue`'s existing hard-fail
    behavior). No functional impact -- the frozen intent-contract and shipped code both target
    the correct direction -- and the document's content is inherited verbatim from `main`'s
    already-ratified `073dfe0fd2` correct-course commit, outside this story's own scope to edit.
    Logged as `DW-FU-8-6-3`.
  - `[low]` `[defer]` (Blind Hunter + Edge Case Hunter, corroborated) independently re-surfaced
    the same `status_mapping`/`field_overrides`/`user_mapping` `or {}` falsy-coercion gap already
    recorded as `DW-FU-8-6` in the prior pass, including the identical `status_mapping: false`
    example. This workflow's defer procedure always mints a fresh entry rather than merging into
    a prior one. Logged as `DW-FU-8-6-4`, cross-referencing `DW-FU-8-6`; no new remediation beyond
    what that entry already describes.
  - reject (9, all low/noise, not actioned): the AC's "any status crossing the boundary" reading
    as requiring `push_to_jira` translation too (Blind Hunter) -- re-verified against the frozen
    Intent section's explicit "confirmed working, out of scope" carve-out for that direction, same
    conclusion as the prior pass's "one-way-only translation" reject; `push_to_jira` staying an
    untranslated passthrough for a non-identity `status_mapping` (Edge Case Hunter) -- the same
    frozen-boundary carve-out, concrete failure mode restated but not new; `--dry-run` not
    validating the mapping (Edge Case Hunter) -- re-verified against the frozen "Never" boundary,
    same as the prior pass's reject; the pre-write convergence check comparing an untranslated
    value (Edge Case Hunter) -- re-verified against the frozen "Never" boundary's explicitly
    accepted one-wasted-write tradeoff, same as the prior pass's reject; an empty-string
    `status_mapping` value writing a blank GitHub status uncaught (Edge Case Hunter) -- re-
    verified as matching the frozen "Never" boundary's explicit no-vocabulary-validation scope,
    same conclusion as the prior pass's reject; the `sprint-status-ledger.yaml` diff also flipping
    `9-6`/`9-7` from `backlog` to `done` with no proposal-document record (Blind Hunter) --
    verified both stories are genuinely done (Tier-3 `sprint-status.yaml`'s own annotations, and
    already-merged commits in this branch's ancestry), a pre-existing Tier-2/Tier-3 drift
    correctly closed as an incidental side-effect of the same-file correct-course cherry-pick, not
    a new or wrong decision; the new `target_value is None` bypass branch reported untested (Blind
    Hunter) -- false, already exercised by the pre-existing
    `test_field_cleared_on_jira_side_is_a_genuine_change_pushed_to_github`; the new Story 8.4's
    "no architecture change needed" claim called optimistic (Blind Hunter) -- speculative concern
    about not-yet-built future work, no code in this diff; `CONFIG_STATUS_TRANSLATION`'s
    dict-spread construction called fragile versus `dataclasses.replace` (Blind Hunter) -- matches
    `CONFIG_JIRA_WINS`'s own pre-existing dict-spread precedent in the same file, not novel to
    this diff; the module docstring's inline `(Story 8.6)` citation called a future-renumbering
    trap (Blind Hunter) -- matches the file's own established header convention (already anchored
    to "Story 8.1" unchanged across four prior stories' additions), not novel to this diff.

**Re-verification after this pass's patch:** `pixi run -e pyforge-steward pyforge-steward-test`
-- 632 passed, 0 failed, zero live network calls (no new test added; the fix's coverage was added
as an assertion inside the existing translation test).

## Design Notes

**Before (raw passthrough, no validation):**
```python
else:
    update_project_item_field(
        gh.item_id, config.github_status_field_id, target_value, ...
    )
...
new_gh_baseline = _serialize_baseline({**gh.baseline, _TRACKED_FIELD: target_value}, ...)
```

**After (translated, hard-fail on unmapped, GH baseline follows the translated value):**
```python
github_write_value = target_value  # unchanged default for push_to_jira / no_op paths
...
else:  # push_to_github
    if target_value is None:
        github_write_value = None
    else:
        mapped = config.status_mapping.get(target_value)
        if mapped is None:
            raise SyncUnmappedStatusError(
                f"unmapped: jira status {target_value!r} has no status_mapping entry for github"
            )
        github_write_value = mapped
    update_project_item_field(
        gh.item_id, config.github_status_field_id, github_write_value, ...
    )
...
new_gh_baseline = _serialize_baseline({**gh.baseline, _TRACKED_FIELD: github_write_value}, ...)
new_jira_baseline = _serialize_baseline({**jira.baseline, _TRACKED_FIELD: target_value}, ...)
```
`github_write_value` defaults to `target_value` so the `push_to_jira` and already-no-op paths
(which never assign it) keep writing exactly what they write today -- only the
`push_to_github` branch's assignment changes behavior.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary.** Story 8.6 (CAP-5 "explicit status-vocabulary translation", FR-31) closes the
asymmetry the correct-course proposal identified: a Jira status value pushed onto GitHub
(`reconcile`'s `push_to_github` branch) now passes through an explicit, reviewable
`status_mapping` config dict before the write; a non-null status absent from that mapping raises
a new named `SyncUnmappedStatusError` instead of silently inventing a GitHub state. The
GitHub-side baseline records the translated value it actually wrote (not the raw Jira value),
preserving the zero-loop guarantee; the Jira-side baseline is unaffected. The reverse direction
(`push_to_jira`) is untouched -- it already hard-fails via Jira's own transition-name lookup, out
of scope per the correct-course decision.

**Files changed:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- added `status_mapping`
  to `SyncConfig`/`load_config` (with a review-pass type-safety check on its keys/values); added
  `SyncUnmappedStatusError`; `reconcile`'s `push_to_github` write branch now translates through
  `status_mapping` (bypassing translation for an explicit `None` clear) before writing, and the
  GH-side baseline refresh uses the translated value; module docstring updated.
- `.steward/sync-config.example.yaml` -- added a commented `status_mapping: {}` section
  (review-pass: sample corrected to show real translation, not just identity mapping).
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_config.py` -- added
  `status_mapping` load/validation tests (happy path, must-be-a-mapping, and two review-pass
  type-safety tests: non-string value, null value).
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` --
  added `status_mapping` to the shared `CONFIG` fixture; added a translated-write test, an
  unmapped-status hard-fail test, and a review-pass `--schedule` batch-isolation test proving
  the new failure mode composes correctly with Story 8.5's batch dispatcher.

**Review findings breakdown:** intent_gap 0, bad_spec 0, patch 4 (2 medium: `status_mapping`
had no value-type check allowing a YAML gotcha to reach a live GraphQL write, and no test proved
the new failure mode composing with the `--schedule` batch dispatcher; 2 low: the example YAML's
sample was a pure identity map contradicting its own motivating comment, and a docstring
line-wrap regression), defer 2 (`DW-FU-8-6` medium -- `load_config`'s `or {}` idiom silently
coerces a falsy-malformed config value to `{}`, shared pre-existing pattern across all three
config-dict fields, not novel to this story; `DW-FU-8-6-2` low -- no operator-facing doc page
covers `status_mapping`/`user_mapping`/`field_overrides` outside example-YAML comments), reject
5 (all low/noise: `--dry-run` not validating the mapping, one-way-only translation, an
untranslated convergence-check comparison, and two failure-shape inconsistency across
directions -- all four match this story's own frozen "Never" boundaries or the correct-course
decision's explicit scope; empty-string mapping ambiguity is speculative with no concrete
failure demonstrated).

**Follow-up review recommendation:** false -- all four patches were mechanical and localized
(config-load type validation, one new test exercising already-reviewed logic in a new
composition context, a documentation-sample correction, a docstring line-wrap fix); none touched
the core translation/baseline mechanism itself, which was already reviewed and unchanged by this
pass. Low volume, low consequence, fully localized.

**Verification performed:** `pixi run -e pyforge-steward pyforge-steward-test` -- 632 passed, 0
failed, zero live network calls (independently re-run twice: once after implementation at 629,
once after the review-pass patches at 632). `pixi run -e pyforge-steward pyforge-steward-dogfood`
-- clean, both before and after patches. `ruff check` on all four touched files -- 3 pre-existing
findings confined to `sync.py`'s import block, confirmed identical against `baseline_revision`
via a direct `git show` comparison (none introduced by this diff); the fourth file's own
apparent "errors" were a YAML file mis-invoked against a Python linter, not a real finding.

**Residual risks:** none blocking. Two items intentionally deferred to the ledger (`DW-FU-8-6`,
`DW-FU-8-6-2`) -- neither is a defect in this story's own delivered behavior; both are
pre-existing patterns shared with sibling config fields, explicitly out of this story's
single-field scope per its frozen intent-contract.

## Auto Run Result

**Summary.** This second dev attempt recovered story 8.6's already-complete, already-reviewed
implementation (CAP-5 "explicit status-vocabulary translation", FR-31) after an orchestrator
auto-preserve/retry triggered by a baseline-metadata bug, not an implementation defect: the
first attempt stamped `baseline_revision` to a commit it created mid-session (syncing
`planning-artifacts` with main's Epic 8 correct-course) instead of the true session-start
commit, so the orchestrator's baseline gate treated the deviation as a mismatch and rolled the
worktree back to a clean baseline while preserving the completed commits to a rescue ref. This
attempt restored those commits via a plain `git merge --ff-only` (zero code changes), corrected
`baseline_revision`, re-verified both gates (632 tests + `spec_surface_reconcile.py`) green, then
ran a full independent fresh review pass per this workflow's `status: done` re-entry rule.

**Files changed (this pass, on top of the restored implementation):**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` -- `reconcile`'s returned
  `DutyResult.details["baseline"]` now mirrors `github_write_value` (the actually-written,
  translated GitHub status) instead of the raw pre-translation `target_value`.
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` --
  added an assertion on `result.details["baseline"]` to the existing translation test, covering
  the fix above.
- `_bmad-output/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md` --
  this file: baseline-metadata correction (Spec Change Log), this pass's Review Triage Log entry,
  this Auto Run Result section.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- two new entries, `DW-FU-8-6-3` and
  `DW-FU-8-6-4`.

**Review findings breakdown (this pass):** intent_gap 0, bad_spec 0, patch 1 (medium: the
`details["baseline"]` translation-mirroring gap above), defer 2 (`DW-FU-8-6-3` low -- the
correct-course proposal document's own root-cause prose has the write direction backwards, no
functional impact, outside this story's scope to edit; `DW-FU-8-6-4` low -- independent
reconfirmation of the already-deferred `DW-FU-8-6` falsy-`or {}` gap), reject 9 (all low/noise --
one true re-discovery of a prior-pass reject re-verified against the frozen intent-contract's
explicit boundaries and confirmed still correctly out of scope (one-way translation and its
concrete convergence-check/dry-run/empty-string variants), one false claim disproven against an
existing test, two speculative concerns about not-yet-built future work or established file
conventions, and one verified-correct incidental ledger fix with no record of its own).

**Follow-up review recommendation:** false -- this pass's only patch was a narrow, mechanical
correction to a returned-details field with zero regression risk (verified: the only 3 prior
assertions on that field checked the unaffected `None` case) and no behavior/API/security/data
impact beyond making an already-correctly-persisted value also correctly reported to callers.
Low volume, low consequence, fully localized.

**Verification performed:** `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- 632
passed, 0 failed, zero live network calls, run twice (once immediately after restoring the
preserved commits, once after this pass's patch). `python scripts/spec_surface_reconcile.py` --
`OK: every tracked file governed or allowlisted; no drift.`

**Residual risks:** none blocking. Four items now on the ledger for story 8.6 in total
(`DW-FU-8-6`, `DW-FU-8-6-2` from the prior pass; `DW-FU-8-6-3`, `DW-FU-8-6-4` from this pass) --
none is a defect in this story's own delivered behavior.
