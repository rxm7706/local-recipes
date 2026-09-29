---
title: '34.2: The flag gate ships in scripts, outside every station, and runs in detectors-ci'
type: 'feature'
created: '2026-09-28'
status: 'backlog'
flag-exempt: detector-or-gate   # a gated gate reports a silent green (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-1-the-flag-rule-has-a-closed-exemption-list-a-rule-date-baseline-and-one-block-shape.md
  - scripts/coverage_gate.py
  - scripts/detectors.py
  - src/platform/config/flags.json
  - src/shared/packages/pyforge-doctor/tests/meta/test_coverage_gate_stays_outside_every_station.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-feature-flag-governance` CAP-2 is the gate that makes the rule bite: from the rule date (2026-09-28)
`detectors-ci` reds a post-rule `type: feature` story spec that carries neither a `flag:` block nor a `flag-exempt:`
value, and it keeps the one tree (`src/platform/config/flags.json`, canopy:AD-11) honest. The gate judges all eight
Smiths, so under Charter §6 it cannot ship inside any of them — Doctor's included, because Doctor is constitutionally
advisory (the coverage-gate-independence resolution: `scripts/coverage_gate.py`, Story 24.1, pinned by Story 24.2's
meta-test). Marshal Story 74.2 will consult this gate at dispatch, so the gate also needs a one-spec interface.

**Approach:** `scripts/flag_gate_check.py` declares `DETECTOR = {"scope": "repo"}`, so `scripts/detectors.py` discovers it
and `detectors-ci` runs it; the `flag-gate-check` pixi task (guild tasks) invokes it. It reuses Story 34.1's
`scripts/flag_rule.py` for classification and the baseline, and reads the tree as JSON. Tree mode walks every tracked
`_bmad-output/projects/*/planning-artifacts/specs/spec-<E>-<S>-*.md` and the tree:
- **FAIL** (exit 1): a post-rule `type: feature` spec that is `neither`; a `flag-exempt:` value not on the roster; a spec
  whose frontmatter `status` is `done` and whose `flag.key` is not a key of the tree (a story still in backlog has not
  added its key yet, so only a landed one is judged); a tree key that no tracked file under `src/` or `scripts/` reads,
  excluding the tree itself, story specs, docs and tests.
- **WARN** (never a FAIL): a pre-rule `type: feature` spec that is `neither` (Ruling 3), grouped by station — the list
  Story 34.4's inventory counts.
- **Unknown** (exit 2): the tree, the roster or the baseline cannot be read — never green (fidelity-enforcement).

`--spec <path>` judges one story spec and prints one JSON object — `verdict` (`pass`, `warn` or `red`), `findings`,
`rule_date` — exiting 0 on `pass` or `warn`, 1 on `red`, 2 when it cannot judge. That object is the interface marshal Story
74.2's dispatch preflight consults. A meta-test in doctor's `tests/meta/` (and its companion copy under
`pyforge-core/tests/meta/`, Story 24.2's reason: the core suite runs on any single-station change) fails if any
`pyforge.<station>` module defines or imports the gate. The metadata checks (per-environment defaults, the 90-day clock)
are Story 34.3's; the two-state-test check is Story 34.5's.

Ledger key: `34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-34.1.

### Living CAP citations

- `spec-feature-flag-governance` CAP-2 (Guild-owned; Doctor as mechanism Smith — Epic 24's relay; no doctor CAP or FR).
- Kinship: marshal Story 74.2 (`spec-feature-flag-governance` CAP-3, consults `--spec`; minted `blocked` behind this
  story); `spec-coverage-gate-independence` CAP-1/CAP-3 (the same "outside every station" shape and its meta-test).

## Acceptance Criteria

- Given a fixture tree with a post-rule `type: feature` spec that carries neither When the gate runs Then it exits 1 with one FAIL naming the spec and the missing block
- Given the same spec listed in the baseline When the gate runs Then it exits 0 with one WARN naming it under its station
- Given `flag-exempt: someday` on any spec When the gate runs Then one FAIL names the unknown value
- Given a `done` flagged spec whose key the tree lacks When the gate runs Then one FAIL names the key; given the same spec at `backlog` Then no finding
- Given a fixture tree holding a test-local key (for example `pyforge.test.orphan`) that no file under the fixture's `src/` or `scripts/` mentions When the gate runs Then one FAIL names the key; given the same fixture with a fixture `src/` file that reads the key Then no finding
- Given the live tree at the landing SHA When the gate runs Then no orphan-key finding: every key it holds is read in `src/` (`pyforge.cutover_root` through `pyforge.core.cutover_root.CUTOVER_FLAG`; any other key the tree holds by then through its own reader). *(Amended 2026-09-29: this criterion named `pyforge.three_surfaces` on the live tree, and steward Story 76.4 removes that demo flag from the tree and from `src/` together, by operator ruling of 2026-09-28 (night). The orphan-key behaviour is now proven on a test-local fixture key, so the criterion holds whether 34.2 lands before or after 76.4.)*
- Given `--spec <path>` on each fixture When it runs Then it prints one JSON object with `verdict` `red`, `warn` or `pass` and exits 1, 0 or 0
- Given an unreadable tree, roster or baseline When the gate runs Then it exits 2 and reports what it could not read
- Given a planted `pyforge.<station>.flag_gate` module in a temporary tree When the meta-test runs Then it fails; on the real tree it passes
- Given the live tree at the landing SHA When `pixi run -e pyforge-guild flag-gate-check` runs Then it exits 0 (warnings allowed), and `pixi run -e pyforge-guild detectors-ci` reports no new finding against `main`
- Given the change When `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Ship the gate in `scripts/`, its tests in `tests/scripts/`, and nothing of it in any `pyforge.<station>` package.
- Read the exemption list and the baseline through `scripts/flag_rule.py` (Story 34.1), never a second copy.
- Register the `flag-gate-check` task in `pixi.toml` and regenerate `environment.yaml` in the same change
  (`pixi project export conda-environment -e build > environment.yaml`); add the script's allowlist line to
  `scripts/spec_surface_allowlist.txt`; record the new paths in the Guild Spec's `.memlog.md` via `memlog.py`.
- Leave the tree at zero FAIL at the landing SHA: a post-rule spec that lacks both is named in the landing PR and
  reported to its owning Smith, never exempted by this story.

**Never:**
- Do not import `pyforge.doctor` or any station's internals from the gate.
- Do not read `.steward/flags.json`: steward Story 76.3 folds that second tree into the one tree.
- Do not add a second PR verdict: the gate is one row of `detectors-ci`.
- Do not edit `SPEC.md`, `sprint-status-ledger.yaml` or the roster's list; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| new feature, no block | post-rule, `neither` | FAIL | exit 1 |
| backlog feature, no block | pre-rule, `neither` | WARN under its station | exit 0 |
| `fix` / `chore` / `docs` | any | nothing (Q1) | — |
| unknown exemption | `flag-exempt: later` | FAIL | exit 1 |
| landed, key missing | `done`, key not in tree | FAIL | exit 1 |
| not landed, key missing | `backlog`, key not in tree | nothing | — |
| orphan tree key | no reader in `src/` or `scripts/` | FAIL | exit 1 |
| one spec | `--spec <path>` | one JSON object | exit 0/1/2 |
| unreadable input | tree, roster or baseline | the input named | exit 2 |

</intent-contract>

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-2 and its rulings (memlog 3 and 23),
`docs/dreams/feature-flag-governance.md`, and the coverage-gate-independence precedent (doctor Stories 24.1 and 24.2),
decomposed 2026-09-28 (night) as Epic 34's mint.

## Binding

Parent Spec capability: `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-2 (Guild-owned; Doctor as mechanism
Smith).
Dream: `docs/dreams/feature-flag-governance.md` § Realization log → *2026-09-28 (night)*.
Ledger key: `34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci`.
Ledger status at mint: `backlog`.
Policy: `marshal-policy.toml` `[epic_surfaces]` `"34"`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild python -m pytest tests/scripts/test_flag_gate_check.py tests/scripts/test_flag_rule.py -q` — expected: pass.
- `pixi run -e pyforge-guild flag-gate-check` — expected: exit 0 on the landing tree (WARNs allowed).
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass (the companion meta-test).

## Review Triage Log
