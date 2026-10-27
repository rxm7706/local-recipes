# Cutover readiness — the BMAD-estate prerequisites python-foundry assumes

Companion of `spec-bmad-suite-lifecycle` (CAP-9). Derived 2026-09-06 from
`spec-python-foundry-cutover/SPEC.md` (constraints :123-163), the cutover spine
`fnd:AD-5 / fnd:AD-12 / fnd:AD-17 / fnd:AD-20`, Epic 44, `customization-inventory.md`, and the era-alignment
chain. The gate: every P line green before Story 44.3 opens the foundry. Owners act; steward reads.

## P — must be true in `local-recipes` before Phase 0

| # | Prerequisite | Source | State (dated per cell; last full re-derivation 2026-09-09) | Owner → story |
|---|---|---|---|---|
| P1 | Every Spec re-renders from its memlog without loss | Epic 44 Story 44.13; `fnd:AD-20` | **partial (2026-09-10, Story 44.13 step-03).** Harness shipped: `pixi run -e local-recipes memlog-fidelity-check` inventories **132 specs + 8 spines**, zero missing memlogs; byte-equivalence re-derive not yet run fleet-wide (requires headless `bmad-spec`/`bmad-architecture` per artifact). Unifying strategy memlog reconciled first; remaining 131 specs + 8 spines await scratch re-derive batch. | steward 44.13 |
| P2 | `spec-pyforge-unifying-strategy`'s "never re-derive" exception retired, reconciled first | 44.13 AC-2; `AGENTS.md:19` | **satisfied (2026-09-10).** AGENTS.md exception removed; 2026-09-09 fleet-readiness hand-edits captured in `spec-pyforge-unifying-strategy/.memlog.md` (entries 128–134). Full `bmad-spec` byte-equivalence re-derive of live `SPEC.md` still pending harness batch. | steward 44.13 |
| P3 | Every spine has a `.memlog.md` | `fnd:AD-20` | **satisfied (2026-09-10, re-measured).** Eight station spines under `planning-artifacts/architecture/*/ARCHITECTURE-SPINE.md` each have a sibling `.memlog.md` (warden spine memlog present at `architecture-pyforge-warden-2026-07-14/.memlog.md`; the 2026-09-09 "8 of 9" figure is superseded). **Spine re-distill byte-equivalence** via `bmad-architecture` not yet run — same batch as P1. | steward 44.13 |
| P4 | No hand-edited SPEC.md; memlog is the single writer | `AGENTS.md:19` | **policy restored (2026-09-10).** No per-spec exceptions remain in AGENTS.md; fleet-wide enforcement awaits P1 scratch re-derive pass. | steward 44.13 |
| P5 | Ledgers generated, feed repaired before any write | cutover SPEC :160-163 | in force | — |
| P6 | Physical-path writes with `BMAD_ACTIVE_PROJECT`; no parallel `bmad-switch` | cutover SPEC :160-162 | in force | — |
| P7 | No in-place edits of installer-owned files; customizations in `_bmad/custom/**` or CAP-8-re-applied | 44.5 AC; `fnd:AD-5`; inventory C1/C5 | **violated** — re-derived **2026-09-09** against the now-applied **6.12.0** package (fleet readiness; the 2026-09-07 figure was measured against the 6.11.0 baseline and is not comparable): **pool = 11** — `local_customizations` **10** + `locally_modified` **1** (C1 `_bmad/scripts/resolve_config.py`, still byte-differing). CAP-8 re-applies them at every apply. Full membership and method in § *Re-run (P7 / P13, 2026-09-09)* below. | steward (mechanism shipped, 14.8); marshal 31.4 governs them |
| P8 | Config pins sit at the installer's own key paths | inventory C2 | satisfied (99e595cc6a) | doctor 20.2 adds the render-HALT detector |
| P9 | skf provisioned by its own installer (class own-installer) | install-class playbook :21,62 | mixed (dual-installer by design; custom-module registration kept) | steward 46.7 (pin) |
| P10 | `_bmad/skf/config.yaml` hand-set keys survive an apply; `skf-export` accepts `skills/stations/<x>/` | inventory C7; `fnd:AD-5` | **2026-09-07 (Story 47.2):** both halves resolved. Keys-survive half: fnd:AD-12's declaring key is `_bmad/custom/config.toml [modules.skf].skills_output_folder` (confirmed present, still `.claude/skills` today); CAP-7's live mechanism, read at `upgrade.py::_restore_custom_module_configs`, is a pre-apply byte **snapshot/restore** of `_bmad/skf/config.yaml` itself (`path.write_bytes(before)`) — it never reads or derives from the config.toml key, so today's mechanism and the fnd:AD-12-target re-render are two independent files with no derivation link (a gap, not built). Export-root half: real headless `skf-export-skill` run in a scratch worktree confirms the root **does** accept `skills/stations/<x>/` (a flat-to-versioned migration lands `skills/stations/pyforge-herald/0.1.0/pyforge-herald/SKILL.md` for real) — see G5 for the full finding and the adjacent gap it surfaces | steward 47.2 (done) |
| P11 | No shims; harness = `bmad-build-auto` | inventory C9; era-alignment CAP-12 | **producer done, cell corrected 2026-09-08** — marshal `30-5-the-harness-and-every-live-caller-follow-the-shim-retirement` and steward `14-9-the-apply-retires-deprecation-shims-on-purpose-no-shims` both read `done` in their tracked ledgers; re-confirm the live shim count before the flip. **Re-confirmed green live 2026-09-09 (fleet readiness):** none of the ten shim skill dirs exists (`bmad-dev-auto`, `bmad-quick-dev`, `bmad-create-story`, `bmad-dev-story`, `bmad-create-prd`, `bmad-create-architecture`, `bmad-check-implementation-readiness`, `bmad-document-project`, `bmad-generate-project-context`, `bmad-index-docs`); `_bmad/{core,bmm}/v6-shims/` contain only `README.md`; `.claude/skills/bmad-build-auto/` is present as the harness. | marshal 30.5; steward 14.9 |
| P12 | No `project-context.md` rulebooks, readers migrated | inventory C13; era-alignment CAP-9 | **producer done, cell corrected 2026-09-08** — marshal `30-2-the-project-context-surface-follows-6-12-d1` reads `done` in its tracked ledger; re-confirm the live file/reader count before the flip. **Re-confirmed green live 2026-09-09 (fleet readiness):** zero tracked `project-context.md` anywhere (`git ls-files | grep project-context.md` is empty); the only hits are inside vendored `build_artifacts/` source. | marshal 30.2 |
| P13 | Every in-place-edited installer file under a spec `surface:` | inventory §2 item 5 | **4 of 11 ungoverned, re-derived 2026-09-09** (fleet readiness; supersedes the 2026-09-07 "5 of 9" snapshot and closes its Known-staleness-risk note — the unmerged sibling branch landed). Governed (7): the four `.claude/skills/bmad-build-auto/` files (`compile-epic-context.md` → `spec-marshal-token-economy`; `spec-template.md`, `step-01-clarify-and-route.md`, `step-04-review.md` → `spec-marshal-single-story-dispatch`) plus the three sprint-planning files (`references/generate-tracking.md`, `scripts/sprint_plan.py`, `scripts/tests/test_sprint_plan.py` → `spec-marshal-single-story-dispatch`). Ungoverned (4) and **three of them named nowhere in any cutover text before this pass** — see the table in § *Re-run (P7 / P13, 2026-09-09)*. `brain-methods.csv` **left** the pool (now byte-identical to the 6.12.0 package copy). | marshal 31.4 |
| P14 | AGENTS.md block written only by `bmad-project-context` / `skf-export` | `fnd:AD-6`, `fnd:AD-17` | in force | — |
| P15 | `bmad-module-skill-forge uninstall` never run | inventory C20; AGENTS pitfall | recorded | — |
| P16 | No loop running at the flip; 8 homes re-provisioned attended | `fnd:AD-12`, `fnd:AD-17`; 44.12 | mechanism = 44.12 (not built); readiness **still undefined, correctly** (re-confirmed 2026-09-09: marshal 31.5 `backlog`, steward 44.12 `blocked`) | marshal 31.5 defines; steward 44.12 builds |
| P17 | `gh` can create a private repo; paid plan persists | cutover SPEC :185-187 | assumption | steward 44.3 |
| P18 | Every register row with verdict `wield` is re-provisioned in foundry by its provisioning-path cell (the replay list): module class via `steward provision`, skf via its own installer, labs by name; nothing re-creates the installer-written dirs otherwise (`fnd:AD-5` keeps them real dirs but 44.11's link step generates only estate adapters) | adversarial review F-12 (2026-09-06); `fnd:AD-5`, `fnd:AD-12` | not defined until the register has a `wield` verdict per row (46.1) | steward 47.1 (checklist) + 44.5 (replay) |

## Re-run (P7 / P13, 2026-09-07)

Live, report-only re-verification of P7/P13 (`git status --short` identical
before and after):

    pyforge steward upgrade bmad-core --target 6.12.0 --json

(review finding: an earlier draft of this command hardcoded
`--package-root ~/.cache/rattler/cache/pkgs/bmad-method-6.12.0-h98f672e_0/...`
— a machine- and build-specific hash (`h98f672e_0`) that would not resolve
on a different machine or after a rebuild, undermining the "so every later
pass is mechanical" goal. Confirmed live: `--package-root` is not needed
for the P7 finding at all — only `--installed-package-root` drives
`local_customizations`/`locally_modified`, and `upgrade.py`'s own
`default_installed_package_root` best-effort-globs
`~/.cache/rattler/cache/pkgs/bmad-method-<installed>-*/lib/node_modules/bmad-method`
whenever that flag is unset too — so the bare command above, with NEITHER
path flag, reproduces the identical 9-file result. Pass `--installed-
package-root <dir>` explicitly only if more than one `bmad-method-*`
version is ever cached at once and the auto-glob picks the wrong one.)

Found: `local_customizations` 8 + `locally_modified` 1 = **9** files (up
from the epic's 2026-09-06 assumption of 7 — one additional skill-file
edit landed 2026-09-06→09-07). Cross-referenced against every `surface:`
field in every project's every `SPEC.md` on THIS branch's checkout
(full-repo grep, not scoped to one project): 4 governed, 5 ungoverned —
the ungoverned count matches P13's pre-existing "5 ungoverned" claim
exactly even though the total pool grew from 7 to 9.

**Known staleness risk (review finding, not resolved here):** this "5
ungoverned" figure is a snapshot of THIS branch's own checkout, not a
fleet-wide fact — `bmad/adoption-readiness-2026-09-06-marshal-r1` (commit
`6ba6bd9eb6`, "Story 31.4," unmerged as of this pass) already adds
`generate-tracking.md`, `sprint_plan.py`, and `test_sprint_plan.py` to
`spec-marshal-single-story-dispatch`'s `surface:` list — 3 of the 5 files
this row lists as ungoverned. Once that branch merges, a re-run of this
same command will correctly report **2 of 9** ungoverned
(`brain-methods.csv`, `resolve_config.py`), not 5 — this row's count is
therefore due for re-verification at that point, not a settled number.
Governing the ungoverned files remains marshal Story 31.4's job either
way; this note exists so a later reader isn't misled into treating "5"
as more durable than it is.

## Re-run (P7 / P13, 2026-09-09 — fleet readiness pass)

Re-derived against the **now-applied 6.12.0** package. The 2026-09-07 figures above were
measured against the 6.11.0 baseline, so the two are not comparable — this is a new baseline,
not a delta.

| | 2026-09-07 (6.11 baseline) | **2026-09-09 (6.12 baseline)** |
|---|---|---|
| `local_customizations` | 8 | **10** |
| `locally_modified` (C1 `resolve_config.py`) | 1 | **1** (still byte-differs) |
| **total pool** | 9 | **11** |

The ten `local_customizations`: `.claude/skills/bmad-build-auto/{compile-epic-context.md,
spec-template.md, step-01-clarify-and-route.md, step-04-review.md}`,
`.claude/skills/bmad-retrospective/scripts/{sprint_status.py, tests/test_sprint_status.py}`,
`.claude/skills/bmad-sprint-planning/{references/generate-tracking.md, scripts/sprint_plan.py,
scripts/tests/test_sprint_plan.py, sprint-status-template.yaml}`.
`.claude/skills/bmad-brainstorming/assets/brain-methods.csv` **left** the pool (now byte-identical
to the 6.12.0 package copy). `_bmad/scripts/resolve_config.py` and `resolve_customization.py` are
now in the 6.12.0 catalog's `upstream_touched_paths`, so they are excluded from the customization
scan; `resolve_config.py` still differs and stays the C1 `locally_modified` finding.

**P13 — 4 of 11 ungoverned.** The 2026-09-07 row's own predicted merge landed
(`generate-tracking.md`, `sprint_plan.py`, `test_sprint_plan.py` are now governed by
`spec-marshal-single-story-dispatch`), `brain-methods.csv` left the pool, and **three files never
named anywhere entered it**:

| ungoverned today | why it is a real edit |
|---|---|
| `.claude/skills/bmad-retrospective/scripts/sprint_status.py` | `f2dccab2b9` "give sprint_status.py's YAML factory sprint_plan.py's width fix" |
| `.claude/skills/bmad-retrospective/scripts/tests/test_sprint_status.py` | same commit |
| `.claude/skills/bmad-sprint-planning/sprint-status-template.yaml` | `f527e526f0` "sprint_plan.py erased the operator's `blocked` gate; restore steward Epic 44" |
| `_bmad/scripts/resolve_config.py` | C1, `locally_modified` |

The template file is the one carrying the fix that protects **Epic 44's own `blocked` rows** — so
the guard on the operator gate is itself an ungoverned in-place edit that CAP-8 must three-way-merge
at every apply. Governing all four remains marshal Story **31.4**'s job (`backlog`).

**Method.** Byte-diff of every installed manifest skill dir plus `_bmad/scripts/*.py` against
`~/.cache/rattler/cache/pkgs/bmad-method-6.12.0-*/lib/node_modules/bmad-method`, reproducing
`upgrade.py::_skill_customization_findings` / `_scripts_customization_findings` exactly — the
pre-flight CLI itself was blocked by the analysing session's sandbox, so it was replicated
read-only. Governance cross-referenced against every `surface:` field in every project's every
`SPEC.md` on this checkout (full-repo grep, not scoped to one project).

Source: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`
(Class B row stA, § C5).

## G — gaps the cutover texts assume but nothing tracked (relayed 2026-09-06)

| # | Gap | Evidence | Relay |
|---|---|---|---|
| G1 | `_bmad/**` missing from Epic 44 `[epic_surfaces]` (fnd:AD-12 moves it in 44.5; MRS-GATE-007 would fire) | `marshal-policy.toml` `"44"` | **RESOLVED 2026-09-07 (Story 47.3):** `"_bmad/**"` added to epic `"44"`'s `[epic_surfaces]` array in `marshal-policy.toml`; every other epic's array left byte-identical. | steward 47.3 (done) |
| G2 | Epic 44 has no dependency on Epic 14 (customization re-apply) or Epic 30 (era tail) | `epics.md` 44.x `Deps:` | **RESOLVED 2026-09-07 (Story 47.5):** 44.5's `Deps:` line gains `S-14.9` (same-station, Epic 14) and its new acceptance clause carries the trailing prose "after marshal 30.5 and 30.2" (Epic 30, fnd:AD-10 — cross-station producers are named in prose, never as a `Deps:` token); all three confirmed `done` live in their own projects' ledgers on this date. | steward 47.5 (done) |
| G3 | No story retired the shims or flipped the harness | inventory C9 | **RESOLVED 2026-09-07 (Story 47.5, relaying marshal 30.5 / steward 14.9):** both producers read `done` in their own projects' `sprint-status-ledger.yaml`, verified live — the shim retirement and the harness flip have landed; 44.5's new `Deps:` token and in-story acceptance clause relay this into Epic 44's own text. **Named finding, left open:** P11's own state cell above still reads "not done" (2026-09-06 snapshot) — correcting that cell is P11's own producer's job (marshal 30.5 / steward 14.9), out of this story's Surface line. | marshal 30.5 (done); steward 14.9 (done) |
| G4 | Rulebooks unclassified for the move (neither Dream, memlog, nor narrative) | fnd:AD-20 buckets | **RESOLVED — producer done (marked 2026-09-09, fleet readiness):** marshal Story 30.2 reads `done` in its own tracked ledger; the rulebooks retire rather than being classified. | marshal 30.2 (done) |
| G5 | `skf-export` accepting `skills/stations/<x>/` asserted, never proven | `fnd:AD-5` | **RESOLVED 2026-09-07 (Story 47.2), with a new gap surfaced.** Real headless `skf-export-skill` run against a scratch worktree copy of this repo (config.yaml `skills_output_folder: skills/stations`, `snippet_skill_root_override` left at `.claude/skills/` per the story's own instruction): (1) an already-exported skill referenced by name at its OLD `.claude/skills/` location HALTS (exit 3, `resolution-failure`) the moment `skills_output_folder` changes — SKF's read-side resolution (manifest → active symlink → flat path) is scoped entirely to the CURRENT `skills_output_folder` value with no fallback to a prior location, so flipping the config key alone does not migrate or even discover already-exported packages; the on-disk tree must move (or be freshly forged) at the new root first — **new gap, not previously named anywhere in the cutover texts.** (2) Once the skill package was staged flat at the new root (exercising SKF's own documented flat-to-versioned auto-migration), a full real run completed successfully end to end: `skills/stations/pyforge-herald/0.1.0/pyforge-herald/SKILL.md` and `skills/stations/.export-manifest.json` both land exactly as the target layout assumes — the root-acceptance half of AD-5 **holds**. (3) The link-generation half is **confirmed empirically, not merely re-asserted**: `git diff --stat -- .claude/skills/` in the scratch worktree is byte-empty after the run — nothing under `.claude/skills/` was created, touched, or removed; no script under `_bmad/skf/shared/scripts/` performs any adapter/symlink generation. CLAUDE.md/AGENTS.md's managed sections gained only a timestamp bump (`updated:2026-08-26` → `2026-09-07`) — content otherwise byte-identical, and the `root:` pointer for the re-exported skill still reads `.claude/skills/pyforge-herald/` (the override was correctly left untouched, so nothing forced a rewrite) even though the package itself now lives at `skills/stations/pyforge-herald/…` — a live, concrete instance of the exact adapter gap fnd:AD-19 assumes away. **Net: SKF has no link-generation step of any kind; the `.claude/skills/` "generated per-machine links" this repo's own target-tree diagram assumes must be built new** (a link-generator, or an SKF feature) — filed as a finding in `spec-python-foundry-cutover`'s own memlog. | steward 47.2 (done) |
| G6 | 44.13's scope omits spine memlogs; only one `bmad-architecture` re-derive is exercised (44.14) | fnd:AD-20 vs 44.13 AC | **RESOLVED 2026-09-07 (Story 47.5):** 44.13's acceptance gains "and every spine's own `.memlog.md` re-distills through `bmad-architecture` without loss," recorded first as a cutover memlog `(note)` per the AC's own ordering requirement. | steward 47.5 (done) |
| G7 | render-HALT class (ambiguous config key kills every rendering skill) has no detector | inventory C2 | **RESOLVED — producer done (marked 2026-09-09, fleet readiness):** doctor Story 20.2 reads `done`; the render-HALT detector exists. | doctor 20.2 (done) |
| G8 | `_bmad-output/PROJECTS.md` has no cutover-target layout (marker/junction vs `bmad-switch`) | `PROJECTS.md:36-46,68-85` | **RESOLVED 2026-09-07 (Story 47.3):** new "## Cutover target (foundry, fnd:AD-12)" subsection added after § Adding a new project, before § Reading another project's artifacts — § Config layering and § Adding a new project are no longer left silently un-cross-referenced with fnd:AD-12/fnd:AD-19. | steward 47.3 (done) |
| G9 | Foundry Stack table has no `bmad-*` floor row; win-64 excludes skf + eval-quality | cutover spine :249-260 | **RESOLVED 2026-09-07 (Story 47.4):** `ARCHITECTURE-SPINE.md` § Stack gains a 9th row, `bmad-* suite floor`, appended after `GitHub Actions`, transcribing the 2026-09-06 memlog decision verbatim: `bmad-method >=6.12.0, bmad-loop >=0.11.1, bmad-module-skill-forge >=2.1.0 (linux-64 only), bmad-creative-intelligence-suite, bmad-method-test-architecture-enterprise, bmad-eval-quality, bmad-utility-skills, bmad-builder` — win-64 (44.11) excludes skf and eval-quality; no AD id added or changed. | steward 47.4 (done) |
| G10 | Loop-home readiness undefined (`pyforge.toml name = "local-recipes"`, own `_bmad/`) | `fnd:AD-12`; `DW-CC-2026-09-04-1` | **Still open (re-confirmed 2026-09-09):** marshal 31.5 is `backlog`. With G4/G7/G11 resolved this is the only open G row. | marshal 31.5 |
| G11 | `frozen-path-changed` detector named by fnd:AD-22/fnd:AD-11, never built | cutover spine :159,225 | **RESOLVED — producer done (marked 2026-09-09, fleet readiness):** doctor Story 20.3 reads `done`; `frozen_path.py` ships. | doctor 20.3 (done) |

## Re-derived by the cutover (never pre-build here)

Every rendered SPEC/spine/epic; `.claude/skills/` adapters (generated per machine); the
`bmad-switch` marker and the two planning symlinks; loop-home remotes; CLAUDE.md / AGENTS.md path
rewrites (`skf-export`); spec-surface baselines; `environment.yaml`.
