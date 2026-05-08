# Tech Spec: `claude-team-memory`

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> bounded scope, single feature, ~10 implementation stories, no separate
> PRD / architecture phase needed).
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/claude-team-memory.md
> ```

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only, no PRD/architecture phase) |
| Scope | Layers 1 + 2 of the team-memory analysis (checked-in `.claude/memory/` + `team-memory` skill). Layers 3 (Stop hook automation) and 4 (plugin packaging) are explicitly deferred. |
| Target users | Every developer working in this repo. v1 is single-author (rxm7706); design tolerates future multi-author without rework. |
| Distribution | Lives entirely inside this repo. No PyPI / conda / pip / npm / plugin marketplace package. |
| Lifetime | Long-running — replaces ad-hoc manual promotion of user-local auto-memory entries into `CLAUDE.md`. |
| Companion to | `~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/` (per-user auto-memory) |

---

## Background and Context

### The problem

Claude Code's auto-memory system writes to
`~/.claude/projects/<encoded-path>/memory/` — **per-machine, per-user**.
Entries that are genuinely team-relevant (rules about how every developer
should work in this repo) get trapped there, invisible to anyone else who
clones the repo. Today the only way to share them is to **manually edit
`CLAUDE.md`**, which is friction-laden and easy to skip.

Concrete example that motivated this spec: in commit `d43899c1cb` the
owner shipped two team-relevant rules (`feedback_bmad_uses_cfe_skill.md`
and `feedback_bmad_runs_cfe_retro.md`) into user-local auto-memory and
**also** into `CLAUDE.md`. The duplication is the friction made visible —
user-local memory had to be hand-promoted to a checked-in surface.

### What's been ruled out

- **First-class team-shared memory in Claude Code.** Not shipped (open
  feature request: `anthropics/claude-code#38536`). CLAUDE.md, rules, and
  skills are the only durable team-shared surfaces.
- **Switching to a community memory plugin** (e.g., `claude-mem`,
  `claude-mem-sync`, `memory-toolkit`, `Claudeception`). Each restructures
  how memory is stored or captured; would conflict with the existing
  BMAD multi-project + conda-forge-expert layout. Plus: third-party
  unmaintained risk.
- **Auto-fire on session end via `Stop` hook (Layer 3 of the analysis).**
  Deferred. v1 stays manual: `/team-memory` is invoked explicitly. Adding
  a hook later is additive; baking it in now risks hooks-noise before the
  manual workflow is proven.
- **Packaging as a plugin (Layer 4).** Deferred until a second repo wants
  this. YAGNI otherwise — the entire feature is ~3 markdown files.
- **Replacing user-local auto-memory.** Not goal. User-local memory keeps
  per-user nuance (terse-vs-verbose preferences, personal habits). The
  team-memory layer is **additive and selective**.

### What's available to leverage

- **Auto-memory frontmatter schema** at
  `~/.claude/projects/<encoded-path>/memory/*.md` — `name` / `description`
  / `type` fields with a body. The team-memory layer reuses this 1:1 so
  promotion is mechanical, not translation.
- **CLAUDE.md `@import` syntax** (5-hop max, fully loaded at session
  start). Wiring `@.claude/memory/MEMORY.md` into CLAUDE.md is the
  entire "make team memory visible" mechanism. No hook required.
- **`bmad-distillator` and `bmad-retrospective` skills.** Both already
  do a related job — distillator compresses a source doc; retrospective
  writes lessons after an epic. The `team-memory` skill steals their
  shape (proposal-then-confirm, frontmatter-aware) and narrows scope to
  "session → team-memory promotion."
- **Existing `.claude/skills/` directory** — committed, hot-reloaded,
  46 skills already living there. New skill drops in cleanly.

---

## Goals

- **G1.** A checked-into-the-repo `.claude/memory/` directory that
  mirrors the schema of user-local auto-memory and is auto-loaded into
  every session (via CLAUDE.md `@import`).
- **G2.** A `team-memory` skill that, on invocation, reads user-local
  memory + recent session context and proposes a diff promoting
  team-relevant entries into `.claude/memory/`.
- **G3.** Promotion is **proposal-then-confirm**, never auto-commit. The
  skill stops after writing the proposed files; the human reviews and
  commits.
- **G4.** Promoted entries get **rewritten in a team voice** (impersonal,
  no "I prefer…"), not copy-pasted verbatim from user-local memory.
- **G5.** After promotion, the user-local entry becomes a **one-line
  pointer stub** (`Promoted to .claude/memory/feedback/X.md`), not
  deleted. Preserves traceability; avoids re-promotion churn.
- **G6.** A documented **team-relevance test** baked into the skill so
  decisions are repeatable: *"Would a brand-new contributor to this repo,
  on their first session, without ever having talked to me, benefit from
  this rule?"* Yes → promote. No → leave personal.
- **G7.** Initial seed: migrate the two existing BMAD↔CFE feedback rules
  from user-local memory + `CLAUDE.md` into `.claude/memory/feedback/`,
  proving the workflow end-to-end.
- **G8.** `MEMORY.md` index stays under 200 lines (Claude Code truncates
  past that). Enforced by convention, not tooling, in v1.

## Non-Goals

- **NG1.** No automation. v1 is manual `/team-memory` invocation only.
- **NG2.** No Stop / SessionEnd hook. Deferred to v2.
- **NG3.** No plugin packaging or marketplace publication. Deferred.
- **NG4.** No replacement of user-local auto-memory. Coexists.
- **NG5.** No cross-repo synchronization. Each repo has its own
  `.claude/memory/`.
- **NG6.** No conflict resolution beyond standard git merge. If two
  developers concurrently promote the same rule, git decides; the skill
  does not need to merge entry files.
- **NG7.** No TTL / decay / staleness scoring on entries. v1 trusts
  humans to prune.
- **NG8.** No write to `.claude/agents/` or `.claude/skills/` from the
  promotion flow — the skill writes only inside `.claude/memory/`.
- **NG9.** No new Python scripts. The entire feature is markdown:
  directory + index + skill. No `.claude/scripts/` additions in v1.
- **NG10.** No analytics / metrics / dashboard. Not needed at this scale.

---

## Lifecycle Expectations

The team-memory layer is **long-running**, like the conda-forge-tracker
spec — it's not a one-shot migration:

- **Bootstrap once:** scaffold `.claude/memory/` (Story 1), create the
  `team-memory` skill (Story 2), wire the import into `CLAUDE.md`
  (Story 5), and run the seed promotion of the two existing CFE rules
  (Story 6).
- **Use ad hoc:** whenever the user notices accumulated user-local
  memory entries that look team-relevant, invoke `/team-memory`. Expected
  cadence: every few sessions, or after a notable burst of new feedback
  entries.
- **Prune occasionally:** when a rule becomes obsolete (skill changes,
  project pivots), edit `.claude/memory/MEMORY.md` to remove the line and
  delete or archive the entry file. Standard git workflow.

The `team-memory` skill itself is expected to evolve via the same
BMAD↔conda-forge-expert retrospective pattern — invoke
`bmad-retrospective` when corrections / refinements / additions surface,
land them as edits to the skill's `SKILL.md`. The skill's CHANGELOG
records the deltas.

---

## User Stories

Each story is sized for one BMAD `bmad-create-story` / `bmad-dev-story`
cycle. Stories are grouped into three waves; each wave is independently
shippable.

### Wave A — Foundation (Stories 1, 2, 4, 5, 8)

#### Story 1 — Scaffold `.claude/memory/` directory

**As** the owner,
**I want** an empty `.claude/memory/` directory with a starter
`MEMORY.md` index, a `feedback/` subdir, and a `README.md`,
**so that** there is a checked-in destination for promoted entries with
documented schema and scope rules.

**Acceptance:**

- Directory `.claude/memory/` exists with subdirectories
  `feedback/`, `project/`, `reference/` (matching user-local auto-memory
  type taxonomy).
- `.claude/memory/MEMORY.md` exists with the canonical index format
  (sections `## Feedback` / `## Project` / `## Reference`, each empty
  initially, header explaining what this file is and the 200-line
  truncation rule).
- `.claude/memory/README.md` documents: purpose, schema (frontmatter
  fields), scope rule (the "team-relevance test" from G6), how the
  skill writes to it, and the relationship to user-local auto-memory.
- Each subdirectory contains a `.gitkeep` so the structure is committed
  even when empty.
- `.gitignore` is **not** updated — everything under `.claude/memory/`
  is intentionally tracked (unlike `.claude/data/` which stays ignored).

#### Story 2 — Create `team-memory` skill scaffold

**As** the owner,
**I want** `.claude/skills/team-memory/SKILL.md` with frontmatter
(`name`, `description`, `model`, `tools`) and a stub workflow body,
**so that** Claude Code auto-discovers `/team-memory` and the skill is
invocable.

**Acceptance:**

- `SKILL.md` frontmatter:
  - `name: team-memory`
  - `description:` clearly states "Promote team-relevant entries from
    user-local auto-memory into checked-in `.claude/memory/`. Invoke when
    user-local entries have accumulated and may belong in version
    control."
  - `model:` unset (inherits from session) or `inherit`.
  - `tools:` minimal — `Read`, `Write`, `Edit`, `Bash` (for `ls` of
    user-local memory), `Glob`.
- Body has the placeholder sections defined in Story 4 (Workflow,
  Frontmatter Schema, Team-Relevance Test, Output Contract).
- Skill loads on session start without error (visible in `/skills` or
  via the system reminder).
- Invoking `/team-memory` enters the skill (even if the body is still
  mostly stub at this point — Story 4 fills it in).

#### Story 4 — `team-memory` skill workflow body

**As** Claude executing `/team-memory`,
**I want** an explicit step-by-step workflow in `SKILL.md` that
classifies user-local entries and proposes a promotion diff,
**so that** every invocation produces a consistent, reviewable output.

**Acceptance:**

- Workflow defined as a numbered sequence:
  1. Resolve user-local memory path:
     `~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/`.
     (Skill reads this dynamically — the path is derived from `pwd` +
     standard Claude Code encoding rule, documented in the skill body
     as a note.)
  2. List entries there; read each frontmatter + body.
  3. Read `.claude/memory/MEMORY.md` and every entry it references.
  4. Classify each user-local entry into one of:
     - **team-relevant** — passes the test in Story 3.
     - **personal** — fails the test; leave alone.
     - **already-promoted** — pointer stub or content match exists in
       `.claude/memory/`.
     - **stale** — refers to deleted code / obsolete rule; flag but
       don't auto-promote.
  5. For each `team-relevant` entry, draft a rewritten team-voice
     version (rules in Story 3).
  6. Output a structured proposal: list of files to write, full content
     of each, and the updated `MEMORY.md` index.
  7. Show the proposed pointer-stub edit for each promoted user-local
     entry (Story 7 defines the pointer format).
  8. **Stop**. Do not execute writes. Wait for user confirmation.
  9. On confirmation: execute the writes, update `MEMORY.md`, edit each
     user-local entry to its pointer stub, then summarize.
- Workflow body includes one worked example showing input (one
  user-local entry), classification reasoning, rewritten output, and the
  resulting MEMORY.md line.

#### Story 5 — Wire `@.claude/memory/MEMORY.md` into root `CLAUDE.md`

**As** every developer working in this repo,
**I want** `CLAUDE.md` to import `.claude/memory/MEMORY.md` so the team
memory loads automatically at session start,
**so that** promoted entries are visible without any extra setup.

**Acceptance:**

- A new short section near the bottom of `CLAUDE.md` (just above
  "Project Documentation Reference" or at the very end — see Q3 in Open
  Questions) reads:
  ```markdown
  ## Team Memory

  Team-relevant rules and context that have been promoted from user-local
  auto-memory. See `.claude/memory/README.md` for the schema and the
  promotion workflow.

  @.claude/memory/MEMORY.md
  ```
- After this change, opening a fresh Claude Code session in the repo
  shows the index content in context (verifiable by asking Claude to
  "list every entry currently in team memory").
- No other CLAUDE.md content is removed in this story (the BMAD↔CFE
  rules section is touched separately in Story 9 if Q3 resolves to
  "remove").

#### Story 8 — `.claude/memory/README.md` schema + workflow doc

**As** a future contributor (human or LLM),
**I want** a README at `.claude/memory/README.md` that documents the
schema, the team-relevance test, the skill's workflow, and the
pointer-stub convention,
**so that** the design is recoverable months later without re-deriving
it from this spec.

**Acceptance:**

- README sections:
  - **Purpose** — what `.claude/memory/` is and why it exists.
  - **Relationship to user-local auto-memory** — both schemas; this
    layer is additive, selective, team-relevant only.
  - **Schema** — frontmatter fields (`name`, `description`, `type` ∈
    `{feedback, project, reference}`), body shape.
  - **MEMORY.md index** — one-line entries, ≤ 200 lines, format is
    `- [Title](file.md) — one-line hook`.
  - **Team-relevance test** — the day-1 contributor heuristic from G6.
  - **Promotion workflow** — invoke `/team-memory`; review proposal;
    confirm; commit.
  - **Pointer stubs** — what they are, why we keep them, format.
  - **When to prune** — humans decide; standard git delete.
- README cross-links the `team-memory` skill, the user-local memory path,
  and this spec.

### Wave B — Initial promotion (Stories 3, 6, 7)

#### Story 3 — Team-relevance test + team-voice rewrite rules in `SKILL.md`

**As** Claude executing the skill,
**I want** explicit rules in the skill body for (a) deciding what's
team-relevant and (b) how to rewrite an entry into team voice,
**so that** classification and rewriting are deterministic, not
improvised per session.

**Acceptance:**

- Skill body has a section "Team-Relevance Test" stating:
  > An entry is team-relevant **iff** a brand-new contributor working
  > in this repo on their first day, without ever having talked to the
  > current owner, would benefit from this rule. Personal taste,
  > workflow tics, individual tone preferences, terseness preferences,
  > and other "how Claude works for *me*" rules are **not**
  > team-relevant.
- Skill body has a section "Team-Voice Rewrite Rules":
  - Strip first-person ("I prefer…" → "Use…" or "The convention is…").
  - Drop the "user prefers" framing ("user prefers X" → "X").
  - Drop incident-specific anecdotes; keep the rule + brief reason.
  - Preserve the **Why:** and **How to apply:** structure where the
    user-local entry has it.
  - Preserve all file paths, command names, identifiers verbatim.
- Skill body shows two before/after rewrite examples — one feedback
  entry (rule-style) and one project entry (fact-style).

#### Story 6 — Seed promotion: BMAD↔CFE feedback rules

**As** the owner,
**I want** the two existing CFE-related feedback rules promoted as the
seed content of `.claude/memory/feedback/`,
**so that** the team-memory layer is non-empty on first commit and
proves the workflow against real entries.

**Acceptance:**

- `.claude/memory/feedback/bmad_uses_cfe_skill.md` exists, derived
  from user-local `feedback_bmad_uses_cfe_skill.md`, rewritten in team
  voice per Story 3 rules.
- `.claude/memory/feedback/bmad_runs_cfe_retro.md` exists, derived
  from user-local `feedback_bmad_runs_cfe_retro.md`, similarly
  rewritten.
- `.claude/memory/MEMORY.md` lists both with one-line hooks.
- The user-local source entries are converted to pointer stubs per
  Story 7.
- The seed promotion is performed **by invoking `/team-memory`**, not
  by hand — this is the end-to-end test of the skill. The story is
  complete only when the skill workflow runs against these two real
  entries and produces the diff that gets committed.

#### Story 7 — Pointer-stub convention + applied to seed promotion

**As** the owner,
**I want** a documented format for the post-promotion pointer stub in
user-local memory,
**so that** future `/team-memory` runs can detect "already-promoted"
without re-reading the original body.

**Acceptance:**

- Format defined in the skill body and `.claude/memory/README.md`:
  ```markdown
  ---
  name: {{original name}}
  description: {{original description}}
  type: {{original type}}
  promoted: true
  ---

  Promoted to `.claude/memory/{{type}}/{{filename}}.md` in repo
  `local-recipes` on {{ISO date}}. See that file for the canonical
  team-shared version. Do not edit this stub — edit the promoted file
  in the repo.
  ```
- The two seed entries from Story 6 are converted to this stub format
  in user-local memory after the promotion lands.
- Pointer stubs are detected in Story 4 step 4 by the `promoted: true`
  frontmatter field.

### Wave C — Integration polish (Stories 9, 10)

#### Story 9 — Update root `CLAUDE.md` references + decide Q3 (de-dup)

**As** the owner,
**I want** the root `CLAUDE.md` to reference the new `team-memory`
skill in the Skill Reference table, and to either link or remove the
duplicated BMAD↔CFE rules now that they live in `.claude/memory/`,
**so that** the canonical home is unambiguous.

**Acceptance:**

- `CLAUDE.md` Skill Reference table gains a row for `team-memory` with
  the trigger ("when user-local auto-memory has accumulated…").
- **If Q3 resolves to "remove":** the entire `## BMAD ↔
  conda-forge-expert integration` section in `CLAUDE.md` is replaced
  with a single line: "See `.claude/memory/feedback/bmad_uses_cfe_skill.md`
  and `.claude/memory/feedback/bmad_runs_cfe_retro.md` (loaded
  automatically via `@.claude/memory/MEMORY.md`)."
- **If Q3 resolves to "keep both":** the `CLAUDE.md` section gains a
  "Canonical home: `.claude/memory/feedback/…`" pointer at the top of
  each rule, but the body stays.
- **If Q3 resolves to "shrink to a stub":** middle ground — keep the
  section header, replace the body with one-paragraph summaries +
  pointers.

#### Story 10 — Skill smoke test + manual exercise

**As** a future maintainer,
**I want** confidence that the skill behaves correctly on a range of
inputs,
**so that** drift is caught before it accumulates.

**Acceptance:**

- A manual test transcript (saved to
  `.claude/skills/team-memory/test-transcripts/seed-promotion.md` —
  optional, gitignored if it gets long) records the skill's first run
  on the two seed entries.
- The skill is exercised against three additional manufactured cases
  (each a 5-line throwaway entry written to user-local memory by hand,
  invoked, observed, then rolled back):
  1. A clearly **personal** entry (e.g., "user prefers terse output")
     — verify it is **not** promoted.
  2. A clearly **stale** entry (mentions a deleted file path) —
     verify it is flagged, not promoted.
  3. A clearly **already-promoted** entry (a copy of a seed entry) —
     verify it is detected and skipped.
- The smoke results inform any quick refinements to Story 3's rules
  before the spec is closed.

---

## Functional Requirements

### FR-1: Frontmatter schema parity
Entries in `.claude/memory/` MUST use the same frontmatter fields as
user-local auto-memory: `name`, `description`, `type`. The `type` value
MUST be one of `feedback`, `project`, `reference`. This parity makes
mechanical migration possible in either direction.

### FR-2: MEMORY.md index size discipline
`.claude/memory/MEMORY.md` MUST stay under 200 lines (Claude Code
truncates beyond that). Enforced by convention only — entries are
one-line `- [Title](file.md) — hook`. No tooling check in v1.

### FR-3: Proposal-then-confirm
The `team-memory` skill MUST stop after producing the proposed diff
and wait for explicit user confirmation before writing. No auto-commit,
no auto-write of multiple files in one shot without review.

### FR-4: Team-voice rewrite required
Promoted entries MUST be rewritten per Story 3's rules — no verbatim
copy from user-local memory. The skill body shows the before/after
examples; the rule is enforced by the skill instructions, not tooling.

### FR-5: Pointer stub after promotion
After the user confirms promotion, the skill MUST replace the source
user-local entry with the pointer stub format (Story 7). The original
body content is **not** preserved in user-local memory after promotion
— it lives in the promoted file and in git history of `.claude/memory/`.

### FR-6: Detect already-promoted entries
The skill MUST detect already-promoted entries by the `promoted: true`
frontmatter field and skip them (no re-classification, no re-promotion
proposal). Idempotent against repeated invocation.

### FR-7: Read-only access to anything outside `.claude/memory/`
The skill MUST NOT write to `.claude/skills/`, `.claude/scripts/`,
`.claude/agents/`, `.mcp.json`, `recipes/`, `_bmad/`, or
`_bmad-output/`. Writes to `CLAUDE.md` are also out of scope for the
skill (Story 5 and Story 9 are human-driven edits, not skill outputs).

### FR-8: Type taxonomy match
`.claude/memory/` subdirectories MUST be `feedback/`, `project/`,
`reference/` — same three types as user-local auto-memory. Promotion
into a subdirectory matches the source entry's `type` field unless the
human reclassifies during review.

### FR-9: Manual-only invocation in v1
The skill MUST be invoked manually via `/team-memory`. v1 MUST NOT
register a `Stop`, `SessionEnd`, `PreCompact`, or any other hook in
`.claude/settings.json`. Hooks are deferred to v2.

---

## Technical Approach

### Stack

- **Language:** Markdown only. No Python, no shell scripts (in v1).
- **Files added:** ~5 markdown files (1 skill, 1 README, 1 MEMORY.md
  index, 2 seed feedback entries) + 3 `.gitkeep`s + edits to root
  `CLAUDE.md`.
- **Build:** none.
- **Test:** manual exercise per Story 10.

### File layout

```
local-recipes/
├── CLAUDE.md                          # edited — Story 5, optionally Story 9
├── .claude/
│   ├── memory/                        # NEW
│   │   ├── README.md                  # Story 8
│   │   ├── MEMORY.md                  # Story 1, 6
│   │   ├── feedback/
│   │   │   ├── .gitkeep
│   │   │   ├── bmad_uses_cfe_skill.md # Story 6 (seed)
│   │   │   └── bmad_runs_cfe_retro.md # Story 6 (seed)
│   │   ├── project/
│   │   │   └── .gitkeep
│   │   └── reference/
│   │       └── .gitkeep
│   └── skills/
│       └── team-memory/               # NEW
│           ├── SKILL.md               # Stories 2, 3, 4, 7
│           └── test-transcripts/      # OPTIONAL, gitignored if used
│               └── .gitkeep
```

No changes to `.gitignore` — all new content under `.claude/memory/`
is intentionally tracked.

### `team-memory` skill body shape

```markdown
---
name: team-memory
description: |
  Promote team-relevant entries from user-local auto-memory
  (~/.claude/projects/.../memory/) into checked-in .claude/memory/.
  Invoke when user-local entries have accumulated and some look
  team-relevant.
tools: [Read, Write, Edit, Bash, Glob]
---

# team-memory

## When to invoke

[…]

## Workflow (9 steps — see Story 4)

1. Resolve user-local memory path
2. List + read entries
3. Read .claude/memory/ current state
4. Classify each entry: team-relevant | personal | already-promoted | stale
5. Draft team-voice rewrites for team-relevant entries
6. Output structured proposal
7. Show pointer-stub edits
8. STOP — wait for confirmation
9. On confirm: execute writes + update MEMORY.md + apply pointer stubs

## Team-Relevance Test (Story 3)

[verbatim definition + 2-3 examples]

## Team-Voice Rewrite Rules (Story 3)

[5 rules + 2 before/after examples]

## Pointer Stub Format (Story 7)

[verbatim YAML+body template]

## Output Contract

The skill always produces:
- A list of proposed new files (path + full content).
- Updated MEMORY.md content.
- A list of pointer-stub edits to user-local entries.
- A short summary categorizing every user-local entry.
```

### `.claude/memory/MEMORY.md` initial contents (post-Story 6)

```markdown
# Team Memory Index

Team-relevant rules and context promoted from user-local auto-memory.
See `README.md` for schema and the promotion workflow.

⚠️  Keep this file under 200 lines — Claude Code truncates beyond that.
Each entry is one line; details live in the linked file.

## Feedback

- [BMAD must invoke conda-forge-expert for any conda-forge work](feedback/bmad_uses_cfe_skill.md) — Always-on integration rule
- [Every conda-forge BMAD effort ends with a CFE-skill retro](feedback/bmad_runs_cfe_retro.md) — Always-on closeout rule

## Project

(none yet)

## Reference

(none yet)
```

### Promotion classification rules (in skill body)

| User-local entry trait | Classification | Action |
|---|---|---|
| `promoted: true` in frontmatter | already-promoted | skip |
| Body matches existing `.claude/memory/<type>/*.md` content | already-promoted | skip + propose adding `promoted: true` to user-local |
| References file/path that no longer exists in repo | stale | flag, don't promote, list for human review |
| Contains "user prefers", "I like", individual tone/style guidance | personal | leave alone |
| Rule about how the team works in this repo (build, test, conventions, BMAD/CFE patterns, project-specific gotchas) | team-relevant | promote |
| Reference to external system (Linear, Slack, Grafana) used by the team | team-relevant | promote |
| Project fact about ongoing work, freezes, deadlines, stakeholder asks | team-relevant if shared, personal if individual scheduling | judge per the day-1-contributor test |

### What the skill explicitly does NOT do

- Does not run `git add` / `git commit`. Human commits.
- Does not modify CLAUDE.md (Story 5 and 9 are human edits).
- Does not write to `.claude/skills/` or any other skill directory.
- Does not delete entries from user-local memory — only converts to
  pointer stubs (Story 7).
- Does not re-run automatically. Pure on-demand.

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** `.claude/memory/` exists and is committed with the
  documented structure (README, MEMORY.md, three subdirs, .gitkeeps).
- **AC-2.** A fresh Claude Code session in the repo loads
  `.claude/memory/MEMORY.md` automatically (visible by asking Claude to
  "list everything in team memory").
- **AC-3.** Invoking `/team-memory` runs the 9-step workflow and
  produces a structured proposal for at least one of the seed
  user-local entries before any code is written.
- **AC-4.** The two seed entries (`bmad_uses_cfe_skill`,
  `bmad_runs_cfe_retro`) live in `.claude/memory/feedback/`, are
  rewritten in team voice (no first-person, no "user prefers"), and
  appear in `MEMORY.md`.
- **AC-5.** The user-local source entries for those two rules are
  pointer stubs after promotion (`promoted: true` + pointer body).
- **AC-6.** Re-invoking `/team-memory` after a successful promotion
  classifies the just-promoted entries as `already-promoted` and skips
  them (idempotency check).
- **AC-7.** A clearly personal user-local entry (created by hand for
  the smoke test) is classified `personal` and not promoted.
- **AC-8.** No file outside `.claude/memory/` and `.claude/skills/team-memory/`
  is written by the skill. (CLAUDE.md edits are human-authored in
  Stories 5 and 9.)
- **AC-9.** `.claude/memory/MEMORY.md` is ≤ 200 lines after the seed
  promotion (trivially satisfied; this is a discipline check for the
  future).
- **AC-10.** The `team-memory` skill body documents the team-relevance
  test, the team-voice rewrite rules, the pointer stub format, and the
  output contract — all four sections present and non-empty.

---

## Open Questions

These are the design decisions deferred to BMAD planner / human
elicitation before story execution. Each has a recommended default; the
Quick Flow planner should confirm or override.

### Decided in this spec (do not re-litigate)

| # | Decision | Rationale |
|---|---|---|
| D1 | Promoted entries get rewritten in team voice (not verbatim copy) | User-local entries embed first-person phrasing; reads wrong as a team rule. |
| D2 | After promotion, user-local entry → pointer stub (not deleted) | Preserves traceability; `promoted: true` is the idempotency signal. |
| D3 | Team-relevance test = "day-1 contributor without talking to me" | Simple, repeatable heuristic; avoids endless judgment calls. |
| D4 | v1 is manual `/team-memory` only — no Stop hook | Hooks add noise before the manual workflow is proven. Layer 3 of analysis is deferred. |
| D5 | No plugin packaging | YAGNI until a second repo wants this. Layer 4 of analysis is deferred. |
| D6 | Frontmatter / type taxonomy matches user-local auto-memory exactly | Mechanical migration possible in either direction. |
| D7 | No new Python scripts in v1 | Entire feature is markdown — keep it that way. |

### Must answer (v1-blocking)

| # | Question | Tradeoff | Default |
|---|---|---|---|
| Q1 | Skill name — `team-memory` vs `promote-memory` vs `share-memory`? | `team-memory` reads as the *thing*; `promote-memory` reads as the *action*; `share-memory` is closest to "what it does." | `team-memory` |
| Q2 | Multi-project shape — flat (`.claude/memory/feedback/X.md`) vs partitioned by BMAD project (`.claude/memory/projects/<slug>/feedback/X.md`)? | Flat is simpler and matches user-local memory's shape. Partitioned matches `_bmad-output/projects/<slug>/`. Most team-relevant rules are repo-wide, not project-specific. | Flat. Revisit if entries cross 30 and per-project rules dominate. |
| Q3 | Once seed entries are promoted, what happens to the BMAD↔CFE rules section currently in `CLAUDE.md`? | (a) Remove it entirely — single source of truth in `.claude/memory/`. (b) Keep both — explicit redundancy. (c) Shrink to one-paragraph stub + pointer. | (a) Remove — `@.claude/memory/MEMORY.md` import already loads the full rules into context. Redundancy hurts maintenance. |

### Behavior — confirm or override

| # | Question | Default |
|---|---|---|
| Q4 | Does the skill require explicit user confirmation per file, or one bulk confirmation? | One bulk confirmation per invocation. |
| Q5 | Stale entries — flag-only, or auto-delete after N runs? | Flag-only in v1. Human deletes. |
| Q6 | Should the skill propose a CHANGELOG entry alongside each promotion? | No. The promoted file's git history is the changelog. |
| Q7 | Should `/team-memory --dry-run` exist as a separate flag? | No — proposal-then-confirm makes every invocation effectively dry-run until confirmed. |

### Conventions

| # | Question | Default |
|---|---|---|
| Q8 | Filename convention for promoted entries — same as user-local (`bmad_uses_cfe_skill.md`) or restructured? | Same. Mechanical. |
| Q9 | Where do `feedback_` / `project_` / `reference_` prefixes go? | Drop the prefix when promoting (subdirectory encodes type). User-local: `feedback_X.md`. Promoted: `feedback/X.md`. |
| Q10 | ISO date format for the pointer stub | `YYYY-MM-DD`, no time. |

### v2 — explicitly deferred

| # | Item | Why deferred |
|---|---|---|
| Q11 | `Stop` / `SessionEnd` hook nudging the user when N user-local entries have accumulated since the last promotion | Layer 3 of the analysis. Hooks-noise risk; manual cadence first. |
| Q12 | Plugin packaging via `extraKnownMarketplaces` | Layer 4 of the analysis. YAGNI until second repo. |
| Q13 | Adopt `.claude/agents/*.md` and `.mcp.json` for `tools/conda_forge_server.py` + `tools/gemini_server.py` registration in the same change | Independent of memory work. Inventory turned them up as missing surfaces but they don't unblock anything for v1. Separate spec if desired. |
| Q14 | Cross-repo team-memory sync (e.g., `claude-mem-sync`-style GitHub Action) | Multi-repo concern; this repo is single-source. |
| Q15 | TTL / decay scoring on entries | Premature. Trust humans + git delete. |
| Q16 | Linter / size guard on `MEMORY.md` 200-line limit | Convention-only in v1. Add CI check if it ever fails. |
| Q17 | Two-way sync (changes in `.claude/memory/` flow back to user-local) | Out of scope by design — promoted entry is canonical. User-local pointer stub is read-only after promotion. |

### Genuinely open (design call)

| # | Question | Tradeoff | Default |
|---|---|---|---|
| Q18 | Should the skill also surface entries that exist in `CLAUDE.md` as inline rules but would be cleaner as `.claude/memory/` entries (the inverse promotion)? | Catches the BMAD↔CFE situation that motivated this spec — but expands scope beyond user-local→team. | No in v1. The seed promotion of the BMAD↔CFE rules is a one-time human-run cleanup (Story 9 handles it). If this pattern repeats, revisit. |

---

## Dependencies and Constraints

- **D-1.** Requires Claude Code's `@import` syntax in CLAUDE.md
  (documented; 5-hop max; loads at session start). If Claude Code drops
  this, the team memory still exists but is no longer auto-loaded.
- **D-2.** Skill discovery requires `.claude/skills/` to be readable
  by the running Claude Code instance. Standard.
- **D-3.** Pointer-stub detection depends on the `promoted: true`
  frontmatter convention. If a user manually writes a non-stub entry
  with `promoted: true`, the skill will skip it (acceptable
  false-negative; documented in skill body).
- **D-4.** User-local memory path is hardcoded into the skill as a
  derivation rule (`pwd` + Claude Code's encoding). If Anthropic
  changes the encoding, the skill needs a one-line update.
- **C-1.** `MEMORY.md` 200-line truncation is enforced by Claude Code,
  not us. Discipline-only in v1.
- **C-2.** This is single-author repo today (rxm7706). Multi-author
  conflict resolution is git-merge-only; the skill does not do
  semantic merging. Documented in NG6.
- **C-3.** No CI in this repo enforces team-memory hygiene. Drift is
  caught at the next `/team-memory` invocation when stale-entry
  classification surfaces it.

---

## Out of Scope (Explicit)

- ❌ Stop / SessionEnd / PreCompact hook — deferred to v2 (Q11).
- ❌ Plugin packaging via `extraKnownMarketplaces` — deferred (Q12).
- ❌ `.claude/agents/` adoption — independent surface, separate spec
  (Q13).
- ❌ `.mcp.json` registration of `conda_forge_server.py` /
  `gemini_server.py` — independent surface, separate spec (Q13).
- ❌ Cross-repo team-memory sync — single-repo by design (Q14).
- ❌ TTL / decay / staleness scoring — humans + git (Q15).
- ❌ CI check on MEMORY.md 200-line limit — convention-only in v1
  (Q16).
- ❌ Two-way sync between user-local and team memory — promoted entry
  is canonical (Q17).
- ❌ Inverse promotion: scanning `CLAUDE.md` for inline rules that
  should become `.claude/memory/` entries — Q18, deferred.
- ❌ Replacement of user-local auto-memory — coexists.
- ❌ Auto-commit / auto-push of promoted entries — human commits.
- ❌ Rewriting user-local memory bodies in place (other than the
  pointer-stub conversion) — out of scope.
- ❌ Multi-language support / i18n on rewrite rules — English-only.
- ❌ Analytics, dashboards, metrics — none.

---

## References

- **`docs/specs/conda-forge-tracker.md`** — sibling BMAD spec; shape
  reference for this document.
- **`docs/specs/db-gpt-conda-forge.md`** — sibling BMAD spec; wave-based
  story grouping reference.
- **`CLAUDE.md`** (this repo) — destination of the `@.claude/memory/MEMORY.md`
  import (Story 5) and current home of the BMAD↔CFE rules slated for
  de-duplication (Story 9).
- **`~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/`**
  — user-local auto-memory; source of seed promotions and ongoing
  promotion candidates.
- **`.claude/skills/bmad-distillator/SKILL.md`** — skill that compresses
  source docs; structural reference for how `team-memory`'s skill body
  is shaped.
- **`.claude/skills/bmad-retrospective/SKILL.md`** — skill that writes
  lessons after an epic; structural reference for proposal-then-confirm
  pattern.
- **Anthropic docs:**
  - [How Claude remembers your project](https://code.claude.com/docs/en/memory.md)
    — `@import` syntax, auto-memory schema.
  - [Extend Claude with skills](https://code.claude.com/docs/en/skills.md)
    — skill structure, hot reload, frontmatter.
  - [Explore the .claude directory](https://code.claude.com/docs/en/claude-directory.md)
  - [Hooks reference](https://code.claude.com/docs/en/hooks.md) — for v2
    when the Stop-hook layer lands.
- **Simon Willison background:**
  - [Claude Skills are awesome, maybe a bigger deal than MCP](https://simonwillison.net/2025/Oct/16/claude-skills/)
  - [simonw/claude-skills](https://simonwillison.net/2025/Oct/10/claude-skills/)
  - [Claude Code: Best practices for agentic coding](https://simonwillison.net/2025/Apr/19/claude-code-best-practices/)
  - [Claude Code sub-agents](https://simonwillison.net/2025/Oct/11/sub-agents/)
  - [Superpowers (Jesse Vincent's plugin)](https://simonwillison.net/2025/Oct/10/superpowers/)
- **Open feature request — anthropics/claude-code#38536** — first-class
  team-shared memory in Claude Code (not shipped at spec time).
- **BMAD Method docs** — `.claude/docs/bmad-method-llms-full.txt`
  (offline) / <https://docs.bmad-method.org/llms-full.txt> (live).

---

## Suggested BMAD Invocation

This spec is structured for `bmad-quick-dev`. Either:

```
# Single shot — let bmad-quick-dev plan + implement story-by-story:
run quick-dev — implement docs/specs/claude-team-memory.md
```

or, if full BMAD discipline is preferred (PRD → Architecture → Stories →
Implementation), invoke the planning chain with this spec as the brief
input. For a feature this small (~10 stories, no architecture decisions
beyond markdown + one skill), the quick-dev path is recommended.

**Note:** Story 6 (seed promotion) requires invoking the **just-built**
`team-memory` skill against real user-local entries. Plan that story to
run after Stories 1–5 and 7–8 land — the skill must exist and the
destination directory must exist before the seed promotion can execute.

**Closeout:** per the BMAD↔conda-forge-expert integration rule
(`.claude/memory/feedback/bmad_uses_cfe_skill.md` after Story 6), this
effort does not touch conda-forge work, so the CFE-skill retro from
Rule 2 does not apply. A standard `bmad-retrospective` invocation at
closeout is still warranted to capture lessons about the team-memory
skill itself — file findings as edits to `.claude/skills/team-memory/SKILL.md`
and add a CHANGELOG entry there.
