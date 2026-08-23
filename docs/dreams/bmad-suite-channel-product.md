---
title: The PrivateChannel bmad-suite is a governed product — always latest, dual-path installable, modules provisioned
type: dream
owner: steward
status: specified   # 2026-08-22 — spec-bmad-suite-channel-product (5 CAPs + install-matrix.md); decomposed as steward Epic 15 (4 stories) + doctor Epic 15 (2 stories, CAP-5 relay); channel bmad-method refreshed to 6.11.0 same day
---

# The PrivateChannel conda install bmad-suite is a governed product

## The Dream

The operator intends to utilize the complete bmad-suite (13 packages). Every
one of them should be installable two ways at all times — **via pixi from the
PrivateChannel channel** and **via its upstream-native method** (npm, npx
module selection, uv-from-git, Claude plugin marketplace, custom-source) —
at the latest available version, with its skills/module actually wired where
the fleet works. Today that is true only because a human hand-drove all seven
pipeline stages during the 2026-08-21/22 refresh: upstream-watch → recipe
bump → build → channel publish → pixi install → module wiring → native-parity
check each exist as an isolated tool, and **no stage is connected to the
next, scheduled, or verified end-to-end**. The proof: the channel served a
stale `bmad-method 6.3.0` for four months and bmad-loop sat two minors behind
(an unattended-run breaker) with no signal until a human looked.

## Grounding — verified state (2026-08-22 research pass)

**Version currency is NOT the gap (today):** all 5 tag-pinned suite recipes
match the newest upstream tag/release; all 6 commit-pinned recipes
(utility-skills, labs-skills, module-template, manticore, dashboard, mybmad)
are pinned at the literal default-branch HEAD. Two exceptions:

1. **Channel `bmad-method` = 6.3.0** vs recipe/conda-forge 6.11.0 — the one
   channel↔recipe divergence (harmless to solves: conda-forge shadows it, and
   conda-forge/bmad-method-feedstock is current at 6.11.0 — the ONLY suite
   package with a feedstock; the other 12 are PrivateChannel-Conda -only).
2. **TEA v1.23.3 tagged-but-unreleased** (git tag exists, package.json 1.23.3;
   npm latest still 1.23.2, no GH release) — a watch/optional bump.

**The native-method taxonomy (7 classes, per upstream docs — the matrix a
dual-path guarantee must encode):**

| Class | Packages | Native command |
|---|---|---|
| npm CLI installer | bmad-method | `npx bmad-method install` |
| Own npx installer | bmad-module-skill-forge | `npx bmad-module-skill-forge install` |
| BMAD module via installer selection | TEA, bmad-builder, CIS, WDS | `npx bmad-method install` → select module |
| Custom-source BMAD module | bmad-manticore | `npx bmad-method install --custom-source <repo-url>` |
| Claude Code plugin marketplace | bmad-utility-skills, bmad-labs-skills | `/plugin marketplace add <repo>` (labs also `npx skills add bmad-labs/skills`) |
| uv-from-git (Python, not on PyPI) | bmad-loop | `uv tool install "bmad-loop[tui] @ git+…@v0.11.0"` |
| Template / build-from-source | bmad-module-template (GitHub template); bmad-dashboard + mybmad-dashboard (pnpm build / self-host) | per-repo README |

**npm hazards the pipeline must encode:** 7 packages are npm-invisible under
their recipe names (loop, wds, utility-skills, labs-skills, module-template,
manticore, mybmad); 3 more are npm-STALE with GitHub as the channel of record
(builder 1.1.0-on-npm vs 2.2.1, CIS 0.1.9 vs 0.3.1, WDS 0.3.1/0.3.4 vs
0.4.3); and 3 npm name-collisions must never be confused with the suite
(`bmad-dashboard` = caionormando, `bmad-skills` = bacoco, `bmad-method-ui` =
lorenzogm).

**The machinery that exists but composes into nothing (local audit):**

- `autotick-github` / `autotick-npm` pixi tasks — one recipe per manual
  invocation; no batch mode, no registration of covered recipes, no schedule,
  and no HEAD-advance mode for the six commit-pinned dev recipes.
- `steward provision --module` shipped (Epic 6) but `_SUPPORTED_MODULES`
  holds exactly one entry (`bmb`); TEA/CIS/utility-skills/manticore were
  never added. Wired today: core+bmm, skf, labs-skills, loop, dashboards.
  Unwired: TEA, BMB(builder), CIS, utility-skills, manticore.
- `inventory-channel` can audit any channel URL — never pointed at our own.
- Channel publish = the hand-run `anaconda -s … upload` cheatsheet flow; no
  task, no verify-the-listing step, no channel↔recipe drift detection.
- Doctor's suite drift (14.1, shipped 2026-08-22) watches installed-env vs
  npm only — blind to the 7 npm-invisible packages pending the
  GitHub-releases fallback (doctor DW-14-1-1), and nothing watches
  recipe-vs-upstream or channel-vs-recipe at all.
- `bmad-module-skill-forge` has NO pixi.toml pin (consumed only via the BMAD
  installer) — the one pixi-installability gap in the suite itself.

## Whose job this is

**Steward** — the pipeline is operations: publishing to a channel it holds
credentials for, provisioning modules (its realized `bmad-module-provisioning`
capability, deliberately built to grow one `_SUPPORTED_MODULES` entry at a
time), and running scheduled duties. The pieces other stations own are
relayed, not absorbed: **doctor** keeps ambient detection (the
GitHub-releases fallback DW-14-1-1 + new channel↔recipe/recipe↔upstream
checks extend its shipped suite-drift spec); **CFE/the factory** keeps recipe
bumps (autotick extensions land as skill-script work under Rule 1/2);
**mason** keeps recipe validation. Kin, not overlap: steward Epic 14 (core
upgrade apply), `bmad-611-era-alignment` (marshal, era retrofits).

## What it looks like when real

- **One command reports the whole pipeline's truth**: for each of the 13 —
  upstream latest (npm AND GitHub, per its class), recipe version, channel
  version, installed version, wired-or-not — with drift named per stage.
- **One command advances a stale package end-to-end**: autotick (tag-mode or
  HEAD-advance mode per the recipe's pin style) → build → test → publish →
  listing verified — the 2026-08-21 seven-stage hand ritual as governed
  machinery, CFE conventions intact.
- **`steward provision --module` covers every wire-decided module** (TEA,
  bmb, CIS, utility-skills, manticore added; WDS explicitly skip-decided as
  upstream-deprecated; template is a scaffold, labs/loop/skf/dashboards
  already wired) — reproducible against a fresh clone, manifest-recorded,
  collision-checked, guard-green.
- **The dual-path matrix is a tracked contract**: per package, the pixi path
  and the native command, with the npm-invisible/stale/collision hazards
  recorded — and the upgrade verification gate spot-checks one native path
  per class rather than trusting docs.
- **The channel never rots silently again**: channel↔recipe drift is an
  ambient doctor finding (the 6.3.0 relic class), and the stale
  `bmad-method 6.3.0` itself is resolved (refresh-or-drop decided at spec
  time; conda-forge stays canonical for that one package either way).

## What is real

The isolated tools named above; the 2026-08-21/22 refresh as the worked
example of the full pipeline run by hand; doctor 14.1's env-vs-npm slice;
`provision --module bmb`; this week's current-versions state. No stage
connections, no schedule, no channel verification, no wiring beyond bmb/skf,
no dual-path contract.

## Constraints

- conda-forge stays canonical for `bmad-method`; the channel copy is
  refresh-or-drop, never a fork.
- Wiring is deliberate per-module triage (one-front-door's posture), never
  wire-everything: WDS is a skip (deprecated upstream, absorbing into
  bmad-ux); each addition to `_SUPPORTED_MODULES` carries its own
  verification (manifest recorded, no skill-name collisions, retired-ID
  guard + integrity meta tests green).
- Native-method commands come from upstream READMEs, recorded with the
  citation — never invented; the collision list travels with the matrix.
- Publishing stays credential-gated through steward's key discipline;
  publish-before-floor-bump ordering holds (the cheatsheet rule).
- Commit-pinned dev recipes keep the `X.Y.Z.dev0 @ <sha>` encoding and the
  version-of-record re-derivation rule (CFE G109).

## Non-goals

- Packaging anything new (autopilot/bmalph/dashboard-extension stay parked;
  the suite is the operator's 13).
- Submitting more suite packages to conda-forge (PrivateChannel is the home;
  bmad-method's feedstock is the one exception and stays upstream).
- The bmad-method core upgrade itself (steward Epic 14) and the era-retrofit
  chain (marshal Epic 25) — kin efforts this pipeline feeds and consumes.
- Auto-merge of autotick output — bumps land as reviewable PRs, git review
  decides (the factory's standing posture).

## Kinships

[[bmad-module-provisioning]] (realized; `_SUPPORTED_MODULES` is this Dream's
wiring seam) · [[bmad-suite-install-class-wiring]] (companion Dream: how
method/loop/skf/labs/dashboards/template get provisioned by install class —
not through `--module`) · [[bmad-method-version-drift]] (doctor; DW-14-1-1's
GitHub fallback + the new per-stage drift checks extend it) ·
[[bmad-method-core-upgrade]] (steward Epic 14; its CAP-4 pin fan-out and
CAP-5 gate consume this pipeline's output) · [[bmad-611-era-alignment]]
(marshal Epic 25; the era-alignment this pipeline keeps from regressing) ·
CFE skill (autotick machinery; Rule 1/2 govern the recipe-side stories).
