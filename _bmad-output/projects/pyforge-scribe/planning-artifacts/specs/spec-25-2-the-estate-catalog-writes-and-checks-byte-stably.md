---
title: '25.2: The estate catalog writes and checks byte-stably'
type: 'fix'
created: '2026-11-01'
status: 'backlog'
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

## Auto Run Result

Status: backlog
