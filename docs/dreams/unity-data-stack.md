---
title: Unity Data Stack — the enterprise innersource platform
type: dream
owner: crew
status: in-spec
---

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
