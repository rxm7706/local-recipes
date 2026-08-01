---
title: Marshal (pyforge-marshal)
status: final
created: 2026-07-25
updated: 2026-08-01  # CAP-9 -> FR-59/FR-60; competitive re-frame; FR-13 re-scope; FR-58 psmux; convergence watch; Q-3/Q-10..14 resolutions; durable-runs -> FR-61/FR-62/FR-63; fidelity-enforcement (Marshal-only slice) -> FR-64
project: pyforge-marshal
dist: pyforge-marshal
module: pyforge.marshal
cli: marshal
owner-dream: docs/dreams/pyforge-marshal.md
mode: headless
inputs:
  - planning-artifacts/product-brief-pyforge-marshal.md
  - planning-artifacts/research/market-agent-orchestration-research-2026-07-25.md
  - planning-artifacts/research/domain-agent-portability-and-governance-research-2026-07-25.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/ecosystem-crew.md
  - docs/dreams/agent-portability.md
  - docs/dreams/agentic-sdlc-autonomy.md
  - _bmad-output/projects/local-recipes/planning-artifacts/specs/spec-bmad-loop-governance/SPEC.md
  - _bmad-output/projects/local-recipes/planning-artifacts/specs/spec-multi-loop-isolation/SPEC.md
  - docs/specs/bmad-loop-adoption.md
  - docs/specs/copilot-bridge-vscode-extension.md
  - docs/specs/bmad-copilot-adapter-upstream.md
---

# PRD: Marshal

## 0. Document Purpose

This PRD is for the Marshal builder, the Ecosystem Crew's station owners, and the downstream architecture and epic-breakdown workflows. It is structured Glossary-first so that downstream artifacts inherit exact vocabulary; features are grouped with globally-numbered FRs nested beneath them; cross-cutting NFRs are separate; and inferences are tagged `[ASSUMPTION]` inline and indexed in §13.

It builds on, and does not duplicate, the product brief (`planning-artifacts/product-brief-pyforge-marshal.md`) and the two cited research reports under `planning-artifacts/research/`. Two sections carry decisions rather than requirements and are load-bearing for everything downstream: **§5 — the wrap-versus-absorb decision** and **§6 — the agent-portability fold**. Read those before §7.

---

## 1. Vision

Marshal makes unattended software development something a human can actually trust. Not autonomy as a leap of faith — autonomy as a *gradient*: attended stories first, then unattended loops wrapped in verify gates and quality gates, with a hard rule that anything the agent cannot safely decide **escalates to a human instead of being guessed**. Spec in, validated code out, every run visible.

Today the capability runs as a hand-assembled stack of an external orchestrator plus two shell-adjacent scripts and a set of memorized operating rules. It works — it drove `pyforge-atlas` to 32/32 stories and `pyforge-warden` to 31/31 across six epics, and it runs seven concurrent loop homes on one machine today. But its failure modes are absorbed by the operator: a dropped connection parks a session until a token cap fires; a merged story's spec is deleted with its worktree unless someone remembers to copy it; hard stories need a config file hand-edited between batches; a resume launched in the foreground gets killed mid-review.

`marshal` turns that stack into a product: one CLI with four charter verbs, a supervisor that catches what the raw loop does not, and a paper trail that survives teardown by construction. It is deliberately **harness, not skill** — the thing that governs the agent cannot be a thing the agent authors.

---

## 2. Target User

### 2.1 Jobs To Be Done

- **Get a wave of stories built overnight** without waking up to a stalled session, a surprise bill, or an unreviewable diff.
- **Prove what happened.** Reconstruct, months later, which spec drove which merge, what the gate checked, and who approved what.
- **Run many projects at once** without one project's state bleeding into another's.
- **Stop memorizing the operating rules.** Encode them where a machine enforces them.
- **Keep the method when the agent changes.** Run the same spec and the same gates on whichever CLI the subscription covers.
- *(Emotional)* **Stay the governor, not the operator.** Own intent; delegate execution; never be the thing that noticed the run died.

### 2.2 Non-Users (v1)

- Developers wanting inline completion or IDE chat. That is Copilot and Cursor; Marshal adds nothing.
- Teams wanting a hosted service. Marshal is a self-hosted CLI; there is no control plane.
- Windows-native users without WSL — a harness constraint, not a choice (§11, C-4).

### 2.3 Key User Journeys

- **UJ-1. The overnight wave.** The operator has an approved epic of eight stories. They run `marshal factory spin --epic 6` and go to bed. The supervisor watches each session; one dev session's API connection drops mid-response and is detected idle at 25 minutes, stopped, and retried rather than burning to a 4M-token cap. One story hits a genuine spec contradiction and escalates — the run pauses and notifies rather than guessing. By morning six stories are merged with green verifies, one is waiting on a human decision, one is deferred with a named reason. *Realizes FR-9, FR-13, FR-15, FR-17.*

- **UJ-2. The contract freeze.** Story 6.1 amended a schema and froze three files. The operator sets the gate mode to per-story spec approval; every subsequent producer story pauses after drafting its spec. The operator reads the spec, and `marshal gate evaluate --scope-check` confirms the story's declared surface does not touch the frozen trio. Approval releases the story. *Realizes FR-20, FR-22, FR-24.*

- **UJ-3. The morning after.** `marshal status` shows nine loop homes: seven idle, one running with its current story and elapsed budget, one paused on an escalation. Each row links to a run journal. The operator drills into the paused one, resolves the contradiction, and resumes — backgrounded, because there is no other way to launch it. *Realizes FR-36, FR-38, FR-17.*

- **UJ-4. Landing the wave.** `marshal deploy` opens one batch pull request for the merged stories, promotes each merged story's spec from the run's gitignored scratch into tracked planning artifacts, refreshes the sprint feed and console data, and reports which merge subjects conformed to the convention the dashboard keys on. Nothing depends on the operator remembering to copy a file. *Realizes FR-28, FR-30, FR-32.*

- **UJ-5. Proving portability.** The operator wants the method to run on the Copilot CLI. `marshal adapters sync` projects the 89 skills into the tree that adapter expects; `marshal adapters probe copilot` records what the CLI actually supports here; `marshal adapters conform copilot` drives a canonical smoke story end to end and writes the result into a conformance matrix. The claim "BMAD runs on Copilot" becomes an artifact with a date on it, not an aspiration. *Realizes FR-41, FR-43, FR-45.*

---

## 3. Glossary

- **Marshal** — the display brand. **`pyforge-marshal`** is the distribution name, **`pyforge.marshal`** the import module, **`marshal`** the CLI. Branding rule (matching Warden): display copy uses *Marshal*; file and package names use *pyforge-marshal*.
- **Harness** — the deterministic, non-LLM machinery that governs an agent session: the orchestrator, the gates, the sandbox and permission boundaries, the verify commands. The unit of governance. **Never a skill.**
- **Skill** — an LLM-executed workflow (a BMAD skill, a community plugin, a forged skill). The unit of execution. Runs *inside* the harness.
- **Loop** — one orchestrated run: a sequence of stories, each driven through dev → verify → review → verify → commit in fresh agent sessions.
- **Loop home** — an isolated working directory for one loop: a git worktree on branch `loop/<slug>` with its own BMAD active-project state and a backlink to the canonical Tier-3 store. Many loop homes coexist; `main` is never checked out twice.
- **Story** — the smallest gated unit of work, identified `<epic>.<seq>`.
- **Story spec** — the per-story intent contract (intent, acceptance criteria, and where present the dev/review triage log). Durable and git-tracked, not runtime scratch.
- **Gate** — a checkpoint that must pass before a story progresses. Three kinds: an **approval gate** (a human releases the story), a **verify gate** (a deterministic command must exit zero), and a **scope check** (the story's changed surface must lie inside its declared surface).
- **Gate mode** — the run-level approval policy: `per-story-spec-approval`, `per-epic`, or `none`. Mapped to autonomy levels in §7.3.
- **Escalation** — a halt because the agent encountered something it cannot safely decide (a spec contradiction or gap). Pauses the run; resolved by a human as a spec amendment, never as chat.
- **Deferral** — a story the loop could not land (attempts exhausted, review did not converge, budget or idle ceiling hit) recorded with a reason, leaving the run to continue.
- **Supervisor** — Marshal's out-of-band watcher over a running loop: idle-strand detection, budget ceilings, escalation surfacing, journal emission. Runs *outside* the agent session and cannot be disabled from inside it.
- **Idle strand** — an agent session that has stopped producing output but has not exited — typically a dropped connection mid-response — and will otherwise burn to a token or time cap before being noticed.
- **Adapter** — a coding-agent CLI that the harness can drive (claude, codex, gemini, copilot, antigravity, opencode), described by a declarative profile.
- **Skill tree** — the directory an adapter reads skills from. Divergent by adapter: `.claude/skills` (claude, opencode) versus `.agents/skills` (codex, gemini, copilot, antigravity).
- **Conformance matrix** — the dated, per-adapter record of whether a canonical smoke story completed here.
- **Run journal** — Marshal's own durable, append-only record of a run: story transitions, gate outcomes, escalations, budget consumption, supervisor actions.
- **Frozen surface** — a set of files a prior story declared contractually stable; later stories must not modify them.
- **Tier-2 / Tier-3** — tracked planning artifacts versus gitignored execution output, per the repo's spec-driven layout.

---

## 4. Why Now

Three windows are open simultaneously, and none of them stays open indefinitely.

**The competitive slot is vacating, not filling.** Between 2025 and 2026 the open-source local-loop tier thinned sharply — Roo Code shut down 2026-05-15, aider went nine weeks without a commit against 1,762 open issues, Sweep pivoted to an IDE product, Codegen was acquired and deprecated — while hosted agents consolidated around platform-bound gating. The gate-first, self-hosted, spec-as-contract slot is emptier now than it was a year ago.

**The upstream harness just got materially better, in exactly the directions Marshal needs.** `bmad-loop` moved 0.8.1 → 0.9.0 within the adoption window, gaining a pluggable multiplexer layer (with a non-tmux backend in the tree, the first crack in the POSIX-only constraint), an adapter-probe subcommand, and **six declarative adapter profiles**. Wrapping captures that velocity; forking forfeits it.

**The strongest competitor has announced the thesis but not shipped it.** OpenHands' *Verification Stack* post argues verification, not generation, is the bottleneck and proposes a critic model plus a repo-level verifier. They are funded, at 82k stars, and aiming at the same target. The window is measured in quarters.

**Re-framed 2026-08-01** (`research/market-agent-orchestration-research-2026-07-31.md` supersedes the generic slot claim): gated-unattended became a *named industry practice* ("Ralph loops"), Claude Code **Auto Mode** ships in-session safety with approval checkpoints first-party, and **Composio AO** — now the closest competitor — runs worktree-isolated agents managing their own PR lifecycle behind milestone gates. What remains unclaimed is **four properties in combination**: (1) the spec as an *executable contract* — frozen-surface scope checks; everyone stops on tests, nobody on contract conformance; (2) the supervisor *outside the session*, un-disableable (NFR-4); (3) **never-false-green** as a verdict lattice — unevaluable ≠ pass; (4) the paper trail that *survives teardown*. Marshal's positioning language uses these four, never the eroded generic claim.

---

## 5. Decision: Wrap versus Absorb

**This is the PRD's central question and it is resolved here, not deferred.**

### 5.1 The question

Marshal's capability today is `bmad-loop` (an external, MIT-licensed, git-upstream orchestrator) plus `scripts/bmad-switch` and `scripts/bmad-loop-worktree` (repo-local, stdlib-only Python). Two shapes were on the table:

- **Option A — Wrap.** `marshal` is thin porcelain that orchestrates `bmad-loop`, `bmad-switch` and worktree provisioning as they are. The harness stays external; Marshal owns composition, supervision, and the paper trail.
- **Option B — Absorb.** `pyforge-marshal` absorbs or forks the loop, becoming a self-contained distributable that owns the whole DEV → VERIFY → REVIEW → COMMIT engine.

### 5.2 Evidence that decides it

Five findings, in descending weight.

**(1) Option B's headline benefit already exists.** The stated case for absorbing was "self-contained distributable." But `bmad-loop` 0.9.0 is *already packaged by this factory* as a `noarch: python` conda recipe (`recipes/bmad-loop/`, MIT, entry point `bmad-loop`, five pure-Python run deps, built GREEN on linux-64 with rattler-build). A `pyforge-marshal` conda package that declares `bmad-loop` as a run dependency installs the entire stack in one command. **Absorbing buys nothing on distribution and costs a fork.**

**(2) Every known gap is peripheral to the loop's core, not inside it.** The gaps are real and they are Marshal's product — but examine where each one *lives*:

| Known gap | Where the fix lives |
|---|---|
| No idle-strand detection — a dropped connection parks a session until the ~4M-token cap fires | **Outside** the session. The proven stopgap was already an external `tmux` + log-mtime watchdog. |
| Story specs destroyed by worktree teardown (13 of 31 lost outright) | **After** merge. A promotion step. |
| Model tiering is per-run; hard-story batches need `policy.toml` hand-edited between batches | **Before** launch. Policy composition. |
| Resumes must be backgrounded or a foreground timeout kills them mid-review | **At** launch. Process management. |
| Doc-only stories trip a "no changes in worktree" false negative | **Around** the verify step. A pre-classification. |
| Sound-but-unconverged stories need hand-landing with an exact merge-subject string | **After** the loop. A landing step. |
| `worktree_seed` carries a hard-coded project slug | **Before** launch. Policy composition. |
| No PR lifecycle — the loop stops at local merge | **After** the loop. |
| `planning_artifacts` composition is hard-coded upstream | **Upstream** — and the multi-loop-isolation SPEC already says so explicitly. |

**Not one of these sits inside the dev/verify/review/commit engine.** They are all provisioning, supervision, or landing — the exact surface a wrapper owns naturally. Absorbing the engine would be paying a fork's price to fix problems that are not in the engine.

**(3) The doctrine points at wrap, harder than it first appears.** The execution doctrine says the harness is the unit of governance and is deliberately not a skill. Both options satisfy that — `marshal` is a deterministic CLI either way. But the multi-loop-isolation SPEC already binds a related principle: fixing `planning_artifacts` composition "belongs upstream in bmad-method," listed under *Non-goals*. Absorbing would make Marshal the fork-owner of somebody else's governance core, converting every upstream fix into a merge conflict and every upstream improvement into a decision about whether to port it. That is the opposite of the standing posture.

**(4) Upstream velocity is high and directionally aligned.** 0.8.1 → 0.9.0 delivered a pluggable multiplexer (with a non-tmux backend appearing — the eventual answer to the Windows constraint), `probe-adapter`, and six adapter profiles covering the entire portability charter. A fork taken today forfeits all of that, and the portability work Marshal would then have to build itself.

**(5) The market's cautionary tale is a fork-and-claim project.** The most-starred orchestrator in the category accumulated ~290 stub tools and a synthesized benchmark number while reimplementing everything. The credible position is a small, honest surface over machinery that demonstrably works, with first-party run evidence — not a large surface with a thin implementation.

**The one genuine argument for absorbing** — single-vendor dependency risk, the failure mode that killed Roo Code and stalled aider — is real, and it is addressed by design rather than by forking: see §5.4.

### 5.3 Decision

> **RECOMMENDATION: Option A — Wrap.** Specifically, **"wrap and supervise":** `marshal` is thin porcelain over `bmad-loop`, `bmad-switch` and worktree provisioning, **plus a supervisory layer that owns everything the loop's core does not** — provisioning, policy composition, out-of-band run supervision, gate evaluation as a standalone object, landing, paper-trail promotion, fleet visibility, and adapter conformance.

The distinction matters for scoping: "thin porcelain" alone would be a shell alias and would not be a product. The supervisor *is* the product. `bmad-loop` remains the engine; Marshal is the factory floor around it — the thing that provisions the line, watches it run, judges the output, and files the paperwork.

### 5.4 Recorded tradeoffs

**What wrapping costs, stated plainly.**

- **Single-upstream dependency.** If `bmad-loop` stalls or breaks, Marshal is exposed. *Mitigations:* keep the coupling surface small and explicit (FR-52 — every call into the loop goes through one adapter module, never scattered); pin the dependency by version (FR-56); contribute the three upstream-shaped fixes back (FR-58); and define hard fork triggers (below).
- **Gaps Marshal cannot fix from outside stay unfixed.** Anything genuinely inside the engine — session-level retry semantics, per-story model tiering if upstream never adds it — is an upstream feature request, not a Marshal story. Accepted; the current gap inventory contains none.
- **Version-skew surface.** A `bmad-loop` minor bump can change output shape. *Mitigation:* NFR-9 requires contract tests over the loop's observable surface, run in CI, failing loudly on drift rather than silently misparsing.
- **Marshal cannot claim to be "the orchestrator."** It is the station around one. Positioning must be honest about this; the research is clear that overclaiming is what destroyed the category's most-starred project's credibility.

**Fork triggers — the conditions under which this decision is revisited, written down now so the revisit is evidence-driven:**

1. `bmad-loop` goes 6 months with no release **and** an accumulating blocker-severity issue backlog (the aider signature: 0 commits in 9 weeks against 1,762 open issues).
2. An upstream change breaks Marshal's contract tests in a way that cannot be adapted around within one minor version.
3. Upstream declines a fix that is load-bearing for a Marshal invariant (a false-green risk, or a governance boundary).
4. Licence change away from MIT.

**Convergence watch item (added 2026-08-01 — a watch, not a trigger):** the upstream method's public roadmap names **"Dev Loop Automation"**. If upstream ships native loop automation overlapping bmad-loop or Marshal's supervision, the response is to **re-evaluate the seam, not the wrap** — convergence is the opposite failure mode from stall, and the four fork triggers above do not cover it.

On trigger, the fallback is **vendoring a pinned fork behind the same adapter module** — which FR-52's single-seam constraint makes a bounded change rather than a rewrite. This is why the seam is a requirement and not a style preference.

---

## 6. Decision: the agent-portability fold

The portability charter (`docs/dreams/agent-portability.md`, re-scoped from Herald to Marshal in the 2026-07-23 ownership review) arrived with two legacy specs attached. Both encode a 2025-era answer. Research supersedes most of it, and the substance survives in a different, safer form.

### 6.1 What changed

`bmad-loop` 0.9.0 ships **six declarative adapter profiles** — `claude`, `codex`, `gemini`, `copilot`, `antigravity`, `opencode` — each naming the binary, prompt template, bypass arguments, model flag, usage parser, hook dialect, seed files, and **skill tree**. The `copilot` profile drives the **GitHub Copilot CLI directly** (`copilot -i --allow-all-tools --allow-all-paths`). The sanctioned headless path to Copilot therefore already exists upstream, and the HTTP-proxy premise of the legacy bridge spec is obsolete for this charter.

Research reinforces this from the other side. There is no published GitHub statement permitting or forbidding third-party OpenAI/Anthropic-format clients against Copilot inference, but the mechanism is an undocumented token-exchange endpoint plus mandatory spoofed editor headers — unversioned, reverse-engineered, and abuse-detection-exposed — while GitHub shipped `copilot --acp` in public preview on 2026-01-28 with "CI/CD pipeline orchestration" named as an intended use case. And `vscode.lm` is unusable for unattended work on four independent grounds: no headless VS Code exists, first-use consent cannot be pre-granted or suppressed, extension tool invocations always confirm, and the API draws the same rate-limited Copilot quota.

**But the charter is not therefore satisfied, because of one concrete, verified gap:** four of the six profiles read skills from `.agents/skills/`. **`.agents/` does not exist in this repository**, and all 89 skills live only under `.claude/skills/`. Running the loop on codex, gemini, copilot or antigravity today would find no skills at all. That gap — not a proxy, not an extension — is Marshal's actual portability work.

### 6.2 The fold

| Legacy scope | Source | v1 / Deferred | Disposition |
|---|---|---|---|
| **Skill-tree projection** across adapter trees | *(new — found by this research)* | **v1** | FR-41, FR-42. The blocking gap. 89 skills; `.agents/` absent. |
| **Adapter probe + conformance matrix** | new; wraps upstream `probe-adapter` | **v1** | FR-43, FR-44, FR-45. Turns "runs on any agent" into a dated artifact. |
| **Per-project adapter and model policy** | absorbs bridge stories 13–14 (headless runner wiring; multiproject awareness), in safer form | **v1** | FR-49, FR-50, FR-51. Env wiring becomes composed policy; the hard-coded `worktree_seed` slug dies here. |
| **Entry-file family lockstep check** (`AGENTS.md` ↔ `CLAUDE.md` / `.cursor/rules` / `GEMINI.md` / `copilot-instructions.md`) | agent-portability Dream; AGENTS.md Portability contract | **v1 (detector only)** | FR-46. Research shows Cursor applies the *union* of AGENTS.md and CLAUDE.md while Claude reads only CLAUDE.md — drift is silently cross-contaminating. Detect and report; **do not edit shared files** (Q-2 ownership). |
| **Unattended-use risk surface** | absorbs bridge story 15 | **v1 (reframed)** | FR-47. Not a Copilot-TOS modal — a general first-run acknowledgement per adapter, recording the adapter's own first-run requirement (each profile ships one) and the sustained-automation caveat. |
| **copilot-api HTTP bridge** (five proxy patterns) | `copilot-bridge-vscode-extension.md` G1–G5, stories 1–12 | **SUPERSEDED** | Upstream `copilot` profile drives the sanctioned CLI. Proxy is unversioned, reverse-engineered, abuse-exposed. Not built. |
| **Sideloaded VS Code extension** (`.vsix`, setup wizard, service registration, migration assistant, diagnostics) | same spec | **DEFERRED — out of charter** | An IDE developer-experience product, not headless orchestration. Marshal is a CLI. |
| **`@bmad` Copilot-Chat adapter upstreaming** | `bmad-copilot-adapter-upstream.md` | **DEFERRED — re-owned** | A human-in-the-IDE conversational surface. Remains a valid upstream contribution brief; belongs with Herald/comms, not Marshal's line. Contribution-path decision stays open upstream. |
| **ACP as the adapter contract** | *(new)* | **DEFERRED — scheduled revisit** | Versioned schema, neutral governance, 38-agent pinned registry, native gate primitives. But `bmad-loop` owns driving, `schema-v2.0.0-alpha` is in flight, and the two agents this factory most uses are the only two needing adapters. Revisit trigger in Q-6; upstream feature request under FR-58. |
| **Windows-native operation** | bmad-loop-adoption § Windows note | **DEFERRED — upstream-tracked** | A non-tmux multiplexer backend now exists in the upstream tree. Wrapping means Marshal inherits it when it lands. |

Both legacy specs are to be marked superseded **at merge time by the caller** — this effort does not edit `docs/specs/`.

---

## 7. Features

### 7.1 Loop homes and isolation — `marshal init`

**Description.** Provisioning a place for a loop to run is currently three commands plus a memorized rule about a first-run trust dialog. `marshal init <slug>` makes it one idempotent operation that either produces a verified-isolated loop home or fails with a named finding. It creates or reuses a git worktree on `loop/<slug>`, switches the BMAD active project *inside* that worktree, provisions the Tier-3 backlink to the canonical store, composes run policy, projects adapter skill trees, and runs preflight. Realizes UJ-3, UJ-5.

**Functional Requirements:**

#### FR-1: Provision a loop home
The operator can create an isolated loop home for a project slug in one command.
**Consequences (testable):**
- A git worktree exists at the conventional sibling path on branch `loop/<slug>`.
- Re-running against an existing home succeeds and changes nothing (idempotent).
- The command prints a directly runnable launch line.

#### FR-2: Per-worktree active-project state
Each loop home carries its own BMAD active-project marker and planning-artifact symlinks, independent of every other home and of the main checkout.
**Consequences:**
- Provisioning home B leaves home A's and the main checkout's active project unchanged.
- The marker and the planning symlinks always agree; a desync is reported, never silently tolerated.
- `BMAD_ACTIVE_PROJECT` is exported in the printed launch line as belt-and-suspenders.

#### FR-3: Single-sourced Tier-3 store
A loop home's `implementation-artifacts` resolves to the main checkout's canonical directory, so every consumer sees one store at an identical repo-relative path.
**Consequences:**
- The home's `implementation-artifacts` realpath equals the main checkout's.
- The canonical directory is created if absent.
- A real, non-empty local directory is **never** replaced; the command refuses with a named finding.

#### FR-4: Isolation verification
The operator can assert that two or more loop homes are genuinely isolated.
**Consequences:**
- Exit 0 when markers and symlinks are independent, Tier-3 realpaths are identical, and the main checkout is untouched.
- Non-zero with a named finding on any cross-talk.
- Works for N ≥ 2 homes in one invocation. *(Live evidence: seven homes provisioned as of 2026-07-25.)*

#### FR-5: Preflight
Initialization verifies the run can actually start, rather than discovering it cannot at minute 90.
**Consequences:**
- Reports: harness present and version; multiplexer backend available; adapter binary present; story feed resolvable and parseable; verify commands resolvable; `main` not checked out twice.
- Each adapter's declared first-run requirement is surfaced as an explicit human action, because an unanswered first-run dialog is indistinguishable from a session timeout.
- Exits non-zero on any blocking finding, naming it.

#### FR-6: Teardown
The operator can remove a loop home cleanly.
**Consequences:**
- Worktree and branch are removed; `git worktree list` is clean afterwards.
- Refuses when the home has uncommitted or unmerged work unless explicitly forced.
- Never touches the canonical Tier-3 store.

#### FR-7: Adapter config seeding
Gitignored adapter configuration a fresh worktree lacks is seeded into the home.
**Consequences:**
- Each loaded adapter's declared seed files are present in the home after init.
- Project-specific extra paths are seeded from composed policy, not from a hard-coded list.

#### FR-8: Enumerate loop homes
The operator can list all loop homes with their resolved active project.
**Consequences:**
- One row per home: path, branch, active project, and whether it is desynced.

---

### 7.2 Run supervision — `marshal factory spin`

**Description.** The launch verb, and the home of Marshal's differentiator. `marshal factory spin` starts or resumes a gated run against an approved spec — **always detached**, so the foreground-timeout failure that killed a run mid-review is structurally impossible — with a supervisor attached that watches from outside the agent session. The supervisor detects idle strands, enforces budget ceilings, surfaces escalations, and writes the run journal. Realizes UJ-1, UJ-3.

**Functional Requirements:**

#### FR-9: Detached launch by default
Runs and resumes execute detached from the invoking shell.
**Consequences:**
- The command returns promptly with a run identifier; the run survives the caller exiting.
- Foreground execution is available only behind an explicit flag, documented as unsafe for resumes.
- Attaching to a live run's session is a separate, non-destructive command.

#### FR-10: Scoped launch
The operator can scope a run to one story, an epic, a count, or the whole feed.
**Consequences:**
- Story, epic, and max-count selectors are supported and composable.
- The resolved story list is echoed before launch and recorded in the journal.

#### FR-11: Supervisor attaches to every run
Every run started by Marshal has a supervisor process attached for its lifetime.
**Consequences:**
- The supervisor runs outside the agent session and cannot be disabled from within it.
- Supervisor death is itself detected and journaled; it does not silently stop watching.
- The supervisor is inert on a run it did not start.

#### FR-12: Idle-strand detection
A session that has stopped producing output but has not exited is detected and acted on well before any token or time cap.
**Consequences:**
- Idleness is measured from observable session output (pane content and log modification time), not from the agent's self-report.
- The threshold is configurable with a default materially below the session budget. `[ASSUMPTION: default 25 minutes, matching the hand-written stopgap that worked in production.]`
- Fresh output re-arms the window.
- On expiry the supervisor takes a configured action — nudge, then stop-and-retry, then defer — with each step journaled and counted.
- *Motivating evidence: this class of failure cost three story attempts and one 4M-token review cycle in a single wave.*

#### FR-13: Budget ceilings
A run cannot exceed configured token and wall-clock ceilings without a named stop.
**Consequences:**
- Per-story and per-run ceilings are enforced; a breach stops the unit with a named reason rather than a silent defer.
- Consumption is journaled per story with a cost estimate where the adapter reports one.
- Approaching a ceiling emits a warning before the stop.
- *(Re-scoped 2026-08-01:)* upstream `bmad-loop` v0.9.0 ships **in-session** budget guards — credited, and not duplicated. Marshal's requirement is the half upstream cannot provide: ceilings enforced **from outside the session** by the supervisor (NFR-4), reachable from externally-observed quantities alone, so a wedged or compromised session cannot outlive its budget by being its own witness.

#### FR-14: Heaviest-story budget advisory
Before launch, the operator is warned when a selected story is likely to exceed the configured session budget.
**Consequences:**
- Preflight compares the session budget against a per-story hint (spec size, declared difficulty, prior attempt history) and warns.
- *Motivating evidence: a 90-minute cap killed the keystone story mid-work and burned 25.8M unrecoverable tokens.*

#### FR-15: Escalation surfacing
An escalation pauses the run and reaches the operator through configured channels.
**Consequences:**
- The run pauses; no story proceeds past an unresolved escalation.
- The escalation is journaled with story key, reason, and the artifact needing a decision.
- Notification fires on at least a durable file marker; desktop notification is best-effort.

#### FR-16: Deferral capture
A story the loop could not land is recorded rather than lost.
**Consequences:**
- Every deferral carries story key, reason class, attempt count, and where any preserved work lives.
- The run continues to the next story unless configured otherwise.

#### FR-17: Resume
A paused run can be resumed after a human resolves the blocking condition.
**Consequences:**
- Resume is detached, on the same terms as launch (FR-9).
- Resume re-attaches a supervisor.
- Resuming a run whose escalation is unresolved is refused with a named finding.

#### FR-18: Run journal
Every run produces a durable, append-only journal owned by Marshal.
**Consequences:**
- Records story transitions, gate outcomes, escalations, deferrals, budget consumption, and supervisor actions, each timestamped.
- The journal is machine-readable and survives worktree teardown.
- It is written incrementally, so a killed run still has a journal up to the kill.
- *Rationale: vendor retention is 48 hours to 180 days and agent transcript formats are documented as changing between versions. The record must be self-owned.*

#### FR-61: Bounded-loss durability *(added 2026-08-01 — `docs/dreams/durable-runs.md`)*
The supervisor pushes a run's work at its own stage boundaries, and durability is on by default for every fleet launch — no separate step a human has to remember to start.
**Consequences:**
- After the dev commit, after the review verdict, and after the merge, the supervisor pushes the affected station and per-story branches — loss is bounded by a stage, not by an interval timer.
- An interval-push watcher remains as the floor for whatever the stage hooks miss, and starts automatically as part of a fleet launch rather than requiring a separate manual invocation.
- Push is read-only against working trees and remotes — never a force-push, never a rewrite — so it cannot disturb a live session.
- *Motivating evidence: measured 2026-07-31 — 6 station loop branches on no remote, ~5,150 lines on `recover/*`, one story's 734-line transport branch (spec included) unpushed six days, 156 dangling commits one `git gc` from unrecoverable, and 1,748 lines sitting 40 minutes as a local-only commit. Nine detectors ran green throughout because none asked the durability question — the window reopens roughly every 60–90 minutes, once per station's dev phase.*

---

### 7.3 Gates and verification — `marshal gate evaluate`

**Description.** In the current stack the gate is a configuration line inside the orchestrator. Marshal makes it a first-class, independently invocable object: the same gate a run uses can be run by a human before approving, or by CI after the fact. It adds the scope check the operator currently performs by eye, and the doc-only classification that currently causes a false-negative rollback loop. Realizes UJ-2.

**Functional Requirements:**

#### FR-19: Standalone gate evaluation
The operator or CI can evaluate a project's gates without a run in flight.
**Consequences:**
- Runs the project's configured verify commands and reports pass/fail per command with captured output.
- Exit code is a stable contract: 0 pass, non-zero fail, with a distinct code for "could not evaluate".
- Evaluation never mutates the working tree.

#### FR-20: Project-scoped verify commands
Verify commands resolve from composed policy and are scoped to the active project.
**Consequences:**
- Another project's gates are never run during this project's story.
- A verify command that cannot be resolved is a blocking finding at preflight (FR-5), not a runtime surprise.

#### FR-21: Deterministic, no-LLM gates
Gate evaluation involves no model call.
**Consequences:**
- Evaluation is reproducible: the same tree and commands produce the same verdict.
- Gate outcome is derived only from command exit codes and the scope check — never from an agent's assertion that it passed.

#### FR-22: Frozen-surface scope check
A story's changed surface is checked against its declared surface and against frozen surfaces.
**Consequences:**
- Declared surfaces come from the story spec and may only **narrow** the project-declared surface, never widen it — a story spec is machine-drafted, so it cannot author the allowlist it is judged against (architecture AD-27). Frozen surfaces accumulate from prior stories through the run record (AD-26).
- A change to a frozen file is a hard failure naming the file and the story that froze it.
- A change outside the declared surface is a failure naming each offending path.
- *Motivating evidence: the operator performed this check manually on every producer story of a six-epic build.*

#### FR-23: Doc-only story classification
Stories that legitimately produce no source change are classified before verification.
**Consequences:**
- A story whose declared deliverable is a document or decision record does not fail on "no changes in worktree".
- Classification is recorded in the journal.
- *Motivating evidence: a design-spike story tripped this false negative into a rollback loop and had to be recovered from a preserved ref by hand.*

#### FR-24: Gate mode ladder
The run's approval policy is selectable and labelled with its autonomy level.
**Consequences:**
- Supports per-story spec approval, per-epic, and none.
- Each mode carries an explicit autonomy label (§7.3 mapping below) surfaced at launch and in the journal.
- Changing gate mode mid-run is recorded as a decision with a timestamp, never applied silently.

**Autonomy mapping** — the gate configuration *is* the autonomy declaration:

| Gate mode | Autonomy level | Meaning |
|---|---|---|
| `per-story-spec-approval` | **L2 — Task-Based / Operator** | Human approves each unit's contract before work proceeds. |
| `per-epic` | **L3 — Conditional / Context Gates** | Machine-readable boundaries; human at epic seams. The production ceiling. |
| `none` + verify gates + escalation | **L4 — Approver** | Runs independently; surfaces only at blockers or pre-specified conditions. |
| *(unbuilt)* fleet budgets, self-governance | **L5 — Observer** | Frontier. Explicitly out of scope. |

*Grounding: no vendor or analyst publishes an authoritative numbered scale for coding agents; Anthropic explicitly declines, arguing autonomy is a property of the deployment. The labels above are adopted from DeepMind's Levels of Autonomy and Feng/McDonald/Zhang's Operator→Observer framing, and are declared here as Marshal's own documented tiering.*

#### FR-25: Gate evidence record
Every gate evaluation produces a durable record.
**Consequences:**
- Records commands run, exit codes, scope-check verdict, tree revision, and timestamp.
- Referenced from the journal and retrievable per story.

#### FR-26: Never false-green
No story reaches a merged state without a green verify and a passing scope check.
**Consequences:**
- Any path that would merge without both is refused.
- An unevaluable gate is treated as failure, never as pass. *(Consistency with Warden's never-false-green invariant.)*

#### FR-27: Review-cap landing path
A story that is sound but did not converge in review can be landed deliberately, under the same gates.
**Consequences:**
- A dedicated command lands a named story branch only after re-running the full gate (FR-19, FR-22).
- The merge uses the conventional subject form (FR-32); the operator does not hand-type it.
- The manual landing and its justification are journaled.
- *Motivating evidence: two warden stories were landed this way by hand.*

#### FR-64: A gate evaluation binds to the spec's Success signal *(added 2026-08-01 — `docs/dreams/fidelity-enforcement.md`, CAP-4)*
Gate evaluation checks that the verify commands it runs still trace to the tracked story spec's declared Success signal, not only that they pass.
**Consequences:**
- Evaluating a story's gate resolves its tracked `specs/spec-<key>.md` and confirms the verify commands run are the ones the spec's Success signal names.
- A verify command silently removed or narrowed since the spec was tracked is a named finding — a contract breach, not a passing suite.
- Where no tracked spec exists to bind against, the gate reports that gap explicitly (a row-7 finding in the fidelity stack) rather than evaluating silently against nothing.
- *Rationale: a spec's Success signal is worthless as a contract if nothing later fails when the test that proved it stops running — the never-false-green doctrine (FR-26) extended past merge time into the tracked record itself.*

---

### 7.4 Landing and paper trail — `marshal deploy`

**Description.** The verb that closes a wave. Landing is currently a sequence of remembered steps whose most important one — promoting each merged story's spec into tracked storage — is a convention adopted *after* 13 specs were lost. `marshal deploy` makes it mechanical. Realizes UJ-4.

**Functional Requirements:**

#### FR-28: Batch pull request
The operator can open one pull request for a wave of merged stories.
**Consequences:**
- Title and body are derived from the merged story set and the journal; the body lists stories with their gate verdicts.
- The PR targets the configured base branch; it is never opened against an upstream fork's default.
- Existing-PR detection updates rather than duplicating.

#### FR-29: Repository-hygiene preflight
Before opening or updating a PR, mechanical repository gates are checked.
**Consequences:**
- Reports which project-configured hygiene rules apply to the change set and whether each is satisfied.
- Rules are declared in project policy, not hard-coded into Marshal.
- Exits non-zero on an unsatisfied blocking rule with a remediation line.

#### FR-30: Automatic story-spec promotion
Every merged story's spec is promoted from run scratch into tracked planning artifacts.
**Consequences:**
- After a story merges, its spec is copied from the run's Tier-3 scratch into the project's tracked `planning-artifacts/specs/` — the **real** project path, never the gitignored `_bmad-output/planning-artifacts/` symlink — and **committed** by Marshal in a dedicated commit containing only promotion paths.
- Promotion is complete only when those bytes are reachable from a ref that survives the loop home; that ref may be **local**, so promotion never requires the network (architecture AD-29, NFR-2). *(Amended 2026-07-30, **F-14**: this consequence said "staged for commit", which AD-29 explicitly declares insufficient — a merely-staged spec dies with the branch at teardown, which is the motivating incident.)*
- Promotion happens **before** any worktree teardown for that story.
- A story that merges without a promotable spec is reported as a paper-trail gap, never passed over silently.
- Zero-byte or truncated specs are detected and reported rather than promoted.
- *Motivating evidence: 13 of 31 story specs were lost entirely and 8 more reduced to zero-byte husks before this became convention.*

#### FR-31: Spec-recovery assistance
When a spec is missing, the operator is given the recovery search paths.
**Consequences:**
- Reports the ordered candidate locations — surviving run-worktree snapshots first, then the epics-derived contract fallback.
- Reports, never fabricates: a regenerated contract-only spec is labelled as such.

#### FR-32: Merge-subject conformance
Merge commits carry the subject form downstream consumers key on.
**Consequences:**
- Marshal-performed merges emit the conventional subject; the exact form is configuration, not a literal in code.
- Deploy reports any merge in the wave whose subject does not conform.
- *Rationale: the program console's git-mode status detection keys on this string.*

#### FR-33: Sprint and console feed refresh
Landing refreshes the derived status surfaces.
**Consequences:**
- The project's sprint status is updated from the journal and the merged set.
- Console data regeneration is invoked where configured.
- Discrepancies between the ledger and git history are reported, never silently resolved. *(Motivating evidence: a sibling project's sprint file drifted to 26/32 against an actual 32/32.)*

#### FR-34: Deploy is idempotent and re-runnable
Re-running deploy after a partial failure completes the remaining steps.
**Consequences:**
- Already-promoted specs are not re-promoted or duplicated.
- Each step reports skipped / done / failed.

#### FR-35: No AI attribution in emitted artifacts
Commits, PR bodies and comments Marshal emits carry no AI-attribution or courtesy preamble.
**Consequences:**
- No co-author trailer, model line, or generated-with line is added by Marshal.
- Attribution, if ever added, is opt-in configuration and default-off.
- *Grounding: the repo's standing convention, and the cautionary precedent of an editor vendor defaulting an AI co-author trailer on and reverting it after backlash — a commit trailer is part of the permanent authorship and blame record.*

#### FR-59: Landing rules are declared policy *(added 2026-08-01 — CAP-9, operator ruling via `docs/dreams/pr-lifecycle.md`; resolves Q-3)*
The rules a repository demands for landing compose from the policy layers with per-key provenance, like every other governed value.
**Consequences:**
- Required checks, merge strategy, label rules, branch-retirement behaviour, and repo-specific triggers are policy keys, not memorized habits — including this repository's `maintenance` label on non-`recipes/` changes and the **ungated** `environment.yaml` sync check that the label does not suppress.
- The effective landing policy prints with each key's winning layer; an invalid landing policy is a preflight finding.
- *Grounding: five PRs hand-driven in one session (2026-07-31), each repeating the same written-but-unenforced sequence; one (#170) merged a real detector break because nothing in the landing path asked.*

#### FR-60: The last mile lands itself — `marshal land` *(added 2026-08-01 — CAP-9)*
A story or wave that passed its gates lands on the integration branch without a human driving the sequence.
**Consequences:**
- `marshal land` opens or updates the PR, applies required labels, waits on required checks, merges by the declared strategy, retires the branch, and resyncs — idempotently and re-entrantly, so a half-landed story (PR open, checks green, merge never issued) converges on re-run.
- Refusal semantics mirror teardown (FR-8): no merge on a red required check, no merge past an unacknowledged advisory finding, no silent force — refusals are named findings in the common envelope.
- Every landing writes a journal verdict: which checks were required, which passed, what merged, under whose authority.
- Wrap-never-absorb carried unchanged: the engine keeps dev/verify/review/commit and deliberately leaves this gap open; Marshal fills it around the engine, in the supervisor's domain.

#### FR-63: Fleet-wide branch retirement *(added 2026-08-01 — `docs/dreams/durable-runs.md`)*
Marshal proposes which station and story branches may be released, across the whole fleet, not only the one a landing just merged.
**Consequences:**
- A branch is a retirement candidate only when its content is reachable in the integration branch **by patch-id** (never a two-dot or three-dot diff heuristic — both misclassify squash-merges and branches the base has since moved past), its run has concluded, and its story is `done` with a recorded merge sha.
- `loop/*` branches and `rescue/*` tags are permanent exclusions — `loop/*` is how the fleet operates, and `rescue/*` tags are the only reachability for commits `git gc` would otherwise collect.
- Every proposed retirement names its evidence (merge sha, patch-id match, concluded run); anything unproven is refused, never defaulted to delete. Dry-run by default, like teardown (FR-8).
- Distinct from FR-59's per-landing branch-retirement policy key: that retires the one branch a landing just merged; this sweeps the fleet's accumulated estate on its own schedule. The two share no code path but must not disagree — a branch FR-59 already retired is never re-proposed here.
- *Motivating evidence: saving work created 36 branches and 160 rescue tags in one afternoon (2026-07-31), and nothing knew when any of them could be released.*

---

### 7.5 Fleet visibility — `marshal status`

**Description.** With nine loop homes live, "what is running?" currently requires inspecting several places. `marshal status` answers it in one view derived from ledgers, never hand-maintained. Realizes UJ-3.

**Functional Requirements:**

#### FR-36: Fleet view
The operator sees every loop home and its current state in one command.
**Consequences:**
- One row per home: project, branch, state (idle / running / paused-on-escalation / stopped), current story, elapsed time, budget consumed.
- Rows are derived from journals and run state, not from a hand-maintained file.

#### FR-37: Per-run detail
The operator can drill into one run.
**Consequences:**
- Shows the story sequence with per-story gate verdicts, escalations, deferrals, and consumption.
- Machine-readable output is available for every human view.

#### FR-38: Escalation queue
Runs paused on escalations are surfaced first.
**Consequences:**
- Paused-on-escalation rows are visually distinguished and sorted to the top.
- Each carries the reason and the artifact needing a decision.

#### FR-39: Ledger-versus-git reconciliation
Status reports disagreements between the ledger and git history rather than trusting either blindly.
**Consequences:**
- A story marked done with no corresponding merge — and the converse — is reported as a named discrepancy.
- *Rationale: git history is the durable record; the sprint ledger is the local one, and it has drifted in practice.*

#### FR-40: Stable machine-readable status contract
Status output has a versioned schema downstream consumers can depend on.
**Consequences:**
- A schema version accompanies the payload; additive changes do not bump it, breaking changes do.
- The console generator and any dashboard can consume it without scraping human output.

#### FR-62: Durability as a reported fleet property *(added 2026-08-01 — `docs/dreams/durable-runs.md`)*
`marshal status` reports unpushed work as a finding on the owning row, not only in a separate detector's output the operator has to remember to run.
**Consequences:**
- A row whose branches carry local-only content is never reported clean — the same refusal the fleet view already applies to an unowned Dream row.
- The finding names the branch and the extent (line/commit count) so the operator does not have to cross-reference a second command to size the exposure.
- *Rationale: "is the fleet's work saved?" required four separate commands before this FR (`bmad-loop status`, `tmux capture-pane`, a manual detector run, and re-deriving from git) — the same operator question, asked twice, is the failure signature this FR closes.*

---

### 7.6 Adapter portability — `marshal adapters`

**Description.** The portability charter, reduced to what is actually missing (§6). Realizes UJ-5.

**Functional Requirements:**

#### FR-41: Skill-tree projection
Skills are made available in every tree the configured adapters read from.
**Consequences:**
- After projection, each configured adapter's declared skill tree contains the project's skills.
- Projection uses the cheapest mechanism that the adapter and platform support, and the mechanism used is reported.
- The canonical source tree is authoritative; projected trees are derived and never edited in place.
- Re-projection after a source change converges; stale entries are removed.
- *Motivating evidence: `.agents/` does not exist in this repository; 89 skills live only under `.claude/skills/` (93 directories, 89 carrying a `SKILL.md`; verified 2026-07-30). Four of six adapter profiles would find nothing.*

#### FR-42: Projection drift detection
Divergence between the canonical skill tree and a projected tree is detected.
**Consequences:**
- Reports added, removed, and modified skills per adapter tree.
- Runs as part of preflight when a non-default adapter is configured.

#### FR-43: Adapter probe
The operator can capture what an adapter actually supports on this machine.
**Consequences:**
- Records binary presence and version, declared capabilities from the profile, and probe output.
- Sensitive values are redacted from the stored record.
- Probing an absent adapter reports it as unavailable rather than failing the command.

#### FR-44: Conformance smoke
The operator can drive a canonical smoke story end to end on a named adapter.
**Consequences:**
- The smoke story exercises spec read → change → verify → commit and is adapter-agnostic.
- Result is pass / fail / unavailable with the failing stage named.
- Runs in a throwaway loop home and leaves no residue.

#### FR-45: Conformance matrix
Per-adapter conformance results accumulate into a dated, tracked artifact, **keyed by host**.
**Consequences:**
- One row per adapter: status, adapter version, harness version, date, and the failing stage where applicable.
- Results older than a configured age are marked stale.
- The matrix is the only place Marshal makes a portability claim.

#### FR-46: Entry-file family drift check
Divergence across the cross-tool instruction-file family is detected and reported.
**Consequences:**
- Checks presence and mutual consistency of the configured entry-file family.
- Reports drift with the specific divergence; **does not edit** the files. *(Ownership is Q-2.)*
- *Rationale: Cursor applies the union of AGENTS.md and CLAUDE.md, Claude reads only CLAUDE.md, Codex and Copilot read only AGENTS.md — instruction content is not isolated per-CLI, so drift cross-contaminates.*

#### FR-47: First-run acknowledgement per adapter
Each adapter's first-run requirement and unattended-use caveat is surfaced once and recorded.
**Consequences:**
- On first configuration of an adapter, the profile's declared first-run requirement is presented as a required human action.
- A sustained-automation caveat is presented once per adapter and the acknowledgement recorded.
- Unacknowledged adapters are a blocking preflight finding, because an unanswered first-run dialog is indistinguishable from a session timeout.

#### FR-48: Adapter selection is project-scoped
Adapter and model choices resolve per project.
**Consequences:**
- Two loop homes may run different adapters simultaneously without cross-configuration.
- The resolved adapter and per-stage models are echoed at launch and journaled.

---

### 7.7 Policy composition — `marshal` configuration layer

**Description.** Today one policy file carries a hand-edited model tier, a hard-coded project slug, and a comment block describing which stories to flip before which batch. Marshal composes run policy from layered sources so the operating rules become configuration a machine enforces.

**Functional Requirements:**

#### FR-49: Layered policy composition
Effective run policy is composed from ordered layers with defined precedence.
**Consequences:**
- Layers: Marshal defaults → project policy → invocation flags, highest last.
- The composed policy is materialized into the loop home at init and echoed on request.
- Composition is pure: the same inputs produce the same output.

#### FR-50: Project-scoped policy without hand-editing
Project-specific values are supplied by the project layer, never by editing a shared file.
**Consequences:**
- The worktree-seed path list is generated from the active project, not literal.
- Verify commands, the **initial** frozen-surface set, the merge-subject form, and **the per-epic declared surface allowlist** come from the project layer. Freezes declared *during* a run accumulate through the run record, not through policy (architecture AD-26).
- *The per-epic surface is mandatory, and its absence is a registered finding naming the epic — never a default.* Architecture AD-27 computes the effective surface as `policy_surface ∩ spec_surface`, so the per-epic entry is what a story spec is intersected against; AD-17 forbids "everything except", so an epic with no entry yields `∅` (every story fails) or `unevaluable` (every story blocks). There is no benign default, which is exactly why a missing entry must be reported as a policy gap rather than silently bricking the epic. *(Added 2026-07-30, **F-18**: AD-27 and this FR were edited in the same pass, and this — the FR that enumerates what the project layer supplies — did not list the key AD-27 requires.)*
- Switching projects requires no edit to any shared file.

#### FR-51: Per-story model tiering
A story's declared difficulty selects the model tier without a between-batch config edit.
**Consequences:**
- Project policy maps a story difficulty class to per-stage models (dev, review, triage).
- Difficulty is read from the story's declaration; an undeclared story takes the mechanical default.
- The resolved per-stage model is journaled per story.
- Where the harness supports only run-level model selection, Marshal batches stories by tier and reports the batching. `[ASSUMPTION: batching is acceptable v1 behaviour; a per-story upstream key is an FR-58 request.]`
- *Motivating evidence: the live policy file carries a written "HARD-STORY BATCH PROCEDURE" naming which stories to flip and when.*

#### FR-52: Single harness seam
All interaction with the underlying orchestrator passes through one internal module.
**Consequences:**
- No other module invokes the harness binary or parses its output.
- The seam declares the harness version range it supports.
- An architectural test fails the build if the seam is bypassed.
- *Rationale: this is what makes §5.4's fork fallback a bounded change rather than a rewrite.*

#### FR-53: Policy validation
An invalid composed policy is rejected before launch.
**Consequences:**
- Unknown keys, unresolvable commands, and out-of-range values are reported with the layer that introduced them.
- Validation runs in preflight (FR-5).

#### FR-54: Configuration is inspectable
The operator can see the effective policy and where each value came from.
**Consequences:**
- Output shows each effective key with its winning layer.
- Secrets are redacted.

---

### 7.8 Packaging and distribution

**Description.** Marshal ships the way the rest of the crew ships.

**Functional Requirements:**

#### FR-55: Package identity and layout
Marshal ships as a Python distribution following the crew convention.
**Consequences:**
- Distribution `pyforge-marshal`, module `pyforge.marshal`, console script `marshal`.
- Source lives in the repo's shared packages workspace alongside its siblings.
- `import pyforge.marshal` succeeds from a clean environment install.

#### FR-56: Conda and wheel artifacts
Marshal is installable as a conda package and as a wheel.
**Consequences:**
- The conda recipe declares the harness as a run dependency, pinned to the supported version range (FR-52).
- Wheel and sdist build from the same source tree.
- Installing the conda package yields a working `marshal --help` and `marshal --version` with the harness resolvable.
- *This is the operative half of the §5 wrap decision: one install command yields the whole stack.*

#### FR-57: Version and capability reporting
`marshal --version` reports Marshal's version and the resolved harness version.
**Consequences:**
- Both versions appear in the journal for every run.
- A harness outside the supported range emits a prominent warning and is a blocking preflight finding when the mismatch is major.

#### FR-58: Upstream contribution register
Fixes that belong upstream are tracked as such rather than worked around indefinitely.
**Consequences:**
- A tracked register lists each upstream-shaped gap, its Marshal workaround, and its upstream status.
- Initial entries: idle-strand detection; per-story model tiering; `planning_artifacts` composition; ACP evaluation; ~~non-POSIX multiplexer support~~ *(landed upstream — v0.9.0 shipped a Windows psmux backend; entry closes as delivered, 2026-08-01)*.
- Each entry names the Marshal FR that compensates while the gap is open.

---

## 8. Non-Goals (Explicit)

- **Marshal does not reimplement the dev/verify/review/commit engine.** §5.
- **Marshal is not a skill.** It is deterministic harness; nothing in it is LLM-authored at runtime.
- **Marshal does not judge its own output.** Station verdicts stay independent — the hand that builds is not the gate that judges. Compliance verdicts belong to Warden; toolchain health to Doctor; provisioning to Steward; comms to Herald.
- **No hosted control plane, no telemetry to a remote host, no account.** Local-first.
- **No IDE extension, no chat participant, no marketplace artifact.** §6. *(Q-13 resolved 2026-07-31: exclusion retained. The enterprise-seam ask dissolved into existing seams — adapter profiles, the policy-declared tool surface, installer-materialized site policy — and this Non-Goal stands.)*
- **No HTTP proxy against any vendor's inference endpoint.** §6.
- **No sandbox or container implementation.** Worktree isolation is in scope; process and network isolation is Steward's provisioning territory. *A worktree isolates the filesystem and branch, not the process or network — this boundary is stated, not hidden.*
- **No PR-lifecycle automation beyond opening and updating a batch PR** — no CI watching, no auto-merge. (Q-3.) *(AMENDED 2026-07-31: Q-3 resolved — Marshal owns the PR lifecycle, per `docs/dreams/pr-lifecycle.md`. This non-goal narrows at the Spec's memlog-driven re-derivation; the line is annotated rather than deleted so the amendment stays visible.)*
- **No fleet-level resource budgeting across concurrent runs.** Per-run ceilings only. (Q-4.)
- **Marshal does not claim to be "the orchestrator."** It is the station around one. *(Q-14 resolved 2026-07-31: this Non-Goal stands with its scope clarified — it targets the engine claim. Marshal may sequence on verdicts it never authors; the route-verb surface belongs to the `spec-one-front-door` derivation.)*

---

## 9. MVP Scope

### 9.1 In Scope

- All four charter verbs (`init`, `factory spin`, `gate evaluate`, `deploy`) plus `status` and `adapters`.
- Loop-home provisioning, per-worktree project state, Tier-3 backlink, isolation verification, teardown.
- The supervisor: idle-strand detection, budget ceilings, escalation surfacing, run journal.
- Gate evaluation as a standalone object, with frozen-surface scope checks, doc-only classification, the autonomy-labelled gate-mode ladder, and **binding to the tracked spec's Success signal (FR-64, per the `docs/dreams/fidelity-enforcement.md` ruling)**.
- Automatic story-spec promotion; batch PR; merge-subject conformance; sprint and console feed refresh; **landing rules as policy + `marshal land` (FR-59/FR-60, per the 2026-07-31 CAP-9 ruling)**.
- Fleet status with ledger-versus-git reconciliation and a versioned machine-readable contract.
- **Bounded-loss durability and fleet-wide branch retirement (FR-61/FR-62/FR-63, per the `docs/dreams/durable-runs.md` ruling)**.
- Skill-tree projection, adapter probe, conformance smoke and matrix, entry-file drift detection.
- Layered policy composition with per-story model tiering and the single harness seam.
- Conda package and wheel; upstream contribution register.

### 9.2 Out of Scope for MVP

- Forking or vendoring the harness — deferred behind explicit triggers (§5.4).
- ACP as the adapter contract — deferred with a revisit trigger (Q-6). *`[NOTE FOR PM]` This is the most likely v2 headline; the seam in FR-52 is what keeps it cheap.*
- The VS Code extension and the `@bmad` chat adapter (§6).
- Windows-native operation — upstream-tracked (§6).
- Fleet-level resource budgets and formal L1–L5 story-mode labelling beyond the gate-mode mapping — Dream frontier.
- Sandbox/container isolation — Steward.
- OpenTelemetry `gen_ai.*` emission (Q-5). *Deferred on evidence: the conventions moved repositories in June 2026 and remain Development-stability with live attribute renames. The run journal (FR-18) carries the same information in a self-owned format.*

---

## 10. Cross-Cutting Non-Functional Requirements

- **NFR-1 — Determinism.** Every Marshal decision path is deterministic and LLM-free. Identical inputs produce identical outputs. No model call occurs anywhere in Marshal's own code.
- **NFR-2 — Offline by default.** Marshal performs no network access except where a wrapped operation inherently requires it (PR creation, the agent's own model calls). Network use is never silent.
- **NFR-3 — Never false-green.** Any state Marshal cannot verify is treated as failure, never as success. Unevaluable ≠ pass. *(Consistency with the crew's established compliance invariant.)*
- **NFR-4 — Supervisor independence.** The supervisor observes from outside the agent session and cannot be disabled, silenced, or misled by anything the session does. *Grounding: conversational safety instructions do not survive context compaction — confirmed independently by a vendor's own documentation and by a field incident.*
- **NFR-5 — Structural over conversational governance.** Every hard limit is expressed as configuration or a deterministic check, never as an instruction to the agent.
- **NFR-6 — No destructive default.** No Marshal operation deletes or force-updates tracked work without an explicit flag. Teardown refuses on unmerged work. Marshal never force-pushes.
- **NFR-7 — Idempotence.** `init`, `deploy`, `adapters sync`, and policy composition are idempotent; re-running after partial failure converges.
- **NFR-8 — Durable, self-owned evidence.** Journals, gate records, and the conformance matrix survive worktree teardown and do not depend on vendor retention or vendor transcript formats.
- **NFR-9 — Harness contract tests.** The observable surface Marshal depends on is covered by tests that run in CI and fail loudly on upstream drift rather than misparsing silently.
- **NFR-10 — Lean dependencies.** Marshal's own runtime dependencies are minimal and conda-forge-available; the harness is a package dependency, not a vendored tree.
- **NFR-11 — Secret hygiene.** No credential, token, or key is written to a journal, gate record, probe record, PR body, or commit. Probe and diagnostic output is redacted by construction.
- **NFR-12 — Machine-readable everything.** Every human-facing output has a machine-readable counterpart with a stable, versioned schema.
- **NFR-13 — Platform targets.** linux-64 and osx-arm64 for v1; Windows via WSL only, and stated as such rather than silently failing.
- **NFR-14 — Performance envelope.** Marshal's own overhead is negligible against run duration: `init` and `status` complete in seconds; the supervisor's steady-state cost is a low-frequency poll, and its poll interval is never longer than the active prompt-cache TTL. `[ASSUMPTION: init/status under 10s on a warm checkout; supervisor poll ≤ 60s.]` *Grounding: a polling interval longer than the cache TTL converts every cheap cache-read into a full cache-write — the documented mechanism behind the largest circulated cost overrun.*

---

## 11. Constraints and Guardrails

**Safety**
- **C-1.** Marshal never merges a story without a green verify and a passing scope check (FR-26).
- **C-2.** Escalations pause; they never resolve themselves.
- **C-3.** Marshal writes only within the loop home and the canonical Tier-3 store, plus the tracked planning artifacts it is explicitly asked to promote into. It never edits shared cross-project files.
- **C-4.** `main` is never checked out in a second working tree; loop merges publish by push or batch PR.
- **C-5.** Allowlist, never denylist, for any command surface Marshal governs. *Grounding: a major vendor deprecated its command denylist after four published bypasses and stated plainly that its permission file "is not a security boundary."*

**Cost**
- **C-6.** Every run has a ceiling. There is no unbounded mode. *Grounding: every verifiable runaway-cost incident traces to unbounded loops, absent real-time spend visibility, or a poll interval longer than the cache TTL.*
- **C-7.** Model tiering is expressed as policy, not as a hand edit: strong models where review misses ship false greens, cheap models for mechanical work.

**Operational**
- **C-8.** Marshal depends on an external harness; the supported version range is declared and enforced (FR-57).
- **C-9.** Marshal depends on BMAD Method artifact conventions for the story feed.
- **C-10.** A worktree is not a sandbox. Unattended runs on untrusted input require process and network isolation Marshal does not provide.

---

## 12. Success Metrics

**Primary**
- **SM-1 — Zero false greens.** No story reaches merged state without a green verify and passing scope check. Target: 100%. Validates FR-19, FR-22, FR-26.
- **SM-2 — No silent burn.** Every unattended run terminates in one of: completed, escalated, or stopped-with-named-reason. Target: 100%; specifically, zero idle-strand-to-cap events. Validates FR-12, FR-13.
- **SM-3 — Complete paper trail.** Share of merged stories whose spec is promoted into tracked artifacts without human action. Target: 100%. Validates FR-30.

**Secondary**
- **SM-4 — Escalation precision.** Share of escalations a reviewing human agrees were genuinely undecidable. Target: ≥80%. `[ASSUMPTION: 80% is a first target absent a baseline.]` Validates FR-15.
- **SM-5 — Concurrency.** Loop homes running simultaneously with isolation verification passing. Target: ≥4 sustained (current live evidence: 7 provisioned). Validates FR-1, FR-4.
- **SM-6 — Portability proven.** Adapters with a dated passing conformance smoke. Target: ≥2 by v1 close. Validates FR-44, FR-45.
- **SM-7 — Cost per merged story** is reported for every story. Target: reported 100% of the time where the adapter exposes usage. Validates FR-13.

**Counter-metrics (do not optimize)**
- **SM-C1 — Raw story throughput.** Counterbalances SM-2 and SM-5. Optimizing throughput reproduces the documented failure of autonomous agents spending days on impossible solutions.
- **SM-C2 — Adapter count.** Counterbalances SM-6. Two proven adapters beat six claimed ones; the category's most-starred project has ~290 stub tools.
- **SM-C3 — Escalation count reduction.** Counterbalances SM-4. Fewer escalations is only good if precision holds; driving the number down by widening what the agent guesses at is the failure this product exists to prevent.

---

## 13. Open Questions

1. **Q-1 — Wrap versus absorb.** **RESOLVED (§5): wrap and supervise.** Revisit triggers recorded in §5.4.
2. **Q-2 — Ownership of the AGENTS.md entry-file family.** `AGENTS.md` states the portable Dream→spec handoff is Herald's job; `docs/dreams/agent-portability.md` records portability as re-scoped to Marshal on 2026-07-23. One is stale. Marshal ships **detection only** (FR-46) until this is settled; it edits nothing.
3. **Q-3 — PR-lifecycle automation.** **RESOLVED (operator, 2026-07-31): Marshal owns it.** Input Dream: `docs/dreams/pr-lifecycle.md` — landing rules become a declared policy surface; `marshal land` performs the last mile and refuses like teardown; wrap-never-absorb unchanged. The §8 non-goal narrows at the Spec's memlog-driven re-derivation, not by hand-patch.
4. **Q-4 — Fleet-level resource budgets.** Per-run ceilings ship in v1; cross-run budgeting is deferred. Revisit when two projects routinely run heavy loops concurrently.
5. **Q-5 — OpenTelemetry `gen_ai.*` emission.** Deferred; the conventions moved repositories in June 2026 and remain Development-stability with live renames. Revisit when the conventions stabilize or an external consumer requires them.
6. **Q-6 — ACP migration trigger.** Proposed trigger: the upstream harness gains an ACP client path, **or** two adapters Marshal must support ship ACP-only, **or** ACP schema v2 reaches stable with the Claude adapter's known gaps closed. Until then, the harness's declarative profiles are the adapter contract.
7. **Q-7 — Idle threshold default.** 25 minutes is carried from the production stopgap. Needs one wave of data to confirm it does not false-positive on legitimately slow verify steps.
8. **Q-8 — Difficulty declaration source.** FR-51 reads story difficulty from the story's declaration; whether that lives in the story spec frontmatter or the epics document is an architecture-phase call.
9. **Q-9 — Conformance smoke story content.** What minimal story exercises spec→change→verify→commit while staying adapter-agnostic and cheap? Architecture phase.

**Q-10 … Q-14 added and resolved 2026-07-31 (architecture audit).** Five candidate capabilities were raised against this PRD, recorded as open questions rather than features, and resolved by operator ruling the same day. **Applied 2026-07-31/08-01:** the Spec re-render landed them as CAP-9, four constraints, and non-goal reaffirmations; this PRD carries the FR-level decomposition (FR-59/FR-60) and the §5.2/§7.2 re-scopes. None became an FR beyond what its decision states.

10. **Q-10 — Serialization of shared Tier-2 writes.** **RESOLVED: decomposed; no mutex engine.** Tracked Tier-2 files are per-worktree copies, serialized by git at the push/PR boundary; the real hazard is semantic lost-update through clean merges of *regenerated* artifacts. Rule: merge append-only inputs, re-derive regenerated outputs on main after landing (an Epic 4 deploy-ordering rule). The genuinely shared canonical Tier-3 store gets an advisory append lock. The journal's two-writer problem is the Spec's F-6, already carried.
11. **Q-11 — Tool-surface brokering.** **RESOLVED: yes, scoped.** The project's tool surface is declared in the project policy layer; `marshal init` renders a project-scoped `.mcp.json` into the loop home (the adapter-seed pattern); preflight probes resolvability. The user-scoped registry is never touched. Post-MVP, on the portability/adapter surface.
12. **Q-12 — Escalation knowledge capture.** **RESOLVED: pull model.** Marshal's half is one FR-17 consequence — the resume entry records a reference to the resolving decision. Scribe ingests from run journals; that story is Scribe's backlog. No station writes across the boundary.
13. **Q-13 — Enterprise plugin seam.** **RESOLVED: dissolved into existing seams; IDE exclusion retained.** Internal MCP servers → the Q-11 tool surface; proprietary/third-party agent CLIs → FR-52 adapter profiles; design bridges → Herald; internal skills → FR-45 projection. Site-wide policy vs the no-fourth-layer constraint resolves at install time — genesis-installer materializes site config into the Marshal-defaults layer, keeping runtime composition three layers and pure. No plugin-registry subsystem.
14. **Q-14 — Does Marshal enforce inter-station order?** **RESOLVED (operator, 2026-07-31): Marshal sequences on verdicts it never authors.** Gating reads each station's durable, schema-validated verdict artifact, pinned to the tree revision it judged; Marshal never runs the judge. This *clarifies* the two §8 Non-Goals rather than striking them — "not 'the orchestrator'" targets the engine claim and stands; "verdicts stay independent" bars authorship, not consumption. Verdict reads remove most of the cross-environment invocation-port need; the route-verb surface is the queued `spec-one-front-door` derivation's contract.

---

## 14. Assumptions Index

- **§7.2 FR-12** — idle threshold defaults to 25 minutes, carried from the production stopgap that worked.
- **§7.7 FR-51** — where the harness supports only run-level model selection, tier-batching is acceptable v1 behaviour; a per-story key is an upstream request.
- **§10 NFR-14** — `init`/`status` under 10 seconds warm; supervisor poll ≤ 60 seconds.
- **§12 SM-4** — 80% escalation precision as a first target absent a baseline.
- **Brief A1** — the reference customer is this factory and its operator; no external customer discovery was performed.
- **Brief A2** — the upstream harness remains actively maintained. Mitigated by §5.4 fork triggers.
- **Brief A3** — BMAD Method artifact conventions remain the story-feed contract.
- **Brief A4** — linux-64 and osx-arm64 hosts for v1; Windows via WSL.
- **Brief A5** — the local conda channel is acceptable for v1 distribution; the harness is packaged here but not yet on conda-forge.
- **Brief A6** — flat `planning-artifacts/` output per repo convention, rather than a run-folder workspace with a memlog; input provenance lives in frontmatter.

---

```json
{
  "status": "partial",
  "intent": "create",
  "prd": "_bmad-output/projects/pyforge-marshal/planning-artifacts/prd.md",
  "decisions": [
    "Q-1 RESOLVED: Option A (wrap + supervise) — bmad-loop already conda-packaged so absorbing buys nothing on distribution; all 9 known gaps sit outside the dev/verify/review/commit engine; doctrine already routes upstream fixes upstream; upstream velocity 0.8.1->0.9.0 delivered the whole portability surface; fork triggers + single-seam constraint (FR-52) preserve the escape hatch",
    "Agent-portability fold: v1 = skill-tree projection, adapter probe/conformance matrix, project-scoped adapter+model policy, entry-file drift detection, per-adapter first-run acknowledgement. SUPERSEDED = copilot-api HTTP bridge. DEFERRED = VS Code extension, @bmad chat adapter (re-owned), ACP adapter contract, Windows-native"
  ],
  "open_questions": [
    "Q-2 AGENTS.md family ownership (Herald vs Marshal) — detection-only until settled",
    "Q-3 RESOLVED 2026-07-31: Marshal owns the PR lifecycle (docs/dreams/pr-lifecycle.md); non-goal narrows at Spec re-derivation",
    "Q-4 fleet-level resource budgets",
    "Q-5 OTel gen_ai.* emission",
    "Q-6 ACP migration trigger",
    "Q-7 idle threshold default validation",
    "Q-8 story difficulty declaration source",
    "Q-9 conformance smoke story content",
    "Q-10 RESOLVED 2026-07-31: Tier-2 writes decomposed — merge append-only inputs, re-derive outputs on main; Tier-3 append lock; F-6 carries the journal",
    "Q-11 RESOLVED 2026-07-31: tool surface policy-declared, .mcp.json rendered into the loop home; user registry untouched",
    "Q-12 RESOLVED 2026-07-31: pull model — FR-17 resume records the resolution reference; Scribe ingests from journals",
    "Q-13 RESOLVED 2026-07-31: seam dissolved into adapter profiles + tool surface + installer-materialized site policy; IDE exclusion retained",
    "Q-14 RESOLVED 2026-07-31: Marshal sequences on verdicts it never authors; non-goals clarified, not struck; route verbs -> spec-one-front-door"
  ],
  "assumptions": [
    "FR-12 idle default 25 min",
    "FR-51 tier-batching acceptable where harness is run-level only",
    "NFR-14 init/status <10s; supervisor poll <=60s",
    "SM-4 80% escalation precision first target",
    "brief A1-A6 carried forward"
  ],
  "counts": {"features": 8, "frs": 60, "nfrs": 14, "constraints": 10, "success_metrics": 10}
}
```
