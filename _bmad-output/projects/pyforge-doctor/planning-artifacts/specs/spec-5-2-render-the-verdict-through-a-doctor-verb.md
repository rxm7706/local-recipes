---
title: "Story 5-2: Render the verdict through a `doctor` verb"
type: "feature"
created: "2026-08-08"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-09"
---

<!-- RECOVERED 2026-08-09 Tier 3 (epics.md-derived Intent + ACs). No session transcript,
     bmad-loop worktree snapshot, or Tier-3 draft survived — this story landed via hand-driven
     PR #325, not a bmad-loop run, so no spec was ever drafted to promote. Regenerated from
     epics.md (which carries an unusually complete Outcome section for this story) plus its
     merged-PR Delivery Record, per CLAUDE.md's recovery priority order. -->

## Intent

As the operator, I want `doctor` to actually **show** me the Marshal-durability verdict, so
that the check is something I see, not something that merely exists. FR-14; AD-11.

**Why this is its own story, not part of 5.1.** `sources/marshal.py` shipped with **no
caller** — `__main__.py:47` imported `atlas` and `warden`, not `marshal`. Marking 5.1 done
while the source was unreachable would be the "merged, marked done, never became the
runtime" shape this repo already carries as the Atlas Kedro precedent and forbids in
Marshal's marshal:AD-67. Splitting states the truth: the verdict is built and provably independent,
and it is not yet rendered.

**Sequenced behind a profile, not blocked on nothing.** `doctor check` was measured at
**7.04s against its documented 5.0s budget** (SM-C1, `DW-DOCTOR-2026-08-08-1`). Adding a
gather filter to that verb before profiling would knowingly worsen a live NFR breach —
hence `Deps: S-5.1, S-6.1`.

**Surface:** `__main__.py`

## Acceptance Criteria

- **Given** a repo with tracked sprint ledgers, **When** the operator runs the verb this
  story wires, **Then** the `marshal-durability` Findings appear in **both** human and
  `--json` output.
- **And** a FAIL Finding participates in the exit-code lattice like any other.
- **And** `doctor check` is inside its documented budget after the addition — **measured,
  not assumed**.

## Delivery Record

Merged via PR #325 (`ef9feea727`), commit `64b46de2de` — *"doctor 5.2: render the
marshal-durability verdict, and the schema gap it exposed"*, 2026-08-08T19:17:08-05:00.
7 files, +192/−48.

Measured, not assumed: `doctor check` **2.95 / 2.99 / 3.03s** against the 5.0s budget, with
the durability gather itself **~0.04s** — the headroom S-6.1 created, spent as intended.
FAIL drives exit 0 → 2. Suite 418 → 422.

## Outcome

Wired as a third `doctor check` category (`--durability`), **whole-category only**:
per-check addressability is a `checks.registry` concern and this story's surface is
`__main__.py`; a NAME argument would hand-roll a second filter path beside `gather_one` —
the exact drift that function's "filter, not a second code path" rule prevents. Default run
is all three categories; an explicit `--engines`/`--env` narrows, so durability is excluded
— the existing semantics extended, not special-cased.

**The split paid for itself immediately.** `--json` crashed with
`jsonschema.ValidationError` and exit 2 on the first run: Story 5.1 had added
`Source.MARSHAL_DURABILITY` to the Python enum but **not** to `data/report-schema.json`,
and nothing caught it because 5.1 shipped the source with no caller — its findings had
never been rendered, so they had never been validated. Exactly the "merged, marked done,
never became the runtime" shape this split was written to expose.

Schema extended, plus `test_schema_source_enum_matches_the_source_taxonomy_exactly`
asserting **set equality in both directions** — a one-way `schema ⊆ enum` check would have
passed while the member was missing, which is the direction that actually broke.
Mutation-tested by removing the member.

## Notes

That both-directions set-equality lesson recurs: Story 6.7's AD-13 conformance test asserts
set equality against the installed harness for the same reason, and was likewise
mutation-tested before landing. A subset check passes in exactly the case worth catching.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `64b46de2de` (2026-08-08, "doctor 5.2: render the marshal-durability verdict, and the schema gap it exposed"); also `2425dc3216` (2026-08-08, "doctor: 5.2's forward dependency on the profile is now expressed, not prose"); also `e2c77635e0` (2026-08-07, "herald: Story 5.2 — conflict refusal on export push (CAP-5)"). Ledger row `5-2-render-the-verdict-through-a-doctor-verb: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`, `docs/dashboard/data.js`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json`, `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py`, `src/shared/packages/pyforge-doctor/tests/unit/test_models.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
