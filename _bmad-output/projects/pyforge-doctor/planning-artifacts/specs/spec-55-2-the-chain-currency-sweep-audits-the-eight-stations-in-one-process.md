---
title: "55.2: The chain-currency sweep audits the eight stations in one process"
type: 'fix'
created: '2026-10-27'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py
  - scripts/chain_currency_sweep_check.py
  - pixi.toml
---

<intent-contract>

## Intent

**Problem:** The sweep is eight interpreter start-ups: `_audit` (`scripts/chain_currency_sweep_check.py:54-60`) runs `python -m pyforge.doctor.sources chain-completeness --layers --project <slug>` per station, and each one re-imports `fleet_scan`. 48.9 s in CI for work that is seconds in-process — and AD-1 says a Doctor source is a library call, never a subprocess reimplementation.

**Approach:** Call the gatherer the subprocess called: `board.gather_chain_layers_audit(target, project)` already saves and restores `generate.py`'s globals per call, so a sequential in-process loop is safe. The JSON shape the script filtered is `Finding.to_json_dict()`, the same serializer `__main__` printed. Keep the subprocess path only as a fallback when the import fails (the script runs in `pyforge-guild`, where `pyforge.doctor` is declared), and keep the exit-code domain.

Ledger key: `55-2-the-chain-currency-sweep-audits-the-eight-stations-in-one-process`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **spec-pyforge-doctor CAP-20 (the sweep detector) under AD-1 (library, not subprocess) and AD-2 (the closed exit-code space).**
- **`spec-pyforge-steward:CAP-175`** — the preflight and a PR's CI answer within a measured budget, and a station suite runs once, as its package-local and live-tree halves; doctor's part of its fleet, measured and ruled 2026-10-27 (D1–D4 in that Spec's `.memlog.md`).
- **`spec-pyforge-doctor` AD-1, AD-2, AD-5** — a Doctor source is a library call; the exit-code space is closed; `run_git` is the one subprocess site.

## Acceptance Criteria

- **AC1 — Same verdict.** `python scripts/chain_currency_sweep_check.py --json` emits the same `findings` and `errors` as the subprocess form at the baseline commit, for all eight stations and for `--project <slug>`.
- **AC2 — One process.** A test monkeypatching `board.gather_chain_layers_audit` sees eight calls and no `subprocess.run`; a test making the import fail sees `errors` name the station and exit 2.
- **AC3 — Time.** `chain_currency_sweep_check` reports ≤ 10 s in the `detectors` job of the landing PR.
- **AC4 — Exit codes.** 0 / 1 / 2 as documented; `--json` output shape unchanged.

## Boundaries & Constraints

**Always:**
- Keep every finding's shape and verdict; read every verdict from an exit code, never through a pipe.
- Keep `run_git` the one subprocess site for `git grep`; keep the exit-code space `{0, 2, 130}`.

**Never:**
- Never delete, skip or re-mark a test to meet a time; never narrow `doctor_paths` by hand (Story 98.1, rulings 2026-10-12); never hand-edit `SPEC.md`; never reimplement a Doctor source as a subprocess.

</intent-contract>

## Binding

- Parent capability: spec-pyforge-doctor CAP-20.

Parent: spec-pyforge-doctor CAP-20

- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-27 (the repo-scope detectors and the doctor suite answer in seconds) entry.
- Epic: Epic 55, minted with this story.
- Ledger key: `55-2-the-chain-currency-sweep-audits-the-eight-stations-in-one-process`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."55"`.
- Minted 2026-10-27 in one chain commit beside steward Epic 117 (the preflight and CI budget effort).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild python scripts/chain_currency_sweep_check.py --json` — expected: exit 0 and the same findings as before.
- `pixi run --frozen -e pyforge-guild scripts-lib-test` — expected: pass (the new test file listed in `scripts-lib-test.txt`).

**Run before the push:**
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: built in PR #2331 (2026-10-27): `_audit` calls `board.gather_chain_layers_audit(REPO_ROOT, slug)` in-process (stdout preamble swallowed, `Finding.to_json_dict()` rows filtered as before); an unimportable `pyforge.doctor` or a raising audit is COULD NOT RUN per station; `tests/scripts/test_chain_currency_sweep_check.py` added. The eight-station sweep measured 16.9 s locally (48.9 s in CI before).

## Spec Change Log

- 2026-10-27: minted from the station Dream's entry of 2026-10-27 beside steward Epic 117 (spec-pyforge-steward:CAP-175).

## Review Triage Log

- (none yet)
