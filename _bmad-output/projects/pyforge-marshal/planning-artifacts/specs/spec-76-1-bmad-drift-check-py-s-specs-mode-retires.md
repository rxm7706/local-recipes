---
title: "76.1: bmad_drift_check.py's --specs mode retires"
type: 'chore'
created: '2026-09-29'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '2157e66d12c7306777f98b02fe25ee3080f432c5'
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - scripts/bmad_drift_check.py
  - scripts/fleet_scan.py
  - _bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-one-chain-per-station:CAP-11` (operator ruling 2026-09-29) retires `docs/specs/`; doctor Story 37.1
empties it. `scripts/bmad_drift_check.py --specs` (`DOCS_SPECS` ~line 85, `cmd_specs` ~lines 463-480, the flag ~line 488)
prints each `docs/specs/*.md` status and whether `CLAUDE.md` indexes it. No pixi task or detector calls it; it is a manual
residual. Once the tier is gone the mode reports nothing.

Three more marshal files still describe the tier:
- `scripts/fleet_scan.py` (~line 2257) cites `docs/specs/presentation-deck.md`.
- `SYNC-RUNBOOK.md` lists `docs/specs/` in the source-of-truth surface that "the baseline check (`surface-changed`)
  detects". That was already untrue: doctor's `FINGERPRINT_KEYS` never covered `docs/specs/`.
- `SYNC-RUNBOOK.md` also names `docs/specs` in its out-of-band `git diff` command and has a `docs-specs-nonmd` row in its
  finding table.

CHAIN-STANDARD §11 requires every reader to follow before the PR that empties the directory.

**Approach:**
- Remove the `--specs` mode, `DOCS_SPECS` and `cmd_specs`, with their help and docstring lines.
- Add a test that `--specs` is rejected.
- Point `fleet_scan.py`'s comment at `docs/how-to/presentation-deck.md`.
- Take `docs/specs/` out of the runbook's surface list and `git diff` command, and its `docs-specs-nonmd` row out of the
  table.

The other modes, and marshal's seed templates, are unchanged. The seed templates teach Tier 1 to other repositories, and
this ruling is this repository's. The `AGENTS.md` sentence that names `--specs` leaves in Story 37.1.

Ledger key: `76-1-bmad-drift-check-py-s-specs-mode-retires`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- `spec-one-chain-per-station:CAP-11` (the Guild's; Marshal mints no CAP and no FR, as Epics 74 and 75 do); CHAIN-STANDARD
  §11.
- `spec-dream-to-code-model-self-verification` (governs `scripts/bmad_drift_check.py`); `spec-pyforge-marshal` (governs
  `scripts/fleet_scan.py`).
- `spec-feature-flag-governance` Q1: a `chore` needs no flag.
- Siblings: doctor Story 37.1 (blocked on this story), atlas Story 26.1, steward Story 77.1, herald Story 34.1.

## Acceptance Criteria

- Given the script When `python scripts/bmad_drift_check.py --specs` runs Then it exits 2 with argparse's
  unrecognised-argument message
- Given each other mode (`--groundtruth`, `--fix`, `--json`, `--write-baseline`) When it runs on today's tree Then its
  output is what it was before the change
- Given `SYNC-RUNBOOK.md` and `scripts/fleet_scan.py` When `git grep "docs/specs"` runs over them Then it finds nothing
- Given a test for the retired flag When the flag is restored Then the test fails (mutation)
- Given the marshal suite When `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` runs Then it passes

## Tasks

1. Read `scripts/bmad_drift_check.py`, the runbook and `fleet_scan.py`'s comment.
2. Remove the mode, and add the rejected-flag test under `tests/scripts/`.
3. Edit the runbook and the comment.
4. Run `pixi run -e pyforge-guild python -m pytest tests/scripts -q -k drift` and `pixi run --frozen -e pyforge-marshal
   pyforge-marshal-test`, and read each exit code.
5. Reconcile every Spec `spec-surface-check` names: memlog first, `git add`, then a scoped `--write-baseline --spec` for
   each (expected: `spec-dream-to-code-model-self-verification`, `spec-pyforge-marshal`).

## Boundaries & Constraints

**Always:**
- Keep every other mode's behaviour and output unchanged.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not edit marshal's seed templates.
- Do not move or edit anything under `docs/specs/` in this story.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| retired flag | `--specs` | exit 2, unrecognised argument | — |
| other modes | `--groundtruth`, `--fix`, `--json`, `--write-baseline` | unchanged | — |
| seed templates | `seed/templates/*` naming `docs/specs` | unchanged | out of scope |

</intent-contract>

## Code Map

Line numbers are from `2157e66d12`; measured, not copied from the intent.

- `scripts/bmad_drift_check.py` -- edit. Module docstring names `--specs` at 2, 20-30, 52. `DOCS_SPECS` at 85.
  `frontmatter_status` at 237-244 has `cmd_specs` as its only caller (`git grep` over `scripts src tests .claude`; the
  `_frontmatter_status` twins in doctor and scribe are separate functions), so it goes with it. `cmd_specs` at 463-480.
  The argparse flag at 488-489 and its dispatch at 500-501. The bare-run stderr message at 530-535 also lists `--specs`.
  Keep `_read` (many callers), `classify`, `TRACKED`.
- `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md` -- edit. `docs/specs/` at 46 (surface list), 76 (`git diff`
  paths), 84 (`tracked-impl-artifact` remedy) and 85 (`docs-specs-nonmd` row). The intent named 46, 76 and 85; line 84
  is the fourth hit and the "finds nothing" AC needs it gone too.
- `scripts/fleet_scan.py` -- edit two comments. 1126 (specs-roster header: "docs/specs legacy is deliberately out"; the
  intent named only the second hit) and 2294 (the 6-artifact family standard, cited to `docs/specs/presentation-deck.md`;
  the intent said ~2257).
- `tests/scripts/test_bmad_drift_check_specs_retired.py` -- new. No `bmad_drift_check` test exists in `tests/scripts/`;
  style follows `test_bmad_loop_baseline_drift_check.py` (importlib-load the script by path).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/{development-guide.md:244,443, source-tree-analysis.md:588,
  project-overview.md:437}` -- edit. These describe `--specs` as a live mode; removing the mode makes them false, so the
  same change fixes them (AGENTS.md § Behavioural guidelines 3).
- Read-only. `pyforge-doctor/.../sources/factory.py` `FINGERPRINT_KEYS` (257-265) has no `docs/specs`, which confirms the
  runbook claim was already untrue. Its `docs-specs-nonmd` emitter and `_docs_specs` stay: doctor Story 37.1's.
  `docs/how-to/presentation-deck.md` is the deck standard's home. Marshal seed templates: out of scope.
- Pre-change baseline (scratchpad): `--json` and `--groundtruth` are byte-identical, 229 bytes; a bare run exits 2.

## Spec Change Log

## Binding

Parent capability: `spec-one-chain-per-station:CAP-11` (Guild relay; no marshal CAP or FR).
Dream: `docs/dreams/one-chain-per-station.md` → § *2026-09-29 — One archive home*.
Ledger key: `76-1-bmad-drift-check-py-s-specs-mode-retires`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `chore` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `python scripts/bmad_drift_check.py --specs; echo $?` — expected: `2`.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
