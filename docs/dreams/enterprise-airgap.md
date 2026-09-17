---title: Firewalled Factory
type: practice
owner: steward
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-steward]]** on 2026-09-17 (one-chain-per-station steward fold; folded from `enterprise-airgap`).


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
- **Closed (2026-09-09)** — the `JFROG_API_KEY` cross-resolver leak (the header
  attaching to every outbound request regardless of host) is **fixed**:
  `_http.py:508` gates `X-JFrog-Art-Api` on `is_configured_host`, with regression
  coverage in `tests/unit/test_http_jfrog_host_gate.py`,
  `test_dependency_checker_auth_host_gate.py` (including "never sent to an
  explicitly named public channel") and `test_inventory_channel_auth_host_gate.py`.
  ([[pyforge-doctor]] found it; [[pyforge-steward]] still owns the key lifecycle.)
- **Deployment & install operations** (bundles, OpenShift, mirrors) are the
  **Steward's** station ([[pyforge-steward]], adopted 2026-07-23).
- Offline bundle format for the whole operating model ([[pyforge-genesis]]
  behind a firewall) — kinship with [[sentinel]]'s §40 Airgap Bundle & Install.

## Kinships

- **[[miniforge-installer]]** (mason) — **reciprocal, recorded 2026-09-09.** Its activation
  trigger is *steward-owned and un-watched*: "steward's enterprise-airgap / Story 12.3 work
  surfaces a private-channel-locking need for a Python distributable." The socket already
  exists and is empty by design —
  `src/shared/packages/pyforge-mason/src/pyforge/mason/airgap_contract.py:54`,
  `SUPPORTED_DISTRIBUTABLES: dict[str, DistributableBackend] = {}`
  ("Empty by design (Story 9.2). External installers register later."). So whoever runs CAP-3's
  mirror exercise or Story 12.3's air-gap parity check must also decide whether a Python
  distributable needs private-channel locking, and tell mason if it does — nothing on the mason
  side watches for it. *(Fleet readiness 2026-09-09, mason-E1 / Class D D11; the reciprocal half
  is a note on `spec-enterprise-airgap`'s memlog.)*

## Realization log

- **2026 (CFE v6.0→v7.0)** — enterprise routing shipped runtime-driven.
- **2026-07-23** — Dream retro-seeded from the deployment doc + the pattern's
  presence across atlas/warden/presenton/deckcraft.
- **2026-09-09** — **Fleet readiness pass** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, row stA / § C2). The host-gate fix verified live (`_http.py:508` plus five regression-test files); § *The frontier*'s "Known health issue" bullet was stale, security-shaped text and is closed. **Still unexercised:** CAP-3's success clause ("pipeline phases run against a JFrog remote-repo mirror unchanged") has no recorded run — realization-gate partial, placed `foundry-side`. Status stays `realized`.
