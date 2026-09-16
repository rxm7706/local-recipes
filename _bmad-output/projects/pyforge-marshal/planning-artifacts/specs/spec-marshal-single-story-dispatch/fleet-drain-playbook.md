# Fleet drain playbook — operational prototype for Epic 22

**Status:** living reference (validated 2026-08-22 → 2026-08-23)  
**Binds to:** `spec-marshal-single-story-dispatch` CAP-1..CAP-7, Epic 22 Stories 22.1–22.7  
**Interim runner:** `.cursor/pyforge-fleet-drain/` — **superseded 2026-08-27** by Story 22.7's
`marshal factory drain`; kept as the campaign's historical record, not a runbook.

This companion is the **acceptance oracle** for Epic 22: when Story 22.1 lands, a operator replaying the
2026-08-22/23 fleet drain must get the same outcomes from marshal verbs, not from session discipline.
Story 22.7 pins that replay as a fixture —
`tests/unit/test_dispatch_fleet.py::test_eight_station_campaign_replays_without_session_discipline`
seeds this campaign's exact shape (eight stations, `drain_to_zero`, six drained, marshal + steward
under `order_overrides`, steward's 12-7 `skip_policies` entry) and asserts its skip / parallel /
chain / drained outcomes.

---

## What marshal must productize

| Playbook phase | Epic 22 story | Target marshal surface |
|----------------|---------------|------------------------|
| Preflight (ledger, branch, PR, zombie) | 22.2 | `marshal factory dispatch` preflight + refuse redispatch |
| Launch worktree + `bmad-build-auto` | 22.1 | `marshal factory dispatch <station> <story>` |
| One in flight per station; parallel stations | 22.5 | queue + in-flight registry |
| Merge when CI green + ledger sync + spec promote | 22.4 | compose `land` / `deploy land-story` + Epic 15 |
| Independent verify before merge | 22.3 | Epic 2 gate objects on frozen surface |
| Survive operator death | 22.6 | journal + attach/resume |
| Fleet-wide queue + modes | 22.7 | `marshal factory drain --mode <mode>` (shipped 2026-08-27; the provisional `--fleet` / `marshal drain` spellings resolved to this one) |

---

## Eight stations (pyforge fleet)

`atlas`, `doctor`, `herald`, `marshal`, `mason`, `scribe`, `steward`, `warden` — each maps to
`pyforge-<slug>`, `_bmad-output/projects/pyforge-<slug>/planning-artifacts/sprint-status-ledger.yaml`,
and a package surface under `src/shared/packages/pyforge-<slug>/` (steward also `src/platform/`).

**HARD:** `BMAD_ACTIVE_PROJECT=pyforge-<slug>` per dispatch; physical paths under
`_bmad-output/projects/<slug>/…`; never `scripts/bmad-switch` from parallel agents (CLAUDE.md).

---

## Operating modes (CAP-7)

| Mode | Behavior |
|------|----------|
| `drain_to_zero` | Dispatch until ledger has zero non-`done` story keys |
| `leave_one` | Stop with `leave_remaining` story untouched (graceful shutdown) |
| `skip_on_blocked` | HALT on blocked story → skip to next queue entry, report to operator |

`--mode` is required and never defaulted (`MRS-DRAIN-001`).

Mode governs **derived** blocks only — CAP-2 git/process facts saying a story's last dispatch ended
`failed`. A **declared** `skip_policies` entry (the hand-authored kind, e.g. steward `12-7` needs a live
OCP cluster) is honored under *every* mode: the 2026-08-22/23 campaign ran `drain_to_zero` *with* seven
such entries, so collapsing the two would make its own mode unreplayable. Either way the story stays in
the backlog and is never auto-retried.

Queue source: per-station ordered backlog from the tracked `sprint-status-ledger.yaml` files, plus the
optional in-repo `_bmad-output/projects/pyforge-marshal/planning-artifacts/fleet-drain-queue.yaml`
(`order_overrides` + `skip_policies` only). The interim `.cursor/pyforge-fleet-drain/queues.yaml` +
`generate-queues.py` — including its regenerated `stations:` block, which duplicated ledger state — is
superseded; campaign journals live under that project's `implementation-artifacts/fleet-drain-runs/`.

---

## Merge-in-agent (2026-08-23 policy)

Dispatch session **owns merge-through-finalize** when CI is green:

1. `gh pr merge <n> --merge` (never `--squash`)
2. Mark story `done` in Tier-3 `implementation-artifacts/sprint-status.yaml`
3. `pixi run -e local-recipes sprint-ledger-sync --project <station>` (that station only)
4. Promote story spec → `planning-artifacts/specs/`
5. Regenerate fleet queue file

**Parallel safety:** each agent finalizes only its own project's ledger row; never
`sprint-ledger-sync` without `--project`; shared-root files (`pixi.toml`, `_bmad/custom/config.toml`,
`.github/workflows/`) require rebase-before-merge discipline.

Coordinator role collapses to monitor + rescue (blocked CI, symlink breakage, SendMessage orphans).

---

## One dispatch cycle

Since Story 22.7 a cycle is machinery, not a checklist: `marshal factory drain --mode <mode>` runs
**exactly one** cycle in the operator's foreground and returns, then detaches
`pyforge.marshal.dispatch_fleet_supervisor`, which re-runs that same published command
(`--once --campaign <run_id>`) on a tick until the campaign reports itself complete. Nothing in the
foreground waits — the ~600 s watchdog that killed the hand ritual's busy-waiting parent has nothing
to kill. Chaining is structural: a station whose story finished merge-through-finalize has an advanced
tracked ledger and a free in-flight slot, so the next cycle hands it its next story.

`--once` runs a single cycle with no supervisor. The hand-ritual step-by-step (prompt skeleton,
recovery playbooks) survives at `.cursor/pyforge-fleet-drain/PLAN.md` as historical record only.

---

## Validated incidents (regression fixtures)

| Incident | Fix / rule |
|----------|------------|
| Busy-wait parent watchdog-killed | No foreground wait; supervisor owns await (CAP-2) |
| "Completed" notification while agent still live | Judge from git + process facts; refuse redispatch |
| `implementation-artifacts` directory replaces symlink | `readlink -f` before spec promotion |
| `user_skill_level` in two config layers | Exactly one definition fleet-wide |
| SendMessage orphan to `general-purpose` | Nudge top-level task id; re-verify independently |
| Steward 12-7 needs live OCP | `skip_on_blocked`, dispatch 12-8 |

---

## Exit criteria (campaign)

Every station terminal for this campaign — `drained` (zero non-`done` keys in its tracked ledger),
`left-remaining` (the `leave_one` target), `blocked`, `all-skipped`, or `ledger-unreadable`. That is
exactly `data.complete` in the cycle envelope, and it is what stops the campaign supervisor; a busy or
just-dispatched station is progress, never terminal. Post-drain: optional epics retrospective; the
marshal journal becomes source for the dashboard-velocity Dream.
