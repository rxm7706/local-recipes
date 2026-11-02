---
title: '25.2: The estate catalog writes and checks byte-stably'
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-24-1-the-bmad-estate-catalog-is-generated-not-written.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-24-2-the-catalog-cannot-drift-silently.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-25-1-the-estate-catalog-skips-skill-directories-git-ignores.md
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_catalog_bmad_estate.py
  - docs/reference/bmad-estate-llms-full.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** At `03a7aff5d9` the estate catalog (`src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py`)
has two defects. Each makes the committed file read differently depending on how or when it was written.

- **`pipeline-truth` carries a digest no offline check can re-derive (cluster SCR-7).** `Estate.section_facts()`
  (`catalog.py`:212) includes `pipeline-truth`, so `digests()` records a digest for it. Without `--pipeline-truth`
  that digest is `sha256('{}')`, the committed `44136fa355b3` (`docs/reference/bmad-estate-llms-full.md`:24). So any
  `--check --pipeline-truth` reds a clean tree, and a `--write --pipeline-truth` would red every later bare
  `bmad-estate-check` in `detectors-ci`. The section is optional input by CAP-32's own text, and an offline check
  cannot re-derive it.
- **Every write re-stamps today's date (cluster SCR-8).** `render()` stamps `date.today()` (`catalog.py`:670, :685),
  and `write()` (:855-859) never reuses the committed date. Every write on a new day therefore gives a date-only diff,
  even when no source moved. Commit `9dff064f01` (steward 117.5's checkpoint) carried one. `--check` stays green
  because prose is exempt, so the damage is churn: a date-only diff from `steward estate reconcile` and
  `docs_bmad_estate.py`, a fired steward station lane, and line-13 conflicts between parallel PRs. This also makes
  Story 25.1's criterion ("on a clean checkout `--write` changes no byte") false on every new calendar day. The
  severity was contested and settled at Major.

The check's completeness is already sound and needs no clause. A section missing from the file reds, because
`check()` loops over the fresh digests (`catalog.py`:873-877). The SCR-M-C3 skeptic's "dropped section passes" does
not hold.

EGM audit 2026-11-01 findings carried: SCR-M-D3, SCR-D-C1 (clusters SCR-7, SCR-8). Research:
`_bmad-output/projects/pyforge-scribe/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**

1. `digests()` skips the `pipeline-truth` section. The section still renders, but no digest line records it. Adjust
   `SECTION_SOURCES`, or the assertion at `test_catalog_bmad_estate.py`:272 that the recorded digests equal
   `SECTION_SOURCES`, so the two agree.
2. `write()` gains `today: date | None = None`. It parses the committed `Generated:` date and renders with it. When
   the bytes are identical it leaves the file untouched. Otherwise it renders with `today` (default `date.today()`).
   This also covers a template-prose change: new bytes re-stamp the date.
3. Add tests to `src/shared/packages/pyforge-scribe/tests/unit/test_catalog_bmad_estate.py`:
   - a write with `--pipeline-truth`, then a bare check, exits 0;
   - a bare write, then `--check --pipeline-truth`, exits 0;
   - two writes with different `today` values and no source moved give identical bytes;
   - a moved source re-stamps the date.
4. Regenerate `docs/reference/bmad-estate-llms-full.md` with
   `pixi run -e pyforge-guild scribe catalog bmad-estate --write`, never by hand. Confirm `bmad-estate-check` exits 0.
5. Do not reword Story 25.1's criterion in the done epic. The deviation note goes in this story's
   `spec-pyforge-scribe` memlog event.

Ledger key: `25-2-the-estate-catalog-writes-and-checks-byte-stably`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-scribe` CAP-32: `--check` exits 0 on `main`; steward's `pipeline-truth` JSON is an optional input,
  never required; the catalog is generated, never hand-written. This story makes the check agree across invocations
  and the write byte-stable. No new CAP.
- `spec-feature-flag-governance` Q1: a `fix` needs no flag. CAP-32's kill switch `pyforge.scribe.bmad_estate_catalog`
  (Story 29.1) is unchanged.

## Acceptance Criteria

- AC1: Given a catalog written with `--pipeline-truth <file>` When `scribe catalog bmad-estate --check` runs without it
  Then it exits 0.
- AC2: Given a catalog written without `--pipeline-truth` When `scribe catalog bmad-estate --check --pipeline-truth
  <file>` runs Then it exits 0.
- AC3: Given the rendered file When its digest block is read Then it has no `pipeline-truth` digest line, the section
  itself still renders, and the recorded digests equal the set the test asserts against `SECTION_SOURCES`.
- AC4: Given no source moved When `write()` runs twice with different `today` values Then the file's bytes are
  identical, and the second write leaves the file untouched.
- AC5: Given a moved source (or a template-prose change) When `write()` runs Then the file is re-rendered and its
  `Generated:` line carries `today`.
- AC6: Given a section removed from the file When `--check` runs Then it exits 1 naming the section, as today.
- AC7: Given this story lands When `pixi run -e pyforge-guild scribe catalog bmad-estate --write` and then
  `pixi run -e pyforge-guild bmad-estate-check` run Then the check exits 0, and `pixi run --frozen -e pyforge-scribe
  pyforge-scribe-test` exits 0.
- AC8: Given the AC1, AC2 or AC4 test When the change it pins is removed Then it fails (mutation).

## Boundaries & Constraints

**Always:**
- Keep the generator offline: no network call and no `pyforge.<station>` import.
- Keep the check's exit-code domain (0 / 1 / 2) and its prose exemption.
- Reconcile every Spec `spec-surface-check` names. `catalog.py` is co-governed by `spec-pyforge-scribe`,
  `spec-pyforge-core` (pyforge-marshal) and `spec-pyforge-unifying-strategy` (pyforge-steward). The test file is
  co-governed by scribe and unifying-strategy. Write the memlog entry on each first, then `git add`, then one scoped
  `--write-baseline --spec <project>/<spec>` per Spec. Each memlog touch cascades chain-currency in its station.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Never hand-edit `docs/reference/bmad-estate-llms-full.md`.
- Never reword Story 25.1's criterion in `epics.md`.
- Never add a completeness clause. The fresh-digest loop already reds a dropped section.
- Never change the catalog's sources or its other sections. Epic 25's byte-identical boundary holds after this
  story's one re-render, which drops the `pipeline-truth` digest line.
- Never hand-edit `SPEC.md` or `sprint-status-ledger.yaml`; never run a bare `spec_surface_check.py --write-baseline`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| write with truth, bare check | `--write --pipeline-truth f`, then `--check` | exit 0 | — |
| bare write, check with truth | `--write`, then `--check --pipeline-truth f` | exit 0 | — |
| no-op write on a new day | no source moved, `today` differs | bytes identical, file untouched | — |
| moved source | a manifest version moves | re-rendered, `Generated:` = `today` | — |
| missing section | a section deleted from the file | `--check` exit 1 naming it | — |
| unparsable committed date | no `Generated:` line | render with `today` | never raises |

</intent-contract>

## Binding

Parent: `spec-pyforge-scribe` CAP-32; a `fix`, so no new CAP; no FR.
Parent capability:
- `spec-pyforge-scribe` CAP-32 — every session reads one derived picture of the BMAD estate.
Dream: `docs/dreams/pyforge-scribe.md` (the 2026-09-29 entry and the 2026-09-30 Realization-log entry; the 2026-11-01
EGM audit residue).
Ledger key: `25-2-the-estate-catalog-writes-and-checks-byte-stably`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `fix` (`spec-feature-flag-governance` Q1).
EGM audit findings: SCR-M-D3, SCR-D-C1 (clusters SCR-7, SCR-8).
Surface: `src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py` (`digests()`, `write()`), `src/shared/packages/pyforge-scribe/tests/unit/test_catalog_bmad_estate.py`, `docs/reference/bmad-estate-llms-full.md` (re-rendered, never hand-edited).

## Epic excerpt

**Type:** fix • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-scribe CAP-32 (no FR); a fix, no new CAP.
See `epics.md` § Story 25.2 for the full Given / When / Then / And.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_catalog_bmad_estate.py`
  — expected: pass.
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-guild scribe catalog bmad-estate --write` — expected: exit 0; a second run the next day leaves
  `docs/reference/bmad-estate-llms-full.md` untouched.
- `pixi run -e pyforge-guild bmad-estate-check` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

**Manual checks:**
- `pixi run -e pyforge-steward pyforge steward suite pipeline-truth --json > <scratch>/pt.json`, then
  `pixi run -e pyforge-guild scribe catalog bmad-estate --check --pipeline-truth <scratch>/pt.json` — expected: exit 0.

## Spec Change Log

- 2026-11-01 — minted `backlog` from the EGM fleet audit (marshal Story 113.7; operator triage 2026-11-01).
- 2026-11-01 — implemented (EGM audit fix pass); `in-review`.

## Auto Run Result

Status: done (independent review passed 2026-11-01; see Review Triage Log)

**What changed**

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py`:
  - `Estate.section_facts()` no longer lists `pipeline-truth`, and `SECTION_SOURCES` drops its entry. So `digests()`
    records no digest for the optional section. Section 8 still renders, with the table when `--pipeline-truth` is
    passed and the "Not rendered" note when it is not. `check()` is unchanged: the fresh-digest loop still reds a
    dropped section (AC6).
  - `write()` gains `today: date | None = None`. It reads the target and parses its `> Generated: YYYY-MM-DD.` line
    (new `_GENERATED_RE` and `_generated_date()`). It renders with that date, and when the text is identical it returns
    without writing. Otherwise it renders with `today` (default `date.today()`) and writes atomically as before. A
    missing, unreadable or undated target, or a date that does not parse (for example `2026-13-45`), falls through to
    the `today` render and never raises.
  - The module docstring names both rules.
- `src/shared/packages/pyforge-scribe/tests/unit/test_catalog_bmad_estate.py`: the pipeline-truth JSON fixture moves
  into a `_truth_file()` helper that the existing stage-column test reuses. Seven new tests:
  - `test_25_2_ac1_written_with_pipeline_truth_checks_clean_without_it` (CLI)
  - `test_25_2_ac2_written_bare_checks_clean_with_pipeline_truth` (CLI)
  - `test_25_2_ac3_pipeline_truth_renders_but_records_no_digest`
  - `test_25_2_ac4_a_no_op_write_on_a_new_day_leaves_the_file_untouched` (identical bytes, same inode and `mtime_ns`)
  - `test_25_2_ac5_a_moved_source_or_a_prose_change_re_stamps_the_date`
  - `test_25_2_an_unparsable_committed_date_renders_with_today` (three cases)
  - `test_25_2_ac6_a_section_removed_from_the_file_reds_the_check` (CLI, exit 1 naming `harness` and its source)
- `docs/reference/bmad-estate-llms-full.md`: regenerated with `pixi run -e pyforge-guild scribe catalog bmad-estate
  --write`, not by hand. The diff is the dropped `pipeline-truth=44136fa355b3` digest line and `Generated: 2026-11-01`.
  Every other byte is unchanged (Epic 25's byte-identical boundary).
- Story 25.1's criterion in `epics.md` is not reworded. The deviation note is in the `spec-pyforge-scribe` memlog
  surface-reconcile event.

**Commands (exit codes)**

- Red first: the 25.2 tests against the unfixed `catalog.py` gave 8 failed and 1 passed. The pass was AC6, which is
  already true. Exit 1.
- `pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_catalog_bmad_estate.py`
  gave 24 passed. Exit 0.
- AC8 mutation, through a scratch pytest plugin with no tracked file touched:
  - Putting `pipeline-truth` back into `section_facts`/`SECTION_SOURCES` fails AC1, AC2 and AC3. Exit 1.
  - Making `_generated_date` always return `None` fails AC4. Exit 1.
- `pixi run -e pyforge-scribe-pg scribe-pg-up` exits 0. Then `pixi run --frozen -e pyforge-scribe pyforge-scribe-test`
  gives 460 passed and 12 skipped. Exit 0. `catalog.py` coverage is 93.1%, and no line of the new code is missed.
- Ruff, run from the package root in `-e pyforge-guild` over the two changed files: `ruff check` exits 0 and
  `ruff format --check` exits 0.
- `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.scribe` (the `lint-types` mypy slice for this package) exits 0.
- `pixi run -e pyforge-guild scribe catalog bmad-estate --write` exits 0. A second write, and a
  `catalog.write(root, today=date(2026, 11, 2))` next-day write, left the file's md5, inode and mtime unchanged.
- `pixi run -e pyforge-guild bmad-estate-check` exits 0.
- Manual check: `pixi run -e pyforge-steward pyforge steward suite pipeline-truth --json` exits 0, then
  `scribe catalog bmad-estate --check --pipeline-truth <scratch>/pt.json` exits 0.
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_bmad_estate_check.py tests/scripts/test_docs_bmad_estate.py`
  gave 13 passed. Exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` exits 0 before any stamp.

**Left to the session owner**

- Co-governor reconciles and the scoped stamps. Per this spec's Boundaries, `catalog.py` is co-governed by
  `spec-pyforge-core` (pyforge-marshal) and `spec-pyforge-unifying-strategy` (pyforge-steward), and the test file by
  `spec-pyforge-unifying-strategy`. Each one needs its memlog line, then `git add`, then one
  `--write-baseline --spec <project>/<spec>`. Only this station's `spec-pyforge-scribe` memlog was appended: one
  surface-reconcile event and one CAP-32 success event.
- The `pyforge-scribe-test` task description in `pixi.toml` mentions "later segments", but its `cmd` runs a single
  pytest segment. This was noted, not changed, because it is outside this story's surface.

## Review Triage Log

### 2026-11-01 — Independent review (reviewer: independent session) — PASS

Judged against this spec's ACs and Boundaries from `git diff HEAD` of `catalog.py`, `test_catalog_bmad_estate.py` and
`docs/reference/bmad-estate-llms-full.md`, not the implementer's summary. Every verdict read from the exit code.

- AC1 / AC2 — hold. `test_25_2_ac1_…` and `test_25_2_ac2_…` drive the CLI (`--write [--pipeline-truth]`, then
  `--check [--pipeline-truth]`), exit 0 each. Live: `pyforge steward suite pipeline-truth --json` exit 0, then
  `scribe catalog bmad-estate --check --pipeline-truth <scratch>/pt.json` exit 0.
- AC3 — holds. `section_facts()` and `SECTION_SOURCES` drop `pipeline-truth`; section 8 still renders;
  `test_25_2_ac3_…` asserts no digest line and recorded digests == `SECTION_SOURCES`.
- AC4 — holds. `test_25_2_ac4_…` asserts same bytes, inode and `mtime_ns`. Live: `catalog.write(root, output=<scratch
  copy of the committed file>, today=date(2026, 11, 2))` left bytes, inode and mtime unchanged (tracked file untouched).
- AC5 — holds. `test_25_2_ac5_…` covers a moved manifest version and a template-prose change, each re-stamped.
  The unparsable-date edge case is pinned (three ids) and never raises.
- AC6 — holds. `test_25_2_ac6_…`: a removed section digest reds `--check` (exit 1) naming `harness` and its source.
- AC7 — holds. `pixi run -e pyforge-guild bmad-estate-check` exit 0; the committed file's diff is exactly the dropped
  `pipeline-truth=44136fa355b3` line and `Generated: 2026-11-01` (no other byte). `pyforge-scribe-test` exit 0
  (460 passed, 12 skipped).
- AC8 — holds, re-observed via scratch pytest plugins (no tracked file touched): restoring `pipeline-truth` in
  `section_facts`/`SECTION_SOURCES` fails AC1, AC2, AC3 (exit 1); `_generated_date` → `None` fails AC4 (exit 1).
- Boundaries — held: offline generator, exit domain 0/1/2 and the prose exemption unchanged, no completeness clause,
  Story 25.1 not reworded (deviation note is in the memlog event), catalog regenerated not hand-edited.
- Callers: CLI `--write` goes through `catalog.write()`; `scripts/bmad_estate_check.py`, `scripts/docs_bmad_estate.py`
  and steward `estate_reconcile` shell the CLI unchanged; `realization_register_lib.py` imports only `read_pins`.
  `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_bmad_estate_check.py tests/scripts/test_docs_bmad_estate.py`
  exit 0 (13 passed).
- Lint/types: ruff check and format --check from the package dir over `src tests` exit 0 / 0; `mypy -p pyforge.scribe`
  (guild cache) exit 0. `except OSError, ValueError:` is PEP 758 form, valid on the py314 floor every scribe env runs.
- `pixi run -e pyforge-guild spec-surface-check` exit 0 (co-governor stamps are the session owner's).

Failures: none.
