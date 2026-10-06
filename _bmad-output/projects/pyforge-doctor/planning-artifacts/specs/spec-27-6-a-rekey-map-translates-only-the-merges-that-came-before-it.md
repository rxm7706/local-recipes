---
title: "27.6: A rekey map translates only the merges that came before it"
type: 'fix'
created: '2026-10-06'
status: 'in-progress'
baseline_revision: '609be7ff82ddb1f30ea6ab2faf076b9086d3920a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-27-2-ledger-direction-reads-the-stations-rekey-map.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/rekey-2026-09-17.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger_direction.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `ledger-direction` reads a station's new story through an old fold's rekey map.

- **The predicate.** `gather_direction` (`src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py`)
  collects the story ids that `main`'s merge subjects name (`_merged_ids_for_project`), then passes the whole set
  through `_rekey_sid_maps`' result (about :1133-1135). Every map the station tracks applies to every merge,
  whenever the merge happened.
- **The live failure.** Atlas's 2026-09-17 fold shifted Epics 12..25 to 11..24, so `rekey-2026-09-17.md` maps the
  old `25-2` to `24-2`. Atlas's new Story 25.2 (`spec-pyforge-atlas` CAP-61) landed on 2026-10-05 as
  `3f2744da9e Merge pyforge-atlas/25-2 into main`. The detector read that merge as `24-2`, which is `blocked`, and
  failed `landed-but-unpromoted`. Measured: `gather_direction` at `3f2744da9e^1` and at `a529f18da3` (the PR head)
  reports nothing; at `3f2744da9e` and every later `main` it reports the row.
- **The second, latent defect.** `_rekey_sid_maps` walks each entry to a fixed point across the union of all maps
  (about :971-983). A one-epic shift map holds both `13-1 -> 12-1` and `12-1 -> 11-1`, so a pre-fold merge naming
  `13-1` resolves to `11-1` instead of `12-1`. Atlas's 25-2 stopped at `24-2` only because the old Epic 24 had no
  `24-2`.
- **What 27.2 fixed, which must hold.** The 27.2 incident merge `7156c2b66f` (2026-08-10, a bmad-loop merge naming
  atlas's old `13-5`) predates the map's arrival on `main` (`93bcba96dc`, first-parent, 2026-09-17).

**Approach:** date each map and each merge, and translate only forward in time.

- For each `rekey-*.md` tracked at the base ref, record its own `{old_sid: new_sid}` entries (no fixed point inside
  one map) and the committer time of the commit that added it on the base ref's first-parent line
  (`git log --first-parent --diff-filter=A --format=%ct <base_ref> -- <path>`, the oldest such commit).
- Read each commit's committer time in the same `git log` that already reads the subjects, and record which
  commits named each merge-derived id.
- Translate an id per naming commit: apply each map in arrival order, one hop, only when the commit predates that
  map's arrival. An id named both before and after a map yields both readings.
- A map whose arrival time cannot be read, or a commit whose time cannot be read, keeps today's behaviour: the map
  applies. That fails toward Story 27.2's guarantee, never toward a new false row.

Ledger key: `27-6-a-rekey-map-translates-only-the-merges-that-came-before-it`.
Type / Effort / Deps: fix / S / S-27.2.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-doctor` CAP-79 (`ledger-direction` reads the station's rekey map; Story
  27.2). This is a defect of shipped behaviour, so it mints no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** Found 2026-10-05 while landing atlas 25.2 by hand: the bookkeeping branch's `detectors-ci` and
  `pr-preflight` were red only on this row.

## Acceptance Criteria

- Given the live tree When `ledger.gather_direction(repo_root)` runs Then no finding names
  `pyforge-atlas/24-2-materialize-cap-8-s-canonical-parquets-one-recorded-run`, and no atlas
  `landed-but-unpromoted` row appears for 13-5, 14-4 or 15-3.
- Given a map `25-2-old -> 24-2-old` committed, then a later merge `Merge pyforge-atlas/25-2 into main`, and a ledger
  with `24-2-old: blocked` and `25-2-new: done` When `gather_direction` runs Then there is no FAIL.
- Given a merge naming `13-5` committed before a map `13-5 -> 12-5`, and `12-5` done When `gather_direction` runs Then
  the result is `ok` (Story 27.2's case, re-dated so the merge predates the map).
- Given two maps, `13-5 -> 12-5` then `12-5 -> 11-5`, and a merge naming `13-5` before both When `gather_direction`
  runs Then it resolves to `11-5`; a merge naming `12-5` made between the two maps resolves to `11-5`; a merge naming
  `12-5` made after both stays `12-5`.
- Given one shift map holding `13-1 -> 12-1` and `12-1 -> 11-1`, a pre-map merge naming `13-1`, a ledger with
  `12-1: done` and `11-1: backlog` When `gather_direction` runs Then there is no FAIL.
- Given the translation applied regardless of date (mutation) When the station suite runs Then the post-map fixture
  fails.

## Boundaries & Constraints

**Always:**
- Fix it where the shipped behaviour lives: `_rekey_sid_maps` and the translation in `gather_direction`.
- Use committer time (`%ct`) for both sides; the map's arrival is the oldest first-parent commit that added it at
  the base ref.
- Keep `rekey-map-unreadable` exactly as it is (WARN naming the file, never a crash).
- Reconcile the governed files on their owning Specs' memlogs and stamp them scoped. `spec-pyforge-doctor` owns
  `ledger.py`, and `spec-pyforge-core` co-governs every station's `src/` (AGENTS.md pre-PR item 5).

**Never:**
- Never edit atlas's rekey map, ledger or epics to make the finding pass.
- Never drop Story 27.2's translation for merges older than the map.
- Never change `gather()`'s own rekey handling (`_new_rekey_maps`); it compares a base/head range, not merge
  subjects.
- Never import `pyforge.marshal`; never widen the exit-code domain `{0, 2, 130}`.
- Never weaken or delete an existing test; re-dating a 27.2 fixture so its merge predates its map keeps what it
  proves.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-06 (rekey dating) entry.
- Epic: Epic 27 (a fix joins its own epic, which reopens; Story 41.5).
- Ledger key: `27-6-a-rekey-map-translates-only-the-merges-that-came-before-it`.
- Ledger status at mint: `backlog`.
- Deps: S-27.2.
- Minted 2026-10-06 on branch `landing-bookkeeping-2026-10-05`, with the fix in the same PR: the bookkeeping PR's
  preflight cannot pass while this row is red, and a separate PR's preflight cannot pass without the bookkeeping.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild ledger-direction-check`: no atlas `landed-but-unpromoted` row.
- `pixi run --frozen -e pyforge-guild detectors-ci`: exit 0.
- Mutation: make the translation ignore dates and re-run the station suite; the post-map fixture fails. Restore it.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
