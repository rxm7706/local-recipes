---
doc_type: retrospective
project: pyforge-atlas
epic: 10
wave: I
title: Wave I — Post-Audit Truth-Up (Round-3 Findings)
stories: 6
date: 2026-08-02
basis: reconstructed from tracked evidence (epics.md, deferred-work-ledger.md
  DW-I4-1/DW-I5-1/DW-AD23-1..3, squash-merge PR #132 `55ce2f4bae`, source-branch
  commits on `fix/atlas-post-audit-epic-10`, abandoned PR #131, CFE Rule-2 retro
  `e8d5cc40e1`)
---

# Epic 10 · Wave I — Post-Audit Truth-Up (Round-3 Findings)

**Scope:** I0 dependency-completeness unblock, AUD-ATLAS-010/013 (10.1) · I1/I2 Spec
kernel + story-spec frontmatter truth-up, AUD-ATLAS-041/045/046/047/048/049 (10.2/10.3)
· I3 NULL-identity fix under pandas 3.0, AUD-ATLAS-011 (10.4, `f0b7958c62`/`90c2792843`,
bmad-loop run `20260728-190006-ce13`) · I4 build-provenance stamping (AD-17), reverted
once on its original contract and re-driven on a corrected one, AUD-ATLAS-043/044
(10.5, `771e151a1a`/`008edb036b`, run `20260728-201438-15bd`) · I5 real cross-process
run admission (AD-23) (10.6, `cc17b96aba`, run `20260729-112237-3139`). All six
squash-merged to `main` as PR #132 (`55ce2f4bae`, merged 2026-07-29) from the
`fix/atlas-post-audit-epic-10` branch, closing the atlas-owned subset of an
independent Round-3 spec-to-code audit whose own remediation branch — PR #131,
opened 2026-07-27 — was closed unmerged on 2026-07-30.

## What worked

- **The loop refused to ship a faithful implementation of a wrong contract.** I4's
  original AC specified `build_stamp` as wall-clock-now at read time — a value that
  can never distinguish fresh data from stale, since every read of month-old data
  reports "now". The dev session implemented it exactly as written (790/790 green),
  its own review pass located the defect in the *contract* rather than the code,
  reverted rather than ship, and escalated. The operator rejected both offered
  workarounds and re-grounded the fix in code that already existed
  (`IncrementalParquetDataset`'s per-row `fetched_at`, already persisted on 15
  catalog entries) rather than inventing a new signal. This is the single strongest
  finding in the epic: a green gate was not treated as sufficient.
- **The two "owed" independent follow-up reviews were actually run to completion,
  as adversarial mutation testing rather than a second read-through** — a
  deliberate compensation for the reviewer no longer being context-free.  I5's pass
  (`fe7d3fbf20`) found a real defect this way: `DW-AD23-3`, the run-admission lock
  store's default location sat *inside* the data tree it guards, so `rm -rf data/`
  — an ordinary operator action — unlinks a live holder's flock inode and lets a
  second writer proceed, a direct violation of the invariant the story had just
  re-promoted. It was fixed the next day as PR #140 (`5e054b617c`).
- **I5's concurrency mechanism was closed as binding ACs (D1-D6) by the operator
  before the dev session started**, grounded in the code's own shape (writes land
  as Parquet under `data/`; every DuckDB connection in the package is argless /
  in-memory) rather than left as an open `q_gate` for the dev session to decide —
  specifically to prevent I4's failure mode (a faithful implementation of an
  unexamined design question) from recurring on the harder story.
- **AD-23 was re-promoted with four explicitly stated boundaries** (single-machine
  only; release is not symmetric across the three planes; a later before-hook
  raising holds locks until process exit; the lock store's default sits inside the
  tree it guards) instead of as a clean, unconditional claim — the direct repair of
  `AUD-ATLAS-046`, the false-safety-claim finding that opened this epic (the Spec,
  architecture spine, epics, and `definitions.py` all asserted run admission that
  the `in_process` executor never provided).
- **I0's restored dependency-completeness gate found real, independently
  verifiable defects on its first run**, not zero: `AUD-ATLAS-050`
  (`boring_semantic_layer` is PyPI-only, no conda-forge candidate — a packaging
  blocker, not a declarable dependency) and `AUD-ATLAS-051` (conda `playwright`
  ships only the CLI, not the Python bindings — later generalized as CFE gotcha
  G107).
- **Deferred-work durability held.** `DW-I4-1` and `DW-I5-1` were promoted out of
  the gitignored Tier-3 ledger into the tracked ledger the same day they were
  created, rather than left for the next accidental loss (SYNTHESIS Action A5,
  applied in real time rather than only in the retro that named it).

## What did not

- **PR #131 never merged.** Opened 2026-07-27, closed unmerged 2026-07-30 — every
  fix its Round-3 audit described was branch-scoped and had to be independently
  re-verified against `main` from scratch rather than simply landed. A later,
  separate commit (`864558e02d`, outside this epic) root-caused why: `.claude/skills`
  sat in `.git/info/exclude`, which hides *new* files from `git status` — so PR
  #131's own path-guard fix imported a module it never actually committed, and a
  fresh checkout of that branch would `ImportError`. Epic 10's decision to treat
  every one of #131's "Status: fixed" lines as unverified rather than trusted was
  the right call, evidenced after the fact.
- **I5 was interrupted by an unplanned shutdown, not a designed checkpoint.** The
  machine went down mid review-1, with the dev pass already complete and six files
  modified-and-uncommitted inside a run worktree that bmad-loop's own cleanup would
  otherwise have destroyed. Recovery required a hand-made WIP commit, a
  `checkpoint/i5-10-6-wip` tag, and a written resume runbook — and the WIP commit
  itself, by the recovery commit's own words, "passed NO gate... preserved, not
  proven."
- **The review adapter hit its weekly usage cap mid-review and stalled at an
  interactive prompt for roughly 2.5 hours** (I4 review-3, Fable). bmad-loop cannot
  distinguish a session blocked on a prompt from one genuinely still working — it
  only notices a session that ends without a result — so status reporting showed
  "review-running" for the entire stall. This corroborates the standing team-memory
  finding on bmad-loop blind spots rather than discovering a new one.
- **Two consecutive stories (I4/10.5, then I5/10.6) both finalized `done` while
  their review pass was still actively recommending a further follow-up**, because
  `max_followup_reviews` — an unchosen upstream default of 1 — was spent, not
  because the reviewer was satisfied. The *repetition* (not the single instance)
  is what turned this into a contract-level question rather than a one-off: the
  cap, not the reviewer, was deciding when a story was done. The fix landed inside
  this same epic's tail (`max_followup_reviews` raised to 2, explicitly chosen and
  recorded; a new `deferred_work_check.py` detector, because the ledger the loop
  force-refiles a spent recommendation to is itself gitignored — and that detector
  immediately found five damped recommendations across three projects, not only
  the two atlas ones that had prompted the question).
- **The review-model escalation (Fable → opus, then sonnet → opus for I5) was a
  manual, mid-epic decision** rather than a documented default going in — chosen
  and written down only after the Fable cap was actually hit.

## Carry-forward

1. **An abandoned remediation branch is not a merge candidate at any later point** —
   its findings must be independently re-verified against current `main`, never
   ported wholesale from a "Status: fixed" line on unmerged code. Epic 10 modeled
   this correctly; keep it as the standing rule for any future "fixed on a branch
   that never merged" record.
2. **A story whose AC bakes in an untested temporal assumption** ("now" as a proxy
   for "fresh") deserves the same up-front grounding-in-code that D1-D6 gave I5's
   concurrency mechanism, applied *before* the dev session starts rather than after
   a faithful implementation reveals the contract was wrong.
3. **`max_followup_reviews` needs a chosen, non-default value in every loop
   policy** — this epic is the direct evidence, and the remedy (cap raised to 2,
   with a leak detector on the gitignored refile target) should be treated as
   already shipped, not re-litigated by a future retro.
4. **bmad-loop still cannot detect a session stalled on an interactive prompt** —
   an unplanned shutdown and a usage-cap prompt both look identical to "still
   running" from outside. This needs an external liveness check; a documentation
   workaround does not close it.
5. **Re-promoting a repaired invariant WITH its stated boundaries** (AD-23's four
   limits) is a better closure pattern than either a bare reinstated claim or a
   full retraction — prefer it for any other "was this really true" audit finding.
