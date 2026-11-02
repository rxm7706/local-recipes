---
title: "118.6: The attended NKP sign-in, spawn and landing probes are tracked commands"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-2-nebi-pack-and-the-data-science-pack-reach-healthy-on-kind-and-a-notebook-spawns.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-5-deploy-nic-up-installs-the-packs-under-nebari-apps-and-waits-for-the-sync-it-rendered.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/how-to/host-nebari.md
  - pixi.toml
---

<intent-contract>

## Intent

**Problem:** CAP-177's success names observables a person checks by hand: `https://hub.<domain>` signs in through Keycloak, a `small-instance` server spawns, and the landing page shows the JupyterHub and Nebi cards. The attended kind runs of 2026-10-31 proved them with `kc_signin.py`, `hub_signin.py` and `landing_cards.py`, and the deferred-work ledger closed DW-steward-118-1, DW-steward-118-2 and DW-steward-118-2-2 on those runs. None of the three scripts is tracked. So the success line cannot be repeated, and Story 118.3 AC3 has to prove sign-in again on Hetzner with nothing to run (EGM audit 2026-11-01, finding STW-D-R4, cluster STW-CL-10; contested, settled for the refute skeptic on the bootstrap job, which already has a tracked `kubectl` check in Story 118.2's spec AC2).

**Approach:** Add `src/shared/packages/pyforge-steward/tests/integration/` with three attended probes and one pixi task to run them. Each probe reads the domain and the bootstrap admin credential from `nic outputs --show-secrets` at run time and stores neither. Each probe skips with the reason named when no kubeconfig is reachable, so the task is safe on any host. `pyforge-steward-test` and `pyforge-steward-live-test` keep collecting only `tests/unit` and `tests/meta`. The how-to names the command, and the three closed DW rows gain a dated note citing it. The Keycloak bootstrap job is out of scope.

Ledger key: `118-6-the-attended-nkp-sign-in-spawn-and-landing-probes-are-tracked-commands`.
Type / Effort / Deps: fix / M / S-118.5.

### Living CAP citations

- **`spec-pyforge-steward` CAP-177** — the sign-in, spawn and landing-card observables of its success line; this story makes them repeatable commands. A fix: no new CAP, no FR, no AD moves (AD-1: the probes call the cluster's endpoints and `nic outputs`, never reimplement them).

## Acceptance Criteria

- **AC1 — The probes.** `src/shared/packages/pyforge-steward/tests/integration/` holds attended probes for: the landing SPA's Keycloak auth-code + PKCE sign-in as the bootstrap admin (Story 118.1 AC2); the hub's OAuth sign-in through Keycloak followed by a `small-instance` spawn that reaches ready; and the landing page's JupyterHub and Nebi cards, both reported healthy.
- **AC2 — No stored secret.** Each probe reads the domain and the admin credential from `nic outputs --show-secrets -f <config>` at run time. No credential is written to disk, to a log, to the journal or to pytest output; a unit-level check over the probe module's output proves the password never appears.
- **AC3 — Safe anywhere.** With no reachable kubeconfig every probe skips with its reason named, and the task exits 0. The config path is a parameter, and the domain comes from the config, so Story 118.3 AC3 reuses the probes on the Hetzner config unchanged.
- **AC4 — One command.** A task under `[feature.pyforge-steward.tasks]` in `pixi.toml` runs `tests/integration` alone; `pyforge-steward-test` and `pyforge-steward-live-test` still collect only `tests/unit` and `tests/meta`.
- **AC5 — The record.** `docs/how-to/host-nebari.md` names the task. DW-steward-118-1, DW-steward-118-2 and DW-steward-118-2-2 in `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` each gain a dated note citing it; their `RESOLVED` verdicts are not rewritten.
- **AC6 — Green.** `pyforge-steward-test` and `lint-types` exit 0, and the spec-surface stamp is scoped to `pyforge-steward/spec-pyforge-steward` after its memlog reconcile.

## Boundaries & Constraints

**Always:**
- Read every credential at run time from `nic outputs --show-secrets`; skip, never fail, when the cluster is absent.
- Keep the probes out of the default station suite and out of CI; they are attended.

**Never:**
- Never commit a credential, a kubeconfig or a captured token; never add the Keycloak bootstrap-job check here (Story 118.2's spec owns it); never touch `deploy_nic.py` or `deploy_nic_packs.py`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-177.

Parent: `spec-pyforge-steward` CAP-177

- Dream: `docs/dreams/pyforge-steward.md` § *2026-10-31 — Nebari hosted: NKP on kind, then Hetzner, with the data-science pack*, and its Realization log's 2026-11-01 (the EGM fleet audit) entry.
- Epic: Epic 118.
- Ledger key: `118-6-the-attended-nkp-sign-in-spawn-and-landing-probes-are-tracked-commands`.
- Deps: S-118.5.
- Surface: `marshal-policy.toml` `[epic_surfaces]."118"`; the story's files are `src/shared/packages/pyforge-steward/tests/integration/` (new), `pixi.toml`, `docs/how-to/host-nebari.md` and `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`.
- Audit: EGM audit 2026-11-01 finding STW-D-R4 (cluster STW-CL-10); residue `_bmad-output/projects/pyforge-steward/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Minted 2026-11-01 by the EGM fleet audit landing (marshal Story 113.7); lands in that PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/integration -q -rs` — expected: exit 0; with no kubeconfig every probe is skipped with its reason.
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta --collect-only -q` — expected: no path under `src/shared/packages/pyforge-steward/tests/integration` collected.
- `grep -n 'tests/integration' docs/how-to/host-nebari.md` — expected: exit 0.
- `pixi run -e pyforge-guild lint-types` — expected: exit 0.

**Attended (the operator runs this on a live cluster):**
- the new task on `src/platform/deploy/nic/my-nebari-local.yaml` — expected: exit 0 with the three probes passed.

**Run before the push:**
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `deferred-work-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done (independent review passed 2026-11-01; see Review Triage Log)

Summary: implemented 2026-11-01 in the EGM audit landing worktree (`egm-audit-2026-11`). Not committed. The attended run on a live cluster is still the operator's.

What changed:

- `src/shared/packages/pyforge-steward/tests/integration/` (new):
  - `nkp_probes.py` is the shared client. `connect()` reads the config and resolves any `env:` credentials through `deploy_nic.load_secret_env` (keys). It then runs `nic kubeconfig -f <config>` in memory and checks that the API server it names accepts a TCP connection. Only then does it run `nic outputs --format json --show-secrets -f <config>`. When there is no config, no `nic`, no credential, no kubeconfig or no API server, it raises `ClusterAbsent` with the reason. It also has the Keycloak auth-code + PKCE sign-in (the redirect is read, never followed into the SPA), the hub OAuth sign-in and `spawn_and_stop`, and the landing-card parser.
  - `Secret` never prints its value. Every `*password` field from `nic outputs`, every keys-resolved credential and every access token joins a registry that `redact` and `scrub_report` scrub.
  - TLS is verified except for a `certificate.type: selfsigned` config. `--nkp-connect-to` sends connections for `<domain>` and `*.<domain>` to an address (the rootless-kind port-forward) and keeps SNI and the Host header.
  - `conftest.py` adds `--nkp-config` (default `src/platform/deploy/nic/my-nebari-local.yaml`) and `--nkp-connect-to`. It provides the session fixture `nkp`, which skips with the `ClusterAbsent` reason, and a `pytest_runtest_makereport` wrapper that scrubs every report.
  - Three probes (AC1):
    - `test_nkp_landing_signin.py`: client `nebari-system-nebari-landing-spa`, the token's `preferred_username` is `admin`.
    - `test_nkp_hub_spawn.py`: `/hub/api/user` is `admin`, `POST /hub/spawn profile=small-instance` reaches ready within 300 s, and the server is then stopped. The probe refuses to start when `admin` already runs a server.
    - `test_nkp_landing_cards.py`: `/api/v1/services` with the SPA bearer shows JupyterHub and Nebi as `healthy`. The response shape follows nebari-landing's `internal/cache/service_cache.go`.
  - `test_nkp_probes_offline.py` holds 27 cluster-free checks (21 at first, 6 more from the fix round below).
    - AC2: a stand-in Keycloak shows the password goes to Keycloak alone, and a refused sign-in's message omits it. A real pytest subprocess over a copy of the conftest shows that a failing probe which prints the password and raises with it leaves only `***` in pytest's output. Deleting the scrub hook fails that check (mutation run on a scratch copy).
    - AC3: each skip reason, and `outputs --show-secrets` is never asked for without a reachable cluster.
    - Also covered: the spawn and stop sequence, and both card response shapes.
- `pixi.toml`:
  - New task `[feature.pyforge-steward.tasks.pyforge-steward-nkp-probes]` runs `pytest src/shared/packages/pyforge-steward/tests/integration -q -rs -p no:cacheprovider` (AC4).
  - `pyforge-steward-test-coverage` now passes `--suites unit`. Its driver defaults to `unit,integration` and would otherwise run the attended probes under a coverage evaluate. `pyforge-steward-test` and `pyforge-steward-live-test` are unchanged and still name only `tests/unit` and `tests/meta`.
- `docs/how-to/pixi-tasks.md` is regenerated (`python scripts/docs_pixi_tasks.py`). The only change is the new task row and the render stamp.
- `docs/how-to/host-nebari.md` gains § *Check sign-in, spawn and the landing cards*, which names the task, `tests/integration` and the two options (AC5).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`: DW-steward-118-1, DW-steward-118-2 and DW-steward-118-2-2 each gain a `note: 2026-11-01` line citing the task. Their `resolution:` and `verified:` lines are unchanged (AC5).
- `spec-pyforge-steward/.memlog.md` has one surface-reconcile event naming every path above. CAP-177's promise is unchanged, so there is no second event.
- Out of scope, as the spec requires: the Keycloak bootstrap-job check, `deploy_nic.py` and `deploy_nic_packs.py`.

Commands run (exit codes read from `$?`):

- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/integration -q -rs` exited 0: 21 passed, 3 skipped. Each skip reads `no reachable kubeconfig: nic kubeconfig exited 1: … could not locate any control plane nodes for cluster named 'my-nebari-local'`.
- `pixi run --frozen -e pyforge-steward pyforge-steward-nkp-probes` exited 0 with the same result. With `-- --nkp-config src/platform/deploy/nic/absent.yaml` it exited 0, and the skip reason names the missing config.
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta --collect-only -q` exited 0: 3537 collected, and none is under `tests/integration`.
- `grep -n 'tests/integration' docs/how-to/host-nebari.md` exited 0.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` exited 1: 1743 passed, 2 skipped, 1 failed. The failure is `tests/meta/test_station_tests_trigger_map.py::test_every_read_and_declared_glob_fires_its_job`. Its 7 findings are all reads added by other stations' in-flight edits in this shared worktree: mason's `test_mason_skills.py` and `test_persona_consults_cfe.py`, and scribe's `test_instruction_surface_parity.py` and `test_guild_env_membership.py`. Their paths are missing from `.github/workflows/pyforge-station-tests.yml`. None comes from this story, because CI never collects steward's `tests/integration`.
- `pixi run --frozen -e pyforge-steward pyforge-steward-live-test` exited 0: 1684 passed, 2 skipped, then 72 passed.
- `pixi run --frozen -e pyforge-guild lint-types` exited 1. The failure is ruff I001 in pyforge-doctor's in-flight `tests/unit/test_sources_pages_liveness.py`, which is not this story's file. The legs run one by one gave `ruff-format` 1 (pyforge-marshal's in-flight files; pyforge-steward ok), `mypy` 0, `target-version-check` 0 and `precommit-config-check` 0. pyforge-steward is `ok` in every leg. `ruff check` and `ruff format --check` over the package's `src` and `tests` both exited 0.
- `deferred-work-check`, `chain-completeness-check`, `story-status-check`, `spec-surface-check` and `python scripts/docs_pixi_tasks.py --check` (all `-e pyforge-guild`) each exited 0.

Left for the session owner:

- The co-governor reconciles and the scoped stamps. `pixi.toml` is also governed by doctor `spec-pixi-candidate-currency`, herald `spec-deck-family-currency`, `spec-deck-family-lockstep` and `spec-pyforge-pages`, marshal `spec-pyforge-core` and `spec-pyforge-marshal`, and steward `spec-pyforge-unifying-strategy`. `docs/how-to/host-nebari.md` and `docs/how-to/pixi-tasks.md` are governed by doctor `spec-pyforge-doctor`.
- The attended run of the task on `src/platform/deploy/nic/my-nebari-local.yaml` (the operator's).

### 2026-11-01 — Fix round (review_loop_iteration 1)

This round fixes the review's AC2 failure in `tests/integration/nkp_probes.py` and adds six offline checks to `tests/integration/test_nkp_probes_offline.py`. Nothing else changed. Not committed.

- **The URL-encoded password.**
  - `register()` now adds every form a value can print in: raw, `quote_plus`, `quote`, `quote(safe="")`, and repr-escaped (a quote or a backslash inside a local's repr).
  - `Browser.request` builds the form body inside the `Request(...)` call, so there is no `data` local.
  - `submit_keycloak_login` passes the `Secret` itself. Only `_form_body` reveals it, and that frame returns before anything can fail. Under `-l` the `form` funcarg shows `Secret('***')`. When locals print through pprint (`-l` at verbosity above 1), pprint has no password string and no body bytes to split across lines.
- **The token response.**
  - `keycloak_pkce_signin` registers every `*token` string in the token response (access, refresh and ID) as soon as the response parses.
  - `token_claims` keeps only the claims segment in a local, so the access token's signature never sits in a local on its own.
- **Two fixes in the same file.**
  - `Browser.request` also turns `http.client.HTTPException` (a malformed answer) into `ProbeError`. If it propagated, its traceback would show urllib's frames, and their request headers hold the session cookies.
  - `_StopRedirect.redirect_request` now annotates `headers` as `http.client.HTTPMessage`, typeshed's type. That was the module's one mypy error; mypy over the module now exits 0.
- **The new offline checks.** `RESERVED` is a long password with spaces, URL-reserved characters, both quotes and a backslash.
  - `test_a_registered_secret_is_scrubbed_in_every_form_it_can_print_in`.
  - `test_a_credential_post_that_fails_never_prints_the_password_in_any_form[truncated|untruncated]`: a real pytest under `-l`, then `-l -vvv`, runs `submit_keycloak_login` against a closed port. The failure happens inside the credential POST. No raw, URL-encoded or repr-escaped form of the password is printed, whole or as any ten-character piece.
  - `test_a_token_response_that_fails_its_check_never_prints_a_token[truncated|untruncated]`: a stand-in Keycloak answers access, refresh and ID tokens, and the access token's claims do not parse. No token is printed, and neither is the signature on its own.
  - `test_an_answer_that_is_not_http_fails_as_a_probe_error`.
- **The checks fail without the fix.**
  - Against the module as reviewed, all five new leak checks failed. The output carried the password's `quote_plus` and repr forms, the refresh and ID tokens, and the signature segment.
  - Each change was then reverted alone on a scratch copy outside the worktree, and each turned a check red:
    - the registered forms: the unit check;
    - the token registration and the claims-segment change: both token cases;
    - the in-call body and the `Secret` pass-through: the untruncated credential case;
    - the `HTTPException` catch: the non-HTTP case.

Commands run (exit codes read from `$?`):

- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/integration -q -rs` exited 0: 27 passed, 3 skipped. Each skip names the missing `my-nebari-local` control plane.
- `pixi run --frozen -e pyforge-steward pyforge-steward-nkp-probes` exited 0 with the same result.
- `pytest …/tests/unit …/tests/meta --collect-only -q` exited 0: 3537 collected, 0 under `tests/integration`.
- `grep -n 'tests/integration' docs/how-to/host-nebari.md` exited 0.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` exited 1: 1743 passed, 2 skipped, 1 failed. The failure is the same `test_station_tests_trigger_map.py::test_every_read_and_declared_glob_fires_its_job`, with the same 7 mason and scribe findings the review recorded. None comes from this story.
- `pixi run --frozen -e pyforge-guild lint-types` exited 1. The failure is its ruff leg: I001 in pyforge-doctor's in-flight `tests/unit/test_sources_pages_liveness.py`. Run one by one, the other legs exited 0: `ruff-format`, `mypy`, `target-version-check` and `precommit-config-check`. pyforge-steward is `ok` in every leg. Run from the package, `ruff check` and `ruff format --check` over `tests/integration` exited 0.
- `chain-completeness-check`, `story-status-check`, `deferred-work-check` and `spec-surface-check` (`-e pyforge-guild`) each exited 0.

Memlog: no new event. The existing surface-reconcile event already names both changed files by their full literal paths.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), finding STW-D-R4, cluster STW-CL-10; in the audit landing PR.

## Review Triage Log

### 2026-11-01 — Independent review (reviewer: independent session)

Verdict: **fail**. The status goes back to `in-progress`. One AC2 defect must be fixed. Everything else held.

What was checked (exit codes read from `$?`, in worktree `egm-audit-2026-11`):

- The diff of every file the implementer reported, read against the ACs and Boundaries. The six new `tests/integration/` files were read in full. `git diff HEAD --stat -- src/shared/packages/pyforge-steward/src/` is empty, so `deploy_nic.py` and `deploy_nic_packs.py` are untouched. The probes contain no bootstrap-job check.
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/integration -q -rs`: exit 0, 21 passed and 3 skipped. Each skip names `no reachable kubeconfig: nic kubeconfig exited 1: … could not locate any control plane nodes …` (AC3).
- `pixi run --frozen -e pyforge-steward pyforge-steward-nkp-probes`: exit 0. With `-- --nkp-config src/platform/deploy/nic/absent.yaml` it also exits 0, and the skip reads `config … does not exist` (AC3, AC4).
- `pytest …/tests/unit …/tests/meta --collect-only -q`: exit 0, 3537 collected, 0 under `tests/integration`. The `pyforge-steward-test` and `pyforge-steward-live-test` cmds are unchanged and name only `tests/unit` and `tests/meta`. Nothing in `.github/workflows/`, `scripts/` or the preflight suite reduction collects `pyforge-steward/tests` whole. `pyforge-steward-test-coverage --suites unit` behaves as it did before, because before this story there was no `tests/integration` and the driver skipped that suite (AC4).
- `grep -n 'tests/integration' docs/how-to/host-nebari.md`: exit 0. The three DW rows each gain one `note: 2026-11-01` line, and their `resolution:`/`verified:` lines are unchanged. `deferred-work-check` exits 0 (AC5).
- `nic kubeconfig --help` says the default output is stdout, so the kubeconfig gate writes no file.
- Mutation on a scratch copy (outside the worktree): with the conftest's `scrub_report` call removed, `test_a_failing_probe_s_pytest_output_never_carries_the_password` fails. The AC2 proof does fire.
- `pyforge-steward-test`: exit 1, from 1 failure, `tests/meta/test_station_tests_trigger_map.py::test_every_read_and_declared_glob_fires_its_job`. All 7 of its findings name mason (`test_mason_skills.py`, `test_persona_consults_cfe.py`) or scribe (`test_instruction_surface_parity.py`, `test_guild_env_membership.py`) test files. Other agents are editing those files in this worktree, and this story does not touch `.github/workflows/pyforge-station-tests.yml`. The suite's second segment (`test_preflight_concurrency.py`) exits 0, 33 passed. `pyforge-steward-live-test` exits 0.
- `lint-types`: exit 1. The ruff leg fails on I001 in pyforge-doctor's in-flight `tests/unit/test_sources_pages_liveness.py`. Run leg by leg, `ruff-format` exits 1 and `mypy` exits 1 (`pyforge/doctor/sources/one_chain.py:1029,1032`), both on doctor alone. `target-version-check` and `precommit-config-check` exit 0. pyforge-steward is `ok` in every leg. `ruff check` and `ruff format --check` (ruff 0.17.0, the package's own config) over `tests/integration` exit 0.
- `chain-completeness-check`, `story-status-check`, `deferred-work-check`, `spec-surface-check` and `python scripts/docs_pixi_tasks.py --check` (`-e pyforge-guild`) each exit 0. `spec-pyforge-steward`'s surface (`src/shared/packages/pyforge-steward/**`) covers the new directory once it is tracked.

Failures:

1. **AC2: the admin password reaches pytest output in URL-encoded form.** `Browser.request` keeps the urlencoded form body in its local `data`. `register()`/`redact()` only know the raw value. A failure inside `Browser.request` during the Keycloak credential POST (a connect error or a timeout, which becomes `ProbeError`) prints `data` when the operator runs the task with `-- -l`. That is the same `-l` the offline AC2 proof uses. The scrub does not catch the password when it contains a URL-reserved character. Reproduced on a scratch copy outside the worktree: with `Secret("p@ss w0rd!/Xy9")` and `submit_keycloak_login` against a closed port, `pytest -l` printed `data = b'username=admin&password=p%40ss+w0rd%21%2FXy9&credentialId='`. Without `-l` the output was clean, because the `form` funcarg is scrubbed.
   - The same class of leak: `keycloak_pkce_signin`'s `payload` local holds the token response's `refresh_token` and `id_token`, and neither is registered. They would print under `-l` if `token_claims` raised.
   - The offline proof's sentinel has no reserved characters, so it cannot see either leak.
   - Fix: also register each secret's URL-encoded forms (`quote_plus`, `quote`), or keep no encoded body in a local. Register (or drop) every token in the token response. Then extend `test_nkp_probes_offline.py` with a reserved-character password and a failure inside the credential POST under `-l`, and show that it fails without the fix.

Not counted against this story:

- AC6's two exit-0s cannot be observed in this shared worktree. The reds above all come from other stations' in-flight files. Re-run both at landing.
- AC6's scoped stamp and the co-governor reconciles are the session owner's job. The `spec-pyforge-steward` memlog reconcile is in place.
- The live attended run of the three probes (AC1 against a cluster) is still the operator's. AC1 was checked by code review and by the offline stand-ins: the PKCE flow against a fake Keycloak, the spawn and stop sequence, and both card shapes.
- One observation, not a defect of this story: on a config that declares `env:` credentials (the Hetzner reuse in 118.3), `connect()` resolves them through `deploy_nic.load_secret_env`. Its `_decrypt_age_secret` briefly writes a `.plain` file and then unlinks it. That is `deploy nic`'s existing path, and the Boundaries keep this story out of `deploy_nic.py`.

### 2026-11-01 — Second independent review, after the fix round (reviewer: independent session)

Verdict: **pass**. The status is set to `done`. The round-1 AC2 failure is fixed, and each new check fails without its fix. Every other AC holds as far as this worktree can show it.

What was checked (exit codes read from `$?`, in worktree `egm-audit-2026-11`):

- The spec's ACs and Boundaries. The diffs of `pixi.toml`, `docs/how-to/host-nebari.md`, `docs/how-to/pixi-tasks.md`, the deferred-work ledger and the `spec-pyforge-steward` memlog. All six untracked `tests/integration/` files, read in full.
  - `git diff HEAD --stat -- src/shared/packages/pyforge-steward/src/` is empty, so `deploy_nic.py` and `deploy_nic_packs.py` are untouched.
  - No probe checks the bootstrap job.
- **The round-1 failure (AC2) is fixed.**
  - I re-ran the round-1 reproduction on a scratch copy outside the worktree: `Secret("p@ss w0rd!/Xy9")` and `submit_keycloak_login` against a closed port. Under `pytest -l` and under `pytest -l -vvv`, each run exits 1 with `did not connect`.
  - Neither output carries the password raw or URL-encoded: `grep -E 'p@ss|p%40ss|w0rd|Xy9'` exits 1 on both.
  - The `form` local prints `Secret('***')`, and `Browser.request` has no `data` local.
- **Each new check fails without its fix.** I mutated scratch copies outside the worktree, one change at a time:
  - `register()` cut back to the raw value: `test_a_registered_secret_is_scrubbed_in_every_form_it_can_print_in` fails.
  - The encoded body held in a `data` local again: `test_a_credential_post_that_fails_never_prints_the_password_in_any_form[untruncated]` fails.
  - The token-response registration removed: both cases of `test_a_token_response_that_fails_its_check_never_prints_a_token` fail.
- **The hub's user model holds no token.** The data-science pack's `config/jupyterhub/00-gateway-auth.py` enables `auth_state` and stores the Keycloak tokens in it. But JupyterHub's `SelfAPIHandler`, which serves `/hub/api/user` (the only user endpoint the probes call), never fills `auth_state`. So the `user` locals of the spawn probe carry no token. Both upstream sources were read on the web: the nebari-data-science-pack repository and `jupyterhub/apihandlers/users.py`.
- AC3, AC4:
  - `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/integration -q -rs` exits 0: 27 passed, 3 skipped. Each skip names `no reachable kubeconfig: nic kubeconfig exited 1: … could not locate any control plane nodes …`.
  - `pixi run --frozen -e pyforge-steward pyforge-steward-nkp-probes` exits 0 with the same result. With `-- --nkp-config src/platform/deploy/nic/absent.yaml` it also exits 0, and the skip reads `config … does not exist`.
  - `pytest …/tests/unit …/tests/meta --collect-only -q` exits 0: 3537 collected, 0 under `tests/integration`. The `pyforge-steward-test` and `pyforge-steward-live-test` cmds are unchanged.
  - CI's steward coverage step and `pyforge-steward-coverage-gate` pass `--suites unit`. `pyforge-steward-test-coverage --suites unit` measures what it measured before this story. No workflow collects steward's `tests/integration`.
- AC5: `grep -n 'tests/integration' docs/how-to/host-nebari.md` exits 0. The three DW rows each gain one dated `note:` line, and their `resolution:`/`verified:` lines are unchanged.
- Lint: ruff 0.17.0 with the package's config, run over `tests/integration`. `ruff check` and `ruff format --check` each exit 0.
- AC6:
  - `pyforge-steward-test` exits 1: 1743 passed, 2 skipped, 1 failed. The one failure is `test_station_tests_trigger_map.py::test_every_read_and_declared_glob_fires_its_job`. All 7 of its findings name mason (`test_mason_skills.py`, `test_persona_consults_cfe.py`) or scribe (`test_instruction_surface_parity.py`, `test_guild_env_membership.py`) files, and none names a steward `tests/integration` path.
  - `lint-types` exits 1 at its ruff leg, on I001 in pyforge-doctor's in-flight `tests/unit/test_sources_pages_liveness.py`. Run alone, `ruff-format` exits 0 and `mypy` exits 0. pyforge-steward is `ok` in every leg.
- `deferred-work-check`, `chain-completeness-check`, `story-status-check`, `spec-surface-check` and `python scripts/docs_pixi_tasks.py --check` (`-e pyforge-guild`) each exit 0. These ran before this entry set the status to `done`.

Failures: none.

Not counted against this story:

- AC6's two exit-0s still cannot be observed in this shared worktree. Both reds come from other stations' in-flight files. Re-run both at landing.
- The scoped stamp, the co-governor reconciles and the ledger promotion are the session owner's job.
- The live attended run of the three probes (AC1 on a cluster) is still the operator's.

Observations (not defects, for a follow-up):

1. When the token POST fails after Keycloak has redirected back, `keycloak_pkce_signin`'s `code` and `verifier` locals print raw under `pytest -l`. I reproduced this on a scratch copy.
   - Together the two values are a single-use authorization grant. Keycloak expires it after about 60 s. It is still usable only if the token endpoint never received the code.
   - I do not count it against AC2. AC2's proof names the password, and the round-1 leaks were tokens that stay valid for a session.
   - Holding both values as `Secret`, or registering them, would close it.
2. The fix round's record says mypy over `nkp_probes.py` exits 0. With pyforge-guild's mypy 2.4.0 and the package's `[tool.mypy]` (`warn_unused_ignores = true`), `mypy tests/integration/nkp_probes.py` exits 1: `nkp_probes.py:388: error: Unused "type: ignore" comment [unused-ignore]`.
   - The `lint-types` mypy leg runs `-p pyforge.steward` (src only), so no gate sees it.
   - The fix is one line.
3. The round-1 observation on `_decrypt_age_secret`'s transient `.plain` file still stands. It belongs to `deploy nic`'s path, outside this story.

## Dev Notes

- Review follow-up 2026-11-01 (station-tests routing): steward's trigger map
  (`src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py`) went red on this story's
  directory. `nkp_probes.py` names the tracked `src/platform/deploy/nic/my-nebari-local.yaml` (`DEFAULT_CONFIG`), and
  the `nkp` fixture in `conftest.py` hands the repo root to `nkp_probes.connect`, but no module carried the live-tree
  mark. Every module in `src/shared/packages/pyforge-steward/tests/integration/` now carries
  `pytestmark = pytest.mark.live_tree`. The map's scanner reads the conftest with each module in the directory, so
  each one is a live-tree module. `ROOT_HANDOFF_INPUTS["steward_live"]` declares the conftest with
  `src/platform/deploy/nic/**`, which `steward_live_paths` already covers (`src/platform`). Neither suite half
  collects `tests/integration`, so no new test runs. `pyforge-steward-nkp-probes` exits 0 (27 passed, and 3 skipped
  with no cluster), and so does the meta-test. Surface reconcile is on the `spec-pyforge-steward` memlog.
