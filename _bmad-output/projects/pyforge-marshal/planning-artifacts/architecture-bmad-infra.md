---
doc_type: architecture
part_id: bmad-infra
display_name: BMAD infrastructure
project_type_id: infra
date: 2026-09-06
source_pin: 'BMAD 6.12.0 / conda-forge-expert v8.86.4'
---

# Architecture: BMAD Infrastructure (Part 4)

> **Re-grounded 2026-08-24** (source_pin → **BMAD 6.11.0 / conda-forge-expert v8.84.0**; CAP-7 /
> marshal Story 25-7; living-doc cadence owned by **marshal** per SYNC-RUNBOOK). Corrected against
> the live install: BMAD-METHOD **6.11.0** (was pinned here as 6.10.0); **90 real skills** in
> `.claude/skills/` = 94 dirs − 4 nonskill; **52 `bmad-*`** (32 active + **20** deprecated v7-removal
> forwarders); **5** BMAD agents (Paige / `bmad-agent-tech-writer` **retired** in 6.11); renames
> `bmad-build` / `bmad-build-auto` / `bmad-project-context` / `bmad-deep-recon`; the **render
> pipeline** (`_bmad/scripts/render_skill.py` → immutable snapshots under `_bmad/render/`);
> nonskill dirs are `cf-atlas-legacy`, `cfe-recipe-generation`, `knowledge`, `shared` (not a stray
> `data/` as "current"). Active BMAD projects under `_bmad-output/projects/` are the **8** Smith
> stations (portfolio peers dissolved/archived earlier). Live factory facts (`bmad-groundtruth`):
> cf_atlas **schema v29**, **46 MCP tools**, **22** atlas phases, gotchas **G1–G110**, **26** pixi
> envs, CFE **v8.84.0**. Historical note: the 2026-07-25 pass had re-grounded an earlier 6.6.0-era
> draft onto the then-current 6.10.0 install — that revision is superseded here, not rewritten.

BMAD-METHOD is an AI-driven software development framework that this repository hosts as a
**multi-project installation**. A single BMAD installer (`_bmad/`) drives spec + planning + dev +
review + retro workflows for the **8** active Smith-station projects under
`_bmad-output/projects/<slug>/` (plus archived/dissolved peers retained only as history).

BMAD itself is **independent of conda-forge**, but this repo's **BMAD ↔ conda-forge-expert
integration rules** (codified in `CLAUDE.md`) make BMAD the entry point for any planned
conda-forge work, with mandatory retro closeouts that update the skill.

Part 4 is also where the repo's **governance** lives. In PyForge doctrine the Skill is the unit of
*execution* and the deterministic harness — bmad-loop, the sandbox/permission gates, the CI verify
gates, the drift and surface detectors — is the unit of *governance*, and is deliberately **not a
skill**. The hand that builds is never the gate that judges.

---

## Mission

> **Provide a multi-project BMAD-METHOD 6.11.0 installation — six-layer config merge, render-pipeline
> skill snapshots, marker+symlink active-project resolution, 90 installed skills, a deterministic
> loop harness, and the detectors that bind every tracked file to a Spec — so any of the 8 active
> Smith-station projects can be specced, planned, built, reviewed and retro'd without
> cross-contamination.**

> **Re-grounded 2026-09-05** (`source_pin` v8.84.0 → **conda-forge-expert v8.86.1**; hand pass per SYNC-RUNBOOK row 84 after the `bmad-drift` `pin-behind` warn). BMAD core stays **6.11.0** in `_bmad/` (the 6.12.0 core upgrade is planned, not applied), while the 2026-09-05 pixi upgrade sweep moves the `bmad-method` pin to **>=6.12.0** in `pixi.toml` / `environment.yaml` — the pin-fan-out step of that upgrade landing early. bmad-suite metapackage **2026.9.5** (v8.86.0 retro: `bmad-eval-quality` joined as the 14th recipe, `bmad-method-wds-expansion` retired). Live factory pin row (2026-09-05): schema **v29** · MCP **46** · atlas phases **22** · gotchas **G1–G113** · pixi envs **28** · CFE **v8.86.1**. CFE releases in the window: v8.82.0–v8.82.3 (`scripts/_paths.py` shared data-dir/repo-root helper; `_http.py` JFrog credential host-gate + public-host floor + credential-kind gating; G108), v8.83.0 (G109/G110; SelfExplainML publish flow in the cheatsheet), v8.84.0 (`github_updater.py --head` HEAD-advance), v8.84.1 (`bmad_suite_metapackage.py` marker-splice fix + test), v8.85.0 (3.11 floor; 438 recipes lost a redundant `context.python_min`, 47 unparseable recipes repaired; `tests/meta/test_dashboard_renders.py` retired), v8.85.1 (G82 / CI-provider table correction), v8.85.2 (`_paths.get_repo_root` marker walk; both compiled slices back in equivalence), v8.86.0 (G111–G113; HEAD mode increments `build.number`; `config/failure-catalog.yaml` regenerated), v8.86.1 (`tests/meta/test_recipe_maintainers_nonempty.py`; the G26 marker-split extension re-landed from orphaned commit `74bc80fe61`). live `bmad-groundtruth` 2026-09-05: schema **v29**, MCP tools **46**, atlas phases **22 executable / 23 cataloged** — all three unchanged since the 2026-07-29 pass; gotchas now **G1–G113** (v8.82.0 G108 `sys.executable` for internal subprocess calls; v8.83.0 G109 upstream can renumber past a dev snapshot, G110 npm bin maps are release-mutable; v8.86.0 G111 `noarch_platforms` is required for selector-carrying noarch recipes, G112 npm-from-commit-archive build with a clean prod reinstall, G113 same-version content changes bump `build.number`); pixi **28 envs / 31 features / 236 tasks (146 in `local-recipes`)** counted from `pixi.toml` (`[environments]` keys / distinct `[feature.<x>…]` names / `[feature.<x>.tasks.<t>]` headers); SKILL.md **4,287 lines**; **71 `.py` files under `scripts/`** (including the `_`-prefixed shared helpers) and **63 entries in `.claude/scripts/conda-forge-expert/`**; conda-forge's Python floor is **3.11** since 2026-09-02 (v8.85.0 — the generator now reads it from the installed pinning). Body figures below that predate this pass (18 / 20 / 26 envs, 17 features, 152 / 106 tasks, G1–G107 / G1–G110, 3,887 lines, 66 canonical scripts) are historical — read them against the live numbers here.

> **Re-grounded 2026-09-06** (`source_pin` → **BMAD 6.12.0 / conda-forge-expert v8.86.4**; marshal
> Story 30.3 / `spec-bmad-611-era-alignment` CAP-10, after steward Epic 14's first core apply —
> PR #1074 + #1076, commit `4fa185be56`). BMAD core + `bmm` bump to **6.12.0** in
> `_bmad/_config/manifest.yaml` (`steward upgrade bmad-core --target 6.12.0 --apply` ran the
> installer as sole writer). **`installShims: true`** — all 20 v6-shims plus
> `bmad-checkpoint-preview`'s forwarding shim to `bmad-walkthrough` stay installed; the
> `--no-shims` retirement is steward Story 14.9, **not yet run**. The custom `skf` module still
> reads **`version: main` / `source: custom`** in the manifest — **not yet pinned to v2.1.0**
> (that pin is Story 46.7, a different repo's pixi env; do not read the commit title
> "skf 2.1.0 re-coherent" as a manifest pin — it names the installer tool version used to
> reconcile the module, not the recorded module version). CFE bumped **v8.86.1 → v8.86.4**:
> v8.86.2 (strict duplicate-mapping-key `recipe.yaml` audit; 31 recipes fixed), v8.86.3 (the
> retired-BMAD-skill-ID regression guard's tracked-id tuple — which guards bare mentions of an
> id that is INSTALLED as a live forwarding shim, not one that is gone — gains
> `bmad-checkpoint-preview` as its 21st tracked id, since 6.12.0 renamed it to forward to
> `bmad-walkthrough` — marshal Story 30.1), v8.86.4 (`test_bmad_loop_skills_match_installed.py`
> proves the three vendored `bmad-loop-*` skills match the installed package — marshal Story
> 30.4). Live `bmad-groundtruth` 2026-09-06: schema **v29** · MCP **46** · atlas phases **22** ·
> gotchas **G1–G113** · pixi envs **28** — all five UNCHANGED since the 2026-09-05 pass. **Not
> touched this pass** (out of Story 30.3's scope; residual for a future full re-ground): the
> Mission statement above, the "Live factory pin" / "BMAD dependency pins" table rows, the
> Rebuild-checklist's `bmad-method` mentions, and the whole "Installed Skills" section below,
> INCLUDING the "At a Glance" table's own "Skill directories" / "Skill split" rows (lines
> ~109-110, immediately above this note) and the matching counts in the source-tree comment
> (~line 600) and the rebuild-checklist bullet (~line 1229) — all four cite the same stale
> **94** dirs / **52** `bmad-*` (32 active + **20** deprecated forwarders) figures. A spot-check
> during this pass found the live count is **121** directories / **109** `SKILL.md` files / **71**
> bare `bmad-*` dirs (new `bmad-agent-<station>` personas, `bmad-cis-*` Creative Intelligence
> Suite skills, and 7 `pyforge-<station>` skills have landed since 2026-09-05; separately, the
> "20 deprecated forwarders" sub-count is ALSO stale on its own terms — Story 30.1 grew the
> guard to 21 tracked ids the same week — but is left unchanged here rather than partially
> corrected, since the surrounding 52/32 totals cannot be recomputed with confidence without
> the same full re-audit). All of it is known-stale pending a dedicated re-audit, not just the
> "Installed Skills" section by itself.

Operationalized:
- Six-layer TOML config merge (installer team/user → custom team/user → project team/user) resolved
  by `_bmad/scripts/resolve_config.py`.
- **Render pipeline** — `_bmad/scripts/render_skill.py` materializes immutable, content-addressed
  skill snapshots under `_bmad/render/<skill>/<project-slug>-<root_hash>/<generation_hash>/` before
  an agent follows `workflow.md` (skills such as `bmad-build` invoke this on activation).
- Active-project resolution via CLI flag → env var → marker file → none, in priority order —
  **plus** the two `_bmad-output/` symlinks that write-skills actually resolve through.
- Per-project artifacts under `_bmad-output/projects/<slug>/{planning-artifacts,implementation-artifacts}/`,
  with the tier rules enforcing what may be tracked where.
- **The Spec** as the unit of contract, derived on every run from an append-only `.memlog.md`.
- **bmad-loop** (`>=0.11.0`) as the deterministic DEV → VERIFY → REVIEW → VERIFY → COMMIT harness,
  one isolated loop home per project.
- Three governance detectors (`bmad_drift_check.py`, `spec_surface_check.py`, `llms_full_check.py`)
  that make drift visible instead of silent.
- BMAD ↔ CFE integration rules in `CLAUDE.md` make every conda-forge-touching BMAD agent invoke the
  skill and run a retro on closeout.
- Living factory docs (`architecture-bmad-infra.md` + 8× `project-context.md`) re-ground on the
  **marshal** SYNC-RUNBOOK cadence (CAP-7 decision 2026-08-24) — not a per-station relay.

---

## At a Glance

| Field | Value |
|---|---|
| Installer root | `_bmad/` |
| Multi-project root | `_bmad-output/projects/` |
| BMAD-METHOD version | **6.12.0** (`_bmad/_config/manifest.yaml`; `_bmad/{bmm,core}/config.yaml` headers agree) |
| Install / last update | installed 2026-04-30, last updated 2026-09-06 |
| Installed modules | `core` 6.12.0, `bmm` 6.12.0 (both `source: built-in`) + `skf` **`main`** (`source: custom`, not yet pinned to v2.1.0 — Story 46.7) |
| Registered IDEs | `claude-code` |
| Skill directories | **94** in `.claude/skills/` = **90 real skills** + **4** nonskill support dirs |
| Skill split | **52** `bmad-*` (32 active + 20 deprecated forwarders) · **16** `skf-*` · **21** engineering-practice · **1** repo-specific (`conda-forge-expert`) |
| BMAD agents | **5** (analyst / architect / dev / pm / ux-designer) — tech-writer retired in 6.11 |
| Render pipeline | `_bmad/scripts/render_skill.py` → `_bmad/render/<skill>/…` immutable snapshots |
| Currently active | ephemeral — `scripts/bmad-switch --current` or `BMAD_ACTIVE_PROJECT` / marker; not a fixed doc field |
| Config merge layers | 6 (layers 2 and 4 are optional; both currently absent) |
| Per-skill customization layers | 3 (`resolve_customization.py`) |
| BMAD projects (active, this repo) | **8** Smith stations under `_bmad-output/projects/` |
| Specs (`planning-artifacts/specs/spec-*/SPEC.md`) | **107** (live count; grows with story-spec promotions) |
| Active-project marker | `_bmad/custom/.active-project` (gitignored, single-line slug) |
| Active-project symlinks | `_bmad-output/{planning,implementation}-artifacts` (gitignored) |
| Switcher CLI | `scripts/bmad-switch` (stdlib-only) — parallel agents: prefer `BMAD_ACTIVE_PROJECT` |
| Loop-home provisioner | `scripts/bmad-loop-worktree` |
| Config resolver | `_bmad/scripts/resolve_config.py` |
| Per-skill customization resolver | `_bmad/scripts/resolve_customization.py` |
| Skill renderer | `_bmad/scripts/render_skill.py` |
| Memory log writer | `_bmad/scripts/memlog.py` |
| Loop orchestrator | `bmad-loop >=0.11.0` (external, pinned in `pixi.toml`) |
| Program console | the **Guildhall** — `docs/dashboard/` → GitHub Pages |
| Live factory pin | schema **v29** · MCP **46** · atlas phases **22** · gotchas **G1–G110** · pixi envs **26** · CFE **v8.84.0** |
| Python requirement | 3.11+ for the config resolvers (stdlib `tomllib`); `memlog.py` declares `>=3.8` — no pip, no venv |

---

## The Tier Model

Everything starts with a Dream. BMAD turns it into the Spec. The Spec drives the build. The agent
and the framework are interchangeable; the tiers are not, and are never crossed.

| Tier | Location | Purpose | Git |
|---|---|---|---|
| **0 — Dream** | `docs/dreams/*.md` (**115** Dreams + a README as of this re-ground — recount before citing) | the raw human aspiration | tracked, permanent |
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

Every project has a `.bmad-config.toml`; all **8** active Smith stations are present.

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

**8 active Smith-station projects** under `_bmad-output/projects/` (atlas, doctor, herald, marshal,
mason, scribe, steward, warden). Every one has `.bmad-config.toml` + `planning-artifacts/` +
`implementation-artifacts/`. Earlier peers (`local-recipes` as a BMAD project slug, genesis,
deckcraft, unity-/wasm- stacks, …) were dissolved or archived — see `_bmad-output/PROJECTS.md`
and `archive/` for the historical map; do not invent a 14-project live tree from older docs.

```
_bmad-output/
├── PROJECTS.md                                # multi-project index
├── planning-artifacts        -> projects/<active>/planning-artifacts        (gitignored symlink)
├── implementation-artifacts  -> projects/<active>/implementation-artifacts  (gitignored symlink)
│
└── projects/
    ├── pyforge-atlas/   pyforge-doctor/   pyforge-herald/   pyforge-mason/
    ├── pyforge-scribe/  pyforge-steward/  pyforge-warden/
    │   ├── project-context.md             # station rulebook (legacy living doc; pin by hand)
    │   ├── .bmad-config.toml              # layer 5 (project team, committed)
    │   ├── planning-artifacts/            # PRD, architecture*, epics, specs/
    │   │   └── specs/spec-<slug>/{SPEC.md,.memlog.md,<companions>.md}
    │   └── implementation-artifacts/      # Tier 3 — gitignored
    └── pyforge-marshal/
        ├── project-context.md             # factory-wide rulebook (project_name: local-recipes)
        ├── SYNC-RUNBOOK.md                # ONLY here — marshal-owned detector → reconciler map
        ├── .bmad-config.toml
        ├── planning-artifacts/
        └── implementation-artifacts/
```

The eight are **Smith** projects — the PyForge Guild's stations, each productizing one capability:
Herald (visual media / the Design↔Code bridge), Marshal (orchestration, productizing bmad-loop),
Atlas (the cf_atlas data pipeline), Warden (dependency compliance), Mason (packaging, wrapping the
conda-forge-expert skill), Doctor (health and diagnostics), Scribe (team knowledge), Steward
(platform/ops). Living factory-doc re-ground for `architecture-bmad-infra.md` + all eight
`project-context.md` files is a **marshal** duty (SYNC-RUNBOOK / CAP-7), not a per-station relay.

### Spec ownership

Specs live under each station's `planning-artifacts/specs/spec-*/SPEC.md`. Live count as of this
re-ground: **107** SPEC.md files across the 8 projects (includes promoted per-story specs). Treat
the filesystem count as groundtruth — do not hard-code a portfolio total into other docs without
re-counting.

### Artifact naming is not uniform

A rebuild must not assume one shape across stations:

- **PRD**: some stations use a flat `prd.md` / `PRD.md`; most Smiths use a dated `prds/` subdirectory.
- **Architecture**: mix of flat `architecture.md` / `architecture-*.md` and dated `architecture/` trees.
- **Epics**: every active Smith carries `epics.md` (and often epic-scoped companions).
- **Per-story specs**: promoted into tracked `planning-artifacts/specs/` after merge (durable, not
  Tier-3). Counts move with every promotion — recount rather than cite a frozen portfolio total.

### `_bmad-output/PROJECTS.md`

Sections: *Active project switching* · *Config layering* (the 6-row table) · *Projects* (slug /
status / description for the live stations + dissolved/archived peers) · *Adding a new project* ·
*Reading another project's artifacts (without switching)* · *Running a skill against a non-active
project (without switching globally)*.

Reading another project's artifacts needs no switch — read the file path directly. Only **writes**
need the active project set (or `BMAD_ACTIVE_PROJECT=<slug>` / `--project` without touching the
shared switcher).

---

## Installed Skills

`.claude/skills/` holds **94 directories = 90 real skills + 4 nonskill support directories**. A real
skill is a directory containing `SKILL.md`; the resolver and Claude Code's `Skill` tool read them
at runtime.

| Family | Count |
|---|---|
| `bmad-*` (BMAD installer, bmm + core) | **52** (32 active + **20** deprecated v7-removal forwarders) |
| `skf-*` (Skill Forge module) | **16** |
| Engineering-practice (not BMAD-installer) | **21** |
| Repo-specific | **1** (`conda-forge-expert`) |
| **Total real skills** | **90** |

### BMAD agent personas (5 — bmm module; tech-writer retired in 6.11)

Defined in `_bmad/config.toml` under `[agents.bmad-agent-<role>]`, each with `name`, `title`, `icon`,
`description`. Invoked via the `bmad-agent-<role>` skill name.

| Agent | Role | Display name | Icon |
|---|---|---|---|
| `bmad-agent-analyst` | Business Analyst | Mary | 📊 |
| `bmad-agent-architect` | System Architect | Winston | 🏗️ |
| `bmad-agent-dev` | Senior Software Engineer | Amelia | 💻 |
| `bmad-agent-pm` | Product Manager | John | 📋 |
| `bmad-agent-ux-designer` | UX Designer | Sally | 🎨 |

**Historical gloss (6.11):** `bmad-agent-tech-writer` / **Paige** shipped in earlier 6.x installs and
is **retired** — no skill directory and no `[agents.*]` entry remain. Do not invoke or document it
as current.

**These five are not the same layer as the Smiths.** The eight Smiths (Herald · Marshal · Atlas ·
Warden · Mason · Doctor · Scribe · Steward) are the *factory's stations* — accountable owners of a
capability, each with its own project and Spec. Mary, John, Winston, Sally and Amelia are
**Marshal's sub-agents on the floor**: personas the orchestration station spawns inside a single
effort. Conflating the two layers is the standard reading error; the Smiths own capabilities, the
BMAD agents own turns of work.

### Spec & planning (active)

`bmad-spec` (**the Spec producer**), `bmad-prd`, `bmad-architecture`,
`bmad-create-epics-and-stories`, `bmad-ux`, `bmad-product-brief`, `bmad-prfaq`,
`bmad-sprint-planning` (6.11 readiness gate absorbed the former
`bmad-check-implementation-readiness` surface).

### Discovery / customization (active)

`bmad-project-context` — **6.11 successor** of `bmad-document-project` /
`bmad-generate-project-context`. It maintains a **verified `AGENTS.md` block only**; it does **not**
produce brownfield living docs (`architecture-*`, `project-overview`, `project-context.md`). Those
are re-grounded by hand / plain agents on the marshal SYNC-RUNBOOK cadence. Also: `bmad-customize`.

### Research (active)

`bmad-deep-recon` — **6.11 consolidation** of the former domain / market / technical research
skills (those three IDs survive only as deprecated forwarders).

### Implementation (active)

`bmad-build` (was `bmad-quick-dev`) — implement any intent against existing conventions.
`bmad-build-auto` (was `bmad-dev-auto`) — **one iteration of an unattended development loop**.
`bmad-forge-idea` — persona-driven interrogation that hardens or kills an idea cheaply.

`bmad-build-auto` ends a turn only by halting with an explicit terminal `status`, written either
into `{spec_file}`'s frontmatter (plus an `## Auto Run Result` section) or, when no spec file is
known, into a result file under implementation-artifacts. Subagents must be invoked
**synchronously**.

Many active skills (`bmad-build` among them) **must** run
`uv run …/_bmad/scripts/render_skill.py --project-root … --skill …` on activation and then follow
the printed absolute `workflow.md` — they do not execute source Markdown in-place.

### Review (active + shims)

`bmad-review` is the consolidated multi-lens reviewer (adversarial, edge-case-hunter,
verification-gap, structure, prose). `bmad-code-review` remains a separate adversarial code-review
workflow. The former standalone lens / editorial skill IDs are deprecated forwarders (see table).

### Sprint + retro + loop support

`bmad-sprint-planning`, `bmad-correct-course`, `bmad-retrospective`, `bmad-loop-setup`,
`bmad-loop-resolve`, `bmad-loop-sweep`. (`bmad-sprint-status` is a deprecated forwarder.)

### Process / facilitation

`bmad-advanced-elicitation`, `bmad-brainstorming`, `bmad-walkthrough`, `bmad-help`,
`bmad-party-mode`, `bmad-qa-generate-e2e-tests`. (**6.11 removed `bmad-index-docs`** with no
replacement — maintain `index.md` by hand. **`bmad-shard-doc` is also gone** — no skill directory
and no deprecated forwarder; do not invoke it.)

### Deprecated `bmad-*` skills (21 — committed v7 removal list)

These are the IDs the CAP-1 regression guard tracks. Each ships a stub `SKILL.md` that forwards to
its 6.11 successor. They still occupy skill directories and count toward the 52.

| Deprecated shim | Forwards to / note |
|---|---|
| `bmad-quick-dev` | `bmad-build` |
| `bmad-dev-auto` | `bmad-build-auto` |
| `bmad-create-story` | `bmad-build` |
| `bmad-dev-story` | `bmad-build` |
| `bmad-create-prd` | `bmad-prd` (create) |
| `bmad-edit-prd` | `bmad-prd` (update) |
| `bmad-validate-prd` | `bmad-prd` (validate) |
| `bmad-create-architecture` | `bmad-architecture` |
| `bmad-market-research` | `bmad-deep-recon` |
| `bmad-domain-research` | `bmad-deep-recon` |
| `bmad-technical-research` | `bmad-deep-recon` |
| `bmad-sprint-status` | `bmad-sprint-planning` (status surfaces) |
| `bmad-document-project` | `bmad-project-context` (AGENTS.md only — not brownfield docs) |
| `bmad-generate-project-context` | `bmad-project-context` |
| `bmad-review-adversarial-general` | `bmad-review` |
| `bmad-review-edge-case-hunter` | `bmad-review` |
| `bmad-review-verification-gap` | `bmad-review` |
| `bmad-editorial-review` | `bmad-review` |
| `bmad-editorial-review-prose` | `bmad-review` |
| `bmad-editorial-review-structure` | `bmad-review` |
| `bmad-checkpoint-preview` | `bmad-walkthrough` |

Shims stay installed until the v7 cut; live instruction text must use the 6.11 names (historical
mentions keep a same-line gloss).

### Skill Forge — `skf-*` (16)

Separately managed module (`_bmad/skf/`, version **2.1.0** per `_bmad/_config/manifest.yaml`
module `skf` — prefer that over `_bmad/_config/skf-manifest.yaml`, which can lag). Compiles
repositories and docs into version-pinned, provenance-backed agent skills. Its
`forge_data_folder` points at
`_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data` (Tier-3, gitignored).

`skf-setup`, `skf-forger`, `skf-analyze-source`, `skf-brief-skill`, `skf-create-skill`,
`skf-quick-skill`, `skf-create-stack-skill`, `skf-verify-stack`, `skf-refine-architecture`,
`skf-test-skill`, `skf-audit-skill`, `skf-update-skill`, `skf-export-skill`, `skf-rename-skill`,
`skf-drop-skill`, `skf-campaign`.

### Engineering practice (21 — not BMAD-installer)

`api-and-interface-design`, `browser-testing-with-devtools`, `ci-cd-and-automation`,
`code-review-and-quality`, `code-simplification`, `context-engineering`,
`debugging-and-error-recovery`, `deprecation-and-migration`, `documentation-and-adrs`,
`frontend-ui-engineering`, `git-workflow-and-versioning`, `idea-refine`,
`incremental-implementation`, `performance-optimization`, `planning-and-task-breakdown`,
`security-and-hardening`, `shipping-and-launch`, `source-driven-development`,
`spec-driven-development`, `test-driven-development`, `using-agent-skills`.

### Repo-specific (1)

`conda-forge-expert` — the Part 1 skill (**v8.84.0** at this re-ground). Drives every conda-forge
task; `CLAUDE.md` mandates that BMAD agents invoke it for any conda-forge work.

### Nonskill support directories (4)

These sit in `.claude/skills/` but contain **no top-level `SKILL.md`** and are not skills:

| Directory | Role |
|---|---|
| `cf-atlas-legacy/` | versioned legacy skill store (`active/`, pinned versions) |
| `cfe-recipe-generation/` | recipe-generation support tree (not a Claude Skill entry) |
| `knowledge/` | shared knowledge notes |
| `shared/` | shared `data/`, `references/`, `scripts/`, health-check helpers |

A prior revision listed a stray top-level `data/` as a current nonskill directory — **that is not
current**. Do not count `data/` as one of the four.

### Skill count math

```
  52  bmad-*            (32 active + 20 deprecated forwarders)
  16  skf-*
  21  engineering-practice
   1  conda-forge-expert
 ───
  90  real skills
 + 4  nonskill dirs (cf-atlas-legacy, cfe-recipe-generation, knowledge, shared)
 ───
  94  directories in .claude/skills/
```

---

## Installer Layout (`_bmad/`)

> BMAD 6.x is skill-based: workflows live in `.claude/skills/`, and the module directories carry
> configuration, help indexes, and (in 6.11) the **render** snapshot tree. The old
> `_bmad/bmm/{1-analysis,2-plan-workflows,…}/` phase directory tree does not exist.

```
_bmad/
├── config.toml            # layer 1 (installer team) — [agents.*] descriptors live here
├── _config/
│   ├── manifest.yaml      # installation.version 6.12.0, modules core+bmm+skf, ides [claude-code]
│   ├── skf-manifest.yaml  # Skill Forge detail manifest
│   ├── skill-manifest.csv
│   ├── files-manifest.csv
│   └── bmad-help.csv
├── bmm/                   # config.yaml + module-help.csv  (NO phase directories)
├── core/                  # config.yaml + core module assets
├── custom/                # customization + active-project marker (below)
├── render/                # gitignored / local — immutable skill snapshots from render_skill.py
├── scripts/               # resolve_config.py · resolve_customization.py · memlog.py · render_skill.py
└── skf/                   # Skill Forge module tree
```

### Render pipeline (`render_skill.py`)

6.11 skills that ship a `workflow.md` (and related Markdown sources) are **not** executed from the
mutable skill tree. On activation the skill runs:

```bash
uv run --no-cache "{project-root}/_bmad/scripts/render_skill.py" \
  --project-root "{project-root}" --skill "{skill-root}"
```

`render_skill.py`:

1. Loads the skill's declared Markdown sources + six-layer central config + three-layer
   per-skill customization (`customize.toml` / `_bmad/custom/<skill>.toml`).
2. Substitutes `{{config.*}}`, `{{.token}}`, `{workflow.*}`, and `[[bmad-snapshot:…]]` tokens.
3. Publishes an **immutable** snapshot under
   `_bmad/render/<skill-name>/<project-slug>-<root_hash>/<generation_hash>/` with a content-addressed
   `manifest.json` (renderer SHA, source SHAs, resolved values, output hashes).
4. Prints `read and follow <absolute-path>/workflow.md` — the agent follows **that** file only.

Snapshots are regenerable local artifacts (typically gitignored). Re-running with identical inputs
reuses the same generation hash; changing config, customization, or skill sources yields a new
directory. This is how policy knobs and project-layer TOML reach the agent without mutating the
installed skill package.

The four-phase mental model (analysis → plan → solutioning → implementation) remains a fair
description of how a project *traverses* the skills, but it is not a directory layout.

---

## Skill Customization Layer

`_bmad/custom/` holds **per-skill** TOML overrides separate from the global config layers, plus the
active-project marker:

```
_bmad/custom/
├── config.toml              # layer 3 (global custom team) — currently comments only
├── config.user.toml         # layer 4 (global custom user, gitignored) — absent
├── .gitignore               # ignores *.user.toml
├── .active-project          # active-project marker (gitignored, single-line slug)
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

Same merge rules as the global resolver. The skill name is the basename of the skill directory.
This is how `bmad-review` gets its lens set, and how `bmad-project-context` (and other rendered
skills) resolve `{workflow.*}` tokens into the snapshot `render_skill.py` publishes.

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

`bmad-method >=6.11.0` · `bmad-builder >=2.1.0` · `bmad-creative-intelligence-suite >=0.2.1` ·
`bmad-dashboard >=1.2.2.dev0` · `bmad-loop >=0.11.0` ·
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
4a. bmad-build       4b. bmad-loop drives DEV→VERIFY→REVIEW→VERIFY→COMMIT
    / bmad-build-auto    in a loop home (~/.bmad-loops/<slug>), one worktree
                         + branch per story, squash-merged
                         (deprecated shims: bmad-quick-dev / bmad-dev-auto)
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
**`conda-forge-expert v8.80.0`**, re-grounded 2026-07-25). Drift contract: a MINOR bump triggers
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

1. **Run the BMAD installer** (`bmad-method >=6.11.0`) in a fresh repo. It writes:
   - `_bmad/config.toml` (Layer 1) and, optionally, `_bmad/config.user.toml` (Layer 2)
   - `_bmad/_config/` (`manifest.yaml`, `skill-manifest.csv`, `files-manifest.csv`, `bmad-help.csv`)
   - `_bmad/bmm/` and `_bmad/core/` — **config + help CSV only; no phase directories**
   - `_bmad/scripts/{resolve_config,resolve_customization,memlog,render_skill}.py`
   - `.claude/skills/bmad-*` (52 skills at 6.11.0: 32 active + 20 deprecated v7-removal forwarders;
     5 agent personas — tech-writer retired)
2. **Install the Skill Forge module** (`skf` v2.1.0 per `manifest.yaml`) if wanted → `_bmad/skf/` +
   `_bmad/_config/skf-manifest.yaml` + 16 `.claude/skills/skf-*`. Point `forge_data_folder` at a
   Tier-3 path (here: `_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data`).
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
11. **Author or refresh agent instructions** via `bmad-project-context` (writes the verified
    `AGENTS.md` block). Living brownfield docs (`architecture-*`, station `project-context.md`) are
    re-grounded by hand / plain agents — give each a `source_pin`; marshal owns the cadence.
12. **Install the loop harness**: `bmad-loop >=0.11.0` + `tmux >=3.7b_` in `pixi.toml`;
    `.bmad-loop/policy.toml` (or marshal-rendered harness policy); gitignore `.bmad-loop/runs/`.
    Make every `[verify]` command `--frozen`. Skills that render must be able to write `_bmad/render/`.
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
