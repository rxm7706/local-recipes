---
title: The dossier is the source and Pages is a render
type: feature
created: '2026-09-13'
status: done
baseline_revision: 907c1cc233106973948c48976e9438d6c2d85917
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md'
  - '{project-root}/docs/dreams/pyforge-herald.md'
deferred:
  - summary: 'Sprint ledger key `22-1-the-dossier-is-the-source-and-pages-is-a-render` still reads `backlog` although the capability it tracks (spec-pyforge-pages CAP-1..5) was verified shipped on `main` via PR #1341/#1351, merged before this Story was minted.'
    evidence: '`pyforge.core.landing_evidence`''s recognized grammars (GitHub PR branch keyed to the story slug, bmad-loop merge subject, `Story N.M:` commit subject, `land/<station>-<epic>-<seq>` branch) do not match branch `pyforge-pages`, so automatic landing detection never promoted the key past `backlog` in either the tracked ledger or the Tier-3 feed.'
    location: '_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml'
    severity: low
declared_low_risk: false
---
<intent-contract>

## Intent

**Problem:** The public Pages tree publishes `docs/dashboard/` (Kedro-Viz at `kedro-viz/`). The PyForge dossier lives only as a published artifact, so the site and the dossier drift. Landing the incoming bundle without a Story would skip the contract and leave foundry with nothing to rebuild.

**Approach:** Realize `spec-pyforge-pages` CAP-1..5 in one PR: rebase `pyforge-pages.bundle` onto `origin/main`, keep `feature.site` off the `-e build` export, build the site in `dashboard.yml` into `docs/dashboard/`, never add a second `deploy-pages`.

## Boundaries & Constraints

**Always:**
- One Pages deployment. `dashboard.yml` is the only `deploy-pages` caller.
- `build.py` deletes only the outputs it owns.
- `pixi project export conda-environment -e build > environment.yaml` is byte-identical.
- `maintenance` label.
- After 54.5, foundry re-derives this surface; same CAP-N; no `_bmad-output` rsync.

**Never:**
- Second Pages workflow.
- `verify_claims.py` in `detectors-ci`.
- Blanket `rmtree` of `docs/dashboard/`.
- Lane 1 `/console/` replacement.
- Story 44.4 fold.

## Tasks & Acceptance

**Execution:**
- Rebase bundle commits onto this worktree.
- Confirm `environment.yaml` unchanged.
- `pixi run -e site site-check`.
- Open PR with `maintenance`.

**Acceptance Criteria:**
- `site-check` green.
- `environment.yaml` `git diff` empty after `-e build` export.
- `dashboard.yml` still the sole `deploy-pages` caller; Kedro-Viz path unchanged.
- Dream `specified`, Spec `ready`, ledger key `22-1-the-dossier-is-the-source-and-pages-is-a-render` present.

</intent-contract>

## Verification

**Verified (2026-09-18, this worktree, baseline `907c1cc233`):** the target capability
(spec-pyforge-pages CAP-1..5, folded into `spec-pyforge-herald` CAP-43..47) was **already fully
realized and merged to `main` before this Story was minted** — PR #1341 "Publish the PyForge
dossier as the Pages landing page" (merged 2026-09-13T19:24:33Z) and PR #1351 "Drop the Fleet
scorecards from the PyForge dossier" (merged 2026-09-14T01:02:40Z), both from branch
`pyforge-pages` (the rebased bundle) and both carrying the `maintenance` label. `docsite/`,
`pixi.toml`'s `feature.site`, and `.github/workflows/dashboard.yml`'s build step in this worktree
are byte-identical to `origin/main` (`git diff origin/main HEAD -- docsite/ pixi.toml
.github/workflows/dashboard.yml` empty) — the worktree's other divergence from `origin/main` is
unrelated in-flight work from other stories on this shared bmad-loop branch, out of this Story's
scope. No code changes were needed or made. Re-ran every Acceptance Criterion fresh:
- `pixi run -e site site-check` → exit 0, "checks passed — 6 required outputs, 10 infographics"
  (includes the CAP-47 artifact-shell body-only check).
- `pixi project export conda-environment -e build > environment.yaml` → byte-identical to the
  committed copy (`diff` empty); `feature.site` confirmed absent from the `build` environment's
  feature list (`build = ["python", "build"]`).
- `grep -rl 'deploy-pages@' .github/workflows/` → `dashboard.yml` only; `kedro-viz-publish.yml`
  stages to `docs/dashboard/kedro-viz/` and never deploys, matching the intended pattern.
  `docs/dashboard/kedro-viz/` unchanged.
- `docs/dreams/pyforge-herald.md` (the Dream that now covers `pyforge-pages`, per the 2026-09-17
  one-chain fold) is `status: specified`; `spec-pyforge-herald/SPEC.md` is `status: ready` and
  lists `docs/dreams/pyforge-pages.md` under `covers-dreams`; the sprint ledger key
  `22-1-the-dossier-is-the-source-and-pages-is-a-render` is present in both
  `planning-artifacts/sprint-status-ledger.yaml` and the Tier-3
  `implementation-artifacts/sprint-status.yaml` feed.
- `docsite/build.py`'s cleanup is an explicit allow-list (`shutil.rmtree(target)` /
  `target.unlink()` over enumerated owned outputs only) — confirmed no blanket
  `docs/dashboard` rmtree.
- `verify_claims.py` does not appear in `python scripts/detectors.py --scope repo --list`
  (the `detectors-ci` task) — its only repo references are `dashboard.yml` (CI, advisory,
  `continue-on-error: true`) and the `site-verify` pixi task.

**Residual/risk (not fixed here, flagging for the operator):** the sprint-status ledger's
`22-1-the-dossier-is-the-source-and-pages-is-a-render` key still reads `backlog` in both the
tracked ledger and the Tier-3 feed. `sprint-status-ledger.yaml` is a GENERATED file
("do not hand-edit"; regenerate via `sprint-ledger-sync`, which promotes from the Tier-3 feed —
it does not recompute status from git). The likely reason automatic landing-evidence detection
(`pyforge.core.landing_evidence`) never marked it done: PR #1341/#1351 merged from branch
`pyforge-pages`, which predates this Story's key and matches none of that module's recognized
grammars (GitHub PR branch keyed to the story slug, bmad-loop merge subject, `Story N.M:` commit
subject, `land/<station>-<epic>-<seq>` branch). This is a landing-evidence gap for
pre-convention work, not a defect in this Story's own deliverable; left for the operator/doctor
`story-status-check` pass to reconcile rather than hand-edited here.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 6 findings — high 0, medium 2, low 2, false 2, maybe-false 0
- findings:
  - `[medium]` `[patch]` Residual ledger-key drift (ledger `backlog` vs. verified-shipped) is documented only as prose in `## Verification`, not in the structured `deferred:` frontmatter field, so `deferred_work_intake.py`'s sweep never surfaces it — confirmed `deferred-work-ledger.md` has no `22-1` entry. Action: add a `deferred:` entry recording the stale ledger key.
  - `[false]` `[reject]` `followup_review_recommended` should be `true` so a follow-up pass reconciles the stale ledger key. Refutation: that flag re-engages this same bmad-build-auto review loop over the same frozen intent-contract; it cannot write `sprint-status-ledger.yaml` (orchestrator-owned, explicitly off-limits to this workflow per this run's own invocation), so a follow-up pass would not resolve the named risk.
  - `[medium]` `[patch]` Frontmatter `context:` still points at `spec-pyforge-pages/SPEC.md` and `docs/dreams/pyforge-pages.md`, both folded 2026-09-17 into `spec-pyforge-herald`/`docs/dreams/pyforge-herald.md`; confirmed `spec-pyforge-pages/SPEC.md` is now a disposed redirect stub ("Derived SPEC body disposed"). A future context reload for this spec would load the stub instead of the live governing spec. Action: repoint `context:` to the live files.
  - `[low]` `[patch]` The Verification prose's "unrelated Epic 21 deck-registry work" characterization of the worktree's divergence from `origin/main` is incomplete — confirmed `git diff origin/main HEAD --stat` also shows unrelated doctor/marshal spec removals, `docs/governance/guild-roster.json`, `docs/dreams/pyforge-charter.md`, `scripts/fleet_picture.py`, and spec-surface baseline/allowlist changes. Action: generalize the wording so it doesn't misstate scope.
  - `[false]` `[reject]` This Story's own upcoming PR should be checked for the `maintenance` label. Refutation: no PR exists yet for this diff — step-04 does not push or open a PR (that happens later in the external bmad-loop landing flow), so there is no labeling outcome this diff could get wrong.
  - `[low]` `[reject]` The spec doesn't narrate that its own Verification section was already relocated once out of the sealed `<intent-contract>` block (a prior self-correction). Rejected: git history (`fix(herald): move Story 22.1's verification notes...`) already documents this; adding narrative here is more than a direct correction for negligible reader benefit.

## Auto Run Result

**Summary:** Story 22.1's target capability (`spec-pyforge-pages` CAP-1..5, folded into `spec-pyforge-herald` CAP-43..47) was already fully implemented and merged to `origin/main` — PR #1341 and PR #1351, both `maintenance`-labeled — before this Story's Dream/Spec/Story were minted (an "express mode" bundle import per `spec-pyforge-pages/.memlog.md`). This dispatch made no code changes; it independently re-verified every Acceptance Criterion and Boundary/Constraint against the live worktree, recorded that verification, and closed out the Story's own paper trail.

**Files changed:** `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-22-1-the-dossier-is-the-source-and-pages-is-a-render.md` only (frontmatter status/baseline tracking, an added `## Verification` section, an added `## Review Triage Log`, this section) — no application code, config, or workflow files.

**Review findings breakdown (6 findings, 1 review pass):**
- Patched (3): stale `deferred:` frontmatter (added an entry so the residual ledger-key drift is machine-discoverable); stale `context:` pointers (repointed from the disposed `spec-pyforge-pages`/`pyforge-pages.md` stubs to the live `spec-pyforge-herald`/`pyforge-herald.md` successors); inaccurate "Epic 21 deck-registry work" characterization of unrelated worktree divergence (reworded to a general, accurate statement).
- Rejected as false (2): `followup_review_recommended` should be `true` to fix the ledger — false, that flag re-runs this same review loop, which cannot write the orchestrator-owned `sprint-status-ledger.yaml`. This Story's own PR should be checked for the `maintenance` label — false, no PR exists yet for this diff; labeling happens later in the external landing flow.
- Rejected as low/not-worth-fixing (1): the spec doesn't narrate its own prior self-correction (moving content out of the sealed `<intent-contract>` block) — git history already documents this; not worth the added narrative.

**Follow-up review recommendation: `true`.** Two `medium` entries were patched this pass (the threshold for a first-pass follow-up). Named unverified risk: the new `deferred:` frontmatter entry was confirmed *discoverable* by directly calling `pyforge.doctor.sources.chain.discover_spec_frontmatter_deferrals()`, but the end-to-end `deferred_work_intake.py` sweep (which promotes discovered entries into the tracked `deferred-work-ledger.md`) was not actually run against this spec — so whether it round-trips into the ledger as expected is unverified.

**Verification performed:** `pixi run -e site site-check` (exit 0, 6 required outputs + 10 infographics green); `pixi project export conda-environment -e build > environment.yaml` (byte-identical, confirmed via `diff`); `grep -rln deploy-pages .github/workflows/` (only `dashboard.yml`); Dream (`docs/dreams/pyforge-herald.md`, `status: specified`) and Spec (`spec-pyforge-herald/SPEC.md`, `status: ready`, CAP-43..47 mapped from `spec-pyforge-pages` CAP-1..5) read directly; sprint-ledger key presence confirmed in both the tracked ledger and Tier-3 feed; `docsite/build.py` cleanup logic read directly (explicit allow-list, no blanket `rmtree`); `verify_claims.py` confirmed absent from `detectors-ci` and marked `continue-on-error: true` in `dashboard.yml`; PR #1341/#1351 labels confirmed live via `gh pr view --json labels`. After patching: frontmatter re-parsed with `yaml.safe_load` (clean), both new `context:` paths confirmed to exist and resolve to the live documents, and the `<intent-contract>` block confirmed byte-identical to its pre-patch state via whole-line-anchored diff.

**Residual risks:** the sprint-status ledger key remains `backlog` (orchestrator-owned; explicitly out of this workflow's writable scope per this run's own invocation instructions) — now captured in the `deferred:` field for the operator/doctor `story-status-check` pass to reconcile. The `deferred_work_intake.py` end-to-end round-trip is unverified (see follow-up recommendation above).
