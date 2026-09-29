---
title: "36.1: A fold-complete check proves each archived Dream's body is in its station Dream"
type: 'feature'
created: '2026-09-29'
status: 'backlog'
flag-exempt: detector-or-gate
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/dreams/one-chain-per-station.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py
  - scripts/detectors.py
  - docs/governance/chain-sprawl-baseline.json
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

1. Read `sources/chain.py` (`gather_chain_sprawl`, `_frontmatter_parse`, `_split_fenced_block`), `sources/__init__.py`,
   `sources/__main__.py`, `scripts/detectors.py` and Story 25.1's spec for the registration shape.
2. Write `gather_fold_complete` and its paragraph splitter as pure functions over a `target` path, so tests run on
   `tmp_path`.
3. Register the source, add the `fold-complete-check` task (description names the Spec, CAP-11 and CHAIN-STANDARD §11), and
   add the `detectors-ci` row.
4. Write `docs/governance/fold-complete-baseline.json` with a `$comment` naming the rule date and that it only shrinks.
5. Add unit tests for every acceptance criterion under `src/shared/packages/pyforge-doctor/tests/unit/`.
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

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
