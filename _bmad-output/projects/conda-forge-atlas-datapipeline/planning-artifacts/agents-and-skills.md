# Agents & Skills Lineup — cf_atlas Kedro-Migration Planning Phase

**Project:** `conda-forge-atlas-datapipeline` · **Date:** 2026-07-17
**Intake spec:** `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` (v5 reset, v5.6 analysis-complete, `spec_updated: 2026-07-17`)
**Mode:** unattended BMAD Tier-2 planning; commit+push between stages; parallelism bounded by data dependencies (PRD → architecture → epics → readiness → sprint feed).

This document records which BMAD personas and skills drive each planning stage
and what artifact each stage produces, so a future session (human or agent) can
re-run or audit the chain without re-deriving it.

---

## 1. Purpose & Phase Context

The spec's § 14 "Suggested BMAD Invocation" names the Phase-1 Tier-2 chain
directly: `bmad-prd` → `bmad-architecture` → `bmad-create-epics-and-stories`,
followed by the readiness gate and per-wave sprint planning. This phase runs
that chain unattended against the v5.6 spec (9 waves 0 + A–H, 22 FRs, seven-
pipeline decomposition). Tier-2 outputs land in
`_bmad-output/projects/conda-forge-atlas-datapipeline/planning-artifacts/`
(tracked); Tier-3 sprint feeds land in `implementation-artifacts/` (gitignored,
regenerated per wave — never committed).

Active-project state at time of writing: `_bmad/custom/.active-project` =
`conda-forge-atlas-datapipeline`; project config layer at
`_bmad-output/projects/conda-forge-atlas-datapipeline/.bmad-config.toml`
(`status = "active"`). Switching is done only via `scripts/bmad-switch
conda-forge-atlas-datapipeline` (marker + the two `_bmad-output` symlinks move
atomically — see CLAUDE.md).

---

## 2. Persona Roster

**Where persona definitions live in this install.** There is no
`_bmad/bmm/agents/` directory. Each persona is installed as a Claude Code
skill under `.claude/skills/bmad-agent-*/` (a `SKILL.md` activation protocol +
a `customize.toml` carrying the persona's role/identity/communication-style/
principles/menu). `_bmad/_config/skill-manifest.csv` records the nominal BMAD
module source paths (e.g. `_bmad/bmm/2-plan-workflows/bmad-agent-pm/SKILL.md`),
but those module directories are not materialized on disk — the `.claude/skills/`
copies are the operative definitions. Team-level persona overrides live in
`_bmad/custom/bmad-agent-*.toml` (present for pm and dev).

The install ships six personas: Mary (analyst), Paige (tech-writer), John (PM),
Sally (UX designer), Winston (architect), Amelia (dev). **There is no dedicated
Scrum-Master agent in this install** — the SM function is covered by workflow
skills (see the roster row and § 3).

| Persona | BMAD agent name | Definition source (operative) | Function in this phase |
|---|---|---|---|
| Product Manager (PM/PO) | **John** (`bmad-agent-pm`) | `.claude/skills/bmad-agent-pm/SKILL.md` + `customize.toml`; team override `_bmad/custom/bmad-agent-pm.toml`; manifest source `_bmad/bmm/2-plan-workflows/bmad-agent-pm/SKILL.md` | Owns the PRD (create + validate via `bmad-prd`). His menu also carries `bmad-create-epics-and-stories` (CE), `bmad-check-implementation-readiness` (IR), and `bmad-correct-course` (CC). |
| System Architect | **Winston** (`bmad-agent-architect`) | `.claude/skills/bmad-agent-architect/SKILL.md` + `customize.toml`; manifest source `_bmad/bmm/3-solutioning/bmad-agent-architect/SKILL.md` | Owns the architecture spine (`bmad-architecture`, menu code CA). Also carries IR — the readiness gate is a PM+Architect joint validation in this install. |
| Scrum Master | **none — no dedicated agent definition in this install** | n/a (no `bmad-agent-sm` skill exists) | SM functions are delivered by workflow skills directly: `bmad-create-epics-and-stories` (epic/story breakdown), `bmad-sprint-planning` (sprint feed), `bmad-correct-course` (mid-sprint change), `bmad-sprint-status` (tracking). In unattended mode these are invoked as skills, not through a persona. |
| (Tier-3 reference) Senior Software Engineer | **Amelia** (`bmad-agent-dev`) | `.claude/skills/bmad-agent-dev/customize.toml`; team override `_bmad/custom/bmad-agent-dev.toml` | Not part of Tier-2 planning; named here because epics/stories and the sprint feed are authored *for* her (execution runs via bmad-loop / `bmad-dev-story` / `bmad-dev-auto` per spec § 2.5). |

Readiness gate note: `bmad-check-implementation-readiness` appears on **both**
John's and Winston's menus (code IR in each `customize.toml`), which is why
Stage 4a below is recorded as a PM/Architect (PO/SM-equivalent) joint
validation rather than a single-persona gate.

---

## 3. Stage → Skill → Artifact Map

All artifact paths below are relative to
`_bmad-output/projects/conda-forge-atlas-datapipeline/` unless noted.
Commit+push after each stage completes (planning-artifacts are tracked;
implementation-artifacts are never committed).

| Stage | Persona | Skill invoked | Artifact produced | Notes |
|---|---|---|---|---|
| **0 — Scaffold / switch / groundtruth** | none (scripts) | none — `scripts/bmad-switch conda-forge-atlas-datapipeline`, then groundtruth verification per spec § 1 Groundtruth rule | `planning-artifacts/intake-groundtruth-2026-07-17.md` (done: § 3.3 snapshot at `58a6dcc` re-verified valid at intake HEAD `4cf1b74`; 23 phases / 28 read CLIs / schema v29 carry forward) | Marker + symlinks verified in agreement before any write-skill runs. |
| **1a — PRD create + validate** | John (PM) | `bmad-prd` (create intent, then validate intent; `bmad-create-prd`/`bmad-validate-prd` are deprecated shims) | `planning-artifacts/prd.md` + PRD validation report | Input: the intake spec + intake-groundtruth. Unattended: Fast path, no elicitation pauses; assumptions recorded in the PRD itself. |
| **1b — Lineup doc** | none (documentation step) | none | `planning-artifacts/agents-and-skills.md` (this file) | Runs parallel-safe alongside 1a (no data dependency on PRD content). |
| **2 — Architecture** | Winston (Architect) | `bmad-architecture` ("lean spine of invariants"; `bmad-create-architecture` is a deprecated shim) | `planning-artifacts/architecture.md` | Depends on prd.md. Grounds against spec §§ 4–7 (Kedro/Dagster/DuckDB target, seven pipelines, MCP/A2A, BSL). |
| **3 — Epics & stories** | John's CE menu item / SM-function skill | `bmad-create-epics-and-stories` | `planning-artifacts/epics.md` | Depends on prd.md + architecture.md. Must preserve the spec's wave structure (0, A–H) and § 9 story decomposition. |
| **4a — Readiness gate** | John + Winston jointly (IR on both menus) | `bmad-check-implementation-readiness` | `planning-artifacts/implementation-readiness-report-*.md` | Validates PRD ⇄ Architecture ⇄ Epics alignment before Phase-4 implementation. Gate must pass before any sprint feed is generated. |
| **4b — Sprint planning** | SM-function skill (no SM persona) | `bmad-sprint-planning` | `implementation-artifacts/sprint-status.yaml` — **Tier-3, gitignored** | Regenerated **per wave** at wave start per spec § 14's per-wave operating loop (step 1: drain Q-gates → sprint-planning for the wave). Never a one-shot whole-project feed; never committed. |
| **5 — Closeout** | none (documentation step) | none | Planning-phase closeout doc in `planning-artifacts/` | Records what was produced, deviations from spec defaults, and the handoff state for Phase-2 execution (bmad-loop, spec § 2.5). |

Skill frontmatter (verbatim `description` fields, from `.claude/skills/<name>/SKILL.md`):

- `bmad-prd` — "Create, update, or validate a PRD. Use when the user wants help producing, editing, or validating a PRD."
- `bmad-architecture` — "Produce the architecture: a lean spine of invariants that keeps everything built from it consistent, projected into whatever format the work needs."
- `bmad-create-epics-and-stories` — "Break requirements into epics and user stories." Goal line: "Transform PRD requirements and Architecture decisions into comprehensive stories organized by user value … with complete acceptance criteria for the Developer agent."
- `bmad-check-implementation-readiness` — "Validate PRD, UX, Architecture and Epics specs are complete." Goal line: "…complete and aligned before Phase 4 implementation starts."
- `bmad-sprint-planning` — "Generate sprint status tracking from epics." Goal line: "…detecting current story statuses and building a complete sprint-status.yaml file."
- `bmad-correct-course` — "Manage significant changes during sprint execution." (Held in reserve; not a scheduled stage.)
- `bmad-agent-pm` — "Product manager for PRD creation and requirements discovery. Use when the user asks to talk to John or requests the product manager."
- `bmad-agent-architect` — "System architect and technical design leader. Use when the user asks to talk to Winston or requests the architect."

---

## 4. Appendix — Persona "Skill Docs" (quoted identity/role blocks)

### 4.1 John — Product Manager

Source: `.claude/skills/bmad-agent-pm/SKILL.md` (overview) and
`.claude/skills/bmad-agent-pm/customize.toml` (persona block).

> "You are John, the Product Manager. You drive PRD creation through user
> interviews, requirements discovery, and stakeholder alignment — translating
> product vision into small, validated increments development can ship."

From `customize.toml`:

> `role` = "Translate product vision into a validated PRD, epics, and stories
> that development can execute during the BMad Method planning phase."
> `identity` = "Thinks like Marty Cagan and Teresa Torres. Writes with Bezos's
> six-pager discipline."
> `communication_style` = "Detective's 'why?' relentless. Direct, data-sharp,
> cuts through fluff to what matters."
> `principles` = PRDs emerge from user interviews, not template filling ·
> Ship the smallest thing that validates the assumption · User value first;
> technical feasibility is a constraint.

Team override (`_bmad/custom/bmad-agent-pm.toml`) appends repo-specific
principles, notably: "A 'product' in this repo is a conda-forge recipe or a
tooling change under .claude/. Frame PRDs accordingly." and "Recipe lifecycle
work rarely needs a PRD … reserve PRD/Epic shape for tooling additions or
cross-recipe migrations." (This migration is exactly the tooling-scale effort
the override reserves PRD shape for.)

### 4.2 Winston — System Architect

Source: `.claude/skills/bmad-agent-architect/SKILL.md` (overview) and
`.claude/skills/bmad-agent-architect/customize.toml` (persona block). No team
override file exists for the architect.

> "You are Winston, the System Architect. You turn product requirements and UX
> into technical architecture that ships successfully — favoring boring
> technology, developer productivity, and trade-offs over verdicts."

From `customize.toml`:

> `role` = "Convert the PRD and UX into technical architecture decisions that
> keep implementation on track during the BMad Method solutioning phase."
> `identity` = "Channels Martin Fowler's pragmatism and Werner Vogels's
> cloud-scale realism."
> `communication_style` = "Calm and pragmatic. Balances 'what could be' with
> 'what should be.' Answers with trade-offs, not verdicts."
> `principles` = Rule of Three before abstraction · Boring technology for
> stability · Developer productivity is architecture.

### 4.3 Scrum Master — no persona definition in this install

Searched: `_bmad/` (no `agents/` directory exists; `_config/skill-manifest.csv`
lists no SM agent) and `.claude/skills/` (no `bmad-agent-sm`/scrum-master
skill). The six installed personas are analyst (Mary), tech-writer (Paige),
PM (John), UX designer (Sally), architect (Winston), dev (Amelia).

The SM function in this phase is therefore skill-borne, not persona-borne:
`bmad-create-epics-and-stories` (Stage 3), `bmad-sprint-planning` (Stage 4b),
with `bmad-correct-course` and `bmad-sprint-status` available for mid-execution
change management and tracking. Where a persona anchor is wanted for
story-facing artifacts, the nearest installed persona is Amelia (dev), whose
persona block (for the record, from `.claude/skills/bmad-agent-dev/customize.toml`) reads:

> `role` = "Implement approved stories with test-first discipline and ship
> working, verified code during the BMad Method implementation phase."
> `identity` = "Disciplined in Kent Beck's TDD and the Pragmatic Programmer's
> precision."
> `communication_style` = "Ultra-succinct. Speaks in file paths and AC IDs —
> every statement citable. No fluff, all precision."

— but Amelia is a Tier-3/implementation persona and takes no Tier-2 stage here.

---

## 5. Unattended-Mode Rules Used

1. **No elicitation pauses.** Persona menus and interview loops are skipped;
   each skill is invoked with its intent stated up front (the persona SKILL.md
   activation explicitly permits direct dispatch when "the user's initial
   message already names an intent"). `bmad-advanced-elicitation` is not used.
2. **Spec § 11 recommended defaults are adopted** wherever a stage hits an
   open question (e.g. Q1 parity default: exact row-count + value parity on
   actionable views, timestamp/ordering-only diffs documented as benign).
   Q2/Q3/Q4 are deferred to the start of their gating waves per § 14, not
   resolved during planning.
3. **Assumptions are recorded in each artifact** — every generated document
   carries its own assumptions/deviations section rather than relying on chat
   history, since no human is present to confirm choices in-session.
4. **Commit+push between stages** (planning-artifacts only). Tier-3 outputs
   (`sprint-status.yaml`) stay local per the repo's tracked-impl-artifact HARD
   rule; drift is checked with `pixi run -e local-recipes bmad-drift-check`.
5. **Skill-over-story authority and Rule 1/Rule 2 obligations** (CLAUDE.md)
   carry into execution: any stage output touching recipe code or atlas
   tooling routes through `conda-forge-expert`, and the effort closes with a
   CFE retro + CHANGELOG entry (spec § 14 restates both).
6. **Do not re-point the active project mid-phase.** All write-skills resolve
   through the `_bmad-output/planning-artifacts` symlink; a desync between
   marker and symlinks silently writes to the wrong project (documented
   near-miss 2026-07-14 in CLAUDE.md).
