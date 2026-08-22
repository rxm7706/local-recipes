---
title: 'Isolation and statelessness proven'
type: 'test'
created: '2026-08-21'
status: 'done'
baseline_revision: '150a8057b9076f768f59eaa9f61266de1f401fca'
final_revision: '17f0d9b95f36aafb872c1d500bda4b6252e66f4f'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md', '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/SPEC.md']
warnings: []
---

<intent-contract>

## Intent

**Problem:** Epic 11 claims cross-engine schema isolation (AD-5) and statelessness (AD-6) under both AD-17 integration patterns, but nothing proves either claim — and an unproven guarantee is exactly what CAP-2/CAP-3's success clauses say is not enough ("kill-and-replace losing any flow, session, or state is a failing test, not a bug report"). A 546-line WIP proof suite exists (`src/platform/tests/test_isolation_and_statelessness.py`, resumed from `backup/steward-a9b6f8d0`) but is unverified, and its Pattern-A proof does not yet cover the "no session" clause (credential state surviving the replacement).

**Approach:** Complete and verify the WIP suite: three claims, each as a real proof plus a "guard removed" companion that proves the real proof's own assertion logic would catch a regression (the 9.6 discipline — a suite that cannot fail is a failing suite). Claim 1: schema inspection over `public`/`langflow_schema`/`dbgpt_schema` after driving Langflow's real Alembic bootstrap (AD-16 Tier 1, no container). Claim 2: Pattern-A replacement — two fully independent `_LifespanManager` cycles; extend the WIP so cycle 2 also exercises cycle 1's API key (a real re-run through the replacement unit), covering flow + session/credential + write-path state. Claim 3: Pattern-B replacement — a real `docker compose kill`+`start` of the `dbgpt` service with a marker row in the shared `dbgpt_schema` surviving (AD-16 Tier 2, opt-in via `PLATFORM_DOCKER_COMPOSE_TESTS=1`); its guard-removed companion stays ungated so the discipline runs even where Tier 2 is unavailable.

## Boundaries & Constraints

**Always:** Guard-removed companions use locally-defined reproductions fed to the SAME assertion helpers the real proofs use — never a monkeypatch of production code (the `test_dashboard_isolation_proof.py` convention). DB connections go through the settings-derived DSN strings (`LANGFLOW_DATABASE_URL`/`DBGPT_DATABASE_URL` minus query string), never `django.db.connection` — order-independent of pytest-django's test-DB swap (the `langflow_integration/tests.py` rationale). The Pattern-B test always cleans up (container removed, probe table dropped) so `dbgpt_integration/tests.py`'s zero-tables-in-`dbgpt_schema` invariant holds regardless of outcome or ordering. Verification runs against real Postgres + Redis (AD-16 Tier 1: `platform-dev` per-user processes) with the missing `pytest-django`/`django-environ` pip-installed ephemerally.

**Block If:** the Pattern-A extension cannot prove session/credential survival through an already-public Langflow API surface (would force inventing a fake proof); or the live red/green mutation demo cannot be made to go red (that means an assertion is vacuous — a spec-level defect, not an environment problem).

**Never:** commit any pixi/requirements manifest or lock change for the ephemeral test deps. Never wire the docker-compose proof into the pip-only CI `test` job (it is opt-in Tier 2, per spec-11-2's precedent of live compose round trips verified manually). Never leave a silent pass where docker is unavailable — the skip reason must name the missing capability. Never touch sprint-status ledgers, push, or open PRs (the landing session owns those).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Schema isolation holds | Langflow Alembic bootstrap driven; all three schemas inspected via `pg_tables` | No table name appears in more than one schema; `langflow_schema` non-empty (anti-vacuous) | N/A |
| Isolation removed | Synthetic rows with a `public`/`langflow_schema` name collision fed to the same assertion helper | `AssertionError` raised | Proves the real check can fail |
| Pattern-A replacement | Flow created+run+API-keyed in lifespan cycle 1; cycle torn down; independent cycle 2 | Flow record fetchable, cycle-1 API key still authorizes a real re-run (200), write-path rows never lost | N/A |
| Pattern-A state in process memory only | Local in-process-only store wiped by a kill simulation, fed to the same assertion helper | `AssertionError` raised | Proves the real check can fail |
| Pattern-B replacement (opt-in) | Marker row in shared `dbgpt_schema`; real `docker compose kill`+`start` of `dbgpt`; same container id after | Marker row survives; service healthy again | Missing docker/opt-in → skip naming the capability; unhealthy-in-time → `pytest.fail` naming an environment problem |
| Pattern-B state tied to the sidecar's own storage | Same local store reproduction (identical guarantee basis), ungated | `AssertionError` raised | Runs even in pip-only CI |

</intent-contract>

## Code Map

- `src/platform/tests/test_isolation_and_statelessness.py` -- the WIP suite (all six tests exist); extend the Pattern-A pair of cycles for API-key/session survival, verify everything else as-is
- `src/platform/langflow_integration/tests.py` -- convention source (DSN handling, `_LifespanManager` usage, flow helpers); read-only
- `src/platform/dbgpt_integration/tests.py` -- zero-tables invariant the Pattern-B cleanup must preserve; read-only
- `src/platform/compose/compose.yml` -- the `dbgpt` service the Pattern-B proof kills/starts; read-only
- `src/platform/config/settings/base.py` -- `LANGFLOW_DATABASE_URL`/`DBGPT_DATABASE_URL` derivation the DSNs come from; read-only

## Tasks & Acceptance

**Execution:**
- [x] `src/platform/tests/test_isolation_and_statelessness.py` -- extend `_cycle_one_create_and_run_flow`/`_cycle_two_refetch_flow` so cycle 2 re-runs the flow with cycle 1's API key and the final row-count check asserts growth (cycle-1 rows never lost, cycle-2 run really wrote) -- covers the AC's "no session" clause with a real credential surviving replacement
- [x] Stand up AD-16 Tier 1 locally (per-user Postgres + Redis from the `platform-dev` env binaries -- the conda env resolves PostgreSQL 18.6, a major ahead of CI's `postgres:17` service image, noted honestly; ephemeral `pip install pytest-django django-environ`) and run the full `src/platform` pytest suite -- proves the new module coexists with every existing test
- [x] Run the Pattern-B proof for REAL (`PLATFORM_DOCKER_COMPOSE_TESTS=1`, docker present, prebuilt `compose-dbgpt` image) -- the story's own kill+restart round trip, not just the skip path
- [x] Live mutation demo (the 9.6 discipline, beyond the always-on companions): temporarily plant a cross-schema duplicate table (claim 1), temporarily delete the flow row between cycles (claim 2), temporarily delete the marker row before the final assert (claim 3, if Tier 2 available) -- watch each real test go RED, restore, watch it go GREEN; record evidence in Dev Notes

**Acceptance Criteria:**
- Given Langflow's real Alembic bootstrap has run, when `public`/`langflow_schema`/`dbgpt_schema` are inspected together, then each engine's tables live only in its own schema and the check is demonstrably non-vacuous (AC1)
- Given the same assertion helper, when fed rows with a cross-schema name collision, then it raises — the isolation check can fail (AC2)
- Given a flow created+run in one lifespan cycle, when that cycle is torn down and a fully independent cycle starts, then the flow record, its write-path rows, AND cycle 1's API key all survive — the key authorizes a real re-run in cycle 2 (AC3)
- Given the same statelessness assertion, when fed a store wiped by a kill simulation, then it raises — the Pattern-A check can fail (AC4)
- Given a marker row in the shared `dbgpt_schema`, when the real `dbgpt` compose service is killed and restarted (same container), then the marker survives; without docker/opt-in the test skips with a reason naming the missing capability, never a silent pass (AC5)
- Given the ungated Pattern-B companion, when state is modeled as tied to the sidecar's own storage, then it raises even where Tier 2 is unavailable (AC6)

## Spec Change Log

## Review Triage Log

### 2026-08-21 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 1, medium 3, low 3)
- defer: 1: (high 0, medium 0, low 1)
- reject: 4
- addressed_findings:
  - `[high]` `[patch]` Module-level `pytest.importorskip("langflow")` skipped the whole module in the pip-only CI lane, falsifying AC6's "runs even in pip-only CI" (and silently un-running the AC4 companion there too) — re-gated per-test via a `requires_langflow` skipif mark; proven in a langflow-less `requirements/local.txt` venv: 3 passed + 3 skipped
  - `[medium]` `[patch]` The two assertions this story added (API-key survival, counts growth) had zero red-path evidence, violating the story's own 9.6 discipline — both now demonstrated red live (apikey-row deletion → HTTP 403 red; partial `vertex_build` deletion → doubling red) and restored green; a permanent bogus-key vacuousness guard added in cycle 2 (empirically 403, so key auth is not inert under `AUTO_LOGIN`)
  - `[medium]` `[patch]` Strictly-greater growth masked PARTIAL loss of cycle-1 rows behind cycle-2's own writes — replaced with exact per-table doubling (`== 2 *`), which the deterministic flow supports; the masked scenario was reproduced live (3 > 2 passes, 3 != 4 reds)
  - `[medium]` `[patch]` Any cycle-2 rerun failure (500/timeout) was misdiagnosed as credential loss with all diagnostics discarded — rerun status+body now ride in the assertion message (demonstrated in the live red: the 403 body appears verbatim)
  - `[low]` `[patch]` Cycle-2's teardown-before-count-read ordering (which the doubling assertion depends on) was unnarrated — docstring now states it
  - `[low]` `[patch]` Spec said "Postgres 17" for Tier 1 while the conda env runs 18.6 and only CI runs 17, and Dev Notes' "CI's shape" read as a version claim — Task 2 wording made honest; terminology note added
  - `[low]` `[patch]` Verification's expected results held only in an environment the commands never established — precondition paragraph added, including the honest langflow-less result shape

Rejected (recorded for auditability, dropped from action): a timeout on the cycle-2 rerun call (no call in this file or its sibling module carries one — harness-level timeouts govern; adding one only here would be inconsistent noise); frontmatter incompleteness mid-review (the workflow's own Finalize step stamps `final_revision`/`done`); AC1 anti-vacuity beyond `langflow_schema` (the real regression paths — leak into a populated `public`, or bootstrap landing only in `public` — are both caught by the existing two-pronged assertion, demonstrated red live via the planted `public.flow`); Dev-Notes-as-wall (dated evidentiary paragraphs are this project's own promoted-spec convention, e.g. spec-11-3).

## Design Notes

The Pattern-B real proof kills/restarts the sidecar while the marker lives in the platform's own PostgreSQL — that asymmetry IS the property: statelessness means the compute unit holds nothing, so replacing it cannot lose `dbgpt_schema` state. DB-GPT's own metadata store is the dated AD-6 bounded exception (SQLite + PVC, Story 10.5's two-boot test) and is deliberately NOT this story's surface — asserting it here would contradict the architecture's own exception.

`kill`+`start` (not `up --force-recreate`) is chosen deliberately: it reuses the same container, and the test asserts that premise (`container_after == container_before`) so a compose behavior change cannot silently turn the proof into a different experiment.

Both guard-removed companions share one `_InProcessOnlyStore` reproduction because both patterns' statelessness guarantee rests on the identical basis — state in externally-shared storage, never in the compute unit's own memory/disk.

**Dev Notes -- real verification, 2026-08-21 (Story 11.4):** the Pattern-A extension landed as specced (`_cycle_one_create_and_run_flow` now returns `(flow_id, api_key)`; `_cycle_two_refetch_and_rerun_flow` re-fetches AND re-runs the flow authorized by cycle 1's key; the final check asserts strict per-table row-count GROWTH). AD-16 Tier 1 stood up from the worktree's own `pixi install --frozen -e platform-dev` env binaries: fresh `initdb` cluster (PostgreSQL 18.6, trust auth) on :5432 + `redis-server` on :6379, `DATABASE_URL=postgres://postgres:platform@localhost:5432/platform` (password inert under trust — CI's shape). Tier 1 story suite: **5 passed + 1 skipped**, the skip reason naming the missing capability verbatim ("opt-in only (AD-16 Tier 2): set PLATFORM_DOCKER_COMPOSE_TESTS=1 with docker on PATH…"). Tier 2 (`PLATFORM_DOCKER_COMPOSE_TESTS=1`): **6 passed** with a REAL `docker compose up -d dbgpt` → healthy → `kill` → `start` → healthy round trip — prebuilt `compose-dbgpt:latest` reused (no `--build`), container `compose-dbgpt-1` observed live mid-run (id `57d17cd3885e` on the final green run, `health: starting` → `healthy` in ~6s of polling), same-container-id premise asserted in-test, docker test itself 14.25s; after every run `docker compose ps -a` shows nothing and `dbgpt_schema` is back to zero tables (the 11.2 invariant). Full suite from `src/platform`: **48 passed + 1 skipped** (~20s), langflow_integration + dbgpt_integration + platformapp + tests + meta all green together. Live mutation demos, all run RED for real then restored GREEN: (1) `CREATE TABLE public.flow (id int);` → `test_each_engines_tables_are_confined_to_their_own_schema` FAILED `AssertionError: tables leaked across schemas (table, first-schema, also-in): [('flow', 'langflow_schema', 'public')]` → `DROP TABLE public.flow;` → 1 passed; (2) temporary psycopg `DELETE FROM langflow_schema.flow WHERE id = %s` inserted between cycles → `test_pattern_a_kill_and_fresh_start_loses_no_flow_state` FAILED `AssertionError: the flow record did not survive the kill+restart cycle` → edit reverted precisely (git diff carries only the permanent extension) → 1 passed; (3) temporary marker-row DELETE right after the restart, before the survival assert → `test_pattern_b_sidecar_kill_and_restart_preserves_shared_dbgpt_schema_state` FAILED `AssertionError: the dbgpt_schema marker row did not survive the kill+restart cycle` through a real 16.8s round trip → reverted → 1 passed (16.45s). The spec's Verification gates exposed two latent WIP defects, both fixed in the story file: two call sites `ruff format --check` rejects (magic-trailing-comma one-liners, now split) and a mypy `[index]` error on `cursor.fetchone()[0]` (now None-guarded; the identical pattern in `langflow_integration/tests.py` never erred only because that file sits outside the `mypy platformapp config tests` surface). Gates: `ruff check` + `ruff format --check` clean; `mypy platformapp config tests` = "Success: no issues found in 50 source files", run from a pip venv built from `requirements/local.txt` — the CI-faithful surface, since mypy 1.17.0 INTERNAL-ERRORs following imports into the conda env's installed `langchain` (present only via langflow, which the pip-only CI lane never installs). Ephemeral deps (nothing committed, no manifest/lock change): `pip install --no-deps` into the worktree's platform-dev env of the local.txt/base.txt-pinned test+host deps absent from the conda solve (pytest 8.4.1, pytest-django 4.11.1, django-environ 0.12.0, factory-boy 3.3.2+faker, mypy 1.17.0, django-stubs 5.2.2+ext, ruff 0.12.5, crispy-forms 2.4, crispy-bootstrap5, allauth 65.10.0+fido2+qrcode, compressor 4.5.1+rjsmin+appconf, django-redis 6.0.0, model-utils 5.0.0, celery-beat 2.8.1+timezone-field+cron-descriptor+crontab, whitenoise 6.9.0, slugify+text-unidecode, rcssmin, hiredis); `lint-imports` (import-linter 2.13) ran from an isolated scratch venv appended to PATH instead — it requires `rich>=14.2.0` while the conda env carries langflow-pinned rich 13.9.4, and in-env it dies with rich's "Only one live display may be active at once" (contract verdict: "Contracts: 1 kept, 0 broken."). `src/platform/.langflow/` confirmed gitignored (`.gitignore:837`), never staged. (Terminology note: "CI's shape" above refers to the `DATABASE_URL` credential/URL shape matching `platform-ci.yml`'s, NOT the Postgres major -- the conda env runs 18.6 while CI's service image is `postgres:17`; see Tasks item 2.)

**Dev Notes -- review pass, 2026-08-21 (Story 11.4):** the adversarial + edge-case review produced 7 patches, all applied and re-verified live. (1) The high finding: `pytest.importorskip("langflow")` at module scope meant the whole module -- including all three guard-removed companions -- skipped in the pip-only CI `test` job, making AC6's "runs even in pip-only CI" false as written; re-gated per-test via a `requires_langflow` skipif mark on the two langflow-dependent real proofs, and proven in a langflow-less venv built from `requirements/local.txt` (the CI-faithful surface): **3 passed + 3 skipped in 0.06s** -- the companions genuinely run in that lane now. (2) The two assertions this story ADDED got their own live red demos (they had none -- a 9.6-discipline violation the review caught): temp `DELETE FROM langflow_schema.apikey` between cycles → RED `AssertionError: cycle 1's API key (its authority for cycle 2's real re-run; cycle-2 re-run response was HTTP 403: {"detail":"Invalid or missing API key"}) did not survive the kill+restart cycle` → reverted → green; temp single-row `vertex_build` DELETE (a PARTIAL loss) → RED `AssertionError: the flow's write-path row counts (expected exact doubling, got cycle-1 {'vertex_build': 2, 'transaction': 2} -> cycle-2 {'vertex_build': 3, 'transaction': 4}) did not survive the kill+restart cycle` → reverted → green. That second red is the exact scenario the review flagged: 3 > 2 would have PASSED the original strictly-greater check -- the counts assertion is now exact doubling (`== 2 *` per table, both dicts in the failure message), which the deterministic TextInput→TextOutput flow supports (2 `vertex_build` + 2 `transaction` rows per run, observed stable across runs). (3) A permanent vacuousness guard rides in cycle 2: a deliberately invalid `x-api-key` must be rejected (verified in installed Langflow source AND empirically -- HTTP 403 -- key auth is DB-validated even under `AUTO_LOGIN`), so a future Langflow upgrade cannot silently hollow out the credential proof; it runs after the real re-run so a vacuous-auth bogus run could never distort the counts. (4) Cycle-2 rerun failures now carry the response status+body in the assertion message (a 500/timeout no longer masquerades as "key gone" with no evidence). (5) Cycle-2's docstring now narrates the teardown-before-count-read ordering the doubling assertion depends on. Full re-verification after all patches: Tier 1 **5 passed + 1 skipped**; pip-lane venv **3 passed + 3 skipped**; Tier 2 (`PLATFORM_DOCKER_COMPOSE_TESTS=1`, real kill+start round trip) **6 passed in 27.54s**; full suite **48 passed + 1 skipped**; `ruff check` + `ruff format --check` clean; `mypy platformapp config tests` clean; `docker compose ps -a` empty and `dbgpt_schema` back to zero tables. One review finding deferred (the unguarded `cursor.fetchone()[0]` in `langflow_integration/tests.py`, a pre-existing latent defect in a file this story treats as read-only) -- recorded in the Tier-3 deferred-work file as DW-FU-11-4.

## Verification

**Commands:**

All commands below assume the AD-16 Tier-1 environment the Dev Notes describe: the `platform-dev` pixi env python with the ephemeral pip test deps installed, live per-user Postgres on :5432 (`DATABASE_URL=postgres://postgres:platform@localhost:5432/platform`) and Redis on :6379 (`REDIS_URL=redis://localhost:6379/0`). In a shell without langflow the honest result of the first command is instead 3 passed + 3 skipped (the two langflow-gated real proofs + the docker proof skip; the three guard-removed companions still run -- that IS the pip-only CI lane's expected shape).

- `cd src/platform && pytest -v tests/test_isolation_and_statelessness.py` -- expected: 5 pass + 1 skip (Tier 1, docker proof gated off)
- `cd src/platform && PLATFORM_DOCKER_COMPOSE_TESTS=1 pytest -v tests/test_isolation_and_statelessness.py` -- expected: 6 pass (Tier 2, real kill+restart)
- `cd src/platform && pytest -v` -- expected: full suite passes (no cross-test interference; `dbgpt_schema` zero-tables invariant intact)
- `cd src/platform && ruff check tests/test_isolation_and_statelessness.py && ruff format --check tests/test_isolation_and_statelessness.py` -- expected: clean
- `cd src/platform && mypy platformapp config tests` -- expected: clean

**Manual checks (if no CLI):**
- Each live mutation (planted duplicate table / deleted flow row / deleted marker) turns exactly its real test RED; restoring turns it GREEN — evidence in Dev Notes
- `docker compose -f src/platform/compose/compose.yml ps -a` shows no lingering `dbgpt` container after the real run

## Auto Run Result

**Status:** done (branch `steward/11-4-isolation-statelessness-land`, implementation commit `17f0d9b95f36`; not pushed — the landing session owns push/PR/ledger).

**Summary:** Resumed the 546-line WIP proof suite from `backup/steward-a9b6f8d0`, extended its Pattern-A proof to cover the "no session" clause (cycle 2 re-runs the flow with cycle 1's API key; write-path counts must exactly double), verified everything live at AD-16 Tier 1 AND Tier 2 (a real `docker compose kill`+`start` of the `dbgpt` sidecar), and hardened it through an adversarial + edge-case review pass (7 patches, headline: the module-level langflow importorskip was silently disabling all three guard-removed companions in the pip-only CI lane, falsifying AC6 — now per-test gating, proven in a langflow-less venv).

**Files changed:**
- `src/platform/tests/test_isolation_and_statelessness.py` — Pattern-A API-key/doubling extension; per-test `requires_langflow` gating; bogus-key vacuousness guard; evidence-bearing failure messages; two gate-forced WIP fixes (formatter, `fetchone` None-guard)
- this spec — authored (new), with dated Dev Notes for both verification passes, the review triage log, and DW-FU-11-4's deferral context

**Review findings breakdown:** 7 patched (1 high, 3 medium, 3 low), 1 deferred (DW-FU-11-4, Tier-3 file), 4 rejected. No intent_gap, no bad_spec, no loopbacks.

**Verification:** Tier 1 story suite 5 passed + 1 skipped; pip-lane (langflow-less local.txt venv) 3 passed + 3 skipped; Tier 2 real docker round trip 6 passed (27.54s; same-container-id premise asserted in-test); full `src/platform` suite 48 passed + 1 skipped; ruff check/format clean; mypy clean (50 files); `dbgpt_schema` zero-tables invariant intact and no containers left behind. Five live red/green mutation demos total (planted `public.flow`; deleted flow row; deleted marker row; deleted apikey rows; partial `vertex_build` deletion) — every real assertion demonstrated able to fail.

**Residual risks:** the docker-compose proof is opt-in (`PLATFORM_DOCKER_COMPOSE_TESTS=1`) by design and runs in no CI job — it was proven live on this host, and the skip reason names the capability; the Tier-1 Postgres was 18.6 (conda) vs CI's 17 — noted honestly in Tasks/Dev Notes; the langflow-dependent proofs still run only where langflow is installed (the `platform-dev`/`python-agent-platform` envs), same as the rest of the langflow test surface.
