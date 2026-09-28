---
title: '71.7: The one-minute budget is a check that reads the journal'
type: 'feature'
created: '2026-09-27'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-159's success is a number — under 60 s of wall clock for `pr-preflight` on a single-station branch on the 16-core reference laptop — and the Dream asks that it be "a number something checks, not a hope". Stories 71.1–71.6 make the run fast and journal it; nothing yet reads the journal and says when the minute is gone, or which lane took it.

**Approach:** `python -m pyforge.steward.preflight --budget [--seconds 60] [--run <id>]`, registered as a `preflight-budget` task in `[feature.guild-tasks.tasks]`, reads `.steward/preflight-runs.jsonl` and judges the newest run, or the one named. A run is single-station when its journaled selection (Story 71.2) holds at most one of the eight `pyforge-<station>-test` lanes and not `test-ci`. Such a run over the budget exits 1, naming its run id, wall time, the machine's core count and its three slowest lanes with their seconds (the install phase counted as a lane). Any other run — a shared-surface or multi-station branch — is reported against its slowest lane, whose time bounds it, and exits 0: its size is CI's rule, not a defect. An empty, missing or wholly unreadable journal exits 2 — cannot evaluate, never a silent 0; a malformed line is skipped with a warning naming its line number. The check is a separate read: it never runs inside `pr-preflight`, never changes its verdict, and is neither a detector nor a PR gate (it reads a gitignored, machine-local file). The budget is declared once, as the `--seconds` default, with its CAP-159 citation.

Ledger key: `71-7-the-one-minute-budget-is-a-check-that-reads-the-journal`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-71.2, S-71.3, S-71.4, S-71.5, S-71.6.

### Living CAP citations

- `spec-pyforge-steward` CAP-159 (FR-32).

## Acceptance Criteria

- Given a journal whose newest run is single-station at 58 s When `preflight-budget` runs Then it exits 0 and prints the wall time and slowest lane
- Given a journal whose newest run is single-station at 61 s When `preflight-budget` runs Then it exits 1 naming that run, its core count and its three slowest lanes with their seconds
- Given a journal whose newest run is a shared-surface run at 300 s When `preflight-budget` runs Then it exits 0 and reports the run against its slowest lane
- Given an empty or missing journal When `preflight-budget` runs Then it exits 2
- Given a journal with one malformed line and one valid run When `preflight-budget` runs Then it judges the valid run and warns with the malformed line's number
- Given `--run <id>` naming an older run When `preflight-budget` runs Then it judges that run; an id not in the journal exits 2
- Given `pr-preflight` When it runs Then it does not invoke the budget check, and its exit code is independent of it
- Given a marshal-only branch on the 16-core reference laptop with Stories 71.1–71.6 landed When `pr-preflight` then `preflight-budget` run Then the journaled wall time is under 60 s and the check exits 0 (the measured seconds are recorded in this story's run results)

## Boundaries & Constraints

**Always:**
- Exit codes 0 / 1 / 2 as above; the module's own `main()` owns them (AD-8).
- Read only the journal; never re-run a lane to judge it.
- The new task: regenerate `environment.yaml` (`pixi project export conda-environment -e build > environment.yaml`) and `docs/how-to/pixi-tasks.md` (`pixi run -e pyforge-guild docs-pixi-tasks`) in the same change; reconcile and scoped-stamp every Spec `spec-surface-check` names for `pixi.toml`.

**Never:**
- Do not make the check a `depends-on` of `pr-preflight`, a step of the `pre-push` hook, a detector, or a CI lane.
- Do not red a shared-surface run for its length.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| single-station, 58 s | newest run | exit 0 | — |
| single-station, 61 s | newest run | exit 1, three slowest lanes named | — |
| shared surface, 300 s | newest run | exit 0, reported against its slowest lane | — |
| no journal | file absent or empty | exit 2 | cannot evaluate |
| malformed line | one bad JSON line | skipped, line number warned | exit 2 if no valid run remains |
| `--run` unknown | id not journaled | exit 2 | names the id |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-steward` CAP-159 (FR-32).
Dream: `docs/dreams/pyforge-steward.md` § Realization log → *2026-09-27 — Proposed: the preflight answers in under a minute*.
Ledger key: `71-7-the-one-minute-budget-is-a-check-that-reads-the-journal`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- On a marshal-only branch on the 16-core reference laptop: `pixi run -e pyforge-guild pr-preflight`, then `pixi run -e pyforge-guild preflight-budget` — expected: exit 0, wall time under 60 s.
