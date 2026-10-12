---
name: "the-local-pr-preflight-marshal-lane-pyforge-marshal-test-can"
description: "A test that passes everywhere but the local pr-preflight lane is usually reading the lane: preflight names each lane'…"
metadata:
  type: feedback
---

A test that passes in CI and in a bare local run but fails in every local `pr-preflight` run is usually reading
something the preflight lane changes. Two things differ there: `pr-preflight` names each lane's scratch directory
after the lane (`TMPDIR` and `--basetemp` under `…/<lane-task>/…`, so `tmp_path` contains the lane name, e.g.
`pyforge-marshal-test`), and every lane runs from the Guild environment, so Guild tools (`doctor`, `codegraph`) are
on PATH, beside about twenty parallel lanes on a few xdist workers each.

Found 2026-10-12 (marshal Story 98.1): (1) `test_dispatch_verification.py`'s `PackagingFailProcess` failed any
argv whose joined text contained `pyforge-marshal-test`; under the preflight that matched the worktree path in a
`git` call, and the verdict read `refused`. (2) The two NFR-P1 tests timed `marshal seed check` end to end, about 4 s
of it `bmad-loop --version` and `copier --version` probes (plus a Doctor subprocess when `doctor` is on PATH), which
parallel load stretched past 5 s. The first diagnosis, an xdist-order cache leak, was wrong: bare, `-n auto`,
two-worker and Guild-PATH runs all passed.

**How to apply:** reproduce with `--basetemp=<dir>/<lane-task>/bt` and the Guild bin on PATH before blaming order or
load; make fakes match argv tokens exactly, never substrings of the joined command; in a timing test, stub any probe
that is not what the test claims to measure. Until such a fix lands, push with `PYFORGE_PREFLIGHT_SKIP=1` and a
`PYFORGE_PREFLIGHT_SKIP_REASON` naming the tests and the proof (journaled to `.steward/preflight-skips.log`), after
running every lane the red one cancelled.
