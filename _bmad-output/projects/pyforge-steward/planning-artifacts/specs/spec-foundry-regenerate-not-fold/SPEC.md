---
spec: foundry-regenerate-not-fold
status: ready
created: "2026-09-13"
updated: "2026-09-13"
owner-dream: docs/dreams/foundry-regenerate-not-fold.md
extends: spec-python-foundry-cutover
surface: []
companions:
  - ab-sync.md
sources:
  - ../../../../../../docs/dreams/foundry-regenerate-not-fold.md
open_questions: []
---

> **Canonical contract.** Derived 2026-09-13 from
> `docs/dreams/foundry-regenerate-not-fold.md` and `.memlog.md`. Extends
> `spec-python-foundry-cutover`; cite this file's ids as `fnr:CAP-1..5`.
> Decomposed as steward **Epic 54**. Does not flip any Epic 44 `blocked`
> key. Does not dispatch 44.4, 44.5, or 44.6. Companion `ab-sync.md` is
> the dual-root protocol.

# SPEC — Foundry regenerate, not fold

## Why

**A mandate to meet and a vision to realize.** Launch the Foundry / Adopt
Frames / Build the Intelligence Hub / Wire the BMAD-suite cannot be a
`src/shared/packages` path-rename. Foundry is a clean BMAD-on-B tree.
local-recipes is the A control and legacy oracle. The shared starting
contract is Dream + Frame + Spec five-fields; behavior is A/B tested.
Historical PRD / arch / epics / comments stay on A.

## Capabilities

- **CAP-1 — Thin oracle.**
  - **intent:** The operator can freeze a small archived suite that is
    also the A/B case list for the foundry kernel.
  - **success:** A tracked list of about 20–40 existing core / steward /
    marshal cases lives with this Spec (and on B after 54.5); those cases
    run against foundry trees; Frame frontmatter preflight alone is not
    acceptance.

- **CAP-2 — Rebuild `pyforge-core` in foundry.**
  - **intent:** Foundry gains `station_port`, hooks, and the cutover-root
    reader as a new leaf under `src/packages/`, not a copy of
    `src/shared/packages/pyforge-core`.
  - **success:** The public core contract plus the CAP-1 core slice are
    green on B, with an A/B row that is not `diverge`.

- **CAP-3 — Rebuild steward in foundry.**
  - **intent:** `pyforge steward` (provision, workspace, frames, guards,
    cutover, suite register path) exists as a regenerated engine with CLI
    and MCP.
  - **success:** Steward's CAP-1 slice is green on B with an A/B row;
    implementation commits land only in a python-foundry worktree.

- **CAP-4 — Rebuild marshal in foundry.**
  - **intent:** `pyforge marshal` cursor-native dispatch exists as a
    regenerated engine with CLI and MCP.
  - **success:** One dispatch against the foundry remote plus the CAP-1
    marshal slice are green with an A/B row. Drain corners not in the
    thin list stay on A until `fnd:CAP-9` / 44.14 grows the list.

- **CAP-5 — Dual-root A/B.**
  - **intent:** The operator can keep one starting contract across two
    git roots and compare behavior without copying BMAD trees or code.
  - **success:** `ab-sync.md` is in `companions:`; B (after 54.5) has a
    pin file and a case-list stub; writer lock holds (one Dream author);
    `diverge` blocks `verified-in-foundry`; no `_bmad-output` rsync.

## Constraints

- After the 48h kit exists on B, B is writer for new Dreams / Frames /
  Specs. A mirrors by SHA pin. Until then this Spec on A is the seed.
- Factory / CFE / recipes stay invented on A until a foundry CFE exists.
  Kernel package commits only on B.
- Public CLI verbs stay (`pyforge steward`, `pyforge marshal`, `warden scan`).
- `steward cutover apply --phase 1a` is not how packages appear.
- `pyforge.cutover_root` stays `local-recipes` until the kernel passes
  the shared list; the flip is attended and refused while a loop is running.
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
- Moving the CFE cell (44.6). Foundry CFE is rebuilt from Specs; A is the oracle.
- Byte-sync of PRD, ARCH, epics, sprint files, stories, or package trees.

## Success signal

A new builder can open B, read the slim kit, and implement in
`src/packages/` without reading A's cutover novel. Kernel CLI + MCP on B
pass the shared case list; A/B rows are not `diverge`; no package fold
and no host.

## Assumptions

- Factory island (44.7) and the cutover flag (44.12) already exist on
  foundry / local-recipes and stay.
- Frames (53.2) and Hub objects (53.1–53.4) on A are the first pin
  targets, not cargo to fold.
