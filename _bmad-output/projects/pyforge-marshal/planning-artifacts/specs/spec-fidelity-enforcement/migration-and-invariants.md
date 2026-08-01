# Trigger invariants and migration doctrine

## Six invariants for the detector trigger

Recorded here because they are the parts that do not regenerate — the
detector inventory, run timings, and repo/runtime split are all derivable
from the tree at any moment; the choices below are not.

1. **One derived registry, never a second list.** Enumerating detectors by
   hand is what produced the pre-CAP-1 state (eight scripts on disk, seven
   pixi tasks, three board rows, zero in CI, with the newest detector
   missing from two of the three). The registry (`scripts/detectors.py`)
   derives a task's command from `pixi.toml` and fails on its own gaps: a
   detector script with no declaration, or a declared detector with no
   task, is itself a finding.
2. **Each detector declares its own scope.** `repo` reads tracked files
   only and can run anywhere; `runtime` observes host state (Tier-3 feeds,
   tmux, `~/.bmad-loops`) and cannot run in CI at all. This is not a
   limitation to work around — it is the missing observation plane (CAP-6)
   showing up as a deployment constraint. The runtime detectors are the
   ones with nowhere to run today.
3. **A detector that cannot run reports `unknown`, never green.** Already
   the dashboard's behaviour — the strip never claims green it did not
   measure — promoted here to a rule binding every consumer of the
   registry.
4. **Advisory locally and in CI; the fleet is where it must bind.** Amended
   2026-07-31 from the original "blocking in CI and in the fleet" design
   (operator decision). A local hook is per-clone, untracked, bypassable —
   never a real gate. CI is now also advisory by choice: findings surface
   as warning annotations and never block a merge. This is a real
   concession against this Spec's own thesis (by CAP-1's own test, an
   advisory check is a plan) — recorded as an amendment rather than quietly
   implemented. What it buys: the suite runs at all, on every PR. What it
   costs: a red detector can still be merged past, which is exactly how PR
   #170 landed a `spec_surface_check` break. The fleet's `[verify]` set
   therefore carries the whole binding weight until CI is upgraded.
5. **Never a blocking `pre-commit`.** Every worktree — loop homes and
   per-story worktrees alike — resolves to the same `.git/hooks`. A
   blocking pre-commit fires inside unattended dev sessions that cannot
   interpret a detector failure, converting one red check into fleet-wide
   story loss. `pre-push` is the local seam.
6. **The fleet is the load-bearing consumer, not CI.** Most code here is
   written by `bmad-loop`, not by a human at a terminal in a pull request.
   Until the repo-scope detectors are in the harness `[verify]` set, the
   trigger covers the least of the three places work happens.

## Migration doctrine for CAP-2 (INV-4)

Every gate in this Spec fails on contact with the existing estate. INV-4
switched on unconditionally reds CI against ~52 shipped stories fleet-wide
(9 of Marshal's own 10, verified 2026-08-01) and blocks the whole fleet —
not a reason to soften it, but a reason it needs a migration doctrine in
the same change, not after. `pyforge-warden` already solved this shape once
(baseline and grandfathering as a first-class v1 concern), and the same
three rules apply:

- **Baseline the debt, never the rule.** Record the current gap as a dated,
  enumerated exemption list — not a lowered threshold. A threshold that
  moves is a rule nobody can appeal to afterwards; an exemption list is a
  backlog with an end.
- **The exemption list may only shrink.** Ratchet, checked. Anything not on
  the baseline fails from day one, so the gate is real for all *new* work
  immediately — which is where the leak actually is.
- **Grandfathering expires, and says when.** An exemption with no end date
  is a permanent hole wearing a temporary name. Charter §7 gated hard from
  day one on the reasoning that a grace period on the critical path is how
  drift becomes permanent; this record trace is on that path.

Landing this doctrine means CAP-2 goes green on a factory that is still
~52 specs in debt, and says so on the board rather than hiding it — the
CAP-7 "ungated boundary declares itself" rule turned on this Spec's own
migration.
