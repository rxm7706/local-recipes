---
spec: bmad-suite-metapackage
status: shipped   # 2026-09-06 — CAP-1..4 as steward Epic 39 (4/4 done 2026-09-01); recorded late
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
  - "The 13-package install-matrix remains the authoritative population. Superseded 2026-09-06:
    `bmad-method-wds-expansion` was retired 2026-09-05 (deprecated upstream in the 6.12.0 module
    registry, absorbed into `bmad-ux`; recipe kept as a catalog row only) — it is no longer a
    published-but-skip-wired member; `bmad-eval-quality` is seated in its place."
  - "Member upstream resolution uses each recipe's cfe-upstream-registry (github/npm/pypi),
    matching doctor Story 19.1 — not npm-first globally."
  - "LIVE DRIFT, 2026-09-09: `recipes/bmad-suite/recipe.yaml:14` reads `2026.9.9` while
    `pixi.lock:17510` still resolves `bmad-suite-2026.9.5`. The metapackage's own criterion —
    one install pulls every channel product at upstream-aligned floors — is true of the RECIPE
    and NOT in effect in the LOCK until the next lock refresh. `bmad-suite-full` therefore still
    resolves eval-quality through the old metapackage's floor; publishing 2026.9.9 is what moves
    it."
updated: "2026-09-09"
open_questions: []
  # ANSWERED 2026-09-09, both retired (batch row stA-C7):
  # - Version scheme: CalVer refresh stamp (unpadded), as already shipped —
  #   `recipes/bmad-suite/recipe.yaml:13-14` says so in the file ("bumped by `generate-bmad-suite`
  #   when pins change"); live value 2026.9.9. The default at spec time held.
  # - bmad-method's channel: **conda-forge is canonical** for bmad-method; SelfExplainML carries
  #   refresh-parity for the other twelve (`install-matrix.md:14,:43`).
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
  - **verified:** 2026-09-11 — `bmad_method.py:372` (`_SUITE_MANIFEST_REL`) and `:411`
    (`_manifest_suite_members`) read `recipes/bmad-suite/suite-members.yaml` directly; live
    `pipeline-truth --json` returned exactly 13 active members this session, matching the
    manifest.

- **CAP-2 — Metapackage recipe.** *Intent:* `recipes/bmad-suite/recipe.yaml` is a
  `noarch: generic` metapackage whose `requirements.run` pins each manifest member at `>=`
  the resolved upstream version (exact `==` optional for lock-step refresh PRs). Own
  `context.version` is a CalVer refresh stamp bumped whenever any member version in the
  generated block changes. *Success:* `pixi run -e local-recipes recipe-build recipes/bmad-suite`
  succeeds; tests assert every manifest member appears in `requirements.run`.
  - **verified:** 2026-09-11 — this session's own PR #1205: `recipe-build recipes/bmad-suite`
    built `bmad-suite-2026.9.11` green with all anchor-CLI tests passing (`bmad-loop --version`,
    `bmad-module-skill-forge --help`, etc.); `requirements.run` carries all 13 active members
    (verified by direct read).

- **CAP-3 — Generator / refresh command.** *Intent:* one command (steward duty or CFE script)
  resolves upstream latest per member using registry class from each member's
  `recipes/<name>/recipe.yaml`, rewrites the metapackage pin block + version stamp, and prints a
  diff summary (member, old pin, new upstream, registry used). *Success:* dry-run against live
  upstream reproduces the 2026-09-01 channel table within one patch version; github-primary
  packages never consult stale npm.
  - **verified:** 2026-09-11 — this session's own `generate-bmad-suite --dry-run` resolved
    live upstream per member (`[npm+floor]`/`[github+floor]`/`[recipe-floor]` tags shown per
    member in the diff summary), correctly flagged only `bmad-method-test-architecture-enterprise`
    and `bmad-eval-quality` as changed and everything else unchanged.

- **CAP-4 — Channel publish + pixi feature (optional follow-on).** *Intent:* publish
  `bmad-suite` to SelfExplainML; add optional `feature.bmad-suite-full` in `pixi.toml` that
  depends on `bmad-suite` instead of enumerating members. *Success:* `pixi install -e
  local-recipes` with feature enabled resolves the bundle; documented in install-matrix.
  - **verified:** 2026-09-11 — the served `conda.anaconda.org/selfexplainml/noarch/repodata.json`
    lists real published `bmad-suite` builds (2026.9.1, 2026.9.5, 2026.9.9 — 2026.9.11 from this
    session not yet uploaded, an operator step by design); `feature.bmad-suite-full` at
    `pixi.toml:1989`; `tests/packaging/test_bmad_suite_full_feature.py` 9/9 pass.

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
