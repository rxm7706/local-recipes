# Signal inventory — what a hand-driven story actually leaves behind

Companion to `SPEC.md` (CAP-1's evidence basis). Every claim verified against live code and
artifacts on 2026-08-21. A capability that requires a signal nobody records is not
implementable; this file is the honest census of what exists.

## Usable signals

### 1. Story-spec frontmatter `baseline_revision` / `final_revision` — the chosen basis

- **Written by:** `bmad-dev-auto` — `step-03-implement.md` L20 captures `baseline_revision`
  (current HEAD, or `NO_VCS`) into the spec frontmatter *before any changes*;
  `step-04-review.md` L126 captures `final_revision` (HEAD *after committing*).
- **Durability:** spec promotion (`pyforge.marshal.cli.deploy::_execute_promotion_plan`,
  shared by `run_promote` and Story 5.9's `run_reconcile_completions`) copies the Tier-3
  file's bytes verbatim into tracked `planning-artifacts/specs/` — frontmatter intact.
  Verified: promoted `spec-11-3-migration-registry-and-runner.md` carries both fields, and
  its `final_revision` (`f749d93…`) is reachable on main via the story's merge commit.
- **Derivable metric:** wall-clock only. `git show -s --format=%ct <rev>` on both revisions.
- **Caveats (all load-bearing):**
  - The baseline commit's timestamp is when the *previous* work was committed, not when this
    story started — `ts(final) − ts(baseline)` overstates by the idle gap before dispatch.
    The alternative bound (first commit in `baseline..final` → final) understates by the
    work done before the first commit. Neither is active agent-compute. (SPEC open
    question 1.)
  - `NO_VCS` sentinel possible in either field → no derivation.
  - Both revisions must resolve in the local repo. The `--merge`-never-`--squash` landing
    policy keeps `final_revision` reachable; a squash or rebase would orphan it → no
    derivation, story stays absent, never a guess.
  - Coverage is `bmad-dev-auto` completions with promoted specs. A plain `bmad-quick-dev`
    session does not write these fields, and a recovered spec
    (`recovery_source: epics-derived-contract-only`, from `deploy recover-spec`) has none —
    both land in CAP-3's "spec without revision fields" caption class.

### 2. PR timestamps (created-at → merged-at)

Available for any PR-landed story (the dispatch ritual lands via PR) and already the metric
behind atlas's *curated* timing (waves 0-H, hand-computed once). Requires network (`gh`) and
merge-subject → story-key mapping. Measures wall-clock *including* review/merge wait —
a third metric class. **Status: stays a curated/manual path** (SPEC constraint "offline
derivation"); not part of the automatic derivation.

### 3. Merge-range commit timestamps

For stories detectable via merge subjects (`core.promotion.merged_story_keys`'s
three-pattern match), the merge commit's parents bound the branch's own commits; first→last
commit timestamps give a span. Subsumed by signal 1 when revision fields exist (same git
data, spec-anchored instead of subject-parsed); only independent value is for merged stories
*without* revision-bearing specs — deliberately not derived (SPEC non-goal: no signal
invention beyond what the story's own contract artifacts carry; subject parsing alone cannot
prove the route or the working span).

## Rejected signals

- **Claude Code session transcripts** (`~/.claude/projects/**/*.jsonl`): per-machine, not
  durable, no story-key structure; proven useful for spec *recovery*, unusable as a
  systematic timing source.
- **bmad-loop journals for hand-driven stories:** do not exist by definition — the whole
  gap. No session-start/session-end events means **active agent-compute is genuinely
  unobtainable retroactively for hand-driven work**; only wall-clock proxies exist. This is
  why CAP-2's fidelity distinction is a hard constraint, not styling.
- **`sprint-status-ledger.yaml` / reconcile-completions output:** proves *that* and *how* a
  story completed (`not-loop-native` label), carries no *when* beyond the ledger commit's
  own timestamp (reconciliation may run days after the work; its commit time measures the
  operator's cadence, not the story's effort).

## Where derivation runs and persists

`scan_timing` runs wherever `generate.py` runs; the journal-derived numbers reach the
public Pages board only because the generated `data.js` is committed. The wall-clock
fallback follows the identical model: derived locally (full git history, tracked spec
archive present), persisted in `data.js`, re-rendered anywhere. CI needs no new capability.
