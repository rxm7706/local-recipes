# Cutover readiness — the BMAD-estate prerequisites python-foundry assumes

Companion of `spec-bmad-suite-lifecycle` (CAP-9). Derived 2026-09-06 from
`spec-python-foundry-cutover/SPEC.md` (constraints :123-163), the cutover spine
`fnd:AD-5 / AD-12 / AD-17 / AD-20`, Epic 44, `customization-inventory.md`, and the era-alignment
chain. The gate: every P line green before Story 44.3 opens the foundry. Owners act; steward reads.

## P — must be true in `local-recipes` before Phase 0

| # | Prerequisite | Source | State 2026-09-06 | Owner → story |
|---|---|---|---|---|
| P1 | Every Spec re-renders from its memlog without loss | Epic 44 Story 44.13; `fnd:AD-20` | not done (44.13 `backlog`; 127 SPEC.md, 128 memlogs) | steward 44.13 |
| P2 | `spec-pyforge-unifying-strategy`'s "never re-derive" exception retired, reconciled first | 44.13 AC-2; `AGENTS.md:22` | exception live | steward 44.13 |
| P3 | Every spine has a `.memlog.md` | `fnd:AD-20` | satisfied (11/11) | — |
| P4 | No hand-edited SPEC.md; memlog is the single writer | `AGENTS.md:22` | policy; enforced by 44.13 | steward 44.13 |
| P5 | Ledgers generated, feed repaired before any write | cutover SPEC :160-163 | in force | — |
| P6 | Physical-path writes with `BMAD_ACTIVE_PROJECT`; no parallel `bmad-switch` | cutover SPEC :160-162 | in force | — |
| P7 | No in-place edits of installer-owned files; customizations in `_bmad/custom/**` or CAP-8-re-applied | 44.5 AC; `fnd:AD-5`; inventory C1/C5 | **violated** — 2026-09-07 re-verified via live pre-flight (see Re-run note below): **9** files today, not the epic's 2026-09-06 assumption of 7 — C1 `_bmad/scripts/resolve_config.py` (`locally_modified`) plus **8** `local_customizations` skill files (C5 was 7, now 8; one more skill-file edit landed 2026-09-06→09-07) — CAP-8 re-applies them at every apply | steward (mechanism shipped, 14.8); marshal 31.4 governs them |
| P8 | Config pins sit at the installer's own key paths | inventory C2 | satisfied (99e595cc6a) | doctor 20.2 adds the render-HALT detector |
| P9 | skf provisioned by its own installer (class own-installer) | install-class playbook :21,62 | mixed (dual-installer by design; custom-module registration kept) | steward 46.7 (pin) |
| P10 | `_bmad/skf/config.yaml` hand-set keys survive an apply; `skf-export` accepts `skills/stations/<x>/` | inventory C7; `fnd:AD-5` | **2026-09-07 (Story 47.2):** both halves resolved. Keys-survive half: AD-12's declaring key is `_bmad/custom/config.toml [modules.skf].skills_output_folder` (confirmed present, still `.claude/skills` today); CAP-7's live mechanism, read at `upgrade.py::_restore_custom_module_configs`, is a pre-apply byte **snapshot/restore** of `_bmad/skf/config.yaml` itself (`path.write_bytes(before)`) — it never reads or derives from the config.toml key, so today's mechanism and the AD-12-target re-render are two independent files with no derivation link (a gap, not built). Export-root half: real headless `skf-export-skill` run in a scratch worktree confirms the root **does** accept `skills/stations/<x>/` (a flat-to-versioned migration lands `skills/stations/pyforge-herald/0.1.0/pyforge-herald/SKILL.md` for real) — see G5 for the full finding and the adjacent gap it surfaces | steward 47.2 (done) |
| P11 | No shims; harness = `bmad-build-auto` | inventory C9; era-alignment CAP-12 | **producer done, cell corrected 2026-09-08** — marshal `30-5-the-harness-and-every-live-caller-follow-the-shim-retirement` and steward `14-9-the-apply-retires-deprecation-shims-on-purpose-no-shims` both read `done` in their tracked ledgers; re-confirm the live shim count before the flip | marshal 30.5; steward 14.9 |
| P12 | No `project-context.md` rulebooks, readers migrated | inventory C13; era-alignment CAP-9 | **producer done, cell corrected 2026-09-08** — marshal `30-2-the-project-context-surface-follows-6-12-d1` reads `done` in its tracked ledger; re-confirm the live file/reader count before the flip | marshal 30.2 |
| P13 | Every in-place-edited installer file under a spec `surface:` | inventory §2 item 5 | 5 of 9 ungoverned on THIS branch's checkout, 2026-09-07 (not "5 of 7" — total pool grew to 9; re-derived, not assumed — see Re-run note below, which also flags a KNOWN staleness risk: an unmerged sibling branch already governs 3 of these 5): governed — `.claude/skills/bmad-build-auto/compile-epic-context.md` (`spec-marshal-token-economy`), `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md`, `.claude/skills/bmad-build-auto/step-04-review.md`, `.claude/skills/bmad-build-auto/spec-template.md` (all three `spec-marshal-single-story-dispatch`); ungoverned on this branch — `.claude/skills/bmad-brainstorming/assets/brain-methods.csv`, `.claude/skills/bmad-sprint-planning/references/generate-tracking.md`, `.claude/skills/bmad-sprint-planning/scripts/sprint_plan.py`, `.claude/skills/bmad-sprint-planning/scripts/tests/test_sprint_plan.py`, `_bmad/scripts/resolve_config.py` | marshal 31.4 |
| P14 | AGENTS.md block written only by `bmad-project-context` / `skf-export` | `fnd:AD-6`, `AD-17` | in force | — |
| P15 | `bmad-module-skill-forge uninstall` never run | inventory C20; AGENTS pitfall | recorded | — |
| P16 | No loop running at the flip; 8 homes re-provisioned attended | `fnd:AD-12`, `AD-17`; 44.12 | mechanism = 44.12 (not built); readiness undefined | marshal 31.5 defines; steward 44.12 builds |
| P17 | `gh` can create a private repo; paid plan persists | cutover SPEC :185-187 | assumption | steward 44.3 |
| P18 | Every register row with verdict `wield` is re-provisioned in foundry by its provisioning-path cell (the replay list): module class via `steward provision`, skf via its own installer, labs by name; nothing re-creates the installer-written dirs otherwise (`fnd:AD-5` keeps them real dirs but 44.11's link step generates only estate adapters) | adversarial review F-12 (2026-09-06); `fnd:AD-5`, `AD-12` | not defined until the register has a `wield` verdict per row (46.1) | steward 47.1 (checklist) + 44.5 (replay) |

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

## G — gaps the cutover texts assume but nothing tracked (relayed 2026-09-06)

| # | Gap | Evidence | Relay |
|---|---|---|---|
| G1 | `_bmad/**` missing from Epic 44 `[epic_surfaces]` (AD-12 moves it in 44.5; MRS-GATE-007 would fire) | `marshal-policy.toml` `"44"` | **RESOLVED 2026-09-07 (Story 47.3):** `"_bmad/**"` added to epic `"44"`'s `[epic_surfaces]` array in `marshal-policy.toml`; every other epic's array left byte-identical. | steward 47.3 (done) |
| G2 | Epic 44 has no dependency on Epic 14 (customization re-apply) or Epic 30 (era tail) | `epics.md` 44.x `Deps:` | **RESOLVED 2026-09-07 (Story 47.5):** 44.5's `Deps:` line gains `S-14.9` (same-station, Epic 14) and its new acceptance clause carries the trailing prose "after marshal 30.5 and 30.2" (Epic 30, AD-10 — cross-station producers are named in prose, never as a `Deps:` token); all three confirmed `done` live in their own projects' ledgers on this date. | steward 47.5 (done) |
| G3 | No story retired the shims or flipped the harness | inventory C9 | **RESOLVED 2026-09-07 (Story 47.5, relaying marshal 30.5 / steward 14.9):** both producers read `done` in their own projects' `sprint-status-ledger.yaml`, verified live — the shim retirement and the harness flip have landed; 44.5's new `Deps:` token and in-story acceptance clause relay this into Epic 44's own text. **Named finding, left open:** P11's own state cell above still reads "not done" (2026-09-06 snapshot) — correcting that cell is P11's own producer's job (marshal 30.5 / steward 14.9), out of this story's Surface line. | marshal 30.5 (done); steward 14.9 (done) |
| G4 | Rulebooks unclassified for the move (neither Dream, memlog, nor narrative) | AD-20 buckets | marshal 30.2 (they retire) |
| G5 | `skf-export` accepting `skills/stations/<x>/` asserted, never proven | `fnd:AD-5` | **RESOLVED 2026-09-07 (Story 47.2), with a new gap surfaced.** Real headless `skf-export-skill` run against a scratch worktree copy of this repo (config.yaml `skills_output_folder: skills/stations`, `snippet_skill_root_override` left at `.claude/skills/` per the story's own instruction): (1) an already-exported skill referenced by name at its OLD `.claude/skills/` location HALTS (exit 3, `resolution-failure`) the moment `skills_output_folder` changes — SKF's read-side resolution (manifest → active symlink → flat path) is scoped entirely to the CURRENT `skills_output_folder` value with no fallback to a prior location, so flipping the config key alone does not migrate or even discover already-exported packages; the on-disk tree must move (or be freshly forged) at the new root first — **new gap, not previously named anywhere in the cutover texts.** (2) Once the skill package was staged flat at the new root (exercising SKF's own documented flat-to-versioned auto-migration), a full real run completed successfully end to end: `skills/stations/pyforge-herald/0.1.0/pyforge-herald/SKILL.md` and `skills/stations/.export-manifest.json` both land exactly as the target layout assumes — the root-acceptance half of AD-5 **holds**. (3) The link-generation half is **confirmed empirically, not merely re-asserted**: `git diff --stat -- .claude/skills/` in the scratch worktree is byte-empty after the run — nothing under `.claude/skills/` was created, touched, or removed; no script under `_bmad/skf/shared/scripts/` performs any adapter/symlink generation. CLAUDE.md/AGENTS.md's managed sections gained only a timestamp bump (`updated:2026-08-26` → `2026-09-07`) — content otherwise byte-identical, and the `root:` pointer for the re-exported skill still reads `.claude/skills/pyforge-herald/` (the override was correctly left untouched, so nothing forced a rewrite) even though the package itself now lives at `skills/stations/pyforge-herald/…` — a live, concrete instance of the exact adapter gap AD-19 assumes away. **Net: SKF has no link-generation step of any kind; the `.claude/skills/` "generated per-machine links" this repo's own target-tree diagram assumes must be built new** (a link-generator, or an SKF feature) — filed as a finding in `spec-python-foundry-cutover`'s own memlog. | steward 47.2 (done) |
| G6 | 44.13's scope omits spine memlogs; only one `bmad-architecture` re-derive is exercised (44.14) | AD-20 vs 44.13 AC | **RESOLVED 2026-09-07 (Story 47.5):** 44.13's acceptance gains "and every spine's own `.memlog.md` re-distills through `bmad-architecture` without loss," recorded first as a cutover memlog `(note)` per the AC's own ordering requirement. | steward 47.5 (done) |
| G7 | render-HALT class (ambiguous config key kills every rendering skill) has no detector | inventory C2 | doctor 20.2 |
| G8 | `_bmad-output/PROJECTS.md` has no cutover-target layout (marker/junction vs `bmad-switch`) | `PROJECTS.md:36-46,68-85` | **RESOLVED 2026-09-07 (Story 47.3):** new "## Cutover target (foundry, AD-12)" subsection added after § Adding a new project, before § Reading another project's artifacts — § Config layering and § Adding a new project are no longer left silently un-cross-referenced with AD-12/AD-19. | steward 47.3 (done) |
| G9 | Foundry Stack table has no `bmad-*` floor row; win-64 excludes skf + eval-quality | cutover spine :249-260 | **RESOLVED 2026-09-07 (Story 47.4):** `ARCHITECTURE-SPINE.md` § Stack gains a 9th row, `bmad-* suite floor`, appended after `GitHub Actions`, transcribing the 2026-09-06 memlog decision verbatim: `bmad-method >=6.12.0, bmad-loop >=0.11.1, bmad-module-skill-forge >=2.1.0 (linux-64 only), bmad-creative-intelligence-suite, bmad-method-test-architecture-enterprise, bmad-eval-quality, bmad-utility-skills, bmad-builder` — win-64 (44.11) excludes skf and eval-quality; no AD id added or changed. | steward 47.4 (done) |
| G10 | Loop-home readiness undefined (`pyforge.toml name = "local-recipes"`, own `_bmad/`) | `fnd:AD-12`; `DW-CC-2026-09-04-1` | marshal 31.5 |
| G11 | `frozen-path-changed` detector named by AD-22/AD-11, never built | cutover spine :159,225 | doctor 20.3 |

## Re-derived by the cutover (never pre-build here)

Every rendered SPEC/spine/epic; `.claude/skills/` adapters (generated per machine); the
`bmad-switch` marker and the two planning symlinks; loop-home remotes; CLAUDE.md / AGENTS.md path
rewrites (`skf-export`); spec-surface baselines; `environment.yaml`.
