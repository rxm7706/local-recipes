---
title: "117.13: The herald job builds on the checkout's filesystem"
type: 'fix'
created: '2026-11-04'
status: 'done'
baseline_revision: 'f604a1ab86'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - .github/workflows/pyforge-station-tests.yml
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** `herald-test (2)` on PR #2360 failed 11 tests and errored 14 with `EXDEV: cross-device link not permitted`. Its
built-site tests point Astro's output at pytest's temp dir, and Astro `rename`s `docs-site/.astro/` there, which cannot cross
filesystems. The same job passed on runner image `ubuntu-26.04` 20261025.179.1 and failed on 20261101.64.1, so the new image
puts `/tmp` on another filesystem. No diff caused it: `main`'s next herald run would have failed the same way. An operator
laptop with `/tmp` on tmpfs has hit the same error since 2026-10.

**Approach:** set `TMPDIR` to `runner.temp` on the job's built-site step. `runner.temp` is `/home/runner/work/_temp`, beside
the checkout on one filesystem and outside the repo tree. It goes on the step because a job-level `env` cannot read the
`runner` context. A `fix` under CAP-175: no CAP, no flag.

Ledger key: `117-13-the-herald-job-builds-on-the-checkout-s-filesystem`. Type / Effort / Deps: fix / XS / —.

## Acceptance Criteria

- **AC1 — The build lands.** `herald-test` passes on PR #2360 with no `EXDEV` in its log.
- **AC2 — One line of CI.** Only the built-site step's `env` changes; no test, task or Astro config moves.

## Boundaries & Constraints

- The laptop path stays `TMPDIR=$HOME/.cache/pyforge-preflight-tmp`, set by the operator; this story is the CI job only.

## Binding

- spec-pyforge-steward CAP-175; Epic 117. The fix lands at `done`.

## Verification

```bash
gh pr checks 2360 --repo rxm7706/local-recipes
```

</intent-contract>

## Spec Change Log

- 2026-11-04: minted `done` from PR #2360's CI, where the new runner image blocked the merge; landed in that PR.
- 2026-11-04: AC1 is proved by this PR's own `herald-test` run, which a spec cannot cite because its own commit starts that
  run. The local half is the full preflight, which runs the same built-site tests with `TMPDIR` on the checkout's filesystem;
  they fail with the same `EXDEV` when `TMPDIR` is on the laptop's tmpfs.
