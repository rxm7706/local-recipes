---
spec: bmad-module-provisioning
status: shipped   # corrected 2026-08-15 (fleet-wide decomposition audit): was stale at
                   # 'draft' despite Epic 6 (Stories 6.1-6.3, all CAP-1..3) reading `done` in
                   # epics.md -- matches the owner-dream's own already-correct `status: realized`.
owner-dream: docs/dreams/bmad-module-provisioning.md
surface:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
sources:
  - ../../research/market-steward-platform-ops-2026-08-08.md
updated: "2026-09-09"
open_questions: []
  # ANSWERED IN CODE 2026-09-09, all three retired (batch row stA-C6):
  # 1. "What is a module, concretely?" — the five names in `_SUPPORTED_MODULES`
  #    (bmb, tea, cis, utility-skills, manticore) plus `_SKIPPED_MODULES`; the five install
  #    classes in `install-class-playbook.md` draw the boundary a hand-authored
  #    `.claude/skills/` skill falls outside of. The Spec's own first cut held.
  # 2. Installed-vs-available state — DERIVED, no state file. `provision.py:71` records it
  #    verbatim ("no new state file — derive-don't-declare"); `.steward/` holds only the
  #    keys-inventory plus the examples. The Terraform comparison won.
  # 3. Flag-value naming — short module names, `--module bmb|tea|cis|utility-skills|manticore`.
  #    `--module skf` is an explicit, documented REFUSAL (Skill Forge installs by its own
  #    installer).
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
  - **verified:** 2026-09-11 — `steward provision --module NAME` live at
    `provision.py`, supporting bmb/cis/manticore/tea/utility-skills; re-run-safety exercised
    by `tests/unit/test_provision_module.py` (104 tests, incl.
    `test_provision_module_bmb_foreign_collision_refuses_and_writes_nothing` and
    `test_provision_module_bmb_retry_after_first_script_failure_does_not_self_collide`) — all
    pass. Not re-exercised against a real fresh clone in this pass (destructive/slow); the
    unit-level idempotency claim is verified, the fresh-clone end-to-end claim is not.
- **CAP-2 — module discovery.** Intent: `provision --list` (Story 3.3) is
  extended — or a sibling read verb added — so the operator sees which BMAD
  modules are installed vs merely available, with `--json` honored on success
  *and* error paths per the existing `_render_error` precedent. Success: the
  installed/available answer matches the filesystem, at-a-glance, before
  picking a module.
  - **verified:** 2026-09-11 — live: `steward provision --list-modules --json` returns
    `{"bmb": "installed", "cis": "installed", "manticore": "available", "tea": "installed",
    "utility-skills": "installed"}`, matching the actually-installed `.claude/skills/` state;
    `steward provision --module notreal --json` returns `{"error": "...not a supported
    module..."}`, confirming `--json` is honored on the error path too.
- **CAP-3 — partial state is named, never silent.** Intent: every `--module`
  failure path follows `_run_runner`'s template — anything already created
  when a later step fails (files landed, config half-merged) is named
  explicitly in the `DutyResult`, and the wrapped installer's own stderr
  reaches the operator, not a Steward paraphrase. Success: no `--module`
  failure leaves state the error message doesn't mention.
  - **verified:** 2026-09-11 — `test_provision_module.py`'s
    `test_provision_module_mid_chain_failure_names_already_wrote_config_section`,
    `test_provision_module_first_script_failure_names_nothing_written`, and
    `test_provision_module_script_failure_surfaces_stderr_verbatim_and_honors_json` all pass,
    directly covering the named-partial-state and verbatim-stderr claims.

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
