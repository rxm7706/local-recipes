---
title: 'pyforge-mason — Retrospective (2026-11-12: Epics 37 to 39, the cutover readiness change)'
project: pyforge-mason
created: '2026-11-12'
updated: '2026-11-12'
epics: [37, 38, 39]
date: '2026-11-12'
verdict: rejected
criteria: declared
headless: true
scope: 'Epics 37, 38 and 39 of the single cutover-readiness PR (branch cutover-readiness-2026-11-10): the Spec, PRD and package say what is built (Epic 37), the oracle travels (Epic 38), the factory-island seam (Epic 39). Written by bmad-retrospective, headless, as Story 37.4 step (1). The package pyproject.toml moved on 2026-11-11 (e455948f1f, Story 38.2), so this is the code->retro retrospective the chain-currency sweep owes.'
evidence:
  - 'range ec233e46d7^..HEAD on cutover-readiness-2026-11-10 (HEAD d2951f07fd at the time of reading): 43 commits, 0 merges; scripts/git_evidence.py output kept in the build scratch folder'
  - 'story commits: ffe1438da1 (37.3, 38.1, 38.3, 39.1), 7c17b13f03 (deferred twins for 38.3 and 39.1), e455948f1f (38.2), 839fc04c9f (37.1), 22d63ea328 (37.2); the mint ec233e46d7'
  - 'pixi run --frozen -e pyforge-mason pyforge-mason-test: exit 0, 1693 passed, 73 deselected (2026-11-12)'
  - 'pixi run --frozen -e pyforge-mason pyforge-mason-live-test: exit 0, 73 + 2 + 12 passed (2026-11-12)'
---

# pyforge-mason — Retrospective, Epics 37 to 39 (2026-11-12)

## Epic summary

- **Epics:** 37 (*The mason Spec, PRD and package say what is built*), 38 (*Mason's oracle travels*), 39 (*Mason's
  cutover seam*), all minted 2026-11-10 in `ec233e46d7` from the station Dream's entry of that date
  (`docs/dreams/pyforge-mason.md`, Realization log, *2026-11-10 (the cutover readiness audit)*) and the operator rulings
  of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization log).
- **Diff range:** `ec233e46d7^..HEAD` (the mint's parent through the last mason build commit `22d63ea328` and the
  later non-mason waves). 43 commits, no merges (`merge_count` 0, `merges_measured` 0), no binary revisions on a mason path.
- **Stories built and reviewed on the branch:** 37.1 (`839fc04c9f`), 37.2 (`22d63ea328`), 37.3, 38.1, 38.3 and 39.1
  (`ffe1438da1`, twins `7c17b13f03`), 38.2 (`e455948f1f`). Each build commit says the story passed an independent
  review and the wave gate.
- **Stories not `done` in the feed** (`sprint_status.py detect-epic --epic <n>` on
  `implementation-artifacts/sprint-status.yaml`, 2026-11-12): Epic 37: 37-1, 37-2, 37-3, 37-4; Epic 38: 38-1, 38-2,
  38-3; Epic 39: 39-1, 39-2. The tracked ledger reads the same (`sprint-status-ledger.yaml` lines 127-135: blocked or
  backlog). Every built key is promoted by the change's CLOSE-LEDGERS job, after this retro; 37.4 is the story writing
  this document; 39.2 is minted `blocked` until the root of record flips (operator ruling 2026-11-10) and never runs in
  this change.
- **Evidence inventory.** Available: the epics and story specs (`planning-artifacts/epics.md` lines 3993-4183;
  `planning-artifacts/specs/spec-37-*` to `spec-39-*`), the per-story commits, the story specs' review and gate
  records (38.2 § Review findings rounds 1-2 and § Build round 3; 38.3 and 39.1 § Gate findings), the Spec memlog,
  both test halves run today. Missing: session logs of the build agents (not kept in the tree), so process lessons
  come from the review and gate records the story specs carry, nothing else.

## Findings

Each finding carries its source and two dispositions: this instance (fix now / defer / accept), and what prevents the
next one.

### Spec-to-implementation reconciliation

1. **Story 37.1's planned deferral cannot reach 37.1's own frontmatter.** Source:
   `spec-37-1-the-mason-spec-defines-each-capability-once-and-marks-it-as-it-stands.md` AC11 (expects the
   `airgap-contract-key-guard-is-dead` row in its frontmatter `deferred:`) and § Planned deferral (written at build)
   (asks Story 37.4 to write the row there); Story 37.4's `files_owned` in the plan names no 37.1 file, and the build
   rules forbid editing another story's spec. *Instance:* defer: Story 37.4 writes the ledger twin with the fingerprint
   37.1's Notes give the row (summary plus `airgap_contract.py:71`), so a later frontmatter row dedupes against it;
   the frontmatter edit is an integrator's call. *Prevention:* a deferral row a build may not write in its own
   frontmatter is written by the closer only if the closer's `files_owned` names the spec; mint it so.
2. **`spec-pyforge-mason`'s `companions:` comments trail the reviewed chain.** Source: `SPEC.md` frontmatter
   `companions:` (`FR-1..FR-50 / NFR-1..NFR-16 / D-1..D-13` for the PRD, `AD-1..AD-16 + AD-25/AD-26` for the spine)
   against the PRD at FR-1..FR-64 and the spine with AD-27 and AD-28 after Story 37.2 (`22d63ea328`); recorded in
   `spec-37-2-...` § Planned deferral. *Instance:* defer, ledger row through Story 37.4; the next re-derive restates both
   ranges. *Prevention:* none beyond the re-derive; no capability, surface or criterion reads the comments.
3. **The kernel stayed as built.** Source: the only `src/` change of the three epics is `resolve.py` (+14 −6: one
   leading `./` stripped instead of a run of dots and slashes; the unresolved-root error stops naming a
   `--foundry-root` flag that never existed) plus help and docstring text in `cli.py` (2 lines) and `models.py`
   (1 line); `pyproject.toml` gains the `live_tree` marker; `pixi.toml` moves the Python floor to 3.14 (decision D6).
   No new import edge, no new verb, no flag, matching Epic 37's HARD boundaries (`epics.md` lines 4002-4010).
   *Instance:* accept.

### Story boundaries (diff-scope review, inline)

4. **A guard in one story found its siblings' defect, and the fix needed a third review round.** Source:
   `spec-38-2-mason-s-suite-runs-as-a-package-half-and-a-live-tree-half.md` § Review findings rounds 1 and 2 and
   § Spec Change Log *fix round 3*: Story 38.2's import-time check reported `tests/meta/test_public_contract.py:54`
   (Story 38.1) and `tests/meta/test_cfe_adapter_argv_live.py:49` (Story 38.3) deriving the repository root at import,
   which stops collection of the whole package half outside the repository; neither sibling's spec carried the
   obligation and both reviews had finished. Resolved by widening 38.2's `files_owned` for those two modules
   (`e455948f1f`). *Instance:* fixed; today the package half passes (1693 passed) and the out-of-tree copy passed in
   round 3 (`spec-38-2` § Build round 3, AC4). *Prevention:* a wave that writes `live_tree` test modules states the
   import rule at mint; the build rules of this change now say it ("never derives the repository root at import time").
5. **Deferral twins lagged their rows by eight waves until the orchestrator moved the intake.** Source:
   `spec-38-3-...` § Gate findings and `spec-39-1-...` § Gate findings (`deferred-work-check` exit 2,
   `spec-frontmatter-only-deferral`, 2026-11-11, "stays red at each wave gate until 37.4 lands"), closed early by
   `7c17b13f03` (*deferred twins for 38.3 and 39.1*). *Instance:* fixed. *Prevention:* a story that writes a frontmatter
   `deferred:` row runs the intake in its own wave, or records the row in its body (§ Planned deferral) for the closer,
   as 37.1 and 37.2 did; never a frontmatter row with no twin across a gate.
6. **A literal acceptance command re-locked `pixi.lock`.** Source: `spec-38-2-...` § Build round 3, AC9 bullet: the
   command had no `--frozen`, the wave's path-dependency manifests (Story 37.3's `pixi.toml` floor, Story 38.2's
   `pyproject.toml`) no longer match the lock's hashes, and the run rewrote `pixi.lock`; the file was restored and AC9
   re-run with `--frozen`. *Instance:* fixed in round 3; the lock regeneration stays steward Story 124.3's.
   *Prevention:* acceptance commands minted on a branch that edits a path-dependency manifest carry `--frozen`.

### Aggregate views

7. **Three new meta-tests of 530 to 570 lines.** Source: `git_evidence.py` `files`: `test_cfe_adapter_argv_live.py`
   net +566, `test_live_tree_split.py` +546, `test_public_contract.py` +533; `wc -l` today 566, 546, 533. Read: each is
   one oracle with its planted cases (38.2's guard plants each root-derivation form marked and unmarked; 38.1's test
   walks every parser path; 38.3's reads each wrapped script's declared options). *Instance:* accept; size follows the
   number of forms each oracle refuses, not accreted logic. *Prevention:* none.
8. **Duplication: one root-derivation shape, three spellings.** Source: the `_load_guard()` shape in
   `tests/unit/test_cfe_rebuild_guard_merges.py`, `_repo_root()` in `test_cfe_adapter_argv_live.py`, and
   `_repo_root()` / `_contract()` / `_mcp_asgi()` / `_assertion_client()` in `test_public_contract.py` (38.2 § Spec
   Change Log fix round 3). Each module keeps its own helper on purpose: a shared helper imported from another module
   is a call form the split guard does not follow (38.2 § Spec Change Log fix round 2). *Instance:* accept.
9. **The mypy baseline on `pyforge.mason.cli` stays.** Source: `spec-38-2-...` § Spec Change Log (the 2026-11-11 mypy
   record: 6 errors, `assignment` at cli.py 1335, 1462, 1533, 1571, 1628 and `attr-defined` at 1637), and
   `pyproject.toml`'s override `disable_error_code = ["assignment", "attr-defined"]`. Story 37.3 touched `cli.py` (help
   text only) and both codes still fire. *Instance:* defer: typing the dispatch's result variable is a code change no
   story of this change carries (operator ruling 2026-11-10: no new behaviour in this PR). *Prevention:* none new; the
   ratchet rule in `AGENTS.md` (tighten when you touch the module) applies to the next code story on `cli.py`.

### Records this change closes or carries

10. **Story 5.4's first spec read blocked beside a `done` ledger key.** Source: the 2026-11-10 audit
    (`planning-artifacts/research/cutover-readiness-audit-2026-11-10.md` line 53, § SHOULD RECHECK, *Stories*),
    `spec-5-4-free-inheritance-verification.md` (`status: 'blocked'`) against
    `spec-5-4-free-inheritance-verification-2.md` (`status: 'done'`) and the ledger key `5-4-free-inheritance-verification: done`.
    *Instance:* fix now, in Story 37.4 (the first spec reads `superseded`, pointing at the recheck).
11. **`DW-mason-25-2-3` sat open beside a campaign the Spec records as closed.** Source: the audit (line 55, § SHOULD RECHECK,
    *Deferred work*); the ledger entry (`status: open`, the 92-recipe Track B queue, the G53 audit and the Rule-2 retro) against the
    eight batch stories that ran it (merges `26992240c4`, `96c64771f0`, `ab9e52789b`, `2095e94e43`, `32344834ec`,
    `a46fd89638`, `1dfc9cca86`, `90456f9c6c`, each run-results table carrying a G53 maintainers column and each batch
    its `retro(cfe):` commit) and Stories 25.18 (`c806b74707`) and 25.19 (`6d52ea19c3`). *Instance:* fix now, in Story
    37.4 (judged on that evidence). The drift since the batches is its own open row, `DW-mason-25-18`.
12. **Open rows this change carries, by ruling.** Source: the ledger twins written in `7c17b13f03` and the rows Story
    37.4 writes: the nine wrapped scripts with a static check only (Story 38.3), the Docker island build that builds
    nothing from the island (39.1), the ship and submit root that does not follow the root of record (39.1, waits on
    steward Stories 44.8 and 44.9), no kill switch for Mason's runtime capabilities (39.1), the dead air-gap key guard
    (37.1), the companions comments (37.2), the untriaged open mason deferrals and the two `-2` story-spec names (37.4).
    *Instance:* defer, each an open ledger row; none is a blocker for these epics' criteria (operator rulings
    2026-11-10, rulings-impact § Mason: "each gap is a deferred row").

## Behavior verification

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` (the package half): exit 0, 1693 passed, 73 deselected.
- `pixi run --frozen -e pyforge-mason pyforge-mason-live-test` (the live-tree half, the non-unit tests and CFE's
  CLI-tool parity test): exit 0, 73 passed, then 2, then 12.
- `mason recipe update --help`: the help now says the update writes the field-scoped change by default and that
  `--dry-run` computes and shows the plan without writing (spec-pyforge-mason:CAP-2 as amended; Story 37.3).
- `mason --format json recipe build factory/recipes/nonexistent-37-4-probe` with no `MASON_FOUNDRY_ROOT`, from the
  worktree root (no `factory/` directory): exit 1, `factory:missing-island`, and the message names only
  `MASON_FOUNDRY_ROOT` and the upward walk, never a `--foundry-root` flag (spec-pyforge-mason:CAP-36; Story 39.1).
- Not exercised: a real factory-island build (needs a python-foundry clone with `factory/pixi.toml` and
  `factory/pixi.lock`), and the out-of-tree copy run, which Story 38.2's round 3 recorded (§ Build round 3, AC4).

## Previous-retro follow-through

`implementation-artifacts/sprint-status.yaml` carries no `action_items` (read 2026-11-12: zero entries), so there was
nothing to follow through on by id. The prior retro, `retro-pyforge-mason-2026-09-20.md`, left two carry-forward notes
and no tracked items: run `lint-types` before pushing (the wave gates run it; 38.2 § Build round 3, AC9), and drop an
`unused-ignore` when seen (no instance in this range's diff).

## Action items

All proposed; none is applied by this retrospective.

| # | Action | Owner | Kind |
|---|---|---|---|
| 1 | Write the `airgap-contract-key-guard-is-dead` row into Story 37.1's frontmatter `deferred:` with the summary and location its Notes give, so its AC11 reads it; the ledger twin Story 37.4 writes dedupes it at intake. | change integrator | spec reconciliation |
| 2 | Restate the PRD and spine ranges in `spec-pyforge-mason`'s `companions:` comments at the next re-derive (the 37.2 row). | mason (next re-derive) | spec reconciliation |
| 3 | Mint each later plan's `live_tree` test modules with the import rule, and give a closer the `files_owned` for every row it is asked to write (findings 1, 4, 5). | marshal (plan mint) | process lesson |
| 4 | Mint acceptance commands with `--frozen` on any branch that edits a path-dependency manifest (finding 6). | marshal (plan mint) | process lesson |
| 5 | Type the dispatch result in `cli.py` and drop the `assignment` and `attr-defined` override, in the next code Story on `cli.py`. | mason | remediation |

## Acceptance verdict

**Machine verdict: rejected** (headless, criteria declared in the epics and story specs). Forced by the rubric:
nine story keys of the three epics are not `done` in the feed (Epic summary). That is the state of record until the
change's CLOSE-LEDGERS job promotes the built keys; 39.2 stays `blocked` by ruling until the flip.

On the evidence alone, the declared criteria of the seven built stories hold: both test halves pass today, the help
and the error say what the code does, the kernel changed only where the stories said, and each gap the audit named is
either closed in this change or an open ledger row by ruling. No blocking finding stands. A human may override to
**accepted-with-open-items** once the keys are promoted; this run records no such decision.

## Open questions

- Should Story 37.1's frontmatter row be written by the integrator (action 1), or should 37.1's AC11 be read from the
  ledger twin instead? Either answer closes the gap; the build rules allowed neither to this run.

## Assumptions

- The epics were taken from the invocation (37, 38 and 39), not auto-detected; `detect-epic --epic <n>` returned
  `story_count` 4, 3 and 2 with every key in `pending_stories` (listed in Epic summary).
- The machine verdict is **rejected** because `pending_stories` was non-empty; no human decision was available.
- `bmad-review` was not invoked: each story had an independent review and a wave gate at build (the build commits
  say so), and the build rules of this change confine Story 37.4 to its own files. The diff-scope review ran inline over
  the story boundaries only (findings 4 to 6); the code lenses were not re-run over each hunk.
- Phase 5's `sprint_status.py update` was not run: this change writes no Tier-3 feed or ledger outside its
  CLOSE-LEDGERS job, so `epic-37-retrospective`, `epic-38-retrospective` and `epic-39-retrospective` stay as they are
  and the action items above are recorded here only.
- The document lives at `planning-artifacts/retros/retro-pyforge-mason-2026-11-12.md`, the path Story 37.4 names (the
  station's tracked retro home, which the chain-currency sweep reads), not the skill's default Tier-3 path.
