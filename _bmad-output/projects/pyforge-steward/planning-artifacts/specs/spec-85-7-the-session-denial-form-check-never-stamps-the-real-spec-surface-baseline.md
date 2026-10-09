---
title: "85.7: The session-denial form check never stamps the real spec-surface baseline"
type: 'fix'
created: '2026-10-08'
status: 'ready-for-dev'
baseline_revision: '488837c504cb46ebf973c50e337af5623fafac13'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-85-6-every-command-a-session-denial-names-as-the-sanctioned-form-exists.md
  - tests/scripts/test_session_denial_forms.py
  - docs/governance/guild-roster.json
  - scripts/spec_surface_check.py
  - scripts/worktree_sweep.py
  - pixi.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 85.6's check learns whether a script accepts a flag by running the script, so the scripts suite
stamps steward's spec-surface baseline in whatever checkout runs it.

- **The probe.** `_script_accepts_argv` (`tests/scripts/test_session_denial_forms.py:109`) runs
  `[sys.executable, str(script), *argv]` with `cwd=REPO_ROOT` (`:112`-`:117`) and counts the argv accepted unless the
  combined output contains `unrecognized arguments` or `invalid choice:` (`:119`). An accepted argv therefore runs the
  script's whole body, and a script that crashes, or exits before it parses, is also counted accepted.
- **The span that writes.** The roster's `spec-surface-bare-write-baseline` reason
  (`docs/governance/guild-roster.json:374`) names `python scripts/spec_surface_check.py --write-baseline --spec
  <project>/<spec>`, and `_PLACEHOLDERS` (`:27`-`:33`) fills `<project>/<spec>` in as
  `pyforge-steward/spec-pyforge-steward` (`:30`). `spec_surface_check.py` parses at `:557` (`ap.parse_args()`) and
  then stamps: `_stamp_baseline` (`:612`) takes the `.lock` sidecar (`:388`) and writes the baseline atomically
  (`os.replace`, `:411`).
- **Who runs it.** Three tests reach that span through the live roster:
  `test_live_roster_session_denial_forms_resolve` (`:225`), `test_broken_retire_form_in_reason_fails` (`:231`) and
  `test_historical_roster_with_retire_and_marshal_preserve_fails` (`:310`). They run in `pyforge-doctor-scripts-test`
  (`pixi.toml:825`, `-e pyforge-ci`), in CI's `Detectors / scripts-suite` (`.github/workflows/detectors.yml:89`) and in
  `pr-preflight`'s leg of it (`pixi.toml:1592`), which the `pre-push` hook runs. Every local push restamps the
  pushing checkout.
- **Measured.** In a fresh worktree of `488837c504`, one run of `test_live_roster_session_denial_forms_resolve`
  (`pixi run --frozen -e pyforge-ci python -m pytest
  tests/scripts/test_session_denial_forms.py::test_live_roster_session_denial_forms_resolve`) rewrote
  `scripts/.spec-surface-baseline.json` from 1,073,738 to 1,075,879 bytes, changing only the
  `pyforge-steward/spec-pyforge-steward` entry (its memlog hash and 35 file hashes), and created
  `scripts/.spec-surface-baseline.json.lock` (ignored, `.gitignore:780`). It was first seen on 2026-10-08 during
  marshal Story 69.1's fix, when the file's mtime moved after each of the three tests. A `git add -A` after a local
  test run commits a stamp nobody reconciled, the write AGENTS.md § Pre-PR item 5 allows only after a memlog entry and
  a `git add`.

**Approach:**

- **Probe the parser, not the script.** `_script_accepts_argv` runs a small bootstrap with `sys.executable -c`
  instead of the script. The bootstrap wraps `argparse.ArgumentParser.parse_args` and `parse_known_args` (and the two
  `*_intermixed_*` entry points) with a depth counter. argparse calls `parse_known_args` from `parse_args` and from
  each subparser (Python 3.14 `argparse.py`: `parse_args` → `self.parse_known_args`; `_SubParsersAction` →
  `subparser.parse_known_args`), so only the outermost call decides. When the outermost call returns, the bootstrap
  flushes stdout and stderr and ends the process with `os._exit(0)`, so nothing after the parse runs: not the body,
  not a `finally` block, not an `atexit` handler. An outermost `parse_known_args` that returns leftover arguments is a
  rejection: the bootstrap prints `unrecognized arguments: …` to stderr and exits 2, as `parse_args` would.
- **Run it as `python script.py` would.** The bootstrap sets `sys.argv = [script, *argv]`, puts the script's
  directory at `sys.path[0]`, then calls `runpy.run_path(script, run_name="__main__")`. A rejection is argparse's own:
  `error()` prints `unrecognized arguments` or `invalid choice:` and exits 2, and the probe reports it as today
  (`<script> rejects [...]`).
- **Accepted means the parse completed.** The probe reports an argv accepted only on the bootstrap's exit 0. If
  `run_path` returns, or raises `SystemExit`, before an outermost parse completes, the bootstrap exits 3 and the probe
  reports the script unprobeable, naming the script and the outcome. It is never counted accepted.
- **No argparse, no run.** Before it runs anything, the probe reads the script with `ast` and requires an
  `import argparse` or a `from argparse import …`. A script without one is reported unprobeable (a failure naming it)
  and is never executed.
- **Fixtures outside the repo.** The probe takes any script path. A script outside `REPO_ROOT` (a `tmp_path` fixture)
  is named by its path; today's `relative_to(REPO_ROOT)` in the rejection message raises for such a path.
- **What runs before the parse still runs.** Module top-level code, imports and parser construction execute as they
  do under `python script.py`; the contract covers everything after the parse. At `488837c504`,
  `spec_surface_check.py` (top level `:93`-`:107`) and `worktree_sweep.py` (`:57`-`:67`) only bind constants before
  they parse. Validation after the parse (`ap.error` following `parse_args`, e.g. `spec_surface_check.py:559`-`:565`)
  stays outside the probe, as Story 85.6's I/O matrix already says ("parser accepts both flags").

Ledger key: `85-7-the-session-denial-form-check-never-stamps-the-real-spec-surface-baseline`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-165 (FR-38) and CAP-5 (Story 63.3: "a one-line reason naming the
  sanctioned form"): Story 85.6's check proves that every command a denial names exists. Proving it must not perform
  it: a guardrail test that runs a scoped stamp does the write AGENTS.md § Pre-PR item 5 keeps for a reconcile. A
  fix of 85.6's check; it mints no CAP and changes no `SPEC.md` text.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag; the change is test code only.
- **Origin.** Found on 2026-10-08 during marshal Story 69.1's fix; re-measured on `488837c504` (above).

## Acceptance Criteria

- Given the live roster and `scripts/.spec-surface-baseline.json` When a new test probes `python
  scripts/spec_surface_check.py --write-baseline --spec pyforge-steward/spec-pyforge-steward` through the probe Then
  the probe reports the argv accepted, and the file's sha256 and `st_mtime_ns` are unchanged. The test restores the
  file's bytes if they ever change, so a red run leaves no stamp behind.
- Given a clean checkout When `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` runs Then it passes and
  `scripts/.spec-surface-baseline.json` is byte-identical afterwards (`git diff --exit-code` exits 0, mtime unchanged).
- Given a fixture script under `tmp_path` that imports argparse, adds `--known`, calls `parse_args()` and then writes
  a marker file When the probe runs it with `["--known"]` Then it reports accepted and the marker file does not exist.
- Given the same fixture When it is probed with `["--known", "--no-such-flag"]` Then the probe reports `rejects`,
  naming the flag, and the marker does not exist. And a fixture with a subparser is accepted for `["sub", "--known"]`
  without writing its marker and rejected for `["sub", "--known", "--bogus"]`; a fixture whose outermost call is
  `parse_known_args` is rejected for an unknown flag.
- Given a fixture script with no argparse import that writes a marker at import When the probe runs it Then it is
  reported unprobeable, naming the script, and the marker does not exist. And a fixture that imports argparse and
  exits 1 before it parses is reported unprobeable, never accepted.
- Given the change When `tests/scripts/test_session_denial_forms.py` runs Then every existing test passes and asserts
  what it asserted before: `--retire` and `--no-such-flag` still fail naming the flag, the missing script, the bad
  verb and the unclassified span still fail, and the live roster still resolves.
- Given today's direct `[sys.executable, script, *argv]` run put back into the probe When the new tests run Then the
  baseline test and the marker test fail; with the depth counter removed, the subparser case fails (mutation).

## Boundaries & Constraints

**Always:**
- Change only `tests/scripts/test_session_denial_forms.py`.
- Keep the probe stdlib-only: the file runs in the dependency-free `pyforge-ci` environment.
- Keep `unrecognized arguments` and `invalid choice:` as the rejection signal, so 85.6's failure messages hold.
- Write fixture scripts and their markers under `tmp_path`; nothing is written under the repository.

**Never:**
- Never change `docs/governance/guild-roster.json`, `.claude/hooks/pre-shell.py`, `scripts/spec_surface_check.py`
  or any other probed script; no reason text moves.
- Never drop the `spec_surface_check.py` span from the check, skip it, or special-case a script by name: the fix is in
  the probe and covers every script.
- Never let the body run somewhere else instead (a copied tree, a redirected `BASELINE`, an environment switch): the
  contract is that the body does not run.
- Never weaken or delete an existing test.
- Never commit `scripts/.spec-surface-baseline.json` in this story's diff. At `488837c504` no Spec's surface in the
  baseline names `tests/scripts/test_session_denial_forms.py`, so no reconcile or stamp is due.

## I/O & Edge-Case Matrix

| Script and argv | Probe result | Body runs |
|---|---|---|
| `scripts/spec_surface_check.py --write-baseline --spec pyforge-steward/spec-pyforge-steward` | accepted | no: baseline bytes and mtime unchanged |
| `scripts/worktree_sweep.py --retire example-branch` | rejects (`unrecognized arguments`) | no |
| `scripts/worktree_sweep.py --no-such-flag` | rejects | no |
| fixture: `parse_args()` then writes a marker; `--known` | accepted | no: marker absent |
| fixture: same; `--known --no-such-flag` | rejects | no |
| fixture with a subparser; `sub --known` | accepted (outermost parse) | no |
| fixture with a subparser; `sub --known --bogus` | rejects | no |
| fixture whose outermost call is `parse_known_args`; an unknown flag | rejects (leftover arguments) | no |
| fixture with no argparse import | unprobeable | never started |
| fixture that imports argparse and exits before it parses | unprobeable | top level only |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-08 (denial probe) entry.
- Epic: Epic 85 (CAP-165; `in-progress` while Story 85.5 is `blocked`).
- Ledger key: `85-7-the-session-denial-form-check-never-stamps-the-real-spec-surface-baseline`.
- Ledger status at mint: `backlog`.
- Deps: — (Story 85.6, the check this story fixes, is `done`).
- Spec: `spec-pyforge-steward/.memlog.md` records the mint; `SPEC.md` untouched.
- Governance: the roster, the hook's `MATCHERS` and every reason are unchanged.
- Surface: `tests/scripts/test_session_denial_forms.py` only. Epic 85's `[epic_surfaces]` entry already admits
  `tests/scripts/**`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_session_denial_forms.py -q` — expected: pass.
- Baseline unchanged: record `sha256sum scripts/.spec-surface-baseline.json` and `stat -c '%y %s'
  scripts/.spec-surface-baseline.json`, run `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` (expected:
  pass; the CI `scripts-suite` twin), and record both again — expected: identical, and
  `git diff --exit-code scripts/.spec-surface-baseline.json` exits 0.
- Mutation: put today's direct `[sys.executable, script, *argv]` run back into the probe and re-run the new tests;
  the baseline test and the marker test fail. Restore the probe and
  `git checkout -- scripts/.spec-surface-baseline.json`.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
