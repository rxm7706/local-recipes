# Domain research — Marshal orchestration, 2026-08-08

> **Scope:** re-validation of the domain problem now that the Dream
> (`docs/dreams/pyforge-marshal.md`, status: realized — "autonomy a human can
> trust") has 50/50 stories shipped across Epics 1–6, and the remaining work
> (Epics 7–12, absorbed genesis-installer) is a different problem class.
> Companion to `domain-agent-portability-and-governance-research-2026-07-25.md`
> (whose governance findings this doc re-confirms against shipped mechanics —
> see § 5) and the undated `domain-research-scaffolder-landscape.md` (which
> becomes newly relevant to Epics 7–9, § 4). Ground truth: the ledger
> (`sprint-status-ledger.yaml`, 110 story keys), the shipped package
> (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/`), and this
> session's fleet-refresh survey.

## 1. Does "deterministic BMAD-loop supervisor" still describe Marshal?

**No — it describes roughly one shipped epic of six.** The phrase was
accurate at Dream-seed time (2026-07-23), when the capability *was*
`bmad-loop` plus aspiration. What actually shipped is a **governance layer
around an untrusted worker**, of which loop supervision is one stage:

| Shipped surface | Epic | What it governs |
|---|---|---|
| Loop homes: provision, isolate, verify, teardown-that-refuses-to-destroy-work (`marshal init`, `cli/spin.py`, Story 1.8) | 1 | *where* work runs |
| Gates: standalone verify runner, verdict lattice, frozen-surface scope check, gate-mode ladder (`core/gate.py`, `core/verdict.py`, `core/spec_surface.py`) | 2 | *whether* work counts |
| Supervisor: external sidecar, budgets, escalation (`supervisor/`) | 3 | *while* work runs |
| Landing: `marshal land`, spec promotion, journal, merge-subject conformance (`core/landing.py`, `core/promotion.py`, `core/journal.py`) | 4 | *how* work becomes durable |
| Fleet visibility: `marshal status` + `--reconcile-ledger` + `marshal check` (`cli/status.py`, `cli/check.py`, `core/context.py`) | 5 | *what is true right now* |
| Portability: adapter probe, conformance matrix, skill-tree projection (`core/conformance.py`, `core/skill_projection.py`) | 6 | *which agent* does the work |

Only Epic 3 is "supervising bmad-loop." Epics 2, 4, 5 govern stages bmad-loop
never touches (the engine stops at a merged commit on the station branch —
the `pr-lifecycle` Dream's founding observation), and Epic 6 governs the
choice of harness itself. The accurate 2026-08 description is: **Marshal is
the factory's execution-governance CLI — it provisions, gates, supervises,
lands, reports, and ports unattended agent work; `bmad-loop` is one wrapped
engine inside it** (wrap-never-absorb, re-confirmed by the upstream
bmad-automator→bmad-loop lineage post-mortem in the 07-31 technical doc).
Downstream artifacts that still lead with "loop orchestrator" (the archived
`pyforge-marshal-loop-orchestrator.md` duplicate already caught this;
dashboards and deck copy should be checked for the same lag).

## 2. "Autonomy a human can trust" — what the realized framing means mechanically now

The Dream's gradient ("attended first, then unattended wrapped in gates,
escalate instead of guess") is no longer prose; each clause has a shipped
mechanism and a real incident that exercised it:

- **The gradient is the gate-mode ladder** (Story 2.5): per-story autonomy
  labels, with doc-only classification (2.4) as the shipped proof that the
  ladder has more than two rungs — a prose-only story earns a lower gate.
- **"Escalates instead of guesses"** is the CRITICAL-escalation path ending
  in the interactive `bmad-loop-resolve` skill; `marshal status
  --escalations` (5.3) sorts them first with reason + artifact. The measured
  claim in outward material — 0 guessed escalations — remains derivable, not
  asserted.
- **"Every run visible"** is now two-sided: the feed reports *intent*
  (bmad-loop marks `done` at DEV completion, before review — auto-memory
  `feedback_feed_reports_intent_run_reports_fact.md`), while `marshal status
  --reconcile-ledger` (5.4) reports *fact* from git's durable-merge evidence,
  tagging discrepancies `confirmed`/`unconfirmed` because squash merges
  genuinely blind git-subject archaeology. The domain lesson: **visibility
  needed a truth hierarchy, not a dashboard** — the run's `state.json` >
  git evidence > the feed > the rendered page, and each shipped surface
  declares which layer it reads.
- **"The thing that governs the agent cannot be a thing the agent authors"**
  held structurally: gates run as a standalone project-scoped command (2.1),
  the supervisor is a separate process the session cannot silence, and the
  verdict lattice's one-exit-authority rule is meta-tested since 1.1.
- **Trust was earned by the tool catching itself.** Epic 5's closeout run of
  `marshal deploy promote` + `--reconcile-ledger` caught Story 5.1's own
  spec falling through promotion (its PR was squash-merged against
  convention). That is the domain thesis in one incident: a trustworthy
  autonomy system is one whose *paper-trail checks fire on the system's own
  output*.

## 3. Domain gaps that remain in the *orchestration* problem (not Epics 7–9)

These are marshal-owned Dreams still `dreamt`, each naming a real recurring
cost — the unsolved residue of the original domain:

1. **Promotion is a remembered step** (`sprint-status-auto-promote.md`) —
   three same-session incidents of the dashboard silently stale; the fix is
   event-triggered promotion (post-merge hook or supervisor duty), not a
   better runbook. This is the highest-frequency remaining pain.
2. **Loop-home refresh is a hand-run ritual** (`loop-home-fleet-refresh.md`)
   — pull-side automation (fetch main, ff-only per home, report
   live/diverged/clean per the three-case taxonomy) does not exist; the
   push-side watcher exists but was found not running. Natural `marshal`
   verb; overlaps FR-61's stage-boundary push.
3. **The harness's blind spots are documented — and the worst one is now
   closed by Marshal, unclosed in bare bmad-loop**
   (`feedback_bmad_loop_blind_spots.md`): `bmad-loop status` cannot see a
   session stalled at an interactive prompt (2.5 hours at a billing prompt
   while reporting `review-running`). Epic 3's shipped idle ladder samples
   exactly what the manual runbook sampled — pane content + log mtime
   (`core/supervise.py::evaluate_idle`, nudge → stop-and-retry → defer at
   the 25-minute threshold) — so a *marshal-spun* run now catches this
   class. The residual gap: runs launched outside `factory spin` (bare
   `bmad-loop run`) still have no witness, and the memory entry should gain
   a "superseded when supervised" note.
4. **Forward-dependency blindness** (`bmad-loop-forward-dependency-blindness.md`,
   realized): the detector shipped and Story 8-5 sits correctly `blocked` on
   S-10.2 in the ledger — but the *engine* still has no `depends_on`; the
   protection is the tracked-status workaround, upstream contribution still
   open on the Epic 6 register.
5. **Fleet-chain completeness** (`spec-fleet-chain-completeness`, 5 CAPs,
   undecomposed) — regenerating a full planning chain from a consolidated
   Dream is still what a human did by hand across the 2026-08-02
   consolidation session.

## 4. Epics 7–9: the domain problem actually changes shape

The next work (E7 Foundation & the Write Guard · E8 The Managed-Region
Engine · E9 Detect & Plan; 17 stories, all backlog, 8-5 blocked) is **not
orchestration** — it is *idempotent brownfield repo templating*: an
extraction manifest describing the operating model's files, a marker/region
grammar so managed spans can live inside files the adopter also edits
(nesting rejection, fence awareness, anchor insertion, deletion-as-opt-out),
and a findings/inventory scanner (severity taxonomy, content hashing,
legacy-convention detection, plan builder). The users differ too: Epics 1–6
serve the operator running this factory; 7–12 serve a *stranger's repo*
adopting the model (`genesis check`'s question — "does an externally
installed repo still conform" — vs `marshal check`'s "is *this* repo
healthy"). The domain literature for it is the scaffolder shelf
(`domain-research-scaffolder-landscape.md` — Copier/cruft/Backstage
templates), where the unclaimed capability is managed regions in files the
tool does not own plus a never-write guard. Two unresolved design
contradictions are already on record and are domain-level, not cosmetic: the
CLI framework split (shipped argparse vs designed typer+rich) and the
`check`/`init` verb collisions (Open Question 17,
`genesis-installer-name-retirement.md`). **Recommendation carried to the
technical doc: treat 7–12 as a second product sharing Marshal's spine
(findings model, write discipline, exit taxonomy — E7 deliberately rebuilds
all three), and run the planning chain once against the unified Spec before
S-7.1 opens, exactly as the name-retirement Dream argues.**

## 5. Refreshed 2026-08-08 — standing findings from the 07-25 domain research

- **L4 Approver as the target autonomy level** — confirmed and now
  *implemented* as the gate-mode ladder; the Cihon et al. framing ("autonomy
  is what the orchestrator code permits") is literally true here: the policy
  files (`policy-defaults.toml` + per-station `marshal-policy.toml`, 4-layer
  composition) are the autonomy level.
- **Gates must live outside the conversation** — re-confirmed by the
  interactive-prompt stall incident (§ 3.3): even the *harness's* own status
  is not evidence; only externally observed quantities (log growth, pane
  content, CPU) are.
- **ACP as the socket** — unchanged since the round-2 verification: Q-6
  triggers unfired, seam stays the hedge; Epic 6's conformance matrix is the
  shipped insurance policy.
- **93%-approval rubber-stamping risk** — Marshal's answer shipped as
  *fewer, richer* escalations (sorted, reasoned, artifact-linked) rather
  than more prompts; no new evidence against.
