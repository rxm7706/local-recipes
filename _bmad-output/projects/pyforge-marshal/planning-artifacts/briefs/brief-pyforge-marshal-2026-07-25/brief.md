---
title: Marshal — graduated autonomy on the factory floor
status: draft
created: 2026-07-25
updated: 2026-08-02  # genesis-installer brief consolidated in as a Satellite section (explicit user override); competitive re-framing + Epic-1 shipped facts + Q3 resolution (see JSON block)
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


---

## Satellite: Genesis Installer

**Consolidated 2026-08-02 — see
`archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/research/product-brief-pyforge-genesis.md`
for the original standalone document.** The section below is the genesis-installer product
brief, folded into this single Marshal-station brief verbatim (own status/frontmatter
preserved below for traceability), per explicit user override of the "kept separate on
purpose" decision recorded in `docs/dreams/pyforge-marshal.md` / `docs/dreams/genesis-installer.md`. Nothing in Marshal's
own brief above this line was changed.

**Original frontmatter** (`research/product-brief-pyforge-genesis.md`):

```yaml
title: "Product Brief: pyforge-genesis (Genesis)"
status: "complete"
created: "2026-07-25"
updated: "2026-07-25"
inputs:
  - "{project-root}/docs/dreams/pyforge-genesis.md (Tier-0 Dream — the seed)"
  - "{project-root}/docs/dreams/ecosystem-crew.md (founding Dream — the eight personas)"
  - "{project-root}/docs/dreams/README.md (Dream conventions, Tier-0 contract)"
  - "{project-root}/archive/docs/bmad-setup-plan.md (the origin document — Phases 0–10)"
  - "{project-root}/AGENTS.md (tiers + portability contract)"
  - "{project-root}/CLAUDE.md (multi-project pattern, durable story specs, sync loop)"
  - "{project-root}/_bmad-output/PROJECTS.md (multi-project index + registration procedure)"
  - "{project-root}/scripts/bmad-switch, {project-root}/scripts/bmad-loop-worktree"
  - "{project-root}/docs/intake/gists/how-we-operate/HOW-WE-OPERATE.md"
  - "planning-artifacts/research/domain-research-scaffolder-landscape.md"
  - "planning-artifacts/research/technical-research-installer-implementation.md"
references:
  - "https://copier.readthedocs.io/en/stable/updating/ — the update algorithm Genesis wraps"
  - "https://github.com/github/spec-kit — closest comparable: an installer for a way of working"
  - "https://nx.dev/docs/features/automate-updating-dependencies — two-phase migrate (plan, then apply)"
  - "https://projen.io/docs/introduction/getting-started/ — synthesis model (regenerate, don't merge)"
  - "conda-forge/copier-feedstock v9.17.0 — noarch:python, MIT (verified live 2026-07-25)"
project_slug: "pyforge-genesis"
```

### Product Brief: pyforge-genesis (Genesis)

#### Executive Summary

**Genesis** packages this repository's proven operating model as an installable tool.
Two verbs: **`genesis init`** creates a new repository born Dream-first — `docs/dreams/`,
the tier layout, the AGENTS.md family, BMAD multi-project wiring, the deck family, from
day zero. **`genesis adopt`** layers that same model onto an existing repository without
disturbing what already runs. Distribution: dist `pyforge-genesis` / module
`pyforge.genesis` / CLI `genesis`.

The model Genesis installs is not theoretical. It was installed *here*, by hand, from a
562-line setup plan (`archive/docs/bmad-setup-plan.md`), and then run hard enough to
prove it: **pyforge-atlas** shipped 32 stories across waves 0–H through it (PRs #58–#105);
**pyforge-warden** shipped 31 stories across 6 epics through it (PR #110); fifteen BMAD
projects now share one installation; 25 Dreams sit at Tier 0 with a no-straggler policy
binding each to exactly one project. The Dream set the gate — *"awaits its own
`bmad-spec` run when the model stabilizes"* — and the model has stabilized. This brief
is the beginning of collecting on that.

The hard part is not scaffolding. Scaffolding is a solved commodity — Copier, cruft,
cookiecutter, and Nx generators all do it, and Copier is already a conda-forge package
(`copier` v9.17.0, `noarch: python`, MIT) that Genesis can simply consume. The hard part
is **the second install and every one after it**: when the model improves — a corrected
tier rule, a new drift-check finding, the durable-story-specs convention that landed on
2026-07-25 — how does an already-installed repository take that improvement? Every tool
in the field that failed, failed there. Genesis is designed backwards from that question.

#### The Problem

**1. The model is trapped in one repository.** Everything that makes this repo work —
Dream-first governance, the four tiers and the rules against crossing them, the
framework-neutral portability contract, the six-layer BMAD config merge, the
marker+symlink project switch, the durable-story-specs convention, the detector/reconciler
sync loop — exists as conventions written into `CLAUDE.md`, `AGENTS.md`, `PROJECTS.md`,
and two shell-invoked Python scripts. There is exactly one way to get it into a second
repository today: read the 562-line setup plan and do all ten phases by hand. The next
pyforge sibling, the next enterprise innersource monorepo (`unity-data-stack` is already
waiting), and every external adopter pays that cost from scratch.

**2. Hand-installed models drift the moment they are installed.** The origin document is
itself the evidence: it is dated `2026-07-18`, and by `2026-07-25` it is already behind
in at least three ways — it points spec-first work at the now-legacy `docs/specs/` Tier 1,
it lists a `scripts/bmad-loop-project` helper as "recommended, not yet built," and it
predates the durable-story-specs convention entirely. A hand-installed copy in another
repo would have frozen at *its* install date with no mechanism to catch up, and the
agents reading it would faithfully follow the stale rules. **For an operating model read
by autonomous agents, staleness is not documentation debt — it is a behavioral bug.**

**3. The cost of getting it subtly wrong is high and silent.** The model has sharp edges
that took production incidents to find. The marker/symlink desync ran undetected for 10
hours and came within one command of overwriting pyforge-warden's PRD and epics with
local-recipes content. Story specs were being written into a gitignored Tier-3 directory,
and pyforge-warden lost 13 of 31 of them to worktree teardown before anyone noticed —
recovered only because Claude Code session transcripts happened to preserve the tool
calls; pyforge-atlas, whose transcripts were not in the local store, permanently lost 30
of 32. A hand-installed model reproduces the *shape* of these conventions without the
*guards*, and the guards are the expensive part.

**4. Brownfield is the common case, and it is the dangerous one.** Most repositories that
should adopt this model already exist, already build, already ship. An installer that
overwrites a working `.gitignore`, clobbers an existing `CLAUDE.md`, or deletes a legacy
convention that is still load-bearing is worse than no installer. This repo's own
`docs/specs/` tier is the canonical example: superseded, but still holding five in-flight
efforts that must be preserved and *marked* legacy — never removed.

#### The Solution

Genesis is a small Python CLI that wraps a mature engine and adds the three things the
engine does not know about: the model itself, brownfield safety, and conformance.

**`genesis init <path>`** — greenfield. Materializes a complete Dream-first repository:
`docs/dreams/` with the README, frontmatter contract, and one seed Dream; the tier layout
with its gitignore rules; `AGENTS.md` carrying the portability contract plus the per-tool
adapter files for whichever agents the user selects; the BMAD multi-project subtree
(`_bmad-output/projects/<slug>/`, `.bmad-config.toml`, `PROJECTS.md` with the first row);
`scripts/bmad-switch` with its atomic marker+symlink switch; the drift detector wired
into CI; and the deck-family scaffolding.

**`genesis adopt`** — brownfield, and the verb that carries the product's risk. It runs
**detect → plan → confirm → apply**, dry-run by default:

- **Detect** walks the repo and classifies every model artifact as `absent`,
  `present-conformant`, `present-divergent`, or **`present-legacy`** — the state that
  exists specifically so a superseded-but-live convention is preserved and marked, not
  deleted.
- **Plan** emits a reviewable, committable artifact naming every proposed action. Nothing
  is written yet. (This two-phase split is Nx's `migrations.json` pattern, and it matches
  the detector/reconciler loop this repo already runs.)
- **Apply** materializes only what the plan says, preserving anything already present.
- **Re-running converges.** A second `adopt` on an already-adopted repo produces an empty
  plan and touches nothing.

**`genesis check`** — read-only, non-zero exit on drift. Runs in CI. This is the verb that
makes the model *stay* installed, and it is the one capability no comparable tool in the
field ships.

**`genesis update`** — the reason the whole thing is architected the way it is. The model
is versioned independently of the CLI; a repo records which model version it is at; an
update computes a plan, applies version-ordered migrations, and rewrites **only** the
regions Genesis owns.

That last point is the core design idea. Files split into four classes by *who owns them*:

| Class | Example | On update |
|---|---|---|
| **Referenced** | `bmad-method`, `copier`, `pixi` | version range only — nothing in the repo changes |
| **Copied (managed)** | `scripts/bmad-switch`, the drift detector | regenerated wholesale; hash-guarded against hand-edits |
| **Copied (seeded)** | a starter Dream, `.bmad-config.toml` | written once, repo-owned forever, never auto-touched |
| **Generated (derived)** | `.cursor/rules/specs.mdc`, `GEMINI.md`, `PROJECTS.md` rows | recomputed from the neutral contract + repo state |

And for the files that must be both — `AGENTS.md` and `CLAUDE.md` are narrative documents
a team writes in freely, *and* they carry the tier rules that must upgrade — a
**marker-delimited managed region**:

```markdown
<!-- genesis:begin managed-block=tiers model-version=1.4.0 -->
…generated; do not edit — run `genesis update`…
<!-- genesis:end managed-block=tiers -->
```

Only the span between markers is replaced. The file stays the team's. Deleting the markers
is a deliberate, greppable opt-out. Hand-editing inside them is detected by content hash
and reported by `genesis check`. This is the same two-zone discipline the repo already
runs on recipes, where agent-authored rationale parks in a bottom `# CFE comments` block
and human comments stay in the body.

**One hard structural guarantee:** the update path has no write access to Tier-0 or Tier-2
content. A repo's Dreams, PRDs, architectures, epics, and specs are unreachable from
`genesis update` by construction, not by convention. Upgrading the model can never touch
the work made with it.

#### What Makes This Different

| Dimension | cookiecutter / Yeoman / degit | cruft (on cookiecutter) | Copier | projen | spec-kit | **Genesis** |
|---|---|---|---|---|---|---|
| What it installs | app source | app source | app source | build config | a way of working | **an operating model** |
| Update after install | ✗ none | ✓ commit-hash diff | ✓ tag-ordered smart merge | ✓ regenerate (files not editable) | ✓ `self upgrade` (tool only) | ✓ **plan → migrate → apply** |
| Versioned migrations | ✗ | ✗ | ✓ | n/a | ✗ | ✓ |
| Brownfield adopt verb | ✗ | ✓ `link` (state only) | partial | ✗ | ✓ documented loop | ✓ **detect → plan → apply, dry-run default** |
| Editable files that still upgrade | ✗ | skip-globs only | conflict markers | ✗ by design | override layer | ✓ **managed regions** |
| Conformance check in CI | ✗ | ✓ `check` | ✗ | ✗ | ✗ | ✓ **`genesis check`** |
| Agent entry-point fan-out | ✗ | ✗ | ✗ | ✗ | ✓ 30+ agents | ✓ generated from one contract |
| Air-gapped | varies | ✗ (git fetch) | ✗ (git fetch) | ✗ (npm) | ✗ (GitHub releases) | ✓ **templates in-package, conda-provisioned** |

Two of those columns are the whole thesis. **Conformance checking** — every surveyed tool
stops at "here are the files"; Backstage, the most institutional of them, does not address
post-scaffold updates at all. And **managed regions** — the field's two update models are
projen's regenerate-everything (perfect fidelity, files not editable) and Copier's
three-way merge (editable, but produces conflict markers in documents humans are actively
writing). Neither works for `AGENTS.md`. The hybrid does.

The third differentiator is not technical: **the model itself is the product.** Copier
ships an engine and you supply the template. Genesis ships a specific, battle-tested
operating model — 63 stories of production evidence across two shipped projects — with an
engine attached.

#### Who This Serves

1. **The pyforge ecosystem, immediately.** Nine sibling projects (`herald`, `marshal`,
   `mason`, `doctor`, `scribe`, `steward`, `atlas`, `warden`, and the applications) plus
   `unity-data-stack` and `wasm-analytics-stack`. Several will graduate out of this
   monorepo into their own repositories; each needs the model installed correctly on day
   one rather than hand-copied and immediately stale.
2. **This repository, as the reference implementation.** `local-recipes` was the first
   brownfield adoption, done by hand. It becomes Genesis's regression oracle:
   `genesis adopt --dry-run` here must produce an **empty plan**. One mechanical test
   validates the entire model manifest — if Genesis's notion of the model disagrees with
   the repo the model was extracted from, the test fails.
3. **Teams adopting spec-driven, agent-run development.** The audience
   `HOW-WE-OPERATE.md` was written for — organizations that want documentation as
   programmable infrastructure and need a starting configuration rather than a blank page
   and a framework.
4. **Enterprise / air-gapped adopters.** A standing constraint in this repo and a real
   differentiator: with templates shipped in-package and the engine consumed as a conda
   package, `genesis init` runs with zero egress behind a firewall.

#### Success Criteria

**Primary (the master switch).** A second repository is created by `genesis init`, runs a
full Dream → spec → epics → loop-driven build, and **takes a later model upgrade via
`genesis update` without hand-editing** — with `genesis check` green before and after.

**Supporting, all mechanically testable:**

- `genesis adopt --dry-run` against `local-recipes` at the shipped model version produces
  an **empty plan**. (The oracle.)
- `genesis adopt` is idempotent: second run ⇒ empty plan, zero files changed.
- `genesis adopt` on a repo with a hand-edited managed region **refuses and reports**
  rather than overwriting.
- `genesis adopt --apply` on a dirty git worktree refuses.
- `genesis init` + `genesis check` = green, offline, **zero network calls** (egress-counter
  test, the pattern warden already established).
- A simulated breaking model change (v1 → v2) is absorbed by a migration in an installed
  repo with no manual edits.
- `genesis update` cannot write to `docs/dreams/**` or `**/planning-artifacts/**` — proven
  by test, not by policy.
- Time to a working Dream-first repo: **under 5 minutes**, versus the ten-phase manual
  setup plan.

**Kill criteria.** Genesis pauses or rescopes if: the managed-region merge proves
unreliable on real files (conflicts or corruption in the first two adopters); the empty-plan
oracle against `local-recipes` cannot be reached without special-casing the model into
incoherence (meaning the model is not actually extractable and the Dream's stabilization
gate was called too early); or the model changes so fast that migrations cost more than
hand-editing each installed repo would.

#### Technical Approach

**Wrap Copier, don't rebuild it.** Copier is on conda-forge at v9.17.0, `noarch: python`,
MIT, with a clean run-dependency set — consumed exactly as `pyforge-warden` consumes
`deptry` and `osv-scanner` from existing feedstocks (no new recipe, no runtime fetch). Its
public API is the surface Genesis needs: `run_copy` / `run_update` / `run_recopy`, with
`pretend` (dry-run), `skip_if_exists` (the brownfield primitive), `data` (programmatic
answers computed from inventory), `exclude`, `vcs_ref` (version pinning), and `conflict`.
Copier also brings the two most expensive pieces for free: the six-step update algorithm
and **migrations** — the only tool in the survey that has them. Genesis confines itself to
the three documented `run_*` functions; the internals are marked private upstream.

**Genesis builds four things Copier does not have:** the model content itself; the
brownfield inventory and plan; the managed-region post-pass; and `genesis check`.

**Packaging clones `pyforge-warden` exactly** — a pixi workspace member at
`src/shared/packages/pyforge-genesis/`, hatchling backend, `packages = ["src/pyforge"]`
namespace layout, `genesis = "pyforge.genesis.cli:main"` entry point, `pixi-build-python`,
and a lean environment with `no-default-feature = true` (required, not cosmetic: bmad-loop
worktrees materialize the lean env, never the fat `local-recipes` one). Root `pixi.toml`
gains a feature + environment via path dependency — there is no `[workspace] members` key
in pixi through 0.72.2.

**Templates ship inside the package**, spec-kit style, rather than being fetched from a
git-tagged repo (Copier's default). This is what makes air-gapped operation work, and
`--template <path|url>` covers development and forks. The trade-off is explicit: a model
change requires a package release.

**Two version numbers, both recorded in state:** the CLI version and the operating-model
semver. They move independently — the model is what installed repos track.

#### Boundaries With the Crew

Genesis is a `crew`-owned Dream, and it sits close enough to two siblings that the lines
must be drawn in the PRD or the products will overlap:

- **Marshal** owns *operating* the multi-project machinery — `scripts/bmad-switch`,
  `scripts/bmad-loop-worktree`, concurrent loop homes, graduated autonomy — after the
  2026-07-23 ownership review, and already advertises `marshal init --spec …`. **Genesis
  installs that machinery; Marshal runs it.** Proposed rule: Genesis's write scope is a
  repo's *structure and conventions*; Marshal's is a repo's *executions*. `marshal init`
  initializes a build from a spec; `genesis init` initializes the repo the spec lives in.
- **Doctor** owns pre-flight toolchain verification. `genesis check` asks *"does this repo
  conform to the model?"*; `doctor check` asks *"is this machine able to run the factory?"*
  Genesis should verify referenced-dependency presence by delegating to Doctor where the
  surfaces overlap, rather than growing its own probe suite.
- **Herald** owns the deck family Genesis scaffolds; Genesis lays down the directory and
  conventions, Herald fills and round-trips them.

#### Roadmap Thinking

- **V1** — `init`, `adopt`, `check`, `update`; the full model manifest; managed regions;
  migrations; in-package templates; the `local-recipes` empty-plan oracle; adapter fan-out
  for the four agents this repo already targets (Claude Code, Cursor, Copilot, Gemini).
- **V1.x** — feature modules (adopt a subset of the model: tiers only, or tiers + BMAD
  wiring); more agent adapters; `genesis check --fix` for mechanically-safe findings.
- **V2** — the model published as an independently versioned artifact for teams that fork
  it; conformance scorecards across a fleet of repos; a `genesis migrate` authoring flow so
  a model change *generates* its own migration.
- **Deliberately out of scope for V1** — hosted registry of installations, repo creation
  on a git host (`genesis init` makes a tree, not a GitHub repo), and non-git targets.

#### Known Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | Managed-region merge corrupts a file | pure span substitution (no three-way merge); hash guard; dry-run default; clean-worktree precondition so git is always the undo |
| R2 | The model is not actually extractable — too much of it is repo-specific | the empty-plan oracle surfaces this in V1, early; it is also the stated kill criterion |
| R3 | Model churn makes migrations a treadmill | model semver decoupled from CLI; only *managed* and *derived* classes ever migrate; seeded files never do |
| R4 | An upgrade damages a team's real work | structural guarantee: no write access to Tier-0/Tier-2 from the update path, enforced by test |
| R5 | Genesis and Marshal overlap and confuse users | boundary resolved explicitly in the PRD (§ Boundaries), before any code |
| R6 | Copier API drift | pin `>=9.17,<10`; public `run_*` only; version-range sync test (warden's established pattern) |
| R7 | Brownfield adopt breaks a working repo | dry-run default; `skip_if_exists`; `present-legacy` classification; refuses on dirty worktree |
| R8 | In-package templates couple model releases to package releases | accepted trade-off for air-gap; `--template` override for development and forks |

#### Assumptions

1. Genesis targets **git repositories only** — every update mechanism in the field depends
   on git for diffing, undo, and version pinning.
2. The operating model is **semver'd and released independently** of the `pyforge-genesis`
   package version.
3. Installed repos run `genesis check` in **their own CI**; Genesis is not a service and
   keeps no central registry of installations.
4. First two adopters are **this repo** (oracle) and **one greenfield pyforge sibling**;
   external adoption is a later concern.
5. The model has genuinely stabilized — the Dream's own gate. Evidence: atlas and warden
   both shipped through it; the durable-story-specs convention closed the last known hole
   on 2026-07-25.
6. `pyforge.genesis` coexists with `pyforge.warden` / `pyforge.atlas` in the `pyforge`
   namespace under the shared hatch layout. Not yet built and verified.
7. This repo's existing `bmad-drift-check` seeds the shipped detector rather than a
   from-scratch build. **Not yet validated against the code.**
8. `genesis adopt` must be idempotent — implied by detect/plan/apply, not directly
   documented by any surveyed tool.

#### Open Questions (for the PRD)

1. **The extraction manifest.** The Dream's central question. The research resolves the
   *rule* (classify by who owns the file and how it updates) and shows the Dream's
   three-way split is one class short — "copied" must divide into **managed** (tool-owned,
   updatable) and **seeded** (repo-owned after first write). The PRD must ratify the actual
   per-artifact manifest.
2. **Genesis ↔ Marshal boundary** — must be resolved explicitly (§ Boundaries proposes a
   rule; the PRD ratifies it).
3. **Does `genesis init` create a repository or only a tree?** (git init / remote / first
   commit, or not.)
4. **One model or composable feature modules?** Modularity is attractive; it multiplies the
   test matrix.
5. **CLI framework** — typer + rich (both already pinned; better for plan/diff/confirm UX)
   vs argparse (warden's lean-engine precedent). Note Copier already pulls in
   prompt-toolkit / questionary / pygments regardless.
6. **State file shape** — one Genesis-owned file, or Genesis state alongside Copier's
   `.copier-answers.yml` (which must never be hand-edited)?
7. **Marker syntax for non-markdown files** — `.gitignore`, `pixi.toml`, workflow YAML each
   have different comment syntax; a per-format marker registry may be needed.
8. **`genesis check` and `bmad-drift-check`** — reuse, extract, or re-implement?
9. **Legacy conventions as a first-class state** — is `present-legacy` recorded in the state
   file, and does the model define a deprecation path (e.g. `docs/specs/` → Tier 2)?
