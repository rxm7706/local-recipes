---
title: Non-module bmad-suite pieces are provisioned by install class — not forced through --module
type: dream
owner: steward
status: dreamt
---

# Non-module bmad-suite pieces are provisioned by install class

## The Dream

An operator who wants the **whole** SelfExplainML bmad-suite live on a fresh
clone — not only the five wire-decided BMAD modules — can get there without a
session-scratchpad ritual and without pretending every package is a
`steward provision --module` target.

Today the suite Dream ([[bmad-suite-channel-product]]) correctly grows
`_SUPPORTED_MODULES` for **bmb / tea / cis / utility-skills / manticore**
(CAP-3) and correctly **skips** WDS. It also correctly says steward's product
job is **channel ops + upgrade pipeline**. That left a hole in the operator's
head: *how do method, loop, skill-forge, labs-skills, dashboards, and
module-template get onto PATH and actually wired*, if not through `--module`?

This Dream answers that hole. **Each remaining piece has an install class.**
Steward provisions and keeps them current **through that class** — pixi pin,
existing `--env` / `--runner`, Epic 14 upgrade prove-landed, pixi tasks, or
documented native one-shots — never by stuffing the wrong shape into
`_SUPPORTED_MODULES`.

When this is real, "the suite is installed" means: artifacts on PATH **and**
the class-correct wire has been run (or deliberately N/A), reported in the
same pipeline-truth language CAP-1 already wants (`wired-or-not` per package,
named by class).

## Grounding — the six that are not CAP-3 modules

| Piece | Install class | How it gets on PATH | How it gets wired | Steward surface (intended) |
|---|---|---|---|---|
| **bmad-method** | Core / npm CLI installer | pixi pin (conda-forge canonical; SelfExplainML parity) | `npx bmad-method install` owns `_bmad/core` + BMM — Genesis must never write there | Epic 14 upgrade + prove-landed; **not** `--module` |
| **bmad-loop** | uv-from-git tool / orchestrator | pixi pin (+ optional `uv tool install …@git`) | Loop homes / worktrees | Existing `steward provision --runner bmad-loop --env …`; **not** `--module` |
| **bmad-module-skill-forge** (skf) | Own npx installer (+ module into `_bmad`) | pixi pin (suite pixi gap closed 2026-08-22) | `npx bmad-module-skill-forge install` (or method-driven module install) | Channel pin + native install; **optional** future `--module skf` only if Spec proves it is the same family as bmb — not required to close this Dream |
| **bmad-labs-skills** | Claude plugin / `skills add` marketplace | optional pixi package | `npx skills add bmad-labs/skills` or `/plugin marketplace add …` | Channel pin + CAP-4 matrix spot-check; **not** `--module` |
| **bmad-dashboard** / **mybmad-dashboard** | Build / self-host app | pixi `bmad-ui` feature | `pixi run bmad-dashboard-install` (VS Code); pnpm/setup for web | Publish + pin + install task; **not** `--module` |
| **bmad-module-template** | GitHub template scaffold | channel mirror (optional) | "Use this template" when **creating** a new module repo — never into an existing tree | Channel completeness only; **no provision-into-repo** |

**WDS** stays the explicit skip from the suite Dream (deprecated → `bmad-ux`).
**CAP-3 five** stay on `--module`. This Dream does not reopen those decisions.

## Whose job this is

**Steward** — same estate as [[bmad-module-provisioning]] and
[[bmad-suite-channel-product]]: wrap external installers, never absorb them;
keep pins and channel listings honest; make the operator path discoverable.

Not Marshal/Genesis: those own Copier regions and multi-project wiring;
`_bmad/core/**` and `_bmad/bmm/**` remain installer-owned.

Doctor stays ambient (suite drift, channel↔recipe); CFE/mason stay recipe
build/validate. This Dream does not move those boundaries.

## What it looks like when real

- A **class-keyed playbook** (Dream → Spec companion to the install matrix)
  tells an operator, for each of the six, the pixi path, the native wire, and
  the steward verb/task — one page, no tribal knowledge.
- A **fresh clone** can reach "method core installed, loop runner provisionable,
  skf skills present, labs plugin path documented, dashboard install task
  runnable, template N/A unless scaffolding" without hand-driving npm
  `Installer` classes from a chat transcript.
- CAP-1's `wired-or-not` column tells the truth **per class** (installer tree /
  runner home / plugin enabled / VS Code extension / scaffold N/A) — not a
  boolean that only CAP-3 modules can satisfy.
- Nothing in `_SUPPORTED_MODULES` that is not a BMAD expansion module merging
  into `_bmad/` + `.claude/skills`.
- Optional stretch (Spec may refuse): `steward provision --module skf` as a
  thin wrap of skf's own non-interactive install — sibling to bmb, not a
  precedent for loop/labs/dashboards/template.

## Constraints

- **Never wire-everything through `--module`.** Install class is load-bearing;
  symmetry is not a reason.
- **Never absorb bmad-method first-install** into steward; Epic 14 owns
  reconcile/upgrade of an already-installed core
  ([[bmad-method-core-upgrade]]).
- **Never absorb bmad-loop**; wrap via `--runner` only
  ([[bmad-module-provisioning]]'s same "wrap, don't absorb" line).
- Native commands come from upstream READMEs and the suite install matrix —
  cited, never invented; npm collision denylist travels with the matrix.
- Template is scaffold-only; provisioning it "into" this monorepo is out of
  scope forever.
- Dual-path (pixi + native) remains the suite product contract; this Dream
  only names the **wiring** half for non-module classes.

## Non-goals

- Growing CAP-3's five-module set, or un-skipping WDS.
- Replacing Epic 15's channel pipeline / truth report / advance command.
- Packaging autopilot / bmalph / dashboard-extension (still parked).
- Making labs or dashboards look like BMAD installer modules.
- Auto-enabling Claude plugins without operator consent.

## Kinships

[[bmad-suite-channel-product]] (parent product Dream; CAP-3 modules + CAP-4
matrix — this Dream is the **non-module wiring** companion) ·
[[bmad-module-provisioning]] (realized `--module` seam for installer-class
modules; skf optional extension lives there if Spec says yes) ·
[[bmad-method-core-upgrade]] (method upgrade / prove-landed) ·
[[bmad-method-version-drift]] (doctor ambient) ·
[[one-front-door]] (own / route / triage posture that forbids wire-everything)

## Realization log

- **2026-08-23** — Dreamt. Captured after operator confusion: channel listing
  of all 13 packages ≠ `--module` wiring; CAP-3 five clarified; remaining six
  needed an explicit install-class Dream so steward's "channel + upgrade, not
  --module" line has a positive "how then?" rather than only a refusal.
