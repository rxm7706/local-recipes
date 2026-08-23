# Fleet drain playbook — operational prototype for Epic 22

**Status:** living reference (validated 2026-08-22 → 2026-08-23)  
**Binds to:** `spec-marshal-single-story-dispatch` CAP-1..CAP-7, Epic 22 Stories 22.1–22.6  
**Interim runner:** `.cursor/pyforge-fleet-drain/` (Cursor hand-driven; until `marshal factory dispatch` ships)

This companion is the **acceptance oracle** for Epic 22: when Story 22.1 lands, a operator replaying the
2026-08-22/23 fleet drain must get the same outcomes from marshal verbs, not from session discipline.

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
| Fleet-wide queue + modes | **CAP-7** (this spec) | `marshal factory dispatch --fleet` / `marshal drain` |

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
| `skip_on_blocked` | HALT on blocked story → skip to next queue entry, report to operator (steward `12-7` live OCP) |

Queue source: per-station ordered backlog from `sprint-status-ledger.yaml` + `order_overrides`
(interim: `.cursor/pyforge-fleet-drain/queues.yaml` + `generate-queues.py`).

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

## One dispatch cycle (reference)

Detailed step-by-step (prompt skeleton, recovery playbooks, verification commands) lives in the
interim runner copy at `.cursor/pyforge-fleet-drain/PLAN.md` — keep in sync when this companion
changes; Story 22.1 implementation tests against both.

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

All stations `drained: true` in queue file (zero backlog per ledger), or `leave_one` target reached.
Post-drain: optional epics retrospective; marshal journal becomes source for dashboard-velocity Dream.
