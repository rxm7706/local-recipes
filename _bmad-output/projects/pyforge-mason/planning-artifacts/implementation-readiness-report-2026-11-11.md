---
title: 'Mason — implementation readiness (2026-11-11, after the cutover-readiness review)'
project: pyforge-mason
created: '2026-11-11'
updated: '2026-11-11'
status: final
type: implementation-readiness
gate: PASS
scope: 'The readiness gate of bmad-sprint-planning (references/readiness-gate.md), run for readiness only (no tracking generated, no ledger written) over mason''s planning chain after Story 37.1 re-derived spec-pyforge-mason and Story 37.2 reviewed the brief, PRD, spine and epics in feed order. Written by Story 37.2; the previous gate report is implementation-readiness-report-2026-08-10.md.'
---

# Mason — implementation readiness, 2026-11-11

**Question:** could a developer implement mason's open stories without inventing decisions nothing records?

**Overall: PASS — ready.** Every open mason story has the decisions it needs recorded in its story spec, the Spec,
the PRD, the spine or the operator rulings of 2026-11-10. The concerns below are recorded with owners and do not
block any of them.

## Inventory (what planning exists)

| Artifact | Path (under `planning-artifacts/` unless rooted) | Date |
|---|---|---|
| Dream | `docs/dreams/pyforge-mason.md` (`status: specified`) | Realization log through 2026-11-10 (the cutover readiness audit) |
| Research | `research/cutover-readiness-audit-2026-11-10.md` (newest of the station's research) | 2026-11-10 |
| Brief | `briefs/brief-pyforge-mason-2026-07-25/brief.md` (with `addendum.md`) | 2026-11-11 (reviewed) |
| Spec | `specs/spec-pyforge-mason/SPEC.md` (CAP-1 to CAP-37, each defined once) with `contract.md`, `glossary.md`, `feedstock-refresh.md`, `campaign-state.yaml` | 2026-11-11 |
| PRD | `prds/prd-pyforge-mason-2026-07-25/prd.md` (FR-1 to FR-64, NFR-1 to NFR-16, D-1 to D-13) | 2026-11-11 (reviewed) |
| Architecture | `architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md` (AD-1 to AD-16, AD-25 to AD-28; the retired Presenton AD-17 to AD-24) | 2026-11-11 (reviewed) |
| Epics | `epics.md` (39 Epic headings, 138 Story headings; every heading has its ledger key) | 2026-11-11 |
| Story specs | `specs/spec-<epic>-<story>-*.md`, one per story of Epics 37 to 39, and one per other open story | 2026-10-09 to 2026-11-11 |
| Test design | `test-architecture.md`, `test-design-architecture.md`, `test-design-qa.md`, `test-design-progress-system.md`, `test-design/pyforge-mason-handoff.md` | earlier; no open story depends on a new test-design decision |
| Deferred work | `deferred-work-ledger.md` (`DW-mason-*` rows) | live |
| Retro | `retros/retro-pyforge-mason-2026-09-20.md` (newest; Story 37.4 writes the next) | 2026-09-20 |
| UX | none; no open story has a user interface (the portal is `django-mason` code under `spec-pyforge-unifying-strategy`) | n/a |

## Open stories

| Story | Ledger | What it needs, and where it is recorded |
|---|---|---|
| 37.4 (the station's close) | `blocked` (forward dependency) | Its story spec names the retro, the surface-reconcile events, the deferral intake, Story 5.4's record and `DW-mason-25-2-3`, and its acceptance commands; it runs last, after Stories 37.1 to 39.1 |
| 33.2 (NFR arrows) | `backlog` | Its story spec: trace each of NFR-1..NFR-16 from a capability's success and prune `docs/governance/fr-baseline.json`; it edits `prd.md`, so it is never built beside Story 37.2 |
| 22.3, 22.4 (two sentinel recipes) | `blocked` | Each waits on a named upstream rattler-build release; the decisions are in their story specs |
| 39.2 (conda-forge-expert's own Spec) | `blocked`, as minted | Specs nothing in this change; the operator flips its key after `pyforge.cutover_root` flips; its story spec lists the decisions it will take |

Stories 37.1, 37.3, 38.1, 38.2, 38.3 and 39.1 are built on branch `cutover-readiness-2026-11-10` and Story 37.2 is
this review; their ledger keys move at the change's close (the CLOSE-LEDGERS job), not here.

## Checks

- **Requirements trace forward.** Every FR in the PRD cites a defined capability (`← CAP-n`; `fr-without-cap-check`
  exits 0). Story 37.2 read FR-58 to FR-64 against CAP-36, CAP-37, CAP-5, CAP-7, CAP-27 and CAP-28 as Story 37.1
  words them: FR-58 to FR-62 were amended with the clauses their capabilities state, FR-63 and FR-64 read true. FR-48
  names the six global knobs and the two environment-only factory-island variables and cites CAP-36. Every capability
  that is neither retired (CAP-8..CAP-17, CAP-31, CAP-35) nor A-only (CAP-18..CAP-26) is cited by a requirement; an
  A-only capability's FR is written when it is rebuilt (CAP-19 and CAP-21..CAP-26 by Story 39.2).
- **Stories trace back.** Each story of Epics 37 to 39 names the capabilities and requirements it realizes
  (FR-58 to FR-64) and has a tracked story spec with machine-checkable acceptance criteria. Epics 37 to 39 trace to the
  spine through AD-13, AD-16, AD-27 and AD-28.
- **Architecture decisions are recorded.** The factory-island resolution (AD-27), the contract companion and its
  meta-test (AD-28), the two suite halves (AD-16 as amended), the closed knob set with its two environment-only
  variables (AD-13 as amended), the sole CFE caller (AD-3) and the read-only CFE surface (AD-15) are in the spine. The
  floor is 3.14 in the Spec's Constraint, PRD NFR-11 and D-6, the spine's stack row and the package manifests.
- **Forward dependencies are declared, not hidden.** Stories 37.1, 37.3 and 37.4 were minted `blocked` with the
  forward dependency named in the `S-<epic>.<num>` grammar, unblocked only with operator confirmation; Story 37.4 runs
  last. Cross-station dependencies are written in story-spec notes, not `**Deps:**` lines.
- **Conflicts between artifacts are surfaced.** Two remain, both recorded below; neither changes what a story must
  build.

## Concerns (recorded; none blocks)

| Concern | Where it lives | Why it does not block |
|---|---|---|
| `SPEC.md`'s `companions:` comments still read `FR-1..FR-50` for the PRD and `AD-1..AD-16 + AD-25/AD-26` for the spine | Story 37.2's story spec, § Planned deferral (written at build); Story 37.4 writes the ledger row | Comments only; no capability text, surface or acceptance criterion depends on them, and `SPEC.md` moves only through a memlog entry and a render |
| The sixteen NFRs carry no capability arrow | Story 33.2; `docs/governance/fr-baseline.json` (baselined) | The rule's pre-rule population, baselined until Story 33.2 lands in its own sequence |
| The Docker build of a factory-island recipe reports a directory the script does not write; the ship and submit root does not follow the root of record | Story 39.1's `deferred:` rows; CAP-36; AD-27 | Recorded deferrals by operator ruling 2026-11-10; native build is the capability |
| Nine of ten wrapped CFE scripts have no real-CFE fidelity run | Story 38.3's `deferred:` row | FR-62's static argv check covers each script's existence and options |
| conda-forge-expert has no Spec of its own | Story 39.2, `blocked` as minted; CAP-19, CAP-21..CAP-26 routing lines | Operator ruling 2026-11-10: A-only until its own Spec Story, after the flip |
| The newest mason retro is 2026-09-20 | Story 37.4 | Story 37.4 writes the retro over Epics 37 to 39 within two days of the package change |

## Verdict

PASS. Story 37.4 is implementable as recorded once the stories its Deps name are built and the operator confirms the
unblock; Stories 33.2, 22.3, 22.4 and 39.2 are implementable as their story specs record, each in its own sequence.
No planning skill needs to run first.
