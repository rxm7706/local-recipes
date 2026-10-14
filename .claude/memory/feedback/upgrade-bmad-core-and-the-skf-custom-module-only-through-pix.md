---
name: "upgrade-bmad-core-and-the-skf-custom-module-only-through-pix"
description: "Upgrade BMAD core and the skf custom module only through pixi run -e pyforge-steward pyforge steward upgrade bmad-core…"
metadata:
  type: feedback
---

Upgrade BMAD core and the skf custom module only through pixi run -e pyforge-steward pyforge steward upgrade bmad-core --target <v> --apply --package-root .pixi/envs/pyforge-guild/lib/node_modules/bmad-method, never a raw bmad-method or bmad-module-skill-forge update: the raw skf 3.0.0 update dropped Mason Story 27.1's local edits to installer-owned files, and the steward apply three-way re-applies them. Each target needs a curated catalog at src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/<v>.yaml first (Story 100.7 added 6.12.2), and the apply leaves the checkout on its own review branch, uncommitted.
