---
title: '123.2: One steward module names this root''s layout and repository, and prove-landed reads doctor through its command'
type: 'feature'
created: '2026-11-10'
status: 'done'
flag-exempt: detector-or-gate
difficulty: medium
story: 123.2
spec: pyforge-steward
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/root_layout.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/corridor.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/measures.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/bootstrap.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/marketplace_pages.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py
  - src/shared/packages/pyforge-steward/tests/meta/test_portability.py
  - src/shared/packages/pyforge-steward/tests/unit/test_upgrade_prove_landed.py
context:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Real defects the audit found: hard-coded roots and an in-process import of another station, where the grammar is the only contract between stations.

**Approach:** A refactor with a gate. Steward's four identity sites (`steward ci`'s default repository, `bootstrap --url`'s default, the marketplace URL, the owner) are this checkout's identity, not the root of record: one constant each in `root_layout.py`, listed in contract.md as estate-bound, and none follows a flip (operator ruling 2026-11-10 on question 5). No module starts reading `pyforge.cutover_root`.

Ledger key: `123-2-one-steward-module-names-this-root-s-layout-and-repository-and-prove-landed-reads-doctor-through-its-command`. Type / Effort / Deps: feature / M / S-121.2, S-123.3.

### Living CAP citations

- **`spec-pyforge-steward` CAP-182** — one module names this root's layout and repository, and a test holds the rest of steward's source to it; minted 2026-11-10 `(ready 2026-11-10)` and rendered at mint. Works with `spec-pyforge-core:CAP-13` (`root_of_record()`, `LOCAL_DEV_RELATIVE`).

## Boundaries & Constraints

**Always:**
- Keep every value identical on A.
- Keep `root_layout.py` to assignments: no function and no import of a steward module.

**Never:**
- Never edit `src/platform/ingest/github_projects/pipeline.py` (the src/platform import guard; DW-steward-74-1 holds the private import).
- Never edit session.py or test_session.py (Story 123.3's).
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — the portability test passes.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_portability.py -q
  ```
- **AC2 — the test can fire.** Expected: exit 0 with at least 4 tests selected (a planted path constant, a planted slug, a planted cross-station import, an exception entry that no longer applies).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_portability.py -q -k fires
  ```
- **AC3 — no path constant outside the one module.** Expected: exit 1 (no match); docstrings and comments use backticks and are not matched, which is what CAP-182 says.
  ```bash
  git grep -nE "[\"']src/shared/packages" -- src/shared/packages/pyforge-steward/src/pyforge/steward ':(exclude)src/shared/packages/pyforge-steward/src/pyforge/steward/root_layout.py'
  ```
- **AC4 — no slug outside the one module.** Expected: exit 1 (no match).
  ```bash
  git grep -n 'rxm7706' -- src/shared/packages/pyforge-steward/src/pyforge/steward ':(exclude)src/shared/packages/pyforge-steward/src/pyforge/steward/root_layout.py'
  ```
- **AC5 — no cross-station import remains (session.py's left with Story 123.3, operator ruling 2026-11-10).** Expected: exit 1 (no match).
  ```bash
  git grep -nE 'from pyforge\.(doctor|marshal|herald|scribe|mason|atlas|warden)|import pyforge\.(doctor|marshal|herald|scribe|mason|atlas|warden)' -- src/shared/packages/pyforge-steward/src/pyforge/steward
  ```
- **AC6 — the values are unchanged.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src python -c "from pyforge.steward import catalog,corridor,measures,ci,workspace,root_layout as r;from pyforge.core.cutover_root import LOCAL_DEV_RELATIVE as L;assert str(catalog.CATALOG_RELATIVE)=='src/shared/packages/pyforge-steward/catalog';assert str(corridor.CORRIDOR_RELATIVE).endswith('pyforge-steward/corridor');assert str(measures.MEASURES_RELATIVE).endswith('pyforge-steward/measures');assert ci.DEFAULT_REPO=='rxm7706/local-recipes';assert catalog.PUBLIC_MARKETPLACE_GIT_URL=='https://github.com/rxm7706/local-recipes.git';assert workspace.default_flags_path()==workspace.repo_root()/L"
  ```
- **AC7 — prove-landed keeps its verdict.** Expected: exit 0: `run_bmad_drift_integrity` takes exit 0 as pass, 1 as findings and 2 as could-not-run from `pixi run --frozen -e pyforge-guild bmad-drift-check` through the stubbed command runner; test_session.py is not edited by this story (Story 123.3 owns it).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_upgrade_prove_landed.py src/shared/packages/pyforge-steward/tests/unit/test_session.py -q
  ```
- **AC8 — no new subprocess call site and no builtin-rooted exception.** Expected: prints 0 (BASE is the `baseline_revision` in this story's spec frontmatter; core-kit Story 117.1 pins both counts).
  ```bash
  git diff "$BASE"..HEAD -- src/shared/packages/pyforge-steward/src/pyforge/steward | grep -cE '^\+.*(subprocess\.(run|Popen|check_)|class [A-Za-z]+\((Exception|ValueError|RuntimeError|OSError|TypeError|KeyError|LookupError)\))'
  ```
- **AC9 — src/platform is not touched.** Expected: prints 0.
  ```bash
  git diff --name-only "$BASE"..HEAD -- src/platform | wc -l
  ```
- **AC10 — coverage floor on touched modules.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-coverage-gate
  ```
- **AC11 — package half.** Expected: exit 0 (until Story 124.2 lands, steward's package half runs without test_station_tests_trigger_map.py, which reds on other units' new reads by design; 124.2 restores the full `pyforge-steward-test`).
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta -q -m "not slow and not live_tree" -n auto --dist loadgroup -p no:cacheprovider --ignore=src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py --cov=pyforge.steward --cov-branch --cov-report=json:.steward/coverage/steward-unit.json
  ```
- **AC12 — live-tree half.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```
- **AC13 — lint and types.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild lint-types
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-182

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 123.
- Ledger key: `123-2-one-steward-module-names-this-root-s-layout-and-repository-and-prove-landed-reads-doctor-through-its-command` (`backlog` at mint).
- Deps: S-121.2, S-123.3.
- Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/root_layout.py` (new), `src/shared/packages/pyforge-steward/src/pyforge/steward/corridor.py, measures.py, catalog.py, preflight_ci.py, upgrade.py, workspace.py, ci.py, bootstrap.py, marketplace_pages.py and sync.py`, `src/shared/packages/pyforge-steward/tests/meta/test_portability.py` (new), `src/shared/packages/pyforge-steward/tests/unit/test_upgrade_prove_landed.py`.
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_portability.py -q` — expected: exit 0.
- `pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_portability.py -q -k fires` — expected: exit 0 with at least 4 tests selected (a planted path constant, a planted slug, a planted cross-station import, an exception entry that no longer applies).

## Notes

- Cross-station: marshal:S-117.2 (core-kit) publishes `root_of_record()` and `LOCAL_DEV_RELATIVE` first; steward does not consume `root_of_record()` (its identity sites are this checkout's).
- Operator ruling 2026-11-10 (Story 123.3): `steward session check` finding (2) takes `bmad-drift-check`'s verdict everywhere, so session.py's `pyforge.doctor` import leaves with Story 123.3 and this story's exception list is empty; the plan's session.py exception is superseded. Hence the dependency on 123.3.
- control-plane 121.2 drops cutover.py's path literals with the apply code; if any remains, this story moves it.
- `$BASE` in the acceptance criteria is the `baseline_revision` the build writes into this spec's frontmatter when it starts (the commit it starts from); it is not set at mint.
- Until Story 124.2 lands, steward's trigger-map test may red on other units' new reads (a planned red window); this story is judged by its own test modules and by steward's package half without that module.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (steward and host: Story 122.5) and doctor Story 58.4 runs every scoped stamp once, after the last edit.

## Planned deferral (written at build)

Two of the three deferrals below are rows the cutover-readiness plan already reserves; Steward's closer story
(Story 122.5) writes those to `planning-artifacts/deferred-work-ledger.md`, and this story asks for no second row
for either. The third is new at build. Station deferred-work rows are written at build, never at mint, and none
goes into this spec's `deferred:` frontmatter before its ledger twin exists (`deferred-work-check` refuses one).

- **`DW-steward-cutover-2026-11-10-7`** (reserved; low; location
  `src/shared/packages/pyforge-steward/src/pyforge/steward/bootstrap.py:84-94`, lines 85-95 after this story's
  import line): steward still needs a checkout to run. `repo_root()` finds the checkout by walking up to its `scripts/bmad-loop-worktree` sentinel, and `catalog.py`,
  `corridor.py` and `measures.py` read data directories (`catalog/`, `corridor/` and `measures/` under
  `root_layout.STEWARD_PACKAGE_DIR`) that the wheel does not carry. Story 123.2 moved the paths into `root_layout.py`
  and changed no value; Story 122.2 lists both facts in `contract.md` as estate-bound. Changing where the data lives
  changes behaviour on A, which this story forbids.
- **`DW-steward-cutover-2026-11-10-3`** (reserved; low; under `DW-steward-74-1`; location
  `src/platform/ingest/github_projects/pipeline.py:11-12`): the host still imports the private
  `pyforge.steward.sync._default_transport`. `sync.py` now names the same function `default_transport`, so closing the
  row is a one-line import change in the host, which needs the src/platform import guard to carry the carve-out
  list first; this story may not edit the host.
- **`DW-steward-123-2-2`** (new at build; low; location
  `src/shared/packages/pyforge-steward/src/pyforge/steward/five_tier.py:70`, with
  `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_suite_reduction.py:194`): two steward modules
  still spell the station-packages directory out one segment at a time (`repo_root / "src" / "shared" / "packages"`),
  so spec-pyforge-steward:CAP-182's "every other module derives from it" is not yet true and the capability is not
  met until this row closes. Neither file is in this story's files_owned and no story of the cutover-readiness plan
  owns either, so the build could not move them (a named blocker: file ownership in a parallel wave). The gate now
  sees the form: `test_portability.py` reports a segment run in any steward module and names these two in
  `LAYOUT_EXCEPTIONS` under this id, and the test fails when either entry no longer applies, so the fix (derive both
  from `root_layout.STATION_PACKAGES_DIR`) must delete the entries in the same change. Preferred close: the
  orchestrator adds both files to this story's files_owned and a later round moves them, which drops the exceptions
  and this row. Otherwise the steward closer writes the row; its id is outside Story 122.5's
  `DW-steward-cutover-2026-11-10-<n>` count, so that count stays 12. (`DW-steward-123-2-1`, named by the first
  attempt, is withdrawn as a duplicate of `DW-steward-cutover-2026-11-10-7` and is not reused with a second meaning.)

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the first build attempt. Each finding, where it is, the problem, and what this round
did. `$BASE` for AC8 and AC9 is `1c9cb4ade3ba259ca99923df295303f2afadde45` (HEAD when the build started, the
`build(steward): 121.2 (BUILD-4)` commit); this story may not write the spec frontmatter, so the wave gate or the
orchestrator records it there as `baseline_revision`.

1. **Major — `five_tier.py:70`, `preflight_suite_reduction.py:194`, `test_portability.py` (`root_literals`).** Two
   steward modules still name where station packages live as Path segments (`repo_root / "src" / "shared" /
   "packages"`), contradicting spec-pyforge-steward:CAP-182 and FR-56, and the scan could not see that form (a
   mutant `_MARSHAL_PKG = Path("src") / "shared" / "packages" / "pyforge-marshal"` in `upgrade.py` passed, and
   `test_each_moved_site...` compared it with `==`). Neither file is in files_owned and no story owns them.
   **Done:** the scan now reports a run of the segments `src`, `shared`, `packages` spread over more than one
   operand of a `/` or `+` chain, a `Path(...)`/`os.path.join(...)` call, an f-string or a tuple or list (`fires`
   cases for each form, the reviewer's mutant among them); `upgrade._MARSHAL_PKG` is asserted to be
   `root_layout.MARSHAL_PACKAGE_DIR` by identity. The two files cannot be edited here, so they are named in
   `LAYOUT_EXCEPTIONS` under `DW-steward-123-2-2` (§ Planned deferral) and the test reds when an entry no longer
   applies. The reviewer's preferred fix (add both files to files_owned) is the orchestrator's call; it is reported.
2. **Major — § Planned deferral.** `DW-steward-123-2-1` duplicated the reserved `DW-steward-cutover-2026-11-10-7`
   (the sentinel and the data directories outside the wheel), and the section left out the reserved
   `DW-steward-cutover-2026-11-10-3` for the host's private-import switch. **Done:** the section cites both reserved
   ids, drops `DW-steward-123-2-1` and its request to Story 122.5, and adds only the genuinely new
   `DW-steward-123-2-2` (finding 1).
3. **Minor — `test_upgrade_prove_landed.py::_make_doctor_importable`.** The fake `pyforge.doctor.models` had no
   `DoctorStatus`, so restored in-process code fell back to the subprocess on `ImportError` and the
   `doctor-importable` case passed. **Done:** the fake models module carries a `DoctorStatus` enum, so an in-process
   read reaches `factory.gather` and `pytest.fail` fires; re-checked by restoring the old branch on a scratch copy.
   The gate also reports an `import_module`/`__import__` whose module name is not a string literal, and a relative
   import that climbs out of `pyforge.steward` into another station (`fires` cases), so a computed or relative name
   no longer gets past the scan.
4. **Minor — spec frontmatter `baseline_revision`.** Not written. **Done:** `$BASE` is stated above; the frontmatter
   write is left to the wave gate or orchestrator (this story edits only its spec's body sections).
5. **Minor — `session.py:127-133` (Story 123.3's file).** `_bmad_method_finding`'s docstring still says it runs the
   subprocess `run_bmad_drift_integrity` runs "when `pyforge.doctor` is not importable"; after this story that
   function always runs it. **Not fixed here:** session.py is Story 123.3's; reported to the orchestrator for 123.3's
   owner or the steward closer to drop the clause.
6. **Minor — AC10, AC12, AC13.** Red for reasons outside this story (the coverage gate's dependency on the full
   `pyforge-steward-test` before Story 124.2, a concurrent marshal rename that the live half's case list reads, and
   pyforge-marshal's lint). **No change in 123.2:** re-run at the wave gate after Story 124.2 and the marshal rename
   settle; each steward leg is reported in the build notes. Round 2 (2026-11-11): AC13 now exits 0. AC12 still
   reds only on `test_cutover_case_list.py`'s two cases naming the moved marshal module. AC10's gate step, judged
   with `--paths-file` over this story's 11 modules and the reports its own dependency run wrote, prints
   `coverage gate OK for pyforge-steward unit: 11 module(s) ≥ 80%`; the literal task reds on its dependency
   `pyforge-steward-test` (the trigger-map module before Story 124.2, and the case below).
7. **Found in round 2, outside this story — AC11.** `test_deploy_nic_packs.py::test_run_nic_up_refuses_a_missing_pack_cli_before_nic_starts[off]`
   fails whenever it is the first test in its process to read a flag: `pyforge.core.flags.read_boolean`'s first
   call installs the flagd provider over the `flag_provider` fixture's in-memory one, so the `off` case reads the
   real tree's `on`. It fails alone (`pytest <that id>`, exit 1) and on origin/main's steward, core and
   testing-kit source too, and passes after its `on` case. Under `-n auto` it reds AC11 whenever the scheduler puts
   it first on a worker that has read no flag, which this story's added tests make more likely without touching
   it (the full package half without them: exit 0). Neither file is this story's; reported to the orchestrator
   for an owner.

No acceptance command was changed in this round: the reviewer named none as wrong.
