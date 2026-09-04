---
spec: python-foundry-cutover
status: ready
chain: pyforge-unifying-strategy
created: "2026-09-04"
updated: "2026-09-04"
owner-dream: docs/dreams/pyforge-unifying-strategy.md
extends: spec-pyforge-unifying-strategy  # cite this file's ids as fnd:CAP-1..7 outside it; Unifying CAP-1..19 and pap:CAP-1..6 are different sets — never collapse
surface: []
companions:
  - cutover.md
sources:
  - ../../../../../../docs/dreams/pyforge-unifying-strategy.md
  - ../../../../../../docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md
open_questions:
  - actions-minutes
---

> **Canonical contract.** Derived 2026-09-04 from the Dream § *Cutover to
> `python-foundry`* (build target). Extends `spec-pyforge-unifying-strategy`; it does
> not re-mint any Unifying `CAP-*` or `pap:CAP-*`. Realized by steward **Epic 44**
> (Stories 44.1–44.10). The evergreen Spec is not re-derived for this work.

# SPEC — Cutover to `python-foundry` (Phases 0–6)

## Why

**A mandate to meet and a vision to realize.** The Dream names `python-foundry`
(pixi workspace `pyforge`) as the lasting git root and `factory/` as the recipe
island. Today's clone is a `staged-recipes` shape the estate outgrew: workspace
name `staged-recipes`, 7,855 recipe dirs beside the platform, one 59k-line lock
for 29 environments, a staged-recipes linter gating every non-recipe PR, and 268
registered worktrees. The review's gate on the cutover (Epics 40 → 43, Mason 13)
closed 2026-09-03 with nothing downstream of it. This Spec is that downstream:
the contract Epic 44 realizes, and the gate Phase 0 waits on.

## Capabilities

- **CAP-1 — Open foundry (Phase 0).**
  - **intent:** The operator can create `rxm7706/python-foundry` as a fresh,
    recipe-free, lean-pixi estate with estate-only CI.
  - **success:** The clone exists; CI is green on the empty estate; no `recipes/`
    directory; the `environment.yaml` export is automated or absent, never by hand.

- **CAP-2 — Move the estate (Phase 1).**
  - **intent:** `pyforge-core`, the eight `pyforge-<station>`, `pyforge-testing-kit`,
    `django-pyforge` and the `django-<station>` packages live under `src/packages/`;
    skills under `skills/` with IDE adapters as symlinks; BMAD, decks and dreams in
    foundry.
  - **success:** Every station env solves and the host boots in foundry; no
    `sys.path` insert and no Containerfile `COPY` of django src remain;
    `.claude/skills/` and `.cursor/skills/` are symlinks into `skills/`.

- **CAP-3 — CFE comes home (Phase 2).**
  - **intent:** The authoritative conda-forge-expert skill, scripts and tools
    resolve from `skills/domain/conda-forge-expert` in foundry, and retros land there.
  - **success:** No `MASON_CFE_ROOT` (flag, env, or cwd walk) resolves to
    `local-recipes`; `mason-cfe-surface-check` and `cfe-rebuild-guard-check` pass.

- **CAP-4 — Factory island (Phase 3).**
  - **intent:** Recipe work runs from `factory/` with its own `pixi.toml` and lock
    and a recipes-only CI.
  - **success:** `mason recipe build factory/recipes/<r>` matches today's CFE wrap;
    the estate lock holds no factory solver dependency; factory CI triggers on
    `paths: factory/**` only.

- **CAP-5 — Working set (Phase 4).**
  - **intent:** Only in-flight and sole-maintainer recipes move.
  - **success:** `factory/recipes/` is the working set under an asserted count
    ceiling; the 7,855-dir universe is not copied.

- **CAP-6 — Mason talks to conda-forge (Phase 5).**
  - **intent:** From foundry, `submit` targets staged-recipes or the bot fork and
    `update` targets the feedstock maintainer-edit path.
  - **success:** An agent-opened PR never targets `local-recipes` (asserted on the
    submit path).

- **CAP-7 — Archive `local-recipes` (Phase 6).**
  - **intent:** `local-recipes` is read-only history.
  - **success:** README superseded; Azure disabled; last SHA pinned in the foundry
    manifest; history kept; worktree residue retired; the default clone is foundry
    and `.steward` has one git root.

## Constraints

- Contract before repo: CAP-1 is not dispatched until this Spec is `ready` and Epic 44
  exists. CAP-1, CAP-6 and CAP-7 are outward; the ledger holds them `blocked` until
  the operator flips each one. Never auto-drained.
- Fresh repo (operator 2026-09-04): no history import; source SHAs live in the
  move-list manifest.
- The move-list manifest (Story 44.1) is derived from the spec-surface map and precedes
  CAP-2. Never a hand list.
- Package fold and the skills / BMAD move are separate stories. Never one.
- The estate `pixi.lock` never absorbs the factory solver farm.
- No `services/` or `:800x` tree; no root `docker-compose.yml`; no
  `src/platform/compliance_face/` as the portal; no `.claude/skills/pyforge-mason/`.
- CAP-3 and CAP-6 are Mason work under Rule 1 and Rule 2: `conda-forge-expert` is
  invoked and a CFE retro lands. Marshal's `Deps:` parser is station-local, so Mason
  gates are ledger state, as 43.6 was behind Mason 13.
- `DW-RT-2026-09-02-2..6` (R-18..R-22) never block CAP-2; they stay steward-owned
  ledger entries.
- Cite this Spec's ids as `fnd:CAP-N` outside this file; the evergreen Spec is not
  re-derived.
- Physical writes under `_bmad-output/projects/pyforge-steward/` with
  `BMAD_ACTIVE_PROJECT=pyforge-steward`; no `bmad-switch` from parallel agents. The
  Tier-3 feed is repaired (`sprint-ledger-sync --project steward --repair-feed`, then
  `story-status-check`) before any ledger write.

## Non-goals

- Re-deciding the modular-monolith topology or any Unifying `CAP-1..19`.
- Renaming the pixi env `python-agent-platform`, or the parked `pap:` Single-Spec merge.
- Rewriting `local-recipes` git history; the fresh repo leaves it behind.
- Closing R-18..R-22 (an Epic 45 candidate).
- Copying the `recipes/` universe or the feedstock mirrors.
- Migrating the 268 registered worktrees; CAP-7 retires them.

## Success signal

A fresh clone of `rxm7706/python-foundry` boots Foundry Platform and every station
env, `mason recipe build factory/recipes/<r>` builds a recipe there, and an
agent-opened conda-forge PR originates from foundry, while `rxm7706/local-recipes`
is archived with its last SHA pinned in the foundry manifest.

## Assumptions

- `gh` auth for rxm7706 can create a private repository (CAP-1).
- No detector enforces a line-count cap on the living Dream; the Dream section grows
  the file past 43.1's 400-line target by design.

## Open Questions

- **actions-minutes:** CAP-1's "CI green on the empty estate" needs GitHub Actions
  minutes, and rxm7706 was under an account-wide billing block on 2026-08-30. If it is
  still blocked when 44.3 dispatches, what counts as CAP-1's CI evidence?
