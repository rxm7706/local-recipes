---
title: '65.1: A drain plan reports every refusal it can decide before launch'
type: 'feature'
created: '2026-09-27'
status: 'backlog'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Nothing in marshal can say what a drain would do before it does it. `dispatch_once`'s first write is `git worktree add`, and neither `marshal factory dispatch` nor `marshal factory drain` has a plan or check flag. Many refusals are decidable before anything launches, yet they fire only after a whole session. `MRS-GATE-010`/`011` (the tracked spec has no `## Verification` → `**Commands:**` section, or declares a command outside the station's `verify_commands`) are evaluated post-session against the primary checkout's tracked spec. `MRS-GATE-003` (a verify command the gate cannot run) and `MRS-DISP-019` (a merge subject that is not marshal-native) also fire late. On 2026-09-27 a hand read of steward's queue found 44.4–44.6 parked only by a "Parked 2026-09-13 … do not dispatch" line in `epics.md`, which no code reads. 44.4's Deps (44.3, 44.12) were `done` and its spec had no `## Verification`, so a steward drain would have dispatched it first and re-dispatched it every cycle, because the drain classes `MRS-GATE-010` transient. The same read found two more things nobody could see without launching: a non-empty `order_overrides` list switches the Story 28.12 Deps sort off even when every key in it is done (`dispatch_fleet.station_backlog`), and in serial mode Deps only order the queue and never gate it (only the parallel wave gates, through `spec_deps.ready_backlog`).

**Approach:** add `--plan` to `marshal factory drain`. It takes drain's own `--mode`, `--station`, `--stories`, `--leave-remaining` and `--max-in-flight`, so the queue it reports is the one the same invocation would drain; `--plan` with `--once`, `--campaign`, `--max-cycles` or `--tick-seconds` is a usage error (exit 2). The per-station queue computation inside `execute_fleet_cycle` is extracted into ONE read-only planner that both `execute_fleet_cycle` and the plan call. It covers the tracked-ledger read (`_station_ledger_statuses`), `station_backlog` with the queue file's overrides and Deps (`_read_fleet_queue_config`), `station_finalize_pending_story`, `_station_blocked_map`, `plan_station_queue`, and in parallel mode `ordered_ready_backlog` plus `build_wave_batch`. The plan cannot drift from the drain because they share this code. The plan runs it as a fresh campaign's first cycle would (no campaign blocks) and never calls `_journal_dispatch_wave`, `dispatch_once` or any other writer. For the next story (and for every queued story with `--all-stories`), the plan evaluates each refusal decidable without launching, through the functions the launch path itself uses:
- scope: `_dispatch_scope_refusal` → `MRS-DISP-041`;
- spec presence: `dispatch_core.resolve_story_spec_path` → `MRS-DISP-005`;
- worktree spec status: `parse_spec_status` with `blocks_harness_relaunch` → `MRS-DISP-045`, or the `MRS-DISP-040` land-only path, reported as land-only and not as a refusal;
- legacy branch: `dispatch_core.resolve_dispatch_branch` → `MRS-DISP-030`;
- leftover worktree state: the existing WIP and pending-finalize reads → `MRS-DISP-036`/`039`;
- binding: `spec_binding.parse_success_signal` with `gate.check_spec_binding` against the guard-appended verify commands (`dispatch_verify._verify_commands_with_surface_guard`) → `MRS-GATE-010`/`011`;
- command shape: `shlex.split` with `dispatch_verify._bare_shell_metacharacters` → `MRS-GATE-003`;
- merge subject: `identity.render_merge_subject` with `merge_subject_is_marshal_native` → `MRS-DISP-019`;
- already landed: the story key is among `promotion.corroborated_merged_story_keys` over `main`'s subjects;
- Deps readiness, in both modes.

The harness binary and authcheck walk (`build_harness.binary_present`) and the session-precondition probe run only with `--check-env`. The pure predicates live in a new `core/dispatch_prelaunch.py` (AD-4): the spec-binding predicate (which Story 65.2 reuses), the prose-park detector ("Parked" or "do not dispatch", case-insensitive, in the story's `epics.md` block or its tracked spec, with no `skip_policies` entry for that station and story) and the inert-override check (an `order_overrides` list whose keys are all `done` or absent from the station's ledger). Reads stay in `cli/`.

**Findings (new namespace; `MRS-PLAN` is taken by planning-graph retrieval, `CODE_PATTERN` admits one token):**

| Code | Tier | Meaning |
|---|---|---|
| `MRS-DRAINPLAN-001` | ERROR | the station's next story would not dispatch cleanly — one finding per reason, naming the station, the story and the would-be code (`MRS-DISP-041/005/045/030/036/039/019`, `MRS-GATE-010/011/003`), `already-landed`, or `prose-park` |
| `MRS-DRAINPLAN-002` | WARN | the same for a queued story beyond the next (with `--all-stories`); and every prose park in the station's backlog that no `skip_policies` entry mirrors, reported always |
| `MRS-DRAINPLAN-003` | WARN | an `order_overrides` list whose keys are all `done` or absent — it changes nothing but switches the Deps sort off |
| `MRS-DRAINPLAN-004` | WARN | the next story's declared Deps are not all `done` — serial mode dispatches it anyway (Deps only order), parallel mode holds it; the message names the mode |
| `MRS-DRAINPLAN-005` | UNEVALUABLE | the station's plan could not be computed (ledger, epics, spec or git read failed) — never a clean plan |

The exit comes from the AD-7 lattice: 4 (ERROR) when any station's next story would not dispatch cleanly, 1 (UNEVALUABLE) when a station's plan cannot be computed, 0 otherwise (WARNs included). The JSON envelope's `data.stations[]` carries, per station: `slug`, `mode`, `parallel_cap`, the ordered `backlog`, the cycle `outcome`, `next_story` (or the wave's members), `would_dispatch`, `refusals` (`{story, code, reason}`), `skipped` (declared skips and advances, with reasons), `deps` and `env_checked`.

Ledger key: `65-1-a-drain-plan-reports-every-refusal-it-can-decide-before-launch`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-274 (FR-220).

## Acceptance Criteria

- Given a fixture replaying steward's 2026-09-27 state (44.3 and 44.12 `done`; 44.4, 44.5 and 44.6 `backlog`, each with "Parked 2026-09-13 … do **not** dispatch" in its `epics.md` block; 44.4's tracked spec without `## Verification`; `skip_policies: []`; a steward `order_overrides` list whose keys are all `done`) When `marshal factory drain --plan --mode drain_to_zero --station pyforge-steward --format json` runs Then `next_story` is 44.4, there is one `MRS-DRAINPLAN-001` finding naming `MRS-GATE-010` and one naming `prose-park`, there are `MRS-DRAINPLAN-002` findings for the 44.5 and 44.6 parks and one `MRS-DRAINPLAN-003` for the override list, and the exit code is 4
- Given the same run When the fakes are inspected Then no file was written, no worktree added, no directory created, no journal line appended and no advisory lock acquired, and `dispatch_once` was never called
- Given the same fixture with `skip_policies` entries for 44.4, 44.5 and 44.6 When the plan runs Then they appear in `skipped` as declared skips with their reasons, none of them is `next_story`, and no `MRS-DRAINPLAN-001`/`002` names them
- Given one shared fixture fleet When the plan runs and `execute_fleet_cycle` runs one cycle against a recording fake `dispatch_once` Then the plan's `next_story` per station (serial) and its wave members (with `--max-in-flight 2` and disjoint declared surfaces) equal the stories the cycle handed to `dispatch_once`
- Given a station whose next story is corroborated merged on `main` while its ledger reads `backlog` When the plan runs Then it reports `MRS-DRAINPLAN-001` naming `already-landed`
- Given a next story whose declared Deps are not all `done` When the plan runs in serial mode Then `MRS-DRAINPLAN-004` names serial mode and the unmet Deps; in parallel mode the story is reported held, not dispatched
- Given a station whose verify command carries bare shell syntax (e.g. `a && b`), or whose `merge_subject_template` renders a subject that is not marshal-native When the plan runs Then `MRS-DRAINPLAN-001` names `MRS-GATE-003` or `MRS-DISP-019` respectively
- Given no `--check-env` When the plan runs Then `build_harness.binary_present` and the session-precondition probe are never called and `env_checked` is false; with `--check-env` a missing harness is reported as `MRS-DRAINPLAN-001` naming `MRS-DISP-003`
- Given a station whose tracked ledger cannot be read When the plan runs Then it reports `MRS-DRAINPLAN-005` for that station and, with no ERROR elsewhere, exits 1
- Given `--plan --once` (or `--campaign`, `--max-cycles`, `--tick-seconds`) When parsed Then it is a usage error (exit 2)
- Given the new codes When `test_findings.py` runs Then `MRS-DRAINPLAN-001..005` are registered with the tiers above

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 65.1. The plan composes the functions the drain and the launch path already use; the only new logic is the extracted planner (moved, not rewritten), the pure predicates in `core/dispatch_prelaunch.py`, and the plan's projection and rendering. The plan runs from the repository root and reads only. Physical `_bmad-output/projects/<slug>/` paths.

**Never:**
- Do not write anything from `--plan`: no worktree, run directory, journal entry, wave journal, campaign journal, lock or supervisor.
- Do not change which story a drain cycle chooses — the extraction is behaviour-preserving, and the existing `test_dispatch_fleet.py` and `test_dispatch.py` expectations stay unchanged.
- Do not honour a prose park in the drain, or add a second park mechanism; `skip_policies` stays the one.
- Do not change the post-session gate (`dispatch_verify.py`), its transient classification (`core/dispatch_retry.py`), or `dispatch_once` (Story 65.2 owns the pre-launch refusal).
- Do not run a harness binary, authcheck or any verify command without `--check-env` (and never run a verify command at all).
- Do not hand-edit `sprint-status-ledger.yaml`, `SPEC.md` or `fleet-drain-queue.yaml`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| steward 44.4 replay | Deps done, spec without Verification, prose park, empty skips, inert overrides | next 44.4; 001 × 2 (GATE-010, prose-park); 002 × 2; 003; exit 4 | none — reported |
| parked in code | `skip_policies` for 44.4–44.6 | listed as declared skips; not next; no 001/002 for them | none |
| clean station | next story binds, no park, Deps done | `would_dispatch: true`; no ERROR | exit 0 |
| already landed | key corroborated on `main`, ledger `backlog` | 001 `already-landed` | none |
| serial Deps unmet | next story's Deps not `done`, `max_parallel = 1` | 004 naming serial mode | none |
| parallel Deps unmet | same, `--max-in-flight 2` | story reported held | none |
| worktree spec blocked | existing dispatch worktree, spec `status: blocked` | 001 naming `MRS-DISP-045` | none |
| worktree spec done | existing worktree, spec `done` | reported land-only (`MRS-DISP-040` path), not a refusal | none |
| env not checked | no `--check-env` | no harness/authcheck/session probe; `env_checked: false` | none |
| ledger unreadable | the station's tracked ledger unreadable | 005 for that station | exit 1 unless an ERROR elsewhere |
| launch-only flags | `--plan` with `--once`/`--campaign`/`--max-cycles`/`--tick-seconds` | usage error | exit 2 |

</intent-contract>

## Source

Contract authored from `docs/dreams/pyforge-marshal.md`'s 2026-09-27 (late night) Realization-log entry ("Proposed: a drain can be asked what it would dispatch before it launches anything") and `spec-pyforge-marshal` CAP-274 with its 2026-09-27 direction entry in the Spec's `.memlog.md` (the file:line evidence), decomposed the same session as Epic 65's mint.

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-274 (FR-220).
Dream: `docs/dreams/pyforge-marshal.md` § Realization log → *2026-09-27 (late night) — Proposed: a drain can be asked what it would dispatch before it launches anything*.
Ledger key: `65-1-a-drain-plan-reports-every-refusal-it-can-decide-before-launch`.
Ledger status at mint: `backlog`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks (read-only; safe from inside a dispatched session):**
- `pixi run -e pyforge-marshal -- marshal factory drain --plan --mode drain_to_zero --format json` — prints one plan per live station and writes nothing (`git status` clean, no new directory under any `dispatch-runs/` or `fleet-drain-runs/`).
