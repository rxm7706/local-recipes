---
title: '49.2: The capability effect check'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 49.1's column **When** `capability-effect-check` runs **Then** it reports every capability whose ledger stories are all `done` but whose `verified:` line names an unexercised clause — advisory, exit-code domain unchanged, never a second PR verdict — and runs in `detectors` beside `story-status`

**Approach:** it reports every capability whose ledger stories are all `done` but whose `verified:` line names an unexercised clause — advisory, exit-code domain unchanged, never a second PR verdict — and runs in `detectors` beside `story-status`

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-49-2-the-capability-effect-check.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| 49.1's column **When** `capability-effect-check` runs **Then** it reports every capability whose ledger stories are all `done` but whose `verified:` line names… | `capability-effect-check` runs **Then** it reports every capability whose ledger stories are all `done` but whose `veri… | it reports every capability whose ledger stories are all `done` but whose `verified:` line names an unexercised clause — advisory, exit-code domain unchanged, never a second PR verdict — and runs in… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the check's **input is widened beyond this Spec's own CAP list** to every station's Specs: the pass that minted this story found the five worst cases in steward's *own* satellites (`unified-container… | n/a |
| And-clause from epics.md | when the story lands | it adopts the cheapest effect test the pass found: **"has a caller outside its own test file"** (fleet readiness 2026-09-09, mars-B-E6 / Class D D4) | n/a |
| And-clause from epics.md | when the story lands | the **implementation is relayed to a new doctor Dream + Spec** (fleet readiness § 2.3 C8): every other doctor Source came through doctor's own chain, and `sources/bmad_method.py:9-20` is doctor's own… | n/a |

</intent-contract>

## Binding

Parent Spec capability: `Spec Constraints (2026-09-09)`.
Surface: this Spec's `verified:` column (the **criterion** stays here). The implementation lives in doctor's own chain and is **named as a relay, never edited by steward** — Dream `docs/dreams/capability-effect-check.md`, Spec `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-capability-effect-check/`, code at `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/` (a new source), `pixi.toml` (`detectors` membership), doctor `report-schema.json` (additive)
Ledger key: `49-2-the-capability-effect-check`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-49-2-the-capability-effect-check.md`.

## Epic excerpt

**Type:** feat • **Effort:** S • **Deps:** S-49.1; cross-station: doctor's own Dream + Spec for the implementation (ledger `blocked` until doctor's story lands — never a foreign-station `Deps:` token) • **FR/AD:** Spec Constraints (2026-09-09) • doctor advisory doctrine • fleet readiness 2026-09-09 § 2.3 C8
**Surface:** this Spec's `verified:` column (the **criterion** stays here). The implementation lives in doctor's own chain and is **named as a relay, never edited by steward** — Dream `docs/dreams/capability-effect-check.md`, Spec `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-capability-effect-check/`, code at `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/` (a new source), `pixi.toml` (`detectors` membership), doctor `report-schema.json` (additive)
**Given** 49.1's column **When** `capability-effect-check` runs **Then** it reports every capability whose ledger stories are all `done` but whose `verified:` line names an unexercised clause — advisory, exit-code domain unchanged, never a second PR verdict — and runs in `detectors` beside `story-status`
**And** the check's **input is widened beyond this Spec's own CAP list** to every station's Specs: the pass that minted this story found the five worst cases in steward's *own* satellites (`unified-container`, `secure-live-dashboards`, `ocp-as-a-portability-profile`, `scratch-worktree-lifecycle`, `multi-repo-workspaces`), none of which is a Unifying CAP — a detector scoped to CAP-1..145 would be built to miss its own station on day one (fleet readiness 2026-09-09, stB-D1)
**And** it adopts the cheapest effect test the pass found: **"has a caller outside its own test file"** (fleet readiness 2026-09-09, mars-B-E6 / Class D D4)
**And** the **implementation is relayed to a new doctor Dream + Spec** (fleet readiness § 2.3 C8): every other doctor Source came through doctor's own chain, and `sources/bmad_method.py:9-20` is doctor's own precedent for a dedicated module. **Doctor records the incoming surface claim in `spec-pyforge-doctor`'s memlog BEFORE any code lands**, otherwise `spec-surface-check` reds this story and 49.8 at merge. This story closes when doctor's story lands; it is minted `blocked` until then
**Status:** done
**Outcome (2026-09-13):** doctor's Stories 21.9/21.10/21.11 shipped `sources/capability_effect.py` (`c27e8386d8`, `2bb7bc58f5`, `b2e5b9e948`); `docs/dreams/capability-effect-check.md` and its Spec are now `realized`/`shipped` with `verified:` lines on all three CAPs, including confirming the widened-beyond-this-Spec's-own-CAP-list clause against live code (`iterdir()` over every `_bmad-output/projects/*`, not a hardcoded list). Live run: 396 findings, exit 0. `pyforge-doctor-test -k capability_effect` 30/30 pass. Ledger was never flipped after the work landed; 49.8 was already closed separately (`96387a0730`).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `49-2-the-capability-effect-check: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
