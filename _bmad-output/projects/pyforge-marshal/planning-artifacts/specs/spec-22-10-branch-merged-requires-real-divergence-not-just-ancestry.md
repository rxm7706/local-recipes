---
title: '`branch_merged` requires real divergence, not just ancestry'
type: bug
created: '2026-08-28'
status: done
updated: '2026-08-28'
baseline_revision: 70c859217fdba38c1f9e2c9fd42fc4de5aa1b2e9
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-2-completion-is-judged-from-git-and-process-facts-and-a-zombie-is-never-redispatched.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-9-a-dispatch-branch-names-its-station.md
warnings: []
deferred:
  - summary: >-
      A dispatch branch silently rebased onto main's advancing tip with zero real new
      commits would trivially re-trigger `branch_merged: true` post-divergence-check
      (ancestry would say yes, and `current_head_sha` would differ from the ORIGINAL
      `baseline_head_sha` purely from the rebase, not from real work).
    evidence: |-
      Review-pass finding (Blind Hunter layer): confirmed no code path in
      `pyforge-marshal/src/` auto-rebases a dispatch worktree branch onto main outside of
      an actual landing operation (grepped for `rebase` repo-wide) -- not reachable in
      practice today, a defensive concern rather than a live bug.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
    severity: low
  - summary: >-
      The fix prevents FUTURE false positives; it does not repair the dispatch runs whose
      journal already carries the poisoned `completed` verdict from before this fix
      landed.
    evidence: |-
      Review-pass finding (Verification Gap layer): independently grepped all 26
      `journal.jsonl` files under `dispatch-runs/` and found 20 already carrying
      `branch_merged: true` at zero divergence, timestamped 0.3-1.4s after their
      `dispatch-supervisor-attach` entry -- confirms the bug was near-universal across
      observed runs, not an edge case, but those journals stay poisoned. Not a gap
      against this story's own Acceptance Criteria (nothing here claims retroactive
      repair) -- any already-affected, still-relevant run needs the same manual
      "own-agent continuation" recovery used three times live this session, not
      something this fix can retroactively correct.
    location: >-
      _bmad-output/projects/*/implementation-artifacts/dispatch-runs/*/journal.jsonl
    severity: low
---

<intent-contract>

## Intent

**Problem:** `gather_dispatch_git_facts` (`dispatch_supervisor/__main__.py`) computes
`branch_merged` from `vcs.is_branch_merged(repo_root, branch, into="main")`, which shells
`git merge-base --is-ancestor branch main`. That check is trivially TRUE the instant a
dispatch branch is forked from `main`'s own current tip — a fresh branch's tip literally
IS on `main` already, before any commit exists on it. Confirmed live 2026-08-28 on three
real dispatches in one fleet-drain session (mason 12.7, atlas 20.5, mason 12.8): every one
journaled a `dispatch-completion` `verdict: "completed"` (`branch_merged: true`) within
~2 seconds of launch, `changed_paths: []`, `current_head_sha == baseline_head_sha`.
`resolve_dispatch_session_verdict` (`cli/dispatch.py`) then trusts any journaled
`COMPLETED`/`FAILED` verdict forever without re-deriving it from live facts — so this false
positive poisons the run's journal for its entire lifetime: `marshal factory
dispatch-resume`/`dispatch-attach` refuse with `MRS-DISP-023` regardless of whether the
dispatched session is genuinely still alive and working. All three occurrences this
session were recovered by hand (manual "own-agent continuation" landing) rather than
through the tooling.

**Approach:** Gate the ancestry answer on real divergence: `branch_merged` is only `true`
when `is_branch_merged` says yes AND the branch's `current_head_sha` differs from its own
launch `baseline_head_sha`. The `is_branch_merged` question is still always asked when a
branch resolves (existing branch-derivation tests depend on the ask itself, per Story 22.9's
own `test_every_branch_consumer_agrees_on_the_one_derivation`) — only the trust in a "yes"
answer changes. This is a divergence guard on an existing fact, not a new completion signal,
not a change to CAP-2's `story_merged_on_main` path (which independently confirms landing via
commit-subject scanning on `main` and is unaffected by this bug or this fix), and not a
change to `vcs.is_branch_merged`'s own general-purpose ancestry/patch-equivalence semantics
(used elsewhere for branch retirement and landing checks, where the vacuous-true-at-zero-
divergence case does not arise the same way).

## Acceptance Criteria

- **Given** a dispatch branch that has not diverged from its own launch `baseline_head_sha`
  **When** the completion supervisor gathers git facts **Then** `branch_merged` reads
  `false` regardless of what `is_branch_merged`'s ancestry check answers.
- **Given** a dispatch branch that HAS diverged (real commits past baseline) and is
  genuinely merged **When** the same check runs **Then** `branch_merged` reads `true`
  exactly as before this fix (no regression to the legitimate detection path).
- **Given** the existing test suite **Then** it remains green — this is a divergence guard,
  not a rewrite of any other consumer of `is_branch_merged` or `gather_dispatch_git_facts`.

## Boundaries & Constraints

**Always:**
- Fix scoped to `gather_dispatch_git_facts` in `dispatch_supervisor/__main__.py` only —
  `vcs.is_branch_merged`'s own implementation (`adapters/vcs_git.py`) is correct for its
  general-purpose contract ("is this branch's content already captured on `into`") and is
  used correctly elsewhere (branch retirement, landing checks); this story does not touch it.
- The `is_branch_merged` call itself still always executes when `resolution.resolved is not
  None` — existing tests (`test_every_branch_consumer_agrees_on_the_one_derivation`) assert
  the ask happens; this story changes what is trusted from the answer, not whether it is
  asked.
- Add regression tests pinning both the false-positive-fixed case and the genuine-merge
  case, so the bug cannot silently regress.

**Never:**
- Never touch `vcs.is_branch_merged`'s own ancestry/patch-equivalence logic.
- Never change `story_merged_on_main`'s independent commit-subject-scanning path.
- Never weaken the existing "never ask git about a branch the resolver did not resolve"
  rule (Story 22.9) — this fix is additive to that, not a replacement.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh dispatch, zero divergence | `current_head_sha == baseline_head_sha`, ancestry says yes | `branch_merged: false` | — |
| Real work landed, branch diverged + merged | `current_head_sha != baseline_head_sha`, ancestry says yes | `branch_merged: true` | — |
| Real work in progress, not yet merged | diverged, ancestry says no | `branch_merged: false` (unchanged path) | — |
| No branch resolved | `resolution.resolved is None` | `branch_merged: false`, `is_branch_merged` never asked (unchanged, Story 22.9) | — |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py:196-253`
  — `gather_dispatch_git_facts`, the one site computing `branch_merged`; `current_head_sha`
  is already computed at the top of this function (line 206), so the divergence check needs
  no new git call.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_completion.py` —
  read-only; `judge_dispatch_completion`/`has_git_progress`/`zombie_redispatch_evidence`
  consume `DispatchGitFacts.branch_merged` as-is, no change needed there — the fix is
  entirely in how the fact itself is derived.
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py:408-450`
  (`resolve_dispatch_session_verdict`) — read-only; the journal short-circuit this bug
  exploited is unchanged (a correct verdict written once is still trusted after that,
  by design — the fix is upstream of this, in never writing the WRONG verdict in the
  first place).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` — `AlwaysMergedVcs`
  (new fixture), `test_branch_merged_ignores_ancestry_when_the_branch_has_not_diverged`,
  `test_branch_merged_trusts_ancestry_once_the_branch_has_diverged` (new regression tests).

## Implementation record — 2026-08-28

**Shape as built.** `gather_dispatch_git_facts` already computes `current_head_sha` at its
top (`vcs.worktree_head_sha(worktree)`) before deriving `branch_merged` further down. The
fix renames the `is_branch_merged(...)` call's result to `raw_branch_merged` and ANDs it
with `current_head_sha != baseline_head_sha` to produce the `branch_merged` fact
`DispatchGitFacts` actually carries. The `is_branch_merged` call itself is unconditional
whenever `resolution.resolved is not None` — unchanged from before this story, and still
exercised by Story 22.9's own `test_every_branch_consumer_agrees_on_the_one_derivation`.
No other function signature, caller, or consumer of `DispatchGitFacts` changed.

**Two new regression tests**, both using a new `AlwaysMergedVcs(RecordingVcs)` fixture
whose `is_branch_merged` always answers `True` (mirroring the real ancestry check's
vacuous-true answer at zero divergence) and whose `worktree_head_sha` is settable per test:
`test_branch_merged_ignores_ancestry_when_the_branch_has_not_diverged` (head_sha equals
baseline — asserts `branch_merged is False` while confirming the ancestry question was
still asked) and `test_branch_merged_trusts_ancestry_once_the_branch_has_diverged`
(head_sha differs from baseline — asserts `branch_merged is True`, pinning the legitimate
path this fix must not break).

**Verification** (after the review-pass, both layers run in parallel against the diff):
`pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → **6510 passed / 1 failed /
12 deselected** — the one failure, `test_context_files_not_hand_edited`
(`tests/meta/test_skf_domain_skill.py`), asserts on `CLAUDE.md`/`AGENTS.md` SKF markers,
neither touched by this diff, and independently re-confirmed pre-existing/unrelated by
both this story's own initial run and the review pass's own independent re-run. Targeted
run of `test_dispatch.py` plus the sibling `test_dispatch_completion.py` /
`test_dispatch_landing.py` / `test_dispatch_fleet.py` / `test_dispatch_station_guard.py`
suites: 75/75 pass, no collateral breakage. `is_branch_merged`'s other two call sites
(`cli/retire.py:383`, `cli/init.py:2349`) confirmed untouched — this fix is entirely local
to `gather_dispatch_git_facts`'s handling of the result, never to
`vcs.is_branch_merged`'s own implementation.

**Root-cause evidence, independently re-derived** (not just the story-teller's account):
grepped all 26 `journal.jsonl` files under `dispatch-runs/` across every project and found
20 already carrying `"branch_merged": true` with `current_head_sha == baseline_head_sha`
and empty/near-empty `changed_paths`, timestamped 0.3-1.4s after their own
`dispatch-supervisor-attach` entry — confirming the bug was near-universal across observed
dispatch runs this session, not the edge case the initial "confirmed 3x" framing
understated.

## Review Triage Log

### 2026-08-28 — Review pass

Two review layers run in parallel: a Blind Hunter / Edge Case Hunter pass (correctness,
blast radius, interaction with `has_git_progress`/`judge_dispatch_completion`, test
quality) and a Verification Gap pass (independently re-deriving every claim rather than
trusting the story-teller's account — journal evidence, the full test suite, CAP-9's own
success text against the real diff).

- intent_gap: 0
- bad_spec: 0
- patch: 1 (high 0, medium 1, low 0)
- defer: 2 (high 0, medium 0, low 2)
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` `SPEC.md`'s decomposition table marked CAP-9/Story 22.10 `done`
    while the ledger read `backlog` and this spec's own frontmatter read `in-review` —
    three artifacts, three different completion states for the same story, in the same
    uncommitted change. Exactly the ledger-false-done failure pattern this fleet has been
    burned by before (unverified self-reports). Fixed: `SPEC.md`'s row corrected to
    `in-review` until the dispatcher's own landing actually flips all three together.
  - `[low]` `[defer]` A dispatch branch silently rebased onto main's advancing tip with
    zero real new commits would trivially re-trigger `branch_merged: true`
    post-divergence-check. Confirmed not reachable today (no code path auto-rebases a
    dispatch worktree branch outside an actual landing) — recorded in frontmatter
    `deferred`, not defensively coded against a path that does not exist.
  - `[low]` `[defer]` The fix prevents future false positives; it does not repair the ~20
    dispatch runs whose journal already carries the poisoned verdict from before this fix
    landed. Not a gap against this story's own AC (no retroactive-repair claim made) —
    recorded in frontmatter `deferred` for visibility.
- Independently reconfirmed, no discrepancy found: the root-cause mechanism (re-derived
  from 26 real `journal.jsonl` files, not just this spec's own narrative — found 20
  affected, not just the 3 this session hand-recovered), the full test suite's real
  pass/fail counts (6510 passed / 1 failed / 12 deselected, the 1 pre-existing and
  unrelated), and CAP-9's own intent/success text against the actual diff (no gap between
  what was promised and what shipped).

## Auto Run Result

Status: done

**Summary:** `gather_dispatch_git_facts` (`dispatch_supervisor/__main__.py`) no longer
trusts `is_branch_merged`'s ancestry answer as completion evidence unless the dispatch
branch has genuinely diverged from its own launch `baseline_head_sha`. This closes a
false-positive that (independently confirmed via `journal.jsonl`, not just this story's
own account) affected 20 of 26 real dispatch runs this session: `git merge-base
--is-ancestor branch main` is trivially true for a branch that has not diverged at all,
so the completion supervisor journaled `completed` verdicts within ~1.4 seconds of every
dispatch launch, before any work happened — and because `resolve_dispatch_session_verdict`
trusts any journaled `COMPLETED`/`FAILED` verdict forever without re-deriving it,
`dispatch-resume`/`dispatch-attach` could never recover supervision for a run's entire
lifetime, regardless of whether the dispatched session was genuinely still alive. Two
review layers ran in parallel against the diff: no correctness or blast-radius defects
found (the fix is entirely local to `gather_dispatch_git_facts`; `vcs.is_branch_merged`'s
own implementation and its other two callers are untouched), one process finding fixed
(a premature `done` claim in `SPEC.md`'s decomposition table, corrected before this
story's own status genuinely reaches `done`), and two low-severity items honestly
deferred rather than speculatively coded against.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py`
  — the fix: `branch_merged` gated on real divergence.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py` — two new regression
  tests + the `AlwaysMergedVcs` fixture.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md`
  — new CAP-9, decomposition-record row.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md` — new Story 22.10.
- This spec file (new).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` —
  ledger key added (dispatcher finalize, flipped to `done` alongside this file's own
  `status` field once landing actually happens — not before, per this pass's own review
  finding).

**Review findings breakdown:** 2 review layers run in parallel. 1 `patch` (medium) — a
premature `done` claim in `SPEC.md`'s decomposition table, corrected. 2 `defer` (both
low) — a theoretical, currently-unreachable rebase edge case, and the fix's honestly-
scoped non-repair of already-poisoned journals. 0 `reject` — every finding either landed
as a fix or an honest deferral; nothing was raised and dismissed as noise this pass.

**Follow-up review recommendation:** `true`. Score from this pass's `patch` findings only:
1 medium → `3*0 + 1*1 = 1` (< 5), below the numeric threshold on its own — but this fix
touches a completion-judging seam every future dispatch depends on, and the true blast
radius (20 of 26 real runs affected before this fix) argues for a second look once this
lands and a few more real dispatches have run against it, rather than closing the loop
purely on the score.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 6510 passed, 1 failed
  (pre-existing/unrelated `test_context_files_not_hand_edited`), 12 deselected. Re-run
  independently by the Verification Gap review layer with identical results.
- Targeted `test_dispatch.py` + sibling dispatch-suite files — 75/75 pass.
- `is_branch_merged`'s other two call sites (`cli/retire.py`, `cli/init.py`) confirmed
  untouched by this diff.
- `python3 -c "import yaml; yaml.safe_load(open('.../campaign-state.yaml'))"`-style parse
  checks not applicable here (no YAML campaign state in this story's surface); `yaml.safe_load`
  on this spec's own frontmatter and `sprint-status-ledger.yaml` confirmed clean.
- Journal evidence independently re-derived from the real `journal.jsonl` files on disk
  (20 of 26 affected), not asserted from narrative alone.

**Residual risks:** The two deferred items above (a theoretical, unreachable rebase edge
case; the already-poisoned journals this fix does not retroactively repair) are both
low-severity and explicitly out of this story's own Acceptance Criteria. No functional or
correctness risk identified in either review layer. Landing (git commit beyond this
session's working tree, the ledger flip for key
`22-10-branch-merged-requires-real-divergence-not-just-ancestry`, and the `maintenance` PR
label — this touches `src/` and `_bmad-output/`, never `recipes/**`) is the dispatcher's,
matching every other story landed this session.
