---
title: "34.6: A flag key shared by several done stories is judged against the latest one"
type: 'fix'
created: '2026-10-07'
status: 'done'
baseline_revision: 'b36482389641efd2591a9d5b5c8a883bcafcf746'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-3-the-flag-gate-reads-the-tree-metadata-per-environment-defaults-and-the-90-day-clock.md
  - scripts/flag_gate_check.py
  - scripts/flag_rule.py
  - scripts/flag_inventory.py
  - tests/scripts/test_flag_gate_check.py
  - docs/reference/story-spec-flag-block.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the flag gate reds an earlier `done` story spec when a later story changes the per-environment value of
the flag key both declare.

- **The predicate.** `judge_spec_env_defaults` (`scripts/flag_gate_check.py`, about :381-:417, Story 34.3) takes every
  `done` story spec that carries a `flag:` block and compares its `flag.default` for each environment with the value
  the tree renders (`flags.json` plus `flag-overlays.json`). A mismatch is `flag-default-env-mismatch` (FAIL).
  `judge_one` calls it for each spec on its own, in tree mode and in `--spec` mode.
- **Why keys are shared.** A story spec is a permanent record of what its story shipped, and the flag-block convention
  is one flag per CAP, so several stories under one CAP carry the same key. Measured on `966b166f76`: steward 74.1 and
  74.2 (`pyforge.steward.object_store_consumer`), herald 29.1 and 29.2 (`pyforge.herald.deck_publish`), herald 30.1
  and 30.2 (`pyforge.herald.deck_viewer`), marshal 85.1, 85.2 and 85.3 (`pyforge.marshal.verify_fix_loop`) and seven
  marshal 87.x specs (`pyforge.marshal.preserve_refs`). All of them belong to one station each.
- **The live failure.** Steward 74.1 shipped `pyforge.steward.object_store_consumer` off everywhere; 74.2 turns it on
  in dev and staging and registered those values in `src/platform/config/flag-overlays.json`. With that overlay and
  74.2's `done` spec in the tree (both from `37800e84e5`), `flag_gate_check.py` on `966b166f76` reports two
  `flag-default-env-mismatch` FAILs on 74.1's spec (`dev: off`, `staging: off` against `on`) and exits 1. The 74.2
  branch cleared them only by rewriting 74.1's `flag.default` with a Spec Change Log line (`37800e84e5`): a
  historical record edited to satisfy a check.

**Approach:** judge a shared key against its latest declaration only.

- Within one station, a key's **declarations** are the `done` story specs of that station whose `flag:` block names
  it. The **latest** is the one with the highest story key: the epic number, then the story number, read from the
  `spec-<epic>-<story>-` filename and compared as integers (`87-11` follows `87-3`). Story keys within a station are
  minted in order, and a later story under one CAP builds on the earlier one (74.2 depends on 74.1).
- `judge_spec_env_defaults` judges only the latest declaration of a key. An earlier `done` spec's `flag.default` is
  history and yields no `flag-default-env-mismatch`.
- A key exactly one `done` spec declares is judged exactly as today. A key declared by `done` specs of more than one
  station has no order between stations, so each declaration is judged as today (a finding, never a silent pass). A
  spec that is not `done` is not a declaration and never supersedes one.
- `--spec <path>` reads the other tracked story specs to find the latest declaration, so it reports the same
  `flag-default-env-mismatch` findings for that spec as tree mode does.
- `docs/reference/story-spec-flag-block.md` gains one sentence: when several stories share a key, each spec's
  `default` records what its story shipped, the gate judges the tree against the highest-numbered `done` spec of the
  station, and an earlier spec is never rewritten to match.

Ledger key: `34-6-a-flag-key-shared-by-several-done-stories-is-judged-against-the-latest-one`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-feature-flag-governance` CAP-2 (the gate; Story 34.3's per-environment clause, "a `done`
  flagged spec whose declared per-environment `default` disagrees with the tree's value for that environment"). Doctor
  is the mechanism Smith (Epic 34's relay); the Guild Spec's memlog enumerates the story. This is a defect of shipped
  behaviour, so it mints no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag, and the gate itself is exempt
  (`detector-or-gate`).
- **Origin.** Steward Story 74.2's landing on 2026-10-07.

## Acceptance Criteria

- Given a fixture tree with station specs `spec-74-1-…` (`done`, key K, `{production: off, staging: off, dev: off}`)
  and `spec-74-2-…` (`done`, key K, `{production: off, staging: on, dev: on}`), and a tree rendering K on in dev and
  staging and off in production When the gate runs in tree mode Then there is no `flag-default-env-mismatch`.
- Given the same fixture with the tree rendering K off everywhere When the gate runs Then `flag-default-env-mismatch`
  names `spec-74-2-…` for `dev` and `staging`, and nothing names `spec-74-1-…`.
- Given the same fixture When `--spec spec-74-1-…` runs Then its JSON verdict carries no `flag-default-env-mismatch`;
  and `--spec spec-74-2-…` reports the same findings tree mode reports for it.
- Given `spec-87-3-…` and `spec-87-11-…`, both `done` with key K and different defaults When the gate runs Then the
  `87-11` declaration is the one judged.
- Given a key one `done` spec declares When its `default` disagrees with the tree Then the finding and its message are
  exactly today's.
- Given two `done` specs of different stations that declare one key When either disagrees with the tree Then each
  disagreeing spec is reported, as today.
- Given a later spec that is not `done` (backlog, ready-for-dev, in-progress) sharing the key When the gate runs Then
  the earlier `done` spec is still the declaration judged.
- Given the live tree When `pixi run -e pyforge-guild flag-gate-check` runs Then it exits 0, and with
  `37800e84e5`'s `flag-overlays.json` and 74.2 spec placed over `966b166f76`'s 74.1 spec it also exits 0.
- Given `judge_spec_env_defaults` judging every `done` spec again (mutation) When the gate's tests run Then the first
  fixture fails.

## Boundaries & Constraints

**Always:**
- Fix it where the shipped behaviour lives: `judge_spec_env_defaults` and the path that feeds it in
  `scripts/flag_gate_check.py`.
- Keep `flag-default-env-mismatch`'s message text and every other finding kind, severity and message as they are.
- Keep `flag_inventory.py`'s reports byte-identical on the same tree (it reuses `judge_one`).
- Add the one sentence to `docs/reference/story-spec-flag-block.md`, keeping its `docs/map.yaml` row and
  `docs-currency` green.
- Record the surface on `docs/governance/spec-feature-flag-governance/.memlog.md` and reconcile any Spec
  `spec-surface-check` names, scoped stamps only (AGENTS.md pre-PR item 5).

**Never:**
- Never touch `docs/governance/flag-rule-baseline.json` or the rule date.
- Never read git history in the gate to order declarations; the order is the story key, so a fixture tree without git
  judges the same way.
- Never edit any station's story spec, `flags.json` or `flag-overlays.json` to make a finding pass. Whether steward's
  2026-10-07 amendment of 74.1's `flag.default` stays is steward's call, not this story's.
- Never import a `pyforge.<station>` module (Charter section 6; the Story 34.2 meta-test).
- Never weaken or delete an existing test.

## I/O & Edge-Case Matrix

| Declarations of key K (all `done` unless stated) | Tree renders | Judged | Finding |
|---|---|---|---|
| steward 74.1 off/off/off, 74.2 off/on/on | off/on/on | 74.2 | none |
| steward 74.1 off/off/off, 74.2 off/on/on | off/off/off | 74.2 | 74.2: dev, staging |
| only 74.1 off/off/off | off/on/on | 74.1 | 74.1: dev, staging (as today) |
| marshal 87.3 off/off/off, 87.11 off/on/on | off/on/on | 87.11 | none |
| a herald spec and a steward spec declaring one key (none today) | either disagrees | both | each disagreeing spec (as today) |
| 74.1 done, 74.2 backlog | off/on/on | 74.1 | 74.1: dev, staging |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-07 (detector gaps) entry.
- Epic: Epic 34 (a fix joins its own epic, which reopens; Story 41.5).
- Ledger key: `34-6-a-flag-key-shared-by-several-done-stories-is-judged-against-the-latest-one`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Guild Spec: `docs/governance/spec-feature-flag-governance/.memlog.md` records the CAP-2 → 34.6 mapping; no contract
  change, `SPEC.md` untouched.
- Minted 2026-10-07 with Story 6.13, in one chain commit. Epic 34's `[epic_surfaces]` entry already admits every path
  above.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_gate_check.py -q` — expected: pass.
- `pixi run -e pyforge-guild flag-gate-check` — expected: exit 0 on the landing tree.
- Probe: place `37800e84e5`'s `src/platform/config/flag-overlays.json` and steward 74.2 spec over a tree whose 74.1
  spec declares off everywhere, run `python scripts/flag_gate_check.py` — expected: exit 0 (exit 1 with two
  `flag-default-env-mismatch` FAILs on `966b166f76`). Restore both files with `git checkout --`.
- Mutation: judge every `done` spec again and re-run the gate's tests; the first fixture fails. Restore it.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Review Triage Log

### 2026-10-07 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - (no actionable findings after self-review against intent contract and matrix audit)

## Auto Run Result

Status: done

**Summary.** The flag gate now compares per-environment `flag.default` to the tree only for the latest `done` declaration of each `(station, flag key)` pair (highest `spec-<epic>-<story>-` numeric key). Earlier `done` specs on the same key are historical; cross-station keys are still judged per station; non-`done` specs never supersede.

**Files changed**
- `scripts/flag_gate_check.py` — `env_default_judge_targets`, wiring in tree and `--spec` mode
- `scripts/flag_inventory.py` — same target set when reusing `judge_one`
- `tests/scripts/test_flag_gate_check.py` — Story 34.6 AC and I/O matrix coverage
- `docs/reference/story-spec-flag-block.md` — shared-key sentence for authors
- `docs/governance/spec-feature-flag-governance/.memlog.md` — surface reconcile entry

**Review.** No patches, deferrals, or rejections.

**Follow-up review recommendation:** false

**Verification**
- `pytest tests/scripts/test_flag_gate_check.py` — 152 passed
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 3448 passed, 1 skipped
- `pixi run -e pyforge-guild flag-gate-check` — exit 0
- `python scripts/spec_surface_reconcile.py` — exit 0
- Two consecutive `flag_inventory` runs — byte-identical (steward report spot-check)

**Governed paths reconciled (memlog)**
- `scripts/flag_gate_check.py`
- `scripts/flag_inventory.py`
- `tests/scripts/test_flag_gate_check.py`
- `docs/reference/story-spec-flag-block.md` (co-governor: spec-34-1 story spec surface; guild memlog names both)
