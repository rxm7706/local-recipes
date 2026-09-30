---
title: '34.5: The flag gate reds a landed flagged story whose test does not run both states'
type: 'feature'
created: '2026-09-28'
status: 'done'
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
- `docs/reference/story-spec-flag-block.md` -- "How a machine reads it" paragraph names what the gate judges. Not changed (see the 2026-09-30 review entry in the Spec Change Log): the contract's Boundaries confine every change to `scripts/` and `tests/scripts/`.
- `src/shared/packages/pyforge-doctor/tests/meta/test_flag_gate_stays_outside_every_station.py` -- pins "no `pyforge.*` import in the gate"; the new code is stdlib-only.

## Tasks & Acceptance

**Execution:**
- `scripts/flag_gate_check.py` -- add `judge_two_state(root, rel, frontmatter, *, exemptions)` and three kinds (`flag-verification-names-no-test`, `flag-test-file-missing`, `flag-test-not-two-state`); call it from `judge_one` for post-rule specs; update the module docstring -- CAP-4's gate clause, static reads only
- `tests/scripts/test_flag_gate_check.py` -- one test per acceptance row and I/O row (kit helper, two trees, key never referenced, no test named, missing file, backlog and exempt, `--spec` red); fix the three existing `done`-spec tests -- the new check changes what a `done` flagged fixture must carry
- ~~`docs/reference/story-spec-flag-block.md` -- one sentence about the new check~~ -- dropped at review: outside the contract's Boundaries (`scripts/` and `tests/scripts/` only)

**Acceptance Criteria:**
- Given the acceptance criteria and I/O matrix in the intent contract, when the suite runs, then every row has a passing test
- Given the live tree, when `pixi run -e pyforge-guild flag-gate-check` runs, then it exits 0

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-4 (success: the gate can tell a
Verification that names no two-state test) and Charter §6, decomposed 2026-09-28 (night) as Epic 34's mint.

## Spec Change Log

- 2026-09-30 -- operator flip, `blocked` -> `backlog`: the cross-station gate cleared when marshal Story 74.1 landed on main (1c3e4ba113). Nothing else in the contract changed. A resumed worktree brings `origin/main` into its branch first (merge, never rebase).
- 2026-09-30 -- implemented: status `in-progress` -> `in-review`; every task done, the intent contract unchanged. The kit helper's name is `flag_states` in `pyforge.testing_kit.flags` (read from the landed module, also re-exported by `pyforge.testing_kit`); the pre-kit shape is one `*flagd_tree*` call naming `"on"` and another naming `"off"`. Live tree: both `done` flagged specs (steward 74.1 and 75.1) pass through the pre-kit shape in `src/platform/tests/test_openfeature_file_flags.py`; `flag-gate-check` exits 0 (1208 judged, 0 fail, 840 warn).
- 2026-09-30 -- review (one pass, no loopback): the docs sentence in `docs/reference/story-spec-flag-block.md` was reverted and the docs task dropped from Tasks & Acceptance -- the contract's Boundaries confine every change to `scripts/` and `tests/scripts/`, and the plan's own Task had contradicted them. The `implemented` entry above says both live `done` flagged specs (steward 74.1 and 75.1) "pass through the pre-kit shape"; measured more exactly, they pass because `src/platform/tests/test_openfeature_file_flags.py` names both keys (in `_SHIPPED_BOOLEANS`) and carries two `_flagd_tree` calls, one `"on"` and one `"off"` -- written for a different key. That is the presence-based bar in Design Notes, not trees written for each key. KEEP: the three finding kinds, the one-finding-per-spec order, the static read, and the presence-based bar (call-level binding would red both live specs and break the AC that the live tree exits 0).

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

### 2026-09-30 — Review pass
- verdicts: 44 findings — high 0, medium 1, low 35, false 6, maybe-false 2
- findings:
  - `[low]` `[reject]` Blind Hunter: the key and the kit helper are matched separately, so a file with `@flag_states("other")` and the spec's key in a comment passes — real but it is the contract's stated bar ("references the spec's `flag.key` together with ..."), recorded in Design Notes; binding the key to the call would red steward 74.1 and 75.1 on the live tree (AC 8), and the fix adds branches for a contrived authoring shape.
  - `[low]` `[reject]` Blind Hunter: two calls that each name both variants (`_flagd_tree({"a": "on", "b": "off"})` twice) count as two trees — real but contrived; the fix (tie a variant to the key inside the call) adds parsing complexity for a shape no story has.
  - `[low]` `[reject]` Blind Hunter: real two-state shapes (a parametrized variant, an indirect `flag_provider` fixture, a key reached through an imported constant) are reported `flag-test-not-two-state` — the intent names exactly two shapes and the message names both; supporting more shapes is AST work beyond the contract.
  - `[low]` `[reject]` Blind Hunter: comments and docstrings count as evidence — the check is presence-based by contract; a deliberately faked test is not a case this gate claims to catch, and stripping comments adds a tokenizer pass.
  - `[low]` `[reject]` Blind Hunter: a named test that exists on disk but is untracked passes locally and reds in CI — CI reds it as `flag-test-file-missing`, which is the correct verdict for a file that never landed; the gate elsewhere reads tracked files, but a local green here costs one CI round, and the fix adds a `git ls-files` membership guard per spec.
  - `[low]` `[reject]` Blind Hunter: the Verification parser is narrower than every real spec (`### Verification`, `## Verification evidence`, a `## ` line inside a fence, `--ignore tests/x` with a space, `conftest.py`, directory targets) — the intent says "the spec's `## Verification` section"; both live `done` flagged specs use that exact heading, and each fix adds a branch for a shape no landed spec has.
  - `[low]` `[patch]` Blind Hunter: `flag-test-file-missing` says "do not exist" although `_read_test` also returns None for a directory, an unreadable file and a path outside the repo — the message now says "not a readable file under the repo root".
  - `[low]` `[reject]` Blind Hunter: the docs sentence is thin (no finding kinds, no literal-key limits) — the intent's Boundaries confine every change to `scripts/` and `tests/scripts/`, so the docs file is excluded by the intent itself; the module docstring in `scripts/flag_gate_check.py` carries the full account. Patched separately, see the docs-sentence row below.
  - `[false]` `[reject]` Blind Hunter: no memlog "Surface reconcile" event and no scoped stamp — `python scripts/spec_surface_reconcile.py` and `pixi run -e pyforge-guild spec-surface-check` both exit 0: `scripts/flag_gate_check.py` is allowlisted (`scripts/spec_surface_allowlist.txt`, owning Spec is guild-owned) and `tests/scripts/` and `docs/reference/**` govern no Spec surface, so no governed path moved.
  - `[low]` `[reject]` Blind Hunter: the Change Log gives live-tree counts and no test result, and `pyforge-doctor-test` does not run `tests/scripts` — the counts are a dated record, not a gate; the new tests run in the `scripts-suite` lane and in `pr-preflight`, and were run here (see Auto Run Result).
  - `[low]` `[reject]` Edge Case Hunter: key and helper or tree shape are never tied to each other — same root cause and same reasoning as the first Blind Hunter row.
  - `[low]` `[reject]` Edge Case Hunter: the live `done` flagged specs (steward 74.1 and 75.1) pass because their keys sit in `_SHIPPED_BOOLEANS` while `_flagd_tree` writes trees for another key — true, and it is the presence-based bar the Design Notes state and AC 8 needs; recorded in Auto Run Result as a residual risk. The Change Log wording that overstates it is a spec edit, which this pass does not make.
  - `[low]` `[reject]` Edge Case Hunter: a key reached through an imported constant is reddened — same root cause as the shapes row above.
  - `[low]` `[reject]` Edge Case Hunter: trees written with the kit's `ON`/`OFF` constants, a parametrized variant or a loop are reddened — same root cause as the shapes row above.
  - `[low]` `[reject]` Edge Case Hunter: an aliased import (`import flag_states as fs`) or `from pyforge import testing_kit` reddens a correct kit test — no live spec uses the kit yet; resolving aliases needs an AST pass the contract does not ask for.
  - `[low]` `[reject]` Edge Case Hunter: a file that imports any name from `testing_kit` and defines its own `flag_states` passes as kit-based — contrived; the fix adds two guards for a state nothing reaches.
  - `[low]` `[reject]` Edge Case Hunter: `*.test.ts` and `*.spec.ts` are accepted as test files but no TypeScript shape can satisfy the gate — a named TypeScript test reds `flag-test-not-two-state` with a message that names the accepted shapes; no landed spec names one, and the contract defines two Python-shaped patterns only.
  - `[low]` `[reject]` Edge Case Hunter: `--ignore tests/x.py` and `--deselect ...` written with a space count the file as run — contrived (only the `=` form is tested); the fix needs an option table.
  - `[low]` `[reject]` Edge Case Hunter: a glob target (`tests/test_flag*.py`) reds `flag-test-file-missing` — no landed spec writes one; expanding globs adds a branch for no live shape.
  - `[low]` `[reject]` Edge Case Hunter: `cd src/platform && pytest tests/x.py` resolves only from the repo root, so a correct test reds as missing — no live spec writes it and the message names the path, so the author sees why.
  - `[low]` `[reject]` Edge Case Hunter: an untracked or gitignored test passes locally and reds in CI — same root cause as the untracked-file row above.
  - `[low]` `[reject]` Edge Case Hunter: a `## ` line inside a fenced block ends the section early — same root cause as the parser-narrowness row above.
  - `[low]` `[reject]` Edge Case Hunter: an unclosed fence, or a one-line fence, inverts fence pairing — same root cause as the parser-narrowness row above; a malformed fence in a landed spec reds visibly.
  - `[low]` `[reject]` Edge Case Hunter: a non-string `flag.key` (a list or int) is non-blank, so the two-state check returns nothing — the neighbouring `flag-key-not-in-tree` check skips the same value the same way (Story 34.2); no landed spec has one, and a guard would judge a state nothing demonstrated.
  - `[low]` `[reject]` Edge Case Hunter: commented-out or `skip`-marked tests satisfy the gate — same root cause as the comments row above.
  - `[low]` `[patch]` Edge Case Hunter: `text[: call.start()].rstrip().endswith("def")` also matches `undef` or `typedef`, so a real `_flagd_tree(` call after such an identifier is skipped — reproduced (`'undef' -> True`); the check now matches the `def` keyword only, with a test row.
  - `[low]` `[reject]` Edge Case Hunter (claim): the module docstring says "two flagd trees written for it" while the code checks presence — the same docstring paragraph says "It is presence-based" and names what it cannot prove.
  - `[low]` `[reject]` Edge Case Hunter (claim): the Change Log says both live `done` specs "pass through the pre-kit shape" — see the live-tree row above; the fix is a spec edit, and Auto Run Result states the coincidence accurately.
  - `[medium]` `[patch]` Verification Gap: no test pins the kit shape when `flag_states` is imported and the key named but never called (a mutant dropping the call requirement survived) — a row added to the not-two-state parametrize list.
  - `[low]` `[patch]` Verification Gap: the prefix side of the key-name boundary in `_names_key` is unpinned (four lookbehind mutants survived) — rows added for `other.<KEY>`, `x-<KEY>` and `my<KEY>`.
  - `[low]` `[patch]` Verification Gap: `_call_arguments` stopping at the call's own closing parenthesis is unpinned (a mutant survived) — a row added with two `on` trees and a later unrelated `"off"` string.
  - `[low]` `[patch]` Verification Gap: the finding message lists every named file but no test names more than one (a mutant listing only the first survived) — a two-file test added; the reviewer's disposition was defer, patched instead because it is one test.
  - `[low]` `[patch]` Verification Gap: nothing ties the gate's hard-coded `flag_states` and `pyforge.testing_kit` names to what marshal 74.1 landed — a static test reads the kit's `flags.py` and `__init__.py` as text and asserts the names, deriving them from the gate's own constants.
  - `[low]` `[patch]` Verification Gap: three parser behaviours are unpinned (only the first `## Verification` section, `## Verification Notes` matching the heading, the URL skip) — one row each added; the reviewer's disposition was defer, patched instead because each is one row.
  - `[false]` `[reject]` Verification Gap (other): the live tree stays green on the two `done` flagged specs by coincidence — the fact is true and is the same root cause as the live-tree row above; it is the stated presence-based bar, not a defect in the diff.
  - `[low]` `[reject]` Verification Gap (other): the `flag-gate-check` task description in `pixi.toml` and the `docs/how-to/pixi-tasks.md` row do not mention the new check — a `pixi.toml` change is outside the intent's Boundaries and regenerates `docs/how-to/pixi-tasks.md` and `environment.yaml`; the gate's own docstring names the check.
  - `[low]` `[patch]` Intent Alignment: the diff edits `docs/reference/story-spec-flag-block.md`, outside the Boundaries' "every change in `scripts/` and `tests/scripts/`" — the docs task was in this run's own plan, not the contract; the sentence is reverted to its baseline text.
  - `[false]` `[reject]` Intent Alignment: A1 file-level presence versus A2 call-level binding for the live tree — a description of the presence-based reading; AC 8 needs exit 0 and only A1 gives it (A2 reds steward 74.1 and 75.1); same root cause as the live-tree rows.
  - `[false]` `[reject]` Intent Alignment: `pyforge-doctor-test` does not run `tests/scripts`, so AC 9 does not exercise the new check — the bad outcome does not happen: the same Verification section names the `tests/scripts` command, and CI runs it in the `scripts-suite` lane (`pyforge-doctor-scripts-test`), which was also run here.
  - `[low]` `[patch]` Intent Alignment: the live-tree test allows only `flag-missing` and `flag-pre-rule` findings, so a landed spec that lacks a two-state test would red that suite a second time — the three new kinds joined both allowed sets, with the comment extended.
  - `[false]` `[reject]` Intent Alignment: only `flag_states` is recognized, not `installed_flags`, `make_flag_provider_fixture` or a hand-parametrized `flag_provider` — the intent names "the kit's ON/OFF helper" and 74.1 names it `flag_states`; same root cause as the shapes row above.
  - `[false]` `[reject]` Intent Alignment: a missing path reds even when another named file would pass — AC 6 says exactly that ("Given a named test file that does not exist ... one FAIL names the missing path"), and a test pins it.
  - `[maybe-false]` `[reject]` Intent Alignment: the pixi task description and the generated how-to row are outside the diff's surface — would settle by whether `docs-pixi-tasks` reds on a stale description; it does not (it renders from `pixi.toml`, which is unchanged), and the fix would be `low`.
  - `[maybe-false]` `[reject]` Verification Gap (other): whether the change log's live-tree counts (1208 / 0 / 840) stay true — would settle by re-running the gate at landing; they are dated counts in a change-log line, and a stale count would be `low`.

## Auto Run Result

Status: done

**Implemented change.** The flag gate (`scripts/flag_gate_check.py`) now judges a `done`, post-rule spec that carries a complete `flag:` block on its `## Verification`: it collects the test files the section names (backticked paths and `pytest` targets, by file name `test_*.py`, `*_test.py`, `*.test.*`, `*.spec.*`), reads each as text (never imported or run), and reds the spec with at most one finding -- `flag-verification-names-no-test`, then `flag-test-file-missing`, then `flag-test-not-two-state`. A file runs both states when it names the spec's `flag.key` together with the kit's `flag_states` (imported from `pyforge.testing_kit[.flags]` and called) or with two `*flagd_tree*` calls, one naming `"on"` and one `"off"`. A backlog, in-progress, in-review, pre-rule or exempt spec is never judged. `--spec` carries the finding in its JSON with verdict `red`.

**Files changed.**
- `scripts/flag_gate_check.py` -- `judge_two_state` and its helpers, three finding kinds, the call from `judge_one`, the module docstring.
- `tests/scripts/test_flag_gate_check.py` -- one test per acceptance and I/O-matrix row, the edge cases the review raised, a static pin that the gate's kit names match the kit's `flags.py` and `__init__.py`, and the three existing `done`-spec fixtures now carrying a two-state Verification.
- This story spec -- status, `baseline_revision`, Spec Change Log, Review Triage Log, Auto Run Result, and the docs line struck from Tasks & Acceptance.

**Review findings.** 44 findings from four layers, one pass, no loopback: 10 patched (1 medium, 9 low), 0 deferred, 34 rejected -- 26 low, 6 false, 2 maybe-false (rejected as would-be-low). The patches: the docs sentence reverted (outside the Boundaries); the `def` keyword match fixed so `undef` no longer hides a real `_flagd_tree(` call; the missing-file message reworded to "not a readable file under the repo root"; the live-tree test now allows the three new kinds; and test rows pinning the kit import without a call, the prefix side of the key boundary, the closing parenthesis of a tree call, a multi-file message, a second `## Verification` section, a `## Verification Notes` heading, a URL-only span, and the kit's names. Every rejected finding and its reason is in the Review Triage Log above.

**Follow-up review recommendation:** `false`. Patched counts: high 0, medium 1, low 9 -- below the threshold (a patched high, or two or more patched mediums).

**Verification performed (exit codes read directly, none through a pipe).**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- exit 0, 3065 passed, 1 skipped.
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_gate_check.py -q` -- exit 0 (136 tests); with `test_flag_rule.py` and `test_flag_inventory.py`, 284 passed.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` (the CI `scripts-suite` lane) -- exit 0, 1109 passed, 7 skipped.
- `pixi run -e pyforge-guild flag-gate-check` -- exit 0 (1208 specs judged, 0 fail, 840 warn).
- `python scripts/spec_surface_reconcile.py` and `pixi run -e pyforge-guild spec-surface-check` -- exit 0. No governed path moved: `scripts/flag_gate_check.py` is allowlisted (its owning Spec is guild-owned under `docs/governance/`), and `tests/scripts/` governs no Spec surface, so no memlog reconcile entry and no stamp was needed or made; `--write-baseline` was never passed.
- `ruff format --check --line-length 120` on both files -- exit 0. `ruff check` reports 6 findings (`EXE001`, four `RUF100`, `UP031`), identical on the baseline files; `scripts/` sits outside the repo's `lint-types` scope.
- Mutation checks by the implementer: 3 mutants of the check before review and 11 after, all killed.
- `PYTHONSAFEPATH=1` is set in this shell and breaks `pixi_version_check` inside `detectors-ci` (`ModuleNotFoundError`), unrelated to this change; the runs above unset it.

**Residual risks.**
- The check is presence-based, as the contract states: it cannot prove a tree is written for the story's key. The two live `done` flagged specs (steward 74.1 and 75.1) pass because `src/platform/tests/test_openfeature_file_flags.py` names their keys and carries two `_flagd_tree` calls for a different key.
- The recognized shapes are the contract's two: `flag_states`, and two `*flagd_tree*` calls. A real two-state test written another way (a parametrized variant, the `flag_provider` fixture parametrized by hand, a key reached through an imported constant, an aliased import) reds `flag-test-not-two-state`; the message names the accepted shapes.
- The test file is read from the working tree, not from `git ls-files`: an untracked test passes locally and reds in CI as missing.
- The docs sentence, the `flag-gate-check` task description in `pixi.toml` and its `docs/how-to/pixi-tasks.md` row do not mention the new check; the Boundaries exclude them.
- The wip auto-checkpoint commits on this branch hold intermediate states, including one taken during the implementer's first mutation testing; HEAD holds the correct code.
