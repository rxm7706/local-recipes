---
title: '148.2: pixi 0.85.0 at every pin site'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 148-2-pixi-0-85-0-at-every-pin-site
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'pixi.toml'
  - 'src/shared/packages/pyforge-mason/pixi.toml'
  - 'environment.yaml'
  - 'Containerfile'
  - 'src/platform/Containerfile'
  - 'src/platform/compose/dbgpt/Containerfile'
  - 'src/platform/compose/mcp-host/Containerfile'
  - '.github/workflows'
  - '.github/actions/platform-test-setup/action.yml'
  - '.github/actions/sync-pypi-mappings/action.yml'
  - 'docs/tutorials/getting-started.md'
  - 'docs/reference/container-base-layer-convention.md'
  - 'docs/how-to/bootstrap-a-machine-with-steward.md'
  - 'docs/tutorials/onboard-a-machine.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - scripts/pixi_version_registry.py
  - scripts/bump_pixi_version.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Every registered pixi pin site holds 0.80.0, and the `setup-pixi` action is v0.11.2 in 39 steps and v0.10.2 in two composite actions. pixi 0.85.0 (2026-11-25) and `setup-pixi` v0.11.3 are released, and pixi 0.85.0 deprecates the `platform` key of a named platform entry in favour of `subdir`.

**Approach:** `bump-pixi-version` rewrites every site the registry names to 0.85.0 and exports `environment.yaml`; it runs under pixi 0.85.0 (`pixi exec --spec pixi=0.85.0 --spec python=3.14`). Every `setup-pixi` step moves to v0.11.3. The `osx-arm64-min` entry uses `subdir`. The four docs that state the pixi floor state 0.85.0.

Ledger key: `148-2-pixi-0-85-0-at-every-pin-site`.

### Living CAP citations

- spec-pyforge-steward CAP-153 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The registry stays the one list of pixi pin sites; no site is hand-edited around it.

**Never:**
- Never cap pixi in any manifest.

## Acceptance Criteria

**Given** the workspace at pixi 0.85.0
**When** the pin sites are checked
**Then** every one holds 0.85.0, and pixi 0.85.0 reads the manifest with no warning

- **AC1 — Every pin site holds 0.85.0.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pixi-version-check
  ```

- **AC2 — Every setup-pixi step is v0.11.3.** Expected: no output.

  ```bash
  grep -rn 'prefix-dev/setup-pixi@' .github | grep -v 'setup-pixi@v0.11.3'
  ```

</intent-contract>

## Result (2026-11-27)

- `bump-pixi-version` rewrote 22 sites to 0.85.0: `pixi.toml`'s `$schema` URL, `requires-pixi` and three feature floors; `pyforge-mason`'s run-dependency floor; the `pixi-version` of 13 workflows and two composite actions; and the four Containerfiles' builder stage. It exported `environment.yaml` (`pixi >=0.85.0`).
- All 41 `setup-pixi` steps are v0.11.3. The `osx-arm64-min` entry uses `subdir`, and pixi 0.85.0 reads the manifest with no warning; the lock it writes records `subdir: osx-arm64`.
- `docs/tutorials/getting-started.md`, `docs/reference/container-base-layer-convention.md`, `docs/how-to/bootstrap-a-machine-with-steward.md` and `docs/tutorials/onboard-a-machine.md` state the 0.85.0 floor.
- AC1: `pixi-version-check` exits 0 (23 sites). AC2: no step is off v0.11.3.
