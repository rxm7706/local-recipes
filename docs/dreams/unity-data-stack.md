---
title: Unity Data Stack — the enterprise innersource platform
type: dream
owner: atlas
status: archived
archived-reason: absorbed
---

> **Superseded (narrative only).** This Dream's narrative now lives in
> [`docs/dreams/pyforge-atlas.md`](pyforge-atlas.md) § *The estate Atlas
> hosts*, which names Unity Data Stack as a separate, substantial initiative
> that Atlas's project tree hosts — **not** a capability of Atlas's own
> `cf_atlas` pipeline (`spec-pyforge-atlas`'s Capabilities are untouched) and
> **not** a duplicate of anything Atlas already builds. This is a dream-level
> consolidation only: Unity's own contract — 9 capabilities, FR-1–60 — still
> lives at `spec-unity-data-stack/SPEC.md`, with its own PRD
> (`prds/prd-unity-data-stack-2026-07-25/`) and Architecture spine
> (`architecture/architecture-unity-data-stack-2026-07-25/`) already
> produced; neither is touched by this consolidation. It is also **not**
> "the work is done" — epics/stories are deliberately not yet decomposed
> (planning ran to PRD + Architecture depth only) and no code has been
> written; the platform remains planning-complete and unscheduled. Archived
> 2026-08-02 as the narrative entry point only; its Spec/PRD/Architecture
> chain continues independently.

# Unity Data Stack — a python-first innersource delivery model

## The Dream

An opinionated **shared monorepo for the enterprise**: teams co-contribute
reusable templates, plugins, libraries, components, services, dashboards,
reports, and applications on one python-first engineering platform — the
**Inner-Source Model**: open-source culture and practices *inside* the
enterprise. Chosen standards, shared toolchain, faster delivery, consistency by
construction. Where [[pyforge-genesis]] installs the *operating model*, Unity
Data Stack is the *platform* an enterprise runs on it.

## What exists (stranded across three gists, now snapshot in `docs/intake/gists/`)

- **The Constitution** (`spec-kit/`, 37 KB) — the spec-kit-format founding
  document: preamble, principles, standards for the innersource monorepo.
- **The working root** (`unity-data-stack-pixi-toml/`, 100 KB) — a complete
  pixi monorepo workspace config: per-package environments, unified
  test/lint/check-all tasks matching CI.
- **The toolchain spec** (`bmad-method-spec-enterprise-monorepo…/`, 12 KB) —
  Pixi orchestrator root + PDM/pip-tools (PEP 751) compiler +
  `pylock.toml` universal secure lockfile, with an agent role matrix
  (Architect/Developer/DevOps/Security/Compliance) that prefigures the crew.
- Cameo: the "Unity Knowledge Stack" infographic in the [[sentinel]] Design
  session (2026-04-18).

## Kinships

[[pyforge-genesis]] (the installer would bootstrap Unity instances) ·
[[pyforge-warden]] (the Security/Compliance agents of the toolchain spec) ·
[[enterprise-airgap]] (the deployment posture) · [[packaging-factory]]
(conda-native package supply).

## Realization log

- **2026-01 → 05** — constitution, pixi root, and toolchain spec authored as
  gists; never landed in a repo.
- **2026-07-23** — rediscovered in the gist audit; Dream seeded.
