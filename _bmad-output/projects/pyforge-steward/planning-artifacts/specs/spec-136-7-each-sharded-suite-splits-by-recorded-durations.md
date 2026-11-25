---
title: '136.7: Each sharded suite splits by recorded durations'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 136-7-each-sharded-suite-splits-by-recorded-durations
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'tests/durations/**'
  - '.github/workflows/pyforge-station-tests.yml'
  - 'pixi.toml'
  - 'environment.yaml'
  - 'tests/scripts/**'
  - 'scripts/**'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-cutover-2026-11-10-11`. `pyforge-station-tests.yml` passes `--durations-path tests/durations/<task>.json` to six sharded jobs (`pyforge-atlas`, `pyforge-doctor-live`, `pyforge-herald`, `pyforge-marshal`, `pyforge-steward`, `pyforge-steward-live`), and `tests/durations/` holds only its README, so pytest-split splits every one of them by test count.

**Approach:** Write each of the six files from one full unsharded run of the task the job runs, with `PYTEST_ADDOPTS="--store-durations --durations-path tests/durations/<task>.json"`, in that task's own environment, one run at a time (the machine runs one heavy suite at a time). Confirm from the workflow which pixi task each job runs before running it. Add a test that every `--durations-path` the workflow names exists and is a non-empty JSON object, so a seventh sharded job cannot name a missing file. Update the README to say how a file is refreshed.

Ledger key: `136-7-each-sharded-suite-splits-by-recorded-durations`.

### Living CAP citations

- spec-pyforge-steward CAP-175 (each station half runs as N shards sized by time; realized, no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never write a durations file by hand or from a sharded run.
- Never run two full suites at once on this machine.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-cutover-2026-11-10-11` reports that the workflow names six durations files and none exists
**When** each file is written by one full unsharded run of its task with `--store-durations`
**Then** `tests/durations/` holds a non-empty durations file for every `--durations-path` the workflow names, and a test fails when the workflow names one that is missing or empty
**And** no shard count or workflow command changes, the README says how a file is refreshed, and the row reads resolved

- **AC1 — Every named durations file exists and holds timings.** Expected: exit 0.

  ```bash
  python3 -c "import json,pathlib,re,sys; w=pathlib.Path('.github/workflows/pyforge-station-tests.yml').read_text(); names=sorted(set(re.findall(r'--durations-path (tests/durations/[\\w.-]+\\.json)', w))); bad=[n for n in names if not pathlib.Path(n).is_file() or not json.loads(pathlib.Path(n).read_text())]; print(names, bad); sys.exit(1 if bad or not names else 0)"
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 (each station half runs as N shards sized by time; realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 136, minted with this story.
- Ledger key: `136-7-each-sharded-suite-splits-by-recorded-durations`.
- Deferred-work row: `DW-steward-cutover-2026-11-10-11`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."136"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.
- 2026-11-25: reproduced on the unchanged tree: `ls tests/durations/` listed `README.md` only, while `.github/workflows/pyforge-station-tests.yml` names six files.
- 2026-11-25: written by the session lead, one full unsharded run per task with `PYTEST_ADDOPTS="--store-durations --durations-path tests/durations/<file>.json"`, one suite at a time, each in its own environment and each read from its exit code: `pyforge-steward-test` exit 0 (2,208 timings), `pyforge-steward-live-test` exit 0 (1,943), `pyforge-doctor-live-test` exit 1 (1,538), `pyforge-marshal-test` exit 0 (13,812), `pyforge-herald-test` then `pyforge-herald-live-test` into the one file the herald job names, both exit 0 (2,360), `pyforge-atlas-test` exit 0 (3,080). The doctor run's one failure was `test_live_sources_docs_shelf.py::test_live_repo_gather_is_clean`, which read the tree while another agent's skill regeneration was mid-write; the module exits 0 on a rerun here and on main, and a failed test still records its timing, so the file is kept.
- 2026-11-25: added `tests/scripts/test_durations_files.py`: it fails when the workflow names a durations file that is missing, empty or malformed, and when a file is left that no job names (4 passed). The README says how a file is refreshed. No shard count or workflow line changed. The AC command exits 0.
- 2026-11-25: closed. Implemented, independently reviewed against this spec (a read-only reviewer over the whole diff), its findings applied; the deferred-work row or rows are closed in their ledgers by the session lead, and the full local `pr-preflight` gates the PR that lands it (branch `named-blocker-rows-2026-11-25`).
- 2026-11-25: session lead, on the operator's ask of this date: `tests/durations/pyforge-doctor-live.json` is rewritten from a clean unsharded run of `pyforge-doctor-live-test`, exit 0, after the station-skill rebuilds of Story 136.10 had finished (1,542 timings); the earlier file came from a run with one failing test that read the tree mid-rebuild.
