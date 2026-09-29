---
title: "37.1: docs/specs and docs/intake empty, and the legacy tier's index and check retire"
type: 'chore'
created: '2026-09-29'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py
  - CLAUDE.md
  - AGENTS.md
  - .cursor/rules/specs.mdc
  - scripts/spec_surface_allowlist.txt
  - docs/intake/README.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-one-chain-per-station:CAP-11` (operator ruling 2026-09-29) retires the legacy intake-spec tier and
empties the intake inbox. Its success clause names this PR: "`docs/intake/` holds only its README. `docs/specs/` is gone,
with `CLAUDE.md`'s legacy index, `AGENTS.md`'s Tier 1 row and doctor's `check_spec_indexed` retired in the same PR."
CHAIN-STANDARD §11 makes it step 3, after the Dream and Spec-folder moves.

The directories hold, on 2026-09-29:
- `docs/specs/`: `flyte-conda-forge.md` (done; local closure green 2026-07-01), the three workflow stubs
  (`feedstock-failure-remediation.md`, `feedstock-platform-expansion.md`, `presentation-deck.md`, whose bodies live in
  `docs/how-to/` under the same names), and `feedstock-refresh.md` (unfinished, carried into Mason's chain as
  `spec-pyforge-mason` CAP-35, Epic 25).
- `docs/intake/`: `README.md`, `agentic-sdlc/` (steward 59.4 done) and `external-repos-analysis-2026-08-22/` (its report
  items were folded into the atlas and mason Dreams on 2026-09-29).

**Approach:** one PR, after the four reader stories land (atlas 26.1, steward 77.1, herald 34.1, marshal 76.1). It works
in six parts:
1. **Moves**, each a `git mv`:
   - the four done or stub files go to `archive/docs/specs/`;
   - `feedstock-refresh.md` goes to `spec-pyforge-mason/feedstock-refresh.md` and joins that Spec's `companions:` (memlog
     first, then a render by script, because the pre-shell hook denies edits to `SPEC.md`);
   - the two intake items go to `archive/docs/intake/`.
2. **Doctor:**
   - `sources/factory.py` drops `check_spec_indexed`, `_docs_specs` and the `docs-specs-nonmd` branch of
     `check_tier_alignment`;
   - its misfiled-intake remedy (`intake spec -> git mv to docs/specs/`) names the Tier-2 Spec folder instead;
   - `test_sources_factory.py` follows, including the remedy-text assertion at line ~849.
3. **Instruction surface:**
   - `CLAUDE.md` loses § *Legacy intake-spec index*;
   - `AGENTS.md` loses its Tier 1 row and every other `docs/specs/` line, including the Dream-first sentence that names
     `bmad_drift_check.py --specs`;
   - `.cursor/rules/specs.mdc` stays a pointer file (scribe's parity test pins its existence and shape) but stops
     describing Tier 1.
4. **Allowlist and surfaces:**
   - `scripts/spec_surface_allowlist.txt` drops `docs/specs/**`, which would otherwise be a stale-allowlist FAIL;
   - `spec-pyforge-herald`'s surface drops `docs/specs/presentation-deck.md` (memlog, then a render by script).
5. **Live references repointed** to the new paths:
   - the stubs to `docs/how-to/<name>.md`;
   - flyte to `archive/docs/specs/flyte-conda-forge.md`;
   - feedstock-refresh to its companion path;
   - the intake items to `archive/docs/intake/`.
   This covers the CFE skill (`SKILL.md`, `guides/feedstock-platform-expansion.md`, in one `retro(cfe):` commit),
   `docs/reference/agent-instruction-notes.md` § *Intake specs*, `docs/MAP.md`,
   `docs/explanation/the-tier-model-and-data-flow.md`, `docs/reference/README.md`, `docs/reference/library-llms-full.md`,
   planning artifacts' live text (mason Epic 25, and the `context:` of Stories 25.1 and 25.2), and the Dreams that name
   the intake items.
6. **History stays as written:** `.memlog.md` entries, `CHANGELOG.md` entries, dated Realization-log and
   Currency-reconciliation sections, and `archive/`. They record what was true when they were written.

Ledger key: `37-1-docs-specs-and-docs-intake-empty-and-the-legacy-tier-s-index-and-check-retire`.
Ledger status (do not edit the ledger): `blocked` — the cross-project gate; the operator flips it once atlas 26.1,
steward 77.1, herald 34.1 and marshal 76.1 have landed.
Type / Effort / Deps: chore / L / — (cross-project gate above).

### Living CAP citations

- `spec-one-chain-per-station:CAP-11` (the Guild's; Doctor mints no CAP and no FR, the relay shape of doctor Epics 24,
  25, 32, 34 and 36); CHAIN-STANDARD §11 step 3.
- `spec-docs-shelf-alignment` (Doctor's docs shelf; Stories 23.3 and 23.4 shaped `docs/specs/` and `docs/intake/`).
- `spec-pyforge-scribe` CAP-27 (one `AGENTS.md`, pointers elsewhere): the instruction files are scribe-governed.
- `spec-pyforge-mason` CAP-35: `feedstock-refresh.md` becomes its companion.
- `spec-feature-flag-governance` Q1: a `chore` needs no flag.

## Acceptance Criteria

- Given the four reader stories have landed When the PR merges Then `docs/specs/` does not exist and `docs/intake/`
  holds only `README.md`
- Given each moved file When `git log --follow` runs on its new path Then its history is intact (every move is a
  `git mv`)
- Given `spec-pyforge-mason/SPEC.md` When it is read Then `companions:` names `feedstock-refresh.md`, and the file sits
  beside it
- Given doctor's sources When `python -m pyforge.doctor.sources bmad-drift` runs Then no `spec-unindexed` or
  `docs-specs-nonmd` finding code exists, and the misfiled-intake remedy names no `docs/specs/` path
- Given `CLAUDE.md` and `AGENTS.md` When they are read Then neither has a legacy intake-spec index, a Tier 1 row, or a
  `docs/specs/` path, and scribe's `test_instruction_surface_parity.py` passes
- Given the live tree When `git grep` runs for each moved path, excluding `archive/`, `.memlog.md` files, `CHANGELOG.md`
  files and dated sections Then nothing names an old path
- Given `governance-currency`, `spec-surface-check`, `detectors-ci` and `pr-preflight` When each runs Then each exits 0

## Tasks

1. Confirm the four reader stories are merged (`git merge-base --is-ancestor` on each landing) and that the operator
   has flipped this row.
2. Append a `.memlog.md` entry to every Spec whose governed files this PR moves or edits. Name each path and the reason.
   These include:
   - `spec-pyforge-doctor` (the docs shelf);
   - `spec-pyforge-scribe` (the instruction files);
   - `spec-pyforge-herald` (the stub, and its surface entry);
   - `spec-pyforge-mason` (the companion);
   - any other that `spec-surface-check` names.
3. Make the moves with `git mv`, then render the two `SPEC.md` frontmatter changes (mason `companions:`, herald surface)
   by script.
4. Edit doctor's `factory.py` and its tests; edit `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/specs.mdc` and the
   allowlist.
5. Repoint live references. Put the CFE skill edits in their own `retro(cfe):` commit with a CFE `CHANGELOG.md` PATCH
   entry and its version carriers (`cfe_rebuild_guard_check`). Commit the rest as ordinary commits, none with a subject
   starting `Story 37.1:`.
6. `git add`, then a scoped `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` for each Spec
   the detector names.
7. Run `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`, `pixi run -e pyforge-guild governance-currency`,
   `pixi run -e pyforge-guild spec-surface-check` and `pixi run -e pyforge-guild pr-preflight`, and read each exit code.

## Boundaries & Constraints

**Always:**
- Move with `git mv`; never delete a file.
- Read every verdict from the exit code, never through a pipe.
- Render a `SPEC.md` change by script after its memlog entry; never edit a `SPEC.md` by hand.

**Never:**
- Do not rewrite history: `.memlog.md` entries, `CHANGELOG.md` entries, dated sections and `archive/` stay as written.
- Do not change marshal's seed templates (they teach Tier 1 to other repositories).
- Do not change a `pixi.toml` dependency; comment edits only.
- Do not hand-edit `sprint-status-ledger.yaml` or flip a `blocked` row.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | five files and two intake items | `docs/specs/` gone; intake README-only | — |
| reader not landed | one of the four readers still open | do not start | the row stays `blocked` |
| stale allowlist | `docs/specs/**` left in the allowlist | spec-surface FAIL | remove the line |
| a history file names an old path | a memlog entry or CHANGELOG line | left as written | excluded from the `git grep` check |
| a new file lands in `docs/specs/` meanwhile | an unexpected sixth file | stop; route it to its station chain or the archive | report it to the operator |
| CFE skill edit | a `SKILL.md` or guide path repointed | its own `retro(cfe):` commit with a CHANGELOG entry | `cfe_rebuild_guard_check` |

</intent-contract>

## Binding

Parent capability: `spec-one-chain-per-station:CAP-11` (Guild relay; no doctor CAP or FR).
Dream: `docs/dreams/one-chain-per-station.md` → § *2026-09-29 — One archive home*.
Ledger key: `37-1-docs-specs-and-docs-intake-empty-and-the-legacy-tier-s-index-and-check-retire`.
Ledger status at mint: `blocked` (cross-project gate: atlas 26.1, steward 77.1, herald 34.1, marshal 76.1).
Deps: —.
Flag: none. This is a `chore` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `test ! -e docs/specs` and `ls docs/intake` shows only `README.md`.
- `pixi run -e pyforge-guild governance-currency` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert` — exactly one `retro(cfe):` subject.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
