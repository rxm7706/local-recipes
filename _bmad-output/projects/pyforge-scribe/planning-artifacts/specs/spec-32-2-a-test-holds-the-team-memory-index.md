---
title: '32.2: A test holds the team-memory index'
type: 'chore'
created: '2026-11-10'
status: 'done'
difficulty: 'medium'
story: 32-2-a-test-holds-the-team-memory-index
spec: spec-pyforge-scribe
surface:
  - src/shared/packages/pyforge-scribe/tests/meta/test_team_memory_index.py
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-32-2-a-test-holds-the-team-memory-index.md
  - archive/.claude/memory/project/**
  - .claude/memory/project/**
  - .claude/memory/MEMORY.md
review_loop_iteration: 0
followup_review_recommended: false
context:
  - .claude/memory/README.md
  - .claude/memory/MEMORY.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - docs/dreams/pyforge-unifying-strategy.md
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Nothing tests that `.claude/memory/MEMORY.md` and the record files agree (audit SHOULD S7), and about 45
of its 121 index lines are receipts that later records supersede: 9 CI pause and resume entries (no surface in
`docs/governance/ci-surfaces.yaml` is paused), 18 of the 19 session closes, 16 "story landed in dispatch worktree"
receipts, `operator-inbox-as-of-2026-09-19`, and `2026-09-25-bmad-suite-advance-landed-as-pr-1607` (superseded by the
2026-09-26 merged entry).

**Approach:** A guard test, a manifest, and the prune the operator approved on 2026-11-10 (second addendum, item 7).

- `tests/meta/test_team_memory_index.py` (with `pytestmark = pytest.mark.live_tree`) holds: the link targets of
  `MEMORY.md` equal the record files under `feedback/`, `project/` and `reference/`; every link resolves; every record
  parses with the nested `metadata.type` the code writes (`CaptureRecord.to_frontmatter`); the index stays under 200
  lines. It exits 1 naming the record otherwise, and fixture trees plant an unlinked file, a dangling link, a flat
  `type:` record and a 200-line index.
- The story reads each candidate's body before listing it, and leaves out a record that still carries an open
  operator-owned ask or a rule no later record states (`mason-story-26-1` states a standing rule and is not a
  candidate). The manifest is a table in this spec, under a heading that states its count: record path, reason, the
  record that supersedes it. Two candidates are cited from memlogs (`operator-inbox-as-of-2026-09-19` from the marshal
  and scribe memlogs, a 2026-10-13 session close from herald's) and the manifest says so: memlog history is not
  rewritten when a record moves; `archive/<original path>` keeps the old path readable.
- The manifest's records move with `git mv` to `archive/.claude/memory/project/` (the shape of commit `af2d5799d7`;
  leave to add under `archive/` given by the ruling), and their index lines leave `MEMORY.md`, in one commit.

Ledger key: `32-2-a-test-holds-the-team-memory-index`. Type / Effort / Deps: chore / M / none.

### Living CAP citations

- `spec-pyforge-scribe` CAP-1, as amended at the 2026-11-10 mint (FR-2): the index clause, held by this test. Pruning
  stays as `.claude/memory/README.md` § When to prune says: humans decide, and the record is deleted or archived; the
  operator decided this prune on 2026-11-10, and the form is archive.

## Boundaries & Constraints

**Always:**
- Move with `git mv`; read every candidate's body before listing it.
- `MEMORY.md` writers in this PR, in order: this story, then Story 31.4's closing capture.

**Never:**
- Do not delete a record.
- Do not move a record that is not in the manifest, or one that still carries an open operator-owned ask.
- Do not rewrite a memlog or another dated record to name a moved record's new path.

</intent-contract>

## Acceptance Criteria

- **AC1 — Index and files agree, the schema parses, the size bound holds.**
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_team_memory_index.py -q` exits 0.
- **AC2 — The guard fires on four planted fixture trees** (an unlinked file, a dangling link, a flat `type:` record, a
  200-line index):
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_team_memory_index.py -q -k test_index_guard_names` exits 0 and its summary line reads `4 passed`.
- **AC3 — The manifest is in this spec, one row per record.**
  `grep -c '^| `project/' _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-32-2-a-test-holds-the-team-memory-index.md`
  prints a number from 1 to 45, equal to the count the manifest's heading states.
- **AC4 — The manifest's records moved to the archive, and nothing was deleted.**
  `git diff -M --diff-filter=R --name-status $(git merge-base origin/main HEAD) HEAD -- .claude/memory archive/.claude/memory | grep -c 'archive/.claude/memory/project/'`
  prints the manifest's count, and
  `git diff -M --diff-filter=D --name-only $(git merge-base origin/main HEAD) HEAD -- .claude/memory archive/.claude/memory | wc -l`
  prints 0 (both pathspecs, so a move reads as a rename).
- **AC5 — Lint and types.** `pixi run --frozen -e pyforge-guild lint-types` exits 0.

## Binding

- Parent capability: `spec-pyforge-scribe` CAP-1 (amended 2026-11-10); FR-2.
- Dream: `docs/dreams/pyforge-scribe.md` § Realization log, the 2026-11-10 (cutover readiness) entry.
- Epic: Epic 32. Ledger key `32-2-a-test-holds-the-team-memory-index`, minted `backlog`.
- Deps: none. Wave BUILD-1.

## Notes

- Closes audit SHOULD S7 in full: the guard lands and the operator-approved records move.
- Shared request (steward-station): the scribe live-test trigger paths cover the whole `.claude/memory` tree (today
  `MEMORY.md` and `feedback/` only).
- The prune moves records; it adds none. The closing capture of this PR is Story 31.4's.

## Manifest

Written at build, 2026-11-11, after reading each of the 45 candidates' bodies against the tree, the ledgers, the
deferred-work rows and the records that stay. Each record below moves byte-for-byte from `.claude/memory/project/` to
`archive/.claude/memory/project/` (its blob hash is unchanged, so the commit records a rename) and its line leaves
`MEMORY.md` (147 lines before, 107 after). Nothing is deleted.

Memlog citations: the 2026-10-13 session close below is cited from herald's memlog
(`spec-pyforge-herald/.memlog.md`, the 2026-10-14 direction entry). That memlog is not rewritten; the record stays
readable at `archive/.claude/memory/project/2026-10-13-session-close-main-6b9d33263f-2182-pending-landed.md`.
`operator-inbox-as-of-2026-09-19`, cited from the marshal and scribe memlogs, is left out (see below), so its path is
unchanged.

### 40 records move to the archive

| Record | Reason | Superseded by |
|---|---|---|
| `project/ci-pause-state-as-of-2026-10-12-live-gh-audit-repo-variables.md` | CI pause snapshot: both `PAUSE_*` variables and the six hand-disabled workflows are gone (`ci-surfaces.yaml`: 59 live, 7 opt-in-off, 9 retired, none paused); "no branch protection" is out of date; the waiting-deploy trap is the `pages` row's `stuck_rules` read by `steward ci status` | `project/2026-10-17-kedro-viz-is-back-on-pages-2247-resumed-every-ci.md`; `project/2026-10-17-the-protected-refs-rulesets-are-live-on-rxm7706-l.md` |
| `project/ci-pause-set-pause-ci-canary-for-ci-canary-reason-operator-2.md` | CI pause receipt; the pause was lifted (#2247) | `project/2026-10-17-kedro-viz-is-back-on-pages-2247-resumed-every-ci.md` |
| `project/ci-pause-set-pause-cfe-regression-net-for-cfe-regression-net.md` | CI pause receipt; resumed 2026-10-16 (#2241) | `project/2026-10-17-kedro-viz-is-back-on-pages-2247-resumed-every-ci.md` |
| `project/ci-pause-disabled-test-linux-yml-gh-workflow-disable-the-wor.md` | CI pause receipt; `test-linux.yml` re-enabled (#2247), its registry row reads `live` | `project/2026-10-17-kedro-viz-is-back-on-pages-2247-resumed-every-ci.md` |
| `project/ci-resume-delete-pause-cfe-regression-net-for-cfe-regression.md` | CI resume receipt; no `PAUSE_*` variable remains | `project/2026-10-17-kedro-viz-is-back-on-pages-2247-resumed-every-ci.md` |
| `project/ci-resume-delete-pause-ci-canary-for-ci-canary-registry-upda.md` | CI resume receipt; no `PAUSE_*` variable remains | `project/2026-10-17-kedro-viz-is-back-on-pages-2247-resumed-every-ci.md` |
| `project/ci-resume-delete-pause-container-builds-for-station-tests-gu.md` | CI resume receipt; no `PAUSE_*` variable remains | `project/2026-10-17-kedro-viz-is-back-on-pages-2247-resumed-every-ci.md` |
| `project/ci-resume-delete-pause-platform-container-builds-for-platfor.md` | CI resume receipt; no `PAUSE_*` variable remains | `project/2026-10-17-kedro-viz-is-back-on-pages-2247-resumed-every-ci.md` |
| `project/ci-resume-operator-2026-10-16-unpause-everything-gh-workflow.md` | CI resume receipt; the same state is the later record's opening fact | `project/2026-10-17-kedro-viz-is-back-on-pages-2247-resumed-every-ci.md` |
| `project/2026-09-25-bmad-suite-advance-landed-as-pr-1607-branch-suite.md` | "Not merged" capture; its three operator asks (publish, floors, skill-forge 2.2.0) closed in PR #1607 | `project/2026-09-26-pr-1607-merged-f69e0d4d8a-10-commits-the-bmad-sui.md` |
| `project/2026-09-26-session-close-supersedes-the-operator-owned-next.md` | Session close; its queue landed; B's PR #19 is stated by the unifying-strategy Dream and scribe's `epics.md` (B's under the writer lock) | `project/2026-11-10-session-close-main-e694e9911a-zero-open-prs-the-e.md` |
| `project/2026-09-28-session-close-fleet-decomposition-dispatchability.md` | Session close; marshal 68.1 landed; the three flips are done (steward 72.2, herald 27.5, doctor 33.1); the Frame PR is row DW-mason-egm-2026-11-1 | `project/2026-11-10-session-close-main-e694e9911a-zero-open-prs-the-e.md` |
| `project/2026-09-28-night-intake-triage-session-close-pr-1654-merged.md` | Session close; PRs #1655 to #1659 merged 2026-09-29; every named flip is done; `pyforge.three_surfaces` removed (steward 76.4); both open questions were ruled and stand in `spec-pyforge-warden` CAP-25 and steward Story 76.3 | `project/2026-11-10-session-close-main-e694e9911a-zero-open-prs-the-e.md` |
| `project/2026-09-29-session-close-intake-triage-follow-through-main-d.md` | Session close; every authorized flip is done; the refused-landing procedure (MRS-DISP-038) is in `docs/dreams/pyforge-marshal.md` | `project/2026-11-10-session-close-main-e694e9911a-zero-open-prs-the-e.md` |
| `project/2026-09-29-session-close-bmad-estate-catalog-scribe-epic-24.md` | Session close; PR #1672 merged; the channel's role is `recipes/bmad-suite/README.md`'s first paragraph; the version disagreement is row DW-steward-suite-versions-disagree-2026-09-29 | `project/2026-11-10-session-close-main-e694e9911a-zero-open-prs-the-e.md` |
| `project/2026-10-05-session-close-deferral-burn-down-phases-1-3-focus.md` | Session close; marshal 86.2 landed; the parked-story gap (MRS-DISP-034) is marshal Story 83.4 | `project/2026-11-10-session-close-main-e694e9911a-zero-open-prs-the-e.md` |
| `project/2026-10-07-session-close-main-efe571e9da-pr-1893-merged-inde.md` | Session close; the free-threading next steps are the review record's; the merged branch is deleted | `project/2026-10-07-independent-review-of-the-steward-free-threading.md` |
| `project/2026-10-07-session-close-flag-story-batch-landing-path-fixes.md` | Session close; warden 16.1, 16.2 and 16.3 are done | `project/2026-11-10-session-close-main-e694e9911a-zero-open-prs-the-e.md` |
| `project/2026-10-12-session-close-main-3c2659a112-fleet-excluding-the.md` | Session close; its blocked rows (atlas 24.2, marshal 33.11, mason 22.3 and 22.4, steward 87.2) and the warden live scan are in the newest close; `.warden/fleet-target.toml` is in warden's 16.1 and 18.1 specs | `project/2026-11-10-session-close-main-e694e9911a-zero-open-prs-the-e.md` |
| `project/2026-10-13-session-close-main-6b9d33263f-2182-pending-landed.md` | Session close (cited from herald's memlog); the named worktrees are gone; the CI-pause chains landed (doctor 45, herald 39, marshal 100); DW-mason-30-1-2 is a row | `project/2026-11-10-session-close-main-e694e9911a-zero-open-prs-the-e.md` |
| `project/2026-10-15-session-close-main-4846af7fba-landed-steward-102.md` | Session close; the Pages chain landed (#2240), the pauses lifted (#2247); the preflight default is AGENTS.md's | `project/2026-10-16-pages-redesign-landed-pr-2240-merged-as-38ec9a2d2.md`; the newest session close |
| `project/2026-10-16-session-close-main-d25328c356-2246-pending-landed.md` | Session close; the pauses lifted (#2247); the kept worktrees are gone; the stray-patch ask is carried by the 2026-10-17 close, which stays | `project/2026-10-17-session-close-main-ff13960509-landed-since-the-20.md` |
| `project/2026-11-04-session-close-pr-2359-branch-egm-parked-2026-11-b.md` | Session close; PR #2359 merged; 118.3 and the mason rows are in the newest close | `project/2026-11-10-session-close-main-e694e9911a-zero-open-prs-the-e.md` |
| `project/2026-11-04-session-close-main-d403d48148-landed-pr-2360-ee1a.md` | Session close; the first `challenge --audit` ran (the newest close's EGM 2026-11-05 findings); the Sonnet ruling is in marshal's memlog | `project/2026-11-10-session-close-main-e694e9911a-zero-open-prs-the-e.md` |
| `project/story-46-1-landed-in-dispatch-pyforge-doctor-46-1-worktree-e.md` | Landing receipt; doctor `46-1-…: done` | `spec-46-1-the-env-hygiene-scan-walks-each-tree-once-and-skips-test-code.md` (doctor) |
| `project/story-100-2-landed-in-dispatch-pyforge-steward-100-2-worktre.md` | Landing receipt; steward `100-2-…: done` | `spec-100-2-one-command-moves-the-library-pins-on-the-policy-and-restores-what-the-upgrade-loses.md` (steward) |
| `project/story-100-3-landed-in-dispatch-pyforge-steward-100-3-worktre.md` | Landing receipt; steward `100-3-…: done` | `spec-100-3-every-derived-surface-regenerates-from-the-lock-by-its-own-generator.md` (steward) |
| `project/story-100-5-implementation-dispatch-pyforge-steward-100-5-re.md` | Landing receipt; steward `100-5-…: done` | `spec-100-5-a-moved-pin-is-realized-not-just-locked.md` (steward) |
| `project/story-100-4-landed-in-worktree-dispatch-pyforge-steward-100.md` | Landing receipt; steward `100-4-…: done` | `spec-100-4-the-refreshed-estate-proves-itself-in-every-environment-and-every-station-suite.md` (steward) |
| `project/story-99-1-landed-in-dispatch-worktree-ci-surfaces-registry.md` | Landing receipt; steward `99-1-…: done`; its pauses lifted | `spec-99-1-the-ci-surfaces-are-declared-once-and-the-workflows-are-judged-against-them.md` (steward) |
| `project/story-99-2-cap-166-ci-surface-gates-render-sweeps-pause-frag.md` | Landing receipt; steward `99-2-…: done` | `spec-99-2-every-ci-job-carries-its-pause-switch.md` (steward) |
| `project/story-100-7-bmad-build-auto-blocked-estate-refresh-restore-f.md` | Blocked-run receipt; the refresh it asked the operator to rerun landed, steward `100-7-…: done` | `spec-100-7-the-first-refresh-lands-through-the-path.md` (steward) |
| `project/story-99-6-landed-in-worktree-dispatch-pyforge-steward-99-6.md` | Landing receipt; steward `99-6-…: done`, its AC4 run included | `spec-99-6-a-paused-expensive-build-still-runs-once-a-week.md` (steward) |
| `project/story-99-7-bmad-build-auto-retired-staged-recipes-linter-wor.md` | Landing receipt; steward `99-7-…: done` | `spec-99-7-the-hand-disabled-workflows-are-retired-or-parked-and-the-convention-is-documented.md` (steward) |
| `project/story-45-1-cap-89-ci-pause-drift-doctor-source-reads-steward.md` | Landing receipt; doctor `45-1-…: done` | `spec-45-1-doctor-names-every-ci-surface-that-drifted-stuck-or-outlived-its-review-date.md` (doctor) |
| `project/story-102-1-landed-in-worktree-dispatch-pyforge-steward-102.md` | Landing receipt; steward `102-1-…: done` | `spec-102-1-the-pages-workflow-is-steward-s-and-fires-only-on-the-published-inputs.md` (steward) |
| `project/story-48-1-landed-in-worktree-dispatch-pyforge-doctor-48-1-d.md` | Landing receipt; doctor `48-1-…: done` | `spec-48-1-one-registry-orders-every-section-of-the-pages-site.md` (doctor) |
| `project/story-104-1-landed-in-dispatch-pyforge-marshal-104-1-model-i.md` | Landing receipt; marshal `104-1-…: done`; the loop home `~/.bmad-loops/pyforge-marshal` holds the merge (`c2efbade1d`) | `spec-104-1-the-mcp-json-marshal-renders-never-makes-a-loop-home-dirty.md` (marshal) |
| `project/story-118-1-cap-176-steward-deploy-nic-wraps-nic-validate-up.md` | Landing receipt; steward `118-1-…: done`; AC2 ran attended 2026-10-31 | `feedback/attended-nkp-bring-up-on-rootless-docker-kind-steward-story.md`; `spec-118-1-steward-deploy-nic-brings-up-and-tears-down-an-nkp-cluster-on-local-kind.md` (steward) |
| `project/story-117-5-implemented-in-dispatch-pyforge-steward-117-5-wo.md` | Landing receipt; steward `117-5-…: done` | `spec-117-5-preflight-budget-names-every-lane-over-its-journal-derived-budget.md` (steward) |

### Left out (5 candidates stay in the index)

- `operator-inbox-as-of-2026-09-19-the-asks-a-session-cannot-cl.md`: item (4) is row DW-FU-19-1-3, still `open` (the
  non-Claude harness sessions are the operator's to run), and items (5) and (6) close only by editing this record; no
  later record states them.
- `2026-10-06-session-close-main-a16ab7f7e2-re-verified-2026-10.md`: its TRAP is a rule no other record states. A
  checkout without `.git/hooks/pre-push` skips `pr-preflight` on every push with no warning. AGENTS.md says only that
  pushes run the preflight through the hook; `feedback/never-run-a-realize-step-that-installs-git-hooks-pre-commit.md`
  gives only the repair command; `precommit_config_check.py` checks `.pre-commit-config.yaml`, not the installed hook.
- `2026-10-17-session-close-main-ff13960509-landed-since-the-20.md`: the operator has still to delete
  `~/.local/share/pyforge/stray-patches-2026-10-16/` (present 2026-11-11); no later record states the ask.
- `2026-10-18-addendum-to-the-2026-10-17-session-close-main-488.md`: the six merged branches it names are still on
  `origin` (`git ls-remote`, 2026-11-11), and deleting them is the operator's; no later record states the ask.
- `2026-10-31-session-close-main-b9cc03bcc2-nebari-hosting-stew.md`: the nic 0.17.0 publish is open; no later record
  states the ask. `pixi.lock` resolves `nebari-infrastructure-core` 0.14.0, and the `pixi.toml` comment reads "floor
  tracks publish until 0.17.0 lands"; the newest close names only Story 118.3's Hetzner inputs.

## Spec Change Log

- 2026-11-10: minted with Epic 32 at the cutover-readiness mint. The operator approved the manifest and its form
  (`git mv` to `archive/.claude/memory/project/`) the same day, so this story moves the records and AC4 checks the
  moves; the plan's "nothing moves" check and its effort S are superseded (effort M).
- 2026-11-11 (build): deviation from Boundaries "Move with `git mv`". The build runs under a no-git-writes rule (the
  wave gate commits), so the records moved with plain `mv`. Each file is byte-identical (blob hash unchanged), so git
  still records a rename (`R100`), but only if the wave gate stages both halves in one commit: the 40 deletions under
  `.claude/memory/project/`, the 40 additions under `archive/.claude/memory/project/` and the `MEMORY.md` edit. Until
  that commit lands, AC4's rename count reads 0 on the branch.
- 2026-11-11 (build, review round 1): two records went back to the index (see § Review findings), so the manifest
  moves 40 records, not 42, and leaves out 5.

## Review findings (build, round 1, 2026-11-11)

- **Major, Manifest row for `2026-10-31-session-close-main-b9cc03bcc2-nebari-hosting-stew.md`.** It was archived
  while it still carried an open operator ask (the nic 0.17.0 publish). The Never boundary forbids that. No other
  record names the ask. Fixed: the record is back in `.claude/memory/project/`, its index line is restored, and its row
  moved to "Left out".
- **Minor, Manifest row for `2026-10-06-session-close-main-a16ab7f7e2-re-verified-2026-10.md`.** The cited homes do
  not state its TRAP (a missing pre-push hook skips the preflight silently). Searched `.claude/memory/`, AGENTS.md,
  `docs/` and the steward code: no record or check states it. Fixed: the record stays, and its row moved to "Left out".
- **Minor, Boundaries (`git mv`) and AC4.** The moves used plain `mv`, and the story spec did not say so. AC4 reads 0
  renames until the gate commits. Fixed: the Spec Change Log records the deviation and what the wave gate must stage
  together.
- **Minor, `tests/meta/test_team_memory_index.py`.** No fixture covered a link to an existing file that is not a
  record. Fixed with a separate test, `test_a_link_to_a_file_that_is_not_a_record_is_named`. It is not a fifth
  `test_index_guard_names` case, because AC2 expects exactly `4 passed`.
- **Minor, scribe trigger paths in `.github/workflows/pyforge-station-tests.yml`.** That file is not this story's.
  Story 124.2 owns it, depends on this story, and its notes list "scribe's reads of … .claude/memory" among the
  reads its trigger-map test derives. So the widening rides 124.2. Until then the guard runs locally through
  `pyforge-scribe-test`.
