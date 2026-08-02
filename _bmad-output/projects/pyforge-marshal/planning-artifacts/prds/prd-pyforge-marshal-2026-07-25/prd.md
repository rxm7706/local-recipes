---
title: Marshal (pyforge-marshal)
status: final
created: 2026-07-25
updated: 2026-08-02  # genesis-installer PRD (FR1-FR62, own numbering) consolidated in as a Satellite section (explicit user override); CAP-9 -> FR-59/FR-60; competitive re-frame; FR-13 re-scope; FR-58 psmux; convergence watch; Q-3/Q-10..14 resolutions; durable-runs -> FR-61/FR-62/FR-63; fidelity-enforcement (Marshal-only slice) -> FR-64; one-front-door -> FR-65, Q-15/Q-16
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

#### FR-65: The detector registry as a verb — `marshal check` *(added 2026-08-01 — `docs/dreams/one-front-door.md`, CAP-3/CAP-5)*
`marshal check` reaches the repo's detector registry through the same front door as every other verb, and every routed call — `check` included — carries its project/loop-home/policy/story context from one resolution rather than each tool re-deriving it.
**Consequences:**
- `marshal check` invokes `scripts/detectors.py`'s derived registry and returns the same findings as the standalone pixi task — a route, not a reimplementation (wrap-never-absorb applies to detector tooling exactly as it does to the engine).
- `marshal status`'s fleet view (FR-36) may surface a summarized detector-registry state per row; the detailed findings remain `check`'s own output, not duplicated into `status`.
- Context (active project, loop home, composed policy, in-scope story) resolves once per `marshal` invocation and threads to whichever verb is routed to — `run` (`factory spin`), `status`, `check`, and `land` alike — rather than each accepting it as a separately-supplied argument.
- *Non-goal carried from the source Dream: this FR does not decide the final verb names for `run`/`status`/`land` (Q-15), and does not resolve which of the 51 `bmad-*` skills Marshal may route to versus must never contain (Q-16) — both stay open, named rather than invented.*

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
- **`marshal check` — the detector registry through the front door, with context resolved once per invocation (FR-65, per the `docs/dreams/one-front-door.md` ruling)**.
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
14. **Q-14 — Does Marshal enforce inter-station order?** **RESOLVED (operator, 2026-07-31): Marshal sequences on verdicts it never authors.** Gating reads each station's durable, schema-validated verdict artifact, pinned to the tree revision it judged; Marshal never runs the judge. This *clarifies* the two §8 Non-Goals rather than striking them — "not 'the orchestrator'" targets the engine claim and stands; "verdicts stay independent" bars authorship, not consumption. Verdict reads remove most of the cross-environment invocation-port need; the route-verb surface was the then-queued `spec-one-front-door` derivation's contract — **that Spec landed 2026-08-01** (see Q-15/Q-16 below for what it left open).

**Q-15/Q-16 added 2026-08-01, carried from `spec-one-front-door`'s own two live open questions rather than resolved by invention.**

15. **Q-15 — Exact verb surface beyond `check`.** `spec-one-front-door` names `run`/`status`/`check`/`land`/`switch`(shipped)/`homes`(shipped) as candidates it explicitly says to argue with, not a decided list. FR-65 below builds `check` (net-new); `run`/`status`/`land` already exist as `factory spin`/`status`/`land` (FR-9..11, FR-36, FR-59/60) and this PRD does not rename them pending an operator call on whether the shorter forms are worth the churn.
16. **Q-16 — Route-versus-contain boundary, per `bmad-*` skill.** Context supplied once (the front door's stated value) does not by itself say where "supplying context" ends and "containing a skill's logic" begins, across the 51 `bmad-*` skills Marshal routes to. Precedent sets per skill as routing is implemented; FR-65's `marshal check` is the first concrete site this will be tested against.

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


---

## Satellite: Genesis Installer PRD

**Consolidated 2026-08-02 — see
`archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-genesis-installer-2026-07-25/prd.md`
for the original standalone document.** The section below is the genesis-installer PRD,
folded into this single Marshal-station PRD verbatim, per explicit user override of the
"kept separate on purpose" decision recorded in `docs/dreams/pyforge-marshal.md` /
`docs/dreams/genesis-installer.md`. Nothing in Marshal's own PRD above this line was changed.

**Numbering — read this before citing an FR below.** This satellite section's requirement
IDs (`FR1`, `FR2`, … `FR62`, `NFR-R1`, `NFR-A1`, `NFR-P1`, `NFR-C1`, `NFR-S1`, `NFR-M1`,
`NFR-O1`, `SC-01`…`SC-10`, `OQ-1`…`OQ-9`) are **genesis-installer's own, pre-existing
numbering scheme** — no dash after "FR" — and are **NOT** part of, and are **never
renumbered into**, Marshal's own `FR-1`..`FR-65` / `NFR-1`..`NFR-14` sequence above (which
uses a dash). The two ranges are distinct namespaces belonging to two different
sub-products inside one station; a bare "FR62" always means this satellite section, a bare
"FR-62" (with dash) does not exist in either range (Marshal's own range stops at FR-65,
genesis-installer's at FR62 with no dash) and should be read as a typo for one or the other
if ever encountered.

**Original frontmatter** (`prds/prd-genesis-installer-2026-07-25/prd.md`):

```yaml
title: "Product Requirements Document — pyforge-genesis (Genesis)"
status: "final"
created: "2026-07-25"
updated: 2026-08-01
project_slug: "pyforge-genesis"
currency_review: Reviewed 2026-08-04 — spec/brief timestamp bump was structural (project relocation / memlog story-completion recording), not content drift; PRD unchanged.
dream: "docs/dreams/pyforge-genesis.md"
inputs:
  - "planning-artifacts/product-brief-pyforge-genesis.md"
  - "planning-artifacts/research/domain-research-scaffolder-landscape.md"
  - "planning-artifacts/research/technical-research-installer-implementation.md"
  - "{project-root}/docs/dreams/pyforge-genesis.md"
  - "{project-root}/docs/dreams/ecosystem-crew.md"
  - "{project-root}/docs/dreams/README.md"
  - "{project-root}/AGENTS.md"
  - "{project-root}/CLAUDE.md"
  - "{project-root}/_bmad-output/PROJECTS.md"
  - "{project-root}/archive/docs/bmad-setup-plan.md"
  - "{project-root}/scripts/bmad-switch, scripts/bmad-loop-worktree, scripts/bmad_drift_check.py"
distribution:
  dist: "pyforge-genesis"
  module: "pyforge.genesis"
  cli: "genesis"
```

**Product Requirements Document — pyforge-genesis (Genesis)**

### Executive Summary

Genesis packages this repository's proven operating model as an installable tool with
two verbs — **`genesis init`** (greenfield: a new repository born Dream-first) and
**`genesis adopt`** (brownfield: layer the model onto an existing repo without disturbing
what runs) — plus the two verbs that make an install *stay* correct: **`genesis check`**
(read-only conformance, non-zero exit, CI-runnable) and **`genesis update`** (take a later
model version via a reviewable plan and version-ordered migrations).

This PRD resolves the two questions the Dream and the brief left open:

1. **The extraction question** — § *The Extraction Manifest* gives the concrete
   per-artifact classification. The Dream's three-way split (copied / referenced /
   generated) is **one class short**: "copied" divides into **MANAGED** (tool-owned,
   regenerated on update) and **SEEDED** (written once, repo-owned forever). That
   distinction is exactly what decides whether a model upgrade may rewrite a file, so it
   is load-bearing rather than pedantic.
2. **The Genesis ↔ Marshal boundary** — § *Boundaries*. **Genesis installs the machinery;
   Marshal operates it.** Genesis's write scope is a repo's structure and conventions;
   Marshal's is a repo's executions.

Genesis wraps Copier (v9.17.0 on conda-forge, `noarch: python`, MIT — no new recipe) for
file materialization, versioned updates, and migrations, and builds four things Copier has
no concept of: the model content, the brownfield inventory/plan, marker-delimited managed
regions inside repo-owned files, and conformance checking.

---

### Success Criteria

#### Primary success criterion (the master switch)

**SC-01.** A second repository created by `genesis init` runs a full Dream → spec → epics →
loop-driven build, and later **takes a model upgrade via `genesis update` with no hand
edits** — `genesis check` green before and after.

#### Supporting metrics (all mechanically testable)

| ID | Criterion | Measured by |
|---|---|---|
| SC-02 | `genesis adopt --dry-run` against `local-recipes` at the shipped model version produces an **empty plan** | the reference-oracle test |
| SC-03 | `genesis adopt` is idempotent — second run ⇒ empty plan, zero files changed | integration test |
| SC-04 | `genesis adopt` on a hand-edited managed region **refuses and reports**; does not overwrite | integration test |
| SC-05 | `genesis adopt --apply` on a dirty git worktree refuses | integration test |
| SC-06 | `genesis init` + `genesis check` green **offline, zero network calls** | egress-counter test (warden's established pattern) |
| SC-07 | A simulated breaking model change (model v1 → v2) is absorbed by a migration in an installed repo with no manual edits | migration integration test |
| SC-08 | `genesis update` **cannot** write to `docs/dreams/**` or `**/planning-artifacts/**` | write-scope guard test |
| SC-09 | `genesis init` to a working Dream-first repo in **< 5 minutes** wall-clock (vs. the 10-phase manual setup plan) | timed smoke test |
| SC-10 | 100% of model artifacts in the manifest are classified; no artifact is unclassified | manifest-coverage test (mirrors `bmad_drift_check.py`'s `uncovered` HARD finding) |

#### Counter-metrics (watch for success that is actually failure)

| ID | Counter-metric | Why it matters |
|---|---|---|
| CM-01 | Number of manifest entries in the **SEEDED** class that adopters later hand-edit back toward the model | high count means the class was assigned wrong — those artifacts should be MANAGED |
| CM-02 | Number of `skips[]` entries adopters accumulate | a growing skip list means the model is being rejected in practice |
| CM-03 | Migrations authored per model minor version | if every minor needs a migration, the model surface is too volatile to install |

#### Kill criteria

Genesis pauses or rescopes if, at V1 completion:

- **K-01** — the managed-region merge proves unreliable on real files (corruption or
  unresolvable conflicts in either of the first two adopters);
- **K-02** — SC-02 (the empty-plan oracle against `local-recipes`) cannot be reached
  without special-casing the model into incoherence — meaning the model is not actually
  extractable and the Dream's stabilization gate was called too early;
- **K-03** — CM-03 shows migrations cost more than hand-editing each installed repo would.

---

### User Journeys

#### J1 — "Start a new pyforge sibling, Dream-first from day zero"

A maintainer is spinning `pyforge-scribe` out of the monorepo into its own repository. He
runs `genesis init ../pyforge-scribe --slug pyforge-scribe --agents claude,cursor`. Genesis
materializes `docs/dreams/` (README, frontmatter contract, one seed Dream stub named for
the slug), the tier layout with its gitignore rules, `AGENTS.md` carrying the portability
contract, `CLAUDE.md` and `.cursor/rules/specs.mdc` generated from that contract, the BMAD
multi-project subtree with `PROJECTS.md` and its first row, `scripts/bmad-switch`, and the
drift detector wired into CI. He writes the Dream, runs `bmad-spec`, and the loop starts.
Total elapsed before the first Dream: under five minutes, versus reading ten phases of a
562-line plan.

#### J2 — "Adopt the model into a repo that already ships"

A team has a working data-platform monorepo — CI, releases, an existing `CLAUDE.md`, and a
`docs/adr/` convention they like. They run `genesis adopt` (dry-run by default). Genesis
prints a plan: 9 artifacts absent (will create), 3 present-conformant (skip), 1
present-divergent (`CLAUDE.md` — will insert a managed region at an anchor, leaving all
existing content), 1 present-legacy (`docs/adr/` — recorded, preserved, untouched). Nothing
has been written. They review the plan in a PR, run `genesis adopt --apply`, and their
build still works because Genesis never touched a file it did not name.

#### J3 — "Take a model upgrade six weeks later"

The model ships v1.3.0: the durable-story-specs convention adds a `planning-artifacts/specs/`
rule to the tier table, and `bmad-switch` gains an atomicity fix. An installed repo runs
`genesis check` in CI, which fails with `model-behind: repo at 1.2.0, available 1.3.0`. The
maintainer runs `genesis update` — a plan is written naming two migrations and three files.
He reviews it, runs `genesis update --run`. The tiers managed region in `AGENTS.md` is
replaced; `scripts/bmad-switch` is regenerated wholesale; the derived adapters are
recomputed. His Dreams, PRDs, and epics are untouched — structurally unreachable from the
update path. `genesis check` is green.

#### J4 — "The model and the repo disagree"

An engineer hand-edits the tiers block inside `AGENTS.md` because a rule did not fit. Next
CI run, `genesis check` reports `managed-region-modified: AGENTS.md#tiers (hash mismatch)`
and exits non-zero. He has three sanctioned moves: revert; delete the markers (a deliberate,
greppable opt-out that Genesis records and thereafter respects); or add the path to
`skips[]`. What he cannot do is diverge silently — which is the entire point, because the
agents reading that file would otherwise follow a rule the model does not have.

#### J5 — "Verify the model is still extractable"

A CFE retro lands a convention change directly in `local-recipes` (out-of-band, as always
happens). CI runs `genesis adopt --dry-run` against the repo itself. The plan is non-empty:
the model in the package no longer matches the repo it was extracted from. That is the
signal to update the Genesis templates — the drift is caught the day it appears rather than
at the next install.

---

### Domain Requirements

#### D1 — The model is read by agents, not only humans

Every artifact Genesis installs is consumed by autonomous agents (Claude Code, Cursor,
Copilot, Gemini, BMAD skills, bmad-loop). Consequences that shape requirements throughout:
staleness is a **behavioral bug**, not documentation debt; "correctness of an install" must
be **machine-verifiable** (files present, markers intact, hashes matching, detector green)
rather than a matter of taste; and any ambiguity in a convention becomes divergent agent
behavior.

#### D2 — Air-gapped operation is a standing constraint

`docs/dreams/enterprise-airgap.md` is `realized`; `pyforge-warden`'s packaging states
engines are "never curl-fetched at runtime." Genesis inherits this: engine as conda
package, templates in-package, zero egress on `init` / `adopt` / `check`.

#### D3 — This repo's PR CI gates apply to Genesis's own development

Per `CLAUDE.md`: any change outside `recipes/` requires the `maintenance` label on the PR,
and any `pixi.toml` change requires a regenerated committed `environment.yaml`
(ungated by the label). Genesis adds a pixi feature + environment, so both gates fire.
`pixi run -e local-recipes llms-full-check` will additionally flag
`docs/reference/library-llms-full.md` as stale — that catalog's scaffolding section
currently recommends "cookiecutter (+ cruft to stay synced)" and must be updated.

#### D4 — Tier discipline binds Genesis itself

Genesis's own planning artifacts are Tier 2; its story specs are durable and tracked under
`planning-artifacts/specs/` per the 2026-07-25 convention; nothing it produces may be
git-tracked under `implementation-artifacts/`.

#### D5 — Not a conda-forge recipe effort

Genesis consumes `copier` from the existing conda-forge feedstock (consume-not-submit,
CFE G58). No new recipe is authored, so the CFE Rule-1 invocation and Rule-2 retro are
**not** triggered by the core work. They *are* triggered if a story adds a recipe under
`recipes/` (none is planned in V1).

---

### The Extraction Manifest

**This section resolves the Dream's central question.** It is the normative contract that
FR1–FR6 encode and SC-10 tests.

#### The classification rule

> Classify each artifact by **who must be able to change it** and **how an installed repo
> takes a later model upgrade for it.**

| Class | Definition | Behavior on `genesis update` | Behavior on hand-edit |
|---|---|---|---|
| **REFERENCED** | Not materialized. The repo depends on it by version range; it lives upstream. | nothing in the repo changes | n/a |
| **COPIED · MANAGED** | Materialized, **tool-owned**. The repo should not hand-edit it. | regenerated wholesale | `check` reports; `update` refuses without `--force` |
| **COPIED · SEEDED** | Materialized once as a starting point, then **repo-owned forever**. | never touched | expected and fine |
| **GENERATED · DERIVED** | Computed from the neutral contract and/or repo state. | recomputed every run (idempotent) | overwritten on next run; `check` reports |
| **HYBRID · MANAGED REGION** | A repo-owned file containing a tool-owned, marker-delimited span. | only the span is replaced | `check` reports hash mismatch on the span only |

#### The V1 manifest

Derived from a live inventory of the model surface in `local-recipes` (2026-07-25).

##### REFERENCED

| Artifact | Pin | Rationale |
|---|---|---|
| `bmad-method` | `>=6.10.0` (conda-forge) | upstream product; gains `bmad-dev-auto` at 6.10; never vendored |
| `bmad-loop` | `>=0.8.1` (conda-forge) | Marshal's orchestrator; Genesis declares the floor, Marshal operates it |
| `copier` | `>=9.17,<10` (conda-forge) | Genesis's own engine |
| `pixi` | `>=0.72.2` | `preview = ["pixi-build"]` requires it |
| `tmux` | `>=3.7b` | loop spawns agent sessions in it; Linux/macOS only |
| Installed BMAD skills (`_bmad/bmm/**`, `_bmad/core/**`) | installer-owned | regenerated by `bmad-method install`; Genesis must never write here |

Genesis **verifies presence and floor** for these (FR30) and never installs them.

##### COPIED · MANAGED

| Artifact | Why managed |
|---|---|
| `scripts/bmad-switch` | executable model machinery with a known production incident (the 10-hour marker/symlink desync); bug fixes **must** propagate to installed repos |
| `scripts/bmad-loop-worktree` | concurrent loop homes; same reasoning |
| `scripts/bmad_drift_check.py` (the detector) | must run locally, offline, in the adopting repo's CI; this is the conformance engine and it evolves with the model |
| `docs/dreams/README.md` | the Tier-0 contract itself — the Dream frontmatter schema, the flow diagram, the conventions |
| The model's own rule text (tier tables, portability contract) | delivered *into* hybrid files, not as standalone files — see HYBRID |
| CI workflow that runs `genesis check` + the detector | mechanical; no reason for a repo to own it |
| `.gitignore` model block | the tier rules made executable (`_bmad-output/projects/*/implementation-artifacts/`, the two symlinks, `_bmad/custom/.active-project`, `.bmad-loop/runs/`) — delivered as a managed region in a repo-owned `.gitignore` |

##### COPIED · SEEDED

| Artifact | Why seeded |
|---|---|
| A starter Dream at `docs/dreams/<slug>.md` | it is the repo's content from the moment it is written |
| `_bmad-output/projects/<slug>/.bmad-config.toml` | per-project config the team tunes |
| `_bmad/custom/config.toml` (global custom layer) | exists precisely so teams customize it |
| `.bmad-loop/policy.toml` | per-project verify gates and worktree seeds — necessarily repo-specific (the origin document devotes Phase 9.3 to this) |
| `planning-artifacts/specs/README.md` | the durable-specs convention explainer; the repo will extend it with its own provenance table |
| Deck-family scaffolding under `presentations/<slug>/` | Herald's surface; Genesis lays the directory, Herald owns the content |

##### GENERATED · DERIVED

| Artifact | Derived from |
|---|---|
| `CLAUDE.md` (the Dream-first / tiers head matter) | the neutral contract + selected agents |
| `.cursor/rules/specs.mdc` | the neutral contract (verified: it is a mechanical projection of `AGENTS.md`'s tier table) |
| `GEMINI.md` | same |
| `.github/copilot-instructions.md` | same |
| `_bmad-output/PROJECTS.md` § *Projects* table rows | the set of `_bmad-output/projects/*/.bmad-config.toml` files present |
| The `_bmad-output/{planning,implementation}-artifacts` symlinks | the active-project marker (already generated by `bmad-switch`; Genesis ensures they exist and are gitignored) |
| Directory skeletons (`docs/dreams/`, `docs/specs/` only when legacy, project subtrees) | the manifest + slug |

The four agent-adapter files are the clearest case for DERIVED: all three inspected
(`GEMINI.md`, `.cursor/rules/specs.mdc`, `.github/copilot-instructions.md`) restate the
same tier table with per-tool framing. Maintaining them as four independent copies is how
they drift; generating them from one contract is how they cannot.

##### HYBRID · MANAGED REGION

| File | Region(s) | Rationale |
|---|---|---|
| `AGENTS.md` | `tiers`, `portability-contract`, `dream-first-workflow` | the neutral contract must upgrade; the rest of the file is the repo's own (tool-discovery table, local pointers) |
| `CLAUDE.md` | `tiers`, `bmad-multiproject` | in `local-recipes` this file is 230 lines of repo-specific guidance around a small model core; the model core must upgrade, the rest must never be touched |
| `.gitignore` | `model-ignores` | the tier rules in executable form, inside a file every repo owns |
| `README.md` (optional) | `model-badge` | opt-in; off by default |

#### What Genesis must NEVER write (the structural guarantee)

| Path | Why |
|---|---|
| `docs/dreams/*.md` (except the one seed at `init`) | Tier 0 is the team's aspiration |
| `**/planning-artifacts/**` (except the seeded `specs/README.md` at `init`) | Tier 2 is the team's spec and planning work |
| `**/implementation-artifacts/**` | Tier 3, gitignored, runtime scratch |
| `docs/specs/*.md` | legacy tier — preserve and mark, never edit |
| `_bmad/bmm/**`, `_bmad/core/**` | installer-owned; regenerated by BMAD |

Enforced by code and proven by test (FR35, SC-08), not by convention. This is the
structural expression of the field's hardest-won lesson — spec-kit's guidance to *"keep
tooling updates separate from feature artifact evolution."*

#### Deliberately deferred to V1.x

`.claude/skills/**` (skill content), `pixi.toml` task blocks, and
`docs/reference/library-llms-full.md` are model-adjacent but too repo-specific to classify
confidently at V1. They are recorded as `unclassified-deferred` in the manifest, and
SC-10's coverage test treats that as an explicit, enumerated state rather than a gap.

---

### Boundaries

#### Genesis ↔ Marshal (the resolution)

**Genesis installs the machinery; Marshal operates it.**

| | Genesis | Marshal |
|---|---|---|
| Write scope | a repo's **structure and conventions** | a repo's **executions** |
| Owns | the tier layout, AGENTS.md family, BMAD multi-project wiring, the deck-family skeleton, the conformance detector | bmad-loop runs, gates, escalation, graduated autonomy, worktree lifecycle, project switching **at run time** |
| Lifecycle | install-time and upgrade-time | run-time |
| `init` semantics | `genesis init` creates **the repository** the specs will live in | `marshal init --spec …` initializes **a build** from a spec |
| `scripts/bmad-switch`, `scripts/bmad-loop-worktree` | **delivers** them (MANAGED class) and keeps them current | **runs** them; owns their behavior and evolution |
| `.bmad-loop/policy.toml` | **seeds** it | **owns and rewrites** it per project |

The overlap point is real and named: the two scripts are Marshal's per the 2026-07-23
ownership review, but they must be *installed* to exist in a new repo at all. Resolution:
**Marshal owns the source; Genesis owns the delivery.** A change to `bmad-switch` lands in
Marshal's tree and is picked up by Genesis's manifest at the next model version. Genesis
never forks them.

#### Genesis ↔ Doctor

`genesis check` asks *"does this repo conform to the model?"*; `doctor check` asks *"is this
machine able to run the factory?"* Genesis's REFERENCED-dependency verification (FR30)
overlaps Doctor's pre-flight charter, so: **Genesis performs a minimal presence-and-floor
probe with no dependency on Doctor** (it must work in a repo that has not adopted Doctor),
and **delegates to `doctor check` when it is available**, reporting Doctor's findings
rather than duplicating them.

#### Genesis ↔ Herald

Genesis lays down `presentations/<slug>/` and the deck-family conventions (SEEDED); Herald
fills, seeds to Design, and pulls back. Genesis never touches deck content.

---

### Project Scoping

#### Strategy

Build the **update path first**, not the install path. Every tool in the surveyed field
that failed, failed at update; `init` on top of Copier is close to free once the manifest
and the managed-region engine exist. The `local-recipes` empty-plan oracle (SC-02) is
available from the first week and is the highest-signal test in the project — it should
gate every epic, not just the last.

#### V1 feature set

1. **Manifest + classification engine** — the model declared as data, with the five classes
   and complete coverage.
2. **Managed-region engine** — marker parse, span replace, content hash. The riskiest
   bespoke component; independently testable; built early.
3. **`genesis adopt`** — detect → plan → confirm → apply, dry-run default, idempotent,
   `present-legacy` aware.
4. **`genesis check`** — read-only, non-zero exit, CI-shaped output.
5. **`genesis init`** — greenfield, on the same engine as adopt.
6. **`genesis update`** + migration runner — two-phase plan/apply, version-ordered,
   applied-once, write-scope guarded.
7. **State file** — schema-validated, tool-owned, do-not-edit.
8. **Agent adapter fan-out** — Claude Code, Cursor, Copilot, Gemini generated from the
   neutral contract.
9. **Packaging** — pixi workspace member, in-package templates, lean env, offline proof.

#### Explicitly out of scope for V1

Hosted registry of installations · repository creation on a git host (`init` makes a tree,
not a GitHub repo) · non-git targets · composable feature modules (adopt a subset) ·
`check --fix` · fleet conformance scorecards · publishing the model as a separately
versioned artifact.

---

### Functional Requirements

#### Model manifest & classification

- **FR1** — The model is declared as **data** (a manifest file inside the package), not as
  code branches. Each entry carries: path or path-pattern, class, applicable model-version
  range, and (for HYBRID) its region names and anchors.
- **FR2** — Five classes are supported: `referenced`, `copied-managed`, `copied-seeded`,
  `generated-derived`, `hybrid-managed-region`.
- **FR3** — The manifest supports an explicit `unclassified-deferred` state so that
  deferral is enumerated rather than silent.
- **FR4** — A coverage check verifies that every artifact Genesis knows about carries
  exactly one class; an unclassified artifact is a HARD failure. (Mirrors
  `bmad_drift_check.py`'s `uncovered` finding.)
- **FR5** — The manifest is versioned by **model semver**, independent of the
  `pyforge-genesis` package version. Both are recorded in installed state.
- **FR6** — The manifest declares the **never-write path set** (§ *The Extraction
  Manifest*), which the apply and update paths enforce.

#### `genesis init` (greenfield)

- **FR7** — `genesis init <path>` creates a Dream-first repository tree at `<path>`,
  materializing every manifest artifact applicable to a new repo.
- **FR8** — `init` accepts `--slug` (the first BMAD project slug, defaulting to the
  directory name) and `--agents` (comma-separated adapter selection).
- **FR9** — `init` seeds exactly one Dream stub at `docs/dreams/<slug>.md` conforming to
  the Tier-0 frontmatter contract (`title`, `type: dream`, `owner`, `status: seeded`).
- **FR10** — `init` creates the BMAD multi-project subtree:
  `_bmad-output/projects/<slug>/{planning-artifacts,implementation-artifacts}`,
  `.bmad-config.toml`, `planning-artifacts/specs/README.md`, and `PROJECTS.md` with the
  first row.
- **FR11** — `init` writes the `.gitignore` model region covering the tier rules: the
  gitignored `implementation-artifacts/`, the two `_bmad-output` compatibility symlinks,
  `_bmad/custom/.active-project`, `.bmad-loop/runs/` and `cache/`, and
  `_bmad-output/projects/*/.bmad-config.user.toml`.
- **FR12** — `init` writes the state file recording `mode: init`, model version, CLI
  version, selected agents, and the per-artifact hashes.
- **FR13** — `init` refuses to run into a non-empty directory unless `--force`; the
  documented path for an existing repo is `adopt`.

#### `genesis adopt` (brownfield)

- **FR14** — `genesis adopt` runs **detect → plan → confirm → apply** and is **dry-run by
  default**; `--apply` (or `--yes` for unattended use) executes.
- **FR15** — Detect classifies each manifest artifact in the target repo as `absent`,
  `present-conformant`, `present-divergent`, or `present-legacy`.
- **FR16** — `present-legacy` artifacts are **recorded and preserved, never modified or
  deleted**, and are listed in the state file's `legacy[]`.
- **FR17** — The plan is a **machine-readable artifact** written to disk (not only printed),
  listing per artifact: path, class, detected state, proposed action, and rationale.
- **FR18** — Apply materializes only what the plan names. Artifacts already present are
  preserved unless their class is `copied-managed` or `generated-derived`.
- **FR19** — `adopt` is **idempotent**: a second run on an unchanged repo produces an empty
  plan and writes nothing.
- **FR20** — `adopt --apply` refuses on a dirty git worktree, and refuses outside a git
  repository.
- **FR21** — `adopt` refuses (with a specific, actionable message) when a managed region or
  managed file has been hand-modified, unless `--force`.
- **FR22** — `adopt` accepts `--skip <glob>` (recorded in state) and honors previously
  recorded skips on subsequent runs.

#### `genesis check` (conformance)

- **FR23** — `genesis check` is **read-only** and never writes to the repo (state file
  included).
- **FR24** — `check` exits non-zero on any HARD finding; `--strict` additionally fails on
  DRIFT findings.
- **FR25** — Findings are typed and stable, at minimum: `artifact-missing`,
  `managed-file-modified`, `managed-region-modified`, `managed-region-missing`,
  `derived-stale`, `model-behind`, `state-invalid`, `never-write-violation`,
  `referenced-dep-missing`.
- **FR26** — `check --json` emits a machine-readable report suitable for CI annotation.
- **FR27** — `check` reports the repo's model version against the model version available
  in the installed package (`model-behind` / current / ahead).
- **FR28** — `check` runs offline and completes in under 5 seconds on a repo the size of
  `local-recipes`.

#### `genesis update` + migrations

- **FR29** — `genesis update` is **two-phase**: the default invocation writes a plan and
  changes nothing; `--run` applies the plan.
- **FR30** — Update verifies REFERENCED dependencies against their declared floors and
  reports (does not install) anything missing or below floor; delegates to `doctor check`
  when available.
- **FR31** — Migrations are ordered by model semver, applied **exactly once**, and recorded
  in state's `migrations_applied[]`.
- **FR32** — Migrations may only touch `copied-managed`, `generated-derived`, and
  `hybrid-managed-region` artifacts. Touching `copied-seeded` requires an explicit
  interactive/`--yes` opt-in and is reported as an offer, never imposed.
- **FR33** — Update regenerates `copied-managed` files wholesale and recomputes
  `generated-derived` files, after hash-guard checks pass.
- **FR34** — Update replaces only the marked span of `hybrid-managed-region` files.
- **FR35** — Update **cannot** write to any path in the never-write set (FR6); an attempt is
  a hard error and a test asserts it.
- **FR36** — `genesis update --force` maps to Copier `run_recopy` semantics (discard local
  evolution of managed artifacts) and requires explicit confirmation.

#### State file

- **FR37** — Genesis writes one tool-owned state file recording: `model_version`,
  `genesis_version`, `adopted_at`, `last_update`, `mode`, `agents[]`, `managed[]` (path +
  class + content hash), `skips[]`, `legacy[]`, `migrations_applied[]`.
- **FR38** — The state file carries a prominent do-not-hand-edit header.
- **FR39** — State is validated against a JSON schema on every read; an invalid state file
  is a `state-invalid` finding, not a crash.
- **FR40** — Genesis never hand-edits Copier's answers file; if Copier's answers file is
  used it is treated as a second tool-owned file.
- **FR41** — Content hashes cover managed files and managed regions, enabling FR21 / FR25.
- **FR42** — The state file is git-tracked (it is repo metadata, not scratch).

#### Managed regions

- **FR43** — A managed region is delimited by begin/end markers carrying the region name and
  the model version that wrote it.
- **FR44** — Update replaces the span between markers by **pure text substitution** — never
  a three-way merge — so a half-merged file is not representable.
- **FR45** — Marker syntax is **per file format** (HTML comments for markdown, `#` comments
  for `.gitignore` / TOML / YAML), resolved through a format registry.
- **FR46** — If markers are absent in a file that should carry a region, Genesis inserts the
  region at a declared **anchor** (e.g. after the first `# Heading`), or appends when no
  anchor matches.
- **FR47** — Deleting the markers is a **sanctioned permanent opt-out**: Genesis records it
  in state and does not reinsert on later runs. (Mirrors Copier's locally-deleted-path rule.)
- **FR48** — Nested or overlapping regions are rejected with a specific error.

#### Agent adapter fan-out

- **FR49** — The neutral contract (tiers, portability, Dream-first workflow) has exactly one
  source in the manifest; all adapter files derive from it.
- **FR50** — V1 supports four adapters: Claude Code (`CLAUDE.md`), Cursor
  (`.cursor/rules/specs.mdc`), GitHub Copilot (`.github/copilot-instructions.md`), Gemini
  (`GEMINI.md`).
- **FR51** — Adapter selection is per-repo, recorded in state, and changeable later
  (`genesis adopt --agents …` adds adapters idempotently).
- **FR52** — For an adapter file that already exists with repo-specific content
  (`CLAUDE.md` is the common case), the model content is delivered as a **managed region**
  rather than by overwriting the file.

#### Templates, distribution & CLI

- **FR53** — Model templates ship **inside** the `pyforge-genesis` package; no runtime fetch
  is required for any verb.
- **FR54** — `--template <path|url>` overrides the in-package templates, for development and
  for teams that fork the model.
- **FR55** — Genesis wraps Copier via its **public API only** (`run_copy`, `run_update`,
  `run_recopy`); no reliance on `Worker` internals or private modules.
- **FR56** — Copier's code-executing template features remain gated behind an explicit
  `--unsafe` flag.
- **FR57** — Genesis is distributed as a pixi workspace member producing a conda package,
  plus wheel/sdist, with console entry point `genesis`.
- **FR58** — All verbs support `--json` for machine consumption and `--quiet` for
  unattended runs.
- **FR59** — All mutating verbs support `--dry-run` explicitly (and default to it where
  FR14 requires).
- **FR60** — `genesis version` reports both the CLI version and the bundled model version.
- **FR61** — Non-zero exit codes are distinct and documented per failure mode (conformance
  failure, precondition failure, internal error).
- **FR62** — A `genesis explain <artifact>` verb prints an artifact's class, rationale, and
  update behavior — the model documenting itself to the agents that read it (D1).

---

### Non-Functional Requirements

#### Reliability & safety

- **NFR-R1** — No verb may leave the repo in a partially-applied state: apply is
  transactional per plan, or reverts.
- **NFR-R2** — Git is the undo mechanism; every mutating verb requires a clean worktree so
  `git checkout .` fully reverts.
- **NFR-R3** — Managed-region substitution never produces conflict markers (a consequence
  of FR44).
- **NFR-R4** — The never-write guard (FR35) is enforced at the lowest write primitive, not
  at call sites, so no future code path can bypass it.

#### Air-gapped operation

- **NFR-A1** — `init`, `adopt`, and `check` make **zero network calls** with in-package
  templates; asserted by an egress-counter test.
- **NFR-A2** — Every runtime dependency resolves from conda-forge (or an internal mirror);
  nothing is fetched at runtime.

#### Performance

- **NFR-P1** — `check` completes in < 5 s on a `local-recipes`-sized repo.
- **NFR-P2** — `adopt --dry-run` completes in < 10 s on the same.
- **NFR-P3** — `init` to a working tree in < 5 minutes wall-clock end to end (SC-09).

#### Compatibility

- **NFR-C1** — Python `>=3.12`, matching the other pyforge packages and Copier's floor.
- **NFR-C2** — `copier >=9.17,<10`, range-pinned not exact-pinned, with a version-range
  sync test (warden's established pattern).
- **NFR-C3** — Linux and macOS are first-class; Windows support is best-effort for
  `init`/`check` (the loop machinery is Linux/macOS, Windows via WSL).
- **NFR-C4** — `pyforge.genesis` coexists with `pyforge.warden` and `pyforge.atlas` in the
  shared `pyforge` namespace.

#### Security

- **NFR-S1** — No execution of untrusted template content by default (FR56).
- **NFR-S2** — Genesis never writes credentials and never reads them from the target repo.
- **NFR-S3** — Templates are validated against the manifest before apply; a template
  writing outside its declared paths is a hard error.

#### Maintainability & observability

- **NFR-M1** — The model manifest is the single source of truth; adding an artifact must not
  require editing engine code.
- **NFR-M2** — The `local-recipes` empty-plan oracle (SC-02) runs in Genesis's own CI, so
  model drift in the source repo is caught the day it appears.
- **NFR-M3** — Every finding type is documented with a remedy, in the shape of
  `bmad_drift_check.py`'s finding→remedy mapping.
- **NFR-O1** — Plans and reports are machine-readable (`--json`) and human-readable by
  default.

---

### Assumptions

1. **[ASSUMPTION]** Genesis targets git repositories only; non-git targets forfeit the
   update story entirely.
2. **[ASSUMPTION]** The model has genuinely stabilized (the Dream's gate). Evidence: atlas
   (32 stories) and warden (31 stories) both shipped through it; the durable-story-specs
   convention closed the last known hole on 2026-07-25.
3. **[ASSUMPTION]** `scripts/bmad_drift_check.py` (662 lines, with a HARD/DRIFT/INFO
   severity model and a coverage check that already HARD-fails unclassified files) can seed
   `genesis check` rather than requiring a from-scratch build. **Not yet validated against
   the code** — an early spike should confirm before Epic scoping hardens.
4. **[ASSUMPTION]** Copier's `run_copy` / `run_update` / `run_recopy` signatures are stable
   across 9.x.
5. **[ASSUMPTION]** Copier's answers-file path is template-configurable (affects FR40).
6. **[ASSUMPTION]** HTML-comment markers are unambiguous in the specific markdown files in
   the manifest.
7. **[ASSUMPTION]** First two adopters are `local-recipes` (oracle) and one greenfield
   pyforge sibling; external adoption is post-V1.
8. **[ASSUMPTION]** Marshal will accept ownership of `bmad-switch` / `bmad-loop-worktree`
   *source* while Genesis owns *delivery* — this needs Marshal's PRD to agree.

### Open Questions (carried to architecture)

1. **OQ-1** — CLI framework: typer + rich (both already pinned; better for the
   plan/diff/confirm UX) vs argparse (warden's lean-engine precedent). Note Copier already
   pulls in prompt-toolkit / questionary / pygments regardless.
2. **OQ-2** — One state file, or Genesis state alongside Copier's `.copier-answers.yml`?
   Depends on assumption 5.
3. **OQ-3** — Exact marker syntax and the format registry's initial coverage (FR45).
4. **OQ-4** — Does `genesis check` copy, extract, or re-implement `bmad_drift_check.py`?
   Depends on assumption 3. Extraction into the package is attractive but couples
   `local-recipes` to a Genesis release.
5. **OQ-5** — Where does the manifest live physically — one YAML/TOML file, or one file per
   class? Affects FR1 and NFR-M1.
6. **OQ-6** — Anchor semantics for FR46 when a repo's `CLAUDE.md` has an unusual structure.
   Fallback-to-append is specified; is that always safe?
7. **OQ-7** — Does the plan artifact get committed by convention (like Nx's
   `migrations.json`), and if so, where — and is it gitignored or tracked?
8. **OQ-8** — How does a repo *leave* the model (`genesis eject`)? Not in V1 scope, but the
   state file's design should not preclude it.
9. **OQ-9** — Model deprecation path: the manifest marks `docs/specs/` legacy today. Does
   the model define a migration from Tier-1 legacy to Tier-2, or only preserve?
