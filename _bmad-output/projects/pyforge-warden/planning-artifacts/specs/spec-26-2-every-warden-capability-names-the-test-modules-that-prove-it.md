---
title: "26.2: Every warden capability names the test modules that prove it"
type: 'chore'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a companion and a meta-test that judges (spec-feature-flag-governance Q1, Q2)
difficulty: 'medium'
story: '26.2'
spec: _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
surface:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/proof-map.md
  - src/shared/packages/pyforge-warden/tests/meta/test_capability_proof_map.py
  - _bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - src/shared/packages/pyforge-warden/pyproject.toml
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-27.1).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).
>
> **Unblocked 2026-11-13.** Every story its Deps name is `done` on branch `cutover-readiness-2026-11-10`. The operator's "Start build" consent covered the unblock; CLOSE-LEDGERS moved the key to `done`.

<intent-contract>

## Intent

**Problem:** The second root rebuilds each capability with this repository's tests as the oracle, and CHAIN-STANDARD § 2 (operator ruling 2026-11-01) says a success clause names the test that proves it. CAP-1..CAP-22 name none, and the audit left CAP-3, 4, 7, 9, 10 and 17 untraced.

**Approach:** `proof-map.md`, a new companion beside `SPEC.md` and `contract.md`: one table, one row per capability `SPEC.md` defines (29): `| CAP-n | lane | test modules | command |`, a capability with modules in two lanes taking two rows. Lanes: package (unit, meta, integration modules that read nothing outside the package), live-tree (modules marked `live_tree`), slow (the corpus-oracle task: extraction oracle, corpus determinism, strace egress, real-pixi solver; no workflow runs it, DW-5-2-5), platform (`src/platform/tests/*`, for CAP-16, CAP-17, CAP-19..CAP-22 and CAP-29). Cells name test modules and nothing finer. A clause no module proves is one row under *Gaps* (`| CAP-n | the clause, quoted short | DW id |`) and one ledger row from `DW-warden-cutover-2026-11-10-12` up (owner warden, `promoted: 2026-11-10`); never a `SPEC.md` re-word and never a new product test. CAP-28's own row cites `test_public_contract.py`, `test_contract_surface.py` and this module.

**Test.** `tests/meta/test_capability_proof_map.py`, `pytestmark = pytest.mark.live_tree`: every capability `SPEC.md` defines has a row; every cited module exists; each row's lane agrees with the module (live-tree iff it carries `live_tree`, slow iff `slow`, platform iff the path starts `src/platform/`, else package), which is why this story follows 27.1; every Gaps row names a ledger id that exists. Negative tests use synthetic tables.

Ledger key: `26-2-every-warden-capability-names-the-test-modules-that-prove-it`.
Type / Effort / Deps: chore / M / S-25.4, S-26.1, S-26.3, S-27.1.

### Living CAP citations

- spec-pyforge-warden CAP-28 (FR-45).
- CHAIN-STANDARD § 2 (a success clause names its proof).
- `flag-exempt: detector-or-gate`.

## Boundaries & Constraints

**Always:**
- Append to the ledger only this story's own rows, after Story 25.4.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not edit `SPEC.md` or its memlog (CAP-28's marker moves in Story 25.2).
- Do not change code or an existing test.
- Do not edit a row Story 25.4 wrote.

</intent-contract>

## Acceptance Criteria

- **AC1 — The proof-map test.** Run from the repo root, verdict from the exit code (never through a pipe):
  `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/meta/test_capability_proof_map.py -q`
  Expect: exit 0.
- **AC2 — Every capability in SPEC.md has a proof row and every cited test module exists (independent re-derivation).** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,os,sys;s=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/proof-map.md').read();caps=sorted(set(int(n) for n in re.findall(r'(?m)^- \*\*CAP-(\d+) — ',open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md').read())));miss=[n for n in caps if not re.search(r'(?m)^\| CAP-%d \|'%n,s)];dead=sorted(set(p for p in re.findall(r'((?:src/[\w/.-]+|tests/[\w/.-]+)\.py)',s) if not os.path.exists(p if p.startswith('src/') else 'src/shared/packages/pyforge-warden/'+p)));print(len(caps),miss,dead);sys.exit(1 if miss or dead or len(caps)!=29 else 0)"`
  Expect: prints 29 [] [], exit 0.
- **AC3 — The test fails on a dead path, a capability with no row and a wrong lane.** Run from the repo root, verdict from the exit code (never through a pipe):
  `PYTHONPATH=src/shared/packages/pyforge-warden/src:scripts pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/meta/test_capability_proof_map.py -q -k 'dead_path or no_row or lane_mismatch'`
  Expect: exit 0 with at least 3 tests selected and passed.
- **AC4 — Every gap the map records has its deferral row.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,sys;s=open('_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/proof-map.md').read();g=s.split('## Gaps',1)[1] if '## Gaps' in s else '';ids=sorted(set(re.findall(r'DW-warden-cutover-2026-11-10-\d+',g)));rows=[l for l in g.splitlines() if re.match(r'\| CAP-\d+ \|',l)];t=open('_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md').read();m=[i for i in ids if '### '+i+':' not in t];print(len(rows),ids,m);sys.exit(1 if m or len(ids)<len(set(re.findall(r'CAP-\d+ \|[^\n]*',g))) and not ids and rows else 0)"`
  Expect: prints the gap row count, the ids and [], exit 0 (a gap row with no id fails).
- **AC5 — This story changed no Spec clause.** Run from the repo root, verdict from the exit code (never through a pipe):
  `bash -c 'test -z "$(git log --format=%H --grep="26[.-]2" -- _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md | head -1)"'`
  Expect: exit 0 (no commit of this story touches SPEC.md).
- **AC6 — Post-condition (Story 124.2 runs it): Cross-unit: steward's trigger map accepts the new module's reads.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q`
  Expect: exit 0 once steward Story 124.2 carries the paths this story names (shared request); red before it by design (other units' new reads).
- **AC7 — Ledger and lint.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run -e pyforge-guild deferred-work-check && pixi run -e pyforge-guild lint-types`
  Expect: exit 0.

## Binding

- Story: `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md` § *Story 26.2: Every warden capability names the test modules that prove it*.
- Dream: `docs/dreams/pyforge-warden.md`, Realization log, *2026-11-10 (the cutover readiness audit)*; the operator's rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization log, second addendum).
- Ledger key: `26-2-every-warden-capability-names-the-test-modules-that-prove-it`.
- Deps: S-25.4, S-26.1, S-26.3, S-27.1.
- Flag: none (`flag-exempt: detector-or-gate`).
- Cross-station: `steward:S-124.2` carries this module's outside reads in steward's trigger map; AC6 passes once it is on the branch.
