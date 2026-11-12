---
title: 'Atlas — implementation readiness (2026-11-12, at the close of the cutover-readiness change)'
project: pyforge-atlas
created: '2026-11-12'
updated: '2026-11-12'
status: final
type: implementation-readiness
gate: PASS
scope: 'The readiness gate of bmad-sprint-planning (references/readiness-gate.md), run headless for readiness only (no tracking generated, no ledger or feed written) over atlas''s planning chain after Stories 46.1, 46.2, 47.1, 47.2, 48.1, 48.2, 48.3 and 41.2 were built on branch cutover-readiness-2026-11-10 and Story 48.4 flipped CAP-73 to shipped and re-stamped the chain. Written by Story 48.4; the previous gate report is implementation-readiness-report-2026-08-10.md, past its 90-day shelf life on 2026-11-08.'
---

# Atlas — implementation readiness, 2026-11-12

**Question:** could a developer implement atlas's open stories without inventing decisions nothing records?

**Overall: PASS — ready.** Every open atlas story has the decisions it needs recorded in its story spec, the Spec,
the PRD, the spine or the operator rulings of 2026-11-10. The concerns below are recorded with owners and do not block
any of them.

## Inventory (what planning exists)

| Artifact | Path (under `planning-artifacts/` unless rooted) | Date |
|---|---|---|
| Dream | `docs/dreams/pyforge-atlas.md` (`status: specified`) | Realization log through 2026-11-12 (cutover readiness, closed) |
| Research | `research/cutover-readiness-audit-2026-11-10.md` (newest of the station's research) | 2026-11-10 |
| Brief | `briefs/brief-pyforge-atlas-2026-07-25/brief.md` | 2026-11-12 (re-stamped) |
| Spec | `specs/spec-pyforge-atlas/SPEC.md` (CAP-1 to CAP-73, each defined once) with `contract.md`, `catalog-contract.md`, `gate-contract.md`, `signals.md`, `degradation-contract.md`, `live-sources.md`, `catalog-sources.md`, `glossary.md` and the retired satellite's `constitution-provenance.md` | 2026-11-12 |
| PRD | `prds/prd-pyforge-atlas-2026-07-17/prd.md` (FR-1 to FR-78; the retired satellites' sections are `Fold provenance` record sections since Story 41.2) | 2026-11-12 (re-stamped) |
| Architecture | `architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md` (AD-1 to AD-23) | 2026-11-12 (re-stamped) |
| Epics | `epics.md` (48 Epic headings, 168 Story headings; every heading has its ledger key, `chain-completeness-check` exits 0) | 2026-11-12 |
| Story specs | `specs/spec-<epic>-<story>-*.md`, one per open story | 2026-09-18 to 2026-11-11 |
| Test design | `test-architecture.md`, `test-design-architecture.md`, `test-design-qa.md`, `test-design-progress-system.md`, `test-design/` | earlier; no open story depends on a new test-design decision |
| Deferred work | `deferred-work-ledger.md` (`DW-atlas-*` and the older `DW-*` rows) | live |
| Retro | `retros/retro-pyforge-atlas-2026-11-12.md` (Epics 46 to 48 and Story 41.2) | 2026-11-12 |
| UX | `DESIGN.md`, `EXPERIENCE.md`, `design-thinking-atlas-19-pages-2026-08-28.md`; no open story builds a user interface | earlier |

## Open stories

| Story | Ledger | What it needs, and where it is recorded |
|---|---|---|
| 46.1, 46.2, 47.1, 47.2, 48.1, 48.2, 48.3, 41.2 | `backlog` or `blocked` | Built and reviewed on branch `cutover-readiness-2026-11-10` (build commits `a9349acaff`, `d063699879`, `7554595df4`); each key moves at the change's CLOSE-LEDGERS job, not here |
| 48.4 (the station's close) | `backlog` | Its story spec names the CAP-73 flip, the one Surface reconcile event, the chain re-stamp, this report, the retro and the closing Dream line, with its acceptance commands; it runs last |
| 41.3 (NFR arrows) | `blocked` | Retired at the 2026-11-10 mint (ruling: "Retire both"); never dispatched |
| 24.2 (CAP-8's canonical Parquets, one recorded run) | `blocked` | Attended and credentialed: its story spec says the ledger stays `blocked` while no credentialed Artifactory path exists and never fabricates rows; `DW-atlas-46-1-8` records the open run |
| 36.3 (the query-plane estate source has a producer) | `blocked` | Waits on a steward export through `pyforge.core.station_port` that no steward story owns (`DW-steward-egm-2026-11-1`); its story spec records the approach once unblocked and its flag, `pyforge.atlas.estate_source_producer`; CAP-68 is `B-only` (ruling R3) |
| 42.4 (the retrofit kill switches retire on their cleanup date) | `backlog` | Dated work: `cleanup_by: 2027-01-24`; its story spec records the removal path, the `retires-flag:` declaration and the keys it leaves if the operator turned one off |

## Checks

- **Requirements trace forward.** Every FR minted since the FR-arrow rule cites a resolving capability
  (`fr-without-cap-check` exits 0, 2026-11-12). FR-78 derives from CAP-73, which now reads `(shipped 2026-11-11)`.
  One advisory warning stays: FR-18 shares no content word with the capability it cites (`fr-arrow-no-title-overlap`,
  advisory by design).
- **Stories trace back.** Each story of Epics 46 to 48 names the capabilities it realizes or amends, and has a tracked
  story spec with machine-checkable acceptance criteria. Every open Spec is decomposed and epics and ledger agree
  (`chain-completeness-check` exits 0); every Spec links a Dream (`dream-chain-check` exits 0).
- **Architecture decisions are recorded.** The twelve registered pipelines (AD-3 as Story 46.2 amended it), the member
  root and data-root precedence (CAP-69 and the four resolvers it names), the frozen exit-code convention and its one
  attended exception (the Spec's Constraint beside AD-12), and the public contract (CAP-73 and `contract.md`, held by
  `tests/meta/test_public_contract.py` and `tests/meta/test_catalog_contract.py`) are written down.
- **Forward dependencies are declared, not hidden.** Stories 41.2, 47.1 and 47.2 were minted `blocked` with the forward
  dependency named in the `S-<epic>.<num>` grammar and built after the stories they name; `forward-dependency-check`
  exits 0 (atlas reports `partial`: 104 of 165 dependency declarations are machine-readable, a warning about older
  stories' grammar). Cross-station dependencies are story-spec notes.
- **Conflicts between artifacts are surfaced.** None between the Spec, PRD, spine and epics after the re-stamp; the
  chain-currency sweep for atlas is the closing check (Story 48.4 AC8).

## Concerns (recorded; none blocks)

| Concern | Where it lives | Why it does not block |
|---|---|---|
| Two planned deferral rows are addressed to the atlas closer, whose files do not include the ledger: `DW-atlas-47-1-1` (open) and `DW-atlas-41-2-1` (resolved) | `spec-47-1-…` and `spec-41-2-…` § Planned deferral (written at build); retro 2026-11-12 finding 3, action 1 | Records only; no story's implementation depends on them, and the integrator writes them at the ledger close |
| `gate-contract.md` can carry a row for a task that runs no pytest (the `kedro-test` alias row; a `viz` row passes too) | `tests/meta/test_catalog_contract.py` lines 268-273; retro 2026-11-12 finding 7, action 2 | CAP-73's success names the code-has-more direction, which the test holds |
| Four resolvers of the one member root | `query_plane_boot.py:81`, `dashboard/identity_gist.py:204`, `dashboard/data.py:127`, `admission.py:328`; retro 2026-11-12 finding 9, action 3 | Each resolves the same root (CAP-69); folding them is a refactor no open story needs first |
| Five story specs of the change carry no dated build record in their Auto Run Result | `spec-47-1-…`, `spec-47-2-…`, `spec-48-1-…`, `spec-48-2-…`, `spec-48-3-…`; retro 2026-11-12 finding 4 | The build commits date the work; CAP-73's date was read from them |
| The 24.2 attended run and the 36.3 steward export have no date | `DW-atlas-46-1-8`; `DW-steward-egm-2026-11-1` | Both stories stay `blocked` by their own specs; neither blocks another open story |

## Verdict

PASS. Story 48.4 is implementable as recorded and runs last; Stories 24.2, 36.3 and 42.4 are implementable as their
story specs record, each in its own sequence and on its own trigger. No planning skill needs to run first.
