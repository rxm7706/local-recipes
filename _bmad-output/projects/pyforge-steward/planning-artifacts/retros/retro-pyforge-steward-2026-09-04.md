---
title: "pyforge-steward — retrospective, Epics 42–43 and the fleet CI health pass"
created: "2026-09-04"
updated: "2026-09-04"
covers: "Everything since retro-pyforge-steward-2026-08-31.md (commit 8647d37684) through 2026-09-04 — Epic 42 (42.1–42.5) and Epic 43 (43.1–43.6) as landed, plus the CI health pass on PR #1043 that re-enabled GitHub Actions after the 2026-08-30 → 2026-09-04 dormancy and repaired what had rotted underneath it"
evidence: "git log --oneline 8647d37684..HEAD -- src/shared/packages/pyforge-steward src/platform _bmad-output/projects/pyforge-steward; gh run list --workflow platform-ci.yml --branch main; local re-runs of every Platform CI test-job step and image build (this document § Behavior verification); pixi run -e local-recipes detectors-ci"
---

# pyforge-steward — Retrospective, 2026-09-04

**Trigger:** `chain-currency-sweep` flagged the `code→retro` checkpoint stale (the package's
`pyproject.toml` was touched today — the wheel force-include fix below — against a prior retro
dated 2026-08-31, past the 2-day grace in `CHAIN-CURRENCY-RUNBOOK.md`). The operator's standing
directive for the same session — *"fix the pre-existing failures in CI / GitHub workflows; it's
been a while since we checked all stations"* — makes this retro cover both the two epics that
landed in the window and the health pass that audited their landing.

Companion to `retro-pyforge-steward-2026-08-31.md`; the window is what landed after it.

## What landed, and what didn't

**Window (git):** 31 commits since `8647d37684`, 88 files, +10,274 / −394. Story commits exist
for every one of 42.1–42.5 and 43.1–43.6; the tracked story specs `specs/spec-42-*.md` and
`specs/spec-43-*.md` (11 files) are the source of record. `sprint_status.py detect-epic --epic 42`
and `--epic 43` both report `pending_stories: []` — the epics are complete; their retro keys
(`epic-42-retrospective`, `epic-43-retrospective`) were `optional` until this document. The red-team
readiness reports `implementation-readiness-report-2026-09-02-red-team-{critical,high}.md` gated the
window's second half; the resulting `DW-RT-2026-09-02-*` items are already routed (Epic 44 /
Epic 45 candidate) by the cutover spine and are not re-litigated here.

**What the health pass found (all pre-existing on `main`, none reported by CI because Actions was
disabled 2026-08-30 → 2026-09-04; Platform CI had in fact been red on every `main` run since its
last green, run 32667190614 on 2026-08-23):**

| # | Surface | Defect | Fix (PR #1043) |
|---|---|---|---|
| 1 | `pyforge-steward/pyproject.toml` | hatch `force-include` shipped `6.11.0.yaml` twice → wheel build refused (five-tier / fresh-clone workflows) | force-include removed; wheel verified to carry one copy |
| 2 | `pixi.toml` `[feature.platform-ci-test]` | host `manage.py check` died on `ModuleNotFoundError: pyforge` — the host imports `pyforge.steward.keys` (the live `pap:AD-2` breach the cutover spine already names) | `pyforge-steward` path dep added; the breach itself stays Epic 44's (ingest rebuilt into steward) |
| 3 | `src/platform/Containerfile` | image `collectstatic` died on `No module named pyforge.core` | `COPY` of `pyforge/core` beside the steward copy |
| 4 | `pixi.toml` `[feature.dbgpt-sidecar]` | sidecar `/api/health` never 200 (`import pytz`) | `pytz` added |
| 5 | `pixi.toml` `[feature.python-agent-platform]` | `rjsmin` / `rcssmin` carried `build = "py312*"` pins, so the py3.14 env locked cp312 builds; image `compress` step: *rjsmin.jsmin couldn't be imported* | pins dropped; `pixi update rjsmin rcssmin` re-solved to `py314` builds; `pixi lock --check` clean |
| 6 | `src/platform` Ruff / mypy | 234 Ruff findings and 114 mypy errors accumulated over Epics 40–43 with nobody reporting them | safe `--fix` set applied; the rest is dated **per-file / per-module debt** in `src/platform/pyproject.toml` (exact codes, never blanket ignores), same shape as the Story 12.8 block |
| 7 | `config/settings/test.py` | imported `django_pyforge` before `.base` ran its Story 18.1 sys.path insert → mypy's Django plugin (bare interpreter) crashed: *Error constructing plugin instance* | imports reordered behind `.base` with an `# isort: split` |
| 8 | `db/changelog/changes/python-agent-platform-21-…-run-state-tenant.sql` | Story 42.5 hand-inserted a second header `--changeset python-agent-platform:21-1` (not `distribution:seq`; changeset 21 was an empty comment-only changeset) | header dropped; the DDL belongs to changeset 21. A database that already ran `21-1` will fail checksum validation on 21 — only a one-day-old local dev DB can be in that state |
| 9 | `pixi.toml` (python-agent-platform) | commit `098f0f0672` ("iml files", 2026-08-25) dropped the `cachebox <6` and `openfeature-provider-flagd <0.5.1` ceilings the policy suite guards | ceilings restored (`>=5.2.3,<6`, `>=0.5.0,<0.5.1`); the policy constant follows the raised floor |
| 10 | `platformapp/front_door/lane1_seed.py` (landed 2026-08-26, `21dd7f7224`) | `post_migrate` seeder called `add_child()` over wagtailcore's seeded plain `Page` at slug `home` → `ValidationError`; after any transactional flush it created the wrong `Locale` (`en-us` where Wagtail resolves `en`) → `Locale.DoesNotExist`, and never restored the root `Collection`, so every `Image.save()` after a flush died too. **Every DB-marked test (157) errored at test-database creation** on every CI run since | placeholder moved aside and dropped once no `Site` points at it; the content-variant Locale and the root Collection are seeded; two regression tests |
| 11 | `tests/test_herald_portal_deck_status.py`, `tests/test_mason_portal_last_diagnose.py`, `tests/test_station_portal_shells.py`, `tests/test_warden_portal_audit_start_get.py` | Story 42.5's prefixed role namespaces left eleven tests presenting bare `groups: ["herald"]` / `idp_roles = ["atlas"]` claims → 403 | claims carry `pyforge:station:<name>` |
| 12 | `tests/test_cloudevents_redis_broker.py` | one test ran `migrate` and inserted a `RunState` without a DB mark, monkeypatched `supervisor.lookup_runner` — a name `tasks.py` binds at import, so the patch never reached it — and wrote `CELERY_*` straight onto `django.conf.settings`, leaking into every later settings assertion | `django_db` mark; the no-op runner goes through `register_runner`; overrides through pytest-django's `settings` fixture |
| 13 | `tests/test_openfeature_file_flags.py` | rendered the core chart without an image pin after the chart adopted *no mutable default* | the three images pinned by digest exactly as `test_chart_invariants.py::_helm` does |
| 14 | `tests/test_restarts_reconcile.py` vs Mason Story 14.3 | the Steward 25.4 boot guard forbade any `pyforge` import in `pyforge/mason/boot.py`; Mason 14.3 (CAP-5) made `BootInterrupted` subclass `PyforgeError`, which pyforge-core's meta suite requires | the guard admits `pyforge.core.errors` only |
| 15 | `django_pyforge/assertion/client.py` (`85bd5103677`, 2026-08-26) | `Path.home() / ".bmad-loops"` fallback in the front door's loop-home lister — exactly what `test_supervisor_tables.py`'s laptop-state rule forbids | fallback removed; `BMAD_LOOP_HOME_ROOT` is the only source; no root → no homes (regression test) |
| 16 | Detectors workflow | `cfe_rebuild_guard_check` counted the synthetic `refs/pull/N/merge` commit as an unmirrored retro; `failure_catalog_check` was UNKNOWN on the runner (`No module named ruamel`) | `--no-merges` (+ mason unit test); the workflow installs a dedicated `detectors` pixi env, pip as the visible fallback |
| 17 | `scripts/fleet_scan.py` chain-currency | the `epics→sprint` edge fired for every idle station | edge retired with rationale; doctor unit test |
| 18 | `platformapp/front_door/runtime_catalog.py` | `_repo_root()` checked the image-shape rule (`manage.py` + `platformapp/`) on every parent before finishing the walk, so in a checkout it returned `src/platform` two levels short of the monorepo root and every console catalog page (`/console/dreams/` …) listed nothing | monorepo markers over the whole walk first; the image fallback is a second pass |
| 19 | `tests/test_station_api_seam.py` | expected token and the client's own mint both read the clock; across a second boundary they signed different `iat`/`exp` and the equality flaked (seen once in this pass) | clock frozen for the comparison |

Rows 1–5 and 16–17 belong to the platform / fleet surface; rows 6–15, 18–19 are the platform host
and its test suite. Rows 8, 10, 11, 15 are defects **introduced by this window's own stories**
(42.5, the Lane-1 CAP-2 seeder, 42.x portal claims, the 1.4 loop-home lister) that the dormant CI
never surfaced — the one finding no single story review could have shown.

**What did not land:** nothing from Epic 42/43 scope is missing. The `pap:AD-2` breach (row 2)
is deliberately *not* fixed here — the cutover spine routes it to Epic 44's capability ledger
(*Host GitHub Projects ingest → rebuild into pyforge-steward*), and the path dep only makes the
host bootable in CI meanwhile.

## Behavior verification

Not tests alone — the changed flows were exercised end to end on this machine, against an
ephemeral PostgreSQL 17.11 + pgvector and a Redis 7 on the CI job's DSNs
(`postgres://postgres:platform@localhost:5432/platform`, `redis://localhost:6379/0`), in the
`platform-ci-test` env, in the Platform CI test job's step order:

- `python manage.py check` → *System check identified no issues*.
- `ruff check .` → *All checks passed*.
- `mypy platformapp config tests` → *Success: no issues found in 150 source files*.
- `python -m pytest tests/policy` → 76 passed.
- `python -m db.sqlmigrate_extraction` → *sqlmigrate extraction ok (16 first-party migrations)*.
- `python -m pytest` (full suite) → **742 passed, 6 skipped, 0 failed, 0 errors, exit 0.** The
  progression across the pass: 9 failed / 573 passed / 157 errors (row 10's slug collision) →
  582 passed / 159 errors (row 10's Locale) → 11 failed / 730 passed (rows 10–12, 18) →
  1 failed / 741 passed (row 19) → green. The earlier "13 failed / 5 errors is environmental"
  baseline this repo carried was wrong: none of it was environmental.
- Image static pipeline (`collectstatic` → `compress --force` → `collectstatic`) replayed with
  the Containerfile's exact environment (`config.settings.production`, `COMPONENT_RUNTIME=local`)
  → 224 files, *Compressed 2 block(s) from 166 template(s)*.
- `pixi lock --check` → *Lock-file was already up-to-date* after every manifest edit.

On the PR's last push before these fixes (`da187d0f09`), the other workflows were already green:
CFE regression + equivalence net (33912193039), Coverage gates (33912193084), pyforge-core
(33912193108), pyforge-steward-five-tier (33912193077), pyforge-steward-fresh-clone (33912193068).
Detectors and Platform CI are the two this document's fixes re-green; the run ids land in
PR #1043's final comment.

## This session's own contribution to the window

The retro author is also the author of PR #1043, so the boundary is explicit: the epics' code was
written by the bmad-loop dispatches of 2026-08-31 → 2026-09-03; this session wrote rows 1–17 above,
the memlog moves and scoped stamps for every spec surface the fixes crossed, and this document.
None of the epic stories were re-implemented; the fixes are the smallest change that makes each
gate true again, and the debt blocks (row 6) record exactly what was deferred and why.

## Previous-retro follow-through

`retro-pyforge-steward-2026-08-31.md` carried **no action items** (its window was reconciliation
work that closed its own findings while landing). Nothing to check off; nothing regressed from it.

## Action items

1. **Burn down the dated debt blocks when their files are touched** — `[tool.ruff.lint.per-file-ignores]`
   (37 files, 81 file/code pairs) and the `[[tool.mypy.overrides]]` groups (24 modules) in
   `src/platform/pyproject.toml`. Owner: whichever story next edits a listed file; the block's own
   comment says so. Not a story of its own.
2. **`pap:AD-2` — the host must stop importing `pyforge.steward`.** Already owned: Epic 44 capability
   ledger row *Host GitHub Projects ingest → rebuild into pyforge-steward*. The `platform-ci-test`
   path dep is the interim and must be removed in the same story.
3. **Policy-suite parity before `pixi.toml` lands.** Row 9's regression came from an IDE-metadata
   commit that also touched pins, and the only guard was a Platform CI step nobody was running.
   Proposed, not applied: a repo-scope doctor detector that runs `tests/policy` (the manifest-only
   subset) so `detectors-ci` reds the PR, not a workflow that can be disabled. Owner: pyforge-doctor.
4. **`ruff format --check` is not gated** — 48 files under `src/platform` would be reformatted. Decide
   whether to gate it (one commit of churn) or keep `ruff check` as the only lint gate. Owner: operator.
5. **Changeset ids come from the extractor, never by hand.** Row 8 is the second hand-edited
   Liquibase changelog in the window's lineage; `db/sqlmigrate_extraction.py` already names the
   id CI expects. Proposed: the extraction gate refuses any `--changeset` line whose id is not in
   `sqlmigrate-map.yaml`. Owner: steward (the Story 27.2 / 41.3 lineage).

## Acceptance verdict

**Epic 42: accepted-with-open-items. Epic 43: accepted-with-open-items.**

Machine verdict: no `pending_stories` in either epic, so neither is *rejected*. Not plain
*accepted*, because four of the health-pass rows (8, 10, 11, 15) are defects the window's own
stories shipped past a CI that could not report them, and two of them (rows 10 and 8) would have
blocked every later database-backed story or deploy. The open items are exactly action items 1–2;
the rest of the table is fixed in the same PR that carries this retro.

## Open questions

- OQ1 / OQ3 from the 2026-08-31 retro are unchanged (they are cutover-spine questions and were
  answered there as `fnd:AD-14` / `fnd:AD-23` on 2026-09-04, not here).
- Whether Platform CI's `test` job should also run `ruff format --check` (action item 4).

## Assumptions

Headless run (`-H`), operator not consulted mid-retro; recorded so the trail survives:

- **Epic selection:** the invocation named Epics 42 and 43 together with the fleet CI health pass;
  both epics were retro'd in one document because the health pass is the only evidence that
  crosses their story boundaries.
- **Machine verdict** derived from `detect-epic --epic 42` / `--epic 43` (`pending_stories: []`,
  `story_count` 5 and 6) — accepted-with-open-items as argued above; no human override recorded.
- **`git_evidence.py` pre-pass not run:** the script rejected `--help` in this skill version; the
  diff range and per-story commits were derived by hand with `git log 8647d37684..HEAD`. Scope
  narrowed accordingly — commit-to-story attribution is by subject line, not by the script.
- **`bmad-review` not invoked on the epic diff:** the diff-scope lenses were replaced by running
  every CI gate the diff is subject to (§ Behavior verification), which is what surfaced rows
  6–15. Adversarial / edge-case review of the story code itself was **not** done in this pass and
  is not claimed.
- **Session logs** for the bmad-loop dispatches were not read; process lessons above come from
  git and CI evidence only.
- **Proposed transitions** for previous-retro action items: none (the 2026-08-31 retro carried
  none), so `--set-action-status` is not passed.
