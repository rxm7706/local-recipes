---
title: '82.3: A landing claims only committed promotions, rejects a malformed merge template, and stamps only reconciled drift'
type: 'fix'
created: '2026-10-02'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
warnings: [oversized]
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Four landing and ledger writes claim more than they did. Re-verified at HEAD a7cdb91fe4:

- `cli/deploy.py::run_promote`: the copy loop appends each key to `promoted` (`:957`) before the batched
  `vcs.commit_paths` (`:980`); when that raises, the `except VcsCommandError` (`:981-988`) adds an `MRS-DEPLOY-003` but
  removes no key, so `data["promoted"]` and `promoted_count` (`:1091-1092`) publish an uncommitted copy as a durable
  promotion (DW-5-9-2).
- `core/policy.py::_valid_merge_subject_template` (`:1317-1320`) accepts any non-empty `str`; a template without exactly one
  `{key}` composes cleanly, then `core/identity.py::_split_template` (`:224-234`) raises a bare `ValueError` out of
  `marshal land` (`cli/land.py:970`) and `land-story` (`cli/deploy.py:2125`), both unguarded (DW-5-10-1).
- `dispatch_land.py::_reconcile_spec_surface_drift` (`:258`) reads the spec-surface verdict once (`:329`), memlogs and
  scoped-stamps the specs it names (`:521-525`), commits and pushes (`:551-556`), and returns. Doctor's verdict keeps one
  row per path (`pyforge-doctor/src/pyforge/doctor/sources/chain.py:2083-2088`, sorted by rank then spec name, `rows[0]`),
  so for a station `src/` edit only `spec-pyforge-core` is named and the station's own spec stays drifted on `main` until a
  later pass (DW-FU-53-2-3).
- `scripts/spec_surface_check.py --write-baseline --spec NAME` merges `current[name]` (`:233`), every file NAME's surface
  matches, so an unnarrated drifted file under a broad glob is absorbed as reconciled with no trace. The companion half of
  that entry, the unlocked read-modify-write, is already fixed (the flock at `:187-206`) (DW-9-1-1).

**Approach:**

- `run_promote` reports only committed keys under `promoted`; a failed commit's keys are named in its `MRS-DEPLOY-003`
  finding instead.
- `_valid_merge_subject_template` rejects a template without exactly one `{key}`, so composition reports the layer's
  rejected value with `MRS-POLICY-002` (what `_merge_field` already raises for a rejected value, `core/policy.py:2151-2160`)
  and falls back to the default template; no landing path can reach `_split_template`'s `ValueError`.
- The landing reconcile re-reads the verdict after each stamp and reconciles any further spec that names one of the
  branch's own paths, bounded by the number of specs governing those paths; drift on own paths that survives the bound is
  refused with `MRS-DISP-048`; it then commits and pushes once.
- The scoped stamp refuses, exit non-zero and baseline untouched, when NAME has a path that differs from its baseline entry
  and NAME's memlog does not name; the refusal lists each path and the explicit form that accepts it (a repeatable flag,
  such as `--accept PATH`). A spec with no baseline entry stamps as today; an unscoped stamp is unchanged.
- The stamp's tests live in the marshal package and load the script by path (the
  `tests/meta/test_fleet_picture_*.py` precedent), so the station's own suite runs them.

Ledger key: `82-3-a-landing-claims-only-committed-promotions-rejects-a-malformed-merge-template-and-stamps-only-reconciled-drift`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-4 (a spec counts as promoted only once its bytes are reachable from a ref) with Story 5.9
  (FR-186); CAP-9 with Story 5.10 (FR-187; AD-24); CAP-261 (b) with Story 53.2; CAP-235 (`--write-baseline --spec`
  settles one spec without accepting other drift). Defects of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given a promote batch whose `commit_paths` raises after every copy succeeded When the envelope is built Then `promoted` is empty, `promoted_count` is 0 and the `MRS-DEPLOY-003` finding names each uncommitted key
- Given a policy layer setting `merge_subject_template` to a string with no `{key}`, or two When the policy composes Then the value is rejected with `MRS-POLICY-002` and the default template applies, and `marshal land` and `land-story` raise no `ValueError`
- Given a branch whose station-`src/` edit drifts both `spec-pyforge-core` and the station's own spec When the landing reconcile runs Then both specs get a memlog entry and a scoped stamp before the merge
- Given own-path drift that remains after the reconcile's bound When the landing runs Then it refuses with `MRS-DISP-048`
- Given a spec with a drifted path its memlog does not name When `spec_surface_check.py --write-baseline --spec NAME` runs Then it exits non-zero, lists the path, and leaves `.spec-surface-baseline.json` byte-identical
- Given the same path accepted explicitly, or named in the memlog When the stamp runs Then it stamps NAME as today
- Given each of the four fixes reverted in turn When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Doctor's verdict stays read-only from marshal (`gather_spec_surface` is read install-free, never modified).
The stamp keeps its flock. A partial promotion is reported as partial, never as complete. Close DW-5-9-2, DW-FU-53-2-3,
DW-5-10-1 and DW-9-1-1 in `deferred-work-ledger.md` when the story lands (status `closed`, a `resolved:` line naming this
story).

**Never:** Do not edit `pyforge-doctor`'s `sources/chain.py`. Do not change the unscoped `--write-baseline` behaviour. Do
not let the landing reconcile stamp a spec whose drift names a path the branch did not touch (the foreign-drift refusal
stays). Do not change the copy step or the ledger-advance rollback in `deploy.py`.

</intent-contract>

## Code Map

Paths are under `src/shared/packages/pyforge-marshal/` (`M/`) unless rooted. Lines are at HEAD `454df87fbc`.

- `M/src/pyforge/marshal/cli/deploy.py` -- `_execute_promotion_plan` (copy loop `:933-957`, intent write `:973`, `commit_paths` `:979-988`, outcome `:989-1001`); `run_promote` publishes `data["promoted"]`/`promoted_count` (`:1091-1092`); `run_reconcile_completions` shares the helper. Fix 1 lives here. Read-only: the copy step, the lock, the ledger-advance rollback.
- `M/src/pyforge/marshal/core/policy.py` -- `_valid_merge_subject_template` (`:1317-1320`); composition via `_merge_field(...)` (`:2151-2160`) already reports a rejected layer value as `MRS-POLICY-002` and falls back to `DEFAULT_POLICY["merge_subject_template"]`. The module docstring (`:160-164`) still says the field is "validated as a non-empty `str` only, never for placeholder shape" and bars an `identity` import: rewrite that sentence; keep the no-import rule (hold the two placeholder literals locally).
- `M/src/pyforge/marshal/core/identity.py` -- read-only. `_KEY_PLACEHOLDER` (`:63`), `_SLUG_PLACEHOLDER` (`:73`), `_instantiate_slug` (`:204-221`), `_split_template` (`:224-234`) are the two bare `ValueError` sources. Callers `cli/land.py:970`, `cli/deploy.py:2125`.
- `M/src/pyforge/marshal/dispatch_land.py` -- `_reconcile_spec_surface_drift` (`:258-578`): verdict read `:328-348`, own/foreign split `:350-430`, memlog append + per-spec commit `:443-519`, one stamp `:521-547`, baseline commit + push `:548-565`, success `MRS-DISP-047` `:567-578`. Fix 3 lives here. `_SPEC_SURFACE_NAME_RE` (`:243`) stays.
- `scripts/spec_surface_check.py` -- `_stamp_baseline` (`:219-239`, `merged[name] = current[name]` at `:233`), `main` (`:242-278`), `_live_state` (`:138-178`), `_baseline_lock` (`:186-206`, keep). Fix 4 lives here; unscoped path unchanged.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:2011-2093` -- READ-ONLY reference for what "reconciled" means: the memlog hash moved since the baseline AND the memlog text contains the path (`f in named`); one row per path, a rank-0 (clean) row clears the path for every spec, otherwise the lowest `(rank, spec name)` row is the only one reported. The stamp rule mirrors this.
- Tests: `M/tests/unit/test_deploy.py:369` (`commit_raises=True` fake), `M/tests/unit/test_policy.py:2132`, `M/tests/unit/test_dispatch_landing.py:231-760` (`_install_fake_spec_surface` returns a FIXED verdict, `_ReconcileVcs`, `FakeProcess`), `M/tests/meta/test_fleet_picture_missing_spec.py:16-26` (load-a-script-by-path precedent).
- `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py:112-137` -- existing S-13.1 stamp tests; `test-ci` runs this file. `test_scoped_stamp_leaves_every_other_spec_byte_identical` stamps unnarrated drift and expects exit 0, which fix 4 now refuses.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- rows `DW-5-10-1` (`:1506`), `DW-5-9-2` (`:1613`), `DW-9-1-1` (`:1687`), `DW-FU-53-2-3` (`:7219`); closed-row shape: `status: closed` then a `resolved: <date> (marshal Story 82.3, ...)` line, as `DW-5-8-1` at `:1556-1557`.

## Tasks & Acceptance

**Execution:**
- `M/src/pyforge/marshal/cli/deploy.py` -- in `_execute_promotion_plan` collect copied keys in a local list; return (and journal in the OUTCOME entry) only keys whose `commit_paths` succeeded; the INTENT payload keeps the copied keys; a failed commit's `MRS-DEPLOY-003` message names each uncommitted key. Fix the docstring's "Returns the promoted story-key" claim -- fix 1.
- `M/src/pyforge/marshal/core/policy.py` -- `_valid_merge_subject_template` returns the value only for a `str` with exactly one `{key}` and at most one `{slug}`; rewrite the docstring sentences that say otherwise -- fix 2.
- `M/src/pyforge/marshal/dispatch_land.py` -- turn the reconcile into a bounded re-read loop per Design Notes D2; refuse with `MRS-DISP-048` when own drift survives a stamp or the post-stamp re-read fails; commit the baseline and push once -- fix 3.
- `scripts/spec_surface_check.py` -- scoped stamp refuses unreconciled paths and gains the repeatable `--accept PATH`, per Design Notes D1 -- fix 4. Update the module docstring's Usage block.
- `M/tests/unit/test_deploy.py`, `M/tests/unit/test_policy.py`, `M/tests/unit/test_dispatch_landing.py` -- extend with one new test per acceptance criterion below. Make `_install_fake_spec_surface` stateful (a spec's findings drop out once a recorded `--spec NAME` stamp call names it) and move every existing reconcile test that relied on the fixed verdict onto it; add a `settles=False` variant for the survives-the-bound case.
- `M/tests/meta/test_spec_surface_stamp.py` (new) -- loads `scripts/spec_surface_check.py` by path with `REPO_ROOT` repointed at a fixture git repo (the harness shape in `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py:82-109`); covers refusal (exit non-zero, path listed, `--accept` form named, baseline byte-identical), `--accept`, memlog-named, no-baseline-entry, and unscoped-unchanged.
- `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py` -- minimal fixture edit so the existing stamp tests narrate their drift in the spec memlog before a scoped stamp; do NOT touch the tree's CHANGELOG, `SKILL.md`, `MANIFEST.yaml` or `config/` and do NOT commit: the parent lands this file in its own `retro(cfe):` commit.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` -- close `DW-5-9-2`, `DW-FU-53-2-3`, `DW-5-10-1`, `DW-9-1-1` (`status: closed`, a `resolved:` line naming Story 82.3 and the pinning test).
- Surface reconcile -- run `python scripts/spec_surface_reconcile.py`; for every Spec it names, append an `event` memlog entry naming each governed path you changed (`python _bmad/scripts/memlog.py append --workspace <spec-folder> --type event --text "..."`). Never pass `--write-baseline`.

**Acceptance Criteria:**
- Given the contract's seven criteria, when the new tests run, then each fails with its own fix reverted and passes with it applied (revert one at a time by editing the fix out, then restore it; never `git stash`).
- Given a template with two `{slug}`, when the policy composes, then it is rejected with `MRS-POLICY-002` and the default applies (it would otherwise reach `_instantiate_slug`'s bare `ValueError`).
- Given a drifted spec whose memlog names the path but did not move since the baseline, when the scoped stamp runs, then it refuses (Doctor reads that as `drift`, not reconciled).
- Given the landing loop's gather still names a spec after that spec's stamp, when the landing runs, then it makes no second memlog append for it and refuses with `MRS-DISP-048`.

## Spec Change Log

## Design Notes

**D1 -- the stamp rule (fix 4).** Under the lock, for each distinct NAME in `--spec`, read `merged.get(NAME)`; if it is not a dict with a string `memlog`, stamp as today (no usable baseline). Otherwise a path is *reconciled* iff it is in `--accept`, or the contract hash moved (`base["memlog"] != current[NAME]["memlog"]`) AND the path occurs in NAME's current `.memlog.md` text (the file next to its `SPEC.md`; substring test, as Doctor does). A path *differs* when its baseline hash and current hash differ, or it is only on one side. If any differing path is not reconciled, write nothing, print to stderr one line per path (`NAME: PATH (changed|added|removed)`) plus the explicit form `python scripts/spec_surface_check.py --write-baseline --spec NAME --accept PATH` and "baseline untouched", and exit 1 (2 stays usage). Check every NAME before any write, so one refusal stamps none. `--accept` without `--write-baseline`, or without `--spec`, is a usage error (exit 2). Keep `_baseline_lock`, the atomic write and the unknown-spec exit 2. Why "moved AND named", not "named": a stale mention from an earlier reconcile would otherwise launder a fresh edit, which Doctor already reports as `drift`.

**D2 -- the landing loop (fix 3).** Keep the first verdict read, the `MRS-DISP-047` degrade tier and the own/foreign split. Compute `changed` once (before any landing commit) and treat the memlog files the loop appends and `scripts/.spec-surface-baseline.json` as own too, so the loop's own writes never read as foreign on a re-read. Per pass: refuse on any foreign/no-baseline spec (unchanged); refuse `MRS-DISP-048` if an own spec was already reconciled in an earlier pass (its stamp did not settle); else append + commit each own spec's memlog (unchanged text, paths merged across passes only for the final report), run ONE stamp for the pass's specs with a `--accept` for every path in `changed`, then re-read the verdict. Stop when a pass has no own spec; commit the baseline and push once; the single `MRS-DISP-047` aggregates every pass. Each pass reconciles a spec no earlier pass did and every reconciled spec governs an own path, so the loop is bounded by the number of specs governing the branch's own paths. Why `--accept`: a spec's stamp absorbs ALL its drifted paths, including paths Doctor reports under a co-governor or hides behind a clean one; every such path is narrated on some memlog, and a path the branch did not touch is not accepted, so the stamp itself refuses hidden foreign drift. A re-read that raises after a stamp is `MRS-DISP-048` (the post-stamp state is unverified).

**D3 -- the template rule (fix 2).** Literals `"{key}"`/`"{slug}"` held in `policy.py` (it must not import `identity`); a test pins them equal to `identity._KEY_PLACEHOLDER`/`_SLUG_PLACEHOLDER` and checks that every template the validator accepts renders through `identity.render_merge_subject` without `ValueError`.

**D4 -- promote (fix 1).** Golden: batch of two copied keys, `commit_paths` raises -> `promoted == []`, `promoted_count == 0`, the `MRS-DEPLOY-003` text lists both keys; a copy failure for one of three still promotes the two that committed.

## Binding

Parent: Stories 5.9, 5.10 and 53.2, `spec-pyforge-marshal` CAP-4, CAP-9, CAP-261 (b) and CAP-235; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-3-a-landing-claims-only-committed-promotions-rejects-a-malformed-merge-template-and-stamps-only-reconciled-drift`.
Ledger status at mint: `backlog`.
Deps: —.
Policy: `[epic_surfaces]` `"82"` adds `scripts/spec_surface_check.py` to the station-wide surface.
Closes: DW-5-9-2, DW-FU-53-2-3, DW-5-10-1, DW-9-1-1.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0 (ruff, `ruff format --check`, mypy over the touched packages).
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 once every governed path you changed is named on its Spec's `.memlog.md` (never `--write-baseline`).
- the conda-forge-expert stamp tests, `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py`, run with any pytest (`python -m pytest <file> -q`) — expected: pass.

## Review Triage Log

- No review has run yet.
