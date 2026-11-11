---
title: '124.3: Core''s, the kit''s and steward''s manifests state Python 3.14, a check holds every package floor, and the lock follows'
type: 'feature'
created: '2026-11-10'
status: 'backlog'
flag-exempt: detector-or-gate
difficulty: medium
story: 124.3
spec: pyforge-steward
surface:
  - src/shared/packages/pyforge-core/pixi.toml
  - src/shared/packages/pyforge-testing-kit/pixi.toml
  - src/shared/packages/pyforge-steward/pixi.toml
  - src/shared/packages/pyforge-marshal/pixi.toml
  - src/shared/packages/pyforge-warden/pixi.toml
  - pixi.lock
  - scripts/target_version_check.py
  - src/shared/packages/pyforge-steward/tests/unit/test_target_version_check_surfaces.py
  - src/platform/uv.lock
  - environment.yaml
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

**Problem:** Decision D6: package manifests state a floor the code cannot run on, and the check that claims every floor reads none of them.

**Approach:** The six station stories in the cross-station deps change their own `python` lines; each asked this unit only for the re-lock, so the lock moves once, after all of them (`pixi lock`, never `pixi update`). Lines the re-lock may move are named before it runs: each pyforge-* path record's `python` floor, atlas's and scribe's run-dependency strings, and their hashes. If pixi keeps a stale record, evicting environment blocks is the fallback only after the allowed movement is written in this spec.

Ledger key: `124-3-core-s-the-kit-s-and-steward-s-manifests-state-python-3-14-a-check-holds-every-package-floor-and-the-lock-follows`. Type / Effort / Deps: feature / M / S-124.1, S-124.2.

### Living CAP citations

- **`spec-pyforge-steward` CAP-153** — the floors `target-version-check` holds, as Story 122.1 amends it to include each package `pixi.toml`'s host and run `python`.

## Boundaries & Constraints

**Always:**
- Run `pyforge-station-tests` first: a pixi.lock change fires core and all eight station suites in CI.
- Hold the PostgreSQL 17 caps either way.

**Never:**
- Never run `pixi update` or raise a postgresql/libpq pin or lift a psycopg/pgvector cap.
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — no 3.12 floor in any package manifest.** Expected: exit 1 (no match), once the six station stories in deps have landed.
  ```bash
  grep -nE '^python = ">=3\.12"' src/shared/packages/pyforge-*/pixi.toml
  ```
- **AC2 — the check passes and reads the manifests.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild target-version-check
  ```
- **AC3 — the check can fire.** Expected: exit 0, including a case where a fixture package pixi.toml (under tmp_path) at >=3.12 in host or run dependencies makes the script exit 1 and name the file; the test reads fixtures only, so no workflow path array changes.
  ```bash
  pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit/test_target_version_check_surfaces.py -q
  ```
- **AC4 — the stub is gone.** Expected: prints 0.
  ```bash
  git ls-files src/platform/uv.lock | wc -l
  ```
- **AC5 — the lock matches in a fresh clone.** Expected: exit 0 (a cached local pixi false-greens a drifted path-dependency string; the clean clone is the proof; herald's check moved here from Story 52.2).
  ```bash
  git clone --shared . "$SCRATCH/floors-clone" && for e in pyforge-guild pyforge-herald pyforge-scribe pyforge-atlas pyforge-mason pyforge-warden pyforge-marshal; do pixi install --locked -e $e --manifest-path "$SCRATCH/floors-clone/pixi.toml" || exit 1; done
  ```
- **AC6 — every suite on the new lock.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild pyforge-station-tests
  ```
- **AC7 — no PostgreSQL or psycopg pin moved.** Expected: prints 0 (BASE is the `baseline_revision` in this story's spec frontmatter).
  ```bash
  git diff "$BASE"..HEAD -- pixi.lock | grep -cE '^[+-].*(postgresql|libpq|psycopg|pgvector)'
  ```
- **AC8 — only python floors moved in the lock's path records.** Expected: prints 0, or every remaining line is named in the story spec with its reason before the re-lock ran.
  ```bash
  git diff "$BASE"..HEAD -- pixi.lock | grep -E '^[+-] ' | grep -vcE 'python >=3\.1[24]|sha256|input:|hash:|globs:|bokeh|tornado|starlette'
  ```
- **AC9 — Platform CI's test job on the new lock.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild platform-ci-local -- --test
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-153

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 124.
- Ledger key: `124-3-core-s-the-kit-s-and-steward-s-manifests-state-python-3-14-a-check-holds-every-package-floor-and-the-lock-follows` (`backlog` at mint).
- Deps: S-124.1, S-124.2.
- Surface: `src/shared/packages/pyforge-core/pixi.toml` (the two `python` lines and the comment on :28), `src/shared/packages/pyforge-testing-kit/pixi.toml` (the two `python` lines), `src/shared/packages/pyforge-steward/pixi.toml` (the two `python` lines), `src/shared/packages/pyforge-marshal/pixi.toml` (the two `python` lines; granted by marshal), `src/shared/packages/pyforge-warden/pixi.toml` (the two `python` lines and the comment at :11-12; ceded by warden), `pixi.lock`, `scripts/target_version_check.py`, `src/shared/packages/pyforge-steward/tests/unit/test_target_version_check_surfaces.py`, `src/platform/uv.lock` (removed), `environment.yaml` (only through `pyforge steward estate reconcile` if the re-lock moves it).
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `grep -nE '^python = ">=3\.12"' src/shared/packages/pyforge-*/pixi.toml` — expected: exit 1 (no match), once the six station stories in deps have landed.
- `pixi run --frozen -e pyforge-guild target-version-check` — expected: exit 0.

## Notes

- Cross-station deps (the stories in which each station changes its own `python` line, and the run-dependency strings): warden:S-25.3, scribe:S-33.2, mason:S-37.3, atlas:S-48.1, atlas:S-48.3, herald:S-52.2, marshal:S-114.2.
- Re-lock procedure: `git clone --shared . "$SCRATCH/relock"`, then `PIXI_CACHE_DIR="$SCRATCH/pixi-cache-empty" pixi lock` in that clone; copy pixi.lock back; verify with `pixi install --locked` in a second fresh clone.
- src/platform/uv.lock came from commit 41c3bdd772 ('wip: 94.1 (auto-checkpoint)'); it is not a .py file, so the src/platform import guard does not fire.
- `$BASE` in the acceptance criteria is the `baseline_revision` the build writes into this spec's frontmatter when it starts (the commit it starts from); it is not set at mint.
- No build story appends a `Surface reconcile` line to another Spec's memlog or runs `spec_surface_check.py --write-baseline`: each Spec's own closer writes its reconcile event from `git diff --name-only origin/main...HEAD` (steward and host: Story 122.5) and doctor Story 58.4 runs every scoped stamp once, after the last edit.
