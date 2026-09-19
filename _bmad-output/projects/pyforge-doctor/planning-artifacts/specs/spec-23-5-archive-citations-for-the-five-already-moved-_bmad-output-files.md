---
title: '23.5: Archive citations for the five already-moved _bmad-output/ files'
type: 'fix'
created: '2026-09-19'
status: 'done'
baseline_revision: '66463b49860151f0a7ff4d0756cf679be95fe3a0'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      No automated, repeatable check encodes "no live doc cites the old
      _bmad-output/ root path for the five archived files" as a re-checkable
      command anywhere in the repo.
    evidence: |-
      Confirmed independently by two review layers: grepped pyforge-doctor's
      hygiene definitions and tests for DREAM-TRIAGE, archive/_bmad-output,
      stale/dead/broken-link/resolve-citation patterns and found no matching
      detector or meta-test. This story's own bound Verification command
      (pyforge-doctor-test) is the station's generic suite and does not
      exercise this invariant, so a future re-introduction of a stale
      old-root citation would ship green. Already tracked separately as
      Story 23.7 ("A new Doctor source flags leftover shelf occupancy"),
      currently backlog — not this story's problem to build.
    location: >-
      src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/
    severity: low
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** Five files (`CHARTER-ALIGNMENT-PLAN.md`, `DREAM-TRIAGE-2026-08-08.md`,
`FLEET-RUN-2026-07-30.md`, `FLEET-READINESS-2026-08-08.md`, `POLICY_COMPOSITION_README.md`)
already live under `archive/_bmad-output/` (moved 2026-09-14), but several live
navigational pointers across the repo still cite the old root path `_bmad-output/<file>.md`,
which 404s.

**Approach:** Rewrite each live pointer that cites one of the five old root paths to
`archive/_bmad-output/<file>.md`. Leave dated/historical prose (research snapshots, deferred-work
entries, provenance banners, already-archived docs) exactly as written — those describe a past
state truthfully and are not broken navigation.

## Boundaries & Constraints

**Always:**
- No live doc cites the old `_bmad-output/` root path for those five files.
- Only repoint pointers meant to be followed by a reader today (a "See X" / "for … see" style
  citation to a currently-existing document).

**Never:**
- Do not move the archived files back to the root.
- Do not rewrite historical/dated prose (research snapshots like `citation-map.md`, deferred-work
  ledger entries, the `archive/_bmad-output/*.md` "Archived … from `_bmad-output/…`" provenance
  banners, or already-archived docs like `archive/docs/reference/GuildHall_Fleet_Status.md`) —
  those correctly describe where the file was at the time, per the repo's historical-prose
  convention (only live pointers get repointed).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| old citation, live pointer | a station `planning-artifacts/specs/README.md` citing `_bmad-output/DREAM-TRIAGE-2026-08-08.md` | rewritten to `archive/_bmad-output/DREAM-TRIAGE-2026-08-08.md` | n/a |
| dated research snapshot | `citation-map.md` recording where a string appeared as of 2026-08-02 | left unchanged (historical record) | n/a |
| already-archived doc | `archive/docs/reference/GuildHall_Fleet_Status.md` | left unchanged | n/a |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/README.md:65` -- live "See X for…" pointer citing `_bmad-output/DREAM-TRIAGE-2026-08-08.md`; in declared Surface (station `specs/README.md`).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/README.md:25` -- same pattern.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/README.md:22` -- same pattern ("Historical pointer:" label, but still a live navigational citation to a doc that exists today).
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/README.md:23` -- same pattern.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/README.md:17` -- same pattern.
- `docs/intake/README.md` -- in declared Surface; grepped, does not currently cite any of the five old root paths (its one `_bmad-output/` citation is a live `projects/pyforge-steward/...` path, unaffected). No change needed.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-genesis-installer-name-retirement/citation-map.md:85` -- **(corrected during review, see Review Triage Log)** this is a live navigational index ("ground truth for the eventual … rewrite (deferred …)"), not historical prose as originally classified below — cited `_bmad-output/CHARTER-ALIGNMENT-PLAN.md` at the old root; patched to `archive/_bmad-output/CHARTER-ALIGNMENT-PLAN.md`.
- `presentations/six-quarter-roadmap/project/github.md:22-23` -- **(corrected during review)** the "Screen map" table is a durable data-dependency declaration, not narration — added 2026-09-18 (after the 2026-09-14 archive move) already citing two of the five files at the old root; patched all four occurrences to `archive/_bmad-output/…`.
- Out of scope (verified, left alone, genuinely historical/provenance prose or not a path citation):
  `presentations/six-quarter-roadmap/project/PyForge Roadmap.dc.html:3370` (rendered deck footer —
  bare filenames with no `_bmad-output/` path prefix at all, so not an old-root citation; proper
  fix is a deck regen via the Claude Design MCP bridge, deferred/rejected per Review Triage Log),
  the two `deferred-work-ledger.md` hits (bare filename, no `_bmad-output/` prefix, dated findings),
  `archive/_bmad-output/*.md:3` (each file's own "Archived … from `_bmad-output/…`" banner —
  correct as written), `archive/docs/reference/GuildHall_Fleet_Status.md:303` (already archived),
  and this story's own governing Spec / `epics.md` entries (describing the fix, not a broken link).
- Exhaustive repo grep confirmed no other live citations exist for any of the five filenames
  (`grep -rn --exclude-dir=.git -E "_bmad-output/(CHARTER-ALIGNMENT-PLAN|DREAM-TRIAGE-2026-08-08|FLEET-RUN-2026-07-30|FLEET-READINESS-2026-08-08|POLICY_COMPOSITION_README)\.md" .`),
  and a second bare-filename pass (no path prefix) turned up only the historical/provenance hits
  above.

## Tasks & Acceptance

**Execution:**
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/README.md` -- repoint the `DREAM-TRIAGE-2026-08-08.md` citation to `archive/_bmad-output/DREAM-TRIAGE-2026-08-08.md` -- fixes a 404'd live pointer.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/README.md` -- same -- same.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/README.md` -- same -- same.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/README.md` -- same -- same.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/README.md` -- same -- same.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-genesis-installer-name-retirement/citation-map.md` -- (patch, review pass) repoint the `CHARTER-ALIGNMENT-PLAN.md` citation -- fixes a 404'd live index entry.
- `presentations/six-quarter-roadmap/project/github.md` -- (patch, review pass) repoint both `FLEET-READINESS-2026-08-08.md` and `DREAM-TRIAGE-2026-08-08.md` citations (both table rows) -- fixes 404'd live data-dependency declarations.

**Acceptance Criteria:**
- Given the five station `specs/README.md` files that cited `_bmad-output/DREAM-TRIAGE-2026-08-08.md`, when grepped for the old root path, then zero matches remain.
- Given `docs/intake/README.md`, when grepped for any of the five old root paths, then zero matches (already true, unchanged).
- Given the historical/provenance files identified above, when re-grepped after this change, then their old-path citations are unchanged (proving nothing outside declared Surface was touched).

## Spec Change Log

_Empty — no bad_spec loopback occurred._

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 10 findings — high 0, medium 7, low 3, false 0, maybe-false 0
- findings:
  - `[medium]` `[patch]` blind-hunter: `presentations/six-quarter-roadmap/project/github.md` "Screen map" table still cites old-root `` `_bmad-output/FLEET-READINESS-2026-08-08.md` `` and `` `_bmad-output/DREAM-TRIAGE-2026-08-08.md` `` — verified true by re-reading the file; the Code Map's earlier classification of this file as "historical/dated" was wrong (it's a durable data-dependency table, not narration). Grouped with the two rows below; fixed by rewriting both citations to their `archive/_bmad-output/…` equivalents.
  - `[medium]` `[patch]` blind-hunter: the gap is fresh drift, not pre-existing — `git log --follow` shows `github.md` was added 2026-09-18, four days after the 2026-09-14 archive move, so the stale citation was introduced after the move, not inherited from before it. Verified true; same group as above.
  - `[low]` `[reject]` blind-hunter: the fix as first submitted only demonstrated a sweep for `DREAM-TRIAGE-2026-08-08.md`, not the other four files — true of the pre-patch diff, but a repo-wide grep after the patch below confirms full coverage for all five filenames, so nothing further to act on once the patch group lands.
  - `[low]` `[reject]` blind-hunter: the governing Spec's declared `Surface` field (`docs/intake/README.md`; station `specs/README.md` files) doesn't match reality — `docs/intake/README.md` was a no-op inclusion and `github.md` (which did need a fix) wasn't named. Real observation, but its only remedy is editing the governing planning-artifacts Spec, which is out of this build's actionable diff (reject any finding whose fix is to edit the spec); the substantive gap it points at is already closed by the patch group above.
  - `[low]` `[reject]` blind-hunter: the rendered deck output `presentations/six-quarter-roadmap/project/PyForge Roadmap.dc.html:3370` echoes stale bare filenames (`DREAM-TRIAGE-2026-08-08.md`, `FLEET-READINESS-2026-08-08.md`) in its "Source:" footer — verified true, but these are bare filename mentions with no `_bmad-output/` path prefix at all, so they don't violate the stated Always-rule ("no live doc cites the old `_bmad-output/` root path"); the correct remedy is a deck regen via the Claude Design MCP bridge (`docs/how-to/presentation-deck.md`), not a direct hand-edit of a generated prototype — rejected as unlikely-to-be-encountered cosmetic drift whose proper fix is more than a direct correction.
  - `[medium]` `[patch]` verification-gap: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-genesis-installer-name-retirement/citation-map.md:85` still cites old-root `` `_bmad-output/CHARTER-ALIGNMENT-PLAN.md` `` — arrives pre-verified per the layer's evidence rules; the Code Map's classification of this file as a "dated research snapshot" (therefore exempt) was wrong — its own header states it is "ground truth for the eventual … rewrite (deferred …)," i.e. a live index meant for future navigation, not narration. Fixed by rewriting to `archive/_bmad-output/CHARTER-ALIGNMENT-PLAN.md`.
  - `[medium]` `[patch]` verification-gap: `presentations/six-quarter-roadmap/project/github.md:22-23` still cites old-root `FLEET-READINESS-2026-08-08.md`/`DREAM-TRIAGE-2026-08-08.md` — arrives pre-verified; same group and fix as the blind-hunter rows above.
  - `[medium]` `[patch]` intent-alignment: independently names `citation-map.md:85` as a divergence between the intent's repo-wide "no live doc" invariant and the diff's narrower surface — verified true; same group as the verification-gap `citation-map.md` row.
  - `[medium]` `[patch]` intent-alignment: independently names `github.md:22-23` as a divergence — verified true; same group as the `github.md` rows above.
  - `[low]` `[defer]` intent-alignment: no automated, repeatable check anywhere in the repo encodes the acceptance criterion ("no live doc cites the old root path for these five files") as a re-checkable command — verified true (also independently confirmed by the verification-gap layer's search of `pyforge-doctor`'s hygiene definitions and tests). Pre-existing gap, not caused by this story, and already tracked separately: Story 23.7 ("A new Doctor source flags leftover shelf occupancy").

  (Edge Case Hunter reported zero findings.)

## Design Notes

_Straightforward — no design rationale needed beyond the patch group above._

## Verification

**Commands:**
- `grep -rnP --exclude-dir=.git --exclude-dir=archive '(?<!archive/)_bmad-output/(CHARTER-ALIGNMENT-PLAN|DREAM-TRIAGE-2026-08-08|FLEET-RUN-2026-07-30|FLEET-READINESS-2026-08-08|POLICY_COMPOSITION_README)\.md' .` -- expected: only the two known non-pointer hits (this story's own `epics.md` Story 23.5 entry and the governing Spec's I/O-matrix example row, both describing the fix rather than citing it as navigation) — no other output. Broadened repo-wide during the review pass (see Review Triage Log); the original version of this row was scoped only to `_bmad-output/projects/*/planning-artifacts/specs/README.md docs/intake/README.md`, which is why the review caught two live pointers outside that scope.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- expected: pass (the station's `verify_commands` per the governing Spec's Verification section).

## Binding

Parent Spec capability: `spec-docs-shelf-alignment CAP-5`.
Surface: docs/intake/README.md; station planning-artifacts/specs/README.md files that still cite the old root paths..
Ledger key: `23-5-archive-citations-for-the-five-already-moved-_bmad-output-files`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-5-archive-citations-for-the-five-already-moved-_bmad-output-files.md`.

## Auto Run Result

Status: done

**Summary:** Repointed every live citation of the five files archived from `_bmad-output/` to
`archive/_bmad-output/` (moved 2026-09-14) that still used the old root path. Initial pass covered
the five station `specs/README.md` files; the review pass caught two more live pointers the initial
sweep missed and patched them in the same run.

**Files changed:**
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/README.md` -- repointed `DREAM-TRIAGE-2026-08-08.md` citation.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/README.md` -- same.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/README.md` -- same.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/README.md` -- same.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/README.md` -- same.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-genesis-installer-name-retirement/citation-map.md` -- (review-pass patch) repointed `CHARTER-ALIGNMENT-PLAN.md` citation.
- `presentations/six-quarter-roadmap/project/github.md` -- (review-pass patch) repointed both `FLEET-READINESS-2026-08-08.md` and `DREAM-TRIAGE-2026-08-08.md` citations (both table rows, 4 occurrences).

**Review findings breakdown** (10 total; see Review Triage Log for full detail):
- Patched (7 rows / 2 grouped entries, both `medium`): the `citation-map.md` gap and the `github.md` gap, each independently flagged by 2-3 of the 4 review layers.
- Rejected (3, all `low`): "no evidence of exhaustive sweep" (resolved by the patch itself), the governing Spec's `Surface` field not matching reality (fix would require editing the spec, out of this build's scope), and the rendered `.dc.html` deck footer echoing stale bare filenames (not an old-root path citation at all, and the proper fix is a Claude Design MCP-bridge regen, not a hand-edit).
- Deferred (1, `low`): no automated/repeatable detector encodes this invariant anywhere in the repo — pre-existing, already tracked as Story 23.7.

**Follow-up review recommendation:** `false`. Two `medium` entries were patched (which would default this to `true`), but the follow-up review's purpose — catching further missed instances — was already discharged in this same pass: the Verification grep was broadened from a narrow, pre-review scope to a repo-wide, all-five-filenames, `archive/`-excluded sweep, re-run clean after the patch (only the story's own two self-referential text mentions remain, both non-navigational). No further unverified risk can be named.

**Verification performed:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`: 1785 passed, 1 skipped, exit 0 (both before and after the review-pass patch).
- Repo-wide `grep -rnP --exclude-dir=.git --exclude-dir=archive '(?<!archive/)_bmad-output/(CHARTER-ALIGNMENT-PLAN|DREAM-TRIAGE-2026-08-08|FLEET-RUN-2026-07-30|FLEET-READINESS-2026-08-08|POLICY_COMPOSITION_README)\.md' .`: only the two known non-pointer hits remain (this story's own `epics.md` entry and the governing Spec's I/O-matrix example).
- `pixi run -e pyforge-guild spec-surface-check`: clean — none of the seven touched files sit in any Spec's declared surface, so no memlog/stamp reconcile was needed.
- `pixi run -e pyforge-guild detectors-ci`: 32/32 pass.
- Manual read-back of every touched line in all 7 files, confirming only the target substring changed on each line.

**Residual risks:** none identified. The two review-pass patches were independently flagged by 3 of the 4 review layers and are straightforward text substitutions matching the pattern already established by the 5 initial-pass edits.
