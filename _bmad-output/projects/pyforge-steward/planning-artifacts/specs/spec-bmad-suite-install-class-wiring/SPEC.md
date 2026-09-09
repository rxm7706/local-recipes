---
spec: bmad-suite-install-class-wiring
status: shipped   # 2026-09-06 — CAP-1..3 as steward Epic 31 (3/3 done 2026-08-24); recorded late
owner-dream: docs/dreams/bmad-suite-install-class-wiring.md
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/fresh_clone.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
  - src/shared/packages/pyforge-steward/tests/unit/test_fresh_clone_class_path.py
  - .github/workflows/pyforge-pip-install.yml
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/install-class-playbook.md
companions:
  - install-class-playbook.md
  - ../spec-bmad-suite-channel-product/install-matrix.md
sources:
  - ../../../../../../docs/dreams/bmad-suite-install-class-wiring.md
assumptions:
  - "Parent Epic 15 CAP-3 five and the WDS skip remain; the pipeline-truth
    command (spec-bmad-suite-channel-product CAP-1) already exists as the
    report this Spec's wired-or-not language extends."
open_questions: []
---

# SPEC — Non-module bmad-suite pieces are provisioned by install class

## Why

An operator who wants the whole SelfExplainML bmad-suite live on a fresh
clone — not only the five wire-decided BMAD modules — currently has a
session-scratchpad ritual and a hole in the head: method, loop,
skill-forge, labs-skills, dashboards, and module-template are on the
channel but are not `--module` targets. The parent product Dream
correctly grows `_SUPPORTED_MODULES` for bmb/tea/cis/utility-skills/
manticore and correctly skips WDS. This Spec answers *how then* those
six get onto PATH and actually wired — by install class, never by
stuffing the wrong shape into `_SUPPORTED_MODULES`. Owner: **steward**.
Vehicle: **Epic 31** (Epic 15 stays done).

## Capabilities

- **CAP-1 — Class-keyed playbook.** *Intent:* one tracked companion
  tells the operator, for each of the six non-module pieces, the pixi
  path, the native wire (cited from the upstream README /
  `install-matrix.md`), and the steward verb or task — discoverable
  from `steward provision --help` (or an equivalent CLI pointer), not
  tribal knowledge. *Success:* the playbook exists, cites the matrix,
  and `provision --help` names it.
- **CAP-2 — Class-correct wired-or-not.** *Intent:* the pipeline-truth
  report's `wired-or-not` column uses per-class predicates (installer
  tree / runner home / plugin enabled / VS Code extension / scaffold
  N/A), not a boolean only `--module` targets can satisfy. *Success:*
  run against a fresh clone it names each of the six by class without
  claiming "wired" for template-into-this-repo.
- **CAP-3 — Fresh-clone class-path.** *Intent:* a fresh clone can reach
  "method core installed, loop runner provisionable via `--runner`, skf
  skills present via its own installer, labs plugin path documented,
  dashboard install task runnable, template N/A unless scaffolding"
  without hand-driving npm `Installer` classes from a chat transcript.
  *Success:* a recorded fresh-clone run (or CI equivalent) reaches that
  state with zero improvised steps.

## Constraints

- Never wire-everything through `--module`. Install class is
  load-bearing; nothing joins `_SUPPORTED_MODULES` that is not a BMAD
  expansion module merging into `_bmad/` + `.claude/skills`.
- Never absorb bmad-method first-install (Epic 14 owns reconcile/upgrade
  of an already-installed core). Never absorb bmad-loop (wrap via
  `--runner` only).
- Native commands come from upstream READMEs and `install-matrix.md` —
  cited, never invented. The npm collision denylist travels with the
  matrix.
- Template is scaffold-only forever; provisioning it into this
  monorepo is out of scope.
- Dual-path (pixi + native) remains the suite product contract; this
  Spec names only the wiring half for non-module classes.

## Non-goals

- Growing CAP-3's five-module set, or un-skipping WDS.
- Replacing Epic 15's channel pipeline / truth report / advance command.
- `steward provision --module skf` — refused: skf is not proven the
  same family as bmb; wrap stays `npx bmad-module-skill-forge install`
  + the pixi pin.
- Packaging autopilot / bmalph / dashboard-extension (still parked).
- Making labs or dashboards look like BMAD installer modules.
- Auto-enabling Claude plugins without operator consent.

## Success signal

`steward provision --help` points at the class-keyed playbook; a fresh
clone follows it to method-core-installed + loop-provisionable + skf
present + labs-path-documented + dashboard-task-runnable + template-N/A
with zero chat-transcript Installer driving; and pipeline-truth's
`wired-or-not` column tells the class-correct truth for all six.
