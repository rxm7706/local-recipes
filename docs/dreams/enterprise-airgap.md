---
title: Firewalled Factory
type: practice
owner: steward
status: realized
---

# Enterprise air-gap — everything works where the internet doesn't

## The Dream

The whole factory — packaging, intelligence, gates, decks — runs inside
regulated, air-gapped enterprises as naturally as it runs here: every outbound
dependency routable through JFrog Artifactory / internal mirrors, every
capability offline-first by design, credentials handled without leakage. Not a
port; a posture: **air-gapped is the default deployment story, not an
afterthought.**

## What is real (the core)

- **`docs/reference/enterprise-deployment.md`** + `docs/reference/pixi-config-jfrog.example.toml` —
  the deployment doctrine.
- **Runtime-driven routing** in `_http.py`: truststore + JFrog/GitHub/.netrc
  auth chain — env-vars only, never committed config (CFE v6.0/v7.0).
- **Air-gap-by-design decisions** across the stack: atlas's
  `current_repodata.json` choice (explicitly JFrog-reusable), offline-safe read
  CLIs, offline-safe deck bundles, the Pyodide/WASM atlas compilation
  ([[pyforge-atlas]] G1).

## The frontier

- **[[presenton-pixi-image]]** and **[[deckcraft]]** — the two air-gapped
  application expressions, both unbuilt.
- **Warden's registry perimeter** ([[pyforge-warden]] ring 2): block/allow lists
  on Artifactory — quarantine before the firewall.
- **Known health issue**: `JFROG_API_KEY` unconditional injection in `_http.py`
  — the header attaches to every outbound request regardless of host.
  Cross-resolver credential leak; fix before wider enterprise rollout.
  ([[pyforge-doctor]] finds; [[pyforge-steward]] remediates and owns the key
  lifecycle.)
- **Deployment & install operations** (bundles, OpenShift, mirrors) are the
  **Steward's** station ([[pyforge-steward]], adopted 2026-07-23).
- Offline bundle format for the whole operating model ([[pyforge-genesis]]
  behind a firewall) — kinship with [[sentinel]]'s §40 Airgap Bundle & Install.

## Realization log

- **2026 (CFE v6.0→v7.0)** — enterprise routing shipped runtime-driven.
- **2026-07-23** — Dream retro-seeded from the deployment doc + the pattern's
  presence across atlas/warden/presenton/deckcraft.
