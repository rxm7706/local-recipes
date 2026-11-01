# Glossary — Marshal

Companion to `SPEC.md`. The chain is Glossary-first by design so every downstream
artifact inherits exact vocabulary; these terms are part of the contract.

## Product identity

- **Marshal** — the display brand (PyForge Marshal on first mention per document).
  **`pyforge-marshal`** is the distribution, **`pyforge.marshal`** the import module,
  **`marshal`** the CLI. Display copy uses *Marshal*; file and package names use the
  lowercase technical form.

## The governance triad

- **Harness** — the deterministic, non-LLM machinery that governs an agent session:
  the orchestrator, the gates, the sandbox and permission boundaries, the verify
  commands. The unit of governance. **Never a Skill.** Marshal is harness.
- **Skill** — an LLM-executed workflow (a BMAD skill, a community plugin, a forged
  skill). The unit of execution. Runs *inside* the harness, wielded never worn.
- **Station** — the unit of accountability: a lifecycle stage plus its independent
  verdict. The hand that builds is never the gate that judges. Marshal holds the
  orchestration station; it does not hold Warden's, Doctor's, Steward's or Herald's.

## Run vocabulary

- **Loop** — one orchestrated run: a sequence of stories, each driven through
  dev → verify → review → verify → commit in fresh agent sessions.
- **Loop home** — an isolated working directory for one loop: a git worktree on branch
  `loop/<slug>` with its own BMAD active-project state and a backlink to the canonical
  Tier-3 store. Many loop homes coexist; `main` is never checked out twice.
- **Story** — the smallest gated unit of work, identified `<epic>.<seq>`.
- **Story spec** — the per-story intent contract (intent, acceptance criteria, and
  where present the dev/review triage log). Durable and git-tracked, not runtime
  scratch.
- **Run journal** — Marshal's own durable, append-only record of a run: story
  transitions, gate outcomes, escalations, budget consumption, supervisor actions.
- **Supervisor** — Marshal's out-of-band watcher over a running loop: idle-strand
  detection, budget ceilings, escalation surfacing, journal emission. Runs *outside*
  the agent session and cannot be disabled from inside it.
- **Idle strand** — an agent session that has stopped producing output but has not
  exited — typically a dropped connection mid-response — and will otherwise burn to a
  token or time cap before being noticed.
- **Escalation** — a halt because the agent encountered something it cannot safely
  decide (a spec contradiction or gap). Pauses the run; resolved by a human as a spec
  amendment, never as chat.
- **Deferral** — a story the loop could not land (attempts exhausted, review did not
  converge, budget or idle ceiling hit) recorded with a reason, leaving the run to
  continue.

## Gate vocabulary

- **Gate** — a checkpoint that must pass before a story progresses. Three kinds:
  an **approval gate** (a human releases the story), a **verify gate** (a deterministic
  command must exit zero), and a **scope check** (the story's changed surface must lie
  inside its declared surface).
- **Frozen surface** — a set of files declared contractually stable; later stories must
  not modify them. *(Who may declare one mid-run is review blocker F-5 — see
  `SPEC.md` § Open Questions.)*
- **Gate mode** — the run-level approval policy, and the autonomy declaration itself.

| Gate mode | Autonomy level | Meaning |
|---|---|---|
| `per-story-spec-approval` | **L2 — Task-Based / Operator** | Human approves each unit's contract before work proceeds. |
| `per-epic` | **L3 — Conditional / Context Gates** | Machine-readable boundaries; human at epic seams. The production ceiling. |
| `none` + verify gates + escalation | **L4 — Approver** | Runs independently; surfaces only at blockers or pre-specified conditions. |
| *(unbuilt)* fleet budgets, self-governance | **L5 — Observer** | Frontier. Explicitly out of scope. |

No vendor or analyst publishes an authoritative numbered scale for coding agents;
Anthropic explicitly declines, arguing autonomy is a property of the deployment. These
labels are adapted from DeepMind's Levels of Autonomy and the Operator→Observer framing,
and are declared as **Marshal's own documented tiering** — not an industry standard.

## Portability vocabulary

- **Adapter** — a coding-agent CLI the harness can drive (claude, codex, gemini,
  copilot, antigravity, opencode), described by a declarative profile.
  *Adapter* has three meanings in this Spec; read each by its qualifier
  (added 2026-11-01, EGM audit MAR-M-C6):
  1. **Adapter** (this entry) — a coding-agent CLI and its harness profile.
  2. **EGM adapter** — a reviewer persona's agent file in the EGM plugin
     (§ *Challenger vocabulary*). CAP-298 and CAP-299 use this sense.
  3. **A port's adapter** — the one impure implementation behind a port
     (Constraint *Pure decision core, impure edge*), such as the modules under
     `pyforge.marshal.adapters` (`adapters/challenge_harness.py`).
- **Skill tree** — the directory an adapter reads skills from. Divergent by adapter:
  `.claude/skills` (claude, opencode) versus `.agents/skills` (codex, gemini, copilot,
  antigravity). `.agents/` does not exist in this repository — that gap is the whole of
  Marshal's actual portability work.
- **Conformance matrix** — the dated, per-adapter record of whether a canonical smoke
  story completed here. The only place Marshal makes a portability claim.

## Challenger vocabulary (EGM, 2026-11-01)

Added 2026-11-01 from EGM audit MAR-M-C6 (cluster MAR-CL11) for CAP-298..CAP-303.

- **EGM (Elephant-Goldfish Model)** — Google's `google/elephant-goldfish-model`
  (Apache-2.0), a markdown-only Claude Code plugin installed as `egm@egm` and pinned by
  `[challenge].plugin_version` (default `0.1.0`). Its reviewer personas read one
  artifact with no house context. Marshal spawns its registered agents. It never
  invokes EGM's skills (`disable-model-invocation: true`) and never vendors the
  personas (CAP-298).
- **Elephant, goldfish** — the elephant is the house that remembers: Marshal and every
  session that loads the instruction files and the memory index (Dream entry
  2026-11-01: "The elephant stays marshal"). A goldfish remembers nothing. It reads
  its paths cold, reports, and forgets.
- **Challenger** — the fleet's fresh-context reviewer: `marshal factory challenge`,
  its dispatch and retro hooks, and its audit sweep (CAP-298..CAP-303). It reports and
  never gates (Constraint *The challenger never gates*).
- **Goldfish reviewer** — one reviewer persona spawned as a registered agent with no
  session history, no instruction files and no memory index. It receives exactly its
  target and its context paths (the goldfish context rule, CAP-299).
- **Reviewer persona** — one of the EGM agent definitions Marshal dispatches:
  `zoom-out`, `design`, `comprehension`, `implementation-readiness` and
  `codebase-details`, each spawned as `egm:egm-<persona>`. EGM's `structural` and
  `style` personas and `egm:egm-synthesizer` are never spawned.
- **EGM adapter** — a persona's agent file in the plugin cache
  (`.claude-plugin/agents/<file>.md`, for example `design_critic.md` for `design`).
  Every spawn asserts its frontmatter: `omitClaudeMd: true`,
  `tools: [Read, Grep, Glob]` and `model: inherit`. It is not an **Adapter**
  (§ *Portability vocabulary*).
- **Stage** — one of the challenger's five reviews. `mint` reads a Spec against its
  Dream. `decompose` reads an `epics.md` against the Spec whose capability range it
  claims. `readiness` reads a story spec before a dispatch. `drift` reads an epic's code
  against its Spec at retro time. `rules` reads `AGENTS.md`, `CHAIN-STANDARD.md` or a
  station skill. Each stage has a reviewer group and a standard (CAP-299's stage table).
- **Orchestrator session** — the one synchronous Claude Code session, from the packaged
  `claude` profile, that spawns a stage's reviewers through the Agent tool and writes
  `report.json` from their answers. It runs from a temporary directory outside the repo
  with its own `--settings` (CAP-298, CAP-299). It is not a dev session.
- **Challenge report** — `report.json` in a run folder under Tier 3
  `implementation-artifacts/egm/<run>/` (CAP-298). Its fields are `stage`, `target`,
  `project`, `spec_workspace`, `owner_override` (only when another Spec governs a
  `rules` target), `reviewers` and `findings`. It is advisory data, never instruction,
  and it is not the run journal.
- **Finding** — one entry of a report's `findings`: an `id` unique within the report
  (`F<n>` by convention), the `reviewer`, a `severity` (`high`, `medium` or `low`), a
  one-sentence `claim` and its `evidence`. After `resolve` it also carries a
  `resolution` (`accepted` or `rejected`) with the operator's note or reason. A finding
  never changes an exit code.
- **Unevaluable** — a challenge that did not fully run: the session failed or timed
  out, it left no valid report, or its report omits a dispatched reviewer, lists none or
  names another stage. It exits 1 and is never read as clean (Constraint
  *Never false-green; unevaluable is failure*).
- **Red** — a readiness result that carries a finding, or that comes from a review that
  was refused, failed or left an unevaluable report. Red raises `MRS-DISP-067` as a
  WARN and never blocks a dispatch (CAP-300).
- **Run record** — in CAP-300, the dispatch-launch intent's `readiness_challenge`
  payload (the report path, the counts and any error), which `marshal status` and
  `marshal watch` read. It is not a file of its own: the **run journal**
  (§ *Run vocabulary*) holds it.
- **`model_cost_catalog`** — the table of model ids by provider, with prices, in
  `marshal-policy.toml`. The challenger's `model` must be an `anthropic` entry of
  marshal's own catalog, on every station (CAP-299).
- **Usage code** — exit `2` (`EXIT_USAGE`, `core/verdict.py`). A refused challenge exits
  with it: a switch off, the plugin absent or at another version, Claude Code below
  2.1.271, a bad block or a refused model (spec-feature-flag-governance:CAP-7 Q3).
- **Kill switch** — a `pyforge.marshal.egm_*` feature flag, default off:
  `egm_challenge`, `egm_policy_block`, `egm_dispatch_readiness`, `egm_retro_drift`,
  `egm_audit` and `egm_resolve_bridge`. CAP-299's switch matrix says which ones each
  path needs.
- **House terms a goldfish meets** — pointers only. `chain-currency` is the planning
  detector (`scripts/chain_currency_sweep_check.py`) that reds a chain artifact that has
  fallen behind the one upstream of it. `CAP-n`, `FR-n`, Dream, Spec, memlog and the
  tiers are defined in `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md`
  § 0 and § 1.

## Artifact tiers

- **Tier-2** — tracked planning artifacts (`planning-artifacts/`), durable, in every
  clone.
- **Tier-3** — gitignored execution output (`implementation-artifacts/`), local-only and
  destroyed with the worktree. A story spec written only into Tier-3 does not survive;
  that is the failure CAP-4's promotion capability exists to make impossible.
