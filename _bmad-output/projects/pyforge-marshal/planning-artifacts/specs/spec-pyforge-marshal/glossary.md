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
- **Skill tree** — the directory an adapter reads skills from. Divergent by adapter:
  `.claude/skills` (claude, opencode) versus `.agents/skills` (codex, gemini, copilot,
  antigravity). `.agents/` does not exist in this repository — that gap is the whole of
  Marshal's actual portability work.
- **Conformance matrix** — the dated, per-adapter record of whether a canonical smoke
  story completed here. The only place Marshal makes a portability claim.

## Artifact tiers

- **Tier-2** — tracked planning artifacts (`planning-artifacts/`), durable, in every
  clone.
- **Tier-3** — gitignored execution output (`implementation-artifacts/`), local-only and
  destroyed with the worktree. A story spec written only into Tier-3 does not survive;
  that is the failure CAP-4's promotion capability exists to make impossible.
