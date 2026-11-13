---
title: 'Warden — implementation readiness (2026-11-12, the cutover-readiness close)'
project: pyforge-warden
created: '2026-11-12'
updated: '2026-11-12'
status: final
type: implementation-readiness
gate: PASS
scope: 'The readiness gate of bmad-sprint-planning (references/readiness-gate.md), run for readiness only (no tracking generated, no ledger or feed written) over warden''s planning chain after Story 25.2 re-stamped the brief, PRD, spine and epics and rendered CAP-28''s marker. Written by Story 25.2''s close step; it replaces the 2026-08-10 report as warden''s current gate.'
---

# Warden — implementation readiness, 2026-11-12

**Question:** could a developer implement warden's open stories without inventing decisions nothing records?

**Verdict: PASS.** Every story of warden's chain is built. Epics 1 to 24 are `done` in the ledger (76 of 84 stories),
and the eight stories of Epics 25 to 27 are built and reviewed on branch `cutover-readiness-2026-11-10`, waiting only
for the change's ledger close to promote their keys. No story is left to implement; the next warden work enters as a
dated entry on the station Dream. The concerns below are recorded with owners and block nothing.

## Inventory (what planning exists)

| Artifact | Path (under `planning-artifacts/` unless noted) | Date |
|---|---|---|
| Dream | `docs/dreams/pyforge-warden.md` (`status: specified`; *What is real* points at the ledger for counts and at `archive/docs/specs/pyforge-warden.md` for the legacy intake) | Realization log through 2026-11-10 |
| Research | `research/cutover-readiness-audit-2026-11-10.md` (newest of the station's research) | 2026-11-10 |
| Brief | `briefs/brief-pyforge-warden-2026-07-25/brief.md` | 2026-11-12 |
| Spec | `specs/spec-pyforge-warden/SPEC.md` (spec-pyforge-warden:CAP-1 to CAP-29, all 29 `shipped`; CAP-28 since 2026-11-11) with `verdict-contract.md`, `axes.md`, `extraction-contract.md`, `glossary.md`, `contract.md` and `proof-map.md` | 2026-11-12 |
| PRD | `prds/prd-pyforge-warden-2026-07-14/prd.md` (FR-1..FR-50, FR-51 next free; every FR and NFR line cites a defined capability) | 2026-11-12 |
| Architecture | `architecture/architecture-pyforge-warden-2026-07-14/ARCHITECTURE-SPINE.md` (module tree re-drawn as built; no numbered AD, row DW-warden-cutover-2026-11-10-7) | 2026-11-12 |
| Epics | `epics.md` (Epics 1 to 27; 84 `### Story` headings and 26 `## Epic` headings, each with its ledger key) | 2026-11-12 |
| Story specs | `specs/spec-<epic>-<story>-*.md`, one per story of Epics 25 to 27 | 2026-11-10 |
| Test architecture | `test-architecture.md` (regenerated 2026-11-12: 84 stories, 89 test files) | 2026-11-12 |
| Retro | `retros/retro-pyforge-warden-2026-11-12.md` (Epics 25 to 27) | 2026-11-12 |
| UX | none; the one UI surface is `django-warden`'s portal, outside this Spec's surface, and no open story depends on a UX decision | n/a |

## Checks

- **Requirements trace forward.** Every FR and NFR in the PRD cites a defined capability (`pixi run --frozen -e
  pyforge-guild fr-without-cap-check`: exit 0 on 2026-11-12). Its advisory lists FR-31, NFR-R2, NFR-R3.1, NFR-S4,
  NFR-S5, NFR-S8, NFR-P4, NFR-I2 and NFR-U1 as sharing no content word with the capability they cite; those arrows
  were traced by Stories 19.1 and 20.2 and are a reading aid, not a gap. Every capability CAP-1..CAP-29 has at least
  one arrow (Story 25.2's AC2).
- **Stories trace back.** Each story of Epics 25 to 27 names the capability it realizes or amends
  (spec-pyforge-warden:CAP-27 and CAP-29 for Epic 25, CAP-28 for Epic 26, `spec-pyforge-steward:CAP-175` for the Epic
  27 relay) and has a tracked story spec with machine-checkable acceptance criteria.
- **Architecture decisions are recorded.** The change relies on the 2026-09-28 Decisions 1 and 2 (pixi runs only
  inside the actuator's real path; the fleet lives in `django-warden`) and on the sole-ownership walls the spine
  states (`verdict.py`, `engines.py`). It adds no module, port or package boundary. The spine still carries no
  numbered AD-n; that is a deferred row (DW-warden-cutover-2026-11-10-7), and no open story needs one.
- **Forward dependencies are declared, not hidden.** Stories 25.2, 25.3 and 26.2 were minted `blocked` on a later
  epic's story and built with the operator's recorded consent (`72f3e3158f`). The cross-station gates (steward 121.7,
  124.2 and 124.3) are held by the single PR's integration order; all three are on the branch.
- **The chain is whole.** `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`,
  `governance-currency`, `status-body-consistency-check`, `ad-citation-check`, `story-status-check`,
  `deferred-work-check` and `tea-playwright-check` exit 0 on 2026-11-12, with no warden row in their findings.
  `capability-ledger-check` exits 0 (923 live capability extracts match 923 rows).
- **Conflicts between artifacts are surfaced.** None open between the Spec, PRD, spine and epics after Story 25.2's
  pass: the Python floor reads 3.14 everywhere, NFR-S9 and S9 claim an age only for the LTS registry, Journey 4 and
  NFR-R3.2 no longer name unbuilt behaviour (`review_required`, a `--deterministic` volatile-field pin), and the
  spine's tree names every module under `src/pyforge/warden/`.

## Concerns (recorded; none blocks)

| Concern | Where it lives | Why it does not block |
|---|---|---|
| The conda-to-pypi map carries no snapshot and nothing checks its age | DW-warden-cutover-2026-11-10-1; the Spec's narrowed *Bundled data* Constraint | Operator ruling 2026-11-10: the narrowed Constraint stands |
| `--deterministic` changes nothing; the SBOM's `serialNumber` and `metadata.timestamp` are volatile | DW-warden-cutover-2026-11-10-2; CAP-10 | Operator ruling 2026-11-10: the flag stays reserved |
| The report schema leaves `advisory` and `actuation` untyped | DW-warden-cutover-2026-11-10-3; `contract.md` and its test hold the key sets | Operator ruling 2026-11-10: the schema stays 1.1.0 |
| The bundled LTS registry reads stale from 2027-01-02 | DW-warden-cutover-2026-11-10-5 | A data refresh, dated, with an owner |
| CAP-16 and CAP-17 have no proving test of their success clauses | DW-warden-cutover-2026-11-10-12, -13; `proof-map.md` § *Gaps* | Both live in `django-warden`, A-only until steward 121.5 |
| Five `live_tree` test modules derive the repository root at import, so a shallow export of the package cannot collect its package half | the retro's finding 5 and action 1; Story 25.2's *Planned deferral* | In this checkout both halves collect and pass; the fix is a test-only story of its own |
| 86 medium and 16 low findings of the 2026-11-05 EGM audit are untriaged | DW-warden-cutover-2026-11-10-6 | A triage pass of its own; no open story depends on it |

## Verdict

PASS. Warden has no story left to implement in its recorded plan. The eight built stories close with the change's
ledger close; new warden work enters as a dated Dream entry and a minted Story.
