---
title: '30.5: docs-currency tells a generator that cannot run from a stale page, and stops flagging true references'
type: 'fix'
created: '2026-10-25'
status: 'in-progress'
baseline_revision: '0fc09c4aa3'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-30-4-the-docs-dreams-and-planning-warn-backlog-is-cleared.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_currency.py
  - scripts/governance_currency_check.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `docs-currency` reports a generator that cannot run as a stale page, and its dead-reference scan (with
`governance-currency`, which shares the rules) flags two kinds of true reference as dead. Line numbers are at
`0fc09c4aa3`.

- **Generator exit codes (`DW-doctor-30-4-1`).** `_check_generated_page` (`docs_currency.py:500`-`:512`) returns no
  finding for exit 0 and the "stale against its generator -- a hand edit, or a source it derives from moved past its
  stamp" WARN for every other exit. The docs generators exit 1 when stale (`_docs_gen_common.write_generated_page`,
  `docs_map_render.py`); `scripts/docs_bmad_estate.py` (Story 30.4) exits 2 when it cannot run, as
  `bmad_estate_check.run_check` does where `pyforge.scribe` is not importable. There the BMAD-estate page reads as
  hand-edited when nothing is stale.
- **Directory-only ignore rules (`DW-doctor-30-4-2`).** `_dead_references` (`:400`-`:406`) strips a path's trailing
  `/` and then asks `git check-ignore -q <path>`. For an absent path, git cannot know it is a directory, so a
  directory-only rule never matches: `docs/dashboard/kedro-viz/` (ignored by `.gitignore:1038`, the atlas Kedro-Viz
  export staged at build time) reads as dead. `git check-ignore -q docs/dashboard/kedro-viz` exits 1;
  `git check-ignore -q docs/dashboard/kedro-viz/` exits 0. `scripts/governance_currency_check.py:207`-`:210` and its
  `_is_git_ignored` (`:164`-`:177`) do the same.
- **Detector names (`DW-doctor-30-4-2`).** A backticked `bmad-*`/`skf-*` token is dead unless it names a skill
  directory, a script or an exact pixi task or dependency (`_resolves_as_identifier`, `:353`-`:359`;
  `governance_currency_check.py:142`-`:161`). `bmad-output-hygiene` is a Doctor source whose detector task is
  `bmad-output-hygiene-check` (`pixi.toml:1539`), so it reads as a dead skill.
- **What Story 30.4 did around them.** It reworded `docs/reference/github-workflows.md`'s `docs/dashboard/kedro-viz/`
  and `docs/explanation/the-detector-framework.md`'s `bmad-output-hygiene`, and rewrote
  `docs/how-to/manage-worktrees-with-bmad.md`'s `.claude/worktrees/` as placeholder paths. `.claude/worktrees/` is
  ignored only by this machine's `.git/info/exclude` (line 120), so a fresh clone rightly reads it as absent; that
  page keeps its placeholders.

**Approach:**
1. `_check_generated_page`: exit 0 current; exit 1 the stale WARN as today; any other exit a could-not-run WARN on the
   same check (`docs-currency-generated-stale`), worded like the existing "could not run generator" branches and
   naming the exit code, with the output tail in evidence.
2. `_is_git_ignored` in both detectors: when the plain path is not ignored, try it again with a trailing `/`.
3. `_resolves_as_identifier` in both detectors: a token also resolves when `<token>-check` is a pixi task.
4. Restore `docs/dashboard/kedro-viz/` in `github-workflows.md`; in `the-detector-framework.md`, name the sources
   `dreams-hygiene` and `bmad-output-hygiene` where Story 30.4 wrote their `-check` tasks to pass the scan.
5. Close `DW-doctor-30-4-1` and `-2` with `resolution:` and `verified:` lines.

Ledger key: `30-5-docs-currency-tells-a-generator-that-cannot-run-from-a-stale-page`.
Type / Effort / Deps: fix / S / S-30.4.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-84** (documentation currency). A `fix`, so no CAP, no FR and no flag
  (`spec-feature-flag-governance` Q1). `governance-currency` changes in step because `docs_currency.py` mirrors it
  deliberately (its module docstring); neither may drift from the other.
- **Origin.** `docs/dreams/pyforge-doctor.md` Realization log, 2026-10-25 (docs-currency's two detector gaps); the
  operator's ask in session, "Do this task here: Fix docs-currency's two detector gaps (DW-doctor-30-4-1/2)".

## Acceptance Criteria

- **AC1 — Could-not-run is not stale.** A generator stub exiting 2 (and one exiting 3) yields one
  `docs-currency-generated-stale` WARN whose message says the generator could not run and names the exit; exit 1
  still yields the stale message; exit 0 yields none.
- **AC2 — Directory-only ignore rules.** In both detectors, an absent `docs/x/` matched only by a `docs/x/` rule is
  not dead; an absent path matched by no rule still is.
- **AC3 — Detector names.** In both detectors, a backticked `bmad-foo` with a pixi task `bmad-foo-check` is not dead;
  a `bmad-bar` with neither a skill, a script, a task nor a `-check` task still is.
- **AC4 — Nothing else moves.** No check name, severity, threshold or schema changes; the two detectors' resolution
  and ignore rules stay identical.
- **AC5 — The references read true.** `docs/reference/github-workflows.md` names `docs/dashboard/kedro-viz/` again,
  and the sentence Story 30.4 added to `docs/explanation/the-detector-framework.md` names the warn-only sources
  (`dreams-hygiene`, `bmad-output-hygiene`) rather than their tasks; `docs-currency` and `governance-currency`
  report no warning on the tree.
- **AC6 — Suites.** `pixi run -e pyforge-doctor pyforge-doctor-test` and `pixi run -e pyforge-guild scripts-lib-test`
  pass; `DW-doctor-30-4-1` and `-2` read `status: closed` with `resolution:` and `verified:` lines.

## Boundaries & Constraints

- Only the three helpers in each detector change, with their tests; no other detector logic.
- Generated pages are not touched.

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-doctor` CAP-84 (a `fix`; no CAP minted).
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-25 entry.
- Epic: Epic 30, which reopens until this story is promoted (doctor Story 41.5 lets `ledger-regression` accept it).
- Ledger key: `30-5-docs-currency-tells-a-generator-that-cannot-run-from-a-stale-page`; status at mint `backlog`.
- Minted and implemented 2026-10-25 in one session; reviewed by an independent reviewer before landing.

## Verification

- `pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py -q`
  — expected: pass, with the new cases.
- `.pixi/envs/pyforge-guild/bin/python -m pytest tests/scripts/test_governance_currency_check.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources docs-currency` and
  `pixi run --frozen -e pyforge-guild governance-currency` — expected: no warning.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`; `pixi run --frozen -e pyforge-guild scripts-lib-test` —
  expected: pass.
- `TMPDIR=$HOME/.cache/pyforge-preflight-tmp PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` —
  expected: exit 0.

## Spec Change Log

- 2026-10-25: minted with Story 30.5 under Epic 30 from the Dream entry of that date.

## Auto Run Result

- Worktree `.claude/worktrees/exciting-faraday-1e4549-wt-docs-currency-detector-gaps-2026-10-25`, branch
  `docs-currency-detector-gaps-2026-10-25`, from `0fc09c4aa3`.
- AC1-AC3: `test_sources_docs_currency.py` 31 passed (five new: exit 2 and 3 read could-not-run, exit 1 still stale,
  a directory-only ignore rule, a `-check` task); `test_governance_currency_check.py` 9 passed (two new).
- Mutation: undoing each of the five rule changes (the slash retry and the `-check` rule in each detector, the exit
  mapping in `docs-currency`) fails its new test; all five killed.
- AC5: `docs-currency` exit 0 with no warning; `governance-currency` exit 0.
- `pixi run -e pyforge-guild lint-types` exit 0.
