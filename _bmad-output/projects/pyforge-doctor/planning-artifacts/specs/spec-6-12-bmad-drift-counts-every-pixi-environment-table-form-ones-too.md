---
title: "6.12: bmad-drift counts every pixi environment, table-form ones too"
type: 'fix'
created: '2026-10-04'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py
  - scripts/bmad_drift_check.py
  - _bmad-output/projects/pyforge-marshal/.sync-baseline.json
  - _bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** bmad-drift's pixi-environment count misses every environment declared as its own table.

- **Two copies of one line scan.** Doctor's `_env_count` (`src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py`, Story 6.8's port) and the script it was ported from, `env_count` in `scripts/bmad_drift_check.py`, both count `key = value` lines inside the `[environments]` block and stop at the next `[` header.
- **pixi allows a second form.** `pixi.toml` declares 35 environments inside the block and one more, `python-agent-platform`, as its own `[environments.python-agent-platform]` table (around line 1087). `tomllib.load(...)["environments"]` has 36 keys. Both counters report 35.
- **Every consumer inherits the miss.** The count feeds bmad-drift's ground truth (`pixi_envs`), `check_counts` (`count-stale`), `check_baseline` (`surface-changed`) and the sync baseline the script's `--write-baseline` writes. PR #1862 re-grounded marshal's living docs on 2026-10-04; its banners state 36 and have to explain why the check says 35. The 2026-09-12 baseline's 30 was also one short (31 real), and PR #1862's restamp wrote 35 (36 real).

**Approach:** both counters parse `pixi.toml` with stdlib `tomllib` and count the keys of its `environments` table, which covers both forms.
- In Doctor, an unreadable file still raises `OSError` for the caller's net. A missing file still counts 0. A `pixi.toml` that does not parse returns `None`, the value every other ground-truth fact uses for "could not be read", rather than raising `TOMLDecodeError` past the per-fact `except OSError`.
- In the script, a file that does not parse raises: it is a mutation tool, and writing a baseline over an unparseable manifest should stop.
- After landing, restamp `_bmad-output/projects/pyforge-marshal/.sync-baseline.json` (`python scripts/bmad_drift_check.py --write-baseline`) so `pixi_envs` reads 36, and drop the "it reports 35" clause from the re-ground banners.

Ledger key: `6-12-bmad-drift-counts-every-pixi-environment-table-form-ones-too`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 6.8 (FR-15, bmad-drift comes home). This is a defect of shipped behaviour, so it mints no new CAP. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.

## Acceptance Criteria

- Given a `pixi.toml` with environments inside `[environments]` and one more as an `[environments.<name>]` table When Doctor's ground truth and the script's `env_count` run Then both count every environment
- Given the live `pixi.toml` When `python -m pyforge.doctor.sources bmad-drift --groundtruth` runs Then `pixi_envs` is 36
- Given a `pixi.toml` that does not parse When Doctor's ground truth runs Then `pixi_envs` is `None` and the other facts are still read
- Given a missing `pixi.toml` When Doctor counts Then it is 0, as before; given an unreadable one Then the caller's `except OSError` still applies
- Given either counter reverted to the line scan When the tests run Then the table-form test fails (mutation)

## Boundaries & Constraints

**Always:**
- Keep both counters in step: the script writes the baseline Doctor compares against.
- Keep Doctor's never-raise-past-the-net contract for a bad manifest.

**Never:**
- Never import `pyforge.doctor` from the script, or the script from Doctor (Story 6.10, independence is structural).
- Never hand-edit `.sync-baseline.json`; restamp it with the script.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-04 (env count) entry.
- Epic: Epic 6. It reopens (operator ruling, 2026-10-04: a fix joins its own epic and reopens it). Story 6.8 built `_env_count`.
- Ledger key: `6-12-bmad-drift-counts-every-pixi-environment-table-form-ones-too`.
- Ledger status at mint: `in-progress`.
- Deps: —.
- Minted 2026-10-04 at the operator's request: "Fix bmad-drift env count missing table-form envs", found while re-grounding marshal's living docs (PR #1862). Hand-built and hand-landed in one PR with its chain.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks:**
- `python -m pyforge.doctor.sources bmad-drift --groundtruth` (pyforge-guild env) prints `"pixi_envs": 36`.
- `pixi run --frozen -e pyforge-guild bmad-drift-check` exits 0 with no `surface-changed` warn after the restamp.

## Review Triage Log

### 2026-10-04 — Build (hand-built in `chain-doctor-6-12`)
- Doctor's two counter tests, the two script tests and the live-manifest checks pass; reverting either counter to the line scan fails its table-form test.
- The doctor feed's `epic-41` row read `in-progress` after Story 41.6's landing promoted the twin to `done`; the sync refused until the feed was reconciled to the twin.
- The scoped doctor stamp also took in `sources/board.py` and two board tests; the Story 41.6 memlog entry already names them.

### 2026-10-04 — Independent review (against this spec): no HIGH, one MEDIUM, four LOW; all fixed in the branch
- MEDIUM: the scoped `spec-pyforge-core` stamp absorbed `pixi.toml`'s hash change from marshal Story 19.5 (#1859), which reconciled only `spec-pyforge-marshal`. Fixed: a co-governor catch-up entry on `spec-pyforge-core` names `pixi.toml`, then a re-stamp.
- LOW: the script counted a non-table `environments` (a string or list) where Doctor reads it as unknown. Fixed: the script raises; a test pins each side.
- LOW: the script comment claimed `--write-baseline` never stamps a count it could not read, but an unreadable file still reads as `""`. Reworded to "could not parse", naming the old behaviour.
- LOW: no test covered Doctor's non-table branch or the gather path with an unparseable manifest. Added both.
- LOW: the spec's baseline figure described the 2026-09-12 baseline, not `main`'s. Both figures are now stated.
