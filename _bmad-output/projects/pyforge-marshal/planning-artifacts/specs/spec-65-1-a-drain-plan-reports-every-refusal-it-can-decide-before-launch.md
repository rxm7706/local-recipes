---
title: '65.1: A drain plan reports every refusal it can decide before launch'
type: 'feature'
created: '2026-09-27'
status: 'done'
baseline_revision: '8ed023218fc075e8ddc58403331f4990cb4ee156'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings:
  - oversized
deferred:
  - summary: >-
      The prose-park detector flags tracked specs and epics blocks that only quote or negate the marker, so a false
      match on a station's next story reads MRS-DRAINPLAN-001 (ERROR, exit 4).
    evidence: |-
      The intent-contract defines the detector literally ("Parked" or "do not dispatch", case-insensitive, anywhere in
      the story's epics.md block or its tracked spec), and the implementation follows it. Run over the 1,212 tracked
      spec-N-*.md files it matches 32; five are live backlog stories: marshal 65.2, 66.1 and 73.2 (boundary bullets such
      as "Do not dispatch a follow-up whose row is closed"), herald 28.1 ("parked; inherits the smaller tree") and
      mason 25.2 (a table cell). Steward 44.2, 44.9, 44.10 and 44.11 match on "Do not dispatch outward ... work without
      operator confirmation". Tightening it (a marker-line form, negation and fenced-code handling) changes the
      contract, which is read-only in a build run and is amended only through the Spec memlog and bmad-spec.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_prelaunch.py:113
    severity: medium
  - summary: >-
      A serial station with a live session reads would_dispatch true in the plan, while the drain relays it as
      in-flight (MRS-DRAIN-006 WARN) after dispatch_once refuses with MRS-DISP-011/021.
    evidence: |-
      plan_station_cycle's serial branch returns the queue head without a liveness read (the parallel branch reads
      _live_dispatch_story_keys), and evaluate_story never calls station_in_flight_conflict, which dispatch_once runs.
      The intent's evaluated-refusal list and MRS-DRAINPLAN-001's would-be codes exclude MRS-DISP-011/021, so how a busy
      station maps to the plan's outcome, findings and exit code is a Spec decision (the drain's own reading is an
      in-flight WARN, never a refusal).
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py:3890
    severity: medium
  - summary: >-
      Pre-existing crash: with more than one story in flight allowed, an empty parallel wave makes execute_fleet_cycle
      raise ValueError from StationCycleStatus(plan.outcome.value).
    evidence: |-
      When the wave has no members (a missing spec, an unknown surface, or unmet Deps on every ready story),
      stories_to_dispatch is empty and the cycle builds StationCycleResult with StationCycleStatus("dispatch"), which is
      not a member of the enum. Reproduced on a marshal station, whose policy has max_parallel 2, and confirmed by
      reading the pre-change code. Which status an empty wave should report (in-flight keeps the supervisor ticking,
      blocked or all-skipped stops it) is a supervisor-semantics decision, and this story's Boundaries require the
      extraction to preserve cycle behaviour. The plan reports the same case as outcome held and does not crash.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py:4317
    severity: high
declared_low_risk: false
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

## Code Map

All under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` abbreviated `M/`).

- `M/cli/dispatch.py` -- `execute_fleet_cycle` (`:3756`) holds the per-station queue computation to extract: ledger read `_station_ledger_statuses` (`:3324`), `station_backlog` + `_load_station_story_deps` (`:3505`; the Deps sort is skipped when `overrides.get(slug)` is non-empty), `station_finalize_pending_story` (`:1410`), `_station_blocked_map` (`:3607`), `plan_station_queue`, then `resolve_max_parallel` (`:1359`), `_live_dispatch_story_keys` (`:1380`), `_load_station_deps_graph` (`:1330`), `ordered_ready_backlog`, per-story `_effective_surface_for_spec` (`:1339`) and `build_wave_batch`. Its writers stay in the cycle: `_journal_dispatch_wave` (`:3712`), `dispatch_once` (`:2024`), campaign-block bookkeeping. `run_fleet_drain` (`:4414`) parses and validates the flags, then mints the run dir, takes the lock and journals; `add_factory_drain_subparser` (`:3154`) defines the flags. `_read_fleet_queue_config` (`:3527`) returns `(overrides, skips, findings)`.
- Launch-path refusals the plan mirrors, all in `dispatch_once` (`:2024`): scope `_dispatch_scope_refusal` (`:280`, `MRS-DISP-041`); spec `dispatch_core.resolve_story_spec_path` (`MRS-DISP-005`); harness walk `build_harness.binary_present` (`MRS-DISP-003`) and `_surface_session_precondition_findings` (`:458`) -- `--check-env` only; legacy branch `dispatch_core.resolve_dispatch_branch` (`M/core/dispatch.py:463`, `MRS-DISP-030`, read-only); WIP `_surface_worktree_wip_before_dispatch` (`:421`, `MRS-DISP-036`) and `_redispatch_blocked_pending_supervisor_finalize` (`:893`, `MRS-DISP-039`); worktree spec status `parse_spec_status` / `blocks_harness_relaunch` (`M/core/dispatch_harness_done.py:115,133`) -> `MRS-DISP-040` land-only or `MRS-DISP-045`. `_ensure_dispatch_worktree` (`:1009`) is the WRITER (`vcs.add_worktree`); the plan calls only `resolve_dispatch_branch` and `vcs.worktree_path_for_branch`.
- `M/core/dispatch_fleet.py` -- `station_backlog` (`:543`), `plan_station_queue` (`:707`), `build_wave_batch` (`:869`), `ordered_ready_backlog` (`:930`), `_STORY_HEADING_RE` / `parse_epics_dependencies` (`:389`, `:432`: the `### Story N.M:` block splitter the prose-park detector reuses), `StationQueuePlan` / `StationCycleStatus`, `queue_config_path`, `station_epics_paths`.
- `M/core/gate.py:646` `check_spec_binding`, `M/core/spec_binding.py:106` `parse_success_signal` (`None` = no `## Verification`), `M/dispatch_verify.py:76` `_verify_commands_with_surface_guard` and `:45` `_bare_shell_metacharacters` (`MRS-GATE-003` shape; pre-existing, unchanged), `M/core/identity.py:226` `render_merge_subject`, `M/core/dispatch_landing.py:180` `merge_subject_is_marshal_native` (`MRS-DISP-019`), `M/core/promotion.py` `corroborated_merged_story_keys` (already-landed; the same call `_reconcile_campaign_blocked` makes).
- `M/core/findings.py` (`REGISTERED_CODES`, `CODE_PATTERN` `:903` admits `MRS-DRAINPLAN-001`), `M/core/verdict.py` (`_CLASSIFY_TABLE`; exit lattice ERROR 4 / UNEVALUABLE 1 / WARN 0; `EXIT_USAGE = 2` is a handler-returnable domain member) and `tests/unit/test_findings.py` (the expected-code set) -- the three places a code is registered.
- New: `M/core/dispatch_prelaunch.py` (pure, AD-4, no I/O): `spec_binding_findings`, `find_prose_park`, `story_epics_blocks`, `inert_override_keys`. New: `M/cli/drain_plan.py` (reads, projection, findings, rendering); `run_fleet_drain` reaches it through a function-local import (the `cli/gate.py` precedent, load-order safe).
- Tests fake the ports with `FakeFs` / `FakeVcs` / `FakeBuildHarness` / `FakeProcess` / `FakeHarness` and `_seed_fleet` in `tests/unit/test_dispatch_fleet.py:361-580` (`FakeFs` writes through, so the no-write assertions need a recording variant). Read-only evidence: `_bmad-output/projects/pyforge-marshal/planning-artifacts/fleet-drain-queue.yaml` already declares the 44.4-44.6 skips (2026-09-27), so the steward replay is a fixture, not live state.
- Baseline before any change: `tests/unit/test_dispatch_fleet.py` 145 passed.
- Meta tests that can red a new code, flag or module: `tests/meta/test_ad3_ad4_import_linter.py` (core imports), `test_ad7_verdict_sole_ownership.py`, `test_ad11_write_boundary.py`, `test_ad39_envelope_consistency.py`, `test_cli_tool_parity.py`, `test_tool_surface_coverage.py`, `test_finding_remedy_reference_sync.py`.

## Tasks & Acceptance

**Execution:**
- `M/core/dispatch_prelaunch.py` -- new pure predicates (spec binding, prose park, inert override, epics block split) -- the plan and Story 65.2 share them
- `M/core/findings.py`, `M/core/verdict.py`, `tests/unit/test_findings.py` -- register `MRS-DRAINPLAN-001..005` at ERROR / WARN / WARN / WARN / UNEVALUABLE
- `M/cli/dispatch.py` -- extract `resolve_cycle_slugs` and one read-only `plan_station_cycle` (behaviour-preserving) and have `execute_fleet_cycle` call them; add `--plan`, `--check-env`, `--all-stories`; usage-error the launch-only flags; branch `run_fleet_drain` to the plan before anything is minted
- `M/cli/drain_plan.py` -- per-station refusal evaluation, `data.stations[]` projection, findings, text rendering, exit via the lattice
- `tests/unit/test_dispatch_prelaunch.py`, `tests/unit/test_drain_plan.py` -- one test per Acceptance Criterion plus the I/O matrix rows; existing `test_dispatch_fleet.py` / `test_dispatch.py` untouched and green
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` and each co-governor `spec-surface` names -- surface-reconcile entry (never `--write-baseline`)

**Acceptance Criteria:**
- Given the Acceptance Criteria above, when the station suite runs, then every one has a passing test and `test_dispatch_fleet.py` / `test_dispatch.py` still pass unchanged.

## Spec Change Log

- 2026-09-30: planned from the pre-authored contract; the file was minted at `status: backlog` (not a recognised workflow status), so the tracked spec stays the story spec of record and moves `ready-for-dev` -> `in-progress` in place; no second copy under `implementation-artifacts/`. Intent contract unchanged.

## Review Triage Log

### 2026-09-30 — Review pass
- verdicts: 42 findings — high 0, medium 14, low 23, false 5, maybe-false 0
- findings (Blind Hunter, 13):
  - `[medium]` `[patch]` BH1 refusals on wave members after the first are graded WARN and `would_dispatch` reads only `targets[0]` — verified in `_plan_station` (`is_next = refusal.story == next_story`); the cycle hands every member to `dispatch_once`. Applied: both keyed to `refusal.story in handed` (every story handed to `dispatch_once`); `held` also lists every story the wave refused; test added for a refused second member and for a held head staying a 002 WARN.
  - `[low]` `[reject]` BH2 `inert_override_keys` treats only `done` as inert, not `review`/`blocked` (`NON_IMPLEMENT_STATUSES`) — real but the contract names exactly "done or absent"; override lists were pruned to `{}` on 2026-09-27, so a list of only review/blocked keys is a transient state; the fix departs from the contract wording.
  - `[medium]` `[defer]` BH3 prose-park detector is literal and flags non-parks at ERROR when the story is next — verified: 32 of 1212 tracked specs match, 5 live backlog ones; the contract defines the detector as "Parked" or "do not dispatch" anywhere in the block or spec, so tightening it edits the contract. Routed `defer` although the taxonomy's `intent_gap` is the literal fit (root cause inside the intent-contract): the contract states the behaviour exactly and the code matches it, so reverting a fully verified story to re-open a stated design choice was judged worse than a named deferral. The operator/Spec decision is recorded under `deferred:` and in the residual risks.
  - `[low]` `[reject]` BH4 `evaluate_story` and `_check_environment` hand-mirror the launch path's order and the private-name imports — the contract prescribes composing those named private functions, and `dispatch_once` (Story 65.2) is out of bounds; extracting a read-only half of `dispatch_once` is Dream-sized and forbidden by Boundaries.
  - `[low]` `[reject]` BH5 `--check-env` reporting inconsistencies (`env_checked` mirrors the flag as the AC defines it, `env` only when a story was evaluated, harness walk uses the first story) — no false assurance for a station with nothing to launch; the untested non-ok session branch is patched under G2.
  - `[low]` `[reject]` BH6 wave refusals and an empty wave raise no finding in the plan — the payload carries `wave.refused` and `outcome: held`, which is what the contract asks for ("reported held"); emitting `MRS-DRAIN-016` relays would add surface.
  - `[low]` `[reject]` BH7 text form omits wave members, parks and deps — the JSON envelope is the contract's surface (every AC runs `--format json`); the text form still prints every finding, including 002/004.
  - `[medium]` `[patch]` BH8 JSON projection uneven: the 005 row lacks `parallel_cap` (named by the contract) and other keys; two would-be-code comments omit `MRS-DISP-002/003` — verified in `_unevaluable`. Applied: one `_station_row` skeleton builds both the computed and the 005 row; the `findings.py` comment and the `Refusal` docstring now list `MRS-DISP-002/003`; test pins the key superset. The free-form `already-landed`/`prose-park` codes are the contract's own; no schema is required (AGENTS.md § workspace-package conventions).
  - `[low]` `[reject]` BH9 `already-landed` reads the local `origin/main` without a fetch, per-station re-reads, no campaign blocks/lock — no-campaign-blocks and no lock are the contract's; freshness matches what the drain's own ledger read trusts on a clean main; disclosed under residual risks.
  - `[low]` `[reject]` BH10 test-suite structure (sibling-module imports, `--max-in-flight 1` forced, `RecordingFs` coverage, unused `tmp_path`) — importing fakes from a sibling test module has precedent (`test_dispatch_structure_graph.py`), forcing serial mirrors `_cycle`'s `_CYCLE_POLICY_SERIAL`, and the tree snapshot backs `RecordingFs`; nits.
  - `[low]` `[reject]` BH11 the tracked spec carries session scaffolding (an operator absolute path, "do not commit", "lossy-compressed") — the fix is to edit this build's spec, so rejected as a finding; the two session-only bullets were still removed from the Code Map at finalize as the run's own hygiene.
  - `[low]` `[reject]` BH12 no Dream Realization-log entry or operator doc — Boundaries: "Implement only the Surface named in epics.md Story 65.1", and that Surface names neither.
  - `[low]` `[reject]` BH13 production `assert`s narrowing optional fields, `data["plan"]` set twice, plain-text stderr on a usage error, `argparse.SUPPRESS` defaults — the module already narrows with `assert` (`assert station is not None`), argparse usage errors are plain stderr with exit 2, and the only `max_cycles`/`tick_seconds` reader uses `getattr`.
- findings (Edge Case Hunter, 13):
  - `[low]` `[reject]` E1 the plan's ledger read runs `vcs.fetch` when the primary is not a clean `main` — real (a remote-tracking ref refresh, never a working-tree write; an offline failure is swallowed by `_station_ledger_statuses`); the contract mandates reusing that function, so the plan inherits the drain's freshness rule.
  - `[medium]` `[patch]` E2 same defect as BH1 (`is_next` keyed to `targets[0]`).
  - `[low]` `[reject]` E3 `payload["next_story"]` is the queue head while findings use `targets[0]` — `next_story` is `plan_station_queue`'s own name for the head, a held head is listed in `held[]`, AC6 pins it; the refusal-grading half is patched under BH1.
  - `[low]` `[reject]` E4 one failing per-story git read turns the whole station into 005 — the contract defines 005 at station granularity ("the station's plan could not be computed"); a partial plan reads closer to clean.
  - `[medium]` `[defer]` E5 same defect as BH3 (prose-park heuristic).
  - `[low]` `[reject]` E6 same defect as BH2 (`review`/`blocked` override keys).
  - `[false]` `[reject]` E7 `spec_binding_findings` runs when `spec_text` is `None` — `drain_plan.py:322` guards it (`if spec_text is not None:`), so no spurious `MRS-GATE-010` follows an `MRS-DISP-005`.
  - `[low]` `[reject]` E8 station-level `MRS-GATE-003`/`MRS-DISP-019` repeat per story under `--all-stories` — the contract asks for one finding per reason per story, and a station defect does refuse each story; dedup is more than a direct correction.
  - `[medium]` `[patch]` E9 same defect as BH8 (005 row omits `parallel_cap` and siblings).
  - `[low]` `[reject]` E10 `merged_keys` does not fetch before `commit_subjects` — same as BH9.
  - `[false]` `[reject]` E11 `env_checked` true with nothing evaluated — the AC defines the field as whether `--check-env` was in force; a station with nothing to launch has no environment to assure.
  - `[medium]` `[defer]` E12 the plan never calls `station_in_flight_conflict`, so a serial station with a live session reads `would_dispatch: true` while the drain relays it as in-flight — verified in `plan_station_cycle` (the serial branch has no liveness read; parallel uses `_live_dispatch_story_keys`); the contract's evaluated-refusal list and 001's would-be codes exclude `MRS-DISP-011/021`, which the drain relays as a WARN `MRS-DRAIN-006`; how a busy station maps to the plan's outcome and exit code is a Spec decision (three readings, none selected by the intent). Routed `defer` for the same reason as BH3; recorded under `deferred:`.
  - `[low]` `[reject]` E13 a Deps WARN is emitted while a wave is in flight — the head's declared Deps are still true information; a guard adds a branch for no named harm.
- findings (Verification Gap, 6):
  - `[medium]` `[patch]` G1 `--check-env` harness-preference derivation unasserted (mutation left 53 tests green) — tests added for tier-map lead, `--harness` outranking it and transient-failure exclusion.
  - `[medium]` `[patch]` G2 non-ok session-precondition branch unasserted (mutation left tests green) — test added with `session_check_returncode=1`.
  - `[medium]` `[patch]` G3 wave wiring moved into the extraction unasserted (constant wave id, missing text, empty `wave.refused` all survived) — tests added in `test_drain_plan.py`; `test_dispatch_fleet.py` untouched.
  - `[medium]` `[defer]` G4 prose-park false positives on real specs — same defect as BH3.
  - `[medium]` `[patch]` G5 wave members beyond the first unpinned — same defect as BH1.
  - `[low]` `[patch]` G6 `_command_shape_problem`'s `shlex` `ValueError` branch untested — test added.
- findings (Intent Alignment, 10):
  - `[false]` `[reject]` I1 `_plan` forces `--max-in-flight 1` — no bad outcome: cap resolution runs through the cycle's own `resolve_max_parallel`, the `--max-in-flight 2` tests cover the wave, and forcing serial follows `_cycle`'s `_CYCLE_POLICY_SERIAL`.
  - `[low]` `[reject]` I2 `--plan --stories` meets drain's own front-door refusals (`MRS-DRAIN-015`, `MRS-DISP-004/032`) before the plan branch — the same invocation would be refused with those codes; the 005/exit-1 case is exercised without `--stories`.
  - `[medium]` `[defer]` I3 whole-spec prose-park scan — same defect as BH3.
  - `[low]` `[reject]` I4 an unreadable spec surfaces as `MRS-DISP-005` (as `dispatch_once` reports it) and a missing epics file is silent (as `_load_station_story_deps` treats it) — rare, and both mirror the drain.
  - `[medium]` `[patch]` I5 wave "next" semantics — same defect as BH1 (the head-versus-first-member facet is rejected under E3).
  - `[low]` `[reject]` I6 `--check-env` mirrors the preference derivation instead of reusing it — same as BH4; the G1 tests now pin the mirror.
  - `[low]` `[reject]` I7 the drain's front-door findings (`MRS-DRAIN-012/013`, queue-file `MRS-DRAIN-008`) enter the plan's verdict — mirrors the drain; the contract is silent and the one obvious reading is to report them.
  - `[false]` `[reject]` I8 direct disk reads bypass the ports — `dispatch_once` and `_load_station_deps_graph` read specs and epics the same way; AD-11 governs writes and its meta-test is green.
  - `[false]` `[reject]` I9 base ref `origin/main` and the `spec_status_for` corroboration — the same call `_reconcile_campaign_blocked` makes; the contract names `promotion.corroborated_merged_story_keys`.
  - `[low]` `[reject]` I10 no station skill or docs surface touched — same as BH12.

## Design Notes

- The plan and the drain share ONE planner because "the plan cannot drift from the drain" is the contract; the planner returns facts (ledger, backlog, blocked map, queue plan, wave) and never emits findings or writes, so `execute_fleet_cycle` keeps every emission and every writer in its existing order.
- `--tick-seconds` / `--max-cycles` default to `argparse.SUPPRESS` so "explicitly given" is detectable; `run_fleet_drain` already reads both with `getattr(..., default)`, so the drain's own behaviour is unchanged.
- Prose-park detection strips markdown emphasis first (`do **not** dispatch` is the real steward wording), and does not match `un-parked` / `unparked`.

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

## Auto Run Result

Status: done
Blocking condition: none

**Summary.** `marshal factory drain --plan` reports, per station, the next story (or parallel wave) and every refusal decidable before launch, and launches nothing: it is answered in `run_fleet_drain` before a campaign id, run directory, lock, journal entry or supervisor exists. The per-station queue computation moved out of `execute_fleet_cycle` into one read-only `plan_station_cycle` that the cycle and the plan both call (behaviour-preserving; `test_dispatch_fleet.py` and `test_dispatch.py` untouched and green). Findings `MRS-DRAINPLAN-001..005` are registered at ERROR / WARN / WARN / WARN / UNEVALUABLE; exit is 4 / 1 / 0 from the AD-7 lattice; `--plan` with `--once`, `--campaign`, `--max-cycles` or `--tick-seconds` exits 2.

**Files changed** (under `src/shared/packages/pyforge-marshal/`):
- `src/pyforge/marshal/cli/dispatch.py` -- extracts `resolve_cycle_slugs`, `plan_station_cycle`, `skip_basis`; adds `--plan`, `--all-stories`, `--check-env`; `--max-cycles`/`--tick-seconds` default to `argparse.SUPPRESS`; `run_fleet_drain` answers `--plan` first.
- `src/pyforge/marshal/cli/drain_plan.py` -- new: per-story refusal evaluation, `data.stations[]` projection, findings, text rendering, exit code.
- `src/pyforge/marshal/core/dispatch_prelaunch.py` -- new, pure: `spec_binding_findings` (Story 65.2 reuses it), `find_prose_park`, `story_epics_blocks`, `inert_override_keys`, `unmet_deps`.
- `src/pyforge/marshal/core/findings.py`, `core/verdict.py` -- register and classify `MRS-DRAINPLAN-001..005`.
- `tests/unit/test_drain_plan.py`, `test_dispatch_prelaunch.py`, `test_findings.py` -- one test per Acceptance Criterion and I/O matrix row, plus the review-pass regression tests.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`, `.../spec-pyforge-core/.memlog.md` -- surface-reconcile entries naming the governed paths (no baseline stamp; the landing stamps).

**Review findings.** 42 reported across four layers. Patches applied: 5 medium entries (wave-member grading with `held` widened; the 005 row skeleton and code-list comments; `--check-env` harness-preference tests; the non-ok session-probe test; wave wiring tests) and 1 low (the `shlex` parse-error test). Deferred: 3 (below). Rejected: 23 low and 5 false, each with its reason in the Review Triage Log.

**Follow-up review recommendation: `true`.** Two or more medium entries were patched after the only review pass. The unverified risk is the patched wave-member grading in `cli/drain_plan.py` (`is_next` and `would_dispatch` keyed to every story handed to `dispatch_once`) together with the `held` list, which now names every story the wave refused -- a field beyond the contract's projection, added so the overlap case is observable -- and the `_station_row` refactor; no reviewer read them after the patch.

**Verification performed** (all from the exit code, output redirected to files):
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- exit 0, 9065 passed, 1 skipped (9053 before the review patches).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- exit 0, 130 passed, 3 skipped.
- `ruff check`, `ruff format --check` in the package -- exit 0; `mypy -p pyforge.marshal` -- exit 0, no issues in 175 files.
- `python scripts/spec_surface_reconcile.py` -- exit 0, "every tracked file governed or allowlisted; no drift".
- Manual check: `marshal factory drain --plan --mode drain_to_zero --format json` against the real repo, twice -- writes nothing (`git status` and every `dispatch-runs/` and `fleet-drain-runs/` listing identical before and after). With this run's own `BMAD_ACTIVE_PROJECT=pyforge-marshal` set it exits 4, because every other station reads `MRS-DISP-041` scope drift; without it, it exits 0 with 8 stations and only WARNs (6 `MRS-DRAINPLAN-002`, 1 `-004`).
- Review-layer mutation runs by the verification-gap reviewer and by the implementer confirm each added test fails when its behaviour is removed (all except the constant wave id, which is argued from the two-cycle test).

**Residual risks.**
- Prose-park false positives (deferred, needs an operator/Spec decision): the literal detector matches 32 of 1,212 tracked specs, five of them live backlog stories; on a next story a false match reads `MRS-DRAINPLAN-001` and exit 4. The reason text names the matching line, so the operator can tell. Tightening it edits the contract.
- Busy serial station reads `would_dispatch: true` (deferred, Spec decision): the drain relays it as in-flight.
- Pre-existing crash (deferred, high): with `max_parallel` above 1, an empty parallel wave makes `execute_fleet_cycle` raise `ValueError` at `dispatch.py:4317`. Not changed here (the extraction must preserve cycle behaviour); the plan reports the case as `held`.
- The plan reuses `_station_ledger_statuses`, which runs `git fetch origin main` when the primary checkout is not a clean `main` (a remote-tracking ref refresh, never a working-tree write); the already-landed read trusts the local `origin/main` without a fetch.
- `--all-stories` and `--check-env` without `--plan` are a usage error (exit 2), beyond the contract's list of launch-only flags; they are plan modifiers, and a silent no-op would let an operator believe the environment was checked.
- Leftover worktree WIP (`MRS-DISP-036`) is reported as `MRS-DRAINPLAN-001` because the contract lists it among the would-be codes, although a launch proceeds over it; a re-dispatched story with leftover WIP therefore exits 4.
