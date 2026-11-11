---
title: "47.2: The catalog and gate companions name every dataset and gate the code has"
type: 'feature'
created: '2026-11-10'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # companion text and a gate that judges; no runtime path
difficulty: medium
story: '47.2'
spec: pyforge-atlas
surface:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/catalog-contract.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/gate-contract.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/signals.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/degradation-contract.md
  - src/shared/packages/pyforge-atlas/tests/meta/test_catalog_contract.py
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-47-2-the-catalog-and-gate-companions-name-every-dataset-and-gate-the-code-has.md
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/catalog-contract.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/gate-contract.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/signals.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/degradation-contract.md
  - src/shared/packages/pyforge-atlas/conf/base/catalog.yml
  - src/shared/packages/pyforge-atlas/tests/unit/catalog/conftest.py
  - pixi.toml
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name a story in a later epic (S-48.1).
> The key stays `blocked` until that story is `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** `catalog-contract.md` still describes seven pipelines and 86 datasets and names 22 of the 147 catalog entries; `gate-contract.md` lists seven gates at test paths that moved under `tests/unit/` and omits query-plane-parity, dashboard-dryrun, vizro-ai-dryrun and publish-range. Both froze on 2026-07-29. They are the dataset and gate half of the public contract (CAP-73). Companion text is stale, code is right.

**Approach:**
- **Order across units.** Build after steward's `pixi.toml` edit is on the branch (steward Story 124.1: the `pyforge-atlas-live-test` task of decision D2; steward declined moving the seven gate tasks to `feature.pyforge-atlas`, so they stay in `feature.local-recipes`). The meta-test derives each gate task and its feature from `pixi.toml`, so whichever state `pixi.toml` is in when this story builds is the state `gate-contract.md` records; a later `pixi.toml` edit reds `tests/meta/test_catalog_contract.py` until the table follows.
- **catalog-contract.md.** The pipeline table becomes the seven sealed plus the five governed additions, with the per-pipeline counts the suite already pins (`tests/unit/catalog/conftest.py::EXPECTED_PIPELINE_COUNTS`, total 147), and every dataset is named once under its pipeline; the two freshness clocks, the TTL table and the join-key rules keep their text where it is still true.
- **gate-contract.md.** One table row per gate task, with its pixi feature, its real test path and what it proves; `kedro-test` is described as the alias of `pyforge-atlas-test` it now is; the tasks that run no pytest (`dashboard-serve`, `publish`, `wasm-build`) are listed below the table.
- **signals.md and degradation-contract.md.** Read each cited node, dataset and test against the tree and change only what does not resolve ('seven typed pipelines' in `signals.md` becomes the sealed seven).
- The new test reads `catalog.yml` and conftest's counts inside the package and the companions and `pixi.toml` outside it, so it carries `pytestmark = pytest.mark.live_tree`; it has one negative case per family (a synthetic dataset name, a synthetic gate task). It owns no `SPEC.md` text and appends nothing to the memlog (Story 48.4 does).

Ledger key: `47-2-the-catalog-and-gate-companions-name-every-dataset-and-gate-the-code-has`.
Type / Effort / Deps: feature / M / S-48.1.

### Living CAP citations

- `spec-pyforge-atlas` CAP-73 (its catalog and gate half), CAP-1, CAP-2; FR-78 ← CAP-73

## Acceptance Criteria

Each command runs from the worktree root; read every verdict from its exit code, never through a pipe.

- **AC1 — The companion meta-test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/meta/test_catalog_contract.py -q
  ```

- **AC2 — catalog-contract.md names every catalog entry.** Expected: exit 0, prints 147 0 (today 147 125).

  ```bash
  python3 -c 'import yaml,sys;names=[k for k in yaml.safe_load(open('"'"'src/shared/packages/pyforge-atlas/conf/base/catalog.yml'"'"')) if not k.startswith('"'"'_'"'"')];c=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/catalog-contract.md'"'"').read();bad=[n for n in names if chr(96)+n+chr(96) not in c];print(len(names),len(bad));sys.exit(1 if bad else 0)'
  ```

- **AC3 — The frozen counts are gone.** Expected: exit 0.

  ```bash
  ! grep -qE "seven closed pipelines|\*\*86\*\*" _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/catalog-contract.md && ! grep -q "/tests/catalog -q" _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/gate-contract.md
  ```

- **AC4 — gate-contract.md names every pixi task that runs pytest over the atlas tests, with the env pixi.toml holds it in.** Expected: exit 0, the list is empty (today 11 tasks and all 11 fail: the table has no such rows). One table row per task: the task and its pixi feature, both as code tokens.

  ```bash
  python3 -c 'import tomllib,re,sys;g=open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/gate-contract.md'"'"').read();p=tomllib.load(open('"'"'pixi.toml'"'"','"'"'rb'"'"'));f=p['"'"'feature'"'"'];q=chr(96);gates=sorted((k,fn) for fn,v in f.items() for k,t in v.get('"'"'tasks'"'"',{}).items() if isinstance(t,dict) and '"'"'pytest'"'"' in str(t.get('"'"'cmd'"'"','"'"''"'"')) and '"'"'pyforge-atlas/tests'"'"' in str(t.get('"'"'cmd'"'"','"'"''"'"')));row=lambda k:next((l for l in g.splitlines() if l.startswith('"'"'|'"'"') and q+k+q in l),'"'"''"'"');bad=[(k,fn) for k,fn in gates if not row(k) or q+fn+q not in row(k)];print(len(gates),bad);sys.exit(1 if bad else 0)'
  ```

- **AC5 — Every test path the four companions cite exists.** Expected: exit 0, prints [].

  ```bash
  python3 -c 'import re,os,sys;bad=[(f,p) for f in ['"'"'catalog-contract.md'"'"','"'"'gate-contract.md'"'"','"'"'signals.md'"'"','"'"'degradation-contract.md'"'"'] for p in re.findall(r'"'"'\x60(tests/[\w/.-]+)'"'"',open('"'"'_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/'"'"'+f).read()) if not os.path.exists('"'"'src/shared/packages/pyforge-atlas/'"'"'+p)];print(bad);sys.exit(1 if bad else 0)'
  ```

## Boundaries & Constraints

**Always:**
- Derive the dataset and gate sets from `catalog.yml`, the conftest counts and `pixi.toml`.
- Keep the freshness clocks, TTL table and join-key rules where they are still true.

**Never:**
- Never edit `pixi.toml` (steward's); never edit `SPEC.md` or the memlog.
- Never cite a test path that does not exist.

</intent-contract>

## Binding

- Parent: `spec-pyforge-atlas` CAP-73 (its catalog and gate half), CAP-1, CAP-2; FR-78 ← CAP-73.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-11-10 (cutover readiness) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the entry of that date and its two addenda).
- Epic: Epic 47, minted 2026-11-10 with this story.
- Ledger key: `47-2-the-catalog-and-gate-companions-name-every-dataset-and-gate-the-code-has`.
- Deps: S-48.1.
- Cross-station deps: steward:S-124.1 (the pixi.toml edit this story records).
- Flag: `flag-exempt: detector-or-gate` (a gate is never flagged: a flag-OFF gate is a silent green).
- Surface: `marshal-policy.toml` `[epic_surfaces]."47"`, narrowed by this spec's `surface:`.
- Minted 2026-11-10 in the atlas mint of the one cutover-readiness PR (branch `cutover-readiness-2026-11-10`); built in the same PR.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: exit 0.
- `pixi run -e pyforge-atlas kedro-test` — expected: exit 0.

**Run before the push:** the acceptance commands above, each read from its exit code.

## Auto Run Result

Status: blocked (forward dependency on S-48.1, 2026-11-10; minted 2026-11-10).

## Spec Change Log

- 2026-11-10: minted from the station Dream's entry of 2026-11-10 (cutover readiness) under the operator's rulings of 2026-11-10 ("Accept all", "Retire both", "Accept all, run mint"). Acceptance adjusted by the rulings: steward declined moving the seven gate tasks (an estate change), so `gate-contract.md` records them in `feature.local-recipes`.

- 2026-11-11 (third review of the mint): the key is `blocked` (forward dependency: Deps name S-48.1, a later epic; the one policy every station took at this mint), and Deps take the `S-<epic>.<num>` grammar doctor's forward-dependency detector parses.

## Review Triage Log

- (none yet)
