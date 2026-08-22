---
spec: developer-machine-bootstrap
status: ready
owner-dream: docs/dreams/developer-machine-bootstrap.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/developer-machine-bootstrap.md
open_questions:
  - "Container-verified bootstrap: podman-in-podman or a dedicated CI lane? Decide at story time."
---

# SPEC — A fresh machine reaches validate-fast through steward verbs

## Why
Onboarding is undocumented ritual: pixi + git + gh + podman + clones + env
installs + hooks, hand-driven per machine. The sibling PyForge org's
same-name dream contributes a proven command surface (pattern only —
unlicensed; intake report 2026-08-22).

## Capabilities
- **CAP-1 — bootstrap verbs.** *Intent:* `steward init` (prereq detection
  with floors from the pixi version registry), `shell-init`, `setup`
  (clone + pixi install + hooks), `initrepo` — fresh machine to
  validate-fast green. *Success:* the flow reproduces in a clean container;
  every prereq failure names its remedy.

## Constraints
Consumes provision --env/--runner (Epic 3), the OCP 12.4 bring-up, and the
fifteen-factors devinfra substrate — never duplicates them; floors read
`scripts/pixi_version_registry.py`.

## Non-goals
Cluster bring-up (12.4); backing services (fifteen-factors); multi-repo
workspaces (Epic 13 extension).

## Success signal
A recorded clean-container run: nothing → validate-fast passing, zero
improvised steps.
