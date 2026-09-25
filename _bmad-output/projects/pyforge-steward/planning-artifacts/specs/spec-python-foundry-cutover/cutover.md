---
companion-of: spec-python-foundry-cutover
updated: "2026-09-13"
---

# Cutover — phases, target tree, faces, order

Promoted 2026-09-04 out of `docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md`
§ *One working tree*, where Story 43.1 had filed it under "do not build". The living
Dream § *Cutover to `python-foundry`* carries the same table; this file is the
contract's copy and adds the tree, the faces and the do-not-carry list.

## The flag and the plan (iteration 2)

`pyforge.cutover_root` in `src/platform/config/flags.json` is the root of record; the transition point is its flip, after 44.5 today, and flipping back is the rollback. `steward cutover plan --regenerate` rebuilds the manifest from scratch; `--append` folds in the delta since its recorded `source_sha`; both keep `moved` rows. `steward cutover apply --phase <n>` replays a phase into foundry as often as the plan changes. Until the flip, `local-recipes` evolves normally.

## The capability ledger (iteration 3)

The plan has two layers. The **capability ledger** has one row per capability (from the Dreams and the spec-surface owner map) with a mode — `rebuild`, `move`, `retire` — a state — `planned`, `rebuilding`, `moving`, `verified-in-foundry`, `cut` — and dependencies. The **file manifest** below exists only under `move` rows. The seed of foundry is `docs/dreams/` plus every Spec and spine `.memlog.md`; every rendered document is re-derived there (`fnd:AD-20`). A rebuild is a regeneration drill with the archive as oracle (`fnd:AD-18`, `fnd:AD-21`); a capability entering `rebuilding` or `moving` freezes its source at once (`fnd:AD-22`).

**Mode is decided per row on four signals:** Spec fidelity (real memlog vs `epics.md` husk), coupling (`scribe index move-list` counts), open debt (deferred-work + red-team findings), irreplaceable state (data, locks, proofs). First pass, every row `[ASSUMPTION]` for the operator:

| Capability area | Mode | Why |
|---|---|---|
| `pyforge-core` dispatch, hooks, station port | rebuild | 2026-09-13 regenerate-not-fold; Epic 54 / `fnd:CAP-11`; do not fold |
| CFE cell (`conda-forge-expert` skill, scripts, MCP server) | rebuild | operator 2026-09-13: not a 44.6 move; Specs + local-recipes as oracle |
| Atlas pipelines and the query plane | later | Kedro data; not Launch |
| Steward, Marshal engines | rebuild | kernel first; thin archived-test oracle; CLI + MCP |
| Warden, Herald engines | rebuild | after kernel; Warden when foundry PRs need an in-repo verdict |
| Scribe | rebuild | later; store re-point |
| Doctor detectors | rebuild | later; regeneration drill |
| The seven `django-*` portals | later UX Dream | out of Launch; never a fold |
| Host GitHub Projects ingest | later | `pap:AD-2` breach; not Launch |
| Skills tree, adapters, runtime-state home | rebuild | re-provision from the register; not `apply --phase 1b` as a tree copy |
| Azure, staged-recipes CI, `compliance_face`, `services/` | retire | no Dream wants them |
| `src/shared/packages/` brownfield | stays on local-recipes | 44.4 fold parked; do not `apply --phase 1a` |

## Envelope and CI evidence (iteration 4)

Foundry is **private, permanently** (`fnd:AD-14`). CAP-1's authoritative CI
evidence (operator 2026-09-13 D1) is a fresh-clone local run of `detectors-ci`
and `platform-ci-local` (plus CRC IFF the empty repo already carries the estate
Helm chart). GHA is a twin and may stay red; force-merge after that local proof
is the campaign gate. Fresh-clone local is not provisional. Story 44.15 /
`fnd:CAP-10` is later (D1b), not a Launch / 44.3 confirmation gate — it meters
minutes when GHA twins or Marshal drains spend them. Nothing Mason submits
carries a foundry URL. This campaign's publish path is SelfExplainML (D2);
44.9 stays blocked. Launch = 44.12 + 44.3–44.7; later 44.8 / 44.14 / 44.15;
out of campaign 44.9 / 44.11 (D3). **No archive of A (operator 2026-09-25):** CAP-7 and
44.10 are retired; two git roots stay live after the `cutover_root` flip, and what
`local-recipes` hosts afterwards is decided per capability by the ledger's modes.

## Phases → stories

| Phase | CAP | Story | Do | Done when | Gate |
|---|---|---|---|---|---|
| — | CAP-2 input, CAP-9 | 44.1 capability ledger + manifest | derive the capability ledger (mode, state, dependencies, four signals) from the Dreams and the owner map, and the file manifest under its `move` rows; never a hand list | every capability has one row and one mode; 100 % of tracked files under `move` rows resolve to one destination; source SHA recorded | deps 44.13 |
| — | Constraints | 44.2 document fixes | R-23 `readOnlyRootFilesystem` + Windows / free-threading claims aligned to the Containerfile and `pixi.toml` platforms; R-24 Keycloak `26.4.0` pinned once; R-25 "no station-domain models on `django-<station>`"; `stack.md` / `convergence.md` floor `3.12.*` → `3.14.*` | edits land; `DW-RT-2026-09-02-7/-8/-9` resolved | — |
| 0 — Open foundry | CAP-1 | 44.3 | create `rxm7706/python-foundry` (private), workspace `pyforge`, empty of recipes, lean `pixi.toml`, estate-only CI; env export automated or not carried (R-17a) | clone exists; fresh-clone local `detectors-ci` + `platform-ci-local` green (CRC IFF Helm chart present); GHA twin may stay red | **outward** — ledger stays `blocked` until the operator flips; this pass does not flip it |
| 1a — Fold the packages | CAP-2 | 44.4 | `src/shared/packages/` → `src/packages/`; a `pixi.toml` per `django-*`; drop `sys.path` inserts and Containerfile `COPY` of django src; `five_tier.py` `_packages_root` retargeted; package fold only | station envs solve; host boots in foundry | deps 44.1, 44.3 |
| 1b — Move the estate | CAP-2 | 44.5 | skills → `skills/` (`stations/`, `personas/`, `domain/`) with `.claude/skills/` + `.cursor/skills/` as symlink adapters; BMAD, decks, dreams | adapters are symlinks; the BMAD chain resolves in foundry | deps 44.4; never blended with 44.4; no Deps on 44.11 (win-64 out of campaign, D3) |
| 2 — CFE comes home | CAP-3 | 44.6 | authoritative skill / scripts / tools → `skills/domain/conda-forge-expert`; retros land in foundry; `pyforge/mason/resolve.py` chain (flag → `MASON_CFE_ROOT` → cwd walk) retargeted | no `MASON_CFE_ROOT` resolves to `local-recipes`; CFE surface + rebuild guards pass | **Mason** (Rules 1 + 2); deps 44.5 |
| 3 — Factory island | CAP-4 | 44.7 | `factory/pixi.toml` + own lock; `factory/recipes/`, `build-locally.py`, `.ci_support/`, `conda-forge.yml`; recipes-only CI on `paths: factory/**` (R-17b) | `mason recipe build factory/recipes/<r>` matches today's CFE wrap; `DW-RT-2026-09-02-1` resolved | deps 44.3 |
| 4 — Working set | CAP-5 | 44.8 | move in-flight + sole-maintainer recipes only | `factory/recipes/` is the working set; universe not copied (count ceiling asserted) | deps 44.7 |
| 5 — Mason → conda-forge | CAP-6 | 44.9 | `submit` → staged-recipes or bot fork; `update` → feedstock maintainer-edit | an agent PR never opens `local-recipes` (asserted on the submit path) | **outward + Mason**; deps 44.6, 44.8 |
| — | CAP-1..3 | 44.11 Windows-native estate | generated per-machine links (junctions on Windows), long-path preflight, no shell-only tasks, win-64 CI leg, `var/` state home | link check and detectors green on a Windows runner; a stock Windows clone runs recipes and station CLIs | deps 44.3 |
| — | CAP-2 prerequisite | 44.13 memlog fidelity | in `local-recipes`: fold every hand-edit in a rendered SPEC.md (unifying strategy first) back into memlog entries; prove each Spec re-renders without loss | `bmad-spec` re-derive of every Spec is byte-equivalent to the rendered file, or the diff is recorded as memlog entries | none; before Phase 0 |
| — | CAP-9 | 44.14 rebuild harness + oracle gate | Dream + memlog → re-derived Spec → spine → epics in foundry; Marshal drains under a budget; the archived suite runs as oracle; per-capability freeze + `--append` drift finding | one pilot capability (Scribe) rebuilt end to end and `verified-in-foundry` through the oracle gate | deps 44.12 |
| — | CAP-10 | 44.15 Actions-minutes metering | `steward budget check` meters the account's Actions minutes (billing API through a `user`-scoped key in `steward keys`) against included minutes and the declared ceiling; `--json` for Marshal drains and 44.14 when those spend minutes | a real under/over verdict; a refused runner is a finding, never a cheap green | later, not Launch; unhooked from 44.3 (D1b) |
| — | CAP-8 | 44.12 cutover flag + replay harness | `pyforge.cutover_root` flag + `pyforge-core` reader; `steward cutover plan --regenerate\|--append` and `apply --phase` | both modes preserve `moved` rows; apply is idempotent; the flip switches ledger, Mason targets, loop homes | deps 44.1 |
| 6 — Archive | CAP-7 | 44.10 | **Retired 2026-09-25** (no archive of A); the ledger key stays `blocked` and is never dispatched | — | — |

**Order.** 44.13 → 44.1 ∥ 44.2 ∥ 44.15 → operator flips 44.3 → 44.11 ∥ 44.12 → 44.14 → capability realization in dependency order (`pyforge-core` move → moved engines → rebuilt portals and ingest against the moved host → CFE cell placement; 44.4 / 44.5 are the move path's replays) → **flag flip** when the dependencies are verified → 44.6 ∥ 44.7 → 44.8 → operator flips 44.9. (44.10 retired 2026-09-25.)

## Consolidation (2026-09-25) → stories

| CAP | Story | Do | Done when | Gate |
|---|---|---|---|---|
| CAP-12 | steward 67.1 | `pyforge-foundry-full` composes the `build` / `grayskull` / `crm` features (and `pnpm` in `python`) on three platforms; a layer env carries `platform-dev` + `platform-object-storage`; psycopg / pgvector caps and PG17 estate-wide; the `AGENTS.md` line | solves on linux-64, osx-arm64, win-64; the layer solves; scribe's Postgres suite green on PG17 | `pr-preflight`; `pyforge-station-tests` |
| CAP-13 | steward 67.2 | one laptop-gate task from the SBOM + layer alone | green on `main`; a planted missing dependency reds it | deps 67.1 |
| CAP-13 | steward 67.3 | tracked `docs/foundry/` gap list derived from `pixi.toml` | every residual gap and fat-only pin has a disposition and an owner | deps 67.1 |
| CAP-13 | steward 67.4 | upstream tickets for the `upstream` rows | each ticket linked from its row | **outward** — `blocked` until the operator flips; deps 67.3 |
| CAP-12 | steward 67.5 | developer guide, `AGENTS.md`, Mason / CFE docs name the SBOM | no doc names `-e local-recipes` as the laptop install | deps 67.2 |
| CAP-14 | herald 26.1 (steward index 67.6) | dossier Estate / Foundation / Synthesis / Verified | `site-check` green; every Verified claim cites a source | — |
| CAP-15 | scribe 21.1 (steward index 67.7) | `AGENTS.md` estate-first through `bmad-project-context` | parity meta-test and `governance-currency` green | — |
| — (spine) | steward 67.8 | `bmad-architecture` amends fnd:AD-1, fnd:AD-21 and the roles table for no-archive | the spine names no read-only archive; the oracle is a pinned SHA | — |

Campaign phase 5 (close conda-forge gaps) is minted as Mason stories from 67.3's list.

## Target tree

```text
python-foundry/                        # lasting git root (today: local-recipes)
├── pixi.toml                          # Workspace OS. Name: pyforge. No factory farm.
├── pixi.lock                          # Estate lock only. factory/pixi.lock is separate.
├── environment.yaml                   # Derived export — automated, or not carried.
├── AGENTS.md
├── factory/                           # Recipe island. Own lock. Not a platform.
│   ├── recipes/                       # Working set only
│   ├── pixi.toml + pixi.lock
│   ├── build-locally.py, .ci_support/
│   └── conda-forge.yml
├── .github/                           # Estate CI
├── config/                            # Deploy overlays. Secrets in env / cluster.
├── Containerfile
├── src/platform/                      # Foundry Platform. Never import pyforge.*.
├── src/packages/                      # TARGET. Not src/shared/packages/.
│   ├── pyforge-core/                  # python-cli-engine
│   ├── pyforge-<station>/             # × 8
│   ├── pyforge-atlas/                 # Only Kedro home + Vizro
│   ├── pyforge-testing-kit/
│   ├── django-pyforge/
│   └── django-<station>/
├── src/ides/  src/sentinel/  src/domains/<slug>/
├── templates/  presentations/pyforge-<station>/  docs/dreams/
├── skills/
│   ├── stations/<station>/SKILL.md    # × 7. Mason → domain/conda-forge-expert
│   ├── personas/<station>/SKILL.md
│   └── domain/conda-forge-expert/
├── .claude/skills/  (.cursor/skills/) # generated per-machine links, gitignored (fnd:AD-19)
├── var/                               # gitignored runtime state: atlas, cfe, worktrees
└── _bmad-output/projects/
```

## Five faces

| Face | Path |
|---|---|
| CLI | `src/packages/pyforge-<station>/` |
| UI | `src/packages/django-<station>/` |
| MCP | `POST /stations/<name>/mcp` on Foundry Platform |
| Skill | `skills/stations/<station>/` (mason: `skills/domain/conda-forge-expert`) |
| Agent | `skills/personas/<station>/` (`python-persona-engine` + harness) |

## Do not create / carry

`.claude/skills/pyforge-mason/` · lasting `src/shared/packages/` ·
`src/platform/compliance_face/` as the portal · `services/` or `:800x` · root
`docker-compose.yml` · `sys.path` for `django-*` · Containerfile `COPY` of django src ·
the `recipes/` universe · the 268 registered worktrees · `local-recipes` git history.

## Move-list manifest (44.1) — rules

- Source of truth is the spec-surface map (`scripts/spec_surface_check.py`): every
  tracked file already resolves to an owning Spec; the manifest adds a destination.
- One destination per path: a target-tree path, `stays` (remains on local-recipes,
  which is never archived), or `dies` (not carried). No path may resolve to two.
- Records the `local-recipes` source SHA the manifest was derived at; each regenerate
  re-records it (CAP-7, which pinned a final SHA, is retired).
