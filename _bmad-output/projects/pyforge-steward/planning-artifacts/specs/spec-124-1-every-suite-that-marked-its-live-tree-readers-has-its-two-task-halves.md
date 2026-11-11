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

- **AC1 — each landed station has both halves, and each half selects by the marker.** Expected: exit 0; prints `[]`, with STATIONS="atlas herald marshal mason scribe warden core testing-kit" less any station whose marking story did not land (that station gets a deferred row and keeps its one task).
  ```bash
  python3 -c "import tomllib,sys;f=tomllib.load(open('pixi.toml','rb'))['feature'];bad=[]
  for s in sys.argv[1:]:
   t=f[f'pyforge-{s}']['tasks'];a=t.get(f'pyforge-{s}-test');b=t.get(f'pyforge-{s}-live-test')
   if not a or not b or 'not live_tree' not in a['cmd'] or 'live_tree' not in b['cmd'] or 'not live_tree' in b['cmd'].split('&&')[0]: bad.append(s)
  print(bad);sys.exit(bool(bad))" $STATIONS
  ```
- **AC2 — no half is empty and both pass.** Expected: exit 0 (pytest's 'no tests collected' exit 5 is a failure).
  ```bash
  for s in $STATIONS; do pixi run --frozen -e pyforge-$s pyforge-$s-test && pixi run --frozen -e pyforge-$s pyforge-$s-live-test || exit 1; done
  ```
- **AC3 — the aggregate names every new task.** Expected: exit 0; prints `[]`.
  ```bash
  python3 -c "import tomllib,sys;d=tomllib.load(open('pixi.toml','rb'));t={k:v for f in d['feature'].values() for k,v in f.get('tasks',{}).items()};a=str(t['pyforge-station-tests']);m=[s for s in sys.argv[1:] if f'pyforge-{s}-live-test' not in a];print(m);sys.exit(bool(m))" $STATIONS
  ```
- **AC4 — the kit's package half runs without the host on its path.** Expected: prints `False True`.
  ```bash
  python3 -c "import tomllib;t=tomllib.load(open('pixi.toml','rb'))['feature']['pyforge-testing-kit']['tasks'];print('django-pyforge' in str(t['pyforge-testing-kit-test'].get('env','')), 'django-pyforge' in str(t['pyforge-testing-kit-live-test'].get('env','')))"
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
