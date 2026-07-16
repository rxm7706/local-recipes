---
stepsCompleted: [1, 2, 3, 4, 5, 6]
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

Technical research (2026-07-16) resolving the tension between the cf_atlas Kedro migration's ambitious tech stack (spec v5.2: Kedro/Dagster/DuckDB/Ibis-BSL/Vizro, waves 0 + A–H, 21 FRs) and maximal use of the repo's adopted autonomous execution machinery (bmad-method 6.10, bmad-loop v0.8.1, bmad-dev-auto, TEA, the bmad-ui dashboards) — within pixi-first / py3.14 / worktree / spec-first conventions and CLAUDE.md Rules 1–2.

**Conclusion**: the two ambitions compose via **graduated autonomy with verify-first sequencing** — Waves 0/A attended/dev-auto build the deterministic gates, Wave B runs loop-driven under per-story-spec-approval with TEA-generated fixture gates, autonomy relaxes to per-epic through C–E, F–H run mixed. ~19 of 30 stories are loop-drivable; all 4 attended events are schedulable batch boundaries. Verified capability corrections along the way: bmad-loop is sequential-only (`max_parallel = 1`), the dashboards observe artifacts not loop sessions, kedro-mcp is guidance-scoped, and `llms-full.txt` lacks the autonomy docs. Two new risks surfaced and mitigated: the worktree × multi-project-symlink seam (Wave-0 bootstrap + A3 smoke) and worktree pixi-env materialization cost (lean env from A1).

Method: internal grounding (loop policy/hooks, adoption-spec pilot learnings, pixi task inventory) + live external verification (official bmad-code-org sources, dev-auto reference, TEA docs, agentic-SDLC practice). Full detail: the drivability map (step 5), the architecture options (step 4), and the synthesis + hand-off at the end of this document.

**Erratum 2 (2026-07-16, adversarial review)**: this document's story arithmetic is off — § 9 of the spec contains **32** stories, not 30, and the drivability map's own rows sum to ~21 loop-drivable (11 LOOP-S + ~10 LOOP-E), not "19 (10+9)"; the spec (v5.4) carries the corrected numbers.

**Erratum (2026-07-16, post-publication)**: where this document echoes the domain research's "GX blocked on py3.14" finding, apply the spec's v5.2 correction — conda-forge `great-expectations 1.18.2` (already in `pixi.toml`) imports cleanly on py3.14.6 (live-verified); GX is Committed but version-capped at 1.18.2, pandera remains the primary inline layer, and the validator-agnostic F2 hook stands unchanged.

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

## Integration Patterns Analysis

*How the loop integrates with the repo's conventions, the CFE method rules, and the migration's own surfaces. Grounded in `.bmad-loop/bmad_loop_hook.py`, `.claude/settings.json`, `.bmad-loop/policy.toml`, the adoption spec, and the verified upstream facts above.*

### Session & event integration (the loop's nervous system)

bmad-loop drives coding-CLI sessions through a **file-based event bus**: each CLI's hook config registers `.bmad-loop/bmad_loop_hook.py` under native event names (Claude: `SessionStart`/`Stop`/`SessionEnd`/`PreCompact` — registered in `.claude/settings.json`), the relay normalizes to canonical events and writes one JSON file per event into the run directory (`$BMAD_LOOP_RUN_DIR/events/`). **Env-var-gated**: sessions not spawned by the loop no-op, so interactive work is unaffected. Operator signals: desktop notify + an ATTENTION file in the run dir. Integration consequences: (a) the **one-time human hooks-approval** (adoption spec) is a hard precondition for any run; (b) the `Stop` event is the loop's only completion signal — the `dev_stall_grace_s`/`stop_without_result_nudges` machinery exists because a dev session that ends its turn awaiting a background process (exactly what long kedro test runs will do) looks stalled otherwise. _Sources: .bmad-loop/bmad_loop_hook.py ; .claude/settings.json ; .bmad-loop/policy.toml_

### Method-rule integration (CLAUDE.md Rules 1 & 2 inside the loop)

- **Rule 1** (CFE skill for any atlas/recipe work): dev-auto is **spec-driven** — the enforcement point is the *story spec text* (each migration story spec must carry the standing instruction to invoke `conda-forge-expert` for atlas-tooling work, as § 14 already directs for Linker subagents). dev-auto *requires subagent capability* (halts `blocked: no subagents`), so skill/subagent invocation inside loop sessions is architecturally assumed, not exceptional. Enforcement backstop: the REVIEW session's checklist can verify Rule-1 compliance per story.
- **Rule 2** (CFE retro at closeout): the loop's `retrospective = notify` mode surfaces the retro obligation but cannot discharge it (`auto` unsupported in v1) — the retro is an **attended** closeout step. The migration touches atlas tooling throughout, so Rule 2 is engaged from Wave 0; the loop's role is to notify, the human runs `bmad-retrospective` + the CFE CHANGELOG entry.
- **TEA integration**: `atdd` before dev (red-phase acceptance tests) is the natural generator of the per-story verify assets the loop needs — for pipeline stories, ATDD output should *be* the fixture-diff scripts, making TEA the bridge between "spec-approval gate" and "deterministic verify gate." _Sources: docs/specs/bmad-loop-adoption.md ; https://docs.bmad-method.org/reference/dev-auto/ ; TEA docs (cited above) ; CLAUDE.md Rules 1–2_

### Escalation & deferred-work integration

CRITICAL escalation pauses the run and parks the story until an **attended** `bmad-loop-resolve` session (seeded with the escalation + frozen spec → `resolution.json` → re-arm → resume); PREFERENCE journals and continues; intent-gap preserves the attempted change as a patch. Migration-specific escalation sources are predictable: **open-question resolution mid-story** (Q1 parity tolerance inside B4; Q6 inside B5; Q7 inside B8) — the spec's "resolve QN first" sequencing exists precisely to drain these before the loop reaches them; **parity mismatches** (B4) that are data-drift rather than code-bugs — a class the resolve flow (human judges benign-vs-real) fits well. The DW ledger absorbs the long tail (deferred pins, watch items) with `bmad-loop-sweep` triage at chosen boundaries (`auto = never` — sweeps are operator-invoked here). _Sources: .bmad-loop/policy.toml ; .claude/skills/bmad-loop-resolve ; docs/specs/cfe-atlas-datapipeline-kedro-migration.md § 14_

### SCM & PR-lifecycle integration (the known seam)

The loop's SCM scope ends at **local squash-merge** of per-story branches (`bmad_loop/<run_id>/<story>`) back to the checkout branch; it creates no PRs and watches no CI. This repo's delivery convention (feature branch → PR → review, as this very session demonstrates on PR #64) therefore wraps the loop: an attended (or scheduled) push at wave/epic boundaries, with the already-recorded follow-on option — a thin `gh pr create` + `gh pr checks` wrapper at the `[gates] per-epic` boundary (the bmad-autopilot survey's "one delta worth keeping"). Practical wave pattern: loop runs stories on a local integration branch per wave → human reviews the squashed story commits → push → PR per wave. _Sources: docs/specs/bmad-loop-adoption.md (autopilot survey) ; https://github.com/bmad-code-org/bmad-loop_

### Secrets & credentialed-phase integration

Loop sessions inherit the tmux environment — GitHub tokens (Phases E.5/K/N) and BigQuery ADC (Phase P) would be ambient in unattended sessions. Postures this research recommends: **(a)** loop verify commands never touch credentialed live endpoints — fixture-based verification only (this also keeps gates deterministic); **(b)** Phase P stays out of every loop path (spec already mandates admin-only opt-in); **(c)** live credentialed smoke runs are attended, wave-boundary events (B4 parity, C1 schedule bring-up); **(d)** the adapter's permission-bypass flags (`--permission-mode bypassPermissions` class) make the FR-1 per-host credential-scoping fix *more* important, not less — an unattended session with ambient JFrog keys is exactly the § 3.3 leak scenario. _Sources: .bmad-loop/policy.toml [adapter] ; docs/specs/cfe-atlas-datapipeline-kedro-migration.md § 3.3/FR-1_

### Observability integration (joining the three planes)

The pragmatic join is **the artifact tree as the shared bus**: the loop and dev-auto write story/spec state into `_bmad-output` (sprint-status.yaml, spec frontmatter) — which is exactly what `bmad-dashboard` (500 ms file-watch) and MyBMAD render. So story-level progress IS dashboard-visible during loop runs, without any new wiring; what stays TUI-only is session-level detail (phases, attempts, tokens, panes); what stays pipeline-level is kedro-viz/Dagster (from Wave C). Recommended posture: TUI for the operator driving the run; `bmad-dashboard` (bmad-ui env, W4) for story/sprint state; defer any unified view — a MyBMAD-reads-run-journal integration is an upstream feature request, not this effort's scope. _Sources: verified dashboard capabilities (step 2) ; docs/specs/bmad-loop-adoption.md W4_

### ⚠️ The worktree × multi-project seam (new risk, surfaced by this research)

The multi-project layout routes all planning/implementation writes through **gitignored repo-root symlinks** (`_bmad-output/{planning,implementation}-artifacts` → `projects/local-recipes/...`), and `implementation-artifacts/` itself is gitignored. The loop now runs `isolation = "worktree"` — and **a fresh git worktree contains neither the gitignored symlinks nor the gitignored implementation-artifacts directory**. The pyforge-warden pilot learnings predate the worktree switch (in-place mode), so this seam is **untested**: a dev-auto session in a worktree that writes its spec via the standard `{implementation_artifacts}` path would either fail or write to a literal new directory that the squash-merge ignores (gitignored) — silently stranding spec/status artifacts the orchestrator's contract depends on. **Mitigation to validate before Wave 0**: a worktree-bootstrap step (loop hook, `[scm]` hook, or story-spec preamble) that recreates the symlinks + target dirs inside each worktree (the same fix `scripts/bmad-switch` applies at repo root), plus one smoke story to prove spec round-trip from a worktree. Confidence: the layout facts are HIGH (repo-verified); the failure mode is MEDIUM (reasoned, not yet reproduced) — which is precisely why it needs the smoke test. _Sources: CLAUDE.md multi-project pattern ; .bmad-loop/policy.toml [scm] ; docs/specs/bmad-loop-adoption.md W2/pilot learnings_

## Architectural Patterns and Design

### System Architecture Patterns — three candidate execution architectures

**Option A — Loop maximalism** (bmad-loop drives every story, `gates = none`/`per-epic` from day one). *Rejected.* Fails on verified facts: the deterministic verify gates the loop depends on don't exist until Waves A/B build them; keystone stories exceed session budgets unpredictably (pilot: 25.8M tokens burned at a 90-min cap); Q-gated stories (B4/B5/B8) and credentialed smokes structurally require humans; and `max_parallel = 1` removes the throughput argument that would justify the risk.

**Option B — Graduated autonomy (RECOMMENDED)** — the same "Option B" posture the repo already selected for the pyforge-warden pilot, extended wave-wise:

| Phase | Mode | Rationale |
|---|---|---|
| Wave 0 + A1–A3 | **Attended / dev-auto-inline** (no orchestrator) | These stories *build the harness the loop needs* (scaffold, catalog, TTL dataset class, verify tasks); fastest iteration is interactive; establishes the kedro verify commands |
| Wave B (B1–B10) | **Loop, `per-story-spec-approval`** | Heavy, novel, contract-laden ports; spec-approval drains ambiguity pre-implementation; TEA `atdd` generates the fixture gates per story; B4 parity is an attended wave-boundary event |
| Waves C–E | **Loop, relax toward `per-epic`** | Post-parity, gates are proven and the surface is additive (orchestration, BSL, dashboards, A2A); per-epic human review at PR boundaries |
| Waves F–H | **Mixed** | F1 (engine swap) + G1/G2 (WASM) loop-drivable against fixtures; F4 gate + H factory stories carry cross-system integration better handled dev-auto-inline with attended checkpoints |

**Option C — dev-auto-inline only** (no orchestrator ever). *Kept as the fallback + the Windows path.* Loses determinism, journaling, token accounting, and unattended throughput; wins on zero harness risk and OS-independence. It is the correct mode for Wave 0/A regardless (per the table) — so Option B *contains* Option C where it's strongest.

### Design Principles and Best Practices

1. **Verify-first sequencing** — every wave's first deliverable is its own deterministic gate (Wave A: `kedro-test` + catalog smoke; Wave B: per-pipeline fixture-diffs + parity harness; Wave C: schedule dry-run checks). The loop never enters a wave whose gate doesn't exist. This inverts the usual "tests follow features" instinct and is the single highest-leverage decision in this architecture.
2. **Fixture-diff over live-run** (officially-blessed pattern): the 3–4 h rebuild, credentialed APIs, and network flakiness all stay out of gates; snapshot fixtures live in the *tracked* test tree (`tests/data/`), never in the gitignored `.claude/data/` runtime dir (which fresh worktrees don't have — see Data Architecture).
3. **Frozen-lock everywhere in loop paths** (`pixi run --frozen ...`) — the pyforge precedent (worktree re-solve panics + lock rewrites) applies verbatim.
4. **Budgets sized to the heaviest story per wave, pre-flight** (pilot learning #1): B1/B2 are this effort's keystones — assume ≥180 min / high token budgets from the start; consider per-stage `[adapter.dev]` overrides.
5. **Humans at batch boundaries, reviewers on a leash**: spec-approval + wave-boundary events are the human surface; REVIEW sessions constrained to correctness-affecting findings (the verified over-engineering failure mode of long unattended runs).
6. **Specs as the only channel**: dev-auto's frontmatter-status contract means all orchestration state lives in artifacts — which is also what makes the dashboards work for free.

### Scalability and Performance Patterns

- **Throughput model**: sequential stories (`max_parallel = 1`) × ~30 stories × (dev + review + verify cycles) — wave-level wall-clock is dominated by verify time and session budgets, not agent speed. Practical lever: keep gates fast (fixture-diffs in seconds/minutes; full `test-all` at wave boundaries only — the Ralph "scope tests to the changed unit" rule).
- **Worktree economics (new finding)**: `.pixi/` envs are gitignored → **each fresh worktree needs its own pixi env materialization** before any `pixi run --frozen` verify (multi-GB local-recipes env; solve skipped with `--frozen` but download/link time is real, cache hardlinks help). Mitigations to evaluate in the Wave-0 smoke: shared pixi cache (default behavior — links from cache), `detached-environments` config, or a leaner dedicated `cf-atlas-kedro` env for the pipeline package so loop verifies don't materialize the fat env. The nebi-scaffolded project (Story A1) choosing its own lean env is the clean answer.
- **Token economics**: 2M cost-weighted tokens/story budget vs the pilot's 25.8M burn on one killed attempt — the budget exists to stop runaway stories, but keystone stories need explicit budget raises, not silent failures.

### Security Architecture Patterns

As established in Integration (§ above): fixture-only gates; Phase P never loop-reachable; credentialed smokes attended; permission-bypass mode in unattended sessions raises the priority of FR-1 per-host credential scoping; worktrees + `keep_failed = true` mean failed-attempt branches can accumulate — periodic reconciliation (the loop does this at run/sweep start) plus no secrets ever written into worktree files.

### Data Architecture Patterns

Three data domains with different loop-visibility: **(1) artifacts** (`_bmad-output` tree) — the loop's own state, tracked (Tier 2) or symlinked (Tier 3, the worktree seam); **(2) test fixtures** — tracked, in-repo, the *only* data gates may touch; **(3) runtime data** (`.claude/data/`: cf_atlas.db, vdb, caches — gitignored, absent from worktrees) — never a gate dependency; stories that need realistic data get *sampled fixtures* generated attended, once, from the operator's runtime data (e.g., a 500-package cf_atlas.db slice for parity-harness development). This three-way split should be stated in the Tier-2 architecture doc.

### Deployment and Operations Architecture

Operator posture per run: launch via `bmad-loop run` (TUI attached or `tui` separately), desktop-notify + ATTENTION file as the interrupt channel, `bmad-dashboard` (bmad-ui env) for story/sprint state, journals in the run dir as the audit trail. Cadence recommendation: **supervised runs first** (operator present for Wave B's early stories), overnight unattended only after two clean supervised stories in a row; sweeps operator-invoked at wave ends (`auto = never` stays). One-time preconditions checklist: hooks approval, `bmad-switch local-recipes` (symlinks live), worktree-bootstrap smoke, heaviest-story budget review. _Sources for this section: all step-2/3 citations; pilot learnings (adoption spec); Ralph/Claude-Code best-practice docs (cited above)_

## Implementation Approaches and Technology Adoption

### The wave-by-wave drivability map (all stories, spec v5.2)

*Mode legend: **LOOP-S** = bmad-loop, per-story-spec-approval · **LOOP-E** = bmad-loop, per-epic · **AUTO** = dev-auto invoked inline (attended session, unattended skill) · **ATT** = attended · ⚿ = Q-gate or credentialed event.*

| Story | Mode | Deterministic gate (verify command class) |
|---|---|---|
| 0.1 SKF legacy skill | AUTO | skill artifact exists + query smoke |
| A1 nebi scaffold | AUTO | `verify-env` + `llms-full-check` + new `kedro-test` smoke |
| A2 data catalog | AUTO | new `kedro-catalog-check` (catalog resolves, no inline IO) |
| A3 IncrementalParquetDataset | **LOOP-S** (first loop story — doubles as the worktree smoke) | new unit tests (TTL round-trip) |
| B1 backbone ports | LOOP-S (≥180 min budget) | node tests + per-phase engineering-contract fixtures (K token-bucket, F provenance) |
| B2 PyPI/vuln ports | LOOP-S (≥180 min) | node tests + view-contract fixtures + Phase-P cost-gate fixture (`test_no_thirty_gb_lie` port) |
| B3 MCP tools | LOOP-S | tool-callable smoke + kedro-mcp-absent test |
| B4 parity | **ATT** ⚿ (Q1 sign-off; credentialed full run) | loop-built parity-diff harness, human judges drift |
| B5 refresh assets | LOOP-S ⚿ (Q6 first) | vdb/cve/mapping fixture gates; consumer-profile offline fixture |
| B6 seed-gaps | LOOP-E-able | byte-identical-seed fixture + report snapshots |
| B7 SBOM intake | LOOP-S | format fixtures (NBSP, six buckets, offline resolver) |
| B8 Basilisk | LOOP-S ⚿ (Q7 first) | ecosystem-tag + tri-state + offline-skip fixtures |
| B9 velocity | LOOP-E-able | 90-day-gate fixture + baseline-shape check |
| B10 migration-readiness | LOOP-E-able | bucket fixtures + not-in-tracker labeling test |
| C1 kedro-dagster | AUTO + **ATT** ⚿ (schedule bring-up, Q2 re-verify) | `dagster-dryrun` (definitions load, schedules enumerate) |
| C2 kedro-viz | LOOP-E | headless viz-build smoke (`pixi run viz --dry`/build) |
| D1 BSL models | LOOP-S | metric-parity fixtures vs legacy CLI outputs (the 28-CLI answers) |
| D2 Vizro dashboard | AUTO (visual judgment) | page-config validation tests (Vizro = validated config — machine-checkable) |
| D3 Vizro-AI | **ATT** ⚿ (Q3 backend) | NL-query smoke once backend chosen |
| E1 A2A | AUTO (design) → LOOP-E (impl) | payload-schema round-trip fixtures |
| E2 OTel/OpenLineage | LOOP-E | emitted-span/lineage-event fixtures |
| F1 DuckDB swap | LOOP-S + ATT perf benchmark (AC-7 cold-start claim) | full `test-all` + fixture parity re-run |
| F2 validation hooks | LOOP-S | validator-agnostic hook fixture (stub second validator) |
| F3 vss/RAG | LOOP-E | ranked-similarity fixture |
| F4 hygiene + gate | LOOP-S | exit-code contract (0/1/2 + legacy flip) + four-axis schema fixtures |
| G1 WASM | AUTO | Playwright headless load-and-query check (Chromium is pre-provisioned in this factory) |
| G2 static host | LOOP-E (emitter) + ATT (publish creds) | emitted-artifact layout fixture |
| G3 sensors | AUTO ⚿ (Q2 daemon revisit) | simulated-event trigger test |
| H1–H4 factory | H1 LOOP-E; H2 AUTO; H3 LOOP-E; H4 LOOP-E | scaffold-layout test; crew smoke; REST-sync fixtures (mock Wagtail); asset dry-run |

Net: **~19 of 30 stories are loop-drivable** (10 at spec-approval, 9 relaxable to per-epic), 7 dev-auto-inline, 4 attended-with-loop-built-harness. Every ⚿ is a predictable, schedulable human event — none is an emergency.

### Development workflow (the operating loop per wave)

1. Wave opens: resolve the wave's Q-gates; run `bmad-sprint-planning` for the wave's stories; TEA `test-design` for the wave, `atdd` per pipeline story (red-phase fixtures = the verify assets); append the wave's verify commands to `[verify] commands`.
2. Loop runs the wave's LOOP stories sequentially (supervised for the first two, then overnight-eligible); AUTO stories interleave in attended sessions; DW entries accumulate.
3. Wave closes: attended boundary event (parity/benchmark/bring-up as applicable) → `bmad-loop-sweep` triage → full `test-all` + `bmad-drift-check` + `llms-full-check` → squashed story commits reviewed → push → **PR per wave** → CFE Rule-2 check (retro obligations tracked; final retro at effort closeout).

### Testing and QA (the verify-command growth plan)

New pixi tasks to create (each is a story deliverable, per verify-first sequencing): `kedro-test` (A1), `kedro-catalog-check` (A2), `parity-diff` (B4 harness, built by B1/B2 stories incrementally), `dagster-dryrun` (C1), `bsl-metric-check` (D1), `wasm-smoke` (G1). All run `--frozen`; all fixture-based; `[verify] commands` grows per wave and never shrinks. In-loop gates stay scoped (changed-unit tests + the story's fixtures); `test-all` runs at wave boundaries only.

### Cost and resource management

Token: 2M/story ceiling with explicit pre-flight raises for B1/B2/F1 (the keystones); the pilot's 25.8M single-attempt burn is the cautionary anchor — budget-raise beats timeout-retry every time. Time: session 180 min baseline; `dev_stall_grace_s = 600` covers slow background test runs (raise for F1's benchmark story). Disk: lean dedicated pipeline env (A1) keeps worktree materialization cheap; failed-attempt branches (`keep_failed`) pruned at sweep.

### Risk assessment and mitigation (implementation-specific)

| Risk | Mitigation |
|---|---|
| Worktree × symlink seam strands artifacts | Wave-0 bootstrap fix + A3 as the designated smoke story |
| Worktree env materialization slows every story | Lean env from A1; shared pixi cache; measure in the A3 smoke |
| Long test runs read as stalled sessions | `dev_stall_grace_s` tuned per wave; background-run pattern in story specs |
| Adversarial-review over-engineering across ~19 loop stories | Review checklist constrained to correctness + contract fixtures; `trigger = recommended` stays |
| Dagster 2.0 lands mid-effort (breaks `kedro-dagster <2.0` pin) | Q2 wave-C re-verify; thin-bridge principle; Components exit ramp |
| Gate rot (fixtures drift from live behavior) | Wave-boundary attended events re-anchor fixtures against live runs (B4, F1 benchmark) |
| Loop maturity (v0.8.x) regressions | Pin bmad-loop tag; upgrade only at wave boundaries; keep Option C fallback warm |

## Technical Research Recommendations

1. **Adopt Option B (graduated autonomy) as the execution architecture** — encode the drivability map's mode column into the Tier-2 epics/stories and the spec's § 14 invocation.
2. **Make verify-first sequencing explicit in the spec** (§ 2.5): every wave's first deliverable is its gate; the six new pixi verify tasks are story deliverables with named owners (A1/A2/B-harness/C1/D1/G1).
3. **Run the Wave-0 preconditions checklist before any loop run**: hooks approval; `bmad-switch local-recipes`; **worktree-bootstrap fix + A3 smoke story** (the symlink seam); heaviest-story budget review; policy.toml wave-B block (`[verify]` additions, B1/B2 budget raises).
4. **Keep the human surface scheduled, not reactive**: Q-gates drained at wave opens; parity/benchmark/bring-up as named wave-boundary events; PR per wave; Rule-2 retro at closeout.
5. **File the three upstream requests now** (they mature on bmad-loop's timeline, not ours): resume-on-timeout; retry-seeded-from-preserved-attempt; PR-lifecycle hook at the per-epic gate. Watch `max_parallel` — if fan-out ships, Waves C–E are the safe place to use it first.
6. **Fold the § 2.5/§ 14 updates into the spec at the next refinement** (with this report as the cited evidence), alongside the § 12.1 candidate-signals batch from the domain research — one consolidated v5.3.

---

# Research Synthesis: Autonomous Agentic SDLC for the cf_atlas Kedro Migration

## Executive Summary

The question this research answered: **can the ambitious migration and the ambitious execution machinery compose — and what does "using bmad-method/loop/dashboards to the fullest" concretely mean here?** The answer is yes, with a precise shape. "To the fullest" does **not** mean maximal gate removal — the verified reality (bmad-loop v0.8.1 is sequential-only, the loop's power lives entirely in deterministic verify gates, and the migration's gates don't exist yet) means the fullest use of the machinery is **graduated autonomy with verify-first sequencing**: attended/dev-auto sessions build the harness in Waves 0/A, the loop drives Wave B under per-story-spec-approval with TEA-generated fixture gates, autonomy relaxes to per-epic as gates prove out (C–E), and F–H run mixed. Under this architecture ~19 of 30 stories are loop-drivable and every human touchpoint is a scheduled batch-boundary event.

The research also hardened the plan against five concrete failure modes found along the way: the **worktree × multi-project-symlink seam** (untested; could strand spec artifacts — fixed by a Wave-0 bootstrap + the A3 smoke story), **worktree pixi-env materialization cost** (solved by a lean dedicated env from A1), **keystone-story budget blowouts** (the pilot's 25.8M-token lesson — pre-flight budget raises for B1/B2/F1), **long test runs reading as stalled sessions** (`dev_stall_grace_s` tuning), and **adversarial-review over-engineering** (correctness-constrained review checklists). Three upstream bmad-loop gaps worth filing now: resume-on-timeout, retry-from-preserved-attempt, and a PR-lifecycle hook.

**Verified capability corrections that reshape assumptions**: `max_parallel = 1` (parallel-wave imagery is aspirational); kedro-mcp and the BMAD dashboards observe *artifacts*, not loop sessions (the TUI is the only run observer — but the dashboards work during runs for free via the artifact tree); `llms-full.txt` lacks the autonomy docs (use `/reference/dev-auto/` + the TEA site); and the repo's loop policy is already stricter than upstream defaults, with pilot learnings pre-paid on pyforge-warden.

## Hand-off (research → spec v5.3 + Tier-2 intake)

1. § 2.5: encode graduated autonomy + verify-first sequencing (replacing the residual "parallel worktrees" framing with the sequential-story reality).
2. § 14: the per-wave operating loop (Q-drain → atdd → loop → sweep → boundary event → PR per wave) + the Wave-0 preconditions checklist.
3. Tier-2 epics/stories: carry the drivability map's mode column + the six verify-task deliverables (kedro-test, kedro-catalog-check, parity-diff, dagster-dryrun, bsl-metric-check, wasm-smoke); A3 = first loop story/worktree smoke.
4. `.bmad-loop/policy.toml`: wave-B `[verify]` additions; B1/B2/F1 budget raises; per-stage adapter overrides as needed.
5. Upstream: file the three bmad-loop feature requests; watch `max_parallel`.

## Methodology & Source Verification

Internal grounding: `.bmad-loop/policy.toml` + hook relay + `.claude/settings.json`, `docs/specs/bmad-loop-adoption.md` (incl. pilot learnings), `pixi.toml` task inventory, CLAUDE.md conventions, spec v5.2. External verification (web agent + direct fetches, 2026-07-16): official bmad-loop README (bmad-code-org), the `/reference/dev-auto/` page, TEA docs, dashboard marketplace/repo pages, `llms-full.txt` keyword probe, Claude Code best-practices, the Ralph-technique source. Confidence: HIGH on all repo configs and official docs; MEDIUM where single-sourced (dashboard versions, org-adoption inference) or reasoned-not-reproduced (the worktree seam — hence the mandated smoke test).

**Research Completion Date:** 2026-07-16
**Confidence Level:** HIGH on the decision-driving findings (sequential clamp, gate inventory, pilot learnings, dev-auto contract); flagged inline elsewhere.
