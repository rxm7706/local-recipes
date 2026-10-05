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

**Behavioural guidelines** — the eight principles every harness follows (Think before coding · Simplicity first · Surgical changes, healed tissue · Goal-driven execution · Dream to code, always · State over action · Harness-owned ledgers are read-only · Implementation and review stay separate) live in `AGENTS.md` § *Behavioural guidelines (every harness)*, imported above; the `conda-forge-expert` skill specialises them for recipe work and the BMAD skills for planning/dev. Not restated here (scribe CAP-27, point-don't-copy; CAP-29 collapsed the duplicate).

## Legacy intake-spec index (read by `bmad-drift-check`)

Doctor's `bmad-drift-check` detector (`check_spec_indexed`) requires every `docs/specs/*.md` filename
to appear in this file. Author no new file there (`AGENTS.md` § *The tiers*); descriptions and
the shipped rows: `docs/reference/agent-instruction-notes.md` § *Intake specs*.

| Spec | Status |
|---|---|
| `docs/specs/flyte-conda-forge.md` | in-progress |
| `docs/specs/feedstock-refresh.md` | in-progress |
| `docs/specs/feedstock-platform-expansion.md` | workflow stub; body in `docs/how-to/feedstock-platform-expansion.md` |
| `docs/specs/feedstock-failure-remediation.md` | workflow stub; body in `docs/how-to/feedstock-failure-remediation.md` |
| `docs/specs/presentation-deck.md` | workflow stub; body in `docs/how-to/presentation-deck.md` |

## Where moved sections went

This file carried more sections until 2026-09-26 (scribe Story 21.1). A link that names one
lands here: where each went, and its full former text, are in
`docs/reference/agent-instruction-notes.md` § *Moved from CLAUDE.md*.

### Spec-driven, framework-neutral layout
<!-- marshal-seed:begin region=tiers model-version=1.0.0 sha=0b632764 -->
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
<!-- marshal-seed:end region=tiers -->

Now `AGENTS.md` § *The tiers* (including the durable story-spec rule) and § *Dream-first workflow*.

### Multi-Project Pattern
<!-- marshal-seed:begin region=bmad-multiproject model-version=1.0.0 sha=6a76c959 -->
This repository uses a single BMAD installation to drive multiple projects. Each project has its
own subdirectory under `_bmad-output/projects/<slug>/` containing planning artifacts,
implementation artifacts, project context, and project-scoped config overrides. See
**`_bmad-output/PROJECTS.md`** for the index and detailed documentation.

**At session start with the user**, ask which project they're working on (or check
`scripts/bmad-switch --current`) before invoking BMAD skills that write artifacts. Reading another
project's artifacts is fine without switching — read directly from the file path.

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

`_bmad/bmm/config.yaml` hard-codes `planning_artifacts: "{project-root}/_bmad-output/planning-artifacts"`,
and that key does **NOT** compose with a project's `output_folder` override — so **every BMAD
skill that writes planning artifacts resolves through these symlinks**, not through the marker.
Marker and symlinks must always agree; when they disagree, a write-skill silently targets the
*other* project. **Always switch with `scripts/bmad-switch <slug>`** (it re-points the symlinks
atomically and writes the marker last, so a failed re-point can't desync); never hand-edit the
marker. `scripts/bmad-switch --current` / `--list` warn on a desync — heed it before running any
BMAD write-skill.

**PARALLEL AGENTS: never touch the switch — address projects by physical path (HARD, since
2026-07-25).** The marker
*and* the symlinks are **per-working-tree global state**, so `scripts/bmad-switch` is a mutex
nobody holds: two concurrent BMAD write-agents will silently re-point each other's target
mid-write. When fanning out more than one agent that writes planning artifacts:

- **Write to `_bmad-output/projects/<slug>/planning-artifacts/…` literally.** Never to
  `_bmad-output/planning-artifacts/…` (the symlink) and never via a skill that resolves through
  it without pinning.
- **Do not call `scripts/bmad-switch`** from a parallel agent. If a skill needs the active
  project, pass **`BMAD_ACTIVE_PROJECT=<slug>` per invocation** — it takes precedence over the
  marker and mutates nothing shared.
- **Verify placement after writing** (`readlink -f`, or just check the file landed under the
  intended slug) — the failure is silent, never an error.

**Six-layer config merge** (highest priority last):

| Layer | Path                                                         | Scope                                |
|-------|--------------------------------------------------------------|--------------------------------------|
| 1     | `_bmad/config.toml`                                          | Installer team (regenerated)         |
| 2     | `_bmad/config.user.toml`                                     | Installer user (regenerated)         |
| 3     | `_bmad/custom/config.toml`                                   | Global custom team, all projects     |
| 4     | `_bmad/custom/config.user.toml`                              | Global custom user, all projects     |
| 5     | `_bmad-output/projects/<slug>/.bmad-config.toml`             | Project team, active project only    |
| 6     | `_bmad-output/projects/<slug>/.bmad-config.user.toml`        | Project user, active project only    |

Layers 5 and 6 only load when an active project resolves. To set the active project:
`scripts/bmad-switch <slug>`. To list projects: `scripts/bmad-switch --list`.

**Adding a new project:** see `_bmad-output/PROJECTS.md` § "Adding a new project."
<!-- marshal-seed:end region=bmad-multiproject -->

The rules, including PARALLEL AGENTS: `AGENTS.md` § *Policy* and § *Dream-first workflow* item 6.
Config layers: `_bmad-output/PROJECTS.md`; the marker-and-symlink mechanism: the notes file
§ *Multi-Project Pattern*.

## Team Memory

This repo carries a checked-in team-memory index at `.claude/memory/MEMORY.md` — one-line entries capturing team-relevant decisions, feedback, and reference material as reviewable prose (see `.claude/memory/README.md` for the schema and promotion workflow). It is imported below so the index is in context for every session. The import line must stay bare — a backticked `@path` is an inert code span, not an import.

The session-close ritual is `scribe capture`, stated once, in `AGENTS.md` § *Team memory — read at
session start, every harness* (imported above via `@AGENTS.md`) — not restated here.

@.claude/memory/MEMORY.md
