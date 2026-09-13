---
spec: foundry-regenerate-not-fold
status: ready
created: "2026-09-13"
updated: "2026-09-13"
owner-dream: docs/dreams/foundry-regenerate-not-fold.md
extends: spec-python-foundry-cutover
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/foundry-regenerate-not-fold.md
open_questions: []
---

> **Canonical contract.** Derived 2026-09-13 from
> `docs/dreams/foundry-regenerate-not-fold.md` and `.memlog.md`. Extends
> `spec-python-foundry-cutover`; cite this file's ids as `fnr:CAP-1..4`.
> Decomposed as steward **Epic 54**. Does not flip any Epic 44 `blocked`
> key. Does not dispatch 44.4 or 44.5.

# SPEC — Foundry regenerate, not fold

## Why

**A mandate to meet and a vision to realize.** Launch the Foundry / Adopt
Frames / Build the Intelligence Hub / Wire the BMAD-suite cannot be a
`src/shared/packages` path-rename. Frames, the suite register, and a live
second root make a fold the worst remaining option. Foundry must be
regenerated from contracts; local-recipes stays the invention root.

## Capabilities

- **CAP-1 — Thin oracle.**
  - **intent:** The operator can freeze a small archived suite that the
    foundry kernel must pass before a station row is `verified-in-foundry`.
  - **success:** A tracked list of about 20–40 existing core / steward /
    marshal tests lives under planning-artifacts; those tests run against
    foundry trees; Frame frontmatter preflight alone is not acceptance.

- **CAP-2 — Rebuild `pyforge-core` in foundry.**
  - **intent:** Foundry gains `station_port`, hooks, and the cutover-root
    reader as a new leaf under `src/packages/`, not a copy of
    `src/shared/packages/pyforge-core`.
  - **success:** The public core contract plus the CAP-1 core slice are
    green on a python-foundry checkout.

- **CAP-3 — Rebuild steward in foundry.**
  - **intent:** `pyforge steward` (provision, workspace, frames, guards,
    cutover, suite register path) exists as a regenerated engine with CLI
    and MCP.
  - **success:** Steward's CAP-1 slice is green; implementation commits
    land only in a python-foundry worktree.

- **CAP-4 — Rebuild marshal in foundry.**
  - **intent:** `pyforge marshal` cursor-native dispatch exists as a
    regenerated engine with CLI and MCP.
  - **success:** One dispatch against the foundry remote plus the CAP-1
    marshal slice are green. Drain corners not in the thin list stay on
    local-recipes until `fnd:CAP-9` / 44.14 grows the oracle.

## Constraints

- Invent contracts in `local-recipes`; implement new packages only in
  `python-foundry`.
- Public CLI verbs stay (`pyforge steward`, `pyforge marshal`, `warden scan`).
- `steward cutover apply --phase 1a` is not how packages appear.
- `pyforge.cutover_root` stays `local-recipes` until the kernel is
  verified; the flip is attended and refused while a loop is running.
- Never commit on the shared local-recipes checkout; never
  `scripts/bmad-switch` from a parallel agent.
- Do not flip Epic 44 `blocked` keys (44.9, 44.10, 44.11, 44.14, 44.15, 44.1, 44.8).

## Non-goals

- Folding `src/shared/packages/` via 44.4 / apply phase 1a.
- Host, `/console/`, or seven `django-*` portals in Launch.
- Renaming public CLI verbs.
- conda-forge / staged-recipes / feedstock PRs (44.9).
- Copying the recipe universe (44.8) or archiving local-recipes (44.10).
- Waiting for a complete 44.14 oracle before the kernel exists.

## Success signal

A python-foundry checkout runs `pyforge` core, steward, and marshal CLI +
MCP, passes the thin archived suite, and completes one marshal dispatch
against the foundry remote — with no package fold and no host.

## Assumptions

- Factory island (44.7) and the cutover flag (44.12) already exist on
  foundry / local-recipes and stay.
- Frames (53.2) and Hub objects (53.1–53.4) are already on local-recipes
  main and are cargo by re-provision / docs copy, not by engine fold.
