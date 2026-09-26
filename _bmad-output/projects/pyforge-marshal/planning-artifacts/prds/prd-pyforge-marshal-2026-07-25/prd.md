---
title: Marshal (pyforge-marshal)
status: final
created: 2026-07-25
updated: "2026-09-26"   # RE-STAMPED 2026-09-26: chain-currency (spec->prd, behind-code) — bmad-loop cap widened to <0.13 (spec-pyforge-marshal memlog 2026-09-26); Stack literal corrected in place; no FR change. Prior 2026-09-24
# 2026-09-19  # currency reconciliation (§ 21): FR-201..FR-210 registered from spec-pyforge-marshal CAP-249..256 (Epic 51, the landing self-drives — second round) and spec-pyforge-core CAP-8..9 (Epic 52, the shared floor is a PR gate).
# 2026-09-18  # currency reconciliation (§ 20): FR-196..FR-200 registered from spec-pyforge-marshal CAP-244..248 (Epic 50, the landing self-drives); harness policy back on claude this week.
# 2026-09-14  # currency reconciliation (§ 19): `spec-pyforge-marshal` moved to 2026-09-13 while this PRD sat at 2026-09-08. The Spec's 2026-09-09 OPERATOR ANSWERING PASS closed six items that this PRD still carried as open under its OWN numbering — Q-4 (fleet budgets), Q-5 (OTel), Q-6 (ACP trigger), Q-7 (idle threshold) — plus the trust-model declaration (Spec F-4) and the freeze-writer clause (Spec F-5). Those four § 13 entries are amended in place with dated ANSWERED text, § 8's fleet-budget Non-Goal is amended, and § 11 gains C-11 (the declared, advisory-in-v1 trust model). This is a CONTENT change, not a re-stamp.
# 2026-08-26  # currency reconciliation (§ 18): the Spec's 2026-08-22 era-alignment motion folded in (Epic 25 / bmad-loop 0.11 — pin now >=0.11.0,<0.12); FR-192..FR-195 registered from epics.md's 2026-08-15/2026-08-21 additions (with the FR-193 double-assignment recorded as a defect); § 17's static-console line amended per the Unifying Strategy's CAP-2 supersession (2026-08-24). Shipped state re-grounded: 165/165 stories, Epics 1-27.
# 2026-08-14  # FR-188..FR-191 added to § 7.2: the four undecomposed marshal Specs decomposed into epics.md Epic 20 (Stories 20.1-20.10) — spec-bmad-loop-baseline-drift (FR-188), spec-bmad-loop-intent-gap-work-preservation (FR-189), spec-bmad-switch-scope-enforcement (FR-190, closes DW-1-4-2), spec-landing-evidence-grammar (FR-191, Spec authored the same day from docs/dreams/landing-evidence-grammar.md). ONE FR space now FR-1..FR-191, no gaps.
# 2026-08-14  # FR-182..FR-187 backfilled into § 7.2/§ 7.3: six FRs cited by epics.md (Stories 3.11/3.12/3.13/2.8/5.9/5.10, all shipped) but absent here — the same INV-A class the 2026-08-11 line closed for FR-181, found ×6 by the 2026-08-14 dream-backlog chain audit. Sources: spec-adaptive-model-tiering (FR-182/183), spec-horizontal-run-concurrency (FR-184), spec-risk-tiered-review-depth (FR-185), spec-quick-dev-reconciliation (FR-186), spec-marshal-land-merge-subject (FR-187). ONE FR space now FR-1..FR-187, no gaps.
# 2026-08-11  # FR-181 added to § 7.2 (docs/dreams/fleet-status-supervisor-fallback.md, spec-fleet-status-supervisor-fallback): a dead supervisor sidecar consults a fallback engine-liveness signal before reporting "unsupervised". Queued as Story 5.8 (epics.md, PR #425); this closes the chain-completeness INV-A gap that PR #425 left open (the FR entry, not the Dream/Spec/Story chain, was the missing piece). ONE FR space now FR-1..FR-181, no gaps.
# 2026-08-09  # § 16.9 reopened twice: FR-168 (a Spec cannot declare a surface it has no contract for) realizes CAP-5, and FR-169 (the presumed set is worked down by measurement) realizes CAP-6 — both of spec-surface-drift-reconciliation, both found by operating the gate FR-164..FR-167 turned green. ONE FR space now FR-1..FR-180, no gaps. FR-170/171 reopen § 7.2 durability (the guarantee holds, its SIGNAL did not); FR-172/173 reopen pr-lifecycle and FR-174 surface-drift-reconciliation, all three found by operating the fleet during a live 9-story run.
# 2026-08-08  # ONE FR space, FR-1..FR-163, no gaps. The genesis-installer satellite's own FR1..FR62 island renumbered into FR-66..FR-127 and its section retitled "15. The seed installer — `marshal seed`"; OQ-1..9 -> Q-17..25; NFR-O1 retired into NFR-12; SC-01..10 and K-01..03 adopted as-is (Marshal had neither namespace). New § 16: the FR-surface rule widened to an ownership test, and 8 previously-undecomposed Marshal Specs absorbed as FR-128..FR-163 (testing-charter, loop-home-fleet-refresh, sprint-status-auto-promote, dashboard-path-derivation, detector-self-verification, fleet-chain-completeness, agent-tool-surface, pyforge-core). New § 17: the Marshal/Steward seam. jira-github-projects-sync re-owned to Steward; agentic-sdlc-autonomy recorded as a standing position with nothing to decompose.
# 2026-08-02  # genesis-installer PRD consolidated in as a Satellite section (explicit user override); CAP-9 -> FR-59/FR-60; competitive re-frame; FR-13 re-scope; FR-58 psmux; convergence watch; Q-3/Q-10..14 resolutions; durable-runs -> FR-61/FR-62/FR-63; fidelity-enforcement (Marshal-only slice) -> FR-64; one-front-door -> FR-65, Q-15/Q-16
project: pyforge-marshal
dist: pyforge-marshal
module: pyforge.marshal
cli: marshal
owner-dream: docs/dreams/pyforge-marshal.md
mode: headless
inputs:
  - planning-artifacts/briefs/brief-pyforge-marshal-2026-07-25/brief.md
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
fr-derivation-from: "2026-09-16"
---

# PRD: Marshal

## 0. Document Purpose

This PRD is for the Marshal builder, the Ecosystem Crew's station owners, and the downstream architecture and epic-breakdown workflows. It is structured Glossary-first so that downstream artifacts inherit exact vocabulary; features are grouped with globally-numbered FRs nested beneath them; cross-cutting NFRs are separate; and inferences are tagged `[ASSUMPTION]` inline and indexed in §13.

It builds on, and does not duplicate, the product brief (`planning-artifacts/briefs/brief-pyforge-marshal-2026-07-25/brief.md`) and the two cited research reports under `planning-artifacts/research/`. Two sections carry decisions rather than requirements and are load-bearing for everything downstream: **§5 — the wrap-versus-absorb decision** and **§6 — the agent-portability fold**. Read those before §7.

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

#### FR-1: Provision a loop home ← CAP-1
The operator can create an isolated loop home for a project slug in one command.
**Consequences (testable):**
- A git worktree exists at the conventional sibling path on branch `loop/<slug>`.
- Re-running against an existing home succeeds and changes nothing (idempotent).
- The command prints a directly runnable launch line.

#### FR-2: Per-worktree active-project state ← CAP-1
Each loop home carries its own BMAD active-project marker and planning-artifact symlinks, independent of every other home and of the main checkout.
**Consequences:**
- Provisioning home B leaves home A's and the main checkout's active project unchanged.
- The marker and the planning symlinks always agree; a desync is reported, never silently tolerated.
- `BMAD_ACTIVE_PROJECT` is exported in the printed launch line as belt-and-suspenders.

#### FR-3: Single-sourced Tier-3 store ← CAP-1
A loop home's `implementation-artifacts` resolves to the main checkout's canonical directory, so every consumer sees one store at an identical repo-relative path.
**Consequences:**
- The home's `implementation-artifacts` realpath equals the main checkout's.
- The canonical directory is created if absent.
- A real, non-empty local directory is **never** replaced; the command refuses with a named finding.

#### FR-4: Isolation verification ← CAP-1
The operator can assert that two or more loop homes are genuinely isolated.
**Consequences:**
- Exit 0 when markers and symlinks are independent, Tier-3 realpaths are identical, and the main checkout is untouched.
- Non-zero with a named finding on any cross-talk.
- Works for N ≥ 2 homes in one invocation. *(Live evidence: seven homes provisioned as of 2026-07-25.)*

#### FR-5: Preflight ← CAP-1
Initialization verifies the run can actually start, rather than discovering it cannot at minute 90.
**Consequences:**
- Reports: harness present and version; multiplexer backend available; adapter binary present; story feed resolvable and parseable; verify commands resolvable; `main` not checked out twice.
- Each adapter's declared first-run requirement is surfaced as an explicit human action, because an unanswered first-run dialog is indistinguishable from a session timeout.
- Exits non-zero on any blocking finding, naming it.

#### FR-6: Teardown ← CAP-1
The operator can remove a loop home cleanly.
**Consequences:**
- Worktree and branch are removed; `git worktree list` is clean afterwards.
- Refuses when the home has uncommitted or unmerged work unless explicitly forced.
- Never touches the canonical Tier-3 store.

#### FR-7: Adapter config seeding ← CAP-1
Gitignored adapter configuration a fresh worktree lacks is seeded into the home.
**Consequences:**
- Each loaded adapter's declared seed files are present in the home after init.
- Project-specific extra paths are seeded from composed policy, not from a hard-coded list.

#### FR-8: Enumerate loop homes ← CAP-1
The operator can list all loop homes with their resolved active project.
**Consequences:**
- One row per home: path, branch, active project, and whether it is desynced.

---

### 7.2 Run supervision — `marshal factory spin`

**Description.** The launch verb, and the home of Marshal's differentiator. `marshal factory spin` starts or resumes a gated run against an approved spec — **always detached**, so the foreground-timeout failure that killed a run mid-review is structurally impossible — with a supervisor attached that watches from outside the agent session. The supervisor detects idle strands, enforces budget ceilings, surfaces escalations, and writes the run journal. Realizes UJ-1, UJ-3.

**Functional Requirements:**

#### FR-9: Detached launch by default ← CAP-2
Runs and resumes execute detached from the invoking shell.
**Consequences:**
- The command returns promptly with a run identifier; the run survives the caller exiting.
- Foreground execution is available only behind an explicit flag, documented as unsafe for resumes.
- Attaching to a live run's session is a separate, non-destructive command.

#### FR-10: Scoped launch ← CAP-2
The operator can scope a run to one story, an epic, a count, or the whole feed.
**Consequences:**
- Story, epic, and max-count selectors are supported and composable.
- The resolved story list is echoed before launch and recorded in the journal.

#### FR-11: Supervisor attaches to every run ← CAP-2
Every run started by Marshal has a supervisor process attached for its lifetime.
**Consequences:**
- The supervisor runs outside the agent session and cannot be disabled from within it.
- Supervisor death is itself detected and journaled; it does not silently stop watching.
- The supervisor is inert on a run it did not start.

#### FR-12: Idle-strand detection ← CAP-2
A session that has stopped producing output but has not exited is detected and acted on well before any token or time cap.
**Consequences:**
- Idleness is measured from observable session output (pane content and log modification time), not from the agent's self-report.
- The threshold is configurable with a default materially below the session budget. `[ASSUMPTION: default 25 minutes, matching the hand-written stopgap that worked in production.]`
- Fresh output re-arms the window.
- On expiry the supervisor takes a configured action — nudge, then stop-and-retry, then defer — with each step journaled and counted.
- *Motivating evidence: this class of failure cost three story attempts and one 4M-token review cycle in a single wave.*

#### FR-13: Budget ceilings ← CAP-2
A run cannot exceed configured token and wall-clock ceilings without a named stop.
**Consequences:**
- Per-story and per-run ceilings are enforced; a breach stops the unit with a named reason rather than a silent defer.
- Consumption is journaled per story with a cost estimate where the adapter reports one.
- Approaching a ceiling emits a warning before the stop.
- *(Re-scoped 2026-08-01:)* upstream `bmad-loop` v0.9.0 ships **in-session** budget guards — credited, and not duplicated. Marshal's requirement is the half upstream cannot provide: ceilings enforced **from outside the session** by the supervisor (NFR-4), reachable from externally-observed quantities alone, so a wedged or compromised session cannot outlive its budget by being its own witness.

#### FR-14: Heaviest-story budget advisory ← CAP-2
Before launch, the operator is warned when a selected story is likely to exceed the configured session budget.
**Consequences:**
- Preflight compares the session budget against a per-story hint (spec size, declared difficulty, prior attempt history) and warns.
- *Motivating evidence: a 90-minute cap killed the keystone story mid-work and burned 25.8M unrecoverable tokens.*

#### FR-15: Escalation surfacing ← CAP-2
An escalation pauses the run and reaches the operator through configured channels.
**Consequences:**
- The run pauses; no story proceeds past an unresolved escalation.
- The escalation is journaled with story key, reason, and the artifact needing a decision.
- Notification fires on at least a durable file marker; desktop notification is best-effort.

#### FR-16: Deferral capture ← CAP-2
A story the loop could not land is recorded rather than lost.
**Consequences:**
- Every deferral carries story key, reason class, attempt count, and where any preserved work lives.
- The run continues to the next story unless configured otherwise.

#### FR-17: Resume ← CAP-2
A paused run can be resumed after a human resolves the blocking condition.
**Consequences:**
- Resume is detached, on the same terms as launch (FR-9).
- Resume re-attaches a supervisor.
- Resuming a run whose escalation is unresolved is refused with a named finding.

#### FR-18: Run journal ← CAP-2
Every run produces a durable, append-only journal owned by Marshal.
**Consequences:**
- Records story transitions, gate outcomes, escalations, deferrals, budget consumption, and supervisor actions, each timestamped.
- The journal is machine-readable and survives worktree teardown.
- It is written incrementally, so a killed run still has a journal up to the kill.
- *Rationale: vendor retention is 48 hours to 180 days and agent transcript formats are documented as changing between versions. The record must be self-owned.*

#### FR-61: Bounded-loss durability *(added 2026-08-01 — `docs/dreams/durable-runs.md`)* ← CAP-19
The supervisor pushes a run's work at its own stage boundaries, and durability is on by default for every fleet launch — no separate step a human has to remember to start.
**Consequences:**
- After the dev commit, after the review verdict, and after the merge, the supervisor pushes the affected station and per-story branches — loss is bounded by a stage, not by an interval timer.
- An interval-push watcher remains as the floor for whatever the stage hooks miss, and starts automatically as part of a fleet launch rather than requiring a separate manual invocation.
- Push is read-only against working trees and remotes — never a force-push, never a rewrite — so it cannot disturb a live session.
- *Motivating evidence: measured 2026-07-31 — 6 station loop branches on no remote, ~5,150 lines on `recover/*`, one story's 734-line transport branch (spec included) unpushed six days, 156 dangling commits one `git gc` from unrecoverable, and 1,748 lines sitting 40 minutes as a local-only commit. Nine detectors ran green throughout because none asked the durability question — the window reopens roughly every 60–90 minutes, once per station's dev phase.*

#### FR-170: A retired story branch is not a push failure *(added 2026-08-09 — `docs/dreams/durable-runs.md`)* ← CAP-128
The supervisor distinguishes a branch that **cannot** be pushed from one that no longer **needs** to be, and proves the difference rather than assuming it.
**Consequences:**
- bmad-loop deletes a story's branch when the story merges into the station branch; the supervisor polls, so it routinely acts on a `dev-commit-landed`/`story-merged` boundary *after* the branch is gone. That is the ordinary success path, not a fault.
- When the per-story branch is absent, the supervisor checks whether the story's `commit_sha` (already carried on `TaskPhaseSnapshot`) is reachable from the station branch. Reachable → journal a benign `retired-merged` outcome and **no finding**. Not reachable → a **distinct, louder** finding: a branch vanished with work that never landed is real loss, and must not inherit the silence the benign case earns.
- `GitVcs.push` is unchanged: raising on "no such branch" is correct — falling back would push to a target the caller never named. The fix belongs to the caller, which should not ask for a push it does not need.
- *Motivating evidence: measured 2026-08-09 on the doctor Epic 6 run — 6 of 22 `stage-push` records reported `push-failed`/`MRS-SUPV-008` on branches whose work was already safe on `origin/loop/pyforge-doctor`. The false alarm cost an operator an hour and produced the wrong diagnosis "durability is broken."*

#### FR-171: Unpushed work is measured by tip, never by name *(added 2026-08-09 — `docs/dreams/durable-runs.md`)* ← CAP-129
`unpushed-work-check` reports a branch whose remote copy is **behind**, not merely one with no remote copy at all.
**Consequences:**
- `find_unpushed`'s `if br in remote: continue` is replaced by a tip comparison: a local branch whose remote sha differs and which carries commits the remote lacks is unpushed work, however long its name has existed on origin.
- Station branches (`loop/*`) are in scope: they are precisely the long-lived branches whose name always exists remotely and whose tip silently falls behind between runs — the case the name check structurally cannot see.
- *Motivating evidence: measured 2026-08-09 — `loop/pyforge-doctor` on origin at `3f43f486c9` while the local branch stood 8 PRs ahead at `cbd965110b`, reported clean. The Dream's own founding observation ("nine detectors ran green because none asked the durability question") reproduced inside the detector written to ask it.*

#### FR-172: `marshal land` refuses while a run is in flight *(added 2026-08-09 — `docs/dreams/pr-lifecycle.md`)* ← CAP-130
The last mile knows whether the road is still in use.
**Consequences:**
- `land` resolves its head branch to the loop-home **station branch** and retires it by default; invoked during a live run it would merge and then **delete the branch bmad-loop is actively merging stories into**. It now refuses, by name, when a supervisor/engine is live for that slug — the same liveness reading `marshal status` already produces, not a new mechanism.
- The refusal is overridable **explicitly** (a flag that says what it accepts), because landing mid-run is legitimate when the operator knows the run is between stories — it must simply never be the silent default.
- Landing a wave while a run continues stays supported; what is refused is the **branch retirement**, not the merge.
- *Motivating evidence: measured 2026-08-09 — avoided only because a human read `cli/land.py` before invoking it. A safety property that depends on someone reading the source is not one.*

#### FR-173: A landing leaves the loop home current with `main` *(added 2026-08-09 — `docs/dreams/pr-lifecycle.md`)* ← CAP-131
"Resync" means the station branch is current, not merely that the feed is.
**Consequences:**
- `landing_resync` today resyncs the **feed**; `landing_resync_commands` is empty by default, so nothing returns the loop home to `main` after its own work merges. The station branch begins drifting the moment the first PR lands.
- Landing brings the station branch back to `main` (fast-forward where possible), or reports precisely why it cannot — never silently leaves it behind.
- Between-runs staleness is in scope: a home with no live run is exactly where drift accumulates unobserved.
- *Motivating evidence: `loop/pyforge-doctor` measured 5 commits behind `main` minutes after its own stories landed, and 8 PRs behind on origin between runs — reported clean by every detector at the time.*

#### FR-174: The producer reconciles the surface it drifts *(added 2026-08-09 — `docs/dreams/surface-drift-reconciliation.md`)* ← CAP-132
bmad-loop names the governed paths it changed, in the owning Spec's memlog, as part of the story.
**Consequences:**
- A loop-produced story that touches governed files leaves that Spec's `.memlog.md` naming each changed path **before the story is complete**, so `spec-surface-check` is green on the station branch without a human editing a memlog at landing.
- A story that changes no governed file writes nothing — silence is not a finding, and a memlog entry per story would be noise.
- Reconciliation is **per-file naming** under FR-165's rule. The loop is never handed `--write-baseline`: a producer that can stamp its own baseline is the laundering FR-165 exists to end.
- *Motivating evidence: measured 2026-08-09 — the first three loop-produced stories landed drifted 14 governed paths across `spec-pyforge-doctor` plus `pixi.toml` against two further surfaces, every one named by hand at landing. The gate is correct; the machine writing most of the repo's code does not know it exists.*

#### FR-175: The loop's deferred work reaches the tracked ledger *(added 2026-08-09 — the Marshal↔loop seam review)* ← CAP-133
A follow-up the loop defers is a decision of record, not a local note.
**Consequences:**
- When bmad-loop spends its damping cap it files "follow-up review still recommended" into `implementation-artifacts/deferred-work.md` — **gitignored Tier-3**, invisible to CI and absent from every clone — under a **generic `DW-<n>` id** that the next damped story collides with.
- Measured 2026-08-09: `DW-1`/`DW-2` were promoted by hand as `DW-FU-1-1`/`DW-FU-1-3`; **`DW-3`…`DW-7` never were**, and stand today as five `tier3-only-deferral` findings on marshal.
- Promotion carries the ledger's `DW-<story>-<n>` convention so ids cannot collide, and happens as part of the story or its landing — not as archaeology someone performs later.
- Scope note: this is about the **transport** of a deferral into the tracked tier. Whether each follow-up review is then *done* stays the operator's call.

#### FR-176: The failed-story safety net is reported, not merely written *(added 2026-08-09 — the Marshal↔loop seam review)* ← CAP-134
A `changes.patch` left by a killed story is surfaced, so a patch holding unlanded work cannot sit unnoticed.
**Consequences:**
- A session-timeout kill defers a story and preserves its work at `<run>/failed/<story>/changes.patch`. **Nothing in the repo reads that path** — measured 2026-08-09: **7 patches on disk, 26 KB to 205 KB**, across doctor/herald/marshal/mason/warden.
- All seven belong to stories that later reached `done`, so **nothing is lost today** — which is precisely why it has gone unnoticed. The gap is the absence of a signal, not a present loss.
- Reported alongside the other durability signals (`unpushed-work-check`'s family), keyed on whether the owning story has since landed: a patch whose story is `done` is spent and can be said so; one whose story is not is real pending work on one disk.

#### FR-177: One pusher, not two *(added 2026-08-09 — the Marshal↔loop seam review)* ← CAP-135
`loop_push_watch.py`'s role is reconciled with the supervisor that now subsumes it.
**Consequences:**
- FR-61 gave the supervisor its own `boundary: "interval"` push (`_INTERVAL_PUSH_BOUNDARY`), so during a run the standalone watcher duplicates it — two processes pushing the same branches on overlapping timers.
- The script's own pixi description still calls itself "a STOPGAP — the durable fix is for the loop to push at its own stage boundaries", a statement **Marshal made false when FR-61 shipped**. Documentation that describes a world that no longer exists is how an operator (2026-08-09) concluded nothing was pushing at all.
- Either retired, or re-scoped to the one case the supervisor structurally cannot cover — a home with **no live run** — with its description corrected either way. It must not keep claiming to be the fallback for something already built.

#### FR-178: A loop agent cannot mutate repo-wide git state *(added 2026-08-09 — the Marshal↔loop seam review)* ← CAP-136
Isolation covers the shared git directory, not just the working tree.
**Consequences:**
- Every loop home **and every per-story worktree** resolves `--git-common-dir` to the **same** `local-recipes/.git`. `.git/info/exclude`, `.git/config` and the rest of that directory are therefore **repo-wide shared state** that any dev session can write — Marshal's isolation contract (FR-8) covers worktrees and branches, not this.
- Observed three times, most recently **while a run was live**: a dev session re-added `/.claude/skills` to `.git/info/exclude`, which hides only NEW files, from `git status` and `git add -A`, in **every** worktree at once. It cannot be spotted with the tool you would use to spot it, and it nearly cost this session's own new test file.
- `marshal preflight`/`homes` reports a loop home whose shared git state has been mutated — at minimum `info/exclude` — so the condition is visible rather than discovered by a missing file weeks later.
- The existing filesystem-walking guard (`test_skill_files_tracked.py`) stays: it is the only signal that survives the rule, and it is what caught the third recurrence.

#### FR-179: The board answers "how much is left" *(added 2026-08-09 — `docs/dreams/factory-console.md`)* ← CAP-137
A fleet roll-up renders on both boards; live-only fields stay local.
**Consequences:**
- Per-station `done / total`, `epics done / total` and a **PyForge roll-up** row, counted from each project's **tracked** `sprint-status-ledger.yaml` via the same `parse_sprint_status` the deploy already uses — never a second parser, and never the gitignored Tier-3 feed CI cannot read.
- **`blocked` is counted separately**, because the board's own story states are `done`/`active`/`pending` and structurally cannot distinguish a blocked story from an unstarted one. Measured 2026-08-09: 6 blocked looked identical to 119 pending.
- **No live fields on Pages.** Run state, projection and the ATTENTION block derive from `marshal status`, which reads tmux and `~/.bmad-loops`; CI has neither, so publishing them would publish what the deploy cannot measure. `pixi run -e local-recipes fleet-picture` is the local view that adds them.
- An epic counts as done only when every story in it is done — the same rule the report uses, so the two can never disagree.

#### FR-180: A stale loop home cannot be spun *(added 2026-08-09 — `docs/dreams/pr-lifecycle.md`)* ← CAP-138
Preflight refuses a loop home that is behind `main`, and reports one that has diverged from origin.
**Consequences:**
- **Preflight, not the landing path.** FR-173 makes a landing leave the home current, but a landing done by hand (`gh pr merge`) never runs it. Preflight is the chokepoint every `factory spin` must pass, so the check cannot be skipped.
- **ERROR, not WARN**, because the failure is silent: a home on an old baseline sees its drift as non-gating `[drift-presumed]`, `spec_surface_check` exits 0, and the S-13.7 guard never bites. Measured 2026-08-09 — a current home self-reconciled 4/4, a stale one 0/3, with nothing failed and nothing logged. It is clearable by one `git merge --ff-only`, so it gates without being an unclearable red.
- **AHEAD is not BEHIND.** A home carrying unlanded story merges is the ordinary mid-run state and must not be refused.
- **FR-173 is amended to include the push.** Returning the station branch to `main` locally is not enough: provisioning reads **origin**, so a re-provisioned home would clone a stale branch. Measured the same day — seven homes sat 33–74 commits behind on origin after their work had already landed.
- Any probe failure yields no finding: a diagnostic must never become a refusal.

#### FR-181: A dead supervisor sidecar doesn't hide a live engine *(added 2026-08-11 — `docs/dreams/fleet-status-supervisor-fallback.md`)* ← CAP-139
When the supervisor sidecar is dead, `derive_home_state` consults a second, independent liveness signal for the run's engine before reporting `"unsupervised"`, so a dead sidecar behind a demonstrably live engine reads differently from a run that actually needs a re-spin.
**Consequences:**
- `derive_home_state`'s first branch (`if not finished and supervisor_alive is False: return "unsupervised"`) returns before ever checking whether the harness itself has an in-flight task; `supervisor_alive` probes only the sidecar Marshal spawns, never the underlying `bmad-loop` engine process it watches.
- **Narrows a false positive, never softens a real one.** A run whose engine is also gone still reports `"unsupervised"` — the existing rule that a dead supervisor is never reported as healthy stays intact.
- The fallback signal is itself derived from journals/process state (AD-5), never a hand-maintained flag or an operator override.
- The two failure shapes (sidecar-dead-engine-alive vs. sidecar-dead-engine-dead) are distinguishable from `marshal status`/`fleet-picture`'s own output, so an operator never again needs the `ps`/`tmux ls`/`state.json` cross-check by hand.
- *Motivating evidence: measured 2026-08-11 — 5 stations resumed via bare `bmad-loop resume` (which never spawns a fresh sidecar) reported `unsupervised — needs re-spin` for the rest of their run's life, although each was independently verified alive via `ps`/`tmux ls`/`state.json`. Story 5.8 (Epic 5) queues the implementation; the concrete fallback signal is a story-level design decision, not resolved here.*

#### FR-182: A story's declared difficulty actually picks its model *(added 2026-08-14 backfill — `docs/dreams/adaptive-model-tiering.md`; shipped via Story 3.11)* ← CAP-140
A project's declared `model_tier_map` and a story's declared `difficulty:` change which model runs each stage: the rendered `policy.toml` differs from the undeclared baseline in exactly the mapped stages, and the resolution is journaled at launch.
**Consequences:**
- Reuses FR-51's already-shipped chain (`core/spec_difficulty.py`, `cli/spin.py` resolution, `render_policy_toml` tier-batching) — no second mechanism; this FR is the *feeding* of that chain, which grep proved fully built and permanently unused (zero real map entries, zero declared difficulties across all 8 loop homes).
- Difficulty is **authored**, not derived: a Tier-3 story-spec frontmatter `difficulty:` key against the vocabulary `marshal-policy.toml` maps.
- A mismatched or undeclared story still reports via the existing `batching_report` path, unchanged.

#### FR-183: A struggling retry runs under a stronger model *(added 2026-08-14 backfill — `docs/dreams/adaptive-model-tiering.md`; shipped via Story 3.12)* ← CAP-141
A story whose attempt or review-cycle count crosses a configured threshold — derived from the journal fold (AD-26), never a hand-maintained flag — is next dispatched under a model at least as strong as its resolved tier: a floor-raise only, never a downgrade.
**Consequences:**
- The escalation applies on the deferral-then-resume path (`run_resume`'s existing re-render), is journaled with intent/outcome discipline (AD-28) naming trigger and resulting model, and is bounded — it does not re-fire without a new trigger (C-6).
- A story with no declared difficulty still has a baseline model to escalate from — not a no-op for undeclared stories.

#### FR-184: The parallel-fan-out clamp is surfaced, not silent *(added 2026-08-14 backfill — `docs/dreams/horizontal-run-concurrency.md`; shipped via Story 3.13)* ← CAP-142
`bmad_loop==0.9.0`'s server-side clamp of `max_parallel` to 1 (an unbuilt Phase-5 stub) is surfaced as a loud advisory (`MRS-POLICY-007` WARN), registered in Story 6.8's `upstream-register.json`, and assessed for Marshal-side readiness (`parallel-fan-out-readiness-assessment.md`).
**Consequences:**
- Marshal must **not** build concurrent dispatch while upstream clamps (AD-2/AD-3 wrap-never-fork); the capability itself stays parked until upstream Phase 5 ships, at which point adoption starts from the readiness assessment, not a fresh investigation.

#### FR-185: A low-risk story's review runs lighter, never absent *(added 2026-08-14 backfill — `docs/dreams/risk-tiered-review-depth.md`; shipped via Story 2.8)* ← CAP-143
A story mechanically classified low-risk (`classify_review_tier`, the Story-2.4 pure-function idiom) runs review at reduced cycle count (`resolve_review_cycles`) while the independent reviewer still runs on every story with no exception.
**Consequences:**
- Only cycle count varies by tier; review **occurrence** never does (`gate_mode = "none"` stays human-approval-only).
- Any tightened cap is checked against `DW-AD23-3` by name: a too-low cap once silently damped five reviewer-recommended follow-ups; the low-risk tier must not reproduce that loss (CAP-3 regression guarantee on `deferred-work-check`'s full capture).

#### FR-186: A story finished by hand isn't invisible to the ledger *(added 2026-08-14 backfill — `docs/dreams/quick-dev-reconciliation.md`; shipped via Story 5.9)* ← CAP-144
A backlog story merged with no `bmad-loop` run record is detected as completed from git plus story-identity artifacts alone (AD-5/AD-33), advanced out of `backlog` with its completion path recorded, and its spec promoted under Story 4.1's durability guarantee — via `deploy reconcile-completions` with advisory-locked ledger writes.
**Consequences:**
- Only `backlog` rows are eligible for advancement; `blocked`/`in-progress` are never force-advanced.
- Documented label deviation (Spec change log 2026-08-12): the completion path is `not-loop-native`, never `bmad-quick-dev` — git alone could not distinguish quick-dev from `marshal land` until FR-187; the label narrows automatically as FR-187 subjects accumulate.
- Reconciliation around a live run neither reads nor writes that run's journal (CAP-4, proven by test).

#### FR-187: `marshal land` renders a detectable merge subject *(added 2026-08-14 backfill — `docs/dreams/marshal-land-merge-subject.md`; shipped via Story 5.10)* ← CAP-145
`marshal land` merges render the same templated subject (`identity.render_merge_subject`, AD-24) that `deploy land-story` already renders — threaded as a port-level `subject` parameter through `ForgePort.merge_pr` — so `marshal_native_merged_keys` classifies every Marshal-driven landing correctly.
**Consequences:**
- Purely additive and forward-only: no strategy/gate changes, no retroactive relabelling of pre-fix `not-loop-native` rows (explicit non-goal); FR-186's classification precision sharpens with zero change to FR-186 itself.

#### FR-188: A baseline-drift defer can never pass silently *(added 2026-08-14 — `docs/dreams/bmad-loop-baseline-drift.md`; spec-bmad-loop-baseline-drift)* ← CAP-146
A Marshal-side detector at the adapter seam recognizes `bmad_loop`'s baseline-drift defer signature from the feeds the package itself writes, surfaces it loudly with the recovery inputs named, and the drafted upstream issue is filed behind its two gates.
**Consequences:**
- Reads only feeds `bmad_loop` writes (`journal.jsonl`, `state.json`, `attempt-preserve/*` refs, `failed/*/changes.patch`) — never imports or edits the git-pinned package (HARD constraint: it ships via pixi, is imported by live loops, and is wiped on `pixi install`); scope=runtime like `loop-stall-check`, excluded from `detectors-ci`.
- Replaying run `20260813-094919-bfcb`'s journal (story 9-6) fires the detector naming the story, both baselines (`523e938c7978` real vs `26102ea12c6d` drifted), and the preserve ref; a clean run's feeds yield no finding.
- Loud-defer containment only: the finding lands in the operator's existing ATTENTION plane with story, run, preserved ref/patch, and drifted-vs-real baselines named — a run carrying such a defer cannot read healthy, and there is never a quiet auto-land.
- The upstream filing against `bmad-code-org/bmad-loop` is strictly gated — repo-access check and duplicate search recorded, then either filed (URL in the Dream's Realization log) or a duplicate linked — and carries FR-189's Story 10.1 evidence too: the two loss modes share one coordinated report.
- *Motivating evidence: five occurrences in one session (2026-08-14) — marshal 8.1–9.5, 9.6, 10.1, mason 3.6–3.9 — each recovered only by manual git archaeology (PRs #482–#484). Queued as Stories 20.1–20.3.*

#### FR-189: An intent-gap revert leaves a recoverable artifact *(added 2026-08-14 — `docs/dreams/bmad-loop-intent-gap-work-preservation.md`; spec-bmad-loop-intent-gap-work-preservation)* ← CAP-147
When `bmad_loop`'s intent-gap protocol reverts an attempt, Marshal-side compensation at the adapter seam preserves the discarded work the way the deferred-story path already does — branch or patch — the escalation text names the artifact, and a detector flags any halt missing one.
**Consequences:**
- Preservation symmetry with `scm.keep_failed`: an `attempt-preserve/*` branch for real commits, a `failed/<story>/changes.patch` otherwise; the worktree stays reverted clean per protocol; no edits to the installed package.
- `bmad-loop resolve --restore-patch` (or a human following the named ref) restores the attempt from the escalation text alone — zero session-transcript access.
- The intent-gap halt itself stays exactly as strict: the never-patch-around protocol is unchanged, and no preserved attempt auto-relands without the contract fix.
- A post-hoc detector makes any residual gap loud: an intent-gap halt whose preserve artifact is missing is a finding, never a silent pass.
- *Motivating evidence: Story 10.1 (2026-08-14) — full implementation, 3646 tests green, two adversarial reviews, then a correct halt whose revert left nothing; recovered byte-identical (PR #486) only via a transcript accident. Queued as Stories 20.4–20.5; the upstream evidence rides FR-188's gated filing.*

#### FR-190: A write resolves to the slug the caller asked for *(added 2026-08-14 — `docs/dreams/bmad-switch-scope-enforcement.md`; spec-bmad-switch-scope-enforcement)* ← CAP-148
One shared `verify_scope(root, expected_slug)` primitive checks the marker/symlink/expected-slug triangle in a single pass, and both existing guards — `scripts/bmad-switch --current` and `marshal init`'s MRS-INIT-003 — consume it and hard-fail on drift.
**Consequences:**
- A home internally consistent on the WRONG project is a drift, not a pass, and an unrecognized symlink-target shape reports "unrecognized" rather than inferred agreement — closing DW-1-4-2's blind spots (2) and (1) respectively.
- Exactly one implementation of the triangle check exists; the retired per-caller check bodies are gone, not shadowed — the divergent-pair failure mode this exists to kill is not reintroduced as an implementation detail.
- Hard-fail everywhere: `bmad-switch --current` exits non-zero naming the drift (no more advisory stderr at exit 0); `marshal init` refuses a repurposed home instead of silently reconciling it onto the new target.
- Cheap by contract — three file reads and string compares, no subprocess — so wiring it into a write-skill preflight is free; fail-closed on parse.
- *Motivating evidence: the 2026-07-25 five-agent fan-out incident (symlinks observed moving mid-run; one memlog under the wrong project), caught only by voluntary `readlink -f`. DW-1-4-2 (`deferred-work-ledger.md:385`) closes against this. Queued as Stories 20.6–20.7.*

#### FR-191: A legitimate landing is recognizable on every path *(added 2026-08-14 — `docs/dreams/landing-evidence-grammar.md`; spec-landing-evidence-grammar)* ← CAP-149
ONE shared grammar of landing-evidence shapes — merge-subject templates, branch-name grammars, and a documented recovery-commit convention — is defined once and consumed by doctor's `story-status` evidence routes, Marshal's promotion classifiers, MRS-STATUS-010, and `marshal retire`'s patch-id matching.
**Consequences:**
- HARD: doctor never imports `pyforge.marshal`, so the grammar is a contract with a cross-package conformance test, a shared data artifact both read, or a `pyforge-core` module (the Story 14.2 shared-spine precedent) — the home is a story-level design decision inside that boundary.
- Measured deltas the day it ships: the three standing `story-status` false positives (marshal 8-2, 10-1, mason 3-7 — all verified landed, PRs #482/#486/#483) go green with no per-story whitelist; MRS-STATUS-010's 26-warn UNCONFIRMED pile shrinks to genuinely-unlanded patches; `marshal retire` proposes real retirements again.
- Absence of evidence stays hedged: the grammar widens what is *recognizable*, it never converts "no match" into a confident "never landed" anywhere.
- Forward-compatible with FR-187 (the templated subject is one shape in the grammar, not the grammar itself) and never retroactive: existing recovery landings are recognized as written, or via a one-time reviewed allowlist — history is not rewritten.
- *Queued as Stories 20.8–20.10; the Spec was authored 2026-08-14 from the Dream, which carries the full 2026-08-14 broken-windows-audit evidence trail.*

---

### 7.3 Gates and verification — `marshal gate evaluate`

**Description.** In the current stack the gate is a configuration line inside the orchestrator. Marshal makes it a first-class, independently invocable object: the same gate a run uses can be run by a human before approving, or by CI after the fact. It adds the scope check the operator currently performs by eye, and the doc-only classification that currently causes a false-negative rollback loop. Realizes UJ-2.

**Functional Requirements:**

#### FR-19: Standalone gate evaluation ← CAP-3
The operator or CI can evaluate a project's gates without a run in flight.
**Consequences:**
- Runs the project's configured verify commands and reports pass/fail per command with captured output.
- Exit code is a stable contract: 0 pass, non-zero fail, with a distinct code for "could not evaluate".
- Evaluation never mutates the working tree.

#### FR-20: Project-scoped verify commands ← CAP-3
Verify commands resolve from composed policy and are scoped to the active project.
**Consequences:**
- Another project's gates are never run during this project's story.
- A verify command that cannot be resolved is a blocking finding at preflight (FR-5), not a runtime surprise.

#### FR-21: Deterministic, no-LLM gates ← CAP-3
Gate evaluation involves no model call.
**Consequences:**
- Evaluation is reproducible: the same tree and commands produce the same verdict.
- Gate outcome is derived only from command exit codes and the scope check — never from an agent's assertion that it passed.

#### FR-22: Frozen-surface scope check ← CAP-3
A story's changed surface is checked against its declared surface and against frozen surfaces.
**Consequences:**
- Declared surfaces come from the story spec and may only **narrow** the project-declared surface, never widen it — a story spec is machine-drafted, so it cannot author the allowlist it is judged against (architecture AD-27). Frozen surfaces accumulate from prior stories through the run record (AD-26).
- A change to a frozen file is a hard failure naming the file and the story that froze it.
- A change outside the declared surface is a failure naming each offending path.
- *Motivating evidence: the operator performed this check manually on every producer story of a six-epic build.*

#### FR-23: Doc-only story classification ← CAP-3
Stories that legitimately produce no source change are classified before verification.
**Consequences:**
- A story whose declared deliverable is a document or decision record does not fail on "no changes in worktree".
- Classification is recorded in the journal.
- *Motivating evidence: a design-spike story tripped this false negative into a rollback loop and had to be recovered from a preserved ref by hand.*

#### FR-24: Gate mode ladder ← CAP-3
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

#### FR-25: Gate evidence record ← CAP-3
Every gate evaluation produces a durable record.
**Consequences:**
- Records commands run, exit codes, scope-check verdict, tree revision, and timestamp.
- Referenced from the journal and retrievable per story.

#### FR-26: Never false-green ← CAP-3
No story reaches a merged state without a green verify and a passing scope check.
**Consequences:**
- Any path that would merge without both is refused.
- An unevaluable gate is treated as failure, never as pass. *(Consistency with Warden's never-false-green invariant.)*

#### FR-27: Review-cap landing path ← CAP-3
A story that is sound but did not converge in review can be landed deliberately, under the same gates.
**Consequences:**
- A dedicated command lands a named story branch only after re-running the full gate (FR-19, FR-22).
- The merge uses the conventional subject form (FR-32); the operator does not hand-type it.
- The manual landing and its justification are journaled.
- *Motivating evidence: two warden stories were landed this way by hand.*

#### FR-64: A gate evaluation binds to the spec's Success signal *(added 2026-08-01 — `docs/dreams/fidelity-enforcement.md`, CAP-4)* ← CAP-22
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

#### FR-28: Batch pull request ← CAP-4
The operator can open one pull request for a wave of merged stories.
**Consequences:**
- Title and body are derived from the merged story set and the journal; the body lists stories with their gate verdicts.
- The PR targets the configured base branch; it is never opened against an upstream fork's default.
- Existing-PR detection updates rather than duplicating.

#### FR-29: Repository-hygiene preflight ← CAP-4
Before opening or updating a PR, mechanical repository gates are checked.
**Consequences:**
- Reports which project-configured hygiene rules apply to the change set and whether each is satisfied.
- Rules are declared in project policy, not hard-coded into Marshal.
- Exits non-zero on an unsatisfied blocking rule with a remediation line.

#### FR-30: Automatic story-spec promotion ← CAP-4
Every merged story's spec is promoted from run scratch into tracked planning artifacts.
**Consequences:**
- After a story merges, its spec is copied from the run's Tier-3 scratch into the project's tracked `planning-artifacts/specs/` — the **real** project path, never the gitignored `_bmad-output/planning-artifacts/` symlink — and **committed** by Marshal in a dedicated commit containing only promotion paths.
- Promotion is complete only when those bytes are reachable from a ref that survives the loop home; that ref may be **local**, so promotion never requires the network (architecture AD-29, NFR-2). *(Amended 2026-07-30, **F-14**: this consequence said "staged for commit", which AD-29 explicitly declares insufficient — a merely-staged spec dies with the branch at teardown, which is the motivating incident.)*
- Promotion happens **before** any worktree teardown for that story.
- A story that merges without a promotable spec is reported as a paper-trail gap, never passed over silently.
- Zero-byte or truncated specs are detected and reported rather than promoted.
- *Motivating evidence: 13 of 31 story specs were lost entirely and 8 more reduced to zero-byte husks before this became convention.*

#### FR-31: Spec-recovery assistance ← CAP-4
When a spec is missing, the operator is given the recovery search paths.
**Consequences:**
- Reports the ordered candidate locations — surviving run-worktree snapshots first, then the epics-derived contract fallback.
- Reports, never fabricates: a regenerated contract-only spec is labelled as such.

#### FR-32: Merge-subject conformance ← CAP-4
Merge commits carry the subject form downstream consumers key on.
**Consequences:**
- Marshal-performed merges emit the conventional subject; the exact form is configuration, not a literal in code.
- Deploy reports any merge in the wave whose subject does not conform.
- *Rationale: the program console's git-mode status detection keys on this string.*

#### FR-33: Sprint and console feed refresh ← CAP-4
Landing refreshes the derived status surfaces.
**Consequences:**
- The project's sprint status is updated from the journal and the merged set.
- Console data regeneration is invoked where configured.
- Discrepancies between the ledger and git history are reported, never silently resolved. *(Motivating evidence: a sibling project's sprint file drifted to 26/32 against an actual 32/32.)*

#### FR-34: Deploy is idempotent and re-runnable ← CAP-4
Re-running deploy after a partial failure completes the remaining steps.
**Consequences:**
- Already-promoted specs are not re-promoted or duplicated.
- Each step reports skipped / done / failed.

#### FR-35: No AI attribution in emitted artifacts ← CAP-4
Commits, PR bodies and comments Marshal emits carry no AI-attribution or courtesy preamble.
**Consequences:**
- No co-author trailer, model line, or generated-with line is added by Marshal.
- Attribution, if ever added, is opt-in configuration and default-off.
- *Grounding: the repo's standing convention, and the cautionary precedent of an editor vendor defaulting an AI co-author trailer on and reverting it after backlash — a commit trailer is part of the permanent authorship and blame record.*

#### FR-59: Landing rules are declared policy *(added 2026-08-01 — CAP-9, operator ruling via `docs/dreams/pr-lifecycle.md`; resolves Q-3)* ← CAP-9
The rules a repository demands for landing compose from the policy layers with per-key provenance, like every other governed value.
**Consequences:**
- Required checks, merge strategy, label rules, branch-retirement behaviour, and repo-specific triggers are policy keys, not memorized habits — including this repository's `maintenance` label on non-`recipes/` changes and the **ungated** `environment.yaml` sync check that the label does not suppress.
- The effective landing policy prints with each key's winning layer; an invalid landing policy is a preflight finding.
- *Grounding: five PRs hand-driven in one session (2026-07-31), each repeating the same written-but-unenforced sequence; one (#170) merged a real detector break because nothing in the landing path asked.*

#### FR-60: The last mile lands itself — `marshal land` *(added 2026-08-01 — CAP-9)* ← CAP-9
A story or wave that passed its gates lands on the integration branch without a human driving the sequence.
**Consequences:**
- `marshal land` opens or updates the PR, applies required labels, waits on required checks, merges by the declared strategy, retires the branch, and resyncs — idempotently and re-entrantly, so a half-landed story (PR open, checks green, merge never issued) converges on re-run.
- Refusal semantics mirror teardown (FR-8): no merge on a red required check, no merge past an unacknowledged advisory finding, no silent force — refusals are named findings in the common envelope.
- Every landing writes a journal verdict: which checks were required, which passed, what merged, under whose authority.
- Wrap-never-absorb carried unchanged: the engine keeps dev/verify/review/commit and deliberately leaves this gap open; Marshal fills it around the engine, in the supervisor's domain.

#### FR-63: Fleet-wide branch retirement *(added 2026-08-01 — `docs/dreams/durable-runs.md`)* ← CAP-21
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

#### FR-36: Fleet view ← CAP-5
The operator sees every loop home and its current state in one command.
**Consequences:**
- One row per home: project, branch, state (idle / running / paused-on-escalation / stopped), current story, elapsed time, budget consumed.
- Rows are derived from journals and run state, not from a hand-maintained file.

#### FR-37: Per-run detail ← CAP-5
The operator can drill into one run.
**Consequences:**
- Shows the story sequence with per-story gate verdicts, escalations, deferrals, and consumption.
- Machine-readable output is available for every human view.

#### FR-38: Escalation queue ← CAP-5
Runs paused on escalations are surfaced first.
**Consequences:**
- Paused-on-escalation rows are visually distinguished and sorted to the top.
- Each carries the reason and the artifact needing a decision.

#### FR-39: Ledger-versus-git reconciliation ← CAP-5
Status reports disagreements between the ledger and git history rather than trusting either blindly.
**Consequences:**
- A story marked done with no corresponding merge — and the converse — is reported as a named discrepancy.
- *Rationale: git history is the durable record; the sprint ledger is the local one, and it has drifted in practice.*

#### FR-40: Stable machine-readable status contract ← CAP-5
Status output has a versioned schema downstream consumers can depend on.
**Consequences:**
- A schema version accompanies the payload; additive changes do not bump it, breaking changes do.
- The console generator and any dashboard can consume it without scraping human output.

#### FR-62: Durability as a reported fleet property *(added 2026-08-01 — `docs/dreams/durable-runs.md`)* ← CAP-20
`marshal status` reports unpushed work as a finding on the owning row, not only in a separate detector's output the operator has to remember to run.
**Consequences:**
- A row whose branches carry local-only content is never reported clean — the same refusal the fleet view already applies to an unowned Dream row.
- The finding names the branch and the extent (line/commit count) so the operator does not have to cross-reference a second command to size the exposure.
- *Rationale: "is the fleet's work saved?" required four separate commands before this FR (`bmad-loop status`, `tmux capture-pane`, a manual detector run, and re-deriving from git) — the same operator question, asked twice, is the failure signature this FR closes.*

#### FR-65: The detector registry as a verb — `marshal check` *(added 2026-08-01 — `docs/dreams/one-front-door.md`, CAP-3/CAP-5)* ← CAP-23
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

#### FR-41: Skill-tree projection ← CAP-6
Skills are made available in every tree the configured adapters read from.
**Consequences:**
- After projection, each configured adapter's declared skill tree contains the project's skills.
- Projection uses the cheapest mechanism that the adapter and platform support, and the mechanism used is reported.
- The canonical source tree is authoritative; projected trees are derived and never edited in place.
- Re-projection after a source change converges; stale entries are removed.
- *Motivating evidence: `.agents/` does not exist in this repository; 89 skills live only under `.claude/skills/` (93 directories, 89 carrying a `SKILL.md`; verified 2026-07-30). Four of six adapter profiles would find nothing.*

#### FR-42: Projection drift detection ← CAP-6
Divergence between the canonical skill tree and a projected tree is detected.
**Consequences:**
- Reports added, removed, and modified skills per adapter tree.
- Runs as part of preflight when a non-default adapter is configured.

#### FR-43: Adapter probe ← CAP-6
The operator can capture what an adapter actually supports on this machine.
**Consequences:**
- Records binary presence and version, declared capabilities from the profile, and probe output.
- Sensitive values are redacted from the stored record.
- Probing an absent adapter reports it as unavailable rather than failing the command.

#### FR-44: Conformance smoke ← CAP-6
The operator can drive a canonical smoke story end to end on a named adapter.
**Consequences:**
- The smoke story exercises spec read → change → verify → commit and is adapter-agnostic.
- Result is pass / fail / unavailable with the failing stage named.
- Runs in a throwaway loop home and leaves no residue.

#### FR-45: Conformance matrix ← CAP-6
Per-adapter conformance results accumulate into a dated, tracked artifact, **keyed by host**.
**Consequences:**
- One row per adapter: status, adapter version, harness version, date, and the failing stage where applicable.
- Results older than a configured age are marked stale.
- The matrix is the only place Marshal makes a portability claim.

#### FR-46: Entry-file family drift check ← CAP-6
Divergence across the cross-tool instruction-file family is detected and reported.
**Consequences:**
- Checks presence and mutual consistency of the configured entry-file family.
- Reports drift with the specific divergence; **does not edit** the files. *(Ownership is Q-2.)*
- *Rationale: Cursor applies the union of AGENTS.md and CLAUDE.md, Claude reads only CLAUDE.md, Codex and Copilot read only AGENTS.md — instruction content is not isolated per-CLI, so drift cross-contaminates.*

#### FR-47: First-run acknowledgement per adapter ← CAP-6
Each adapter's first-run requirement and unattended-use caveat is surfaced once and recorded.
**Consequences:**
- On first configuration of an adapter, the profile's declared first-run requirement is presented as a required human action.
- A sustained-automation caveat is presented once per adapter and the acknowledgement recorded.
- Unacknowledged adapters are a blocking preflight finding, because an unanswered first-run dialog is indistinguishable from a session timeout.

#### FR-48: Adapter selection is project-scoped ← CAP-6
Adapter and model choices resolve per project.
**Consequences:**
- Two loop homes may run different adapters simultaneously without cross-configuration.
- The resolved adapter and per-stage models are echoed at launch and journaled.

---

### 7.7 Policy composition — `marshal` configuration layer

**Description.** Today one policy file carries a hand-edited model tier, a hard-coded project slug, and a comment block describing which stories to flip before which batch. Marshal composes run policy from layered sources so the operating rules become configuration a machine enforces.

**Functional Requirements:**

#### FR-49: Layered policy composition ← CAP-7
Effective run policy is composed from ordered layers with defined precedence.
**Consequences:**
- Layers: Marshal defaults → project policy → invocation flags, highest last.
- The composed policy is materialized into the loop home at init and echoed on request.
- Composition is pure: the same inputs produce the same output.

#### FR-50: Project-scoped policy without hand-editing ← CAP-7
Project-specific values are supplied by the project layer, never by editing a shared file.
**Consequences:**
- The worktree-seed path list is generated from the active project, not literal.
- Verify commands, the **initial** frozen-surface set, the merge-subject form, and **the per-epic declared surface allowlist** come from the project layer. Freezes declared *during* a run accumulate through the run record, not through policy (architecture AD-26).
- *The per-epic surface is mandatory, and its absence is a registered finding naming the epic — never a default.* Architecture AD-27 computes the effective surface as `policy_surface ∩ spec_surface`, so the per-epic entry is what a story spec is intersected against; AD-17 forbids "everything except", so an epic with no entry yields `∅` (every story fails) or `unevaluable` (every story blocks). There is no benign default, which is exactly why a missing entry must be reported as a policy gap rather than silently bricking the epic. *(Added 2026-07-30, **F-18**: AD-27 and this FR were edited in the same pass, and this — the FR that enumerates what the project layer supplies — did not list the key AD-27 requires.)*
- Switching projects requires no edit to any shared file.

#### FR-51: Per-story model tiering ← CAP-7
A story's declared difficulty selects the model tier without a between-batch config edit.
**Consequences:**
- Project policy maps a story difficulty class to per-stage models (dev, review, triage).
- Difficulty is read from the story's declaration; an undeclared story takes the mechanical default.
- The resolved per-stage model is journaled per story.
- Where the harness supports only run-level model selection, Marshal batches stories by tier and reports the batching. `[ASSUMPTION: batching is acceptable v1 behaviour; a per-story upstream key is an FR-58 request.]`
- *Motivating evidence: the live policy file carries a written "HARD-STORY BATCH PROCEDURE" naming which stories to flip and when.*

#### FR-52: Single harness seam ← CAP-7
All interaction with the underlying orchestrator passes through one internal module.
**Consequences:**
- No other module invokes the harness binary or parses its output.
- The seam declares the harness version range it supports.
- An architectural test fails the build if the seam is bypassed.
- *Rationale: this is what makes §5.4's fork fallback a bounded change rather than a rewrite.*

#### FR-53: Policy validation ← CAP-7
An invalid composed policy is rejected before launch.
**Consequences:**
- Unknown keys, unresolvable commands, and out-of-range values are reported with the layer that introduced them.
- Validation runs in preflight (FR-5).

#### FR-54: Configuration is inspectable ← CAP-7
The operator can see the effective policy and where each value came from.
**Consequences:**
- Output shows each effective key with its winning layer.
- Secrets are redacted.

---

### 7.8 Packaging and distribution

**Description.** Marshal ships the way the rest of the crew ships.

**Functional Requirements:**

#### FR-55: Package identity and layout ← CAP-8
Marshal ships as a Python distribution following the crew convention.
**Consequences:**
- Distribution `pyforge-marshal`, module `pyforge.marshal`, console script `marshal`.
- Source lives in the repo's shared packages workspace alongside its siblings.
- `import pyforge.marshal` succeeds from a clean environment install.

#### FR-56: Conda and wheel artifacts ← CAP-8
Marshal is installable as a conda package and as a wheel.
**Consequences:**
- The conda recipe declares the harness as a run dependency, pinned to the supported version range (FR-52).
- Wheel and sdist build from the same source tree.
- Installing the conda package yields a working `marshal --help` and `marshal --version` with the harness resolvable.
- *This is the operative half of the §5 wrap decision: one install command yields the whole stack.*

#### FR-57: Version and capability reporting ← CAP-8
`marshal --version` reports Marshal's version and the resolved harness version.
**Consequences:**
- Both versions appear in the journal for every run.
- A harness outside the supported range emits a prominent warning and is a blocking preflight finding when the mismatch is major.

#### FR-58: Upstream contribution register ← CAP-8
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
- **No fleet-level resource budgeting across concurrent runs.** Per-run ceilings only. (Q-4.) *(AMENDED 2026-09-14, folding the operator's 2026-09-09 answer: this is now a **decided** Non-Goal for v1 rather than a deferral awaiting evidence. A cross-run budget would be the first thing to need shared mutable state across loop homes and therefore the first to break C-3's loop-home write boundary.)*
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
- **NFR-12 — Machine-readable everything.** Every human-facing output has a machine-readable counterpart with a stable, versioned schema; plans and reports are machine-readable under `--json` and human-readable by default. *(Absorbed the seed installer's `NFR-O1` on 2026-08-08 — it said the same thing without the schema-stability half, so it retired rather than coexisting as a near-duplicate.)*
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
- **C-11.** *(Added 2026-09-14, folding `spec-pyforge-marshal`'s 2026-09-09 operator answer to its F-4.)* **The trust model is declared, and in v1 it is advisory.** The escape hatch for privileged changes is an operator-attributed journal entry admitted at the **call surface only** (`core/journal.py:159`). No authentication primitive exists in the package; the governed agent is **trusted**, and attribution is an audit record rather than an enforcement boundary. This is stated, not hidden: C-10 above is precisely why — a worktree isolates the filesystem and branch, not the process, so an unforgeable attribution would need isolation Marshal deliberately does not provide. The contract becomes unforgeable before the dispatch journal serves a second principal; until then, advisory is the honest description.
- **C-12.** *(Added 2026-09-14, folding `spec-pyforge-marshal`'s 2026-09-09 operator answer to its F-5.)* **There is no unattended mid-run freeze writer, by design.** Under the `none` and `per-epic` gate modes no operator is present and a story may not declare its own freeze; mid-run freezes therefore require **per-story approval**. The vocabulary and the writer constraint already ship (`KIND_FREEZE_DECLARED` / `KIND_FREEZE_REMOVED`, `core/journal.py:152-163`); what was missing was the statement that the absence of an unattended writer is the decision, not a gap.

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
4. **Q-4 — Fleet-level resource budgets.** Per-run ceilings ship in v1; cross-run budgeting is deferred. Revisit when two projects routinely run heavy loops concurrently. **ANSWERED 2026-09-09 (operator, folded in here 2026-09-14 — recorded in `spec-pyforge-marshal` as its Q-11): a cross-run (fleet-level) budget is OUT of scope for v1, for the reason the question itself names — it would be the first thing to need shared mutable state across loop homes, and therefore the first to break the loop-home write boundary (C-3). The deferral is now a decision with a stated cause, not an open item. § 8's Non-Goal is amended to match.**
5. **Q-5 — OpenTelemetry `gen_ai.*` emission.** Deferred; the conventions moved repositories in June 2026 and remain Development-stability with live renames. Revisit when the conventions stabilize or an external consumer requires them. **ANSWERED 2026-09-09 (operator, folded in here 2026-09-14 — `spec-pyforge-marshal` Q-12): deferred with the resumption condition now NAMED rather than left to judgement — emission waits until the semantic conventions reach **stable**. Paying v1 cost against Development-stability attributes that are still being renamed buys instrumentation that must be redone. The run journal carries equivalent information in a self-owned format until then.**
6. **Q-6 — ACP migration trigger.** Proposed trigger: the upstream harness gains an ACP client path, **or** two adapters Marshal must support ship ACP-only, **or** ACP schema v2 reaches stable with the Claude adapter's known gaps closed. Until then, the harness's declarative profiles are the adapter contract. **ANSWERED 2026-09-09 (operator, folded in here 2026-09-14 — `spec-pyforge-marshal` Q-13): trigger one has **FIRED** — bmad-loop 0.9.0 shipped a sanctioned `copilot` profile plus `copilot --acp`, so the harness has gained an ACP client path. One trigger alone does **not** start the migration; the declarative profiles remain the adapter contract until a second trigger fires. Recorded as a fired-trigger state, not as a scheduled migration.**
7. **Q-7 — Idle threshold default.** 25 minutes is carried from the production stopgap. Needs one wave of data to confirm it does not false-positive on legitimately slow verify steps. **ANSWERED 2026-09-09 (operator, folded in here 2026-09-14 — `spec-pyforge-marshal` Q-14): the 25-minute default **stands**, and the "one wave of data" becomes an acceptance clause rather than an open experiment — the threshold is real and operator-tunable, and it holds until a wave is actually *read* from the dispatch journals. The question closes; the measurement obligation survives as a condition on changing the number, not as a blocker on shipping it.**
8. **Q-8 — Difficulty declaration source.** FR-51 reads story difficulty from the story's declaration; whether that lives in the story spec frontmatter or the epics document is an architecture-phase call.
9. **Q-9 — Conformance smoke story content.** What minimal story exercises spec→change→verify→commit while staying adapter-agnostic and cheap? Architecture phase.

**Q-10 … Q-14 added and resolved 2026-07-31 (architecture audit).** Five candidate capabilities were raised against this PRD, recorded as open questions rather than features, and resolved by operator ruling the same day. **Applied 2026-07-31/08-01:** the Spec re-render landed them as CAP-9, four constraints, and non-goal reaffirmations; this PRD carries the FR-level decomposition (FR-59/FR-60) and the §5.2/§7.2 re-scopes. None became an FR beyond what its decision states.

10. **Q-10 — Serialization of shared Tier-2 writes.** **RESOLVED: decomposed; no mutex engine.** Tracked Tier-2 files are per-worktree copies, serialized by git at the push/PR boundary; the real hazard is semantic lost-update through clean merges of *regenerated* artifacts. Rule: merge append-only inputs, re-derive regenerated outputs on main after landing (an Epic 4 deploy-ordering rule). The genuinely shared canonical Tier-3 store gets an advisory append lock. The journal's two-writer problem is the Spec's F-6, already carried.
11. **Q-11 — Tool-surface brokering.** **RESOLVED: yes, scoped.** The project's tool surface is declared in the project policy layer; `marshal init` renders a project-scoped `.mcp.json` into the loop home (the adapter-seed pattern); preflight probes resolvability. The user-scoped registry is never touched. Post-MVP, on the portability/adapter surface.
12. **Q-12 — Escalation knowledge capture.** **RESOLVED: pull model.** Marshal's half is one FR-17 consequence — the resume entry records a reference to the resolving decision. Scribe ingests from run journals; that story is Scribe's backlog. No station writes across the boundary.
13. **Q-13 — Enterprise plugin seam.** **RESOLVED: dissolved into existing seams; IDE exclusion retained.** Internal MCP servers → the Q-11 tool surface; proprietary/third-party agent CLIs → FR-52 adapter profiles; design bridges → Herald; internal skills → FR-45 projection. Site-wide policy vs the no-fourth-layer constraint resolves at install time — the seed installer (then genesis-installer) materializes site config into the Marshal-defaults layer, keeping runtime composition three layers and pure. No plugin-registry subsystem.
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

## 15. The seed installer — `marshal seed`

*(Naming re-issued 2026-08-10 — binding names are the marshal-seed form; prose "Genesis"
is the capability's satellite-era name and binds nothing.)*

**Integrated 2026-08-08.** This section was a satellite — *"Satellite: Genesis Installer
PRD"*, a second sub-product with its own parallel numbering — from its 2026-08-02
consolidation until now. It is no longer. The content is Marshal's own, its requirements
continue Marshal's own sequence, and the name `genesis` is retired. The original standalone
document remains at
`archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-genesis-installer-2026-07-25/prd.md`;
`.memlog.md` and `archive/` are untouched.

**What changed in the integration** (nothing below this block was rewritten for content):

| Namespace | Was | Now | Why |
|---|---|---|---|
| Functional requirements | `FR1`..`FR62` (no dash, own island) | **`FR-66`..`FR-127`** | Continues Marshal's own `FR-1`..`FR-65`. Sequential, gap-free, duplicate-free — verified against `citation-map.md`, all 62 mapped, all 83 references rewritten. |
| Open questions | `OQ-1`..`OQ-9` | **`Q-17`..`Q-25`** | Continues Marshal's own `Q-1`..`Q-16`. Same kind of artifact; `Q-17` was confirmed non-existent before the range was claimed. |
| Observability NFR | `NFR-O1` | **retired** | Redundant with Marshal's own **NFR-12**, which is strictly stronger (it additionally requires a stable, versioned schema). NFR-12 absorbs its `--json`-and-human-default specificity rather than the pair coexisting. |
| Success criteria | `SC-01`..`SC-10` | **`SC-01`..`SC-10`, adopted as-is** | Marshal had **no** `SC-` namespace; its `SM-1`..`SM-7`/`SM-C1`..`SM-C3` are *metrics* — measured, trended, never binary. `SC-*` are per-release *acceptance criteria*. Mapping one onto the other would conflate two different concepts to save a prefix. Both stand; the distinction is stated here. |
| Kill criteria | `K-01`..`K-03` | **`K-01`..`K-03`, adopted as-is** | Marshal had no kill-criteria concept at all. Folding them anywhere would lose them; a falsifier with no home is a falsifier that never fires. |

**One caution, carried from `citation-map.md`:** `FR-66`..`FR-69` were briefly assigned to
`spec-pyforge-testing-charter` on 2026-08-02 and reverted the same session. They are now
permanently the seed installer's. The testing charter's requirements are decomposed in
§ 16 below under their own numbers.

**Verb surface.** Every command in this section reads `marshal seed <verb>` — the collision
resolution recorded in AD-51/AD-54 and Q-17's predecessor. `marshal init` (loop home, by
slug) and `marshal check` (detector registry, this repo) are different, shipped commands and
are untouched.

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

**Part II — the seed installer (integrated; formerly the pyforge-genesis satellite — name retired, re-issued 2026-08-10 to `pyforge.marshal.seed` / `marshal seed <verb>`)**

### Executive Summary

Genesis packages this repository's proven operating model as an installable tool with
two verbs — **`marshal seed init`** (greenfield: a new repository born Dream-first) and
**`marshal seed adopt`** (brownfield: layer the model onto an existing repo without disturbing
what runs) — plus the two verbs that make an install *stay* correct: **`marshal seed check`**
(read-only conformance, non-zero exit, CI-runnable) and **`marshal seed update`** (take a later
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

**SC-01.** A second repository created by `marshal seed init` runs a full Dream → spec → epics →
loop-driven build, and later **takes a model upgrade via `marshal seed update` with no hand
edits** — `marshal seed check` green before and after.

#### Supporting metrics (all mechanically testable)

| ID | Criterion | Measured by |
|---|---|---|
| SC-02 | `marshal seed adopt --dry-run` against `local-recipes` at the shipped model version produces an **empty plan** | the reference-oracle test |
| SC-03 | `marshal seed adopt` is idempotent — second run ⇒ empty plan, zero files changed | integration test |
| SC-04 | `marshal seed adopt` on a hand-edited managed region **refuses and reports**; does not overwrite | integration test |
| SC-05 | `marshal seed adopt --apply` on a dirty git worktree refuses | integration test |
| SC-06 | `marshal seed init` + `marshal seed check` green **offline, zero network calls** | egress-counter test (warden's established pattern) |
| SC-07 | A simulated breaking model change (model v1 → v2) is absorbed by a migration in an installed repo with no manual edits | migration integration test |
| SC-08 | `marshal seed update` **cannot** write to `docs/dreams/**` or `**/planning-artifacts/**` | write-scope guard test |
| SC-09 | `marshal seed init` to a working Dream-first repo in **< 5 minutes** wall-clock (vs. the 10-phase manual setup plan) | timed smoke test |
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
runs `marshal seed init ../pyforge-scribe --slug pyforge-scribe --agents claude,cursor`. Genesis
materializes `docs/dreams/` (README, frontmatter contract, one seed Dream stub named for
the slug), the tier layout with its gitignore rules, `AGENTS.md` carrying the portability
contract, `CLAUDE.md` and `.cursor/rules/specs.mdc` generated from that contract, the BMAD
multi-project subtree with `PROJECTS.md` and its first row, `scripts/bmad-switch`, and the
drift detector wired into CI. He writes the Dream, runs `bmad-spec`, and the loop starts.
Total elapsed before the first Dream: under five minutes, versus reading ten phases of a
562-line plan.

#### J2 — "Adopt the model into a repo that already ships"

A team has a working data-platform monorepo — CI, releases, an existing `CLAUDE.md`, and a
`docs/adr/` convention they like. They run `marshal seed adopt` (dry-run by default). Genesis
prints a plan: 9 artifacts absent (will create), 3 present-conformant (skip), 1
present-divergent (`CLAUDE.md` — will insert a managed region at an anchor, leaving all
existing content), 1 present-legacy (`docs/adr/` — recorded, preserved, untouched). Nothing
has been written. They review the plan in a PR, run `marshal seed adopt --apply`, and their
build still works because Genesis never touched a file it did not name.

#### J3 — "Take a model upgrade six weeks later"

The model ships v1.3.0: the durable-story-specs convention adds a `planning-artifacts/specs/`
rule to the tier table, and `bmad-switch` gains an atomicity fix. An installed repo runs
`marshal seed check` in CI, which fails with `model-behind: repo at 1.2.0, available 1.3.0`. The
maintainer runs `marshal seed update` — a plan is written naming two migrations and three files.
He reviews it, runs `marshal seed update --run`. The tiers managed region in `AGENTS.md` is
replaced; `scripts/bmad-switch` is regenerated wholesale; the derived adapters are
recomputed. His Dreams, PRDs, and epics are untouched — structurally unreachable from the
update path. `marshal seed check` is green.

#### J4 — "The model and the repo disagree"

An engineer hand-edits the tiers block inside `AGENTS.md` because a rule did not fit. Next
CI run, `marshal seed check` reports `managed-region-modified: AGENTS.md#tiers (hash mismatch)`
and exits non-zero. He has three sanctioned moves: revert; delete the markers (a deliberate,
greppable opt-out that Genesis records and thereafter respects); or add the path to
`skips[]`. What he cannot do is diverge silently — which is the entire point, because the
agents reading that file would otherwise follow a rule the model does not have.

#### J5 — "Verify the model is still extractable"

A CFE retro lands a convention change directly in `local-recipes` (out-of-band, as always
happens). CI runs `marshal seed adopt --dry-run` against the repo itself. The plan is non-empty:
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
FR-66–FR-71 encode and SC-10 tests.

#### The classification rule

> Classify each artifact by **who must be able to change it** and **how an installed repo
> takes a later model upgrade for it.**

| Class | Definition | Behavior on `marshal seed update` | Behavior on hand-edit |
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

Genesis **verifies presence and floor** for these (FR-95) and never installs them.

##### COPIED · MANAGED

| Artifact | Why managed |
|---|---|
| `scripts/bmad-switch` | executable model machinery with a known production incident (the 10-hour marker/symlink desync); bug fixes **must** propagate to installed repos |
| `scripts/bmad-loop-worktree` | concurrent loop homes; same reasoning |
| `scripts/bmad_drift_check.py` (the detector) | must run locally, offline, in the adopting repo's CI; this is the conformance engine and it evolves with the model |
| `docs/dreams/README.md` | the Tier-0 contract itself — the Dream frontmatter schema, the flow diagram, the conventions |
| The model's own rule text (tier tables, portability contract) | delivered *into* hybrid files, not as standalone files — see HYBRID |
| CI workflow that runs `marshal seed check` + the detector | mechanical; no reason for a repo to own it |
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

Enforced by code and proven by test (FR-100, SC-08), not by convention. This is the
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
| `init` semantics | `marshal seed init` creates **the repository** the specs will live in | `marshal init --spec …` initializes **a build** from a spec |
| `scripts/bmad-switch`, `scripts/bmad-loop-worktree` | **delivers** them (MANAGED class) and keeps them current | **runs** them; owns their behavior and evolution |
| `.bmad-loop/policy.toml` | **seeds** it | **owns and rewrites** it per project |

The overlap point is real and named: the two scripts are Marshal's per the 2026-07-23
ownership review, but they must be *installed* to exist in a new repo at all. Resolution:
**Marshal owns the source; Genesis owns the delivery.** A change to `bmad-switch` lands in
Marshal's tree and is picked up by Genesis's manifest at the next model version. Genesis
never forks them.

#### Genesis ↔ Doctor

`marshal seed check` asks *"does this repo conform to the model?"*; `doctor check` asks *"is this
machine able to run the factory?"* Genesis's REFERENCED-dependency verification (FR-95)
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
3. **`marshal seed adopt`** — detect → plan → confirm → apply, dry-run default, idempotent,
   `present-legacy` aware.
4. **`marshal seed check`** — read-only, non-zero exit, CI-shaped output.
5. **`marshal seed init`** — greenfield, on the same engine as adopt.
6. **`marshal seed update`** + migration runner — two-phase plan/apply, version-ordered,
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

- **FR-66** — The model is declared as **data** (a manifest file inside the package), not as
  code branches. Each entry carries: path or path-pattern, class, applicable model-version
  range, and (for HYBRID) its region names and anchors.
- **FR-67** — Five classes are supported: `referenced`, `copied-managed`, `copied-seeded`,
  `generated-derived`, `hybrid-managed-region`.
- **FR-68** — The manifest supports an explicit `unclassified-deferred` state so that
  deferral is enumerated rather than silent.
- **FR-69** — A coverage check verifies that every artifact Genesis knows about carries
  exactly one class; an unclassified artifact is a HARD failure. (Mirrors
  `bmad_drift_check.py`'s `uncovered` finding.)
- **FR-70** — The manifest is versioned by **model semver**, independent of the
  `pyforge-genesis` package version. Both are recorded in installed state.
- **FR-71** — The manifest declares the **never-write path set** (§ *The Extraction
  Manifest*), which the apply and update paths enforce.

#### `marshal seed init` (greenfield)

- **FR-72** — `marshal seed init <path>` creates a Dream-first repository tree at `<path>`,
  materializing every manifest artifact applicable to a new repo.
- **FR-73** — `init` accepts `--slug` (the first BMAD project slug, defaulting to the
  directory name) and `--agents` (comma-separated adapter selection).
- **FR-74** — `init` seeds exactly one Dream stub at `docs/dreams/<slug>.md` conforming to
  the Tier-0 frontmatter contract (`title`, `type: dream`, `owner`, `status: seeded`).
- **FR-75** — `init` creates the BMAD multi-project subtree:
  `_bmad-output/projects/<slug>/{planning-artifacts,implementation-artifacts}`,
  `.bmad-config.toml`, `planning-artifacts/specs/README.md`, and `PROJECTS.md` with the
  first row.
- **FR-76** — `init` writes the `.gitignore` model region covering the tier rules: the
  gitignored `implementation-artifacts/`, the two `_bmad-output` compatibility symlinks,
  `_bmad/custom/.active-project`, `.bmad-loop/runs/` and `cache/`, and
  `_bmad-output/projects/*/.bmad-config.user.toml`.
- **FR-77** — `init` writes the state file recording `mode: init`, model version, CLI
  version, selected agents, and the per-artifact hashes.
- **FR-78** — `init` refuses to run into a non-empty directory unless `--force`; the
  documented path for an existing repo is `adopt`.

#### `marshal seed adopt` (brownfield)

- **FR-79** — `marshal seed adopt` runs **detect → plan → confirm → apply** and is **dry-run by
  default**; `--apply` (or `--yes` for unattended use) executes.
- **FR-80** — Detect classifies each manifest artifact in the target repo as `absent`,
  `present-conformant`, `present-divergent`, or `present-legacy`.
- **FR-81** — `present-legacy` artifacts are **recorded and preserved, never modified or
  deleted**, and are listed in the state file's `legacy[]`.
- **FR-82** — The plan is a **machine-readable artifact** written to disk (not only printed),
  listing per artifact: path, class, detected state, proposed action, and rationale.
- **FR-83** — Apply materializes only what the plan names. Artifacts already present are
  preserved unless their class is `copied-managed` or `generated-derived`.
- **FR-84** — `adopt` is **idempotent**: a second run on an unchanged repo produces an empty
  plan and writes nothing.
- **FR-85** — `adopt --apply` refuses on a dirty git worktree, and refuses outside a git
  repository.
- **FR-86** — `adopt` refuses (with a specific, actionable message) when a managed region or
  managed file has been hand-modified, unless `--force`.
- **FR-87** — `adopt` accepts `--skip <glob>` (recorded in state) and honors previously
  recorded skips on subsequent runs.

#### `marshal seed check` (conformance)

- **FR-88** — `marshal seed check` is **read-only** and never writes to the repo (state file
  included).
- **FR-89** — `check` exits non-zero on any HARD finding; `--strict` additionally fails on
  DRIFT findings.
- **FR-90** — Findings are typed and stable, at minimum: `artifact-missing`,
  `managed-file-modified`, `managed-region-modified`, `managed-region-missing`,
  `derived-stale`, `model-behind`, `state-invalid`, `never-write-violation`,
  `referenced-dep-missing`.
- **FR-91** — `check --json` emits a machine-readable report suitable for CI annotation.
- **FR-92** — `check` reports the repo's model version against the model version available
  in the installed package (`model-behind` / current / ahead).
- **FR-93** — `check` runs offline and completes in under 5 seconds on a repo the size of
  `local-recipes`.

#### `marshal seed update` + migrations

- **FR-94** — `marshal seed update` is **two-phase**: the default invocation writes a plan and
  changes nothing; `--run` applies the plan.
- **FR-95** — Update verifies REFERENCED dependencies against their declared floors and
  reports (does not install) anything missing or below floor; delegates to `doctor check`
  when available.
- **FR-96** — Migrations are ordered by model semver, applied **exactly once**, and recorded
  in state's `migrations_applied[]`.
- **FR-97** — Migrations may only touch `copied-managed`, `generated-derived`, and
  `hybrid-managed-region` artifacts. Touching `copied-seeded` requires an explicit
  interactive/`--yes` opt-in and is reported as an offer, never imposed.
- **FR-98** — Update regenerates `copied-managed` files wholesale and recomputes
  `generated-derived` files, after hash-guard checks pass.
- **FR-99** — Update replaces only the marked span of `hybrid-managed-region` files.
- **FR-100** — Update **cannot** write to any path in the never-write set (FR-71); an attempt is
  a hard error and a test asserts it.
- **FR-101** — `marshal seed update --force` maps to Copier `run_recopy` semantics (discard local
  evolution of managed artifacts) and requires explicit confirmation.

#### State file

- **FR-102** — Genesis writes one tool-owned state file recording: `model_version`,
  `seed_model_version`, `adopted_at`, `last_update`, `mode`, `agents[]`, `managed[]` (path +
  class + content hash), `skips[]`, `legacy[]`, `migrations_applied[]`.
- **FR-103** — The state file carries a prominent do-not-hand-edit header.
- **FR-104** — State is validated against a JSON schema on every read; an invalid state file
  is a `state-invalid` finding, not a crash.
- **FR-105** — Genesis never hand-edits Copier's answers file; if Copier's answers file is
  used it is treated as a second tool-owned file.
- **FR-106** — Content hashes cover managed files and managed regions, enabling FR-86 / FR-90.
- **FR-107** — The state file is git-tracked (it is repo metadata, not scratch).

#### Managed regions

- **FR-108** — A managed region is delimited by begin/end markers carrying the region name and
  the model version that wrote it.
- **FR-109** — Update replaces the span between markers by **pure text substitution** — never
  a three-way merge — so a half-merged file is not representable.
- **FR-110** — Marker syntax is **per file format** (HTML comments for markdown, `#` comments
  for `.gitignore` / TOML / YAML), resolved through a format registry.
- **FR-111** — If markers are absent in a file that should carry a region, Genesis inserts the
  region at a declared **anchor** (e.g. after the first `# Heading`), or appends when no
  anchor matches.
- **FR-112** — Deleting the markers is a **sanctioned permanent opt-out**: Genesis records it
  in state and does not reinsert on later runs. (Mirrors Copier's locally-deleted-path rule.)
- **FR-113** — Nested or overlapping regions are rejected with a specific error.

#### Agent adapter fan-out

- **FR-114** — The neutral contract (tiers, portability, Dream-first workflow) has exactly one
  source in the manifest; all adapter files derive from it.
- **FR-115** — V1 supports four adapters: Claude Code (`CLAUDE.md`), Cursor
  (`.cursor/rules/specs.mdc`), GitHub Copilot (`.github/copilot-instructions.md`), Gemini
  (`GEMINI.md`).
- **FR-116** — Adapter selection is per-repo, recorded in state, and changeable later
  (`marshal seed adopt --agents …` adds adapters idempotently).
- **FR-117** — For an adapter file that already exists with repo-specific content
  (`CLAUDE.md` is the common case), the model content is delivered as a **managed region**
  rather than by overwriting the file.

#### Templates, distribution & CLI

- **FR-118** — Model templates ship **inside** the `pyforge-marshal` package (as `pyforge/marshal/seed/templates/` package data — re-issued 2026-08-10, correct-course); no runtime fetch
  is required for any verb.
- **FR-119** — `--template <path|url>` overrides the in-package templates, for development and
  for teams that fork the model.
- **FR-120** — Genesis wraps Copier via its **public API only** (`run_copy`, `run_update`,
  `run_recopy`); no reliance on `Worker` internals or private modules.
- **FR-121** — Copier's code-executing template features remain gated behind an explicit
  `--unsafe` flag.
- **FR-122** — Genesis is distributed as a pixi workspace member producing a conda package,
  plus wheel/sdist, with console entry point `genesis`.
- **FR-123** — All verbs support `--json` for machine consumption and `--quiet` for
  unattended runs.
- **FR-124** — All mutating verbs support `--dry-run` explicitly (and default to it where
  FR-79 requires).
- **FR-125** — `marshal seed version` reports both the CLI version and the bundled model version.
- **FR-126** — Non-zero exit codes are distinct and documented per failure mode (conformance
  failure, precondition failure, internal error).
- **FR-127** — A `marshal seed explain <artifact>` verb prints an artifact's class, rationale, and
  update behavior — the model documenting itself to the agents that read it (D1).

---

### Non-Functional Requirements

#### Reliability & safety

- **NFR-R1** — No verb may leave the repo in a partially-applied state: apply is
  transactional per plan, or reverts.
- **NFR-R2** — Git is the undo mechanism; every mutating verb requires a clean worktree so
  `git checkout .` fully reverts.
- **NFR-R3** — Managed-region substitution never produces conflict markers (a consequence
  of FR-109).
- **NFR-R4** — The never-write guard (FR-100) is enforced at the lowest write primitive, not
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

- **NFR-S1** — No execution of untrusted template content by default (FR-121).
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
- ~~**NFR-O1**~~ — *Retired 2026-08-08 as redundant with **NFR-12**, which states the same
  requirement and additionally demands a stable, versioned schema. Its `--json`-and-
  human-default wording was folded into NFR-12 verbatim; nothing was dropped.*

---

### Assumptions

1. **[ASSUMPTION]** Genesis targets git repositories only; non-git targets forfeit the
   update story entirely.
2. **[ASSUMPTION]** The model has genuinely stabilized (the Dream's gate). Evidence: atlas
   (32 stories) and warden (31 stories) both shipped through it; the durable-story-specs
   convention closed the last known hole on 2026-07-25.
3. **[ASSUMPTION]** `scripts/bmad_drift_check.py` (662 lines, with a HARD/DRIFT/INFO
   severity model and a coverage check that already HARD-fails unclassified files) can seed
   `marshal seed check` rather than requiring a from-scratch build. **Not yet validated against
   the code** — an early spike should confirm before Epic scoping hardens.
4. **[ASSUMPTION]** Copier's `run_copy` / `run_update` / `run_recopy` signatures are stable
   across 9.x.
5. **[ASSUMPTION]** Copier's answers-file path is template-configurable (affects FR-105).
6. **[ASSUMPTION]** HTML-comment markers are unambiguous in the specific markdown files in
   the manifest.
7. **[ASSUMPTION]** First two adopters are `local-recipes` (oracle) and one greenfield
   pyforge sibling; external adoption is post-V1.
8. **[ASSUMPTION]** Marshal will accept ownership of `bmad-switch` / `bmad-loop-worktree`
   *source* while Genesis owns *delivery* — this needs Marshal's PRD to agree.

### Open Questions (carried to architecture)

1. **Q-17** — CLI framework: typer + rich (both already pinned; better for the
   plan/diff/confirm UX) vs argparse (warden's lean-engine precedent). Note Copier already
   pulls in prompt-toolkit / questionary / pygments regardless.
2. **Q-18** — One state file, or Genesis state alongside Copier's `.copier-answers.yml`?
   Depends on assumption 5.
3. **Q-19** — Exact marker syntax and the format registry's initial coverage (FR-110).
4. **Q-20** — Does `marshal seed check` copy, extract, or re-implement `bmad_drift_check.py`?
   Depends on assumption 3. Extraction into the package is attractive but couples
   `local-recipes` to a Genesis release.
5. **Q-21** — Where does the manifest live physically — one YAML/TOML file, or one file per
   class? Affects FR-66 and NFR-M1.
6. **Q-22** — Anchor semantics for FR-111 when a repo's `CLAUDE.md` has an unusual structure.
   Fallback-to-append is specified; is that always safe?
7. **Q-23** — Does the plan artifact get committed by convention (like Nx's
   `migrations.json`), and if so, where — and is it gitignored or tracked?
8. **Q-24** — How does a repo *leave* the model (`marshal seed eject`)? Not in V1 scope, but the
   state file's design should not preclude it.
9. **Q-25** — Model deprecation path: the manifest marks `docs/specs/` legacy today. Does
   the model define a migration from Tier-1 legacy to Tier-2, or only preserve?

---

## 16. The station's own backlog — capabilities absorbed 2026-08-08

**Why this section exists, and why it did not before.** Until today this PRD decomposed
**two** of Marshal's twenty-four Specs: its own (`FR-1`..`FR-65`) and the seed installer's
(§ 15). The other ten open Specs had no FR, no epic and no story — not by oversight, but by
a rule recorded in this document's `.memlog.md` on 2026-08-02:

> capabilities that are repo-level tooling not touching `src/shared/packages/pyforge-marshal/`
> get NO marshal FR — "governed by [their own] spec itself"

That rule caused a real revert: an `FR-66..FR-69` decomposition of the testing charter was
added and withdrawn the same session under it.

**The rule is amended, and this is the amendment.** It was checked against every open
Marshal Spec on 2026-08-08: **not one of the ten declares a `surface:` path inside
`src/shared/packages/pyforge-marshal/`.** The rule therefore excluded all of them,
permanently, by construction — while several are unambiguously marshal-CLI work in their own
words (`loop-home-fleet-refresh` says it "extends `marshal homes`/`init`/`preflight`";
`sprint-status-auto-promote`'s job is `marshal deploy promote`, which shipped in Epic 4).
The `surface:` fields were written before those verbs existed.

> **Amended rule (2026-08-08).** A capability decomposes into this PRD **iff its Dream is
> `owner: marshal`** — not iff it touches a particular directory. `surface:` declares *what
> ships*; it never decides *whether the station is accountable*. The station is the unit of
> accountability (Charter §5), so the station's PRD covers what the station owns.

Two Specs are deliberately **not** decomposed here, and are recorded rather than dropped:

- **`jira-github-projects-sync`** — re-owned to **Steward** on 2026-08-08 and moved out of
  this project entirely. Under the build-line/estate seam it is an estate integration
  service, not build-line machinery. See `pyforge-steward`'s chain.
- **`agentic-sdlc-autonomy`** — a *standing position*, explicitly "not a deliverable" by its
  own text. It has nothing to decompose; requiring an FR would manufacture one.

### 16.1 Test architecture governance — `spec-pyforge-testing-charter`

**Description.** Every station already has real pytest coverage; what is missing is
narrower and more mechanical than "write tests." Realizes the charter's CAP-1..CAP-5.

#### FR-128: Correct fleet-wide TEA signal ← CAP-86
The dashboard's `tea` completeness signal reads the canonical test location.
**Consequences:** `_stage_globs` resolves `src/shared/packages/pyforge-<slug>/tests/`, not the
planning-scaffold `_bmad-output/projects/<slug>/tests/`; atlas and warden report populated,
not pending.

#### FR-129: One automation path, run for real per station ← CAP-87
`bmad_tea_playwright.py` produces every station's `test-architecture.md`.
**Consequences:** all 8 stations have one; output containing a `TBD` token is a failed run,
not a delivered document; the filename convention is reconciled across stations.

#### FR-130: Shared test-support package ← CAP-88
A `pyforge-testing-kit` exists, seeded from Marshal's four real mocks rather than rewritten.
**Consequences:** CLI-runner, page-object, DB-factory and auth/HTTP/time primitives ship; at
least one station other than the seed source imports from it. *(Open: Q-26 — whether this is
its own leaf or a module of `pyforge-core`, see § 16.8.)*

#### FR-131: Coverage gate enforced, not just measured ← CAP-89
A PR that drops a touched package below its station's threshold fails CI, naming the module.
**Consequences:** per-station unit >80% / integration >70% gates run in CI; the failure names
the uncovered module rather than printing a percentage.

#### FR-132: Test architecture stays current as stories land ← CAP-90
Re-running the generator keeps each document true as code lands.
**Consequences:** regeneration is idempotent on an unchanged tree; a station whose tests moved
produces a changed document rather than a stale one.

### 16.2 Loop-home fleet refresh — `spec-loop-home-fleet-refresh`

**Description.** Keeping 8 loop homes current with `main` is a hand-run two-step ritual —
lived on 2026-08-08 when all of them were found 227 commits stale.

#### FR-133: Fleet-wide staleness detection ← CAP-91
One command reports every loop home's distance from `main`.
**Consequences:** each home reports its behind-count and current ref; a home that cannot be
read is reported, never skipped silently.

#### FR-134: Fast-forward and push with a clean-worktree check ← CAP-92
Refresh is fast-forward-only and refuses on a dirty tree.
**Consequences:** a dirty home is refused by name, not merged; no non-fast-forward merge is
ever attempted; the push targets `loop/<slug>` only.

#### FR-135: Policy re-render as a checked step of the same refresh ← CAP-93
The `marshal config --write-harness-policy` step is part of refresh, not a separately
remembered second command.
**Consequences:** a refresh that fast-forwards but fails to re-render reports the home as
incompletely refreshed; each step reports `done | skipped | failed` (AD-21).

### 16.3 Landing-to-ledger promotion — `spec-sprint-status-auto-promote`

**Description.** A story landing does not, by itself, update the tracked ledger or the board;
three live incidents in one session. **This is the Marshal half of the Marshal↔Steward
contract** (§ 17).

#### FR-136: Promotion runs on landing, not on memory ← CAP-94
Landing triggers ledger promotion mechanically.
**Consequences:** a landed story's tracked-ledger entry is current without a separately
remembered command; the trigger is deterministic, not heuristic.
**2026-09-02:** the promote commit is published onto `origin/<base>` from an
isolated detached worktree (CAP-5). It must not be committed on the operator
`main` checkout — that leftover diverged local `main` after every `gh pr merge`.

#### FR-137: Staleness is detectable on its own ← CAP-95
A check answers "is the tracked ledger behind git?" independently of any run.
**Consequences:** ledger-versus-git discrepancies are reported per key with the direction of
the drift.

#### FR-138: The check is real, never approximated ← CAP-96
The comparison reads git and the ledger, never infers from the feed.
**Consequences:** no story status is derived from `sprint-status.yaml` (a statement of intent);
the oracle is merge history.

#### FR-139: Promotion never races the orchestrator, and never downgrades ← CAP-97
Single-writer discipline, and terminal states are monotonic.
**Consequences:** concurrent promotion attempts serialize on a lock; **a transition moving any
key backwards from `done` is refused and named, not written** — closing DW-SYNC-2026-08-08-1,
in which a stale Tier-3 feed silently overwrote the tracked ledger and dropped six `done`
keys while reporting success.

### 16.4 Dashboard path derivation — `spec-dashboard-project-path-derivation`

**Description.** `generate.py` string-glues slugs onto project paths in several independent
places, each with its own patch for the slug≠directory cases. A `TODO` at `generate.py:~45`
names this exact gap.

#### FR-140: One resolver, one override table ← CAP-98
Slug→path resolution happens in one function with one exception table.
**Consequences:** no second call site builds a project path by string concatenation.

#### FR-141: `PROJECT_SOURCES` is derived, not declared ← CAP-99
The dashboard discovers projects rather than hard-coding them.
**Consequences:** a new station appears without a hand edit; a dissolved-and-absorbed project
resolves to its owner's tree rather than 404-ing.

#### FR-142: Resolution ships in `data.js`; the JS never re-derives ← CAP-100
Path resolution is computed once, at generation time.
**Consequences:** `index.html` contains no slug→path special case (today it carries one for
the retired `pyforge-genesis`).

#### FR-143: An unresolvable slug fails loud ← CAP-101
**Consequences:** generation exits non-zero naming the slug, rather than emitting a row whose
links 404.

### 16.5 Detector self-verification — `spec-dream-to-code-model-self-verification`

**Description.** Both detectors gate the tree; nothing gates the detectors. Three real
incidents, one as recent as 2026-08-08.

#### FR-144: Fixture-based meta-tests for `dream_chain_check.py` ← CAP-102
**Consequences:** known-good and known-bad trees assert *exact* findings, not "the live repo
passes"; the `covers-dreams:`/`## Satellite:` coverage path is regression-pinned; unparseable
frontmatter surfaces as a finding rather than being swallowed by `except: return {}`.

#### FR-145: Fixture-based meta-tests for `bmad_drift_check.py` ← CAP-103
**Consequences:** pin-missing, archive-misplaced, stray-file and spec-status-stale each have a
fixture; the existing live-repo integrity test stays — it gates the tree, these gate the
detector.

#### FR-146: A detector-incident log ← CAP-104
**Consequences:** a tracked companion records date, detector, wrong claim, true value, root
cause, fixing commit and pinning fixture; a new entry is mandatory in the same change that
fixes a detector.

#### FR-147: The `--dreams` hygiene mode ← CAP-105
**Consequences:** the mode promised by the 2026-07-23 restructure exists and reports Dream-tier
hygiene findings.

### 16.6 Chain completeness — `spec-fleet-chain-completeness`

**Description.** Keeping Dream→Spec→Research→Brief→PRD→Architecture→Epics→Code coherent is
manual and fragile; this very session is the proof.

#### FR-148: Orchestrated chain regeneration ← CAP-106
**Consequences:** regenerating a project's chain is one invocation, in dependency order.

#### FR-149: Code-status preservation ← CAP-107
**Consequences:** every story key with `status=done` before a regeneration has the identical
key after it; only backlog epics may be restructured.

#### FR-150: Chain-completeness audit mode ← CAP-108
**Consequences:** a read-only mode reports, per project, which chain layers exist and which
are missing.

#### FR-151: Orphan detection with review-gated cleanup ← CAP-109
**Consequences:** specs referencing deleted Dreams and epics referencing orphaned specs are
reported; nothing is deleted without review.

#### FR-152: Configurable per-project invocation ← CAP-110
**Consequences:** the chain runs for one named project without touching another's tree.

### 16.7 The governed tool surface — `spec-agent-tool-surface`

**Description.** Every factory capability should be reachable through one governed, typed
surface. The surface shipped without one.

#### FR-153: One governed surface ← CAP-111
**Consequences:** capabilities are exposed as named tools with typed arguments and structured
answers, not bespoke integrations.

#### FR-154: The surface survives a clone ← CAP-112
**Consequences:** registration is per-home and rendered (the `marshal init` `.mcp.json`
pattern), never a machine-absolute hand edit of `~/.claude.json` — AD-43 already forbids the
latter.

#### FR-155: CLI ⇄ tool parity is gated, not reviewed ← CAP-113
**Consequences:** a capability present in one surface and absent from the other fails a check.

#### FR-156: Coverage is measured, not assumed ← CAP-114
**Consequences:** per-station tool-surface coverage is reported as a number; the 2026-07-28
finding that recorded 2-of-6 coverage with Marshal itself at zero, inside a Dream marked
`realized`, is the reason this is measured rather than asserted.

### 16.8 The shared floor — `spec-pyforge-core`

**Description.** Five primitives written between three and twenty times across eight
stations. Minted 2026-08-08; see `docs/dreams/pyforge-core.md` for the measured census.
**Sequencing: FR-157 and FR-158 must land before Epic 7's stories S-7.2 and S-7.3**, which
would otherwise mint copy #21 of atomic write and copy #6 of the verdict lattice.

#### FR-157: The leaf exists and is provably a leaf ← CAP-115
**Consequences:** pure stdlib; a meta-test fails the build if any module imports from
`pyforge.<station>`; every station stays independently conda-installable.

#### FR-158: Atomic write has one implementation ← CAP-116
**Consequences:** all 20 measured copies across the 6 stations that have them are removed **in
the same story that extracts the primitive**; per-call-site durability semantics are verified,
not assumed uniform.

#### FR-159: The verdict lattice is declared once ← CAP-117
**Consequences:** doctor's `{0, 2, 130}` is an enforced narrowing of warden's `{0, 1, 2, 130}`
rather than a docstring claim; all five declarations retire; observable exit codes are
unchanged.

#### FR-160: One report envelope ← CAP-118
**Consequences:** warden's 22 KB schema becomes an extension of one base; doctor's and
marshal's resolve to it; captured real reports from each station validate unchanged.

#### FR-161: One exception root ← CAP-119
**Consequences:** herald's and mason's independent roots re-parent; no existing `except`
clause changes behaviour — asserted by test, since re-parenting can silently widen a catch.

#### FR-162: The subprocess seam is reconciled ← CAP-120
**Consequences:** one guard, chosen deliberately between doctor's `cli_bridge.run_cli_json` and
marshal's `ProcessPort`; **Marshal's own 7 importing modules — the widest ungated surface in
the fleet — route through it**; steward's deliberate raw-`CalledProcessError` propagation is
folded in or recorded as a tested opt-out; warden's existing single seam is confirmed
conforming, not "fixed."

#### FR-163: A second implementation cannot appear unnoticed ← CAP-121
**Consequences:** one sole-ownership meta-test per extracted primitive; each fails the build
when a second implementation appears anywhere under `src/shared/packages/`.

### 16.9 Surface drift reconciliation — `spec-surface-drift-reconciliation`

**Description.** The ninth Spec absorbed under the amended rule (its Dream is
`owner: marshal`), and the only one where **the broken thing is an instrument this
station already owns**. `scripts/spec_surface_check.py` proves every tracked file is
governed by a spec surface and that no governed file drifted from its contract — and it
has carried **61 findings on `main`** for weeks. The repo is not 61 kinds of broken; the
detector makes its reconciliation claim at the wrong granularity, twice, so its verdict is
unactionable in one direction and untrustworthy in the other. Realizes CAP-1..CAP-5 of
that Spec — CAP-5 added 2026-08-09, after operating the gate the first four turned green
surfaced a third instance of the same granularity error.

#### FR-164: A baseline can be stamped for one spec ← CAP-122
**Consequences:** `--write-baseline` gains `--spec NAME` (repeatable), merging only the
named specs into the committed baseline and leaving every other entry byte-identical; an
unknown name exits 2 with the known set listed. Today the stamp is all-or-nothing, so the
sanctioned fix for one `[no-baseline]` finding necessarily accepts ~34 other specs'
pending drift — which is why the honest move has been to leave the red standing. Unscoped
stamping survives, and says in its own help text what it accepts.

#### FR-165: A moved contract reconciles only the paths it names ← CAP-123
**Consequences:** the drift pass stops short-circuiting per SPEC
(`if b["memlog"] != cur["memlog"]: continue`) and checks each drifted file against the
memlog's text; named paths clear, unnamed paths surface as a **non-gating**
`[drift-presumed]`. Matching is literal substring on the repo-relative path — the form
these entries already cite files in — because inferring intent from prose would rebuild
the blanket it replaces. A memlog naming no paths stays legal: it degrades to
`[drift-presumed]`, never to a hard failure, or the gate reds for every historical entry.

#### FR-166: The standing 61 findings are dispositioned, not carried ← CAP-124
**Consequences:** 24 `[no-baseline]` scoped-stamped; 34 `[drift]` (23 of them one steward
Epic-2/3 delivery) each either genuinely reconciled through its spec **or** scoped-stamped
with the reasoning recorded in that spec's own memlog; 2 `[ungoverned]` Charter files given
a surface or an allowlist entry; 1 `[stale-allowlist]` pattern (`pixi.toml`) removed.
Anything that cannot be honestly cleared is filed as deferred work with its reason —
never suppressed, and never bulk-stamped.

#### FR-167: Neither fix can regress into the blanket it replaces ← CAP-125
**Consequences:** both are mutation-tested **both ways** — removing `--spec` scoping re-reds
the isolation test, and restoring the per-spec short-circuit re-reds a laundering test that
replays the live incident (an unrelated memlog append dropping findings 63 → 61 and clearing
two detectors nobody reconciled). Charter §6 applies directly: the fix is granularity, never
a relaxed threshold.

#### FR-168: A Spec cannot declare a surface it has no contract for ← CAP-126
**Added 2026-08-09, realizing CAP-5.** Two days of operating the now-green gate exposed a
third instance of the same granularity error, found twice in two days: a Spec that declares a
`surface:` but ships with **no `.memlog.md`** is **drift-blind**. `contract_hash()` returns
`""`, the baseline stores `""`, and `"" != ""` is never true — so the contract can never move
and every governed change reports a hard `[drift]` whose printed remedy ("reconcile the
spec") is unreachable. **Consequences:** a spec governing ≥1 tracked file under the default
`surface-drift: memlog` mode with no memlog reports a **gating** `[drift-blind]` finding
naming the spec, its governed count, and where the memlog belongs; zero-file, `exempt`, and
`sentinel:` specs report nothing, none of them being blind. `[drift-blind]` gates where
`[drift-presumed]` does not, and the asymmetry is principled — presumed reconciliation is
*unproven* over historical entries nobody can retro-name, while blindness is *structurally
impossible* and clears by creating one file. The 7 live instances (**396 governed files**,
370 of them mason's CFE tree) are dispositioned by writing each memlog **and** scoped-stamping
its baseline in the same change, since a new memlog otherwise downgrades that spec's next
drift from gating to informational — trading a false green for a quiet one. The detector
never writes the memlog it checks for.

#### FR-169: The presumed set is worked down by measurement, not carried ← CAP-127
**Added 2026-08-09, realizing CAP-6.** FR-165 made a previously-invisible set visible: **994
`[drift-presumed]` entries** across four station Specs. Carrying them unexamined would repeat
the mistake this whole Dream was seeded to correct — a standing number that hardens into
terrain. **Consequences:** every entry is traced to the commit that last moved it and
partitioned before anything is stamped. The measurement, not an estimate: **932 `added` /
62 `changed` / 0 `removed`** — 94% is baseline lag, not drift; **994/994** trace to a commit;
**178** to an explicit `done` story id and **zero to a story that is not `done`**. Herald is
834 of the total and 751 of those (15 clusters) are `presentations/**`, a *declared* part of its surface
contracted by **HER-9** — S-13.4's steward finding at fleet scale, the code having caught up
to a contract that was already correct. Each cluster is judged against its Spec's own
capabilities and the judgment recorded in that Spec's memlog **before** the scoped stamp;
anything moved by an unfinished story or landing outside a contracted capability is reported
instead. A stamp is honest only after the judgment — measuring first and stamping second is
reconciliation; the reverse is the laundering this Spec exists to end, and the two are
indistinguishable in the resulting number, which is why the measurement is recorded.

FR-174 (see § 7, "The producer reconciles the surface it drifts"), realizing **CAP-7**,
closes the loop this whole Dream exists to end: without it, every fix above still relies on a
human naming paths at landing.

---

## 17. The Marshal↔Steward seam

**Ratified 2026-08-08.** Before today neither station's PRD mentioned the other — zero
cross-references in either direction — while both shipped a `deploy` verb, both provisioned
loop homes, and a pipeline ran through both with the hand-off owned by nobody.

**The seam: Marshal owns the build line; Steward owns the estate it stands on.** The test is
*is this the factory's own machinery, or the ground it stands on?*

| | Marshal — the build line | Steward — the estate |
|---|---|---|
| Owns | loop homes, gates, runs, landing, the planning chain, adapters, the detector front door, the egress counter | pixi envs, credentials, budgets, service deploys, images, air-gap bundles, BMAD module installs |
| Setup verbs | `marshal seed` makes a **repo** able to run the model | `steward provision` makes a **machine** able to run it |

**Consequences recorded here, actioned in Steward's chain:**

- **`steward provision --runner bmad-loop` retires in favour of `marshal init`.** Steward's own
  **AD-5** already calls this "Marshal-owned machinery," and it wraps the *legacy*
  `scripts/bmad-loop-worktree` while `marshal init` (Epic 1, 10 shipped stories) is a strict
  superset — worktree plus marker↔symlink agreement, the AD-11 never-write proof, and an
  idempotent step report.
- **The ledger hand-off is a two-sided contract.** Marshal produces
  `sprint-status-ledger.yaml` and is accountable for it being current (**FR-136..FR-139**);
  Steward publishes whatever it says (`steward deploy dashboard`) and never derives status
  itself. Neither station writes into the other's half.
- **Setup routing follows one rule** — *judgment stays with the owning station, install
  mechanics go to Steward, the front door is Marshal's.* Kedro adoption is Atlas's judgment
  and Steward's install; BMAD module installs are Steward's while BMAD config/multi-project
  wiring is Marshal's; MCP server availability is Steward's while per-home `.mcp.json` render
  and the tool-surface contract are Marshal's (**FR-153..FR-156**).
- **Local stays the default; a server is an estate service.** The static console is the
  contract; any live UI is a cache over the same generators — the `artifact-console` failure
  mode (state existing only in the running thing) is on record as the reason.

  *(Amended 2026-08-26 — the console half of this bullet is superseded.)* The Unifying
  Strategy (`spec-pyforge-unifying-strategy`, operator decisions dated 2026-08-24) rules
  that its **CAP-2 Lane 1 CMS front door supersedes Marshal's static Guildhall console** —
  "Marshal's console is superseded, not co-owned" — with a migration obligation: feature
  parity is proven **before** the old build path is removed, and `spec-factory-console` is
  corrected to "superseded by CAP-2" in the same chain. The console's residual backlog, if
  any, remains Marshal's and is not pulled into that chain. Lane 1 went live 2026-08-26
  (`GET /` → 200). The *ledger* half of this seam is untouched: Marshal still produces
  `sprint-status-ledger.yaml` and is accountable for its currency (FR-136..FR-139);
  whatever front door publishes it never derives status itself.

Where an outcome is one station's and the mechanism another's, Charter §5's *Outcome and
mechanism* rule governs: the outcome-owner writes the story, the mechanism-owner owns the verb
it calls.

---

## 18. Currency reconciliation — 2026-08-26

The Spec (`specs/spec-pyforge-marshal/`, memlog re-stamped 2026-08-22) and `epics.md`
(2026-08-25) both moved past this PRD's 2026-08-14 update. This section folds that motion
in — the same INV-A discipline the 2026-08-11/08-14 header lines applied, extended to the
Epic 21–27 era — and re-grounds the document's live claims. Nothing above is renumbered.

### 18.1 The FR space: FR-192..FR-195 registered

`epics.md` cites four FRs this PRD did not carry. Registered here, defined by their
epics-side usage; all of their stories are `done` in the tracked ledger (one exception
since 2026-08-27: Story 22.7, minted for FR-193's CAP-7, is `backlog`):

#### FR-192: The planning chain regenerates itself, and audits whether it is coherent ← CAP-150
The **second, full decomposition** of `spec-fleet-chain-completeness` (CAP-1..5) into
**Epic 21** (Stories 21.1–21.5, added 2026-08-15) — orchestrated regeneration,
code-status preservation, the audit mode extended to full CAP-3 coverage, review-gated
orphan cleanup, per-project invocation. **Relationship to FR-148..FR-152 (§ 16.6):** those
were the first decomposition of the same Spec; Epic 17 realized their audit slice (Story
17.3 / FR-150 → the `chain` verb group), and FR-192's Epic 21 shipped the rest as the
`marshal planning` verb group. **Resolved 2026-08-27** (the INV-A pass this filing
anticipated), by scope partition rather than renumber: **FR-148..FR-152 (§ 16.6) remain
the registration of the Spec's five capabilities as first decomposed — realized by Epic
17's shipped slice** (Story 17.3: FR-150 residual + FR-152 → the read-only layer audit;
Story 17.4: FR-148/149/151 → `marshal chain regenerate`); **FR-192 is scoped to Epic 21's
second-era completion of the same five** (the `marshal planning` verb group + full CAP-3),
never a fresh registration of them. Fresh FR numbers were deliberately NOT minted (FR-196
stays the next free id): every candidate renumber target is load-bearing in shipped
surfaces outside the planning chain — `pixi.toml`'s `chain-layers-audit-check` description
(`17-3 + 21-1 / FR-150 + FR-192`), `pyforge.doctor.sources` module/test comments,
`pyforge/marshal/cli/chain.py` and `core/chain_regen.py` docstrings — so a renumber on
either side would desync code that cites these ids. No `done` story key was touched;
`epics.md`'s Epic 17 and Epic 21 goals now carry the same partition.

#### FR-193: Single-story dispatch is a marshal verb, not a session's discipline ← CAP-151
Decomposes `spec-marshal-single-story-dispatch` (CAP-1..7) into **Epic 22** (Stories
22.1–22.6, added 2026-08-21; Story 22.7 added 2026-08-27 for CAP-7 fleet drain, `backlog`
— the 2026-08-21 pass covered CAP-1..6 only, naming CAP-7 merely as an acceptance
oracle): `marshal factory dispatch` launches one governed, isolated,
detached `bmad-build-auto` story session; completion is judged from git and process facts
(a zombie is never re-dispatched); **verification is the product — no landing on a
self-report**; a verified story lands through the existing machinery; one story in flight
per station with stations in parallel and overlap loud; the run survives its operator and
its journal carries the timing signal; and (22.7) fleet-wide drain across the eight
stations is a marshal-orchestrated campaign mode. **Resolved 2026-08-27** (the INV-A pass
the recorded defect was filed for): `epics.md` had also assigned FR-193 to Story 19.4
(testing-charter CAP-5, added 2026-08-15) — one FR id, two Specs. Story 19.4 now cites
**FR-132**, verified before re-citing: FR-132's § 16.1 registration ("Test architecture
stays current as stories land" — regeneration idempotent on an unchanged tree, a changed
document when tests moved) is Story 19.4's title verbatim and its acceptance substance.
FR-193 is the dispatch Spec's id alone; no fresh number was needed. The promoted story
spec `specs/spec-19-4-test-architecture-stays-current-as-stories-land.md` retains its
historical FR-193 mention as a dev-run record.

#### FR-194: Velocity captures hand-driven work ← CAP-152
Decomposes `spec-dashboard-velocity-captures-hand-driven-work` (CAP-1..3) into **Epic 23**
(Stories 23.1–23.3): wall-clock fallback derived from promoted-spec revision fields,
never blended with active compute, with the coverage caption partitioned by true reason.

#### FR-195: Liveness is one command ← CAP-153
Decomposes `spec-bmad-loop-liveness-footgun` (CAP-1..3) into **Epic 24** (Stories
24.1–24.3): the missing liveness primitive, the operator answer as one documented
command, and a cheap documented double-check for UNSUPERVISED rows.

**ONE FR space now FR-1..FR-195** (FR-196 = next free id). The two defects recorded here
on 2026-08-26 — the FR-148..152/FR-192 overlap and the FR-193 double-assignment — are both
**resolved 2026-08-27**: the overlap by scope partition (FR-148..152 = Epic 17's first
slice, FR-192 = Epic 21's completion; no renumber, every id load-bearing in shipped code),
the double-assignment by re-citing Story 19.4 to FR-132 (its verbatim registration),
leaving FR-193 solely the dispatch Spec's.

### 18.2 The harness era: 0.9 → 0.11, absorbed as product work

Everything in §§ 4–6 citing `bmad-loop 0.9.0` and the `<0.10` pin is intake-era history —
correct when written, superseded in the shipped tree. Live facts: the pin is
**`bmad-loop >=0.11.0,<0.13`** (member `pyproject.toml`; 0.12.0 resolves — cap widened 2026-09-26;
`marshal --version` reports both). **Epic 25** (`spec-bmad-611-era-alignment`, Stories
25.1–25.7, all done 2026-08-22) carried the era into the product: retired v6 skill ids
purged from seed templates and guarded by meta-test (25.1); repo skills matched to the
installed package (25.2); every spec folder accepts a 6.11 `bmad-spec` update (25.3); the
five 0.10/0.11 policy knobs became governable through the AD-16 chain — 28-key closed
vocabulary, strict validators mirroring the installed enums, an `[operator]` render
section (25.4); Marshal speaks the 0.11 status vocabulary — `awaiting-operator` as a
sixth fleet state with `parked_stories`/`preserve_ref` surfaced (25.5); hand-driven runs'
deferrals reach the tracked ledger unaided (25.6); and the factory's living docs were
re-grounded with a named owner (25.7). The installed-package vocabulary pin tests shipped
with 25.4/25.5 are the first real slice of NFR-9's contract-test layer — the top-ranked
debt item in `research/technical-marshal-orchestration-refresh-2026-08-08.md` § 3.

### 18.3 Shipped state and the command surface

The tracked ledger reads **165/166 story keys done across Epics 1–27** (165/165 until
2026-08-27, when Story 22.7 — FR-193 CAP-7 fleet drain — was minted `backlog`; 110-key /
"50 stories" citations elsewhere in this document are dated snapshots). The `marshal`
binary carries **18 top-level command groups** — `config init homes preflight teardown
gate factory deploy land retire status check adapters upstream seed refresh chain
planning` — plus `factory dispatch`/`dispatch-attach`/`dispatch-resume` (Epic 22), the
`marshal-mcp` console script (Epic 18, FR-153..156), and the `pyforge.core.hooks` entry
point registering the bmad-loop runner as the default plugin (Story 26.1). Package
measure as of this pass: 129 src modules / ~63.1k LOC, 149 test files / ~83.6k LOC.

### 18.4 The estate seam (Unifying Strategy, 2026-08-24/26)

Folded per the amended § 17 bullet: the static console is superseded by CAP-2 with a
parity-before-removal obligation; Marshal's estate faces are its **portal** (one of eight,
one host session) and its **MCP face** on the host ASGI (`POST /stations/marshal/mcp` —
never a repo-root process farm); the persona grammar is `pyforge marshal …`; the Epic 22
dispatch verbs served as the 2026-08-25 fleet drain-bind campaign engine — product, not
discipline. Boundary lines recorded verbatim from the strategy pack: *never: Marshal
stores SLAs*; the host never imports `pyforge.*` source.


## Deferred-work verification state — reconciled 2026-09-08

The fleet's tracked deferred-work backlog now reads **100% verified within 30 days on all
eight stations** (marshal: 442 entries). Before the 2026-09-08 sweep steward sat at 61% and
the other seven at 92–98%; 183 entries had never been re-checked against live code since
authoring.

Marshal's own 19 never-verified entries were verified in that pass — three resolutions and
two code fixes: `cli/config.py`'s stale "9 keys" numeral removed in favour of naming
`_UNSETTABLE_KEYS` as the authority (a literal that had gone stale three times), and
`sources/chain.py`'s `_KNOWN_FIELD_KEYS` extended with `note`.

Two marshal entries got **worse** since authoring and carry corrected numbers, not stale
ones: `architecture-bmad-infra.md` still claims 94 skill directories against a live 129, and
the generator's Story Coverage Matrix now reads 394 "none observed" of 404 rows (was 207 of
208).

`spec-deferred-work-resolution-sweep`'s CAP-2/CAP-3/CAP-6 were measured during the sweep and
found inert against these ledgers — see that Spec's `sweep-tooling-effectiveness-2026-09-08.md`.

---

## 19. Currency reconciliation — 2026-09-14

*Chain-currency sweep: `spec-pyforge-marshal`'s SPEC.md moved through 2026-09-09..09-12
and its `.memlog` to 2026-09-13T08:33 while this PRD sat at 2026-09-08 — five days,
past the runbook's 2-day grace window.*

**This is the rare cascade that produced real content edits rather than a note.** The
Spec's **2026-09-09 operator answering pass** closed six items. Four of them exist in
this document under **different numbers**, and all four still read as open. Number
translation, recorded here because it is the thing a future reader will get wrong:

| `spec-pyforge-marshal` | this PRD | subject |
|---|---|---|
| Q-11 | **Q-4** | fleet-level resource budgets |
| Q-12 | **Q-5** | OpenTelemetry `gen_ai.*` emission |
| Q-13 | **Q-6** | ACP migration trigger |
| Q-14 | **Q-7** | 25-minute idle threshold |
| F-4 | *(none — new)* | the trust model |
| F-5 | *(none — new)* | mid-run freeze writer |

**What was changed in place, above:**

1. **§ 13 Q-4, Q-5, Q-6, Q-7 each gained a dated `ANSWERED 2026-09-09 (operator, folded
   in here 2026-09-14)` clause** carrying the operator's actual answer and its stated
   reason — not a pointer to the Spec. Per the runbook's grounding triple: fold the
   upstream content in, do not merely cite it.
2. **§ 8's fleet-budget Non-Goal was amended** from a deferral-awaiting-evidence to a
   decided v1 Non-Goal, with C-3 named as the reason.
3. **§ 11 gained C-11 and C-12** — the declared advisory-in-v1 trust model (Spec F-4)
   and the no-unattended-freeze-writer rule (Spec F-5). Both were amended into the
   Spec's own Constraints on 2026-09-09 and had no home here at all. C-11 is the more
   consequential of the two: it states plainly that operator attribution is an audit
   record, not an enforcement boundary, and ties that to C-10's worktree-is-not-a-sandbox
   position rather than leaving the two facts in separate sections to be reconciled by
   the reader.

**What moved in the Spec and did NOT need a change here.**

- **`status: shipped` added to the Spec (2026-09-09).** One of eight fleet-wide
  status-less Specs, three of them marshal's — a bookkeeping defect that made
  `chain-completeness` report its CAPs uncovered. No PRD consequence.
- **The genesis-installer → seed-installer name retirement (CAP-6, closed 2026-09-12).**
  Checked against this document: **§ 15 is already titled "The seed installer —
  `marshal seed`"** (retitled 2026-08-08). The three remaining "Genesis Installer"
  strings at §§ 15's provenance block are **historical prose** — the original
  frontmatter and the archive path of the superseded satellite PRD — and they keep
  their original names by convention. Nothing to repoint.
- **Eighteen dated `verified:` lines (2026-09-11 operator-directed sweep).** Evidence
  about the shipped contract, not changes to it. Several are `PARTIAL` and say so;
  none contradicts an FR in this document.
- **The 2026-09-12 tier-routing fail-safe surface reconcile and Story 12.1's
  `planning_graph.py`.** Both governed by their own narrower Specs
  (`spec-dispatch-tier-routing-fails-safe`, the recall-kinds work) and already
  reconciled there; this kernel's memlog records them so `spec-surface-check` does not
  later read them as ungoverned drift. A 31-path `surface-drift-exclude:` block exists
  for the same reason. No FR describes drift-tracking bookkeeping.

**Ledger state at this stamp** (measured with `fleet_scan.parse_sprint_status`, not a
regex): **273 story keys — 270 `done`, 2 `backlog`, 1 `blocked` — across 42 epics** (40
`done`, 1 `in-progress`, 1 `backlog`). The § 18 figure of 165/165 across Epics 1–27 is
superseded by growth, not corrected.

**Content changed:** § 8 (one Non-Goal amended), § 11 (C-11, C-12 added), § 13 (four
answers folded in). No FR added, renumbered or removed — the FR space is unchanged.

## 20. Currency reconciliation — 2026-09-18

*Chain-currency sweep: `spec-pyforge-marshal` gained CAP-244..248 on 2026-09-18 (its
`.memlog` stamped 2026-09-18T18:50) while this PRD sat at 2026-09-14. Same-day
reconcile; FRs derived from the CAPs per `one-chain-per-station`'s rule that the PRD is the
Spec's decomposition, never an independent namespace.*

### 20.1 The FR space: FR-196..FR-200 registered

Herald's Epic 23 was drained to zero on 2026-09-18 by `marshal factory dispatch` on the Claude
harness — four stories verified, landed and ledger-flipped unattended, the first since
2026-09-12 — and every one of the four still needed a human within the hour. The station Dream's
2026-09-18 Realization-log entry measures the five things that human did on the run journals;
each FR below is one of them, decomposed into **Epic 50** (Stories 50.1–50.5). Epics 48 and 49
are reserved holes: their keys are already poisoned on `origin/main` by steward's
`Story 48.N:` / `Story 49.N:` direct-commit subjects — the very defect FR-199 closes.

#### FR-196: A landing never re-dispatches the story it just landed ← CAP-244
The fleet campaign supervisor treats the window between a dispatch session exiting and
`dispatch_land_finalize` promoting the ledger as still in flight, and reads a session's own
"already merged" refusal as *advance*, never *blocked*. Success: a fixture journal replaying
the herald sequence (`…151925342Z-82ce96c8`: dispatched → landed → respawned 46 s later →
blocked, complete) chains the next story instead. Story 50.1.

#### FR-197: A harness's own usage-wall wording is a transient outcome ← CAP-245
`classify_session_log` recognises Cursor's live "You're out of usage … increase your limit"
text (and Claude Code's weekly/monthly-limit text) as `quota_exceeded`, keyed per harness in
one table, so the fleet planner classifies the block transient. Story 50.2.

#### FR-198: `--harness` outranks a dead tier-map harness ← CAP-246
An explicit invocation flag leads the harness walk over an inline-table tier-map harness
without a policy edit; the model is resolved for the harness actually chosen, never a foreign
id (spec-cursor-native-tier-map CAP-1's fails-safe preserved); without the flag, today's
behaviour is byte-identical. Story 50.3.

#### FR-199: Landing evidence carries the station in every shape ← CAP-247
The AD-24 templated merge subject carries the station slug by default
(`Merge {slug}/{key} into main`); the un-scoped `Story N.M:` shape needs branch/station
corroboration; live history is grandfathered through the SHA/recovery allowlist and never
re-attributed. Extends FR-193's Story 35.1 corroboration, which cannot help when the key exists
in both ledgers. Story 50.4.

#### FR-200: The promoter reads a spec through its banner ← CAP-248
`is_valid_spec_text` and `parse_declared_surface` accept a leading `<!-- … -->` block before
the frontmatter, so `_already_promoted_keys` never mistakes a banner-topped tracked spec for
unpromoted and finalize never overwrites a reconciled copy with a stale Tier-3 twin
(local commit `b0b7f3019f`, 2026-09-18, dropped before push). Story 50.5.

**ONE FR space now FR-1..FR-200** (FR-201 = next free id).

### 20.2 Harness policy, this week

Cursor ran out of usage on 2026-09-18 (operator ruling). Every station's `marshal-policy.toml`
that named the 2026-09-13 Cursor Ultra ladder moved back to `harness_preference = ["claude"]`
with the sonnet-dev / opus-review tier map (herald PR #1458 first; marshal and doctor with this
reconcile). FR-198 exists so the next such flip needs no policy PR. The tests that pinned the
Cursor ids (`test_dispatch_retry.py`, `test_spin.py`) now assert the shape the station's own
tier map declares — a pinned ladder had turned marshal's own verify command red on `main`.

**Ledger state at this stamp** (measured with `fleet_scan.parse_sprint_status`, not a regex):
**300 story keys — 281 `done`, 18 `backlog`, 1 `blocked` — across 48 epics** (44 `done`, 3
`backlog`, 1 `in-progress`). Epic 50 is the newest of the three backlog epics.

**Content changed:** § 20 added (FR-196..FR-200 registered, harness-policy note). No FR
renumbered or removed.

## 21. Currency reconciliation — 2026-09-19

*Chain-currency sweep: `spec-pyforge-marshal` gained CAP-249..256 and `spec-pyforge-core`
(hosted here, as Epic 14 was) gained CAP-8..9 on 2026-09-19 while this PRD sat at 2026-09-18.
Same-day reconcile; FRs derived from the CAPs per `one-chain-per-station`'s rule that the PRD is
the Spec's decomposition, never an independent namespace.*

### 21.1 The FR space: FR-201..FR-210 registered

The second autonomous drain (2026-09-18/19) landed 17 stories across herald, doctor and marshal
under Epic 50's fixes, and the human acts it still needed are different in kind from the first
drain's — a green branch that was not a green merge, a landing record finalize never saw, an
operator pull before every cycle, a `blocked` session landed as `done`, a silent guard, a watch
reading the wrong engine, a mint branch poisoning a key, and a conformance suite with no lane.
The station Dream's "2026-09-18 (later)" Realization-log entry measures each on the run journals
and PRs; FR-201..FR-208 decompose into **Epic 51** (Stories 51.1–51.8), FR-209..FR-210 into
**Epic 52** (Stories 52.1–52.2). Epics 48 and 49 remain reserved holes.

#### FR-201: Verification sees the merge result ← CAP-249
`dispatch land` materialises `git merge-tree --write-tree origin/main <head>` whenever the branch
baseline is behind `origin/main` on a file the branch touches, runs the station's own
`verify_commands` against that tree, and refuses with a named finding when it is red; a
conflict-free green merge lands unattended; a branch already at `origin/main` verifies once.
Fixture: 50.4 vs doctor 27.5 (`1a5895317f`). Story 51.1.

#### FR-202: The landing record follows the session's write, not the primary's directory ← CAP-250
`dispatch_land_finalize` reads the dispatch worktree's `implementation-artifacts/` as a discovery
source beside the primary's, before teardown, so the Review Triage Log, Auto Run Result and
`deferred:` items a session wrote there reach the tracked spec and the ledger; a land refused after
the PR was opened journals `pr_number` / `marshal_native`. Fixture: 50.4 (#1488). Story 51.2.

#### FR-203: The campaign reads the ledger it just promoted ← CAP-251
After finalize promotes the tracked ledger onto `origin/main`, the next campaign cycle reads it:
the primary checkout is fast-forwarded only when it is a clean `main` (refused by name otherwise),
else the ledger is read from `origin/main`. Fixture: herald 23.x. Story 51.3.

#### FR-204: A blocked outcome never lands ← CAP-252
A session ending `blocked` produces no PR, no `done` promotion and a `dispatch-blocked` journal
fact with its reason; a revert-to-baseline plus a status flip is not git progress. Fixture:
doctor 27.3 (PR #1476). Story 51.4.

#### FR-205: MRS-DISP-043 speaks for an uncatalogued model ← CAP-253
The fails-safe guard fires for a model catalogued under no provider, with the chosen harness's own
default/alias ids kept silent. Closes DW-FU-50-3. Story 51.5.

#### FR-206: `marshal watch` follows the engine that is actually driving the station ← CAP-254
The station's current run is the engine whose last journal fact is most recent — a dispatch run
journaled today outranks a loop row paused in August. Story 51.6.

#### FR-207: Landing evidence is intent-scoped, not just station-scoped ← CAP-255
Only the shapes marshal mints for a landing mark a key merged; `doctor/27-4-mint` (PR #1477) no
longer lands 27.4; `_branch_belongs_to_project` gains its production caller. Closes DW-FU-50-4.
Co-governed by spec-landing-evidence-grammar / spec-pyforge-core. Story 51.7.

#### FR-208: The banner-skip family is complete ← CAP-256
`_skip_leading_banner` (both copies) tolerates leading whitespace/BOM; `parse_declared_low_risk`
skips a banner. Closes DW-FU-50-6 (severity high) and DW-FU-50-5. Story 51.8.

#### FR-209: The six accumulated violations are cleared ← spec-pyforge-core CAP-9
`pyforge-core-test` → 0 failed on `main` (today 6 failed / 1855 passed: three exception-root, three
second-subprocess), each fix the way CAP-5/CAP-6 prescribe; hand-driven (warden and testing-kit
files are outside marshal's dispatch surface). Story 52.1.

#### FR-210: The conformance suite is a PR gate ← spec-pyforge-core CAP-8
A `core-test` job beside the eight station jobs runs the `pyforge-core-test` pixi task on every
PR touching `src/shared/packages/**`, and `pr-preflight` depends on it; never a hand-enumerated
file list. Realizes CAP-7's "fails the build". Story 52.2.

**ONE FR space now FR-1..FR-210** (FR-211 = next free id).

**Ledger state at this stamp** (measured with `fleet_scan.parse_sprint_status`, not a regex):
**310 story keys — 286 `done`, 23 `backlog`, 1 `blocked` — across 50 epics** (45 `done`, 4
`backlog`, 1 `in-progress`). Epics 51 and 52 are the two newest of the four backlog epics.

**Content changed:** § 21 added (FR-201..FR-210 registered). No FR renumbered or removed.

## Currency reconciliation — 2026-09-20 (fleet consistency pass)

*Operator ruling 2026-09-20: every station's PRD, spine and epics are re-stamped in the same pass,
grace period or not, so the whole chain reads current for the foundry cutover. Trigger: the
station Spec's `.memlog.md` gained a 2026-09-20 event — the fleet consistency pass reconciled every
tracked story spec's frontmatter against the sprint ledger, matched each "Ledger status" line,
reconstructed missing Auto Run Results from `main`'s landing commits, fixed invalid frontmatter,
and let `sprint-ledger-sync` roll the epic keys up (`spec→prd` cascade). Bookkeeping only:
no requirement, decision, story or AD changes in this PRD. `updated:` bumped to record that the
check ran.*

## 22. Currency reconciliation — 2026-09-24

*Chain-currency sweep: `spec-pyforge-marshal` gained CAP-265 on 2026-09-24 while this PRD sat at
2026-09-20. Same-day reconcile; FR derived from the CAP per `one-chain-per-station`'s rule that the
PRD is the Spec's decomposition, never an independent namespace.*

### 22.1 The FR space: FR-211 registered

Doctor 24.2 and 24.3 (PRs #1577/#1578, #1579/#1580) each landed cleanly but needed a hand
`--repair-feed` + hand-promote + separate PR to reach the tracked ledger, because
`sprint-ledger-sync`'s regression guard correctly refused over unrelated stale Tier-3 feed keys
(13 and 14, respectively). FR-211 decomposes into **Epic 54** (Story 54.1) — a new epic because
Epic 51 (the `dispatch_land_finalize` reliability thread this continues) is `done`.

#### FR-211: A landing's ledger promotion repairs its own feed drift ← CAP-265
`dispatch_land_finalize`'s promotion retries with the Tier-3 feed's stale-but-safe keys pulled
forward from the tracked twin (the same one-directional operation `--repair-feed` already performs
by hand, safe because the twin is the authoritative record) whenever the regression guard's
refusal names only keys other than the one being promoted, landing the feed catch-up in the same
commit as the story it promotes; a refusal naming the promoted story's own key still stops for a
human, unchanged. Fixture: doctor 24.2/24.3. Story 54.1.

**ONE FR space now FR-1..FR-211** (FR-212 = next free id).

**Content changed:** § 22 added (FR-211 registered). No FR renumbered or removed. No AD amended —
the fix lands on the existing `dispatch_land_finalize` design without a new architectural decision.

## Currency reconciliation — 2026-09-26

`spec→prd` edge (`spec-pyforge-marshal`'s `.memlog.md` moved 2026-09-26) and the `behind-code`
edge (marshal's tree moved the same day) — both from one change: the `bmad-loop` runtime range
widened from `>=0.11.0,<0.12` to `>=0.11.0,<0.13` after 0.12.0 was verified.

**What moved, and why the FR delta is none.** FR-52 makes `adapters/harness_bmadloop.py` the one
source of truth for the harness range; its three spellings (`_HARNESS_MIN_VERSION`,
`_HARNESS_MAX_MINOR_EXCLUSIVE`, `HARNESS_VERSION_RANGE_TEXT`) moved together with the pyproject
and package-manifest pins, and the sync tripwire (`test_manifest_sync.py`) held. Verification was
the requirement's own procedure: the four `bmad_loop` modules the harness lazily imports ship in
0.12.0, and the full suite (8652 tests) passes in an environment re-solved onto 0.12.0. The only
behavioural difference 0.12.0 introduced is that `bmad_loop.bmadconfig` now validates a
non-mapping `config.yaml` itself (`… must contain a top-level mapping`) before marshal's own
"invalid bmad-config shape" guard can fire — the contract (never raise, report) is unchanged and
one test accepts both wordings. Two facts recorded for the record, neither an FR: the estate's
`pixi.toml` pins `bmad-loop` to the SelfExplainML channel because `conda-forge/bmad-loop-feedstock`
(2026-09-20, not this repo's) ships `__unix`-gated builds that strict channel priority would
otherwise prefer; and the § 22 Stack literal above is corrected in place, the same way the
2026-08-26 reconcile corrected `<0.10` → `<0.12`. `updated:` bumped to record that the check ran.
