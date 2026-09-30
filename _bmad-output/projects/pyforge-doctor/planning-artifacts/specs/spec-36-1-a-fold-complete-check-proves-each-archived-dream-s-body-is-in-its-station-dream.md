---
title: "36.1: A fold-complete check proves each archived Dream's body is in its station Dream"
type: 'feature'
created: '2026-09-29'
status: 'done'
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

### 2026-09-29 — Review pass
- verdicts: 38 findings — high 0, medium 0, low 26, false 12, maybe-false 0
- findings:
  - Blind Hunter
    - `[low]` `[reject]` Vacuous pass when an archived body has no paragraph over 80 characters — the contract FAILs only a missing long paragraph; a body with none has nothing to prove, and a fix adds a new finding kind for a case nobody has shown.
    - `[low]` `[reject]` Baseline is not self-policing (no stale-entry check, no prune, exact-string match) — the seventh entry is a path that arrives later by the contract's own design, so a stale-entry WARN would fire on day one; `chain-sprawl`'s prune is a separate script this story was not asked to mirror.
    - `[low]` `[patch]` "Reads nothing" AC weakly tested (spies on `_frontmatter_parse` only) — test now records every `Path.open` / `read_text` / `read_bytes` call and asserts the baselined file is never among them; a sanity test proves the recorder catches an unbaselined read.
    - `[false]` `[reject]` Exit code contradicts the I/O matrix (FAIL exits 2, matrix says 1) — Doctor's exit domain is {0, 2, 130} (`verdict.py` `_EXIT_FAIL = 2`), `scripts/detectors.py:327` folds it to rc 1 for `detectors-ci`, and the fix asked for edits the read-only contract; the difference is recorded in Design Notes *Exit codes*.
    - `[low]` `[patch]` `fold-complete-no-owner` conflates missing, unparseable and invalid-slug owners — message now reads "missing, unparseable, or not a station slug" and the slug check is `fullmatch`.
    - `[false]` `[reject]` OK summary hides failures, an absent archive dir is a silent OK, glob is non-recursive and lowercase — the summary counts only complete Dreams and every FAIL is its own finding; an absent `archive/docs/dreams/` means nothing is archived, so nothing is unproven; the contract names `archive/docs/dreams/*.md`.
    - `[low]` `[reject]` Matching is weaker than "a dated section" (whole-Dream substring, short paragraphs exempt, `#` lines inside code fences read as headings) — the whole-Dream substring and the 80-character floor are the contract's own rule; the fence case needs fence tracking (added branches) for a long `#` comment line nobody has shown.
    - `[low]` `[reject]` Live-tree tests are looser than their names (`<=`, WARN absence passes) — the WARN is meant to disappear once the last station folds, so pinning its presence would go stale by design; `<=` is the "only shrinks" property.
    - `[low]` `[patch]` Test gaps for branches the code adds — added a non-UTF-8 station Dream case (`fold-complete-no-station-dream`); banner-topped, CRLF, unclosed-fence and missing-directory bodies go through the reused chain reader, which has its own tests, and the mutation criterion was verified by a real mutation run (7 tests fail).
    - `[low]` `[reject]` `_gather_fold_complete` is long and constants sit mid-module — cosmetic; no caller or rule named that will break.
    - `[low]` `[patch]` Docs do not point at the new check or its WARNs — the how-to section now documents the `fold-complete-no-baseline` WARN, the unreadable-frontmatter tail and the new per-file checks; CHAIN-STANDARD §11 and `one-chain-station-ops.md` are the Guild's documents (Doctor relays, mints nothing there), left unedited.
    - `[low]` `[reject]` Countdown misses the legacy `docs/dreams/archive/` — the contract limits the WARN to `docs/dreams/*.md`, and the seventh baseline path is that file's arrival.
    - `[false]` `[reject]` Generated-page stamps stale — after the final edits `docs-currency-check` flags neither `docs/how-to/pixi-tasks.md` nor `docs/reference/detectors.md`; the `MAP.md` registry staleness renders identically from the baseline `map.yaml` and the current one, so it predates this story.
    - `[false]` `[reject]` No spec-surface stamp in the diff; memlog out of order — this run forbids `--write-baseline`, so both stamps the implementer made were reverted; the reconcile is the memlog entries naming every path, and `spec_surface_reconcile.py` and `spec-surface-check` exit 0; the `spec-pyforge-core` header `updated:` moved forward (21:20 to 22:49) and the 2026-09-30 entries above the new one are not this story's.
  - Edge Case Hunter
    - `[low]` `[patch]` Countdown WARN is dropped when no readable archived Dream remains but unreadable-frontmatter ones do — `_archived_in_live_tree` now returns nothing only when both counts are 0 and renders an empty per-station list as `none`; test added.
    - `[low]` `[reject]` Zero long paragraphs passes silently — same root and same reason as the Blind Hunter vacuous-pass row.
    - `[low]` `[reject]` `#` lines inside a code fence are dropped as headings — needs fence tracking for a rare long comment line; see the Blind Hunter matching row.
    - `[low]` `[patch]` `$` in `_OWNER_RE` matches before a trailing newline, so `owner: "mason\n"` gives a misleading FAIL naming a path with a newline — `fullmatch`, with a test for `"mason\n"` and `Mason`.
    - `[low]` `[reject]` Stale or `./`-prefixed baseline entries — same as the Blind Hunter baseline row.
    - `[low]` `[reject]` Nested or `.MD` files under the archive are never measured — the contract names `archive/docs/dreams/*.md`.
    - `[low]` `[reject]` A paragraph anywhere in the station Dream passes, not only in the dated section — the contract's rule is "a substring of the station Dream".
    - `[false]` `[reject]` Matrix says exit 1, code exits 2 — same as the Blind Hunter exit-code row.
    - `[low]` `[reject]` 34 glued-opener Dreams are excluded from the per-station counts (124 of 158) — a second parser is forbidden by the Always clause and the reader's glued-opener verdict is Story 28.1's; the WARN discloses the 34 and now stays alive while any remain.
  - Verification Gap Reviewer
    - `[low]` `[patch]` Per-station order in the countdown message not pinned (fixtures happened to sort the same by filename) — fixtures renamed so filename order is the reverse of station order.
    - `[low]` `[patch]` Per-owner station-Dream cache never exercised across two stations — two-owner tests added (both complete; and atlas's paragraph present only in the mason Dream FAILs naming `pyforge-atlas.md`).
    - `[low]` `[reject]` Countdown undercounts against the Code Map's 158 — same as the Edge Case Hunter glued-opener row.
    - `[false]` `[reject]` Exit-code mismatch not recorded — recorded in Design Notes *Exit codes* and both memlogs; same as the Blind Hunter row.
    - `[low]` `[reject]` A missing baseline blanks the whole run to one WARN — that is Story 25.1's shape (`chain-sprawl-no-baseline`), which the contract names, and cannot-evaluate is never a FAIL.
  - Intent Alignment Auditor
    - `[low]` `[patch]` No per-file OK line for a complete or baselined Dream although two criteria say "reports OK for that file" — `fold-complete-ok` and `fold-complete-baselined` findings added, each naming its path; the summary OK is kept.
    - `[false]` `[reject]` A heading line also ends the paragraph — for a well-formed Dream this is the contract's rule (heading lines left out) and it is what keeps a demoted-heading paste matching; a test covers it.
    - `[false]` `[reject]` Owner must match a slug the contract does not name — a value that is not a slug cannot name a station Dream; it FAILs like any unreadable owner.
    - `[low]` `[reject]` Glued-opener Dreams not attributed per station — same as the Edge Case Hunter row.
    - `[false]` `[reject]` Mutation criterion met only by inference — a real mutation run (`missing = []`) failed 5 tests before the patches and 7 after.
    - `[low]` `[patch]` Baselined-file read check observes only `_frontmatter_parse` — same root as the Blind Hunter "reads nothing" row; fixed there.
    - `[low]` `[reject]` No test invokes the pixi task or `detectors-ci` — both were run for this review (`fold-complete-check` exit 0; `detectors-ci` lists `fold-complete` as pass); the task is a one-line `python -m` wrapper whose dispatch is tested in-process.
    - `[false]` `[reject]` Exit 1 versus 2 — same as the Blind Hunter exit-code row.
    - `[false]` `[reject]` Code is in `one_chain.py`, not `chain.py` — recorded in Design Notes *Module correction*; the contract's stated shape is Story 25.1's, whose gatherer lives there.
    - `[false]` `[reject]` Extra files touched (`models.py`, report schema, docs) — registering a `Source` requires the enum member and the additive schema value, and the Code Map lists each.

## Auto Run Result

Status: done

**Summary.** Doctor gains a repo-scope source, `fold-complete`. For every `archive/docs/dreams/*.md` not in `docs/governance/fold-complete-baseline.json` it reads `owner:` with chain's `_frontmatter_parse`, splits the body with `_dream_body_after_frontmatter`, and FAILs naming the file and the count when a paragraph longer than 80 characters is not in `docs/dreams/pyforge-<owner>.md` (both whitespace-collapsed). An unreadable owner or a missing station Dream FAILs. One WARN counts the Dreams in `docs/dreams/` still reading `status: archived`, per station, and reports the ones with unreadable frontmatter beside it. It is read-only.

**Files changed.**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py` -- `gather_fold_complete`, `long_paragraphs`, `FOLD_COMPLETE_BASELINE_REL`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py`, `sources/__init__.py`, `sources/__main__.py`, `data/report-schema.json` -- `Source.FOLD_COMPLETE`, registry row (repo scope), dispatch row, additive schema enum value.
- `pixi.toml`, `scripts/detectors.py` -- `fold-complete-check` task and its `detectors-ci` row.
- `docs/governance/fold-complete-baseline.json` -- new; the seven non-fold paths, only shrinks.
- `docs/how-to/run-and-understand-detectors.md` (hand-written), `docs/how-to/pixi-tasks.md` and `docs/reference/detectors.md` (regenerated), `docs/map.yaml` (generated-page stamps) -- documentation.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fold_complete.py` (new, 44 tests) and the three pinned-map tests `test_models.py`, `test_sources_dispatch.py`, `tests/meta/test_source_independence.py`.
- The `.memlog.md` of `spec-pyforge-doctor` and of `spec-pyforge-core` (the co-governor `spec-surface` names) each name every governed path this story changed.

**Review findings.** 38 from four layers: high 0, medium 0, low 26, false 12. Patches applied: 8 entries, all low (owner `fullmatch` and message; countdown WARN kept while only unreadable-frontmatter Dreams remain; per-file `fold-complete-ok` / `fold-complete-baselined` findings; a stronger never-read test; a non-UTF-8 station-Dream test; a countdown-order test; two-owner tests; the how-to sentences). Deferred: none. Rejected: every other row, each with its reason in the log above.

**Follow-up review recommended:** false. No high patch and fewer than two medium patches; nothing unverified is named.

**Verification** (each verdict read from its exit code, never a pipe):
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- exit 0, 3053 passed, 1 skipped, after the patches.
- `pixi run -e pyforge-guild fold-complete-check` -- exit 0; per-file OK for the six baselined Dreams, the summary OK, and the archived-in-live-tree WARN (124 by station: atlas 12, doctor 14, herald 10, marshal 54, mason 12, scribe 16, steward 2, warden 4; 34 more with unreadable frontmatter).
- Mutation: replacing the paragraph comparison with `missing = []` fails 7 tests; the file was restored and is identical to HEAD.
- `pixi run -e pyforge-guild lint-types` -- exit 0.
- `python scripts/spec_surface_reconcile.py` -- exit 0; `pixi run -e pyforge-guild spec-surface-check` -- exit 0; `story-status-check` and `chain-completeness-check` -- exit 0.
- `pixi run -e pyforge-guild detectors-ci` -- exit 1, on one row only: `bmad_estate_check` (`skills` section drifted). It compares `.claude/skills/*/SKILL.md` with `docs/reference/bmad-estate-llms-full.md`; this story touches neither, so it is not from this diff. `fold-complete` passes in that run.

**Deviations and residual risks.**
- The Tasks section step 7 says to stamp with `--write-baseline --spec`. This run's instruction forbids `--write-baseline`, so the implementer's stamps (two passes) were reverted and `scripts/.spec-surface-baseline.json` is byte-identical to `baseline_revision`. The reconcile is the memlog entries; a scoped stamp remains for whoever lands this outside the run. Sibling stories drafted from the same template carry the same step.
- A FAIL exits 2 from the source CLI (Doctor's domain), 1 through `detectors-ci`; the matrix's "exit 1" is the aggregator's. See Design Notes *Exit codes*.
- 34 of the 158 Dreams reading `status: archived` in `docs/dreams/` have a glued `---title:` opener the reader cannot parse, so they are counted in the WARN's tail, not per station.
- Pre-existing and not touched: `docs-currency` warns that the `docs/MAP.md` registry, `docs/reference/skills-catalog.md` and `docs/reference/station-cheat-sheet.md` are stale (the `MAP.md` render is identical from the baseline `map.yaml`).
- The check proves presence of each long paragraph anywhere in the station Dream, not that it sits in a dated section, and exempts paragraphs of 80 characters or fewer; that is the contract's rule.
