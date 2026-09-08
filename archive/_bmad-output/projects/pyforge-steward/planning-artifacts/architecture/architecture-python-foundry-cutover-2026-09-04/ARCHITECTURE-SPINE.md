---
name: "python-foundry-cutover (steward; extends the Canopy spine)"
type: architecture-spine
purpose: build-substrate
altitude: feature
paradigm: "strangler-fig repository cutover: a fresh lasting root receives the estate by manifest-driven moves over a bounded two-remote interval; the recipe plant is an island with its own lock; the old root becomes a read-only archive"
scope: "spec-python-foundry-cutover CAP-1..7 (cite fnd:CAP-n) — the move from rxm7706/local-recipes to python-foundry, Phases 0–6, decomposed as steward Epic 44 (all stories ledger-blocked). Inherits canopy:AD-1..23 and pap:AD-1..17 read-only."
status: draft
iteration: 4
gate: "PASS-WITH-FIXES 2026-09-04 — rubric walker + reality-check + adversarial-pairs lenses in reviews/; clear fixes applied; iteration 2 folds the review answers and the flag-gated cutover; iteration 3 makes the cutover regenerative: Dreams + memlogs seed foundry, every capability rebuilt or moved; iteration 4 closes the last two open questions: private foundry, CI evidence ladder, minutes metering"
created: "2026-09-04"
updated: "2026-09-04"
chain: pyforge-unifying-strategy
binds: [CAP-1, CAP-2, CAP-3, CAP-4, CAP-5, CAP-6, CAP-7, CAP-8, CAP-9, CAP-10]
sources:
  - ../../specs/spec-python-foundry-cutover/SPEC.md
  - ../../specs/spec-python-foundry-cutover/.memlog.md
  - ../architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
  - ../../../../../../docs/dreams/pyforge-unifying-strategy.md
companions:
  - ../../specs/spec-python-foundry-cutover/cutover.md
  - reviews/review-rubric-walker.md
  - reviews/review-reality-check.md
  - reviews/review-adversarial-pairs.md
---

# Architecture Spine — python-foundry-cutover

> **Solutioning iteration 4 (2026-09-04).** Iteration 1 was revised after the reviewer gate; iteration 2 made the cutover a flag with a regenerable plan; iteration 3 makes it regenerative: Dreams and memlogs are the only unconditional move, and every capability reaches foundry by rebuild or by move, decided per row; iteration 4 closes the last two open questions: foundry is private, and CI evidence is a real run with the remote host as self-hosted fallback (AD-23). Drafted on the
> Fast path; every inferred call still carries `[ASSUMPTION]` for the operator's review loop.
> Nothing here is dispatched: Epic 44's stories are ledger `blocked` until the operator flips
> them (AD-9). Cite this file's ids as **`fnd:AD-n`**; the Canopy spine's as **canopy AD-n**;
> the host spine's as **`pap:AD-n`**. No open question remains — see the last section.

## Design Paradigm

**Regenerative strangler-fig cutover.** The Dream seeds foundry; each capability is realized there by rebuild or by move (AD-2, AD-18, AD-20); the archive is the oracle (AD-21). Three roles, three places:

| Role | Place | Owner |
|---|---|---|
| Lasting root (estate) | `python-foundry/` — `pixi.toml` name `pyforge`, `src/platform/`, `src/packages/`, `skills/`, `_bmad-output/`, `docs/` | steward |
| Island (recipe plant) | `python-foundry/factory/` — own `pixi.toml` + `pixi.lock`, `recipes/` working set, recipes-only CI | mason |
| Archive (copy source) | `rxm7706/local-recipes` — read-only at a pinned SHA after Phase 6 | steward |

The **capability ledger** decides the mode of every capability and the **manifest** routes the files
of the moved ones (AD-2), both regenerated or appended at will. The two-remote era is bounded by one
flag flip (AD-17), not by a date; until a capability freezes (AD-22) `local-recipes` evolves normally.

## Inherited Invariants

Parent: `../architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md`
(canopy:AD-1..23) and, through it, `specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md`
(`pap:AD-1..17`). Read-only; original ids; never re-derived.

| Inherited | Binds here |
|---|---|
| pap:AD-2 host never imports `pyforge.*` | The fold (AD-6) changes paths, not this boundary. **Brownfield breach:** `src/platform/ingest/github_projects/*` imports `pyforge.steward.keys` in eight places today; AD-7 names its successor before deletion (open question `ingest-keys-import`). |
| pap:AD-9 consume factory packages, never fork | AD-7 ratifies it: the Containerfile's ten `COPY src/shared/packages/...` lines are the brownfield drift the cutover removes. |
| pap:AD-15 CI paths | Refined by AD-8: estate and island CI are disjoint by `paths`. |
| canopy:AD-4 reusable-app triple, one distribution per station | Distribution and import names are unchanged by the fold (AD-6). |
| canopy:AD-14 five tiers, or the 03 station is not done | `five_tier.py` retargets `_packages_root` and the skill/persona paths (AD-6, AD-5); the roster stays eight. |
| canopy:AD-16 packaging is an external gate | Foundry packages still arrive via the conda channel; the island builds them (AD-3, AD-4). |
| canopy:AD-17 station domain skills are SKF content skills; `skf-export` is the only writer into `CLAUDE.md` / `AGENTS.md` | SKF compiles into `skills/` (AD-5). Path rewrites inside `CLAUDE.md` / `AGENTS.md` after the fold go through `skf-export`, never a direct edit (AD-6). |
| canopy:AD-21 hooks and plugins are replaceable layers | Unchanged; the hook registry is the seam AD-4 keeps Mason behind. |
| canopy:AD-23 one interpreter `3.14.*`; `mcp-host` isolates MCP-SDK | Estate lock inherits it; the island lock is free to pin what recipes need. |

**Conflict, not override — canopy:AD-17:** AD-6's "every consumer path is rewritten" would
touch `CLAUDE.md` / `AGENTS.md`, whose only sanctioned writer is `skf-export`. Resolution:
44.4 and 44.5 re-run `skf-export` after their moves; the manifest marks those two files
`rewritten-by: skf-export`. **Conflict, not override — pap:AD-2:** the ingest import is a
live breach, not a rule this spine relaxes; 44.4 routes it through the in-process station
port (`pyforge.core.station_port`, steward 43.3) or the `steward keys` CLI, decided by
`ingest-keys-import`.

## Invariants & Rules

```mermaid
flowchart LR
  subgraph foundry [python-foundry]
    host["src/platform/ (host)"]
    pkgs["src/packages/* (workspace members)"]
    skills["skills/ (authoring tree)"]
    adapters[".claude/skills (symlinks; .cursor/skills if needed)"]
    island["factory/ (own lock)"]
    manifest["move-list manifest (rows · owner · coupling · destination)"]
  end
  archive["rxm7706/local-recipes (read-only archive)"]
  host -->|"installs workspace members"| pkgs
  adapters -->|"relative symlink"| skills
  pkgs -->|"pixi run --manifest-path factory/pixi.toml"| island
  manifest -->|"source_sha · epoch"| archive
  island -.->|"never a path-dep"| pkgs
```

### AD-1 — Fresh root, pinned source `[ADOPTED]`

- **Binds:** CAP-1, CAP-7; Stories 44.3, 44.10
- **Prevents:** two live histories; the purged-secret history and 268 worktrees riding into the lasting repo; ambiguity over which repo is truth
- **Rule:** Foundry's first commit carries no `local-recipes` history (no `filter-repo`, no subtree import). Every manifest row carries the `source_sha` it was lifted at, and the manifest records the **foundry epoch SHA** (AD-16). After Phase 6, `local-recipes` is archived read-only at its final SHA, that SHA is pinned in the foundry manifest and the Dream's Realization log, and its README opens with the supersession banner.

### AD-2 — Two layers: a capability ledger over the file manifest, both derived

- **Binds:** CAP-2, CAP-3, CAP-4, CAP-5, CAP-9; Story 44.1 and every realization story
- **Prevents:** two stories routing one path differently; a tracked path silently dropped; the spec-surface allowlist (`.claude/**`, `_bmad/**`, `_bmad-output/**`, `docs/dreams/**`, `docs/governance/**`, `.github/**` — the very trees the cutover moves) leaving 20 % of paths unrouted; a hand list that omits the newest thing
- **Rule:** The **capability ledger** has one row per capability, derived from the Dreams and the spec-surface owner map: `mode` (`rebuild` | `move` | `retire`), `state` (`planned` | `rebuilding` | `moving` | `verified-in-foundry` | `cut`), dependencies, and the four decision signals. The **file manifest** exists only under `move` rows; a `rebuild` row has no file rows (its files are `stays` by construction) and a `retire` row's files are `dies`. Manifest rows come from `git ls-files` — one row per tracked path, allowlisted trees included. The spec-surface classification (`scripts/spec_surface_check.py`) supplies the row's **owner** only (`unowned` is legal). Coupling comes from `scribe index move-list` (`pyforge.scribe.extras.move_list`: host `pyforge.*` imports, `sys.path` inserts, `five_tier` roots, CFE callers) **plus a `parent_depth` signal** for code that computes paths by `parents[N]` / fixed `../` depth. **Destination** is resolved by an ordered precedence list of glob rules (most specific wins); a path matched by two rules of equal precedence is row kind `ambiguous` and blocks until an operator rule resolves it. The manifest is a machine-readable file with per-directory rollups (24,858 rows are not a markdown table), produced by `steward cutover plan` in two modes: `--regenerate` rebuilds every row from scratch at HEAD; `--append` folds in only the delta since the manifest's recorded `source_sha` (added, renamed and deleted paths gain or update rows). Both modes preserve `moved` rows, so regeneration is idempotent over status. A move story consumes the rows for its phase and marks them `moved` with the foundry commit; a move without a row is review-blocking.

### AD-3 — Two locks, one workspace name; tooling split by role

- **Binds:** CAP-1, CAP-4; Stories 44.3, 44.4, 44.7; red-team D-2 / R-17
- **Prevents:** the 29-environment single lock that turns every dependency change into a 59k-line diff; recipe churn re-solving the estate; a "no solver tooling" rule that strips warden's test oracles
- **Rule:** Root `pixi.toml` is `name = "pyforge"` and locks the estate only. `factory/pixi.toml` + `factory/pixi.lock` lock the island only. No path dependency crosses the island boundary in either direction. The island owns **recipe build / lint / submit tooling by role**: `rattler-build`, `conda-smithy`, `conda-build` as a build engine, `conda-forge-pinning`, `grayskull`. Estate exemptions are enumerated by name, never by role: warden's test-only differential oracles `conda-build` and `py-rattler-build` (`[feature.pyforge-warden]`), and the `pixi-build-python` / `pixi-build-rattler-build` workspace-member backends. Any other solver-farm package in the estate lock is a finding.

### AD-4 — Mason reaches the island by manifest path, never by import

- **Binds:** CAP-3, CAP-4, CAP-6; Stories 44.6, 44.7, 44.9
- **Prevents:** the estate environment regrowing the solver farm; a second copy of the CFE skill; `MASON_CFE_ROOT` pointing back at the archive; a marker constant that no longer matches after the move
- **Rule:** `MASON_CFE_ROOT` stays a **repo root** (flag → env → cwd walk, `pyforge/mason/resolve.py`) whose marker `_CFE_MARKER` (today `.claude/scripts/conda-forge-expert`, `resolve.py:100`) moves with the cell to `skills/domain/conda-forge-expert/scripts`; the marker constant is a manifest consumer rewritten in 44.6. Recipe build, submit and update are subprocesses of `pixi run --manifest-path factory/pixi.toml <task>`; `pyforge-mason` imports nothing from the island.

### AD-5 — One skills tree; IDE directories are adapters

- **Binds:** CAP-2, CAP-3; Stories 44.5, 44.6; canopy:AD-17
- **Prevents:** divergent `SKILL.md` copies per IDE; an edit landing in one adapter and not the other; the installer carve-out accidentally exempting the eight station personas; a symlink in git that checks out as a text file on stock Windows
- **Rule:** Estate-authored skills live only under `skills/{stations,personas,domain}/<x>/`; SKF export writes there (`skills/stations/<x>/` is its root; 44.5 verifies `skf-export` accepts it). **No adapter is tracked in git.** Adapters are generated per machine by the link step (AD-19): `.claude/skills/<x>` always; `.cursor/skills/<x>` only where Cursor is detected or requested. Both are gitignored. Installer-**written** directories (`bmad-*` from the BMAD installer, `skf-*` from the forge) stay real directories; the eight station personas (`bmad-agent-<station>`) are estate-authored and move to `skills/personas/<station>/`. A regular directory for an estate skill under an adapter is a detector finding.

### AD-6 — The packages fold is a path rewrite, not a rename

- **Binds:** CAP-2; Story 44.4; canopy:AD-4, AD-14, AD-17
- **Prevents:** a half-moved tree with two package roots; a distribution or import rename smuggled in with the move; 59 files computing paths by fixed parent depth silently resolving a wrong root; a stale spec-surface baseline after every move
- **Rule:** `src/shared/packages/<x>` → `src/packages/<x>`; distribution and import names unchanged. Every consumer is rewritten from manifest rows in the same story: `pixi.toml` path-dependencies (103 sites), the Containerfile `COPY` lines, `five_tier._packages_root`, `script_map_from_packages_root`, `marshal-policy.toml` globs, Spec `surface:` globs, CI `paths:`, and every `parent_depth` coupling row (`parents[N]` constants; no silent wrong-root fallback survives). `CLAUDE.md` / `AGENTS.md` are rewritten by re-running `skf-export` (canopy:AD-17). Every move story ends with a scoped `spec_surface_check.py --write-baseline --spec <affected>` re-stamp. After 44.4 no `src/shared/` exists and `rg src/shared/packages` returns only the manifest and the archive.

### AD-7 — The host consumes packages, never copies source

- **Binds:** CAP-2; Story 44.4; ratifies pap:AD-9, canopy:AD-16
- **Prevents:** the ten `COPY src/shared/packages/...` lines (nine django portals + the `pyforge-steward` library) and the builder-stage `COPY . /app` riding into foundry; deleting a working import path with no successor
- **Rule:** Each `src/packages/*` is a pixi-build workspace member with its own `pixi.toml`; today that is true for all ten `pyforge-*` packages (under the `pixi-build` preview flag) and for none of the seven `django-*` packages — 44.4 adds theirs. The platform image installs workspace members; the Containerfile has no `COPY src/packages`, no `COPY . /app` of package source, and no `sys.path` insert for a package (`platformapp`'s own insert is host-internal `[ASSUMPTION]`). No import path is deleted without its successor named in the story (`ingest-keys-import`).

### AD-8 — Two CI estates, disjoint triggers, classified not counted

- **Binds:** CAP-1, CAP-4, CAP-7; Stories 44.3, 44.7, 44.10; R-17a
- **Prevents:** a recipe PR paying for platform CI and the reverse; the `maintenance`-label and hand-run `environment.yaml` rituals; an undercounted "dies" list
- **Rule:** Estate workflows carry `paths-ignore: [factory/**]`; island workflows carry `paths: [factory/**]`. Every workflow and CI script is a manifest row; a row that references `staged-recipes` **dies**: the four linter workflows, `test-all.yml` and `test-{linux,macos,windows}.yml`, `scripts/linter.py` (where the `environment.yaml` sync check lives), `azure-pipelines.yml`, `.azure-pipelines/`, `.scripts/`. `environment.yaml` is produced by a workflow step or dropped; never a by-hand step. No foundry workflow references `staged-recipes`.

### AD-9 — Every Epic 44 story is a gate the operator flips

- **Binds:** CAP-1, CAP-6, CAP-7; all of 44.1–44.10
- **Prevents:** a drain creating a GitHub repository, opening conda-forge PRs, or disabling CI unattended; implementation starting before the solutioning review closes
- **Rule:** All 44.x are ledger `blocked` while solutioning is under review; the flip to `backlog` is the operator's act per story. 44.3, 44.9 and 44.10 additionally require explicit operator confirmation at dispatch. Marshal never auto-flips a `blocked` key.

### AD-10 — Working set, not universe

- **Binds:** CAP-5; Story 44.8
- **Prevents:** the 7,855-directory `recipes/` copy
- **Rule:** `factory/recipes/` admits a recipe only through a manifest row whose `reason` is one of `in-flight`, `sole-maintainer`, `referenced-by-spec` (the AD-2 precedence list resolves the many-to-many `recipes/**` claims). Island CI asserts `count(factory/recipes/*) <= count(manifest rows)`.

### AD-11 — Two remotes are a migration interval bounded by the flag

- **Binds:** CAP-2..CAP-8; Phases 1–5
- **Prevents:** drift between the two trees while both are live; freezing the evergreen repo before the flip
- **Rule:** Before the flip (AD-17) `local-recipes` is primary and evolves normally except where a capability has entered `rebuilding` or `moving`, which freezes its source paths at once (AD-22); every other change reaches foundry by `steward cutover plan --append` followed by the replay (AD-18). After the flip the roles reverse: foundry is primary, every `moved` row and every rebuilt capability's source is frozen in `local-recipes` (detector `frozen-path-changed`), and `local-recipes` accepts only hygiene.

### AD-12 — The BMAD chain moves whole; one ledger of record

- **Binds:** CAP-2; Stories 44.5–44.10
- **Prevents:** a loop home or a `bmad-switch` marker still targeting `local-recipes`; two ledgers both accepting rows mid-epic
- **Rule:** `_bmad/`, `_bmad-output/projects/` and `docs/dreams/` move in 44.5 as one unit. The marker and the two planning symlinks are per-working-tree state recreated by `bmad-switch` / `bmad-loop-worktree`, never copied. The ledger of record follows the flag (AD-17), not the story: before the flip it is `local-recipes`', after it foundry's, and `sprint-ledger-sync` runs in the primary root. The eight `~/.bmad-loops/*` homes are re-provisioned against the foundry remote by the same flip, in an attended session with no loop running.

### AD-13 — The CFE cell is one unit with one owner

- **Binds:** CAP-3; Story 44.6; canopy:AD-17
- **Prevents:** three claimants on `.claude/skills/conda-forge-expert` (the skills move, 44.6, and the SKF export); its siblings having no owner; both CFE detectors matching nothing after the move and reporting clean
- **Rule:** The cell is `.claude/skills/conda-forge-expert/` + `.claude/scripts/conda-forge-expert/` + `.claude/tools/conda_forge_server.py` + the 76 `.claude/scripts/conda-forge-expert` references in `pixi.toml` (its runtime state `.claude/data/conda-forge-expert/` moves to `var/cfe/`, AD-19). It moves in **44.6 only**, to `skills/domain/conda-forge-expert/{SKILL.md,scripts,tools}`; 44.5 leaves it in place. The path literals in `cfe_rebuild_guard_check.py` and `mason_cfe_surface_check.py` are manifest consumers rewritten in 44.6.

### AD-14 — Repo operational envelope

- **Binds:** CAP-1, CAP-6; Stories 44.3, 44.9
- **Prevents:** a repository created with undecided visibility, no branch protection, and secrets re-typed by hand; a conda-forge reviewer sent to a link that is dead outside the account
- **Rule:** Visibility is **private, permanently** (operator 2026-09-04, iteration 4; closes `repo-visibility`). `dashboard.yml` keeps deploying GitHub Pages on the paid plan that already serves the public site from the private `local-recipes`; the win-64 leg (AD-19) bills at 2×, so Actions minutes are a standing budget under AD-23. Nothing Mason submits carries a foundry URL; the strip on the submit path stays. Default branch `main`, protected, merge commits only; the operator and the marshal bot identity may push. Secrets and variables (`CRC_PULL_SECRET`, `HERALD_WEBHOOK_SECRET`, the six `vars.PLATFORM_CI_*`) are manifest rows of kind `secret` (no value in the manifest) re-provisioned through `steward keys` (FR-5 inventory).

### AD-15 — Identity strings are manifest rows; environment ids are not renamed here

- **Binds:** CAP-3, CAP-6, CAP-7; Stories 44.4–44.10
- **Prevents:** 333 `rxm7706/local-recipes` occurrences in 148 files pointing at the archive; a silent rename of the `local-recipes` pixi env breaking 974 call sites and GATE-011-frozen `verify_commands`
- **Rule:** Repository identity strings (`rxm7706/local-recipes` URLs and slugs) are manifest rows of kind `identity`, rewritten by the story that moves the file. The pixi environment id `local-recipes` stays until a named rename story — the same rule the Dream applies to `[feature.python-agent-platform]`.

### AD-16 — Detector ranges on a fresh root

- **Binds:** CAP-1, CAP-3; Stories 44.3, 44.6
- **Prevents:** `cfe_rebuild_guard_check` and `mason_cfe_surface_check` passing vacuously on a repository whose git range starts at the epoch
- **Rule:** The foundry epoch SHA is recorded in the manifest; every git-range detector takes it as its floor. A zero-commit range is exit 2 (could-not-run), never a clean verdict.

### AD-17 — Cutover is a flag, not a date `[ADOPTED]`

- **Binds:** CAP-8, CAP-6, CAP-7; every story from 44.4 on
- **Prevents:** a dated phase boundary that freezes the evergreen repo; a cutover with no rollback; three consumers deciding the root of record differently
- **Rule:** One flag, `pyforge.cutover_root` in {`local-recipes`, `foundry`}, lives in the CAP-13 flag tree (`src/platform/config/flags.json`, canopy:AD-11), read in-process by the host and by the CLIs through a `pyforge-core` reader (a 44.12 task; none exists today). It alone decides the ledger of record (AD-12), Mason's submit and update targets (AD-4), which remote the loop homes track, and which root the detectors treat as primary. The transition point is the flip, allowed once the capabilities it depends on are `verified-in-foundry` (AD-22); flipping back is the rollback. The flip is an operator act recorded in the Dream's Realization log.

### AD-18 — Moves are replays; rebuilds are regeneration drills

- **Binds:** CAP-2..CAP-5, CAP-8, CAP-9; Stories 44.4–44.8, 44.14 and every capability row
- **Prevents:** one-off hand moves that cannot be repeated after the plan changes; a foundry mirror that silently falls behind the evolving repo; a rebuild that is a rewrite by another name
- **Rule:** A `move` capability is realized by a manifest-driven, idempotent apply step (`steward cutover apply --phase <n>`) that can be re-run into foundry after every `--regenerate` or `--append` until the flag flips; a hand move the apply step cannot reproduce is review-blocking, and the replay records the foundry commit on each row. A `rebuild` capability is realized as a regeneration drill in foundry: its Dream and moved memlog → `bmad-spec` re-derives the Spec → `bmad-architecture` inherits the parent invariants → epics and stories → `bmad-build` drained by Marshal under a `steward budget` ceiling, with the archived code visible only as reference. Either way the row reaches `verified-in-foundry` only through AD-21.

### AD-19 — Native estate on stock Windows; host and supervisor remote `[ADOPTED]`

- **Binds:** CAP-1, CAP-2, CAP-3; Story 44.11
- **Prevents:** symlinks that check out as text files; Developer Mode or WSL as a prerequisite; paths past 260 characters; shell-only tasks that break outside POSIX
- **Rule:** No symlink is tracked in git. A link step (`steward links` — name a 44.11 task) generates every runtime link per machine: symlinks on Linux and macOS, directory junctions via `_winapi.CreateJunction` on Windows (no privilege needed); the same helper serves `bmad-switch` and the adapters. A doctor preflight fails loud when a link is missing or is a text file, and when the deepest tracked path from the clone root exceeds the Windows limit (long-path registry settings are never assumed). No pixi task depends on `bash -c`, `sed`, `grep`, `awk`, `find` or `tee`; Python replaces them, `m2-*` conda tools are the fallback. A win-64 CI leg runs the station suites, the link check and the detectors. Runtime state lives in gitignored `var/` at the repo root (`var/atlas`, `var/cfe`, `var/worktrees`). The Django host and the fleet supervisor are Linux and macOS only, reached from Windows through a remote Linux dev host; making the host native is a solver-probe story, never a promise.

### AD-20 — The seed is Dreams plus memlogs `[ADOPTED]`

- **Binds:** CAP-2, CAP-9; Stories 44.13, 44.1
- **Prevents:** carrying 69 MB of rendered planning narrative into a greenfield root; re-deriving a Spec and losing hand-edits its memlog never recorded
- **Rule:** `docs/dreams/` and every Spec and spine `.memlog.md` move unconditionally; they are the decision record. `SPEC.md`, spines, epics and stories are re-rendered in foundry by `bmad-spec`, `bmad-architecture` and `bmad-create-epics-and-stories`. Every other planning document (research, reviews, proposals, readiness reports, retros, run records, per-story specs of shipped stories) is archived. Prerequisite, in `local-recipes` before Phase 0 (Story 44.13): every hand-edit in a rendered `SPEC.md` — the unifying strategy first — is folded back into memlog entries, and each Spec proves it re-renders without loss.

### AD-21 — The archive is the oracle

- **Binds:** CAP-9; every `rebuild` row
- **Prevents:** regeneration drift dressed as a rebuild
- **Rule:** A rebuilt capability reaches `verified-in-foundry` only when the archived test suite for that capability passes against the rebuilt code, or an equivalence check does, and the re-derived Spec's success criteria hold. A rebuild story without its oracle gate is review-blocking.

### AD-22 — Per-capability state and freeze under one global flag

- **Binds:** CAP-8, CAP-9; every capability row
- **Prevents:** a fragmented root of record; double maintenance of a capability being rebuilt while its source keeps changing; a flip that outruns its dependencies
- **Rule:** `pyforge.cutover_root` remains the only root-of-record switch. Each capability row carries its own state; the flip is allowed only when every capability it depends on is `verified-in-foundry`. A capability entering `rebuilding` or `moving` freezes its source paths in `local-recipes` at once; `frozen-path-changed` is keyed by ledger state, not by the flag, and `steward cutover plan --append` reports any source change against a frozen row as a finding.

### AD-23 — CI evidence ladder and the minutes guard `[ADOPTED]`

- **Binds:** CAP-1, CAP-9, CAP-10; Stories 44.3, 44.14, 44.15
- **Prevents:** a "green" that never ran (the 2026-08-30 block failed every job in 2 s and looked cheap); CAP-1 dispatched into a blocked account; a drain that discovers the minutes ceiling by being refused
- **Rule:** CAP-1's evidence is a real green workflow run on a registered runner, in this order: GitHub-hosted; the AD-19 remote Linux dev host registered as a self-hosted runner (estate workflows declare its label as the `runs-on` fallback); and, only while both are unavailable, a documented fresh-clone run of the estate gates on that host — **provisional**, never CAP-1's success. With no evidence path at all, 44.3 does not dispatch. `steward budget check` meters the account's Actions minutes (the billing API through a `user`-scoped credential in `steward keys`, never a token in the manifest) against the plan's included minutes and the declared ceiling; it is read at 44.3's confirmation, by Marshal's foundry drains and by the rebuild harness as their ceiling (Story 44.15). AD-8's classification is unchanged; runner selection lives here.

## Consistency Conventions

| Concern | Convention |
|---|---|
| Id citation | `fnd:AD-n` / `fnd:CAP-n` (this chain) · `canopy AD-n` · `pap:AD-n` / `pap:CAP-n`. Bare ids outside their own file are review-blocking. |
| Manifest row | `path · kind (file \| secret \| identity) · owner · coupling[] · destination (target path \| stays \| dies \| ambiguous) · reason · source_sha · status (pending \| moved \| archived) · foundry_commit` |
| Manifest file | machine-readable (JSONL or CSV) with per-directory rollups at `docs/foundry/manifest.*` `[ASSUMPTION: location]`; header carries the epoch SHA and the `source_sha` the last `--regenerate` or `--append` ran at |
| Capability row | `capability (fnd/canopy/pap/station CAP-n) · owner spec · mode (rebuild \| move \| retire) · state · depends_on[] · signals (fidelity, coupling, debt, state) · decided_by · decided_on` |
| Mode decision | scored by four repo signals, decided by the operator per row; first pass in `cutover.md` |
| Cutover flag | `pyforge.cutover_root` ∈ {`local-recipes`, `foundry`} in `src/platform/config/flags.json`; flips are Realization-log entries |
| Runtime links | generated per machine, never tracked; symlink on POSIX, junction on Windows; gitignored |
| Phase ↔ story | Phase n ↔ Story 44.(n+3); 44.1 manifest, 44.2 document fixes; ledger key `44-N-<slug>` |
| Workspace names | root `pyforge`; island `pyforge-factory` `[ASSUMPTION]` |
| Adapter symlinks | relative (`../../skills/...`), never absolute |
| Dates / versions | `YYYY-MM-DD`; CalVer unpadded (inherited) |

## Stack

| Name | Version |
|---|---|
| pixi (both workspaces) | `0.78.0` (`requires-pixi >= 0.78.0`; registry-enforced by `pixi-version-check`) |
| pixi-build backends (`pixi-build-python`, `pixi-build-rattler-build`) | lock-pinned; `preview = ["pixi-build"]` stays until the feature is stable |
| Python (estate) | `3.14.*` (canopy:AD-23) |
| rattler-build (island) | `>=0.75.0` (lock `0.75.0`; conda-forge current) |
| py-rattler-build (estate, warden test oracle) | `0.72.2` (lock) |
| conda-smithy (island) | `>=3.44.6,<4` — the cap is deliberate (CalVer `2026.x` needs the `conda` package absent from the env); revisit in 44.7 |
| conda-build (island engine; estate test oracle) | `>=25.3.1` |
| GitHub Actions | estate + island workflows; Azure DevOps not carried |
| bmad-* suite floor | bmad-method >=6.12.0, bmad-loop >=0.11.1, bmad-module-skill-forge >=2.1.0 (linux-64 only), bmad-creative-intelligence-suite, bmad-method-test-architecture-enterprise, bmad-eval-quality, bmad-utility-skills, bmad-builder — win-64 (44.11) excludes skf and eval-quality |

## Structural Seed

```text
python-foundry/
  pixi.toml  pixi.lock  environment.yaml   # estate; name = pyforge; env ids unchanged (AD-15)
  AGENTS.md  CLAUDE.md                     # written by skf-export only (canopy:AD-17)
  factory/                                 # island — own pixi.toml + pixi.lock
    recipes/  build-locally.py  .ci_support/  conda-forge.yml
  .github/workflows/                       # estate (paths-ignore factory/**) + island (paths factory/**)
  src/platform/                            # host; workspace-member installs; no COPY of package source
  src/packages/                            # pyforge-core, pyforge-<station> ×8, pyforge-testing-kit, django-pyforge, django-<station> — each with pixi.toml
  skills/{stations,personas,domain}/       # authoring tree; mason → domain/conda-forge-expert/{SKILL.md,scripts,tools}
  .claude/skills/  (.cursor/skills/)       # generated per-machine links (gitignored) + installer-written skills
  var/                                     # gitignored runtime state: atlas, cfe, worktrees (AD-19)
  src/platform/config/flags.json           # CAP-13 flag tree; carries pyforge.cutover_root (AD-17)
  _bmad/  _bmad-output/projects/  docs/dreams/  docs/governance/
  docs/foundry/manifest.*                  # rows · owner · coupling · destination · epoch (AD-2)  [ASSUMPTION: location]
```

```mermaid
flowchart LR
  P0["Phase 0 · 44.3<br/>open foundry (AD-14 envelope)"] --> P1a["Phase 1a · 44.4<br/>fold packages"]
  M["44.1 manifest<br/>(ls-files · owner · coupling)"] --> P1a
  P1a --> P1b["Phase 1b · 44.5<br/>skills · BMAD · decks · dreams"]
  P1b --> P2["Phase 2 · 44.6<br/>CFE cell (Mason)"]
  P0 --> P3["Phase 3 · 44.7<br/>factory island"]
  P3 --> P4["Phase 4 · 44.8<br/>working set"]
  P2 --> P5["Phase 5 · 44.9<br/>Mason → conda-forge"]
  P4 --> P5
  P5 --> P6["Phase 6 · 44.10<br/>archive local-recipes"]
  D["44.2 document fixes"] -.-> P6
```

## Capability → Architecture Map

| Capability | Lives in | Governed by |
|---|---|---|
| CAP-1 open foundry | `python-foundry` root, estate workflows | AD-1, AD-3, AD-8, AD-9, AD-14, AD-16, AD-23 |
| CAP-2 realize the estate | `src/packages/`, `skills/`, `_bmad*/`, `docs/dreams/` | AD-2, AD-5, AD-6, AD-7, AD-12, AD-15, AD-18, AD-19 |
| CAP-3 CFE comes home | `skills/domain/conda-forge-expert`, `pyforge/mason/resolve.py` | AD-4, AD-5, AD-13, AD-16 |
| CAP-4 factory island | `factory/` | AD-3, AD-4, AD-8 |
| CAP-5 working set | `factory/recipes/` + manifest | AD-2, AD-10 |
| CAP-6 Mason → conda-forge | `pyforge-mason` submit/update paths | AD-4, AD-9, AD-11, AD-15 |
| CAP-7 archive | `rxm7706/local-recipes` | AD-1, AD-8, AD-9, AD-11, AD-15 |
| CAP-8 flag-gated, replayable cutover | `steward cutover plan/apply`, `flags.json`, `pyforge-core` flag reader | AD-2, AD-17, AD-18, AD-22 |
| CAP-9 capability ledger + rebuild harness | `steward cutover plan` (ledger), foundry's own planning tree, Marshal drains | AD-2, AD-18, AD-20, AD-21, AD-22, AD-23 |
| CAP-10 metered minutes budget | `steward budget` (metering source), `steward keys`, estate workflows' `runs-on` | AD-14, AD-19, AD-23 |

## Deferred

| Item | Why it can wait | Revisit when |
|---|---|---|
| `config/` vs today's `conf/`, and `src/ides/ src/sentinel/ src/domains/` scaffolding | Manifest rows decide per path; no cross-story divergence | 44.1 renders the manifest |
| `environment.yaml` keep-or-drop | AD-8 allows either; the sync check dies with `scripts/linter.py` | 44.3 writes the first estate workflow |
| Runtime-state home (`.claude/data/` 11 GB, `.claude/worktrees/` 85 GB) | Gitignored today; no tracked path moves | Open question `runtime-state-home` |
| Epic 45 candidates (R-18..R-22: sizing, NetworkPolicy, secrets, SLOs, `/ws/events/`) | Ops gaps in `src/platform/`, not layout; operator carried them | A consumer story appears |
| Archive history rewrite (purged secret) | AD-1 leaves it behind by construction | Only if the archive must be published |
| Worktree retirement mechanics (268 registered) | Local residue; nothing tracked | 44.10 |
| Foundry package release cadence / channel | Unchanged by the move (`[ASSUMPTION]`) | First island publish after 44.7 |
| Native Django host on win-64 | AD-19 keeps the host remote; Langflow and DB-GPT trees make it a probe | A solver-probe story after 44.11 |
| Renaming the `local-recipes` pixi env | AD-15 holds it; 974 call sites + GATE-011 | A named rename story, after 44.10 |
| Which capabilities rebuild versus move | Operator-owned per row; first pass in `cutover.md` is `[ASSUMPTION]` | 44.1 renders the ledger with the four signals scored |

## Open Questions (iteration 4)

None. Answered in iteration 4: `repo-visibility` (AD-14 — private, permanently) and `actions-minutes` (AD-23 — evidence ladder, self-hosted fallback on the remote host, provisional fresh-clone run, no dispatch without an evidence path; CAP-10 metering, Story 44.15).

Answered in iteration 2 (recorded as ADs): `windows-symlink-adapters` and `runtime-state-home` (AD-19), `cursor-skill-discovery` and `skf-export-root` (AD-5), `loop-home-cutover-timing` (AD-17). Answered in iteration 3: `planning-history-scope` (AD-20), `ingest-keys-import` (rebuild the ingest in `pyforge-steward` behind the station port; capability ledger first pass).
