---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - "docs/dreams/pyforge-marshal.md"
  - "docs/dreams/ecosystem-crew.md"
  - "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md"
workflowType: 'research'
lastStep: 6
research_type: 'market'
research_topic: 'Autonomous dev-loop / agent-orchestration tooling (competitive landscape for Marshal)'
research_goals: 'Position pyforge-marshal against direct competitors; extract gating models, spec-driven-ness, autonomy gradients, concurrency, distribution and pricing; identify defensible whitespace and counter-positioning risk.'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
mode: headless
status: complete
---

# The Gate Is the Product: Competitive Research on Autonomous Dev-Loop Orchestration

**Date:** 2026-07-25 · **Author:** Rxm7706 · **Research type:** Market · **Mode:** headless/express

---

## Executive Summary

The autonomous-dev-loop category has consolidated hard in 2025–2026, and it consolidated *away from* the slot Marshal occupies. Hosted, vendor-gated cloud agents (GitHub Copilot cloud agent, OpenAI Codex, Devin, Jules) captured the enterprise story; the open-source "local loop" tier thinned dramatically (aider effectively stalled, Roo Code shut down, Sweep pivoted to a JetBrains IDE product, Codegen was acquired and deprecated). What remains open is an unusually specific gap: **an OSS, self-hosted, spec-as-contract, gate-first CLI orchestrator that stays gated while running unattended.**

Every competitor trades one of those away. OpenHands has the richest open-source confirmation model in the market — and **hard-disables approval in headless mode** ("Headless mode always runs in `always-approve` mode… this cannot be changed"). Jules ships the cleanest programmable gate found anywhere (`AWAITING_PLAN_APPROVAL` + an `approvePlan` API call) — and **auto-approves on a timer** in its own UI. GitHub's cloud agent has the strongest published gating story of any hosted product — bound entirely to *GitHub's* PR/CI model, unusable off-platform. claude-flow/ruflo has 65.9k stars and effectively no gating at all, with install docs that recommend disabling the underlying agent's permission system outright.

The second finding is sharper than the first: **nobody treats the spec as an executable contract.** Every product's "spec" is context injection — `AGENTS.md`, Devin Knowledge/Playbooks, aider's `CONVENTIONS.md`, Copilot's `copilot-instructions.md`. None consume a spec carrying acceptance criteria and *gate progression on satisfying them*. GitHub's own Spec Kit proves the demand is enormous (123,718 stars, MIT, actively released) and simultaneously proves the gap: it ships **recommended sequencing, not enforced gates**, and is not wired into any server-side loop.

The third finding reframes the whole category. Both the strongest competitor blog post (OpenHands' *Verification Stack*) and the sharpest public critique of software factories converge on the same claim: **verification, not generation, is the bottleneck.** Microsoft's own ten-month retrospective on Copilot in `dotnet/runtime` quantifies the cost — 878 agent PRs at a 67.9% merge rate, but **16.5 review comments per merged PR** versus 12.4 for human PRs, and "5 to 9 hours of review work" created almost immediately. The same retrospective delivers the single most supportive data point for Marshal's thesis: adding one `.github/copilot-instructions.md` moved success from **38.1% to 69%**. Spec quality is the highest-leverage variable anyone has measured.

Counter-positioning risk is real and must shape the messaging. "Multi-agent swarm orchestration" is now a credibility-damaged label: the category's most-starred OSS project has a maintainer-filed issue quoting an independent audit that its headline SWE-bench number was **synthesized by `random.uniform()`**, and a second audit finding ~290 of its 300+ tools are stubs. Marshal should market on **gates, verification, and reproducibility** — never on topology or agent counts.

---

## Table of Contents

1. Market Research Introduction and Methodology
2. Market Analysis and Dynamics
3. Customer Insights and Behavior Analysis
4. Competitive Landscape and Positioning
5. Strategic Market Recommendations
6. Go-to-Market and Distribution
7. Risk Assessment and Mitigation
8. Success Metrics
9. Future Outlook
10. Methodology and Source Verification
11. Appendix — Comparison Matrix

---

## 1. Market Research Introduction and Methodology

### Market Research Significance

Marshal is being productized out of a capability that already runs in production in this factory (bmad-loop + `scripts/bmad-switch` + `scripts/bmad-loop-worktree`). The commercial question is not "can this work" — it demonstrably shipped `pyforge-atlas` 32/32 and `pyforge-warden` 31/31 — but **whether a named product in this slot is differentiated, and against what**. That makes competitive gating models, not feature checklists, the load-bearing research object.

### Methodology

- **Data sources:** primary vendor documentation, pricing pages, official blogs, GitHub REST API, npm registry, PyPI JSON, HN Algolia API. Fetched 2026-07-25.
- **Verification approach:** every figure traced to a primary page or API response; unverifiable claims explicitly tagged `[UNVERIFIED]`.
- **Known limitation:** `reddit.com` and `web.archive.org` were unreachable from the research environment; all community sentiment is Hacker News with item IDs. Reddit sentiment is absent, not negative.
- **Scope:** global; developer-tooling segment; direct competitors plus adjacent orchestration frameworks.
- **Time period:** current state as of 2026-07-25, with 2025–2026 structural changes called out.

### Research Goals

1. Establish whether "gated **and** unattended" is genuinely unserved.
2. Determine whether spec-as-contract is a differentiator or table stakes.
3. Extract pricing anchors to inform whether Marshal is a product, an internal tool, or an OSS artifact.
4. Surface counter-positioning risk in the category's vocabulary.

---

## 2. Market Analysis and Dynamics

### Market Trends and Dynamics — five structural shifts

| Event | Date | Source |
|---|---|---|
| **Roo Code shut down**; repo archived, users redirected to Cline | 2026-05-15 | [RooCodeInc/Roo-Code](https://github.com/RooCodeInc/Roo-Code) |
| **Codegen deprecated** after ClickUp acquisition | acq. 2025-12-22; shutdown 2026-01-16 | [clickup.com/blog](https://clickup.com/blog/clickup-codegen-acquisition/) |
| **Amp spun out of Sourcegraph** into Amp Frontier Corporation | 2025-12-02 | [ampcode.com/news](https://ampcode.com/news/amp-frontier-corporation) |
| **Cognition merged Devin + Windsurf** into one surface | Windsurf acq. 2025-07-14 | [cognition.com/blog/windsurf](https://cognition.com/blog/windsurf) |
| **GitHub replaced premium-request billing with usage-based AI credits**; "coding agent" → "cloud agent" | billing 2026-06-01 | [docs.github.com](https://docs.github.com/en/copilot/reference/copilot-billing/request-based-billing-legacy/what-changed-with-billing) |
| **AutoGen → maintenance mode**, superseded by Microsoft Agent Framework | badge as of 2026-04-15 | [microsoft/autogen](https://github.com/microsoft/autogen) |
| **SWE-agent → maintenance**, superseded by mini-swe-agent | 2026 | [swe-agent.com](https://swe-agent.com/latest/) |

**Read:** the category is consolidating around hosted agents with vendor-controlled gating, while the OSS local-loop tier thins. That is simultaneously a demand signal (the problem is real enough to attract platform vendors) and an opportunity (the OSS gate-first slot is vacating, not filling).

### Pricing and Business Model Analysis

Two distinct models, both now token/credit-metered rather than seat-metered:

| Model | Examples | Anchor prices (2026-07-25) |
|---|---|---|
| **Subscription + metered credits** | Copilot, Codex, Devin, Factory, Amp | Copilot Pro **$10/mo** (1,500 AI credits, 1 credit = $0.01) · Pro+ **$39** · Max **$100** · Business **$19/seat** · Enterprise **$39/seat**. Codex Go **$8** / Plus **$20** / Pro from **$100** / Business **$20/user/mo** annual. Devin Pro **$20** / Max **$200** / Teams **$80 + $40/full seat**. Factory Pro **$20** / Plus **$100** / Max **$200**, no free tier. Amp Megawatt **$20** / Gigawatt **$200**, or PAYG at 0% provider markup, **Enterprise +50%** |
| **OSS + BYO key** | aider, Cline, OpenHands (local), LangGraph, mini-swe-agent, ruflo | **$0**; cost is the user's own model spend |

**Two structural pricing facts worth carrying into the PRD.** First, **GitHub's $0.04/premium-request figure is obsolete** — replaced 2026-06-01 by 1 AI credit = $0.01, token-driven, credits do not roll over, and the cloud agent additionally burns GitHub Actions minutes. Second, **the per-unit dollar rate is unpublished for the two most enterprise-committed vendors**: Devin's USD-per-ACU and Codex's USD-per-credit could not be located on any reachable page `[UNVERIFIED]`. A tool that reports its own cost in dollars per story has a genuine transparency advantage.

Anchor for internal cost modelling: Anthropic publishes ~**$13 per developer per active day** and **$150–250 per developer per month**, with 90% of users below $30/active-day.

---

## 3. Customer Insights and Behavior Analysis

### Customer Behavior Patterns

The observable behavior that matters most is **users hand-rolling the layer Marshal proposes to ship**. The clearest instance is a widely-discussed post running *three aiders in parallel on separate git branches with different models*, producing three competing PRs from one ticket for "less than 10 cents," on the explicit rationale that "even if one model fails or produces a suboptimal fix (which happened!), others might succeed" (HN [43672712](https://news.ycombinator.com/item?id=43672712), 139 pts / 105 comments). That is a user manually building concurrency + differential verification because no product ships it.

The second pattern is **instruction-file investment as the primary quality lever**. Copilot supports `copilot-instructions.md`, path-specific `*.instructions.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and org-level instructions; Codex ships a three-tier `AGENTS.md` precedence chain with an `AGENTS.override.md` mechanism; Devin layers AGENTS.md + Knowledge + Playbooks + DeepWiki. Vendors are converging on "the written contract is the control surface" without closing the loop to enforcement.

The third is **spec-tool adoption without spec enforcement**: GitHub Spec Kit at 123,718 stars, `v0.14.2` released 2026-07-24, 30+ agent integrations — a `/speckit.specify → /speckit.plan → /speckit.tasks → /speckit.implement` workflow that is *recommended sequencing*, not enforced gating.

### Customer Pain Points and Needs

Ranked by evidence strength:

1. **Review burden is the actual cost of agent output — and it is measured.** Microsoft's `dotnet/runtime` retrospective: merged agent PRs averaged **16.5 review comments** (vs 12.4 human), **52.3% received direct commits from humans** (~5× baseline), and the team absorbed "5 to 9 hours of review work" quickly ([devblogs.microsoft.com](https://devblogs.microsoft.com/dotnet/ten-months-with-cca-in-dotnet-runtime/), 2026-03-23). Independently re-verified today: `repo:dotnet/runtime is:pr author:app/copilot-swe-agent` → **1,472 PRs, 1,008 merged (68.5%)**.
2. **Autonomy without escalation becomes a liability.** The canonical Devin field report — 20 tasks → **3 successes, 14 failures, 3 inconclusive** — names the failure mode precisely: "Devin would spend days pursuing impossible solutions rather than recognizing fundamental blockers" ([answer.ai](https://www.answer.ai/posts/2025-01-08-devin.html); HN [42826022](https://news.ycombinator.com/item?id=42826022), 119 pts).
3. **Gates vanish exactly when they are most needed.** OpenHands' headless mode disables approval; Jules' UI auto-approves on a timer. Users who want unattended runs are structurally forced to give up the gate.
4. **Cost opacity.** No dollar-per-task figure on the official SWE-bench Verified leaderboard; unpublished per-credit rates at Devin and Codex; GitHub's own docs note "there is no automatic fallback to lower-cost models when a budget is exhausted."
5. **Agents fabricate evidence convincingly.** danluu's agentic-coding notes (2026-07-04, HN 179 pts) report agents producing plausible-but-false bug reproductions, and observe that "having independent agents repeatedly check an alleged bug reproduction substantially cuts the false positive rate."

### Customer Segmentation and Targeting

| Segment | Need | Current coping | Fit for Marshal |
|---|---|---|---|
| **Solo/small-team factory operator** (the reference customer — this repo) | Many projects, one operator, unattended throughput with a trustworthy paper trail | Hand-rolled: bmad-loop + shell watchdogs + manual spec promotion | **Primary** |
| **OSS maintainer running batch refactors** | Bounded, reviewable, cheap parallel work | Parallel aiders on branches; Copilot cloud agent per-issue | **Primary** |
| **Regulated / air-gapped enterprise team** | Self-hosted, auditable, no vendor data path | Devin dedicated VPC ($$), Factory on-prem, or nothing | **Secondary** (v2) |
| **Platform team standardizing agent use** | Policy enforcement across many agents | Copilot org policy; Codex managed config | **Secondary** (v2) |
| **Individual IDE-assist user** | Inline completion, chat | Copilot/Cursor | **Non-user** |

---

## 4. Competitive Landscape and Positioning

### Key Market Players

**OpenHands** ([All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands), 82,024★) — the strongest OSS gating model found. Three composable layers: a confirmation policy (`AlwaysConfirm` / `ConfirmRisky(threshold=HIGH)` / `NeverConfirm`), deterministic pre-execution security analyzers (`PatternSecurityAnalyzer`, `PolicyRailSecurityAnalyzer`, `EnsembleSecurityAnalyzer`, `LLMSecurityAnalyzer`) scoring `LOW/MEDIUM/HIGH/UNKNOWN`, and six hook events where **exit code 2 blocks** — including a `Stop` hook that can block completion until lint/tests pass. Rearchitected into SDK / Agent Canvas / Cloud / Enterprise; now *hosts other agents* including ACP-compatible ones. **The decisive gap: headless mode is hard-locked to always-approve**, and scheduled Automations "run unattended without requiring human approval." License is `NOASSERTION` — MIT outside `enterprise/`, **PolyForm Free Trial 1.0.0 inside it** (source-available, redistribution forbidden). $18.8M Series A 2025-11-18 positioned explicitly on the "outer loop." Their [Verification Stack](https://www.openhands.dev/blog/20260506-the-verification-stack) post is the closest public articulation of Marshal's own thesis — **treat as validation and as a race signal**.

**aider** ([Aider-AI/aider](https://github.com/Aider-AI/aider), 47,683★, Apache-2.0) — technically excellent, visibly stalled. Last tagged release **v0.86.0, 2025-08-09**; PyPI 0.86.2 (2026-02-12); last commit to `main` 2026-05-22; **zero commits in the trailing ~9 weeks**; 1,762 open issues / 440 open PRs; leaderboard stale since 2025-11-20. The ideas outlive the codebase: graph-ranked repo map with a `--map-tokens` budget; four edit formats auto-selected per model; **architect mode** (strong model proposes, cheap editor model applies — the original model-tiering split); `--auto-lint` on by default and `--test-cmd` retry — but **no attempt limit and no loop-until-green construct**. Git commit-per-change is the audit trail and the rollback mechanism, a primitive Marshal should match or exceed. No worktrees, no sandbox, no concurrency.

**Cline** ([cline/cline](https://github.com/cline/cline), 65,038★, Apache-2.0) — the live successor in the local tier and **the best autonomy gradient in OSS**: eight independently toggleable auto-approve categories (read project / read all / edit project / edit all / execute safe / execute all / browser / MCP) plus YOLO. Plan mode cannot write or execute, but the Plan→Act transition is a user action, not an approval gate. **Shadow-git checkpoints** (separate repo, committed after each tool use, capturing untracked files, three restore modes) are a genuinely good rollback design. Headless CLI with `--auto-approve`. No published dollar pricing `[UNVERIFIED]`.

**Roo Code** — archived 2026-05-15, but its **Orchestrator / Boomerang Tasks** design is the best delegation pattern encountered: parent decomposes, each subtask runs in a specialized mode with **complete conversation isolation**, information flows down via instructions and **up exclusively through a completion summary**; orchestrator mode deliberately lacks file/MCP/exec access to prevent context contamination; and **"by default, users must approve each subtask's creation and completion."** A per-subtask gate — Marshal's exact shape — shipped in a now-dead product. Harvest the design.

**Devin (Cognition)** — latest is **Devin 2.2 (2026-02-24)**; there is no Devin 3.x. Best-in-class concurrency (parallel Devins in isolated VMs; "Devin Manages Devins" coordinator). Session gating is weak — planning is a *recommended mode transition*, the only hard gate is approval of a proposed parallel fan-out; autonomy knobs (`!fast`/`!ultra`/`!lite`) are **effort**-flavored, not permission-flavored. Governance is strong at org level: **AI Guardrails** escalating `log_only → warn_user → block_message → kill_session`. Deepest enterprise story of anyone (single-tenant VPC via PrivateLink/IPSec, SAML/OIDC, RBAC, audit API, customer-managed keys). Docs concede "Devin's performance degrades in long sessions" and flag L/XL (>10 ACU) sessions as unhealthy. **No SWE-bench Verified score has ever been published** `[UNVERIFIED]`; the only published number is 13.86% on a 25% sample from 2024.

**Google Jules** — the **cleanest programmable HIL gate in the market**: `requirePlanApproval: true` puts a session in state `AWAITING_PLAN_APPROVAL` requiring an explicit `approvePlan` POST, in a documented state machine `QUEUED → PLANNING → AWAITING_PLAN_APPROVAL → IN_PROGRESS → COMPLETED/FAILED`. Undermined by its own UI, which "will eventually auto-approve the plan, which is set on a timer." Only vendor publishing hard concurrency numbers (**3 / 15 / 60** concurrent by tier). GitHub-only, beta, `v1alpha` API, **paid tiers available only to individual @gmail.com accounts** — no SSO, audit, RBAC, residency or self-hosting at all.

**OpenAI Codex** — the most granular governance of any competitor and the most instructive reference. Two **orthogonal** axes: `--sandbox` (`read-only` / `workspace-write` / `danger-full-access`, with `.git`, `.agents`, `.codex` read-only even when writable) and `--ask-for-approval` (`untrusted` / `on-request` / `on-failure` / `never`). Trust defaults by VCS state — non-version-controlled directories start read-only. Network **off by default** in the agent phase with an allowlist plus HTTP-method restriction. And **auto-review**: a *separate reviewer agent* evaluates elevated-permission requests, with a **circuit breaker terminating the turn after 3 consecutive denials or 10 in a rolling 50-review window**, on a policy that is open-source and enterprise-customizable. Highest spec-driven-ness of the hosted agents — layered `AGENTS.md` with `AGENTS.override.md`, and a `## Code Review Rules` section *directly executed* by the GitHub reviewer.

**GitHub Copilot cloud agent** — strongest *published* hosted gating story, and it is worth quoting because Marshal should adopt the pattern wholesale: only write-access users can trigger it; it can push to exactly one `copilot/` branch; it is "subject to any branch protections and required checks"; **Actions workflows do not run until a human clicks "Approve and run workflows"**; and "Draft pull requests created by Copilot cloud agent must be reviewed and merged by a human. Copilot cloud agent cannot mark its pull requests as 'Ready for review' and cannot approve or merge a pull request" — with the triggering human also barred from approving. Built-in pre-flight CodeQL + advisory-database + secret scanning, no GHAS licence required. **Three documented gaps:** content exclusions do **not** apply to the agent; the egress firewall does **not** cover MCP servers or external processes; and "Copilot will use available tools autonomously, and will not ask for approval before use" for MCP. Hard limits: 1 repo, 1 branch, 1 PR, **59-minute wall clock that "cannot be extended or bypassed."** Also note the spec-driven footgun: "After assigning the issue, Copilot will not be aware of… any further comments that are added to the issue."

**claude-flow / ruflo** ([ruvnet/ruflo](https://github.com/ruvnet/ruflo), 65,885★, MIT) — the cautionary case, and important for positioning. 765 npm versions since 2025-06-10 (~56/month); ~690k combined monthly downloads. Six topologies, five consensus algorithms, SPARC methodology. **Gating is effectively absent** — the install docs recommend running the underlying agent with its permission system disabled, and federation trust "downgrades are instant — no human in the loop required." *(Relayed as a finding about the product, not adopted as guidance.)* The credibility record is documented in its own tracker: the maintainer filed issue [#1896](https://github.com/ruvnet/ruflo/issues/1896) quoting an independent audit that `simulate_benchmarks.py` generates results with `random.uniform(-0.05, 0.05)` and that "claims of '84.8% on SWE-bench' are synthesized, not verified" — annotated by the maintainer as "the most reputationally damaging finding"; a second audit ([#1514](https://github.com/ruvnet/ruflo/issues/1514)) finds ~290 of 300+ MCP tools are stubs; **no submission exists in [SWE-bench/experiments](https://github.com/SWE-bench/experiments)**; and a critical unauthenticated-RCE advisory ([GHSA-c4hm-4h84-2cf3](https://github.com/ruvnet/ruflo/security/advisories/GHSA-c4hm-4h84-2cf3), 2026-07-01). Bus factor 1.

**Adjacent, not competing:** **Claude Agent SDK** (a library; documented 6-step permission evaluation order — hooks → deny → ask → mode → allow → `canUseTool`; two footguns worth citing in any design doc: allow-lists do not constrain bypass mode, and **subagents inherit the parent's permission mode non-overridably**; a `PreToolUse` hook is the only universal gate). **LangGraph** (38,104★, MIT; `interrupt()` / `Command(resume=)` typed HIL primitive requiring a checkpointer — the reference implementation of durable pause/resume; ships no coding agent). **Factory Droids** — *the most direct architectural competitor*: `droid exec` with a **graduated autonomy ladder as a per-invocation CLI flag** (`--auto low|medium|high`, high "intended for CI/CD"), `--worktree` isolation, `--use-spec` forcing plan-before-execute, `--spec-model` splitting a cheap planner from an expensive executor, and Droid Shield blocking commit/push on detected secrets. **Amp** — loosest gating of anyone ("does not require pre-approval for tool execution"), but its "Dial" (`low/medium/high/ultra` rating *task difficulty*, not model) and **Orbs** (persistent remote machines surviving laptop close) are notable UX ideas. **mini-swe-agent** — >74% SWE-bench Verified in ~100 lines of Python, bash-only, no tool-calling interface: proof that harness minimalism can win.

### Strengths and Weaknesses — where Marshal stands

| | Strength | Weakness |
|---|---|---|
| **Marshal (proposed)** | Gated *and* unattended; spec-as-contract with acceptance criteria; escalation-on-uncertainty; N concurrent isolated loops as a first-class primitive; self-hosted, no vendor data path; already proven on two shipped systems (atlas 32/32, warden 31/31) | Zero market presence; single maintainer; depends on an upstream orchestrator (bmad-loop) and on BMAD Method conventions; Linux/macOS only today; no benchmark score of its own |
| **Hosted agents** | Distribution, enterprise controls, platform-native gates | Gates bound to one platform; opaque unit pricing; no spec enforcement; 59-min / session-degradation ceilings |
| **OSS local loops** | Free, self-hosted, transparent | Gates evaporate headless (OpenHands) or never existed (ruflo); maintenance risk (aider, Roo) |

### Market Differentiation — four defensible gaps

1. **Gated *and* unattended.** Only Factory (`--auto low|medium|high`) and Codex (sandbox × approval + auto-review) offer a real unattended gradient, and **neither is spec-as-contract**.
2. **Spec as executable contract, not context file.** Universal gap. Spec Kit's 123,718 stars prove demand without enforcement.
3. **Escalation-on-uncertainty.** Unaddressed everywhere except Codex's denial circuit breaker. This is precisely the failure Answer.AI named in Devin.
4. **Concurrent isolated loops as a product primitive.** Users hand-roll it; Codex documents worktrees as advice; Factory has `--worktree`; OpenHands' sub-agents are sequential-only. **Nobody ships N gated loops with per-loop verification and merge discipline as the product.** This factory runs **7 concurrent loop homes today** (`scripts/bmad-loop-worktree --list`, 2026-07-25).

### Competitive Threats

- **OpenHands closing the gap deliberately.** Their Verification Stack post proposes a trained critic model plus a repo-level verifier and claims 58% mean-time-to-merge reduction. Well-funded, 82k stars, and aiming at the same thesis. **Highest-probability threat.**
- **Copilot/Codex absorbing spec enforcement.** Codex already executes a `## Code Review Rules` section from `AGENTS.md`; Spec Kit sits in the same org as the cloud agent. If GitHub wires Spec Kit gating into the cloud agent server-side, differentiator #2 narrows sharply.
- **Category vocabulary damage.** "Swarm/multi-agent orchestration" now carries ruflo's baggage.
- **Upstream dependency risk.** Marshal's proposed foundation (bmad-loop) is a young, small-team project — the same profile that killed Roo Code and stalled aider.

### Opportunities

- **Be the answer to the strongest critique.** ["Why Software Factories Fail (or: harness engineering is not enough)"](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/wsff.md) (HN [49023019](https://news.ycombinator.com/item?id=49023019), **376 pts / 264 comments**, 2026-07-23) argues "no amount of 'harness engineering' can compensate for fundamental model training limitations" — models optimize for passing tests, not maintainability, and "the cost function of bad architecture is measured in weeks, months, maybe even years." Its prescription — structured planning phases plus **restored human review at each vertical slice** — is Marshal's design. Answering this post explicitly is a positioning asset, not a liability.
- **Harness choice outweighs model choice.** Databricks' multi-million-line-codebase benchmark (2026-07-08) reports 81–87% completion at **$1.28–$2.09/task** across ~100 real merged PRs and finds harness choice materially outweighs model choice. That is the market's permission slip for a harness product.
- **Cost transparency as a feature.** Per-story dollar reporting is available to nobody buying Devin or Codex.

---

## 5. Strategic Market Recommendations

**Market opportunity assessment.** The high-value opportunity is narrow and real: *the only gate-first orchestrator that keeps its gates when nobody is watching*. Entry timing is favourable — the OSS tier is thinning while enterprise demand for auditable agent output is rising, and the strongest competitor has publicly announced the same thesis but not yet shipped it.

**Recommended positioning.** "Autonomy as a gradient, with the gate intact." Lead with three claims, each independently verifiable: (1) the spec is a contract with acceptance criteria and progression is gated on it; (2) anything the agent cannot safely decide **escalates instead of guessing**; (3) N loops run concurrently, each isolated, each verified, each with a durable paper trail.

**Competitive strategy.** Do not compete on model quality, agent counts, or topology. Compete on **evidence**: every run produces a journal, a verify record, and a merge artifact that a human can audit after the fact. Publish the factory's own numbers (atlas 32/32, warden 31/31, 7 concurrent loop homes) as the proof — first-party dogfooding evidence is the only credible currency in a category where the loudest benchmark number was fabricated.

**Adoption strategy.** Dogfood first, distribute second. The reference customer is the factory itself; the second customer is the OSS maintainer running batch work. Enterprise is a v2 conversation, gated on air-gap and audit stories that do not exist yet.

---

## 6. Go-to-Market and Distribution

**Channel strategy.** conda-forge as the primary channel is a genuine structural advantage here: this factory already packages `bmad-loop 0.9.0` as a noarch conda recipe (`recipes/bmad-loop/`, MIT, built GREEN linux-64), so a `pyforge-marshal` conda package with `bmad-loop` as a run-dependency is a one-command install of the *entire* stack. No competitor ships through conda; PyPI + npm + curl-installers are the norm. Secondary channels: PyPI wheel/sdist (matching the `pyforge-warden` precedent), and a GitHub release.

**Partnership strategy.** The highest-value "partnership" is upstream contribution to `bmad-code-org/bmad-loop`: idle-strand detection, per-story model tiering, and the hard-coded `planning_artifacts` composition fix all belong upstream. Contributing them buys goodwill, reduces Marshal's own surface, and mitigates the single-upstream dependency risk.

**Growth phases.** (1) Internal product — replace the hand-rolled shell watchdogs and manual paper-trail promotion in this factory. (2) OSS release once the conformance matrix covers ≥2 adapters. (3) Enterprise only if air-gap + audit demand materialises.

---

## 7. Risk Assessment and Mitigation

| Risk | Evidence | Mitigation |
|---|---|---|
| **Upstream (bmad-loop) stalls or breaks** — the aider/Roo failure mode | aider: 0 commits in 9 weeks, 1,762 open issues. Roo: archived with 1,036 open issues | Wrap, do not fork: keep the coupling surface small and versioned; pin the dep; contribute fixes upstream; maintain an adapter-boundary contract so a future fork is possible but not required |
| **Category vocabulary is damaged** | ruflo's fabricated benchmark + 290 stub tools, 65.9k stars | Never market on topology/agent counts. Market on gates, verification, reproducibility |
| **"Harness engineering is not enough"** | wsff.md, 376 HN points | Answer it directly in the PRD: gates + human review at each vertical slice are the prescription, not the counter-argument |
| **Review burden negates throughput** | 16.5 review comments/PR; 5–9 hours of review created | Make review cost a first-class metric; invest in scope-checks and frozen-surface guards that cut what a human must re-read |
| **A competitor ships the same thesis first** | OpenHands Verification Stack, funded, 82k stars | Ship the narrow differentiators (escalation, concurrent gated loops, spec-as-contract) rather than the broad one |
| **Benchmark credibility** | No dollar-per-task on the official SWE-bench leaderboard; fabricated numbers in-category | Publish only first-party, reproducible run evidence; never claim a benchmark number without a public artifact |

---

## 8. Success Metrics

**Primary** — stories merged per unattended run without human intervention; escalation precision (share of escalations a human agrees were genuinely undecidable); zero false-green merges (a story never merges without a green deterministic verify).

**Secondary** — concurrent loop homes sustained; dollars per merged story; time from spec approval to merge.

**Counter-metrics (do not optimize)** — raw story throughput (optimizing it re-creates the Devin failure: days spent on impossible solutions); number of agents/topologies (the ruflo trap); reduction in escalation count (fewer escalations is only good if precision holds).

---

## 9. Future Outlook

**Near term (1–2 years).** Gating converges on a small vocabulary — sandbox × approval-policy as orthogonal axes (Codex), tiered per-invocation autonomy flags (Factory), and PR/CI as the platform-enforced backstop (GitHub). Expect spec-driven tooling to acquire enforcement; expect at least one OSS project to ship a critic/verifier layer.

**Medium term.** The socket standardizes. ACP (Agent Client Protocol) already carries a versioned schema, neutral governance, a 38-agent registry with pinned launch commands, and gate primitives — permission requests with a tool-kind taxonomy, session modes, cancel, and normalized stop reasons. Orchestrators that speak one protocol will outlive orchestrators that maintain N hand-written CLI adapters.

**Strategic investments.** Verification and evidence, not generation. The bottleneck claim is now made independently by the leading OSS competitor, by Microsoft's own retrospective, and by the category's sharpest critic.

---

## 10. Methodology and Source Verification

**Primary sources:** vendor documentation sites (docs.openhands.dev, docs.devin.ai, learn.chatgpt.com, docs.github.com, jules.google/docs, docs.cline.bot, aider.chat/docs, docs.factory.ai, ampcode.com), pricing pages, official engineering blogs, GitHub REST API (stars, releases, participation, code/issue search), npm registry, PyPI JSON, HN Algolia API.

**Quality assurance.** Every quantitative claim carries an as-of date of 2026-07-25 and a traceable source. Items that could not be verified against a primary source are tagged `[UNVERIFIED]`, specifically: USD-per-ACU (Devin), USD-per-credit (Codex), numeric concurrency caps (Devin/Codex/Copilot), the Copilot "coding agent"→"cloud agent" rename date, the Copilot Workspace sunset announcement, CODEOWNERS behaviour on Copilot agent PRs, Cline's dollar pricing, ZooCode's canonical repo, and the Faros AI post-adoption regression statistics (available only secondhand).

**Limitations.** Reddit and web.archive.org were unreachable; community sentiment is HN-only. Pricing in this category changed materially twice in the research window (GitHub 2026-06-01, Devin ACU→credits) — **re-verify any dollar-dependent decision before acting on it.**

---

## 11. Appendix — Comparison Matrix

*All figures as of 2026-07-25.*

| Product | Gating model | Spec-driven | Autonomy gradient | Concurrency | Distribution | Price |
|---|---|---|---|---|---|---|
| **OpenHands** | Strongest OSS: confirm-policy + 4 security analyzers + 6 hook events (`exit 2` blocks; `Stop` can block completion) + Docker sandbox. **Headless hard-locked to always-approve** | Medium — AGENTS.md + AgentSkills (keyword- and path-triggered) | Tunable attended; **none headless** | asyncio parallel conversations; **sub-agents sequential-only**; container/session | 82,024★; PyPI `openhands-ai` 1.11.0; npm; Docker; GH Action; SaaS; K8s | OSS free (MIT except `enterprise/` = PolyForm); SaaS free 10 conv/day; Enterprise custom |
| **aider** | Commit-per-change audit + `/undo`; `--auto-lint` on, `--test-cmd` retry — **no attempt limit, no loop-until-green, no sandbox** | Low — `CONVENTIONS.md` via `--read` | Effectively binary (`--yes`) | **None** | 47,683★; PyPI 0.86.2 (2026-02-12). **Last release 2025-08-09; 0 commits/9wk** | Free, Apache-2.0, BYO key |
| **Cline** | 8 toggleable auto-approve categories + YOLO; shadow-git checkpoints, 3 restore modes | Low — `.clinerules` / AGENTS.md | **Best in OSS tier** — per-category | Checkpoints; no worktrees; CLI `--auto-approve` | 65,038★ Apache-2.0; VS Code/JetBrains + `npm i -g cline` | Free OSS, BYOK; **no published $** `[UNVERIFIED]` |
| **Devin** | Weak per-session; hard gate only on parallel fan-out. Org-level **AI Guardrails** `log_only→…→kill_session` | Medium as context, low as contract | Coarse, **effort**-flavored | **Best-in-class** — parallel VMs + "Devin Manages Devins" | Web, CLI (+ACP), Desktop, Slack, Jira, REST v3 | Pro **$20** · Max **$200** · Teams **$80 + $40/seat**. **$/ACU unpublished** |
| **Jules** | **`AWAITING_PLAN_APPROVAL` + `approvePlan` API** — cleanest programmable gate. **UI auto-approves on a timer** | Low — AGENTS.md; plan generated not supplied | Near-binary | **Only published numbers: 3/15/60** by tier | Web, REST `v1alpha`, `npm i -g @google/jules`. **GitHub-only; gmail.com-only paid** | Bundled: AI Pro **$19.99** / Ultra from **$99.99**. No standalone SKU |
| **Codex** | **Most granular:** 3 sandboxes × 4 approval policies (orthogonal), VCS-aware trust, network off by default, **auto-review w/ 3-consecutive / 10-in-50 circuit breaker** | **Highest of hosted** — layered AGENTS.md + `AGENTS.override.md`; `## Code Review Rules` executed | **Fully continuous**, per-invocation or org-pinned | Parallel cloud tasks; local **Worktree** mode | ChatGPT surfaces, **open-source CLI**, GH Action, `@codex` bot, SDK, MCP | Go **$8** · Plus **$20** · Pro from **$100** · Business **$20/user**. **$/credit unpublished** |
| **ruflo (claude-flow)** | **Effectively none**; docs recommend disabling the agent's permission system | Inverted — specs agent-*generated* | Max, no brakes | Worktrees delegated to Claude Code | npm ~690k dl/mo; 65,885★ | Free, MIT |
| **Claude Agent SDK** | Documented 6-step order; **subagents inherit `bypassPermissions`**; `PreToolUse` is the only universal gate | Prompt + filesystem contracts | Tunable per mode | Built-in worktree tools | npm 31.2M dl/mo + PyPI | Free SDK, **Anthropic Commercial Terms** |
| **LangGraph** | Typed HIL `interrupt()`/`Command(resume=)`; needs checkpointer + `thread_id` | Graph authored in code | Author-defined | Graph fan-out; no worktrees/containers | PyPI + npm; 38,104★ | MIT free; LangSmith $0 / **$39/seat** / custom |
| **Copilot cloud agent** | **Strongest published hosted:** write-access triggers only, one `copilot/` branch, branch protection applies, **Actions need human "Approve and run"**, **cannot mark ready / approve / merge**, requester can't approve. Gaps: content exclusions ignored, firewall skips MCP, MCP tools used without approval | Issue-driven + rich instruction files. **Spec Kit (123,718★) = sequencing, not gates** | Largely binary per session | Agent HQ; **1 repo / 1 branch / 1 PR / 59-min hard cap** | github.com, VS Code, Mobile, CLI, API, MCP, Jira/Linear/Slack | **AI credits since 2026-06-01, 1 cr = $0.01.** Pro **$10** · Pro+ **$39** · Max **$100** · Business **$19/seat** · Ent **$39/seat**; also burns Actions minutes |
| **Factory Droids** | **Tiered `--auto low\|medium\|high`** + `--worktree` + Droid Shield (blocks commit/push on secrets) | **Spec-capable** — `--use-spec`, `--spec-model` | **Per-invocation CLI contract** — cleanest in market | `--worktree`, `--session-id`, `--fork` | npm `droid` 0.180.0; desktop, IDEs, Slack; **on-prem/air-gapped** | Pro **$20** / Plus **$100** / Max **$200**; no free tier |
| **Amp** | **Loosest** — no pre-approval for tool execution | Prompt-driven; no spec artifact | "The Dial" rates **task difficulty** | **Orbs** (persistent remote machines); subagents | curl installer; CLI, IDEs, web, Slack | Megawatt **$20** / Gigawatt **$200**; PAYG 0% markup; **Enterprise +50%** |
| **mini-swe-agent** | Sandbox only; **no approval by design** | Prompt | None | Batch/eval | 6,014★ MIT; `pip install mini-swe-agent` | Free |
| **Sweep** | IDE human-in-loop | Prompt | None | None | JetBrains plugin. Repo dead; **not open source** (EE licence) | $10 / $20 / $60 per month |
| **Codegen** | Historical | Prompt/ticket | — | Historical sandboxes | **Shut down 2026-01-16** | n/a |
