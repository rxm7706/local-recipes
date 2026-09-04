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
  - ../../architecture/architecture-python-foundry-cutover-2026-09-04/ARCHITECTURE-SPINE.md
sources:
  - ../../../../../../docs/dreams/pyforge-unifying-strategy.md
  - ../../../../../../docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md
open_questions:
  - actions-minutes
---

> **Canonical contract.** Derived 2026-09-04 from the Dream § *Cutover to
> `python-foundry`* (build target). Extends `spec-pyforge-unifying-strategy`; it does
> not re-mint any Unifying `CAP-*` or `pap:CAP-*`. Decomposed as steward **Epic 44**
> (Stories 44.1–44.14) under the cutover spine (`fnd:AD-1..22`) — **solutioning iteration 3,
> operator review continuing; every story ledger `blocked`**. The cutover is regenerative: Dreams and
> memlogs seed foundry; every capability is rebuilt or moved per the capability ledger.

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

- **CAP-2 — Realize the estate (Phase 1).**
  - **intent:** Every capability of the estate reaches foundry by rebuild or by move per the
    capability ledger, with `pyforge-core`, the eight `pyforge-<station>`, `pyforge-testing-kit`,
    `django-pyforge` and the `django-<station>` packages under `src/packages/`, skills under
    `skills/` with generated adapters, and the BMAD chain seeded from Dreams and memlogs.
  - **success:** Every capability row is `verified-in-foundry` under its mode's gate; every
    station env solves and the host boots from workspace members; no `sys.path` insert and
    no Containerfile `COPY` of package source remain; no `src/shared/` exists.

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

- **CAP-9 — Capability ledger and rebuild harness.**
  - **intent:** The operator sets a mode per capability; the ledger derives from the Dreams
    and the owner map; a `rebuild` re-derives Spec, spine and epics in foundry from the moved
    memlog and is drained by Marshal with the archive as oracle.
  - **success:** `steward cutover plan` emits the ledger with modes, states, dependencies and
    the four decision signals; a rebuilt capability passes the archived suite or an equivalence
    check before `verified-in-foundry`; a capability in `rebuilding` or `moving` has its source
    frozen and `--append` reports drift against it.

- **CAP-8 — Flag-gated, replayable cutover.**
  - **intent:** The operator can regenerate or append the cutover plan at any time while
    `local-recipes` keeps evolving, replay every move into foundry, and flip the root of
    record by one flag.
  - **success:** `steward cutover plan --regenerate` and `--append` both yield a manifest
    that preserves `moved` rows; `steward cutover apply --phase <n>` is idempotent;
    flipping `pyforge.cutover_root` switches the ledger of record, Mason's targets and the
    loop-home remotes without a redeploy, and flipping back restores them.

## Constraints

- Solutioning before implementation (operator 2026-09-04): this Spec, the cutover spine
  and Epic 44 are BMAD Phase 3 artifacts the operator reviews and refines in iterations;
  no story spec is drafted and no 44.x leaves ledger `blocked` until the operator flips it.
- The seed is Dreams plus memlogs only: rendered `SPEC.md`, spines, epics and stories are
  re-derived in foundry; memlog fidelity (44.13) precedes Phase 0.
- The oracle gate is non-negotiable: no rebuilt capability is verified without the archived
  suite or an equivalence check passing against it.
- Mode is per capability, decided by the operator on scored signals; this is not a rebuild
  of everything and not a move of everything.
- The cutover is a flag, not a date: `pyforge.cutover_root` in the CAP-13 flag tree is the
  only switch of the root of record; the transition point is the flip (after 44.5 today);
  before it nothing in `local-recipes` is frozen.
- Every move is a replay: a move the `steward cutover apply` step cannot reproduce is
  review-blocking.
- No symlink is tracked in git; runtime links are generated per machine (symlink on POSIX,
  junction on Windows) and gitignored. Runtime state lives in gitignored `var/`.
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
- Carrying rendered planning narrative (research, reviews, proposals, reports, retros, run
  records, per-story specs of shipped stories); the archive keeps them.

## Success signal

A fresh clone of `rxm7706/python-foundry` boots Foundry Platform and every station
env, `mason recipe build factory/recipes/<r>` builds a recipe there, and an
agent-opened conda-forge PR originates from foundry, while `rxm7706/local-recipes`
is archived with its last SHA pinned in the foundry manifest.

## Assumptions

- `gh` auth for rxm7706 can create a private repository (CAP-1).
- No detector enforces a line-count cap on the living Dream; the Dream section grows
  the file past 43.1's 400-line target by design.
- Stock Windows developers (no WSL, no Developer Mode) are a real population; the estate
  is native for them and the host is remote (spine AD-19).

## Open Questions

- **actions-minutes:** CAP-1's "CI green on the empty estate" needs GitHub Actions
  minutes, and rxm7706 was under an account-wide billing block on 2026-08-30. If it is
  still blocked when 44.3 dispatches, what counts as CAP-1's CI evidence?
