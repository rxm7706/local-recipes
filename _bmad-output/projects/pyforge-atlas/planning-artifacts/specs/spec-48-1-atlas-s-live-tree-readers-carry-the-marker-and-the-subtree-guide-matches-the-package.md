---
title: "48.1: Atlas's live-tree readers carry the marker and the subtree guide matches the package"
type: 'feature'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a test marker and a guide; no runtime path (the shape of doctor Story 55.4)
difficulty: medium
story: '48.1'
spec: pyforge-atlas
surface:
  - src/shared/packages/pyforge-atlas/pyproject.toml
  - src/shared/packages/pyforge-atlas/tests/**/*.py
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/pixi.toml
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-48-1-atlas-s-live-tree-readers-carry-the-marker-and-the-subtree-guide-matches-the-package.md
context:
  - src/shared/packages/pyforge-atlas/pyproject.toml
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/pixi.toml
  - src/shared/packages/pyforge-doctor/pyproject.toml
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-55-4-doctor-s-live-tree-readers-run-as-their-own-half.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Decision D2, and the stale subtree `AGENTS.md`. No atlas test is marked, so the whole 190-module suite reads planning artifacts, `pixi.toml`, workflows, skills, `scripts/` and other stations, and a second root cannot tell which tests judge the package alone. The guide agents read before touching the package names a binding Spec, fixtures and an MCP library that are gone.

**Approach:**
- **Found, not listed.** A literal scan for paths outside the package gives the first list (near 60 of 190 modules: all five `tests/meta` files; the tests that import from `scripts/`; the tests that read `pixi.toml`, `flags.json`, the workflows, `recipes/` or `.claude/`); the exported-copy run (AC3) is the proof and finds the rest. That run sets `PYTHONPATH` to the copy's `src` (`pyforge` is a PEP 420 namespace, so the copy's `pyforge.atlas` wins and `pyforge.core` still comes from the env), asserts it, and runs from inside the copy.
- **Doctor's shape.** `pytestmark = pytest.mark.live_tree` at module level; the marker text copied from `pyforge-doctor/pyproject.toml`; no test deleted, skipped or re-marked to meet a time. `slow` stays unregistered: no atlas test uses it.
- **Scope.** `tests/**/*.py` means the modules that exist at the branch base; the test files Stories 47.1, 47.2, 48.2 and 48.3 add, edit or delete are theirs. This story changes no pixi task and no workflow: the task split, the `atlas-live-test` job, the trigger map and the registry rows are steward's (Stories 124.1 and 124.2); until they land `pyforge-atlas-test` still runs every module.
- **AGENTS.md.** Its `bmad:context` block is refreshed with the `bmad-project-context` skill, never by hand; the kedro-skills block is left alone. The refresh carries: the binding contract is `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md` and its companions; the gates with their real paths under `tests/unit/` and `tests/integration/`; the fixtures that exist (`tests/fixtures/data`, `inventory_identity`, `json_sources`); `mcp/server.py` lazy-loads the official `mcp` SDK; the two suite halves and what `live_tree` means; the exit-code rule with the bring-up tool's exception; 'metric expressions are Ibis; `semantic/query_helpers.py` shapes the returned frame with pandas'; the two pitfall lines that cite NFR-4 and NFR-9 cite CAP-3 and CAP-4 instead; the 'read the directory, don't cite a frozen listing' line stays.
- **Member pixi.toml.** Two comments only: line 11's `docs/specs/…` path gains `archive/`; line 22 drops the claim about warden's floor.
- No atlas capability is minted or amended; the story appends nothing to the memlog (Story 48.4 writes the unit's one surface-reconcile event).

Ledger key: `48-1-atlas-s-live-tree-readers-carry-the-marker-and-the-subtree-guide-matches-the-package`.
Type / Effort / Deps: feature / M / none.

### Living CAP citations

- Relay of `spec-pyforge-steward:CAP-175` (the live-tree split); no atlas CAP or FR

## Acceptance Criteria

Each command runs from the worktree root; read every verdict from its exit code, never through a pipe.

- **AC1 — The marker is registered in the package's pytest options.** Expected: exit 0.

  ```bash
  python3 -c 'import tomllib,sys;m=tomllib.load(open('"'"'src/shared/packages/pyforge-atlas/pyproject.toml'"'"','"'"'rb'"'"')).get('"'"'tool'"'"',{}).get('"'"'pytest'"'"',{}).get('"'"'ini_options'"'"',{}).get('"'"'markers'"'"',[]);sys.exit(0 if any(x.startswith('"'"'live_tree:'"'"') for x in m) else 1)'
  ```

- **AC2 — Every tests/meta module that exists at the branch base is marked.** Expected: exit 0, prints [].

  ```bash
  python3 -c 'import ast,sys;fs=['"'"'test_cli_tool_parity.py'"'"','"'"'test_foundry_full_mypy_lane.py'"'"','"'"'test_planning_record.py'"'"','"'"'test_portal_inventory_row.py'"'"','"'"'test_skf_skill_and_persona.py'"'"'];bad=[f for f in fs if not any(isinstance(n,ast.Assign) and any(getattr(t,'"'"'id'"'"','"'"''"'"')=='"'"'pytestmark'"'"' for t in n.targets) and '"'"'live_tree'"'"' in ast.dump(n.value) for n in ast.parse(open('"'"'src/shared/packages/pyforge-atlas/tests/meta/'"'"'+f).read()).body)];print(bad);sys.exit(1 if bad else 0)'
  ```

- **AC3 — The package half reads nothing outside the package: it passes from an exported copy, importing the copy, with the working directory inside the copy.** Expected: exit 0 (run after the commit). Exit 3 means the copy was not the code under test and the run proves nothing. A module that fails here reaches for the repository and takes the marker; never a skip.

  ```bash
  T="$(mktemp -d)" && W="$PWD" && git archive HEAD src/shared/packages/pyforge-atlas | tar -x -C "$T" && pixi run --manifest-path "$W/pixi.toml" --frozen -e pyforge-atlas bash -c 'cd "$1" && export PYTHONPATH="$1/src" && python -c "import pyforge.atlas,sys;sys.exit(0 if pyforge.atlas.__file__.startswith(sys.argv[1]) else 3)" "$1" && python -m pytest tests/unit tests/meta -q -m "not slow and not live_tree" -p no:cacheprovider' _ "$T/src/shared/packages/pyforge-atlas"
  ```

- **AC4 — The two halves are the whole suite.** Expected: exit 0; prints three counts (all, live_tree, not live_tree) and the last two sum to the first.

  ```bash
  PYTHONPATH=src/shared/packages/pyforge-atlas/src:scripts pixi run --frozen -e pyforge-atlas python -c 'import subprocess,re,sys;b=[sys.executable,'"'"'-m'"'"','"'"'pytest'"'"','"'"'src/shared/packages/pyforge-atlas/tests'"'"','"'"'--collect-only'"'"','"'"'-q'"'"','"'"'-p'"'"','"'"'no:cacheprovider'"'"'];n=lambda a:int(re.search(r'"'"'(\d+)(?:/\d+)? tests? collected'"'"',subprocess.run(b+a,capture_output=True,text=True).stdout).group(1));a,l,p=n([]),n(['"'"'-m'"'"','"'"'live_tree'"'"']),n(['"'"'-m'"'"','"'"'not live_tree'"'"']);print(a,l,p);sys.exit(0 if l>0 and l+p==a else 1)'
  ```

- **AC5 — Nothing was dropped from the station task.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pyforge-atlas-test
  ```

- **AC6 — The subtree guide names nothing that is gone.** Expected: exit 0.

  ```bash
  ! grep -qE "docs/specs/cfe-atlas|tests/fixtures/parity/|tests/fixtures/credentials/|lazy-imports fastmcp|tests/catalog/|NFR-[0-9]" src/shared/packages/pyforge-atlas/AGENTS.md && grep -q "live_tree" src/shared/packages/pyforge-atlas/AGENTS.md && grep -q "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md" src/shared/packages/pyforge-atlas/AGENTS.md && ! grep -q "warden's is 3.12" src/shared/packages/pyforge-atlas/pixi.toml
  ```

- **AC7 — Post-condition, owned by the requests to steward-station: steward's derivation agrees once its half lands.** Expected: exit 0 with `atlas` in LIVE_SPLIT and gone from UNSPLIT_ON_A_STATION_SRC_EDIT; not this story's gate once Story 124.2 has landed; red before it by design (other units' new reads).

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q
  ```

## Boundaries & Constraints

**Always:**
- Mark a module that reaches outside the package; prove the package half from an exported copy.
- Refresh the `bmad:context` block only through `bmad-project-context`.

**Never:**
- Never delete, skip or `xfail` a test; never edit a root pixi task or a workflow.
- Never hand-edit the `bmad:context` block.

</intent-contract>

## Binding

- Parent: Relay of `spec-pyforge-steward:CAP-175` (the live-tree split); no atlas CAP or FR.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-11-10 (cutover readiness) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the entry of that date and its two addenda).
- Epic: Epic 48, minted 2026-11-10 with this story.
- Ledger key: `48-1-atlas-s-live-tree-readers-carry-the-marker-and-the-subtree-guide-matches-the-package`.
- Deps: none.
- Cross-station deps: none.
- Followed by: steward:S-124.1, steward:S-124.2 (the task split and the live-tree CI job that read this marker; both depend on this story, not the reverse).
- Flag: `flag-exempt: detector-or-gate` (a gate is never flagged: a flag-OFF gate is a silent green).
- Surface: `marshal-policy.toml` `[epic_surfaces]."48"`, narrowed by this spec's `surface:`.
- Minted 2026-11-10 in the atlas mint of the one cutover-readiness PR (branch `cutover-readiness-2026-11-10`); built in the same PR.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: exit 0.

**Run before the push:** the acceptance commands above, each read from its exit code.

## Auto Run Result

Status: backlog (minted 2026-11-10).

## Spec Change Log

- 2026-11-10: minted from the station Dream's entry of 2026-11-10 (cutover readiness) under the operator's rulings of 2026-11-10 ("Accept all", "Retire both", "Accept all, run mint"). Acceptance adjusted by the rulings: no adjustment.

- 2026-11-10 (review of the mint): steward:S-124.1 and steward:S-124.2 move from cross-station deps to `Followed by:`; each lists this story among its own deps, so the old line made a cycle.

## Review Triage Log

- (none yet)
