---
title: 'Fleet view'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '3e7b2ad1b4609b3a81a9e82e28133e12f8f840d0'
---

<intent-contract>

## Intent

**Problem:** with several loop homes live, "what is running?" today means opening each home's own journal/state.json by hand -- there is no one command. `marshal homes` (Story 1.6) already enumerates every home and verifies its Tier-3 ISOLATION (structural correctness: marker/symlink/backlink health) but says nothing about RUNTIME state (idle/running/paused/stopped, which story, how long, how much budget). FR-36/AD-5 close this gap: one row per home, one command, derived entirely from journals and run state -- never a hand-maintained file (a sprint-status-style feed an operator could forget to update, exactly the class of gap that just caused a live incident this session: Epic 4's own tracked ledger silently showed 4.1-4.7 as `review` for hours after they'd merged, because nothing but human diligence kept it honest).

**Approach:** `cli/status.py` (NEW top-level `marshal status` command, sibling to `homes`/`deploy`/`land`/`retire`). Fleet enumeration reuses `VcsPort.list_worktrees` (the SAME primitive `marshal homes`/`marshal retire` already use). Per home: the most recent run's journal (`cli/spin.py::_latest_run_dir`/`_resolve_harness_run_id_for_resume`, the SAME read sequence `_gather_claimed_commits`/`cli/retire.py` already established) supplies the supervisor's own launch entry (its `pid`, journaled by `cli/spin.py`'s own spin-launch write) and, via `HarnessPort.run_status_snapshot`, bmad-loop's own `RunStatusSnapshot` (`paused_stage`, `finished`, `tasks`). `core/status.py` gains a PURE state-derivation function (AD-4): `finished=True` -> `"stopped"`; `paused_stage == "escalation"` -> `"paused-on-escalation"`; a task snapshot whose phase is neither terminal (`"done"`) nor `"deferred"` -> `"running"` (that task's `story_key` is the reported current story); no run found at all -> `"idle"`. This derivation is OVERRIDDEN by a supervisor liveness check: `ProcessPort.is_alive(supervisor_pid)` false (and the run not already `finished`) reports `"unsupervised"` regardless of what the journal/harness otherwise implies -- a dead supervisor is never reported as any of the healthy states, per the AC's own explicit wording.

## Boundaries & Constraints

**Always:**
- **`cli/status.py` is a NEW top-level subcommand** (`marshal status`, wired in `cli/main.py`). No required positional argument -- fleet-wide by default; an optional `--project <slug>` scopes to one project (matching `marshal retire`'s own precedent).
- **Fleet enumeration reuses `VcsPort.list_worktrees`** exactly as `marshal homes`/`marshal retire` already do: every worktree whose `.branch` starts with `"loop/"` is one project's row.
- **Every field is derived from journals/run state, never a hand-maintained file** (AD-5) -- this command reads NO `sprint-status.yaml`, NO ledger, nothing an operator could forget to update. Its own worked motivation is this session's own live incident (see Intent).
- **State vocabulary is the closed 4-member set the AC names**: `"idle"`, `"running"`, `"paused-on-escalation"`, `"stopped"` -- PLUS `"unsupervised"` (the AC's own "a home with a dead supervisor is shown as unsupervised, not as healthy" clause, which is not one of the four "healthy" states and must be visually/structurally distinguishable from them).
- **Supervisor liveness reuses `ProcessPort.is_alive`** (Story 3.4, the SAME primitive the supervisor's own loop already uses to detect the harness process itself) -- the supervisor's OWN pid, read from the most recent run's journaled spin-launch entry (`cli/spin.py`'s own `{"pid": spin_result.pid, ...}` payload), never re-derived a second way.
- **"Current story" is the `story_key` of the first `TaskPhaseSnapshot` in `RunStatusSnapshot.tasks` whose `phase` is neither `"done"` nor `"deferred"`** (mirrors `cli/retire.py`'s own established phase-literal reuse of `supervisor/durability.py::_DONE_PHASE`) -- `None` when no such task exists (every task terminal, or zero tasks).
- **"Elapsed time" is derived from the run's own journal timestamps** (the spin-launch entry's own recorded timestamp vs. "now", via the injected `ClockPort`, Story 3.4's own established seam) -- never a live subprocess call per home (NFR-14's 10-second budget across 7+ homes rules out anything but cheap local file reads).
- **"Budget consumed" is best-effort, reported `null` when unavailable, never a blocking failure** -- reads whatever the supervisor's own most recent observed quantity was, if the journal carries one (Story 3.6's own `evaluate_ceiling` is a pure function over an externally-supplied `observed` value; `marshal status` reads the LAST such value the supervisor itself already journaled, never re-queries the harness live). A home with no budget-relevant journal entry yet reports `null`, not an error.
- **`marshal status` completes in under 10 seconds with at least seven homes present** (NFR-14) -- every per-home read is local file I/O only (journal directory listing, `state.json` read via `HarnessPort`, one `os.kill(pid, 0)` liveness probe); no network, no `git log`-scale operation repeated per home beyond what `list_worktrees` already does once.
- **A malformed/unreadable journal for one home is reported as a per-row finding and that row's state degrades to a reportable "unknown"-shaped entry, never a hard failure for the whole sweep** (mirrors `marshal retire`'s own "one project's bad data never blocks the rest of the fleet" precedent).

**Never:**
- No read of `sprint-status.yaml`, the tracked ledger, or any other hand-maintained feed -- AD-5's own explicit prohibition.
- No live subprocess call into the harness itself (no `bmad-loop status`, no shelling out per home) -- every fact is read from already-persisted journal/`state.json` files plus the one cheap `is_alive` liveness probe.
- No reimplementation of fleet enumeration, journal-run discovery, or the merged-story-key/phase-literal machinery already shipped for `marshal retire`/`marshal deploy refresh-feed`.
- Do not build the drill-down (`marshal status <run-id>`, Story 5.2), the escalation-queue sort/filter (Story 5.3), the ledger-vs-git discrepancy report (Story 5.4), or the durability/unpushed-work finding (Story 5.5) -- this story is the fleet-wide summary row shape ONLY; later stories extend the SAME envelope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No loop homes | Empty fleet | Clean no-op, `data.homes: []` | No finding |
| A home with no run yet | Never launched | `state: "idle"`, `current_story: null`, `elapsed: null`, `budget_consumed: null` | No finding |
| A home with a live, running supervisor and an in-flight task | Normal operation | `state: "running"`, `current_story` names the task | No finding |
| A home paused on escalation | `paused_stage == "escalation"` | `state: "paused-on-escalation"` | No finding |
| A home whose run finished | `finished: true` | `state: "stopped"` | No finding |
| A home whose supervisor pid is dead, run not finished | Crashed supervisor | `state: "unsupervised"`, regardless of what the journal otherwise implies | No finding (this IS the intended report, not an error) |
| A home whose journal is malformed/unreadable | Corrupt state | Row reported with an "unknown"-shaped state, per-row WARN finding naming the home | Registered WARN |
| `--project <slug>` naming a nonexistent project | Typo/torn-down project | Clean no-op, `data.homes: []` | No finding |
| Seven or more homes present | Fleet-scale | Completes in under 10s | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/cli/status.py` -- NEW. `add_status_subparser`, `run_status(args, *, vcs=None, fs=None, harness=None, process=None, clock=None) -> int`, `_render_text_status`.
- `src/pyforge/marshal/core/status.py` -- EDIT. New pure function(s): `derive_home_state(*, finished: bool, paused_stage: str | None, tasks: tuple, supervisor_alive: bool | None) -> str` (the closed 5-value state vocabulary), plus a small `FleetHomeRow`-shaped dict-builder mirroring this module's existing `HomeFacts`/`evaluate_homes` convention.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` -- EDIT. Register + classify `MRS-STATUS-00N` (malformed/unreadable journal for one home -> WARN).
- `src/pyforge/marshal/cli/main.py` -- EDIT. Wire `status_cli.add_status_subparser(subparsers)`.
- `tests/unit/test_status.py` -- NEW (or extend `tests/unit/test_core_status.py` if that's this module's existing test file name -- check before creating a duplicate). Pure `derive_home_state` matrix + `cli/status.py`'s full I/O matrix with fake `VcsPort`/`FsPort`/`HarnessPort`/`ProcessPort`/`ClockPort` doubles (mirrors `test_retire.py`'s established fake-port style).

## Design Notes

- **Why supervisor liveness overrides every other derived state:** the AC's own wording ("a home with a dead supervisor is shown as unsupervised, not as healthy") is unconditional -- a journal that still claims "running" or "paused" is exactly the STALE state a crashed supervisor leaves behind; trusting it would misreport the fleet's real health, the precise failure mode this story exists to prevent (and the live incident that motivated writing this story's own Intent section).
- **Why "budget consumed" degrades to `null` rather than being computed live:** NFR-14's 10-second/7-homes budget forbids a live harness query per home; the alternative -- re-deriving consumption from raw token/turn counts this module has no established read path for -- is out of this story's own scope (Story 3.6 already owns ceiling EVALUATION over an externally-supplied observed value; this story only REPORTS whatever was already observed and journaled, never re-computes it).

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

## Review Triage Log

### 2026-08-07 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 3 (critical 1, high 1, low 1)
- defer: 3
- reject: 0
- addressed_findings:
  - `[critical]` `[patch]` **The supervisor-liveness check read the DETACHED HARNESS PROCESS's own pid (`cli/spin.py`'s `spin_result.pid`, journaled on the `run-launch`/`run-resume` OUTCOME entry) instead of the SEPARATE Marshal supervisor sidecar's own pid -- silently defeating this story's own headline safety guarantee.** Found by the Blind Hunter as the single most severe finding against this story: if the supervisor crashes while the watched harness process keeps running (a fully realistic, independent-process failure), the harness pid probes alive, and a truly dead supervisor was reported as a healthy state. Fixed: `_gather_run_journal_facts` now separately recovers the SUPERVISOR's own pid from `supervisor/__main__.py`'s own `"supervisor-attach"`/`"supervisor-heartbeat"` journaled kinds (the most recent, by timestamp, across both), used exclusively for the liveness probe; the launch pid is retained ONLY for `launched_at` (elapsed-time) and the "journal readable at all" signal. A supervisor that never attached is treated as dead (the safe direction), never silently "alive." Tests updated: every test exercising a healthy state now journals a `supervisor-attach` entry with a DIFFERENT pid than the launch line's, and `test_home_with_dead_supervisor_is_unsupervised` now proves the exact worked scenario (harness pid alive, supervisor pid dead) rather than the previous coincidental single-pid case that could not distinguish "reads the right pid" from "reads a wrong one that happened to match."
  - `[high]` `[patch]` **`_TERMINAL_TASK_PHASES` omitted `"escalated"` -- bmad-loop's own authoritative terminal-phase set is `{done, deferred, escalated}`, not just the first two -- so a task stuck awaiting an operator's escalation decision was misreported as still in-flight, both in `derive_home_state` (reporting `"running"` for a home whose only non-terminal task was actually stuck) and `_current_story_key` (reporting the stale escalated story, silently hiding whatever is actually running later in the task list).** Found by the Edge Case Hunter. Fixed: `_TERMINAL_TASK_PHASES = frozenset({_DONE_PHASE, _DEFERRED_PHASE, _ESCALATED_PHASE})`, matching `bmad_loop.model.TERMINAL_PHASES` exactly.
  - `[low]` `[patch]` **The "budget consumed" journal read was not scoped to the current `run_id`, unlike the pid-extraction loop right next to it** -- inconsistent with the module's own established discipline, and a latent risk that a future journal-layout change could misattribute a stale/foreign run's budget figure. Found by the Blind Hunter. Fixed: added the same `entry.run_id == run_id` filter, in the same pass as the pid fix.
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[medium]` D1: `ProcessPort.is_alive`'s bare `os.kill(pid, 0)` (Story 3.4, pre-existing) has no start-time/command-name cross-check -- this story's whole trust model now rests on OS pid-reuse not colliding in the window between a supervisor's exit and the next `marshal status` invocation.
  - `[low]` D2: the journal is read+folded TWICE per home (once directly, once again inside the reused `_resolve_harness_run_id_for_resume`) -- a doc/behavior mismatch and double I/O, not a correctness bug, against NFR-14's budget.
  - `[low]` D3: the text renderer has no inline marker distinguishing a degraded "unknown" row from a healthy one -- the WARN explaining why only appears in a separate findings block.
- rejected: none this pass.

## Suggested Review Order

**The safety-critical fix — start here**

- `_gather_run_journal_facts`'s supervisor-pid extraction (`_SUPERVISOR_ATTACH_KIND`/`_SUPERVISOR_HEARTBEAT_KIND`) and `_gather_home_facts`'s corrected liveness call.
  [`status.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py) — search `_SUPERVISOR_ATTACH_KIND`

**Correctness fix**

- `_TERMINAL_TASK_PHASES`'s `"escalated"` addition.
  [`core/status.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py) — search `_ESCALATED_PHASE`

**Tests (peripherals)**

- `test_status.py`'s updated healthy-state fixtures (each now journals a distinct supervisor pid) and the strengthened dead-supervisor test.
</intent-contract>
