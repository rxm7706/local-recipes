---
title: '19.1: One AGENTS.md, reached natively or by a one-line pointer from every harness'
type: 'feature'
created: '2026-09-19'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md', '{project-root}/_bmad-output/projects/pyforge-scribe/planning-artifacts/research/multi-harness-instruction-surface-2026-09-19.md']
deferred:
  - summary: "The per-tool pointer files (`GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/*.mdc`) are not in `governance-currency`'s `DOCUMENTS`, so a skill, script or path named there can rot unnoticed; only `AGENTS.md` and `CLAUDE.md` are checked. Extending `DOCUMENTS` is a marshal change (`spec-fleet-consistency-standard` CAP-6 owns the script) — Dream item (8)."
    evidence: "`scripts/governance_currency_check.py` `DOCUMENTS = (_bmad-output/EXEMPLAR-STANDARD.md, AGENTS.md, CLAUDE.md, docs/reference/test-charter.md)`; PR #1513's GEMINI.md carried a wrong coverage-gate command that no detector saw."
    location: scripts/governance_currency_check.py
    severity: low
  - summary: "`AGENTS.md` is 476 lines and `CLAUDE.md` 357 after this story; Claude Code's guidance is under 200 lines per instruction file and BMAD's is 'only what is expensive to rediscover'. A Copilot or Devin session loads both. The shrink (nested `AGENTS.md` per station, path-scoped `.claude/rules/` and `.github/instructions/*.instructions.md`, CLAUDE.md deduplicated against the import) is Dream item (4), a later `bmad-spec` pass."
    evidence: "`wc -l AGENTS.md CLAUDE.md` on the branch; code.claude.com/docs/en/memory 'Size: target under 200 lines per CLAUDE.md file'."
    location: AGENTS.md
    severity: low
declared_low_risk: false
baseline_revision: '1ff4b6d212084d74e3be6112221a4261822d74f0'
final_revision: 'pending — the merge commit of PR #1513 (`Merge pyforge-scribe/19-1 into main`)'
---

<intent-contract>

## Intent

**Problem:** "What the team knows, every agent and every session knows" was true for one harness.
`CLAUDE.md` exists and never imported `AGENTS.md`, so Claude Code — the harness doing most of the
work — never loaded the verified `bmad:context` block (four PRs on 2026-09-19 carry the attribution
trailers it forbids). Gemini had no path to `AGENTS.md` at all. PR #1513 (a parallel session) tried
to fix parity by copying a manual into `GEMINI.md` and pointing every harness at five memory files
that exist only in one operator's Claude auto-memory.

**Approach:** one canonical `AGENTS.md`; every harness reaches it natively or through a one-line
pointer (`@AGENTS.md` in `CLAUDE.md`; `.gemini/settings.json` `context.fileName`;
`.vscode/settings.json` `chat.useAgentsMdFile`; Cursor / Codex / Copilot cloud agent / Devin / Jules
native); the per-tool files shrink to addenda; team memory is reached through `AGENTS.md` and filled
with `scribe capture`; a scribe meta-test is the gate (missing pointer, duplicated H2, oversized
per-tool file, dangling memory path).

## Boundaries & Constraints

**Always:**
- Edit `AGENTS.md` only outside the `<!-- bmad:context -->` block (that block is `bmad-project-context`'s).
- Cite team memory as `.claude/memory/<type>/<slug>.md` paths that exist; promote with `scribe capture`.
- Keep `GEMINI.md`, `.github/copilot-instructions.md` and `.cursor/rules/specs.mdc` under 60 lines and free of any H2 that `AGENTS.md` carries.
- Keep `@AGENTS.md` a bare line in `CLAUDE.md` (a backticked mention is an inert code span).

**Never:**
- Copy the checklist, the behavioural guidelines or the tier model into a per-tool file.
- Cite `~/.claude/projects/…` from a repo document.
- Touch `governance_currency_check.py` (marshal-owned; deferred).

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| Claude Code session in a checkout with `CLAUDE.md` | `AGENTS.md` loads through the import (`/context` lists it under Memory files) |
| Gemini CLI `/memory show` | `AGENTS.md` first, then `GEMINI.md` |
| VS Code Copilot chat reply | **References** lists `AGENTS.md` |
| `GEMINI.md` grows a `## Pre-PR` section | `test_per_tool_file_repeats_no_agents_md_section` reds |
| `AGENTS.md` cites `.claude/memory/feedback/<missing>.md` | `test_every_team_memory_path_agents_md_cites_exists` reds |
| someone removes `@AGENTS.md` from `CLAUDE.md` | `test_claude_md_imports_agents_md_as_a_bare_line` reds |
| a second `bmad:context` block appears | `test_bmad_context_block_is_intact` reds |
| `AGENTS.md` names a skill/script/path that no longer exists | `governance-currency` reds (`detectors-ci`) |

## Code Map

- `AGENTS.md` — § *Behavioural guidelines (every harness)*; § *Team memory — read at session start, every harness* (real `.claude/memory/` paths, `scribe capture`, the auto-memory distinction); § *How each harness loads this file* (the pointer table); checklist item 2 (exit codes / no pipes / no remote debugging / `pr-preflight` gaps), item 5 (co-governors), item 9 rewritten (the `dashboard/` extra boundary), item 10 (instruction files); old § *How each tool discovers this* collapsed to a pointer.
- `CLAUDE.md` — `@AGENTS.md` import with a three-line explanation.
- `GEMINI.md` — Gemini-only addendum (15 lines). `.gemini/settings.json` — new, `context.fileName: ["AGENTS.md","GEMINI.md"]`.
- `.github/copilot-instructions.md` — Copilot-only addendum (sandbox, 59-minute cap, `/instructions`).
- `.vscode/settings.json` — `chat.useAgentsMdFile: true`.
- `.claude/memory/feedback/{a-pr-from-a-parallel-agent-…,coverage-gates-run-per-station-…,before-pushing-a-non-recipe-branch-…}.md` + `MEMORY.md` — three direct captures (`scribe capture --type feedback`).
- `scripts/spec_surface_allowlist.txt` — `GEMINI.md` leaves the allowlist; `spec-pyforge-scribe` surface takes `GEMINI.md`, `.gemini/settings.json`, `.github/copilot-instructions.md`, the test.
- `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` — 18 tests (the gate).
- Chain: `docs/dreams/pyforge-scribe.md` (2026-09-19 entry), `specs/spec-pyforge-scribe/{.memlog.md,SPEC.md}` (CAP-27, constraint, surface), `research/multi-harness-instruction-surface-2026-09-19.md`, `epics.md` (Epic 19), `sprint-status-ledger.yaml`, `docs/foundry/capability-ledger.yaml`.

## Binding

Parent Spec capability: `spec-pyforge-scribe CAP-27`.
Surface: as in the Code Map.
Ledger key: `19-1-one-agents-md-reached-natively-or-by-a-one-line-pointer-from-every-harness`.
Ledger status: `done` (set at the review of PR #1513).
Minted 2026-09-19 at the review of PR #1513: the parallel session's PR carried no Dream entry, no CAP, no Story, no story spec, and a memory section citing files outside the repo. This spec is the record the story should have carried from the start.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** `spec-pyforge-scribe` CAP-27
**Given** `CLAUDE.md` exists and never imports `AGENTS.md`, Gemini has no `context.fileName`, and PR #1513 pointed every harness at memory files that live in one operator's home directory
**When** this story lands
**Then** Claude Code loads the verified `bmad:context` block through `@AGENTS.md`; Gemini loads `AGENTS.md` first through `.gemini/settings.json`; VS Code chat loads it through `chat.useAgentsMdFile`; the natively-reading harnesses keep loading it
**And** every memory path `AGENTS.md` cites exists; the per-tool files carry no section `AGENTS.md` carries; a scribe meta-test reds any regression
**Status:** done

</intent-contract>

## Spec Change Log

- 2026-09-19 — minted at review (see Binding). Mechanism changed from the parallel session's "copy the manual into GEMINI.md" (and an interim operator answer "copy into all tool files") to "point, don't copy" after the research showed Copilot's agent and Devin ingest every file together.

## Review Triage Log

### 2026-09-19 — Review pass (three layers over PR #1513 as opened — Blind Hunter, Intent Alignment, Current/Future-state — plus live vendor-doc research)

- intent_gap: 3
- bad_spec: 2
- patch: 9 (high 2, medium 4, low 3)
- defer: 2
- reject: 1
- addressed_findings:
  - `[high]` `[patch]` The "Auto-Memory Engine" section pointed every harness at five `feedback_*.md` files that exist only in `~/.claude/projects/…` (one operator's Claude auto-memory), not in `.claude/memory/` — a Gemini/Cursor/Copilot agent following it reads nothing. Rewritten as *Team memory*: real `.claude/memory/` paths, `scribe capture` as the way in, the auto-memory distinction stated; three lessons direct-captured into team memory; `test_every_team_memory_path_agents_md_cites_exists`.
  - `[high]` `[patch]` `CLAUDE.md` never imported `AGENTS.md`, so the verified block bound every harness except Claude Code (research finding 1; BMAD's `bmad-project-context` prescribes the import). Added `@AGENTS.md`; `test_claude_md_imports_agents_md_as_a_bare_line`.
  - `[medium]` `[patch]` `GEMINI.md` rewritten from a 14-line pointer into a 60-line manual duplicating CLAUDE.md's principles, AGENTS.md's checklist and the tier table, with a coverage-gate command that measures nothing outside steward and `pyforge-doctor-test` made mandatory for every PR. Restored to a Gemini-only addendum; Gemini reaches `AGENTS.md` through the new `.gemini/settings.json`; the duplication guard reds a repeat.
  - `[medium]` `[patch]` Checklist item 9 prescribed `django.apps.apps.get_model` inside function bodies for "core package utility modules (`src/pyforge/<station>/<module>.py`)" — a pattern the repo does not use (only `src/platform/` migrations) and a path that does not exist. Rewritten as the real invariant: no module-level `django`/`channels`/`dashboard` import outside the `dashboard/` extra; one sanctioned `importlib` reach pinned by steward's `test_invariants.py`.
  - `[medium]` `[patch]` Item 10 (multi-spec baseline audit) duplicated item 5 and item 12 (exit-code integrity) duplicated item 2 — folded into 5 and 2; item 11 (no remote debugging) kept and merged into 2 with `pr-preflight`'s known gaps named, because "exit 0 across all local suites" is otherwise unachievable (atlas WASM under `CI=1`).
  - `[medium]` `[patch]` `AGENTS.md` already had a § *How each tool discovers this* table (thin-pointer model, now stale); a second table would be the same drift the story forbids — collapsed into a pointer to the new § *How each harness loads this file*.
  - `[low]` `[patch]` The five behavioural guidelines existed only in `CLAUDE.md` (Claude-only); added once to `AGENTS.md` so every harness gets them.
  - `[low]` `[patch]` `.github/copilot-instructions.md` told Copilot to "then read `CLAUDE.md`" — the cloud agent ingests it regardless, and the instruction invited duplication; rewritten as the Copilot-only addendum.
  - `[low]` `[patch]` The PR body claimed a "PyForge Estate identity modernization", the foundry layout and "115 persistent memory entries" — none in the diff (the first two already in the verified block since 2026-09-06; the count is one operator's auto-memory). Body rewritten to the actual change.
  - `[intent_gap]` `[patch]` No Dream entry, no CAP, no Story, no story spec, no scribe memlog entry although `AGENTS.md` is on `spec-pyforge-scribe`'s surface — the full chain minted (Dream entry, CAP-27, Epic 19 / Story 19.1, this spec, capability-ledger row, memlogs, scoped stamps).
  - `[bad_spec]` `[patch]` PR #1513's own § "12 Pre-Flight Invariants" put governance content in `GEMINI.md`, a file no detector checks (`governance-currency` covers `AGENTS.md`/`CLAUDE.md` only) — deferred as DW (the script is marshal's); the parity test covers the duplication half now.
  - `[reject]` "Add `fold-exemption: cross-station-seam` for cross-station capabilities" (the pre-#1507 item 6 wording) is already gone from `main`; nothing to patch here.
  - `[defer]` ×2 — see frontmatter `deferred:` (pointer files in `governance-currency`; root-file size discipline).

## Design Notes

- **Current state → target state.** Today: `CLAUDE.md` (357 lines, Claude-only) and `AGENTS.md` (476) both carry the contract; only Cursor / Codex / Copilot / Devin read `AGENTS.md`; Gemini reads nothing but `GEMINI.md`; Claude Code reads nothing but `CLAUDE.md`. After 19.1: every harness loads `AGENTS.md` (natively or via one line); per-tool files are addenda; a test guards it. Future (Dream items 4–10, not this story): root file < 200 lines with nested `AGENTS.md` per station and path-scoped rules; skills on the Agent Skills neutral path; transcript ingestion for non-Claude harness logs; recall from the Guild env / MCP for 59-minute cloud sessions; pointer files in `governance-currency`; per-spec surface baselines; Devin Playbooks / Copilot custom agents as dispatch and persona analogues.
- **Why not copies.** The Copilot cloud agent reads `AGENTS.md` + `copilot-instructions.md` + `CLAUDE.md` + `GEMINI.md`; Devin's Knowledge auto-pulls `AGENTS.md`, `CLAUDE.md` and every `.mdc`. A mirrored manual is loaded 2–3× per session and any later edit becomes a contradiction ("Claude may pick one arbitrarily" — Claude Code docs). Pointers are idempotent under duplication; copies are not.
- **Why scribe owns this.** `AGENTS.md` has been on `spec-pyforge-scribe`'s surface since 2026-09-13 (CAP-15 / CAP-21 — durable session instructions); team memory is CAP-1; the instruction surface is the thing scribe's "what the team knows, every agent knows" is delivered through.
- **Attribution.** The verified block's "no `Co-Authored-By`, no AI attribution" now binds Claude Code sessions too; the operator confirmed the rule stands (2026-09-19). A `commit-msg` hook is the block's own TODO.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (station policy verify command; includes the 18 parity tests).

**Manual checks (real tree):**
- `python scripts/governance_currency_check.py --file AGENTS.md` and `--file CLAUDE.md` → exit 0.
- In a Claude Code session at the repo root, `/context` lists `AGENTS.md` under Memory files.
- `gemini` at the repo root, `/memory show` → `AGENTS.md` then `GEMINI.md`.

## Auto Run Result

- **Summary:** PR #1513 (a parallel session's `docs(governance): enhance AGENTS.md and GEMINI.md
  pre-PR pre-flight invariants`, 3 commits on `1ff4b6d212`) reviewed against the scribe Dream / Spec /
  PRD and the live docs of every harness the estate runs (research doc), then rebuilt as Story 19.1:
  the mechanism inverted from copies to pointers, the memory section made true, the checklist
  deduplicated and corrected, the Claude Code import added, Gemini and VS Code settings checked in,
  three team-memory captures made, and an 18-test parity gate added to the scribe suite (verified to
  red against today's `main` on four of its assertions).
- **Verification (exit codes read directly, 2026-09-19):** filled in at landing — see the PR.
- **Files changed:** see Code Map.
