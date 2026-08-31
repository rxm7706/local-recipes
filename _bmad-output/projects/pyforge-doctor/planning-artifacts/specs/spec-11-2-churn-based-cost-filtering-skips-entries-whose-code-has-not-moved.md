---
title: 'Churn-based cost filtering skips entries whose code has not moved'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false # judged: 5 patches, all localized correctness/robustness fixes to a brand-new WARN-only advisory feature, no API/security/data-model impact, full suite verified green after each
context: []
warnings: ['oversized']
baseline_revision: '415595ef93c6c67dc07d41a788f483aedcb02ca3'
final_revision: '7c2969a2e0f2487c32646843979add97d7c0ab9b'
---

<intent-contract>

## Intent

**Problem:** Story 11.1's `gather_due_for_verification` selects every tracked ledger entry due
for re-check (~400+ fleet-wide, growing) — but nothing yet distinguishes an entry whose named
code hasn't moved since it was last looked at from one that genuinely needs the next story's
(11.3) expensive mechanical/agent verification. Without a cost filter, every due entry is an
equally-priced verification candidate.

**Approach:** Extend `_check_project_due_for_verification` (chain.py) to compute, per due
entry, whether its ledger-cited code path(s) have any git commits since the entry's
last-verified date (or its own authoring date, when never verified). When every extractable
path is churn-free, tag that entry's existing `Finding.evidence` with `skip_reason: "no-churn"`
— the SAME Finding stays in the WARN report, visibly marked, never removed.

## Boundaries & Constraints

**Always:** Reuse the same `Source.DUE_FOR_VERIFICATION` stream — no new Source/REGISTRY/
DISPATCH/schema entry (`check` and `evidence` are unconstrained). A skip decision is an
ADDITIVE evidence key on the finding 11.1 already emits for that entry, never a new/removed
Finding. Extract candidate paths only from an entry's own body text (between its heading and
the next), EXCLUDING the `source_spec:` line (provenance, not the code under claim) — a path
token is a backtick-quoted string containing a `.`-extension or a `/`, optional `:LINE` suffix.
Resolve churn per path via two `cli_bridge.run_git` calls: (1) `git log --oneline -1 -- <path>`
— empty means never tracked in this repo (typo/external/cross-repo) and must NOT read as
churn-free; (2) `git log --oneline --since <date> -- <path>` — non-empty means changed inside
the window. An entry is `skip_reason: "no-churn"` only when it has ≥1 extracted path AND every
one resolves in step 1 AND every one is empty in step 2 — any unresolved or churned path, or
zero extracted paths, means NOT skipped (fail toward re-verification, same precedent 11.1 set
for a malformed date). For `reason: "stale"`, the window start is the already-parsed `verified:`
date; for `reason: "never-verified"`, derive an authoring-date proxy via
`git log --reverse --format=%ad --date=short -G '<id>[^A-Za-z0-9-]' -- <tracked ledger path>`,
first line — the id-charset-anchored regex (not a bare `-S "<id>"`) matters: a plain substring
search collides with any longer id sharing the same prefix (e.g. `DW-1-1-1` inside `DW-1-1-10`),
which measurably returns the WRONG, earlier date (verified live in a throwaway repo: naive
search returned 2026-02-01 from an unrelated `DW-1-1-10` addition instead of the real
`DW-1-1-1` entry's own 2026-03-01 introduction). Unresolvable authoring date → not skipped.
A git failure for one entry's churn check degrades to "not skipped" for THAT entry alone — must
never propagate to the project-level try/except that isolates per-project ledger-read failures.
Status stays WARN always, unchanged from 11.1.

**Block If:** None — both design questions the epic left implicit (what "named path" means for
an entry citing several; what "since authoring" means with no authored-date field) are resolved
above, not deferred.

**Never:** Implement the mechanical/agent verification tiering itself (11.3's territory) — 11.2
only computes and records a skip/proceed signal. Add a new `Source` enum member. Mutate a
ledger file. Treat a currently-nonexistent-on-disk path as automatically churned or
churn-free — existence is decided by git history (a since-deleted-but-tracked path still
counts as churn via its deletion commit), never by `Path.exists()`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|-----------------|
| Single path, untouched since date | stale entry citing `` `foo.py:10` ``, zero commits since `verified:` date | `skip_reason: "no-churn"` added | No error |
| Single path, touched since date | stale entry citing `` `foo.py:10` ``, ≥1 commit since date | No `skip_reason`; finding unchanged from 11.1 shape | No error |
| Two paths, one churned | entry citing `` `a.py` `` (clean) and `` `b.py` `` (churned) | No `skip_reason` — any churned path blocks the skip | No error |
| Path never tracked here | entry citing `` `bmad_loop/verify.py:1474` `` (external package, not this repo) | No `skip_reason` — unresolved path defaults to not-skipped | No error |
| No extractable path | entry body has prose but no backtick path-like token | No `skip_reason` | No error |
| Never-verified, authoring date resolvable | no `verified:` line; anchored `-G` search finds the entry's own introduction commit | Churn window starts at that commit's date | No error |
| Never-verified, authoring date unresolvable | anchored search returns nothing | No `skip_reason` (fail toward verification) | No error |
| `source_spec:` cites a path | the field's own value is a `.md` path | Never a churn-check candidate | No error |
| Per-entry git failure | `run_git` raises for one entry's churn lookup | That entry gets no `skip_reason`; every other entry in the project unaffected | Isolated, no exception propagates |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:2379-2513` (the
  `gather_due_for_verification` section, Story 11.1) -- add `_PATH_TOKEN_RE`,
  `_SOURCE_SPEC_LINE_RE`, `_entry_named_paths(path)`, `_authored_date(target, tracked_path,
  entry_id)`, `_churn_since(target, rel_paths, since)`; extend
  `_check_project_due_for_verification` (`:2422`) to call them and attach
  `skip_reason`/`churn_checked_paths`; extend `_due_for_verification_message` (`:2483`) to
  describe a skip decision in the message text.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli_bridge.py:82` (`run_git`) -- reused
  unchanged; `chain.py`'s own `_tracked_files` (`:851`) is the exact
  `try/except (CliBridgeError, UnicodeDecodeError)` idiom to mirror at every new call site.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py` --
  add churn-specific cases alongside 11.1's, same `_write_tracked`/`_project_dir` fixtures for
  ledger text; new cases additionally need a real `git init`-ed `tmp_path` with dated commits --
  mirror `test_sources_marshal_story_status.py`'s `_isolate_git_env` autouse fixture +
  `_init_repo`/`_commit` git-subprocess helpers (test files are exempt from the sole-subprocess
  restriction; use `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` env vars for deterministic dates --
  verified live that `git log --since` filters on COMMITTER date, so set both explicitly).
- `pixi.toml:538` (`due-for-verification-check` task) -- extend the description with the
  churn-skip behavior; `Contract:` line gains `+ CAP-2`.

## Tasks & Acceptance

**Execution:**
- [x] `chain.py` -- add `_PATH_TOKEN_RE`/`_SOURCE_SPEC_LINE_RE` + `_entry_named_paths()` --
  extracts every candidate code path per entry from its own body, excluding `source_spec:`.
- [x] `chain.py` -- add `_authored_date()` -- id-anchored pickaxe derives a never-verified
  entry's authoring date from the tracked ledger's own git history.
- [x] `chain.py` -- add `_churn_since()` -- two-step (history-exists, then since-filtered) git
  churn check per path, short-circuiting to "changed" on the first churned path.
- [x] `chain.py` -- extend `_check_project_due_for_verification()` to call the three helpers and
  attach `skip_reason`/`churn_checked_paths` when every path is churn-free.
- [x] `chain.py` -- extend `_due_for_verification_message()` to append skip-decision text when
  `skip_reason` is present.
- [x] `test_sources_chain_due_for_verification.py` -- one test per I/O matrix row above, real
  git fixtures for churn scenarios, including the id-prefix-collision case.
- [x] `pixi.toml` -- update the `due-for-verification-check` task description + `Contract:` line.

**Acceptance Criteria:**
- Given an entry selected by 11.1 whose only named path has zero commits since its churn-window
  start date, when the sweep runs, then its Finding's evidence carries `skip_reason: "no-churn"`.
- Given the same entry but with ≥1 commit to its named path inside the window, when the sweep
  runs, then no `skip_reason` key is present and the Finding is otherwise identical to 11.1's
  own shape.
- Given an entry citing a path with no git history at all in this repo, when the sweep runs,
  then it is never skipped.
- Given a project where one entry's churn check fails, when the sweep runs, then every other
  entry in that project still reports normally.

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 2, low 3)
- defer: 2: (low 2)
- reject: 6: (low 6)
- addressed_findings:
  - `[medium]` `[patch]` `paths_by_id = dict(_entry_named_paths(tracked_path))` collapsed a duplicate (malformed, invariant-violating) entry id to its LAST occurrence's paths, so an earlier duplicate would be churn-checked against the wrong entry's cited code (Edge Case Hunter). Replaced with positional `zip(_verification(...), _entry_named_paths(...), strict=True)` — both walk the same `_ENTRY_RE` marks over the same text, so pairing is correct regardless of id repeats, and `strict=True` turns a genuine cross-read desync into an isolated per-project WARN instead of a silent mismatch.
  - `[medium]` `[patch]` `test_per_entry_churn_failure_is_isolated_from_its_project_siblings` monkeypatched `chain._churn_since` itself to raise, which only ever exercised `_attach_churn_skip`'s redundant OUTER except — a path `_churn_since` never actually takes in production, since it already catches every `run_git` failure mode internally (Blind Hunter). Rewrote to monkeypatch `chain.run_git` to raise `CliBridgeError` for one specific path, exercising the real internal isolation mechanism end to end.
  - `[low]` `[patch]` `_churn_since`'s second git call (the `--since`-filtered existence check) omitted `-1`, so a frequently-touched path would have git enumerate every matching commit in the window instead of stopping at the first, working against the story's own cost-bound purpose (Blind Hunter). Added `-1`.
  - `[low]` `[patch]` `_authored_date`'s docstring undersold a real (if unlikely) gap: without `--follow`, a ledger rename before an entry's true introduction would truncate the pickaxe search to post-rename history and resolve too LATE a date, narrowing the churn window and masking real earlier churn (Edge Case Hunter). Added `--follow` — a no-op unless a rename is ever detected, so strictly safe.
  - `[low]` `[patch]` `_entry_named_paths`'s docstring said `source_spec:`'s "path-shaped value" is excluded, but the code strips the WHOLE line (Blind Hunter + Edge Case Hunter, same finding). Corrected the docstring to describe and justify the actual whole-line behavior (the ledger's one-field-per-line convention means no real entry co-locates a legitimate citation on that line) rather than narrowing the regex for a case that does not occur.
  - `[low]` `[reject]` (x6) Six findings were each checked directly and found to be either noise or already correctly handled: an unanchored LEFT boundary on the `-G` id-collision pattern (asserted-but-undemonstrated — the literal `DW-` prefix makes a real left-side collision structurally near-impossible, no concrete failure scenario given); the `-G` search matching an id anywhere it appears (not just its own heading) potentially resolving an EARLIER authored-date (verified this fails toward the SAFE direction — an earlier date widens the churn window, making a false skip LESS likely, the same "fail toward re-verification" philosophy already established); a bare heading with no trailing character after the id (degrades to the same already-tested "unresolvable → not skipped" fallback, not a new code path); `_entry_named_paths` performing a second independent read/scan of the ledger rather than sharing `_verification`'s read (the SAME deliberate duplication-over-shared-primitive pattern Story 11.1 itself established for `_verification()` vs `_entries()`, not a new problem); the same-day `--since` boundary being untested (tests git's own well-defined behavior, not this story's logic); and a TOCTOU race between the two independent `read_text()` calls (now additionally mitigated as a side effect of the `strict=True` zip fix above, which converts any real desync into an isolated, caught per-project WARN rather than a silent mismatch).
  - `[low]` `[defer]` No caching of churn-check git calls across entries citing the same path — a genuine future cost-optimization opportunity at greater fleet scale (correct memoization needs a `(path, since)` compound key, a real design addition beyond this story's resolved scope), no measured current performance problem. Minted `DW-FU-11-2`.
  - `[low]` `[defer]` The churn check only sees the current checkout's HEAD (no `--all`/explicit ref) — a pre-existing, repo-wide ambient pattern shared by every other git-based Doctor check in this file, not unique to this story; bounded consequence (advisory, non-mutating, self-correcting on the next sweep). Minted `DW-FU-11-2-2`.

## Design Notes

- Path extraction and the churn check both duplicate small existing shapes (`_verification`'s
  boundary-walk; `_tracked_files`'s try/except-to-degrade idiom) rather than refactor them --
  mirrors this file's own established precedent of duplicating a ~10-line shape over extracting
  a "verbatim from the original" primitive.
- The evidence key is `skip_reason` (snake_case, matching `days_stale`/`projects_scanned`) with
  literal value `"no-churn"` -- the epic's `skip-reason: no-churn` wording spells the VALUE, not
  the key.
- Entry-id charset (`[A-Za-z0-9-]`, per `_ENTRY_RE`) contains no regex metacharacters, so
  interpolating an id directly into the `_authored_date` `-G` pattern needs no escaping.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary.** Extended Story 11.1's `gather_due_for_verification` pipeline with churn-based cost
filtering: for each due ledger entry, extract its ledger-cited code path(s), determine a
churn-window start date (the `verified:` date for a stale entry, or a git-pickaxe-derived
authoring date for a never-verified one), and — only when every extractable path is confirmed
to have zero commits in this repo since that date — tag the SAME 11.1 finding's evidence with
`skip_reason: "no-churn"`. Any unresolved path, any churned path, or zero extractable paths
leaves the entry fully due (the safe default). Story 11.1's own code (not yet on `main`) was
fast-forward-merged into this worktree first, since 11.2 is a strict pipeline dependent on it.

**Files changed:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- new
  `_PATH_TOKEN_RE`/`_SOURCE_SPEC_LINE_RE`/`_entry_named_paths`/`_authored_date`/`_churn_since`/
  `_attach_churn_skip`; `_check_project_due_for_verification` and `_due_for_verification_message`
  extended to compute and surface the skip decision. No new `Source`/REGISTRY/DISPATCH/schema
  entries -- reuses `Source.DUE_FOR_VERIFICATION` entirely.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py` --
  11 new tests (one per I/O matrix row, including a dedicated id-prefix-collision case for
  `_authored_date`, plus 2 message-text tests), real `git init`-ed fixtures with
  `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`-pinned commits, no mocking of `run_git` itself except in
  the one test that specifically needs to simulate a real git failure.
- `pixi.toml` -- `due-for-verification-check` task description documents the churn-skip behavior;
  `Contract:` line now names CAP-1 + CAP-2.

**Review findings.** One review pass, Blind Hunter + Edge Case Hunter in parallel: 5 patches
applied (2 medium: a duplicate-entry-id path-collapse correctness fix, and a test rewritten to
exercise a real `run_git` failure instead of an internal shim; 3 low: a missing `-1` on a git
call, a missing `--follow` safety flag, a docstring/behavior precision fix), 2 low-severity items
deferred to the tracked ledger (`DW-FU-11-2` memoization opportunity, `DW-FU-11-2-2` single-branch
git-history scope -- both pre-existing-pattern-adjacent, bounded-consequence, out of this story's
resolved scope), 6 rejected as noise or already-correctly-handled after direct verification. Full
triage detail in the Review Triage Log above. No intent gaps, no bad-spec findings -- the spec's
two epic-left-implicit design questions (multi-path handling, "since authoring" derivation) held
up under adversarial review without requiring a loopback.

**Verification performed (all green, after the patch pass):**
- `pixi run -e local-recipes pytest .../test_sources_chain_due_for_verification.py -v`: 33 passed.
- `pixi run -e local-recipes pytest .../test_sources_registry.py -v`: 18 passed.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`: 966 passed, 2 skipped.
- `pixi run -e local-recipes due-for-verification-check`: rc=0; 2 real fleet entries show a live
  `skip_reason: no-churn` decision in their message text.
- `ruff check` on both changed source files: 1 new finding (a `re.M` alias on the new regex,
  matching the file's existing convention -- 6 identical pre-existing findings elsewhere in the
  same file, confirmed via `git stash` diff before/after); not a regression.

**Residual risk.** Low. The two deferred findings are both bounded: the missing memoization is a
future cost concern with no current measured impact, and the single-branch git-history scope is
an ambient, repo-wide pattern this story inherits rather than introduces, whose worst case is a
one-run-early cost optimization that self-corrects (this feature makes zero ledger mutations and
never gates -- status stays WARN always, unchanged from 11.1).

**Recovery addendum (dev-2, same day).** This run's orchestrator rejected the dev-1 attempt above
after it had already completed cleanly -- a known bug (task.baseline_commit drift mid-session; see
project memory `the-stuck-orchestrator-baseline-bug`) recorded the rejection as "spec baseline
415595ef93c6 does not match orchestrator-recorded baseline 51262819e76b" and rolled the worktree
back to that baseline, preserving dev-1's 3 commits to `attempt-preserve/20260815-115702-0501-
34fcec5c`. That branch's merge-base with the rolled-back HEAD was exactly the rolled-back HEAD
itself (a clean fast-forward, no real conflict), so dev-2 recovered losslessly via `git merge
--ff-only` instead of re-implementing -- per this repo's standing non-destructive-recovery policy
-- rather than starting a fresh spec. Post-recovery, `spec_surface_reconcile.py` (one of this
run's own verify commands, not part of dev-1's own Verification list) found real drift: 11.2's
own commit (`34fcec5c6d`) changed `chain.py` + its test file (doctor-governed) and `pixi.toml`
(steward-governed) without their owning specs' `.memlog.md` naming them. Reconciled both memlogs
following the exact precedent Story 11.1 itself established for the same gate, re-stamped the
baseline scoped to just those 2 spec keys (0 added/removed, verified by diffing the JSON key sets
before/after), and committed (`7c2969a2e0`). Re-ran the full verify suite post-recovery: `pytest
test_sources_chain_due_for_verification.py` 33 passed, `pyforge-doctor-test` 966 passed/2 skipped,
`spec_surface_reconcile.py` rc=0 -- all unchanged from dev-1's own results, confirming the
recovery introduced no regression. No re-review was run: the recovered diff is byte-identical to
what dev-1's own review pass (documented above) already adversarially reviewed and verified green;
only the mechanical spec-surface bookkeeping was net-new in this session.
