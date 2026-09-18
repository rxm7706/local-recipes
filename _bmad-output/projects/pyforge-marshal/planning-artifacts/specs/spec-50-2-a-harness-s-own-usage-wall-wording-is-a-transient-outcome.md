---
title: '50.2: A harness''s own usage-wall wording is a transient outcome'
type: 'fix'
created: '2026-09-18'
status: 'in-review'
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
