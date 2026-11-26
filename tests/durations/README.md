# Test durations for the sharded CI matrix (steward Story 117.10, CAP-175)

`pytest-split` reads `<station>.json` here to cut a station suite into N groups of equal wall time
(`PYTEST_ADDOPTS="--splits N --group K --durations-path tests/durations/<station>.json"` in the
`pyforge-station-tests.yml` matrix). Without a file it splits by test count and says so; the shards still
cover every test. Write a file from a full local run with
`PYTEST_ADDOPTS="--store-durations --durations-path tests/durations/pyforge-steward.json" pixi run -e pyforge-steward pyforge-steward-test`
(one file per task: `pyforge-steward.json` for the package half, `pyforge-steward-live.json` for the live half, and
likewise for doctor's live half, marshal, atlas and herald). The local preflight runs every suite unsharded and never
reads these files.

Each file here was written on 2026-11-25 (steward Story 136.7) from one full unsharded run of its task. Refresh a
file the same way after a suite gains or loses many tests, one suite at a time; herald's file takes two runs,
`pyforge-herald-test` then `pyforge-herald-live-test`, because one job runs both under the same options and
`--store-durations` merges into the file. `tests/scripts/test_durations_files.py` fails when the workflow names a
file that is missing or empty, or when a file is left here that no job names.
