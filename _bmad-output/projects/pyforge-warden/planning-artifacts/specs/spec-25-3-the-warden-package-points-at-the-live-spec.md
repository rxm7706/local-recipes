---
title: "25.3: The warden package points at the live Spec"
type: 'fix'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: 'easy'
story: '25.3'
spec: _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
surface:
  - src/shared/packages/pyforge-warden/README.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/__init__.py
  - _bmad-output/projects/pyforge-warden/.bmad-config.toml
  - _bmad-output/PROJECTS.md
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - src/shared/packages/pyforge-warden/README.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/__init__.py
  - _bmad-output/projects/pyforge-warden/.bmad-config.toml
  - _bmad-output/PROJECTS.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-26.1).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** Warden's own package points at a file that moved: the README says "Epics 1–8 shipped" and links `docs/specs/pyforge-warden.md`, which moved to `archive/` on 2026-09-18 (doctor Story 23.3); the package docstring calls the package a build-wiring skeleton delivered against that same path; the project config (`.bmad-config.toml` line 11) and its `_bmad-output/PROJECTS.md` row name it as the intake spec.

**Approach:** The README points at the Spec folder and `contract.md` (Story 26.1 creates it, hence the dep), drops the per-epic status sentence and keeps its hook-book section. The `__init__.py` edit is the docstring only; `__version__` does not move. The project config's line 11 and its `PROJECTS.md` row move together, so the pair marshal's seed projects-index reads stays equal. The package manifest's Python floor (decision D6) and its dead-path comment are steward Story 124.3's, because the edit and the re-lock are one commit. `__init__.py` also sits on `spec-pyforge-core`'s surface: Story 25.2 names it in warden's reconcile event, and core-kit's closer writes the co-governor's.

Ledger key: `25-3-the-warden-package-points-at-the-live-spec`.
Type / Effort / Deps: fix / S / S-26.1.

### Living CAP citations

- spec-one-chain-per-station:CAP-11 (readers follow a moved file; CHAIN-STANDARD § 11); no warden CAP or FR.
- `spec-feature-flag-governance` Q1: a `fix` needs no flag. No runtime behaviour changes.

## Boundaries & Constraints

**Always:**
- Change the docstring only in `__init__.py`; edit only line 11 of the config and the warden row of `PROJECTS.md`.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not edit the package `pixi.toml` (steward Story 124.3).
- Do not touch the deck sources.

</intent-contract>

## Acceptance Criteria

- **AC1 — None of the four surface files names the retired legacy spec path.** Run from the repo root, verdict from the exit code (never through a pipe):
  `bash -c '! grep -q "docs/specs/pyforge-warden.md" src/shared/packages/pyforge-warden/README.md src/shared/packages/pyforge-warden/src/pyforge/warden/__init__.py _bmad-output/projects/pyforge-warden/.bmad-config.toml _bmad-output/PROJECTS.md'`
  Expect: exit 0.
- **AC2 — The README no longer says Epics 1-8 shipped and names the Spec folder and its contract.** Run from the repo root, verdict from the exit code (never through a pipe):
  `bash -c '! grep -q "Epics 1.8 shipped" src/shared/packages/pyforge-warden/README.md && grep -q "spec-pyforge-warden" src/shared/packages/pyforge-warden/README.md && grep -q "contract.md" src/shared/packages/pyforge-warden/README.md'`
  Expect: exit 0.
- **AC3 — Every relative link in the README resolves.** Run from the repo root, verdict from the exit code (never through a pipe):
  `python3 -c "import re,os,sys;p='src/shared/packages/pyforge-warden/README.md';b=[u for u in re.findall(r'\]\((\.\.?/[^)#]+)',open(p).read()) if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p),u)))];print(b);sys.exit(1 if b else 0)"`
  Expect: prints [], exit 0.
- **AC4 — The package docstring no longer calls the package a skeleton, and the version line is untouched.** Run from the repo root, verdict from the exit code (never through a pipe):
  `bash -c '! grep -q "build-wiring skeleton" src/shared/packages/pyforge-warden/src/pyforge/warden/__init__.py && grep -q "^__version__ = " src/shared/packages/pyforge-warden/src/pyforge/warden/__init__.py'`
  Expect: exit 0.
- **AC5 — Station suite and lint.** Run from the repo root, verdict from the exit code (never through a pipe):
  `pixi run --frozen -e pyforge-warden pyforge-warden-test && pixi run -e pyforge-guild lint-types`
  Expect: exit 0.

## Binding

- Story: `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md` § *Story 25.3: The warden package points at the live Spec*.
- Dream: `docs/dreams/pyforge-warden.md`, Realization log, *2026-11-10 (the cutover readiness audit)*; the operator's rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization log, second addendum).
- Ledger key: `25-3-the-warden-package-points-at-the-live-spec`.
- Deps: S-26.1.
- Flag: none (a `fix` story, `spec-feature-flag-governance` Q1).
