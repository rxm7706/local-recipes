---
title: "6.13: The spec-to-PRD currency edge ignores a landing's memlog bookkeeping"
type: 'fix'
created: '2026-10-07'
status: 'ready-for-dev'
baseline_revision: '966b166f76797916b96286b88587aa6f10f8240d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/CHAIN-CURRENCY-RUNBOOK.md
  - scripts/fleet_scan.py
  - scripts/chain_currency_sweep_check.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_fleet_scan_currency_feeds.py
  - _bmad/scripts/memlog.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** every landing on a station whose PRD is more than 2 days old reds `chain-currency`, though no requirement
moved.

- **The predicate.** The chain audit dates a station Spec's stage from two files, `SPEC.md` and the sibling
  `.memlog.md` (`scripts/fleet_scan.py` `_stage_globs`, about :1849-:1854), taking the later `updated` of the two
  (`_stage_dates`). Each file's date follows the strict precedence in `_artifact_dates`: frontmatter `updated:` first.
  `_currency` then fires `feeds spec→prd` when that date is more than `_FEEDS_GRACE_DAYS = 2` days past the PRD's
  (about :2112-:2135).
- **Why every landing moves it.** A landing must append a surface-reconcile entry to the Spec memlog of every path it
  changed (AGENTS.md pre-PR item 5), and marshal's `dispatch land` appends `(event by marshal) Story N.M landed …`.
  `_bmad/scripts/memlog.py append` re-stamps the memlog's `updated:` on every append. The detector's own comment
  (about :2112) already calls these appends "routine corrections, validation passes, cross-reference fixes"; the
  2-day grace was its proxy for them, and it does not hold across a station whose PRD is three days old.
- **The live cost.** On 2026-10-07 herald 28.1 (the herald Spec, and the doctor Spec through its co-governor reconcile
  of `docs/how-to/presentation-deck.md`), steward 74.2 (`37800e84e5`) and warden 14.2 (`31d1ea9a86`) each needed a hand
  PRD, spine and epics cascade, with no FR or AD changed, before `pr-preflight` would pass. Mason hit it on 2026-10-05
  (the runbook's last Worked Example: "a landing that only appends to the memlog moves it"). On 2026-10-07 atlas,
  scribe and warden sat at PRD 2026-10-03, and marshal and steward at 2026-10-04, one landing from red.
- **Measured on `966b166f76`.** `chain_currency_sweep_check.py` reads all eight stations current (exit 0). One
  `memlog.py append --type event --text "Surface reconcile 2026-10-07 (probe): no path"` on atlas's Spec memlog turns
  `chain_currency_sweep_check.py --project pyforge-atlas` to exit 1 (`chain-audit-checkpoint-staleness`). Every
  station Spec memlog's last entry on that tree is a bookkeeping entry.
- **What is NOT the problem.** `behind-code` compares the spec stage with the code's date; there a surface reconcile is
  the Spec acknowledging that the code moved, so that reading stays as it is.

**Approach:** split the Spec's date for the one edge that asks whether the contract moved.

- A memlog **bookkeeping entry** is an entry whose tag is `(event)` or `(event by <anyone>)` and whose text begins
  `Surface reconcile` or `Story <N>.<M> landed` (marshal's landing record). Every other entry is a **contract
  entry**: `(capability)`, `(decision)`, `(change)`, `(constraint)`, `(note)`, `(question)`, and every other `(event)`,
  a story mint included.
- The memlog's **contract date**: when its last entry is a contract entry, its frontmatter `updated:` (today's reading,
  unchanged). Otherwise the latest commit date among its contract entry lines, read with `git blame` against the judged
  tree; a line not yet committed dates to the run date. When `git blame` cannot read the file (no git, an untracked
  file, a failed call), the frontmatter `updated:` (today's reading).
- The Spec's **contract date** is the later of `SPEC.md`'s date (`_artifact_dates`, unchanged) and the memlog's
  contract date. The `("spec", "prd")` pair in `_currency` compares the PRD with it. Nothing else reads it.
- The spec stage's `updated` (`updatedAt` on the board, `behind-code`, shelf life, `backfilled`) is unchanged, as are the
  2-day grace, the strict precedence for every other artifact, every other feeds edge and the sweep's exit codes.
- The runbook's § *The audit mechanics you must not fight* gains one line naming the rule, so CAP-21 stays the
  procedure of record.

Ledger key: `6-13-the-spec-to-prd-currency-edge-ignores-a-landing-s-memlog-bookkeeping`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-doctor` CAP-20 (the sweep detector, ← `spec-chain-currency-sweep` CAP-1) and
  CAP-21 (the runbook's audit mechanics: the feeds cascade, the 2-day grace, the strict `updated:` precedence, ←
  `spec-chain-currency-sweep` CAP-2). The sweep reads the chain-layers audit's staleness checkpoint, which came home to
  Doctor in Epic 6 (FR-15, Story 6.5); `test_fleet_scan_currency_feeds.py` is the station suite's existing pin on the
  feeds edges (the 2026-09-04 `epics→sprint` retirement). This is a defect of shipped behaviour, so it mints no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** The 2026-10-07 hand cascades on herald 28.1, steward 74.2 and warden 14.2.

## Acceptance Criteria

- Given a fixture chain whose PRD is dated 2026-10-03, whose `SPEC.md` is dated 2026-09-28, and whose memlog's contract
  entries were committed on 2026-10-04 or earlier, followed by an `(event) Surface reconcile 2026-10-07 …` entry with
  frontmatter `updated: 2026-10-07T09:00` When `_currency` runs for 2026-10-07 Then there is no `feeds spec→prd`
  finding.
- Given the same fixture with `(event by marshal) Story 25.2 landed (run …): …` as the last entry When `_currency` runs
  Then there is no `feeds spec→prd` finding.
- Given the same fixture with a `(capability)` or `(decision)` entry committed on 2026-10-07 before the trailing
  surface reconcile When `_currency` runs Then `feeds spec→prd` fires, naming the 2026-10-07 date.
- Given the same fixture with an uncommitted `(decision)` entry before the trailing surface reconcile When `_currency`
  runs Then `feeds spec→prd` fires.
- Given `SPEC.md` re-derived with `updated: 2026-10-07` and only bookkeeping entries after 2026-10-03 When `_currency`
  runs Then `feeds spec→prd` fires.
- Given a memlog whose last entry is a contract entry When `_currency` runs Then the edge reads the frontmatter
  `updated:` exactly as today.
- Given a fixture tree that is not a git checkout When `_currency` runs Then the memlog's date is its frontmatter
  `updated:`, exactly as today.
- Given code whose date is later than `SPEC.md`'s and a same-day trailing surface reconcile, on a chain whose Dream is
  not `realized` When `_currency` runs Then `behind-code` for the spec stage reads as it does today (no new finding).
- Given the live tree and a station whose PRD is more than 2 days old When a surface-reconcile entry is appended to
  its Spec memlog and `python scripts/chain_currency_sweep_check.py --project <station>` runs Then it reads current
  (the probe in § Verification; on `966b166f76` the same probe on atlas exits 1).
- Given the bookkeeping class emptied, so every entry is a contract entry (mutation) When the station suite runs Then
  the first two fixtures fail.

## Boundaries & Constraints

**Always:**
- Fix it where the shipped behaviour lives: the memlog's date as the `("spec", "prd")` pair reads it in
  `scripts/fleet_scan.py`.
- Run `git blame` against the judged tree (`REPO_ROOT` as `board._load_dashboard_generate` repoints it, Story 40.1),
  never against Doctor's own checkout.
- Fail toward a finding: any memlog Doctor cannot date by entry reads exactly as today.
- Add the runbook line under § *The audit mechanics you must not fight* and keep every other line of the runbook.
- Reconcile the governed files on their owning Specs' memlogs and stamp them scoped. `spec-pyforge-marshal` governs
  `scripts/fleet_scan.py`; `spec-pyforge-doctor` owns the station tests; run `spec-surface-check` for any co-governor it
  names (AGENTS.md pre-PR item 5).

**Never:**
- Never change `_FEEDS_GRACE_DAYS`, the `_FEEDS` graph, the strict date precedence of `_artifact_dates`, `behind-code`,
  shelf life or `backfilled`.
- Never widen the bookkeeping class beyond the two openings above (a story mint, a correction or a validation pass is a
  contract entry here); widening it is a separate ruling.
- Never edit a station's memlog, `SPEC.md`, PRD, spine or epics to make a finding pass, and never bump an `updated:`
  without a reconcile (CAP-24).
- Never change `_bmad/scripts/memlog.py`: it is installer-owned BMAD code.
- Never import `pyforge.marshal` or `pyforge.doctor` from `scripts/fleet_scan.py`; never change the sweep's exit codes.
- Never weaken or delete an existing test.

## I/O & Edge-Case Matrix

| Memlog shape (PRD 2026-10-03, run 2026-10-07) | `feeds spec→prd` |
|---|---|
| last entry `(event) Surface reconcile …`, newest contract entry committed 2026-10-04 | none |
| last entry `(event by marshal) Story 25.2 landed …`, newest contract entry 2026-10-04 | none |
| a `(decision)` committed 2026-10-07, then a surface reconcile | fires (2026-10-07) |
| a `(capability)` not yet committed, then a surface reconcile | fires (run date) |
| last entry a contract entry, `updated:` 2026-10-07 | fires, as today |
| `SPEC.md` `updated:` 2026-10-07, only bookkeeping after 2026-10-03 | fires |
| no git (fixture tree), `updated:` 2026-10-07 | fires, as today |
| an `(event)` about a surface that does not begin `Surface reconcile` (for example `(event) 2026-10-05 spec-surface: …`) | a contract entry: dates as today |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-07 (detector gaps) entry.
- Epic: Epic 6 (a fix joins the epic that brought the chain verdicts home, which reopens; Story 41.5; Story 6.12 is the
  precedent).
- Ledger key: `6-13-the-spec-to-prd-currency-edge-ignores-a-landing-s-memlog-bookkeeping`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Dispatch note: Epic 6's `[epic_surfaces]` entry in `planning-artifacts/marshal-policy.toml` admits only the default
  surface. A Marshal dispatch needs `scripts/fleet_scan.py`, the runbook and the co-governor memlogs admitted first
  (that file is governed by `spec-pyforge-marshal`), or the story lands by hand, as 6.12 and 27.6 did.
- Minted 2026-10-07 with Story 34.6, in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild python scripts/chain_currency_sweep_check.py` — expected: exit 0, all eight
  stations current.
- Probe: `python _bmad/scripts/memlog.py append --path <atlas Spec memlog> --type event --text "Surface reconcile
  <date> (probe): no path"` on a station whose PRD is more than 2 days old, then `chain_currency_sweep_check.py
  --project <that station>` — expected: exit 0. Restore the memlog with `git checkout --`.
- Mutation: empty the bookkeeping class and re-run the station suite; the first two fixtures fail. Restore it.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped
  stamps.

## Review Triage Log

- No review has run yet.
