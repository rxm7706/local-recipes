---
title: "50.1: fr-without-cap resolves every arrow against a defined capability and names a counted run"
type: 'feature'
created: '2026-10-26'
status: 'done'
flag-exempt: detector-or-gate   # a check that judges; gating it off would silence the rule it enforces (spec-feature-flag-governance CAP-1, closed list)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain.py
  - scripts/fr_baseline.py
  - docs/governance/fr-baseline.json
  - pixi.toml
  - docs/reference/detectors.md
---

<intent-contract>

## Intent

**Problem:** The 2026-09-16/17 folds wrote PRD arrows by counting, and `fr-without-cap` (Story 25.2) could not tell: it checked only that a cited number existed somewhere in an open Spec, read `FR-1.1` as `FR-1`, could not see `FR33` or `NFR-C2`, took wrapped prose lines as definitions, and had no notion of a non-CAP arrow. The 2026-10-26 ruling ("forbid it") makes "a requirement cites defined capabilities only" the rule; this story makes it enforced.

**Approach:**
- **Definition grammar.** A requirement definition opens with a marker — heading, bullet, table cell or bold — then an id `N?FR-?[A-Z]?\d+(\.\d+)*`, then a separator; a column-0 or indented line with no marker never defines; an id followed by a range (`..`) or `-letter` is a reference. Fenced code is skipped. First definition wins for citation.
- **Arrow parsing.** The text after `←` (to the first ` — `, ` *(`, ` (`, `: `, `**` or end of line) splits into items; every item must be `(spec-<x> )?CAP-m` (ranges allowed); anything else is `fr-cites-non-capability`.
- **Resolution against definitions.** A bare `CAP-m` resolves against the station Spec's capability definition lines; `spec-<x> CAP-m` against the named Spec wherever it lives (any station's `specs/` or `docs/governance/`); a missing Spec or an undefined CAP is `fr-cap-unresolved` with its reason.
- **Structure.** `fr-id-unhyphenated`; `fr-duplicate-id` (a second definition of an id, except in dated reconciliation sections, which are record); `fr-counted-run` (≥ 4 consecutive hyphenated integer ids, one own-Spec cite each, constant CAP − FR, no title word shared with the CAP's title).
- **Advisory.** `fr-arrow-no-title-overlap` WARN only, aggregated per station when large.
- **Baseline ratchet.** `docs/governance/fr-baseline.json` keeps `projects` (now the arrowless population only, so an FR that has an arrow today is enforced forever) and gains `findings` (`{check}:{FR}` keys present at the snapshot) with `findings_sha`; a listed finding is evidence, not FAIL; a listed key that no longer fires is `fr-baseline-stale` WARN. `scripts/fr_baseline.py` gains `--prune` (removes only) and `--snapshot-findings`; `--project` re-snapshots one station's arrowless ids.
- **The chain.** CAP-92 is minted for the detector and CAP-93 for FR-15 (no doctor capability carried it); FR-14 ← CAP-9, FR-15 ← CAP-93; FR-16 gets the PRD heading it never had (← CAP-11, CAP-12); the 84 cut and 4 placeholder bullets of `SPEC.md` are restored by script from `4d3ae19674^`.
- **`flag-exempt: detector-or-gate`.** A check that judges; an OFF state would be the silence it replaces.

Ledger key: `50-1-fr-without-cap-resolves-every-arrow-against-a-defined-capability-and-names-a-counted-run`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-92** (every requirement arrow resolves to a defined capability, and a counted run is named): minted by this story; the detector realizes it.
- **`spec-pyforge-doctor` CAP-93** (Doctor holds the verdict for every conformance detector): minted from PRD FR-15 so FR-15 cites a capability; realized by Stories 6.2, 6.8, 6.9 and 49.1.
- **`spec-pyforge-doctor` CAP-9** (the verdict on the Marshal's own row): FR-14 now cites it.
- **`spec-one-chain-per-station` CAP-5** (amended 2026-10-26): the rule this detector enforces; CHAIN-STANDARD § 12 names the check codes.
- **Origin.** `docs/dreams/pyforge-doctor.md` Realization log, the 2026-10-26 entry; the operator's 2026-10-26 rulings.

## Acceptance Criteria

- **AC1 — Fixtures with known answers.** Unit tests under `tmp_path` prove each rule yields exactly its named finding: a non-CAP arrow, a mention-only CAP, a cross-Spec cite into `docs/governance/`, dotted and lettered ids, an unhyphenated id, a satellite duplicate versus a reference heading in a `## Currency reconciliation — <date>` section, a counted run with and without title overlap, the wrapped prose line and the column-0 range line that must not define, a baselined finding, a stale baseline key, and `--prune`.
- **AC2 — Live tree.** On the PR head `fr-without-cap` reports no FAIL; the five Constraint arrows are gone (atlas 41.1, marshal 108.1); doctor FR-14 and FR-15 cite CAP-9 and CAP-93; `fr-counted-run` names no run once marshal's pyforge-marshal:CAP-235..pyforge-marshal:CAP-238 titles are restored; the honest runs (steward FR-32..41, atlas FR-69..77, doctor FR-9..13) are quiet.
- **AC3 — The baseline.** `docs/governance/fr-baseline.json` carries `findings` and `findings_sha`; each station's `projects` entry lists only ids whose definition has no arrow (the 82 NFR lines, warden FR9/FR30, atlas's arrowless satellite ids); every entry has a named owner story (atlas 41.2/41.3, marshal 108.2, mason 33.2, warden 20.2).
- **AC4 — Suites.** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` green with its coverage floors; `pixi run -e pyforge-guild lint-types` green for the doctor package; `detectors-ci` exit 0; the five-second CPU budget test holds.
- **AC5 — The chain.** CAP-92 and CAP-93 are defined after CAP-91; FR-14/FR-15/FR-16 carry their arrows; the capability ledger carries both CAPs as `rebuild`; the doctor retrospective for Epic 50 is in the PR (chain currency).

## Boundaries & Constraints

**Always:**
- Keep every check on `Source.FR_WITHOUT_CAP`; fail on new findings only; keep `degrade_on_exception`; read every verdict from the exit code.

**Never:**
- Never make the advisory score change the exit code; never let the baseline grow through `--prune`; never resolve a bare `CAP-m` against another Spec; never edit a PRD from the detector.

## I/O & Edge-Case Matrix

| Input | Finding |
|---|---|
| `#### FR-15: … ← Constraint "…"` | `fr-cites-non-capability` FAIL (new) |
| `- **FR-97** ← CAP-15 —` with CAP-15 defined | none |
| `← spec-pyforge-core CAP-11` with no such definition | `fr-cap-unresolved` (cap-not-defined) |
| `← spec-nowhere CAP-1` | `fr-cap-unresolved` (spec-not-found) |
| `- **FR33** ← CAP-5` | `fr-id-unhyphenated` (baselined for warden) |
| `###### FR-1:` under `## Satellite:` after `#### FR-1:` | `fr-duplicate-id` (baselined for atlas until 41.2) |
| `### FR-34: a dated note (2026-09-28)` under a currency section | none (reference) |
| `  FR-10.)` / `FR-66–FR-71 encode…` | not a definition |
| FR-164..FR-167 ← pyforge-marshal:CAP-235..pyforge-marshal:CAP-238, titles "b"/"a"/"t"/"t" | `fr-counted-run` (clears with the restored titles) |
| steward FR-32..FR-41 ← pyforge-steward:CAP-159..pyforge-steward:CAP-168 | none (titles overlap) |

</intent-contract>

## Binding

- Parent capabilities: `spec-pyforge-doctor` CAP-92 (minted), CAP-93 (minted), CAP-9; `spec-one-chain-per-station` CAP-5 (amended).
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-26 entry.
- Epic: Epic 50 (new), minted with this story. `epic-50` and `epic-50-retrospective` are minted with it. The anchor story of the one-PR effort (merge subject `Merge pyforge-doctor/50-1 into main`).
- Ledger key: `50-1-fr-without-cap-resolves-every-arrow-against-a-defined-capability-and-names-a-counted-run`.
- Deps: —.
- Minted 2026-10-26 in one chain commit; built in the same PR (the one-PR "every requirement derives from a capability" effort: atlas 41.1, doctor 50.1, herald 47.1, marshal 108.1, mason 33.1, scribe 27.1, steward 111.1, warden 20.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass, coverage floors met (AC1, AC4).
- `pixi run -e pyforge-guild lint-types` — expected: exit 0 (AC4).

**Run before the push (not dispatch gates):**
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK, no FAIL (AC2).
- `python3 -I <audit script> HEAD` (the read-only audit) — expected: zero non-CAP arrows, zero placeholder titles fleet-wide.
- `pixi run -e pyforge-guild capability-ledger-check` — expected: exit 0 (AC5).
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-doctor` — expected: no errors (AC5).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (AC4).

## Auto Run Result

Status: done (hand-built in the chain PR; promoted after the independent reviews, inside the PR)
Implementation: the detector upgrade (grammar, arrow parsing, definition-line resolution, five FAIL codes, the advisory WARN, the findings baseline and `--prune`/`--snapshot-findings`) with fixture tests; CAP-92 and CAP-93 rendered after CAP-91 (self-validate passes 1 and 2 logged); FR-14 ← CAP-9, FR-15 ← CAP-93, FR-16's heading; 84 cut and 4 placeholder bullets restored from `4d3ae19674^`; capability-ledger rows; PRD, spine and epics re-stamped with § Currency reconciliation — 2026-10-26.

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (every requirement derives from a capability) at the operator's rulings of 2026-10-26 ("yes forbid it"; the ruling sheet accepted in full).

- 2026-10-26: promoted to `done` inside the chain PR after the independent reviews of 2026-10-26 (planning tables: FAIL then PASS on the amendments; detector diff: FAIL then PASS on round 2), every finding applied in the chain PR.

- 2026-11-01 (append-only note, EGM audit DOC-D-R2 and DOC-D-C3, marshal Story 113.7; status stays `done`, no AC rewritten): three clauses CAP-92, the code and the tests gained at the 2026-10-26 review are not in this spec's Approach or ACs. (1) The detector also emits `fr-id-malformed` (a definition-shaped line whose id-like token is outside the sanctioned grammar), a sixth FAIL code beside the five named in Approach *Structure* and AC1, tested at `src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py` (`test_unhyphenated_and_malformed_ids_fail`). (2) A `spec-<x> CAP-m` cite never resolves into a closed Spec (a folded or superseded one), an `fr-cap-unresolved` finding with reason `spec-closed` (`test_prefixed_cite_resolves_against_that_spec_wherever_it_lives_never_a_closed_one`). (3) `--snapshot-findings` is a one-time act, refused once a `findings` map exists unless `--force` follows a review that names each added key in the PR (`scripts/fr_baseline.py`; `test_cli_snapshot_findings_is_one_time_and_force_prints_the_delta`). The Auto Run Result's "five FAIL codes" is the record of the implementation pass and stays as written. Doctor Story 50.2 enforces the baseline ratchet against the merge-base.

## Review Triage Log

- 2026-10-26: the independent reviews of 2026-10-26 (planning tables: FAIL then PASS on the amendments; detector diff: FAIL then PASS on round 2), every finding applied in the chain PR; no blocker open at promotion.
