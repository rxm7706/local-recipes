---
title: The whole bmad-suite is wielded, kept current, and carried into the foundry
type: dream
owner: steward
status: specified
---

# The whole bmad-suite is wielded, kept current, and carried into the foundry

## The Dream

PyForge runs on the BMAD Method, but it wields only part of the suite it packages. Thirteen
SelfExplainML `bmad-suite` members are recipe-built, channel-published, pixi-pinned and
pipeline-truth-current; four of them (TEA, bmad-builder, utility-skills, manticore) have never been
provisioned, two are "documented" or "n/a" by class, one (eval-quality) is pinned with no runner,
and the ones that are wired carry a tail from the 6.12 era shift — twenty-one deprecated shims,
eight rulebooks nothing loads, ten CIS skills one revision behind, seven installer-owned skill files
edited in place, a harness policy that still names a shim.

The dream has three faces and one owner:

1. **Every suite tool has a wielder.** Each of the thirteen members has a recorded verdict — wield
   or skip — and, when wielded, a named station that reaches for it in its daily work: Herald renders
   station videos through manticore and writes release notes through `bmad-os-changelog`; Doctor
   reaches for `bmad-os-root-cause-analysis`; Warden runs `bmad-os-review-pr` and TEA's
   `tea-test-review` as advisory lenses; Scribe keeps docs through `bmad-os-diataxis`; Atlas builds
   MCP faces with `mcp-builder`; Marshal triages with `bmad-os-gh-triage`; Steward provisions all of
   it by install class and authors modules through bmad-builder beside skill-forge.
2. **The estate stays current per release, by a runbook not by heroics.** One cadence — Doctor
   detects the lag, Steward applies the core (`steward upgrade bmad-core`), Marshal runs the era
   round, Mason refreshes the suite recipes, Steward flips the statuses — and the prerelease channel
   is its optional dry-run.
3. **The BMAD estate is cutover-ready.** Before `python-foundry` opens, every prerequisite the
   cutover assumes about `_bmad/`, `.claude/skills/`, `_bmad-output/` and the loop homes is true and
   checked: no shims, no rulebooks, no ungoverned in-place edits, skf by its own installer, memlogs
   that re-render their Specs without loss.

## Grounding — verified state (2026-09-06 research pass)

**The suite, per `steward suite pipeline-truth` (13/13 recipe = channel = installed):**

| Member | Class | Wired today | Verdict (operator, 2026-09-06) |
|---|---|---|---|
| `bmad-method` 6.12.0 | installer-tree | present | Substrate. Only the era tail remains. |
| `bmad-loop` 0.11.1 | runner-home | provisionable | Marshal wraps it (never absorbs). |
| `bmad-module-skill-forge` 2.1.0 | own-installer (custom-module registration kept) | present, 16 skills | Every station; pin `v2.1.0` — npm 2.1.0 tarball `src/` is byte-identical to tag `v2.1.0` (337 files, verified this pass). |
| `bmad-creative-intelligence-suite` 0.3.2 | module | wired, one revision behind | Herald/Scribe. Re-provision (15 `--project-root` lines across 10 `SKILL.md`). |
| `bmad-eval-quality` 0.2.0.dev0 | cli | runnable, no runner | **Pilot unblocked**: the twin-run contract measures the reviewer (Story 45.2). |
| `bmad-method-test-architecture-enterprise` 1.24.0 | module | unwired | **Full adoption**: TEA's nine `bmad-testarch-*` workflows replace the repo generator; `tea-test-review` becomes a Marshal review lens and a Warden advisory. |
| `bmad-builder` 2.2.2 | module | unwired | **Provisioned beside skf** for agent/workflow authoring. Hazard: never `--legacy-dir`, never `cleanup-legacy.py`. |
| `bmad-utility-skills` 2.0.0 | module | unwired | **Adopted**: ten `bmad-os-*` skills routed to Herald, Doctor, Warden, Scribe, Marshal, Steward. |
| `bmad-manticore` 3.1.0.dev0 | module (`--custom-source`) | unwired | **Adopted for Herald** in a dedicated studio folder (its upgrade wipes the studio's `_bmad/` + `_bmad-output/`). |
| `bmad-labs-skills` 1.0.0.dev0 | plugin-path (consent) | documented | **Skill-by-skill**: `mcp-builder` → Atlas, `slides-generator` → Herald, `multi-repo-git-ops` → Marshal, `release-please` → Steward. Never the whole marketplace. |
| `bmad-module-template` 0.1.0 | scaffold | n/a | Catalog row (upstream LICENSE is placeholder text). |
| `bmad-dashboard` 1.2.2.dev0 | vscode-extension | runnable | Marshal's opt-in dev-machine surface; never the console. |
| `mybmad-dashboard` 0.1.0.dev0 | vscode-extension (a Next.js app) | runnable | Opt-in operator view only; never into the platform (its own Postgres and auth rival `/console/`). |

**The 6.12 era tail, verified at HEAD `35ddefbbc5`:** 21 deprecated shim dirs installed (20 in
`v6-shims/` plus `bmad-generate-project-context`, which 6.12 ships as `lifecycle: shim` under `plan/`
— not orphaned); `installShims: true`; marshal `harness_bmadloop.py:328` still names
`bmad-dev-auto` and all eight loop-home policies carry it; steward's apply has no `--no-shims`; the
retired-ID guard lacks `bmad-checkpoint-preview`; eight `project-context.md` rulebooks (976 lines)
survive with four live readers; `architecture-bmad-infra.md` is pinned to 6.11.0; steward's ledger
reads `backlog` for Stories 14.6–14.8 whose code is on main; `spec-bmad-suite-install-class-wiring`
and `spec-bmad-suite-metapackage` are shipped in fact but not in status.

**The open register:** 73 distinct open BMAD-METHOD items across the fleet (marshal Epic 30, the
core-upgrade Spec's five open questions, the steward customization inventory C9/C11/C13, 18 doctor
and 12 steward deferred-work entries on the drift detectors and the suite duty, the marshal
bmad-loop coupling entries, five horizon watches). The Spec's `open-items-register.md` partitions
them: story, deferred-work entry, or watch.

**The cutover's assumptions about this estate** (`spec-python-foundry-cutover`, spine `fnd:AD-5`,
`AD-12`, `AD-20`): the seed is Dreams plus memlogs only; every Spec, spine and epic is re-rendered in
foundry; adapters under `.claude/skills/` are generated, never copied; `_bmad/`, `_bmad-output/projects/`
and `docs/dreams/` move as one unit; the eight loop homes are re-provisioned by the flip with no loop
running. Seventeen prerequisites follow from that text; the live violations today are the shims,
the rulebooks, the seven in-place skill edits (five ungoverned by any spec surface), skf's
dual-installer state, and memlog fidelity (Story 44.13, `backlog`). Eleven gaps nothing tracks:
`_bmad/**` is missing from Epic 44's surface, Epic 44 has no dependency on the era work, the
foundry stack table has no `bmad-*` floor row, `PROJECTS.md` has no cutover layout, loop-home
readiness is undefined, and the `frozen-path-changed` and render-HALT detectors do not exist.

## Decisions locked (operator, 2026-09-06)

- **Shims go now**, not at v7: the era-alignment constraint that kept them (and the harness
  discriminator `bmad-dev-auto`) is retired by memlog; steward gains `--no-shims`; the same-version
  apply that drops them is the first live exercise of the core-upgrade CAP-6/7/8 path.
- **Adopt** utility-skills, manticore (Herald), labs-skills skill-by-skill, and unblock the
  eval-quality pilot. **BMB beside skf.** **TEA fully**, retiring `_bmad/scripts/bmad_tea_playwright.py`
  and its two meta-tests behind an equivalence check.
- **skf stays registered** as a bmad-method custom module (its `bmad-help` routing for fifteen skills
  is worth CAP-7's cost); the release catalog pins `v2.1.0`.
- **Full planning chain** (Spec → PRD → spine → epics) so the adoption epics can be drained by
  Marshal, one per station.
- **mybmad-dashboard** stays out of the platform.

## Whose job this is

Steward owns this Dream: provisioning by install class, the core apply, the suite pipeline and the
cutover chain are all its duties, and the adoption register is a steward companion. Every other
station wields, and the Spec relays one story per wielding station: Marshal (harness flip, TEA
replacing its generator, spec-surface widening, loop-home readiness), Doctor (suite drift 7→13,
the two missing detectors, `root-cause-analysis`), Warden (advisory lenses), Herald (manticore
studio, changelog, slides), Scribe (docs skills), Atlas (`mcp-builder`), Mason (the eval-quality
Windows variant recipe). The Charter's outcome/mechanism rule holds: the owner of the outcome
writes the story; the owner of the mechanism owns the verb it calls.

## What it looks like when real

**Adoption register (CAP-1).** One companion table, thirteen rows: verdict, wielding station,
provisioning path, hazards, status. It supersedes the channel-product Spec's "never wire-everything"
posture and closes the one-front-door row-6 triage. A member's wiring changes only by changing its row.

**Module wave (CAP-2).** `steward provision --module utility-skills`, `--module tea`, `--module bmb`
land their skills in `.claude/skills/` with manifest sections; CIS is re-provisioned; the retired-ID
guard and the integrity meta-tests stay green; nothing is hand-copied.

**Station routing (CAP-3).** Each adopted skill has exactly one wielding station, recorded in that
station's persona skill and the AGENTS.md managed block — never in CLAUDE.md.

**TEA (CAP-4).** Every station's `planning-artifacts/test-architecture.md` is produced by TEA's
workflows; `tea-test-review --base origin/main --min-score N` runs as a Marshal review lens and a
Warden advisory finding; the repo generator, its two meta-tests and its two pixi tasks are retired
only after an equivalence check shows the TEA output covers what the generator did.

**Manticore studio (CAP-5).** Herald's studio lives outside the repo's `_bmad/` root, provisioned
with `--custom-source`, configured in the studio's own `_bmad/custom/config.toml`; the first station
video renders from the deck's speaker notes; the `.mp4` is a gitignored build artifact.

**labs-skills (CAP-6).** Exactly the consented skills, installed by name, each with a register row.

**eval-quality pilot (CAP-7).** `evals/review-catches-planted-defect/` runs under
`eval-quality-smoke`, `eval-quality-review-twin-run` and `eval-quality-review-replay` with a
per-trial budget ceiling; never a PR gate.

**Release cadence (CAP-8).** One runbook: detect → apply → align → refresh → flip, with the
`@next` prerelease as an optional rehearsal (`6.12.1-next.0` is on npm today, unexercised).

**Cutover readiness (CAP-9).** One checklist with an owner per prerequisite; the gaps relayed to
the cutover chain by memlog; the gate is "every line green" before Story 44.3 opens the foundry.

**Shim retirement (CAP-10).** Harness → `bmad-build-auto`, eight homes re-rendered, callers glossed,
guard widened, one `--no-shims` apply, `installShims: false`.

## What is real

Everything above is planning as of 2026-09-06: the Spec, PRD, spine and epics minted in this
session, nothing provisioned, nothing retired. The 6.12 core is applied (PRs #1074, #1076); CAP-6..8
of the core-upgrade Spec are on main, unit-tested; the suite is 13/13 current on the channel.

## Constraints

- Provision by install class only — no hand copies into `.claude/skills/`, never `cleanup-legacy.py`,
  never `bmad-module-skill-forge uninstall` (it would delete every skill directory).
- The manticore studio is a separate root; its upgrade ritual never touches this repo's `_bmad/`.
- TEA and eval-quality verdicts are advisory (Warden) or lenses (Marshal review); Warden's gate stays
  the sole PR verdict.
- Customizations live in `_bmad/custom/**` or are re-applied by the core-upgrade CAP-8 path; every
  in-place edit of an installer-owned file is under a spec `surface:`.
- Retired-name sweeps gloss shipped history (decks, `docs/specs/`, `pixi.toml` comments) rather than
  rewriting it; live docs and code lead with the live names.
- Amended by this Dream (each by a memlog decision on the owning Spec): channel-product
  "never wire-everything" → "wire by adoption register"; era-alignment "shims stay through v7" and
  "TEA adoption is optional" → retired; one-front-door row-6 triage → closed.
- Parallel agents address projects by physical path with `BMAD_ACTIVE_PROJECT` per invocation; the
  ledgers change only through their tools.

## Non-goals

- First-install of bmad-method (Epic 14 upgrades an installed core; a fresh install is the foundry's).
- Refreshing suite conda recipes (the CFE factory flow, Mason).
- Integrating mybmad-dashboard into the platform, provisioning `bmad-module-template`, or installing
  the whole labs-skills marketplace.
- Upstream pull requests (skf `marketplace.json`, the sprint-plan key fix, the skf uninstall bug) —
  each needs an explicit ask.
- The cutover itself (Epic 44) — this Dream makes it possible, it does not perform it.

## Kinships

- [`bmad-method-core-upgrade.md`](bmad-method-core-upgrade.md), [`bmad-method-version-drift.md`](bmad-method-version-drift.md),
  [`bmad-611-era-alignment.md`](bmad-611-era-alignment.md) — the per-release triad this Dream's cadence
  runbook orders; shim retirement and `--no-shims` land as new capabilities on the first and third.
- [`bmad-suite-channel-product.md`](bmad-suite-channel-product.md), [`bmad-suite-install-class-wiring.md`](bmad-suite-install-class-wiring.md),
  [`bmad-suite-metapackage.md`](bmad-suite-metapackage.md), [`bmad-module-provisioning.md`](bmad-module-provisioning.md) —
  the packaging and provisioning machinery this Dream drives to completion.
- [`bmad-eval-quality.md`](bmad-eval-quality.md) — its CAP-2 pilot is unblocked here.
- [`pyforge-unifying-strategy.md`](pyforge-unifying-strategy.md) and the `python-foundry` cutover chain
  (`spec-python-foundry-cutover`, Epic 44) — the estate this Dream makes cutover-ready.
- [`one-front-door.md`](one-front-door.md) — its own/route/triage survey; row 6 closes here.
- [`herald-pitch.md`](herald-pitch.md) — the named manticore consumer.
- [`conda-forge-expert-rebuild.md`](conda-forge-expert-rebuild.md) — the skf-driven rebuild that the
  authoring path decision (BMB beside skf) must not disturb.

## Realization log

- **2026-09-06** — Seeded and specified in one session after a fleet-wide survey (seven listed items
  verified, 73 open items registered, thirteen members catalogued, seventeen cutover prerequisites
  derived). Operator decisions locked (see § Decisions). `bmad-spec` derived
  `spec-bmad-suite-lifecycle` under pyforge-steward (CAP-1..10, companions `adoption-register.md`,
  `release-cadence.md`, `cutover-readiness.md`, `open-items-register.md`; status `ready`), followed
  by the PRD, the epic-altitude spine, and hand-authored epics across eight stations (steward 46/47
  + Story 14.9, marshal 30.5 + Epic 31, doctor 20, warden 11, herald 18, scribe 7, atlas 24, mason 14).
  Implementation begins next session with the era tail (Epic 30, 14.9, 30.5, the `--no-shims` apply).
- **2026-09-07** — Story 47.1 re-ran the live `steward upgrade bmad-core --json`
  pre-flight against this repo's own state and corrected `cutover-readiness.md`'s
  P7/P13 rows: the P7 evidence pool grew from the epic's assumed seven files to a
  live **nine** (eight `local_customizations` + one `locally_modified`, one
  additional skill-file edit having landed 2026-09-06→09-07); P13's "5
  ungoverned" claim was independently re-derived against all nine and held
  exactly, even as the total pool grew — recorded as two separate, dated facts.
  Governing the five ungoverned files remains marshal Story 31.4's job.
