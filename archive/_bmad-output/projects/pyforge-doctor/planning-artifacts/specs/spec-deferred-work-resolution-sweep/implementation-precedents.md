# Implementation precedents worth reusing

Prior art the source Dream names explicitly, offered as a starting point for whoever implements CAP-2/CAP-3's cost-bounding — reuse the shape, don't reinvent it.

## Cost-bounding shape

This fleet already has two precedents for bounding a recurring, growing verification cost:

- **`bmad-loop`'s own `limits.max_followup_reviews`** — a hard ceiling on repeated review passes per story. The same damping-cap shape applies to a resolution sweep: bound how much re-verification effort any one entry (or batch) can consume per run.
- **`pyforge-warden`'s own product domain** — a compliance gate built entirely around baseline/grandfathering/waiver semantics for "known finding, don't re-flag every run until something changes." Reusing warden's *design pattern* (not the tool itself) for "known-still-open, don't re-verify every run until the churn filter says something changed" would be a fitting, self-referential fit for this Spec's own CAP-2.

## Tiered-check shape

`spec_surface_check.py`'s own two-tier design — hash-drift is mechanical and resolved without judgment; `drift-presumed` needs a human to confirm the memlog covers it — is the direct precedent for CAP-3's mechanical-first, agent-escalation-second split. Reuse that shape rather than inventing a new one.

## Cross-project-sync precedent

The value CAP-6 (cross-entry, cross-project correlation) targets is the same shape of value BMAD's own cross-spec-sync convention already recognizes for specs (see auto-memory `feedback_specs_cross_sync`) — a shared-fact change in one place implies checking siblings, and deferred-work entries deserve the same treatment as specs do there.
