---
title: 'Instance deploy definition (CAP-1)'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: '9c5d3aa94e3fc71107c6c036423a1f81396ce371'
context: []
warnings: ['oversized']
difficulty: ''
baseline_revision: '87b545cc520cd195dce944ee1f8981d9cc93a3df'
---

<intent-contract>

## Intent

**Problem:** `factory/lasuite.py`'s `LaSuiteClient`/`WikiSyncer` (Story 9.3) is proven end-to-end
against an in-memory `MockWagtail` but has no live server to talk to (deferred-work ledger DW-H3);
two open questions block even *defining* that server — the deployment substrate, and whether
DW-H1's PostgreSQL/MinIO is required.

**Approach:** Write the minimal-instance deploy definition — substrate, storage, the exact
Bearer-auth + four-route API surface, and air-gap requirements — resolving both open questions
with repo-local evidence, so Story 16.2's local rehearsal and the later ATTENDED DW-H3 bring-up
have a contract to build against instead of improvising one. No code changes; `factory/lasuite.py`
stays frozen and atlas grows no deploy code.

## Boundaries & Constraints

**Always:** `factory/lasuite.py` is read-only in this story — zero edits, zero diff. Endpoint +
token resolve only from `LASUITE_BASE_URL` / `LASUITE_API_TOKEN` env vars or a secret-mount —
never a hardcoded host or a committed credential. The definition must be air-gap-deployable:
package installs from a mirrored conda channel only, zero CDN references for static assets. The
four routes and Bearer-auth shape are restated exactly as `LaSuiteClient`/`MockWagtail` already
define them — no invented or changed shapes. The deliverable is documentation (this spec's Design
Notes + a small cross-reference update to the parent SPEC's Open Questions) — no deploy-automation
code anywhere in atlas's package tree.

**Block If:** No blocking decisions are anticipated — the substrate, storage, and route/auth facts
below are already resolved from repo-local evidence (existing recipes, the frozen client, the
parent SPEC). If re-verification during implementation shows `recipes/wagtail` or
`recipes/django-lasuite` no longer build, or django-lasuite is no longer listed on the real
conda-forge channel, HALT with blocking condition `deploy definition assumption invalidated`.

**Never:** Never execute or schedule the attended live bring-up itself (DW-H3 stays DEFERRED).
Never add an httpx opener or any HTTP client into `factory/lasuite.py` or elsewhere in atlas
package code (that is Story 16.2's scope, and even there the opener is constructed outside package
code). Never silently absorb the parent SPEC's non-goals (`wagtailsite`/`wagtailtables`/
`wagtailcharts`/`wagtailcolorpicker`, OIDC/django-allauth RBAC, DRF APIs, `BokehPanelPage`,
headless/multi-tenant mode). Never assert that django-lasuite's out-of-the-box REST API exactly
matches `MockWagtail`'s shape as a verified fact — that match is confirmed only at the attended
bring-up; this definition specifies the *required* shape, not a proof it already exists.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/lasuite.py` -- frozen contract this
  definition targets (`resolve_lasuite_config`, `LaSuiteClient`, `Opener` seam); read-only, not
  edited.
- `src/shared/packages/pyforge-atlas/tests/factory/test_lasuite.py` -- `MockWagtail`'s exact
  request/response shapes are the definition's acceptance shapes; read-only, not edited.
- `recipes/wagtail/recipe.yaml`, `recipes/django-lasuite/recipe.yaml`,
  `recipes/django-lasuite/SUITENUMERIQUE_SUMMARY.md` -- evidence for the substrate resolution
  (local Wagtail 7.4.1 recipe; django-lasuite 0.0.26 confirmed live on the real conda-forge
  channel); read-only, cited only.
- `docs/reference/enterprise-deployment.md` -- established air-gap / mirrored-channel /
  `*_BASE_URL` override conventions this definition reuses; read-only, cited only.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py`, `deploy.py`, `provision.py` --
  evidence that Steward currently exposes no deploy/credential-mint verb for an arbitrary external
  service (its real surface is the program-console dashboard + the `bmb` provision module); cited
  to support the Design Notes' credential-minting gap callout, read-only, not edited.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wagtail-corporate-brain/SPEC.md`
  -- parent SPEC; its `open_questions` (substrate, DW-H1 dependency) get a resolution
  cross-reference.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` -- DW-H3 entry
  gets a short annotation pointing at this story's resolution (status stays DEFERRED/ATTENDED).
- `_bmad-output/implementation-artifacts/spec-16-1-instance-deploy-definition.md` (this file) --
  houses the deploy definition itself, in Design Notes below.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/implementation-artifacts/spec-16-1-instance-deploy-definition.md` -- finalize
  the Design Notes below as the complete deploy definition (substrate, storage, API surface,
  air-gap requirements, credential-minting note, Steward-gap flag) -- this spec, once promoted to
  `planning-artifacts/specs/`, is the durable artifact Story 16.2 and the attended DW-H3 session
  build against.
- [x] `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wagtail-corporate-brain/SPEC.md`
  -- in `open_questions` (frontmatter list and the `## Open Questions` prose), mark the deployment
  substrate and DW-H1-dependency questions as resolved, each pointing at
  `spec-16-1-instance-deploy-definition.md` -- prevents the parent contract from reading as
  unresolved once the answer exists.
- [x] `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` -- append a
  short annotation to the DW-H3 entry noting the substrate/storage open questions are now resolved
  by S-16.1 (cite this spec's path), without changing DW-H3's `status` (it stays DEFERRED/ATTENDED
  until the live bring-up runs and passes) -- keeps the ledger's own "buildable half shipped,
  attended half deferred" pattern intact and traceable.

**Acceptance Criteria:**
- Given the frozen `LaSuiteClient` contract and `MockWagtail`'s route shapes, when the deploy
  definition is written, then it specifies Bearer-token auth and the exact four routes/shapes
  (`POST /api/v1/documents/`, `PATCH /api/v1/documents/{id}/`, `GET /api/v1/documents/{id}/`,
  `GET /api/v1/documents/all/`) as the deployed instance's required public API surface, verbatim
  against the client's expectations.
- Given the two open questions in the parent SPEC, when the deploy definition resolves them, then
  it states the substrate (django-lasuite 0.0.26 confirmed on the real conda-forge channel; Wagtail
  7.4.1 has only a local, upstream-unconfirmed recipe; no container) and the storage decision
  (SQLite satisfies Story 16.2's local-rehearsal instance only; DW-H1's PostgreSQL/MinIO stays
  fully open for the eventual attended production bring-up, unchanged by this story) explicitly —
  without overstating the DW-H1 question as fully closed — and the parent SPEC's Open Questions
  section is updated to point at the resolution with the same scope limits.
- Given the air-gap constraint, when the definition specifies deployment, then it requires
  mirrored-channel-only package installs, zero CDN references for static assets, and endpoint +
  token delivered only via env/secret-mount — never a committed credential.
- Given "atlas grows no deploy code" and "`factory/lasuite.py` stays unedited," when this story's
  changes are complete, then `factory/lasuite.py` shows zero diff and no new deploy-automation code
  exists anywhere in atlas's package tree — the deliverable is documentation only.
- Given Story 16.2 depends on "a locally-stood-up instance per the S-16.1 definition," when the
  definition is read in isolation, then it names exact package versions, exact settings shape, and
  exact routes — concrete enough to action without further research.

## Spec Change Log

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 1, medium 2, low 2)
- defer: 1 (medium)
- reject: 2 (low 2)
- addressed_findings:
  - `[high]` `[patch]` `open_questions` frontmatter left 2 "RESOLVED"-prefixed items as block-list
    entries, which `docs/dashboard/generate.py::_spec_open_questions` counts structurally (blind to
    the prefix) — shrunk the frontmatter list to only the genuinely-open item and moved the
    resolution summary to a preceding YAML comment, matching this repo's own documented convention.
  - `[medium]` `[patch]` the DW-H1-dependency "RESOLVED" label overstated completeness (only the
    local-rehearsal scope was resolved; production-scope PostgreSQL/MinIO stays open under DW-H1) —
    reworded the prose Open Questions bullet, the story spec's AC #2, and the ledger's DW-H3
    annotation to state the scope limit explicitly and reconcile with DW-H3's pre-existing
    "+ PostgreSQL/MinIO from DW-H1" text.
  - `[medium]` `[patch]` substrate Design Notes treated Wagtail and django-lasuite as symmetrically
    "mirrored-channel installable," but only django-lasuite is confirmed on the real conda-forge
    channel — Wagtail has only an unpublished local recipe. Rewrote the Substrate section to state
    the asymmetry explicitly and specify which mirrored channel applies to which package.
  - `[low]` `[patch]` ledger cited the story spec by bare filename while SPEC.md used a full
    relative path — gave the ledger citation a directory-qualified relative path instead.
  - `[low]` `[patch]` credential-minting claim (Steward has no deploy verb) had no citation trail —
    added `pyforge-steward`'s `cli.py`/`deploy.py`/`provision.py` to the Code Map and inline text.
  - `[low]` `[reject]` suggestion to add evidence files (recipes/, docs/reference/) to SPEC.md's
    `surface:` list — that field denotes implementation-touched files, not evidence citations;
    conflating the two risks unintended effects on `spec_surface_check.py`'s drift/coverage gate.
  - `[low]` `[reject]` suggestion to bump parent SPEC's `status: ready` → `in-progress` — re-checked
    against the SPEC's own "Success signal" section, which explicitly states the SPEC "holds at
    `draft`/`ready` — never `shipped` on paper alone" until the attended DW-H3 session passes; the
    SPEC's own text overrides the generic CLAUDE.md convention here, so this was not applied.
  - `[medium]` `[defer]` dangling cross-reference to the not-yet-promoted story spec (gitignored
    `implementation-artifacts/`) — real risk per repo's own documented incident history, but the
    fix (promotion) is explicitly a post-merge action outside this workflow's scope. Logged as
    `DW-FU-16-1` in `{implementation_artifacts}/deferred-work.md` so it isn't silently forgotten.

### 2026-08-15 — Review pass (S-13.7 reconciliation repair)
- intent_gap: 0
- bad_spec: 0
- patch: 1 (low 1)
- defer: 0
- reject: 9 (low 9)
- addressed_findings:
  - `[low]` `[patch]` the new `.memlog.md` reconciliation entry (added to
    `spec-wagtail-corporate-brain/.memlog.md` to repair the failed
    `scripts/spec_surface_reconcile.py` gate — Story 16.1's commit `87b545cc52` touched
    `deferred-work-ledger.md`, which that spec's `surface:` list governs, without reconciling)
    cited this story's own spec via the literal, unresolved template token
    `{implementation_artifacts}/spec-16-1-instance-deploy-definition.md` — replaced it with the
    working relative path `../../../../../implementation-artifacts/spec-16-1-instance-deploy-definition.md`,
    matching the precedent already established in the same directory's `SPEC.md` frontmatter
    comment. Baseline re-stamped again for `pyforge-atlas/spec-wagtail-corporate-brain` only after
    the fix; `spec_surface_reconcile.py` confirmed clean (`OK: every tracked file governed or
    allowlisted; no drift.`).
  - `[low]` `[reject]` "short annotation undersells" the ~8-line DW-H3 addition — the phrase
    mirrors this story's own Task 3 wording ("append a short annotation"); not a defect.
  - `[low]` `[reject]` same resolution paraphrased across DW-H3 / SPEC.md / the new memlog entry
    with no single source of truth — inherited from Story 16.1's own content (already reviewed and
    accepted under that story's "Precedent alignment" design note); not caused by this repair.
  - `[low]` `[reject]` no mitigation named for same-day-recurrence risk against the churning
    ledger — process advice (commit promptly), not a content defect; this pass's own Finalize step
    commits immediately after.
  - `[low]` `[reject]` new memlog entry inserted above "pass 2" with only day-level, not
    time-of-day, granularity — matches this file's pre-existing dated-heading convention, and
    `git log` confirms the chronological order (Story 16.1 after pass 2) is correct as placed.
  - `[low]` `[reject]` sibling specs (`pyforge-doctor/spec-fleet-hygiene-verification-exemplar-program`,
    `pyforge-atlas/spec-pyforge-atlas`, `pyforge-marshal/spec-bmad-switch-scope-enforcement`) also
    list `deferred-work-ledger.md` in their `surface:` — re-ran the full, unscoped
    `spec_surface_reconcile.py` (not just this spec) after the fix and confirmed zero drift
    anywhere in the repo, so no sibling spec is left stale.
  - `[low]` `[reject]` suggestion to independently verify the new baseline hash against
    `git hash-object` — already verified by reproducing it via a clean re-run of
    `spec_surface_check.py --write-baseline --spec ...` before and after the patch.
  - `[low]` `[reject]` whole-file hashing "absorbs" any undocumented drift beyond the DW-H3
    annotation — inherent, pre-existing design of every spec's baseline in this repo, not
    introduced by this repair; confirmed via `git status`/`git diff --stat` that
    `deferred-work-ledger.md` itself is untouched by this pass (only `.memlog.md` and the baseline
    JSON changed).
  - `[low]` `[reject]` no atomicity guard between the `.memlog.md` entry and the baseline
    re-stamp — a hypothetical tool-robustness gap in `spec_surface_reconcile.py` itself, not a
    defect in this diff; out of scope for a repair pass.
  - `[low]` `[reject]` memlog entry's claims aren't checkable against an embedded ledger diff
    hunk — a nice-to-have; the two prior "reconciliation only" entries in the same file also use
    prose-only summaries with no embedded hunks, so this matches established convention.

## Design Notes

**Substrate (resolves Open Question 1).** conda-forge Wagtail 7.4.1 + django-lasuite 0.0.26, no
container — but the two packages' real-channel status is **not symmetric**, and the deploy
definition must not be read as though it were:
- **django-lasuite 0.0.26** is confirmed live on the *real, public* conda-forge channel as
  `django-lasuite-feedstock` since 2026-04-13 (`recipes/django-lasuite/SUITENUMERIQUE_SUMMARY.md:157`)
  — installs directly from a standard mirrored-conda-forge proxy, no local build required.
- **Wagtail 7.4.1** has only a working *local* recipe in this repo (`recipes/wagtail/recipe.yaml`,
  `noarch: python`); repo evidence does not confirm it is published on the real public conda-forge
  feedstock. Treat it as needing this repo's own build-and-publish-to-an-internal-mirror step
  (the same local-recipes → Artifactory-mirrored-channel path this repo already uses for its own
  recipes) unless/until someone verifies it is already public — do not assume a bare
  `conda install -c conda-forge wagtail` resolves it.

Both routes are air-gap-compatible (an Artifactory conda-remote proxy for django-lasuite, an
Artifactory-mirrored *local* channel fed by this repo's own recipe build for Wagtail, per
`docs/reference/enterprise-deployment.md` §2's established `~/.condarc` pattern) — the
`helm/lasuite-docs/` chart (pulling the upstream `docs-backend` container image) is a *different*
subsystem's fixture (unrelated `LaSuiteClient` implementation under `src/sentinel/`) and is not a
candidate substrate here.

**Storage (resolves Open Question 2 — for the local-rehearsal scope this story defines).** A
SQLite-backed Wagtail settings module (`DATABASES.default.ENGINE =
"django.db.backends.sqlite3"`) is the target for the *local* rehearsal instance Story 16.2 stands
up. DW-H1's PostgreSQL/MinIO stays reserved for the eventual ATTENDED production bring-up — that
question is unchanged and still deferred to DW-H1. This split is safe because DW-H1's own ledger
entry already notes the codebase's storage resolver degrades to a filesystem backend when no S3
endpoint is configured, so a SQLite + local-filesystem Wagtail instance needs zero additional
server provisioning to stand up for rehearsal purposes.

**Required API surface (verbatim from `LaSuiteClient` / `MockWagtail`; not new — restated as the
deploy target).** Every route requires `Authorization: Bearer {token}` and
`Content-Type: application/json`:
- `POST {base_url}/api/v1/documents/` — body `{"title", "content"[, "parent"]}` — MUST return a
  2xx response whose JSON body carries `id` (`WikiSyncer._created_id` hard-fails otherwise).
- `PATCH {base_url}/api/v1/documents/{id}/` — body `{"title", "content"}` — 2xx with the updated
  doc; 404 if the id is unknown.
- `GET {base_url}/api/v1/documents/{id}/` — 200 with the doc; 404 if unknown.
- `GET {base_url}/api/v1/documents/all/` — 200 with a JSON array of all docs.

django-lasuite is the Suite Numérique integration package `LaSuiteClient` was designed against, so
installing it on Wagtail is the recommended path to this surface — but whether its out-of-the-box
REST API matches this exact path/shape (versus needing a thin compatibility view, itself living in
the deployed instance's own Django project, not in atlas package code) is confirmed only at the
attended bring-up. This definition specifies the *required* contract; it does not claim the match
is already proven.

**Air-gap requirements.** Package installs resolve from a mirrored conda channel only (no PyPI
fallback), reusing this repo's established `*_BASE_URL`-override / JFrog-proxy conventions
(`docs/reference/enterprise-deployment.md` §§1, 2, 6). `python manage.py collectstatic` serves
admin/site static assets from local disk via the app server — zero CDN references anywhere in
Wagtail's static config. Endpoint + token reach the process only via `LASUITE_BASE_URL` /
`LASUITE_API_TOKEN` env vars or a secret-mount, matching `resolve_lasuite_config()`'s existing
contract exactly — no committed credential, no hardcoded host.

**Credential minting — a named gap, not a blocker.** `steward keys` manages this repo's own
encrypted local secret inventory (`age`-based); it has no verb to mint an API token on a *remote*
Wagtail admin, and `steward deploy`/`steward provision` currently expose no verb for deploying an
arbitrary external service — their real surface is limited to the program-console dashboard and
the `bmb` module (`src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py`'s `deploy`
subcommand group and `provision`'s `_SUPPORTED_MODULES`, cross-checked against `deploy.py` and
`provision.py` in that same package as of this story's authoring — re-verify if Steward has grown
since). Per Charter §5's outcome/mechanism split ("a station accountable for an outcome it cannot
deliver alone is accountable for *obtaining* the mechanism, not for owning it"), atlas does not
need Steward to already have this verb — the attended bring-up's interim mechanism is manual token
creation via the Wagtail admin UI, with growing a `steward` verb for this left as a future
decision, not something this story or Story 16.2 needs to build.

**Precedent alignment.** DW-C1-1 (Dagster) and DW-D3-1 (Vizro-AI) both follow the same shape: ship
the offline-verified contract, defer the attended bring-up as a separate scheduled event, and keep
the whole definition inside the shipping story's own spec rather than a separate `docs/deploy/`
artifact. This story follows that precedent exactly — no new directory or file convention is
introduced.

## Verification

**Commands:**
- `git diff --stat -- src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/lasuite.py` --
  expected: no output (zero diff — the frozen contract is untouched).
- `pixi run -e pyforge-atlas kedro-test` -- expected: full pass, including
  `tests/factory/test_lasuite.py` (untouched, still green) and
  `tests/catalog/test_no_inline_io.py` (the no-inline-IO gate stays green since no HTTP client was
  added anywhere in package code).

**Manual checks (if no CLI):**
- Read this spec's Design Notes and confirm: both parent-SPEC open questions (substrate, DW-H1
  dependency) have explicit, concrete answers; the four routes + Bearer-auth shape are restated
  exactly, not altered; air-gap requirements are stated (mirrored channel, zero CDN, env-only
  credential); the Steward credential-minting gap is named rather than silently assumed solved.
- Confirm `spec-wagtail-corporate-brain/SPEC.md`'s `open_questions` now cross-reference this spec
  for the two resolved items, and the DW-H3 ledger entry carries the short resolution annotation
  without its `status` changing.

## Auto Run Result

**Summary:** Story 16.1's own deliverable (the deploy definition, the SPEC cross-reference, and
the DW-H3 ledger annotation) was already complete and committed (`87b545cc52`) before this
session. This session's only job was a repair: bmad-loop's external S-13.7 spec-surface-drift gate
(`scripts/spec_surface_reconcile.py`) failed because `deferred-work-ledger.md` — a file
`spec-wagtail-corporate-brain` governs via its `surface:` list — changed (Story 16.1's DW-H3
annotation) without that spec's own `.memlog.md` being reconciled. Fixed by adding a dated
`.memlog.md` entry naming the change and re-stamping that spec's baseline in isolation
(`--spec pyforge-atlas/spec-wagtail-corporate-brain`). No content from Story 16.1's own diff
(`deferred-work-ledger.md`, `spec-wagtail-corporate-brain/SPEC.md`, `factory/lasuite.py`) was
touched.

**Files changed (this repair, commit `9c5d3aa94e`):**
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-wagtail-corporate-brain/.memlog.md`
  — new dated entry reconciling the ledger change.
- `scripts/.spec-surface-baseline.json` — re-stamped, scoped to
  `pyforge-atlas/spec-wagtail-corporate-brain` only (verified via diff that no other spec's entry
  moved).

**Review findings breakdown (repair-diff pass):** 1 patch (low — a `.memlog.md` citation used the
literal, unresolved template token `{implementation_artifacts}/...` instead of a working relative
path; fixed to match the precedent already set in the same directory's `SPEC.md`), 9 reject (all
low — pre-existing patterns, hypotheses the reviewers' own verification already ruled out, or
tool-design questions out of scope for a repair pass). Full breakdown in the Review Triage Log
entry above.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` — before the fix: reproduced the exact drift finding
  from the feedback file (verified via `git stash`); after the fix and after the low patch: `OK:
  every tracked file governed or allowlisted; no drift.` (exit 0), on the final committed HEAD.
- `git diff --stat -- src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/lasuite.py` —
  empty both before and after this repair (frozen contract untouched, per the spec's own
  `Never` constraint).
- `git status --short` — confirmed only the two intended files changed.
- Did not re-run `pixi run -e pyforge-atlas kedro-test` in this repair pass: this session touched
  no code, only a planning-artifact memlog and a JSON baseline file, and that command was already
  part of Story 16.1's own prior verification.

**Residual risks:** None identified for this repair. The pre-existing pattern of the same
resolution being paraphrased in three places (DW-H3, SPEC.md, this spec's Design Notes) is
inherited from Story 16.1's own content and was already reviewed and accepted there
("Precedent alignment" design note); not re-opened here. `DW-FU-16-1` (post-merge promotion of
this story's own spec into `planning-artifacts/specs/`) remains open from Story 16.1's original
review pass, unaffected by this repair.

