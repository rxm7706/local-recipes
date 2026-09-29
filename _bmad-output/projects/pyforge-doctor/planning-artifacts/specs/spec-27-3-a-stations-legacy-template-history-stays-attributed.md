---
title: '27.3: A station''s legacy-template history stays attributed after its template changes'
type: 'fix'
created: '2026-09-18'
status: 'done'
baseline_revision: '76905db53a99c882398a4412ffa0548984760b46'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 27.1 made Doctor's merge-history sources read each station's *current* `merge_subject_template`. Marshal landed `34-3` on 2026-09-12 as `Merge 34-3 into main` under the then-default template; the moment marshal's policy moved to `Merge pyforge-marshal/{key} into main` (PR #1467), `story-status` on `main` reports `marshal/34-3: reads done in the sprint feed, but the harness says 'deferred' with no commit and no merge commit anywhere` — a `done` story orphaned by its own station's template move.

**Approach:** A bare legacy-form subject (`Merge {key} into main`) is attributed to the querying station only when that station's tracked ledger knows the key (Story 35.1's corroboration), implemented once and used by both `marshal.py::gather_story_status` and `ledger.py::gather_direction`. The scoped form keeps attributing; a bare subject naming a key the station does not know attributes nothing.

## Boundaries & Constraints

**Always:**
- Marshal `34-3` reads as merged and `story-status` on `main` reports no finding for it; a bare subject naming an unknown key attributes nothing; the scoped form still attributes; CAP-78's PR #1465 replay stays `ok`.
- One function, both sources; exit-code domain `{0, 2, 130}` untouched.

**Never:**
- Do not attribute a bare subject to a station whose ledger does not know the key — that is the cross-station poison CAP-78 closed.
- Do not import `pyforge.marshal`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| own legacy landing | `Merge 34-3 into main`; marshal ledger knows 34-3; policy now scoped | attributed to marshal | n/a |
| sibling's bare subject | `Merge 13-5 into main`; atlas ledger does not know 13-5 | nothing | n/a |
| scoped form | `Merge pyforge-marshal/50-1 into main` | attributed | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-80`.
Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py`; `.../sources/ledger.py`; tests.
Ledger key: `27-3-a-stations-legacy-template-history-stays-attributed`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-27-3-a-stations-legacy-template-history-stays-attributed.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- `pixi run -e pyforge-guild story-status-check` on `main` reports no `marshal/34-3` finding.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 8 findings — high 2, medium 0, low 6, false 0, maybe-false 0
- findings:
  - `[high]` `[intent_gap]` `marshal.py::_keys_from_merge_subjects`/`_keys_from_main_commits`'s new legacy-corroboration fallback reopens a cross-station false-green: the querying station's own ledger independently marking a numeric key `done` is sufficient, by itself, to attribute an *unrelated sibling project's own* bare-form commit as this station's landing evidence — no check that the specific commit has anything to do with the querying station. Reproduced directly and independently (not just taken from the reviewer's report): a synthetic repo where `pyforge-doctor` has an override template, its own ledger says `1-1: done`, and the only `"Merge 1-1 into main"` commit anywhere in history belongs to a wholly unrelated project — `marshal._keys_from_merge_subjects(repo, subjects, project_slug="pyforge-doctor")` returned `{StoryKeyRef(1,1)}` (attributed). Root cause is the `<intent-contract>` Approach's "that station's tracked ledger knows the key" corroboration rule — this is exactly what the diff implements, faithfully, and neither reading of "knows" (any-status per the cited Story 35.1 precedent, or the diff's own narrower done-only choice) closes this collision, since bare subjects carry no station token and this repo's own commit history is shared across every station's small, independently-numbered epic/seq keys (the module's own docstring records "3 findings into 306" once bare-form matching went unscoped — i.e. numeric collisions across stations are the norm here, not a rare edge case). The spec does not settle a fix for this (no restriction on which commits are eligible per project, no cross-project collision check) — no trivial fix exists (closing it needs new machinery: either scoping which commits/subjects are eligible per project, or detecting when a candidate key is simultaneously claimed by more than one project's ledger and refusing to attribute in that case).
  - `[high]` `[intent_gap]` Same shared root cause via the same `known_keys.legacy_bare_merge_key`/`load_done_story_keys` functions, on the other call site: `ledger.py::_merged_ids_for_project` suppresses the `done-but-unmerged` WARN the moment an unrelated project's bare-form merge subject coincidentally shares a numeric key with a story this project's own ledger flips to `done` on a branch (verified via the verification-gap reviewer's traced demonstration: `gather_direction` returns `OK` instead of `WARN done-but-unmerged` on that fixture, and monkeypatching `load_done_story_keys` to `frozenset()` restores the correct `WARN`, isolating the new fallback as the cause). Grouped with the finding above — one root cause, one route.
  - `[low]` `[reject]` `known_keys.LEGACY_MERGE_SUBJECT_TEMPLATE` / `marshal.py::_MERGE_SUBJECT_TEMPLATE` / `ledger.py::_MERGE_SUBJECT_TEMPLATE` now triplicate the identical string literal with only a docstring comment asserting they stay in sync (blind-hunter finding) — real, but matches this module's own established precedent of deliberate per-file duplication over cross-module coupling (already 2x before this diff, between marshal.py and ledger.py); drift would surface as functional test failures given the size of this suite, and the "fix" (import the constant across files) would fight a design choice these same files already made on purpose. Not worth it.
  - `[low]` `[reject]` `ledger.py::_merged_ids_for_project`'s new `load_done_story_keys` call re-reads and re-parses the same tracked `sprint-status-ledger.yaml` that `gather_direction` (its caller) already parsed moments earlier via a different key-normalizer (blind-hunter finding) — real duplicate I/O against one small text file, negligible cost; the fix requires threading already-parsed state across a function boundary, more than a direct correction, for an effect nobody would notice.
  - `[low]` `[patch]` `marshal.py::_keys_from_merge_subjects`/`_keys_from_main_commits` call `load_done_story_keys` once per audited key inside `gather_story_status`'s per-key loop, re-reading/re-parsing the tracked ledger every time — unlike the `git log` calls immediately above in the same function, explicitly hoisted out of the loop for stated NFR-4 wall-clock reasons (blind-hunter finding). Real inconsistency with the function's own documented discipline; the fix (hoist the `known_keys` computation out of the loop, same shape as the existing git-call hoist) is small and well-precedented. Not applied this pass — all code reverts under the intent_gap entries above; worth re-adding once the corroboration mechanism itself is redesigned.
  - `[low]` `[reject]` `known_keys.py` has no dedicated unit test file; `_ledger_key_to_ref`'s no-match path, `_parse_statuses`'s comment/blank-line-skip logic, and `load_done_story_keys`'s `UnicodeDecodeError` branch are only indirectly exercised or not covered at all by the two callers' test suites (blind-hunter finding) — real gap on defensive/trivial branches, unlikely to be hit in practice, and the fix (several new direct unit tests) is more than a trivial correction. Not worth it on its own; moot regardless since this pass reverts all code.
  - `[low]` `[patch]` The new `ledger.py` test `test_sibling_default_template_merge_still_not_attributed_when_ledger_key_is_not_done` duplicates the pre-existing `test_sibling_default_template_merge_is_not_attributed_when_station_has_its_own`'s setup and assertion verbatim (same ledger status, same subject, same `fails == []` check), so it provides no discriminating regression-protection beyond the pre-existing test despite its docstring's claim to "pin why it still holds" (blind-hunter finding, independently confirmed by reading both tests). Not applied this pass — moot since all code reverts; a correctly-scoped replacement exercising the actual done-conflict collision (the shape the intent_gap findings above name) would supersede it.
  - `[low]` `[patch]` The "one function, both sources" invariant (this spec's own Boundaries, and the `known_keys.py` module docstring) has no automated enforcement, unlike this repo's own established precedent for exactly this class of cross-module invariant (`test_sources_marshal_independence.py`, `test_no_warden_import.py` — both cited by this same docstring) (blind-hunter finding) — nothing would fail CI if a future change reimplemented the bare-legacy-corroboration logic directly inside `marshal.py` or `ledger.py` instead of calling `known_keys.legacy_bare_merge_key`. Not applied this pass — moot since all code reverts; worth adding alongside the redesigned mechanism.

Attempted patch (reverted): `_bmad-output/implementation-artifacts/spec-27-3-attempted-patch-2026-09-18.patch`.

> **Landed empty — superseded by Story 27.4 (2026-09-18).** The dispatched session found a genuine intent gap in this
> spec's Approach (a station's ledger "knowing" a key cannot disambiguate a bare `Merge N-M into main` when several
> stations know the same key — the common case under one shared integer grammar), reverted to `baseline_revision`,
> saved `spec-27-3-attempted-patch-2026-09-18.patch`, and set `blocked`. `marshal factory dispatch` then verified and
> landed the reverted branch (PR #1476) and promoted `27-3 → done` regardless — a marshal gap recorded on
> `docs/dreams/pyforge-marshal.md` (a `blocked`/intent-gap outcome must never land). The ledger row stays `done`
> because `ledger-regression` (blocking in CI) forbids moving it back; this note is the truth of what shipped: nothing.
> The operator-delegated ruling that closes the gap — attribute a bare-form merge by the station paths its diff
> touches (git is the sole authority for merged facts) — is CAP-80's amended Approach and Story 27.4.

## Auto Run Result

Status: done
Reconciled 2026-09-20: the `blocked` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `9a89b3ec87 2026-09-18 marshal: promote sprint-status ledger for 'pyforge-doctor' (1 key(s) -> done)` — that promotion is the ruling this record now reflects.
Blocking condition: intent gap

**Unresolved questions** (for a human to settle before re-dispatch):
1. The Approach's corroboration rule — "attributed to the querying station only when that station's tracked ledger knows the key" — does not distinguish "this station's own pre-move history" from "an unrelated sibling station's own bare-form commit that happens to share a numeric key this station's ledger separately marks done." Given this repo's own commit history already shows numeric-key collisions across stations are common (the "3 findings into 306" residual CAP-78 first closed), what additional signal should settle a collision? Candidates: (a) accept the residual explicitly, as Story 35.1 already does for marshal's own dispatch-time check — same design shape, arguably already fleet-precedented; (b) refuse to attribute when the same key is independently claimed `done` by *more than one* project's ledger (a collision-detection guard); (c) some other scoping of which commits/subjects are eligible per project.
2. Should the spec's cited precedent, "Story 35.1's corroboration," be read as "any status" (what marshal's own `_load_known_story_keys` literally does) or "done only" (what this diff implemented, narrower, to close the *other* sibling-collision shape `sources/ledger.py`'s pre-existing test already pins)? The diff's choice is defensible and documented but not textually mandated by the spec.

Implementation was carried out in full per the spec text (see the attempted patch) and passed `pyforge-doctor-test` (1732 passed, 1 skipped) plus the manual `story-status-check` before review. Review found the mechanism itself unsafe against a collision shape neither the spec nor the implementation addresses, independently reproduced against a live synthetic repro (not just taken on the reviewing subagent's word). All code changes have been reverted to `baseline_revision`; only this spec file (status + triage log + this result) remains modified. The attempted patch is preserved at the path above for whoever resolves this gap.

**Residual risk:** none introduced — the working tree is back at `baseline_revision`; the underlying `marshal/34-3` false-green this story set out to fix remains unfixed pending re-dispatch.

## Status reconcile 2026-09-20

- Auto Run Result `Status: blocked` → `done` (see the reconcile line under it).
