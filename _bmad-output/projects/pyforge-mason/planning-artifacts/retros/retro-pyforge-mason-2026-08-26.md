---
title: "Retrospective: pyforge-mason close-out"
type: retrospective
project: pyforge-mason
created: "2026-08-26"
updated: "2026-08-26"
scope: "Epics 1-11 completion arc, 2026-08-02 through 2026-08-26 (station complete per fleet ledger 2026-08-21)"
evidence: "git log --oneline --since=2026-08-02 -- src/shared/packages/pyforge-mason (54 commits, 2026-08-09..2026-08-26); sprint-status-ledger.yaml (50/50 stories done); as-built tree src/shared/packages/pyforge-mason/"
---

# Retrospective — pyforge-mason close-out (2026-08-26)

Companion to the same-day § Currency reconciliation truth-ups in the station Spec, PRD,
architecture spine, brief, and epics validation note. This is the close-out retro the
chain-currency sweep requires before the Dream flips to `realized`; the **Rule-2 CFE-skill
retrospective** this station's own FR-47 mandated was its own story (S-5.5) and landed
separately as part of Epic 5 — this document does not substitute for it.

## The completion arc (evidence: the package git log)

- **2026-08-09** — Epic 1 closed: bmad-loop runs landed S-1.5–S-1.10 (root-resolution chain,
  interpreter probe, degradation, `doctor`, fake-CFE-root harness, config/logging/streaming) on
  top of the 2026-08-02 S-1.1–S-1.4 slice.
- **2026-08-10/11** — the seam first: S-2.1 (the CFE port), S-2.2 (the seam guard with
  planted-violation fixtures), S-2.3 (credential isolation) before any user-facing recipe verb —
  the build-the-guard-before-the-surface ordering the 2026-08-08 research (§ 6) argued for.
  Also `56f3e1eebc`: the phase-1 backlog-truth audit — 28 verdicts, first draft overturned by
  review.
- **2026-08-12/13** — the recipe surface (S-2.4–S-2.10, seven verbs) and most of Epic 3
  (engine protocol, `package build`, ship vocabulary, pypi/channel/conda-forge targets, the
  `ship` verb + TestPyPI rehearsal).
- **2026-08-14/15** — Epic 4 (lock engine adapter, manifest discovery, `environment lock` and
  `check`, the latter through three review passes) and Epic 5's proof suite (CFE-independence,
  delegation fidelity).
- **2026-08-21** — completion day per the fleet ledger; final in-package motion that day was
  the pixi 0.77 pin-range sync ("the 17th pin site").
- **2026-08-22/26** — post-completion stories: S-9.2 air-gap contract socket (08-22), S-10.1
  build-engine hook (08-24), the steward S-25.4 boot re-index reconcile (08-25), S-11.1 persona
  (08-25), S-11.2 portal last-diagnose slice (08-26). Epics 6–9 landed mostly *outside* the
  package tree (CI workflow_call, Containerfile convention, skill-spec-derived failure catalog,
  rebuild pilot guards), which is why the package log under-counts them.

## What held

- **The seam.** Zero recipe knowledge in Mason, enforced not asserted: the deny-list meta-test
  with per-category planted violations, the sole-caller test, the one-entry CFE-independence
  allow-list, and delegation fidelity are all green in `tests/meta/` / `tests/integration/`.
  The atlas counter-example (a rebuilt capability nothing routes to) did not recur.
- **The architecture spine as written.** All ADs verified in code at truth-up; the one
  amendment (AD-15, 2026-08-10 correct-course: the CFE surface is read-only for the wrap effort
  while the sanctioned rebuild proceeds under its own Spec) was made through the front door and
  Epic 6 executed its pilot + re-scope gate under it.
- **bmad-loop's safety nets.** Two real recoveries — S-3.6/S-3.9 from the run's auto-preserve
  net (`d4267c1fc7`) and S-3.7 from a `failed/` preserved patch (`03d8fc8c86`) — landed
  losslessly by hand. The preserve-then-restore standing policy earned its keep here.
- **Dry-run-by-default.** Every mutating verb defaults to a plan; the rehearsal target gates
  the irreversible publish (AD-26); the asymmetric receipt (`pending` never collapsed into
  success) shipped exactly as briefed.

## Deviations, named

1. **S-2.5 hand-landed** (`6acc79244d`) after its dev pass deferred on a spec-surface gate —
   not a code defect; the out-of-order landing was reconciled in `cli.py`/`recipe.py`
   docstrings.
2. **Out-of-order Epic 3** — S-3.9 landed before S-3.7/S-3.8; S-2.6 was merged by hand with
   S-2.7–2.10 (`5e4cd03f6b`, stale metavar test fixed in the merge). Cost: several
   merge-reconcile commits; no contract drift found at truth-up.
3. **Research recommendations partially adopted** (2026-08-08 market refresh): channel upload
   via `pixi upload prefix` — adopted; neutral `pypi_upload` adapter name / uv uploader — not
   adopted (shipped as `engines/twine.py`); pixi-first lock engine — not adopted (conda-lock
   only). Recorded decisions; all swappable behind AD-12 if revisited.
4. **SM-1 at the rehearsal tier.** "Mason ships Mason" is proven as S-3.8's real self-hosting
   proof of the ship dry-run plan plus the TestPyPI rehearsal gate; the irreversible public
   PyPI publish of `pyforge-mason` has not been executed. The honest-caveat framing in the
   Spec/PRD now carries a date instead of a hypothesis.
5. **A real inter-story bug** (`83fc7191fc`): `recipe new`'s local `package` variable shadowed
   the `package` module import in `main()`, breaking `package build` — caught and fixed between
   loop landings; the kind of cross-verb interaction a single-story review scope misses.
6. **Duplicate story-spec files** (`spec-2-5-…` ×2, `spec-5-4-…` ×2) survive in
   `planning-artifacts/specs/` from parallel-worktree reconciliation — cosmetic debt, left in
   place by this sweep (no ledger key ambiguity: the ledger holds exactly 50 story keys).
7. **The persona SKILL's "No Wave B" guard aged out the day 11.2 landed** —
   `.claude/skills/bmad-agent-mason/SKILL.md` still forbids *implementing* Story 11.2, which now
   exists. Read today it is a persona-scope rule (the persona must not re-implement the portal),
   not a claim the portal is absent; a future skill touch-up could reword it. Out of this
   sweep's write scope.

## Strategy convergence — mason's place in the Canopy estate

Mason converged onto the unifying strategy (steward
`spec-pyforge-unifying-strategy`) without surrendering its founding decision. In the estate's
hub-and-spoke shape, mason is station 03 with a **portal + MCP face served by the Canopy host**
(`/stations/mason/`, `POST /stations/mason/mcp`) and a persona (`bmad-agent-mason`) that acts
only through `pyforge mason …` grammar and that MCP face — `pyforge.mason` itself ships no
server, so D-8's deferral and the estate's one-host topology turned out to be the same answer.
The strategy's five-tier skill roster (declared complete 2026-08-26, Epic 37.1) records mason's
skill cell as **`conda-forge-expert` — there is no `pyforge-mason` operating skill**: the
station's defining wrap-not-fork seam (D-1) is now estate policy, with the persona *consulting*
CFE as its one sanctioned skill read and 01 recipe experiments minting no portal/MCP/persona.
Convergence also ran the other way: mason publishes its build-engine hook on the shared
`pyforge.core.hooks` surface (S-10.1), hosts a steward-owned boot re-index contract
(`boot.py`), and mirrors steward's registry precedent in the air-gap socket (S-9.2). Mason
consulted conda-forge-expert throughout and replaced it nowhere — the seam the brief promised
is the seam the estate standardized on.

## Open items

- **DW ledger:** open deferred-work entries remain tracked in
  `../deferred-work-ledger.md` (station-scoped sweep runs when doctor Epic 11 ships,
  per the fleet-wide plan); none block close-out.
- **The irreversible self-publish** (SM-1's final tier) — execute deliberately, operator-gated,
  if/when `pyforge-mason` is meant to exist on public PyPI.
- **OIDC / trusted publishing** — the market's golden path (research § 5); the clearest v2
  candidate, deliberately out of v1 (D-5).
- **Autotick ownership (PRD OQ-3 / spec OQ-8)** — still a crew-level question for v2 scoping.
- **Duplicate story-spec files and the persona SKILL "No Wave B" wording** — cosmetic
  follow-ups, named in Deviations 6–7.
