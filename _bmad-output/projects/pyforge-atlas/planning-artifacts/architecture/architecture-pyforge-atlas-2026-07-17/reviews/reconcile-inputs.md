# Input Reconciliation — ARCHITECTURE-SPINE.md vs PRD(+addendum) and Technical Research

- **Pass:** Finalize / input-reconciliation
- **Date:** 2026-07-17
- **Spine:** `_bmad-output/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md`
- **Inputs checked:**
  1. `_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md` + `addendum.md`
  2. `_bmad-output/projects/local-recipes/planning-artifacts/research/technical-agentic-sdlc-kedro-migration-execution-research-2026-07-16.md`

## Verdict

**Substantially faithful — no structural misses, but a cluster of quiet execution-discipline
requirements did not land.** The spine's ADs carry the paradigm, boundaries, contracts,
secrets posture, three-domain data split, worktree seam, keystone budgets, and honest-performance
framing correctly. What dropped is almost entirely the *operating-discipline* layer both inputs
treat as binding: the reviewer leash, two of the four counter-metrics, the verify-command growth
rules, two Wave-0 preconditions, the third observation plane, and the PR-per-wave delivery seam.
A downstream builder configuring the loop from the spine alone could violate each of these.

12 findings: 1 HIGH · 5 MEDIUM · 6 LOW.

---

## Dropped items

### HIGH

**R-1. Reviewer-constraint discipline ("reviewers constrained to correctness") is nowhere in the spine.**
The research states it twice as a verified failure mode with a named mitigation: *"adversarial
reviewers in long unattended runs always find something — constrain them to correctness-affecting
gaps or the loop over-engineers"* (Practice patterns; Design Principle 5; implementation risk table:
"Review checklist constrained to correctness + contract fixtures"). With ~21 loop-driven stories and
`max_review_cycles = 3`, this is the guard against systemic over-engineering across the whole
migration. No AD, convention, or deployment bullet carries it. A builder writing the loop's REVIEW
checklist or story-spec review sections from the spine alone would not know the leash exists.
*Suggested landing:* one clause in AD-11 (loop execution) or the Consistency Conventions
(State & errors / Tests row): "REVIEW sessions are constrained to correctness-affecting findings
and contract-fixture compliance; style/scope findings go to the DW ledger, never rework."

### MEDIUM

**R-2. Counter-metrics SM-C2 and SM-C4 did not land (SM-C1 and SM-C3 did).**
- SM-C1 (cold-start honesty) → landed in AD-4. SM-C3 (signal count) → landed in AD-19
  ("no new external sources beyond the committed set").
- **SM-C2 (autonomy share):** "do not raise the loop-driven story count by weakening gates;
  attended boundary events are features, not friction." AD-11 mandates that gates *exist*, but
  nothing forbids diluting a gate's content or demoting an attended event to make a story
  loop-drivable. This is exactly the quiet-discipline class this pass exists to catch.
- **SM-C4 (dashboard breadth):** "feeds > pages; do not grow the public-facing page surface beyond
  D2's factory-status page." The spine references the § 2.1 agent-legibility bar (AD-8) and defers
  D2 page inventory to the CIS specs, but carries no ceiling on public page growth — a Wave-D/G
  builder could legitimately expand the public surface.
*Suggested landing:* SM-C2 clause in AD-11's rule; SM-C4 clause in AD-8 or AD-21 (the public
surfaces).

**R-3. Verify-command growth rules dropped: monotonic growth + in-loop gate scoping.**
Research (Testing/QA plan, binding for the execution architecture): "`[verify] commands` grows per
wave and **never shrinks**"; "in-loop gates stay scoped (changed-unit tests + the story's fixtures);
`test-all` runs at wave boundaries only" (also Design Principle: keep gates fast — the Ralph
scoping rule; throughput is dominated by verify time). AD-11 names the six tasks and their
fixture/non-credentialed/`--frozen` properties but not these two rules. A builder could (a) retire
a verify command after its wave, or (b) wire `test-all` into every in-loop verify and destroy
wave throughput. Neither violates the spine as written.
*Suggested landing:* two clauses appended to AD-11's rule.

**R-4. Wave-0 precondition set in AD-18 is incomplete: hooks approval and the live groundtruth re-check are missing.**
PRD § 6.2 lists the loop preconditions as: **hooks approval**; `bmad-switch
pyforge-atlas`; worktree symlink bootstrap (A3); heaviest-story budget review.
AD-18 carries the last three and omits the first — and selective enumeration reads as complete.
The research grounds it: the one-time human hooks-approval "is a hard precondition for any run."
Separately, PRD § 9.6/§ 12 record that intake groundtruth was git-surface-only ("live
`bmad-groundtruth`/`bmad-drift-check` could not run in this container — the live CLI re-check
remains a Wave-0 precondition"); the spine's Decisions § only carries the live re-check for
conditional Phase T, not the general Wave-0 groundtruth re-check.
*Suggested landing:* both added to AD-18's rule (or a Wave-0 preconditions line in the deployment
envelope).

**R-5. The three-observation-planes posture dropped; spine names only the pipeline plane.**
Research (Observation layer + Observability integration): three unjoined planes — bmad-loop TUI
(the **only** loop-session observer), the BMAD dashboards (artifact-level, work for free via the
`_bmad-output` artifact tree), and kedro-viz/Dagster UI (pipeline-level) — with the artifact tree
as the pragmatic join and an explicit boundary: **defer any unified view** (a MyBMAD-reads-run-journal
integration is an upstream feature request, "not this effort's scope"). The spine's deployment
envelope names only `pixi run viz` + Dagster UI. Two violations are open to a spine-only builder:
wiring dashboards to loop sessions (impossible-by-design, wasted story) or building a unified
observation view (scope creep the research explicitly fenced off).
*Suggested landing:* one deployment-envelope bullet (loop execution plane): "three observation
planes — TUI (loop sessions), BMAD dashboards (artifacts, via the artifact tree), kedro-viz/Dagster
(pipeline); no unified view is in scope."

**R-6. The delivery seam past the loop's local merge dropped: PR-per-wave + operator-invoked sweeps.**
Research (SCM & PR-lifecycle integration; per-wave operating loop) and addendum § 4: bmad-loop has
**no PR lifecycle** — it stops at local squash-merge — so the repo convention wraps it as
*loop → human review of squashed commits → push → **PR per wave***, with `bmad-loop-sweep` triage
operator-invoked at wave ends (`auto = never`). PRD § 6.2 binds the § 14 per-wave operating loop
(Q-drain → TEA → loop → sweep → boundary event → PR per wave). The spine's AD-11/AD-18 cover gates
and worktrees but never say how work leaves the loop's local branch; spec § 14 is never referenced
by the spine (only § 2.5 is). A spine-only builder has no delivery convention.
*Suggested landing:* one sentence in AD-18 or the loop-execution deployment bullet: "the loop ends
at local squash-merge; delivery is PR-per-wave after the attended boundary event; sweeps are
operator-invoked at wave ends."

### LOW

**R-7. B4 abort ramp / Ibis-over-SQLite severability ramp absent.**
PRD risk table ("B4 parity economically unreachable" → keep legacy, salvage D/G read-surface value
via the Ibis-over-SQLite fallback — fallback, not plan) and addendum § 2 name it as architecture
input. AD-1 carries only the orchestration exit ramps; AD-19 gates retirement but names no ramp for
parity-unreachable. Low because it is a contingency, not a build-time constraint — but it is the
one exit ramp the addendum flags for the read surface and it appears nowhere.

**R-8. TEA `atdd` as the Wave-B fixture generator appears only as an assumption note, not a binding rule.**
PRD § 6.2 (binding): "Wave B runs with TEA `atdd`-generated red-phase fixtures as the verify
assets." The spine mentions TEA only in Decisions #3 (altitude note). A builder could hand-write
Wave-B fixtures without the red-phase discipline. Low because the epics/stories pass will carry
the § 14 loop; flag so it isn't dropped twice.

**R-9. Long-runs-look-stalled mitigation dropped.**
Research risk table: "long test runs read as stalled sessions → `dev_stall_grace_s` tuned per wave;
background-run pattern in story specs" (raise for F1's benchmark story). Pure execution-plane
config, but it is a named failure mode with a named per-wave action that no spine element or
§-reference reaches.

**R-10. § 13 integration-surface matrix review cadence / Anaconda ToS tripwire not surfaced.**
PRD § 2.1 (sustainability governed by spec § 13 matrix reviews) and the risk row "Anaconda CDN/API
ToS shift (biggest structural dependency) → § 13 matrix review; S3-parquet consumer path + mirror
chain." The spine's override/mirror machinery (AD-2/AD-13) covers the mitigation mechanics, but the
standing review cadence and the S3-parquet consumer path are unreferenced. Low: operations
governance, spec-owned — but the spine's deployment envelope is where an operator would look.

**R-11. Rule-2 closeout retro not restated.**
PRD § 6.2: "per Rule 2, the effort closes with a CFE-skill retro." Covered by always-on CLAUDE.md
(so no builder can claim ignorance), hence LOW — but the spine restates Rule 1 authority (AD-10)
while staying silent on Rule 2, an asymmetry worth one clause.

**R-12. Supervised-first cadence note.**
Research Deployment/Operations: "supervised runs first; overnight unattended only after two clean
supervised stories in a row." Not in spine or PRD § 6.2; likely lives in spec § 14 (unverified from
this pass's inputs). Recorded for the epics pass to confirm rather than as a definite drop.

---

## Explicitly checked and confirmed landed (no action)

- **Secrets posture** (research → spine): fixture-only, non-credentialed, `--frozen` gates (AD-11);
  per-host credential scoping incl. the JFrog leak scenario and bypass-permissions rationale (AD-2);
  Phase P admin-opt-in, never a default schedule (AD-6); credentialed runs attended-only (AD-11);
  PRD § 9.12 derived hardening reproduced by the AD-6 + AD-11 combination.
- **Three-domain data architecture** (research): deployment envelope final bullet + the
  sampled-fixtures convention ("generated attended, once, from operator runtime data — gates never
  read `.claude/data/`") in Consistency Conventions.
- **Worktree × symlink seam** and A3-as-smoke, `bmad-switch` supersession (PRD § 9.11): AD-18.
- **Keystone budget pre-raises** (B1/B2/F1): AD-18.
- **Counter-metrics SM-C1/SM-C3**: AD-4 (honest AC-7 scoping) / AD-19 (no new sources).
- **Glossary contracts**: node/dataset/domain-pipeline/wave/verify-gate/bootstrap-profile/
  BSL/derived-layer/ComplianceReport (full enum {0,1,2,130}) all present and consistent
  (AD-3/5/6/8/11/12/15; Consistency Conventions).
- **PRD § 8/§ 9 unattended-intake decisions**: Q-defaults + per-wave re-checks mirrored in
  Decisions #1 and the Deferred list; volatile-count discipline (Decision #5); PRFAQ framing
  (AD-4); market-research "no new FRs" (AD-19 boundary) — modulo the SM-C4 ceiling (R-2).
- **Risks table rows** other than R-7/R-10: Dagster deterioration (AD-1 + Deferred Q2), gates
  never built (AD-11), Basilisk disappearance (AD-13), GX ceiling (AD-9 + Stack cap), worktree
  seam (AD-18), credential leakage (AD-2/6/11).
- **Properly deferred, not flagged** (spine altitude respected): FR-9 port-first CLI ordering and
  D2 page detail (→ CIS specs, Deferred), the ~44-feedstock cf-graph delta (B1/B4 story ACs),
  per-story drivability modes (→ epics + spec § 2.5), rejected-alternatives table (PRD § 5 /
  addendum § 1), upstream bmad-loop feature requests (out of scope § 6.3), Erratum-2 story
  arithmetic (spec v5.4+ carries corrected numbers; spine cites counts via § 3.3/groundtruth only).
