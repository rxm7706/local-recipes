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
realized and merged to `main` before this dispatch began** — PR #1341 "Publish the PyForge
dossier as the Pages landing page" (merged 2026-09-13T19:24:33Z, ~2m23s *after* this Story's
Dream/Spec/Story were minted at 2026-09-13T19:22:10Z via commit `9afa3614` — not before it,
correcting an earlier draft of this note) and PR #1351 "Drop the Fleet scorecards from the
PyForge dossier" (merged 2026-09-14T01:02:40Z, genuinely after both), both from branch
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
pre-convention work, not a defect in this Story's own deliverable. No current detector covers
this exact gap shape: `story-status-check` (`pyforge.doctor.sources.story_status`) only audits
ledger rows already at `done` for landing evidence and never visits rows still at `backlog`, and
`status-body-consistency-check` only fires on a spec whose `status:` frontmatter line carries a
trailing `#` comment, which this file's `status:` line does not — verified live, both
`pixi run -e pyforge-guild story-status-check` and `pixi run -e pyforge-guild
status-body-consistency-check` exit 0 with no mention of this story or ledger key. The
`deferred:` frontmatter entry above is the tracked record of this gap pending a future
reconciliation (an orchestrator `sprint-ledger-sync` pass, or a new detector) — not hand-edited
here.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 6 findings — high 0, medium 2, low 2, false 2, maybe-false 0
- findings:
  - `[medium]` `[patch]` Residual ledger-key drift (ledger `backlog` vs. verified-shipped) is documented only as prose in `## Verification`, not in the structured `deferred:` frontmatter field, so `deferred_work_intake.py`'s sweep never surfaces it — confirmed `deferred-work-ledger.md` has no `22-1` entry. Action: add a `deferred:` entry recording the stale ledger key.
  - `[false]` `[reject]` `followup_review_recommended` should be `true` so a follow-up pass reconciles the stale ledger key. Refutation: that flag re-engages this same bmad-build-auto review loop over the same frozen intent-contract; it cannot write `sprint-status-ledger.yaml` (orchestrator-owned, explicitly off-limits to this workflow per this run's own invocation), so a follow-up pass would not resolve the named risk. (Frontmatter ends up `followup_review_recommended: true` anyway, but for an unrelated, mechanical reason — this pass patched two `medium` findings, the standard first-pass-follow-up threshold, independent of this rejected argument; see `## Auto Run Result`.)
  - `[medium]` `[patch]` Frontmatter `context:` still points at `spec-pyforge-pages/SPEC.md` and `docs/dreams/pyforge-pages.md`, both folded 2026-09-17 into `spec-pyforge-herald`/`docs/dreams/pyforge-herald.md`; confirmed `spec-pyforge-pages/SPEC.md` is now a disposed redirect stub ("Derived SPEC body disposed"). A future context reload for this spec would load the stub instead of the live governing spec. Action: repoint `context:` to the live files.
  - `[low]` `[patch]` The Verification prose's "unrelated Epic 21 deck-registry work" characterization of the worktree's divergence from `origin/main` is incomplete — confirmed `git diff origin/main HEAD --stat` also shows unrelated doctor/marshal spec removals, `docs/governance/guild-roster.json`, `docs/dreams/pyforge-charter.md`, `scripts/fleet_picture.py`, and spec-surface baseline/allowlist changes. Action: generalize the wording so it doesn't misstate scope.
  - `[false]` `[reject]` This Story's own upcoming PR should be checked for the `maintenance` label. Refutation: no PR exists yet for this diff — step-04 does not push or open a PR (that happens later in the external bmad-loop landing flow), so there is no labeling outcome this diff could get wrong.
  - `[low]` `[reject]` The spec doesn't narrate that its own Verification section was already relocated once out of the sealed `<intent-contract>` block (a prior self-correction). Rejected: git history (`fix(herald): move Story 22.1's verification notes...`) already documents this; adding narrative here is more than a direct correction for negligible reader benefit.

### 2026-09-18 — Review pass
- verdicts: 10 findings — high 0, medium 2, low 1, false 7, maybe-false 0
- findings:
  - `[false]` `[reject]` `review_loop_iteration` stays `0` despite a completed review pass having occurred. Refutation: the counter tracks `bad_spec` loopback iterations only (per workflow.md's own rule: incremented "before each bad_spec loopback"), not every review pass — no `bad_spec` routing has ever occurred for this story, so `0` is correct.
  - `[low]` `[patch]` The Review Triage Log's `[false][reject]` row against "`followup_review_recommended` should be `true`" reads as contradicting the frontmatter's actual `followup_review_recommended: true`, with the real reason (the two-medium-patches threshold) not appearing until `## Auto Run Result` several sections later. Action: appended a parenthetical to that row noting the flag is `true` anyway for the unrelated, mechanical threshold reason.
  - `[medium]` `[patch]` The Verification section's "already fully realized and merged to `main`... before this Story was minted" claim is backwards for PR #1341: the Story's Dream/Spec/Story were minted 2026-09-13T19:22:10Z (commit `9afa3614`), and PR #1341 merged 2026-09-13T19:24:33Z — about 2m23s *after* minting, not before. PR #1351 genuinely merged after both. Action: reworded the ordering claim to "before this dispatch began" and annotated PR #1341's actual timing relative to the mint commit.
  - `[false]` `[reject]` The `maintenance`-label evidence for PR #1341/#1351 is asserted in `## Verification` but its supporting check (`gh pr view --json labels`) is only disclosed in `## Auto Run Result` several sections later. Refutation: the evidence is present in the document, just not co-located; a reader auditing a `done` story is expected to read the full file, and there is no concrete harm named beyond needing to read further.
  - `[false]` `[reject]` `## Verification`, `## Review Triage Log`, and `## Auto Run Result` substantially duplicate the same facts three times. Refutation: this three-section shape is mandated by workflow.md's own step-04 Finalize instructions (Summary / files changed / findings breakdown / verification performed / residual risks, alongside the separate Verification and Triage Log sections) — not a choice this story's diff made, and restructuring the workflow template is out of this story's scope.
  - `[false]` `[reject]` The "two `medium` findings patched" first-pass follow-up threshold is asserted with no cited source. Refutation: that threshold is workflow.md's own mechanical Finalize rule ("On a first pass, `true` if any patched entry was `high`, or if two or more `medium` entries were patched") — a meta-rule of the review process itself, not a fact this story's spec needs to re-derive or cite.
  - `[false]` `[reject]` `status: done` [now `in-review`] is set while a `deferred:` entry (the stale ledger key) remains unresolved, in tension with this repo's "pre-existing findings: fix-now is the default" convention. Refutation: that convention's own carve-out permits deferral for "a named blocker" — the entry names one explicitly (`sprint-status-ledger.yaml` is orchestrator-owned, outside this workflow's writable scope), which is exactly the sanctioned pattern, not a violation.
  - `[false]` `[reject]` The diff shows `status: done` being set again immediately after a commit (`e6538e672a`) that had just reverted the same change, with no explanation. Refutation: this was an artifact of a diff-staging error by the orchestrating session — the diff handed to reviewers was generated as `git diff <baseline>..HEAD` (commit-to-commit), which omitted this session's own subsequent uncommitted `status: in-review` edit. Regenerated correctly as `git diff <baseline>` (baseline-to-working-tree); the corrected diff shows a clean `ready-for-dev` → `in-review` transition with no such double-flip.
  - `[medium]` `[patch]` (verification-gap, pre-verified) The Residual/risk prose names `story-status-check` as the mechanism that will reconcile the stale ledger key, but that detector only audits ledger rows already at `done` and never visits rows still at `backlog`; `status-body-consistency-check` only fires on a trailing-`#` status comment this file's `status:` line lacks. Neither detector covers this drift shape — verified live, both exit 0 with no mention of this story. Action: reworded both the Verification section and the Auto Run Result's Residual risks to stop naming `story-status-check` as the reconciling mechanism, stating plainly no current detector covers this gap shape.
  - `[false]` `[reject]` The frozen `<intent-contract>` block still names `spec-pyforge-pages`/`pyforge-pages.md`, both disposed/archived 2026-09-17 into `spec-pyforge-herald`/`pyforge-herald.md`, while frontmatter `context:` already points at the live successors. Refutation: per this repo's own convention ("historical prose keeps its original names — repoint live pointers only"), the sealed intent-contract is a frozen historical record and correctly retains its original names; the live pointer (`context:`) was already correctly updated in the prior pass. The intent-contract is also explicitly read-only, so even were this a defect it could not be patched here.

## Auto Run Result

**Summary:** Story 22.1's target capability (`spec-pyforge-pages` CAP-1..5, folded into `spec-pyforge-herald` CAP-43..47) was already fully implemented and merged to `origin/main` — PR #1341 and PR #1351, both `maintenance`-labeled — before this dispatch began (2026-09-18). This dispatch made no application-code changes; it independently re-verified every Acceptance Criterion and Boundary/Constraint against the live worktree, corrected two factual inaccuracies surfaced across two review passes, and closed out the Story's own paper trail. Governance note: an intermediate commit in this dispatch's history briefly hand-flipped the orchestrator-owned `sprint-status-ledger.yaml` to `done` for this story/epic; that commit was reverted (`e6538e672a`) before this review pass began, and the ledger remains untouched at `backlog`, as required.

**Files changed:** `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-22-1-the-dossier-is-the-source-and-pages-is-a-render.md` only, across this dispatch's full history (frontmatter status/baseline/deferred tracking, `## Verification`, `## Review Triage Log` across two passes, this section) — no application code, config, or workflow files. `sprint-status-ledger.yaml` was touched by an intermediate commit and then reverted; its final state is unchanged from baseline.

**Review findings breakdown (2 review passes, 16 findings total):**
- Pass 1 (6 findings): patched 3 (`deferred:` frontmatter entry; `context:` repoint off disposed stubs; generalized an inaccurate divergence-scope characterization); rejected false (2); rejected low/not-worth-fixing (1).
- Pass 2 (10 findings): patched 3 — `[low]` a triage-log/frontmatter coherence note; `[medium]` corrected a backwards PR-timing claim (PR #1341 merged ~2m23s *after*, not before, this Story's Dream/Spec/Story were minted at `9afa3614`); `[medium]` (verification-gap, pre-verified) corrected a claim that `story-status-check` would reconcile the stale ledger key — verified live that neither `story-status-check` nor `status-body-consistency-check` catches this drift shape. Rejected false (7): `review_loop_iteration` semantics (it tracks `bad_spec` loopbacks only), maintenance-label evidence placement (present, just not co-located), cross-section duplication (workflow-mandated shape, not this story's to restructure), an uncited workflow meta-rule (the threshold lives in workflow.md, not the spec), status-done alongside a named-blocker `deferred:` entry (the sanctioned deferral pattern), a diff-staging artifact from the orchestrating session (corrected before findings were rendered), and the frozen intent-contract retaining pre-fold spec/dream names (this repo's own historical-prose convention; the block is also read-only).

**Follow-up review recommendation: `true`.** This pass patched two `medium` findings (the first-pass follow-up threshold). Named unverified risk: the corrected claim that "no current detector covers this gap shape" (terminal spec status vs. non-terminal ledger row) was verified only against the two most-plausible detectors (`story-status-check`, `status-body-consistency-check`) — the full `detectors`/`pr-preflight` suite was not exhaustively swept for some other detector that might independently catch this drift.

**Verification performed:** Pass 1's checks — `pixi run -e site site-check` (exit 0, 6 required outputs + 10 infographics), `pixi project export conda-environment -e build > environment.yaml` (byte-identical), `grep -rln deploy-pages .github/workflows/` (only `dashboard.yml`), Dream/Spec status, sprint-ledger key presence, `docsite/build.py` cleanup logic, `verify_claims.py` absence from `detectors-ci`, PR #1341/#1351 label confirmation — were independently re-confirmed live by the orchestrating session at step-03's Verify stage and remain valid; no application code changed since. Pass 2 additionally verified: commit `9afa3614`'s timestamp (`git log --format=%ad --date=iso-strict`) against PR #1341's `mergedAt` (`gh pr view --json mergedAt`); `story-status-check` and `status-body-consistency-check` both re-run live (exit 0, no mention of this story); frontmatter re-parsed with `yaml.safe_load` after each patch; the `<intent-contract>` block confirmed byte-identical across all patches; `sprint-status-ledger.yaml` and the Tier-3 feed confirmed reverted to their pre-dispatch `backlog` values.

**Residual risks:** none remaining for this Story's own scope beyond the named follow-up risk above. Out-of-scope, pre-existing and unrelated: the herald Tier-3 feed (`implementation-artifacts/sprint-status.yaml`, gitignored) is stale on other keys unrelated to this story. The sprint-status ledger key for `22-1-...` remains `backlog` (orchestrator-owned; explicitly out of this workflow's writable scope) — tracked via the `deferred:` frontmatter entry, not hand-edited.
