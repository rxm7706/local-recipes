---
title: 'pyforge-marshal — Retrospective (2026-11-26: Epics 119 to 125, test fixes, fail-closed defects and three fleet conventions)'
project: pyforge-marshal
created: '2026-11-26'
updated: '2026-11-26'
epics: [119, 120, 121, 122, 123, 124, 125]
date: '2026-11-26'
verdict: accepted-with-open-items
criteria: declared
headless: true
scope: 'Every marshal epic landed since the 2026-11-13 retro: Epics 119 to 124 on origin/main, and Epic 125 on branch plugin-names-2026-11-26 (HEAD 24af8d0a90, not yet on origin/main). Also the steward stories of the same window that changed marshal source (125.2, 126.4). Written by bmad-retrospective, headless, as the chain-currency remedy: Story 125.1 moved the package pyproject.toml on 2026-11-26 (5ae0f4334f) and the last retro was 2026-11-13, so the sweep reported feeds code->retro (CHAIN-CURRENCY-RUNBOOK.md step 5).'
evidence:
  - 'range ed9668e4ca^..HEAD (HEAD 24af8d0a90 on plugin-names-2026-11-26): 189 commits, 27 merges (24 measured on the first-parent spine), the fleet''s other stations included; scripts/git_evidence.py output kept in the session scratch folder'
  - 'story commits: ed9668e4ca (119.1), 693fcc4d54 (120.1), 56bdadedb8 (121.1), c441309203 and 405ac0c1f4 (122.1), 042f638189 (123.1), 558156c8fa (124.1), 5ae0f4334f (125.1)'
  - 'landing merges on origin/main: 6385246de4 (119.1, subject pyforge-steward/127-2), 9318582f00 (120.1, pyforge-steward/129-1), 080f89c4df (121.1, pyforge-steward/133-1), 4c04b1103e (122.1, pyforge-steward/137-1), 725eb78ee4 (123.1, pyforge-marshal/123-1), 3556bd1f2e (124.1, pyforge-steward/144-1); 125.1 unmerged'
  - 'each story''s acceptance commands re-run 2026-11-26 in this worktree: all exit 0 (or the expected exit 1 for 122.1 AC2); counts under Behavior verification'
  - 'pixi run --frozen -e pyforge-marshal pyforge-marshal-test: exit 0, 13768 passed, 22 skipped, then 27 passed, 4 skipped; pyforge-marshal-live-test: exit 0, 510 passed (2026-11-26)'
---

# pyforge-marshal — Retrospective, Epics 119 to 125 (2026-11-26)

## Epic summary

- **Epics and stories.** Seven one-story epics (`epics.md` lines 11814 to 11975), each minted from a dated entry on
  `docs/dreams/pyforge-marshal.md` and an operator line quoted in the epic header:
  - **119** (*A challenge run past its ceiling is checked without a race*, `spec-pyforge-marshal:CAP-298`, fix, minted
    2026-11-21): `test_a_session_past_its_ceiling_exits_1_with_outcome_error` waits up to 2 s for its fake session's pid
    file instead of reading it at once. It failed once in a 48-lane preflight on PR #2375 and never alone (commit body of
    `ed9668e4ca`). Test-only.
  - **120** (*The dispatch-verification fakes match a command by its words*, `spec-pyforge-marshal:CAP-170`, fix,
    2026-11-21): `CrossSurfaceProcess` and the environment-yaml fake matched a substring of the joined command line, so
    a worktree named `platform-ci-local-test-leak-2026-11-21` reddened six cross-surface tests (`spec-120-1-...` § Spec
    Change Log). They now match whole tokens. Test-only.
  - **121** (*Teardown, the front door and the required-check read fail closed*, CAP-287, CAP-304, CAP-210, fix,
    2026-11-25): closes `DW-marshal-review-2026-11-24-1`, the three marshal defects of the 2026-11-24 review. Each was
    reproduced by a failing test on the unchanged tree before its code changed (`spec-121-1-...` § Spec Change Log,
    defects 1 to 3). The changes are in `core/teardown_preserve.py`, `cli/main.py` and `adapters/forge_gh.py`.
  - **122** (*Marshal's verdict and seed take their exit codes from the declaration*, `spec-pyforge-steward:CAP-184`,
    fix, 2026-11-25): `core/verdict.py` and `seed/errors.py` read the `marshal` and `marshal-seed` domains of
    `pyforge.core.exit_domains`. Before and after, every code is equal and `contract.md` did not move (§ Spec Change Log).
  - **123** (*The citation detector reads station source*, `spec-one-chain-per-station:CAP-9`, feature, 2026-11-26):
    `scripts/ad_citation_check.py` also scans `src/shared/packages/pyforge-*/src` against each package's home project.
    It adds no baseline entry for source.
  - **124** (*Marshal's verbs take both spellings for JSON*, `spec-pyforge-steward:CAP-185`, feature, 2026-11-26):
    the parser builder calls `pyforge.core.cli_output.align_json_options`, and `contract.md` lists the added spelling.
  - **125** (*Marshal's loop-runner plugin is registered under marshal's name*, `spec-pyforge-unifying-strategy:CAP-18`,
    chore, 2026-11-26): the `pyforge.core.hooks` entry point `bmad-loop` becomes `marshal-runner-bmad-loop` in
    `pyproject.toml`. Selection stays by `plugin_id`.
- **Status.** Every story key and `epic-119` to `epic-125` read `done` in `sprint-status-ledger.yaml` (lines 136 and
  143 to 148; 618 to 633). Every story spec's frontmatter reads `status: 'done'`. The `epic-N-retrospective` keys read
  `optional`. No `pending_stories`: the completeness gate passes on the tracked ledger.
- **Landing.** Six stories are on `origin/main` (`3556bd1f2e`), each by `git merge-base --is-ancestor`; the evidence
  block names their merges. Story 125.1 (`5ae0f4334f`) is on this branch only. It shares its commit with steward 146.1
  and mason 45.1.
- **Also in the window (not a marshal epic).** Two steward stories changed marshal source under
  `spec-pyforge-steward:CAP-175`. Story 125.2 (`d2089bb49d`) changed `seed/engine/copier.py`, which now resolves its
  stage root behind a symlinked temp directory. Story 126.4 (`bfa5fe8db8`) changed `dispatch_verify.py`,
  `adapters/session_group_psutil.py`, `seed/detect/findings.py` and `seed/detect/optout.py`, so marshal reads a zombie
  without `/proc` and its remedies name commands that exist. Marshal's memlog names both (entries 2387 to 2390).
- **Evidence inventory.** Available: `epics.md`, the seven story specs, the ledger, the marshal Spec memlog (entries
  2386 to 2406 cover the window), the deferred-work ledger, the commits and merges, `git_evidence.py` output, and the
  acceptance commands re-run today. The Review section of `spec-125-1-...` is in the working tree and not yet committed:
  another agent is editing it on this branch now, and this retro reads it as found. Missing: the build agents' session
  logs. So process lessons come only from the story specs' change logs and review sections, and from the memlog.

## Findings

Each finding has a source and two dispositions: what happens to this instance (fixed, defer or accept), and what
prevents the next one.

### Spec-to-implementation reconciliation

1. **Three of the 2026-11-13 retro's open rows are still open, and no story in this window carries them.** Source:
   `deferred-work-ledger.md` lines 9237 (`DW-marshal-114-2-3`), 9259 (`DW-marshal-114-3-2`) and 9314
   (`DW-marshal-116-4-1`) all read `status: open`. `tests/meta/test_spec_names_live_paths.py:120-121` still carries the
   two `CAP-305` ALLOW entries, with the reason "open while CAP-305 reads ready". `grep -nE
   'MRS-CHAIN-005|MRS-PREFLIGHT-016|MRS-REFRESH-008' core/verdict.py` exited 1 today. Epics 122 and 124 edited
   `core/verdict.py` and `cli/main.py`, the modules next to two of these rows, and left both rows alone.
   *Instance:* defer; each row stays open (action items 1 to 3). *Prevention:* when a story edits a module that an open
   row names, its mint lists that row and either folds it in or says why not. AGENTS.md behavioural guideline 3 makes
   a fix in a surface the story already carries the default.
2. **Story 123.1's first reconcile entry cited the wrong capability.** Source: marshal memlog line 2402 says
   "spec-one-chain-per-station capability 3". Line 2403, the review round, corrects it to capability 9, the chain
   standard's id grammar. The epic header and the story spec say CAP-9. *Instance:* fixed in the review round.
   *Prevention:* a reconcile entry copies its capability id from the epic header, not from memory.
3. **Two reconcile entries reached the memlog a day late.** Source: memlog lines 2405 and 2406 were "named now, found
   by spec-surface while landing Story 146.1". They name 122.1's meta-test
   `tests/meta/test_verdict_reads_the_exit_declaration.py` (landed 2026-11-25 in `c441309203`) and the co-governed
   kernel files of steward 137.1, 142.1 and 144.1. `spec-125-1-...` § Review finding 3 records the same thing for five
   other Specs. *Instance:* fixed in `5ae0f4334f`. *Prevention:* a multi-station change runs `spec-surface-check` before
   its own stamp and names every governor the detector lists (AGENTS.md § Pre-PR checklist item 5). The 122.1 change
   landed without running that step.
4. **One accepted narrowing in Story 123.1.** Source: `spec-123-1-...` § Review (2026-11-26) leaves out `django-*`
   portals and non-Python files. `django-pyforge` cites 43 bare tags and marshal's JSON data files cite 76.
   `_bmad/custom/bmad-review.toml` still names a bare roster tag. A bare number that two spines both define stays
   invisible to the check. *Instance:* accept as scoped; the review records it. *Prevention:* none proposed here. The
   gap belongs to the spec that owns the detector (action item 4).

### Story boundaries and test reliability (inline diff-scope review)

5. **Two tests that the machine could break, not the code.** Sources: `ed9668e4ca` (a 1.5 s ceiling raced the fake
   session's first line under a 48-lane preflight) and `693fcc4d54` (a substring fake matched the interpreter's path in
   a worktree named for a command). Neither fix changed runtime code. The HARD boundaries of Epics 119 and 120 forbid
   it, and `git show --stat` lists test files and planning files only. *Instance:* fixed. *Prevention:* a test fake
   matches argv tokens, never a joined command line, and a test that reads a file a subprocess writes waits a bounded
   time for it. Story authors can check both (action item 5).
6. **No review is recorded for Stories 119.1 and 120.1.** Source: `grep -i review` over both story specs finds only the
   frontmatter keys (`review_loop_iteration: 0`). Their change logs say only "done on branch ..." / "done on that
   branch". The other five stories record an independent review: 121.1 and 122.1 in their change logs, and 123.1 to
   125.1 in a § Review section. AGENTS.md behavioural guideline 8 requires a separate review. *Instance:* accept. Both
   are test-only S fixes, and the suites pass today (Behavior verification). *Prevention:* a story spec is not moved to
   `done` without a review line, even for a test-only fix (action item 6).
7. **Story 121.1's three defects were each reproduced before the fix, and none was closed as "not a defect".** Source:
   `spec-121-1-...` § Spec Change Log, defects 1 to 3. Each names the failing test and its exit 1 on the unchanged tree.
   A lead ruling after review kept the teardown scan fail closed on local refs and named the remedy in
   `MRS-TEARDOWN-006`. *Instance:* accept. This is the pattern to repeat. *Prevention:* none needed.
8. **A one-line `pyproject.toml` edit failed `ruff format --check`.** Source: `spec-125-1-...` § Review finding 2
   (working tree). Three station tests also pinned the old entry-point names: `test_build_hooks.py`,
   `test_loop_runner_hook.py` and `test_deploy_profile_plugins.py`. *Instance:* fixed in `5ae0f4334f`. *Prevention:*
   the 2026-11-13 retro's finding 7 applies again: a story that changes a declared name lists, at mint, every test
   that pins that name. 125.1's surface named only `test_loop_runner_hook.py` at mint.

### Aggregate views

9. **The runtime change is small and stays on existing seams.** Source: `git_evidence.py` `files` for marshal `src/`
   over the range: `cli/main.py` +27 −2 (121.1 and 124.1), `core/teardown_preserve.py` +28 −5, `adapters/forge_gh.py`
   +47 −42 (121.1), `core/verdict.py` +11 −11 and `seed/errors.py` +12 −6 (122.1). Adding steward's 125.2 and 126.4
   from the wider window (`git diff dca04bd9e9 HEAD --stat`), marshal `src/` is 11 files, +167 −83. No new verb, port,
   flag or exit code. *Instance:* accept.
10. **Marshal now depends on two new kernel declarations.** Source: `c441309203` adds
    `pyforge-core/src/pyforge/core/exit_domains.py` (+95) and `558156c8fa` adds `core/cli_output.py` (+158). Marshal
    reads both through `pyforge.core`, its allowed seam. A drift between marshal's frozen AD-7 domain and the
    declaration now reds `tests/meta/test_verdict_reads_the_exit_declaration.py`. *Instance:* accept. A second root
    rebuilds one declaration, not eight sets of constants.
11. **Five of seven marshal stories landed under another station's merge subject.** Source: the landing merges in the
    evidence block. Only 123.1 landed as `Merge pyforge-marshal/123-1 into main`. The rest rode multi-station PRs whose
    subject names one steward key, as AGENTS.md § Pre-PR checklist item 7 allows. *Instance:* accept. The ledger rows
    are `done`, and `git merge-base --is-ancestor` proves each landing. *Prevention:* any tool that reads landing
    evidence for marshal keys from merge subjects alone will miss these five. That is a known pitfall in AGENTS.md
    (§ Known pitfalls), so no new action.

### Records this window closes or carries

12. **One row closed, none opened by marshal stories.** Source: `DW-marshal-review-2026-11-24-1` reads `RESOLVED
    2026-11-25 — Story 121.1` (`deferred-work-ledger.md` line 9490 and below). Story 122.1 binds `DW-VOCAB-2026-09-14-8`
    (`spec-122-1-...` § Binding). Every story spec of the seven has `deferred: []`. *Instance:* accept.

## Behavior verification

Run 2026-11-26 in this worktree. Each verdict comes from the exit code; the counts are from pytest's summary line.

- 119.1: `pytest tests/unit/test_factory_challenge.py -m "live_tree or not live_tree"` (`-e pyforge-marshal`): exit 0,
  106 passed.
- 120.1: `pytest tests/unit/test_dispatch_verification_live_tree.py tests/unit/test_dispatch_environment_yaml.py`: exit
  0, 67 passed. The worktree path does not name a command, so this run does not re-create the trigger condition.
- 121.1: `pytest` over `test_teardown_preserve.py`, `test_init_teardown_preserve.py`, `test_cli.py` and
  `test_forge_gh.py`: exit 0, 260 passed, 7 skipped.
- 122.1: AC1 (`-k 'verdict or seed_errors or exit or public_contract'`, run as written): exit 0, 1216 passed,
  1 skipped. The build record says 1,314 passed. The cause of the difference was not investigated. AC2 (the grep for
  spelled exit numbers): exit 1, the expected result.
- 123.1: AC1 `pytest tests/scripts/test_ad_citation_check.py` (`-e pyforge-guild`): exit 0, 17 passed. AC2
  `ad-citation-check`: exit 0.
- 124.1: AC1 `tests/meta/test_public_contract.py`: exit 0, 33 passed. AC2 `tests/scripts/test_json_output_spellings.py`:
  exit 0, 21 passed.
- 125.1: AC1 `pyforge-core` `test_plugin_registration_conformance.py -m live_tree`: exit 0, 15 passed. AC2
  `test_loop_runner_hook.py`: exit 0, 8 passed.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` (the package half): exit 0; 13768 passed, 22 skipped,
  then 27 passed, 4 skipped.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-live-test` (the live-tree half): exit 0; 510 passed.
- Not exercised end to end: a real `teardown --force` against a loop home with an unpushed branch (121.1 exercises it
  through real-git tests only), and a paginated required-check read against GitHub (exercised through fakes only).

## Previous-retro follow-through

The 2026-11-13 retro's verdict was **rejected** because every key of Epics 114 to 118 was then `backlog` or `blocked`.
The ledger now reads `done` for all 22 story keys and for `epic-114` to `epic-118` (`sprint-status-ledger.yaml` lines
114 to 135 and 608 to 616), so the condition that forced that verdict is gone. Its six action items:

| # (2026-11-13) | State on 2026-11-26 | Evidence |
|---|---|---|
| 1 Amend CAP-305's guard clause | open | `DW-marshal-116-4-1` `status: open` |
| 2 `_CLASSIFY_TABLE` rows for three codes | open | `DW-marshal-114-3-2` open; grep of `core/verdict.py` exits 1 |
| 3 Drop two dead ALLOW entries | open | `DW-marshal-114-2-3` open; `test_spec_names_live_paths.py:120-121` |
| 4 `deferred_work_intake.py --project` long slug | open | `scripts/deferred_work_intake.py:225` still rejects a name not in `slug_map` |
| 5 Run each acceptance command once at mint | partly followed | every AC re-run above passes as written |
| 6 No fixture rebinds `__file__`; grep node ids before a move | no counter-evidence | no test module was moved in this window |

## Strategy convergence

Under the Unifying Strategy, marshal is the station that turns a Dream into a measured build, and the cutover will
rebuild it on B from the seed. This window adds no capability toward B. It does make marshal more uniform with the rest
of the fleet in three ways, each declared once in the kernel: exit-code domains (`spec-pyforge-steward:CAP-184`,
Epic 122), the JSON spellings (`CAP-185`, Epic 124), and plugin registration names
(`spec-pyforge-unifying-strategy:CAP-18`, Epic 125). Epic 123 holds station source to the same citation grammar as
planning prose (`spec-one-chain-per-station:CAP-9`). Each convention is now a declaration in `pyforge-core` plus a
meta-test, not a pattern each station copies. A rebuild then has one contract to match, and drift reds a test.
Epics 119 to 121 make marshal's suite and its fail-closed paths trustworthy as the oracle `spec-pyforge-marshal:CAP-305`
asks for: two tests no longer read the machine, and three runtime paths no longer fail open. The remaining gap toward
"the Spec says what is built" is the three open rows of finding 1. The estate has not moved: the cutover state is
recorded in herald's dossier, not here.

## Action items

All are proposed; this retrospective applies none of them.

| # | Action | Owner | Kind |
|---|---|---|---|
| 1 | Amend `spec-pyforge-marshal:CAP-305`'s guard clause to name the off-tree start (memlog change entry and render), closing `DW-marshal-116-4-1`. Carried from 2026-11-13. | marshal (next Spec story) | spec reconciliation |
| 2 | Add verdict-lattice rows for `MRS-CHAIN-005`, `MRS-PREFLIGHT-016` and `MRS-REFRESH-008`, closing `DW-marshal-114-3-2`. Carried. | marshal | remediation |
| 3 | Drop the two dead `CAP-305` ALLOW entries, closing `DW-marshal-114-2-3`. Carried. | marshal | remediation |
| 4 | Decide whether `ad-citation-check` scans `django-*` portals and data files, or records why it does not (finding 4). | the owner of `spec-one-chain-per-station` | tooling |
| 5 | Test fakes match argv tokens; a test that reads a file a subprocess writes waits a bounded time (finding 5). | marshal (story authors) | process lesson |
| 6 | Record a review line on every story spec before `done`, test-only fixes included (finding 6). | marshal (story closers) | process lesson |
| 7 | A story that edits a module named by an open deferred-work row lists that row at mint (finding 1). A story that renames a declared name lists every test that pins it (finding 8). | marshal (plan mint) | process lesson |

## Acceptance verdict

**Machine verdict: accepted-with-open-items** (headless, criteria declared in each story spec's Acceptance Criteria).
Every story key is `done` on the tracked ledger, every acceptance command re-run today exits as declared, and the
runtime changed only on the seams the stories named. No finding blocks acceptance. The open items are the three rows
carried from 2026-11-13 (finding 1), the late reconciles fixed on this branch (finding 3), and the review records
missing from 119.1 and 120.1 (finding 6). Story 125.1 is accepted on its branch state, and it holds only once
`5ae0f4334f` lands. A human may override; this run records no human decision.

## Open questions

- Should 119.1 and 120.1 get a retroactive review line, or is the passing suite enough for test-only fixes? The build
  rules gave this run no answer.

## Assumptions

- The epics were taken from the invocation (119 to 124 landed on `origin/main`, plus 125 on this branch), not
  auto-detected. The completeness check read the tracked `sprint-status-ledger.yaml`. `sprint_status.py detect-epic`
  was not run, because this worktree's `implementation-artifacts/` feed is not part of the evidence for a landed
  window.
- The EGM drift stage (the activation append step in `_bmad/custom/bmad-retrospective.toml`) was skipped:
  `pyforge.marshal.egm_retro_drift` is `off` in `src/platform/config/flags.json` and in every overlay of
  `flag-overlays.json`.
- `bmad-review` was not invoked. Five of the seven stories already record an independent review (finding 6), and this
  run's brief limits it to one file. The diff-scope review ran inline over the story boundaries (findings 5 to 8)
  only; the code lenses were not re-run over each hunk.
- Phase 5's `sprint_status.py update` was not run, and no `--set-action-status` transitions were written. This run
  writes no ledger or feed, so `epic-119-retrospective` to `epic-125-retrospective` stay `optional`, and the action
  items above are recorded only here.
- The document lives at `planning-artifacts/retros/retro-pyforge-marshal-2026-11-26.md`, the station's tracked retro
  home that the chain-currency sweep reads, not at the skill's default Tier-3 path.
