# Test durations for the sharded CI matrix (steward Story 117.10, CAP-175)

`pytest-split` reads `<station>.json` here to cut a station suite into N groups of equal wall time
(`PYTEST_ADDOPTS="--splits N --group K --durations-path tests/durations/<station>.json"` in the
`pyforge-station-tests.yml` matrix). Without a file it splits by test count and says so; the shards still
cover every test. There is one file per task: `pyforge-steward.json` for the package half, `pyforge-steward-live.json`
for the live half, and likewise for doctor's live half, marshal, atlas and herald. Herald's file serves both its
halves. The local preflight runs every suite unsharded and never reads these files.

**Write a file the way the CI shards read it** (steward Story 117.25). Write it from empty, under xdist with four
workers, as the CI runner runs the task, into a new path, then copy it here:

```bash
PYTEST_XDIST_AUTO_NUM_WORKERS=4 PYTEST_ADDOPTS="--store-durations --durations-path=/tmp/new/pyforge-steward-live.json" \
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
```

The reasons for each step:

- **Under xdist.** With `--dist loadgroup`, xdist appends `@<group>` to the id of each test that has an
  `xdist_group` mark before pytest-split splits. A file written without xdist keys those tests by their bare ids,
  so on CI they miss the file and count at its average duration.
- **From empty.** `--store-durations` merges into the file it reads, so keys of tests that are gone, or of
  groups that were renamed, stay.
- **Herald.** Herald's file takes two runs into the one new path, `pyforge-herald-test` and then
  `pyforge-herald-live-test`. Both run after `pixi run -e site docs-site-install`, with `HERALD_DOCS_SITE_REQUIRED=1`;
  without the install the built-site tests skip and record nothing.

**What a file cannot fix.** A shard's wall time is at least its heaviest xdist group on one worker, its longest
single test, and its start-up. pytest-split balances a shard's summed durations, not those. A CI run that printed
every live test's time (2026-11-27, `--durations=0 --durations-min=0`) showed it for three lanes: a split from the
runner's own times left each one's longest shard unchanged. Steward's trigger-map module is more than a quarter of its
lane, so it always spans two shards, and marshal's and doctor's longest single tests set their shards. Each file here was
written on 2026-11-26 (steward Story 117.25). Refresh a file the same way after a suite gains or loses many tests,
one task at a time with nothing else running. `tests/scripts/test_durations_files.py` fails when the workflow names a
file that is missing or empty, or when a file is left here that no job names.
