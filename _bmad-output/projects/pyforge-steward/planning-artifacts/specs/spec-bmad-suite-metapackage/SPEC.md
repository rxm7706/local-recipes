---
spec: bmad-suite-metapackage
status: ready
owner-dream: docs/dreams/bmad-suite-metapackage.md
surface:
  - recipes/bmad-suite/recipe.yaml
  - recipes/bmad-suite/suite-members.yaml
  - .claude/skills/conda-forge-expert/scripts/bmad_suite_metapackage.py
  - .claude/scripts/conda-forge-expert/bmad_suite_metapackage.py
companions:
  - suite-members.yaml
sources:
  - ../../../../../../docs/dreams/bmad-suite-metapackage.md
  - ../spec-bmad-suite-channel-product/install-matrix.md
assumptions:
  - "The 13-package install-matrix remains the authoritative population; WDS stays published
    but skip-wired per parent spec."
  - "Member upstream resolution uses each recipe's cfe-upstream-registry (github/npm/pypi),
    matching doctor Story 19.1 — not npm-first globally."
open_questions:
  - "Metapackage version scheme: CalVer refresh stamp (2026.9.1) vs composite hash of member
    versions? Default CalVer at spec time — sortable, human-readable on channel."
  - "Include bmad-method from conda-forge in run deps vs SelfExplainML refresh-parity copy only?
    Default: pin conda-forge channel for bmad-method, SelfExplainML for the other 12 (matches
    install-matrix 'conda-forge canonical' row)."
---

# SPEC — The bmad-suite metapackage

## Why

Operators install 11+ separate pixi pins to get the suite; the channel lists 13 products with
no single "give me all of it at latest" artifact. Drift between members (builder recipe 2.2.1
vs GitHub 2.2.2) has no bundle-level version to bump. A metapackage plus manifest gives one
install surface and one catalog file consumed by doctor ambient drift (Story 19.1).

Parent: `spec-bmad-suite-channel-product` (governed channel product). Kin: doctor Epic 19
(registry-aware upstream), CFE autotick (per-member bumps).

## Capabilities

- **CAP-1 — Canonical suite manifest.** *Intent:* tracked
  `recipes/bmad-suite/suite-members.yaml` lists every channel product by conda name
  (13 active + deprecated local-only recipes), with `deprecated: true` for packages
  removed from SelfExplainML (`bmad-autopilot`, `bmad-dashboard-extension`, `bmalph`).
  Deprecated rows stay in the manifest for doctor/catalog completeness but are **never**
  written into the metapackage `requirements.run`. *Success:* doctor Story 19.1 reads
  it; steward pipeline-truth cross-checks active population against install-matrix.

- **CAP-2 — Metapackage recipe.** *Intent:* `recipes/bmad-suite/recipe.yaml` is a
  `noarch: generic` metapackage whose `requirements.run` pins each manifest member at `>=`
  the resolved upstream version (exact `==` optional for lock-step refresh PRs). Own
  `context.version` is a CalVer refresh stamp bumped whenever any member version in the
  generated block changes. *Success:* `pixi run -e local-recipes recipe-build recipes/bmad-suite`
  succeeds; tests assert every manifest member appears in `requirements.run`.

- **CAP-3 — Generator / refresh command.** *Intent:* one command (steward duty or CFE script)
  resolves upstream latest per member using registry class from each member's
  `recipes/<name>/recipe.yaml`, rewrites the metapackage pin block + version stamp, and prints a
  diff summary (member, old pin, new upstream, registry used). *Success:* dry-run against live
  upstream reproduces the 2026-09-01 channel table within one patch version; github-primary
  packages never consult stale npm.

- **CAP-4 — Channel publish + pixi feature (optional follow-on).** *Intent:* publish
  `bmad-suite` to SelfExplainML; add optional `feature.bmad-suite-full` in `pixi.toml` that
  depends on `bmad-suite` instead of enumerating members. *Success:* `pixi install -e
  local-recipes` with feature enabled resolves the bundle; documented in install-matrix.

## Constraints

- Generator lives under CFE/steward tooling (Rule 1 conda-forge-expert for recipe shape);
  doctor only reads manifest (Rule: no duplicate pipeline-truth).
- Member recipes remain individually autotick-able; metapackage refresh is a **downstream**
  commit after member bumps land (or batch refresh PR that bumps members + metapackage together).
- `mybmad-dashboard` and `bmad-dashboard` stay platform-scoped where upstream requires —
  metapackage may use selectors or split into `bmad-suite` + `bmad-suite-ui` if noarch deps
  cannot express platform skips (decide at Story 19.2/steward story time).

## Non-goals

- Auto-merge metapackage refresh PRs.
- Provisioning / module wiring inside the metapackage.
- conda-forge feedstock for `bmad-suite`.

## Success signal

Channel listing shows `bmad-suite` with a CalVer version; installing it pulls all members at
upstream-aligned pins; doctor + pipeline-truth both derive the same 13-name set from
`suite-members.yaml`; one generator command replaces hand-maintaining 13 pixi pins for
greenfield installs.
