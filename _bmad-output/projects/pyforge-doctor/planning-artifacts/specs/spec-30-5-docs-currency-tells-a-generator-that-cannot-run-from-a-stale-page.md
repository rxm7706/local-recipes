---
title: '30.5: docs-currency tells a generator that cannot run from a stale page, and stops flagging true references'
type: 'fix'
created: '2026-10-24'
status: 'done'
baseline_revision: '0fc09c4aa3'
review_loop_iteration: 1
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
  `docs_map_render.py`). Only `scripts/docs_bmad_estate.py` (Story 30.4) exits 2 by design, when it cannot run, as
  `bmad_estate_check.run_check` does where `pyforge.scribe` is not importable; there the BMAD-estate page reads as
  hand-edited when nothing is stale. argparse also exits 2 on a usage error. The five `_docs_gen_common` generators
  have no exit-2 path: each `main()` calls `common.head_stamp`, whose git calls raise before `--check` is read, so a
  crash exits 1 with a traceback and also reads as stale.
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
1. `_check_generated_page`: exit 0 current; exit 1 the stale WARN as today, unless its output carries a Python
   traceback; any other exit, or that crash, a could-not-run WARN on the same check (`docs-currency-generated-stale`),
   worded like the existing "could not run generator" branches and naming the exit code, with the output tail in
   evidence.
2. `_is_git_ignored` in both detectors: when the page wrote the path with a trailing `/` and the plain path is not
   ignored, try it again in that slashed form. A path written without the slash is not retried, so a deleted file
   whose name a directory-only rule (`build/`) matches still reads dead.
3. `_resolves_as_identifier` in both detectors: a token also resolves when `<token>-check` is a pixi task.
4. Restore `docs/dashboard/kedro-viz/` in `github-workflows.md`; in `the-detector-framework.md`, name the sources
   `dreams-hygiene` and `bmad-output-hygiene` where Story 30.4 wrote their `-check` tasks to pass the scan.
5. Say what the could-not-run reading means: `cli_bridge.run_check_script`'s docstring and the `generated-stale`
   entry of `docs/how-to/run-and-understand-detectors.md`.
6. Close `DW-doctor-30-4-1` and `-2` with `resolution:` and `verified:` lines.

Ledger key: `30-5-docs-currency-tells-a-generator-that-cannot-run-from-a-stale-page`.
Type / Effort / Deps: fix / S / S-30.4.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-84** (documentation currency). A `fix`, so no CAP, no FR and no flag
  (`spec-feature-flag-governance` Q1). `governance-currency` changes in step because `docs_currency.py` mirrors it
  deliberately (its module docstring); neither may drift from the other.
- **Origin.** `docs/dreams/pyforge-doctor.md` Realization log, 2026-10-24 (docs-currency's two detector gaps); the
  operator's ask in session, "Do this task here: Fix docs-currency's two detector gaps (DW-doctor-30-4-1/2)".

## Acceptance Criteria

- **AC1 — Could-not-run is not stale.** A generator stub exiting 2 (and one exiting 3) yields one
  `docs-currency-generated-stale` WARN whose message says the generator could not run and names the exit; a stub that
  raises (exit 1 with a traceback) yields one could-not-run WARN saying it crashed; a plain exit 1 still yields the
  stale message; exit 0 yields none.
- **AC2 — Directory-only ignore rules.** In both detectors, an absent `docs/x/` written with its trailing slash and
  matched only by a `docs/x/` rule is not dead; the same path written without the slash, and an absent path matched by
  no rule, still are.
- **AC3 — Detector names.** In both detectors, a backticked `bmad-foo` with a pixi task `bmad-foo-check` is not dead;
  a `bmad-bar` with neither a skill, a script, a task nor a `-check` task still is.
- **AC4 — Nothing else moves.** No check name, severity, threshold or schema changes; the two detectors' resolution
  and ignore rules stay identical.
- **AC5 — The references read true.** `docs/reference/github-workflows.md` names `docs/dashboard/kedro-viz/` again,
  and the sentence Story 30.4 added to `docs/explanation/the-detector-framework.md` names the warn-only sources
  (`dreams-hygiene`, `bmad-output-hygiene`) rather than their tasks; `docs-currency` and `governance-currency`
  report no warning on the tree.
- **AC6 — Suites.** `pixi run -e pyforge-doctor pyforge-doctor-test` and `pixi run -e pyforge-ci
  pyforge-doctor-scripts-test` (the lane that runs `tests/scripts/test_governance_currency_check.py`) pass;
  `DW-doctor-30-4-1` and `-2` read `status: closed` with `resolution:` and `verified:` lines.

## Boundaries & Constraints

- Only docs-currency's three helpers (`_check_generated_page`, `_is_git_ignored`, `_resolves_as_identifier`) and the
  two governance-currency mirrors (`_is_git_ignored`, `_resolves_as_identifier`) change, with their call sites and
  tests; no other detector logic. `run_check_script` changes only in its docstring.
- Generated pages are not touched.

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-doctor` CAP-84 (a `fix`; no CAP minted).
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-24 entry.
- Epic: Epic 30, which reopens until this story is promoted (doctor Story 41.5 lets `ledger-regression` accept it).
- Ledger key: `30-5-docs-currency-tells-a-generator-that-cannot-run-from-a-stale-page`; status at mint `backlog`.
- Minted and implemented 2026-10-24 in one session; reviewed by an independent reviewer before landing.

## Verification

- `pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py -q`
  — expected: pass, with the new cases.
- `.pixi/envs/pyforge-guild/bin/python -m pytest tests/scripts/test_governance_currency_check.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources docs-currency` and
  `pixi run --frozen -e pyforge-guild governance-currency` — expected: no warning.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`; `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test`
  — expected: pass.
- `TMPDIR=$HOME/.cache/pyforge-preflight-tmp PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` —
  expected: exit 0.

## Review Triage Log

- **Review 1 (independent, read-only, against `0fc09c4aa3`..`a3e2b0bac3`): PASS**, 3 should-fix and 6 nits, all fixed
  on the branch.
  - S1, the could-not-run claim covered one generator, not six: only `scripts/docs_bmad_estate.py` exits 2, and the
    five `_docs_gen_common` generators crash with exit 1 (a traceback) before `--check` is read. Fixed: an exit 1
    whose output carries `Traceback (most recent call last)` reads could-not-run ("crashed"), with a test; the
    comments, the module docstring, the DW resolution and this spec say only `docs_bmad_estate.py` exits 2 by design;
    a correction event on the `spec-pyforge-doctor` memlog fixes the decision's wording.
  - S2, AC6 named `scripts-lib-test`, which does not list `tests/scripts/test_governance_currency_check.py`. Fixed:
    AC6, Verification and the epic name `pixi run -e pyforge-ci pyforge-doctor-scripts-test`, and its run is recorded
    below.
  - S3, the chain was dated 2026-10-25 though the work is 2026-10-24 local (and `gather_due_for_verification` flags a
    future `verified:` date). Fixed: the Dream entry, the DW `verified:` lines and this spec read 2026-10-24; the
    memlog decision, append-only, carries a correction event.
  - N4, the slash retry hid a deleted file whose name a directory-only rule matches. Fixed: both detectors retry with
    the slash only when the page wrote one; the tests judge each form alone (a shared page let the dedupe mask the
    mutant).
  - N5-N9: `governance_currency_check.py`'s module and `_resolves_as_identifier` docstrings state the derived rule;
    `run_check_script`'s docstring no longer says every non-zero exit is a result; the `generated-stale` entry of
    `docs/how-to/run-and-understand-detectors.md` describes the could-not-run reading and its fix; the Boundaries
    count the helpers per detector and the epic states AC5's wording; the new lines in `governance_currency_check.py`
    wrap at the file's width.

## Spec Change Log

- 2026-10-24: minted with Story 30.5 under Epic 30 from the Dream entry of that date.
- 2026-10-24: review 1 fixes (see the triage log): a crash reads could-not-run, the slash retry needs a written slash,
  the dates and the scripts lane corrected.

## Auto Run Result

- Worktree `.claude/worktrees/exciting-faraday-1e4549-wt-docs-currency-detector-gaps-2026-10-25`, branch
  `docs-currency-detector-gaps-2026-10-25`, from `0fc09c4aa3`.
- AC1-AC3: `test_sources_docs_currency.py` 32 passed (six new: exits 2 and 3 read could-not-run, a crash reads
  could-not-run, exit 1 still stale, a directory-only ignore rule judged in a slashed and an unslashed page, a
  `-check` task); `test_governance_currency_check.py` 9 passed (two new).
- Mutation: eight mutants, all killed — in each detector, no slash retry, an unconditional slash retry and no
  `-check` rule; in `docs-currency`, exit 2 read as stale and a crash read as stale.
- AC5: `docs-currency` exit 0 with no warning; `governance-currency` exit 0; `deferred-work-check` exit 0.
- AC6: `pixi run -e pyforge-doctor pyforge-doctor-test` exit 0 (3825 passed, 1 skipped); `pixi run -e pyforge-ci
  pyforge-doctor-scripts-test` exit 0 (823 passed, 65 skipped) after doctor's `test-architecture.md` was regenerated
  for 30.5 (the other stations' fingerprint-only drift reverted).
- `pixi run -e pyforge-guild lint-types` exit 0; `story-status-check` and `chain-currency-sweep-check` exit 0.
- Healed in passing: `spec-surface-check` read four Specs as drifted at the base — doctor's
  `spec-pixi-candidate-currency` and herald's `spec-deck-family-currency`, `spec-deck-family-lockstep` and
  `spec-pyforge-pages`. `pixi.toml` moved with atlas Story 38.1's `ca442c6f75` (a `pyforge-atlas-bootstrap` task
  edit) and none of their memlogs did. Each stamp matched `ca442c6f75`'s parent byte for byte and `pixi.toml` is the
  only path of each surface that moved, so each memlog carries a reconcile event and each Spec is stamped scoped.
- Scoped stamps: `spec-pyforge-doctor`, `spec-pyforge-core`, `spec-pyforge-marshal`, `spec-pixi-candidate-currency`,
  `spec-deck-family-currency`, `spec-deck-family-lockstep`, `spec-pyforge-pages`.
