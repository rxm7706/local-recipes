---
title: BMAD Method modules are provisioned, not hand-installed
type: dream
owner: steward
status: realized
---

# BMAD Method modules are provisioned, not hand-installed

## The Dream

Every BMAD Method module this repo actually uses — `bmad-method` itself, Skill Forge
(`skf-*`), `bmad-builder` (BMB), and whichever of TEA/CIS/the currently-unexercised
`bmad-manticore`/`bmad-labs-skills`/`bmad-utility-skills`/`bmad-method-wds-expansion`/
`bmad-module-template` turn out to be kept — gets provisioned the same disciplined way
`steward provision` already handles pixi environments and `bmad-loop-worktree` runners:
one command, a clear error on failure, no hand-driven installer scripts kept alive only in
someone's session scratchpad.

Today it isn't. Skill Forge is live in `.claude/skills/skf-*` because of a single ad-hoc
`story(0.1)` commit (2026-07-17) that manually drove the `bmad-module-skill-forge` npm
package's TTY-only `Installer` class via a custom, undiscoverable driver script — provisioned
for `pyforge-atlas`'s own needs, not as a repeatable repo-wide capability. `bmad-builder`
is installed as a pixi package but was never taken through its own `bmad-bmb-setup` skill, so
it isn't wired into `.claude/skills/` at all. Neither installation is reproducible, auditable,
or re-runnable against a fresh clone or a brownfield adoption.

## Whose job this is, and why it isn't genesis's

This was investigated directly, not assumed. Two boundaries rule out Marshal:

- Marshal's own gap survey ([[one-front-door]]) marks `bmad-method`, BMB, and Skill Forge as
  **"route"** — explicitly distinct from the things it marks **"own"** (multi-project wiring,
  loop homes, the detector registry) in the same table.
- Marshal's own architecture is explicit that installed BMAD skills (`_bmad/bmm/**`,
  `_bmad/core/**`) are **"installer-owned... Genesis must never write here"** — absorbing
  module installation would make Marshal "the fork-owner of somebody else's governance core"
  (the same reasoning that keeps `bmad-loop` wrapped, never absorbed).
- [[genesis-installer]] (Marshal's Epics 7-12)'s actual FR/AD coverage — read directly from
  its epics document — is a Copier-based *file/region templating* engine (extraction
  manifest, managed-region markers, detect/plan/materialize/migrate). It stamps this repo's
  own conventions (Dreams tier, `AGENTS.md` family, multi-project wiring) into a repo; it has
  no FR anywhere for provisioning a third-party npm-distributed BMAD module.

Steward's own Dream is "the estate the factory stands on — provisioning, deployment,
credential lifecycle, budgets," and its just-shipped Epic 3 (`steward provision --env
<name>`, `--runner bmad-loop --env <name>`) is already the exact shape this needs: wrap an
external installer non-interactively (AD-1/AD-5, "delegate, never reimplement"), report a
clear error instead of the tool's own raw one, never leave partial state unreported.

## What it looks like when real

- `steward provision --module skf` / `--module bmb` (naming TBD at Spec time) runs whatever
  each module's own non-interactive install path actually is — `bmad-bmb-setup`'s config-merge
  scripts for BMB, an equivalent non-interactive driver for Skill Forge — the same way
  `--env`/`--runner` already wrap `pixi install`/`bmad-loop-worktree`.
- `steward provision --list` (already ships, Story 3.3) is extended, or a sibling verb is
  added, so an operator can see which BMAD modules are installed and which are merely
  available, the same at-a-glance discovery Story 3.3 already gives pixi environments.
- A fresh clone or a brownfield `genesis adopt` target can reach "Skill Forge and bmad-builder
  are both live and correctly configured" through one Steward command — no session-scratchpad
  driver script, no manual npm `Installer` class invocation, ever again.
- The existing, already-working Skill Forge installation is left alone (it works); this closes
  the gap for the *next* module or the *next* repo, and gives the current installation a real,
  reproducible provisioning path to fall back on if it ever needs to be redone.

## What is real

Nothing built yet. This is a `dreamt`-stage placeholder, captured at the moment the gap was
found while scoping [[conda-forge-expert-rebuild]] (which needs Skill Forge, live today only
because of the one-off 2026-07-17 provisioning). Owner assigned to `steward` per the
investigation above — Marshal was ruled out on its own documented boundaries, not by default.

## Constraints

- **Never absorb `bmad-method`'s own governance core AS A FIRST-INSTALL.** This Dream
  provisions modules from scratch (the Skill Forge/BMB-class case); it does not reimplement
  `bmad-method install` for a repo that has never run it, and does not take blanket ownership
  of `_bmad/bmm/**`/`_bmad/core/**`, which stay installer-owned per Marshal's own architecture.
  **Amended 2026-08-15** (see Realization log): this line originally read as a blanket ban on
  any `bmad-method`-core work by Steward at all, which turned out to be broader than the
  reasoning behind it actually supported. Reconciling an ALREADY-installed bmad-method core
  against a new upstream release — diff, merge, re-apply `_bmad/custom/**` overrides — is a
  distinct capability, carved out to [[bmad-method-core-upgrade]] (owner: steward), never this
  Dream. This Dream's own scope stays exactly what it always was: first-install provisioning
  of adjacent modules (Skill Forge, BMB, future TEA/CIS).
- **Non-interactive by construction.** Every module's own installer tends to assume a TTY
  (Skill Forge's does); the provisioning wrapper must drive it headlessly and reproducibly,
  not rely on a hand-kept driver script the way the 2026-07-17 commit did.

## Non-goals

- Not deciding which of the currently-unexercised modules (`bmad-manticore`,
  `bmad-labs-skills`, `bmad-utility-skills`, `bmad-method-wds-expansion`,
  `bmad-module-template`) to keep or drop — that triage is [[one-front-door]]'s own open
  question, orthogonal to how a kept module gets provisioned.
- Not re-provisioning Skill Forge's already-working installation — this targets the *next*
  module and the *next* repo, not a redo of what already runs.

## Kinships

[[conda-forge-expert-rebuild]] (the effort that surfaced this gap — needs Skill Forge
provisioned reproducibly) · [[pyforge-steward]] (the estate; Epic 3's provisioning duty is
this Dream's direct precedent) · [[one-front-door]] (the survey that first drew the
own/route/triage line this Dream's ownership reasoning relies on) · [[genesis-installer]]
(the boundary this Dream is deliberately outside of) · [[bmad-method-core-upgrade]] (the
distinct, ALSO-Steward-owned capability this Dream's Constraints were narrowed 2026-08-15 to
carve out — first-install here, already-installed reconciliation there).

## Realization log

- **2026-08-07** — Dream captured. Surfaced while scoping [[conda-forge-expert-rebuild]]: that
  effort needs Skill Forge, and investigation showed it was installed via a single 2026-07-17
  ad-hoc commit driving an npm package's TTY-only Installer class by hand, not through any
  repeatable path, and `bmad-builder` was never taken through its own setup skill at all. User
  asked whether provisioning both should have been genesis's job; investigation (Marshal's own
  "route" vs "own" survey, its "installer-owned... Genesis must never write here" architecture
  line, and genesis-installer's actual FR coverage being file/region templating, not module
  provisioning) ruled Marshal out on its own documented boundaries. Assigned to Steward,
  whose Epic 3 provisioning duty (just merged) is structurally the same shape this needs.

- **2026-08-10** — **Realized.** Steward Epic 6, "Module provisioning", is **3/3 done and
  merged**. The Dream's frontmatter had been left at `dreamt` throughout — same rot as
  [[unified-container]], found in the same 2026-08-10 sweep. What the Dream asked for is what
  landed: the hand-installed modules are now provisioned through Steward's own `provision` duty,
  the way it already wraps pixi and the bmad-loop worktree, rather than through a one-off npm
  Installer invocation nobody could reproduce. Evidence: steward's `sprint-status-ledger.yaml`
  Epic 6.

- **2026-08-15 (amendment)** — Constraints narrowed. A new Dream, [[bmad-method-core-upgrade]]
  (captured the same day investigating whether any station owns *upgrading* an already-installed
  bmad-method core — not just first-installing adjacent modules — after the user noticed
  BMAD-METHOD v6.11.0 had released), initially came up genuinely unowned, blocked by this
  Dream's own "never absorb bmad-method's own governance core" line read literally. Deep-dive
  (an independent research pass over this Dream's full text, Steward's own charter, and
  genesis-installer's actual FR coverage) confirmed that line was written to prevent
  duplicating Marshal's/genesis-installer's turf for FIRST-INSTALL, never evaluated against the
  distinct case of reconciling an already-installed core against a new upstream release — this
  Dream drives each module's own installer once, from nothing; reconciling means diffing
  installed state against upstream AND against this repo's own `_bmad/custom/**` overrides,
  which this Dream's existing scope never touches. Concrete live proof the gap is real, found
  during the same investigation: `pixi.toml` already declares `bmad-method = ">=6.11.0"` but
  `_bmad/_config/manifest.yaml` (the actually-installed core) still reports `version: 6.10.0`
  — the dependency floor was bumped without the installed content ever being reconciled.
  Narrowed the Constraint to say so explicitly and handed the upgrade-apply capability to
  [[bmad-method-core-upgrade]] (owner: steward) as its own Dream, keeping this Dream's own
  realized scope (Epic 6, first-install provisioning) unchanged.
