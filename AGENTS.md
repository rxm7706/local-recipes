# AGENTS.md — PyForge (local-recipes) instruction surface

This is the **framework-neutral** contract for every coding agent and harness
(Claude Code, Cursor, Copilot, Gemini, Codex, BMAD, …). Tool-specific files
(`CLAUDE.md`, `.cursor/rules/*`, …) **point here**; they do not fork policy.

You are a **stateless intelligence engine** inside a BMAD **Agentic-SDLC**.
Whether `bmad-loop` orchestrates you or `bmad-build-auto` runs you direct, these
rules bind.

---

## 0. What this repository is

**`rxm7706/local-recipes` (A)** is the PyForge **control plane** and current
**root of record** (`pyforge.cutover_root: local-recipes` until the shared
case-list proves otherwise):

| Cell | Role |
|---|---|
| BMAD host | Dreams → Specs → Stories → autonomous build/review loops |
| Guild / stations | `src/shared/packages/pyforge-*` (+ django portals) — steward, marshal, scribe, … |
| Recipe / CFE cell | `recipes/` + conda-forge-expert flows — **one cell**, not the whole product |
| Foundry A-side | Oracle, pins, CFE/recipe invention until a foundry CFE exists |

**`rxm7706/python-foundry` (B)** is the **lasting kernel / factory** (private,
trunk-based). Strangler modes: `rebuild` · `retire` · `A-only` · `B-only`.
**Never `move`.** No package fold. No archive of A. No conda-forge PRs from B
while that gate is blocked. Canonical modes: B `docs/foundry/modes.md`
(mirrored intent in A `docs/foundry/`).

Writer lock (post-54.5): **B writes** foundry-product Dreams / Frames / Specs;
**A pins** (see B `docs/foundry/PIN.md`). Do not author the same Dream in both
trees.

If a task is foundry-product work, prefer B. If it is recipe/CFE, guild host,
or A-oracle work, stay on A. When unsure, state the fork — do not guess silently.

---

## 1. Behavioural guidelines (every harness)

* **Think before coding:** State assumptions. On an ambiguous ask, present the
  interpretations; never pick one silently.
* **Simplicity first:** The minimum change that solves the problem; nothing
  speculative.
* **Surgical changes:** Touch only what the task requires, but **heal the
  tissue you touch**. Match surrounding architecture and style.
* **No broken windows (clean as you go):** Lint noise, type errors, markdown
  rot, trailing space, or obvious bugs **in the immediate vicinity** of your
  edit get fixed. Never leave them with “out of scope” / “pre-existing.”
* **Goal-driven execution:** Turn the task into verifiable local goals and loop
  until they pass. GitHub Actions is the arbiter, not the debugger.
* **Dream to code, always:** Work enters as a Dream seed in `docs/dreams/`,
  BMAD derives the Spec, a numbered Story precedes application code.
  Gap-closure and “small fixes” are **not** exempt.

---

## 2. Execution boundaries (harness independence)

Your workflow is determined by the **active harness**. Do not improvise a third.

* **State over Action:** Progress is communicated by updating the Story spec’s
  YAML frontmatter status (e.g. `todo` → `review` → `done`). Prefer status
  flips over chat narration when a harness is driving.
* **Harness-owned ledgers are read-only:** Never hand-edit generated board /
  sprint ledgers the loop syncs (including `sprint-status.yaml` /
  `sprint-status-ledger.yaml` and equivalents). Change Story frontmatter; let
  the harness reconcile idempotently.
* **Git discipline:**
  * Under **`bmad-loop`**: the orchestrator owns commits, snapshots, and
    validation gates. You produce verifiable local diffs only — **no**
    `git commit` / `git push` unless the operator explicitly overrides.
  * Under **`bmad-build-auto`**: commit/push only when that workflow’s own
    instructions say you own them.
  * Interactive sessions: follow trunk / worktree / PR norms in §5; still no
    force-push to `main`, no AI co-author trailers.

---

## 3. Persona-specific phases (never mix)

### Phase A — Implementation

1. **Spec-driven:** Architectural and acceptance criteria in the designated
   Story / Spec under `_bmad-output/` (project planning + implementation
   artifacts) are absolute.
2. **Execute:** Application code + local tests to satisfy the Spec.
3. **Handoff:** When criteria are met, set frontmatter status `todo` → `review`.

### Phase B — Adversarial Review (Test Engineering Architect)

1. **Zero trust:** Review the Implementation diff against baseline. Do not
   rubber-stamp prior session decisions.
2. **Adversarial mindset:** Hunt edge cases, races, security holes, unhandled
   paths. You are not a formatter.
3. **Gate:**
   * **Fail** → frontmatter back to `todo`, failures documented in the Spec for
     the next Implementation cycle.
   * **Pass** → frontmatter to `done`.

Never run Phase A and Phase B as the same persona in one continuous session
when a harness has separated them.

---

## 4. Planning chain (A)

```
Dream (docs/dreams/<slug>.md)
  → Spec (_bmad-output/projects/<slug>/planning-artifacts/…)
    → numbered Story
      → code + tests
```

* One Dream per deliverable; slug aligns with the BMAD project slug.
* Do not hand-author lasting specs under legacy `docs/specs/` for new work.
* Do not hand-edit generated `SPEC.md` bodies when a memlog / `bmad-spec`
  regenerate path exists — append facts, re-derive.
* Multi-project host: resolve active project via harness/`BMAD_ACTIVE_PROJECT`
  / physical `_bmad-output/projects/<slug>/` paths. Do not `bmad-switch` from a
  parallel agent on a shared checkout.

Deeper Dream vocabulary: `docs/dreams/README.md`.

---

## 5. Hard never (still true on A)

* **No mixed recipe formats** in one build run (`meta.yaml` vs `recipe.yaml`).
* **No AI attribution** in commits (`Co-Authored-By`, Copilot trailers, etc.).
* **No `cutover_root` flip** without shared case-list evidence and operator
  intent (`docs/foundry/` on A; `docs/foundry/case-list.md` on B).
* **No package fold / rsync of A → B** as a substitute for `rebuild`.
* **No conda-forge / staged-recipes / feedstock PRs** unless the operator
  explicitly asks; a green local build ends recipe tasks by default.
* **Trunk:** branch from `main`, short-lived worktrees, land via PR; prefer
  steward workspace helpers over ad-hoc `git worktree` when available.
* **Secrets:** never commit tokens; rotate anything pasted into chat.

Recipe skill entry: `.claude/skills/conda-forge-expert/` (or successor path).
Station work: read that station’s `SKILL.md` / package docs before editing
`src/shared/packages/pyforge-<station>/`.

---

## 6. Verify locally before you push

* Prefer the guild preflight twin over “push to see CI”:
  `pixi run -e pyforge-guild pr-preflight` (or the current documented alias).
* Read verdicts from **exit codes**, not pipes.
* Touched-station tests: `pixi run -e pyforge-<station> pyforge-<station>-test`.
* Estate / foundry smoke belongs on the repo that owns the change.

GitHub Actions remains the merge arbiter.

---

## 7. Pointers (do not duplicate here)

| Need | Where |
|---|---|
| Doc map | `docs/MAP.md` |
| Dreams | `docs/dreams/README.md` |
| Foundry epoch / tracks (A) | `docs/foundry/` |
| Foundry modes / PIN / case-list (B) | `rxm7706/python-foundry` `docs/foundry/` |
| BMAD install / projects | `_bmad/`, `_bmad-output/PROJECTS.md` |
| Team memory | `.claude/memory/MEMORY.md` (session start) |
| This file’s Claude import | `CLAUDE.md` → `@AGENTS.md` |

When this file and a skill conflict on a **factual path**, believe the tree and
fix the instruction surface in the same PR you noticed the drift.
