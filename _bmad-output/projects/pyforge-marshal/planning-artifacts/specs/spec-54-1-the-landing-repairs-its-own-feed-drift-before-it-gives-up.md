---
title: '54.1: The landing repairs its own feed drift before it gives up'
type: 'feature'
created: '2026-09-24'
status: 'backlog'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** As a fleet operator landing a dispatched story, doctor 24.2 and 24.3 (PRs #1577/#1578, #1579/#1580) each landed cleanly — PR merged, spec `status: done` — but `sprint-ledger-sync`'s regression guard correctly refused to promote the tracked ledger, because the Tier-3 feed (`implementation-artifacts/sprint-status.yaml`) had drifted stale on 13 and 14 keys *unrelated* to the story being promoted. Both times a human ran `--repair-feed` by hand, hand-flipped the one new key, and opened a separate PR whose only content was that two-line YAML diff. Minting this very epic reproduced the same disease a third time: marshal's own Tier-3 feed needed `--repair-feed` (18 regressed + 11 missing keys) before this epic's own backlog rows could sync.

**Approach:** `dispatch_land_finalize`'s promotion attempt partitions a regression-guard refusal into "the story being promoted" vs "every other key." When the promoted story's own key is not among the refused set, the refusal is provably safe to repair — the tracked twin is the authoritative record and pulling its `done` keys forward into the feed (exactly what `--repair-feed` already does by hand) only ever moves a key *toward* `done`, never away from it. Finalize performs that repair itself, retries the promotion once, and lands the feed catch-up in the SAME commit as the story it is promoting. A refusal that names the promoted story's own key is left exactly as it is today: refused, named, and handed to a human, because that is a genuine disagreement about the story itself, not blind drift.

Ledger key: `54-1-the-landing-repairs-its-own-feed-drift-before-it-gives-up`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-265.

## Acceptance Criteria

- Given a promotion attempt refused only over keys other than the one being promoted When `dispatch_land_finalize` runs Then it repairs the Tier-3 feed from the tracked twin and promotes the just-landed key in the same commit, opening no second PR
- Given a promotion attempt refused because the promoted story's OWN key disagrees with the twin When `dispatch_land_finalize` runs Then it still refuses, names the disagreement, and stops for a human — unchanged from today
- Given the doctor 24.2 and 24.3 stale-feed fixtures (13 and 14 unrelated keys behind, respectively) When replayed against the fix Then both promote cleanly with no manual `--repair-feed` step

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths. The auto-repair is strictly the same one-directional pull-forward `scripts/promote_sprint_status.py --repair-feed` already performs — never a new merge policy, never a write that could move a key away from `done`.

**Never:**
- Do not weaken the regression guard for the story actually being promoted — a self-disagreement always stays a human decision.
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.
- Do not flip the parent Dream to `realized` (benchmark artifact is the realized-guard).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| refusal on unrelated keys only | feed stale on N keys not including the promoted story's | feed repaired from twin, promotion retried and succeeds in one commit | none — no second PR |
| refusal includes the promoted story's own key | twin and feed disagree about the story itself | promotion still refused, disagreement named | surfaced to a human, unchanged |
| doctor 24.2/24.3 fixture replay | 13 / 14 unrelated stale keys | both promote cleanly, no `--repair-feed` by hand | none |

</intent-contract>

## Source

Contract authored directly from `docs/dreams/pyforge-marshal.md`'s 2026-09-24 Realization-log entry and `spec-pyforge-marshal` CAP-265 (this Spec's own `.memlog.md`), decomposed the same session as Epic 54's mint.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
