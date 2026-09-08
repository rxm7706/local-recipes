---
title: 'pyforge-doctor — Retrospective (Epics 5–18, the conformance-home era)'
project: pyforge-doctor
created: '2026-08-26'
updated: '2026-08-26'
scope: 'Everything since the 2026-08-08 whole-build retro: Epics 5–18 (66 stories), the code→retro currency edge that fired at 2026-08-24 vs. 2026-08-08'
evidence:
  - 'git log --oneline --since=2026-08-08 -- src/shared/packages/pyforge-doctor (65 commits)'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml (82/82 done, stamped 2026-08-26)'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-*.md (Epic 5–18 story specs, 2026-08-09 → 2026-08-26)'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/research/*-2026-08-08.md (the refresh wave this period opened with)'
---

# pyforge-doctor — Retrospective (Epics 5–18)

**Scope:** the 18 days after the 2026-08-08 whole-build retro declared "Doctor's build
is closed; this retro is the terminal artifact for it." It was terminal for the v1
consolidation thesis only: 65 commits have touched `src/shared/packages/pyforge-doctor`
since, and the tracked ledger has gone from 16 to **82 stories done** (Epics 5–18).
**Retro produced:** 2026-08-26, as the reconciler half of the chain-currency sweep
(the `code→retro` feeds edge fired: code last moved 2026-08-24, last retro 2026-08-08).
**Format:** solo / AI-driven effort; evidence is commits, story specs, and the ledger —
no fabricated dialogue.

## What shipped

Fourteen epics, clustering into four arcs:

- **The Charter §6 arc — Doctor becomes the fleet's verdict home (Epics 5–6, FR-14/15/16).**
  Story 5.1/5.2 shipped the marshal-durability source (AD-11: reads tracked ledgers +
  git, imports no station package) and wired it to a verb. Epic 6 then re-homed the 10
  detectors that judge another station's artifact as Doctor sources behind one
  dispatcher (`python -m pyforge.doctor.sources`, 14 addressable sources today):
  ledger verdicts (6.4), board verdicts (6.5), chain verdicts (6.6),
  `forward_dependency` with the AD-13 harness-coupling decision (6.7), `bmad_drift`
  without breaking the board (6.8), and the retirement of 8 legacy `scripts/` shims —
  6.9's landing note records it was "rebuilt across 87 commits of drift" after the
  shims kept moving under the port. 6.10 made independence structural for *every*
  source; 6.11 taught the classifier the spike-report shape. 6.1 re-profiled
  `doctor check` back inside its NFR-4 budget before the additions landed.
- **The deferred-work arc (Epics 7, 8, 11, 13).** Identity minted at defer time (7.1),
  the 470-entry legacy backlog grandfathered at a dated cut-off (7.2) then parsed,
  minted, promoted, and baseline-re-stamped so a second run is a no-op (8.1–8.4);
  Epic 11 built the re-verification pipeline (due-for-verification selection, churn
  filtering, mechanical checks without an agent, evidence-grounded judgment verdicts,
  cross-project reach, near-duplicate detection, staleness surfacing ambiently);
  Epic 13 surfaces matching deferred entries during story drafting.
- **The ambient-drift arc (Epics 9, 10, 12, 14, 15, 16).** The five hygiene finding
  classes got testable definitions and the sweep runs against all eight stations,
  report-never-mutate (9.1–9.3); loop-home staleness joined the ATTENTION block (9.4);
  BMAD's installed core is compared against declared floor and upstream, ambient and
  never gating (10.1–10.3); the fleet tooling's documented sharp edges were fixed —
  including capability-id parsing for chain completeness and closing the spec-surface
  baseline write race (12.1–12.5); the bmad-suite's lag became derived-not-declared
  (14.1), GitHub releases unblinded the npm-invisible packages and channel/recipe
  staleness became ambient (15.1–15.2); sibling dreams-directory drift became an
  ambient finding (16.1).
- **The Canopy arc (Epics 17–18, post the 2026-08-24 obligations).** Gather/prescribe
  became hook specs on the shared `pyforge.core.hooks` contract with today's backends
  as the default plugins (17.1, canopy:AD-21); Doctor minted its SKF domain skill and
  `bmad-agent-doctor` persona (18.1, closed with a CAP-15 consult guard on review) and
  landed its first portal job — `/stations/doctor/` renders the last fleet pulse via
  `PortalClient` only (18.2, landed 2026-08-26).

## What held

- **The AD-1..AD-6 spine absorbed a 5× scope growth without a rewrite.** The frozen
  `Finding`/`DoctorReport` contract took ~12 new sources; AD-5's sole-subprocess rule
  held by *catching its own violation* — `sources/marshal.py`'s first cut called
  `subprocess` directly, `test_cli_bridge_sole_subprocess.py` failed, and the fix was
  AD-12 (widen the sanctioned site with `run_git()`) rather than a second shell-out
  site. That is the meta-test program working as designed.
- **"Advisory, never gating" survived becoming the verdict home.** The riskiest part
  of Epic 6 was that a station holding 14 conformance verdicts drifts into being a
  second PR gate. It did not: exit-code domain still `{0, 2, 130}`, bmad-core drift
  "surfaces ambiently, never gates" (10.3) is the template every later source
  followed, and the operating-model bind (findings are advisory or Warden *inputs*)
  is now written into the hooks module's own docstring.
- **Independence became structural, not conventional.** AD-11's no-station-import rule
  generalized to every source (6.10) and is meta-tested — the judged station cannot
  weaken its own judgement. AD-13 resolved the hardest case (the `bmad_loop` harness
  coupling) by moving the invariant from runtime import to test-time set-equality.
- **The 2026-08-08 refresh reports proved immediately load-bearing:** the technical
  refresh's debt register and the domain refresh's answered-questions table were the
  grounding for this sweep's brief/PRD/arch reconciliation — commissioned research
  that got consumed, not shelved.

## What changed course

- **"Terminal artifact" lasted one day.** The 08-08 retro closed the build the same
  day FR-15's detector-ownership audit reopened it — the pattern to carry: a station
  retro can close an *arc*, but "the build" of a station in this estate is never
  closed while the Charter can mint it a new role.
- **The FR inventory stopped being the story universe.** From Epic 7 on, sibling Specs
  (deferred-work visibility, resolution sweep, hygiene exemplar, bmad-method drift,
  backlog intake, sibling-dreams drift) decompose directly into epics referencing
  CAP-Ns — no new PRD FR-Ns minted. Recorded in the PRD's 2026-08-26 reconciliation
  so nobody reads FR-1..16 as complete coverage.
- **Cross-station landings became normal.** Chain-audit code that lives in
  `pyforge.doctor.sources` landed under *marshal* story numbers (17-3, 21-1 —
  FR-150/FR-192 CAP-3), and marshal 19.2's `pyforge-testing-kit` is now imported by
  Doctor's tests. Ownership of the verdict surface (Doctor) and ownership of the
  driving story (whichever station's PRD minted the FR) have decoupled — fine in
  practice, worth knowing when tracing a change.

## Strategy convergence (Unifying Strategy check)

Doctor's five-tier obligations as spoke #5 of the Canopy: CLI (`doctor`, also
`pyforge doctor …` via CAP-5 dispatch) — shipped; web portal (`/stations/doctor/`,
first slice) — shipped 2026-08-26; service face (`POST /stations/doctor/mcp` on the
host ASGI; mounts owned by steward) — Doctor-side obligations recorded, dual-era with
the in-process MCP *client* AD-6 already runs; domain skill + persona — shipped
(Epic 18, `.claude/skills/pyforge-doctor/`, `bmad-agent-doctor`). Constraints held:
no second chrome, no extra port, no `pyforge.*` under `src/platform/`, never a
competing PR-gate verdict. `stack.md`'s `doctor check --syntax` preflight bind
(taplo/sqlfluff/yamllint) is noted as *bound but not yet built* — no story exists.

## Open items (carried forward, with owners)

1. **Marshal-side unprompted `doctor check` pre-flight** — the adoption half of SM-1,
   open at 08-08; not re-verified this pass (wiring lives in Marshal policy, not in
   Doctor's stories). Owner: Marshal.
2. **Shared AST alias-resolution helper** (technical refresh debt #1, 3 recurrences) —
   still open; `pyforge-testing-kit` (2026-08-23) ships mock families, not AST guard
   helpers. Owner: Doctor or a testkit sibling, first new guard pays for it.
3. **Atlas label/JSON-shape coupling smoke assertions** (debt #3) — still convention,
   not contract. One test-only story.
4. **`DoctorReport` schema_version bump policy** — `schema_version: 1` shipped; the
   bump rule is still undefined (SPEC + PRD OQ 4).
5. **`chain-currency-sweep` Spec** — the Dream (owner: doctor) is `dream-without-spec`
   in the chain audit's orphans checkpoint; the Spec is being authored in a parallel
   pass this same day. This retro deliberately does not touch it.
6. **Per-epic retro habit** — the 08-08 action item ("run per-epic retros going
   forward") was *not* followed: this is again a 14-epic batch retro reconstructed
   from specs and commits, and all 18 `epic-N-retrospective` ledger keys sit
   `optional`. Either adopt the habit or retire the action item honestly; the
   chain-currency sweep's `code→retro` edge (this document's trigger) is currently
   the only mechanism forcing retro cadence, and 16 days of lag is what it permits.

## Readiness

All 82 stories done in the tracked ledger as of 2026-08-26; the planning spine
(brief → PRD → arch → epics) was reconciled and re-dated in the same sweep that
produced this retro. Doctor's contract of record: `specs/spec-pyforge-doctor/SPEC.md`
(CAP-1..9, `shipped`) plus the sibling Specs its later epics decompose. This retro
closes the Epic 5–18 arc; per finding 6 above, it makes no claim to be terminal.
