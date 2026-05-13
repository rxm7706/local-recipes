---
doc_type: architecture
part_id: bmad-infra
display_name: BMAD infrastructure
project_type_id: infra
date: 2026-05-12
source_pin: 'conda-forge-expert v7.9.0'
---

# Architecture: BMAD Infrastructure (Part 4)

BMAD-METHOD is an AI-driven software development framework that this repository hosts as a **multi-project installation**. A single BMAD installer (`_bmad/`) drives planning + dev + review + retro workflows for multiple projects (`local-recipes`, `deckcraft`, `presenton-pixi-image`, …), each with its own subdirectory under `_bmad-output/projects/<slug>/`.

BMAD itself is **independent of conda-forge**, but this repo's **BMAD↔conda-forge-expert integration rules** (codified in `CLAUDE.md`) make BMAD the entry point for any planned conda-forge work, with mandatory retro closeouts that update the skill.

---

## Mission

> **Provide a multi-project BMAD-METHOD installation with six-layer config merge, active-project resolution, and 65 installed skills — so planning, development, review, and retro workflows can be run for any project hosted in this repo without cross-contamination.**

Operationalized:
- Six-layer TOML config merge (installer team/user → custom team/user → project team/user) resolved by `_bmad/scripts/resolve_config.py`.
- Active-project resolution via CLI flag → env var → marker file → none, in priority order.
- Per-project artifacts under `_bmad-output/projects/<slug>/{planning-artifacts,implementation-artifacts}/`.
- BMAD↔CFE integration rules in `CLAUDE.md` make every conda-forge-touching BMAD agent invoke the skill and run a retro on closeout.

---

## At a Glance

| Field | Value |
|---|---|
| Installer root | `_bmad/` |
| Multi-project root | `_bmad-output/projects/` |
| BMAD-METHOD version | 6.6.0 (`_bmad/bmm/config.yaml` header) |
| Installed skills | 65 (mix of BMAD installer + repo-specific + engineering-practice) |
| BMAD module | `bmm` (located at `_bmad/bmm/`) |
| Workflow phases (under bmm/) | 4 (1-analysis, 2-plan-workflows, 3-solutioning, 4-implementation) |
| Config merge layers | 6 |
| Active projects (this repo) | 3 (`local-recipes`, `deckcraft`, `presenton-pixi-image`) |
| Active-project marker | `_bmad/custom/.active-project` (gitignored, single-line slug) |
| Currently active | `local-recipes` |
| Switcher CLI | `scripts/bmad-switch` |
| Config resolver | `_bmad/scripts/resolve_config.py` |
| Per-skill customization resolver | `_bmad/scripts/resolve_customization.py` |
| Python requirement | 3.11+ (stdlib `tomllib`) — no pip, no venv |

---

## Six-Layer Config Merge

The config resolver reads up to six TOML files, deep-merging them in priority order (highest priority wins):

```
Layer 1: _bmad/config.toml                                              # installer team (regenerated)
Layer 2: _bmad/config.user.toml                                         # installer user (regenerated)
Layer 3: _bmad/custom/config.toml                                       # global custom team (committed)
Layer 4: _bmad/custom/config.user.toml                                  # global custom user (gitignored)
Layer 5: _bmad-output/projects/<slug>/.bmad-config.toml                 # project team (committed; loaded only if active project resolves)
Layer 6: _bmad-output/projects/<slug>/.bmad-config.user.toml            # project user (gitignored; loaded only if active project resolves)
```

**Merge rules** (consistent across `resolve_config.py` and `resolve_customization.py`):
- **Scalars**: override wins
- **Tables**: deep merge
- **Arrays of tables** keyed by `code` or `id`: merge matching entries, append new entries
- **All other arrays**: append (cumulative)

**Layer 1 + Layer 2 are regenerated on every install.** Direct edits will be lost. To pin a value durably without re-running the installer, use Layers 3-6.

**Layers 5 + 6 only load** when an active project resolves (see below). When no active project, only Layers 1-4 apply, and skills fall back to `_bmad-output/` as the output folder — which can pollute the multi-project layout. **Set an active project before invoking write-skills.**

---

## Active-Project Resolution

```
                                ┌─────────────────────────┐
                                │  Active project query    │
                                └────────────┬────────────┘
                                             │
                            ┌────────────────┴────────────────┐
                            │ Priority 1: --project <slug>    │ (CLI flag, per-call override)
                            │   Used by: resolve_config.py    │
                            └────────────────┬────────────────┘
                                             │ if missing
                            ┌────────────────┴────────────────┐
                            │ Priority 2: BMAD_ACTIVE_PROJECT │ (env var, per-shell)
                            └────────────────┬────────────────┘
                                             │ if unset
                            ┌────────────────┴────────────────┐
                            │ Priority 3: _bmad/custom/       │ (marker file, gitignored)
                            │     .active-project             │
                            │   Managed by: scripts/bmad-switch│
                            └────────────────┬────────────────┘
                                             │ if missing
                            ┌────────────────┴────────────────┐
                            │ Priority 4: None — no project   │
                            │ Layers 5+6 skip; only globals.   │
                            └─────────────────────────────────┘
```

### The `scripts/bmad-switch` helper

```bash
scripts/bmad-switch --list                 # list known projects under _bmad-output/projects/
scripts/bmad-switch --current              # print currently active project (reads marker)
scripts/bmad-switch <slug>                 # set active project (writes marker)
scripts/bmad-switch --clear                # remove marker (no active project)
```

The script validates that `<slug>` matches `^[a-z0-9][a-z0-9_-]*$` and that `_bmad-output/projects/<slug>/` exists. Writes to `_bmad/custom/.active-project` (gitignored).

**Why a marker file vs. just env var:** the marker survives across shells, so re-opening Claude Code in a fresh session picks up the right project automatically. The env var is for ephemeral overrides (e.g., running one BMAD command against a different project without changing the global state).

---

## Multi-Project Layout

```
_bmad-output/
├── PROJECTS.md                                # multi-project index (this repo's hosted projects)
│
└── projects/
    ├── local-recipes/                         # ★ active
    │   ├── project-context.md                 # foundational rules every BMAD agent reads on spawn
    │   ├── .bmad-config.toml                  # layer 5 (project team, committed)
    │   ├── planning-artifacts/                # PRDs, architecture, epics-and-stories, this doc set
    │   └── implementation-artifacts/          # specs, deferred work, review diffs
    │
    ├── deckcraft/                             # sibling project (gitignored content)
    │   ├── .bmad-config.toml
    │   ├── planning-artifacts/
    │   └── implementation-artifacts/
    │
    └── presenton-pixi-image/                  # air-gapped Presenton repackaging
        ├── .bmad-config.toml
        ├── planning-artifacts/
        └── implementation-artifacts/
```

Each project has full BMAD-output autonomy: independent PRDs, architectures, epics, stories, retros. The shared installation means **one** `_bmad/` installer and **one** skill catalog, but per-project config overlays + per-project artifacts.

---

## 65 Installed Skills (Categorized)

Skill manifest comes from BMAD installer + repo-specific additions. Read at runtime by the resolver and by Claude Code's `Skill` tool.

### BMAD agent personas (6 — bmm module)

Defined in `_bmad/config.toml` under `[agents.bmad-agent-<role>]`. Each has `name`, `title`, `icon`, `description`. Invoked via `bmad-agent-<role>` skill name or the slash-command equivalent.

| Agent | Role | Display name | Icon |
|---|---|---|---|
| `bmad-agent-analyst` | Business Analyst | Mary | 📊 |
| `bmad-agent-architect` | System Architect | Winston | 🏗️ |
| `bmad-agent-dev` | Senior Software Engineer | Amelia | 💻 |
| `bmad-agent-pm` | Product Manager | John | 📋 |
| `bmad-agent-tech-writer` | Technical Writer | Paige | 📚 |
| `bmad-agent-ux-designer` | UX Designer | Sally | 🎨 |

### Planning chain (9)

`bmad-product-brief`, `bmad-prfaq`, `bmad-create-prd`, `bmad-edit-prd`, `bmad-validate-prd`, `bmad-create-architecture`, `bmad-create-epics-and-stories`, `bmad-create-story`, `bmad-create-ux-design`

### Discovery / customization (3)

`bmad-generate-project-context`, `bmad-document-project` (used to produce this doc set), `bmad-customize`.

### Research (3)

`bmad-domain-research`, `bmad-market-research`, `bmad-technical-research`.

### Implementation skills (2)

`bmad-quick-dev` (implement a story spec), `bmad-dev-story` (story-spec-driven implementation).

### Review skills (5)

`bmad-code-review`, `bmad-review-adversarial-general`, `bmad-review-edge-case-hunter`, `bmad-editorial-review-prose`, `bmad-editorial-review-structure`.

### Sprint + retro skills (4)

`bmad-sprint-planning`, `bmad-sprint-status`, `bmad-correct-course`, `bmad-retrospective`.

### Process / facilitation skills (10)

`bmad-advanced-elicitation`, `bmad-brainstorming`, `bmad-check-implementation-readiness`, `bmad-checkpoint-preview`, `bmad-distillator`, `bmad-help`, `bmad-index-docs`, `bmad-party-mode`, `bmad-qa-generate-e2e-tests`, `bmad-shard-doc`.

### Engineering practice skills (21 — not BMAD-installer)

`api-and-interface-design`, `browser-testing-with-devtools`, `ci-cd-and-automation`, `code-review-and-quality`, `code-simplification`, `context-engineering`, `debugging-and-error-recovery`, `deprecation-and-migration`, `documentation-and-adrs`, `frontend-ui-engineering`, `git-workflow-and-versioning`, `idea-refine`, `incremental-implementation`, `performance-optimization`, `planning-and-task-breakdown`, `security-and-hardening`, `shipping-and-launch`, `source-driven-development`, `spec-driven-development`, `test-driven-development`, `using-agent-skills`.

### Repo-specific skills (1)

`conda-forge-expert` — the Part 1 skill. Drives every conda-forge task. CLAUDE.md mandates BMAD agents invoke it for any conda-forge work.

### Total skill count math

- **42 BMAD-installer skills**: 6 personas + 9 planning + 3 discovery/customization + 3 research + 2 implementation + 5 review + 4 sprint+retro + 10 process/facilitation = **42**
- **21 engineering-practice skills** (separate from BMAD installer; copy from upstream or author)
- **1 repo-specific skill**: `conda-forge-expert`
- **Subtotal real skills: 64**
- The current repo state shows **65** entries in `ls .claude/skills/` because of a stray `.claude/skills/data/` directory (no SKILL.md inside; contains only an old `conda-forge-expert/` subdir). The rebuild target does NOT recreate this stray; clean-up is documented as deferred work.

---

## BMAD Workflow Phases (`_bmad/bmm/`)

The bmm module organizes work into 4 phases:

```
_bmad/bmm/
├── 1-analysis/        # discovery, research, domain studies
│   └── research/
├── 2-plan-workflows/  # PRD, architecture, UX design, validation
├── 3-solutioning/     # epics + stories, sprint planning, story files
└── 4-implementation/  # dev story execution, retros, sprint status
```

A typical project lifecycle traverses 1 → 2 → 3 → 4, but skills within each phase are independent. The current effort (`bmad-document-project` producing this doc set) is a brownfield variant of phase 1 — extracting structure from existing code rather than discovering it from a user brief.

---

## Skill Customization Layer

`_bmad/custom/` holds **per-skill** TOML overrides separate from the global config layers:

```
_bmad/custom/
├── config.toml              # layer 3 (global custom team)
├── config.user.toml         # layer 4 (global custom user, gitignored)
├── .active-project          # active-project marker (gitignored)
├── bmad-agent-dev.toml      # per-skill override for Amelia
└── bmad-agent-pm.toml       # per-skill override for John
```

Per-skill overrides are resolved by **`resolve_customization.py`**, which reads `customize.toml` in the skill's installed directory (layer 1 default), then merges from `_bmad/custom/<skill-name>.toml` (layer 2), then `_bmad/custom/<skill-name>.user.toml` (layer 3 if present). Same merge rules as the global config resolver.

This is how skills like `bmad-generate-project-context` and `bmad-document-project` resolve their `workflow` blocks (`activation_steps_prepend`, `persistent_facts`, `on_complete`).

---

## BMAD ↔ conda-forge-expert Integration

This is the **most consequential** part of Part 4's design — it makes BMAD and CFE coordinate across project lifecycles.

Codified in `CLAUDE.md` § "BMAD ↔ conda-forge-expert integration" as two always-on rules:

### Rule 1: BMAD must invoke `conda-forge-expert` for conda-forge work

Any BMAD agent (planning, dev, review, retro, persona) whose current task involves:
- creating/editing/validating/optimizing/building/submitting a conda recipe
- responding to a conda-forge build failure or review comment
- packaging a PyPI / npm / CRAN / CPAN / LuaRocks / GitHub source as a conda artifact
- working with `pin_subpackage`, `compiler()`, `stdlib()`, `noarch: python`, conda-forge selectors, rattler-build features
- interacting with pixi recipe-build / autotick / submit-pr tasks
- reading/modifying anything under `.claude/{skills,scripts,data}/conda-forge-expert/`

…**must invoke** the `conda-forge-expert` skill (via `Skill: conda-forge-expert`) before producing recipe code or running recipe-related tooling. The skill's 10-step autonomous loop, Operating Principles, Critical Constraints, and Build Failure Protocol are **authoritative** — they override BMAD story instructions when they conflict.

### Rule 2: Every conda-forge BMAD effort runs a retro

When a BMAD effort that did conda-forge work reaches closeout (final story complete, PR merged or final review-comment resolved, or user marks effort done), the agent **must** run a retrospective focused on the `conda-forge-expert` skill:

1. Invoke `bmad-retrospective` skill (or follow its protocol manually).
2. Review session logs, build failures, recipe diffs, reviewer comments to identify:
   - **Corrections** — guidance that was wrong, stale, misleading
   - **Refinements** — guidance that worked but was harder to apply than it should have been
   - **Additions** — patterns, constraints, gotchas, recipes encountered for the first time
3. Land findings as edits to:
   - `SKILL.md` (Operating Principles, Critical Constraints, Recipe Authoring Gotchas, Build Failure Protocol)
   - `reference/*.md` (per-topic deep references)
   - `guides/*.md` (workflow / troubleshooting guides)
   - `CHANGELOG.md` (a new dated entry summarizing the deltas, one line per finding)
4. **Bump skill version** per semver (PATCH for fixes/clarifications, MINOR for new gotchas/sections, MAJOR only for breaking workflow changes).
5. Save corresponding auto-memory entry only if the finding crosses skill boundaries (skill-internal findings stay in the skill files).

**This rule is not optional and not deferrable.** An effort is not "done" until the retro lands. If no novel findings (rare), the retro still produces a CHANGELOG entry stating "no skill changes; verified existing guidance held for: <summary>".

---

## How a Typical Effort Flows

```
1. User: "Implement story X" (or "fix this conda build failure")
                │
                ▼
2. scripts/bmad-switch --current  → confirm active project = "local-recipes"
                │
                ▼
3. Claude Code activates appropriate BMAD skill (e.g. bmad-quick-dev)
                │
                ▼
4. bmad-quick-dev reads project-context.md (foundational rules) on spawn
                │
                ▼
5. Rule 1 check: does this work touch conda-forge?
                │
       ┌────────┴────────┐
       │ Yes              │ No
       ▼                  ▼
6a. Invoke Skill:    6b. Proceed with
    conda-forge-expert    BMAD-only workflow
       │
       ▼
7. CFE skill's 10-step autonomous loop runs
       │
       ▼
8. Work completes (PR merged, build green, review resolved, etc.)
       │
       ▼
9. Rule 2 check: was this a conda-forge effort?
       │
       ▼
10. If Yes: bmad-retrospective runs; updates SKILL.md / reference/ / guides / CHANGELOG
       │
       ▼
11. Skill version bump per semver; project-context.md MINOR pin re-verified if needed
```

---

## State Files & Auto-Memory

### Project-context.md

`_bmad-output/projects/local-recipes/project-context.md` — foundational rules every BMAD agent reads on spawn. Hand-maintained; pinned to skill version (currently `v7.8.1` — re-sync to `v7.9.0` pending; owner: rxm7706, post-v7.9.0 audit). Drift contract: MINOR bump triggers re-sync; PATCH does not.

### Implementation artifacts

`_bmad-output/projects/local-recipes/implementation-artifacts/`:
- `deferred-work.md` — cross-spec deferred items (per-spec sections)
- `spec-cursor-sdk-local-recipe.md` — feature spec (BMAD-consumable)
- `spec-atlas-phase-f-s3-air-gap.md` — feature spec
- `review-diff.patch` — captured review-feedback diff

### Auto-memory

`~/.claude/projects/<repo-slug>/memory/` (gitignored, user-scope):
- `MEMORY.md` — index of saved feedback / project / reference entries
- `feedback_*.md` — durable preferences ("loosen pins for unavailable packages", "call .cmd shims in build.bat", BMAD multi-project pattern, skill disambiguation defaults, BMAD↔CFE integration rules, CFE retro contract, three-place-rule for new scripts)
- `project_*.md` — durable project state (roadmap, copilot-cli blocker, atlas rattler-502 incident, Phase K rate-limit incident, _http.py JFROG leak)
- `reference_*.md` — pointers (canonical npm recipe pattern, v0 ↔ v1 about-field mapping)
- `canonical_*.md` — canonical patterns

Auto-memory crosses sessions and projects; it's the long-term knowledge bank. Skill files (Part 1) cross projects but are CFE-specific; project-context cross sessions but is project-specific; auto-memory is the user's durable scratchpad.

---

## Why Multi-Project (vs. Multiple Repos)

The decision to host multiple BMAD projects in one repo (rather than separate repos):

**Pros**:
- One BMAD installation, one skill catalog → all projects benefit from skill improvements
- Cross-project knowledge (auto-memory) is shared automatically
- One pixi.toml, one set of envs, one CI pipeline
- Sibling-project specs can cross-reference each other freely

**Cons**:
- Active-project resolution is required for every write operation (overhead)
- Mistakes (writing to wrong project) are easier
- Per-project artifact privacy is convention, not enforcement

**Mitigation**: the active-project resolution machinery (CLI flag → env var → marker → none) makes the choice explicit at every layer. `scripts/bmad-switch --current` is a one-line sanity check. CLAUDE.md mandates checking active project before any write-skill invocation.

---

## Integration Points (recap)

See `integration-architecture.md` for full cross-part contracts. Summary:

- **→ Part 1 (skill)**: Rule 1 mandates skill invocation for conda-forge work. Rule 2 mandates skill update via retro on closeout.
- **→ Part 1 indirectly via auto-memory**: feedback memories like `feedback_bmad_uses_cfe_skill.md` and `feedback_bmad_runs_cfe_retro.md` reinforce the integration rules across sessions.
- **No direct dependency on Part 2 or Part 3**: BMAD doesn't read cf_atlas.db directly or call MCP tools without going through Part 1.
- **→ scripts/bmad-switch**: user-facing CLI for marker management; reads `_bmad-output/projects/` to validate slugs.

---

## Rebuild checklist for Part 4

1. **Run BMAD installer** (`bmad-method` package) in a fresh repo. Installer writes:
   - `_bmad/config.toml` (Layer 1, team)
   - `_bmad/config.user.toml` (Layer 2, user)
   - `_bmad/bmm/` module structure (1-analysis, 2-plan-workflows, 3-solutioning, 4-implementation)
   - `_bmad/scripts/{resolve_config,resolve_customization}.py`
   - `.claude/skills/bmad-*` (~40 BMAD installer skills)
2. **Add engineering-practice skills** (~20): copy from upstream BMAD-METHOD repo or author from scratch. These are not BMAD-installer-managed.
3. **Add `conda-forge-expert` skill** (Part 1) under `.claude/skills/conda-forge-expert/` — this is the repo-specific addition that ties Parts 1-3 to BMAD.
4. **Create `_bmad/custom/` directory** with empty `config.toml` + `config.user.toml`. Add per-skill `<skill-name>.toml` files as customizations accumulate.
5. **Create `_bmad-output/projects/<slug>/` for each project**:
   - `local-recipes/` (the primary)
   - any siblings (`deckcraft`, `presenton-pixi-image`, etc.)
   - Each gets `.bmad-config.toml` (committed) + optional `.bmad-config.user.toml` (gitignored)
6. **Create `_bmad-output/PROJECTS.md`** — multi-project index.
7. **Author `_bmad-output/projects/local-recipes/project-context.md`** — foundational rules (use `bmad-generate-project-context` skill for the first pass).
8. **Add `scripts/bmad-switch`** — active-project CLI. (~80 lines Python.)
9. **Write CLAUDE.md** with the BMAD↔CFE integration rules (Rules 1 + 2). Mandate retro discipline.
10. **Seed auto-memory** at `~/.claude/projects/<repo-slug>/memory/` with the always-on feedback entries (BMAD multi-project pattern, BMAD-uses-CFE rule, retro contract, three-places rule). Without these, the rules silently lapse across sessions.

Rebuild order: Part 4 must exist for BMAD planning to happen at all. In practice, Part 4 is the **first** part to bootstrap on a clean repo, even though Parts 1-3 are heavier in code.
