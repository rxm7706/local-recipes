# Horizon watches — named triggers, no code in this chain

Wave-D of the alignment plan. Each row names the trigger that converts a watch
into work, and where that work goes. Doctor's ambient drift (core 10.1/10.2 +
suite CAP-4) reports "an upgrade exists"; these rows say what to check WHEN it
lands.

| Watch | Trigger | Then |
|---|---|---|
| **bmad-ticket tree** (v7 planning lane; retires `sprint-status.yaml` for net-new work — our entire tracking machinery rides it: epics.md → Tier-3 feed → tracked ledger → promote/story-status/fleet-picture/dashboard) | bmad-ticket lands in a **tagged release** (6.12-ish expected before the v7 cut; grammar on `ticket-master` "reworked twice", so don't build against the branch) | New marshal-owned Dream: the tracking-machinery adapter. Study material: `docs/explanation/tickets-and-specs.md` on ticket-master; `.bmad-obeya/` store, `ticket_tree.py` verbs, `update_ticket.py` gate |
| **config.yaml→TOML cutover** (kills the multi-project planning-artifacts symlink mechanism) | steward Epic 14 CAP-1's pre-flight diff flags a release where `_bmad/bmm/config.yaml` disappears or module config moves to TOML | Migrate the multi-project mechanism to per-project TOML `planning_artifacts` overrides — soft landing: the repo-custom six-layer `resolve_config.py` already speaks TOML layers 5/6. Named consequence also recorded in steward's `failure-modes.md` |
| **v7 shim cut** (the 20 retired IDs stop resolving) | any 7.x release | CAP-1's guard is the mitigation — at the trigger it should already be green; verify, then the guard's list becomes historical |
| **Spec-template / menu-code drift** (#2761 "Ask First/Block If" removed; #2737-#2739 menu codes) | next bmad-method core bump applied by steward Epic 14 | Re-check anything parsing spec files or documenting menu codes against the current templates |
| **AGENTS.md managed block / project-context ledger** | upstream's ledger rework (#2715/#2733/#2750/#2754) stabilizes in a tagged release | Revisit the HOLD: adopt the managed block or recommit to repo-owned rulebooks — a deliberate decision, recorded here either way |
| **Paige replacement / "explain this system" / bmad-ux+WDS** | any implementing release note | Re-evaluate CAP-7's owner question (a real successor may take over living-doc re-grounding) |
| **bmad-loop parallel fan-out** (issue #229, needs-design) | upstream ships Phase 5 | Marshal's `parallel-fan-out-readiness-assessment.md` (S-3.13) is the prepared entry point |
