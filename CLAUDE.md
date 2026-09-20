# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The cross-tool contract lives in `AGENTS.md` (the verified `bmad:context` block, the team-memory
boot line, the pre-PR checklist); with a `CLAUDE.md` present, Claude Code reads it only through the
import below — keep this line bare (`spec-pyforge-scribe` CAP-27).

@AGENTS.md

## Interactive session path

`marshal factory dispatch` / `spin` are the **measured** path (policy-rendered, journaled,
benchmarked). An interactive Claude Code session on the shared checkout is the **documented
convenience path** — the same instruments, wired by hand, from repo root:

```bash
caveman-install --only claude --with-hooks   # once per machine: output-compression skill + hooks
headroom wrap claude --code-memory none      # launch this session behind the wire-compression proxy
```

Neither path gets a second kit, and the interactive path gets no separate benchmark (operator
decision 2026-09-16; `spec-pyforge-marshal` CAP-195, folded from `spec-marshal-token-economy`
CAP-22). Once the session is open, retrieve/recall discipline replaces wholesale `epics.md` /
PRD loads — see AGENTS.md § *Scribe recall (session path)* and `marshal context retrieve`.

**Behavioural guidelines** — the five principles every harness follows (Think before coding · Simplicity first · Surgical changes · Goal-driven execution · Dream to code, always) live in `AGENTS.md` § *Behavioural guidelines (every harness)*, imported above; the `conda-forge-expert` skill specialises them for recipe work and the BMAD skills for planning/dev. Not restated here (scribe CAP-27, point-don't-copy; CAP-29 collapsed the duplicate).

---

## Project Overview

This repository is an **AI-assisted, semi-autonomous packaging factory** for conda-forge recipes. It mirrors the workflow of `conda-forge/staged-recipes` but is supercharged with a suite of custom tools that enable Claude to handle nearly the entire recipe lifecycle, from generation and security scanning to building, debugging, and maintenance.

This is a multi-skill repo: conda-forge recipe work uses the `conda-forge-expert` skill (loads on-demand), and BMAD-driven planning/dev for sibling projects lives under `_bmad-output/projects/`.

**Critical Rule**: Do not mix `meta.yaml` and `recipe.yaml` formats in the same build run. The tooling will reject mixed-mode runs.

**Critical Rule — PR CI gates (ALWAYS-ON, every PR to `rxm7706/local-recipes`):** the inherited staged-recipes linter reds two ways that Claude must pre-empt at PR open/update time (do NOT wait for red CI):
1. **Any change outside `recipes/`** (docs, `.github/`, `docs/specs/`, `src/`, `prototypes/`, `pixi.toml`, dashboards — anything but `recipes/**`) → **add the `maintenance` label**: `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`.
2. **`pixi.toml` changed** → regenerate + commit `environment.yaml`: `pixi project export conda-environment -e build > environment.yaml` (this sync check is UNGATED — the `maintenance` label does not suppress it). Also fix `main` directly whenever a `pixi.toml` dep change lands there.
3. **`pixi.toml`/`pixi.lock` changed** → also run `pixi run -e pyforge-guild pyforge-station-tests` locally first: that touches every PyForge station's "shared surface" per `.github/workflows/pyforge-station-tests.yml`, so `pyforge-core` + ALL 8 station suites fire together in CI, not just the one you meant to touch. Locally the `pyforge-core` leg runs first and fails fastest; in CI `core-test` is a concurrent peer of the station jobs that fires on any shared-surface OR any single-station change (its sole-ownership meta-tests scan every station's tree). Found live 2026-09-14: a 5-day GitHub Actions billing outage (see `.claude/memory/` project notes) let ~260 PRs merge with this workflow never actually running; the next `pixi.toml` push afterward surfaced 5 days of accumulated doctor/marshal/mason drift all at once, entirely unrelated to that PR's own diff.

4. **Before pushing ANY non-recipe branch → `pixi run -e pyforge-guild pr-preflight`.** One command covering the four lanes that actually red a PR: `detectors-ci`, `test-ci` (the CFE regression suite — this lane owns the spec-surface meta-test), `pyforge-station-tests` (`pyforge-core` + all 8 stations), and `pyforge-station-coverage-gates` (touched-module coverage floors). Added 2026-09-14 after PR #1355 went red on two lanes with **no local equivalent at all**: a stale spec-surface baseline (a scoped `--write-baseline` was taken, then a governed file was edited *again*, silently invalidating it — a stamp is only valid until the next edit of any file in that spec's surface), and a coverage floor that only measures modules a branch *touches*, so `board.py` sat at 70.1% for weeks and surfaced on an unrelated edit. Neither was reachable from `detectors` or `pyforge-station-tests`. Not covered by it: container/guild-container (needs Docker/podman), atlas's Chromium/DuckDB/WASM setup, herald's browser check, and scribe's Postgres (`scribe-pg-up` first).

**Reading a detector's result: never through a pipe** — see `docs/reference/judgement-vocabulary.md` § *Severity and exit codes*. This produced a false green on 2026-09-14 that CI then caught.

Recipe-only PRs (touching only `recipes/**`) need neither.

**Repo surfaces beyond `recipes/`:** the PyForge Guild station code (atlas, doctor, herald, marshal, mason, scribe, steward, warden, plus `pyforge-core` / `pyforge-testing-kit` and the `django-*` UI packages) lives in `src/shared/packages/pyforge-*`, each with its own pixi environment and `pyforge-<station>-test` / `-build` tasks. The Vizro/BSL fleet dashboard is part of pyforge-atlas (`src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/`); the old GuildHall Pages console is retired and `retired-console-check` fails CI if it is reintroduced.

## Common Commands

Everything runs through pixi (`pixi.toml` is the task registry; `pixi task list -e pyforge-guild` for the Guild set, `-e local-recipes` for the full set). **`pyforge-guild` is the session default** for every agent and harness doing planning-chain work (detectors, ledger sync, surface stamps, `fleet-picture`, marshal dispatch/spin, the token-economy kit — ~860 MB; steward Story 63.1, `spec-pyforge-steward` CAP-5); `local-recipes` (10 GB) is Mason's recipe-factory environment and includes every Guild task, so `-e local-recipes <guild task>` still works. `scribe capture` / `scribe recall` run in `pyforge-guild` too (scribe Story 19.2, 2026-09-19); only `scribe graph compile` with the graphify / cocoindex / postgres extras needs `-e pyforge-scribe`. Full recipe-lifecycle reference: `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md`.

**Recipes:**
- Build one recipe natively (recommended default): `pixi run -e local-recipes recipe-build recipes/<name>` — rattler-build, auto-detects platform, layers conda-forge-pinning so `${{ python_min }}` resolves like upstream CI. Variants: `recipe-build-docker`, `recipe-build-cross`.
- Lint all recipes: `pixi run -e conda-smithy lint` (CI-parity alternative: `pixi exec conda-smithy recipe-lint`).
- Generate a recipe: `pixi run -e grayskull pypi <pkg>` (v1 format), or `pixi run -e local-recipes generate-recipe`; `generate-npm` / `generate-cran` / `generate-cpan` / `generate-luarocks` for other ecosystems.
- Full staged-recipes-style build of changed recipes: `python build-locally.py`.

**Tests:**
- CFE skill suite: `pixi run -e local-recipes test-skill` — scope with `--unit` / `--integration` / `--meta`, single test via `--keyword <expr>`; network tests are opt-in (`-m network`).
- A PyForge station: `pixi run -e pyforge-<station> pyforge-<station>-test` (e.g. `pixi run -e pyforge-warden pyforge-warden-test`).
- **`pyforge-core` + all 8 PyForge stations** (mirrors `.github/workflows/pyforge-station-tests.yml`'s `core-test` + per-station jobs): `pixi run -e pyforge-guild pyforge-station-tests`. The `pyforge-core` leg runs first (Story 52.2: the sole-ownership meta-tests scan every station's tree, so CI fires it on any station change, not only shared surface). That workflow runs every station together whenever `pixi.toml`/`pixi.lock`/`pyforge-core`/`pyforge-testing-kit` changes ("shared surface") — easy to miss locally since most PRs touch only one station. Run this before pushing any change to those shared files; covers `pyforge-core-test` and each station's own `-test` task only, not atlas's Chromium/DuckDB/WASM setup, herald's browser check, or scribe's Postgres+pgvector service (`scribe-pg-up`).
- Dashboard structural gate: `pixi run -e local-recipes dashboard-dryrun` — builds the Dashboard object offline, but also runs the Playwright e2e/ARIA suite, which launches a real local server (not fully offline despite the gate's name).

**Health / status:**
- All detectors: `pixi run -e pyforge-guild detectors` (CI subset: `detectors-ci`); exit 0 = pass, 1 = findings, 2 = could-not-run (never a false green).
  A single doctor-sourced task — `bmad-drift-check`, `story-status-check`, `spec-surface-check`, `capability-effect-check` and the rest of `python -m pyforge.doctor.sources <name>` — projects through `pyforge.doctor.verdict.exit_code_for`, a **different** exit-code domain than the aggregator above. See `docs/reference/judgement-vocabulary.md` § *Severity and exit codes* for the full domain table and the `2`-inversion trap.
- Fleet progress: `pixi run -e pyforge-guild fleet-picture` — read-only, never gating; paste its stdout verbatim, not reformatted.

## BMAD Method Documentation

The BMAD Method is an AI-driven software development framework used in this project.

- **Local snapshot** (offline, last of its kind): `.claude/docs/bmad-method-llms-full.txt` — captured 2026-08-21 from the 6.11-era docs. BMAD-METHOD 6.12.0 (2026-09-03) **discontinued** `llms.txt` / `llms-full.txt`; there is no live source to fetch any more.
- **Live docs**: https://docs.bmad-method.org/ (task-organised since 6.12) and the installed skills themselves under `.claude/skills/bmad-*/` — the skill files are the authoritative 6.12 behaviour, the snapshot is historical.

Reference the snapshot with `@.claude/docs/bmad-method-llms-full.txt` only for pre-6.12 background; check the installed skill first.

### Multi-Project Pattern (this repo hosts multiple BMAD projects)

This repository uses a single BMAD installation to drive multiple projects. Each project has its own subdirectory under `_bmad-output/projects/<slug>/` containing planning artifacts, implementation artifacts, project context, and project-scoped config overrides. See **`_bmad-output/PROJECTS.md`** for the index and detailed documentation.

**At session start with the user**, ask which project they're working on (or check `scripts/bmad-switch --current`) before invoking BMAD skills that write artifacts. Reading another project's artifacts is fine without switching — read directly from the file path.

**Active-project resolution priority** (used by `_bmad/scripts/resolve_config.py`):
1. `--project <slug>` per-call CLI flag (highest priority).
2. `BMAD_ACTIVE_PROJECT` environment variable.
3. `_bmad/custom/.active-project` marker file (managed by `scripts/bmad-switch`, gitignored).
4. None — only global config layers resolve; skills fall back to repo-root `_bmad-output/`.

**The marker is only half the switch — two gitignored symlinks are the other half:**

```
_bmad-output/planning-artifacts       -> projects/<slug>/planning-artifacts
_bmad-output/implementation-artifacts -> projects/<slug>/implementation-artifacts
```

`_bmad/bmm/config.yaml` hard-codes `planning_artifacts: "{project-root}/_bmad-output/planning-artifacts"`, and that key does **NOT** compose with a project's `output_folder` override — so **every BMAD skill that writes planning artifacts resolves through these symlinks**, not through the marker. Marker and symlinks must always agree; when they disagree, a write-skill silently targets the *other* project. **Always switch with `scripts/bmad-switch <slug>`** (since 2026-07-14 it re-points the symlinks atomically and writes the marker last, so a failed re-point can't desync); never hand-edit the marker. `scripts/bmad-switch --current` / `--list` warn on a desync — heed it before running any BMAD write-skill. Live near-miss (2026-07-14): the symlinks sat on `pyforge-warden` while the marker said `local-recipes`, so a local-recipes doc re-sync would have overwritten pyforge-warden's PRD/epics/architecture.

**PARALLEL AGENTS: never touch the switch — address projects by physical path (HARD, since 2026-07-25).** The marker *and* the symlinks are **per-working-tree global state**, so `scripts/bmad-switch` is a mutex nobody holds: two concurrent BMAD write-agents will silently re-point each other's target mid-write. When fanning out more than one agent that writes planning artifacts:

- **Write to `_bmad-output/projects/<slug>/planning-artifacts/…` literally.** Never to `_bmad-output/planning-artifacts/…` (the symlink) and never via a skill that resolves through it without pinning.
- **Do not call `scripts/bmad-switch`** from a parallel agent. If a skill needs the active project, pass **`BMAD_ACTIVE_PROJECT=<slug>` per invocation** — it takes precedence over the marker in `_bmad/scripts/resolve_config.py` and mutates nothing shared.
- **Verify placement after writing** (`readlink -f`, or just check the file landed under the intended slug) — the failure is silent, never an error.

Live incident (2026-07-25, the 11-Spec derivation fan-out): five concurrent agents each ran `bmad-switch`; the shared symlink was observed moving `pyforge-doctor → pyforge-marshal → pyforge-mason → deckcraft` mid-run, and one agent's 30-entry memlog landed under **pyforge-marshal's** tree instead of pyforge-doctor's. It was caught by `readlink -f` and recovered intact; the other four agents independently adopted physical paths after noticing the drift. Nothing was lost — but only because the agents checked.

**Six-layer config merge** (highest priority last):

| Layer | Path                                                         | Scope                                |
|-------|--------------------------------------------------------------|--------------------------------------|
| 1     | `_bmad/config.toml`                                          | Installer team (regenerated)         |
| 2     | `_bmad/config.user.toml`                                     | Installer user (regenerated)         |
| 3     | `_bmad/custom/config.toml`                                   | Global custom team, all projects     |
| 4     | `_bmad/custom/config.user.toml`                              | Global custom user, all projects     |
| 5     | `_bmad-output/projects/<slug>/.bmad-config.toml`             | Project team, active project only    |
| 6     | `_bmad-output/projects/<slug>/.bmad-config.user.toml`        | Project user, active project only    |

Layers 5 and 6 only load when an active project resolves. To set the active project: `scripts/bmad-switch <slug>`. To list projects: `scripts/bmad-switch --list`.

**Adding a new project:** see `_bmad-output/PROJECTS.md` § "Adding a new project."

### Spec-driven, framework-neutral layout (the tiers)

This repo is spec-driven and tool-agnostic — **everything starts with a Dream; BMAD turns it into the spec; the spec drives the build** — the agent/framework is interchangeable. **`AGENTS.md`** (repo root) is the cross-tool entry point (thin per-tool pointers: `CLAUDE.md`, `.cursor/rules/specs.mdc`, `GEMINI.md`, `.github/copilot-instructions.md`). Tiers, never crossed:

| Tier | Location | Purpose | Git |
|---|---|---|---|
| **0 — Dream** | `docs/dreams/*.md` | The raw human aspiration / starting point (BMAD — *Build More Architect Dreams*); Herald renders it into a deck, and BMAD turns it into the spec | tracked, permanent |
| **1 — Intake spec (LEGACY)** | `docs/specs/*.md` | Former hand-authored spec tier — kept for existing efforts, **superseded by Tier 2**; author no new files here | tracked, phasing out |
| **2 — Spec & planning (BMAD)** | `_bmad-output/projects/<slug>/planning-artifacts/` | `bmad-spec` output + PRD, architecture/API specs, epics+stories, gate reports — produced from the Dream. **The active spec lives here.** | tracked, permanent |
| **3 — Execution output** | `_bmad-output/projects/<slug>/implementation-artifacts/` | story files, sprint YAMLs, test outputs, retros, derived per-effort specs | **gitignored / local-only** |

Rules: the **active spec is a BMAD artifact in Tier 2** (produced from a Tier-0 Dream) — don't hand-author new specs in the legacy `docs/specs/`, and never drop one into a Tier-3 output dir; `implementation-artifacts/` is gitignored, so **nothing there may be git-tracked** (HARD `tracked-impl-artifact` finding).

**Story specs are durable (tracked), NOT Tier-3 (convention since 2026-07-25).** Per-story intent-contract specs are load-bearing in a spec-driven build — the spec *is* the contract — so they must survive worktree teardown and live in every clone. bmad-loop drafts a story spec into the run's gitignored `implementation-artifacts/` (runtime scratch); **after the story merges, promote that spec into the tracked `planning-artifacts/specs/` subdir and commit it** (the source of record). Motivating incident: pyforge-warden lost 13 of 31 story specs entirely (all of Epics 3 & 4) plus 8 husks to Tier-3 worktree teardown before this convention existed — **fully recovered 2026-07-25 to 31/31 real originals.** Recovery-source hierarchy (highest fidelity first): (1) **Claude Code session transcripts** `~/.claude/projects/**/*.jsonl` — the `Write`/`Edit` tool-calls that created each spec survive there, so originals (often incl. the dev/review triage log) come back verbatim (recovered warden's last 13 this way); (2) surviving bmad-loop **run-worktree snapshots**; (3) **`epics.md` regeneration** (Intent + ACs only — the contract, not the narrative). pyforge-atlas is the cautionary counter-case: its dev-session transcripts are NOT in the local store, so only 2 of 32 originals survived (30 are epics.md contract-specs). See each project's `planning-artifacts/specs/README.md`. This supersedes the "derived per-effort specs → Tier-3" row above for **story** specs.

<!-- governance-currency:ignore-start (removed/renamed skills named BECAUSE they were removed) -->
**Dream-first (MANDATORY, always-on):** before implementing any non-trivial effort, a **Dream** must exist in `docs/dreams/<slug>.md`, and BMAD must have produced its **spec** from it — run **`bmad-spec`** to produce **the Spec** — the five-field contract, and the artifact everything downstream binds to. For product/platform scope the planning chain (`bmad-prd` / `bmad-architecture` / `bmad-create-epics-and-stories`) then **decomposes** that Spec; it is *not a substitute for it* (Charter § The Lexicon §2 — the Spec is the unit of contract, the chain is its decomposition). Output lands in `_bmad-output/…/planning-artifacts/`. Marshal (`bmad-loop` / `bmad-build-auto` — the 6.11 name for `bmad-dev-auto`; bmad-loop ≥0.9.1 resolves whichever is installed) can do this unattended from a new Dream. **Keep the spec's status current** (`draft → ready → in-progress → shipped`) regardless of who did the work. **Gap-closure and realization work are not exempt (operator ruling 2026-09-12):** when asked to close a realization gap, realize a capability, or fix an effort whose stories already exist, the first artifact is still a **Dream seed** (`status: dreamt`, an owning station, Kinships to every chain it binds — exemplar: `docs/dreams/run-state-one-publisher.md`, minted on the CAP-17 run-state gap), and `bmad-spec` derives the Spec from it before any story is drafted or dispatched. Legacy `docs/specs/*.md` still carry `status:` frontmatter (read by `python scripts/bmad_drift_check.py --specs`) during the transition. **Spec → Story before code (found live 2026-09-12, no exemption for a small fix):** a `ready` Spec is a contract, not a work order. Once `bmad-spec` produces it inside a BMAD project, decompose its capabilities into a numbered Story in that project's `epics.md` and reflect it in `sprint-status-ledger.yaml` — via `bmad-sprint-planning` / `bmad-create-epics-and-stories`, or by hand mirroring the project's own established numbering convention when those skills aren't invoked directly — **before** touching any file outside `docs/dreams/` or the Spec folder itself. A mechanically well-understood, single-CAP fix is not an exemption: skipping the Story skips the one place the dev/review loop and retro triggers this repo relies on actually fire. Incident: `spec-library-catalog-manifest-sync` CAP-1/CAP-2 were hand-implemented straight from the Spec with no Story minted in `pyforge-marshal/epics.md` and no ledger entry — caught mid-turn by the operator, reconciled after the fact. Full convention: **`AGENTS.md`** (repo root).
<!-- governance-currency:ignore-end -->

### Keeping BMAD artifacts in sync with the live repo (always-on)

The `_bmad-output/projects/pyforge-marshal/` artifacts (PRD, architecture set, epics, overview, specs) hard-code volatile facts about the factory (skill version, cf_atlas schema, MCP tool / atlas-phase / pixi-env counts, gotcha range) and drift behind the fast-moving `conda-forge-expert` skill. A **two-layer sync loop** keeps them accurate and able to catch up after *any* out-of-band change (BMAD or not):

- **Detector** (cheap, deterministic): `pixi run -e pyforge-guild bmad-drift-check` (and `bmad-groundtruth` for live facts as JSON). Reports pin drift, count/phase-list staleness, stale rules, archive-hygiene + stray files, coverage completeness (every project file must be classified), and baseline-vs-live surface change. The verdict lives in `pyforge.doctor.sources.factory::gather` (Story 6.9 ported it off the script); `pixi run -e pyforge-guild bmad-drift-check` now runs `python -m pyforge.doctor.sources bmad-drift`, the dispatcher entrypoint. Enforced in the test suite by `.claude/skills/conda-forge-expert/tests/meta/test_bmad_artifacts_in_sync.py` (integrity only).
<!-- governance-currency:ignore-start (removed/renamed skills named BECAUSE they were removed) -->
- **Reconciler** (correctness): the **BMAD skills themselves** — `bmad-correct-course` + `bmad-create-epics-and-stories` the PRD/epics; `bmad-prd` (validate) + `bmad-sprint-planning`'s readiness gate (6.11 absorbed `bmad-check-implementation-readiness`) the gate reports. **6.11 gaps:** `bmad-document-project`'s brownfield re-grounding (living architecture/overview/source-tree/parts docs) has NO direct 6.11 equivalent — `bmad-project-context` only maintains a verified block in `AGENTS.md`; re-ground those docs by hand or with a plain agent until upstream ships the promised "explain this system" capability. `bmad-index-docs` is removed with no replacement — maintain `index.md` by hand. Then re-stamp the baseline: `python scripts/bmad_drift_check.py --write-baseline` (the read-only pixi task can't do this — that mutation-only surface survives directly in the script, run with plain `python`, no pixi task).
<!-- governance-currency:ignore-end -->

**When to run:** after every CFE retro / skill MINOR bump, and whenever the detector reports `surface-changed` (an out-of-band edit to `recipes/`, `.claude/`, `pixi.toml`, or `docs/specs/`). Full procedure + finding→remedy mapping: **`_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md`**. The verdict is `pyforge.doctor.sources.factory::gather`; `scripts/bmad_drift_check.py` survives as a mutation-only residual (`--fix`, `--write-baseline`, `--json`/`--groundtruth`, `--specs`) invoked with plain `python`, not pixi.

## Skill Reference

| Skill | Purpose | When to invoke |
|---|---|---|
| `conda-forge-expert` | Full conda-forge recipe lifecycle (generate → validate → build → submit) | Creating/updating recipes, fixing build failures, any conda packaging |
<!-- governance-currency:ignore-start (removed/renamed skills named BECAUSE they were removed) -->
| `bmad-build` (6.11 name of `bmad-quick-dev`; `bmad-build-auto` = `bmad-dev-auto`) | Implement story / feature / fix from a spec — "the one official way BMad implements code". Default front door is `marshal factory dispatch` (one story) / `marshal factory spin` (many): journaled, benchmarked, running the substrate/compression layers. Invoking `bmad-build-auto` bare is sanctioned but unmeasured — no journal entry, no per-harness savings rollup. | Direct implementation requests when the story spec exists |
| `bmad-prd` / `bmad-architecture` / `bmad-create-epics-and-stories` | BMAD planning chain (deprecated forwarders — `bmad-create-prd` / `bmad-create-architecture` / `bmad-create-story` / `bmad-dev-story` — removed in v7) | Starting a new product or feature in `_bmad-output/projects/<slug>/` |
| `bmad-project-context` | Verified agent-instructions block in `AGENTS.md`, or a subtree-scoped "child" `AGENTS.md` (own Children rule, all five conditions: subtree-exclusive, substantial, materially reduces the parent block, loading verified for every harness in use, user-approved — e.g. `src/shared/packages/pyforge-atlas/AGENTS.md`) (6.11 replacement for `bmad-document-project` + `bmad-generate-project-context`; does NOT produce brownfield docs) | "Set up / refresh / audit agent instructions"; record observed agent mistakes |
<!-- governance-currency:ignore-end -->
| `bmad-agent-*` (analyst/architect/dev/pm/ux-designer; tech-writer retired in 6.11) | Persona-led workflows | "Talk to John/Mary/Winston/…" requests |

For full skill list and disambiguation defaults (which review skill, simplify-vs-code-simplification, schedule-vs-loop, etc.) see auto-memory entry `feedback_skill_disambiguation.md`.

## BMAD ↔ conda-forge-expert integration

These three rules govern any BMAD-driven effort that touches conda-forge work in this repo. Rules 1–2 apply to every BMAD skill (`bmad-build`, `bmad-agent-dev`, persona agents, planning agents, code-review agents — everything); Rule 3 is narrower, applying only to the planning skills that scope conda-forge stories (`bmad-prd`, `bmad-create-epics-and-stories`, `bmad-build`/persona planning). All three are **always-on** within their stated scope; no opt-in.

### Rule 1 — BMAD must invoke `conda-forge-expert` for any conda-forge work

When a BMAD agent's current story, task, or sub-task involves any of:

- creating, editing, validating, optimizing, building, or submitting a conda recipe (`recipe.yaml`, `meta.yaml`, multi-output, patches under `recipes/<name>/patches/`)
- responding to a conda-forge build failure or staged-recipes review comment
- packaging a PyPI / npm / CRAN / CPAN / LuaRocks / GitHub source as a conda artifact
- working with `pin_subpackage`, `compiler()`, `stdlib()`, `noarch: python`, conda-forge selectors, or rattler-build features
- interacting with `pixi run -e local-recipes …` recipe-build / autotick / submit-pr tasks
- reading or modifying anything under `.claude/skills/conda-forge-expert/`, `.claude/scripts/conda-forge-expert/`, `.claude/data/conda-forge-expert/`

…the agent **must** invoke the `conda-forge-expert` skill (via the `Skill` tool with `skill: conda-forge-expert`) before producing recipe code or running recipe-related tooling. The skill's 9-step autonomous loop, Operating Principles, Critical Constraints, and Build Failure Protocol are authoritative — the BMAD story file does not override them.

If a BMAD story's instructions conflict with `conda-forge-expert`'s guidance (e.g., the story says "loosen this pin to `>=1.0`" but conda-forge-expert's pin-loosening convention applies a different rule), the skill wins and the agent updates the story comment to record the deviation.

### Rule 2 — Every conda-forge BMAD effort ends with a retro that improves the skill

When a BMAD effort that did conda-forge work reaches its closeout (final story complete; PR merged or final review-comment resolved; or the user marks the effort done), the agent **must** run a retrospective focused on the `conda-forge-expert` skill itself. The retro:

1. Invokes the `bmad-retrospective` skill (or follows its protocol manually if BMAD is not loaded).
2. Reviews session logs, build failures encountered, recipe diffs, and reviewer comments to identify:
   - **Corrections** — guidance in the skill that turned out to be wrong, stale, or misleading.
   - **Refinements** — guidance that worked but was harder to apply than it should have been (missing examples, ambiguous wording, missing edge cases).
   - **Additions** — patterns, constraints, gotchas, or build-failure recipes encountered for the first time during this effort that future efforts should benefit from.
3. Lands the findings as edits to:
   - `.claude/skills/conda-forge-expert/SKILL.md` (Operating Principles, Critical Constraints, Recipe Authoring Gotchas, Build Failure Protocol)
   - `.claude/skills/conda-forge-expert/reference/*.md` (per-topic deep references)
   - `.claude/skills/conda-forge-expert/guides/*.md` (workflow / troubleshooting guides)
   - `.claude/skills/conda-forge-expert/CHANGELOG.md` (a new version entry summarizing the retro's deltas, dated, with a one-line summary per finding)
4. Bumps the skill version per semver (PATCH for fixes/clarifications, MINOR for new gotchas / new sections, MAJOR only if breaking workflow changes).
5. Saves a corresponding auto-memory feedback entry only if the finding crosses skill boundaries (e.g., affects how BMAD interacts with `conda-forge-expert`); skill-internal findings stay in the skill files, not in auto-memory.

The retro is not optional and not deferrable. An effort is not "done" until the retro lands.

If the effort produced no novel findings (rare — almost every effort surfaces at least one refinement), the retro still runs and produces a CHANGELOG entry stating "no skill changes; verified existing guidance held for: <summary of effort>".

### Rule 3 — Planner constraints for conda-forge stories

These rules reshape **story scope** for `bmad-prd`, `bmad-create-epics-and-stories`, and `bmad-build`/persona planning whenever the work being scoped is conda-forge recipe work (recovered 2026-09-06 from the retired `pyforge-marshal/project-context.md` rulebook, Story 30.2):

- **`noarch: python` recipes have no per-platform test matrix.** A story that splits test coverage by OS for a noarch package is invalid. Either commit to per-platform builds (drop `noarch:`) or write a single test matrix.
- **The submission-ready gate is non-negotiable.** A story that targets "submit PR" cannot complete until `validate_recipe` + `optimize_recipe` + `scan_for_vulnerabilities` + a green linux-64 build are all green. Plan the four checks as explicit acceptance criteria, not implicit "tests pass."
- **Step 8b is a story boundary.** `prepare_submission_branch` is the natural "done for now" point for a recipe-authoring story; `submit_pr` belongs to a separate, human-authorized "publish recipe" story. Don't bundle them.
- **`python_min` floor moves.** When planning a story that pins a Python floor, reference the **current** `conda-forge-pinning-feedstock` value at implementation time, not a snapshot recorded at planning time.
- **Cross-platform stories require a named build host.** A story authoring a recipe that ships on `win-64` must name the build host (Windows host, Windows VM, or "rely on conda-forge CI") in the acceptance criteria — a Linux host cannot validate win-64 binaries.

## Project Documentation Reference

For extended architectural context, please reference the centralized `docs/` folder (map at **`docs/MAP.md`**):
- **`docs/explanation/mcp-server-architecture.md`** — FastMCP server integration and PyPI name mapping subsystem.
- **`docs/explanation/enterprise-deployment.md`** — Air-gapped environments and JFrog Artifactory integration.
- **`docs/reference/developer-guide.md`** — Local testing and general recipe development guidelines.
- **`docs/dreams/pyforge-herald.md`** + **`docs/how-to/presentation-deck.md`** § *The MCP bridge* — decks/prototypes round-trip between Claude Design and the repo via the `claude-design` MCP tools (seed → design visually → pull → extract/build/`deck-export`); no manual downloads. Piloted 2026-07-23 (Marshal deck). Same spec, § *Artifact dependency tree & editing surfaces* — **read before editing any deck artifact**: per-deck branch heads (deck prototype / infographic trio head / exec summary / marp exports), what derives from what, and the two propagation paths.
- **`docs/reference/library-llms-full.md`** — LLM/agent-facing catalog of every library and CLI in the pixi environments: capabilities, version pins, import-name gotchas, env membership, and what is deliberately NOT installed. Derived from `pixi.toml` (regeneration prompt in its header) — consult before importing a library or proposing a new dependency. Drift detector: `pixi run -e pyforge-guild llms-full-check` (exits non-zero when the catalog is stale; reconcile by regenerating).

### Intake specs (`docs/specs/` — LEGACY Tier 1, being phased out)

> **Legacy.** `docs/specs/` is the former hand-authored intake-spec tier — **superseded** by the
> Dream → `bmad-spec` → `_bmad-output/…/planning-artifacts/` flow (see § *Spec-driven,
> framework-neutral layout*). These files are **kept for existing efforts**; author no new specs
> here. The index below remains the map of in-flight legacy specs during the transition.
> `shipped`/`superseded` specs sunset to `archive/docs/specs/` by their own frontmatter
> `status:` (Story 23.3); `docs/specs/` itself keeps only `in-progress` specs and the three
> `workflow` stubs (bodies moved to `docs/how-to/`).

One table row per spec; the **spec file itself is the source of truth** (frontmatter contract + its
`## Current State` block where present) — long-form status detail is deliberately not duplicated here.
List live statuses with `python scripts/bmad_drift_check.py --specs`. Unless a row says
<!-- governance-currency:ignore-start (removed/renamed skills named BECAUSE they were removed) -->
otherwise, run a spec via `bmad-build` (6.11 name of `bmad-quick-dev`) with the spec path + parameters named in the prompt.
<!-- governance-currency:ignore-end -->

**Active (`in-progress`):**

| Spec | What it is |
|---|---|
| `archive/docs/specs/langflow-conda-forge.md` | langflow-suite — MERGED + graduated to `conda-forge/langflow-feedstock`, now v1.11.4 with 8 outputs (2026-08-20; the 4 `lfx-*` plugins absorbed). The spec file is the historical record of the submission era plus dated addenda; open residue tracked there (`DW-FU-10-4` cp314 onnxruntime gate). python_min 3.11 (G41). |
| `archive/docs/specs/db-gpt-conda-forge.md` | DB-GPT on conda-forge. **TERMINAL — delivered via external PR #33883 (consume-not-submit, G58); do NOT re-run BMAD on it.** Only § Current State + § Readiness are authoritative; the stories are historical. |
| `docs/specs/flyte-conda-forge.md` | Flyte 2 SDK (PyPI `flyte` ≠ v1 `flytekit`) — 6-recipe closure built GREEN locally; submission blocked on the buf.validate namespace collision (G88). python_min 3.11 (G40/G41). |
| `docs/specs/feedstock-refresh.md` | Two-track bulk refresh of ALL 769 feedstocks rxm7706 can modify (regenerate, v0→v1, platform-expand). Track A (sole, 537): Waves B–F shipped, reopened for Wave H total-coverage (179 remaining). Track B (co, 232): ready; adds co-maintainer etiquette + a no-local-recipe bucket. Delegates per-feedstock work to `feedstock-platform-expansion.md`. |

**Ready (backlog, unimplemented): none.** The three specs formerly here
(`claude-team-memory.md`, `copilot-bridge-vscode-extension.md`,
`bmad-copilot-adapter-upstream.md`) turned out to already be `status: superseded`
in their own frontmatter, dated 2026-07-25 — this index just hadn't caught up
(found 2026-08-15, same pattern as trendshift/warden below). See "Shipped" for
their corrected entries.

**Timeless workflows (`workflow` — parameterized, re-runnable; per-case state appends to their Worked Examples):**

| Spec | What it is |
|---|---|
| `docs/specs/feedstock-platform-expansion.md` | Dual-goal per-feedstock workflow: refresh `recipes/<feedstock>/` to the latest CFE shape at the latest upstream version AND widen the build matrix (osx-arm64 / linux-aarch64) in the same PR. The procedural core both refresh specs delegate to; deep detail in `.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md`. **Body relocated to `docs/how-to/feedstock-platform-expansion.md`** (Story 23.3); invoke `bmad-build` with that path — this stub carries `status: workflow` for indexing. |
| `docs/specs/feedstock-failure-remediation.md` | Red feedstock-PR remediation loop: triage FLAKE / REAL_FIX / BLOCKED (G32 signature catalog), execute-locally-first, maintainer-edit push to the bot fork, rerender-after-push. Worked example: the 2026-06-17/18 12-PR batch (G31–G34). **Body relocated to `docs/how-to/feedstock-failure-remediation.md`** (Story 23.3); invoke `bmad-build` with that path — this stub carries `status: workflow` for indexing. |
| `docs/specs/presentation-deck.md` | Reusable React+Vite slide-deck workflow: turn a Claude Design 1920×1080 `.dc.html` prototype into a self-contained deck via mechanical slide extraction → a small deck engine (fit-to-viewport, keyboard nav, URL-hash routing, overview grid, presenter view w/ notes+timer), a static offline-safe Vite bundle, and Marp + PPTX exports. Parameterized by topic (non-conda-forge). Worked Example 1 = the 45-slide *Agentic AI across the SDLC* / BMAD deck (`presentations/agentic-sdlc/`, PR #50). **Body relocated to `docs/how-to/presentation-deck.md`** (Story 23.3); invoke `bmad-build` with that path — this stub carries `status: workflow` for indexing. |

**Shipped (historical record — evidence in each spec's `shipped_ref`):**

| Spec | What it is |
|---|---|
| `archive/docs/specs/bmad-loop-adoption.md` | BMAD 6.6.0→6.10.0 upgrade + bmad-loop adoption — SHIPPED, closed out 2026-08-21 (Rule-2 CFE retro = skill v8.83.0). The fleet has since moved on: core 6.11.0 / bmad-loop 0.11.0, and repeatability is now owned by `spec-bmad-method-core-upgrade` (steward Epic 14) + `spec-bmad-method-version-drift` CAP-4 (doctor Epic 14). |
| `archive/docs/specs/cfe-atlas-datapipeline-kedro-migration.md` | cf_atlas orchestrator migrated to a Kedro/Dagster/DuckDB stack — Waves 0 + A–H (22 FRs incl. FR-19 Basilisk / FR-20 release velocity / FR-21 readiness / FR-22 factory layer) executed via bmad-loop under BMAD project `pyforge-atlas`; **PRs #58–#105 MERGED; the original 32 stories all done, epics 0–9 done** — SHIPPED 2026-07-18 (CFE v8.79.0). Impl-artifact truncation incident reconciled 2026-07-23 (`_bmad-output/projects/pyforge-atlas/_root-fallback-fork-2026-07-19/README.md`); trust only canonical hyphenated files there. **`pyforge-atlas` has since grown well past this original migration** (epics 10–16: dashboard provenance, run-admission hardening, kedro-skills adoption, the real DAG publish, and — absorbing `archive/docs/specs/trendshift-conda-forge.md`, below — the trending-candidates discovery engine); track ongoing atlas work via `pixi run -e pyforge-guild fleet-picture`, not this spec. |
| `archive/docs/specs/trendshift-conda-forge.md` | Two-track upstream-sweep packaging. **Track A superseded 2026-07-25** by the spec's own `superseded_by` pointer to `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-upstream-discovery/` — Phase T was reframed as Kedro-pipeline work and became atlas Epic 13 (`spec-13-1-trending-ingest` through `spec-13-5-downstream-handoff-to-mason`), **now fully shipped** as part of atlas's own story count. Track B (absorbed `microsoft-conda-forge.md`, the `github.com/microsoft/*` org audit) status not re-verified in this pass — check `archive/docs/specs/trendshift-conda-forge.md` § Track B directly before assuming it's also absorbed. Do not run BMAD against Track A via this file; it's a historical record now. |
| `archive/docs/specs/pyforge-warden.md` | **Warden** — pluggable multi-axis Python dependency compliance gate (hygiene `deptry`, security `osv-scanner`+CISA-KEV+EPSS gates, license + currency, baseline & grandfathering, opt-in fix-PR actuator) over Python/Conda/Pixi manifests. This legacy intake spec's own frontmatter still reads `status: in-progress` (stale — not corrected in this pass, since story specs are the source of truth per this file's own Tier convention) but the work it specced **shipped in full as the `pyforge-warden` BMAD project**: all 6 epics / 31 stories done (verified 2026-08-15, `pixi run -e pyforge-guild fleet-picture` reports it `complete`), including a dedicated fleet-wide code-verification campaign (PRs #145–147, 2026-07-30) re-confirming every tracked deferred-work finding against live code. Do not run BMAD against this legacy file; the BMAD project's own `planning-artifacts/` is authoritative. |
| `archive/docs/specs/lts-registry-gap.md` | `lts-registry-gap` CLI — read-only suggester diffing endoflife.date's product list against `v_actionable_packages` to propose lts-registry.yaml entries (exact/likely tiers; the registry stays hand-curated, git review decides) — SHIPPED 2026-07-06 (CFE v8.74.0). |
| `archive/docs/specs/seed-gap-suggesters.md` | `cwe-seed-gap` + `spdx-schema-gap` + `license-map-gap` — read-only suggesters proposing `cwe_categories_seed.json` / `spdx.schema.json` / in-code `_LICENSE_TO_SPDX` entries (keyword-classified `Other` CWEs; vendored-vs-upstream SPDX diff; unmapped-PyPI-license ranking); the curated maps stay hand-owned, git review decides — SHIPPED 2026-07-06 (CFE v8.75.0 + v8.76.0). |
| `archive/docs/specs/cyclonedx-universe-inventory.md` | CycloneDX inventory of the FULL PyPI + conda-forge universes — SHIPPED 2026-07-06 (Waves A–E + S-retro, CFE v8.73.0): `export-purls`/`mapping-gap` (+v29 view), `universe-sbom` (856,766-component BOM), `inventory-match` (S5a intake incl. pixi.lock; transitive resolver; decision-4 live channeldata; vulns policy gate), `add-handoff`, `library-futures`/`recommend-2027` (2027–2030 tiers, py314 + LTS/endoflife signals). All local live gates PASS — dated Dev Notes in the spec. Do not re-run BMAD on it. |
| `archive/docs/specs/cfe-shipped-releases.md` | Consolidated archive of the 10 shipped intakes (2026-07-02): v7.9.0 pypi-universe-split, v8.0.0 + v8.9.0 CFE bundles, v8.1.0 PyPI intelligence, v8.6.0 AppThreat, v8.14.0 PR-artifact downloader, v8.15.0 Phase P incremental, Phase F Waves 1–3 (v7.6.0→v8.19.0), v8.20.0 Phase K scheduler, + the closed graphifyy osx-arm64 fanout effort. Release notes: skill CHANGELOG. Do not re-run BMAD on any part. |
| `archive/docs/specs/conda-forge-tracker.md` | Sibling repo `~/UserLocal/Projects/Github/rxm7706/conda-forge-tracker/` — markdown-first personal feedstock tracker (13 stories) |
| `archive/docs/specs/claude-team-memory.md` | `.claude/memory/` team-shared memory layer + `team-memory` skill. **Superseded 2026-07-25** by its own frontmatter — folded into the `pyforge-scribe` planning chain (all 10 stories), now the complete BMAD project (9/9 stories). Found still mis-filed as "Ready/unimplemented" 2026-08-15. |
| `archive/docs/specs/copilot-bridge-vscode-extension.md` | Sideload-only VS Code extension wrapping the copilot-api bridge pattern. **Superseded 2026-07-25** by its own frontmatter — stories 13-15 absorbed into `pyforge-marshal` v1; the copilot-api HTTP-bridge premise (stories 1-12) is obsolete now that bmad-loop 0.9.0 ships a sanctioned `copilot` profile + `copilot --acp`. Found still mis-filed as "Ready/unimplemented" 2026-08-15. |
| `archive/docs/specs/bmad-copilot-adapter-upstream.md` | Contribution brief to upstream the `@bmad` Copilot-Chat adapter. **Superseded 2026-07-25** by its own frontmatter — a deferred item, re-owned to Herald for the chat-adapter comms face. Found still mis-filed as "Ready/unimplemented" 2026-08-15. |

Skill-internal documentation (loaded on-demand when the skill activates):
- **`.claude/skills/conda-forge-expert/SKILL.md`** — Recipe authoring agent operating principles, 10-step lifecycle loop (step 8b: prepare submission branch on fork, step 9: open PR), build-failure protocol.
- **`.claude/skills/conda-forge-expert/reference/`** — `recipe-yaml-reference.md`, `meta-yaml-reference.md`, `python-min-policy.md`, `mcp-tools.md`, `conda-forge-ecosystem.md`, `pinning-reference.md`, `selectors-reference.md`, `jinja-functions.md`, `atlas-phases-overview.md` (consolidated atlas intelligence reference — Part A: persona-mapped catalog of every actionable signal, shipped + open + gap; Part B: phase-indexed overview of each pipeline stage), `atlas-phase-engineering.md` (engineering patterns for writing or refactoring phases — rate limits, GraphQL batching, atomic writes, enterprise routing; § 13: Phase P cost model + operator playbook), `dependency-input-formats.md` (manifest / lock-file / SBOM / container-input support matrix — the canonical "what does scan_project accept?" reference), `conda-forge-yml-reference.md` (high-signal subset of conda-forge.yml keys — staged-recipes per-recipe override + feedstock-level — covers `azure.store_build_artifacts`, `os_version`, `provider`, `bot.version_updates.exclude`, deprecated keys, and common patterns).
- **`.claude/skills/conda-forge-expert/guides/`** — getting-started, migration, ci-troubleshooting, cross-compilation, feedstock-maintenance, testing-recipes.
- **`.claude/skills/conda-forge-expert/quickref/`** — `commands-cheatsheet.md` (incl. project pixi tasks), `bot-commands.md`.

### conda-forge-expert v7.0.0 layout (3-tier + MCP layer)
- **`.claude/skills/conda-forge-expert/scripts/`** — canonical implementation (source of truth). Edit code here.
- **`.claude/scripts/conda-forge-expert/`** — public CLI entrypoint layer (~30 thin subprocess wrappers). What `pixi run` calls.
- **`.claude/data/conda-forge-expert/`** — mutable runtime state (cf_atlas.db, vdb/, cve/, mappings, caches). Gitignored.
- **`.claude/tools/conda_forge_server.py`** — FastMCP server exposing 30+ tools across recipe-authoring + atlas-intelligence + project-scanning surfaces. Started by Claude Code at session boot; tool schemas surface at call time.

**Three-place rule for a new CI script:** (1) canonical implementation at `.claude/skills/conda-forge-expert/scripts/<name>.py`; (2) thin CLI wrapper at `.claude/scripts/conda-forge-expert/<name>.py`; (3) a pixi task (`[feature.local-recipes.tasks.<name>]` in `pixi.toml`) plus an entry in the `SCRIPTS` list in `.claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py`. Missing any one breaks that meta-test.

**Atlas intelligence (v7.0+)** — `cf_atlas.db` ships 16 schema versions, 15 pipeline phases (B → N), and 17 CLIs. Daily-use entrypoints: `detail-cf-atlas`, `staleness-report`, `feedstock-health`, `whodepends`, `behind-upstream`, `cve-watcher`, `version-downloads`, `release-cadence`, `find-alternative`, `adoption-stage`, `scan-project`. All read-side CLIs are offline-safe. See `.claude/skills/conda-forge-expert/SKILL.md` § "Atlas Intelligence Layer" for the persona-mapped guide.

Enterprise routing (JFrog Artifactory, internal mirrors) is **runtime-driven** via `_http.py` (truststore + JFrog/GitHub/.netrc auth chain) — env vars only, never committed config. See `.claude/skills/conda-forge-expert/CHANGELOG.md` v6.0.0 / v7.0.0 entries for the full release notes.

Repo-wide pointers:
- **`_bmad-output/PROJECTS.md`** — BMAD multi-project index.
- **Auto-memory** — `~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/MEMORY.md` indexes accumulated feedback (skill disambiguation, recipe pin-loosening, .bat shim rules, BMAD multi-project pattern) and project context.

## Team Memory

This repo carries a checked-in team-memory index at `.claude/memory/MEMORY.md` — one-line entries capturing team-relevant decisions, feedback, and reference material as reviewable prose (see `.claude/memory/README.md` for the schema and promotion workflow). It is imported below so the index is in context for every session. The import line must stay bare — a backticked `@path` is an inert code span, not an import.

@.claude/memory/MEMORY.md

<!-- SKF:BEGIN updated:2026-08-26 -->
[SKF Skills]|7 skills|0 stack
|IMPORTANT: Prefer documented APIs over training data.
|When using a listed library, read its SKILL.md before writing code.
<!-- governance-currency:ignore-start (a path that must NEVER exist -- mason's skill tier is conda-forge-expert per five_tier.py; named here BECAUSE minting it is forbidden. Mirrors AGENTS.md:30-32.) -->
|Mason is the eighth PyForge Guild station but deliberately has no SKF skill — recipe work uses `conda-forge-expert` instead (see `AGENTS.md` governance-currency policy on never minting `.claude/skills/pyforge-mason/`).
<!-- governance-currency:ignore-end -->
|
|[pyforge-atlas v0.1.0]|root: .claude/skills/pyforge-atlas/
|IMPORTANT: pyforge-atlas v0.1.0 — read SKILL.md before atlas pipeline work. Do NOT rely on training data. Use `pyforge atlas …` and POST /stations/atlas/mcp. Do not import pyforge.atlas internals. Do not replace conda-forge-expert. This is not cf-atlas-legacy.
|quick-start:{SKILL.md#quick-start}
|api: main(), run_pipeline(), read_dataset(), list_pipelines(), list_datasets()
|key-types:{SKILL.md#key-types} — PIPELINE_NAMES, AtlasMCPError
|gotchas: run from repo root; --version is first-token only; unknown MCP pipeline → AtlasMCPError
|
|[pyforge-doctor v0.1.0]|root: .claude/skills/pyforge-doctor/
|IMPORTANT: pyforge-doctor v0.1.0 — read SKILL.md before writing doctor diagnostics code. Do NOT rely on training data. Use pyforge doctor grammar, not pyforge.doctor imports. Findings stay advisory — not a second PR gate.
|quick-start:{SKILL.md#quick-start}
|api: main()
|key-types:{SKILL.md#key-types} — Finding (advisory signal), DoctorReport
|gotchas: run from repo root; pyforge doctor … not a freelance filesystem; monitor requires --fleet; warn never changes exit code; not a competing PR verdict
|
|[pyforge-herald v0.1.0]|root: .claude/skills/pyforge-herald/
|IMPORTANT: pyforge-herald v0.1.0 — read SKILL.md before writing herald/deck code. Do NOT rely on training data. Use the herald CLI, not pyforge.herald imports.
|quick-start:{SKILL.md#quick-start}
|api: main(), dispatch()
|key-types:{SKILL.md#key-types} — TOOL_NAME (herald), TOP_LEVEL_COMMANDS (deck|progress|success|notice|scheduler)
|gotchas: run from repo root; Path B grammar is pyforge herald …; POST /stations/herald/mcp only; Lane 1 CMS stays steward
|
|[pyforge-marshal v0.1.0]|root: .claude/skills/pyforge-marshal/
|IMPORTANT: pyforge-marshal v0.1.0 — read SKILL.md before writing marshal/loop-supervisor code. Do NOT rely on training data. Use the marshal CLI, not pyforge.marshal imports.
|quick-start:{SKILL.md#quick-start}
|api: main()
|key-types:{SKILL.md#key-types} — MarshalContext (--project front door), frozen exit domain
|gotchas: run from repo root; persona grammar is pyforge marshal …; do not import internals; Do not implement bmad-loop ingest in this skill
|
|[pyforge-scribe v0.1.0]|root: .claude/skills/pyforge-scribe/
|IMPORTANT: pyforge-scribe v0.1.0 — read SKILL.md before writing scribe/team-memory code. Do NOT rely on training data. Use the scribe CLI, not pyforge.scribe imports.
|quick-start:{SKILL.md#quick-start}
|api: capture_cmd(), graph_compile(), recall_cmd(), main()
|key-types:{SKILL.md#key-types} — CaptureType (feedback|project|reference), RecallAnswer (grounded miss is explicit)
|gotchas: run from repo root; --promote/--transcripts exclusive with --type/--text; recall never invents an uncited answer
|
|[pyforge-steward v0.1.0]|root: .claude/skills/pyforge-steward/
|IMPORTANT: pyforge-steward v0.1.0 — read SKILL.md before writing steward/platform code. Do NOT rely on training data. Use pyforge steward grammar (or the steward CLI), not pyforge.steward imports.
|quick-start:{SKILL.md#quick-start}
|api: build_parser(), resolve_duty(), main()
|key-types:{SKILL.md#key-types} — DutyResult is frozen evidence; duties never sys.exit (AD-8)
|gotchas: run from repo root; crash is exit 70 not 1; provision uses flags not nested verbs; do not replace conda-forge-expert
|
|[pyforge-warden v0.1.0]|root: .claude/skills/pyforge-warden/
|IMPORTANT: pyforge-warden v0.1.0 — read SKILL.md before warden work. Use `warden scan` / `pyforge warden scan`. Do NOT import pyforge.warden. Do NOT invent a second PR-gate verdict.
|quick-start:{SKILL.md#quick-start}
|api: main(), compose(), exit_code_for(), match_level_rung()
|key-types:{SKILL.md#key-types} — Status (seven-rung lattice), ComplianceReport
|gotchas: CLI is the sole gate; --doctor never exits 1; do not replace conda-forge-expert
<!-- SKF:END -->
