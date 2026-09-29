---
title: '10.5: The DB-GPT sidecar image + docker-compose wiring'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** DB-GPT's Pattern-B deviation (pap:AD-14, dated 2026-08-21 in `db-gpt-django-plugin.md`) **Then** a `docker-compose.yml` service builds and runs DB-GPT as its own container (model worker + API server), rootless-clean under the same Docker∩Podman intersection discipline as Story 10.3's image, wired into the local-dev tiers (pap:AD-16) and platform CI so 11.2's sidecar integration is testable end-to…

**Approach:** a `docker-compose.yml` service builds and runs DB-GPT as its own container (model worker + API server), rootless-clean under the same Docker∩Podman intersection discipline as Story 10.3's image, wired into the local-dev tiers (pap:AD-16) and platform CI so 11.2's sidecar integration is testable end-to-end without a manual DB-GPT setup step. Added 2026-08-21 — Story 10.3 shipped "one image, both e…

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-10-5-the-db-gpt-sidecar-image-docker-compose-wiring.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| DB-GPT's Pattern-B deviation (pap:AD-14, dated 2026-08-21 in `db-gpt-django-plugin.md`) **Then** a `docker-compose.yml` service builds and runs DB-GPT as its o… | as in epics.md | a `docker-compose.yml` service builds and runs DB-GPT as its own container (model worker + API server), rootless-clean under the same Docker∩Podman intersection discipline as Story 10.3's image, wire… | fail loud; never silent skip |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `src/platform/compose/dbgpt/`, platform CI
Ledger key: `10-5-the-db-gpt-sidecar-image-docker-compose-wiring`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-10-5-the-db-gpt-sidecar-image-docker-compose-wiring.md`.

## Epic excerpt

**Type:** infra • **Effort:** M • **Deps:** S-10.3 • **FR/AD:** pap:CAP-6, pap:AD-17
**Surface:** `src/platform/compose/dbgpt/`, platform CI
**Given** DB-GPT's Pattern-B deviation (pap:AD-14, dated 2026-08-21 in `db-gpt-django-plugin.md`)
**Then** a `docker-compose.yml` service builds and runs DB-GPT as its own container (model
worker + API server), rootless-clean under the same Docker∩Podman intersection discipline as
Story 10.3's image, wired into the local-dev tiers (pap:AD-16) and platform CI so 11.2's sidecar
integration is testable end-to-end without a manual DB-GPT setup step. Added 2026-08-21 —
Story 10.3 shipped "one image, both engines" before this deviation existed; this is the
additive counterpart for the engine that no longer fits that image, not a correction to 10.3.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `087d218fbd` (2026-08-21, "Merge pull request #583 from rxm7706/steward/10-5-db-gpt-sidecar-compose"). Ledger row `10-5-the-db-gpt-sidecar-image-docker-compose-wiring: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.github/workflows/platform-ci.yml`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `pixi.lock`, `pixi.toml`, `src/platform/compose/compose.yml`, `src/platform/compose/dbgpt/Containerfile`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
