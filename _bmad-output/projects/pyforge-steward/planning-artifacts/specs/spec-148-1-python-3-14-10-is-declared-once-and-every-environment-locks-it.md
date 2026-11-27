---
title: '148.1: Python 3.14.10 is declared once, and every environment locks it'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 148-1-python-3-14-10-is-declared-once-and-every-environment-locks-it
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'pixi.toml'
  - 'pixi.lock'
  - 'environment.yaml'
  - 'docs/reference/library-llms-full.md'
  - 'docs/governance/pin-policy.yaml'
  - 'tests/packaging/test_bmad_suite_full_feature.py'
  - 'src/shared/packages/pyforge-marshal/tests/meta/test_ad65_lean_env_conda_forge.py'
  - 'src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - scripts/target_version_check.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `pixi.toml` named `python` in eleven tables: the root `[dependencies]` and ten features, at `>=3.14.7,3.14.*`, `3.14.*` or `>=3.12`. Fourteen of the 36 environments composed none of them, so their Python came from whatever their packages allowed: `pyforge-marshal` locked 3.15.0 while the other 35 locked 3.14.7.

**Approach:** One table declares Python, `[feature.interpreter.dependencies] python = "3.14.10.*"`. No other table names `python`, and every environment lists the `interpreter` feature first. The lock is re-solved with pixi 0.85.0 (`pixi exec --spec pixi=0.85.0 -- pixi lock`), the version that writes it in CI too (Story 148.2), and `environment.yaml` is exported again. The library catalog's Python lines say where the version is declared.

Ledger key: `148-1-python-3-14-10-is-declared-once-and-every-environment-locks-it`.

### Living CAP citations

- spec-pyforge-steward CAP-153 (one interpreter, every target and floor matching it; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Only what Python 3.14.10's own build requires, `pyforge-marshal`'s rebuild for cp314, and nodejs inside its LTS pin may move in the lock.

**Never:**
- Never move nodejs off `>=24.19.0,<27.0,!=25.*`, and never run `pixi update`.

## Acceptance Criteria

**Given** the manifest with one Python declaration
**When** the lock is re-solved
**Then** every environment locks Python 3.14.10 on every platform it locks

- **AC1 — One declaration, every environment, one locked version.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild target-version-check
  ```

- **AC2 — The library catalog agrees with the manifest.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild llms-full-check
  ```

</intent-contract>

## Result (2026-11-27)

- `[feature.interpreter.dependencies] python = "3.14.10.*"` is the one declaration; eleven `python` lines left the root `[dependencies]` and ten features, and all 36 environments list `interpreter` first. conda-forge carries Python 3.14.10 for linux-64, osx-arm64 and win-64.
- The lock, re-solved by pixi 0.85.0 in 11 s, holds Python 3.14.10 in all 87 environment-platform pairs. What else moved, counted in environment-platform pairs: `libsqlite` 3.53.4 to 3.54.1 (82), `libexpat` 2.8.5 to 2.11.0 (21), `zstd` 1.5.7 to 1.6.0 (19), `icu` 78.3 to 79.1 (13), `apsw` and `sqlite` with `libsqlite`; nodejs 26.10.0 to 26.13.1 where it moved with `icu`, and with it `c-ares`, `libabseil`, `libbrotli*` and `libnghttp2` in `detectors` and `pyforge-steward`, plus `grpcio` in `pyforge-steward`. `pyforge-marshal` left 3.15.0 and rebuilt for cp314 (`grimp`, `regex`, `watchfiles`, `websockets`; `uv` 0.12.19 to 0.13.10 on win-64).
- The first solve took nodejs 22.23.5 in `pyforge-steward`, where `bmad-eval-quality` pulls nodejs in unpinned. The steward feature now carries the estate's LTS pin, `nodejs = ">=24.19.0,<27.0,!=25.*"`, with its comment, and the second solve keeps 26.13.1.
- `environment.yaml` is exported again by pixi 0.85.0: `python 3.14.10.*` and `pixi >=0.85.0`. `docs/reference/library-llms-full.md` names the declaration, and its table no longer says three platform environments are on 3.12 (they moved to 3.14 in Story 43.6).
- `docs/governance/pin-policy.yaml` held python in eight per-feature `3.14.*` rows, which `pin_policy_check` read as dangling holds once those features stopped declaring python. One exact `3.14.10.*` hold on the `interpreter` feature replaces them, and nodejs's `<27.0` cap row adds `pyforge-steward`.
- What followed from it in the full preflight: two tests that pinned an environment's feature list (`bmad-suite-full`, `pyforge-marshal`) now expect `interpreter` first; and marshal's live half, which had run on 3.15, met Python 3.14's dataclasses resolving string annotations through `sys.modules[cls.__module__]`. The two loaders in `test_promote_sprint_status_regressions.py` that run `scripts/promote_sprint_status.py` and `scripts/fleet_scan.py` from a file now register the module first, and the 16 errors in its eight tests are gone.
- AC1: `target-version-check` exits 0. AC2: `llms-full-check` exits 0.
