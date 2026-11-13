---
companion-of: spec-python-foundry-cutover
updated: "2026-11-11"
---

# Cutover — phases, target tree, faces, order

Promoted 2026-09-04 out of `docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md`
§ *One working tree*, where Story 43.1 had filed it under "do not build". The living
Dream § *Cutover to `python-foundry`* carries the same table; this file is the
contract's copy and adds the tree, the faces and the do-not-carry list. Rewritten 2026-11-11
(Story 120.1) for the operator's rulings of 2026-11-10.

## The flag and the plan (rulings 2026-11-10)

`pyforge.cutover_root` in `src/platform/config/flags.json` is the root of record and the writer lock: the root it names writes every Dream, Frame, Spec and the capability ledger (`fnd:CAP-8`, `fnd:AD-24`), read through `pyforge.core.cutover_root.root_of_record()`. The operator flips `pyforge.cutover_root` by hand, with no loop running, once the Launch slice is proven; nothing flips it automatically. The slice is proven when B lands one story on itself through its own dispatch and detectors and every Launch row of the case list reads `verified-in-foundry` (`launch-slice.md`). `steward cutover flip` makes the flip, is refused while a loop runs and stamps the Realization log; flipping back is the rollback. `steward cutover plan` generates and validates the capability ledger (`--regenerate`, `--append`, `--check`; `fnd:CAP-9`). `steward cutover apply` and the file manifest are retired (operator 2026-11-10). Until the flip, `local-recipes` evolves normally, except the source of a `rebuilding` row, whose freeze Doctor judges (`spec-pyforge-doctor:CAP-94`).

## The capability ledger (rulings 2026-11-10)

The plan has one layer: the **capability ledger**, `docs/foundry/capability-ledger.yaml`, one row per capability of a live Spec. `steward cutover plan --regenerate` writes the derived fields (id, spec, station, heading, path) from the live Specs and keeps the decided ones; `--append` adds rows for new capabilities only (`spec-foundry-capability-ledger:CAP-1`, `fnd:AD-25`). A row's mode is `rebuild` (B re-derives it; A is its oracle until `verified-in-foundry`), `retire` (never appears on B), `A-only` (with an expiry Story or date) or `B-only` (named on a Spec before `done`), plus `pending` for a row waiting on a named operator question. Its state is `planned`, `rebuilding`, `verified-in-foundry` or `cut`. There is no file manifest. The seed of foundry is `docs/dreams/` plus every Spec and spine `.memlog.md`, `archive/**/.memlog.md` included, with no backfill; every rendered document is re-derived there (`fnd:AD-20`), and a Frame is a pointer to that seed. A rebuild is a regeneration drill with the archive as oracle (`fnd:AD-18`, `fnd:AD-21`); a capability entering `rebuilding` freezes its source at once, and Doctor judges the freeze (`fnd:AD-22`).

**Mode is decided per row by the written rules of `spec-foundry-capability-ledger` `modes.md`** (operator 2026-11-10; the four scored signals are retired). The rulings: a capability whose artifact is deleted on A is `retire`; a closed one-time campaign is `retire`; host, platform and portal capabilities are `A-only` with Story 121.5 as expiry; the testing kit is `rebuild`; conda-forge-expert is `A-only` on mason Story 39.2; a capability never built is `B-only` when a live `blocked` or `backlog` Story carries it and `retire` when none does. By area (the ledger rows decide; this table summarises them):

| Capability area | Mode | Rule |
|---|---|---|
| `pyforge-core` dispatch, hooks, station port | rebuild | regenerate-not-fold (2026-09-13); Epic 54 / `fnd:CAP-11`; never a fold |
| Steward, Marshal engines | rebuild | kernel first; thin archived-test oracle; CLI + MCP |
| Warden, Herald, Scribe, Doctor, Atlas engines | rebuild, row by row | after the kernel; a closed one-time campaign or a deleted artifact is `retire` |
| Testing kit | rebuild | `spec-pyforge-testing-charter:CAP-4`; `spec-pyforge-testing-charter:CAP-1`, `spec-pyforge-testing-charter:CAP-2` and `spec-pyforge-testing-charter:CAP-5` are `A-only` with a Story expiry |
| CFE cell (`conda-forge-expert` skill, scripts, MCP server) | A-only, expiry `mason:39.2` | rebuilt from its own Spec after the flip (`fnd:CAP-3`); never carried |
| Host, platform, the `django-*` portals, GitHub Projects ingest | A-only, expiry `steward:121.5` | out of Launch; never a fold |
| Skills tree, adapters, runtime-state home | rebuild | re-provisioned from the adoption register; never a tree copy |
| Azure, staged-recipes CI, `compliance_face`, `services/` | retire | no Dream wants them |
| Never-built capabilities (atlas's Unity and Wasm satellites, Mason's Presenton set) | retire | operator 2026-11-10 ("Retire both"); `spec-pyforge-atlas:CAP-68` is `B-only`, a live Story carries it |
| `src/shared/packages/` brownfield tree | — (not a row) | stays on `local-recipes`; B rebuilds what its rows name; Story 44.4 retired 2026-11-10 |

## Envelope and CI evidence (iteration 4)

Foundry is **private, permanently** (`fnd:AD-14`). CAP-1's authoritative CI
evidence (operator 2026-09-13 D1) is a fresh-clone local run of `detectors-ci`
and `platform-ci-local` (plus CRC IFF the empty repo already carries the estate
Helm chart). GHA is a twin and may stay red; force-merge after that local proof
is the campaign gate. Fresh-clone local is not provisional. Story 44.15 /
`fnd:CAP-10` is later (D1b), not a Launch / 44.3 confirmation gate — it meters
minutes when GHA twins or Marshal drains spend them. Nothing Mason submits
carries a foundry URL. This campaign's publish path is SelfExplainML (D2);
44.9 stays blocked. Launch is the self-hosting slice of `launch-slice.md` (`fnd:CAP-2`); 44.3,
44.7 and 44.12 are done; 44.1, 44.4, 44.5 and 44.6 are retired (2026-11-10); later 44.8 / 44.14 /
44.15; out of campaign 44.9 / 44.11 (D3). **No archive of A (operator 2026-09-25):** CAP-7 and
44.10 are retired; two git roots stay live after the `cutover_root` flip, and what
`local-recipes` hosts afterwards is decided per capability by the ledger's modes.

## Phases → stories

| Phase | CAP | Story | Do | Done when | Gate |
|---|---|---|---|---|---|
| — | CAP-2 input, CAP-9 | 44.1 | **Retired 2026-11-10** (operator, second addendum ruling 3): its file-manifest half retired with `steward cutover apply`; its ledger half lands in Stories 121.1 to 121.7 | — | the ledger key stays `blocked` and is never dispatched |
| — | Constraints | 44.2 document fixes | R-23 `readOnlyRootFilesystem` + Windows / free-threading claims aligned to the Containerfile and `pixi.toml` platforms; R-24 Keycloak `26.4.0` pinned once; R-25 "no station-domain models on `django-<station>`"; `stack.md` / `convergence.md` floor `3.12.*` → `3.14.*` | edits land; `DW-RT-2026-09-02-7/-8/-9` resolved | — |
| 0 — Open foundry | CAP-1 | 44.3 | create `rxm7706/python-foundry` (private), workspace `pyforge`, empty of recipes, lean `pixi.toml`, estate-only CI; env export automated or not carried (R-17a) | clone exists; fresh-clone local `detectors-ci` + `platform-ci-local` green (CRC IFF Helm chart present); GHA twin may stay red | **outward**; operator-flipped; done 2026-09-13 |
| 1a — retired | CAP-2 | 44.4 | **Retired 2026-11-10** (operator ruling 2): no package fold; B rebuilds the kernel (Epic 54, `fnd:CAP-11`) | — | the ledger key stays `blocked` and is never dispatched |
| 1b — retired | CAP-2 | 44.5 | **Retired 2026-11-10** (operator ruling 2): no tree copy of skills, BMAD, decks or Dreams; B re-derives its chain from Dream plus memlog | — | the ledger key stays `blocked` and is never dispatched |
| 2 — retired | CAP-3 | 44.6 | **Retired 2026-11-10** (operator ruling 3): conda-forge-expert stays `A-only` until its own Spec exists after the flip (mason Story 39.2) | — | the ledger key stays `blocked` and is never dispatched |
| 3 — Factory island | CAP-4 | 44.7 | `factory/pixi.toml` + own lock; `factory/recipes/`, `build-locally.py`, `.ci_support/`, `conda-forge.yml`; recipes-only CI on `paths: factory/**` (R-17b) | `mason recipe build factory/recipes/<r>` matches today's CFE wrap; `DW-RT-2026-09-02-1` resolved | done 2026-09-13 |
| 4 — Working set | CAP-5 | 44.8 | carry in-flight and sole-maintainer recipes into the working set only | `factory/recipes/` is the working set; universe not copied (count ceiling asserted against a working-set list) | deps 44.7 |
| 5 — Mason → conda-forge | CAP-6 | 44.9 | `submit` → staged-recipes or bot fork; `update` → feedstock maintainer-edit | an agent PR never opens `local-recipes` (asserted on the submit path) | **outward + Mason**; deps 44.8 (and 44.6, retired 2026-11-10) |
| — | CAP-1..3 | 44.11 Windows-native estate | generated per-machine links (junctions on Windows), long-path preflight, no shell-only tasks, win-64 CI leg, `var/` state home | link check and detectors green on a Windows runner; a stock Windows clone runs recipes and station CLIs | deps 44.3 |
| — | CAP-2 prerequisite | 44.13 memlog fidelity | in `local-recipes`: fold every hand-edit in a rendered SPEC.md (unifying strategy first) back into memlog entries; prove each Spec re-renders without loss | `bmad-spec` re-derive of every Spec is byte-equivalent to the rendered file, or the diff is recorded as memlog entries | done 2026-09-10; `scripts/memlog_fidelity_check.py` holds the seed |
| — | CAP-9 | 44.14 rebuild harness + oracle gate | Dream + memlog → re-derived Spec → spine → epics in foundry; Marshal drains under a budget; the archived suite runs as oracle; a `rebuilding` row's freeze is judged by Doctor (`spec-pyforge-doctor:CAP-94`) | one pilot capability (Scribe) rebuilt end to end and `verified-in-foundry` through the oracle gate | deps 44.12 |
| — | CAP-10 | 44.15 Actions-minutes metering | `steward budget check` meters the account's Actions minutes (billing API through a `user`-scoped key in `steward keys`) against included minutes and the declared ceiling; `--json` for Marshal drains and 44.14 when those spend minutes | a real under/over verdict; a refused runner is a finding, never a cheap green | later, not Launch; unhooked from 44.3 (D1b) |
| — | CAP-8 | 44.12 cutover flag | `pyforge.cutover_root` flag + `pyforge-core` reader; `steward cutover plan` and `flip` | done 2026-09-13; its replay half is retired (operator ruling 2) | — |
| — | CAP-8, CAP-9 | Epics 120 and 121 | the contract and its decisions (Epic 120); the ledger generator, `plan` without `apply`, the ledger data, the session denial, the host anchor 121.5 (Epic 121) | each story's acceptance | the guard's branch half is doctor 56.5; the seam is marshal 117.2; the forge remote is marshal 115.4 |
| 6 — Archive | CAP-7 | 44.10 | **Retired 2026-09-25** (no archive of A); the ledger key stays `blocked` and is never dispatched | — | — |

**Order.** 44.13 (done) → 44.3 (done) → 44.7 ∥ 44.12 (done) → Epic 54, the kernel prototype at
PR #1344 (done) → Epics 120 and 121 (the contract, the generated ledger and the writer-lock guard) →
44.14 (the rebuild harness) → capability realization on B in dependency order, each row by its mode
(the kernel rebuilt first, then the rebuilt engines; `A-only` rows stay on A until their expiry;
`retire` rows never appear) → the Launch slice (`launch-slice.md`) → **flag flip**: the operator
flips `pyforge.cutover_root` by hand, with no loop running, once the Launch slice is proven;
nothing flips it automatically. (Retired: 44.1, 44.4, 44.5 and 44.6 on 2026-11-10, 44.10 on
2026-09-25. After the flip: 44.8 and mason 39.2. Out of campaign: 44.9 and 44.11.)

## Consolidation (2026-09-25) → stories

| CAP | Story | Do | Done when | Gate |
|---|---|---|---|---|
| CAP-12 | steward 67.1 | `pyforge-foundry-full` composes the `build` / `grayskull` features (and `pnpm` in `python`) on three platforms; current `crm` (≥0.8, feedrattler) stays a named CAP-13 gap; a layer env carries `platform-dev` + `platform-object-storage`; psycopg / pgvector caps and PG17 estate-wide; the `AGENTS.md` line | solves on linux-64, osx-arm64, win-64; the layer solves; scribe's Postgres suite green on PG17 | `pr-preflight`; `pyforge-station-tests` |
| CAP-13 | steward 67.2 | one laptop-gate task from the SBOM + layer alone | `pixi run -e pyforge-foundry-full sbom-laptop-gate` exit 0 on `main`; a planted missing dependency reds it | deps 67.1 |
| CAP-13 | steward 67.3 | tracked `docs/foundry/` gap list derived from `pixi.toml` (every feature outside the SBOM and its layer; every fat-only pin) | `pixi run -e pyforge-guild sbom-gaps-check` exit 0; every row has a disposition and an owner | deps 67.1 |
| CAP-13 | steward 67.4 | the upstream to-do list in the repo: a registry and paste-ready drafts for every `upstream` row and each session find; files nothing | `pixi run -e pyforge-guild upstream-todos-check` exit 0; every `upstream` row has an entry; an operator-only state carries `decided_by: operator` and a date | filing, tracking and retiring are the operator's acts alone; deps 67.3 |
| CAP-12 | steward 67.5 | developer guide, `AGENTS.md`, Mason / CFE docs name the SBOM | no doc names `-e local-recipes` as the laptop install | deps 67.2 |
| CAP-14 | herald 26.1 (steward index 67.6) | dossier Estate / Foundation / Synthesis / Verified + a structural test | `pixi run -e site site-check` exit 0; the structural test asserts every Verified item cites a source | — |
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
│   ├── stations/<station>/SKILL.md    # × 8; Mason's sits beside domain/conda-forge-expert
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
| Skill | `skills/stations/<station>/` (mason: `skills/stations/mason/` + `skills/domain/conda-forge-expert`) |
| Agent | `skills/personas/<station>/` (`python-persona-engine` + harness) |

## Do not create / carry

`.claude/skills/pyforge-mason/` (never carried; `A-only` on A until the flip) · lasting `src/shared/packages/` ·
`src/platform/compliance_face/` as the portal · `services/` or `:800x` · root
`docker-compose.yml` · `sys.path` for `django-*` · Containerfile `COPY` of django src ·
the `recipes/` universe · the 268 registered worktrees · `local-recipes` git history.

## The file manifest (retired 2026-11-10)

There is no file manifest. Story 44.1's manifest half retired with `steward cutover apply`
(operator ruling 2 of 2026-11-10); the plan is the capability ledger,
`docs/foundry/capability-ledger.yaml`, generated by `steward cutover plan` (§ The capability
ledger, `fnd:CAP-9`, `spec-foundry-capability-ledger`). B records its epoch in
`docs/foundry/EPOCH.md` and keeps its repository and its CI (operator ruling 1 of 2026-11-10).
