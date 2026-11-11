---
title: "48.3: The retired views runtime leaves the package again"
type: 'refactor'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: heavy
story: '48.3'
spec: pyforge-atlas
surface:
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/views/**
  - src/shared/packages/pyforge-atlas/tests/unit/views/**
  - src/shared/packages/pyforge-atlas/tests/unit/catalog/test_no_inline_io.py
  - src/shared/packages/pyforge-atlas/tests/unit/singularity/test_duckdb_sole_engine.py
  - src/shared/packages/pyforge-atlas/pyproject.toml
  - src/shared/packages/pyforge-atlas/pixi.toml
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-48-3-the-retired-views-runtime-leaves-the-package-again.md
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-24-1-retire-the-second-lane-3-runtime.md
  - src/shared/packages/pyforge-atlas/pyproject.toml
  - src/shared/packages/pyforge-atlas/pixi.toml
  - src/shared/packages/pyforge-atlas/tests/unit/catalog/test_no_inline_io.py
  - src/shared/packages/pyforge-atlas/tests/unit/singularity/test_duckdb_sole_engine.py
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Code is wrong by an operator ruling. The operator retired `pyforge/atlas/views/` on 2026-09-09 (fleet readiness decision batch § 2.3 C1) and Story 24.1 deleted it on 2026-09-10. A baseline-drift recovery re-landed it on 2026-09-18 (PR #1451) on the premise that it had never merged. It is a second runtime that nothing calls, reads the legacy SQLite database through conda-forge-expert scripts against CAP-36 and the Spec's own Non-goal, and holds three run-dependencies in the member manifests. Ruling 6 of the second addendum: Story 48.3 deletes it again.

**Approach:**
- **Re-run Story 24.1's contract** (`specs/spec-24-1-retire-the-second-lane-3-runtime.md`) against today's tree. Delete the 7 modules under `src/pyforge/atlas/views/` (792 lines) and the 7 files under `tests/unit/views/` (1,003 lines); remove `test_asgi_host_only_in_views_asgi_module` and its constants from `tests/unit/catalog/test_no_inline_io.py`; remove the 'second, INDIRECT exception' paragraph and the cli_bridge lines from `tests/unit/singularity/test_duckdb_sole_engine.py`; drop `bokeh`, `tornado` and `starlette` with their comments from the member `pyproject.toml` and the member `pixi.toml`, byte for byte in step (AUD-ATLAS-010).
- **One story, one commit.** The package, its tests, its two fences and its three run-dependencies leave together so the suite, the singularity gate and the manifest pair stay green. Size L because 1,795 lines are deleted in 14 files; the edited lines are under 100 in four files, and the review reads the path list and those lines.
- **Never (Story 24.1's own list).** Root `pixi.toml`'s `httpx` (`tools/lasuite_bringup.py` needs it), root `starlette` under `feature.mcp-host` and root `bokeh` under `feature.local-recipes` stay; the widget registry is not resurrected. Root `pixi.toml` and `pixi.lock` are steward's: the lock regeneration and the comment at root `pixi.toml` near the views lines are steward Story 124.3's. The Spec text for CAP-44..CAP-47 is Story 46.1's; `docs/reference/library-llms-full.md`'s tornado entry is scribe's.
- The story marks nothing in the deferred-work ledger (the two rows Story 24.1 closed on 'views/ deleted' are true again) and appends nothing to the memlog: Story 48.4 names every deleted path in the reconcile event.

Ledger key: `48-3-the-retired-views-runtime-leaves-the-package-again`.
Type / Effort / Deps: refactor / L / S-48.1.

### Living CAP citations

- `spec-pyforge-atlas` CAP-44..CAP-47 (retired 2026-09-09: the views runtime), CAP-36 (no legacy read through conda-forge-expert scripts); no CAP minted, no FR

## Acceptance Criteria

Each command runs from the worktree root; read every verdict from its exit code, never through a pipe.

- **AC1 — The package and its tests are gone.** Expected: exit 0.

  ```bash
  test ! -e src/shared/packages/pyforge-atlas/src/pyforge/atlas/views && test ! -e src/shared/packages/pyforge-atlas/tests/unit/views
  ```

- **AC2 — Nothing in the package, scripts or the workflows names the module.** Expected: exit 0 (today 20 lines match).

  ```bash
  ! git grep -qE 'atlas\.views|atlas/views|views/(asgi|live|cli_bridge|registry|render|widgets)\.py' -- src/shared/packages/pyforge-atlas scripts .github
  ```

- **AC3 — The three run-dependencies declared for it alone are gone from both member manifests, which stay in step.** Expected: exit 0.

  ```bash
  ! grep -qE '^\s*"?(bokeh|tornado|starlette)\b' src/shared/packages/pyforge-atlas/pyproject.toml && ! grep -qE '^(bokeh|tornado|starlette) = ' src/shared/packages/pyforge-atlas/pixi.toml && ! git grep -qE '^\s*(import|from) (bokeh|tornado|starlette)\b' -- src/shared/packages/pyforge-atlas/src src/shared/packages/pyforge-atlas/tools
  ```

- **AC4 — The station suite, the catalog gate and the singularity gate pass.** Expected: exit 0 for each.

  ```bash
  pixi run --frozen -e pyforge-atlas pyforge-atlas-test && pixi run --frozen -e pyforge-atlas kedro-catalog-check && pixi run --frozen -e pyforge-atlas duckdb-singularity
  ```

- **AC5 — Lint and types hold.** Expected: exit 0.

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

- **AC6 — Post-condition, owned by the request to steward-station: the lock matches the member manifests.** Expected: exit 0 once steward-station has regenerated pixi.lock (the member's run-dependency strings are recorded there; a cached local pixi can false-green this, so read CI's result too).

  ```bash
  pixi lock --check
  ```

## Boundaries & Constraints

**Always:**
- Delete with `git rm` semantics (the files leave the tree); keep both member manifests in step.
- Re-run the station suite, the catalog gate and the singularity gate.

**Never:**
- Never remove root `httpx`, `feature.mcp-host` `starlette` or `feature.local-recipes` `bokeh`.
- Never resurrect the widget registry; never edit root `pixi.toml` or `pixi.lock`.

</intent-contract>

## Binding

- Parent: `spec-pyforge-atlas` CAP-44..CAP-47 (retired 2026-09-09: the views runtime), CAP-36 (no legacy read through conda-forge-expert scripts); no CAP minted, no FR.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-11-10 (cutover readiness) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the entry of that date and its two addenda).
- Epic: Epic 48, minted 2026-11-10 with this story.
- Ledger key: `48-3-the-retired-views-runtime-leaves-the-package-again`.
- Deps: S-48.1.
- Cross-station deps: none.
- Followed by: steward:S-124.3 (regenerates pixi.lock after the member manifests drop the three run-dependencies; it depends on this story, not the reverse).
- Flag: none (`type: refactor`, as Story 24.1 was: it removes a retired runtime and adds no runtime path).
- Surface: `marshal-policy.toml` `[epic_surfaces]."48"`, narrowed by this spec's `surface:`.
- Minted 2026-11-10 in the atlas mint of the one cutover-readiness PR (branch `cutover-readiness-2026-11-10`); built in the same PR.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: exit 0.
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: exit 0.

**Run before the push:** the acceptance commands above, each read from its exit code.

## Auto Run Result

Status: backlog (minted 2026-11-10).

## Spec Change Log

- 2026-11-10: minted from the station Dream's entry of 2026-11-10 (cutover readiness) under the operator's rulings of 2026-11-10 ("Accept all", "Retire both", "Accept all, run mint"). Acceptance adjusted by the rulings: the deletion is ruled (ruling 6 of the second addendum); the plan's 'stop it only on the operator's word' is closed.

- 2026-11-10 (review of the mint): steward:S-124.3 moves from cross-station deps to `Followed by:`; it lists this story among its own deps, so the old line made a cycle.

## Review Triage Log

- (none yet)
