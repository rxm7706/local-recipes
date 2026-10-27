# Test durations for the sharded CI matrix (steward Story 117.10, CAP-175)

`pytest-split` reads `<station>.json` here to cut a station suite into N groups of equal wall time
(`PYTEST_ADDOPTS="--splits N --group K --durations-path tests/durations/<station>.json"` in the
`pyforge-station-tests.yml` matrix). Without a file it splits by test count and says so; the shards still
cover every test. Write a file from a full local run with
`PYTEST_ADDOPTS="--store-durations --durations-path tests/durations/pyforge-steward.json" pixi run -e pyforge-steward pyforge-steward-test`
(one file per task: `pyforge-steward.json` for the package half, `pyforge-steward-live.json` for the live half, and
likewise for doctor's live half, marshal, atlas and herald). The local preflight runs every suite unsharded and never
reads these files.
