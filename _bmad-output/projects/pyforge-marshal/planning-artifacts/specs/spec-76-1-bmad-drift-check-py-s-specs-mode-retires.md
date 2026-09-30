---
title: "76.1: bmad_drift_check.py's --specs mode retires"
type: 'chore'
created: '2026-09-29'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '2157e66d12c7306777f98b02fe25ee3080f432c5'
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - scripts/bmad_drift_check.py
  - scripts/fleet_scan.py
  - _bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-one-chain-per-station:CAP-11` (operator ruling 2026-09-29) retires `docs/specs/`; doctor Story 37.1
empties it. `scripts/bmad_drift_check.py --specs` (`DOCS_SPECS` ~line 85, `cmd_specs` ~lines 463-480, the flag ~line 488)
prints each `docs/specs/*.md` status and whether `CLAUDE.md` indexes it. No pixi task or detector calls it; it is a manual
residual. Once the tier is gone the mode reports nothing.

Three more marshal files still describe the tier:
- `scripts/fleet_scan.py` (~line 2257) cites `docs/specs/presentation-deck.md`.
- `SYNC-RUNBOOK.md` lists `docs/specs/` in the source-of-truth surface that "the baseline check (`surface-changed`)
  detects". That was already untrue: doctor's `FINGERPRINT_KEYS` never covered `docs/specs/`.
- `SYNC-RUNBOOK.md` also names `docs/specs` in its out-of-band `git diff` command and has a `docs-specs-nonmd` row in its
  finding table.

CHAIN-STANDARD §11 requires every reader to follow before the PR that empties the directory.

**Approach:**
- Remove the `--specs` mode, `DOCS_SPECS` and `cmd_specs`, with their help and docstring lines.
- Add a test that `--specs` is rejected.
- Point `fleet_scan.py`'s comment at `docs/how-to/presentation-deck.md`.
- Take `docs/specs/` out of the runbook's surface list and `git diff` command, and its `docs-specs-nonmd` row out of the
  table.

The other modes, and marshal's seed templates, are unchanged. The seed templates teach Tier 1 to other repositories, and
this ruling is this repository's. The `AGENTS.md` sentence that names `--specs` leaves in Story 37.1.

Ledger key: `76-1-bmad-drift-check-py-s-specs-mode-retires`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- `spec-one-chain-per-station:CAP-11` (the Guild's; Marshal mints no CAP and no FR, as Epics 74 and 75 do); CHAIN-STANDARD
  §11.
- `spec-dream-to-code-model-self-verification` (governs `scripts/bmad_drift_check.py`); `spec-pyforge-marshal` (governs
  `scripts/fleet_scan.py`).
- `spec-feature-flag-governance` Q1: a `chore` needs no flag.
- Siblings: doctor Story 37.1 (blocked on this story), atlas Story 26.1, steward Story 77.1, herald Story 34.1.

## Acceptance Criteria

- Given the script When `python scripts/bmad_drift_check.py --specs` runs Then it exits 2 with argparse's
  unrecognised-argument message
- Given each other mode (`--groundtruth`, `--fix`, `--json`, `--write-baseline`) When it runs on today's tree Then its
  output is what it was before the change
- Given `SYNC-RUNBOOK.md` and `scripts/fleet_scan.py` When `git grep "docs/specs"` runs over them Then it finds nothing
- Given a test for the retired flag When the flag is restored Then the test fails (mutation)
- Given the marshal suite When `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` runs Then it passes

## Tasks

1. Read `scripts/bmad_drift_check.py`, the runbook and `fleet_scan.py`'s comment.
2. Remove the mode, and add the rejected-flag test under `tests/scripts/`.
3. Edit the runbook and the comment.
4. Run `pixi run -e pyforge-guild python -m pytest tests/scripts -q -k drift` and `pixi run --frozen -e pyforge-marshal
   pyforge-marshal-test`, and read each exit code.
5. Reconcile every Spec `spec-surface-check` names: memlog first, `git add`, then a scoped `--write-baseline --spec` for
   each (expected: `spec-dream-to-code-model-self-verification`, `spec-pyforge-marshal`).

## Boundaries & Constraints

**Always:**
- Keep every other mode's behaviour and output unchanged.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not edit marshal's seed templates.
- Do not move or edit anything under `docs/specs/` in this story.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| retired flag | `--specs` | exit 2, unrecognised argument | — |
| other modes | `--groundtruth`, `--fix`, `--json`, `--write-baseline` | unchanged | — |
| seed templates | `seed/templates/*` naming `docs/specs` | unchanged | out of scope |

</intent-contract>

## Code Map

Line numbers are from `2157e66d12`; measured, not copied from the intent.

- `scripts/bmad_drift_check.py` -- edit. Module docstring names `--specs` at 2, 20-30, 52. `DOCS_SPECS` at 85.
  `frontmatter_status` at 237-244 has `cmd_specs` as its only caller (`git grep` over `scripts src tests .claude`; the
  `_frontmatter_status` twins in doctor and scribe are separate functions), so it goes with it. `cmd_specs` at 463-480.
  The argparse flag at 488-489 and its dispatch at 500-501. The bare-run stderr message at 530-535 also lists `--specs`.
  Keep `_read` (many callers), `classify`, `TRACKED`.
- `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md` -- edit. `docs/specs/` at 46 (surface list), 76 (`git diff`
  paths), 84 (`tracked-impl-artifact` remedy) and 85 (`docs-specs-nonmd` row). The intent named 46, 76 and 85; line 84
  is the fourth hit and the "finds nothing" AC needs it gone too.
- `scripts/fleet_scan.py` -- edit two comments. 1126 (specs-roster header: "docs/specs legacy is deliberately out"; the
  intent named only the second hit) and 2294 (the 6-artifact family standard, cited to `docs/specs/presentation-deck.md`;
  the intent said ~2257).
- `tests/scripts/test_bmad_drift_check_specs_retired.py` -- new. No `bmad_drift_check` test exists in `tests/scripts/`;
  style follows `test_bmad_loop_baseline_drift_check.py` (importlib-load the script by path).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/{development-guide.md:244,443, source-tree-analysis.md:588,
  project-overview.md:437}` -- edit. These describe `--specs` as a live mode; removing the mode makes them false, so the
  same change fixes them (AGENTS.md § Behavioural guidelines 3).
- Read-only. `pyforge-doctor/.../sources/factory.py` `FINGERPRINT_KEYS` (257-265) has no `docs/specs`, which confirms the
  runbook claim was already untrue. Its `docs-specs-nonmd` emitter and `_docs_specs` stay: doctor Story 37.1's.
  `docs/how-to/presentation-deck.md` is the deck standard's home. Marshal seed templates: out of scope.
- Pre-change baseline (scratchpad): `--json` and `--groundtruth` are byte-identical, 229 bytes; a bare run exits 2.

## Spec Change Log

## Binding

Parent capability: `spec-one-chain-per-station:CAP-11` (Guild relay; no marshal CAP or FR).
Dream: `docs/dreams/one-chain-per-station.md` → § *2026-09-29 — One archive home*.
Ledger key: `76-1-bmad-drift-check-py-s-specs-mode-retires`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `chore` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `python scripts/bmad_drift_check.py --specs; echo $?` — expected: `2`.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

### 2026-09-30 — Review pass
- verdicts: 30 findings — high 0, medium 0, low 22, false 8, maybe-false 0
- findings:
  - Blind Hunter (10)
    - `[low]` `[patch]` `agent-instruction-notes.md` lines 56 and 346 still name the removed `--specs` flag as a working command — verified (the report's line 247 is the same claim, found on a sweep); reworded all three to point at each spec's own frontmatter `status:` field.
    - `[low]` `[patch]` `agent-instruction-notes.md:259` still lists `docs/specs/` as a `surface-changed` trigger, contradicting the runbook edit — verified; dropped it from the list.
    - `[low]` `[reject]` Runbook lost its `docs-specs-nonmd` row while doctor's `factory.py` still emits that finding — the intent orders the row's removal; `docs/specs/` holds only `.md` files, so the finding cannot fire; doctor Story 37.1 drops the emitter (its spec, Tasks item 2). Fix would edit against the intent.
    - `[low]` `[patch]` The rewritten `tracked-impl-artifact` row still ends `see CLAUDE.md "three tiers"`, a section CLAUDE.md no longer has — verified; repointed to `AGENTS.md § The tiers`.
    - `[low]` `[patch]` Stale facts on touched lines: `--integrity-only` (grep finds it in no script, nor in doctor's sources) and the "19 files" count (`docs/specs/` holds 5) — verified; dropped the dead flag and reworded the pixi-task row, dropped the count from the `project-overview.md` line. The dated "19 files, verified 2026-07-25" snapshot sentence in `development-guide.md` stays: it is a dated statement of a past fact.
    - `[low]` `[patch]` The "output unchanged" test compares `--json` with `ground_truth()`, i.e. with itself — verified; added a subset assertion on six stable keys.
    - `[low]` `[reject]` No standing guard that the runbook stays free of `docs/specs/` — AC 3 is a one-time `git grep` check, not a standing test; a text guard is new surface.
    - `[low]` `[reject]` Test harness leaves `sys.modules` registered and re-executes the module per test — the sibling `test_bmad_loop_baseline_drift_check.py` does the same; the module name is unique, so nothing collides.
    - `[low]` `[patch]` Allowlist reason line says the `--specs` report "retired with the docs/specs tier" though the tier still holds 5 files — verified; reworded to "ahead of". The memlog wording ("full entry" across two entries) stays: memlogs are append-only and the two entries together are complete.
    - `[low]` `[reject]` `AGENTS.md:221` still names `--specs` with no interim note — the intent itself defers that sentence to doctor Story 37.1 (its spec, Tasks item 3).
  - Edge Case Hunter (8)
    - `[low]` `[patch]` `agent-instruction-notes.md` lines 346 and 56 — same root cause as the first Blind Hunter row; fixed together.
    - `[low]` `[patch]` `spec_surface_allowlist.txt:7` says `drift-check --specs governs`, a governor that no longer exists — verified; dropped the clause. Doctor Story 37.1 later drops the whole line.
    - `[false]` `[reject]` No tracked owner for the `docs/specs` stubs, `AGENTS.md:221` or the atlas `factory_status.py:14` docstring — each has one: the stubs and `AGENTS.md` are 37.1's (its spec, Tasks items 3 and 5), the docstring is atlas Story 26.1's (its spec, Tasks item 2); this story's Never clause forbids editing `docs/specs/`.
    - `[low]` `[reject]` `docs-specs-nonmd` row removed while doctor still emits it — same as the third Blind Hunter row.
    - `[low]` `[reject]` Runbook remedy names `planning-artifacts/specs/` while doctor's emitted text still says `docs/specs/` — 37.1's Tasks item 2 rewrites the emitter's remedy to name the Tier-2 folder, which is what the runbook now says; the runbook is the correct end state.
    - `[low]` `[patch]` `--json` test asserts against its own function — same root cause as the sixth Blind Hunter row; fixed together.
    - `[low]` `[reject]` `sys.modules` leak and unguarded `spec_from_file_location` — same as the eighth Blind Hunter row.
    - `[false]` `[reject]` `--json` on a checkout without the marshal project dir prints nothing, so the test would hit `JSONDecodeError` — this repository tracks `_bmad-output/projects/pyforge-marshal/`; the failure would be loud, not silent, and cannot occur here.
  - Verification Gap Reviewer (6, filed under `Other findings`; the layer filed no gap)
    - `[low]` `[patch]` `agent-instruction-notes.md` lines 56 and 346 — same root cause as the first Blind Hunter row; fixed together.
    - `[low]` `[reject]` `AGENTS.md:221` — same as the tenth Blind Hunter row.
    - `[false]` `[reject]` The three `docs/specs/*.md` stubs still say `--specs` keeps reporting `status: workflow` — true, and this story's Never clause forbids editing `docs/specs/`; 37.1 moves the stubs. No bad outcome at this story's surface.
    - `[low]` `[reject]` Runbook and detector give different guidance for `tracked-impl-artifact` — same as the fifth Edge Case Hunter row.
    - `[low]` `[patch]` `spec_surface_allowlist.txt:7` — same as the second Edge Case Hunter row; fixed together.
    - `[false]` `[reject]` The atlas `factory_status.py:14` docstring is historical text with no owner — atlas Story 26.1's Tasks item 2 updates that module docstring.
  - Intent Alignment Auditor (6, descriptive; each divergence it names is triaged as a finding)
    - `[false]` `[reject]` AC 5 lives on the package-test surface while the change sits under `scripts/` — the spec's Tasks item 4 runs both the marshal suite and `tests/scripts -k drift`, which collects the new test; both ran green (8939 and 50 passed).
    - `[low]` `[patch]` AC 2 ("other modes unchanged") is asserted against the post-change module, and `--fix`/`--write-baseline` run in no test — the before/after byte comparison was made on the tree (229 bytes, identical); the standing test now pins the stable `--json` keys (same fix as the sixth Blind Hunter row); `--fix` and `--write-baseline` mutate the project tree and stay untested on purpose.
    - `[false]` `[reject]` AC 1 and AC 4 are exercised in-process and through a subprocess — the auditor names no divergence; mutation check run by hand: restoring the flag fails 2 of 6 tests, restoring the file passes 6 of 6.
    - `[false]` `[reject]` Task 5's scoped `--write-baseline` stamps are absent — the dispatch instruction for this run forbids `--write-baseline` and overrides the spec's Task 5; the implementation subagent stamped once, and that stamp of `scripts/.spec-surface-baseline.json` was reverted to the baseline revision. Both governing Specs' memlogs name the changed paths; `spec_surface_reconcile.py` and `spec-surface-check` exit 0 without a stamp.
    - `[low]` `[reject]` Residual readers: `architecture-bmad-infra.md` still lists the `docs-specs-nonmd` finding, and `AGENTS.md` still names `--specs` — the finding code exists until 37.1 drops it, so the doc is accurate today; `AGENTS.md` is 37.1's. The `agent-instruction-notes.md:259` part of this row is the second Blind Hunter row, patched.
    - `[false]` `[reject]` Edits beyond the named items (`frontmatter_status`, the second `fleet_scan.py` comment, the `tracked-impl-artifact` row, four docs, the allowlist) — informational; each is required by an acceptance criterion or by a line the flag's removal made false, and none crosses a Never clause.
