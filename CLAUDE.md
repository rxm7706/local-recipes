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

Now `AGENTS.md` § *The tiers* (including the durable story-spec rule) and § *Dream-first workflow*.

### Multi-Project Pattern

The rules, including PARALLEL AGENTS: `AGENTS.md` § *Policy* and § *Dream-first workflow* item 6.
Config layers: `_bmad-output/PROJECTS.md`; the marker-and-symlink mechanism: the notes file
§ *Multi-Project Pattern*.

## Team Memory

This repo carries a checked-in team-memory index at `.claude/memory/MEMORY.md` — one-line entries capturing team-relevant decisions, feedback, and reference material as reviewable prose (see `.claude/memory/README.md` for the schema and promotion workflow). It is imported below so the index is in context for every session. The import line must stay bare — a backticked `@path` is an inert code span, not an import.

The session-close ritual is `scribe capture`, stated once, in `AGENTS.md` § *Team memory — read at
session start, every harness* (imported above via `@AGENTS.md`) — not restated here.

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
