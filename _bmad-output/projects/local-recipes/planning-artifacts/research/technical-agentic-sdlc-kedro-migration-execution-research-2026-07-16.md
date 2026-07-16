---
stepsCompleted: [1]
inputDocuments:
  - 'docs/specs/cfe-atlas-datapipeline-kedro-migration.md (v5.2)'
  - 'docs/specs/bmad-loop-adoption.md'
  - '_bmad-output/projects/local-recipes/planning-artifacts/research/domain-cf-atlas-domain-triad-research-2026-07-16.md'
  - '.claude/docs/bmad-method-llms-full.txt (local mirror of https://docs.bmad-method.org/llms-full.txt — user-designated primary BMAD reference)'
  - 'docs/library-llms-full.md (vetted single-env package catalog — the in-stack constraint)'
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'Executing the cfe-atlas-datapipeline Kedro migration (v5.2) as an autonomous agentic SDLC — bmad-method 6.10 + bmad-loop + bmad-dev-auto + bmad-ui/dashboards used to the fullest, within the repo tech stack and operating conventions'
research_goals: 'Resolve the tension between the migration spec ambitious tech stack (Kedro/Dagster/DuckDB/Ibis-BSL/Vizro, waves 0+A-H, 21 FRs) and maximal use of the adopted autonomous execution machinery (bmad-method 6.10 core+bmm, bmad-loop v0.8.1, bmad-dev-auto, TEA, bmad-ui dashboards): determine what an autonomous agentic SDLC for THIS effort concretely looks like — which waves/stories are loop-drivable vs attended, what verify-gates the loop needs (tests, drift-check, llms-full-check, parity checks), how the dashboards observe the run, where the CFE Rules 1&2 hooks fire — while staying inside pixi-first / py3.14 / worktree-isolation / spec-first conventions. Deliver an execution-architecture recommendation ready to encode in the spec § 2.5/§ 14 and the Tier-2 planning intake.'
user_name: 'Rxm7706'
date: '2026-07-16'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-07-16
**Author:** Rxm7706
**Research Type:** technical

---

## Research Overview

[Research overview and methodology will be appended here]

---

<!-- Content will be appended sequentially through research workflow steps -->

## Technical Research Scope Confirmation

**Research Topic:** Executing the cfe-atlas-datapipeline Kedro migration (v5.2) as an autonomous agentic SDLC — bmad-method 6.10 + bmad-loop + bmad-dev-auto + bmad-ui/dashboards used to the fullest, within the repo tech stack and operating conventions.

**Scope:**
- **Architecture Analysis** — how the deterministic dev-loop (DEV→VERIFY→REVIEW→VERIFY→COMMIT, tmux + worktrees) composes with a data-pipeline effort (long builds, dataset parity, credentialed phases); bmad-dev-auto vs full loop vs attended; state of the art in agentic-SDLC harnesses.
- **Implementation Approaches** — wave-by-wave drivability map for 0 + A–H (~30 stories): loop-drivable vs gated vs attended; per-story verify commands.
- **Technology Stack** — in-stack verify-gate inventory (pixi test tasks, bmad-drift-check, llms-full-check, meta-tests, future kedro/parity tasks); bmad-ui / mybmad-dashboard / BMad-dashboard observation capabilities; genuine gaps.
- **Integration Patterns** — Rules 1 & 2 inside loop sessions; escalation (bmad-loop-resolve, deferred-work ledger/sweep); dashboard↔loop↔git observability; kedro-viz/Dagster UI complementing BMAD dashboards.
- **Performance Considerations** — session timeouts (180 min) vs pipeline build times; worktree/disk economics; parallel-story limits; where in-loop verification is impossible (fixture-based verify instead).

**Method:** internal grounding (bmad-method llms-full local mirror + live, bmad-loop-adoption spec, pixi.toml tasks, loop config, library catalog) + web verification (bmad-loop repo/docs, agentic-SDLC practice); confidence flags throughout; deliverable shaped for spec § 2.5/§ 14 and Tier-2 intake.

**Scope Confirmed:** 2026-07-16

## Technology Stack Analysis — the Execution Machinery

*Verified 2026-07-16 against live sources (official docs, bmad-code-org repos, marketplace pages) + the repo's own configs. The "stack" here is the autonomous-SDLC machinery that will execute the migration.*

### Layer map

| Layer | Component | Verified state |
|---|---|---|
| Orchestration | `bmad-loop` v0.8.1 (bmad-code-org, official; 2026-07-06) | Deterministic Python loop, "No LLM in the control loop"; tmux sessions; **`max_parallel = 1` — validation clamps to 1, fan-out unbuilt** |
| Worker | `bmad-dev-auto` (BMM 6.10) | Single-iteration unattended worker (clarify → spec → implement → review → terminal status); **no approval checkpoints**; halts `blocked` on unsafe conditions |
| Method / skills | BMM 6.10 lifecycle + TEA module (9 workflows) | create-story → dev-story → code-review (+ retrospective per epic); TEA `atdd` (red-phase acceptance tests **before** dev) + `test-review` (0–100 scored) |
| Observation | bmad-loop TUI · `bmad-dashboard` (VS Code) · MyBMAD (Next.js web) | TUI = the only loop-session observer; both dashboards visualize **BMAD artifacts** (sprint/story/epic states), not loop sessions |
| Verify gates | repo pixi tasks + `.bmad-loop/policy.toml` `[verify]` | Today: one command (pyforge-warden pytest, `--frozen`); rich unused inventory (below) |
| Constraint envelope | pixi-first, py3.14, tmux (linux-64/osx-arm64), worktrees | Loop-driven runs Linux/macOS only; attended flows OS-agnostic |

### Orchestration layer — bmad-loop v0.8.1 (verified against the official README)

DEV (fresh tmux window) → VERIFY (repo commands) → REVIEW (independent fresh-context session) → VERIFY → COMMIT (orchestrator squashes). Gates: `none | per-epic (upstream default) | per-story-spec-approval` — **this repo runs the strictest mode** with `retrospective = notify`. SCM: worktree isolation, `branch_per = story` on `bmad_loop/<run_id>/<story>` branches, squash merge (repo choice; upstream default is `merge`), `keep_failed = true`, leaked-worktree reconciliation. Limits (repo policy vs upstream defaults): session 180 min (up from 90 after pilot learning #1 — a keystone story burned 25.8M unreusable tokens at the 90-min cap), `max_dev_attempts = 2`, `max_review_cycles = 3`, 2M cost-weighted tokens/story (cache reads 0.1×). Escalation: CRITICAL → run pauses → `bmad-loop resolve` (interactive, `resolution.json`, re-arm + resume); PREFERENCE → journaled, run continues; intent-gap → patch preserved (`--restore-patch`). Deferred-work: `DW-<n>` ledger + sweep (`auto = never` here; bundles ≤5). Adapters: claude (reference; repo pins model=opus after a Fable-5 usage-cap stall), codex, gemini, copilot, antigravity; per-stage overrides. **Hard limits verified: `max_parallel` clamped to 1 (no story fan-out in v0.8.1); tmux-only backend (Windows = WSL); no PR lifecycle (stops at local merge)** — the PR gap and resume-on-timeout are already-filed follow-on/watch items. _Sources: https://github.com/bmad-code-org/bmad-loop (README); .bmad-loop/policy.toml; docs/specs/bmad-loop-adoption.md_

### Worker layer — bmad-dev-auto (verified against the official reference page)

*"One unattended development-loop iteration"*: clarify intent → create/resume spec → implement → review → **write terminal status to the spec frontmatter** (`draft / ready-for-dev / in-progress / in-review / done / blocked`). Halts `blocked` on: unclear intent, intent gap, **no subagents**, missing spec before implementation, implementation verification failed, review repair loop > 5. Orchestrator contract: one coherent intent per dispatch; read `status` + `blocking condition` + `followup_review_recommended` from frontmatter, *never* infer success from chat output. Shares the Quick-Dev spec format line-for-line — the difference is the removal of approval checkpoints. v6.10.0 also formally deprecated `bmad-automator` in favor of bmad-loop. **Verification caveat on the user-designated reference: `docs.bmad-method.org/llms-full.txt` contains none of the dev-auto/TEA autonomy material (keyword-probed live 2026-07-16) — the authoritative sources are the `/reference/dev-auto/` page and the TEA doc site; docs lag source, as the adoption spec also found on 2026-07-12.** _Sources: https://docs.bmad-method.org/reference/dev-auto/ ; https://www.bmadcode.com/bmad-method-has-three-flows-now-heres-what-actually-changes-between-them/ ; https://docs.bmad-method.org/llms-full.txt_

### Method layer — BMM 6.10 + TEA

Documented per-story cycle in fresh chats (create-story → dev-story → code-review "recommended"), retrospective per epic. TEA ("Murat, Master Test Architect") adds nine workflows; the two the loop pipeline names: **`atdd`** — red-phase acceptance-test scaffolds + implementation checklist generated *before* dev; **`test-review`** — scored (0–100) test-quality report. Official lifecycle guidance: `test-design` per epic, `atdd` before dev "when helpful", `automate` after, `test-review` per story/sprint-end. Official autonomy framing: *"human-on-the-loop, supervising several cycles at once… the quality bar stays where it was; only the vantage point moves."* _Sources: https://bmad-code-org.github.io/bmad-method-test-architecture-enterprise/explanation/tea-overview/ ; https://docs.bmad-method.org/tutorials/getting-started/_

### Observation layer — dashboards (verified)

- **bmad-loop TUI** (`bmad-loop tui`): runs table, sprint tree, DW ledger, per-story phase/attempts/cycles/**tokens**, journal + pane-log + ATTENTION tabs, policy editor, attach-to-session. **The only surface that observes loop sessions.**
- **`bmad-dashboard`** (VS Code, in the `bmad-ui` env via W4's mirrored recipes): real-time sidebar over `_bmad/` (500 ms debounce) — sprint progress, epic/story cards, state-machine next-action buttons (Play/Copy). Artifact-level, not loop-level.
- **MyBMAD** (`mybmad-dashboard`, Next.js 16 + PostgreSQL + Better Auth): read-only web visualization of epics/stories/sprint velocity from GitHub repos or local folders; multi-user. Artifact-level, not loop-level. (The org repo `bmad-code-org/bmad-method-ui` hosts both surfaces; feature-identical to the marketplace extension — likely an org adoption of the community extension, MEDIUM.)
- **Gap confirmed**: nothing displays loop sessions except the TUI; and kedro-viz + the Dagster UI (the migration's own § 5.4 observability) are a *third*, pipeline-level plane. Three observation planes, no unified view. _Sources: https://marketplace.visualstudio.com/items?itemName=elvince.bmad-dashboard ; https://github.com/bmad-code-org/bmad-method-ui_

### Verify-gate inventory (in-stack, callable by `[verify] commands` today)

From `pixi.toml` (all `-e local-recipes` unless noted): `test` / `test-all` / `test-coverage` (pytest suites; 85 unit + 4 integration + 8 meta), `test-skill`, `bmad-drift-check` (BMAD-artifact integrity), `llms-full-check` (library-catalog drift), `verify-env`, `health-check`, `lint-optimize`, `check-deps`, `build-local-check`, `version-check`, `license-check`, `test-recipes`, `wiki-lint[-all]`; plus ruff/pyright/mypy/pyrefly and pytest-xdist for parallel test execution (§ 14 of the library catalog). **Gap for the migration: no kedro-pipeline test task, no dataset-parity task, no fixture-diff task exists yet — Wave A/B stories must create them before the loop can verify those stories.** The pyforge-warden precedent (`--frozen` after the pixi-build worktree path-length panic) sets the pattern: every loop verify command should run `--frozen`. _Sources: pixi.toml ; .bmad-loop/policy.toml ; docs/library-llms-full.md § 14_

### Practice patterns (external verification)

- **Layered verification with a deterministic hard-stop**: official Claude Code guidance — in-prompt check → per-turn evaluator → **Stop-hook deterministic gate** ("what let an unattended run finish correctly without you") → fresh-context verification subagent. bmad-loop's VERIFY phase is exactly the deterministic tier. _Source: https://code.claude.com/docs/en/best-practices_
- **Fixture-diff verification for slow pipelines is an officially named pattern** ("a script that diffs output against a fixture") — the answer to "the 3–4 h rebuild can't run in-loop": snapshot expected outputs once, diff in-loop. The Ralph technique (bmad-loop's ancestor) adds: scope in-loop tests to the changed unit, mandatory static analyzers, and the sober ceiling — *"no way this is possible without senior expertise guiding Ralph"*, ~90% completion realistic. _Sources: https://code.claude.com/docs/en/best-practices ; https://ghuntley.com/ralph/_
- **Humans at batch boundaries** is the convergent placement (per-epic gates, CRITICAL-only pauses, "supervising several cycles at once"); and a warning to carry: **adversarial reviewers in long unattended runs always find something — constrain them to correctness-affecting gaps** or the loop over-engineers. _Sources: https://www.bmadcode.com/bmad-method-has-three-flows-now-heres-what-actually-changes-between-them/ ; https://code.claude.com/docs/en/best-practices_

### Cross-technology analysis & quality assessment

The machinery is real, official, and already configured stricter-than-default in this repo — but three verified constraints shape everything downstream: **(1) sequential stories** (`max_parallel = 1`): "parallel waves" is not a v0.8.1 capability — parallelism must come from *multiple runs* (risky, unsupported) or patience; **(2) the verify layer is the bottleneck asset**: the loop is only as good as its deterministic gates, and the migration's gates (kedro tests, parity fixtures) don't exist yet — they are themselves early-wave deliverables; **(3) three unjoined observation planes** (TUI / BMAD dashboards / kedro-viz+Dagster). Confidence: HIGH on all repo-config and official-doc facts; MEDIUM on dashboard version numbers and the org-adoption inference; the practice patterns are official-doc-sourced (HIGH) with vendor-blog corroboration.
