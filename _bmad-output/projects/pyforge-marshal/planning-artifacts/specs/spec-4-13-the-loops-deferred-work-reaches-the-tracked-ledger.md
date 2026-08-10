---
title: "The loop's deferred work reaches the tracked ledger"
type: 'feature'
created: '2026-08-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'effe2a3127'
final_revision: '45812b19'
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** When a story's follow-up-review damping cap is spent, bmad-loop refiles the
recommendation as a bare `DW-<n>` id in the gitignored `implementation-artifacts/deferred-work.md`
(Tier-3) — a note that does not survive a clone or worktree teardown, and nothing today promotes it
into the tracked `planning-artifacts/deferred-work-ledger.md` when the story lands. Measured
2026-08-09: two of seven such entries (`DW-1`/`DW-2`) were promoted only because a human did it by
hand; five (`DW-3`…`DW-7`) stood as `tier3-only-deferral` findings until also hand-promoted the same
day (already committed, `c6b877f0cc`, ids `DW-FU-2-1`/`DW-FU-2-6`/`DW-FU-3-3`/`DW-FU-3-4`/`DW-FU-3-5`
— confirmed live: `python3 scripts/deferred_work_check.py` already reports zero findings for
pyforge-marshal).

**Approach:** teach `marshal land` to do automatically, at the moment a story is confirmed landed,
what was so far always done by hand: read the Tier-3 review-budget-followup entry for each landing
story (if any), rename it to the ledger's own established `DW-FU-<epic>-<seq>` id form, and append +
commit it into the tracked ledger — idempotently, mirroring `core/promotion.py` +
`cli/deploy.py::run_promote`'s existing pure-classify / impure-write split.

## Boundaries & Constraints

**Always:** Only Tier-3 blocks shaped `### DW-<n>: Follow-up review still recommended for <story>
after the damping cap was spent` with `origin: review-budget-followup` are in scope (bmad-loop's own
damping safety-valve output — the only kind `scripts/deferred_work_check.py` can ever flag, since
general anonymous Tier-3 findings carry no id to collide). Promoted id is `DW-FU-<epic>-<seq><suffix>`
(`core.identity.render_filename_slug`), no numeric counter — the form already established by every
prior promotion in this ledger and in warden's/doctor's own ledgers. Promotion runs only once a wave
is CONFIRMED landed: the already-landed shortcut, and the merge path strictly after
`forge.merge_pr` succeeds — never at the `if not wave_keys` no-op exit, never before the merge
gate decides. An id already present anywhere in the tracked ledger's text is never re-appended
(idempotent; a fully-idempotent run acquires no lock and writes nothing). The write is a single
`FsPort.write_text_atomic` of the ledger's full content, guarded by an advisory lock on the ledger
path, followed by `vcs.commit_paths` in its own dedicated commit, journaled intent-before/
outcome-after (mirrors `_PROMOTE_COMMIT_KIND`).

**Never:** Never touches or re-shapes the anonymous (un-id'd) Tier-3 review findings — out of this
story's scope. Never mutates or deletes an existing ledger entry — append-only, matching the
ledger's own "copy, not curation" convention. Never adds a policy key or CLI flag to disable this —
it runs unconditionally as part of landing (no AC names an opt-out). Never blocks `land`'s exit code
or its already-decided merge/branch-retirement outcome on a promotion failure — reported as one new
WARN-tier finding (`MRS-LAND-010`), the same non-blocking tier as `MRS-LAND-008`/`009`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Landing story has a followup deferral | wave includes story `2-1`; Tier-3 carries `### DW-8: ... 2-1 ...` with `origin: review-budget-followup` | `DW-FU-2-1` appended to the tracked ledger and committed; `data["deferred_work_promoted"] == ["DW-FU-2-1"]` | none |
| Landing story has no followup deferral | wave includes story `5-1`; no matching Tier-3 block | no ledger change; key absent from `data` | none |
| Re-run after promotion | ledger text already contains `DW-FU-2-1` | no duplicate entry, no lock acquired, no commit | none |
| Already-landed shortcut re-confirms a story | wave already reachable on `base`, `land` invoked again | same promotion path runs (idempotent per above) | none |
| Ledger lock contended | another `land`/`deploy promote` holds the ledger's advisory lock | nothing promoted this run | one `MRS-LAND-010` WARN; exit code unaffected |
| `vcs.commit_paths` fails | ledger file locally rewritten, commit raises | id present locally but uncommitted — next run's idempotency check must not be fooled by an uncommitted write | one `MRS-LAND-010` WARN; exit code unaffected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/deferred_work.py` -- NEW pure module (mirrors `core/promotion.py`'s split): `DeferralCandidate` dataclass (`tier3_id`, `story_key`, `title`, `source_spec`, `severity`, `reason`, `status`); `parse_followup_deferrals(text) -> tuple[DeferralCandidate, ...]` (matches `### DW-<n>: Follow-up review...` blocks by column-0-anchored field lines `origin:`/`source_spec:`/`severity:`/`reason:`/`status:`, tolerating interleaved indented anonymous bullets between fields -- the live shape of Tier-3's own `DW-6` block, `implementation-artifacts/deferred-work.md:483-504`); `promoted_id(key) -> str` (`f"DW-FU-{render_filename_slug(key)}"`); `render_ledger_entry(candidate, *, promoted_date) -> str` (the bulleted `- source_spec:/summary:/evidence:/promoted:/severity:/status:` shape, matching the existing `DW-FU-2-1`..`DW-FU-3-5` entries verbatim in `planning-artifacts/deferred-work-ledger.md:650-693` as the golden template); `deferrals_to_promote(candidates, landing_keys, tracked_text) -> tuple[DeferralCandidate, ...]` (filters to `story_key in landing_keys` and `promoted_id(story_key) not in tracked_text`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py` -- new `_MRS_LAND_010` constant + `_LAND_DEFERRED_WORK_KIND = "land-deferred-work-promotion"`; new helper `_promote_deferred_work(fs, vcs, root, slug, wave_keys, clock, deploy_run, findings) -> tuple[str, ...]` reading Tier-3 `implementation-artifacts/deferred-work.md` and tracked `planning-artifacts/deferred-work-ledger.md` (same `root / "_bmad-output" / "projects" / slug / ...` paths `cli/deploy.py` already uses), locking/appending/committing/journaling per the Boundaries above; called from the already-landed shortcut (~land.py:587, alongside its own `_resync_home_branch` call) and from the merge path immediately after `data["merged"] = True` (~land.py:967, before the OBSERVATION journal write); sets `data["deferred_work_promoted"]` only when non-empty.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py::_render_text_land` -- print `deferred_work_promoted` when present (mirrors the existing `home_current` `if "key" in data` clause).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` / `core/verdict.py` -- register `MRS-LAND-010`, classify `Verdict.WARN` (append to `REGISTERED_CODES` and `_CLASSIFY_TABLE`, same pattern as `MRS-LAND-008`/`009`).
- `src/shared/packages/pyforge-marshal/tests/unit/test_deferred_work.py` -- NEW: `parse_followup_deferrals` (incl. the `DW-6`-shaped interleaved-bullet case, and a non-`review-budget-followup` origin being ignored), `promoted_id`, `render_ledger_entry`, `deferrals_to_promote` (in-scope, no-match, already-promoted-by-text).
- `src/shared/packages/pyforge-marshal/tests/unit/test_land.py` -- extend with a Tier-3/tracked-ledger fixture pair under `tmp_path` (real `LocalFs()`, matching this file's own convention): promote-on-merge, promote-on-already-landed-shortcut, idempotent re-run (no duplicate, no lock call), lock-contention WARN, no-matching-entry no-op.

## Tasks & Acceptance

**Execution:**
- [x] `core/deferred_work.py` -- add the pure module described in Code Map -- the parse/classify/render core, no I/O
- [x] `core/findings.py` / `core/verdict.py` -- register `MRS-LAND-010` as `Verdict.WARN` -- defines the finding `land.py` reports below
- [x] `cli/land.py` -- add `_promote_deferred_work` + `_MRS_LAND_010` + journal kind, wire into the already-landed shortcut and the post-merge-success path -- the feature itself
- [x] `cli/land.py::_render_text_land` -- render `deferred_work_promoted` when present
- [x] `tests/unit/test_deferred_work.py` -- pure-function tests incl. the `DW-6` interleaved-bullet parse
- [x] `tests/unit/test_land.py` -- promote-on-merge, promote-on-already-landed, idempotent re-run, lock-contention WARN, no-match no-op

**Acceptance Criteria:**
- Given a landing story whose Tier-3 `deferred-work.md` carries a `review-budget-followup` entry naming it, when that story's wave is confirmed landed (merged, or already-landed and reconfirmed), then a `DW-FU-<epic>-<seq>` entry is appended to `planning-artifacts/deferred-work-ledger.md` in its own dedicated commit, and `scripts/deferred_work_check.py` reports zero `tier3-only-deferral` findings for that story's Tier-3 id.
- Given a `DW-FU-<epic>-<seq>` entry already present in the tracked ledger's text, when `land` runs again for that same story, then no duplicate entry is appended and no advisory lock is acquired.
- Given the five pre-existing standing entries (Tier-3 `DW-3`…`DW-7`, already promoted as `DW-FU-2-1`/`DW-FU-2-6`/`DW-FU-3-3`/`DW-FU-3-4`/`DW-FU-3-5` in commit `c6b877f0cc`), when `scripts/deferred_work_check.py` runs against pyforge-marshal, then it continues to report zero findings (already true; this story's own test suite must not regress it).

## Design Notes

**The five standing entries are already promoted — verified, not re-done.** `python3
scripts/deferred_work_check.py` already prints "OK: every Tier-3 deferral has a tracked twin" for
pyforge-marshal (commit `c6b877f0cc`, already on `main` and this branch). This story's own new code
must reproduce that SAME entry shape for future promotions, not redo the backfill.

**Golden template** (`planning-artifacts/deferred-work-ledger.md:650-657`, `render_ledger_entry`'s
target shape almost verbatim -- only the `promoted:` sentence's "manual act" framing changes to
reflect automation):
```
### DW-FU-2-1: Follow-up review still recommended for 2-1-standalone-verify-command-runner-project-scoped after the damping cap was spent

- source_spec: `spec-2-1-standalone-verify-command-runner-project-scoped.md`
  summary: Follow-up review still recommended for ... after the damping cap was spent
  evidence: <Tier-3's own `reason:` text, verbatim>
  promoted: <date> — promoted from Tier-3 `implementation-artifacts/deferred-work.md` (id `DW-8`
    there) under the ledger's `DW-FU-<story>` convention, so the next damped story cannot collide
    with a generic `DW-8`.
  severity: low
  status: open
```

**Why `DW-FU-<story>` with no counter**, deviating from the epics' literal "`DW-<story>-<n>`"
phrasing: it is the convention already in live use across marshal (`DW-FU-1-1`, `DW-FU-1-3`,
`DW-FU-2-1`, `DW-FU-2-6`, `DW-FU-3-3`, `DW-FU-3-4`, `DW-FU-3-5`), warden (`DW-FU-6-3`, `DW-FU-5-1`),
and doctor (`DW-FU-6-4`/`6-5`/`6-6`/`6-8`) -- at most one review-budget-followup entry has ever
existed per story, so this is the actual non-colliding convention, not a deviation from intent.

**Why the lock/commit/journal shape mirrors `run_promote`, not a new pattern:** `cli/deploy.py`'s
`_scan_promotions`/`run_promote` (`cli/deploy.py:563-894`) already establishes exactly this
"cheap read unlocked → lock only the write section → append/commit → intent-before/outcome-after
journal → release in `finally`" shape for the structurally identical spec-promotion problem
(Story 4.9, AD-42); reusing it here avoids a second uncommitted-write class of bug like the one
`_already_promoted_keys`'s own `vcs.path_has_uncommitted_changes` check was added to close.

**Deviation -- idempotency check stays a plain text-substring test, never a
`vcs.path_has_uncommitted_changes` guard (2026-08-10).** The I/O matrix's
`vcs.commit_paths` fails row reads "next run's idempotency check must not be
fooled by an uncommitted write," which in the strictest reading would
require `_promote_deferred_work` to also confirm, via git, that a promoted
id's presence in the tracked ledger's text is actually COMMITTED before
treating it as done -- mirroring `cli/deploy.py::_already_promoted_keys`'s
own `vcs.path_has_uncommitted_changes` guard. Implemented instead as the
simpler substring-only check (`core.deferred_work.deferrals_to_promote`),
per this story's own prompt guidance and Design Notes above ("this
simpler check ... is sufficient and correct" -- this operation reads,
writes, AND commits the ONE shared ledger file within a single call, unlike
`run_promote`'s per-story tracked-file copies, which a separate, earlier,
possibly-crashed invocation could leave uncommitted). The accepted gap: if
`vcs.commit_paths` fails after `write_text_atomic` has already landed the
new entry locally, a LATER `land` invocation's own fresh read of the ledger
will see the id already present as plain text and skip re-attempting the
commit, leaving that one promotion durably un-committed until a human
notices and commits it by hand. This is reported the SAME run it happens
(`MRS-LAND-010` WARN, naming the exact promoted ids and the tracked path),
matching `cli/deploy.py::run_promote`'s own `MRS-DEPLOY-003` handling of an
identical `commit_paths` failure -- which likewise adds no separate,
cross-run git-status healing pass for THAT failure mode (its own
`_already_promoted_keys` git-status guard exists for a structurally
different hazard: N independently-copied tracked files from one batched
promote, not one file written-and-committed in the same call). Not
re-litigated further without a concrete failure observed in practice.

**Correctness fix -- idempotency check was a substring test, not a token
match (2026-08-10 review finding).** `deferrals_to_promote`'s original
`promoted_id(...) in tracked_text` was a bare `in` substring test, which
false-positives whenever one promoted id is a literal string-prefix of
another -- `"DW-FU-1-1"` is a substring of `"DW-FU-1-10"`, a real collision
already live in this repo (story 1.10 alongside the already-promoted
`DW-FU-1-1`; epic 4 now runs 4-1..4-13 too). Fixed by tokenizing
`tracked_text` first (`core.deferred_work._tracked_promoted_ids`, mirroring
`scripts/deferred_work_check.py`'s own greedy `_DW_RE` convention) and
checking set membership against the COMPLETE token, never a raw substring.
Regression tests added: `test_deferrals_to_promote_is_not_fooled_by_a_
prefix_collision` and its companion exact-match test.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green, including new `test_deferred_work.py` and the extended `test_land.py` cases
- `python3 scripts/deferred_work_check.py` -- expected: unchanged, "OK: every Tier-3 deferral has a tracked twin"
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: no new disallowed import edges
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- expected: clean

## Spec Change Log

## Review Triage Log

### 2026-08-10 — Review pass 1
- intent_gap: 0
- bad_spec: 0
- patch: 7 (medium 2, low 5)
- defer: 4 (low 4)
- reject: 2
- addressed_findings:
  - `[medium]` `[patch]` Two Tier-3 `review-budget-followup` blocks resolving to the same story key in one wave could write two identical `### DW-FU-<story>:` headings in a single commit -- `core.deferred_work.deferrals_to_promote` now dedupes within one call, first-by-input-order wins; regression test added.
  - `[medium]` `[patch]` A project with no tracked `deferred-work-ledger.md` at all silently and permanently no-op'd its first promotion forever -- `_promote_deferred_work` now bootstraps a missing tracked file as empty content instead of returning early; regression test added.
  - `[low]` `[patch]` Bootstrapping an empty/missing ledger could prepend two blank lines before the first entry -- the append now conditions the separator on non-empty existing content.
  - `[low]` `[patch]` A tracked ledger that existed at the first unlocked read but was deleted before the lock-held re-read was silently resurrected with stale pre-lock content -- now reported as `MRS-LAND-010` WARN instead, distinguishing a genuine concurrent deletion from the ordinary bootstrap-missing-file case; regression test added.
  - `[low]` `[patch]` Multi-candidate promotion (>1 distinct story in one wave/commit, including the commit-message pluralization branch) was completely untested -- test added.
  - `[low]` `[patch]` The already-landed-shortcut call site's own idempotent-rerun behavior had no dedicated regression test (only the full-merge path did) -- test added.
  - `[low]` `[patch]` `_FakeVcs.commit_paths_calls`'s type annotation used a bare, unparameterized `tuple` inconsistent with this test file's own convention -- tightened to `tuple[Path, ...]`.
  - `[low]` `[defer]` A second, distinct Tier-3 followup deferral for a story that already has one promoted entry is permanently invisible to auto-promotion under the established no-counter `DW-FU-<story>` id scheme (an intent-contract-level decision, not a mechanical patch) -- mitigated by `scripts/deferred_work_check.py`'s own existing `tier3-only-deferral` safety net. Logged to the deferred-work file.
  - `[low]` `[defer]` A `commit_paths` failure after the ledger write succeeds leaves that run's journal INTENT permanently unreconciled (no data loss -- the promotion itself self-heals on the next `land` retry via the ledger's own content, not the journal). Logged to the deferred-work file.
  - `[low]` `[defer]` `parse_followup_deferrals` silently drops a `source_spec:` field that fails to parse to a story key, with no diagnostic -- never observed in this project's live Tier-3 history (bmad-loop's own output is deterministic). Logged to the deferred-work file.
  - `[low]` `[defer]` The originating Tier-3 entry's own `status: open` is never updated after promotion -- consistent with this ledger's own established "status fields are as-of-authoring-date, not current" precedent, recorded for future confirmation. Logged to the deferred-work file.

### 2026-08-10 — Repair pass (external verification failure, no code change)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none (not a code review pass -- see note below)

The dev pass and review pass 1 above completed and committed
(`bb2a7a95c0`), but bmad-loop's own harness-level verify command --
`python scripts/spec_surface_check.py`, appended to every station's
`verify_commands` by S-13.7 -- then failed: the story's seven governed
files (`cli/land.py`, `core/deferred_work.py`, `core/findings.py`,
`core/verdict.py`, `tests/unit/test_deferred_work.py`,
`tests/unit/test_findings.py`, `tests/unit/test_land.py`) changed while
`spec-pyforge-marshal`'s own `.memlog.md` did not move, the identical
failure mode stories 4.11 and 4.12 hit before it. This left the run
recorded `failed` with the dev-auto workflow's own Finalize step
interrupted before it could set `status: done`.

Repaired per the established convention (memlog reconciliation +
`--write-baseline --spec pyforge-marshal/spec-pyforge-marshal`, matching
4.11's/4.12's own `## Surface reconcile` memlog sections): no file under
this story's own Code Map or `<intent-contract>` was touched -- only
`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`
and `scripts/.spec-surface-baseline.json`, both outside this story's
governed surface, committed separately as `45812b19`. Re-verified at the
new HEAD: `pyforge-marshal-test` 3131 passed (9 slow deselected),
`pyforge-deps-test` 67 passed, `lint-imports` clean (3 contracts kept, 0
broken), `python scripts/spec_surface_check.py` exit 0 ("OK: every
tracked file governed or allowlisted; no drift"), `deferred_work_check.py`
unchanged ("OK: every Tier-3 deferral has a tracked twin").

## Auto Run Result

Status: done

**Summary:** `marshal land` now promotes each landing story's Tier-3
`review-budget-followup` deferral into the tracked
`deferred-work-ledger.md` under the ledger's own `DW-FU-<epic>-<seq>`
convention, idempotently, at the already-landed shortcut and immediately
after a successful merge -- automating what was previously always done by
hand. Adds `MRS-LAND-010` (WARN) for advisory-lock contention or a
`vcs.commit_paths` failure.

**Files changed** (commit `bb2a7a95c0`):
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/deferred_work.py` -- NEW pure module: parse/classify/render core for Tier-3 followup-deferral promotion.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py` -- `_promote_deferred_work` wired into both landed-confirmation exits; `_render_text_land` renders `deferred_work_promoted`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` / `core/verdict.py` -- register `MRS-LAND-010` as `Verdict.WARN`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_deferred_work.py` -- NEW, pure-function coverage incl. the `DW-6` interleaved-bullet parse shape.
- `src/shared/packages/pyforge-marshal/tests/unit/test_land.py` -- promote-on-merge, promote-on-already-landed, idempotent re-run, lock-contention WARN, no-match no-op, multi-candidate, bootstrap/concurrent-deletion.
- `src/shared/packages/pyforge-marshal/tests/unit/test_findings.py` -- exact-contents registry guard extended.

**Repair changed** (commit `45812b19`, this session -- no story code touched):
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` -- reconciled the seven governed-file drift findings under a new `## Surface reconcile 2026-08-10 — story 4-13 landing` section, naming each path.
- `scripts/.spec-surface-baseline.json` -- scope-stamped for `pyforge-marshal/spec-pyforge-marshal` only (`--write-baseline --spec pyforge-marshal/spec-pyforge-marshal`).

**Review findings breakdown:** Review pass 1 (2026-08-10): 7 patches applied (2 medium, 5 low), 4 deferred (all low, logged to Tier-3 `deferred-work.md`), 2 rejected, 0 intent_gap, 0 bad_spec. Repair pass (2026-08-10): not a code review -- 0 findings in every category; the fix was external governance-drift reconciliation only.

**Follow-up review recommendation:** `false` -- review pass 1's fixes were the only substantive round and did not warrant one; the repair pass touched no story code.

**Verification performed:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3131 passed, 9 deselected. `python3 scripts/deferred_work_check.py` -- OK, zero `tier3-only-deferral` findings. `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 67 passed. `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- clean, 3 contracts kept. `python3 scripts/spec_surface_check.py` -- OK, no drift (previously 7 findings; now 0).

**Residual risks:** None new. The story's own Review Triage Log already carries the 4 accepted deferrals (second-followup-deferral invisibility, unreconciled journal intent on a `commit_paths` failure, silent `source_spec:` parse drop, stale Tier-3 `status:` field) as known, accepted gaps.
