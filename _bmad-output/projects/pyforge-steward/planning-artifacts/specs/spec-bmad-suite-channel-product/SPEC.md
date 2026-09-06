---
spec: bmad-suite-channel-product
status: shipped   # 2026-09-05 — CAP-1..5 as steward Epic 15 + doctor Epics 15/19, CAP-6 as steward Epic 39; first governed refresh ran 2026-09-05 (PRs #1059/#1060, metapackage 2026.9.5); residue relayed as deferred work
owner-dream: docs/dreams/bmad-suite-channel-product.md
surface: []   # none claimed: steward suite.py / provision.py, the metapackage recipe + generator are governed by their home specs (spec-bmad-suite-metapackage, steward and CFE surfaces)
companions:
  - install-matrix.md
sources:
  - ../../../../../../docs/dreams/bmad-suite-channel-product.md
assumptions:
  - "The 2026-09-05 state is the baseline (supersedes 2026-08-22): 6 tag-pinned
    recipes at newest tag, 7 commit-pinned at literal HEAD; TEA 1.24.0 released
    (the v1.23.3 watch closed); bmad-method 6.12.0 on conda-forge and the
    channel while the applied `_bmad/` core is 6.11.0 pending steward Epic 14."
open_questions:
  - "CAP-2 scheduling: manual-on-drift-signal only, or a Phase-K-style
    scheduled sweep? Story 15.2 did not decide it; the 2026-09-05 refresh was
    triggered by doctor's ambient drift plus the operator, not a schedule —
    manual-on-signal stays the default until a schedule earns its keep."
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

Shipped (re-checked 2026-09-05 after BMAD-METHOD 6.12.0): the governed
pipeline exists end to end and carried its first real refresh the same day —
method 6.12.0, eval-quality in, WDS out (deprecated in 6.12.0's module
registry), metapackage `2026.9.5`. Residue is relayed as deferred work, not
new capabilities.

## Capabilities

- **CAP-1 — Pipeline-truth report.** *Intent:* one command reports, for each
  of the 13 packages: upstream latest (npm AND GitHub, per its class), recipe
  version, channel version, installed version, wired-or-not — drift named per
  stage. *Success:* run against the 2026-08-22 state it reproduces the
  research matrix (including the 6.3.0 relic until refreshed); offline it
  degrades fail-open per stage. *(Shipped: steward 15.1; class-correct
  `wired` since 31.2. Known hole, relayed: for the installer-tree class the
  `installed` stage reads the pixi env's conda-meta, not the applied
  `_bmad/_config/manifest.yaml`.)*
- **CAP-2 — End-to-end advance.** *Intent:* one command takes a stale package
  through autotick (tag-mode, or a new HEAD-advance mode for the six
  commit-pinned dev recipes) → build → test → publish → listing verified,
  landing as a reviewable PR — never auto-merged. *Success:* replays the
  2026-08-21 seven-stage hand ritual for one package with zero improvised
  steps. *(Shipped: steward 15.2; `anaconda upload` stays the operator's
  step by design.)*
- **CAP-3 — Module wiring through the verb.** *Intent:*
  `steward provision --module` grows `_SUPPORTED_MODULES` from `{bmb}` to
  `{bmb, tea, cis, utility-skills, manticore}` — each addition
  manifest-recorded, skill-name-collision-checked, retired-ID guard +
  integrity meta tests green, reproducible on a fresh clone. WDS is an
  explicit skip (deprecated in 6.12.0's module registry, folded into
  `bmad-ux`; retired from the roster 2026-09-05). *Success:* all five
  wire-decided modules provision through the verb and `.claude/skills`
  gains the expected skill sets. *(Shipped: steward 15.3.)*
- **CAP-4 — Dual-path contract.** *Intent:* the per-package install matrix
  (pixi command + native command with upstream citation + hazard flags,
  recounted 2026-09-05: npm-invisible ×6, npm-stale-GitHub-canonical ×3,
  name-collisions ×3, G109 renumber ×2; eight native classes) is a tracked
  artifact (`install-matrix.md`), and the upgrade verification gate
  spot-checks one native path per class instead of trusting docs. *Success:*
  the matrix exists cited; a gate run exercises ≥1 command per class.
  *(Shipped: steward 15.4 + Epic 31; matrix re-verified 2026-09-05 against
  `pipeline-truth`.)*
- **CAP-5 — Ambient drift, relayed to doctor.** *Intent:* channel-vs-recipe
  and recipe-vs-upstream join doctor's suite-drift surfaces (fail-open,
  warn-only), and the GitHub-releases fallback (doctor DW-14-1-1) unblinds
  the 7 npm-invisible packages. *Success:* a fixture of the 6.3.0 relic fires
  channel-drift; the fallback names bmad-loop's version from GitHub.
  *(Shipped: doctor 15.1/15.2 + 19.1. Known hole, relayed: suite drift maps
  7 of 13 members — commit-pinned members unmapped.)*
- **CAP-6 — Suite metapackage (2026-09-01).** *Intent:* one conda metapackage
  (`bmad-suite`) plus canonical manifest install all 13 channel products at
  upstream-aligned pins; the generator refreshes from the registry class per
  member. *Success:* decomposed in `spec-bmad-suite-metapackage` and shipped
  as steward Epic 39 (39.1–39.4): `recipes/bmad-suite/{recipe.yaml,
  suite-members.yaml}`, `generate-bmad-suite` / `build-bmad-suite`, opt-in
  `feature.bmad-suite-full`; `bmad-suite 2026.9.5` on the channel; doctor
  Epic 19 consumes the same manifest for its watched set.

## Constraints

- conda-forge stays canonical for `bmad-method` (its feedstock is current);
  the channel copy is refresh-parity, never a fork; no other suite package
  goes to conda-forge.
- Wiring follows the adoption register (`spec-bmad-suite-lifecycle` CAP-1,
  2026-09-06) — the 2026-08-22 'never wire-everything' posture is superseded;
  a member's wiring changes only by changing its register row.
- Publishing stays credential-gated via steward's key discipline;
  publish-before-floor-bump ordering holds.
- Commit-pinned dev recipes keep the `X.Y.Z.dev0 @ <sha>` encoding and the
  G109 version-of-record re-derivation rule.
- Autotick output lands as reviewable PRs; git review decides.
- Native commands come from upstream READMEs with citations — never invented.
- A member the upstream module registry marks `deprecated: true` (WDS since
  6.12.0) stays in `suite-members.yaml` as a catalog row and never re-enters
  the metapackage run deps or the matrix; its recipe is kept, not deleted.

## Non-goals

- Packaging anything new (autopilot/bmalph/dashboard-extension stay parked).
- Submitting more suite packages to conda-forge.
- The core-upgrade apply (steward Epic 14) and era retrofits (marshal
  Epic 25 and its 6.12 round) — kin chains this pipeline feeds and consumes.
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

**Shipped evidence (2026-09-05):** `pipeline-truth` reports 13/13
recipe = channel = installed, with drift named only for the four modules
deliberately left unprovisioned here and the npm/GitHub divergence of builder
and CIS; the 2026-09-05 refresh (PRs #1059/#1060) ran the seven stages through
the governed machinery with upload the one operator step by design, and two
improvisations recorded (the unix-only `bmad-eval-quality` variant forced the
pin into per-platform target tables; the CFE-retro slices needed a CRLF
re-mirror). Residue relayed as deferred work, not CAPs: the installer-tree
`installed` stage reads the pixi env rather than the applied `_bmad/`
manifest; `bmad-eval-quality` lacks a `__win` variant; doctor's suite drift
maps 7 of 13.
