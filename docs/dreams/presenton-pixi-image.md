---
title: Presenton, conda-native — AI decks inside the regulated enterprise
type: dream
owner: mason
status: archived
archived-reason: blocked
blocked-on: Phase-0 decision gate (Epic 1)
---

> **Archived, blocked — the Dream-level narrative stays separate; the
> planning-chain documents were consolidated 2026-08-02.** The full BMAD
> planning chain (research → brief → PRD → architecture → 7 epics / 30
> stories) landed 2026-07-25 and has not moved since: no story has entered
> implementation, and the Phase-0 exit criteria this Dream's own frontmatter
> names (`blocked-on: Phase-0 decision gate`) remain unresolved — most
> load-bearingly, whether Microsoft's disconnected on-prem stack (GA
> 2026-02-24) already ships a Copilot-for-PowerPoint-equivalent, which bears
> directly on whether this Dream's core differentiator still holds. This
> record is genuinely unrelated subject matter to [[pyforge-mason]] — an
> air-gapped repackaging of a third-party AI deck tool, not part of the
> `mason` CLI — and the *Dream-level narrative* below stays archived on its
> own for exactly that reason.
>
> **2026-08-02 update:** the *planning-chain documents* — this project's
> brief, PRD, architecture spine, and Spec — were consolidated into
> `pyforge-mason`'s own single brief/PRD/architecture/Spec, per an explicit
> user override of the separation decision recorded above (shown this exact
> language before deciding). Each merged document now carries a clearly
> labeled "Satellite: Presenton" section holding this project's content
> verbatim, with a "Contradiction flagged" note recording the override. The
> originals were moved (not deleted) to
> `archive/_bmad-output/projects/pyforge-mason/planning-artifacts/{briefs,prds,architecture,specs}/…`.
> **What did NOT change:** this Dream file, the epics
> (`epics-presenton-pixi-image.md`, still separate from `pyforge-mason`'s own
> `epics.md`), and the blocked status — those remain exactly as archived
> above. Only the brief/PRD/architecture/Spec tier was folded in; see
> `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md`
> § *Satellite: Presenton* for the merged Spec (superseding the retirement
> record's own non-folding non-goal for that tier only) and
> `archive/_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-presenton-pixi-image/SPEC.md`
> for the original retirement record.

# Presenton for the air-gapped enterprise

## The Dream

Bring the Presenton AI deck-generation app to places SaaS cannot go: an
**air-gapped, conda-forge-native repackaging** deployable on OpenShift Container
Platform in regulated-enterprise environments. Every dependency resolved from
governed channels, every image reproducible, no call home — AI deck generation
as an internal platform service.

## What it looks like when real

- Presenton repackaged with conda-forge primitives (pixi-locked image,
  OpenShift-ready), passing [[pyforge-warden]]-grade dependency gates.
- Distribution through the [[enterprise-airgap]] machinery (Artifactory
  routing, offline bundles).
- Division of labor with [[deckcraft]]: presenton = the repackaged *app*;
  deckcraft = the from-primitives *pipeline*. Complementary, not competing.
- Stations: [[packaging-factory]] (Mason) repackages; **[[pyforge-steward]]
  deploys and operates** the OpenShift service.

## What is real

- The BMAD project `presenton-pixi-image` (registered, active). Planning not yet
  run under the Dream-first flow.

## Realization log

- **2026-07** — project registered in PROJECTS.md.
- **2026-07-23** — Dream retro-seeded; awaits `bmad-spec`.
- **2026-08-02** — **ARCHIVED (blocked)** during dream consolidation: the full
  planning chain landed 2026-07-25 (7 epics / 30 stories) and has not moved
  since — no story has entered implementation, and the Phase-0 exit criteria
  remain unresolved. See `spec-presenton-pixi-image`'s retirement record for
  the full account.
- **2026-08-02 (same day, later)** — the brief/PRD/architecture/Spec
  planning-chain tier (only) was consolidated into `pyforge-mason`'s own
  single documents per explicit user override; this Dream's own narrative and
  the epics/blocked-status were deliberately left as archived above. Originals
  moved to `archive/_bmad-output/projects/pyforge-mason/planning-artifacts/`.
