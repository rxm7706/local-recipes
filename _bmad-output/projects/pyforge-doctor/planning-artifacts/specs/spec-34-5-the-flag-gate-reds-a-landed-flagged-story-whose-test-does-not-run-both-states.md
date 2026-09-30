---
title: '34.5: The flag gate reds a landed flagged story whose test does not run both states'
type: 'feature'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: 50976c802aac4e6716012db7b8430b8cae63c286
flag-exempt: detector-or-gate   # a gated gate reports a silent green (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-74-1-the-testing-kit-runs-a-story-in-both-flag-states-through-one-fixture.md
  - src/platform/tests/test_openfeature_file_flags.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-feature-flag-governance` CAP-4 requires that "a flagged story's Verification names such a test" — one
that runs both flag states through the testing kit's fixture — and its success clause says "the CAP-2 gate can tell when a
story's Verification names no two-state test". The kit is Marshal's cross-station seam, so marshal Story 74.1 ships the
fixture; the gate that judges every station's stories is Doctor's, outside every station (Charter §6), so the check that
reads a story's Verification belongs here, beside the rest of the gate. Without it a story can declare a flag, land, and
never have tested its OFF path.

**Approach:** extend `scripts/flag_gate_check.py` (Story 34.2) with one check over `done`, post-rule, flagged story
specs: read the spec's `## Verification` section, collect the test files it names (backticked paths and `pytest` targets),
and read each statically (never run it). FAIL when no named test file references the spec's `flag.key` together with
either the kit's ON/OFF helper (`pyforge.testing_kit.flags`, as Story 74.1 names it) or two flagd trees written for that
key (the pre-kit shape of `src/platform/tests/test_openfeature_file_flags.py`, so a story that predates the kit is not
red for it). A spec still in backlog is never judged on this (its test does not exist yet), and neither is an exempt one.
The `--spec` JSON carries the finding for one spec.

**Blocked until marshal Story 74.1 has landed; the operator flips it.** The helper's name and import path are what 74.1
ships; the ledger key is minted `blocked` because marshal's `Deps:` parser is station-local (the doctor 33.1 precedent).
Do not start this story while 74.1 is unlanded.

Ledger key: `34-5-the-flag-gate-reds-a-landed-flagged-story-whose-test-does-not-run-both-states`.
Ledger status (do not edit the ledger): `backlog` -- flipped 2026-09-30 by the operator after marshal Story 74.1 landed on main (1c3e4ba113).
Type / Effort / Deps: feature / S / S-34.2 (cross-project gate: marshal Story 74.1).

### Living CAP citations

- `spec-feature-flag-governance` CAP-4 (its gate clause; the kit half is marshal Story 74.1). The Spec's *Who does the
  work* table gives CAP-4 to Marshal; the gate code that judges it stays Doctor's under Charter §6 — recorded in the Guild
  Spec's `.memlog.md` on 2026-09-28 as a story-home decision, no contract change.
- Kinship: marshal Story 74.1.

## Acceptance Criteria

- Given a `done` post-rule flagged spec whose Verification names a test that uses the kit's ON/OFF helper with the spec's key When the gate runs Then no finding
- Given the same spec naming a test that writes two flagd trees for the key When the gate runs Then no finding
- Given the same spec naming a test that never references the key When the gate runs Then one FAIL names the spec and the test file
- Given the same spec whose Verification names no test file When the gate runs Then one FAIL names the spec
- Given the same spec at `backlog`, or an exempt spec When the gate runs Then no finding from this check
- Given a named test file that does not exist When the gate runs Then one FAIL names the missing path
- Given `--spec` on the failing fixture When it runs Then its JSON carries the finding and `verdict` `red`
- Given the live tree at the landing SHA When `pixi run -e pyforge-guild flag-gate-check` runs Then it exits 0
- Given the change When `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Read test files statically; never import or run them.
- Take the helper's name and import path from what marshal 74.1 landed; never guess them.
- Keep every change in `scripts/` and `tests/scripts/`; nothing in any `pyforge.<station>` package.

**Never:**
- Do not start before marshal Story 74.1 has landed; do not flip this story's ledger key.
- Do not edit the testing kit or any station's tests.
- Do not edit `SPEC.md` or `sprint-status-ledger.yaml`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| kit helper | test uses the helper with the key | nothing | — |
| pre-kit pattern | two flagd trees for the key | nothing | — |
| key never referenced | test ignores the key | FAIL | exit 1 |
| no test named | Verification lists commands only | FAIL | exit 1 |
| missing file | named path absent | FAIL naming the path | exit 1 |
| not landed / exempt | `backlog`, or `flag-exempt:` | nothing | — |

</intent-contract>

## Code Map

- `scripts/flag_gate_check.py` -- the gate. `judge_one` (reads frontmatter, `is_post_rule`, calls `judge_spec`) is the one place both `--spec` and tree mode pass through, so the new check hangs off it; `K_*` finding kinds, `Finding`, and the module docstring's kind list are the shape to extend. The existing `done` test (`K_NOT_IN_TREE`, in `judge_spec`) is the precedent for "landed".
- `scripts/flag_rule.py` -- pure reader: `classify_frontmatter(...).verdict == FLAG` is "flagged with a complete block", `read_frontmatter`, `is_post_rule`. Read-only here.
- `src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/flags.py` -- marshal 74.1's landed helper (on main, `1c3e4ba113`): module `pyforge.testing_kit.flags`; the ON/OFF helper is `flag_states(key)`; `flagd_tree(tmp_path, {key: "on"|"off"})` writes one tree. Read-only; take the names from here, never guess.
- `src/platform/tests/test_openfeature_file_flags.py` -- the pre-kit shape: `_flagd_tree("on")` and `_flagd_tree("off")` calls (lines ~267, 278). It is also the only test the one live `done` flagged spec names (steward 74.1, key `pyforge.steward.object_store_consumer`, which the file names at `_SHIPPED_BOOLEANS`), so the live tree stays green through this shape.
- `tests/scripts/test_flag_gate_check.py` -- the suite. `_fixture`, `_spec`, `_write`, `_run`, `_tree_json`, `_kinds` are the helpers. `_spec` writes a body of `body\n`; the three existing tests that write a `done` flagged spec expecting no finding (`status="done"` at the `landed` / `spec-1-2-done` rows) now need a Verification naming a two-state test.
- `docs/reference/story-spec-flag-block.md` -- "How a machine reads it" paragraph names what the gate judges; add the two-state check there.
- `src/shared/packages/pyforge-doctor/tests/meta/test_flag_gate_stays_outside_every_station.py` -- pins "no `pyforge.*` import in the gate"; the new code is stdlib-only.

## Tasks & Acceptance

**Execution:**
- `scripts/flag_gate_check.py` -- add `judge_two_state(root, rel, frontmatter, *, exemptions)` and three kinds (`flag-verification-names-no-test`, `flag-test-file-missing`, `flag-test-not-two-state`); call it from `judge_one` for post-rule specs; update the module docstring -- CAP-4's gate clause, static reads only
- `tests/scripts/test_flag_gate_check.py` -- one test per acceptance row and I/O row (kit helper, two trees, key never referenced, no test named, missing file, backlog and exempt, `--spec` red); fix the three existing `done`-spec tests -- the new check changes what a `done` flagged fixture must carry
- `docs/reference/story-spec-flag-block.md` -- one sentence: the gate also reds a `done` flagged spec whose Verification names no test that runs both states

**Acceptance Criteria:**
- Given the acceptance criteria and I/O matrix in the intent contract, when the suite runs, then every row has a passing test
- Given the live tree, when `pixi run -e pyforge-guild flag-gate-check` runs, then it exits 0

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-4 (success: the gate can tell a
Verification that names no two-state test) and Charter §6, decomposed 2026-09-28 (night) as Epic 34's mint.

## Spec Change Log

- 2026-09-30 -- operator flip, `blocked` -> `backlog`: the cross-station gate cleared when marshal Story 74.1 landed on main (1c3e4ba113). Nothing else in the contract changed. A resumed worktree brings `origin/main` into its branch first (merge, never rebase).

## Binding

Parent Spec capability: `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-4, its gate clause (Guild-owned;
Doctor as mechanism Smith for the gate, Marshal for the kit).
Dream: `docs/dreams/feature-flag-governance.md` § Realization log → *2026-09-28 (night)*.
Ledger key: `34-5-the-flag-gate-reds-a-landed-flagged-story-whose-test-does-not-run-both-states`.
Ledger status at mint: `blocked` (cross-project gate: marshal Story 74.1).
Policy: `marshal-policy.toml` `[epic_surfaces]` `"34"`.

## Design Notes

The check is static and presence-based: it cannot prove a tree in a test file is written for the spec's key, only
that the file names the key and carries the shape. That is the contract's own bar ("references the key together
with ..."), and it is what lets a pre-kit story pass without a rewrite. A named path counts as a test file by its
name (`test_*.py`, `*_test.py`, `*.test.*`, `*.spec.*`); a directory target (`pytest some/dir`) names no file.

- Kit shape: the file imports `pyforge.testing_kit.flags`, calls `flag_states(`, and names the key.
- Pre-kit shape: the file names the key and calls a `*flagd_tree*` writer at least twice, with both `"on"` and `"off"`.
- Finding order per spec: no test named -> one FAIL; named paths absent -> one FAIL listing them; else, when no
  present file has either shape -> one FAIL naming the spec and those files. Never two FAILs for one cause.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_gate_check.py -q` — expected: pass.
- `pixi run -e pyforge-guild flag-gate-check` — expected: exit 0 on the landing tree.

## Review Triage Log
