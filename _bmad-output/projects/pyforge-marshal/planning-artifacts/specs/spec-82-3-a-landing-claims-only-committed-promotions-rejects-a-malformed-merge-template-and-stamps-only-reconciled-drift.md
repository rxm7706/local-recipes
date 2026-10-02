---
title: '82.3: A landing claims only committed promotions, rejects a malformed merge template, and stamps only reconciled drift'
type: 'fix'
created: '2026-10-02'
status: 'done'
baseline_revision: '2b69320bf65ccc518adecb258d6dbeb8b2d1d387'
review_loop_iteration: 0
followup_review_recommended: false
warnings: [oversized]
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
deferred:
  - summary: >-
      Doctor reads `merge_subject_template` itself and still accepts a template marshal now rejects, so landing evidence
      may be classified against a template marshal no longer uses.
    evidence: |-
      `sources/marshal.py::_project_merge_subject_template` and `sources/ledger.py::_project_merge_subject_template` return any
      non-empty string from `marshal-policy.toml`; `pyforge.core.landing_evidence._split_template` returns None for a template
      without exactly one `{key}`, so the templated route never matches. Unverified: whether Doctor's other fallbacks recover
      the key. A Doctor fixture with a malformed template and a merge commit carrying the default subject would settle it.
      Doctor deliberately duplicates this reader, and this story's Never list excludes its `sources/chain.py`.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py:102
    severity: medium (unverified)
  - summary: >-
      `dispatch_land_finalize` decides whether the tracked spec still needs promoting from the planned Tier-3 keys, not from
      `_execute_promotion_plan`'s committed keys.
    evidence: |-
      `__main__.py:828` sets `tier3_promoted_keys` from `to_promote` and discards the helper's return value; the tracked-spec step
      at `:851` is skipped for those keys, so a failed Tier-3 commit (an `MRS-DEPLOY-003` finding) still skips it. Both lines are
      present at `454df87fbc` (Story 79.1), so this predates 82.3, whose contract names only `run_promote` and
      `run_reconcile_completions`. The fix derives the set from the helper's return and adds one failing-commit test in
      `test_dispatch_land_finalize.py`.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py:828
    severity: medium
  - summary: >-
      Doctor's `drift-presumed` remedy and AGENTS.md § Pre-PR item 5 name `--write-baseline --spec NAME` without `--accept`,
      which the scoped stamp now refuses when the memlog moved but does not name the path.
    evidence: |-
      `chain.py` tells the operator to run `--write-baseline --spec {name}` for a `drift-presumed` row; the stamp now exits 1 for
      that case unless `--accept PATH` is passed. The refusal output prints the explicit `--accept` form, so the cost is a
      misleading remedy string. The fix edits `chain.py` (excluded by this story's Never list) and AGENTS.md (an agent-context
      file).
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:2074
    severity: low
  - summary: >-
      A renamed governed file's old path is never accepted by the landing reconcile, because `changed_files` keeps only a
      rename's new path.
    evidence: |-
      `adapters/vcs_git.py` runs `git diff -M --name-status` and keeps only the new path for an `R` row, so the old (removed)
      governed path is neither in `changed` nor accepted, and the foreign-drift check already refused such a landing before this
      story. Settling the fix needs a rename source on the VcsPort or an accept rule for removed paths of the stamped spec.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py:715
    severity: low
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
- `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py` -- DO NOT EDIT. Any commit touching `.claude/skills/conda-forge-expert/` must be a `retro(cfe):` commit that also moves that skill's CHANGELOG, and an idle `wip:` checkpoint would break that. The parent updates this file's fixtures to narrate their drift in a separate `retro(cfe):` commit after you finish. Do not touch anything under `.claude/skills/conda-forge-expert/`.
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
- `python -m pytest .claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py -q` — expected: the only failure is `test_scoped_stamp_leaves_every_other_spec_byte_identical` (unnarrated drift, which fix 4 refuses); the parent fixes that fixture. Report any other failure.

## Review Triage Log

### 2026-10-02 — Review pass
- verdicts: 35 findings — high 0, medium 5, low 21, false 7, maybe-false 2
- findings:
  - `[maybe-false]` `[defer]` (Blind Hunter) Doctor's two policy readers still accept a `merge_subject_template` marshal now rejects — settling it needs a Doctor fixture with a malformed template and a merge commit carrying the default subject; Doctor duplicates the reader on purpose and `sources/chain.py` is excluded by the contract, so deferred at medium (unverified).
  - `[low]` `[defer]` (Blind Hunter) Doctor's `drift-presumed` remedy and AGENTS.md § Pre-PR item 5 omit `--accept` — real but cosmetic, since the refusal prints the explicit `--accept` form; the fix edits `chain.py` and an agent-context file, so deferred.
  - `[false]` `[reject]` (Blind Hunter) The landing's blanket `--accept` lets a path hidden behind a clean co-governor stamp with no memlog line — Doctor's own rule (`chain.py:2083-2088`, rank 0) clears such a path for every co-governor, and a path the branch did not touch is never accepted (`test_foreign_drift_the_re_read_reveals_refuses_and_pushes_nothing`).
  - `[low]` `[reject]` (Blind Hunter) One `--accept` pair per changed path grows the argv — it takes on the order of 10,000 changed files to reach the limit, and it then fails closed as `MRS-DISP-048`; the fix is a new file or stdin surface.
  - `[low]` `[reject]` (Blind Hunter) The multi-line stamp refusal text lands inside a one-line `MRS-DISP-048` — accurate text, shown only when the stamp refuses a path the landing did not accept; summarizing it is new code for a cosmetic gain.
  - `[false]` `[reject]` (Blind Hunter) The loop and the stamp are only tested against fakes — refuted by running the real `scripts/spec_surface_check.py` in a fixture repo with the landing's exact argv shape: own paths stamp (exit 0) and a path that is not accepted still refuses (exit 1).
  - `[medium]` `[patch]` (Blind Hunter) A refusal in a later pass leaves an earlier pass's stamped baseline uncommitted — verified: the baseline was committed only after the loop and a retry reads the dirty file as clean, so a stale baseline lands (the hazard the Story 53.2 B4/E2 comment guards for memlogs). Patched: the baseline is now committed right after each pass's successful stamp and the single push stays after the loop.
  - `[low]` `[reject]` (Blind Hunter) The "memlog names the path" test is a substring match and the memlog hash and text could describe different versions — the substring match is Doctor's own (`chain.py:2046`) and Design Notes D1; the race needs a concurrent memlog edit inside one stamp call.
  - `[low]` `[reject]` (Blind Hunter) `--accept` is global across `--spec` names and ignores an unmatched path — the contract asks for "a repeatable flag"; the refusal prints a per-spec command and an unmatched accept is harmless.
  - `[low]` `[reject]` (Blind Hunter) `land-story` merges with the default subject yet exits 1 — this is the contract's own behaviour (rejected value reported as `MRS-POLICY-002`, default template applies); failing closed would contradict its Approach.
  - `[low]` `[reject]` (Blind Hunter) `run_reconcile_completions` has no failed-commit test — it calls the same helper the new `run_promote` tests cover; an open INTENT journal entry after a failed commit is the story's existing I/O matrix.
  - `[low]` `[reject]` (Blind Hunter) The story spec's CFE "DO NOT EDIT" and "only failure is…" lines are stale — the parent changed that file in a separate `retro(cfe):` commit, as the spec said it would; the fix would edit this build's spec.
  - `[low]` `[reject]` (Blind Hunter) The CHANGELOG says the other six tests are unchanged although the shared lock helper also changed `test_full_stamp_blocks_while_lock_held` — true and cosmetic; correcting it needs another `retro(cfe):` commit.
  - `[low]` `[reject]` (Blind Hunter) Gaps in `test_spec_surface_stamp.py` (a text assertion a comment satisfies, no sentinel/exempt or missing-`files` case, `parents[6]`) — `StampRefused` is also asserted by attribute, the extra cases are outside the acceptance criteria, and `parents[6]` follows the `test_fleet_picture_*` precedent the spec cites.
  - `[false]` `[reject]` (Blind Hunter) A reconciled spec that reappears with a path outside the branch's own set is called foreign drift instead of "did not settle" — that path really is foreign drift, so the message is correct.
  - `[low]` `[reject]` (Edge Case Hunter) The post-stamp re-read's `except` never fires for real crashes, because `gather_spec_surface` turns an exception into a WARN finding (`degrade_on_exception`) — verified, but a crashed re-read lands exactly as the pre-change single read did, so it is no regression; a Doctor crash is unlikely and the guard is new branching.
  - `[medium]` `[patch]` (Edge Case Hunter) Pass-2 refusal leaves the stamped baseline uncommitted — same root cause as the Blind Hunter row above; patched by the per-pass baseline commit.
  - `[low]` `[defer]` (Edge Case Hunter) `changed_files` keeps only a rename's new path, so a renamed governed file's old path is never accepted — verified in `adapters/vcs_git.py`; the foreign check refused it before this story, so it predates it.
  - `[low]` `[reject]` (Edge Case Hunter) `execute_dispatch_land` renders from its template parameter unguarded — the parameter comes from composed policy through the supervisor spawn, which now validates it; only a supervisor spawned before this change with a malformed template could reach it.
  - `[low]` `[reject]` (Edge Case Hunter) A rejected template is an ERROR yet the merge proceeds, unlike `_MALFORMED_LANDING_KEYS` — the contract chose the fallback (see the `land-story` row).
  - `[low]` `[reject]` (Edge Case Hunter) A baseline entry with a string `memlog` but no `files` makes every governed path read as added — Doctor reads it the same way (`b_files` falls back to `{}`), the refusal prints the remedy, and only a hand-edited baseline reaches it.
  - `[low]` `[reject]` (Edge Case Hunter) Global `--accept` across specs — same as the Blind Hunter row.
  - `[low]` `[reject]` (Edge Case Hunter) Memlog hash and text read at different moments — same as the Blind Hunter row.
  - `[low]` `[reject]` (Edge Case Hunter) A changed path starting with `-` breaks `--accept <path>` and spaces break the printed remedy — repo-relative git paths almost never start with `-`, and `--accept=PATH` would change every test's argv parsing.
  - `[maybe-false]` `[defer]` (Verification Gap) Doctor's readers accept a malformed template — same as the first Blind Hunter row; recorded once in `deferred`.
  - `[medium]` `[defer]` (Verification Gap) `dispatch_land_finalize/__main__.py:828` derives `tier3_promoted_keys` from the planned set, so a failed Tier-3 commit still skips the tracked-spec promotion — verified at `:828` and `:851`; both predate this story (present at `454df87fbc`, Story 79.1) and the contract names only `run_promote` and `run_reconcile_completions`.
  - `[medium]` `[patch]` (Verification Gap) The refusal-after-a-stamp state is untested — same root cause as the Blind Hunter row; the patch also adds the asked-for assertions (the two refusal tests now check the baseline commit exists before the refusal).
  - `[low]` `[defer]` (Verification Gap) Doctor's `drift-presumed` remedy text — same as the second Blind Hunter row.
  - `[low]` `[reject]` (Intent Alignment) The loop tests use a fake Doctor and a recording process — the file's pattern since Story 53.2; the real verdict is tested in Doctor's suite and the real-script check passed.
  - `[false]` `[reject]` (Intent Alignment) Inside the landing the `--accept` set exempts own paths from the refusal — intended (Design Notes D2); only paths outside the branch's own set trip it, as the real-script check shows.
  - `[low]` `[reject]` (Intent Alignment) Fix 1 changes the shared helper but only `run_promote` is tested — see the `run_reconcile_completions` row.
  - `[false]` `[reject]` (Intent Alignment) Fix 2 is wider than "exactly one `{key}`" (two `{slug}`, `MRS-POLICY-002` for every composed-policy consumer, exit 1 on land) — `identity._instantiate_slug` raises `ValueError` for two `{slug}`, so the "no landing path can reach the `ValueError`" criterion needs it; the verdict follows from the contract's `MRS-POLICY-002`.
  - `[medium]` `[patch]` (Intent Alignment) A later-pass refusal can leave local state behind — same root cause as the Blind Hunter row; its other listed divergences (widened own-path set, no loop counter, per-memlog commits, argv size) are Design Notes D2 or covered above.
  - `[false]` `[reject]` (Intent Alignment) AC6's "named in the memlog" is implemented as "memlog moved AND names it" — that is Doctor's clean-pass bar and "stamps NAME as today"; a mention in an unmoved memlog is what Doctor reports as `drift`.
  - `[false]` `[reject]` (Intent Alignment) The mutation counts were unconfirmed — settled by reverting each fix in turn and running its tests: all four fail (fix 1 `test_deploy.py`, fix 2 `test_policy.py`, fix 3 landing tests, fix 4 `test_spec_surface_stamp.py`), each file restored byte-identical.

## Auto Run Result

Status: done

**Summary of the implemented change.** The four defects are fixed and each has its own test:
- `run_promote` and `run_reconcile_completions` publish `promoted` and `promoted_count` only for keys whose batched `commit_paths` returned; a failed commit leaves them empty and its `MRS-DEPLOY-003` finding names each uncommitted key.
- A `merge_subject_template` must carry exactly one `{key}` and at most one `{slug}`; anything else is rejected with `MRS-POLICY-002` and the default applies, so `marshal land` and `land-story` no longer reach `identity`'s bare `ValueError`.
- The landing reconcile is a bounded loop that re-reads the spec-surface verdict after each stamp and reconciles any further spec naming one of the branch's own paths. Own drift that survives its spec's stamp, or foreign drift revealed on a re-read, refuses with `MRS-DISP-048`. Each pass commits its memlogs and its stamped baseline as it goes, and the branch is pushed once after the loop.
- `scripts/spec_surface_check.py --write-baseline --spec NAME` refuses (exit 1, baseline untouched) a path that differs from NAME's baseline entry unless it is passed with the new `--accept PATH` or NAME's memlog moved since the baseline and names it; a spec with no baseline entry and the unscoped stamp are unchanged, and the flock is kept.
- Closed `DW-5-9-2`, `DW-FU-53-2-3`, `DW-5-10-1` and `DW-9-1-1` in `deferred-work-ledger.md`.

**Files changed.**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py` -- promote reports committed keys only.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` and `schemas/policy.json` -- the template shape rule and its description.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` -- the bounded reconcile loop with a per-pass baseline commit.
- `scripts/spec_surface_check.py` -- the scoped-stamp refusal and `--accept`.
- `src/shared/packages/pyforge-marshal/tests/meta/test_spec_surface_stamp.py` (new) and `tests/unit/test_deploy.py`, `test_policy.py`, `test_land.py`, `test_dispatch_landing.py`, `test_drain_plan.py` -- one or more tests per acceptance criterion; `test_drain_plan.py` keeps its `MRS-DISP-019` render-guard test by injecting an unvalidated template.
- `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py` plus `SKILL.md`, `CHANGELOG.md`, `MANIFEST.yaml`, `config/skill-config.yaml` (v8.91.2) -- four existing stamp tests now name their drift on the spec memlog first; landed in the separate `retro(cfe):` commit `3080feca16`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md`, the memlogs of `spec-pyforge-marshal`, `spec-pyforge-core`, `spec-quick-dev-reconciliation`, `spec-surface-drift-reconciliation` (marshal project) and `spec-conda-forge-expert-rebuild`, `spec-packaging-factory` (mason project) -- surface reconcile entries naming each governed path.

**Review findings.** Four layers reported 35 findings: high 0, medium 5, low 21, false 7, maybe-false 2.
- Patches applied: one grouped medium entry (four rows, one root cause). A refusal in a later reconcile pass left an earlier pass's stamped baseline uncommitted, so a retry could land a stale baseline. The baseline is now committed right after each pass's stamp, and two refusal tests assert it.
- Deferred (4 entries in frontmatter `deferred:`): Doctor's two merge-template readers (medium, unverified); `dispatch_land_finalize`'s `tier3_promoted_keys` (medium, predates this story); Doctor's `drift-presumed` remedy and AGENTS.md wording (low); a rename's old path never accepted (low, predates this story).
- Rejected (25): each with its reason in the triage log above. The ones worth naming are the blanket `--accept` in the landing (Doctor's own co-governor rule and the foreign-path refusal cover it), the "only tested against fakes" claim (refuted with a real-script run), the post-stamp re-read that cannot raise (no regression from the old single read), `land-story` merging with the default subject (the contract's chosen behaviour), and the mutation-count doubt (settled by reverting each fix).
- Follow-up review recommended: false. One medium entry was patched and none was high.

**Verification performed.** After the patch, all by exit code:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 9870 passed, 1 skipped.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 130 passed, 3 skipped.
- `pixi run --frozen -e pyforge-guild lint-types` -- exit 0.
- `python scripts/spec_surface_reconcile.py` -- exit 0; no `--write-baseline` was run.
- `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py` -- 10 passed.
- AC7 mutation: reverting each fix in turn fails its own tests (fix 1 in `test_deploy.py`, fix 2 in `test_policy.py`, fix 3 in `test_dispatch_landing.py`, fix 4 in `test_spec_surface_stamp.py`), each file restored byte-identical.
- The real `spec_surface_check.py` accepts the landing's exact `--accept` argv for own paths and still refuses a path that is not accepted.
- `branch_diff_guard.unsanctioned_commits` for the CFE tree returns an empty list.

**Residual risks.** Not run: `pr-preflight` as a whole, the touched-module coverage floors, and the sprint ledger and its Tier-3 feed (this run does not write them). Doctor can still classify landing evidence against a malformed template that marshal ignores (deferred, unverified). A crashed post-stamp re-read reads as no drift, as the old single read did. A branch changing more than roughly 10,000 files could exceed the argv limit on the stamp and would then refuse.
