---
title: Marshal — graduated autonomy on the factory floor
status: draft
created: 2026-07-25
updated: 2026-08-01  # competitive re-framing + Epic-1 shipped facts + Q3 resolution (see JSON block)
project: pyforge-marshal
dist: pyforge-marshal
module: pyforge.marshal
cli: marshal
owner-dream: docs/dreams/pyforge-marshal.md
mode: headless
inputs:
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/ecosystem-crew.md
  - docs/dreams/agent-portability.md
  - docs/dreams/agentic-sdlc-autonomy.md
  - _bmad-output/projects/local-recipes/planning-artifacts/specs/spec-bmad-loop-governance/SPEC.md
  - _bmad-output/projects/local-recipes/planning-artifacts/specs/spec-multi-loop-isolation/SPEC.md
  - docs/specs/bmad-loop-adoption.md
  - planning-artifacts/research/market-agent-orchestration-research-2026-07-25.md
  - planning-artifacts/research/domain-agent-portability-and-governance-research-2026-07-25.md
  - planning-artifacts/research/technical-bmad-ecosystem-verification-research-2026-07-31.md
  - planning-artifacts/research/market-agent-orchestration-research-2026-07-31.md
  - planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
---

# Product Brief: Marshal

## Executive Summary

**Marshal** is the orchestration station of the pyforge Ecosystem Crew, productized: a deterministic CLI (`marshal`) that turns an approved spec into merged, verified code through gated, unattended development loops — and escalates to a human anything it cannot safely decide. Autonomy is a gradient, not a leap: attended stories first, then unattended loops wrapped in verify gates and quality gates, with every run visible in a durable journal.

The capability already exists and already shipped real systems. It began as a hand-assembled stack — the external `bmad-loop` orchestrator plus `scripts/bmad-switch` and `scripts/bmad-loop-worktree` — which drove **pyforge-atlas to 57/57 stories** and **pyforge-warden to 43/43**, with **eight concurrent loop homes** on one machine. *(Updated 2026-08-01:)* **the product's first epic has now shipped through its own line** — Epic 1 · 10/10, six commands (`init · homes · preflight · config · teardown · --version`), 785 tests, coded `MRS-*` envelopes, one import-linter-enforced harness seam. What remains ahead: the supervisor for the failure modes the raw loop does not catch (Epic 3), gates as objects (Epic 2), the landing paper trail and PR lifecycle (Epic 4, now in charter), fleet status (Epic 5), and the portability layer proven rather than claimed (Epic 6).

The market timing remains favourable, but the slot **narrowed between intake and now** — the 2026-07-31 refresh (`market-agent-orchestration-research-2026-07-31.md`) supersedes this paragraph's original framing. Gated-unattended is no longer the differentiator: "Ralph loops" made overnight autonomy with stop criteria a named industry practice; Claude Code Auto Mode ships layered in-session safety with approval checkpoints first-party; and **Composio AO — the closest competitor — runs worktree-isolated agents that manage their own PR lifecycle behind milestone gates**. The intake-era observations (OpenHands hard-disabling approval headless, Jules auto-approving on a timer, Spec Kit's recommended-not-enforced sequencing) still hold individually. What remains genuinely unclaimed is **four properties in combination**: the spec as an *executable contract* (frozen-surface scope checks — everyone stops on tests, nobody on contract conformance); the supervisor *outside the session*, un-disableable; **never-false-green** as a verdict lattice (unevaluable ≠ pass); and the paper trail that *survives teardown*. Marshal's slot is those four, self-hosted, with first-party run evidence.

---

## The Problem

An operator running many projects with agent labour hits four failures that no available tool addresses together.

**The gate disappears exactly when it matters.** Attended, every product will ask before it acts. Unattended — the mode that actually produces throughput — OpenHands is documented as "always runs in `always-approve` mode… this cannot be changed," and its scheduled Automations "run unattended without requiring human approval." The operator's real choice today is *supervised and slow* or *unsupervised and fast*.

**Unattended runs fail silently and expensively.** This factory has the receipts. A mid-response API connection drop leaves a dev or review session **parked at the prompt with no idle detection**, burning to the per-session token cap (~4M weighted) or the time cap before it defers — this cost three story attempts and one full review cycle in a single wave, and had to be papered over with a hand-written `tmux` + log-mtime watchdog script. Earlier, a 90-minute session cap killed the keystone story mid-work and **burned 25.8M tokens that the retry contract cannot reuse**. The industry pattern is identical: every verifiable runaway-cost incident traces to unbounded loops, no real-time spend visibility, or a poll interval longer than the prompt-cache TTL.

**The paper trail evaporates.** Story specs are the contract in a spec-driven build, and they were being written into gitignored Tier-3 worktrees that the loop cleans up after merge. By 2026-07-25, of 31 warden story specs **only 10 survived intact; 8 were zero-byte husks; 13 were gone entirely** — all of Epics 3 and 4. All were recovered, but only by mining Claude Code session transcripts and a surviving run-worktree snapshot. The sibling project pyforge-atlas was less lucky: 30 of 32 originals are unrecoverable. Promotion of a merged story's spec into tracked storage is now convention — and entirely manual.

**Operating the loop is a set of memorized rules.** Resumes must be backgrounded or a foreground timeout kills them mid-review. Model tiering is per-run, not per-story, so hard-story batches require hand-editing `policy.toml` between batches — the file literally carries a "HARD-STORY BATCH PROCEDURE" comment naming which stories to flip. Doc-only stories trip a "no changes in worktree" false negative and rollback-loop. A story that defers with "review did not converge" but is demonstrably sound must be landed by hand with an exact commit subject string that the dashboard's status detection keys on. `worktree_seed` carries a hard-coded project slug that must be edited on every project switch. None of this is written down anywhere a machine can enforce it.

**And the portability charter is unmet.** The Crew's doctrine is that the method is the asset and the agent is a socket. `bmad-loop` 0.9.0 ships six adapter profiles — claude, codex, gemini, copilot, antigravity, opencode — but **four of them look for skills in `.agents/skills/`, and this repo's 92 skills live only in `.claude/skills/`**. Running the loop on anything but Claude Code today would find no skills at all.

---

## The Solution

`marshal` is thin porcelain over the proven machinery plus the supervisory layer that machinery lacks. Four verbs, matching the Crew charter:

- **`marshal init`** — provision an isolated loop home: a git worktree on `loop/<slug>`, per-worktree BMAD project switching, a single-sourced Tier-3 backlink, composed run policy, adapter skill-tree projection, and a preflight that fails loudly instead of hanging on a first-run trust dialog.
- **`marshal factory spin`** — launch or resume a gated run against an approved spec. Backgrounded by default (the foreground-timeout footgun becomes structurally impossible), with a **supervisor** attached: idle-strand detection, hard token and wall-clock ceilings, and escalation surfacing.
- **`marshal gate evaluate`** — run the deterministic verify gates and scope checks standalone, callable by a human, by CI, or by the loop. The gate is a first-class, independently invocable object rather than a config line.
- **`marshal deploy`** — land merged work: batch pull request, **automatic promotion of each merged story's spec into tracked planning artifacts**, sprint and console feed refresh, and merge-subject conformance.

Plus two supporting surfaces: **`marshal status`** for a fleet view across all loop homes, and **`marshal adapters`** for skill-tree projection, adapter probing, and a conformance matrix recording which agents actually work here.

The governing principle stays the Crew's execution doctrine, unchanged: **skills are the unit of execution; the deterministic harness is the unit of governance, and is deliberately not a skill** — because the thing that governs the agent cannot be a thing the agent authors. `marshal` is harness, not skill.

---

## What Makes This Different

**Gated and unattended — now table stakes; the contract and the outside supervisor are the difference.** *(Re-framed 2026-08-01.)* The unattended gradient exists elsewhere (Factory's `--auto`, Codex's sandbox × approval axes, Auto Mode's checkpoint ladder, Ralph-loop practice). What no surveyed product carries: progression gated on *contract conformance* rather than tests alone, and enforcement ceilings reachable from **outside the session** — a wedged agent is never its own witness. Marshal's gate modes still map onto the published autonomy taxonomy, targeting **L4 "Approver"**; upstream `bmad-loop` 0.9.0's new *in-session* budget guards sharpen rather than erode this claim, since the supervisor's premise was always externality (NFR-4), not the mere existence of a ceiling.

**The spec is an executable contract, not a context file.** Every competitor's "spec" is context injection — `AGENTS.md`, Devin Knowledge and Playbooks, aider's `CONVENTIONS.md`, `copilot-instructions.md`. Marshal consumes a spec carrying acceptance criteria and gates progression on satisfying them, with frozen-surface scope checks so a producer story cannot silently amend a contract another story froze.

**Escalation-on-uncertainty is a primitive, not a hope.** The canonical field critique of autonomous agents names this exactly: "Devin would spend days pursuing impossible solutions rather than recognizing fundamental blockers." Anything the agent cannot safely decide pauses the run for a human, and the resolution is captured as spec amendment rather than chat.

**N concurrent gated loops as the product.** *(Updated 2026-08-01 — the adjacent space filled; the claim narrows and holds.)* Conductor now ships a parallel-worktree dashboard (attended-only) and Composio AO ships per-agent worktrees with PR lifecycle management — the hand-rolling era is ending. What neither carries: **verified isolation as a command** (`marshal homes` — the machine that caught six homes running another station's verify), teardown that refuses to destroy unmerged work, and merge discipline bound to contract conformance. This factory runs eight homes; the provisioning half of the product is shipped and tested.

**Honest moat statement.** The moat is not technical novelty — it is *composition plus evidence*. Every ingredient exists somewhere; nobody has assembled them, and nobody can point at two complete systems shipped through their own gated loop. In a category where the loudest benchmark number was independently found to be generated by `random.uniform()`, first-party reproducible run evidence is the only credible currency.

---

## Who This Serves

**Primary — the solo or small-team factory operator.** Many projects, one operator, wanting unattended throughput without surrendering the audit trail. This is the reference customer: this repo, running seven loop homes across the pyforge Crew. Success looks like a wave of stories merging overnight with a journal the operator can read in the morning and a spec archive that is complete without anyone remembering to copy files.

**Primary — the OSS maintainer running batch refactors.** Bounded, reviewable, cheap parallel work across many repositories, where review burden is the real cost. Microsoft's own ten-month retrospective quantifies it: agent PRs drew **16.5 review comments each versus 12.4 for human PRs**, and 52.3% needed direct human commits. Success is cutting what a human must re-read, not raising raw throughput.

**Secondary (v2) — regulated and air-gapped teams**, who need self-hosting and an audit story that no hosted agent can offer off-platform.

**Explicit non-user.** The individual wanting inline completion or IDE chat. That is Copilot and Cursor territory, and Marshal has nothing to add there.

---

## Success Criteria

- **Zero false greens.** A story never merges without a green deterministic verify and a scope check. Non-negotiable — it is the property the whole product sells.
- **No silent burn.** Every unattended run either completes, escalates, or is stopped by a budget or idle ceiling with a named reason. The idle-strand class of failure that cost three story attempts in one wave does not recur.
- **Complete paper trail, unattended.** 100% of merged stories have their spec promoted into tracked planning artifacts automatically. The 13-specs-lost incident is structurally impossible.
- **Escalation precision.** A human reviewing escalations agrees they were genuinely undecidable — the metric that keeps the gate honest rather than merely frequent.
- **Concurrency holds.** Loop homes run simultaneously with verified isolation and no cross-project state bleed.
- **Portability is proven, not claimed.** A conformance matrix shows, per adapter, whether a canonical smoke story completes here — evidence, not a support table.
- **Counter-metrics (do not optimize):** raw story throughput; number of adapters or agents supported; reduction in escalation count.

---

## Scope

**In, for v1.** The four charter verbs plus `status` and `adapters` — and, per the 2026-07-31 operator ruling (`docs/dreams/pr-lifecycle.md`, contracted as SPEC CAP-9), **`marshal land`: the PR lifecycle as declared policy** with teardown-grade refusals. Loop-home provisioning and isolation verification. Run supervision — idle-strand detection, token and time ceilings, escalation surfacing, durable run journal. Gate evaluation with frozen-surface scope checks and a gate-mode ladder mapped to autonomy levels. Adapter skill-tree projection, probing, and conformance recording. Batch-PR landing with automatic story-spec promotion and merge-subject conformance. Distribution as a conda package (with `bmad-loop` as a run dependency) plus a wheel.

**Out, for v1.** Forking or reimplementing `bmad-loop` — see the wrap-versus-absorb decision, resolved in the PRD. Any Copilot HTTP proxy or sideloaded VS Code extension — superseded, because `bmad-loop` already drives the sanctioned Copilot CLI directly and the proxy path is unversioned, reverse-engineered, and abuse-detection-exposed. The `@bmad` Copilot-Chat adapter — a human-in-the-IDE surface, deferred and re-owned. Speaking ACP as the adapter contract — a scheduled migration with an explicit revisit trigger, not a v1 bet. Windows-native operation — the harness is POSIX-multiplexer-bound, though upstream is moving. Sandboxing and container isolation beyond worktrees — real and necessary, but Steward's provisioning territory.

---

## Vision

Two to three years out, Marshal is the reference answer to a question the industry is only starting to ask properly: *how do you let agents build software unattended without giving up the ability to prove what happened?* The gate configuration becomes the autonomy declaration — machine-readable, diffable, reviewable, and the thing an auditor reads instead of a marketing claim about "levels." Loops run across a fleet under resource budgets rather than one at a time under a watchful eye. And the socket thesis lands: the same Dream, the same spec, the same gates, running on whichever agent the team happens to hold a subscription to — with a conformance matrix proving it rather than a compatibility table asserting it.

---

## Assumptions

- **A1.** The reference customer is this factory and its operator; there is no external customer discovery. Success criteria are drawn from live operational evidence, not interviews.
- **A2.** `bmad-loop` remains actively maintained upstream. It moved 0.8.1 → 0.9.0 within the adoption window, gaining pluggable multiplexers and six adapter profiles. *(Re-verified 2026-08-01, STRENGTHENED: ten releases Jun 29 → Jul 21; predecessors retired cleanly — `bmad-automator` archived Jul 13 with a migration notice to bmad-loop; the method repo at 51k stars with "Dev Loop Automation" on its roadmap — logged as a convergence watch item on the §5.4 revisit list, not a fork trigger.)*
- **A3.** BMAD Method conventions (`sprint-status.yaml`, `epics.md`, planning/implementation artifact tiers) remain the story-feed contract.
- **A4.** Linux and macOS are the supported hosts for v1; Windows is WSL-only, consistent with the harness. *(Note 2026-08-01: upstream v0.9.0 shipped a Windows psmux backend — the assumption stands for v1, but the FR-58 register's "non-POSIX multiplexer" upstream-gap entry needs updating.)*
- **A5.** Distribution through the local conda channel is acceptable for v1; `bmad-loop` is packaged here but not yet on conda-forge (`cfe-on-conda-forge-status: pending-submission-to-conda-forge`).
- **A6.** Per repo convention (matching `deckcraft` and `pyforge-warden`), this brief is written flat into `planning-artifacts/` rather than into a `briefs/<run-folder>/` workspace with a `.memlog.md`; the brief's own frontmatter carries the input provenance.

## Open Questions

- **Q1.** Wrap versus absorb — thin porcelain over `bmad-loop`, or absorb the loop into the distributable? **Resolved in the PRD; recorded here as the brief's central open question at intake.**
- **Q2.** Ownership of the AGENTS.md entry-file family. `AGENTS.md` states "Keeping the Dream → spec handoff portable across agents is **Herald's** job," while `docs/dreams/agent-portability.md` records portability as re-scoped to **Marshal** in the 2026-07-23 ownership review. One of the two is stale.
- **Q3.** ~~Does `marshal` own PR-lifecycle automation?~~ **RESOLVED 2026-07-31 (operator): Marshal owns it** — `docs/dreams/pr-lifecycle.md`; contracted as SPEC CAP-9; the Scope section updated accordingly.
- **Q4.** Should the fleet-level resource budget (a Dream frontier item) be v1 scope, or does it wait for a second project running loops?
- **Q5.** Is a `marshal`-emitted OpenTelemetry `gen_ai.*` trace worth v1 cost? *(Re-verified 2026-08-01: still Development-stability; the June 2026 move was a repo split, not a graduation — deferral holds.)*
- **Q6.** What is the trigger condition for migrating the adapter layer to ACP? *(Re-verified 2026-08-01: ACP at v0.13.6, registry live, JetBrains/Google adoption — none of the recorded triggers fired; deferral holds, revisit pressure rising.)*

---

```json
{
  "status": "complete",
  "intent": "update",
  "updated": "2026-08-01",
  "update_summary": "Competitive framing narrowed to four unclaimed properties (spec-as-contract, external supervisor, never-false-green, teardown-surviving trail; Composio AO named closest); Epic-1-shipped facts (10/10, six commands, 785 tests) folded into the summary; fleet numbers 57/57, 43/43, eight homes; marshal land added to v1 scope per CAP-9; A2 strengthened and A4 annotated from the 2026-07-31 verification research; Q3 resolved, Q5/Q6 re-verified as holding.",
  "brief": "_bmad-output/projects/pyforge-marshal/planning-artifacts/product-brief-pyforge-marshal.md",
  "open_questions": [
    "Q1 wrap-vs-absorb (resolved downstream in the PRD)",
    "Q2 AGENTS.md family ownership: Herald (per AGENTS.md) vs Marshal (per agent-portability Dream)",
    "Q3 RESOLVED 2026-07-31: Marshal owns the PR lifecycle (CAP-9)",
    "Q4 fleet-level resource budgets in v1?",
    "Q5 OTel gen_ai.* emission — deferral holds (re-verified 2026-08-01)",
    "Q6 ACP migration trigger — unfired (re-verified 2026-08-01)"
  ],
  "assumptions": [
    "A1 reference customer is this factory; no external discovery",
    "A2 bmad-loop remains actively maintained upstream",
    "A3 BMAD Method conventions remain the story-feed contract",
    "A4 Linux/macOS hosts only for v1",
    "A5 local conda channel acceptable for v1 distribution",
    "A6 flat planning-artifacts output per repo convention; no briefs/ run-folder or .memlog.md"
  ]
}
```
