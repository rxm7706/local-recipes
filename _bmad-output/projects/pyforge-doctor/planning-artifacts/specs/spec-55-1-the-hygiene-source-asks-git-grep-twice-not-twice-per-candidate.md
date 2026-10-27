---
title: "55.1: The hygiene source asks git grep twice, not twice per candidate"
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

**Problem:** `bmad-output-hygiene` is the slowest repo-scope detector (189.6 s in CI on 2026-10-27; 190–1486 s locally), and the time is one function: `_has_inbound_references` (`hygiene.py:383-392`) runs `git grep -l --fixed-strings -e <path>` and `git grep -l -E '\b<basename>\b'` over the whole tree for each of ~119 non-conventional candidates — ~238 full-tree greps whose answers could come from two.

**Approach:** Batch the two greps across candidates: `-f <patterns-file>` carries every path (first pass) and every basename (second pass, `-w --fixed-strings`, the literal equivalent of `\b…\b` for the escaped basename), `-o` prints `<file>:<match>` so the index knows which pattern each file matched, and the two scopes (`()` then `--untracked --no-exclude-standard`) are kept as `_grep_other_paths` keeps them. `_has_inbound_references(target, repo_relpath)` stays as the one-candidate reading over the same index so no caller changes. Verdict logic (`is_orphan_file`) is untouched.

Ledger key: `55-1-the-hygiene-source-asks-git-grep-twice-not-twice-per-candidate`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **spec-pyforge-doctor CAP-42 (the fleet-wide hygiene sweep; its orphan-file class) and CAP-43 (findings reported, never auto-applied).**
- **`spec-pyforge-steward:CAP-175`** — the preflight and a PR's CI answer within a measured budget, and a station suite runs once, as its package-local and live-tree halves; doctor's part of its fleet, measured and ruled 2026-10-27 (D1–D4 in that Spec's `.memlog.md`).
- **`spec-pyforge-doctor` AD-1, AD-2, AD-5** — a Doctor source is a library call; the exit-code space is closed; `run_git` is the one subprocess site.

## Acceptance Criteria

- **AC1 — Same verdicts.** On the live tree at the story's baseline commit, `python -m pyforge.doctor.sources bmad-output-hygiene --json` emits the same findings (check, status, message, evidence) before and after the change, for every station.
- **AC2 — Bounded calls.** With 50 synthetic non-conventional candidates in a real git fixture, the source makes at most four `git grep` invocations (a `run_git` spy counts them); `test_sources_hygiene.py` asserts it.
- **AC3 — Unevaluable.** When `git grep` raises `CliBridgeError`, every pending candidate still gets its `orphan-file-unevaluable` WARN with the same message shape.
- **AC4 — Time.** `bmad-output-hygiene` reports ≤ 10 s in the `detectors` job of the landing PR (`scripts/detectors.py` prints per-detector seconds).

## Boundaries & Constraints

**Always:**
- Keep every finding's shape and verdict; read every verdict from an exit code, never through a pipe.
- Keep `run_git` the one subprocess site for `git grep`; keep the exit-code space `{0, 2, 130}`.

**Never:**
- Never delete, skip or re-mark a test to meet a time; never narrow `doctor_paths` by hand (Story 98.1, rulings 2026-10-12); never hand-edit `SPEC.md`; never reimplement a Doctor source as a subprocess.

</intent-contract>

## Binding

- Parent capability: spec-pyforge-doctor CAP-42.

Parent: spec-pyforge-doctor CAP-42

- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-27 (the repo-scope detectors and the doctor suite answer in seconds) entry.
- Epic: Epic 55, minted with this story.
- Ledger key: `55-1-the-hygiene-source-asks-git-grep-twice-not-twice-per-candidate`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."55"`.
- Minted 2026-10-27 in one chain commit beside steward Epic 117 (the preflight and CI budget effort).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass.
- `pixi run -e pyforge-guild bmad-output-hygiene-check` — expected: exit 0 in ≤ 10 s.

**Run before the push:**
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: built in PR #2331 (2026-10-27): `_check_orphan_files` collects the candidates that survive the conventional-name pre-filter and asks `_inbound_reference_index` once — one `git grep -a -z --fixed-strings` per scope with every path and basename as a `-e` pattern (Doctor writes no patterns file: `test_read_only_guard.py`), the per-candidate verdict decided on the returned lines with the same two tests; `_has_inbound_references` kept as the one-candidate reading. `bmad-output-hygiene` measured 3.0 s locally (190 s in CI before).

## Spec Change Log

- 2026-10-27: minted from the station Dream's entry of 2026-10-27 beside steward Epic 117 (spec-pyforge-steward:CAP-175).

## Review Triage Log

- (none yet)
