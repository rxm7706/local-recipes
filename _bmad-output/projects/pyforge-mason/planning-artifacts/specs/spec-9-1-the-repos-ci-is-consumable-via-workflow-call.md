---
title: "The repo's CI is consumable via workflow_call"
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_revision: 'e96443e3c4c993302182938eca61a909131f6419'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** This repo's CI (`detectors.yml`, `staged-recipes-linter.yml`, etc.) only runs as
plain, repo-local Actions triggers. No workflow here is consumable by another repository via
`uses:`, so a second repo (named candidate: `conda-forge-tracker`) cannot reuse this repo's CI
logic, and an air-gapped fork has no vendorable copy.

**Approach:** Add one new, additive `on: workflow_call` reusable workflow that wraps the existing
staged-recipes-style PR linter (`.github/workflows/scripts/linter.py`, currently driven by
`staged-recipes-linter.yml`) with documented `inputs:`/`secrets:`, plus a same-repo selftest
workflow that consumes it via `uses:` to prove the contract works. `staged-recipes-linter.yml`
itself is left untouched.

## Boundaries & Constraints

**Always:**
- Additive only. Do not modify `staged-recipes-linter.yml`, `detectors.yml`, or any other
  existing ALWAYS-ON workflow -- a YAML mistake there breaks CI repo-wide, not just this PR.
- Reuse `staged-recipes-linter.yml`'s existing pinned actions
  (`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`,
  `mamba-org/setup-micromamba@ce51e99f4bb8a82ab7158c4dc59ef4634c59c4f9 # v3.1.0`) rather than new pins.
- Do not modify `linter.py`. It resolves `ROOT` as three parents up from its own file (line 18),
  and reads `ROOT/environment.yaml` + shells `pixi project export ...` (line 65) -- so it must run
  from `<repo-root>/.github/workflows/scripts/linter.py` in a repo that also has
  `pixi.toml`/`environment.yaml`. This is why consumers vendor the *script* at that exact path
  rather than the wrapper fetching it into an isolated subdirectory.
- The wrapper's header comment documents both consumption modes: (a) `uses:` cross-repo (consumer
  vendors `.github/workflows/scripts/linter.py` at the same relative path -- a one-file copy, same
  as any staged-recipes fork already does today), and (b) full vendoring (workflow file + script)
  for GitHub-egress-blocked consumers.

**Block If:** none -- self-contained additive change, no unresolved external dependency.

**Never:**
- No "63-family" centrally-maintained multi-repo workflow architecture (step workflows + entry
  points, Vault, Kaniko) -- `spec-reusable-cicd-workflows` keeps that parked; only the
  extension-contract socket ships here.
- Do not integrate `conda-forge-tracker` itself (separate, untouched sibling repo) -- named future
  candidate only.
- No `pull_request:`/`push:` triggers on the new wrapper file -- `workflow_call`-only (plus the
  selftest file's own `workflow_dispatch:`), so it never fires uninvited on this repo's own PRs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Same-repo selftest | `workflow_dispatch` with a real open PR number here | Selftest `uses:` the reusable workflow; it lints that PR, appends summary to `$GITHUB_STEP_SUMMARY` | N/A |
| Missing `pr-num` on `workflow_call` | Caller omits the required input | Actions rejects the run at dispatch time | Native validation error, not runtime failure |
| Caller omits `github-token` secret | No `secrets:` passed | Falls back to caller's automatic `secrets.GITHUB_TOKEN` | No error -- documented fallback |

</intent-contract>

## Code Map

- `.github/workflows/staged-recipes-linter.yml` -- reference only, not modified. Source of the
  action pins, `create-args`, and command line (`python .github/workflows/scripts/linter.py
  --repo=... --pr-num=...`, `GH_TOKEN` env) to mirror.
- `.github/workflows/scripts/linter.py` -- reference only. `--repo`/`--pr-num` are plain CLI args
  (repo-agnostic; only comments mention `rxm7706/local-recipes`). `ROOT` resolution (line 18) is
  the key constraint -- see Boundaries.
- `.github/workflows/test-all.yml` -- reference only. This repo's existing local precedent for a
  `workflow_dispatch` entry point that `uses:` `workflow_call`-only workflows
  (`test-linux.yml`/`test-windows.yml`/`test-macos.yml`) -- the selftest file follows this pattern.
- `.github/workflows/reusable-staged-recipes-linter.yml` -- NEW. The `workflow_call` wrapper.
- `.github/workflows/reusable-staged-recipes-linter-selftest.yml` -- NEW. `workflow_dispatch`
  entry point that `uses:` the wrapper, proving the contract against a real PR here.
- `.../pyforge-mason/planning-artifacts/specs/spec-reusable-cicd-workflows/SPEC.md` -- reference
  only. Governing "Extension contract" section states this story's exact mandate.

## Tasks & Acceptance

**Execution:**
- `.github/workflows/reusable-staged-recipes-linter.yml` -- create -- `on: workflow_call` with
  `inputs: pr-num (required, number), repo (optional, string, default ${{ github.repository }})`;
  `secrets: github-token (optional)`; same `permissions:` as `staged-recipes-linter.yml`; checkout
  + `mamba-org/setup-micromamba` steps mirroring its pins/`create-args`; a `lint` step running
  `python .github/workflows/scripts/linter.py --repo=${{ inputs.repo }}
  --pr-num=${{ inputs.pr-num }}` with `GH_TOKEN: ${{ secrets.github-token || secrets.GITHUB_TOKEN }}`,
  appended to `$GITHUB_STEP_SUMMARY`. Header comment documents both consumption modes and scopes
  out the 63-family shape.
- `.github/workflows/reusable-staged-recipes-linter-selftest.yml` -- create -- `workflow_dispatch`
  with required `pr-num` input; one job `uses: ./.github/workflows/reusable-staged-recipes-linter.yml`
  with `with: pr-num: ${{ inputs.pr-num }}` and job-level `permissions:`.

**Acceptance Criteria:**
- Given the new wrapper file, when parsed as YAML, then it parses cleanly and its `on:` block is
  exactly `workflow_call` with the documented `pr-num`/`repo` inputs and `github-token` secret.
- Given the selftest file, when parsed as YAML, then it parses cleanly and its job's `uses:` is
  the literal relative path `./.github/workflows/reusable-staged-recipes-linter.yml`.
- Given `staged-recipes-linter.yml`, `detectors.yml`, and every other pre-existing workflow, when
  compared to their pre-story content, then they are unchanged.
- Given the wrapper's header comment, when read, then it documents both the cross-repo `uses:`
  mode (naming `conda-forge-tracker`) and vendoring for air-gapped use, and states the 63-family
  architecture is out of scope.

## Design Notes

Rejected alternative: sparse-checkout `linter.py` into an isolated subdirectory at run time so a
consumer vendors nothing. Rejected because `linter.py`'s `ROOT` (three parents up from itself)
would then resolve inside that isolated checkout, not the calling repo's root, breaking its
`environment.yaml`/`pixi.toml` sync check. Vendoring the one script file at the conventional path
avoids touching `linter.py` and matches how staged-recipes forks already vendor this file today.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `3b519841c7` (2026-08-22, "Merge pull request #631 from rxm7706/mason/9-1-workflow-call-wrappers"); also `95f1db76aa` (2026-08-13, "Merge branch 'bmad-loop/20260813-094919-bfcb/9-1-findings-model-severity-types-remedies' i"). Ledger row `9-1-the-repos-ci-is-consumable-via-workflow-call: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.github/workflows/reusable-staged-recipes-linter-selftest.yml`, `.github/workflows/reusable-staged-recipes-linter.yml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
