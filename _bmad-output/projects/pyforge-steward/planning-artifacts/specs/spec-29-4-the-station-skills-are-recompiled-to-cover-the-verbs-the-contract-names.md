---
title: "29.4: The station skills are recompiled to cover the verbs the contract names"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md
  - .claude/skills/pyforge-marshal/skill-brief.yaml
  - .claude/skills/pyforge-steward/skill-brief.yaml
  - .claude/skills/pyforge-scribe/skill-brief.yaml
  - .claude/skills/pyforge-atlas/skill-brief.yaml
  - .claude/skills/skf-update-skill/SKILL.md
  - .claude/skills/skf-export-skill/SKILL.md
  - AGENTS.md
---

<intent-contract>

## Intent

**Problem:** AGENTS.md makes each station's `SKILL.md` the grammar reference ("read `.claude/skills/pyforge-<station>/SKILL.md` before touching" a station; "use the CLI grammar"), so a verb the skill omits reads as absent. The station skills Story 29.1 built are compiles of `865b95dc951`, and their `skill-brief.yaml` scopes list only the first CLI modules: marshal `cli/main.py`, `status.py`, `check.py`, `init.py`, `seed.py`; steward `cli.py`; scribe `capture.py`, `compile.py`, `recall.py`; atlas `mcp/tools.py`. So the skills miss commands AGENTS.md tells agents to run — marshal `factory dispatch`/`spin`, `context advisory`, `challenge`; steward `estate`, `ci`, `preflight`; scribe `catalog` (finding RUL-C3, cluster RUL-CL2). The atlas skill names `mcp/tools.py` functions (`run_pipeline`, `read_dataset`, …) as MCP tools instead of the tools `mcp/server.py` registers, and no skill says how to reach a station's `POST /stations/<s>/mcp` (finding RUL-D7, cluster RUL-CL13). The AGENTS.md SKF block's root path cannot point at each skill's `active/` root (`snippet_skill_root_override` gives one root for all), the skill half of RUL-CL1.

**Approach:** Widen each brief's `scope.include` to the modules that now carry the verbs, run `skf-update-skill` once per skill (MANUAL blocks preserved), then one `skf-export-skill` run, which regenerates the AGENTS.md SKF block and carries the snippet template, skill lines and atlas tool names of RUL-CL1, RUL-CL3 and RUL-CL13. Add a per-skill root pointer outside the SKF markers (or change the export layout). Each MANUAL block cites the station-MCP how-to the same PR writes as a doc. Re-check and close DW-FU-42-2-11 and DW-steward-75-1-2. One story, under done Epic 29 (Story 29.1 built these skills), and it runs last among the PR's code changes (operator ruling 2026-11-01).

*Amended 2026-11-01 (session owner's ruling on the first attempt's block report, option (b)):* `skf-update-skill` cannot run headless on this tree, so each skill is recompiled in place at `0.1.0` by SKF helpers and source read, and the AGENTS.md SKF block is rebuilt by the SKF managed-section helper; Boundaries names the method and its precedent.

Ledger key: `29-4-the-station-skills-are-recompiled-to-cover-the-verbs-the-contract-names`.
Type / Effort / Deps: fix / M / S-29.1.

### Living CAP citations

- **`spec-pyforge-unifying-strategy` CAP-15** — "Every station teaches an agent its own work"; it governs the station skill files (canopy:FR-37, canopy:AD-17, as Story 29.1). A fix: no new CAP, no FR, no AD moves.

## Acceptance Criteria

- **AC1 — Scopes widened.** `scope.include` gains: in `.claude/skills/pyforge-marshal/skill-brief.yaml`, `src/pyforge/marshal/cli/spin.py`, `src/pyforge/marshal/cli/dispatch.py` (where `factory dispatch` registers), `src/pyforge/marshal/cli/context.py` and `src/pyforge/marshal/cli/challenge.py`; in `.claude/skills/pyforge-steward/skill-brief.yaml`, `src/pyforge/steward/estate.py`, `src/pyforge/steward/ci.py` and `src/pyforge/steward/preflight_verify.py` (the duty modules `cli.py` resolves for `estate`, `ci` and `preflight`); in `.claude/skills/pyforge-scribe/skill-brief.yaml`, `src/pyforge/scribe/catalog.py`; in `.claude/skills/pyforge-atlas/skill-brief.yaml`, `src/pyforge/atlas/mcp/server.py`.
- **AC2 — Recompiled.** *(Amended 2026-11-01.)* Each skill is recompiled in place by SKF helpers and source read, once per skill, and each `.claude/skills/pyforge-<station>/0.1.0/pyforge-<station>/SKILL.md` (marshal, steward, scribe, atlas) lists the verbs AGENTS.md names for its station; every existing `[MANUAL:…]` block survives byte-identical (`skf-hash-content.py manual-verify` against the inventory taken before the compile), and the AC4 citation lands in a new `[MANUAL:station-mcp]` block; `provenance-map.json` pins the compile commit, the commit the tree is cut from (`03a7aff5d9`), with repo-root-relative `source_file` values.
- **AC3 — Atlas tools.** The atlas skill's Key API and its MCP section name the tools `mcp/server.py` registers (`run_<pipeline>_pipeline`, `read_atlas_dataset`, `list_atlas_pipelines`, `list_atlas_datasets`), not the `mcp/tools.py` function names.
- **AC4 — How to reach a station host.** Each station skill's MANUAL block cites the `docs/how-to/` page on reaching a station MCP endpoint (starting the host, authenticating, the request shape), which the same PR writes with its `docs/map.yaml` row.
- **AC5 — One export.** *(Amended 2026-11-01.)* One run of the SKF managed-section helper regenerates the AGENTS.md SKF block from the skills' `context-snippet.md` files (`skf-rebuild-managed-sections.py` `assemble`, then `replace`: the steps `skf-export-skill` runs at update-context §4b and §9), never a hand edit inside its markers; AGENTS.md carries a pointer to each skill's `active/` root outside the SKF markers, or the export layout changes so the block names it.
- **AC6 — DW closed.** DW-FU-42-2-11 (the steward skill card omits `revoke` and `restore`) and DW-steward-75-1-2 (the steward skill lists `keys` without `exec`) in `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` close after a re-check against the recompiled `SKILL.md`, or stay open with the reason named.
- **AC7 — Reconciled and green.** The `spec-pyforge-unifying-strategy` memlog carries the surface reconcile naming the recompiled `SKILL.md` paths, and the stamp is `--spec pyforge-steward/spec-pyforge-unifying-strategy`; chain-currency re-runs for steward; `pyforge-steward-test`, `governance-currency` and the instruction-surface parity test exit 0.

## Boundaries & Constraints

**Always:**
- *(Amended 2026-11-01, option (b) of the first attempt's block report, ruled by the session owner.)* Recompile in place at `0.1.0` by SKF helpers and source read, the way Story 29.1 and atlas Stories 33.1 and 33.2 did (the atlas `SKILL.md` Overview records that precedent): widen each `skill-brief.yaml` scope, read each station's source in that scope and its real `--help`, run the helpers that apply (`skf-extract-public-api.py`, `skf-hash-content.py` `manual-inventory` / `manual-verify`, `skf-validate-frontmatter.py`, `skf-validate-output.py`, `skf-count-tokens.py`), keep the `0.1.0` folder and the `active` symlink, and re-point each `provenance-map.json` `source_commit` to the commit the tree is cut from (`03a7aff5d9`) with repo-root-relative `source_file` values. Rebuild the AGENTS.md SKF block with `skf-rebuild-managed-sections.py` from the skills' snippets. Preserve every MANUAL block byte-identical. `skf-update-skill` is not run: headless it halts here (no forge tier, no forge-data provenance map), and an update writes a `0.1.1/` folder (Auto Run Result, first attempt).
- Run last among the PR's code changes, so the compile reads the final tree.

**Never:**
- Never edit compiled skill text except by the source-read recompile above, or AGENTS.md inside the SKF markers except through the SKF helper; never edit the `bmad:context` block; never touch `.claude/skills/conda-forge-expert/`; never run `bmad-module-skill-forge uninstall`; never add a second compiler.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-unifying-strategy` CAP-15.

Parent: `spec-pyforge-unifying-strategy` CAP-15

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry; the operator ruling of 2026-11-01 is the `(decision)` entry on `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md`.
- Epic: Epic 29 (done; Story 29.1 built these skills).
- Ledger key: `29-4-the-station-skills-are-recompiled-to-cover-the-verbs-the-contract-names`.
- Deps: S-29.1.
- Surface: `marshal-policy.toml` `[epic_surfaces]."29"` does not cover `.claude/skills/` or `AGENTS.md`; this story is hand-landed in the audit PR, not dispatched. Its files are the four `skill-brief.yaml` and four compiled `SKILL.md` paths of AC1 and AC2, `AGENTS.md`, and `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`.
- Audit: EGM audit 2026-11-01 findings RUL-C3 (cluster RUL-CL2) and RUL-D7 (cluster RUL-CL13), with the skill halves of RUL-CL1 and RUL-CL3 (findings RUL-Z5, RUL-D5 and RUL-C2 name this story as a co-carrier); residue `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md` (the rules stage).
- Minted 2026-11-01 by the EGM fleet audit landing (marshal Story 113.7); lands in that PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite, the SKF meta-tests included; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_skf_domain_skills.py src/shared/packages/pyforge-steward/tests/meta/test_skf_steward_skill.py src/shared/packages/pyforge-steward/tests/meta/test_five_tier_check.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-scribe pytest src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py -q` — expected: pass.
- `grep -n 'factory dispatch' .claude/skills/pyforge-marshal/0.1.0/pyforge-marshal/SKILL.md`, `grep -n 'estate' .claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md`, `grep -n 'catalog' .claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md`, `grep -n 'read_atlas_dataset' .claude/skills/pyforge-atlas/0.1.0/pyforge-atlas/SKILL.md` — expected: exit 0 each.
- `pixi run -e pyforge-guild governance-currency` — expected: exit 0.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `deferred-work-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

### Second attempt (2026-11-01, option (b): in place at 0.1.0)

Status: in-review. Each of the four skills is recompiled in place at `0.1.0` by SKF helpers and source read
(Boundaries, amended); the `0.1.0` folders and the `active` symlinks are unchanged.

- **AC1.** Each `skill-brief.yaml` `scope.include` gains the AC1 modules; `skf-validate-brief-schema.py` reads each
  brief valid.
- **AC2.** `skf-extract-public-api.py --mode quick` over each widened scope gave the exports; each `SKILL.md` lists
  the verbs read from the real `--help` (marshal `factory dispatch` / `spin` / `challenge`, `context advisory` /
  `retrieve` and every top-level verb; steward all 31 duties with `estate`, `ci`, `preflight`; scribe
  `catalog bmad-estate`; atlas the tools `mcp/server.py` registers). Quick Start lines run from the repository root
  under `-e pyforge-guild` (atlas under `-e pyforge-atlas`); the scribe `capture` / `recall` lines Story 19.4
  corrected are unchanged. `skf-hash-content.py manual-verify` against the inventory taken before the compile:
  `ok`, every existing `[MANUAL]` block preserved byte-identical in all four. Each `provenance-map.json` pins
  `source_commit` `03a7aff5d911e4c4b9a590fcd00dadc96f8e698c` with repo-root-relative `source_file` values, every
  `source_line` located from the tree; `skf-verify-provenance-completeness.py verify`: 0 stale citations (the old
  maps had 5 / 3 / 7 / 7), the orphans are the internal handlers the maps record by design. `metadata.json`
  (exports, stats, `source_commit`) and `context-snippet.md` follow. `skf-validate-frontmatter.py` and
  `skf-validate-output.py`: pass, 0 issues each (the marshal description is one quoted line now, which clears the
  validator's pre-existing low "unknown frontmatter field"; its text is unchanged, so `bmad-estate-check` stays
  green). Frontmatter descriptions are otherwise unchanged: they feed the BMAD-estate catalog digest.
- **AC3.** The atlas Key API and MCP section name `run_<pipeline>_pipeline` (all eight), `read_atlas_dataset`,
  `list_atlas_pipelines`, `list_atlas_datasets`, `query_vizro_ai`, `query_trending_candidates`, each cited to
  `mcp/server.py`; `mcp/tools.py` functions appear only as the implementations they delegate to. "Run from the
  repository root" replaces "or any directory".
- **AC4.** Each skill gains a `[MANUAL:station-mcp]` block citing `docs/how-to/reach-a-station-mcp-endpoint.md`.
- **AC5.** `skf-rebuild-managed-sections.py` `resolve-targets`, `check`, `assemble` (the four skills as
  `--include`, root override `.claude/skills/`, orphans kept: none found) and `replace` regenerated the AGENTS.md SKF
  block; only lines between its markers changed (the four stations' api / gotchas rows and the `updated:` date). The
  export manifest (`.claude/skills/.export-manifest.json`, step §9b) is not rewritten: it is outside this run's
  write set and already names every skill at `0.1.0`. The `active/` pointer outside the markers was in place.
- **AC6.** Re-checked against the recompiled steward `SKILL.md`: DW-FU-42-2-11 is satisfied (`revoke` and
  `restore` are listed as duties with their purpose and CLI lines) and DW-steward-75-1-2 is satisfied (`keys
  {…,revoke,exec}`). The ledger rows are not closed here: `deferred-work-ledger.md` is outside this run's write
  set, so the session owner closes both.
- **AC7.** Surface-reconcile events appended to `spec-pyforge-unifying-strategy` (all 20 changed
  `.claude/skills/pyforge-*` paths) and `spec-pyforge-scribe` (AGENTS.md, SKF block only); `spec-surface-check`
  exits 0 and names none of them. Not done here (the run may not): the scoped stamp `--spec
  pyforge-steward/spec-pyforge-unifying-strategy` and the chain-currency reconciler sweep
  (`chain-currency-sweep-check` exits 1 on all seven stations' staleness checkpoints, the whole PR's state).
  `governance-currency`, `bmad-drift-check`, `bmad-estate-check`, the scribe parity test, the steward SKF
  meta-tests, the scribe, mason and atlas skill meta-tests and the four Verification greps exit 0.
  `pyforge-steward-test` exits 1 on one test outside this story: `test_station_tests_trigger_map.py::
  test_every_read_and_declared_glob_fires_its_job` lists 8 paths read by other in-flight test edits (marshal
  `test_factory_challenge.py`, mason `test_mason_skills.py` / `test_persona_consults_cfe.py`, scribe
  `test_instruction_surface_parity.py` / `test_guild_env_membership.py`) that
  `.github/workflows/pyforge-station-tests.yml` does not route; 1743 others pass.

### First attempt

Status: blocked (2026-11-01, EGM audit fix pass). `skf-update-skill` (SKF 3.0.0, `_bmad/skf/VERSION`) cannot run
headless on this tree for the four skills, and where it can be made to run it writes a layout this spec and the
station meta-tests do not accept. Nothing from this story is left in the tree: no brief, `SKILL.md`, `AGENTS.md`,
memlog or deferred-work edit; only this status block changed.

**Blocking condition.** Five findings, each read from the SKF stage files and checked on this tree:

1. **No forge tier.** `{sidecar_path}` is the module default `_bmad/_memory/forger-sidecar/` (gitignored, absent from
   this worktree). init.md §3 (`.claude/skills/skf-update-skill/references/init.md:203`) halts `blocked` at
   `init:forge-tier` without `forge-tier.yaml`. The primary checkout's copy has `tier: ~` and preferences
   `tier_override: ~`, so `skf-setup` never finished there either.
2. **No provenance map where SKF reads it.** init.md §4 reads `{forge_data_folder}/<skill>/<version>/provenance-map.json`
   (`forge_data_folder` = `_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data`, which holds only
   `pyforge-mason/`). Headless, that halts `blocked` at `init:load-provenance-map` unless `--allow-degraded`, which
   init.md:235 reserves for an operator ("a policy call that belongs to an operator"). Seeding the forge folder from
   the package's own `provenance-map.json` does not help: its `source_file` values are repo-root relative
   (`src/shared/packages/pyforge-marshal/src/...`), and `skf-classify-changed-files.py classify` run on the marshal
   package with the AC1 scope (source root `src/shared/packages/pyforge-marshal`, tree status `skipped`) reported all
   5 tracked files `deleted` and all 11 in-scope files `added`.
3. **SKF reads another brief.** detect-changes.md:104 binds the brief to `{forge_data_folder}/<skill>/skill-brief.yaml`,
   not the tracked `.claude/skills/pyforge-<station>/skill-brief.yaml` that AC1 widens.
4. **Version folder.** merge.md:245-246: outside gap-driven mode (which needs an `skf-test-skill` report), an update
   writes a new `.claude/skills/pyforge-<station>/0.1.1/` beside an unchanged `0.1.0/` and moves `active` there.
   AC2 and this spec's Verification greps name `0.1.0/.../SKILL.md`, and
   `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py:189-190` pins the marshal and
   scribe `0.1.0` files, so after an update that test would go on reading the stale copies.
5. **Provenance lands outside the package and is never re-pinned.** write.md:233 writes the map to
   `{forge_data_folder}/<skill>/<new_version>/provenance-map.json` with source-root-relative paths. The package's
   `provenance-map.json` is carried into `0.1.1/` unchanged by merge.md:282, and the steward meta-tests read the
   package map and need repo-root-relative `source_file` (`test_skf_domain_skills.py:73-76`,
   `test_skf_steward_skill.py:66-69`). For a local source, write.md:191 leaves `source_commit` as it was
   (`865b95dc951`; scribe `a5e9dad59ab`), so AC2's "`provenance-map.json` pins the compile commit" cannot come from
   the run.

**Already true.** The AC5 pointer outside the SKF markers is in place: `AGENTS.md:39` names
`.claude/skills/pyforge-<station>/active/pyforge-<station>/SKILL.md` (commit `db3a81aede`). The AC4 how-to,
`docs/how-to/reach-a-station-mcp-endpoint.md`, has its `docs/map.yaml` row (line 117). DW-FU-42-2-11 and
DW-steward-75-1-2 stay open, because the recompile they wait on did not happen.

**To unblock (operator or session owner), choose one:**
- (a) Run SKF interactively in this worktree: `skf-setup` (writes the sidecar), then per skill copy the widened brief
  to `{forge_data_folder}/<skill>/skill-brief.yaml` and choose [D] at init §4. Accept `0.1.1/` and the `active` move,
  then amend AC2, this spec's Verification greps and the parity test's two pinned paths to `active/`. Also decide how
  the forge-data map reaches the package `provenance-map.json` in the repo-root-relative form the steward meta-tests
  read, and what "pins the compile commit" means for a `source_ref: local` skill.
- (b) Amend Boundaries to allow the recompile that Story 29.1 and atlas Stories 33.1 and 33.2 used: SKF helpers
  (`skf-extract-public-api.py`, the validators) plus a source-read compile in place at `0.1.0`, with
  `provenance-map.json` re-pointed and `[MANUAL]` blocks preserved byte-identical. The atlas `SKILL.md` Overview
  records that precedent.

Either way the export step (`skf-export-skill`, one run) follows the recompile and is not blocked by itself.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), clusters RUL-CL2 and RUL-CL13, under done Epic 29 per the operator ruling of the same date; in the audit landing PR.
- 2026-11-01: amended after the first attempt blocked, by the session owner's ruling on its option (b): the skills are recompiled in place at `0.1.0` by SKF helpers and source read (precedent: Story 29.1, atlas Stories 33.1 and 33.2) and the SKF block is rebuilt by `skf-rebuild-managed-sections.py`. Approach, AC2, AC5 and Boundaries reworded from `skf-update-skill` / `skf-export-skill` to that method; AC2 names the compile commit (`03a7aff5d9`) and puts the AC4 citation in a new `[MANUAL:station-mcp]` block, so every existing MANUAL block stays byte-identical. Status blocked → in-progress.

## Review Triage Log

### 2026-11-01 — Independent review (reviewer: independent session)

Verdict: **pass**. The status is set to `done`. AC1 to AC5 hold on evidence observed in this worktree. AC6 and
AC7 hold up to the steps that belong to the session owner, listed under *Landing conditions* below. I did not
write this change. I read `git diff HEAD` of the reported files against this spec as amended today, not against
the Auto Run Result.

During the review the session owner committed `f742908321` (the other fix stories' code). After that commit
the 29.4 files are the only reported paths that are still uncommitted, and the compile's line citations
resolve against that commit (see AC2).

What was checked (worktree `egm-audit-2026-11`, run from its root; every verdict read from `$?`, never through a
pipe):

- **AC1.** All four `skill-brief.yaml` diffs add exactly the AC1 modules, and each one exists. `cli.py`
  `resolve_duty` imports `EstateDuty` from `.estate`, `CiDuty` from `.ci` and `PreflightDuty` from
  `.preflight_verify` (`cli.py:1939-1953`). `skf-validate-brief-schema.py` reads each brief as valid (exit 0
  ×4, no errors or warnings).
- **AC2, verbs against the real `--help`.** All of these exit 0:
  - marshal under `-e pyforge-guild`: `marshal --help`, `factory`, `factory dispatch`, `factory spin`,
    `factory challenge`, `factory challenge resolve`, `context`, `context advisory`, `context retrieve`, `seed`.
  - steward under `-e pyforge-guild`: `steward --help`, `keys`, `keys exec`, `estate`, `estate plan`,
    `estate realize`, `ci`, `ci status`, `ci vars`, `ci pause`, `preflight`, `preflight verify-deferred`,
    `workspace`, `budget`, `pages`, `revoke`, `restore`.
  - scribe under `-e pyforge-guild`: `scribe --help`, `catalog`, `catalog bmad-estate`, `index`, `graph`,
    `recall`, `capture`.
  - atlas under `-e pyforge-atlas`: `pyforge atlas --help`, `--version`.

  Each skill's CLI section matches that output:
  - marshal: all 22 top-level verbs, the 9 `factory` verbs, the 6 `context` verbs and the 8 `seed` verbs.
    The flags of `dispatch`, `spin`, `challenge`, `challenge resolve`, `advisory` and `retrieve` match too.
  - steward: all 31 duties, in the order `steward --help` gives. The sub-verbs of `keys`, `estate`, `ci`,
    `preflight`, `workspace`, `budget` and `pages` and the flags of `revoke` and `restore` match.
  - scribe: `catalog bmad-estate` with `--write`, `--check`, `--root`, `--output` and `--pipeline-truth`, and
    its exit 2 when `--write` and `--check` are both given (`cli.py`).
  - atlas: `run`, `ipython`, `package`.

  These Quick Start lines run under `-e pyforge-guild`, each exit 0: `pyforge steward estate plan --help`,
  `pyforge steward workspace start --help`, `pyforge steward preflight verify-deferred --help`,
  `marshal factory dispatch --help` and `scribe catalog bmad-estate --check`.

  Every verb AGENTS.md names for these stations appears in its skill. These are `factory dispatch` / `spin`,
  `context advisory`, `scribe capture` / `recall` / `graph compile` / `catalog bmad-estate`,
  `steward estate reconcile` / `plan --due`, `ci status`, `preflight verify-deferred`,
  `workspace start` / `status` / `clean`, and `setup`. The four Verification greps exit 0.
- **AC2, `[MANUAL]` blocks.** Each SKILL.md at HEAD went through `skf-hash-content.py manual-inventory`, and
  each working-tree file through `manual-verify` against that inventory. All four report `ok: true`, with
  `additional-notes` and `api-notes` preserved and nothing modified, missing or moved. A regex byte compare of
  each block gives the same result. The one new block in each skill is `[MANUAL:station-mcp]`.
- **AC2, frontmatter.** `skf-validate-frontmatter.py` passes for all four (exit 0, 0 issues).
  `skf-validate-output.py` passes for all four (exit 0, 0 issues). The steward, scribe and atlas descriptions are
  unchanged. The marshal description parses to the same text, without the trailing newline that YAML folding
  added. `bmad-estate-check` exits 0. The `active` link still resolves to `0.1.0` for all four, there is no
  `0.1.1/`, and `.claude/skills/.export-manifest.json` has no diff.
- **AC2, provenance.** All four `provenance-map.json` files parse. Each pins `source_commit`
  `03a7aff5d911e4c4b9a590fcd00dadc96f8e698c`, and every `source_file` is repo-root relative (`src/shared/...`).
  - All 51 entries name a file that exists. On the export's own line, each holds the export's name in the
    working tree and at `f742908321`.
  - `skf-verify-provenance-completeness.py verify --source-root . --skill-dir <pkg>` finds 0 stale, 0 missing
    and 0 citation findings in all four. Run on the HEAD maps, the same check finds 5, 3, 7 and 7 stale. The
    orphans are the handlers and types that the maps record and `metadata.json` `exports` leaves out: 13, 6, 7
    and 2.
  - Every `[SRC:path:Lx-Ly]` citation in the four SKILL.md files resolves to an existing file and an in-range
    line (139 citations). The only other match is the atlas Overview's literal `[SRC:…]` placeholder.
  - I spot-read 25 marshal and steward citation lines. Each lands on the definition it names.
- **AC3.** `mcp/server.py` registers the eight `run_<pipeline>_pipeline` tools, `read_atlas_dataset`,
  `list_atlas_pipelines`, `list_atlas_datasets`, `query_vizro_ai` and `query_trending_candidates`
  (`server.py:55-124`). The atlas Key API table, the MCP paragraph, `metadata.json` `exports` and the snippet
  `api:` line name these tools. They name the `mcp/tools.py` functions only as the implementations the tools
  call.
- **AC4.** `docs/how-to/reach-a-station-mcp-endpoint.md` exists and has its `docs/map.yaml` row (line 117). It
  covers starting the host, the assertion and the request shape. Each skill's `[MANUAL:station-mcp]` block
  cites it, once.
- **AC5.** In the AGENTS.md diff, every change sits between `<!-- SKF:BEGIN` (line 473) and `<!-- SKF:END -->`
  (line 533): the marker date and the four stations' `api:` / `gotchas:` rows. The `bmad:context` block and
  every other line are untouched.

  `skf-rebuild-managed-sections.py assemble` (the four skills as `--include`, root override
  `.claude/skills/`, `--orphans keep`) rebuilds the block from the snippets. Its output equals the live block
  (`read`) after whitespace is stripped. `check` reports `markers_valid: true`. The per-skill `active/` pointer
  outside the markers is `AGENTS.md:39`.
- **AC6, re-check.** Both rows are satisfied by the recompiled steward SKILL.md:
  - DW-FU-42-2-11: the duty table lists `restore` and `revoke`, and the CLI block carries
    `steward restore --drill --backup-path PATH` (line 236) and `steward revoke --sub ID` (line 237).
  - DW-steward-75-1-2: the grammar reads `steward keys {encrypt,decrypt,rotate,list,audit,revoke,exec}`
    (line 226), and the Keys paragraph describes `exec`.
  - Both rows are still `status: open` in the ledger. The reason is named in the Auto Run Result (the ledger
    is outside the run's write set).
- **AC7.**
  - The surface-reconcile events are in place on `spec-pyforge-unifying-strategy` (all 20 `.claude/skills/`
    paths) and on `spec-pyforge-scribe` (AGENTS.md, SKF block only).
  - Exit 0: `spec-surface-check`. Its drift-presumed WARNs name other stories' `src/platform` and
    `django-warden` paths, never a 29.4 path.
  - Exit 0: `governance-currency`, `bmad-drift-check` (two `surface-changed` WARNs, CFE skill version and
    gotcha count), `bmad-estate-check`, `chain-completeness-check`, `story-status-check`, `deferred-work-check`.
  - Exit 0: the scribe meta-tests (`-e pyforge-scribe`, 85 passed, 1 skipped, including
    `test_instruction_surface_parity.py`) and the steward SKF meta-tests (`test_skf_domain_skills.py`,
    `test_skf_steward_skill.py`, `test_five_tier_check.py`: 23 passed).

Not counted against this story (as in the 118.6 review):

- `pixi run --frozen -e pyforge-steward pyforge-steward-test` exits 1: 5 failed, 1739 passed, 2 skipped. All 5
  are in `tests/meta/test_station_tests_trigger_map.py`.
  - The findings name test reads that `.github/workflows/pyforge-station-tests.yml` does not route. Marshal:
    `test_factory_challenge.py`. Mason: `test_mason_skills.py`, `test_persona_consults_cfe.py`. Scribe:
    `test_instruction_surface_parity.py`, `test_guild_env_membership.py`. Steward 118.6:
    `tests/integration/nkp_probes.py`, `tests/integration/conftest.py`, the latter not in
    `ROOT_HANDOFF_INPUTS`.
  - The findings also include a warden `ROOT_HANDOFF_INPUTS` line.
  - None of them names a 29.4 path.
- The mason meta-tests (`-e pyforge-mason`) exit 1: 1 failed, 448 passed. `test_skf_mason_skill.py` and
  `test_mason_skills.py` pass.
  - The failure is `test_persona_consults_cfe.py::test_does_not_mint_01_portal_mcp_or_persona`. It names
    `f742908321`, a single commit that edits both mason source and `src/platform`
    (`warden-fabric-0004` changelog, `sqlmigrate-map.yaml`, four platform tests).
  - The check reads commits only, and the 29.4 files are uncommitted. This red comes from how the session's
    commit is cut. The session owner has to clear it before the push, for example by carrying the platform
    files in a commit with no mason source.
- The scoped stamp and the chain-currency re-run are the session owner's steps. This run may not run
  `--write-baseline`.

Observations (no change required by this spec):

- **The pinned commit and the line citations disagree on 7 entries.** AC2 pins `03a7aff5d9`. The compile read
  the final tree, so 7 of the 51 provenance `source_line`s, and the SKILL.md citations that match them, fit
  `f742908321` and the working tree but not `03a7aff5d9`:
  - marshal `run_status`, `run_dispatch`, `add_factory_challenge_subparser` and `run_challenge`;
  - scribe `derive`, `write` and `check` in `catalog.py`.

  This follows from the spec's own choice of commit, not from a defect in the compile. If a later round
  (marshal 113.8 or 113.10-113.13) changes a module in the four scopes, re-point the citations. Before landing,
  re-run `skf-verify-provenance-completeness.py verify`; it must still find 0 stale.
- **DW-steward-75-1-2 evidence goes further than its summary.** The evidence also cites the `--approval`
  contract and the exit codes of `keys exec`. The skill names neither and defers to
  `steward <duty> --help`. The row's summary, and AC6's reading of it, are met.

Landing conditions (the session owner's):

1. Close DW-FU-42-2-11 and DW-steward-75-1-2 in
   `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`, each with a `verified:`
   line citing the steward SKILL.md lines above.
2. Run the scoped stamp `--spec pyforge-steward/spec-pyforge-unifying-strategy`, and the `spec-pyforge-scribe`
   stamp for AGENTS.md, after the last edit.
3. Run the chain-currency reconcile for steward.
4. Get `pyforge-steward-test` and the mason meta-tests to exit 0, as described above.
