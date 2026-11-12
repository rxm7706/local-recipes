---
title: '124.1: Every suite that marked its live-tree readers has its two task halves'
type: 'feature'
created: '2026-11-10'
status: 'backlog'
flag-exempt: detector-or-gate
difficulty: medium
story: 124.1
spec: pyforge-steward
surface:
  - pixi.toml
  - environment.yaml
  - docs/how-to/pixi-tasks.md
  - docs/reference/environments.md
  - docs/map.yaml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight.py
  - src/shared/packages/pyforge-steward/tests/meta/test_preflight_docs_site_lanes.py
  - src/shared/packages/pyforge-testing-kit/tests/meta/test_testing_kit_lane_wired.py
  - src/shared/packages/pyforge-herald/tests/meta/test_built_site_tests_install_first.py
context:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
declared_low_risk: false
baseline_revision: 'b6f53ebcf807'
---

<intent-contract>

## Intent

**Problem:** Decision D2: completing what CAP-175 and Story 117.4 specify for every suite. `pixi.toml` has one owner, so the descriptions other units found wrong are corrected here too.

**Approach:** Each dependency is the story that marks that suite's outside readers `live_tree`; a package half that still reads outside its package reds steward's trigger-map test, so marking lands first. 124.1 and 124.2 land back to back; this story runs each new task directly and leaves steward's suite and the aggregate to 124.2. A station whose marking story did not land keeps its one task and gets a deferred row. Add the `writer-lock-check` task doctor Story 56.5 hands to this story (`pixi.toml` has one owner): `[feature.guild-tasks.tasks.writer-lock-check]` with `cmd = "python -m pyforge.doctor.sources writer-lock"` and a description citing spec-pyforge-doctor:CAP-100 and doctor Story 56.5, on the shape of `capability-ledger-check` and `frozen-path-changed-check`; until it lands, doctor's registry test (`tests/scripts/test_detectors_doctor_sources.py::test_every_doctor_source_task_is_a_pixi_task_running_its_own_source`) is red on the branch. The regenerated `docs/how-to/pixi-tasks.md` follows (AC7).

Ledger key: `124-1-every-suite-that-marked-its-live-tree-readers-has-its-two-task-halves`. Type / Effort / Deps: feature / M / S-121.4.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** (FR-49) — each station suite runs once, as its package-local and live-tree halves.

## Boundaries & Constraints

**Always:**
- Move `environment.yaml` only through `pixi run --frozen -e pyforge-steward pyforge steward estate reconcile`.
- Label the PR `maintenance`.

**Never:**
- Never move a dependency or run `pixi update`.
- Never move atlas's seven gate tasks (DW-atlas-46-1-4 stands: atlas Story 46.1 writes it, and its body names the plan's working id DW-atlas-cutover-2026-11-10-4).
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — each landed station has both halves, and each half selects by the marker (corrected by the integrator ruling).** Expected: exit 0; prints `[]`, with STATIONS="atlas herald marshal mason scribe warden core testing-kit" less any station whose marking story did not land (that station gets a deferred row and keeps its one task). For core and the testing kit the package half is `pyforge-<s>-package-test` and `pyforge-<s>-test` is the cmd-less `depends-on` aggregate of both halves.
  ```bash
  python3 -c "import tomllib,sys;f=tomllib.load(open('pixi.toml','rb'))['feature'];bad=[];K=('core','testing-kit')
  for s in sys.argv[1:]:
   t=f[f'pyforge-{s}']['tasks'];w=t.get(f'pyforge-{s}-test') or {};b=t.get(f'pyforge-{s}-live-test') or {};a=(t.get(f'pyforge-{s}-package-test') or {}) if s in K else w
   legs={d if isinstance(d,str) else d['task'] for d in w.get('depends-on',[])}
   whole=s not in K or ('cmd' not in w and legs=={f'pyforge-{s}-package-test',f'pyforge-{s}-live-test'})
   if not a or not b or 'not live_tree' not in a.get('cmd','') or 'live_tree' not in b.get('cmd','') or 'not live_tree' in b['cmd'].split('&&')[0] or not whole: bad.append(s)
  print(bad);sys.exit(bool(bad))" $STATIONS
  ```
- **AC2 — no half is empty and both pass.** Expected: exit 0 (pytest's 'no tests collected' exit 5 is a failure).
  ```bash
  for s in $STATIONS; do pixi run --frozen -e pyforge-$s pyforge-$s-test && pixi run --frozen -e pyforge-$s pyforge-$s-live-test || exit 1; done
  ```
- **AC3 — the aggregate names every new task (corrected by the integrator ruling).** Expected: exit 0; prints `[]`. For core and the kit the aggregate names the whole-suite task, whose `depends-on` AC1 proves holds the live half.
  ```bash
  python3 -c "import tomllib,sys;d=tomllib.load(open('pixi.toml','rb'));t={k:v for f in d['feature'].values() for k,v in f.get('tasks',{}).items()};a=str(t['pyforge-station-tests']);m=[s for s in sys.argv[1:] if (f'pyforge-{s}-test' if s in ('core','testing-kit') else f'pyforge-{s}-live-test') not in a];print(m);sys.exit(bool(m))" $STATIONS
  ```
- **AC4 — the kit's package half runs without the host on its path (corrected by the integrator ruling).** Expected: prints `False True`.
  ```bash
  python3 -c "import tomllib;t=tomllib.load(open('pixi.toml','rb'))['feature']['pyforge-testing-kit']['tasks'];print('django-pyforge' in str(t['pyforge-testing-kit-package-test'].get('env','')), 'django-pyforge' in str(t['pyforge-testing-kit-live-test'].get('env','')))"
  ```
- **AC5 — the three wrong comments are gone.** Expected: prints 0.
  ```bash
  grep -cE 'unit \+ conformance \+ meta|pgvector/pgvector:pg16|docs/specs/pyforge-warden\.md' pixi.toml
  ```
- **AC6 — the two ledger detector descriptions say what the detectors read.** Expected: prints 0.
  ```bash
  grep -cE 'manifest\.\{yaml,yml,json\}' pixi.toml
  ```
- **AC7 — the generated pages follow.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild python scripts/docs_pixi_tasks.py --check && pixi run --frozen -e pyforge-guild python scripts/docs_environments.py --check && pixi run --frozen -e pyforge-guild docs-currency-check
  ```
- **AC8 — environment.yaml is in sync.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild pyforge steward provision --verify
  ```
- **AC9 — the library catalog still matches.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild llms-full-check
  ```
- **AC10 — the lock is not this story's.** Expected: prints 0 (BASE is the `baseline_revision` in this story's spec frontmatter; task edits move no dependency, and Story 124.3 re-locks once for the floors).
  ```bash
  git diff --name-only "$BASE"..HEAD -- pixi.lock | wc -l
  ```
- **AC11 — doctor's writer-lock task runs and names this checkout the writer.** Expected: exit 0; stdout contains `is the writer`.
  ```bash
  pixi run --frozen -e pyforge-guild writer-lock-check
  ```
- **AC12 — the `writer-lock-check` task exists, runs doctor's source and satisfies doctor's task registry.** Expected: prints `python -m pyforge.doctor.sources writer-lock`, then exit 0.
  ```bash
  python3 -c "import tomllib,sys;t=tomllib.load(open('pixi.toml','rb'))['feature']['guild-tasks']['tasks'].get('writer-lock-check') or {};print(t.get('cmd'));d=t.get('description','');sys.exit(0 if t.get('cmd')=='python -m pyforge.doctor.sources writer-lock' and 'CAP-100' in d and '56.5' in d else 1)" && pixi run --frozen -e pyforge-doctor pyforge-doctor-aggregate-scripts-test
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-175 (FR-49)

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 124.
- Ledger key: `124-1-every-suite-that-marked-its-live-tree-readers-has-its-two-task-halves` (`backlog` at mint).
- Deps: S-121.4.
- Surface: `pixi.toml`, `environment.yaml` (only through `pyforge steward estate reconcile`), `docs/how-to/pixi-tasks.md` (regenerated), `docs/reference/environments.md` (regenerated), `docs/map.yaml` (the `stamp:` mappings of how-to/pixi-tasks.md and reference/environments.md only).
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `for s in $STATIONS; do pixi run --frozen -e pyforge-$s pyforge-$s-test && pixi run --frozen -e pyforge-$s pyforge-$s-live-test || exit 1; done` — expected: exit 0 (pytest's 'no tests collected' exit 5 is a failure).

## Notes

- Cross-station deps (each station's marking story, and doctor's tasks): warden:S-27.1, scribe:S-33.1, mason:S-38.2, atlas:S-48.1, herald:S-52.1, doctor:S-56.1, doctor:S-56.2, doctor:S-56.5, marshal:S-116.1, marshal:S-116.2, marshal:S-116.3, marshal:S-116.4, marshal:S-117.1, marshal:S-117.7, marshal:S-118.1; same-station: control-plane 121.4.
- Doctor's request (doctor:S-56.5, spec-pyforge-doctor:CAP-100): the `writer-lock-check` pixi task is this story's, not doctor's; doctor 56.5 registers `("writer-lock", "writer-lock-check")` in `_DOCTOR_SOURCE_TASKS` and runs its source module directly until this lands (AC11, AC12).
- Atlas's request: the seven atlas gate tasks stay in `-e local-recipes`; the deferral is DW-atlas-46-1-4 (atlas Story 46.1), whose body carries the plan's working id DW-atlas-cutover-2026-11-10-4.
- Descriptions and comments: `frozen-path-changed-check` reads the capability ledger's rebuilding rows (doctor 56.1), `capability-ledger-check` names orphan rows, heading drift and judged expiries (doctor 56.2); pixi.toml:640 drops 'conformance'; :2752 names warden's live Spec folder; :3069 says pg17.
- `$BASE` in the acceptance criteria is the `baseline_revision` the build writes into this spec's frontmatter when it starts (the commit it starts from); it is not set at mint.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (steward and host: Story 122.5) and doctor Story 58.4 runs every scoped stamp once, after the last edit.

## Planned deferral (written at build)

None. The integrator ruling of 2026-11-11 (§ Integrator ruling) dropped both rows the earlier rounds wrote:
`DW-steward-124-1-1` (core and the testing kit are split here, in the aggregate shape) and `DW-steward-124-1-2`
(herald's `pyforge-herald-test-built` and `pyforge-herald-coverage-gate` depend on both halves here). Atlas, herald,
marshal, mason, scribe, warden, pyforge-core and the testing kit are all split as this story says, so no station keeps
its one task and steward's closer story (Story 122.5) writes no ledger row for this story.

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the first build. Each finding is listed with its severity, where it sits and the
problem, followed by what this round did. Findings 1 to 3 cannot be closed inside this story's files (`pixi.toml`,
`environment.yaml`, the two generated pages, the two `docs/map.yaml` stamp mappings), so they go to the integrator
or the operator. The reviewer did not call any acceptance command wrong, so the AC block is unchanged.

1. **Blocker: core and the testing kit are not split.** Where: `pixi.toml`
   `[feature.pyforge-core.tasks.pyforge-core-test]` and `[feature.pyforge-testing-kit.tasks.pyforge-testing-kit-test]`;
   § Planned deferral, `DW-steward-124-1-1`. Problem: with the full STATIONS, AC1 and AC3 print
   `['core', 'testing-kit']` and exit 1, and AC4 raises `KeyError: 'pyforge-testing-kit-live-test'`. The story lets a
   station stay unsplit only when its marking story did not land. Marshal:S-117.1, marshal:S-117.7 and
   marshal:S-118.1 all landed, so the deferral is outside what the story allows, and it names no later story.
   This round: re-verified, and not fixable in this story's files. Core's `pixi_leg_problems` and
   `lane_halves_problems` (`tests/meta/test_conformance_lane_wired.py`) and the kit's `leg_problems`
   (`tests/meta/test_testing_kit_lane_wired.py`) require `pyforge-core-test` and `pyforge-testing-kit-test` to stay
   the whole suite: either one command, or a `depends-on` aggregate of both halves. AC1's shape gives each task a
   package-half `cmd`, which contradicts that. The core-kit plan asked this story for the aggregate shape
   (`pyforge-core-package-test`, `pyforge-core-live-test`, and `pyforge-core-test` as a cmd-less aggregate; the same
   for the kit). That shape fails AC1 (no `cmd`) and AC4. It also reds steward's
   `tests/unit/test_preflight.py::test_real_pixi_lists_every_leaf_once`, which asserts the lane
   `("pyforge-core-test", "pyforge-core")`, and the kit's `_split_pixi`, which reads `whole["cmd"]`. One more shape
   would pass both sets of checks as written: `pyforge-core-test` keeps a package-half `cmd` and also lists the live
   half under `depends-on`. This round rejects it. Running that task runs both halves, so it is not a package half;
   it would satisfy AC1's text but not what AC1 checks. None of those test files belongs to this story, so the
   reviewer's fix applies: the integrator or the operator rules on one shape.
   (a) Keep AC1's shape: a story that owns core's `test_conformance_lane_wired.py` and the kit's
   `test_testing_kit_lane_wired.py` amends `pixi_leg_problems` and `leg_problems`, along with core's
   `_split_pixi_data` and the kit's `_split_pixi`. (b) Take the core-kit aggregate shape: a memlog line amends this
   story's AC1, AC3 and AC4, and steward's `test_preflight.py` and the kit's `_split_pixi` go to a story.
   Under either ruling, this story then splits core and the kit, and steward:S-124.2 adds `core-live-test` and
   `testing-kit-live-test`. Until the ruling, the story is blocked, not done.
2. **Blocker: herald's live half is a docs-site task that the preflight does not list.** Where:
   `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py` `DOCS_SITE_TASKS` (no story owns it) and
   `src/shared/packages/pyforge-steward/tests/meta/test_preflight_docs_site_lanes.py`. Problem: steward's derivation
   classes `pyforge-herald-live-test` as a docs-site task, because it runs herald's built-site tests and those call
   `astro_build`. `DOCS_SITE_TASKS` does not name it, so `test_the_declared_set_is_exactly_the_derived_set` and
   `test_a_build_through_a_docs_site_script_is_seen_without_its_install_dependency` go red. Steward's live half and
   steward:S-124.2's AC13 stay red with them. This round: reproduced both failures (missing
   `['pyforge-herald-live-test']`). It cannot be fixed in this story's files. The task cannot honestly escape the
   classification either: it really does run `astro build` in `docs-site/`. Escalated: the integrator assigns
   `preflight.py` to a story, with steward:S-124.2 as the natural owner. That story adds
   `"pyforge-herald-live-test"` to `DOCS_SITE_TASKS`, so the herald live lane takes the docs-site mutex beside
   `npm ci`.
3. **Major: herald's built-site tests left CI's strict run.** Where: `pixi.toml`
   `[feature.pyforge-herald.tasks.pyforge-herald-test-built]` and `[feature.pyforge-herald.tasks.pyforge-herald-coverage-gate]`;
   § Planned deferral, `DW-steward-124-1-2`. Problem: the plan notes say `pyforge-herald-test-built` depends on the
   install and both halves. It still depends only on `[docs-site-install, pyforge-herald-test]`, because herald's
   `tests/meta/test_built_site_tests_install_first.py` pins the list. The built-site tests are now live-tree
   modules, so CI's herald job, which runs `pyforge-herald-test-built` with `HERALD_DOCS_SITE_REQUIRED=1`, no
   longer runs them. Herald Story 45.1's rule that a missing install fails and never skips is lost in CI.
   Steward:S-124.2's spec never names `HERALD_DOCS_SITE_REQUIRED` or the `site` environment. A second point: the
   herald gate merges `herald-live*.json` but depends only on the package half, so in pr-preflight it can read a
   stale live report or none at all. This round: re-verified the pins
   (`test_the_built_task_installs_then_runs_the_suite` and `test_the_coverage_gate_takes_no_install_dependency`
   assert the lists exactly). The pin is herald's and steward:S-124.2's spec is not this story's, so it cannot be
   fixed here. Escalated with a ruling request: a herald story changes the pin to admit the live half; this story
   then makes `pyforge-herald-test-built` depend on the install and both halves, and the gate on both halves; and
   steward:S-124.2's spec is amended (a memlog line, then a re-derive) so its `herald-live-test` job sets up the
   `site` environment, runs the install and sets `HERALD_DOCS_SITE_REQUIRED=1`.
4. **Minor: the gate commands open a red window until steward:S-124.2.** Where: AC2 (herald's live half), herald's
   `tests/meta/test_preflight_pages_lane.py`, and steward's `tests/unit/test_preflight_ci.py` and
   `tests/unit/test_preflight_selection.py`. Problem: each of the six split stations' gate commands now carries
   `--report ".steward/coverage/<s>-live*.json"`. No CI gate step carries it yet, so the preflight refuses with exit
   2 ("no CI step runs pyforge-<s>-coverage-gate ... refusing the run"). This round: by design, since this story
   and steward:S-124.2 land back to back. Reproduced: 4 tests red in `test_preflight_ci.py` and 18 in
   `test_preflight_selection.py`. Note for the integrator to carry into steward:S-124.2: each split station's CI gate
   step must carry the string that station's gate `cmd` carries in `pixi.toml`, `--report
   ".steward/coverage/<s>-live*.json"` (a double-quoted glob, after the unit report), for atlas, herald, marshal,
   mason, scribe and warden. After steward:S-124.2, re-run herald's `test_preflight_pages_lane.py` and steward's
   `test_preflight_ci.py`.
5. **Minor: AC9 is red on a `tornado` ghost entry.** Where: `docs/reference/library-llms-full.md`. Problem: the
   failure is already present at HEAD (atlas commit a9349acaff dropped `tornado`). This story's diff does not touch
   `tornado`, and the catalog belongs to scribe:S-31.4. This round: no change here; re-run AC9 after scribe:S-31.4
   regenerates the catalog.
6. **Minor: there was no `baseline_revision`, so AC10 ran with an empty BASE.** Where: the frontmatter and AC10.
   This round: fixed. `baseline_revision: 'b6f53ebcf807'` is in the frontmatter, and the status is untouched. AC10
   prints 0 against it.
7. **Minor: scribe's live half fails `test_spec_not_behind_memlog`.** Where: AC2 (scribe's live half). Problem: the
   cause is outside this story. `spec-pyforge-steward` has not been re-derived since the event steward Story 122.2
   appended, and `spec_behind_memlog_known.json` carries stale marshal rows. This round: reproduced
   (1 failed, 162 passed). No change here; it closes with steward:S-122.5's re-derive and marshal's closer.

## Review findings (build, round 2, 2026-11-11)

A second independent review failed the round-1 fix. It reports round-1 findings 1 to 3 as still open and adds
three minors. Each finding below gives its severity, where it sits and the problem, then what this round did.
The reviewer agrees that findings 1 to 3 cannot be closed in this story's files: "the integrator or the operator
picks one shape", and `preflight.py`, herald's pin and steward:S-124.2's spec belong to other stories. The
reviewer did not call any acceptance command wrong and gave no corrected form, so the oracle rule does not apply.
The AC block and `plan.json` `stories[124.1].acceptance` are unchanged.

1. **Blocker: core and the testing kit are not split** (round-1 finding 1, still open). Where: `pixi.toml`
   `[feature.pyforge-core.tasks.pyforge-core-test]` and `[feature.pyforge-testing-kit.tasks.pyforge-testing-kit-test]`;
   § Planned deferral, `DW-steward-124-1-1`. Problem: with the full STATIONS, AC1 and AC3 print
   `['core', 'testing-kit']` and exit 1, AC4 raises `KeyError: 'pyforge-testing-kit-live-test'`, and AC2 cannot
   pass because `pyforge-core-live-test` and `pyforge-testing-kit-live-test` do not exist. Marshal:S-117.1,
   marshal:S-117.7 and marshal:S-118.1 are in `built_so_far`, so `DW-steward-124-1-1` is not a deferral this story
   permits. The contradiction is real. The core-kit plan asks for the aggregate shape, and core's
   `pixi_leg_problems` and the kit's `leg_problems` require the task to stay the whole suite. AC1 and AC4 require
   a package-half `cmd`, and steward's `test_preflight.py:81` asserts the lane `("pyforge-core-test", "pyforge-core")`.
   No ruling exists in `rulings-impact.md` or `plan.json`.
   This round: re-verified against the guards as they stand. No shape passes every check:
   - **AC1's shape:** `pyforge-core-test` gets a package-half `cmd` and no `depends-on`. Core's
     `pixi_leg_problems` reds it ("drops the live-tree half").
   - **The aggregate shape:** `pyforge-core-test` becomes a cmd-less `depends-on`. AC1 fails, because there is no
     `cmd`. Steward's `test_real_pixi_lists_every_leaf_once` also reds: its fixture shows a cmd-less aggregate is
     expanded to its leaves, so the asserted lane disappears.
   - **The hollow shape:** a package-half `cmd` plus `depends-on` the live half. It still fails core's guard as
     well as its intent: `_split_pixi_data` keeps the real data once `depends-on` exists, and `_split_halves`
     then finds no package-only leg, so `test_the_split_wiring_is_accepted` errors.

   One fact for the ruling that the round-1 text did not cite: both kernel Specs already state the aggregate
   shape. `spec-pyforge-core`'s memlog amends spec-pyforge-core:CAP-8 (2026-11-10) so that "pyforge-core-test
   stays the whole suite". Marshal Story 118.1's spec says "`pyforge-testing-kit-test` stays the whole suite."
   As written for core and the kit, AC1 and AC4 contradict two ready Spec capabilities, which points to ruling (b).
   This story cannot take ruling (b) alone. The reviewer named no corrected command, so the oracle rule does not
   apply. Ruling (b) also needs steward's `tests/unit/test_preflight.py` and the kit's `_split_pixi` changed by a
   story that owns them. Escalated unchanged; the story stays blocked on the ruling. Once a ruling lands, this
   story splits core and the kit in the chosen shape and drops `DW-steward-124-1-1`. Steward:S-124.2 adds
   `core-live-test` and `testing-kit-live-test`.
2. **Blocker: `pyforge-herald-live-test` is a docs-site task the preflight does not list** (round-1 finding 2,
   still open). Where: `src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py` `DOCS_SITE_TASKS`
   (lines 97 to 108), and steward's `tests/meta/test_preflight_docs_site_lanes.py`. Problem: the live half runs
   herald's built-site tests, which run `astro build` in `docs-site/`. `test_the_declared_set_is_exactly_the_derived_set`
   and `test_a_build_through_a_docs_site_script_is_seen_without_its_install_dependency` fail on the extra item
   `pyforge-herald-live-test`. No story's `files_owned` names `preflight.py`, including steward:S-124.2's, so the
   red has no contracted owner. Without the entry, the herald live lane runs without the docs-site mutex beside
   `npm ci`. This round: reproduced (see the results below). The fix is outside this story's files, and the task
   cannot honestly escape the class: it does build in `docs-site/`. Escalated: the integrator assigns `preflight.py`
   to a story, steward:S-124.2 being the natural owner, through a memlog amendment of that story's `files_owned`
   and spec. That story adds `"pyforge-herald-live-test"` to `DOCS_SITE_TASKS`.
3. **Major: herald's built-site tests left CI's strict run** (round-1 finding 3, still open). Where: `pixi.toml`
   `[feature.pyforge-herald.tasks.pyforge-herald-test-built]` and `[feature.pyforge-herald.tasks.pyforge-herald-coverage-gate]`;
   herald's `tests/meta/test_built_site_tests_install_first.py`; `DW-steward-124-1-2`. Problem:
   `pyforge-herald-test-built` still depends on `[docs-site-install, pyforge-herald-test]` while the built-site
   tests are live-tree modules. CI's herald job, run with `HERALD_DOCS_SITE_REQUIRED=1`, therefore no longer
   reaches them, and herald Story 45.1's rule (a missing install fails) is lost in CI. The herald gate merges
   `herald-live*.json` but depends only on the package half, so pr-preflight can read a stale live report or none.
   Steward:S-124.2's spec does not name `HERALD_DOCS_SITE_REQUIRED` or the `site` environment. This round:
   re-verified the pins. `test_the_built_task_installs_then_runs_the_suite` asserts
   `depends-on == [INSTALL, SUITE]`. `test_the_coverage_gate_takes_no_install_dependency` asserts
   `depends-on == [SUITE]`. `test_ci_s_herald_job_runs_the_built_task_strictly_with_the_site_environment` pins
   CI's one run step. Each pin reds the fix this story would make, and none of those files is this story's.
   Escalated: a herald story amends the pin to admit the live half. This story then makes
   `pyforge-herald-test-built` depend on the install and both halves, and the gate on both halves. Steward:S-124.2's
   spec is amended by memlog so its `herald-live-test` job sets up the `site` environment, runs the install and sets
   `HERALD_DOCS_SITE_REQUIRED=1`.
4. **Minor: the gate commands open a red window until steward:S-124.2.** Where: the coverage-gate `cmd` of atlas,
   herald, marshal, mason, scribe and warden in `pixi.toml`; steward's `tests/unit/test_preflight_ci.py` and
   `tests/unit/test_preflight_selection.py`; herald's `tests/meta/test_preflight_pages_lane.py`. Problem: the
   preflight refuses with exit 2 until each CI gate step carries the exact report string. Steward:S-124.2's spec
   does not spell it out. This round: by design, since the two stories land back to back, so there is no change
   here. The instruction for the integrator to carry into steward:S-124.2 is that each split station's CI gate step
   carries, verbatim and after its unit report, the string its `pixi.toml` gate `cmd` carries:
   `--report ".steward/coverage/atlas-live*.json"`, `--report ".steward/coverage/herald-live*.json"`,
   `--report ".steward/coverage/marshal-live*.json"`, `--report ".steward/coverage/mason-live*.json"`,
   `--report ".steward/coverage/scribe-live*.json"` and `--report ".steward/coverage/warden-live*.json"`.
5. **Minor: AC9 exits 1 on the ghost entry `tornado`.** Where: `docs/reference/library-llms-full.md`. Problem: the
   cause predates this diff. `pixi.toml` mentions `tornado` only in an unchanged comment, and the catalog is
   scribe:S-31.4's. This round: no change; AC9 was re-run (see the results below) and closes when scribe:S-31.4
   regenerates the catalog.
6. **Minor: scribe's live half fails `test_spec_not_behind_memlog`.** Where: AC2, scribe's live half. Problem:
   `spec-pyforge-steward` has not been re-derived since steward Story 122.2's memlog event, and
   `spec_behind_memlog_known.json` carries stale marshal rows. This diff does not cause it. This round: no change;
   it was re-run (see the results below) and closes with steward:S-122.5's re-derive and marshal's closer.

**Round-2 results (2026-11-11).** No file of this story changed this round: none of the six findings can be
closed in `pixi.toml`, `environment.yaml`, the two generated pages or the `docs/map.yaml` stamps. `pixi.lock`,
`environment.yaml` and `docs/reference/environments.md` are untouched. Each verdict below was read from an exit
code.

- AC1, with the full STATIONS: prints `['core', 'testing-kit']`, exit 1. With the six split stations: `[]`, exit 0.
- AC2, per half:
  - Every package half of the six split stations exits 0.
  - The live halves of atlas, marshal, mason and warden exit 0.
  - Herald's live half fails 1 test (726 passed), `test_preflight_pages_lane.py::test_the_install_runs_before_herald_s_suite_in_one_slot_and_many`,
    which is the window of finding 4.
  - Scribe's live half fails 1 test (162 passed), `test_spec_not_behind_memlog`, which is finding 6.
  - `pyforge-testing-kit-test` (still whole) exits 0.
  - `pyforge-core-test` (still whole) fails 1 test (2642 passed),
    `test_exception_root_sole_ownership.py::test_no_unreparented_exception_root[pyforge-herald/src/pyforge/herald/local_ship.py]`.
    Herald 52.2's committed `ForgeSlugError(ValueError)` is not reparented on `PyforgeError`. This is outside
    this story; it was red the same way in round 1, and it is reported to the integrator.
  - `pyforge-core-live-test` and `pyforge-testing-kit-live-test` do not exist (exit 127): finding 1.
- AC3, with the full STATIONS: `['core', 'testing-kit']`, exit 1. With the six: `[]`, exit 0.
- AC4: `KeyError: 'pyforge-testing-kit-live-test'` (finding 1).
- AC5: prints 0. AC6: prints 0.
- AC7: all three checks exit 0. AC8: exit 0.
- AC9: exit 1, on the ghost entry `tornado` only (finding 5).
- AC10: prints 0. The working tree's `pixi.lock` is unchanged as well.
- AC11: exit 0; the output says "this checkout (local-recipes) is the writer".
- AC12: prints the command; `pyforge-doctor-aggregate-scripts-test` exits 0.
- Finding 2, reproduced: steward's `test_preflight_docs_site_lanes.py` fails 2 of 17, on
  `docs-site tasks missing from preflight.DOCS_SITE_TASKS: ['pyforge-herald-live-test']`.
- Finding 3: herald's `test_built_site_tests_install_first.py` passes against the unchanged lists, so the pins
  still hold the lists this story would change.

Verdict: blocked. Findings 1 and 2 are blockers and finding 3 is a major. Each waits on an integrator or operator
act outside this story's files: a ruling on the shape of the core and kit split, an owner for `preflight.py`, and
a herald pin amendment together with a memlog amendment of steward:S-124.2's spec.

## Gate findings (build, BUILD-8)

- 2026-11-11, `pyforge-steward-live-test` (wave gate): 24 failures, all from this story's uncommitted `pixi.toml`
  and all already recorded above as review findings 2 and 4 (rounds 1 and 2); no fix was made. 18 in steward's
  `tests/unit/test_preflight_selection.py` and 4 in `tests/unit/test_preflight_ci.py` are finding 4: the six new
  `pyforge-<s>-live-test` lanes have no CI job yet, and the six changed gate `cmd`s (`--report
  ".steward/coverage/<s>-live*.json"`) match no CI gate step, so the preflight counts them as always-run lanes
  and refuses with exit 2 on the stranded gates. 2 in `tests/meta/test_preflight_docs_site_lanes.py` are finding 2:
  `preflight.DOCS_SITE_TASKS` lacks `pyforge-herald-live-test`. None closes inside this story's files without
  reverting its intent (every new task joins `pyforge-station-tests`, spec-pyforge-steward:CAP-175). The
  workflow jobs, the gate steps and the selection expectations are steward:S-124.2's files; `preflight.py` and
  `test_preflight_ci.py` are no story's, so the integrator still has to assign them (steward:S-124.2 is the
  natural owner). Re-run of `pyforge-steward-live-test` with nothing changed: exit 1 (24 failed, 1659 passed,
  1 skipped), the same 24.

## Integrator ruling (2026-11-11, before the chunk-4 retry)

The build integrator rules on the three findings that rounds 1 and 2 escalated. Each follows a Spec or a guard
already on the branch; none adds behaviour.

1. **Core and the testing kit take the aggregate shape (ruling (b) of round 1).** Reason: two ready Spec
   capabilities already say so (spec-pyforge-core:CAP-8 as amended 2026-11-10, "pyforge-core-test stays the whole
   suite"; marshal Story 118.1's spec for the kit), and the guards marshal:S-117.1 and marshal:S-118.1 built on the
   branch accept exactly this split: core's `_split_pixi_data` and the kit's `_split_pixi` model it. The shape:
   `pyforge-<s>-package-test` runs `-m "not live_tree"` (the kit's drops django-pyforge from `PYTHONPATH`),
   `pyforge-<s>-live-test` runs `-m live_tree` (the kit's keeps it), and `pyforge-<s>-test` becomes a cmd-less
   `depends-on` aggregate of both, for `s` in `core` and `testing-kit`. `pyforge-station-tests` keeps
   `pyforge-core-test` as its first leg and `pyforge-testing-kit-test` beside it, so each runs whole. The plan note
   that gave `pyforge-core-test` a package-half `cmd` is superseded. AC1, AC3 and AC4 were written for the other
   shape; they are corrected below, and each still checks what it meant to: both halves exist and select by the
   marker, the whole-suite task runs both, the aggregate reaches every live half, and the kit's package half runs
   without the host. `DW-steward-124-1-1` is dropped: nothing is deferred.
   - AC1 (corrected): exit 0, prints `[]`, STATIONS as before.
     ```bash
     python3 -c "import tomllib,sys;f=tomllib.load(open('pixi.toml','rb'))['feature'];bad=[];K=('core','testing-kit')
     for s in sys.argv[1:]:
      t=f[f'pyforge-{s}']['tasks'];w=t.get(f'pyforge-{s}-test') or {};b=t.get(f'pyforge-{s}-live-test') or {};a=(t.get(f'pyforge-{s}-package-test') or {}) if s in K else w
      legs={d if isinstance(d,str) else d['task'] for d in w.get('depends-on',[])}
      whole=s not in K or ('cmd' not in w and legs=={f'pyforge-{s}-package-test',f'pyforge-{s}-live-test'})
      if not a or not b or 'not live_tree' not in a.get('cmd','') or 'live_tree' not in b.get('cmd','') or 'not live_tree' in b['cmd'].split('&&')[0] or not whole: bad.append(s)
     print(bad);sys.exit(bool(bad))" $STATIONS
     ```
   - AC3 (corrected): exit 0, prints `[]`. For core and the kit the aggregate names the whole-suite task, whose
     `depends-on` AC1 proves holds the live half.
     ```bash
     python3 -c "import tomllib,sys;d=tomllib.load(open('pixi.toml','rb'));t={k:v for f in d['feature'].values() for k,v in f.get('tasks',{}).items()};a=str(t['pyforge-station-tests']);m=[s for s in sys.argv[1:] if (f'pyforge-{s}-test' if s in ('core','testing-kit') else f'pyforge-{s}-live-test') not in a];print(m);sys.exit(bool(m))" $STATIONS
     ```
   - AC4 (corrected): prints `False True`.
     ```bash
     python3 -c "import tomllib;t=tomllib.load(open('pixi.toml','rb'))['feature']['pyforge-testing-kit']['tasks'];print('django-pyforge' in str(t['pyforge-testing-kit-package-test'].get('env','')), 'django-pyforge' in str(t['pyforge-testing-kit-live-test'].get('env','')))"
     ```
   Files this ruling adds to this story: steward's `tests/unit/test_preflight.py` (the lane assertion
   `("pyforge-core-test", "pyforge-core")` follows the aggregate's leaves, `pyforge-core-package-test` and
   `pyforge-core-live-test`; nothing else in that file), and the kit's `tests/meta/test_testing_kit_lane_wired.py`
   (`_split_pixi` returns the real data once the task is already an aggregate, the way core's `_split_pixi_data`
   does, and each mutation premise that reads `pyforge-testing-kit-test`'s `cmd` reads the split's legs instead;
   no assertion is dropped or loosened).
2. **`preflight.py` is this story's for one line.** `DOCS_SITE_TASKS` gains `"pyforge-herald-live-test"`: the task
   does run `astro build` in `docs-site/`, so it takes the docs-site mutex beside `npm ci`. Files added: steward's
   `src/pyforge/steward/preflight.py` (`DOCS_SITE_TASKS` only) and `tests/meta/test_preflight_docs_site_lanes.py`
   (only if its expectations name the set).
3. **Herald's built-site tests return to CI's strict run, here.** Herald's
   `tests/meta/test_built_site_tests_install_first.py` is added to this story: its pins admit the live half, so
   `pyforge-herald-test-built` depends on `[docs-site-install, pyforge-herald-test, pyforge-herald-live-test]` and
   `pyforge-herald-coverage-gate` on `[pyforge-herald-test, pyforge-herald-live-test]`, each pin still asserting the
   exact list. Herald Story 45.1's rule (a missing install fails under `HERALD_DOCS_SITE_REQUIRED=1`) holds again
   wherever `pyforge-herald-test-built` runs. `DW-steward-124-1-2` is dropped. The CI pin in that file
   (`test_ci_s_herald_job_runs_the_built_task_strictly_with_the_site_environment`) stays as it is; Story 124.2
   owns any CI change.
4. **Planned red window until steward:S-124.2 (finding 4), unchanged.** Steward's
   `tests/unit/test_preflight_selection.py` and `tests/unit/test_preflight_ci.py`, and herald's
   `tests/meta/test_preflight_pages_lane.py`, red from this story's commit until Story 124.2 lands, because the new
   lanes and the gate commands' `--report ".steward/coverage/<s>-live*.json"` strings have no CI step yet. This is
   the back-to-back window the plan names; Story 124.2's spec now names those files and the exact strings
   (its § Integrator note). A reviewer judges those reds as this window, not as a failure of this story.
5. **AC9 (`tornado` ghost entry) closes with scribe:S-31.4**, which regenerates the library catalog; scribe's
   `test_spec_not_behind_memlog` closes with steward:S-122.5's re-derive. Neither is this story's.
6. `pyforge-core-test`'s one red in round 2 (`test_no_unreparented_exception_root[...herald/local_ship.py]`) is
   fixed by the integrator in herald (`ForgeSlugError(PyforgeError, ValueError)`), recorded on herald Story 52.2.
