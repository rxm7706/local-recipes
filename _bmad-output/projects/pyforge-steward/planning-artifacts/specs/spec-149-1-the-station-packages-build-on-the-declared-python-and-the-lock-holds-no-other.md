---
title: '149.1: The station packages build on the declared Python, and the lock holds no other'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 149-1-the-station-packages-build-on-the-declared-python-and-the-lock-holds-no-other
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-atlas/pixi.toml'
  - 'src/shared/packages/pyforge-core/pixi.toml'
  - 'src/shared/packages/pyforge-doctor/pixi.toml'
  - 'src/shared/packages/pyforge-herald/pixi.toml'
  - 'src/shared/packages/pyforge-marshal/pixi.toml'
  - 'src/shared/packages/pyforge-mason/pixi.toml'
  - 'src/shared/packages/pyforge-scribe/pixi.toml'
  - 'src/shared/packages/pyforge-steward/pixi.toml'
  - 'src/shared/packages/pyforge-testing-kit/pixi.toml'
  - 'src/shared/packages/pyforge-warden/pixi.toml'
  - 'pixi.lock'
  - 'scripts/target_version_check.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_target_version_check_surfaces.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - pixi.toml
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** After Story 148.1 every environment locks Python 3.14.10, but the lock still holds other Pythons. pixi-build solves a host environment for each station package it builds, and the lock kept those 43 records at 3.14.7 (33), 3.14.8 (3), 3.15.0 (3) and 3.15.2 (4): the host spec, `python = ">=3.14"`, was still satisfied, so the re-lock never solved them again. The `cpython` and `python-gil` metapackages stayed at 3.14.7 in 76 of 87 environment-platform pairs for the same reason.

**Approach:**
- Each station package's `[package.host-dependencies]` pins `python = "3.14.10.*"`, so a lock whose build host runs anything else no longer satisfies it and pixi solves it again. A workspace build variant and a host spec of `*` were both tried first, and neither moved a record.
- `cpython` and `python-gil` are locked once pinned to `3.14.10.*` in the interpreter feature and once without the pin; pixi keeps what it locked.
- `target-version-check` holds the copies to the declaration: a build host pin other than the declared `X.Y.Z.*`, a build host on another Python, or a `libpython`, `cpython` or `python-gil` entry on another version reds it, and its message names the fix.

Ledger key: `149-1-the-station-packages-build-on-the-declared-python-and-the-lock-holds-no-other`.

### Living CAP citations

- spec-pyforge-steward CAP-153 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The declaration in `pixi.toml` stays the one place the version is chosen.
- The run-dependency floor of each package stays `>=3.14`, the floor its consumers need.

**Never:**
- Never move another package of any environment; never run `pixi update`.

## Acceptance Criteria

**Given** the ten station packages and the lock
**When** `target-version-check` reads them
**Then** every build host and every Python package of every environment is the declared version, and the check exits 0

- **AC1 — The tree is clean.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild target-version-check
  ```

- **AC2 — Each new rule is held by a test.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_target_version_check_surfaces.py -q
  ```

</intent-contract>

## Result (2026-11-27)

- The ten station packages pin `python = "3.14.10.*"` in `[package.host-dependencies]`; their run floors stay `>=3.14`. The re-solved lock holds 40 build host records, every one on Python 3.14.10, and the only Python records left in it are 3.14.10.
- `cpython` and `python-gil` are 3.14.10 in every environment-platform pair that has them (82 of 87, as before). In the environments nothing else moved.
- `target-version-check` reads `pixi.lock`'s pixi-build source records and the environments' `libpython`, `cpython` and `python-gil`; on `main`'s lock it names 152 family entries and 43 build hosts, and on this tree it exits 0.
- `test_target_version_check_surfaces.py` seeds the host pin, the family packages and build records, and gains six cases: a build host off the declaration, a family package off it, three host specs that are not the pin (`>=3.14`, `*`, `3.14.7.*`), and a mutation that would hide a build host. 43 pass.
- AC1: exit 0. AC2: 43 passed.
