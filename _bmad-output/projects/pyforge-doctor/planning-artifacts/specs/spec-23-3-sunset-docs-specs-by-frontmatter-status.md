---
title: '23.3: Sunset docs/specs/ by frontmatter status'
type: 'feature'
created: '2026-09-16'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 19 legacy intake specs still live in docs/specs/ with YAML status:.

**Approach:** shipped and superseded move to archive/docs/specs/. in-progress stays. Each workflow body moves to docs/how-to/ with a stub at docs/specs/<name>.md (status: workflow + pointer). --specs still lists the three workflow stubs; CLAUDE.md still indexes those filenames.

## Boundaries & Constraints

**Always:**
- No shipped/superseded Tier-1 spec remains the live home.
- python scripts/bmad_drift_check.py --specs still lists the three workflow stubs.

**Never:**
- Do not drop the --specs glob of docs/specs/*.md.
- Do not author new specs under docs/specs/.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| shipped intake | docs/specs/<name>.md status shipped | lives under archive/docs/specs/ | n/a |
| workflow | status: workflow | body in docs/how-to/; stub remains | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-docs-shelf-alignment CAP-3`.
Surface: docs/specs/, docs/how-to/, archive/docs/specs/, CLAUDE.md, scripts/bmad_drift_check.py --specs..
Ledger key: `23-3-sunset-docs-specs-by-frontmatter-status`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-3-sunset-docs-specs-by-frontmatter-status.md`.
