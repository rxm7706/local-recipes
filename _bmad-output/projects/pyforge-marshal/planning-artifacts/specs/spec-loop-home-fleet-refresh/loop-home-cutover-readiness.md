# Loop-home readiness for the python-foundry cutover flip

Companion of `spec-loop-home-fleet-refresh/SPEC.md`. Written for marshal Story 31.5, relaying
`spec-bmad-suite-lifecycle` G10 / `cutover-readiness.md` P16 (owned by pyforge-steward). This is
a **one-time target-state definition** for steward Story 44.12's flip — a different lifecycle
and cadence than CAP-1's live, recurring staleness detection above, which is why it lives as a
sibling file rather than inside `SPEC.md` itself (see the SPEC's Design Notes rationale carried
in the originating story spec).

## Scope

There are eight `~/.bmad-loops/pyforge-*` loop homes today. Each is a full git worktree pointed
at **this** repo (`local-recipes`), with its own `pixi.toml`, `pyforge.toml`
(`[project] name = "local-recipes"`), `_bmad/`, and `_bmad-output/`. At the python-foundry
cutover flip, steward Story 44.12 (`_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md:2706-2715`) builds `pyforge.cutover_root`, a config
flag in `src/platform/config/flags.json` whose value alone decides the ledger of record, Mason's
targets, and the loop-home remotes — flipping it back restores the previous state (explicitly
reversible). Story 44.5's own note on that flip (`epics.md:2636`) states that flipping
`pyforge.cutover_root` from `local-recipes` to `foundry` is an attended act with no loop running,
and that "the eight loop homes [are] re-provisioned against the foundry remote" as part of it.
This doc names what the resulting state must satisfy (R1–R6 below) — it does not build the flag
or the replay harness that performs the flip, and it does not assume a particular low-level
mechanism (in-place remote change vs. destroy-and-recreate) beyond what epics.md states.

## Readiness items

Each row: the concrete fact that must be true, the check that proves it (an existing
command/field only — no new detector), and who runs it.

| # | Fact that must be true | Proving check | Who runs it |
|---|---|---|---|
| R1 | The home's git remote points at the new foundry repo, not `local-recipes` | manual: `git remote -v` in the home's root checkout | steward 44.12, attended |
| R2 | `pyforge.toml`'s `[project] name` matches the foundry repo's own name, not `"local-recipes"` | manual: `cat pyforge.toml` | steward 44.12, attended |
| R3 | The home's marker/symlink/backlink state is internally consistent for its slug | `marshal homes --json` — the home's row reports `desynced: false` and `active_project` equal to the **expected slug** (the directory basename under `~/.bmad-loops/`, e.g. `pyforge-marshal` for `~/.bmad-loops/pyforge-marshal`; the eight slugs are the eight `pyforge-*` station tokens). The boolean is computed from marker-vs-symlink-vs-Tier-3-backlink agreement internally; the raw fields are not themselves serialized — `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py::_evaluate_home`) | steward 44.12, attended |
| R4 | The rendered `.bmad-loop/policy.toml`'s `[dev] skill` field reads `"bmad-dev-auto"` — a permanent internal adapter discriminator that is never renamed to whatever harness skill is actually invoked (the invoked skill, e.g. `bmad-build-auto`, is resolved from disk at runtime, independent of this field) | `bmad-loop validate`, or manual `cat .bmad-loop/policy.toml` for the `[dev] skill` value; per the `spec-bmad-suite-lifecycle/.memlog.md` CAP-10 spec correction (2026-09-06), verified against installed `bmad_loop` 0.11.1 (`policy.py:44`, `DEV_SKILLS = {"bmad-dev-auto"}`) | steward 44.12, attended |
| R5 | The `_bmad-output` planning/implementation relays are refreshed against the new tree (not stale symlinks or content pointed at the retired `local-recipes` project layout) | manual inspection: `readlink -f` on the planning-artifacts and implementation-artifacts links, cross-checked against the new tree's active project | steward 44.12, attended |
| R6 | No run is in flight for that home at the moment of re-provisioning | `marshal status --project <slug> --format json` (home must not report a running/awaiting state) and, if a run id is visible, `bmad-loop status <run_id> --json` from that home's root | steward 44.12, attended |

**Not proven by any of the above** (confirmed by code search — no existing marshal code reads
`pyforge.toml`; `grep -rln "pyforge.toml" src/shared/packages/pyforge-marshal/src/` returns zero
hits): R1, R2, and R5 have no CLI/JSON surface today and are named here as manual inspection
steps, not gaps to close in this story.

## Who runs it

Per `cutover-readiness.md` P16, this is **attended**: steward Story 44.12 performs the
re-provisioning by hand, one home at a time, with the operator running the checks above and
confirming each before moving to the next home. This is explicitly not an unattended gate, a
CI job, or a new `marshal homes` mode — Effort S / Type docs; nothing here proposes new
automation.

## Reconciling "retired" vs "re-provisioned"

`spec-python-foundry-cutover`'s deferred-work entry `DW-CC-2026-09-04-1`
(`_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md:2591-2598`; the ledger row reads `status: resolved` as of 2026-09-08 — this reconciliation is historiographic, not an open blocker) is an aggregate over 268 registered worktrees across six
categories (58 `.worktrees/`, 66 `.cursor/worktrees`, 33 `.claude/worktrees`, 93 retired under
loop homes, 8 loop homes, 3 `local-recipes-wt-*`); "8 loop homes... retired at Phase 6, never
moved" is one line-item within that larger entry, and it is only that line-item this section
reconciles. `cutover-readiness.md` P16 describes the same eight homes as "re-provisioned." These
are not in tension and do not describe two different fates for the eight loop homes specifically:

- **"Retired"** is the DW entry's description of Phase 6's own end state for the *old*,
  `local-recipes`-pointed loop homes — as of 2026-09-04 nothing had yet acted on them; they were
  simply sitting there, un-acted-on residue, once the flip made them stale.
- **"Re-provisioned"** is P16's (and epics.md Story 44.5's note's) description of what happens
  to those same eight slugs at the flip — `pyforge.cutover_root` moves to `foundry` and, per that
  note, the eight loop homes are "re-provisioned against the foundry remote."

Neither wording implies the homes silently disappear. What is genuinely **unclear from
epics.md** is the low-level mechanism: whether the flag-flip tooling built in Story 44.12 itself
also refreshes R3 (marker/symlink/Tier-3-backlink consistency), R4 (rendered policy), and R5
(refreshed `_bmad-output` relays) as part of "re-provisioned," or whether a bare remote change is
all the flip performs and R3–R5 remain separate attended-operator checks on top of it. This doc
does not assert either way — it names R1–R6 as the facts that must hold of the *resulting* state
regardless of how many of them the flip's own tooling automates versus leaves to the attended
operator named in P16. "Retired" names the old state's fate; "re-provisioned" names the new
state's arrival at the same slug. Both are true of the same eight homes.

## Non-goals

- Does not build steward 44.12's re-provisioning mechanism — this doc only defines the target
  state that mechanism must reach.
- Does not add a new `marshal homes` field, detector, or CLI flag. R1, R2, and R5 stay manual
  inspection until (if ever) a future story decides to automate them.
- Does not hand-edit `cutover-readiness.md`. The relay note in
  `spec-bmad-suite-lifecycle/.memlog.md` gives steward what it needs to update G10/P16's State
  column, by whatever means steward's own process actually uses for that companion doc — P4's
  "memlog is the single writer" convention is scoped to `SPEC.md` specifically, and
  `cutover-readiness.md`'s own State column (e.g. P8's "satisfied (99e595cc6a)") reads as
  updated directly as work lands, not necessarily memlog-driven.
