---
title: 'pyforge-steward — Retrospective (2026-10-27: CAP-175 Waves 1 and 2, the preflight and CI budget)'
project: pyforge-steward
created: '2026-10-27'
updated: '2026-10-27'
scope: 'Epic 117 Stories 117.1, 117.2, 117.3, 117.4 and 117.7 (PRs #2331 and #2332, merged 2026-10-27) and the doctor relays 55.1–55.4 beside them. Story 117.4 registered the live_tree marker in the package pyproject.toml, so the code stage moved on 2026-10-27 (`code→retro` currency edge); this is the retrospective that follows it, covering the effort since the 2026-09-20 retro.'
evidence:
  - 'PR #2331 (3b4c04d058) and PR #2332 (0101b8a553): pixi.toml, scripts/coverage_gates_ci.py, .github/workflows/pyforge-station-tests.yml, src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py, preflight_xdist.py, pyproject.toml, 113 live_tree-marked test modules'
  - '.steward/preflight-runs.jsonl (every worktree): full pr-preflight median 670 s before; 772 s for 40 lanes after, the wall equal to its longest lane'
  - 'Actions API, heads 84481970c1 / 284bd10325 / a4da08aa01: runner-minutes 106 -> 94; steward-test 503 s -> 106 s + 245 s; doctor-test 456 s -> 60 s + 121 s; wall 784 s -> 764 s'
---

## What the effort set out to do

Epic 71 (CAP-159) had the preflight under a minute on 2026-09-27; by 2026-10-27 a full run took eleven minutes at the
median and a PR's CI thirteen, and nothing had said so. CAP-175 named four rulings (D1–D4) and eight stories. Waves 1
and 2 built five of them: the steward suite under xdist (117.1), the coverage gate reading its own suite's run and
`coverage-gates.yml` retired (117.2), critical-path admission (117.3), the live-tree split (117.4, with doctor 55.4),
and CI hygiene (117.7). Doctor took its half on its own chain (55.1 hygiene greps 190 s → 3 s, 55.2 chain-currency
in-process, 55.3 the worker share from the caller).

## What the measurements said

- The suites fell where the stories aimed: `pyforge-steward-test` 698 s serial → 62 s + 108 s locally, 503 s → 106 s +
  245 s in CI; doctor 456 s → 60 s + 121 s; `detectors` 343 s → 130 s; runner-minutes per head 126 → 94.
- The local preflight's wall is now its longest lane (772 s for 40 lanes against `test-ci` 768 s), not a queue.
- The PR wall barely moved (784 s → 764 s): it is set by the CFE serial suite, the image builds and their "free
  runner disk" steps, serial herald, and the `changes` gate ahead of every station job — lanes outside these waves.
  The repository is public, so runner minutes are free and the wall is the only cost. That reading became the
  second 2026-10-27 Dream entry and Stories 117.10–117.12.

## What worked

- Measuring first, from the journals and the Actions API, and amending the Dream with the table before any story.
  The path-filter idea the first draft carried was wrong (Story 98.1's arrays are derived; narrowing them reds
  `steward-test`); the split kept the contract and still cut the fan-out.
- One convention for the live-tree half — the `live_tree` marker, registered in each package's `pyproject.toml` — and
  the trigger map filtering each half's derivation by that marker, so the package half's outside reads are asserted
  empty rather than declared.
- One PR carrying several stations' stories with every chain complete (118 story keys promoted through the feeds).

## What hurt

- The scoped spec-surface stamp reconciles a drifted path only when the memlog names it in full; a grouped memlog line
  reconciled nothing, and 113 marked modules needed their paths spelled out.
- A new flag must join three shipped-flag tables (core's `test_flags.py` twice, the platform's
  `test_openfeature_file_flags.py`); the local preflight never runs the platform suite, so only Platform CI caught it.
- A preflight test assumed the laptop's sixteen cores and red on the four-core runner (`'4' == '16'`); the OFF path
  now reads the injected core count and the test derives its expectation from the same input.
- `estate reconcile` appended a stray memlog line and failed its own scoped stamp; the reconcile was redone by hand.
- A backgrounded shell whose first token was `cd <worktree> &&` still ran a later `git` in the primary checkout; nothing
  landed there, but every background git now carries an explicit `cd` and a printed `pwd`.

## Strategy convergence

CAP-175 stays steward's: the preflight, the CI shape and the station workflow are the estate the factory stands on.
The per-station xdist and split stories (herald, mason, atlas, scribe, warden, core) stay on their own chains, as the
Dream entry lays out; the remaining steward stories (117.5, 117.6, 117.8, 117.9, 117.10–117.12) are ordered by payoff
in the second Dream entry: D1 first, then the shallow gates, the shards, the platform suite.

## What to carry forward

- Name every drifted path in full in a surface-reconcile memlog event; the stamp's refusal prints the exact list.
- Inject core counts and derive expectations from the same input; never read the machine in a test's expectation.
- Count a new flag's tables before pushing: two in core, one in the platform.
- Measure the wall per PR head from the Actions API, not the runner-minutes, on a public repository.
