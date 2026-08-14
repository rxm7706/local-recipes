---
title: 'One factory-sourced environment'
type: 'feature'
created: '2026-08-14'
status: done
baseline_revision: '4febffd7bf72267dffdef46b529157c01e5aca1e'
final_revision: 'f72d89506ce44f06c2adb7d912106672e160323d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/planning-artifacts/specs/spec-python-agent-platform/SPEC.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** No environment exists yet capable of running the three agentic engines
(`langflow`, `dbgpt`, `dbgpt-serve`) alongside Django on one Python interpreter, sourced from
this factory's own conda-forge feedstocks. Epic 11's engine-mounting stories and this epic's own
Story 10.3 (container image) both depend on it existing first, and the rest of the repo must
stay on python 3.14 while this one environment stays on 3.12.

**Approach:** Add a new pixi feature+environment `python-agent-platform` pinning
`python = "3.12.*"` (env-scoped only), declaring `langflow`, `dbgpt`, `dbgpt-serve`, `django`,
and the host deps already justified by Story 10.1 and the PostgreSQL/Redis infra constraint —
promoting the already-verified 373-package conda-native solve into a first-class, reproducible
pixi env — then own the resulting ripple end-to-end (`environment.yaml`, the library catalog,
the drift baseline).

## Boundaries & Constraints

**Always:** the `python-agent-platform` env pins exactly `python = "3.12.*"`; no other
feature/env in `pixi.toml` changes its python floor. Every new package resolves from
conda-forge (verified via `lookup_feedstock`) — no PyPI fallback. `pixi.toml` stays the single
source; `environment.yaml` is a derived, regenerated artifact (never hand-edited), regenerated
with exactly `pixi project export conda-environment -e build > environment.yaml` per CLAUDE.md's
always-on rule (note: that command always targets the `build` env, regardless of which env
changed). The same PR reconciles `environment.yaml`, `docs/reference/library-llms-full.md`, and
the bmad-drift `.sync-baseline.json` (`python scripts/bmad_drift_check.py --write-baseline`) —
no detector left redder than it started.

**Block If:** `lookup_feedstock` reports any of langflow / dbgpt / dbgpt-serve / django as
absent from conda-forge at a usable floor → HALT `blocked` (`feedstock unavailable`). `pixi
install -e python-agent-platform` fails to solve after reasonable floor adjustment → HALT
`blocked` (`environment does not solve`).

**Never:** touch `src/platform/requirements/*.txt` (Story 10.1's surface) or attempt a full
pip-to-conda migration of the rendered host's dependencies — reconciling those with this env is
Story 10.3's container-layer decision. Wire the engines into the Django host (mounts,
migrations, ASGI dispatch) — Epic 11. Add packages beyond the four named engines plus the host
deps justified in Design Notes — no speculative additions. Hand-edit
`pyforge-marshal`'s planning-artifacts prose (env-count text) — outside this spec's declared
surface; see Design Notes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | `pixi install -e python-agent-platform` run fresh | solves; `pixi.lock` gains a `python-agent-platform` env pinned to `python 3.12.*`; exit 0 | n/a |
| Rest of repo untouched | `pixi install -e local-recipes` after this change | still solves at `python 3.14.*`, unaffected | n/a |
| Missing feedstock (regression guard) | A future pin names a package absent from conda-forge | `pixi install -e python-agent-platform` fails loud with an unsatisfiable-solve error naming it | never silently dropped |

</intent-contract>

## Code Map

- `pixi.toml` -- add `[feature.python-agent-platform]`(+`.dependencies`) and
  `[environments].python-agent-platform`; uncomment/bump the stale `pixitainer` pin in
  `[feature.local-recipes.dependencies]` (line ~1025)
- `environment.yaml` -- regenerate (derived from the `build` env, unaffected content-wise by
  this story except the regeneration timestamp)
- `docs/reference/library-llms-full.md` -- regenerate catalog: §11 gains langflow/dbgpt/dbgpt-serve,
  §13 gains the python-agent-platform-scoped django/fastapi/django-health-check/psycopg2/redis-py,
  §3 documents pixitainer no longer commented-out, §17 gains the `redis-py`→`import redis`
  name gotcha
- `scripts/bmad_drift_check.py` -- run with `--write-baseline` (mutates
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/.sync-baseline.json`; do not hand-edit)

## Tasks & Acceptance

**Execution:**
- [x] `pixi.toml` -- add `[feature.python-agent-platform]` with `platforms = ["linux-64",
  "osx-arm64-min"]` and `[feature.python-agent-platform.dependencies]` pinning `python =
  "3.12.*"`, `langflow >=1.11.2`, `dbgpt >=0.8.1`, `dbgpt-serve >=0.8.1`, `django >=5.2,<6`,
  `fastapi >=0.141.1`, `django-health-check >=4.5.0`, `psycopg2 >=2.9.12`, `redis-py >=6.0.0` --
  the factory-sourced trio + django + the host deps this story's Design Notes justify. Also
  needed `channel-priority = "flexible"` on this feature (not touching the workspace default of
  "strict") -- see Spec Change Log's 2026-08-14 addendum below.
- [x] `pixi.toml` -- add `python-agent-platform = { features = ["python-agent-platform"],
  no-default-feature = true }` to `[environments]` -- mirrors the lean per-station env pattern
  (`pyforge-warden`/`-atlas`/`-doctor`/…)
- [x] `pixi.toml` -- uncomment + bump the stale `#pixitainer = ">=0.7.1"` pin to
  `pixitainer = ">=0.8.3"`, placed under `[feature.local-recipes.target.linux-64.dependencies]`
  (NOT the cross-platform dependencies table: pixitainer's recipe is `build.skip: "not linux"`,
  so an unscoped placement breaks the local-recipes env's win-64/osx solves -- the 2026-08-14
  triage log's independent finding, resolved here) -- Story 10.3's named pixitainer-evaluation
  AC needs the tool installed and available first
- [x] run `pixi install -e python-agent-platform` -- proves the declared set solves
  reproducibly (the story's core AC); updates `pixi.lock`
- [x] `environment.yaml` -- regenerate via `pixi project export conda-environment -e build >
  environment.yaml` -- CLAUDE.md's always-on pixi.toml-changed rule
- [x] `docs/reference/library-llms-full.md` -- regenerate per its own header prompt (read all of
  `pixi.toml`, keep the 18-section structure, update the Generated date); verify with `pixi run
  -e local-recipes llms-full-check`
- [x] run `python scripts/bmad_drift_check.py --write-baseline` -- reconciles the
  `.sync-baseline.json` surface fingerprint so this intentional `pixi.toml` change doesn't
  register as unreconciled drift

**Acceptance Criteria:**
- Given the new `[feature.python-agent-platform]` + `[environments].python-agent-platform`,
  when `pixi install -e python-agent-platform` runs, then it solves and exits 0, and `pixi.lock`
  gains a `python-agent-platform` environment pinned to `python 3.12.*`.
- Given the repo's pre-existing environments (e.g. `local-recipes`, `pyforge-ci`), when `pixi
  install -e local-recipes` runs after this change, then it still solves at `python 3.14.*`,
  unaffected by the new feature.
- Given `environment.yaml`, when regenerated, then it matches `pixi project export
  conda-environment -e build`'s output byte-for-byte (still the `build` env, per CLAUDE.md
  convention -- NOT `python-agent-platform`).
- Given `docs/reference/library-llms-full.md`, when `pixi run -e local-recipes llms-full-check`
  runs after the regeneration, then it exits 0.
- Given `python scripts/bmad_drift_check.py` run after `--write-baseline`, then it reports no
  NEW `surface-changed`/baseline-drift finding attributable to this story's `pixi.toml` edit
  (pre-existing unrelated findings are out of scope).

## Spec Change Log

- **2026-08-14 (resolution, operator-driven — re-arms the 2026-08-14 BLOCKED escalation):**
  the Task-4 solver conflict is resolved EXTERNALLY, none of the triage log's options (a)-(c):
  a relaxed `slowapi 0.1.10` build 1 (`run_constrained: redis-py >=3.4.1` — the `<4` cap was
  upstream's vestigial 2020 poetry caret; slowapi never imports redis, storage via `limits`;
  runtime-validated co-installed with redis-py 8.1.0) is live on the **selfexplainml** channel,
  which is ALREADY in the workspace `channels` list. **No pixi.toml channel changes**: the
  env's own `redis-py >=6.0.0` floor makes every conda-forge slowapi candidate infeasible and
  the solver falls through to selfexplainml's build — verified with the workspace's exact
  conda-forge-first order (probe resolves `slowapi 0.1.10 pyhcba1bba_1 selfexplainml` alongside
  langflow 1.11.2 + redis-py 8.1.0 + dbgpt 0.8.1 + django 5.2.15). EXPECT slowapi from
  selfexplainml in `pixi.lock` — that is correct, not an error. Retirement is transparent:
  conda-forge/slowapi-feedstock#4 (open — v1 conversion + 0.1.10 + the same relaxation)
  supersedes the override when merged; upstream ask laurentS/slowapi#290. Task 3's pixitainer
  placement corrected to the linux-64 target table (see task). Keep the `redis-py >=6.0.0`
  floor exactly as spec'd.

- **2026-08-14 (implementation, deviations from literal instructions):**
  1. **`channel-priority = "flexible"` added to `[feature.python-agent-platform]`** (not
     anticipated by the Change Log entry above). `pixi install -e python-agent-platform` failed
     first with pixi 0.76.2's WORKSPACE DEFAULT channel priority (`"strict"`, undeclared
     anywhere in `pixi.toml`, so it's pixi's own default): strict priority hard-excludes an
     entire lower-priority channel the instant the higher-priority channel has ANY build of a
     package name -- confirmed live: `slowapi 0.1.10 is excluded because due to strict channel
     priority not using this option from 'SelfExplainML'`, even though conda-forge's own only
     build (0.1.9) is infeasible against `redis-py >=6.0.0`. `channel-priority = "flexible"`
     (Feature-scoped per the pixi 0.76.2 manifest schema; verified via the published
     `schema/manifest/schema.json`) is the mode that actually implements the fallthrough this
     spec describes ("exhaust conda-forge's candidates first, only fall back to SelfExplainML
     once conda-forge is exhausted"). Scoped to this one feature only -- no other feature/env
     changes its channel-priority off the workspace default. No channel-list change (still
     `channels = ["conda-forge", "SelfExplainML"]`, unchanged); no redis-py floor relaxation.
     With this one addition, the solve matched the Change Log's prediction exactly: `slowapi
     0.1.10 pyhcba1bba_1 selfexplainml` alongside `langflow 1.11.2`, `redis-py 8.1.0`, `dbgpt
     0.8.1`, `django 5.2.15`.
  2. **`docs/reference/library-llms-full.md` also fixed 33 pre-existing floor-drift findings +
     1 pre-existing `undocumented-dep` (`pyforge-core`, Story 14.1's env, missing its
     "Environments at a glance" row) unrelated to this story's own CAP-5 additions.** Confirmed
     pre-existing by re-running the detector against `git show HEAD:` copies of both files
     before touching either -- identical 34 findings, none touching this story's 8 packages or
     `pixitainer`. Task 5's literal instruction ("verify with `llms-full-check`... iterate until
     0") and the AC ("then it exits 0") required a genuine 0, and the catalog's own regeneration
     prompt already scopes "rewrite the catalog... with version floors" broadly -- so these were
     fixed as pure version-number syncs (no prose rewrites beyond the CAP-5-relevant additions)
     rather than left as an unrelated non-zero exit.
  3. **`python scripts/bmad_drift_check.py` (bare, no flags) no longer computes a verdict** --
     confirmed against the script's own `--help` text: Story 6.9 ported the read-only VERDICT
     into `pyforge.doctor.sources.factory::gather` (`pixi run -e local-recipes bmad-drift-check`
     / `python -m pyforge.doctor.sources bmad-drift`), matching CLAUDE.md's own "Keeping BMAD
     artifacts in sync" section (given as context for this story). Used that command for the
     before/after verdict instead of the bare script; used the bare script (as spec'd, plain
     `python`) only for its still-live `--write-baseline` mutation. After `--write-baseline`,
     `surface-changed` (pixi_envs 20->22) cleared as expected. The only surviving non-`ok`
     finding after stamping is a pre-existing HARD `uncovered` on
     `_bmad-output/projects/pyforge-marshal/planning-artifacts/parallel-fan-out-readiness-assessment.md`
     -- confirmed via `git log` to have landed 2026-08-12 (PR/commit `6469d9db91`, S-3.13),
     entirely unrelated to this story's `pixi.toml`/CAP-5 surface. Per the AC's own explicit
     scoping ("no NEW `surface-changed`/baseline-drift finding... pre-existing unrelated
     findings are out of scope"), this AC is satisfied.

### 2026-08-14 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1 (low)
- defer: 2 (medium 1, low 1)
- reject: 9 (medium 2, low 7)
- addressed_findings:
  - `[low]` `[patch]` `docs/reference/library-llms-full.md`'s new `dbgpt-serve` entry read
    "installed alongside **dbgpt** itself (§ 6 — same package...)" -- ambiguous phrasing a
    literal reading takes as claiming `dbgpt`/`dbgpt-serve` are the same conda package (they
    are not; both reviewers flagged it independently). Reworded to "a separate package from the
    same feedstock, also floor `>=0.8.1`". Re-verified `llms-full-check` still exits 0 after the
    edit.

### 2026-08-14 — Repair pass (deterministic verification failure)

`python scripts/spec_surface_reconcile.py` (bmad-loop's own verify command) was failing:
`pixi.toml`'s new content wasn't named in the `.memlog.md` of two OTHER specs that also declare
`pixi.toml` in their `surface:` (`pyforge-marshal/spec-bmad-loop-baseline-drift`,
`pyforge-steward/spec-python-agent-platform` -- the latter is this story's own umbrella spec).
Fixed by adding a reconciliation entry to each spec's `.memlog.md` naming the changed path(s),
then `python scripts/spec_surface_check.py --write-baseline --spec <name>` scoped to just those
two specs. `src/platform/docs/make.bat` also reported drifted against
`spec-python-agent-platform`'s baseline -- confirmed a checkout artifact (`.gitattributes`
`eol=crlf` smudges the file to CRLF on this worktree's checkout; the committed blob and the
original baseline hash are LF), not new content since Story 10.1. No file inside this story's
own `<intent-contract>` or Tasks & Acceptance changed; `pixi run --frozen -e pyforge-steward
pyforge-steward-test` (695 passed) and `python scripts/spec_surface_reconcile.py` (`OK: every
tracked file governed or allowlisted; no drift.`, exit 0) both reverified clean after the fix.

- intent_gap: 0
- bad_spec: 0
- patch: 3 (low)
- defer: 2 (medium)
- reject: 4 (low)
- addressed_findings:
  - `[low]` `[patch]` The new `spec-bmad-loop-baseline-drift` memlog entry cited the bmad-loop
    pin at `pixi.toml:1058` -- stale as of this very diff, which shifted it to `:1121` by
    inserting `[feature.python-agent-platform]` earlier in the file. Corrected the citation and
    re-verified the line number live.
  - `[low]` `[patch]` The new `spec-python-agent-platform` memlog entry described the pixitainer
    edit as "uncommented/relocated" without mentioning the version floor also moved
    (`>=0.7.1` -> `>=0.8.3`). Added the version detail.
  - `[low]` `[patch]` Neither new memlog entry cited the actual passing verification-gate output.
    Added the `spec_surface_reconcile.py` `OK`/exit-0 confirmation to both.
  - Two findings deferred as `DW-FU-10-2-3` (two other pixi.toml-governing specs,
    `spec-pyforge-core`/`spec-unified-container`, already carry a stale baseline predating this
    story, silently absorbed rather than reported) and `DW-FU-10-2-4` (`gather_spec_surface`'s
    file-drift hash reads raw on-disk bytes rather than git's blob content, so an `eol=`-attributed
    file reproduces false drift in any worktree whose checkout differs from the one that stamped
    the baseline) -- both pre-existing gaps in shared S-13.7 reconciliation infrastructure this
    story does not own; see `_bmad-output/implementation-artifacts/deferred-work.md` for full
    evidence.

## Review Triage Log

**2026-08-14 — BLOCKED at Task 4 (`pixi install -e python-agent-platform`).** Genuine,
platform-independent solver conflict matching the Boundaries & Constraints' second `Block If`
clause. conda-forge's `slowapi` feedstock (only one build published, `0.1.9`; pulled in
transitively via `langflow` -> `langflow-base` -> `slowapi >=0.1.9,<1.0.0`) carries a hard
`run_constrained: redis-py >=3.4.1,<4.0.0`. That directly conflicts with this story's own
`redis-py >=6.0.0` floor -- and, independently, with `django-health-check`'s own unconstrained
`redis-py` run-dep, which pulls redis-py into the solve regardless. Confirmed
platform-independent (`slowapi` is `noarch: python`) by reproducing the identical error on both
`linux-64` and `osx-arm64-min`. Confirmed no floor adjustment on any of the 8 named packages
resolves it: the only solvable state found was leaving `redis-py` completely unpinned, which
the solver then forces down to `redis-py 3.5.3` (released ~2020, no async support, pre-RESP3) --
a 3-major-version downgrade from the story's `>=6.0.0` floor, not a reasonable adjustment but a
reversal of the floor's stated intent. Per the spec's own Block-If clause this HALTs the story
`blocked`.

Operational note: pixi solves its lockfile atomically across ALL declared environments, so
leaving `[feature.python-agent-platform]` + its `[environments]` entry declared (even
temporarily, mid-diagnosis) broke `pixi install`/`pixi run` for EVERY environment in the repo
(verified: `pixi install -e local-recipes` also failed while it was present, en route to
re-solving `python-agent-platform`). All `pixi.toml`/`pixi.lock` edits were therefore reverted
back to the pre-story baseline (`git checkout -- pixi.toml pixi.lock`) so the repo stays usable
while this is blocked; no residual pixi.toml/pixi.lock diff was left in the working tree.

Independent finding worth carrying forward when this unblocks: Task 3 (uncomment+bump
`pixitainer`) was dry-run tested and found a real, unrelated placement bug in the spec's literal
instruction. `pixitainer`'s own recipe is `build.skip: "not linux"` (linux-only), so placing it
in the cross-platform `[feature.local-recipes.dependencies]` (line ~1025, as the spec's Code Map
names) breaks the `local-recipes` env's solve on win-64/osx-arm64-min (`pixitainer >=0.8.3
... requires __linux, for which no candidates were found`). The fix, verified to solve cleanly,
is to place it in the pre-existing `[feature.local-recipes.target.linux-64.dependencies]` block
instead -- the exact pattern this file already uses for `mlx`/`tmux`/`ocrmypdf` immediately
above it (same section, same reasoning comment).

Unblock options for a human/operator decision (none taken unilaterally -- no packages were
added or dropped from the named eight, no speculative pins introduced):
- (a) accept `redis-py 3.5.3` (drop/relax the `>=6.0.0` floor) -- changes CAP-5's implicit
  modern-Redis-client guarantee for Django/Celery.
- (b) get the `slowapi` conda-forge feedstock's stale `run_constrained` relaxed upstream
  (maintained by `mediocretech`, not this factory) or vendor a locally-patched slowapi build.
- (c) revisit CAP-5's "one environment" framing -- defer `redis-py`/`psycopg2` host-dep
  installation to a separate environment that doesn't co-install `langflow`.

## Design Notes

**Version floors verified against this factory's own published feedstocks**
(`lookup_feedstock`, 2026-08-14): `langflow` 1.11.2 (langflow-suite feedstock, `python_min`
3.11 -- compatible with our 3.12 floor); `db-gpt` feedstock's `dbgpt`/`dbgpt-serve` outputs at
0.8.1; `django-health-check` feedstock at 4.5.0 (needs `django>=5.2`, matching our floor -- a
DIFFERENT install from Story 10.1's PIP-pinned `django-health-check==3.24.0`, which targets that
story's separately-pinned `django==5.1.11`; the two are unrelated, differently-scoped installs
in different environments); `pixitainer` feedstock at 0.8.3 (the existing pixi.toml comment was
stale at `>=0.7.1`). Matches the operator-verified feasibility spike
(`docs/dreams/enterprise-multi-agent-orchestration.md`, 2026-08-14): `micromamba create
--dry-run -c conda-forge langflow dbgpt dbgpt-serve "django>=5" python=3.12` solved cleanly at
373 packages, agreeing on `pydantic 2.13.4`/`sqlalchemy 2.0.52`/`fastapi 0.141.1` -- this story
promotes that spike into a first-class, reproducible pixi feature+env.

**"Host deps" scope decision.** CAP-5 names "langflow, dbgpt, dbgpt-serve, django and host
deps" without enumerating the host deps. This story scopes "host deps" to four packages with a
direct, already-established justification: `fastapi` (Story 10.1's own ASGI/FastAPI-integration
seam, floor matches its pin exactly -- also arrives transitively via langflow-base's own
`fastapi >=0.135.0,<1.0.0` run-dep, so the explicit pin only documents intent) and
`django-health-check` (Story 10.1's K8s liveness/readiness requirement, CAP-1) as the
Django-host-specific additions, plus `psycopg2` and `redis-py` as the PostgreSQL/Redis client
drivers the "infrastructure is exactly PostgreSQL + Redis" constraint (Always,
spec-python-agent-platform) requires Django/Celery to actually reach either backing service.
Import-name gotcha: the conda-forge package is named `redis-py`; it imports as `redis`. This
deliberately does NOT attempt a full pip-to-conda migration of
`src/platform/requirements/{base,production,local}.txt` (whitenoise, argon2-cffi, celery,
django-allauth, django-compressor, etc.) -- that reconciliation belongs to Story 10.3, which
owns deciding how the container's environment layer is actually generated (pixitainer vs
hand-rolled) and whether it supersedes or coexists with the pip requirements files.

**Env-count doc staleness is pre-existing, non-blocking, and out of this story's surface.**
`pyforge-marshal`'s planning docs (`index.md`/`architecture.md`/`architecture-bmad-infra.md`)
already state "20 pixi envs" while the live count is 21 (`_env_count` in
`pyforge.doctor.sources.factory`) -- a drift that predates this story. `check_counts`'s `pixi
envs` probe is INFO-severity (maps to `DoctorStatus.OK`, never gates the detector's exit code).
This story's addition makes the live count 22; reconciling `pyforge-marshal`'s prose docs is
that project's own sync-loop responsibility (CLAUDE.md § "Keeping BMAD artifacts in sync"), not
this story's surface (`spec-python-agent-platform`'s declared surface is `src/platform/**`,
`pixi.toml`, `environment.yaml` -- it does not cover another project's planning-artifacts).
This story's obligation is limited to `--write-baseline`, which reconciles the separate
`.sync-baseline.json` surface-fingerprint file, not the prose count text.

## Verification

**Commands:**
- `pixi install -e python-agent-platform` -- expect a clean solve, exit 0
- `pixi run -e python-agent-platform python --version` -- expect `Python 3.12.x`
- `pixi list -e python-agent-platform | grep -E "^(langflow|dbgpt|dbgpt-serve|django|fastapi|django-health-check|psycopg2|redis-py) "` -- expect all eight present
- `pixi run -e local-recipes llms-full-check` -- expect exit 0
- `python scripts/bmad_drift_check.py` -- run before AND after `--write-baseline`; expect no
  NEW finding introduced by this story's `pixi.toml` change after stamping
- `git diff -- environment.yaml` -- expect only the regenerated `build`-env content (no
  `python-agent-platform` leakage into that file)

## Auto Run Result

Status: done

**Summary.** This story's own capability work (the `python-agent-platform` pixi feature/env,
`environment.yaml`, `library-llms-full.md`) was already implemented and reviewed in a prior
session (see the 2026-08-14 Spec Change Log / Review pass entries above). This session was a
repair pass: the prior session's work failed bmad-loop's own deterministic verify step
(`python scripts/spec_surface_reconcile.py`) because this story's `pixi.toml` edit wasn't named
in the `.memlog.md` of two OTHER specs that also govern `pixi.toml` in their `surface:` frontmatter.
No content inside `<intent-contract>`, Tasks & Acceptance, Design Notes, or the story's own
task-owned files (`pixi.toml`, `environment.yaml`, `docs/reference/library-llms-full.md`) changed
in this pass.

**Files changed (this pass only):**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-baseline-drift/.memlog.md` -- reconciliation entry naming `pixi.toml`
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/.memlog.md` -- reconciliation entry naming `pixi.toml` and `src/platform/docs/make.bat`
- `scripts/.spec-surface-baseline.json` -- re-stamped, scoped to exactly those two specs (`--spec pyforge-marshal/spec-bmad-loop-baseline-drift --spec pyforge-steward/spec-python-agent-platform`)

**Review findings breakdown (this pass's Blind Hunter + Edge Case Hunter, on the repair diff only):**
patch 3 (low, all fixed: stale `pixi.toml:1058` line-number citation, undersold pixitainer
version bump, missing verification evidence in the new memlog entries); defer 2 (medium, both
pre-existing gaps in shared S-13.7 infrastructure this story does not own -- logged as
`DW-FU-10-2-3` and `DW-FU-10-2-4` in `deferred-work.md`); reject 4 (low, noise/context restating
already-documented behavior).

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` (bare/no-pixi interpreter, matching how bmad-loop's
  own verify command runs it): `OK: every tracked file governed or allowlisted; no drift.`, exit 0
- `pixi run --frozen -e pyforge-steward pyforge-steward-test`: 695 passed
- Both reverified after the final patch-fix edits, against the committed state (`f72d89506c`)

**Residual risks:** the two deferred findings are real but non-gating and pre-existing (not
introduced or worsened by this story): (1) two other pixi.toml-governing specs
(`spec-pyforge-core`, `spec-unified-container`) already carry stale baselines, silently absorbed
rather than reported by the reconciliation gate's substring-match suppression; (2) the gate's
file-drift hash reads raw on-disk bytes rather than git's blob content, so the
`src/platform/docs/make.bat` re-stamp in this pass is checkout-environment-specific and could
reproduce the same false-positive drift in a future worktree with different EOL smudging. Neither
blocks this story; both are logged for whoever next owns the affected surfaces.

