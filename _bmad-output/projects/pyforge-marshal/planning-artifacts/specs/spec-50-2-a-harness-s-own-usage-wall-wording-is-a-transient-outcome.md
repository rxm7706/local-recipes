---
title: '50.2: A harness''s own usage-wall wording is a transient outcome'
type: 'fix'
created: '2026-09-18'
status: 'done'
baseline_revision: 'e484f16ce071f650e59ece2fb2efc3219322f16b'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred:
  - summary: >-
      Only Claude and Cursor have quota-marker entries in
      `_QUOTA_MARKERS_BY_HARNESS`; the other configured harnesses (gemini,
      copilot, devin, codex, antigravity, opencode) still misclassify their
      own usage-wall wording as `unknown`/terminal.
    evidence: |-
      Real latent gap, but pre-existing (every non-Claude/Cursor harness had
      zero markers before this story too) and not caused by this diff. The
      Approach explicitly scoped this fix to Cursor's live text from the
      named 2026-09-18 incident, not to every configured harness. Close the
      next instance the same way this one was closed: from a real run
      journal, not a guess at wording.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_session.py:28
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `classify_session_log` returned `unknown` for `ActionRequiredError: Increase limits for faster responses You're out of usage. Switch to Auto, or ask your admin to increase your limit to continue.` (none of `monthly spend limit` / `spend limit` / `usage limit` / `rate limit` / `quota exceeded` / `insufficient quota` match), so `classify_dispatch_block` returned `terminal` and the drain refused 23.1 until a human re-dispatched it

**Approach:** the marker table recognises `out of usage` and `increase your limit` (Cursor) beside the Claude Code weekly/monthly-limit text already catalogued, keyed per harness in one place

## Boundaries & Constraints

**Always:**
- the fixture classifies `QUOTA_EXCEEDED`, `classify_dispatch_block(session_log=fixture, failed_gate=None, changed_path_count=0)` returns `TRANSIENT`, and `exclude_harness_profiles_after_transient_failure` drops the first preference entry for it
- removing the new markers re-terminalises the fixture (mutation test), and no existing classification changes (the current marker fixtures stay green)

**Never:**
- Do not make the supervisor trust a session's self-report, add a second gate, or re-attribute landed history — the Epic 50 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the 2026-09-18 fixture | the real run/journal named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-245`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_session.py` (`_QUOTA_MARKERS` becomes per-harness and covers Cursor's live text), `.../core/dispatch_retry.py` (no behaviour change expected; covered by test), tests with the real `pyforge-herald-20260918T132400673Z-194af3a0` session log as a fixture.
Ledger key: `50-2-a-harness-s-own-usage-wall-wording-is-a-transient-outcome`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-50-2-a-harness-s-own-usage-wall-wording-is-a-transient-outcome.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- `classify_session_log` on the real `pyforge-herald-20260918T132400673Z-194af3a0` session.log returns `QUOTA_EXCEEDED`; `classify_dispatch_block(..., changed_path_count=0)` returns `TRANSIENT`; removing the marker re-terminalises it.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 7 findings — high 0, medium 2, low 2, false 3, maybe-false 0
- findings:
  - `[medium]` `[defer]` Only Claude and Cursor are covered in `_QUOTA_MARKERS_BY_HARNESS`; other configured harnesses still misclassify their own usage-wall wording as terminal — real latent gap, but pre-existing (every non-Claude/Cursor harness had zero markers before this story too) and the Approach explicitly scoped this fix to Cursor's live text from the named incident. Recorded in `deferred:`.
  - `[false]` `[reject]` "The per-harness dict is built but `classify_session_log` pools it into one flat tuple instead of consulting it by key" — `classify_session_log(log_text)` has never taken a harness argument (pre-existing, unchanged signature); the Approach's own words are "keyed per harness in one place," i.e. organizational/provenance, not a request for per-harness-scoped matching. Not a regression this diff introduced.
  - `[low]` `[reject]` New markers (`out of usage`, `increase your limit`) are bare, unanchored substrings with false-positive risk — true, but identical in shape/risk to every pre-existing marker in the same tuple (`usage limit`, `rate limit`, etc.); not a new risk pattern, and a guard would add branching complexity for a risk this file already accepts everywhere else.
  - `[false]` `[reject]` New tests "break the file's established grouping-by-scenario convention" — checked: no such convention exists. `test_transient_block_on_quota_with_no_git_progress` (pre-existing) sits multiple unrelated tests away from `test_classify_session_log_quota`; the new tests are in fact placed adjacently to the existing quota test, which is more grouped than the file's pre-existing norm.
  - `[low]` `[reject]` Module docstring not updated to describe the per-harness structure — the diff already documents the rationale in a comment directly above `_QUOTA_MARKERS_BY_HARNESS`, at the point of use; a module-level docstring edit would be redundant with it.
  - `[false]` `[reject]` Intent Alignment: diff uses a hand-typed inline string instead of "the real session log as a fixture" per the Binding text, and no such fixture file exists in the repo — verified independently: the real file (`.../pyforge-herald-20260918T132400673Z-194af3a0/session.log`, untracked/gitignored, present in a sibling local checkout) is byte-identical to `_CURSOR_USAGE_WALL_LOG`, confirmed by running `classify_session_log`/`classify_dispatch_block` directly against its contents (`quota_exceeded`/`transient`, matching the Always bullets). The file's own established convention (`test_classify_session_log_auth`, `test_classify_session_log_quota`, etc.) is inline literal strings for every scenario, not file fixtures, so "the real ... log as a fixture" reads as "use the real wording," which this diff does and I've now verified byte-for-byte.
  - `[medium]` `[patch]` The Always bullet "removing the new markers re-terminalises the fixture (mutation test)" had no dedicated named test — only verified ad hoc during implementation, not preserved as a regression guard. Patched: added `test_classify_session_log_reterminalizes_without_cursor_markers`, which monkeypatches `_QUOTA_MARKERS` back to the Claude-only set and asserts the fixture returns to `unknown`. Both verify commands re-run green after the patch (marshal: 8066 passed/1 skipped; deps: 130 passed/3 skipped).

## Auto Run Result

**Summary:** `_QUOTA_MARKERS` in `core/harness_session.py` is now keyed per harness
(`_QUOTA_MARKERS_BY_HARNESS`, `claude` + `cursor`), adding Cursor's live usage-wall
wording (`out of usage`, `increase your limit`) alongside the already-catalogued
Claude text, so `classify_session_log` recognizes it and `classify_dispatch_block`
returns `TRANSIENT` instead of `terminal` for the 2026-09-18 incident's fixture.
`classify_session_log`'s own pooled-matching behavior (harness-agnostic; it takes
no harness argument) is unchanged — the per-harness table is a provenance/single-
source-of-truth grouping, not a new scoping mechanism, per the Approach's own
"keyed per harness in one place" wording.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_session.py` — `_QUOTA_MARKERS` replaced by `_QUOTA_MARKERS_BY_HARNESS` (`claude`, `cursor`), flattened into the same `_QUOTA_MARKERS` tuple `classify_session_log` already consulted.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_hotfix.py` — added `_CURSOR_USAGE_WALL_LOG` fixture string (verified byte-identical to the real, untracked `pyforge-herald-20260918T132400673Z-194af3a0/session.log`) and four tests: quota classification, transient dispatch-block, harness-preference exclusion, and the mutation test added during review triage.

**Review findings breakdown:**
- Patched (1): missing dedicated mutation test for the "removing markers re-terminalises the fixture" Always bullet — `medium`.
- Deferred (1): other configured harnesses (gemini, copilot, devin, codex, antigravity, opencode) still have no quota markers — `medium`, pre-existing, out of this story's stated Approach scope; recorded in `deferred:` frontmatter for the next incident that surfaces one.
- Rejected (5): per-harness dict pooled rather than key-scoped in matching (`false` — `classify_session_log` never took a harness argument; Approach only asked for organizational keying); false-positive risk from the two new bare-substring markers (`low` — identical shape/risk to every pre-existing marker, not a new pattern); new tests "break" a grouping convention (`false` — no such convention exists in the file, verified against pre-existing test placement); module docstring not updated (`low` — the per-use comment already documents the rationale); hand-typed inline fixture string instead of a captured fixture file (`false` — verified byte-identical to the real untracked log by running `classify_session_log`/`classify_dispatch_block` directly against it, and inline strings are this file's established convention for every scenario).

**Follow-up review recommendation:** `false` (first pass; the one patched entry was `medium`, not `high`, and only one medium entry was patched — threshold requires two or more).

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 8066 passed, 1 skipped (post-patch; was 8065 passed pre-patch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed, 3 skipped.
- Manual: ran `classify_session_log` and `classify_dispatch_block` directly against the real (untracked, gitignored) `pyforge-herald-20260918T132400673Z-194af3a0/session.log` file content (found in a sibling local checkout at `local-recipes/_bmad-output/projects/pyforge-herald/implementation-artifacts/dispatch-runs/...`) — returned `quota_exceeded` / `transient`, matching both Always bullets. Confirmed the file's content is byte-identical to `_CURSOR_USAGE_WALL_LOG`.
- Mutation test (`test_classify_session_log_reterminalizes_without_cursor_markers`) independently confirms the fix is load-bearing: reverting to the Claude-only marker set re-terminalises the fixture.

**Residual risks:** the deferred harness-coverage gap (other harnesses still unrecognized) is the only open item, and is out of this story's scope per its Approach.
