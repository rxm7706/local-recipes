---
title: A backlog authored before the code existed is a plan for a different codebase
type: dream
owner: marshal
status: realized
---

# A backlog authored before the code existed is a plan for a different codebase

> The semantic sibling of [[surface-drift-reconciliation]]. That Dream made the
> *file-level* reconciliation claim honest — a memlog speaks only for the paths
> it names. This one makes the *meaning-level* claim honest: a story's premise,
> a done-claim's acceptance criteria, a test suite's coverage of an epic. The
> detectors police hashes and counts; nothing polices whether the plan is still
> true. Kin: [[regenerable-factory]] (every surface regenerable from its chain),
> [[fidelity-enforcement]] (every tier boundary gated), [[bmad-output-hygiene]]
> (what is real vs. debris, mapped once — this Dream is that audit's
> forward-looking form).

## The Dream

The fleet paused at **267/335 stories, 53/64 epics**, by choice. Behind those
267 stories stands the full dream-to-code chain — Dream, Deck, Spec, Research,
Brief, PRD, UX, Architecture, Context, Epics, Sprint, TEA, Gates, Code, Tested,
Retro, Status — and almost all of it was authored **before most of that code
existed**. The 68 stories that remain were scoped against a codebase that has
since absorbed 267 landings, 13 retro-driven skill revisions, one fleet-wide
naming convention, and a per-station architecture consolidation. Some of those
68 are already implemented under another story's flag. Some contradict
invariants that hardened after they were written. Some are still exactly right.
**Nobody has measured which.**

The mechanical layer is policed: six detectors prove files match contracts,
ledgers match feeds, surfaces match baselines. The semantic layer is not. No
instrument asks *does this story's premise still hold?* or *do the acceptance
criteria of that `done` claim actually appear in code?* or *which ACs have no
covering test?* Those are judgment questions, and they have been answered so
far by the only witness available — the artifacts' own self-assessment, which
is precisely the witness that cannot be trusted. The ledger reports intent; only
the code reports fact.

The dream: **stop building, audit the chain independently against the code,
correct whichever side is wrong, and only then decompose further.** The scope
is all of PyForge — every Dream in `docs/dreams/`, every planning artifact,
every chain stage, all code — and the correction runs both ways: a stale
artifact is rebuilt against the code, and code that diverged from a
still-valid contract is corrected against the artifact. The artifacts that
drive implementation must be at least as true as the implementation they
drove. A factory that regenerates code from its chain is only as good as the
chain — and right now the chain's truth is presumed, not measured. Decomposing
on top of a stale chain compounds the drift at the exact moment it is cheapest
to correct.

## What is real (measured 2026-08-10, on `main` at `dfeb565231`)

- **267/335 stories · 53/64 epics · 0/8 stations running** (`fleet-picture`;
  liveness verified against `ps`, not `engine.pid`). All eight loop homes
  fast-forwarded to `main`; zero unlanded loop merges; zero open PRs.
- **The remaining 68:** marshal 35 (+1 blocked — story 8-5, not 10-1/FR-157 as
  a prior session's note suggested), mason 28, steward 4. Steward's stop is a
  deliberate epic-boundary pause at Epic 8, 1/5. These 68 are the artifacts
  that will drive implementation the moment any station re-spins — the
  highest-leverage audit target in the repo.
- **Five stations read complete** (atlas 46, doctor 28, herald 47, scribe 9,
  warden 31) — a claim this Dream treats as *ledger intent*, to be sampled
  against code, not inherited.
- **Known mechanical debt, already partitioned into three jobs:** 51
  `[drift-presumed]` warns — atlas 24 (name-then-stamp), marshal 26 (a
  *decision* about generated artifacts, still open), mason 1. Plus ~30 dangling
  commits from six orphaned runs, presumed valueless but unverified.
- **Four decomposition chains are queued** (order decided: atlas → herald →
  doctor → steward) — queued *before* the pause-and-reconcile decision existed.
- **The precedents that shape the method are all in-house:**
  - warden lost 13/31 story specs to Tier-3 teardown and recovered 31/31 from
    session transcripts; atlas could not, and carries 30/32 contract-specs —
    the two ends of the artifact-durability spectrum this audit must respect.
  - "feed reports intent, run reports fact" — the loop marks `done` at DEV
    completion, before review; the ledger is structurally optimistic.
  - Blind parallel adversarial review (two hunters, no shared context) is
    validated at N=6 in this repo and is strictly stronger than sequential
    persona role-play over the same content.
- **No semantic detector exists, and none is possible in the mechanical sense.**
  `bmad-drift-check` proves counts and pins; `spec_surface_check` proves files
  against contract hashes. Premise validity and AC truth are judgment calls —
  which is exactly why they have never been checked, and why an independent
  audit (not another script) is the instrument.

## What it looks like when real

- **Every remaining story carries a cited verdict:** `STILL-VALID` /
  `ALREADY-DONE` / `CONTRADICTED` / `NEEDS-RESPEC` / `DROP`. No verdict without
  evidence — a `file:line` citation or a command's output. A `CONTRADICTED`
  claim with no citation is rejected in review.
- **The audit's output is a traceability matrix, not prose**, landed in an
  existing artifact class (the gate report, via
  `bmad-check-implementation-readiness`) — one row per claim:
  *Claim (FR / story / AC) · Ledger status · Code reality (citation) · Verdict ·
  Action → owning skill*. A matrix cannot hide a half-audited epic the way a
  summary can; this is "emit the full contract or nothing" applied to auditing.
- **The TEA column is refreshed by measurement:** per epic, an AC → covering-test
  map. An AC with no test is a distinct *coverage-debt* row, not a drift
  verdict — visible, non-gating, dispositioned by the operator.
- **Done-claims are sampled, not trusted:** N stories per epic on every station
  — including the five that read complete — their ACs checked in code.
- **Fixes land only through the owning skills:** `bmad-correct-course` for
  epic/story surgery, `bmad-sprint-planning` → `sprint-ledger-sync` for the
  ledger, `bmad-document-project` / `bmad-generate-project-context` for
  architecture and context re-grounding, `dashboard-gen` for the board. Every
  spec touched gets a memlog entry naming its paths, then a scoped stamp —
  never a stamp without the why.
- **Every landing is preceded by blind, lens-diverse parallel review** — one
  hunter structural/architectural, one coverage/edge-case, neither shown the
  artifacts' self-assessment before the diff.
- **The five complete stations are closed out as a verified record:** Spec
  status advanced to `shipped` where earned, retro promises confirmed landed,
  story-spec sets complete under `planning-artifacts/specs/`, board rows
  accurate, baselines re-stamped.
- **Decomposition extends only a reconciled chain.** The four queued chains run
  after their station's audit lands, with convergence checked before any new FR
  is minted — most new capability in a mature chain is already covered.
- **At the end, re-spin is an operator decision made on artifacts that are
  true** — and the projected 68 is a number that can finally be believed.

## The shape of the answer

Five phases, in order. The build stays down throughout; a station's audit
landing gates *that station's* further work, not the fleet's.

0. **Freeze + mechanical debt.** Full detector sweep for the baseline
   inventory. Close the 51 warns as the three jobs they are — atlas 24
   name-then-stamp, mason 1, marshal 26 pending the operator's
   generated-artifacts decision. Disposition the dangling commits. The audit
   is worthless while drowned in known noise.
1. **Backlog-truth audit of the three unfinished stations**, smallest first to
   calibrate the method: **steward (4) → mason (28) → marshal (35 + blocked
   8-5)**. Fresh-eyes read of epics, remaining stories, architecture, and
   context against current code; verdict matrix; done-claim sampling; fixes
   through owning skills; blind review; one landing PR per station.
2. **Completed-station audit at equal rigor** (atlas, doctor, herald, scribe,
   warden). Not a lighter close-out — a critical part and point of the audit:
   three of the four queued decomposition chains extend completed stations, so
   this audit gates decomposition exactly as Phase 1 gates re-spin. Same
   verdict matrix, same sampling discipline, chain columns reconciled, Spec
   statuses corrected to earned values. Atlas's 30 contract-specs are accepted
   as-is, not reconstructed.
3. **Decomposition on the clean base** — the four queued chains, content
   decisions unchanged, each gated on its station's audit.
4. **Re-baseline + resume decision.** `--write-baseline`, `dashboard-gen`,
   board render, fleet-picture; then per-station re-spin is the operator's
   call (FF the home + re-render policy first, per standing procedure).

Why audit-before-decomposition, when the queue said decompose first: the queue
ordering predates the pause decision. Extending atlas's chain now would build
on the very drift this Dream exists to measure. Nothing decided is undecided —
the verification step is inserted, not the decisions reopened.

## Method constraints

- **Detectors own mechanical facts; the audit spends judgment only.** Counts,
  pins, surface hashes, ledger totals come from the instruments that already
  emit them deterministically. Model attention goes exclusively to what no
  script can answer: premises, AC truth, coverage meaning.
- **Anchoring is the audit's failure mode.** An auditor steeped in the chain's
  narrative confirms it. Reading order may be artifacts-then-code, but verdicts
  ground in code, done-claims are sampled cold, and reviewers are blind to
  self-assessments.
- **Prose is not an audit output.** Matrix rows with citations, or nothing.
- Three moves were considered and **rejected** for this repo: bundling all
  artifacts into a single audit document (a satellite doc by construction);
  letting the auditor rewrite planning artifacts freehand (the laundering
  S-13.2 exists to end — rewrites go through owning skills + memlog + scoped
  stamp); and having the model re-derive mechanical drift (slower and less
  reliable than the detectors that already do).

## Non-goals

- **Not a silent re-scoping.** Correction of specs, code, decisions, and
  artifacts is pre-authorized (operator, 2026-08-10) — but every change traces
  to a cited verdict row and lands in a reviewable PR; nothing is dropped or
  rewritten without the record.
- **Not a Tier-C refresh.** Dreams are permanent record; Decks and UX refresh
  through Herald when wanted. Touched only if the audit proves one
  *contradicted*, never for polish.
- **Not a new detector.** The semantic layer cannot be mechanically gated —
  pretending otherwise would mint a false-green instrument, the exact disease
  [[surface-drift-reconciliation]] just cured elsewhere. If a recurring cadence
  is wanted later, that is a separate decision this Dream does not make.
- **Not a reconstruction of atlas's lost originals.** 30/32 contract-specs is
  the accepted end state of that recovery.
- **Not a re-spin.** No station starts building under this Dream.
- **Not a reopening of the four decomposition chains' content decisions.**
  Their order and scope stand; only their start is gated.

## Open questions

- **Marshal's 26 generated-artifact warns** — *answered 2026-08-10:
  regenerate, verify outputs match, then judge + scoped stamp.*
- **Serial or parallel?** — *answered 2026-08-10: serial, in the main session;
  the judgment stays in one context.*
- **Audit order** — *answered 2026-08-10: steward → mason → marshal confirmed.*
- **Can a "complete" station lose the claim?** If Phase-2 sampling fails an AC
  on a shipped station: reopen the story, or record a coverage-debt row and
  leave the ledger? The answer sets precedent for what `done` means here.
- **Where do the gate reports home?** Presumed: each station's own
  `planning-artifacts/` under its existing gate-report class. INV-1 separately
  requires this Dream's own Spec under
  `pyforge-marshal/planning-artifacts/specs/spec-artifact-chain-reconciliation/`.
- **One-shot campaign or standing practice?** If the audit proves cheap enough
  to repeat at every N-story boundary, it may want to become `type: practice` —
  deferred until the first pass prices it.

## Realization log

- **2026-08-10** — Seeded at operator request, at the 267/335 pause, immediately
  after a landing pass confirmed zero in-flight work fleet-wide — the cheapest
  moment this audit will ever have. The plan was drafted in-session; an
  external model's (Gemini) reconciliation advice was weighed against it — three
  constraints adopted (strict traceability matrices, citation enforcement, an
  explicit AC→test coverage lens), three rejected as unsafe for this repo
  (bundled context document, freehand artifact rewrites, model-side mechanical
  drift detection), and its sequential persona passes replaced by the
  repo-validated blind parallel form. The queued decomposition-first ordering
  was deliberately inverted: verify the chain, then extend it.
- **2026-08-10 (later)** — Specified. The three operator decisions landed
  (marshal's 26: regenerate + verify + stamp; serial execution; steward →
  mason → marshal), and mid-spec the operator elevated the completed stations
  from "lighter close-out" to **first-class audit scope** — a critical part
  and point of the audit, since three of the four queued decomposition chains
  extend completed stations. Two further directions in the same session
  widened the contract: the audit spans **all of PyForge** — all 61 Dreams,
  all artifacts, all stages, all code (the non-station inventory is CAP-8) —
  with completed stations queued after steward → mason → marshal; and
  **rebuilding/correcting specs, code, decisions, and artifacts is
  pre-authorized**, two-sided (stale artifact → rebuild from code; divergent
  code → correct against contract), nothing silent. Spec:
  `pyforge-marshal/planning-artifacts/specs/spec-artifact-chain-reconciliation/`
  at `ready`, CAP-1..CAP-8, with the completed-station audit as CAP-3.
- **2026-08-10 (close)** — Realized. Phases 0–4 executed in one autonomous session
  (PRs #399–#406): 51 warns to zero by measurement, 68 backlog verdicts + 21+21+4
  done-claim samples all cited, 19 story-spec recoveries, 195 citation re-issues,
  61/61 Dreams dispositioned, one decomposition landed and two held conservatively
  when the blind verifier and the consent classifier said hold. Every phase's first
  draft was refuted in part by its own blind review — the method's point, proven
  eight times. Spec `shipped`; the resume decisions are packaged in
  `resume-package-2026-08-10.md`.
