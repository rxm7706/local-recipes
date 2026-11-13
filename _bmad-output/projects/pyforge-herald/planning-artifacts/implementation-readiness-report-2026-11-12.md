---
title: 'Herald — implementation readiness (2026-11-12, the cutover-readiness close)'
project: pyforge-herald
created: '2026-11-12'
updated: '2026-11-12'
status: final
type: implementation-readiness
gate: PASS
scope: 'The readiness gate of bmad-sprint-planning (references/readiness-gate.md), run for readiness only (no tracking generated, no ledger written) over herald''s planning chain after Story 50.2 re-derived spec-pyforge-herald and re-stamped the brief, PRD, spine and epics. Written by Story 50.2 step (k); it replaces the 2026-08-10 report as herald''s current gate.'
---

# Herald — implementation readiness, 2026-11-12

**Question:** could a developer implement herald's open stories without inventing decisions nothing records?

**Verdict: PASS.** Every story of herald's chain is built: Epics 1 to 49 are `done` in the ledger, and the eight
stories of Epics 50 to 52 are built and reviewed on branch `cutover-readiness-2026-11-10`, waiting only for the
change's ledger close to promote their keys. No story is left to implement, and the next herald work enters as a
Dream entry. The concerns below are recorded with owners and block nothing.

## Inventory (what planning exists)

| Artifact | Path (under `planning-artifacts/` unless noted) | Date |
|---|---|---|
| Dream | `docs/dreams/pyforge-herald.md` (`status: specified`; the landed line of 2026-11-12) | Realization log through 2026-11-12 |
| Research | `research/cutover-readiness-audit-2026-11-10.md` (newest of the station's research) | 2026-11-10 |
| Brief | `briefs/brief-pyforge-herald-2026-08-01/brief.md` | 2026-11-12 |
| Spec | `specs/spec-pyforge-herald/SPEC.md` (spec-pyforge-herald:CAP-1 to spec-pyforge-herald:CAP-62: 59 shipped, 3 retired; Constraints, Non-goals and Assumptions back with 11, 7 and 11 bullets, among them the two station-level constraints and two station-level non-goals the Spec's "Consolidated 2026-08-02" note cites, the Guildhall dependency a 2026-09-09 memlog decision orders rendered, the design-system home spec-pyforge-herald:CAP-30 cites, and the 2026-08-02 items the fold dropped, restored, narrowed or retired; every Constraints and Non-goals bullet of the Spec's own text before the 2026-09-17 fold is rendered or retired) with `contract.md` and nine other companions | 2026-11-12 |
| PRD | `prds/prd-pyforge-herald-2026-08-01/prd.md` (Feature Groups 1 to 12 and 14; FR-14.1 ← spec-pyforge-herald:CAP-62, FR-12.5 ← spec-pyforge-herald:CAP-61, spec-pyforge-herald:CAP-46) | 2026-11-12 |
| Architecture | `architecture/architecture-pyforge-herald-2026-08-01/ARCHITECTURE-SPINE.md` (no AD added by the change) | 2026-11-12 |
| Epics | `epics.md` (Epics 1 to 52; 160 Story headings, each with its ledger key) | 2026-11-12 |
| Story specs | `specs/spec-<epic>-<story>-*.md`, one per story of Epics 50 to 52 | 2026-11-10 to 2026-11-12 |
| Retro | `retros/retro-pyforge-herald-2026-11-12.md` (Epics 50 to 52) | 2026-11-12 |
| UX | none; no open story depends on a UX decision | n/a |

## Checks

- **Requirements trace forward.** Every FR in the PRD cites a defined capability (`pixi run --frozen -e pyforge-guild
  fr-without-cap-check`: exit 0 on 2026-11-12). Its advisory lists FR-1.1, FR-1.2, FR-2.1, FR-2.2 and FR-7.3 as sharing
  no content word with the capability they cite; the arrows were traced by Story 46.1 and are a reading aid, not a
  gap.
- **Stories trace back.** Each story of Epics 50 to 52 names the capability it realizes, amends or fixes under
  (spec-pyforge-herald:CAP-46, spec-pyforge-herald:CAP-62 and the markers of spec-pyforge-herald:CAP-1..CAP-61;
  `spec-pyforge-steward:CAP-175` for the relay; `spec-python-foundry-cutover:CAP-14` for the dossier claims), and
  each has a tracked story spec with machine-checkable acceptance criteria.
- **Architecture decisions are recorded.** The change relies on herald:AD-23 (one generator; the measurer under
  `docs-site/` stays under 300 lines; `verify_claims.py` is 153 lines) and on core's seam for the forge slug
  (`pyforge.core.cutover_root.forge_slug_for`); herald imports no sibling station. No story needs a decision the
  spine does not hold.
- **Forward dependencies are declared, not hidden.** Stories 50.2, 50.3, 50.4, 51.1 and 51.2 were minted `blocked`
  on a later epic's story, in the `S-<epic>.<num>` grammar, and unblocked with operator confirmation for this PR. The
  cross-station gates (steward 121.4, 121.7 and 124.1, marshal 117.2, doctor 56.5) are held by the single PR's
  integration order, not by a ledger row.
- **The chain is whole.** `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`,
  `status-body-consistency-check` and `ad-citation-check` exit 0 on 2026-11-12, with no herald row in their findings.
- **Conflicts between artifacts are surfaced.** None open between the Spec, PRD, spine and epics after Story 50.2's
  pass; its coherence pass, re-run on review round 3, resolves every "below" and "see <section>" the Spec cites. The six companions
  dated 2026-08-02 each say whether they are a record or live (`> **Standing:**`); the records keep their 2026-08-02
  counts as written.

## Concerns (recorded; none blocks)

| Concern | Where it lives | Why it does not block |
|---|---|---|
| A live `sync-all` second run never reports all-unchanged | `deferred-work-ledger.md` DW-FU-23-6-1; spec-pyforge-herald:CAP-36, spec-pyforge-herald:CAP-50 `not met` | Stated in the markers by ruling; a fix is a feature of its own |
| `/changes/` and `/status/runs/` publish "input absent" | DW-steward-43-6-1 (steward's); spec-pyforge-herald:CAP-61 `not met` | The Guild steps that feed them are steward's |
| The dossier artifact's republish and the CI-surfaces snapshot refresh are operator acts | DW-herald-egm-2026-11-01-1; spec-pyforge-herald:CAP-47, spec-pyforge-herald:CAP-59 | Operator ruling 2026-11-01; doctor Story 58.4 refreshes the snapshot once at the change's head |
| Five specs' `deferred:` frontmatter rows are not written | the retro's action 1; DW-herald-50-2-1, -50-3-2, -50-4-1, -52-1-1, -52-1-2, -52-2-1 | The ledger rows carry the intake fingerprint, so a later frontmatter row dedupes |
| The built-site oracles of spec-pyforge-herald:CAP-47 and spec-pyforge-herald:CAP-58..CAP-61 run only where docs-site's install runs first (`pyforge-herald-test-built`, and the operator's `pyforge-herald-test-coverage` report) | the Spec's § Assumptions | CI's herald job runs `pyforge-herald-test-built` with `HERALD_DOCS_SITE_REQUIRED=1` |
| Herald's live half reds on steward's preflight lane list (`test_preflight_pages_lane.py`) | the retro's finding 14 | The lane registry and workflows are steward's; the split's CI jobs are steward Story 124.2's |
| The nine Specs the 2026-09-17 fold absorbed lost their Constraints, Non-goals and Assumptions text (89 bullets at `4251c42229^`, 54 of them carried by no typed entry of their own memlogs, and 6 prose paragraphs of the two pptx Specs), and 58 constraint, non-goal and assumption entries in the archived memlogs never entered herald's memlog; the re-derived sections render none of them, and none is restored | DW-herald-50-2-2 (medium; its evidence counts each Spec); the retro's finding 1 and action 6 | Herald's own Spec text is accounted for (every Constraints and Non-goals bullet before the fold rendered or retired, its citations resolving); recovering, retiring or ruling out each absorbed item is a Spec pass of its own |
| 48 open rows of herald's deferred-work ledger carry no severity | DW-herald-50-1-3 | A `bmad-loop sweep` of its own; no open story depends on it |

## Verdict

PASS. Herald has no story left to implement in its recorded plan. The eight built stories close with the change's
ledger close; new herald work enters as a dated Dream entry and a minted Story.
