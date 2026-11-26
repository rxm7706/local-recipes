---
title: 'pyforge-steward — Retrospective (2026-11-26: Epics 109 and 117 to 146, from the CAP-175 Wave 3 to plugin registration names)'
project: pyforge-steward
created: '2026-11-26'
updated: '2026-11-26'
date: '2026-11-26'
epics: [109, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146]
verdict: rejected
criteria: declared
headless: true
scope: 'Every steward story that landed on origin/main after the 2026-10-27 retrospective (the CAP-175 Wave 3 merge b306864227 through Merge pyforge-steward/144-1, 3556bd1f2e), plus Epic 146 (Story 146.1, commit 5ae0f4334f) on branch plugin-names-2026-11-26, not yet on main. Story 146.1 renamed the six deploy-profile entry points in the package pyproject.toml on 2026-11-26, so the code stage moved past the 2026-10-27 retro (the feeds code->retro edge); this is the retrospective that follows it. Stray stories of older epics that landed in the window (21.6, 99.9) are read with their group.'
evidence:
  - 'range 7909b1857a..HEAD (HEAD 24af8d0a90 on plugin-names-2026-11-26): git_evidence.py reports 571 commits, 72 merges, 66 merges measured; steward package files: 379 touched, +55893 -8529 across non-merge commits; steward src/: 63 files, +7387 -1487'
  - 'sprint_status.py detect-epic --epic 109..146 on implementation-artifacts/sprint-status.yaml (2026-11-26): pending_stories only in Epics 109 (109.4, 109.5), 114 (114.9), 117 (117.9), 118 (118.3), 121 (121.5); every other epic in scope reads all done; the tracked sprint-status-ledger.yaml agrees row for row'
  - 'pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_profile_plugins.py -q: exit 0, 26 passed (Story 146.1 AC2, 2026-11-26)'
  - 'pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/meta/test_plugin_registration_conformance.py -q -m live_tree: exit 0, 15 passed (Story 146.1 AC1, 2026-11-26)'
  - 'pixi run --frozen -e pyforge-guild python scripts/chain_currency_sweep_check.py --project pyforge-steward --json before this file: exit 1, one finding, staleBy feeds code (2026-11-26) than retro (2026-10-27)'
---

# pyforge-steward — Retrospective, Epics 109 and 117 to 146 (2026-11-26)

## Epic summary

- **Range.** `7909b1857a..HEAD`: the commit that carried the 2026-10-27 retro and the Wave 3 chain, through Story
  146.1's two commits on this branch (`5ae0f4334f`, `24af8d0a90`). The range is repository-wide (571 commits); this
  retro reads the steward package, `.claude/hooks/pre-shell.py`, the steward planning artifacts and the Specs steward
  co-governs. Steward merges on main in the window: 27 `Merge pyforge-steward/<key> into main` subjects (from
  `b306864227` 117-10, 2026-10-27, to `3556bd1f2e` 144-1, 2026-11-26), plus the integrator branches that carried
  steward stories under another subject (`#2371` cutover readiness, `close-review-stories-2026-11-25`,
  `close-defect-stories-2026-11-25`, `cap-184-shipped-2026-11-25`).
- **Epics, by group** (headings `epics.md` lines 7189 to 9762):
  - *CI and preflight budget, CAP-175 / CAP-159:* 117 (Wave 3: 117.6, 117.8, 117.10 to 117.12 in `69a64505b7`; 117.5
    `d5b4c833b1`; 117.13 `9f9bc6ed50`), 125, 126, 128, 129 (the macOS host), 131 (Playwright from pixi), 145 (a suite
    runs whole when its gate only judges reports).
  - *Marketplace, CAP-168 to CAP-173:* 109 (109.1, 109.3, 109.6 to 109.8), 130.
  - *NKP hosting, CAP-176 to CAP-178:* 118 (118.1, 118.2, 118.4 to 118.8).
  - *Start tools and shared floor, unifying-strategy CAP-18, CAP-20, CAP-21, CAP-4:* 119 (with 21.6), 141, 143, 146.
  - *Cutover readiness (PR #2371, merged by main `dca04bd9e9` per the 2026-11-13 session-close team memory; build commits `b78da81aba` to `d3a131a7da`):* 120 to
    124.
  - *Corridor on the platform database, CAP-139/141/143:* 127.
  - *Review and blocker close-out:* 132 to 134, 136, 138.
  - *Onboarding verb, CAP-183:* 135. *Exit-code declaration, CAP-184:* 137, 142. *One JSON spelling, CAP-185:* 144.
  - *Session hook, CAP-5:* 139, 140 (and 134.2).
- **Stories not `done`** (`detect-epic`, Evidence): 109.4 (backlog, Deps 109.5's desk-test note), 109.5 (in-progress,
  waits on the Round 0 desk test and the Wizard-of-Oz pilot), 117.9 (backlog, the slowest-test shedding split out of
  117.1 at build), 118.3 (backlog, needs operator-owned `GITOPS_DEPLOY_KEY`, `HETZNER_TOKEN` and DNS), 121.5
  (`blocked` on the operator's ruling on the host after Launch; `epics.md` line 8511 says an agent never flips it).
  114.9 (retire the retrofit kill switches on their cleanup date) is pending too, but no Epic 114 story landed in the
  window, so Epic 114 is out of scope.
- **Evidence inventory.** Available: `epics.md`, 109 story specs under `planning-artifacts/specs/spec-1{09,17..46}-*`,
  the tracked ledger and the Tier-3 feed, the commits, `deferred-work-ledger.md`, the team-memory trap entries of
  2026-11-24 to 2026-11-26 (`.claude/memory/feedback/traps-met-*.md`), the two acceptance tests run today. Missing:
  build-session logs (not kept in the tree), so process lessons come from commit subjects, story-spec review sections
  and team memory. No `bmad-review` pass over the full range (see Assumptions).

## Findings

Each finding: source, then disposition for this instance and what prevents the next.

### Spec-to-implementation reconciliation

1. **Two built capabilities still read `ready`.** Source: `spec-pyforge-steward/SPEC.md` line 1075 (CAP-183, `(ready
   2026-11-25 …)`; Epic 135, all three stories `done` in the ledger) and line 1127 (CAP-185, `(ready 2026-11-26 …)`;
   Story 144.1 merged `3556bd1f2e`). CAP-184, landed the same day, was flipped to `(shipped 2026-11-25)` by
   `cap-184-shipped-2026-11-25` (line 1108). *Instance:* defer to a memlog status-marker entry and anchored render
   (this retro writes no Spec). *Prevention:* the closing story of a single-story capability carries its marker flip,
   as the CAP-184 branch did.
2. **Story 146.1 amended a shared Spec and found unnamed paths on six others.** Source: `spec-146-1-…` § Review,
   findings 1 to 3: mason CAP-37 named the old entry points; three station tests pinned the old names; the memlogs
   of doctor, marshal, warden, core and unifying-strategy lacked reconcile entries for paths the 2026-11-25 exit
   declaration and the 2026-11-26 JSON change moved. *Instance:* fixed in `5ae0f4334f` (the commit body names the
   reconcile entries). *Prevention:* see finding 9.
3. **The registry never selects by entry-point name, so the rename moves no operator value.** Source: `spec-146-1-…`
   § Review intro (`PluginRegistry.load_entry_points` uses the name only in error labels; steward selects by
   `plugin_id`); `git diff` of `pyforge-steward/pyproject.toml` (six `steward-deploy-<id>` names); AC1 and AC2 pass
   today (Evidence). *Instance:* accept.

### Process (story boundaries and review)

4. **Story 109.3 took eight review loops.** Source: commits `d2702f1f8f` (loop 2) through `ada33b46ee` (loop 8,
   2026-10-29); `8d47df4f50` gave loop 7 a "narrowed review contract" after loops 4 to 6 each failed 109.3 again.
   *Instance:* closed (`a7c42a06d9`, 109-1, and `cb601ac369`, 109-3). *Prevention:* when a story fails the same
   review twice, narrow the review contract to the story's acceptance criteria then, not after the sixth loop.
5. **The session hook needed three stories to read every form of a command.** Source: Story 134.2 (resolution text,
   `deferred-work-ledger.md` line 7434: wrappers, `git -c/-C`, `gh api` methods), Epic 139 (`epics.md` line 9578:
   `$(...)`, backticks and process substitution were never read), Epic 140 (line 9602: a redirection after `git push`
   read as the remote; the operator applied the push half of `DW-steward-134-2-1`'s patch and an independent review
   re-tightened six forms the patch loosened). *Instance:* fixed; `session_denials` unchanged throughout.
   *Prevention:* none beyond the tests; each epic added cases to `tests/scripts/test_pre_shell_hook.py` and kept every
   existing case's result.
6. **A landed story's ledger key was promoted after the merge.** Source: `d5b4c833b1` (Merge 117-5, 2026-10-31)
   followed by `c969fca867` and `68483c11fc` (promote 117.5 to done). *Instance:* fixed. *Prevention:* the AGENTS.md
   pitfall already says promote before landing; no new guard.
7. **Integrator branches carried steward stories under non-story merge subjects.** Source: `3551065c0c`
   (`close-review-stories-2026-11-25`), `21087f55c9` (`close-defect-stories-2026-11-25`), `560877e19e`
   (`cap-184-shipped-2026-11-25`), and the cutover-readiness PR built as `build(steward): <key> (BUILD-n)` commits.
   *Instance:* accept; every key reads `done` in both ledgers. *Prevention:* landing evidence for those keys rests on
   `git merge-base --is-ancestor`, not the subject (AGENTS.md § Known pitfalls).

### Recurring traps (team memory, 2026-11-24 to 2026-11-26)

8. **docs-currency goes red after the commit, not before.** Source: `traps-met-extending-one-declaration-…` (1),
   `traps-met-closing-eleven-defect-stories-…` (5), `traps-met-landing-a-documentation-fix-…` (5); `24af8d0a90`
   re-read and stamped the sync-templates page after steward's `pyproject.toml` moved. Four of five entries name it.
   *Instance:* handled each time. *Prevention:* action item 3.
9. **Co-governed paths need a reconcile on every governing Spec.** Source: `traps-met-extending-one-declaration-…`
   (7), `traps-met-closing-eleven-defect-stories-…` (6), finding 2. *Instance:* handled. *Prevention:* the 2026-10-27
   carry-forward (name each path in full) holds; the remaining gap is finding the co-governors before the stamp.
10. **A new story or test module has registries to join.** Source: Story Coverage Matrix
    (`bmad_tea_playwright.py`; three entries), `oracle-map.md` for a new steward test module
    (`traps-met-extending-one-declaration-…` (2)), the capability-ledger row for a new CAP
    (`traps-met-minting-one-herald-capability-…` (1)), `contract.md` for a new env var
    (`traps-met-landing-a-documentation-fix-…` (3)). *Instance:* handled. *Prevention:* action item 4.

### Aggregate views

11. **Runtime growth sits in four new or rewritten modules.** Source: `git_evidence.py` `files`, steward `src/`:
    `marketplace_pages.py` +2361 −539 (Epic 109/130), `machine.py` +1339 −14 (CAP-183, Epic 135),
    `deploy_nic_packs.py` +681 −40 and `deploy_nic.py` +377 −15 (Epic 118), `cutover_ledger.py` +668 and
    `cutover_ledger_check.py` +572 (Epic 121); `cutover.py` shrank (+172 −226, 121.2 "no longer copies trees").
    *Instance:* accept. *Prevention:* none; each is the module its epic named.
12. **Test churn dominates.** Source: steward package +55893 −8529 over 379 files against `src/` +7387 −1487 over
    63. *Instance:* accept (the live-tree splits, the macOS work and the contract meta-tests); not reviewed hunk by hunk.

## Behavior verification

- Story 146.1 AC1, `test_plugin_registration_conformance.py -m live_tree` in `pyforge-core`: exit 0, 15 passed.
- Story 146.1 AC2, `test_deploy_profile_plugins.py` in `pyforge-steward`: exit 0, 26 passed.
- Not exercised by this retro: the full steward suite halves, the preflight, the NKP bring-up (attended, operator
  hardware), the marketplace pages build, `steward init` on a bare machine, the session hook's cases. Their evidence
  is each story's own verification and the merges' CI; this run did not re-run them.

## Previous-retro follow-through

The 2026-10-27 retro left four carry-forward lines, not sprint-status action items (the feed has none to move).

| Carry-forward | Evidence | Reading |
|---|---|---|
| Name every drifted path in full in a surface-reconcile memlog event | `5ae0f4334f` body and `spec-146-1-…` § Review 3 name paths on six Specs; the 2026-11-25 trap entries still meet unnamed co-governor paths | held, gap moved to co-governors |
| Inject core counts; never read the machine in an expectation | `grep -rn 'os.cpu_count()' pyforge-steward/tests` prints nothing (2026-11-26) | held |
| Count a new flag's tables before pushing | Story 124.4 (`…kill-switch-joins-the-flag-tree-and-every-shipped-flag-table`, done) | landed |
| Measure the wall per PR head from the Actions API | `684c7ea2c1` "the five specs record the PR head's seconds" (Wave 3) | landed |

Headless: no `--set-action-status` transitions proposed (none exist to move).

## Strategy convergence

Steward stayed the estate the factory stands on, and the unifying strategy's shared-floor capabilities moved through
it: CAP-20's seven start tools do their work from one closed table (Epic 119), CAP-21 makes broker TLS a capability
(Epic 141), CAP-4's MCP placement is one rule held by a test (143.2), and CAP-18's registration shape now says whose
each plugin is and refuses a repeated name (Epic 146, with marshal 125.1 and mason 45.1 on their own chains). The
cutover contract (Epics 120 to 121) is generated and writer-locked; 121.5 waits on the operator, and the estate has
not moved (AGENTS.md, `pyforge.cutover_root`). CAP-184 and CAP-185 put one exit-code declaration and one JSON spelling
across every station, each station keeping its story in its own `epics.md`. No steward capability drifted from the
strategy Spec; the drift found is markers (finding 1) and unnamed paths (finding 2).

## Action items

All proposed; this retro applies none.

| # | Action | Owner | Kind |
|---|---|---|---|
| 1 | Flip CAP-183 and CAP-185 to `(shipped <date>)` by a memlog status-marker entry and an anchored render (finding 1). | steward (next Spec story) | spec reconciliation |
| 2 | Narrow a review contract to the story's acceptance criteria after a second failed loop on the same story (finding 4). | steward (story authors, review driver) | process lesson |
| 3 | After committing a source file, re-read every page that lists it, bump `verified:`, commit, and re-run docs-currency until it is stable (finding 8). | every story author | process lesson |
| 4 | Before the first full preflight on a new story or CAP: Story Coverage Matrix, `oracle-map.md` row, capability-ledger row, `contract.md` row (finding 10). | every story author | process lesson |
| 5 | Keep 109.4, 109.5, 117.9, 118.3 and 121.5 on their recorded blockers; none is an agent's to unblock (118.3 and 121.5 are operator-owned). | operator | carried |

## Acceptance verdict

**Machine verdict: rejected** (headless, criteria declared in each epic's stories). Forced by the rubric:
`pending_stories` is non-empty for Epics 109, 117, 118 and 121 (Epic summary). The other 27 epics in scope read all
`done` in the feed and the ledger, and the two acceptance commands run today pass. On the evidence alone those 27
would read **accepted-with-open-items** (finding 1's markers). No human decision was available to override.

## Open questions

- Should 117.9 stay open now that Epic 145 runs a suite whole and Wave 3 shards the station jobs, or is its payoff
  spent? The evidence here does not measure the steward suite's wall after Wave 3.

## Assumptions

- Epics were taken from the invocation (steward epics landed since the 2026-10-27 retro, plus Epic 146 at HEAD), not
  auto-detected; `detect-epic --epic <n>` ran for 109 to 146 and its `pending_stories` are listed in Epic summary.
- The verdict is a single machine value over the set; it is **rejected** because four epics carry unfinished stories.
- The EGM drift stage (activation append step) does not apply: it is gated to `pyforge-marshal` epics.
- `bmad-review` was not invoked over the 571-commit range: each story carried its own review (story-spec § Review
  sections; the 109.3 loops), and a full re-review is outside a write-one-file retro. Findings 4 to 7 are the inline
  story-boundary read.
- Phase 5's `sprint_status.py update` was not run: this run writes no ledger or feed, so every
  `epic-<n>-retrospective` key stays `optional` and the action items live here only.
- The document lives at `planning-artifacts/retros/retro-pyforge-steward-2026-11-26.md`, the station's tracked retro
  home that the chain-currency sweep reads, not the skill's default Tier-3 path.
