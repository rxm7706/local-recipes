---
spec: bmad-suite-channel-product
status: ready
owner-dream: docs/dreams/bmad-suite-channel-product.md
surface: []   # populated as stories land (pipeline report/advance tooling, provision.py _SUPPORTED_MODULES, matrix doc)
companions:
  - install-matrix.md
sources:
  - ../../../../../../docs/dreams/bmad-suite-channel-product.md
assumptions:
  - "The 2026-08-22 currency state holds as the baseline: 5 tag-pinned recipes
    at newest tag, 6 commit-pinned at literal HEAD; TEA v1.23.3 stays a watch
    until npm/GH release it."
open_questions:
  - "CAP-2 scheduling: manual-on-drift-signal only, or a Phase-K-style
    scheduled sweep? Decide at story time — CAP-1's report plus doctor's
    ambient findings may make a schedule redundant."
---

# SPEC — The SelfExplainML bmad-suite is a governed product

## Why

The operator intends to utilize all 13 suite packages, installable two ways at
all times (pixi from SelfExplainML; upstream-native per package) at the latest
version, with modules actually wired. Today that held only because a human
hand-drove all seven pipeline stages during the 2026-08-21/22 refresh — the
stages exist as isolated tools with no connections, schedule, or verification,
and the channel served a stale `bmad-method 6.3.0` for four months unnoticed.
Owner: **steward** (publishing, provisioning, scheduled operations); doctor
keeps detection (relayed), CFE keeps recipe-bump machinery (Rules 1/2), mason
keeps validation. Operator decisions locked 2026-08-22: channel bmad-method
**refreshed** to 6.11.0 (executed same session), and the standing policy —
always upgrade and refresh any outdated component, never leave a stale copy
because it is shadowed.

## Capabilities

- **CAP-1 — Pipeline-truth report.** *Intent:* one command reports, for each
  of the 13 packages: upstream latest (npm AND GitHub, per its class), recipe
  version, channel version, installed version, wired-or-not — drift named per
  stage. *Success:* run against the 2026-08-22 state it reproduces the
  research matrix (including the 6.3.0 relic until refreshed); offline it
  degrades fail-open per stage.
- **CAP-2 — End-to-end advance.** *Intent:* one command takes a stale package
  through autotick (tag-mode, or a new HEAD-advance mode for the six
  commit-pinned dev recipes) → build → test → publish → listing verified,
  landing as a reviewable PR — never auto-merged. *Success:* replays the
  2026-08-21 seven-stage hand ritual for one package with zero improvised
  steps.
- **CAP-3 — Module wiring through the verb.** *Intent:*
  `steward provision --module` grows `_SUPPORTED_MODULES` from `{bmb}` to
  `{bmb, tea, cis, utility-skills, manticore}` — each addition
  manifest-recorded, skill-name-collision-checked, retired-ID guard +
  integrity meta tests green, reproducible on a fresh clone. WDS is an
  explicit skip (deprecated upstream, absorbing into bmad-ux). *Success:* all
  five wire-decided modules provision through the verb and `.claude/skills`
  gains the expected skill sets.
- **CAP-4 — Dual-path contract.** *Intent:* the per-package install matrix
  (pixi command + native command with upstream citation + hazard flags:
  npm-invisible ×7, npm-stale ×3, name-collisions ×3) is a tracked artifact
  (`install-matrix.md`), and the upgrade verification gate spot-checks one
  native path per class instead of trusting docs. *Success:* the matrix
  exists cited; a gate run exercises ≥1 command per class.
- **CAP-5 — Ambient drift, relayed to doctor.** *Intent:* channel-vs-recipe
  and recipe-vs-upstream join doctor's suite-drift surfaces (fail-open,
  warn-only), and the GitHub-releases fallback (doctor DW-14-1-1) unblinds
  the 7 npm-invisible packages. *Success:* a fixture of the 6.3.0 relic fires
  channel-drift; the fallback names bmad-loop's version from GitHub.
- **CAP-6 — Suite metapackage (2026-09-01).** *Intent:* one conda metapackage
  (`bmad-suite`) plus canonical manifest install all 13 channel products at
  upstream-aligned pins; generator refreshes from registry class per member.
  *Success:* decomposed in `spec-bmad-suite-metapackage`; doctor Epic 19 consumes
  the same manifest for its watched set.

## Constraints

- conda-forge stays canonical for `bmad-method` (its feedstock is current);
  the channel copy is refresh-parity, never a fork; no other suite package
  goes to conda-forge.
- Wiring is deliberate per-module triage — never wire-everything.
- Publishing stays credential-gated via steward's key discipline;
  publish-before-floor-bump ordering holds.
- Commit-pinned dev recipes keep the `X.Y.Z.dev0 @ <sha>` encoding and the
  G109 version-of-record re-derivation rule.
- Autotick output lands as reviewable PRs; git review decides.
- Native commands come from upstream READMEs with citations — never invented.

## Non-goals

- Packaging anything new (autopilot/bmalph/dashboard-extension stay parked).
- Submitting more suite packages to conda-forge.
- The core-upgrade apply (steward Epic 14) and era retrofits (marshal
  Epic 25) — kin chains this pipeline feeds and consumes.
- The operator's incoming OCP hybrid-environment effort — its BMAD-wiring
  phase CONSUMES CAP-3 (its wiring table is this chain's target state); the
  OCP environment itself is that Dream's scope, not this one's.

## Success signal

`pipeline-truth` reports all-green across 13 packages × 5 stages with zero
hand-checks; a deliberately staled fixture package advances end-to-end
through one command into a reviewable PR; all five wire-decided modules
provision through the verb on a fresh clone; and the next suite release is
absorbed without a single improvised step — the 2026-08-21 ritual never
happens by hand again.
