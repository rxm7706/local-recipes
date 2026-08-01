# Market research — agent orchestration, 2026-07-31 refresh

> **Supersedes** `market-agent-orchestration-research-2026-07-25.md` for
> competitive framing; that document remains valid history. Inputs: the
> 2026-07-31 live-verification research (rounds 1–3, same folder), the
> operator-directed BMAD-ecosystem sweep, and the shipped state of Marshal
> (Epic 1 · 10/10). Purpose: give the brief (task 4) and PRD (task 5) a
> current competitive posture. Analyst pass in the Mary role; facts from the
> verification doc, not memory.

## 1. The market moved under the chain

Between the 2026-07-25 chain and today, three shifts matter:

1. **Gated-unattended became a named practice, not a differentiator.**
   "Ralph loops" — overnight autonomous loops with objective stop criteria,
   iteration caps, token budgets, stop hooks, and worktree isolation — are
   mainstream guidance. The *generic* claim "nobody combines the gate with
   unattendedness" is no longer defensible.
2. **First-party safety arrived.** Claude Code Auto Mode ships layered
   in-session safety (input filtering, action evaluation, two-stage
   classification, approval checkpoints, subagent outbound/return checks).
   The vendor itself now sells "gates + autonomy."
3. **The orchestrator layer commercialized.** Conductor (parallel worktree
   dashboard, attended) and Composio AO (per-agent worktrees + PRs, CI-fix +
   review-response + PR-lifecycle management, milestone gates) occupy the
   space Marshal's CAP-5/CAP-9 describe.

## 2. Competitive table (2026-07-31)

| Player | Unattended | Gates | Spec-as-contract | External supervisor | Paper trail | Notes |
|---|---|---|---|---|---|---|
| **Marshal (this)** | ✅ fleet, 8 homes | ✅ ladder + standing review | ✅ five-field kernel + frozen-surface scope checks | ✅ NFR-4, un-disableable | ✅ promote-before-teardown, journal-first | Epic 1 shipped; supervisor epics ahead |
| Claude Code Auto Mode | ✅ | ✅ in-session | ❌ | ❌ in-session safety | vendor transcripts (48h–180d) | first-party; subagent injection checks |
| Composio AO | ✅ | ✅ milestone | ❌ task-level | ❌ | PR-centric | **closest overlap** — incl. PR lifecycle (CAP-9) |
| Conductor (macOS) | ❌ attended | human review/merge | ❌ | ❌ | dashboard | fleet visibility only |
| Devin | ✅ delegated | ✅ coarse | ❌ | sandbox ≠ supervisor | vendor-side | $500+/mo; low operator skill target |
| OpenHands | ✅ self-host | DIY | ❌ | DIY | DIY | Docker-centric; regulated/academic niche |
| Copilot Coding Agent | partial | PR review | ❌ | ❌ | GitHub-native | collaborative-first |
| Ralph-loop practice | ✅ | tests-as-stop | ❌ tests ≠ contract | ❌ | ad hoc — **loses specs at teardown** | the pattern Marshal productizes *with* the contract |

## 3. The narrowed slot — four properties still unclaimed

1. **The spec is the executable contract.** Everyone stops on tests; nobody
   stops on *contract conformance* — per-story intent contracts, declared
   surfaces, frozen-surface scope checks at merge.
2. **The supervisor lives OUTSIDE the session** — a separate process the
   agent cannot disable, silence, or starve; every ceiling reachable from
   externally-observed quantities (NFR-4). Auto Mode's safety is in-session;
   a wedged session elsewhere is still its own witness.
3. **Never-false-green as a verdict lattice** — unevaluable ≠ pass, one exit
   authority, no path from "could not determine" to "clean". Stated by no
   surveyed tool.
4. **The paper trail survives teardown** — promotion-before-teardown off the
   disposable ref, journal-before-the-act. Ralph practice loses exactly this
   (and this factory paid 13/31 specs to learn it).

**Positioning instruction for the PRD (task 5):** replace "every competitor
trades away either the gate or the unattendedness" with the four properties;
add Auto Mode and Composio AO rows to the competitive analysis; keep the
counter-metric stance (throughput and adapter count deliberately not
optimized).

## 4. Ecosystem strength (supply side)

- BMAD-METHOD at **51,344 stars**, weekly activity, v6 current; roadmap names
  "Dev Loop Automation" — convergence watch item on the §5.4 revisit list,
  not a fork trigger.
- bmad-loop cadence: 10 releases Jun 29 → Jul 21 (v0.7.6 → v0.9.0);
  predecessors retired cleanly (automator archived Jul 13 with a migration
  notice). **Brief A2 (upstream maintenance) strengthens.**
- The conda-packaged distribution moat holds: eleven org packages installed
  from one channel — no surveyed competitor has a package-manager-native
  story for the whole method + engine + modules.
- Adjacent: ACP (v0.13.6, registry live, JetBrains/Google adoption) is the
  interop layer most likely to touch the adapter seam next — Q-6 triggers
  unfired, seam stays the hedge.

## 5. Calibration (for honest marketing + the video scripts)

SWE-bench Verified 20–45% across agents; practitioner-reported 60–80% on
well-scoped tasks. Industry consensus independently converged on this
factory's thesis: **invest in agent infrastructure and tests before
autonomy** — the tool matters less than the platform around it. Use the
fleet's own numbers (128/333, 0 frozen-surface violations, 0 guessed
escalations) rather than benchmark claims in outward material.

## 6. Marketplace note

`bmad-plugins-marketplace` (31 stars) is the community registry;
`bmad-labs-skills` (local 2.0.0, 21 skills) is its packaged consumption here.
No further inventory taken this round — the org survey (round 1) covers the
catalog; a per-plugin audit is deferred until a plugin enters factory use.
