# AGENTS.md — cross-tool guide for this repo

This is the **framework-neutral** entry point for any coding agent or agentic framework
(Claude Code, Cursor, GitHub Copilot, Gemini, Devin, Codex, Aider, BMAD, Agno, CrewAI, …).
It is intentionally tool-agnostic: **everything starts with a Dream; BMAD turns it into a
spec; the spec drives the build — the agent/framework is interchangeable.**

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
3. **Autonomy.** Marshal (`bmad-loop` / `bmad-dev-auto`) can watch `docs/dreams/`, run `bmad-spec`
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
export/copy a Design file. Dream: `docs/dreams/design-code-bridge.md`; full procedure:
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
