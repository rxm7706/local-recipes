# Test durations for the sharded CI matrix (steward Story 117.10, CAP-175)

`pytest-split` reads `<station>.json` here to cut a station suite into N groups of equal wall time
(`PYTEST_ADDOPTS="--splits N --group K --durations-path tests/durations/<station>.json"` in the
`pyforge-station-tests.yml` matrix). Without a file it splits by test count and says so; the shards still
cover every test. There is one file per task: `pyforge-steward.json` for the package half, `pyforge-steward-live.json`
for the live half, and likewise for doctor's live half, marshal and its live half, atlas, atlas's live half (Story
117.28), warden (Story 117.38) and herald. Herald's file serves both its halves. `platform.json` serves Platform CI's
test job (Story 117.23), whose paths run from `src/platform`. The local preflight runs every suite unsharded and never
reads these files.

**Write a file from the runner's own times** (steward Story 117.35). A laptop's times are not the runner's: on
2026-11-27 the runner took 1.6 times the laptop's seconds for steward's live half, 0.46 times a stale file's for its
package half, and two to three times for herald's built-site tests, so a split balanced on a laptop is not balanced
on CI. To write the files:

1. On a scratch branch, add `--durations=0 --durations-min=0` to each sharded job's `PYTEST_ADDOPTS` (and to an
   unsharded job you mean to shard), push it, and dispatch the workflow on it (`gh workflow run
   pyforge-station-tests.yml --ref <branch>`; `platform-ci.yml` likewise). Never merge that branch.
2. From each job's log, read every `<seconds>s <setup|call|teardown> <test id>` line, and sum each test id's three
   phases, as `pytest-split --store-durations` does. Merge the shards of one task into one file.
3. Write it as `pytest-split` writes its own: `json.dump(durations, f, sort_keys=True, indent=4)`, seconds to two
   places, no trailing newline.

Score a new file before trusting it: split each task's pytest segments (each `&&` part of the task is its own
`pytest` run, split on its own) by the old file and by the new one, in collection order, as `duration_based_chunks`
does, and sum each group's runner seconds. On 2026-11-27 that reproduced the probe's shards to the second.

**The laptop method** (steward Story 117.25) still writes a usable file when no probe run exists. Write it from empty,
under xdist with four workers, as the CI runner runs the task, into a new path, then copy it here:

```bash
PYTEST_XDIST_AUTO_NUM_WORKERS=4 PYTEST_ADDOPTS="--store-durations --durations-path=/tmp/new/pyforge-steward-live.json" \
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
```

- **Under xdist.** With `--dist loadgroup`, xdist appends `@<group>` to the id of each test that has an
  `xdist_group` mark before pytest-split splits. A file written without xdist keys those tests by their bare ids,
  so on CI they miss the file and count at its average duration. The runner's printed ids carry the same suffix.
- **From empty.** `--store-durations` merges into the file it reads, so keys of tests that are gone, or of
  groups that were renamed, stay.
- **Herald.** Herald's file takes two runs into the one new path, `pyforge-herald-test` and then
  `pyforge-herald-live-test`. Both run after `pixi run -e site docs-site-install`, with `HERALD_DOCS_SITE_REQUIRED=1`;
  without the install the built-site tests skip and record nothing.

**What a file cannot fix.** A shard's wall time is at least its heaviest xdist group on one worker, its longest
single test, and its start-up. pytest-split balances a shard's summed durations, not those. On the runner a shard's
wall time follows its summed seconds (marshal's four shards: about 0.7 s of wall per summed second, plus a little per
test), so a balanced sum is a balanced shard where no single module or test dominates. Steward's trigger-map module is
more than a quarter of its live half, so it always spans two shards, and each shard derives what it needs. A probe
that prints only tests over 0.3 s (as one did on 2026-11-27) cannot score a split: every shorter test counts at the
average. Refresh a file after a suite gains or loses many tests. `tests/scripts/test_durations_files.py` fails when the
workflow names a file that is missing or empty, or when a file is left here that no job names.
