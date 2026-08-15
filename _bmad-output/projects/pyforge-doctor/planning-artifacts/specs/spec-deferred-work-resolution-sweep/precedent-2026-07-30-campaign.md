# Precedent: the 2026-07-30 verification campaign (PR #147)

Every tracked deferred-work entry across the fleet-as-it-existed-then — atlas 57, warden 43, herald 24, marshal 17, doctor 4 (**145 total**; mason/steward/scribe didn't exist as stations yet) — was individually re-verified against live code, entirely by hand. `bmad-loop-sweep` could not be used: it is automation-only and scoped to Tier-3, not the tracked ledger. Full account in auto-memory `project_deferred_work_verification_campaign`.

## What it found

- **12 entries were already resolved and nobody closed them.** The sharpest case: one root defect (`bmad-ui` losing its local `./build_artifacts` channel) had been independently hit and fixed **three times** across three different stories in three different projects, and two of the three ledger entries still read `open`.
- **2 entries got *worse* since authoring** — a duplication bug that roughly doubled, and a per-entry cost that grew. A stale `status: open` cannot show drift in either direction; only re-reading the code can.
- **5 entries understated their own scope** once the pattern was traced to sibling packages that had cloned the same defect.
- **1 finding could only be verified by reading a *different* project's code.** `atlas DW-I5-1`'s part (b) turned out to be resolved in marshal's `core/policy.py` — a single-project sweep cannot catch this class at all (this is CAP-5's direct motivation).

## What the protocol proved, worth preserving

- **Batch 8–14 entries per pass**, gathering evidence with a few wide greps covering many entries at once rather than one grep per entry.
- **Apply results via `{id: (status, note)}`**, not per-entry `Edit` — every `status:` line is textually identical and unaddressable on its own.
- **Commit per project.**
- **Prove each verdict by reading or executing the actual code**, never by pattern-matching the entry's own prose back at itself. Three entries were only correctly resolved by actually *running* the code: AST-evasion, a dict-key collapse, and a schema-gap reproduction. Reading alone was insufficient for those three.

## Named tooling gaps the campaign surfaced, still unfixed as of this Spec

- `normalize_deferred_ledgers.py` cannot see a heading-less entry (undercounted marshal's real deferral count by 2 at the time) — the same blind spot `deferred-work-audit-completeness` documents independently, six weeks later, from the promotion side. Shared root cause; see this Spec's own Constraints.
- `warden DW-1-4-1` — marked `done` off the wrong half of two deferrals sharing one id — still needs splitting into two ids.
- Atlas's own frontmatter declared `entries: 55` against 57 real entries, in a file whose whole job is to declare that count correctly.
