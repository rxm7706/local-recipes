# AGENTS.md — cross-tool guide for this repo

This is the **framework-neutral** entry point for any coding agent or agentic framework
(Claude Code, Cursor, GitHub Copilot, Gemini, Devin, Codex, Aider, BMAD, Agno, CrewAI, …).
It is intentionally tool-agnostic: **everything starts with a Dream; BMAD turns it into a
spec; the spec drives the build — the agent/framework is interchangeable.**

<!-- bmad:context -->
<!-- Verified 2026-09-04 against bd37dfd607. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## local-recipes (PyForge)

A conda-forge recipe factory (`recipes/`, driven by the `conda-forge-expert` skill) and the PyForge estate: a Django + Wagtail host at `src/platform/` plus eight `pyforge-<station>` packages and their `django-<station>` portals under `src/shared/packages/`, on Python 3.14 via pixi (`pixi.toml` is the task and dependency registry). Planning is BMAD: Dreams in `docs/dreams/`; Specs, spines, epics and ledgers under `_bmad-output/projects/<station>/planning-artifacts/`. The lasting root is `python-foundry`; that cutover is under contract in PR #1041 (`spec-python-foundry-cutover`, Epic 44, every story `blocked`) and not started.

## Policy

- Never mix `meta.yaml` and `recipe.yaml` recipes in one build run; the tooling rejects it.
- Never code from a bare prompt: a Dream in `docs/dreams/` and a Spec under `planning-artifacts/specs/spec-<slug>/` come first. Never author a new file under `docs/specs/` (legacy).
- Never hand-edit a `SPEC.md`; append to its `.memlog.md` with `uv run _bmad/scripts/memlog.py` and re-derive with `bmad-spec`. Exception: `spec-pyforge-unifying-strategy` is hand-edited past its memlog; never re-derive it.
- Never hand-edit `sprint-status-ledger.yaml` (generated); write the Tier-3 feed, then `pixi run -e local-recipes sprint-ledger-sync -- --project <station>`.
- Never track anything under `implementation-artifacts/`; it is Tier 3 and gitignored.
- Never run `scripts/bmad-switch` from a parallel agent; set `BMAD_ACTIVE_PROJECT=<slug>` and write physical `_bmad-output/projects/<slug>/` paths.
- Never run a bare `spec_surface_check.py --write-baseline`; stamp scoped with `--spec <project>/<spec>` after `git add`, from a clean tree.
- `src/platform/` never imports `pyforge.*`; reach station code through `pyforge.core.station_port`. No `services/` or `:800x` process tree.
- Any PR touching a path outside `recipes/` gets the `maintenance` label. A `pixi.toml` change regenerates `environment.yaml` in the same PR (`pixi project export conda-environment -e build > environment.yaml`); that check ignores the label.
- Merge with `gh pr merge --merge`, never squash. Create with `gh pr create --repo rxm7706/local-recipes`. TODO: disable squash merges in the repository settings; this line goes when that lands.
- Commit messages carry no `Co-Authored-By` line and no AI attribution. TODO: a `commit-msg` hook in the pre-commit set; this line goes when it lands.
- Never open a feedstock, staged-recipes or upstream PR without an explicit ask; a green local build ends the task.
- Never flip a ledger `blocked` key, and never dispatch outward work (a new repo, an upstream PR, disabling CI) without operator confirmation.
- New paths must fit the foundry target tree (`src/packages/`, `factory/`, `skills/{stations,personas,domain}/`, `docs/foundry/`); never mint a lasting `src/shared/packages/` or `.claude/skills/pyforge-mason/` path.

## Where things are

- Recipe lifecycle: `.claude/skills/conda-forge-expert/SKILL.md`. Invoke the skill before any conda work; every conda-forge effort closes with a retro that edits that skill and its `CHANGELOG.md`.
- Station code: read `.claude/skills/pyforge-<station>/SKILL.md` before touching `src/shared/packages/pyforge-<station>/`; use the CLI grammar, never `pyforge.<station>` internals.
- Architecture invariants and naming (station token, `python-<role>-<class>`, id prefixes, ledger keys): `planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md` under `pyforge-steward`; cite `canopy AD-n`, `pap:AD-n` for the host, and `fnd:AD-n` for the cutover spine once PR #1041 merges.
- Library availability and pins: `docs/reference/library-llms-full.md` before importing or proposing a dependency.
- Governance: `docs/governance/`; Dream status vocabulary: `docs/dreams/README.md`; dates versus versions: § Dates below.

## Running and verifying

- The merge gate is `detectors-ci` measured as no new findings against `main`. It is red at `main` today (pre-existing pin drift and three ungoverned scripts), so diff against `main`; do not expect green.
- Planning edits keep `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`, `deferred-work-check`, `ledger-regression-check` and `story-status-check` green; epic stories and their ledger keys land in the same commit.
- Before any ledger write: `sprint-ledger-sync -- --project <station> --repair-feed`, then `story-status-check`; a Tier-3 feed behind its tracked twin makes a bare sync refuse.
- Lint and types are per package (`[tool.ruff]`, `[tool.mypy]` in each `pyproject.toml`); `src/platform` still targets py312 while the interpreter is 3.14. TODO (decided 2026-09-04, not landed): repo-level `ruff` and `mypy` pixi tasks, a `.pre-commit-config.yaml`, mypy strict for `pyforge-core`, py314 targets, and a target-version registry check like `pixi-version-check`. Do not invent these invocations.
- BMAD skill renders need `PYTHONPATH="$PWD/_bmad/scripts:$PYTHONPATH"` in this shell.

## Known pitfalls

- Run `uv run` and every pixi task from the repo root; from a package directory `uv run` creates a stray `.venv` there (caught 2026-09-04).
- A merged story left at `backlog` in a ledger respawns on every drain; promote it with `sprint-ledger-sync` before landing.
- Unauthenticated GitHub probes fail open (`ok` at a 0/60 rate limit); check `gh api rate_limit` before trusting a green drift verdict.
- `--write-baseline` reads the working tree; a dirty checkout bakes uncommitted content into the baseline.
- Squash subjects break merge detection; `git merge-base --is-ancestor` is the proof a story landed.
- `.cmd` shims in `build.bat` need `call`, or the parent script exits.
- Marshal's `Deps:` parser is station-local; a cross-project gate is a ledger `blocked` row the operator flips.

<!-- /bmad:context -->

## Dream-driven: where work starts

**Every deliverable starts as a Dream in `docs/dreams/*.md`** — the raw, pre-technical aspiration
(the BMAD mission: *Build More Architect Dreams*). Plain markdown, version-controlled, neutral.
From a Dream, **BMAD-method produces the spec**:

- **Always** → **`bmad-spec`** distils the Dream into **the Spec** (five fields + companions)
  — the unit of contract; everything downstream binds to it.
- **Product / platform scope** → the planning chain then **decomposes** that Spec:
  `bmad-product-brief` → `bmad-prd` → `bmad-architecture` → `bmad-create-epics-and-stories`.
  The chain is the Spec's decomposition, **not a substitute for it** (Charter § The Lexicon §2):
  without a Spec there is a plan, but nothing holds the five fields still while the plan moves.

The resulting spec + planning artifacts live in **BMAD's own folder** —
`_bmad-output/projects/<slug>/planning-artifacts/` — not in a hand-maintained specs directory.

> **Legacy — `docs/specs/*.md`.** This was the former hand-authored intake-spec tier. It is
> **kept for existing efforts** (folder retained; files still valid and still carry the `status:`
> frontmatter that `bmad-drift-check --specs` reads) but is **superseded** — author no new specs
> there. New work is Dream → `bmad-spec` → the BMAD planning folder.

## Portability contract (why this stays framework-neutral)

BMAD *produces* the spec, but the spec stays portable — you are **not locked to BMAD**. The
neutral / framework-specific line runs *through* the spec:

- **Shared, portable layers:** the **Dream** (`docs/dreams/`, the WHY) and the **neutral
  Spec** (`bmad-spec`'s output — the WHAT + machine-checkable acceptance criteria, i.e. the
  verification oracle). Both are framework-agnostic by construction.
- **Per-framework layers:** decomposition (BMAD epics/stories vs. CrewAI crews vs. LangGraph
  nodes) and execution (orchestration, sprints, run traces) belong to whichever framework runs —
  BMAD, CrewAI, Agno, LangGraph, Devin, ….

So another framework has **two entry points**: (1) start from the **Dream** and do everything its
own way, or (2) consume the **neutral Spec** and diverge only at decomposition/execution —
which also lets you verify (and compare) any framework's build against the *same* oracle.

**The one property to protect:** the Spec's acceptance criteria must stay
framework-agnostic and machine-checkable (behavior + oracle — never "BMAD story 3.2 passed").
Keeping the Dream → spec handoff portable across agents is **Herald's** job.

## Dream-first workflow (MANDATORY — every agent, every framework)

1. **No non-trivial work without a Dream + spec.** Before implementing a feature, migration,
   packaging effort, or refactor, a **Dream** must exist in `docs/dreams/<slug>.md`, and BMAD must
   have produced its **spec** (via `bmad-spec` or the planning chain) in
   `_bmad-output/projects/<slug>/planning-artifacts/`. Never code from a bare prompt.
2. **Keep the spec's status current** as work proceeds (`draft → ready → in-progress → shipped`) —
   no matter who does the work (Claude, Cursor, Gemini, Devin, Copilot, a human, or any agentic
   framework). BMAD specs track status in the framework; legacy `docs/specs/*.md` track it in
   `status:` frontmatter.
3. **Autonomy.** Marshal (`bmad-loop` / `bmad-build-auto`) can watch `docs/dreams/`, run `bmad-spec`
   on a new Dream, and drive the build unattended — so "a Dream is written" can trigger "BMAD
   creates the spec" with no human in the loop.

## The tiers (do not cross them)

| Tier | Location | Purpose | Git |
|---|---|---|---|
| **0 — Dream** | `docs/dreams/*.md` | The raw human aspiration / starting point (BMAD — *Build More Architect Dreams*); Herald renders it into a deck, and BMAD turns it into the spec | tracked, permanent |
| **1 — Intake spec (LEGACY)** | `docs/specs/*.md` | Former hand-authored spec tier — kept for existing efforts, **superseded by Tier 2**; author no new files here | tracked, phasing out |
| **2 — Spec & planning (BMAD)** | `_bmad-output/projects/<slug>/planning-artifacts/` | The `bmad-spec` output + PRD, architecture, API/interface specs, epics+stories, gate reports — produced from the Dream. **The active spec lives here.** | tracked, permanent |
| **3 — Execution output** | `_bmad-output/projects/<slug>/implementation-artifacts/` (BMAD); your own tool dir for others | story files, sprint YAMLs, test outputs, retros | **local-only / gitignored** |

**Rules:**
- The **active spec is a BMAD artifact in Tier 2** — produced from a Tier-0 Dream. Don't hand-author
  a new spec in the legacy `docs/specs/` (Tier 1), and never drop one into a Tier-3 output dir.
- Each tool writes its working output into **its own** area (BMAD → `implementation-artifacts/`;
  Cursor → `.cursor/`; etc.) and **reads the spec from the BMAD planning folder** (Tier 2) — or a
  legacy `docs/specs/` file for an existing effort.
- `implementation-artifacts/` is gitignored/local-only — **nothing there should be git-tracked.**

## Dates, tags and versions (one rule: is it a date or a version?)

Two formats that sort alike but can never be confused for one another. The distinction is
load-bearing — the Fleet console extracts dates with `\d{4}-\d{2}-\d{2}`, so a dotted
version string cannot be mistaken for a date, and vice versa.

| It is a… | Format | Where |
|---|---|---|
| **date** | `YYYY-MM-DD` — hyphenated ISO, zero-padded | filenames (`…-research-2026-07-25.md`), directory names (`prd-<chain>-2026-07-25/`), frontmatter (`created:`, `updated:`, `date:`), changelog date lines |
| **version** | `YYYY.MM.DD` CalVer, declared **unpadded** (`2026.7.30`) | `pyproject.toml`, package metadata, git tags |

**Dates are zero-padded** and therefore sort correctly as plain text — that property belongs
to the date format only, and several tools here rely on it.

**Versions are declared unpadded** because PEP 440 normalization strips leading zeros
whatever you write: `2026.07.30` becomes `2026.7.30` in the wheel filename, the metadata and
on PyPI. Declaring the normalized form keeps declared == displayed. The consequence is that a
normalized version does **not** text-sort correctly (`2026.10.1` sorts before `2026.7.9`), so
**never text-sort a version** — use `sort -V`, or `packaging.version.Version` as the key.
A second release on one day takes a fourth segment: `2026.7.30.1`.

**A git tag is a version alias, not a date** — unpadded, byte-identical to the version.
Do not pad it: 1,926 recipes here build their source URL from `{{ version }}` (57 as
`/v{{ version }}`), so a `v2026.07.30` tag against a `2026.7.30` version resolves to a URL
that 404s.

**Chain-scoped artifacts carry both** the chain and the date in the filename **and** declare
them in frontmatter (`chain:`, `created:`, `updated:`). Redundant on purpose: the filename is
greppable and sortable with no parsing, the frontmatter is authoritative, and a detector
cross-checks them — so a rename that forgets the frontmatter, or an edit that forgets the
rename, becomes visible instead of silently drifting.

## Claude Design ↔ repo bridge (decks, prototypes)

When the session has the **`claude-design` MCP server** connected (`/design-login` in Claude
Code), visual artifacts round-trip by **tools, not downloads** — never ask the user to manually
export/copy a Design file. Dream: `docs/dreams/pyforge-herald.md` (absorbed `design-code-bridge` 2026-08-08); full procedure:
`docs/specs/presentation-deck.md` § *The MCP bridge*. In short:

- **Seed:** prove the prototype locally (`extract` + `build`), then `create_project` (bind the
  **Modernist** design system for PyForge persona decks), `finalize_plan`, `create_support_js`,
  `copy_files` a `deck-stage.js`, `write_files` the `.dc.html`.
- **Pull:** `read_file` with `if_none_match` (unchanged → repo already current); decode the
  entity-escaped body; land it in `presentations/<slug>/project/`; re-extract, rebuild,
  `deck-export`, commit.
- **Discipline:** etags on every read/write; only the prototype crosses (never a mirrored app
  tree); `get_claude_design_prompt` before any write; share only `claude.ai/design/...` links.

## Library catalog (what's available to import/run)

**`docs/reference/library-llms-full.md`** is the llms-full-style catalog of every library, CLI, and
framework available in this repo's pixi environments — per-library capabilities, version pins,
import-name gotchas, environment membership, and what is deliberately NOT installed. It is
derived from `pixi.toml` (the source of truth; regeneration prompt in its header). Consult it
before importing a library or proposing a new dependency, and run all work through
`pixi run -e local-recipes …`. Staleness check: `pixi run -e local-recipes llms-full-check`
exits non-zero when the catalog drifts from `pixi.toml`.

## How each tool discovers this

| Tool | Entry file (thin pointer → this file + `docs/dreams/` + the BMAD planning folder) |
|---|---|
| Claude Code | `CLAUDE.md` (full repo guidance) |
| Cursor | `.cursor/rules/specs.mdc` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Gemini CLI | `GEMINI.md` |
| Devin / Codex / Factory / Zed | this `AGENTS.md` |
| Agentic frameworks (BMAD, Agno, CrewAI, LangGraph) | start from the Dream in `docs/dreams/`; BMAD's `bmad-spec` produces the spec the agent then consumes |

## Keeping the BMAD planning docs accurate

The `_bmad-output/projects/local-recipes/` artifacts are kept in sync with the live repo by a
detector + reconciler loop — run `pixi run -e local-recipes bmad-drift-check` and follow
`_bmad-output/projects/local-recipes/SYNC-RUNBOOK.md`. The detector also enforces the tier rules
above (e.g. it HARD-fails if a spec is git-tracked under `implementation-artifacts/`).

<!-- SKF:BEGIN updated:2026-08-26 -->
[SKF Skills]|7 skills|0 stack
|IMPORTANT: Prefer documented APIs over training data.
|When using a listed library, read its SKILL.md before writing code.
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
