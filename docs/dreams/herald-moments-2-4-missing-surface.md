---
title: Herald — Moments 2–4 Missing Surface
type: dream
owner: herald
status: pitched
---

# Herald — Moments 2–4 Missing Surface

## The Dream

Herald orchestrates **Four Moments of Proclamation** across the factory:

1. **Moment 1: Pitch** — A dream must be argued. The case made legible to non-dreamers. ✅ **READY** (Deck family spec complete)
2. **Moment 2: Progress** — A build in flight is not self-explaining. What changed, what it cost, what it unblocked. 📋 **SPECCED, UNBUILT**
3. **Moment 3: Success** — Shipping is not the same as being known to have shipped. The claim with evidence attached. 📋 **SPECCED, UNBUILT**
4. **Moment 4: Operations** — The long tail nobody announces. Fixes, updates, deprecations, end-of-life. ⚠️ **ZERO IMPLEMENTATION**

This dream addresses the **3 missing surfaces**: Moments 2, 3, and 4.

---

## Why It Matters

Herald Moment 1 (deck family) is a narrative tool for *launching* ideas. But proclamation doesn't end at launch:

- **Moment 2 (Progress)**: When we ship a new station, update a major component, or cross a milestone, who knows? A weekly/monthly artifact proving motion and explaining cost.
- **Moment 3 (Success)**: When a project ships, who knows it shipped? Success requires **claim + evidence** — not just a closed PR, but a public statement linking to proof (tests passing, metrics green, users adopting).
- **Moment 4 (Operations)**: Deprecations, security fixes, end-of-life notices — the unglamorous tail that protects users but nobody announces. Requires **proactive surfaces** (published notices, timeline archives, redirect rules).

---

## What is Real

- **Specs exist** for Moments 2 and 3 in `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/` (archived from prior work).
- **Moment 1 spec is complete** and production-ready (spec-herald-pitch/).
- **Moment 4 has zero implementation** — only a mention in the Herald Four Moments framework.

---

## Realization Log

- **2026-07** — Herald's Four Moments framework established (docs/dreams/pyforge-herald.md).
- **2026-08-01** — Moment 1 (Pitch) fleet-chain-completeness regeneration: Dream → Spec → PRD → Architecture → Epics → Stories fully grounded.
- **2026-08-02** — Identified 3 missing surfaces for Moments 2–4. Opening this dream to prioritize surface completion.

---

## Next Steps (Planning Phase)

1. **Audit existing Moment 2 & 3 specs** — retrieve from archive, assess completeness and currency.
2. **Author Moment 4 spec** — from first principles (deprecation & end-of-life proclamation workflow).
3. **Decide orchestration strategy** — separate specs/dreams per Moment, or unified Herald v2 spec?
4. **Scope surface delivery** — Moment 2 (dashboard widget?), Moment 3 (release page?), Moment 4 (archive + redirect rules?).

---

## Success Criteria

- [ ] All three Moment specs (2, 3, 4) drafted and reviewed
- [ ] Surface strategy decided (format, frequency, automation)
- [ ] Each Moment has a clear entry point in Herald CLI / web surface
- [ ] Automation identified (what triggers Moment 2 updates? Who authors Moment 3 claims?)
