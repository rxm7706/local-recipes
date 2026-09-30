---
title: "36.1: A fold-complete check proves each archived Dream's body is in its station Dream"
type: 'feature'
created: '2026-09-29'
status: 'in-review'
baseline_revision: 'a468651c83a9f3c97b5ec4c7cbaf872fa95a16ce'
flag-exempt: detector-or-gate
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/dreams/one-chain-per-station.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py
  - scripts/detectors.py
  - docs/governance/chain-sprawl-baseline.json
warnings: [oversized]
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-one-chain-per-station` CAP-11 (operator ruling 2026-09-29) moves every archived Dream out of
`docs/dreams/` into `archive/docs/dreams/`, but only once its whole body sits, verbatim, in a dated section of its station
Dream. Nothing checks that today, and the gap is real. Measured on `main` at `3e047430cf`, finding each archived
satellite's long paragraphs in its station Dream:

- steward: 33 of 34 complete (steward's 2026-09-17 fold pasted bodies in).
- marshal: 22 complete, 10 partial, 22 with nothing.
- scribe, doctor, mason, herald and warden: none (those folds only added a `Consolidated into` banner).
- 14 archived Dreams, mostly atlas, carry no banner at all.

A fold PR that moves a file without this check can drop a Dream's only copy of its content out of the live tree.

**Approach:** add a Doctor source, `fold-complete`, in Story 25.1's shape (`chain-sprawl`):

- `sources/chain.py` gains `gather_fold_complete(target)`, registered as `Source.FOLD_COMPLETE` (scope `repo`) in
  `sources/__init__.py`, with a dispatcher row in `sources/__main__.py`, a `fold-complete-check` task in `pixi.toml`, and a
  row in `scripts/detectors.py`'s `detectors-ci` list.
- For each `archive/docs/dreams/*.md` not named in `docs/governance/fold-complete-baseline.json`:
  - read `owner:` with the chain module's frontmatter reader (Story 28.1's line-anchored reader);
  - the station Dream is `docs/dreams/pyforge-<owner>.md`;
  - split the archived body into paragraphs: blank-line separated, frontmatter and heading lines left out, whitespace
    runs collapsed, kept only when longer than 80 characters;
  - FAIL, naming the file and the count, when any such paragraph is not a substring of the station Dream (also
    whitespace-collapsed); OK otherwise. A Dream whose owner cannot be read, or whose station Dream does not exist, FAILs.
- Every `docs/dreams/*.md` whose frontmatter reads `status: archived` counts toward **one** WARN, naming the count per
  station. That is the migration's countdown. It is never a FAIL here; a later story can promote it once the last station
  folds.
- The baseline file lists the seven paths expected under `archive/docs/dreams/` that are not folds of a station Dream: the
  six already there (`deckcraft`, `design-code-bridge`, `herald-pitch-deck-family-expansion`, `modernist-identity`,
  `pyforge-genesis`, `video-scripts`) and `pyforge-unifying-strategy-2026-08-23-topology.md`, the historical split of a live
  Dream, which moves from `docs/dreams/archive/`. It only ever shrinks, like `chain-sprawl-baseline.json`.

Heading depth does not matter, because heading lines are left out: a satellite whose headings were demoted one level when
pasted still matches.

Ledger key: `36-1-a-fold-complete-check-proves-each-archived-dream-s-body-is-in-its-station-dream`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-one-chain-per-station` CAP-11 (the Guild's; Doctor mints no CAP and no FR, the Epic 24/25/32/34 relay);
  CHAIN-STANDARD §7 item 4 and §11. AD-2 (Doctor reads; it never writes).
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: detector-or-gate`. A flag-OFF check would be a silent green.
- Siblings: Story 36.2 (sibling-drift), marshal Story 75.1 (the console), herald Story 33.1 (the deck facts). All four land
  before the first station fold PR moves a file.

## Acceptance Criteria

- Given a fixture `archive/docs/dreams/foo.md` with `owner: mason` and a `docs/dreams/pyforge-mason.md` holding every one of its long paragraphs When `fold-complete-check` runs Then it reports OK for `foo.md`
- Given the same fixture with one long paragraph missing from the station Dream When it runs Then it FAILs naming `foo.md` and `1 paragraph missing`
- Given the station Dream holds the satellite's paragraphs under headings one level deeper than the satellite's When it runs Then it reports OK
- Given an archived Dream with no readable `owner:` (missing frontmatter, or a glued `---title:` opener) When it runs Then it FAILs naming the file
- Given `owner: atlas` and no `docs/dreams/pyforge-atlas.md` in the fixture When it runs Then it FAILs naming the missing station Dream
- Given two files in `docs/dreams/` read `status: archived`, one owned by doctor and one by herald When it runs Then it reports one WARN naming `doctor 1, herald 1`, and no FAIL
- Given a file listed in `fold-complete-baseline.json` When it runs Then it reports OK for that file and reads nothing from it
- Given today's `main` When `pixi run -e pyforge-guild fold-complete-check` runs Then it reports the archived-in-live-tree WARN and exits 0
- Given the paragraph comparison is removed When the missing-paragraph test runs Then it fails (mutation)

## Tasks

1. Read `sources/one_chain.py` (`gather_chain_sprawl`), `sources/chain.py` (`_frontmatter_parse`,
   `_dream_body_after_frontmatter`), `models.py`, `sources/__init__.py`, `sources/__main__.py`, `scripts/detectors.py` and
   Story 25.1's spec for the registration shape. (Done at planning; Code Map above.)
2. `sources/one_chain.py` -- write `gather_fold_complete` and its paragraph splitter as pure functions over a `target`
   path, so tests run on `tmp_path`.
3. `models.py`, `sources/__init__.py`, `sources/__main__.py`, `data/report-schema.json` -- register `Source.FOLD_COMPLETE`.
   `pixi.toml` -- add the `fold-complete-check` task (description names the Spec, CAP-11 and CHAIN-STANDARD §11).
   `scripts/detectors.py` -- add the `detectors-ci` row. `docs/how-to/pixi-tasks.md` and
   `docs/how-to/run-and-understand-detectors.md` -- document it.
4. Write `docs/governance/fold-complete-baseline.json` with a `$comment` naming the rule date and that it only shrinks.
5. Add unit tests for every acceptance criterion and every I/O-matrix row in
   `tests/unit/test_sources_one_chain_fold_complete.py`; extend the three pinned-map tests named in the Code Map.
6. Run `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` and `pixi run -e pyforge-guild fold-complete-check`, and read
   each exit code.
7. Reconcile every Spec `spec-surface-check` names (`spec-pyforge-doctor`, and `spec-pyforge-core` as co-governor of
   station `src/`): memlog first, `git add`, then a scoped `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Read only. The check moves no file and edits no Dream.
- Use the chain module's existing frontmatter reader; never a second parser.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not FAIL on archived Dreams still in `docs/dreams/`: that is the WARN countdown.
- Do not import any station's internals.
- Do not move, edit or fold any Dream in this story.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| complete fold | every long paragraph in the station Dream | OK | exit 0 |
| incomplete fold | one paragraph missing | FAIL naming file and count | exit 1 |
| demoted headings | `##` became `###` | OK | exit 0 |
| unreadable owner | no or glued frontmatter | FAIL naming file | exit 1 |
| missing station Dream | `docs/dreams/pyforge-<owner>.md` absent | FAIL naming it | exit 1 |
| archived still live | `status: archived` in `docs/dreams/` | one WARN, counts per station | exit 0 |
| baseline file | listed in the baseline | OK, not read | exit 0 |

</intent-contract>

## Code Map

Paths are under `src/shared/packages/pyforge-doctor/` unless rooted. Planning found the intent contract's file list
partly off; the corrections are in Design Notes.

- `src/pyforge/doctor/sources/one_chain.py` -- home of `gather_chain_sprawl` / `gather_fr_without_cap` (Story 25.1 shape:
  public `gather_*` wraps `_gather_*` in `degrade_on_exception`); already imports `_frontmatter_parse` from `.chain`;
  reuse `_read_json`. `gather_fold_complete` lands here, with `FOLD_COMPLETE_BASELINE_REL` in `__all__`.
- `src/pyforge/doctor/sources/chain.py` -- read-only reuse: `_frontmatter_parse(path) -> (fields, unparseable)` (glued
  `---title:` opener returns `({}, True)`), `_dream_body_after_frontmatter(text)` (body after the line-anchored fence).
- `src/pyforge/doctor/models.py` (~l.329) -- `Source` enum: add `FOLD_COMPLETE = "fold-complete"` beside `CHAIN_SPRAWL`.
- `src/pyforge/doctor/sources/__init__.py` (~l.487) -- `REGISTRY`: add a `SourceRegistration(scope="repo",
  subject_station="fleet", owning_station="doctor")` row after `FR_WITHOUT_CAP`.
- `src/pyforge/doctor/sources/__main__.py` (~l.134) -- `DISPATCH`: add `Source.FOLD_COMPLETE.value:
  one_chain.gather_fold_complete`.
- `src/pyforge/doctor/data/report-schema.json` (~l.92) -- frozen schema, additive only: add `"fold-complete"` to the
  `source` enum.
- `pixi.toml` (~l.1385) -- `[feature.guild-tasks.tasks.chain-sprawl-check]` is the task template; add
  `fold-complete-check` (`python -m pyforge.doctor.sources fold-complete`).
- `scripts/detectors.py` (~l.258) -- `detectors-ci` tuple: add `("fold-complete", "fold-complete-check")`.
- `docs/governance/fold-complete-baseline.json` -- new; seven paths, `$comment` naming the rule date and "only shrinks".
- `docs/how-to/pixi-tasks.md` (~l.79), `docs/how-to/run-and-understand-detectors.md` (~l.70) -- the two docs that list
  `chain-sprawl-check`; add a `fold-complete-check` row / section.
- `tests/unit/test_models.py` (~l.213), `tests/unit/test_sources_dispatch.py` (~l.78),
  `tests/meta/test_source_independence.py` (~l.135) -- each pins the Source / DISPATCH / module map; add the new member.
- `tests/unit/test_sources_one_chain.py` -- fixture style (`_roster`, `_dream`, `tmp_path` trees, a live-tree leg); the
  new tests go in `tests/unit/test_sources_one_chain_fold_complete.py` beside it.
- Live tree today (read-only evidence): `archive/docs/dreams/` holds exactly the six baseline files; 158
  `docs/dreams/*.md` read `status: archived`; `docs/dreams/archive/` holds the seventh baseline path.

## Binding

Parent capability: `spec-one-chain-per-station` CAP-11 (Guild relay; no doctor CAP or FR).
Dream: `docs/dreams/one-chain-per-station.md` → § *2026-09-29 — One archive home*.
Ledger key: `36-1-a-fold-complete-check-proves-each-archived-dream-s-body-is-in-its-station-dream`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: `flag-exempt: detector-or-gate` (a detector; flagging it OFF would be a silent green).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild fold-complete-check` — expected: exit 0 on `main`, with one WARN counting the archived Dreams
  still in `docs/dreams/`.
- `pixi run -e pyforge-guild detectors-ci` — expected: the new source appears and adds no FAIL.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Spec Change Log

<!-- Append-only. Empty until the first bad_spec loopback. -->

## Design Notes

- **Module correction.** The intent contract says `sources/chain.py` gains the gatherer and that `gather_chain_sprawl` lives
  there. It lives in `sources/one_chain.py`, which is the one-chain family module (`chain-sprawl`, `fr-without-cap`) and
  already imports `_frontmatter_parse` from `.chain`; `Source` is declared in `models.py`, not `sources/__init__.py`. The
  contract's intent is "Story 25.1's shape", so the gatherer goes to `one_chain.py` and reuses the `.chain` reader. Nothing
  observable changes: the CLI name, task name and findings are the contract's (the exit code is the one difference; see
  *Exit codes*). `chain.py` (5.5k lines) is not grown.
- **Exit codes.** The I/O matrix says a FAIL "exit 1". Doctor's own exit domain is {0, 2, 130} (`verdict.py`,
  `_EXIT_FAIL = 2`), so `python -m pyforge.doctor.sources fold-complete` exits 2 on a FAIL and 0 otherwise, and a test
  pins that. `scripts/detectors.py` folds any non-zero verdict to its own rc 1, so the `detectors-ci` row reads as the
  matrix says. The contract block is read-only; this note is where the difference is recorded.
- **Paragraph rule.** Body via `_dream_body_after_frontmatter`; a heading line (`#{1,6}` then a space) is dropped and also
  ends the paragraph, exactly as a blank line does. That keeps a paragraph that abuts a heading with no blank line
  matching the station Dream, where the same text sits beside a differently-demoted heading. Whitespace runs collapse
  to one space on both sides; only paragraphs longer than 80 characters count; the station Dream is
  collapsed whole and searched with `in`.
- **Findings.** One FAIL per failing archived Dream (check `fold-complete-incomplete`, `-no-owner`, `-no-station-dream`);
  one OK per complete Dream (`fold-complete-ok`) and one per baselined Dream (`fold-complete-baselined`), each naming its
  path, mirroring `chain-sprawl-exempt`, so "reports OK for `foo.md`" is a line that names `foo.md`; a `fold-complete` OK
  summary carries the counts; one WARN (`fold-complete-archived-in-live-tree`) carries the per-station count, sorted by
  station name. (Planning first wrote a single summary OK; review pass 1 found that under-read the two "reports OK for
  that file" criteria, and the code was patched to match them.)
- **Countdown and unreadable frontmatter.** A `docs/dreams/*.md` whose frontmatter the reader marks unparseable (a glued
  `---title:` opener, 34 today) has no readable `status:` or `owner:`, and the Always clause forbids a second parser, so
  it cannot be attributed to a station. The WARN reports that count beside the per-station counts and stays alive while
  any such file remains, so the countdown never reads finished early.
- **Baseline.** A listed path is skipped before any read (the "reads nothing" AC): its file is never opened. A missing
  or unreadable baseline file is a WARN `fold-complete-no-baseline`, like `chain-sprawl-no-baseline`, never a crash.
- **No banner allowance.** CHAIN-STANDARD §7 item 4 says a moved Dream carries no `Consolidated into` banner, so a
  leftover banner line is correctly a missing paragraph.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
