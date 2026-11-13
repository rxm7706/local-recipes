---
title: 'pyforge-marshal — Retrospective (2026-11-13: Epics 114 to 118, the cutover readiness change)'
project: pyforge-marshal
created: '2026-11-13'
updated: '2026-11-13'
epics: [114, 115, 116, 117, 118]
date: '2026-11-13'
verdict: rejected
criteria: declared
headless: true
scope: 'Epics 114 to 116 (the marshal unit) and 117 to 118 (the core-kit unit) of the single cutover-readiness PR (branch cutover-readiness-2026-11-10): the marshal Spec says what is built (114), roots, forge and station reach come from their seams (115), the suite is an oracle off the monorepo and the change closes (116), the shared floor says what it is (117), the testing kit is a floor a second root can rebuild (118). Written by bmad-retrospective, headless, as Story 116.5 step (6). The package pyproject.toml moved on 2026-11-11 (f1e2c49267, Story 116.1''s live_tree marker), so this is the code->retro retrospective the chain-currency sweep owes.'
evidence:
  - 'range 66a1d3ce24^..HEAD on cutover-readiness-2026-11-10 (HEAD 501890d2ab at the time of reading): 61 commits, 0 merges (merge_count 0, merges_measured 0); scripts/git_evidence.py output kept in the build scratch folder'
  - 'story commits: f1e2c49267 (114.1, 115.1, 115.2, 115.3, 116.1, 117.1, 117.2, 117.3, 117.5, 118.1, 118.2), 977582c2e9 (deferred twin for 115.1), 2a2f4d6557 (114.2, 115.4, 117.4, 117.7), a15d2cdd6f (114.3), e7ba4e90f5 (116.2), d931b251c2 (116.3), b6f53ebcf8 (116.4), 77c9b7acc5 (117.6), d774391a2e (117.8); the mint 66a1d3ce24'
  - 'pixi run --frozen -e pyforge-marshal pyforge-marshal-test: exit 0, 13730 passed, 14 skipped, then 27 passed, 4 skipped (2026-11-13)'
  - 'pixi run --frozen -e pyforge-marshal pyforge-marshal-live-test: exit 0, 504 passed; pyforge-core-test: exit 0, 433 passed 1 skipped and 2228 passed; pyforge-testing-kit-test: exit 0, 79 and 40 passed (2026-11-13)'
---

# pyforge-marshal — Retrospective, Epics 114 to 118 (2026-11-13)

## Epic summary

- **Epics:** 114 (*The marshal Spec says what is built*), 115 (*Marshal's roots, forge and station reach come from
  their seams, and its guards can fire*), 116 (*Marshal's suite is an oracle off the monorepo, and the change closes on
  a reconciled Spec*), 117 (*The shared floor says what it is*), 118 (*The testing kit is a floor a second root can
  rebuild*), all minted 2026-11-10 in `66a1d3ce24` from the station Dream's two entries of that date
  (`docs/dreams/pyforge-marshal.md`: *The Spec says what marshal is, and its roots come from one place*; *The shared
  floor says what it is*) and the operator rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`,
  Realization log). Headings: `epics.md` lines 11330 (Epic 114) to 11748 (Story 118.2).
- **Diff range:** `66a1d3ce24^..HEAD` (the mint's parent through scribe 31.4's build commit `501890d2ab`). 61 commits,
  no merges, no binary revisions. The range carries every unit's waves; this retro reads the marshal, core and kit
  paths and the marshal planning artifacts.
- **Stories built and reviewed on the branch:** the 21 named in the evidence block; 116.5 is the story writing this
  document. Each build commit says the story passed an independent review and the wave gate.
- **Stories not `done` in the feed** (`sprint_status.py detect-epic --epic <n>` on
  `implementation-artifacts/sprint-status.yaml`, 2026-11-13): every key of the five epics (Epic 114: 3, Epic 115: 4,
  Epic 116: 5, Epic 117: 8, Epic 118: 2). The tracked ledger reads the same (`sprint-status-ledger.yaml` lines 114-135:
  `blocked` or `backlog`; `epic-114`..`epic-118` `backlog`). The change's CLOSE-LEDGERS job promotes the built keys
  after this retro.
- **Evidence inventory.** Available: the epics and the 22 story specs (`planning-artifacts/specs/spec-114-*` to
  `spec-118-*`), the per-story commits, the review and gate records the story specs carry (114.1 § Integrator note,
  114.2 § Gate findings, 115.1 § Gate findings, 116.2 and 116.4 § Review findings, 117.7 § Review findings, 117.6
  § Verification), the Spec memlogs, the three suites run today. Missing: the build agents' session logs (not kept in
  the tree), so process lessons come from the review and gate records only.

## Findings

Each finding carries its source and two dispositions: this instance (fix now / defer / accept), and what prevents the
next one.

### Spec-to-implementation reconciliation

1. **Nine capabilities were built but still read ready.** Source: `SPEC.md` at `501890d2ab`
   (`spec-pyforge-marshal:CAP-13`, `spec-pyforge-marshal:CAP-23`, `spec-pyforge-marshal:CAP-208`,
   `spec-pyforge-marshal:CAP-227`, `spec-pyforge-marshal:CAP-229`, `spec-pyforge-marshal:CAP-261`,
   `spec-pyforge-marshal:CAP-287`, `spec-pyforge-marshal:CAP-304`, `spec-pyforge-marshal:CAP-305`
   `(ready 2026-11-10)`); the memlog decision *Marker of an
   amended capability* (2026-11-10) and its addendum. *Instance:* fixed in Story 116.5: the memlog's status-markers
   change entry of 2026-11-13 and the anchored render (10 lines; both self-validate passes logged) move all nine to
   `(shipped 2026-11-11)`, dated from each realizing story's build commit. *Prevention:* none needed; the operator
   ruled the closer flips them inside the PR.
2. **`spec-pyforge-marshal:CAP-305`'s guard clause names half of the guard.** Source: `spec-116-4-...` § Review
   findings round 1, finding 2, and § Planned deferral: the guard is the audit hook plus `tests/conftest.py`'s
   `_package_half_off_the_tree`, which starts every armed test off the tree; the capability names only the hook.
   *Instance:* defer, `DW-marshal-116-4-1`; Story 116.5's render moves markers only. *Prevention:* a contract change a
   review finds is minted into a story that owns the Spec's memlog and render, never left to a closer whose spec does
   not name it.
3. **Three registered finding codes have no verdict-lattice member.** Source: `spec-114-3-...` § Planned deferral;
   `contract.md` rows `MRS-CHAIN-005`, `MRS-PREFLIGHT-016`, `MRS-REFRESH-008` read `unclassified`;
   `grep -n` of the three in `core/verdict.py` prints nothing (2026-11-13). `classify` raises `ValueError` on them.
   *Instance:* defer, `DW-marshal-114-3-2`. *Prevention:* `tests/meta/test_public_contract.py` already reds the
   Verdict cell when a row is added, so the fix cannot land half-done.
4. **Story 46.2 shipped without the flag it declared.** Source: `spec-114-1-...` § Integrator note (BUILD-3 gate):
   `pyforge.marshal.context_bundle_digest` was never in `src/platform/config/flags.json`; the gate failed with
   `flag-key-not-in-tree` once 114.1 moved spec-46-2 to `done`. *Instance:* fixed by the integrator (`retires-flag:` on
   the spec). *Prevention:* the flag gate reads only `done` specs, so a declared flag that never lands surfaces when its
   story is promoted; no new guard is proposed.
5. **The live-path guard keeps two dead ALLOW entries.** Source: `tests/meta/test_spec_names_live_paths.py:120-121`
   (the two `spec-pyforge-marshal:CAP-305` entries, reason "open while CAP-305 reads ready") against `git ls-files`
   listing both files (Story 116.4, `b6f53ebcf8`) and `spec-pyforge-marshal:CAP-305` now shipped. *Instance:* defer, `DW-marshal-114-2-3`
   (the test file is Story 114.2's). *Prevention:* none beyond the row; the stale-entry test cannot see it by design.
6. **An accepted deviation in Story 114.2.** Source: `spec-114-2-...` § Spec Change Log (2026-11-11): the Always line
   named `test_engine_version_range_sync.py`, which keeps copier's range; `spec-pyforge-marshal:CAP-8` names
   `test_manifest_sync.py::test_harness_range_constants_match_pyproject_dependency_pin`, which keeps bmad-loop's.
   *Instance:* accept.

### Story boundaries (diff-scope review, inline)

7. **A header change in one story broke a sibling's pinned bytes.** Source: `spec-114-2-...` § Gate findings (BUILD-3):
   the `-e pyforge-guild` header in `scripts/promote_sprint_status.py` (spec-pyforge-marshal:CAP-229) reddened two
   tests of Story 116.1's `tests/unit/test_land_epic_rollups.py`; fixed by a three-hunk patch in `2a2f4d6557`
   (`_HEADER_THEN` / `_HEADER_NOW`). *Instance:* fixed. *Prevention:* a story that changes a generator's output names,
   at mint, every test that pins that output's bytes.
8. **Moving a test module broke another station's static citations.** Source: `spec-116-2-...` § Review findings
   round 1, finding 1: moving `test_promote_sprint_status_regressions.py` made steward's
   `tests/meta/test_cutover_case_list.py` fail twice (`case-list.md` row `k-launch-ledger-sync`). Fixed by keeping the
   module at its path, marked whole `live_tree`. *Instance:* fixed. *Prevention:* before moving a test module, `git grep`
   its node ids across tracked files (round 1 did it after the fact).
9. **A fixture that rebound `__file__` dropped a touched module's coverage.** Source: `spec-116-4-...` § Review
   findings round 1, finding 1: `monkeypatch.setattr(config, "__file__", ...)` made coverage.py file `cli/config.py`'s
   lines under a path that does not exist; 92.3% fell to 15.3% and `pyforge-marshal-coverage-gate` exited 1. Fixed
   by patching `_editable_checkout_root` instead. *Instance:* fixed. *Prevention:* no fixture rebinds a module's
   `__file__`; patch the reader of it.
10. **A deferral twin would have stayed red from BUILD-1 to this closer's BUILD-17.** Source: `spec-115-1-...`
    § Gate findings (BUILD-1, `deferred-work-check` exit 2, "stays red at each wave gate until 116.5 lands the twin"),
    closed the same day by the orchestrator's `977582c2e9`. *Instance:* fixed.
    *Prevention:* as mason's retro of 2026-11-12 found: a build records a deferral in its body (§ Planned deferral)
    for the closer, never as a frontmatter row with no twin across a gate.
11. **Acceptance commands that do not run as written.** Sources: `spec-116-4-...` § Review findings, finding 3 (AC5
    without `--frozen` re-locks `pixi.lock`); `spec-117-7-...` § Review findings, finding 1 (AC1's baseline at the merge
    base predates steward Story 124.4 and exits 1); this story's AC3, whose `deferred_work_intake.py --project
    pyforge-marshal` exits 2 (`unknown project(s)`: the script takes the short name `marshal`), and whose bare
    `python` (like AC5's) is not on `PATH` outside pixi. *Instance:* all three fixed under the oracle rule; Story
    116.5's AC3 and AC5 now run `pixi run --frozen -e pyforge-guild python …`, AC3 with `--project marshal` (its
    § Review findings (build, round 1, 2026-11-11)).
    *Prevention:* mint each acceptance command by running it once against the tool on the branch, with `--frozen`
    and a baseline read at the story's own parent commit.

### Aggregate views

12. **The runtime change is small and lands on existing seams.** Source: `git_evidence.py` `files`, marshal and core
    `src/`: two new adapters, `adapters/doctor_cli.py` (+141, the one module that runs Doctor's spec-surface command)
    and `adapters/forge_root.py` (+37, the root of record's forge slug), `core/cutover_root.py` (+59, `FORGE_SLUGS`,
    `root_of_record`), `dispatch_land.py` (−21 net: the in-process Doctor import is gone), `cli/config.py` (+41, the
    guarded roots), `mcp/parity.py` and `mcp/server.py` (+36, +29), `seed/errors.py` (+17), and 27
    `CAP-4: loop-home FILE read` tag lines across 18 modules (Story 115.1). No new verb and no new port; each adapter raises the port
    error its callers already map (`ForgeCommandError`; the landing's `ProcessPort`). *Instance:* accept.
13. **The test churn is splits, not new logic.** Source: `files`: marshal `tests/` +9612 −4612 over 138 files, core
    +2611 −934, kit +825 −95; the largest additions are `_live_tree` siblings
    (`test_dispatch_verification_live_tree.py` +1625, `test_chain_regen_live_tree.py` +756) whose source modules
    shrank in the same commits, and the three public-contract meta-tests (core 711, marshal 532, kit 469 lines).
    *Instance:* accept. *Prevention:* none.
14. **Three contract meta-tests, three inventories.** Source: `pyforge-marshal/tests/_support/contract_inventory.py`
    (576 lines), `pyforge-core/tests/meta/test_public_contract.py`, `pyforge-testing-kit/tests/meta/test_public_contract.py`.
    Each package half must run from its own package alone (spec-pyforge-marshal:CAP-305, spec-pyforge-core:CAP-14,
    spec-pyforge-testing-charter:CAP-7), so none may import another's helper. *Instance:* accept; the duplication is the
    price of three self-contained oracles.

### Records this change closes or carries

15. **Two old rows closed, 27 written.** Source: the deferred-work ledger after Story 116.5: `DW-FU-53-2-2` closed moot
    by design (Story 115.2 reads Doctor by subprocess), `DW-FU-4-4-2` closed for the constant (Story 115.4) and
    narrowed into `DW-marshal-115-4-3`; the change's open rows `DW-marshal-114-1-1` to `DW-marshal-118-2-1`, the
    build-time rows `DW-marshal-114-2-3`, `DW-marshal-114-3-2`, `DW-marshal-116-4-1`, `DW-marshal-117-6-3` to
    `DW-marshal-117-6-7` and `DW-marshal-117-7-1`, and `DW-marshal-cutover-2026-11-10-1`. `deferred-work-check` exits 0.
    No `DW-marshal-117-8-1` (the operator ruled the markers flip inside the PR). *Instance:* defer, each an open row by
    ruling (rulings-impact § Marshal + core-kit: "each gap is a deferred-work row").

## Behavior verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` (the package half, with the tree-read guard armed):
  exit 0; 13730 passed, 14 skipped, then 27 passed, 4 skipped.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-live-test` (the live-tree half): exit 0; 504 passed.
- `pixi run --frozen -e pyforge-core pyforge-core-test` (both halves): exit 0; package half 433 passed, 1 skipped
  (the flagd provider test, `DW-marshal-117-5-1`); live-tree half 2228 passed.
- `pixi run --frozen -e pyforge-testing-kit pyforge-testing-kit-test` (both halves): exit 0; package half 79 passed,
  live-tree half 40 passed.
- Not exercised: a dispatch landing end to end against Doctor's command (Story 115.2's tests drive it through a fake
  `ProcessPort`), a `pyforge.cutover_root` flip (operator-held, ruling R1), and the package halves from a copy outside
  the repository, which Stories 116.4 and 117.7 recorded at build.

## Previous-retro follow-through

`implementation-artifacts/sprint-status.yaml` carries no `action_items` (read 2026-11-13: zero entries), so there was
nothing to follow through on by id. The prior retro, `retro-pyforge-marshal-2026-10-25.md`, left six candidate fix
stories, not minted. None is carried by Epics 114 to 118, and none is closed by this range's diff (no change to the
verify-fix harness profile, the follow-up-review hold, the clean-clone lock check, the checkpoint re-lock,
`fr-without-cap`'s trace or the cheat-sheet environment).

## Action items

All proposed; none is applied by this retrospective.

| # | Action | Owner | Kind |
|---|---|---|---|
| 1 | Amend `spec-pyforge-marshal:CAP-305`'s guard clause to name the off-tree start (memlog change entry and render), closing `DW-marshal-116-4-1`. | marshal (next Spec story) | spec reconciliation |
| 2 | Add `_CLASSIFY_TABLE` rows for `MRS-CHAIN-005`, `MRS-PREFLIGHT-016`, `MRS-REFRESH-008` and update `contract.md`'s Verdict cells, closing `DW-marshal-114-3-2`. | marshal | remediation |
| 3 | Drop the two dead `ALLOW` entries in `test_spec_names_live_paths.py`, closing `DW-marshal-114-2-3`. | marshal | remediation |
| 4 | Let `scripts/deferred_work_intake.py --project` accept the long project slug, or mint acceptance text with the short one; a Story under the Spec that owns the script. | the script's owning Spec | tooling |
| 5 | Mint acceptance commands by running each once on the branch (`--frozen`, a baseline at the story's own parent) (finding 11). | marshal (plan mint) | process lesson |
| 6 | A fixture never rebinds a module's `__file__`; a moved test module greps its node ids first (findings 8, 9). | marshal (story authors) | process lesson |

## Acceptance verdict

**Machine verdict: rejected** (headless, criteria declared in the epics and story specs). Forced by the rubric: all 22
story keys of the five epics are not `done` in the feed (Epic summary). That is the state of record until the change's
CLOSE-LEDGERS job promotes the built keys.

On the evidence alone, the declared criteria of the built stories hold: the suites listed above pass today, the Spec's
markers say what is built (no capability reads ready), the moved paths are reconciled on the memlog for doctor Story
58.4's scoped stamp, the runtime changed only on the seams the stories named, and each gap the audit named is either
closed in this change or an open ledger row by ruling. No blocking finding stands. A human may override to
**accepted-with-open-items** once the keys are promoted; this run records no such decision.

## Open questions

- Does `DW-marshal-116-4-1`'s amendment belong to marshal's next Spec story, or should the integrator carry it in this
  PR with a second render? The build rules gave this run neither.

## Assumptions

- The epics were taken from the invocation (114 to 118), not auto-detected; `detect-epic --epic <n>` returned
  `story_count` 3, 4, 5, 8 and 2 with every key in `pending_stories` (listed in Epic summary).
- The machine verdict is **rejected** because `pending_stories` was non-empty; no human decision was available.
- The EGM drift stage (activation append step) was skipped: `pyforge.marshal.egm_retro_drift` is off
  (`flags.json` defaultVariant `off`, every overlay `off`).
- `bmad-review` was not invoked: each story had an independent review and a wave gate at build (the build commits say
  so), and the build rules of this change confine Story 116.5 to its own files. The diff-scope review ran inline over
  the story boundaries only (findings 7 to 11); the code lenses were not re-run over each hunk.
- Phase 5's `sprint_status.py update` was not run: this change writes no Tier-3 feed or ledger outside its
  CLOSE-LEDGERS job, so `epic-114-retrospective` to `epic-118-retrospective` stay `optional` and the action items above
  are recorded here only.
- The document lives at `planning-artifacts/retros/retro-pyforge-marshal-2026-11-13.md`, the path Story 116.5 names
  (the station's tracked retro home, which the chain-currency sweep reads), not the skill's default Tier-3 path.
