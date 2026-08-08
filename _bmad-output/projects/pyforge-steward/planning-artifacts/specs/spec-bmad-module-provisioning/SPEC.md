---
spec: bmad-module-provisioning
status: draft
owner-dream: docs/dreams/bmad-module-provisioning.md
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
sources:
  - ../../research/market-steward-platform-ops-2026-08-08.md
open_questions:
  - "What is a 'module', concretely? The Dream names npm-distributed BMAD Method
    modules (Skill Forge, BMB, TEA/CIS, the unexercised five) — but the boundary
    with a bare .claude/skills/ skill or a _bmad/custom/ config layer is not
    pinned. First cut: a module is a thing with its own upstream installer that
    lands files in .claude/skills/ and/or _bmad/; a hand-authored skill is not."
  - "Installed-vs-available state: new .steward/ file (keys-inventory precedent)
    or derived from the filesystem (derive-don't-declare memory rule)? Research
    OQ2, deliberately unresolved. The Terraform comparison argues hard against
    any state file; leaning derivation, decide at epic time."
  - "Flag-value naming: --module skf vs --module skill-forge vs the npm package
    name (bmad-module-skill-forge). The Dream says 'naming TBD at Spec time';
    still TBD — pick when the first backend lands."
---

# SPEC — BMAD modules are provisioned, not hand-installed

## Why

Skill Forge is live in `.claude/skills/skf-*` only because a single ad-hoc
2026-07-17 commit hand-drove the `bmad-module-skill-forge` npm package's
TTY-only `Installer` class via an undiscoverable driver script; `bmad-builder`
is installed as a pixi package but was never taken through its own
`bmad-bmb-setup` skill, so it isn't wired into `.claude/skills/` at all.
Neither installation is reproducible against a fresh clone or a brownfield
`genesis adopt` target. Steward already owns exactly this shape of duty —
Epic 3's `provision --env` / `--runner bmad-loop` wrap external installers
non-interactively (AD-1/AD-5) — and the 2026-08-08 platform-ops research names
`provision --module` the first genuine post-ship growth vector for the verb:
a Terraform-style *backend* addition, explicitly **not** a state file. Owner:
Steward (Marshal ruled out on its own documented "route, don't own" boundary
and its "installer-owned … Genesis must never write here" architecture line).

## Capabilities

- **CAP-1 — one-command module provisioning.** Intent: `steward provision
  --module <name>` drives the named module's own non-interactive install path
  (BMB's `bmad-bmb-setup` config-merge scripts; a headless driver for Skill
  Forge's TTY-only `Installer`) as a thin subprocess wrap — a third backend
  beside `pixi` and `bmad-loop-worktree`, dispatched through the existing
  `ProvisionDuty` flag precedence, never a reimplementation of any module's
  installer. Success: a fresh clone reaches "module live and correctly wired
  into `.claude/skills/`" through one Steward command, and the run is
  re-runnable (idempotent or cleanly refusing) with no session-scratchpad
  driver script.
- **CAP-2 — module discovery.** Intent: `provision --list` (Story 3.3) is
  extended — or a sibling read verb added — so the operator sees which BMAD
  modules are installed vs merely available, with `--json` honored on success
  *and* error paths per the existing `_render_error` precedent. Success: the
  installed/available answer matches the filesystem, at-a-glance, before
  picking a module.
- **CAP-3 — partial state is named, never silent.** Intent: every `--module`
  failure path follows `_run_runner`'s template — anything already created
  when a later step fails (files landed, config half-merged) is named
  explicitly in the `DutyResult`, and the wrapped installer's own stderr
  reaches the operator, not a Steward paraphrase. Success: no `--module`
  failure leaves state the error message doesn't mention.

## Constraints

- **Respect the six-layer config merge; never bypass it.** Any configuration a
  module provisioning run writes lands in the custom layers (`_bmad/custom/
  config.toml` / `config.user.toml`) or per-project `.bmad-config*.toml` — never
  by editing the installer-regenerated layers 1–2 (`_bmad/config.toml`,
  `_bmad/config.user.toml`) and never by writing outside the layering so a
  later `bmad-method` reinstall silently reverts it.
- **Never absorb `bmad-method`'s governance core.** This provisions modules; it
  does not reimplement `bmad-method install` or take ownership of
  `_bmad/bmm/**` / `_bmad/core/**` (installer-owned, per Marshal's own
  architecture).
- **Non-interactive by construction** (AD-1/AD-5): drive each module's own
  installer headlessly; no state file (the Terraform lesson — `pixi.lock` +
  the filesystem stay the state).

## Non-goals

- Triaging which unexercised modules (`bmad-manticore`, `bmad-labs-skills`,
  `bmad-utility-skills`, `bmad-method-wds-expansion`, `bmad-module-template`)
  to keep — that is [[one-front-door]]'s open question.
- Re-provisioning the already-working Skill Forge installation; this targets
  the *next* module and the *next* repo, giving the current install a
  fallback path only.
- Provisioning non-BMAD tooling (pixi envs and runners already have their own
  flags).

## Success signal

The next kept BMAD module — and a brownfield `genesis adopt` target's Skill
Forge + BMB — reach "live and correctly configured" via `steward provision
--module <name>` alone: reproducible, auditable in the duty's own output,
six-layer config merge intact, and no hand-kept driver script created or
consulted anywhere in the process.
