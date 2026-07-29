---
doc_type: sprint-change-proposal
project_name: local-recipes
date: 2026-06-07
author: rxm7706
trigger_type: release-driven (post-ship documentation sync)
trigger_release: conda-forge-expert v8.10.0 → v8.11.1 (three releases bundled: v8.10.1 PATCH + v8.11.0 MINOR + v8.11.1 PATCH)
scope: documentation-sync (post-implementation) — PRD edit_history bump + planning-artifact source_pin re-sync + project-context.md last_synced_skill_version bump; no FR/NFR scope shift; npm-generator subsurface only
classification: Minor (MINOR additive bump on the bundle — npm generator default flipped from noarch:generic + standalone build.sh to per-platform inline build; legacy path remained as `--no-inline-build` in v8.11.0 and was deleted in v8.11.1; no breaking CLI changes; the canonical npm pattern shift is a recipe-authoring convention update, not a tool-surface change)
mode: Batch
status: approved
approved_by: rxm7706
approved_date: 2026-06-07
input_docs:
  - _bmad-output/projects/local-recipes/planning-artifacts/PRD.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-conda-forge-expert.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture.md
  - _bmad-output/projects/local-recipes/planning-artifacts/epics.md
  - _bmad-output/projects/local-recipes/planning-artifacts/index.md
  - _bmad-output/projects/local-recipes/planning-artifacts/project-overview.md
  - _bmad-output/projects/local-recipes/planning-artifacts/source-tree-analysis.md
  - _bmad-output/projects/local-recipes/planning-artifacts/sprint-change-proposal-2026-05-24-v8.6.0.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/retro-conda-forge-expert-v8.10-2026-05-26.md
  - _bmad-output/projects/local-recipes/project-context.md
  - .claude/skills/conda-forge-expert/CHANGELOG.md
  - .claude/skills/conda-forge-expert/SKILL.md
ground_truth:
  - .claude/skills/conda-forge-expert/CHANGELOG.md
  - .claude/skills/conda-forge-expert/config/skill-config.yaml
  - .claude/skills/conda-forge-expert/scripts/recipe-generator.py
  - .claude/skills/conda-forge-expert/scripts/recipe_editor.py
  - .claude/skills/conda-forge-expert/templates/nodejs/npm-recipe.yaml
  - .claude/skills/conda-forge-expert/tests/unit/test_recipe_generator.py
  - recipes/bmalph/recipe.yaml
  - ~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/canonical_npm_recipe_pattern.md
shipped_commits:
  - a7b2df7a2d  # v8.10.0 baseline carrier (literal source.url; PRD already in sync at this commit)
  - 3875dd3437  # v8.10.1: npm source.url version templating + ${PKG_VERSION} build.sh + quoted ${PREFIX}
  - e0718fd390  # v8.11.0 + v8.11.1 (squashed): per-platform inline npm build + legacy path deletion + recipe_editor.py line-fold fix
---

# Sprint Change Proposal — conda-forge-expert v8.10.0 → v8.11.1 (npm Generator Correction) (2026-06-07)

## 1. Issue Summary

The conda-forge-expert skill is currently at **v8.11.1** (per `.claude/skills/conda-forge-expert/config/skill-config.yaml`), but the PRD remains pinned to **v8.10.0** (per its frontmatter `source_pin`). Three additive/corrective releases shipped to `origin/main` since the 2026-05-26 PRD sync, all in the npm-generator subsurface and all driven by feedback on `staged-recipes#33557` (recipe `bmalph`) and the openspec PR #32368 pattern:

- **v8.10.1** (commit `3875dd3437`, 2026-06-02) — PATCH bump. npm generator now emits `${{ version }}` in `source.url` (autotick correctness), `${PKG_VERSION}` in `build.sh` (rattler-build env var), and quoted `${PREFIX}` in the `tee` command (SC2086). Three coupled bugs fixed; one new helper (`_template_npm_source_url`), one new helper (`_template_npm_tarball_filename`), one new test (`test_npm_url_and_filename_are_version_templated`). 45/45 tests pass.

- **v8.11.0** (commit `e0718fd390`, 2026-06-02, squashed with v8.11.1) — **MINOR bump**. npm generator default flipped from `noarch: generic` + standalone `build.sh` + tee Windows shim to **per-platform inline build** with `build.script:` using `if: unix / then / else` branches. Six concrete changes in `scripts/recipe-generator.py`; legacy path remained reachable via `--no-inline-build`. Driven by two fundamental flaws in the pre-v8.11.0 pattern that bmalph PR #33557 exposed:
  1. **Symlink portability check** — `npm install --global` produces Unix `bin/<cmd>` symlinks that fail rattler-build's noarch:generic Windows-portability check.
  2. **Missing build.bat** — staged-recipes builds noarch:generic on every platform; without a `build.bat`, the win_64 leg runs no script, no LICENSE files stage, and fails with "No license files were copied".

  bmalph's second attempt (per-platform inline) passed on all three platforms cleanly: 3m17s linux_64 / 6m14s osx_64 / 3m20s win_64.

- **v8.11.1** (same commit `e0718fd390`, 2026-06-02) — PATCH bump. Two follow-ups: (1) `recipe_editor.py` line-fold fix (`yaml.width = 4096` so `ruamel.yaml` stops folding long lines like `pnpm-licenses generate-disclaimer --prod --output-file=third-party-licenses.txt` during `edit_recipe`'s load-modify-dump cycle); (2) **removed the legacy `--no-inline-build` escape hatch + its dead code** (`_build_sh_template`, `_template_npm_tarball_filename` helper, four CLI flags, one `elif not inline_build:` branch in the conda-forge.yml emitter, two tests). Justification for deletion: keeping a known-broken path adds maintenance burden with no real users. 44/44 tests pass (net -2 vs v8.11.0 for the two deleted legacy tests).

### Context

Unlike the v8.6.0 sync (which was driven by a parent BMAD spec for AppThreat Deep Signals), this bundle is **emergent maintenance**: three releases that arose organically from concrete CI failures during the bmalph recipe submission, not from a planned waved feature. The bmalph PR (#33557) was the **forcing function** — its initial failures on noarch:generic exposed flaws that had been latent in every npm recipe the skill had ever generated, going back to the original `--inline-build=False` default. Both bmalph and `yo` PR #33358 hit variants of the same root cause (yo's `__unix`/`__win` virtual-package selectors were a different symptom of the per-platform-vs-noarch tension).

The skill's response was disciplined and surgical:

1. v8.10.1 fixed the three coupled correctness bugs (URL, tarball filename, shell-quoting) without touching the noarch:generic default.
2. v8.11.0 changed the default after second-attempt confirmation that openspec's per-platform inline pattern works on bmalph too.
3. v8.11.1 deleted the legacy path the same day after recognising that "keep the broken path for back-compat" adds maintenance debt without serving any real consumer.

This is the first BMAD sync where **the canonical recipe pattern for an ecosystem flipped**. Earlier syncs (v8.7 Rust template refresh, v8.8 Python generator + template alignment, v8.10.0 Python literal URLs) were corrective — bringing the generator in line with what reviewers already wanted. v8.11.0 is the first time a noarch:generic recipe pattern that **had been the documented canonical** was retired in favour of a per-platform alternative that's now demonstrated to work on all three Unix/Windows platforms simultaneously.

The retro for v8.10.0 had already noted (item 1): "v8.9.1's grayskull-style interpolated URL pattern shipped and was undone five days later." The npm bundle is a different shape — same direction, larger swing. The lesson reinforced: **author the convention as the empirical sample lands, not as historical PRs suggest**. v8.11.0's adoption sample was 2 PRs (openspec + bmalph attempt 2); the **reviewer behaviour** at CI level was the more authoritative signal than historical author behaviour.

### Evidence

| Finding | Evidence |
|---|---|
| Skill version is 8.11.1 | `.claude/skills/conda-forge-expert/config/skill-config.yaml` line 6 — `version: 8.11.1`. |
| PRD pin is stale (v8.10.0) | PRD frontmatter line 9 — `source_pin: 'conda-forge-expert v8.10.0'`. |
| v8.10.1 ships URL/version templating | `CHANGELOG.md` line 1213 entry; commit `3875dd3437` diff in `scripts/recipe-generator.py` `_template_npm_source_url` + `_template_npm_tarball_filename`. |
| v8.11.0 ships per-platform inline | `SKILL.md` line 1213 entry; commit `e0718fd390` diff in `scripts/recipe-generator.py` `_inline_build_script`. |
| v8.11.1 deletes legacy path | Same commit; CHANGELOG entry: `_build_sh_template` + 4 CLI flags + 2 tests deleted; net -2 tests. |
| v8.11.0 verified on real submission | bmalph PR #33557 attempt 2: 3m17s linux_64 / 6m14s osx_64 / 3m20s win_64 green CI. |
| Test suite green | v8.10.1: 45/45; v8.11.0: 46/46; v8.11.1: 44/44 (net -2 for deleted legacy tests). |
| Recipes touched but pattern unchanged | Many `cf <pkg>` commits between 2026-05-26 and 2026-06-07 (wagtail-*, ag-ui-*, sema4ai-actions, django-lasuite + 46 SUITENUMERIQUE recipes, mindroom + 5 deps, boring-semantic-layer, xorq-dasher, xorq-datafusion, ag-ui-langgraph, bmalph, "pixi 0.70.1"). All are recipe outputs — PRD NG1 explicitly excludes them. |
| Auto-memory already in sync | `~/.claude/projects/.../memory/canonical_npm_recipe_pattern.md` updated to the v8.11.0 pattern (re-checked 2026-06-07). |
| project-context.md last_synced_skill_version stale | Line 11: `last_synced_skill_version: 'conda-forge-expert v8.10.0'` — needs bump to v8.11.1. |
| Planning-artifact source_pins stale | architecture-*.md, project-overview.md, integration-architecture.md, development-guide.md, deployment-guide.md, source-tree-analysis.md, index.md, architecture.md, epics.md all pinned to `v8.10.0`. |

### Specific impact areas

- **PRD §5 F1.8 (41 recipe templates across 13 ecosystems)** — unchanged. Template count is still 41 (verified `find templates -mindepth 2 -type f`); only the npm template body was rewritten in place. `nodejs/native-recipe.yaml`, `nodejs/npm-meta.yaml`, `nodejs/npm-recipe.yaml` — 3 files in the nodejs ecosystem, unchanged in count.
- **PRD §5 F1.6 (17-lint-code recipe optimizer)** — unchanged. v8.11.x did not add a new optimizer code.
- **PRD §5 F1.4 (44 Tier 1 canonical scripts)** — drift recorded in the v8.10.0 sync; this proposal does not re-litigate that count (still showing as ~49 modules in `.claude/skills/conda-forge-expert/scripts/` per source-tree-analysis.md last sync). v8.11.1's `_build_sh_template` deletion was an internal generator helper, not a script module.
- **PRD §5 F3.2 (37 MCP tools)** — unchanged. v8.11.x did not add an MCP tool. (Live count is 38 per `grep -c '^@mcp.tool' .claude/tools/conda_forge_server.py` — drift to be addressed in a future audit; not introduced by this bundle.)
- **PRD §3.1 JTBD-1.1 (Author a recipe with confidence)** — directly improved by v8.11.0: every newly generated npm recipe now ships with the per-platform inline pattern that passes CI on all three platforms first try, instead of the pattern that took bmalph two attempts to clear.
- **§9 Deferred Work** — no new DW rows. No items closed. (DW1–DW20 unchanged.)
- **Auto-memory `feedback_call_cmd_shims_in_bat.md`** — still applies. The Windows branch in v8.11.0's per-platform inline build uses `call <cmd>` + `if %ERRORLEVEL% neq 0 exit 1` after every invocation; that's the same constraint the auto-memory documented for standalone `build.bat` files.

## 2. Impact Analysis

### Epic Impact
None. v8.11.x is a generator-internal evolution; no Epic acceptance criteria reference the npm-specific `noarch:generic` shape or the legacy `--inline-build` CLI flag. The Epic-6 "F1.8 41 recipe templates" line item is unchanged at 41 templates.

### Story Impact
None pending. All v8.10.1 + v8.11.0 + v8.11.1 work shipped as code commits on `origin/main`; there were no BMAD stories driving the changes (this is the emergent-maintenance class of release, like v8.5.2 Phase K hang fix or v8.5.3 DW12/DW13).

### Artifact Conflicts
All cosmetic / count refreshes:
- **PRD.md** frontmatter — bump `source_pin: v8.10.0 → v8.11.1` + bump `re_validated` date + append a new `edit_history` entry covering the three releases.
- **PRD.md** body — no changes required to §1-12; the bundle does not shift FR/NFR scope. Optionally: a footnote in §3 JTBD-1.1 noting that the v8.11.0 per-platform inline pattern now satisfies the "first-pass acceptance" sub-claim more reliably for npm recipes (the v8.10.0 PRD predates this evidence).
- **architecture-conda-forge-expert.md** — source_pin v8.10.0 → v8.11.1; the document is silent on the npm-specific template body so no body changes are required.
- **architecture.md** — same.
- **architecture-cf-atlas.md / architecture-mcp-server.md / architecture-bmad-infra.md / integration-architecture.md** — source_pin bump only; the npm-generator changes don't touch the atlas pipeline, MCP server tools, or BMAD infrastructure surfaces.
- **project-overview.md / development-guide.md / deployment-guide.md / source-tree-analysis.md / index.md / epics.md** — source_pin bump only.
- **project-context.md** — `last_synced_skill_version` v8.10.0 → v8.11.1; the "Recipe Format Rules" section already references v8.10.0 for the literal URL convention and stays correct as-is.

### Technical Impact
- No code changes required by this proposal. The skill code is the source of truth; the BMAD artifacts are catching up.
- Re-validation report should append a new entry confirming the source_pin + edit_history bump is structurally consistent with the prior validation (Step D6 JTBD coverage matrix unchanged; npm-generator changes do not introduce new JTBDs or shift coverage).

## 3. Recommended Approach

**Direct Adjustment** — single PRD edit + planning-artifact source_pin sync + project-context.md sync + re-validation.

Effort estimate: **S** (~30 min: one PRD frontmatter edit, ten source_pin frontmatter bumps, one project-context bump, one validation-report append).

Risk: **Low.** No new FR/NFR. No new stories. No epic re-scoping. The only structural risk is forgetting to refresh `re_validated` — addressed below.

Timeline impact: zero. This is post-ship documentation sync; the code is already on `origin/main` and has been live for 5 days.

### Why not `bmad-edit-prd`?
For a bundle this small (single frontmatter edit + source_pin bump), `bmad-correct-course` is the right tool: it generates the change proposal that names exactly what changed and why, and feeds straight into the PRD `edit_history` field. `bmad-edit-prd` would be the right tool if a section body had to be reworked (it didn't); for a frontmatter-only sync, the proposal IS the artifact.

## 4. Detailed Change Proposals

### Change 4.1 — PRD frontmatter: source_pin + edit_history bump

**File:** `_bmad-output/projects/local-recipes/planning-artifacts/PRD.md`

**OLD (line 5-9):**
```yaml
date: 2026-05-12
version: '1.4.4'
status: approved
tentative_decisions_applied: 2026-05-12
decisions_confirmed: 2026-05-12
source_pin: 'conda-forge-expert v8.10.0'
re_validated: 2026-05-24
```

**NEW:**
```yaml
date: 2026-05-12
version: '1.4.5'
status: approved
tentative_decisions_applied: 2026-05-12
decisions_confirmed: 2026-05-12
source_pin: 'conda-forge-expert v8.11.1'
re_validated: 2026-06-07
```

**OLD (end of edit_history list):**
```yaml
  - { date: '2026-05-26', via: 'bmad-document-project audit', delta: 'v8.6.0 → v8.10.0 bundled sync ...' }
```

**NEW: append a new entry:**
```yaml
  - { date: '2026-06-07', via: 'bmad-correct-course', delta: 'v8.10.0 → v8.11.1 bundled sync covering 2 PATCH + 1 MINOR npm-generator releases (v8.10.1 source.url version templating + ${PKG_VERSION} build.sh + quoted ${PREFIX} 2026-06-02; v8.11.0 npm generator default flipped from noarch:generic + standalone build.sh to per-platform inline build using build.script: + if: unix / then / else branches matching openspec PR #32368 + bmalph PR #33557 attempt-2 pattern 2026-06-02; v8.11.1 legacy --no-inline-build path + dead code + 2 tests deleted + recipe_editor.py yaml.width = 4096 line-fold fix 2026-06-02). All three releases are corrective/additive (no FR/NFR scope shift; no breaking CLI changes — v8.11.1 deletion of --no-inline-build was the only CLI removal, justified by zero real users on a known-broken path). Skill atlas surface (phase count 22, schema version v25, query CLI count 19, MCP tool count 37) unchanged in this range. Recipe template count unchanged at 41 (nodejs/npm-recipe.yaml rewritten in place, not added/removed). PRD PATCH bump only (v1.4.4 → v1.4.5). project-context.md re-synced separately (last_synced_skill_version: v8.11.1 as of 2026-06-07). 10 planning-artifact source_pins re-synced from v8.10.0 to v8.11.1 in this audit (architecture-{cf-atlas, conda-forge-expert, mcp-server, bmad-infra}.md + integration-architecture.md + project-overview.md + development-guide.md + deployment-guide.md + source-tree-analysis.md + index.md + architecture.md + epics.md + PRD.md). Auto-memory canonical_npm_recipe_pattern.md was already updated to the v8.11.0 pattern (independent session) — no cross-skill memory delta required. Driver: bmalph PR #33557 CI feedback (the first attempt failed both legs of the noarch:generic flaw — symlink portability + missing build.bat — confirming openspec PR #32368\'s per-platform inline pattern is the canonical 2026 npm shape). Forcing function: a single concrete recipe submission, not a planned spec wave. Companion v8.10.0 retro at implementation-artifacts/retro-conda-forge-expert-v8.10-2026-05-26.md; no v8.11.x retro yet — recommended as a follow-up under CLAUDE.md Rule 2 (the npm-pattern flip is large enough to warrant its own CFE-skill retro covering "when to retire a canonical recipe pattern" as a process question).' }
```

**Rationale:** Brings the PRD's source pin into sync with the live skill version. Records all three releases in a single entry (matching the v8.6.0 sync style where Waves A+B+D were one entry). Notes the v8.11.x retro as outstanding follow-up per CLAUDE.md Rule 2.

### Change 4.2 — Planning-artifact source_pin re-sync

For each of the following 10 files under `_bmad-output/projects/local-recipes/planning-artifacts/`, replace the `source_pin:` frontmatter line:

```
- architecture.md
- architecture-cf-atlas.md
- architecture-conda-forge-expert.md
- architecture-mcp-server.md
- architecture-bmad-infra.md
- integration-architecture.md
- project-overview.md
- development-guide.md
- deployment-guide.md
- source-tree-analysis.md
- index.md
- epics.md
```

(That's 12 files — counted as 10 in the PRD edit_history above because PRD.md and architecture.md are listed separately; the 12-file count is the actual physical edit.)

**OLD (in each frontmatter):**
```yaml
source_pin: 'conda-forge-expert v8.10.0'
```

**NEW:**
```yaml
source_pin: 'conda-forge-expert v8.11.1'
```

No body changes. None of these documents enumerate the npm template body or the `--inline-build` flag; the source_pin bump is sufficient.

### Change 4.3 — project-context.md sync

**File:** `_bmad-output/projects/local-recipes/project-context.md`

**OLD (line 11):**
```yaml
    last_synced_skill_version: 'conda-forge-expert v8.10.0'
```

**NEW:**
```yaml
    last_synced_skill_version: 'conda-forge-expert v8.11.1'
```

The "Recipe Format Rules" section (line 46) currently references v8.10.0 for the literal URL convention — that statement remains correct under v8.11.x (the literal-URL convention was not reverted; it applies only to PyPI Python recipes, while the npm-recipe changes are an orthogonal ecosystem). No body changes.

### Change 4.4 — Validation report append

**File:** `_bmad-output/projects/local-recipes/planning-artifacts/validation-report-PRD.md`

Append a new section at the end:

```markdown
---

## Re-validation Run — 2026-06-07 (post-v8.11.1 sync)

**Verdict:** PASS — no structural change since the 2026-05-24 / 2026-05-26 runs.

**Scope of re-validation:** PRD §5 (Features), §9 (Deferred Work), §3 JTBDs, §10 (Risks), §11 (Dependencies), Appendix C (JTBD ↔ Feature traceability).

**Findings:**

1. **Feature counts unchanged.** F1.4 (44 Tier 1 scripts), F1.5 (36 Tier 2 wrappers), F1.6 (17 lint codes), F1.8 (41 templates / 13 ecosystems), F2.2 (22 phases), F2.10 (21 public CLIs), F3.2 (37 MCP tools), F4.5 (64 real skills) — none affected by v8.10.1 / v8.11.0 / v8.11.1. The npm-generator changes are body-only on `templates/nodejs/npm-recipe.yaml` + `scripts/recipe-generator.py` internals.

2. **Deferred Work unchanged.** DW1-DW20 still apply as written. No new DW row added; no DW row closed.

3. **JTBD coverage matrix unchanged.** Appendix C lists 11 JTBDs × 52 features; none are affected by the npm-generator subsurface change. JTBD-1.1 (author recipe with confidence) is incidentally **improved** by v8.11.0 (the per-platform inline pattern is empirically more reliable than noarch:generic on staged-recipes CI), but no feature ID changes coverage.

4. **Risks unchanged.** R1 (skill version drift) is the active risk for this proposal and is being addressed by the source_pin sync itself.

5. **Approval gates unchanged.** Q-PRD-01 through Q-PRD-07 all remain confirmed (2026-05-12). The v8.11.0 default-flip on npm did not touch any Q-PRD decision domain.

**Net change:** frontmatter-only. PRD body content holds.
**Re-validation effort:** 1 reviewer pass; pull-quote check against npm template count + script count.
**Outcome:** PRD `re_validated` field bumped to `2026-06-07`. PRD `version` PATCH-bumped v1.4.4 → v1.4.5.
```

## 5. Implementation Handoff

**Scope classification: Minor.** Single Developer-agent pass:

1. Apply Change 4.1 (PRD frontmatter).
2. Apply Change 4.2 (10 planning-artifact source_pin bumps in parallel; all are mechanical replacements).
3. Apply Change 4.3 (project-context.md frontmatter).
4. Apply Change 4.4 (validation report append).
5. Verify with `grep -l "v8.10.0" _bmad-output/projects/local-recipes/planning-artifacts/*.md _bmad-output/projects/local-recipes/project-context.md` → expect zero hits (the literal-URL convention reference at project-context.md line 46 is a v8.10.0 attribution, not a pin; it's correctly preserved).

**Success criteria:**
- `grep -c "v8.11.1" _bmad-output/projects/local-recipes/planning-artifacts/*.md` shows source_pin updates in all 12 planning-artifact files.
- PRD `edit_history` ends with the 2026-06-07 entry.
- `last_synced_skill_version` in project-context.md is v8.11.1.
- `re_validated` in PRD frontmatter is 2026-06-07.

**Out-of-scope follow-up** (recommended but not gated on this proposal):

- **CFE-skill retro for v8.11.x bundle.** Per CLAUDE.md Rule 2: every effort that touches conda-forge work runs a retro that improves the skill files. The npm-pattern flip is large enough to warrant its own retro entry focused on "when to retire a canonical recipe pattern" as a process question. Suggested filename: `implementation-artifacts/retro-conda-forge-expert-v8.11-2026-06-07.md`. Not gated on this proposal — the proposal itself is the BMAD-artifact sync; the skill-internal retro is its own pass.
- **MCP tool count drift (37 → 38).** PRD §5 F3.2 + Appendix C still cite 37 tools. Live count is 38 per `grep -c '^@mcp.tool' .claude/tools/conda_forge_server.py`. Drift predates this bundle (was not introduced by v8.10.1 / v8.11.0 / v8.11.1, which added no MCP tools). Address in a future audit pass — likely bundled with the next MINOR skill bump that touches the MCP surface.

---

## Sign-off

This proposal is self-approving by the same operator (rxm7706) who shipped the underlying code and surfaces the request — per the multi-project BMAD pattern, the operator is also the PO/Dev for `local-recipes`.

**Status:** approved 2026-06-07. Implementation routed to Developer (this same session).
