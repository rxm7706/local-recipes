---
doc_type: architecture
part_id: bmad-infra
display_name: BMAD infrastructure
project_type_id: infra
date: 2026-07-25
source_pin: 'conda-forge-expert v8.79.1'
---

# Architecture: BMAD Infrastructure (Part 4)

> **Re-grounded 2026-07-25** (source_pin → v8.79.1; reconciler loop per SYNC-RUNBOOK). This was
> the most stale doc in the set — the BMAD layer roughly quadrupled since the 2026-07-06 pass and
> several claims were not merely behind but **wrong**. Corrected: BMAD-METHOD **6.10.0** (was
> documented as 6.6.0); **89 real skills** across `.claude/skills/` (was "65", with math that
> named two skills that do not exist); **14 BMAD projects** (was 3); the `_bmad/bmm/` "4 workflow
> phases" directory tree **does not exist** in a 6.10.0 install and that section is replaced by the
> real installer layout; the FX.8 provenance hook **is not wired** into `.claude/settings.json` and
> so does not run. Added, because the doc had no concept of them: the **tier model**, **the Spec**
> and its `.memlog.md` derivation model, the **bmad-loop** deterministic harness + loop homes, the
> three **governance detectors**, and the **Guildhall**. Re-verified unchanged: the six-layer config
> merge and its merge rules, the active-project priority order, the `resolve_customization.py`
> three-layer per-skill merge, the six BMAD agent personas and their descriptors in
> `_bmad/config.toml`, the 21 engineering-practice skills, and both BMAD ↔ conda-forge-expert
> integration rules. Live factory facts this doc leans on (`bmad-groundtruth`, 2026-07-25):
> cf_atlas **schema v29**, **46 MCP tools**, 23 atlas phases, gotchas **G1–G106**, **19 pixi envs**.

BMAD-METHOD is an AI-driven software development framework that this repository hosts as a
**multi-project installation**. A single BMAD installer (`_bmad/`) drives spec + planning + dev +
review + retro workflows for **14** projects, each with its own subdirectory under
`_bmad-output/projects/<slug>/`.

BMAD itself is **independent of conda-forge**, but this repo's **BMAD ↔ conda-forge-expert
integration rules** (codified in `CLAUDE.md`) make BMAD the entry point for any planned
conda-forge work, with mandatory retro closeouts that update the skill.

Part 4 is also where the repo's **governance** lives. In PyForge doctrine the Skill is the unit of
*execution* and the deterministic harness — bmad-loop, the sandbox/permission gates, the CI verify
gates, the drift and surface detectors — is the unit of *governance*, and is deliberately **not a
skill**. The hand that builds is never the gate that judges.

---

## Mission

> **Provide a multi-project BMAD-METHOD 6.10.0 installation — six-layer config merge, marker+symlink
> active-project resolution, 89 installed skills, a deterministic loop harness, and the detectors
> that bind every tracked file to a Spec — so any of the 14 hosted projects can be specced, planned,
> built, reviewed and retro'd without cross-contamination.**

Operationalized:
- Six-layer TOML config merge (installer team/user → custom team/user → project team/user) resolved
  by `_bmad/scripts/resolve_config.py`.
- Active-project resolution via CLI flag → env var → marker file → none, in priority order —
  **plus** the two `_bmad-output/` symlinks that write-skills actually resolve through.
- Per-project artifacts under `_bmad-output/projects/<slug>/{planning-artifacts,implementation-artifacts}/`,
  with the tier rules enforcing what may be tracked where.
- **The Spec** as the unit of contract, derived on every run from an append-only `.memlog.md`.
- **bmad-loop** as the deterministic DEV → VERIFY → REVIEW → VERIFY → COMMIT harness, one isolated
  loop home per project.
- Three governance detectors (`bmad_drift_check.py`, `spec_surface_check.py`, `llms_full_check.py`)
  that make drift visible instead of silent.
- BMAD ↔ CFE integration rules in `CLAUDE.md` make every conda-forge-touching BMAD agent invoke the
  skill and run a retro on closeout.

---

## At a Glance

| Field | Value |
|---|---|
| Installer root | `_bmad/` |
| Multi-project root | `_bmad-output/projects/` |
| BMAD-METHOD version | **6.10.0** (`_bmad/_config/manifest.yaml`; `_bmad/{bmm,core}/config.yaml` headers agree) |
| Install / last update | installed 2026-04-30, last updated 2026-07-12 |
| Installed modules | `core` 6.10.0, `bmm` 6.10.0 (both `source: built-in`) + `skf` **2.0.1** (separately managed) |
| Registered IDEs | `claude-code` |
| Skill directories | 93 in `.claude/skills/` = **89 real skills** + 4 non-skill support dirs |
| Skill split | 51 `bmad-*` · 16 `skf-*` · 21 engineering-practice · 1 repo-specific |
| Config merge layers | 6 (layers 2 and 4 are optional; both currently absent) |
| Per-skill customization layers | 3 (`resolve_customization.py`) |
| BMAD projects (this repo) | **14** |
| Specs (`planning-artifacts/specs/spec-*/SPEC.md`) | **22** |
| Tracked per-story specs | **63** (pyforge-atlas 32, pyforge-warden 31; all others 0) |
| Active-project marker | `_bmad/custom/.active-project` (gitignored, single-line slug) |
| Active-project symlinks | `_bmad-output/{planning,implementation}-artifacts` (gitignored) |
| Currently active | `local-recipes` |
| Switcher CLI | `scripts/bmad-switch` (319 lines, stdlib-only) |
| Loop-home provisioner | `scripts/bmad-loop-worktree` |
| Config resolver | `_bmad/scripts/resolve_config.py` |
| Per-skill customization resolver | `_bmad/scripts/resolve_customization.py` |
| Memory log writer | `_bmad/scripts/memlog.py` |
| Loop orchestrator | `bmad-loop >=0.9.0` (external, pinned in `pixi.toml`) |
| Program console | the **Guildhall** — `docs/dashboard/` → GitHub Pages |
| Python requirement | 3.11+ for the config resolvers (stdlib `tomllib`); `memlog.py` declares `>=3.8` — no pip, no venv |

---

## The Tier Model

Everything starts with a Dream. BMAD turns it into the Spec. The Spec drives the build. The agent
and the framework are interchangeable; the tiers are not, and are never crossed.

| Tier | Location | Purpose | Git |
|---|---|---|---|
| **0 — Dream** | `docs/dreams/*.md` (**26** Dreams + a README) | the raw human aspiration | tracked, permanent |
| **1 — Intake spec (LEGACY)** | `docs/specs/*.md` (**19**) | former hand-authored tier, superseded by Tier 2 | tracked, phasing out — author no new files here |
| **2 — Spec & planning** | `_bmad-output/projects/<slug>/planning-artifacts/` | `bmad-spec` output + PRD, architecture, epics+stories, gate reports. **The active contract.** | tracked, permanent |
| **3 — Execution output** | `_bmad-output/projects/<slug>/implementation-artifacts/` | story files, sprint YAMLs, test outputs, retros, run scratch | **gitignored — nothing here may be git-tracked** |

Two rules carry weight:

- A tracked file under `implementation-artifacts/` is a **HARD `tracked-impl-artifact`** finding in
  `bmad_drift_check.py`. Tier 3 is local-only by construction.
- **Story specs are durable and tracked, NOT Tier-3** (convention since 2026-07-25). In a
  spec-driven build the spec *is* the contract, so per-story intent contracts must survive worktree
  teardown and exist in every clone. bmad-loop drafts a story spec into the run's gitignored Tier-3
  dir as scratch; **after the story merges, the spec is promoted into the tracked
  `planning-artifacts/specs/` subdir and committed.** Motivating incident: pyforge-warden lost 13 of
  31 story specs outright (all of Epics 3 and 4), plus 8 husks, to Tier-3 worktree teardown before
  the convention existed — recovered 2026-07-25 to 31/31. Recovery-source hierarchy, highest
  fidelity first: Claude Code session transcripts (`~/.claude/projects/**/*.jsonl`, where the
  `Write`/`Edit` tool calls survive verbatim) → surviving bmad-loop run-worktree snapshots →
  regeneration from `epics.md` (Intent + ACs only — the contract, not the narrative).

Dream-first is mandatory: before any non-trivial effort a Dream must exist in `docs/dreams/<slug>.md`
and BMAD must have produced its Spec from it (`bmad-spec` for small scope, or the
`bmad-prd` / `bmad-architecture` / `bmad-create-epics-and-stories` chain).

---

## The Spec — the Unit of Contract

A Spec is a folder under `<project>/planning-artifacts/specs/spec-<slug>/` containing `SPEC.md`,
its `.memlog.md`, and any spec-authored companions. Produced and maintained solely by `bmad-spec`.

### Shape

`SPEC.md` carries exactly five mandatory headings, in order — `## Why`, `## Capabilities`,
`## Constraints`, `## Non-goals`, `## Success signal` — plus optional trailing `## Assumptions` and
`## Open Questions`. Each capability carries a stable `CAP-N` ID with an **Intent** (what, never how)
and a **Success** clause; IDs are never reused and never renumbered.

Frontmatter keys observed in live specs: `spec` / `id`, `status`, `owner-dream`, `program`,
`surface:`, `surface-drift:`, `surface-drift-exclude:`, `companions:`, `sources:`, `open_questions:`,
`assumptions:`.

`bmad-spec` enforces eight Spec Law rules over that shape (both fields per capability; intents
describe WHAT; constraints must actually rule something out; at least one explicit non-goal;
testable success signal; stable IDs; preservation of every load-bearing source claim; lean prose).

### `.memlog.md` is canonical

```
      user intent / PRD / brief / transcript
                    │
                    ▼
        ┌───────────────────────────┐
        │  .memlog.md               │  append-only, chronological, one line per
        │  (the decision-of-record) │  decision | constraint | capability | assumption
        └─────────────┬─────────────┘  | question | direction | note | event
                      │                 never edited, never reordered, no status field
       derived on every run
                      │
        ┌─────────────┴───────────────┐
        ▼                             ▼
    SPEC.md                    spec-authored companions
 (five-field contract)       (glossary.md, waves.md, …)
```

- Writes go through `_bmad/scripts/memlog.py` (`init` / `append`), which is **write-only and blind**:
  every command is an atomic, context-free write (temp + fsync + rename) that echoes the new state as
  one line of JSON, so the caller never re-reads the file mid-session. The one read is on resume.
- The memlog is explicitly **not a deliverable**. `SPEC.md` and every spec-authored companion are
  **re-derived on each run** from it. A hand-edit to `SPEC.md` from outside `bmad-spec` is
  unsupported and is overwritten on the next derive.
- On an update operation the **memlog, not the rendered `SPEC.md`, is the authority** on what was
  decided and on capability IDs.
- Deriving the contract from a living log instead of editing it in place is what lets PRD, UX,
  architecture and epics runs land in any order and feed the same Spec without merge drift: the log
  only accumulates; the artifact is re-rendered.
- Validation is a two-pass sweep after every create or update — **Pass 1 Coherence** (Spec Law 1–6
  and 8) and **Pass 2 Preservation** (walk the source claim by claim; wrapper-ceremony drops are
  logged, never silent). Each verdict appends to the memlog as `--type event`.

### Companions and sources

| Kind | Location | Ownership |
|---|---|---|
| **Spec-authored companion** | sibling of `SPEC.md` (`waves.md`, `glossary.md`, …) | `bmad-spec` owns and may edit |
| **Adopted companion** | referenced by relative path, anywhere in the repo | the originating skill owns it; `bmad-spec` **never** edits it |
| **`sources:`** | fully-absorbed inputs | listed for audit only — downstream does **not** read them |

The split is implicit by path; downstream consumers treat both companion kinds the same and must
read every entry in `companions:` to have the full contract. Diagrams always land in a companion,
regardless of size. Live example of an adopted companion: the `spec-packaging-factory` Spec adopts
`.claude/skills/conda-forge-expert/SKILL.md` — the Part 1 skill file is contract material the Spec
points at but does not own.

---

## Six-Layer Config Merge

The config resolver reads up to six TOML files, deep-merging them in priority order (highest
priority wins):

```
Layer 1: _bmad/config.toml                                              # installer team (regenerated)
Layer 2: _bmad/config.user.toml                                         # installer user (regenerated; absent today)
Layer 3: _bmad/custom/config.toml                                       # global custom team (committed)
Layer 4: _bmad/custom/config.user.toml                                  # global custom user (gitignored; absent today)
Layer 5: _bmad-output/projects/<slug>/.bmad-config.toml                 # project team (committed; loaded only if active project resolves)
Layer 6: _bmad-output/projects/<slug>/.bmad-config.user.toml            # project user (gitignored; loaded only if active project resolves)
```

**Merge rules** (identical in `resolve_config.py` and `resolve_customization.py`, and purely
structural — no field-name special-casing):
- **Scalars**: override wins
- **Tables**: deep merge
- **Arrays of tables** where *every* item shares the same identifier field (all have `code`, or all
  have `id`): merge by that key — matching keys replace, new keys append
- **All other arrays** — including mixed or partially-keyed ones: append (cumulative)

**Layer 1 + Layer 2 are regenerated on every install.** Direct edits will be lost. To pin a value
durably without re-running the installer, use Layers 3–6. Layers 2 and 4 are optional; neither file
exists in the current checkout (`_bmad/custom/.gitignore` ignores `*.user.toml`).

**Layers 5 + 6 only load** when an active project resolves. When none does, only Layers 1–4 apply
and skills fall back to repo-root `_bmad-output/` as the output folder — which pollutes the
multi-project layout. **Set an active project before invoking write-skills.**

Every project has a `.bmad-config.toml`; all 14 are present.

---

## Active-Project Resolution

Resolution has **two halves**, and documenting only the first is how efforts overwrite each other's
artifacts.

### Half 1 — the resolution order (read by `resolve_config.py`)

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
                            │ Priority 2: BMAD_ACTIVE_PROJECT │ (env var, per-shell / per-invocation)
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

### Half 2 — the symlinks that write-skills actually resolve through

```
_bmad-output/planning-artifacts        ──symlink──▶  projects/<slug>/planning-artifacts
_bmad-output/implementation-artifacts  ──symlink──▶  projects/<slug>/implementation-artifacts
```

`_bmad/bmm/config.yaml` hard-codes

```yaml
planning_artifacts: "{project-root}/_bmad-output/planning-artifacts"
implementation_artifacts: "{project-root}/_bmad-output/implementation-artifacts"
```

and **that key does not compose with a project's `output_folder` override**. So every BMAD skill
that writes planning artifacts resolves **through these symlinks, not through the marker**. Marker
and symlinks must always agree.

`scripts/bmad-switch <slug>` re-points both symlinks atomically **and then** writes the marker —
marker last, so a failed re-point aborts before the two can disagree. It also provisions the Tier-3
backlink when run inside a loop-home worktree, so a worktree's `implementation-artifacts` resolves
to the main checkout's canonical store and sprint feeds stay single-sourced.

Before 2026-07-14 the script wrote **only** the marker and left the symlinks wherever they last
pointed. That produced an observed **10-hour desync** — symlinks on `pyforge-warden` while the marker
said `local-recipes` — in which a routine local-recipes doc re-sync would have overwritten
pyforge-warden's PRD, epics and architecture. `--current` and `--list` now warn on any disagreement;
heed the warning before running any BMAD write-skill.

### The `scripts/bmad-switch` helper

```bash
scripts/bmad-switch --list                 # list known projects under _bmad-output/projects/
scripts/bmad-switch --current              # print the active project (warns on marker/symlink desync)
scripts/bmad-switch <slug>                 # set active project (re-points symlinks, THEN writes marker)
scripts/bmad-switch --clear                # remove the marker (no active project)
```

The script validates `<slug>` against `^[a-z0-9][a-z0-9_-]*$` and that `_bmad-output/projects/<slug>/`
exists. It refuses to touch an artifact path that exists and is not a symlink.

**Why a marker file vs. just the env var:** the marker survives across shells, so re-opening Claude
Code in a fresh session picks up the right project automatically. The env var is for ephemeral
overrides — one command against a different project without changing global state.

### HARD rule (since 2026-07-25) — parallel agents never touch the switch

The marker **and** the symlinks are **per-working-tree global state**, so `bmad-switch` is a mutex
that nobody holds. Two concurrent BMAD write-agents silently re-point each other's target mid-write.

1. Write to `_bmad-output/projects/<slug>/planning-artifacts/…` **literally**. Never rely on the
   symlink from a parallel agent.
2. **Never call `scripts/bmad-switch` from a parallel agent.** Pass `BMAD_ACTIVE_PROJECT=<slug>`
   per invocation instead (Priority 2 — per-call, no global mutation).
3. **Verify placement after writing.** The failure mode is silent; nothing errors.

Live incident (2026-07-25, an 11-Spec derivation fan-out): five concurrent agents each ran
`bmad-switch`; the shared symlink was observed moving pyforge-doctor → pyforge-marshal →
pyforge-mason → deckcraft mid-run, and one agent's 30-entry memlog landed under the wrong project's
tree. Everything was recovered intact **only because the agents checked**.

---

## Multi-Project Layout

**14 projects.** Every one has `.bmad-config.toml` + `planning-artifacts/` + `implementation-artifacts/`.

```
_bmad-output/
├── PROJECTS.md                                # multi-project index
├── planning-artifacts        -> projects/<active>/planning-artifacts        (gitignored symlink)
├── implementation-artifacts  -> projects/<active>/implementation-artifacts  (gitignored symlink)
│
└── projects/
    ├── local-recipes/                         # ★ active — the conda-forge packaging factory
    │   ├── project-context.md                 # foundational rules every BMAD agent reads on spawn
    │   ├── SYNC-RUNBOOK.md                    # detector finding → reconciler skill mapping
    │   ├── .bmad-config.toml                  # layer 5 (project team, committed)
    │   ├── planning-artifacts/                # PRD.md, architecture*.md, epics.md, specs/, this doc
    │   │   └── specs/spec-<slug>/{SPEC.md,.memlog.md,<companions>.md}
    │   └── implementation-artifacts/          # Tier 3 — gitignored
    │
    ├── deckcraft/                    presenton-pixi-image/     pyforge-atlas/
    ├── pyforge-doctor/               pyforge-genesis/          pyforge-herald/
    ├── pyforge-marshal/              pyforge-mason/            pyforge-scribe/
    ├── pyforge-steward/              pyforge-warden/
    └── unity-data-stack/             wasm-analytics-stack/
```

Eight of the fourteen are **Smith** projects — the PyForge Guild's stations, each productizing one
capability: Herald (visual media / the Design↔Code bridge), Marshal (orchestration, productizing
bmad-loop), Atlas (the cf_atlas data pipeline), Warden (dependency compliance), Mason (packaging,
wrapping the conda-forge-expert skill), Doctor (health and diagnostics), Scribe (team knowledge),
Steward (platform/ops). Genesis is the operating-model installer. The remainder are product or
stack projects. `PROJECTS.md` lists all 14 as `active`.

### Spec ownership

**22 Specs** across the 14 projects:

| Project | Specs |
|---|---|
| `local-recipes` | **8** — enterprise-airgap, factory-console, fleet-stewardship, modernist-identity, multi-loop-isolation, packaging-factory, pyforge-marshal, regenerable-factory |
| `pyforge-atlas` | 2 — spec-pyforge-atlas, spec-upstream-discovery |
| each of the other 12 | 1 |

`local-recipes/spec-pyforge-marshal` and `pyforge-marshal/spec-pyforge-marshal` are **different
Specs with the same slug** — see the surface-checker's key rule below.

### Artifact naming is not uniform

A rebuild must not assume one shape:

- **PRD**: 6 projects use a flat `prd.md` / `PRD.md` (local-recipes uses uppercase `PRD.md`);
  8 use a `prds/` subdirectory.
- **Architecture**: 5 projects use a flat `architecture.md`; 9 use an `architecture/` subdirectory.
- **Epics**: 12 projects have `epics.md`; `unity-data-stack` and `wasm-analytics-stack` have none
  (both are PRD+architecture depth — stories decompose when scheduled).
- **Per-story specs**: 63 tracked, all in two projects — pyforge-atlas 32, pyforge-warden 31. Every
  other project has 0. Each of those two carries a `specs/README.md` recording provenance and, for
  the regenerated ones, that they are contract-only reconstructions.

### `_bmad-output/PROJECTS.md`

Sections: *Active project switching* · *Config layering* (the 6-row table) · *Projects* (a
`| Slug | Status | Description |` table, all 14 rows `active`) · *Adding a new project* (5 steps) ·
*Reading another project's artifacts (without switching)* · *Running a skill against a non-active
project (without switching globally)*.

Reading another project's artifacts needs no switch — read the file path directly. Only **writes**
need the active project set.

---

## Installed Skills

`.claude/skills/` holds **93 directories = 89 real skills + 4 non-skill support directories**. A
real skill is a directory containing `SKILL.md`; the resolver and Claude Code's `Skill` tool read
them at runtime.

| Family | Count |
|---|---|
| `bmad-*` (BMAD installer, bmm + core) | **51** |
| `skf-*` (Skill Forge module, separately managed) | **16** |
| Engineering-practice (not BMAD-installer) | **21** |
| Repo-specific | **1** (`conda-forge-expert`) |
| **Total real skills** | **89** |

### BMAD agent personas (6 — bmm module)

Defined in `_bmad/config.toml` under `[agents.bmad-agent-<role>]`, each with `name`, `title`, `icon`,
`description`. Invoked via the `bmad-agent-<role>` skill name.

| Agent | Role | Display name | Icon |
|---|---|---|---|
| `bmad-agent-analyst` | Business Analyst | Mary | 📊 |
| `bmad-agent-architect` | System Architect | Winston | 🏗️ |
| `bmad-agent-dev` | Senior Software Engineer | Amelia | 💻 |
| `bmad-agent-pm` | Product Manager | John | 📋 |
| `bmad-agent-tech-writer` | Technical Writer | Paige | 📚 |
| `bmad-agent-ux-designer` | UX Designer | Sally | 🎨 |

**These six are not the same layer as the Smiths.** The eight Smiths (Herald · Marshal · Atlas ·
Warden · Mason · Doctor · Scribe · Steward) are the *factory's stations* — accountable owners of a
capability, each with its own project and Spec. Mary, John, Winston, Sally, Amelia and Paige are
**Marshal's sub-agents on the floor**: personas the orchestration station spawns inside a single
effort. Conflating the two layers is the standard reading error; the Smiths own capabilities, the
BMAD six own turns of work.

### Spec & planning (10)

`bmad-spec` (**the Spec producer** — distils any intent input into the five-field contract plus
companions, memlog-derived and preservation-validated), `bmad-prd`, `bmad-architecture`,
`bmad-create-epics-and-stories`, `bmad-create-story`, `bmad-ux`, `bmad-product-brief`, `bmad-prfaq`,
`bmad-check-implementation-readiness`, `bmad-sprint-planning`.

### Discovery / customization (3)

`bmad-generate-project-context`, `bmad-document-project` (produced this doc set), `bmad-customize`.

### Research (3)

`bmad-domain-research`, `bmad-market-research`, `bmad-technical-research`.

### Implementation (4)

`bmad-quick-dev` (implement any intent against existing conventions), `bmad-dev-story` (context-filled
story file), `bmad-dev-auto` (**one iteration of an unattended development loop**), `bmad-forge-idea`
(persona-driven interrogation that hardens or kills an idea cheaply).

`bmad-dev-auto` is the unattended entry point and has a strict **HALT protocol**: it ends a turn only
by halting with an explicit terminal `status`, written either into `{spec_file}`'s frontmatter (plus
an `## Auto Run Result` section) or, when no spec file is known, into
`{implementation_artifacts}/bmad-dev-auto-result-<slug-or-timestamp>.md`. Subagents must be invoked
**synchronously** — a backgrounded subagent never hands control back and stalls the run.

### Review (7 directories, mid-consolidation)

`bmad-review` is the consolidated multi-lens reviewer. Its `customize.toml` defines five
`[[workflow.lenses]]`, each loading a `references/lens-*.md` from the skill root:

| Lens | Content type | Notes |
|---|---|---|
| `adversarial` | code / any artifact | attitude-driven cynical review |
| `edge-case-hunter` | code / any artifact | method-driven branch + boundary walk |
| `verification-gap` | code | claims vs. evidence |
| `structure` | docs | cuts, reorganization, simplification |
| `prose` | docs | `after = "structure"` — runs once structure lands |

Output is **one JSON array of findings**, each carrying its `lens` and a `location`. Independent
lenses run in parallel via subagents; `prose` waits on `structure`.

**The consolidation is incomplete, and the doc set should say so.** Only
`bmad-review-verification-gap` carries the deprecation notice and forwards (6 lines).
`bmad-review-adversarial-general` (37 lines), `bmad-review-edge-case-hunter` (73),
`bmad-editorial-review-prose` (86), `bmad-editorial-review-structure` (179) and `bmad-code-review`
(92) all still ship **full independent `SKILL.md` bodies** and remain independently invocable. Two
paths to the same review therefore exist; expect divergence until the remaining five are cut over.

### Sprint + retro (4)

`bmad-sprint-planning`, `bmad-sprint-status`, `bmad-correct-course`, `bmad-retrospective`.

### Loop support (3)

`bmad-loop-setup` (installs/configures the loop module in a project), `bmad-loop-resolve`
(**interactive** escalation resolution — a human is present and the agent *should* ask;
invoked as `/bmad-loop-resolve <story-key>` when a run pauses on a CRITICAL escalation),
`bmad-loop-sweep` (automation-only deferred-work ledger triage returning a machine-readable
partition; also migrates pre-DW-format ledgers with `--migrate`).

### Process / facilitation (7)

`bmad-advanced-elicitation`, `bmad-brainstorming`, `bmad-checkpoint-preview`, `bmad-help`,
`bmad-index-docs`, `bmad-party-mode`, `bmad-shard-doc`. Plus `bmad-qa-generate-e2e-tests` for QA
automation.

### Deprecated `bmad-*` skills (5)

| Deprecated | Consolidated into | Notice |
|---|---|---|
| `bmad-create-prd` | `bmad-prd` (create intent) | "will be removed in v7" |
| `bmad-edit-prd` | `bmad-prd` (update intent) | "will be removed in v7" |
| `bmad-validate-prd` | `bmad-prd` (validate intent) | "will be removed in v7" |
| `bmad-create-architecture` | `bmad-architecture` (create intent) | "will be removed in v7" |
| `bmad-review-verification-gap` | `bmad-review` | forwards |

Each ships a stub `SKILL.md` that forwards to its successor. They still occupy skill directories, so
they count toward the 51.

> **Corrections to the previous revision of this doc:** it listed `bmad-distillator` and
> `bmad-create-ux-design` in its category lists. **Neither exists.** The UX skill is `bmad-ux`; there
> is no distillator (`bmad-spec` is the distillation surface). It also had never heard of
> `bmad-spec`, `bmad-architecture`, `bmad-prd`, `bmad-dev-auto`, `bmad-forge-idea`, `bmad-review`,
> `bmad-loop-resolve`, `bmad-loop-setup`, `bmad-loop-sweep`, or any of the 16 `skf-*` skills.

### Skill Forge — `skf-*` (16)

A separately-managed module (`_bmad/skf/`, version **2.0.1**, tracked in its own
`_bmad/_config/skf-manifest.yaml` and **not** in `manifest.yaml`). It compiles code repositories and
docs into version-pinned, provenance-backed agent skills.

`skf-setup`, `skf-forger` (the Ferris persona), `skf-analyze-source`, `skf-brief-skill`,
`skf-create-skill`, `skf-quick-skill`, `skf-create-stack-skill`, `skf-verify-stack`,
`skf-refine-architecture`, `skf-test-skill`, `skf-audit-skill`, `skf-update-skill`,
`skf-export-skill`, `skf-rename-skill`, `skf-drop-skill`, `skf-campaign`.

Its `forge_data_folder` points into `_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data`
— i.e. Tier-3, gitignored, correctly.

### Engineering practice (21 — not BMAD-installer)

`api-and-interface-design`, `browser-testing-with-devtools`, `ci-cd-and-automation`,
`code-review-and-quality`, `code-simplification`, `context-engineering`,
`debugging-and-error-recovery`, `deprecation-and-migration`, `documentation-and-adrs`,
`frontend-ui-engineering`, `git-workflow-and-versioning`, `idea-refine`,
`incremental-implementation`, `performance-optimization`, `planning-and-task-breakdown`,
`security-and-hardening`, `shipping-and-launch`, `source-driven-development`,
`spec-driven-development`, `test-driven-development`, `using-agent-skills`.

### Repo-specific (1)

`conda-forge-expert` — the Part 1 skill. Drives every conda-forge task; `CLAUDE.md` mandates that
BMAD agents invoke it for any conda-forge work.

### Non-skill support directories (4)

These sit in `.claude/skills/` but contain **no `SKILL.md`** and are not skills:

| Directory | Contents | Status |
|---|---|---|
| `cf-atlas-legacy/` | `8.78.0/`, `active/` — versioned legacy skill store | intentional |
| `knowledge/` | shared knowledge notes (`agentskills-spec.md`, `provenance-tracking.md`, …) | intentional |
| `shared/` | `data/`, `references/`, `scripts/`, `health-check.md`, `_known-workarounds.yaml` | intentional |
| `data/` | only `conda-forge-expert/feedstock_cache/` with 3 stale JSON files | **stray** — clean-up deferred |

Only `data/` is a stray. The previous revision described it as the sole non-skill directory and
computed a "65 = 64 + 1 stray" total; both the total and the singular were wrong.

### Skill count math

```
  51  bmad-*            (includes 5 deprecated forwarding stubs)
  16  skf-*
  21  engineering-practice
   1  conda-forge-expert
 ───
  89  real skills
 + 4  non-skill support dirs (cf-atlas-legacy, data, knowledge, shared)
 ───
  93  directories in .claude/skills/
```

---

## Installer Layout (`_bmad/`)

> **This section replaces the previous revision's "BMAD Workflow Phases" section, which described a
> `_bmad/bmm/{1-analysis,2-plan-workflows,3-solutioning,4-implementation}/` directory tree. That
> tree does not exist.** In a 6.10.0 install `_bmad/bmm/` contains exactly two files. BMAD 6.x is
> skill-based: the workflows live in `.claude/skills/`, and the module directories carry only
> configuration and help indexes.

```
_bmad/
├── config.toml            # layer 1 (installer team) — [agents.*] descriptors live here
├── _config/
│   ├── manifest.yaml      # installation.version 6.10.0, modules core+bmm, ides [claude-code]
│   ├── skf-manifest.yaml  # the skf module's own manifest (v2.0.1, ~80 KB) — NOT in manifest.yaml
│   ├── skill-manifest.csv
│   ├── files-manifest.csv
│   └── bmad-help.csv
├── bmm/                   # config.yaml + module-help.csv  (NO phase directories)
├── core/                  # config.yaml + core module assets
├── custom/                # customization + active-project marker (below)
├── scripts/               # resolve_config.py · resolve_customization.py · memlog.py
└── skf/                   # the Skill Forge module tree (config.yaml, module.yaml, knowledge/, shared/, skf-*/)
```

The four-phase mental model (analysis → plan → solutioning → implementation) is still a fair
description of how a project *traverses* the skills, but it is not a directory layout and nothing
enforces it. Skills within each stage are independent and can run in any order — which is precisely
what the memlog-derivation model is designed to tolerate.

---

## Skill Customization Layer

`_bmad/custom/` holds **per-skill** TOML overrides separate from the global config layers, plus the
active-project marker:

```
_bmad/custom/
├── config.toml              # layer 3 (global custom team) — currently comments only
├── config.user.toml         # layer 4 (global custom user, gitignored) — absent
├── .gitignore               # ignores *.user.toml
├── .active-project          # active-project marker (gitignored, single line: "local-recipes")
├── bmad-agent-dev.toml      # per-skill override for Amelia
└── bmad-agent-pm.toml       # per-skill override for John
```

Per-skill overrides are resolved by **`resolve_customization.py`** — a **three-layer** merge,
highest priority first:

```
1. _bmad/custom/{skill-name}.user.toml    # personal, gitignored
2. _bmad/custom/{skill-name}.toml         # team/org, committed
3. {skill-root}/customize.toml            # skill defaults
```

Same merge rules as the global resolver. The skill name is derived from the basename of the skill
directory. This is how `bmad-review` gets its lens set, and how `bmad-generate-project-context` and
`bmad-document-project` resolve their `workflow` blocks (`activation_steps_prepend`,
`persistent_facts`, `on_complete`).

The two committed overrides both re-aim a BMAD persona at this factory:

- **`bmad-agent-dev.toml`** (Amelia) — 3 principles. Redefines "tests pass" for a recipe as
  `validate_recipe + optimize_recipe + scan_for_vulnerabilities + linux-64 build green` (not pytest,
  not vitest); implementation means MCP tool calls wherever possible, hand-edited YAML only when the
  structured action set doesn't cover the change; and a task is "done" when `submit_pr(dry_run=True)`
  passes — the real submit is a deliberate next step.
- **`bmad-agent-pm.toml`** (John) — 3 principles framing "product" as a conda-forge recipe or a
  `.claude/` tooling change.

### `_bmad/scripts/memlog.py`

The third stdlib-only helper, added since the previous revision. It is the **writer for every
Spec's `.memlog.md`**, and its three invariants are what make the derived Spec trustworthy:

1. **Append-only, chronological.** Entries land at the end in the order they happen. There is no
   edit or delete subcommand *by design*; history is never rewritten.
2. **Write-only / blind.** Every command is an atomic, context-free write (temp file, fsync,
   `os.replace`) that echoes the new state as one line of JSON, so the caller never re-reads the
   file mid-session. The single read is on resume, and the caller does it itself.
3. **No lifecycle status.** A memory log has no "complete" flag. Done / blocked / paused is itself a
   fact that happened, so it is recorded as an entry (`--type event`), never as mutable frontmatter.

The tool stays vocabulary-neutral; the host skill supplies meaning through the `--type` it passes
(`decision | constraint | capability | assumption | question | direction | note | event`). It is
explicitly **not a deliverable** — briefs, PRDs, decks, reports and Specs are all *derived* from it.

---

## bmad-loop — the Deterministic Harness

`bmad-loop` is an **external Python orchestrator** (github.com/bmad-code-org/bmad-loop), pinned
`bmad-loop >=0.9.0` in `pixi.toml`. It is not a skill and is not an agent: it is the governance
layer that drives agent sessions and refuses to advance a story that has not passed its gates.

### The cycle

```
   story spec ──▶ DEV ──▶ VERIFY ──▶ REVIEW ──▶ VERIFY ──▶ COMMIT ──▶ merge
                   │        │          │                                │
                   │        │          └── CRITICAL escalation ─▶ /bmad-loop-resolve (human)
                   │        └── deterministic gates ([verify] commands)
                   └── fresh tmux agent session per stage
```

Each stage runs in a **fresh tmux agent session** — hence `tmux >=3.7b_` is pinned in `pixi.toml`
specifically for this. The state machine is resumable; unresolvable contradictions escalate as
CRITICAL and pause the run for `bmad-loop-resolve`; work that plateaus is deferred to the ledger
rather than retried forever.

### In-repo configuration

```
.bmad-loop/
├── policy.toml            # 13.5 KB — the run contract (below)
├── bmad_loop_hook.py      # stdlib-only hook relay
└── runs/                  # gitignored run state (events, worktrees, ATTENTION files)
```

**`bmad_loop_hook.py`** writes exactly one atomic JSON event per hook into
`$BMAD_LOOP_RUN_DIR/events/` (temp + `os.replace`). It **no-ops with exit 0 unless both
`BMAD_LOOP_RUN_DIR` and `BMAD_LOOP_TASK_ID` are set**, so ordinary interactive sessions are
unaffected. It normalizes payload key styles across CLIs — snake_case (`claude`, `codex`),
`conversation_id` (cursor), camelCase `sessionId`/`transcriptPath` (copilot) — and always receives
the **canonical** event name as `argv[1]`, so the orchestrator only ever sees canonical events. It is
wired in `.claude/settings.json` on **SessionStart, Stop, SessionEnd, PreCompact**.

**`policy.toml`**, the values that actually govern a run:

| Block | Setting | Value |
|---|---|---|
| `[gates]` | `mode` | `per-story-spec-approval` (options: `none` \| `per-epic` \| `per-story-spec-approval`) |
| | `retrospective` | `notify` (`never` \| `notify` \| `auto`; `auto` unsupported in v1) |
| `[limits]` | `max_review_cycles` | 3 |
| | `max_dev_attempts` | 2 |
| | `session_timeout_min` | 180 (raised from 90 on 2026-07-12 — a keystone story hit the cap mid-work) |
| | `max_tokens_per_story` | 2,000,000 |
| `[adapter]` | `name` / baseline model | `claude` / sonnet |
| | per-stage | dev = sonnet · review = fable · triage = sonnet |
| `[scm]` | `isolation` | `worktree` |
| | `branch_per` | `story` |
| | `merge_strategy` | `squash` |
| | `delete_branch` / `keep_failed` / `rollback_on_failure` | true / true / true |
| | `max_parallel` | 1 (parallel fan-out unbuilt; values > 1 clamp to 1) |

### `[verify]` commands must be `--frozen`

```toml
commands = [ "pixi run --frozen -e pyforge-warden pyforge-warden-test" ]
```

An **unfrozen** re-solve inside a loop worktree panics `pixi-build-python` 0.8.3 (path-length
underflow at a ~250-character `workDirectory`) and, when it does succeed, rewrites `pixi.lock` with
worktree-absolute `file://` channel paths — which the squash-merge would then commit to `main`.
Frozen mode uses the tracked lock as-is. This is a hard requirement, not a preference.

### Branch conventions

| Pattern | Meaning |
|---|---|
| `loop/<slug>` | the loop-home branch, cut from `main` |
| `bmad-loop/<run-id>/<X-Y>-<story-slug>` | one per story attempt |
| `attempt-preserve/<run-id>-<sha>` | kept failed attempt (retain 20) |
| `attempt-preserve-dirty/*` | kept failed attempt with uncommitted work |

Merge subject shape: `Merge bmad-loop/<run-id>/<X-Y>-<slug> into <target>`. **The Guildhall's
done-detection parses exactly this string** — changing the merge subject silently breaks the
published dashboard.

### Loop homes — `scripts/bmad-loop-worktree`

Only **one** bmad-loop can run per checkout: the marker and the `_bmad-output` symlinks are
per-working-tree state, and two loop homes in one tree would also fight over HEAD. bmad-loop already
isolates each *story* in a worktree; this script adds the missing layer — **one git worktree per loop
home** — so loops for different BMAD projects run concurrently on one machine.

```bash
scripts/bmad-loop-worktree <slug>            # provision (idempotent) + print the launch line
scripts/bmad-loop-worktree --remove <slug>   # remove worktree (branch kept unless --force)
scripts/bmad-loop-worktree --verify <a> <b>  # provision both, assert isolation
scripts/bmad-loop-worktree --list            # loop-home worktrees + their active project
```

**Loop homes moved 2026-07-25 to a short root**: `DEFAULT_LOOP_HOME_ROOT = ~/.bmad-loops/<slug>`,
overridable with **`BMAD_LOOP_HOME_ROOT`** (set it to the repo's parent to restore the legacy sibling
layout). The reason is the same path-length trap as `--frozen`: the sibling layout put the build
`workDirectory` at roughly 238 characters versus roughly 197 under the short root, and long paths
panic `pixi-build-python`.

`--verify <a> <b>` provisions two homes and asserts, for each: the marker equals the slug; the
planning-artifacts symlink points at that slug; the Tier-3 `implementation-artifacts` resolves back
to the main checkout's canonical store; and the **main checkout's active project is unchanged**.

> **Known stale line (not fixed here — outside this doc's edit scope):** the script's own docstring,
> step 1, still describes the old `../<repo>-loop-<slug>` layout even though `DEFAULT_LOOP_HOME_ROOT`
> is now `~/.bmad-loops`. Code is correct; its docstring is not.

Each loop home resolves its own gitignored `.pixi/` on first `pixi run`, so first launch pays a
one-time solve. The **first** agent session in a new loop home also hits the Claude CLI folder-trust
prompt and sits until accepted — attach to the loop's tmux and accept once; later story worktrees
under the same home inherit the trust.

---

## Governance Detectors

Three deterministic, offline-safe detectors in `scripts/`. They only ever *report*; the reconcilers
are the BMAD skills themselves (see `SYNC-RUNBOOK.md`). None of them is a skill — that is the point.

### `bmad_drift_check.py` — the doc↔factory sync loop

Keeps the `_bmad-output/projects/local-recipes/` artifacts honest about volatile factory facts
(skill version, cf_atlas schema, MCP tool count, atlas phase count, pixi env count, gotcha range) and
filing conventions.

Finding kinds actually emitted by the current source (16, across three severities):

| Severity | Kinds |
|---|---|
| **HARD** | `pin-missing`, `archive-misplaced` (fixable), `stray-file` (fixable), `tracked-impl-artifact`, `uncovered`, `baseline-corrupt` |
| **DRIFT** | `pin-behind`, `spec-status-stale`, `deferred-stale`, `surface-changed`, `stale-rule`, `phase-list-stale`, `spec-unindexed`, `docs-specs-nonmd` |
| **INFO** | `count-stale`, `no-baseline` |

> The script's own module docstring still enumerates only the original seven (`pin-missing`,
> `archive-misplaced`, `stray-file`, `spec-status-stale`, `pin-behind`, `deferred-stale`,
> `count-stale`). The other nine were added to the code without updating the docstring — read the
> code, not the header.

**The pin gate is the repo's drift contract:** a doc re-syncs when the skill CHANGELOG **MINOR**
exceeds the doc's `source_pin`; PATCH bumps do not count as drift. `uncovered` is why a new file
under `planning-artifacts/` is a HARD finding — every project file must be classified in the
detector's `TRACKED` table (this doc is classified `living`, so the `count-stale` probes for
`schema v<N>`, `<N> MCP tools`, `G1–G<N>` and `<N> pixi envs` apply to it).

Modes: `--json` / `--groundtruth` (live facts as machine-readable JSON), `--integrity-only` (exit
non-zero on HARD only — what the meta-test uses), `--fix` (safe mechanical archive moves),
`--write-baseline` (re-stamp after a reconciliation). Enforced in the test suite by
`.claude/skills/conda-forge-expert/tests/meta/test_bmad_artifacts_in_sync.py` (integrity only).

### `spec_surface_check.py` — every file bound to a contract

Enforces the regenerable-factory contract (`spec-regenerable-factory` CAP-3): a Spec declares the
code it governs via `surface:` globs in `SPEC.md` frontmatter, and the checker enforces two things.

- **Coverage** — every tracked file matches at least one Spec surface **or** a reason-tagged entry in
  `scripts/spec_surface_allowlist.txt`. There are no silent exemptions: an allowlist line without a
  reason comment is not the convention, and a pattern that matches nothing is itself a finding.
- **Drift** — a governed file's content changed against the committed baseline
  (`scripts/.spec-surface-baseline.json`) while its Spec's `.memlog.md` did **not** move. That is
  code drifting out from under its contract.

Three drift modes via `surface-drift:` — `memlog` (default), `sentinel:<path>` (a nominated file must
move instead), `exempt` — plus `surface-drift-exclude:` for carve-outs.

Findings: `[ungoverned]`, `[stale-allowlist]`, `[no-baseline]`, `[drift]`. It exits non-zero on any
finding — **never false-green**.

**Specs are keyed `<project>/<spec>`, never the bare directory name.** `local-recipes/spec-pyforge-marshal`
and `pyforge-marshal/spec-pyforge-marshal` are legitimately different Specs with the same slug; a
bare-name key silently **dropped one surface** — a governance hole that emitted no finding at all.

Live state (2026-07-25): **22 specs · 7,888 tracked files · 6,323 governed · 1,567 allowlisted**,
verdict `OK: every tracked file governed or allowlisted; no drift`.

| Largest surfaces | Files | Drift mode |
|---|---|---|
| `local-recipes/spec-fleet-stewardship` | 2,809 | `exempt` |
| `pyforge-warden/spec-pyforge-warden` | 2,128 | memlog |
| `local-recipes/spec-modernist-identity` | 693 | memlog |
| `local-recipes/spec-packaging-factory` | 361 | `sentinel:.claude/skills/conda-forge-expert/CHANGELOG.md` |
| `pyforge-atlas/spec-pyforge-atlas` | 275 | memlog |

The packaging-factory sentinel is Rule 2 mechanized: a governed edit to the CFE skill surface that
moves neither the skill's CHANGELOG nor the Spec's memlog is a checker finding.

**Nine Specs currently govern 0 files**, and four of those declare **0 surface globs** at all
(`presenton-pixi-image/spec-presenton-pixi-image`, `pyforge-atlas/spec-upstream-discovery`,
`unity-data-stack/spec-unity-data-stack`, `wasm-analytics-stack/spec-wasm-analytics-stack`). The
other five declare globs that currently match nothing — expected for a Spec whose deliverable does
not exist yet, but worth watching: coverage is only meaningful because the allowlist is explicit.

### `llms_full_check.py` — dependency catalog drift

Detects drift between `pixi.toml` and `docs/reference/library-llms-full.md`:
`undocumented-dep` (an active dependency never mentioned in the catalog), `ghost-entry` (a versioned
catalog entry whose package left `pixi.toml`), `floor-drift` (a catalog version floor incompatible
with the manifest spec).

### Pixi tasks

| Task | Feature / env | What it does |
|---|---|---|
| `bmad-drift-check` | `local-recipes` | the sync-loop detector (`-- --fix`, `-- --integrity-only`, `-- --write-baseline`) |
| `bmad-groundtruth` | `local-recipes` | live factory facts as JSON |
| `spec-surface-check` | `local-recipes` | coverage + drift over Spec surfaces |
| `llms-full-check` | `local-recipes` | dependency-catalog drift |
| `dashboard-gen` / `dashboard-dryrun` | `local-recipes` | regenerate / preview the Guildhall data |
| `bmad-dashboard-install` | `bmad-ui` | install the official BMad Method UI VS Code extension |
| `mybmad` | `bmad-ui` | launch the MyBMAD web dashboard |
| ~~`bmad-preflight`~~ | `local-recipes` | **BROKEN** — see below |

The `bmad-ui` env is `linux-64` only and consumes locally-built packages from the
`./build_artifacts/linux64` channel alongside conda-forge.

> **`bmad-preflight` is broken.** Its command is `bash scripts/ensure-bmad-preflight.sh`, and that
> script **does not exist anywhere in the repo**. The task fails immediately on invocation. Either
> author the script or drop the task; do not cite it as a working pre-flight gate.

### BMAD dependency pins (`pixi.toml`)

`bmad-method >=6.10.0` · `bmad-builder >=2.1.0` · `bmad-creative-intelligence-suite >=0.2.1` ·
`bmad-dashboard >=1.2.2.dev0` · `bmad-loop >=0.9.0` ·
`bmad-method-test-architecture-enterprise >=1.19.1` · `bmad-method-wds-expansion >=0.4.3` ·
`bmad-module-template >=0.1.0` · `bmad-utility-skills >=2.0.0` · `bmad-labs-skills >=1.0.0.dev0`.
Plus `tmux >=3.7b_` for the loop's agent sessions.

---

## The Guildhall — the Program Console

`docs/dashboard/{index.html, data.js, generate.py}`, published to GitHub Pages at
<https://rxm7706.github.io/local-recipes/> by `.github/workflows/dashboard.yml` on **every push to
`main`** plus a **daily 06:17 UTC cron** backstop.

Two source modes:

| Mode | Where | Behaviour |
|---|---|---|
| `sprint-status` (default) | local only | reads each project's `sprint-status.yaml` and sets every mapped story to its full status (done / active / gated / pending). Richest view — but those files are Tier-3 **gitignored**, so this cannot run in CI. |
| `git` | CI | derives the DONE set from `main`'s commit subjects (bmad-loop merge commits + atlas `story(...)` / `GN:` / `HN:` commits). |

The `git` mode **only ever upgrades a story to `done`; it never downgrades.** In-flight `active` /
`gated` state is not derivable from history, so those stay at their committed baseline. That makes
the committed `data.js` the **seed and floor** — it carries the hand-curated narrative and the
in-flight/gated state, and CI can only add completions on top. The workflow deliberately does **not**
commit the regenerated data back; a commit-back would re-trigger the workflow.

Both modes also rescan `docs/dreams/*.md` frontmatter into `data["dreams"]` — the **Dreamscape**
lifecycle board, rendered above the per-project panels, with every Dream in its stage:
`seeded → in-deck → in-spec → realized`. That scan doubles as the Dream frontmatter detector: an
unknown or missing `status:` is warned about and passed through raw, bucketing under `seeded`.
Current distribution across the 26 Dreams: 3 seeded · 2 in-deck · 12 in-spec · 9 realized.

Below the Dreamscape sit per-project story / epic / gate / velocity panels for **6** projects —
warden, atlas, regen (local-recipes), herald, doctor, scribe.

The Guildhall **complements rather than replaces** the official BMad Method UI (the `bmad-dashboard`
VS Code extension and MyBMAD, both in the `bmad-ui` pixi env). The Guildhall is the published,
zero-install program view; the BMad Method UI is the in-IDE working view.

---

## BMAD ↔ conda-forge-expert Integration

This is the **most consequential** part of Part 4's design — it makes BMAD and CFE coordinate across
project lifecycles.

Codified in `CLAUDE.md` § "BMAD ↔ conda-forge-expert integration" as two always-on rules.

### Rule 1: BMAD must invoke `conda-forge-expert` for conda-forge work

Any BMAD agent (planning, dev, review, retro, persona) whose current task involves:
- creating/editing/validating/optimizing/building/submitting a conda recipe
- responding to a conda-forge build failure or review comment
- packaging a PyPI / npm / CRAN / CPAN / LuaRocks / GitHub source as a conda artifact
- working with `pin_subpackage`, `compiler()`, `stdlib()`, `noarch: python`, conda-forge selectors,
  rattler-build features
- interacting with pixi recipe-build / autotick / submit-pr tasks
- reading/modifying anything under `.claude/{skills,scripts,data}/conda-forge-expert/`

…**must invoke** the `conda-forge-expert` skill (via `Skill: conda-forge-expert`) before producing
recipe code or running recipe-related tooling. The skill's 10-step autonomous loop, Operating
Principles, Critical Constraints, and Build Failure Protocol are **authoritative** — they override
BMAD story instructions when they conflict, and the agent records the deviation in the story.

### Rule 2: Every conda-forge BMAD effort runs a retro

When a BMAD effort that did conda-forge work reaches closeout (final story complete, PR merged or
final review-comment resolved, or user marks effort done), the agent **must** run a retrospective
focused on the `conda-forge-expert` skill:

1. Invoke `bmad-retrospective` (or follow its protocol manually).
2. Review session logs, build failures, recipe diffs, reviewer comments to identify:
   - **Corrections** — guidance that was wrong, stale, misleading
   - **Refinements** — guidance that worked but was harder to apply than it should have been
   - **Additions** — patterns, constraints, gotchas, recipes encountered for the first time
3. Land findings as edits to `SKILL.md`, `reference/*.md`, `guides/*.md`, and a dated `CHANGELOG.md`
   entry with one line per finding.
4. **Bump skill version** per semver (PATCH for fixes/clarifications, MINOR for new gotchas/sections,
   MAJOR only for breaking workflow changes).
5. Save an auto-memory entry only if the finding crosses skill boundaries; skill-internal findings
   stay in the skill files.

**This rule is not optional and not deferrable.** An effort is not "done" until the retro lands. If
there are no novel findings (rare), the retro still produces a CHANGELOG entry stating "no skill
changes; verified existing guidance held for: <summary>".

Rule 2 is now partly **mechanized**: `spec-packaging-factory` governs the CFE skill surface with a
`sentinel` on `.claude/skills/conda-forge-expert/CHANGELOG.md`, so a governed edit that moves neither
the CHANGELOG nor the Spec memlog is a `spec_surface_check.py` finding.

---

## How a Typical Effort Flows

```
1. A Dream exists at docs/dreams/<slug>.md               (Tier 0 — mandatory, always-on)
                │
                ▼
2. bmad-spec distils it → planning-artifacts/specs/spec-<slug>/
   {.memlog.md (canonical), SPEC.md (derived), companions}      (Tier 2)
                │
                ▼
3. Active project confirmed — scripts/bmad-switch --current
   (parallel agents: BMAD_ACTIVE_PROJECT=<slug> instead; never call the switch)
                │
        ┌───────┴────────┐
        │ attended       │ unattended
        ▼                ▼
4a. bmad-quick-dev   4b. bmad-loop drives DEV→VERIFY→REVIEW→VERIFY→COMMIT
    / bmad-dev-story     in a loop home (~/.bmad-loops/<slug>), one worktree
                         + branch per story, squash-merged
                │
                ▼
5. Every agent reads project-context.md (foundational rules) on spawn
                │
                ▼
6. Rule 1 check: does this work touch conda-forge?
                │
       ┌────────┴────────┐
       │ Yes             │ No
       ▼                 ▼
7a. Invoke Skill:    7b. Proceed with
    conda-forge-expert   BMAD-only workflow
       │
       ▼
8. CFE skill's 10-step autonomous loop runs
       │
       ▼
9. Story merges → its story spec is PROMOTED from Tier-3 scratch into the
   tracked planning-artifacts/specs/ subdir and committed
       │
       ▼
10. Rule 2 check: was this a conda-forge effort? → bmad-retrospective updates
    SKILL.md / reference/ / guides/ / CHANGELOG; version bump per semver
       │
       ▼
11. Detectors re-run: bmad-drift-check (+ --write-baseline), spec-surface-check,
    llms-full-check. Guildhall refreshes on the next push to main.
```

---

## State Files & Auto-Memory

### `project-context.md`

`_bmad-output/projects/local-recipes/project-context.md` — foundational rules every BMAD agent reads
on spawn. Hand-maintained, pinned via `last_synced_skill_version` (currently
**`conda-forge-expert v8.79.1`**, re-grounded 2026-07-25). Drift contract: a MINOR bump triggers
re-sync, a PATCH does not — detected by `scripts/bmad_drift_check.py`, reconciled per
`SYNC-RUNBOOK.md`.

### Planning artifacts (Tier 2 — tracked)

`_bmad-output/projects/local-recipes/planning-artifacts/`:
- `PRD.md`, `architecture.md` + the four part docs (`architecture-conda-forge-expert.md`,
  `architecture-cf-atlas.md`, `architecture-mcp-server.md`, this file), `integration-architecture.md`
- `epics.md`, `project-overview.md`, `source-tree-analysis.md`, `development-guide.md`,
  `deployment-guide.md`, `index.md`, `project-parts.json`
- `implementation-readiness-report.md`, `validation-report-PRD.md`, the PRFAQ pair, `research/`
- **`specs/`** — the 8 local-recipes Specs, each a folder of `SPEC.md` + `.memlog.md` + companions
- `change-history/` — sprint-change-proposals from `bmad-correct-course` (9 archived)

Every tracked doc carries a `source_pin`; a missing or corrupt one is a HARD `pin-missing` finding.

### Implementation artifacts (Tier 3 — gitignored, nothing tracked)

`_bmad-output/projects/local-recipes/implementation-artifacts/`:
- `sprint-status.yaml` — the Guildhall's local source mode reads this
- `deferred-work.md` — cross-spec deferred items in DW format; carries a `Last reconciled:` stamp
  (a stale or missing stamp is a `deferred-stale` finding)
- `retros/` — archived per-effort retrospectives (frozen historical records)
- per-run bmad-loop scratch, including **draft story specs before promotion**

> The previous revision pointed at repo-root `docs/specs/*.md` as the canonical BMAD-consumable
> intake specs. That tier is **legacy** as of the 2026-07-23 restructure — the active contract is the
> Tier-2 Spec produced by `bmad-spec` from a Tier-0 Dream. `docs/specs/` (19 files) is retained for
> in-flight efforts only; author no new files there.

### Auto-memory

`~/.claude/projects/<repo-slug>/memory/` (gitignored, user-scope):
- `MEMORY.md` — index of saved feedback / project / reference entries
- `feedback_*.md` — durable preferences (pin loosening, `.bat` shim rules, BMAD multi-project
  pattern, skill disambiguation defaults, BMAD↔CFE integration rules, the CFE retro contract, the
  three-place rule for new scripts, the one-canonical-planning-artifact rule)
- `project_*.md` — durable project state (roadmap, incident postmortems, per-effort resume points)
- `reference_*.md` / `canonical_*.md` — pointers and canonical patterns

Four memory scopes, four lifetimes: **skill files** (Part 1) cross projects but are CFE-specific;
**project-context** crosses sessions but is project-specific; a Spec's **`.memlog.md`** crosses
sessions and is effort-specific and append-only; **auto-memory** crosses everything and is the user's
durable scratchpad.

---

## AI Provenance Tracking (FX.8) — implemented but NOT wired

`.claude/hooks/post-tool-call.py` exists (3.4 KB, stdlib-only). It builds a JSON provenance payload
for a tool call and POSTs it over `HTTPConnection` to `localhost` at `/api/provenance/call`,
discovering the port from a `*-provenance-port.txt` file.

**It does not run.** `.claude/settings.json` registers hooks on exactly four events — `SessionStart`,
`Stop`, `SessionEnd`, `PreCompact` — and all four point at `.bmad-loop/bmad_loop_hook.py`. There is
**no `PostToolUse` entry** in `.claude/settings.json`, in `.claude/settings.local.json`, or in the
user-scope `~/.claude/settings.json`.

> **Correction.** The previous revision of this doc stated that "the repository implements strict AI
> provenance tracking… This guarantees an auditable trail of all agentic interactions." The script is
> real; the guarantee is not. FX.8 is **implemented but unwired**, and no provenance trail is being
> produced today. Epic 3 story S9 in `epics.md` is satisfied as to the script's existence and
> unsatisfied as to its effect. Wiring it is a one-line `PostToolUse` addition to
> `.claude/settings.json` — deliberately left to a decision about whether the local receiver should
> be a hard dependency of every session.

The bmad-loop relay is the provenance surface that *is* live, and only for loop-spawned sessions: it
records SessionStart / Stop / SessionEnd / PreCompact with `session_id`, `transcript_path` and `cwd`
per task into the run directory.

---

## Why Multi-Project (vs. Multiple Repos)

**Pros**:
- One BMAD installation, one skill catalog → all 14 projects benefit from every skill improvement
- Cross-project knowledge (auto-memory) is shared automatically
- One `pixi.toml`, one set of 18 envs, one CI pipeline
- Sibling-project Specs can cross-reference each other freely — and the surface checker can bind
  *every* tracked file in the repo to exactly one contract, which is impossible across repos

**Cons**:
- Active-project resolution is required for every write operation (overhead)
- Mistakes (writing to the wrong project) are easier — and **silent**
- Per-project artifact privacy is convention, not enforcement
- The marker + symlinks are per-working-tree state, so concurrency needs an extra isolation layer

**Mitigations**, in the order they were learned:
1. The resolution chain (CLI flag → env var → marker → none) makes the choice explicit at every
   layer, and `scripts/bmad-switch --current` is a one-line sanity check.
2. `bmad-switch` re-points the symlinks **and** the marker, marker last, and warns on desync
   (2026-07-14, after the 10-hour desync near-miss).
3. `scripts/bmad-loop-worktree` gives each concurrent loop its **own** working tree, so per-tree
   state stops being contended (2026-07-15+).
4. Parallel *agents* inside one tree must not switch at all — literal paths plus
   `BMAD_ACTIVE_PROJECT`, and verify after writing (2026-07-25, after the 5-agent fan-out incident).

Mitigations 3 and 4 exist because 1 and 2 were not sufficient. Assume the next concurrency mode will
need a fifth.

---

## Integration Points (recap)

See `integration-architecture.md` for full cross-part contracts. Summary:

- **→ Part 1 (skill)**: Rule 1 mandates skill invocation for conda-forge work; Rule 2 mandates skill
  update via retro on closeout. Additionally `spec-packaging-factory` *governs* the Part 1 surface
  under `spec_surface_check.py`, with the skill CHANGELOG as its drift sentinel — the integration is
  now mechanically checked, not only conventionally required.
- **→ Part 1 indirectly via auto-memory**: `feedback_bmad_uses_cfe_skill.md` and
  `feedback_bmad_runs_cfe_retro.md` reinforce the rules across sessions.
- **→ Parts 2 and 3**: still no direct dependency at runtime — BMAD does not read `cf_atlas.db` or
  call MCP tools except through Part 1. But `bmad_drift_check.py` **reads** live Part 2/3 facts
  (schema version, MCP tool count, atlas phase count, gotcha range, pixi env count) to grade this
  doc set, so Part 4's governance layer has a read-only dependency on Parts 2 and 3.
- **→ `recipes/`**: governed by `local-recipes/spec-fleet-stewardship` (coverage only, drift
  `exempt`); per-recipe control remains the CFE 10-step loop.
- **→ `scripts/bmad-switch`**: user-facing CLI for marker + symlink management; reads
  `_bmad-output/projects/` to validate slugs.
- **→ `scripts/bmad-loop-worktree`**: provisions loop homes; asserts isolation from the main
  checkout.
- **→ the Guildhall**: consumes bmad-loop merge-commit subjects and Tier-3 `sprint-status.yaml`;
  publishes to GitHub Pages. Its done-detection is coupled to the loop's merge-subject format.

---

## Rebuild checklist for Part 4

1. **Run the BMAD installer** (`bmad-method >=6.10.0`) in a fresh repo. It writes:
   - `_bmad/config.toml` (Layer 1) and, optionally, `_bmad/config.user.toml` (Layer 2)
   - `_bmad/_config/` (`manifest.yaml`, `skill-manifest.csv`, `files-manifest.csv`, `bmad-help.csv`)
   - `_bmad/bmm/` and `_bmad/core/` — **config + help CSV only; no phase directories**
   - `_bmad/scripts/{resolve_config,resolve_customization,memlog}.py`
   - `.claude/skills/bmad-*` (51 skills at 6.10.0, including 5 deprecated forwarding stubs)
2. **Install the Skill Forge module** (`skf` v2.0.1) if wanted → `_bmad/skf/` +
   `_bmad/_config/skf-manifest.yaml` + 16 `.claude/skills/skf-*`. Point its `forge_data_folder` at a
   Tier-3 (gitignored) path.
3. **Add engineering-practice skills** (21): copy from upstream or author. Not BMAD-installer-managed.
4. **Add `conda-forge-expert`** (Part 1) under `.claude/skills/conda-forge-expert/` — the repo-specific
   addition that ties Parts 1–3 to BMAD.
5. **Create `_bmad/custom/`** with a `config.toml` and a `.gitignore` ignoring `*.user.toml`. Add
   per-skill `<skill-name>.toml` overrides as customizations accumulate (here: `bmad-agent-dev.toml`,
   `bmad-agent-pm.toml`).
6. **Create `_bmad-output/projects/<slug>/` per project** — each with `.bmad-config.toml` (committed),
   optional `.bmad-config.user.toml` (gitignored), `planning-artifacts/`, and a **gitignored**
   `implementation-artifacts/`. Gitignore Tier 3 *before* the first run.
7. **Create the two gitignored symlinks** `_bmad-output/{planning,implementation}-artifacts`. Without
   them every write-skill lands in repo-root `_bmad-output/`.
8. **Add `scripts/bmad-switch`** — must re-point both symlinks **and then** write the marker, warn on
   desync, and provision the Tier-3 backlink inside worktrees. (~320 lines, stdlib only.)
9. **Create `_bmad-output/PROJECTS.md`** — the multi-project index (switching, config layering, the
   project table, adding a project, reading/running against a non-active project).
10. **Seed Tier 0**: author `docs/dreams/<slug>.md` for each effort, then run `bmad-spec` to derive
    `planning-artifacts/specs/spec-<slug>/`. Nothing downstream is legitimate without a Spec.
11. **Author `project-context.md`** via `bmad-generate-project-context`, and give it a `source_pin`.
12. **Install the loop harness**: `bmad-loop >=0.9.0` + `tmux >=3.7b_` in `pixi.toml`;
    `.bmad-loop/policy.toml`; `.bmad-loop/bmad_loop_hook.py` wired in `.claude/settings.json` on
    SessionStart / Stop / SessionEnd / PreCompact; gitignore `.bmad-loop/runs/`. Make every
    `[verify]` command `--frozen`.
13. **Add `scripts/bmad-loop-worktree`** with a short `DEFAULT_LOOP_HOME_ROOT` (`~/.bmad-loops`) and a
    `BMAD_LOOP_HOME_ROOT` override. Long paths break the build before they break anything else.
14. **Add the detectors**: `scripts/bmad_drift_check.py`, `scripts/spec_surface_check.py` (+
    `spec_surface_allowlist.txt` and `.spec-surface-baseline.json`), `scripts/llms_full_check.py`;
    register the pixi tasks; add the meta-test that runs the drift check in `--integrity-only` mode.
    Key Specs `<project>/<spec>`, never bare.
15. **Add the Guildhall**: `docs/dashboard/{index.html,data.js,generate.py}` +
    `.github/workflows/dashboard.yml` (push to `main` + daily cron, `--source git`, no commit-back).
16. **Write `CLAUDE.md` + `AGENTS.md`** with the tier rules, the BMAD↔CFE integration rules (1 + 2),
    the parallel-agent switch prohibition, and the PR CI gates.
17. **Seed auto-memory** at `~/.claude/projects/<repo-slug>/memory/` with the always-on feedback
    entries. Without these, the rules silently lapse across sessions.

Rebuild order: Part 4 must exist for BMAD planning to happen at all, so it is the **first** part to
bootstrap on a clean repo even though Parts 1–3 are heavier in code. Steps 1–9 are the installation;
steps 10–15 are what turns it from an installation into a governed factory, and skipping them is how
a repo ends up with contracts nothing checks.
