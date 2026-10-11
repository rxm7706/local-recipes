---
title: '19.2: One real ship records itself against a persistent store'
type: 'feature'
created: '2026-09-18'
status: 'in-review'
baseline_revision: '2a725c113f24b794fc745fc711b04f9a0a491e4f'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-19-1-the-webhook-routes-move-onto-the-station-api-seam.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-13-6-a-ship-records-itself-end-to-end.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/sync-proof-2026-09-19.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook_host.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/station_api.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/db.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/scheduler.py
  - src/shared/packages/pyforge-herald/tests/unit/test_webhook_live_smoke.py
  - src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-87-3-the-host-forwards-herald-s-webhooks-to-the-mcp-host-sidecar.md
  - src/platform/mcp_host/app.py
  - src/platform/config/asgi.py
  - src/platform/config/station_api.py
  - src/platform/tests/test_station_api_host_dispatch.py
  - docs/tutorials/local-platform-development.md
  - .github/workflows/herald-live-demo.yml
deferred:
  - 'DW-13-6-1: `steward deploy perimeter` renders only a hardcoded `myproject.asgi:application` (`steward/deploy.py:539` on 2026-10-10; the row says `:484`) with no `--asgi-application` flag. Re-scoped 2026-10-10 (operator ruling): the steward story that closes DW-13-6-1 (key: 86-1-deploy-perimeter-renders-the-asgi-application-it-is-given) adds the flag; this story stays `blocked` until that story is `done` on main, then the operator flips it `blocked -> backlog`. This story never closes on a throwaway store. Gate cleared 2026-10-10: steward 86.1 landed (PR #2056, merge `7d8ab99e88`), herald''s DW-13-6-1 row reads `resolved`, and this story moved `blocked -> backlog` under the ruling.'
  - 'DW-13-6-2: `webhook_host.py`''s timeout frees the caller, not the OS thread a hung handler holds. It becomes reachable once this story keeps a host running; it stays open here (loopback only, one local caller, a restart clears it) and the how-to names the restart as the remedy.'
  - 'AC5 operator proof (2026-10-10 dispatch): live-host-proof transcription not run in bmad-build-auto; operator must complete AC1–AC6 on the primary checkout and write `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/live-host-proof-2026-10-10.md`.'
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Epic 13 closed 6/6 `done`, but a ship has never recorded itself. The only thing in the estate that ever
started a listening process is `.github/workflows/herald-live-demo.yml`, which is `disabled_manually` (checked
2026-10-10 through the Actions API): 769 runs, the last on 2026-08-24, and the last 100 all failed. Its 524 `success`
runs are pushes whose subject matched no station, so every delivery step was skipped (two sampled, both skipped). Its
header declares it "never a persistent, publicly-reachable deployment", and each job writes a `runner.temp` database
that is discarded when the job ends. The 2026-09-09 readiness pass (batch row C11) parked the hosting half
`foundry-side`, waiting for the cutover to give Herald a perimeter.

**Approach (re-scoped 2026-10-10):** host the live backend on this machine's local stack and prove one real ship
against a store that survives a restart of the host process. The operator ruled on 2026-10-10 (chosen option,
verbatim: "go with option 1, local host"):

> "Mint a small steward fix that adds `--asgi-application` to `deploy perimeter`. Then re-scope herald 19.2 so its
> host and store are this machine's local stack: `pyforge-foundry-full-stack` with PostgreSQL 17. No public endpoint,
> nothing outside the repo. Herald Epic 19 then closes, and 49.11 flips to done."

The steward fix is its own story, minted in steward's chain: the steward story that closes DW-13-6-1
(steward Story 86.1, `86-1-deploy-perimeter-renders-the-asgi-application-it-is-given`). This story is gated on it.

**Gate cleared 2026-10-10.** Steward Story 86.1 is `done` on main, by both tests the Never list below names:
- its landing, PR #2056 (merge `7d8ab99e88`, "Merge pyforge-steward/86-1 into main"), is an ancestor of `origin/main`
  (`git merge-base --is-ancestor 7d8ab99e88 origin/main` exits 0 at `8046e1b83d`);
- steward's ledger row `86-1-deploy-perimeter-renders-the-asgi-application-it-is-given` reads `done`.

`steward deploy perimeter --asgi-application MODULE:ATTR` exists on main: the flag is registered at
`steward/cli.py:936`, and `render_daphne_unit` (`steward/deploy.py:595`) writes it into `ExecStart` (`:650`). Under
the ruling's pre-authorisation, the ledger key moved `blocked -> backlog` the same day, through a Tier-3 feed and
`sprint-ledger-sync --allow-regression` (which named that one key and no other). This spec is `ready-for-dev`.

**Re-scoped again 2026-10-10 (later): the host plus the mcp-host sidecar.** The full-stack env cannot run the host: it
lacks the host's Django packages (`import config` stops at `config/celery_app.py:4`), and steward Story 87.2, which
would have added them, is retired. The image env cannot hold herald: herald needs `mcp >=2.2.0`, and langflow-base and
lfx 1.12.x pin `mcp <2.0.0`. The operator chose, verbatim label "Via the sidecar (Recommended)":

> "Mint a steward story: mcp-host env gains pyforge-herald; the sidecar mounts herald's webhook ASGI; the host
> forwards /stations/herald/api/v1/webhooks/* to MCP_HOST_SIDECAR_BASE_URL like MCP. 19.2's proof runs host + sidecar
> locally (loopback). 87.1 stays (host never imports herald); 87.2's full-stack composition can be dropped."

So the host is the platform host from `platform-dev` (Langflow, PostgreSQL 17, no herald), and herald's webhook runs in
the mcp-host sidecar from the `mcp-host` env, both on loopback. The host forwards `/stations/herald/api/v1/webhooks/*`
to the sidecar. That forward is steward Story 87.3 (`87-3-the-host-forwards-herald-s-webhooks-to-the-mcp-host-sidecar`),
and this story waits on it: the ledger key moved `backlog -> blocked` and this spec `ready-for-dev -> blocked`. The
webhook handlers, the HMAC check and the store are unchanged, and herald's code still changes only by the local caller.

**Gate cleared 2026-10-11.** Steward Story 87.3 is `done` on main, by both tests the Never list below names:
- its landing (merge `85e70dedf5`, "Merge pyforge-steward/87-3 into main") is an ancestor of `origin/main`
  (`git merge-base --is-ancestor 85e70dedf5 origin/main` exits 0 at `378cfdf3f0`);
- steward's ledger row `87-3-the-host-forwards-herald-s-webhooks-to-the-mcp-host-sidecar` reads `done`.

The forward's review findings closed with it: Story 87.4 (dark again after a post-landing review), then Story 87.5
(the forward survives a client disconnect and proves AC 6 in any order; independent review iteration 2 passed;
landed as PR #2111), which turned `pyforge.steward.herald_webhook_sidecar` ON in dev. Under the operator's
standing pre-authorisation for this flip (flip 19.2 `blocked -> backlog` once the steward sidecar fix lands, then
dispatch 19.2, then 36.1), the one flip ran: the ledger key moved `blocked -> backlog` through a worktree-local Tier-3
feed and `sprint-ledger-sync --project herald --allow-regression`, which named that one key and no other. This spec is
`ready-for-dev`.

### What the ruling means here (decided 2026-10-10)

- **The host is the platform's one ASGI host, `config.asgi:application`** *(re-scoped 2026-10-10, later: the env is
  `platform-dev`, and herald runs in the mcp-host sidecar; see the paragraph above)*. It runs under `daphne` from
  `platform-dev` on this machine, bound to `127.0.0.1` only. Its Django database is that environment's local
  PostgreSQL 17 (`DATABASE_URL`, default `postgres:///platform`, initialised and migrated as
  `docs/tutorials/local-platform-development.md` Step 2 says). `platform-dev` carries no herald, so Story 87.1's skip
  applies there. With `MCP_HOST_SIDECAR_BASE_URL=http://127.0.0.1:8090` set and `pyforge.steward.herald_webhook_sidecar`
  ON (its `dev` default), the host forwards `/stations/herald/api/v1/webhooks/{on-ship,on-pr-close}` to the sidecar
  (steward Story 87.3).
  - **The sidecar** is the mcp-host process, started with steward's `pixi run --frozen -e mcp-host mcp-host-serve`
    (`uvicorn mcp_host.app:app` on `127.0.0.1:8090`). It serves those paths with `webhook_host`'s application, so
    `HERALD_REPO_ROOT` and the secret are the sidecar's environment, not the host's. It is the estate's existing
    Pattern B process for mcp 2.x code, owned by steward and reached only through the host, not a per-station herald
    process.
  - The daphne command is the `ExecStart` line that `steward deploy perimeter --asgi-application
    config.asgi:application` renders once the steward story lands. The rendered unit carries no working directory and
    no environment, so the how-to supplies both: the host starts from `src/platform/` under `platform-dev`, where
    `config` imports, as the tutorial runs `manage.py`, with `DATABASE_URL` and `MCP_HOST_SIDECAR_BASE_URL` set.
  - *Why not a standalone `pyforge.herald.webhook_host:application` process:* that is a per-station process. AGENTS.md
    § Policy says "No `services/` or `:800x` process tree". The spine's AD-14 as built mounts the webhook "onto the
    host ASGI … no bespoke Herald perimeter". Epic 19 says no extra port. It would also leave PostgreSQL 17 with no
    part in the ruling. *(2026-10-10, later: the sidecar is not that process. It is steward's existing mcp-host
    process, which also serves the station MCP faces; callers reach herald only through the host; its `:8090` is
    loopback here and internal-only in a cluster, so no public port is added.)*
  - The nginx edge config the perimeter also renders (`listen 443 ssl`) is **not installed**: no public endpoint.
- **Herald's record store stays SQLite, on persistent disk under this repo.** `db.py` is `sqlite3` only
  (`DEFAULT_DB_PATH = .herald/herald.db`), and the spine closed the database choice as "SQLite, not PostgreSQL"
  (§ Satellite ADs vs. the as-built live backend, AD-13/AD-17). Moving herald's records into PostgreSQL would be a new
  storage backend. Epic 19 builds no new capability, so that would enter as a dated entry on herald's Dream and a CAP,
  not here. PostgreSQL 17 is the host's database; herald's Progress/Claims/Notices live in
  `<primary checkout>/.herald/herald.db`. `HERALD_REPO_ROOT` is the primary checkout's root, `/.herald/` is
  root-anchored in `.gitignore`, and WAL needs a local disk, which the checkout is on. Never `runner.temp`, a temp
  directory, or a `.worktrees/` path, because a worktree is swept.
- **The secret stays on this machine.** `HERALD_WEBHOOK_SECRET` is generated locally into `.herald/webhook.env`
  (ignored through `/.herald/`, mode `0600`). The sidecar and the caller load it *(2026-10-10, later: was "the host";
  herald now runs in the sidecar)*. It is never committed and never a
  GitHub secret.
- **One real ship** follows Epic 13's success signal (Story 13.6: "a real merge on a station → progress and a
  success-claim draft exist with no human action"). It is one real story landing on `origin/main`: a merge whose subject
  `pyforge.core.landing_evidence` classifies under the landing grammar `Merge {slug}/{key} into main`. That landing is
  delivered as:
  - one signed `on-ship`, which creates the Progress record for the landed station;
  - one signed `on-pr-close` (`merged` and `gates_passed` true, `event_id` `rxm7706/local-recipes@<merge sha>`), which
    creates a draft success claim.

  No human authors either record: the webhook creates both from a payload the local caller derives from the commit.
  The one human act is running the caller. Unattended per-landing triggering (a CI call or a local timer) is **not**
  this story's AC. With no public endpoint, GitHub Actions cannot reach a loopback host, so FR-7.1's "CI notifies
  Herald" half stays open. The PRD's § Currency reconciliation — 2026-10-10 records that residual.
- **The local caller** is a small module in herald's package, run through one pixi task, `herald-ship-local`, in
  `[feature.pyforge-herald.tasks]`. Given a commit (default: the newest landing merge on `origin/main`), it does five
  things:
  1. derives station and story with `pyforge.core.landing_evidence`, and sends the station as its short name from
     `pyforge.core.roster.STATIONS` (`pyforge-mason` → `mason`), the name `herald progress <station>` validates;
  2. builds the two bodies from `webhook.py`'s accepted fields only;
  3. signs them the way `webhook.verify_signature` accepts (`X-Hub-Signature-256: sha256=<hmac of "<ts>.<body>">`,
     `X-Hub-Timestamp`);
  4. POSTs them to the loopback host;
  5. prints both responses as one JSON object.

  It refuses before sending anything when the commit is not a landing, when the secret is unset, or when the URL's host
  is not loopback. For `gates_passed` it uses `merged`, the same documented simplification `herald-live-demo.yml`
  made: a merge on `main` already passed its gate. It calls shipped behaviour. It is not a capability: no CAP, and no
  change to the `herald` CLI's verbs.
- **`herald-live-demo.yml`: left disabled and unchanged.** Three reasons:
  1. It can never be this story's proof. Each job writes a `runner.temp` store on a GitHub-hosted runner and needs a
     GitHub repository secret, which is the opposite of "no public endpoint, nothing outside the repo".
  2. It is governed in three places outside herald's surface, so deleting it is a cross-station change this effect
     story does not need:
     - doctor's `doctor:CAP-77` live-proof catalog: the herald *Live webhook host* row of
       `spec-pyforge-doctor/live-proof-surfaces.md`, and `_HERALD_NAMED_NON_PACKAGE_PATHS` in
       `pyforge-doctor/tests/unit/test_sources_live_proof_surfaces.py`;
     - the pixi version registry: `scripts/pixi_version_registry.py`, site "herald-live-demo.yml setup-pixi (3 jobs)",
       read by `pixi-version-check` and `bump-pixi-version`;
     - the workflow inventories: `docs/reference/github-workflows.md` and `docs/how-to/github-actions-recipe-ci.md`.
  3. While disabled it triggers nothing.

  Deleting it, and repointing doctor's catalog row at this story's how-to, is a separate cleanup the operator can
  order. This story names it and does not do it. *(2026-10-10: the operator ordered it, "Archive after 19.2". Herald
  Story 36.1, `Deps: S-19.2`, archives the file once this story lands; until then this story leaves it alone.)*
- **No flag.** This spec is pre-rule: it is listed in `docs/governance/flag-rule-baseline.json`, so `flag-gate-check
  --spec` warns `flag-pre-rule` and never refuses. None of the five `flag-exempt` values fits honestly, and the story
  ships no new runtime behaviour to flag. The webhook routes it exercises shipped unflagged in 13.4 and 19.1, and the
  caller is an operator-run tool with nothing to switch off. Herald's flag retrofit count (Story 34.4's inventory)
  still includes this spec.

## Acceptance Criteria

- **AC1 — the host is rendered, not hand-edited; the sidecar runs from steward's task.** Given the steward story
  that closes DW-13-6-1 and steward Story 87.3 are both `done` on main, When `steward deploy perimeter` runs with
  `--workers 1`, `--asgi-application config.asgi:application` and `--output-dir .herald/perimeter/`, Then:
  - the rendered daphne unit's `ExecStart` names `config.asgi:application` and `--bind 127.0.0.1`;
  - the host process is started from that line under `platform-dev`, and the proof record quotes both the rendered
    line and the running process's `ps -o args=`;
  - `pixi run --frozen -e platform-dev python -c "import pyforge.herald"` fails: the host env carries no herald;
  - the sidecar is started from the repo root with `pixi run --frozen -e mcp-host mcp-host-serve`, with
    `HERALD_REPO_ROOT` set and `.herald/webhook.env` loaded, and the proof record quotes its `ps -o args=`;
  - `ss -ltnH` shows the host's port and `8090` bound to `127.0.0.1` only;
  - no rendered nginx edge config is installed anywhere.
- **AC2 — one real ship is recorded.** Given the host and the sidecar are running with these settings:
  - the host: `DATABASE_URL` pointing at `platform-dev`'s local PostgreSQL 17, migrated;
    `MCP_HOST_SIDECAR_BASE_URL=http://127.0.0.1:8090`; `pyforge.steward.herald_webhook_sidecar` ON (`PYFORGE_ENVIRONMENT`
    unset or `dev`);
  - the sidecar: `HERALD_REPO_ROOT` set to the primary checkout root and `.herald/webhook.env` loaded;

  When `pixi run -e pyforge-herald herald-ship-local` (any env composing `[feature.pyforge-herald]`) delivers one real
  landing from `origin/main` to the **host's** loopback URL, Then:
  - `on-ship` returns `201` with the Progress record for the landed station;
  - `on-pr-close` returns `201` with a `claim_id`;
  - the response bodies name the landing's station and story;
  - the sidecar's output shows both POSTs. With no herald in the host env, the `201`s can only have come through the
    forward.
- **AC3 — the record survives a restart.** When the host and the sidecar are both stopped (processes gone, ports free)
  and started again from the same lines (the rendered `ExecStart` and `mcp-host-serve`), Then:
  - run from the primary checkout's root, `herald progress <station> --json` shows the AC2 record: its station, its
    date, and the landing subject as the unblock narrative (`herald progress` resolves its store against the working
    directory and takes no `--repo-root`);
  - `herald success --repo-root <primary checkout> get <claim_id>` shows the draft claim with the landing commit as
    evidence (`--repo-root` sits on the `success` parser, before the subcommand);
  - re-delivering the same `on-pr-close` (same `event_id`) to the restarted host returns `201` with the **same**
    `claim_id`;
  - `herald success --repo-root <primary checkout> --json list` holds exactly one claim for that event.

  That last pair proves the restarted sidecar, where herald runs, reads the persistent store, not memory.
- **AC4 — the scheduler runs against the same store (LB-3).** When `herald scheduler run --repo-root <primary
  checkout> --json` runs, Then:
  - it exits 0;
  - `records_aggregated` is at least 1;
  - `snapshot_path` lies under `<primary checkout>/.herald/`.

  The how-to gives the local crontab line for the weekly run. Installing it is the operator's choice, not an AC.
- **AC5 — a run record the estate can see.** Two copies, and neither holds the secret value:
  - **Raw logs** go under the ignored `.herald/live-host/<UTC timestamp>/`: the host's and the sidecar's output before
    and after the restart, the caller's two responses and the re-delivery's, the CLI reads, and the scheduler JSON.
  - **A tracked transcription** goes in `spec-pyforge-herald/live-host-proof-<date>.md`, following the
    `sync-proof-2026-09-19.md` precedent. It names:
    - the landing commit's sha and subject;
    - the store path;
    - the rendered `ExecStart` line;
    - the host's and the sidecar's command lines, with their pids before and after the restart;
    - every HTTP status and body;
    - the `claim_id`;
    - the CLI read output.

  This story's completion note cites that file.
- **AC6 — the store is honest.** The proof's store path:
  - resolves (`realpath`) under the primary checkout's `.herald/`, and not under `.worktrees/`, `/tmp`, `$TMPDIR` or
    any `runner.temp`;
  - is ignored: `git check-ignore -q .herald/herald.db .herald/webhook.env` exits 0;
  - has a private secret file beside it: `stat -c %a .herald/webhook.env` prints `600`;
  - leaks nothing: `git grep -F` for the secret value finds nothing.
- **AC7 — the workflow's fate is recorded and holds.** At close, both hold:
  - `gh api repos/rxm7706/local-recipes/actions/workflows/herald-live-demo.yml --jq .state` prints
    `disabled_manually`;
  - the file is unchanged by this story: `git diff origin/main...HEAD -- .github/workflows/herald-live-demo.yml` (this
    branch's own diff since its merge base) is empty. *(Amended 2026-10-10: it read `git diff <baseline> -- …`, which a
    `bump-pixi-version` run on `main` breaks without this story touching the file; see Known traps.)*

  The reason is the one recorded above.
- **AC8 — tests.**
  - **Default gate (herald, no network)**, a new `tests/unit/test_local_ship.py`:
    - derivation via `landing_evidence` from real landing subjects, one per station
      (`Merge pyforge-<station>/<key> into main`);
    - a non-landing subject refuses with nothing sent;
    - the bodies pass `webhook.handle_on_ship` and `webhook.handle_on_pr_close` (`201`) against a `tmp_path` store;
    - the signature round-trips through `webhook.verify_signature`;
    - an unset secret refuses;
    - a non-loopback URL refuses.
  - **Platform**: `src/platform/tests/test_station_api_host_dispatch.py` gains a signed `on-ship` through
    `config.asgi:application` that returns `201`, with the record in a `tmp_path` `HERALD_REPO_ROOT` store. That closes
    Story 19.1's deferred review finding, "no signed 201 through platform dispatcher". The test signs with stdlib
    `hmac`/`hashlib` and reads the record back with stdlib `sqlite3` or through the `herald` CLI. It imports no
    `pyforge.*`: `src/platform/` never does (AGENTS.md § Policy).
  - **Opt-in live** (`HERALD_LIVE_WEBHOOK=1`): `tests/unit/test_webhook_live_smoke.py` gains a restart case:
    1. a real daphne process, a signed `on-ship` and a signed `on-pr-close`;
    2. terminate it, then start it again on the same store;
    3. re-deliver: the same `claim_id`, one claim, and the Progress record still readable.
  - `pixi run --frozen -e pyforge-herald pyforge-herald-test` passes. So does
    `pixi run -e platform-ci-test pytest src/platform/tests/test_station_api_host_dispatch.py -q`.
- **AC9 — docs.** A new Diátaxis how-to, `docs/how-to/run-herald-live-backend-locally.md`, covers:
  - `platform-dev` for the host, and PostgreSQL 17 `initdb`/`pg_ctl`/`migrate` (pointing at the tutorial, not copying
    it);
  - the sidecar: steward's `mcp-host-serve` from the `mcp-host` env, `HERALD_REPO_ROOT`, `MCP_HOST_SIDECAR_BASE_URL`
    and the flag `pyforge.steward.herald_webhook_sidecar` (pointing at steward's docs, not copying them);
  - generating the secret into `.herald/webhook.env`;
  - rendering through `steward deploy perimeter` (the daphne unit only, never the edge config);
  - starting, stopping and restarting the host and the sidecar;
  - delivering a landing with `herald-ship-local`, and reading the records back;
  - the scheduler's crontab line;
  - why the store is SQLite, and why `herald-live-demo.yml` is not the proof;
  - the DW-13-6-2 symptom (repeated request timeouts) and its remedy (restart the host).

  The page is registered in `docs/map.yaml` (owner `herald`), rendered into `docs/MAP.md` with `docs-map-render`, and
  linked from `docs/how-to/README.md`. Herald's `docs/cli-runbooks.md` and `docs/automation-troubleshooting.md` point at
  it where they now describe the CI-contained demo. `docs-map-hygiene-check` and `docs-currency-check` exit 0.
- **AC10 — close.** When this story lands, its ledger key becomes `done` through the Tier-3 feed and
  `sprint-ledger-sync`, and `epic-19` follows to `done` (all four stories done). Steward's
  `49-11-index-herald-realization-gate-effect-stories` is steward's key: this story names it and never writes it. The
  operator's ruling flips it.

## Boundaries & Constraints

**Always:**
- The host is the platform's one ASGI host, bound to loopback, rendered by `steward deploy perimeter`, and started from
  the rendered line under `platform-dev`.
- Herald's webhook runs in steward's mcp-host sidecar, started with `mcp-host-serve` on `127.0.0.1:8090` and reached
  only through the host's forward.
- Herald's records are in `<primary checkout>/.herald/herald.db` and in no other store.
- HMAC verification and the handlers stay exactly Story 13.4's and 19.1's. The caller signs what `verify_signature`
  already accepts.
- Every payload is derived from a real landing commit. A hand-typed station, story or narrative is a defect.
- Reconcile every Spec `spec-surface-check` names, then stamp each one scoped (AGENTS.md pre-PR item 5). Expect
  `spec-pyforge-herald`, plus `spec-pyforge-core` for the core seam if the caller's import is judged there. Never run a
  bare `--write-baseline`.
- A `pixi.toml` change (the task) regenerates `environment.yaml` in the same PR, and `pyforge-station-tests` runs
  before the push. The PR carries the `maintenance` label.

**Never:**
- Never flip this ledger key off `blocked` before steward Story 87.3
  (`87-3-the-host-forwards-herald-s-webhooks-to-the-mcp-host-sidecar`) is `done` on main. "Done on main" means two
  things hold: its landing is an ancestor of `origin/main` (`git merge-base --is-ancestor`), and steward's ledger row
  reads `done`. Then exactly one flip runs, `blocked -> backlog`, the same one-flip rule the earlier ruling set for
  86.1 (that gate cleared on 2026-10-10). No agent flips it early, and no dispatch starts while it is `blocked`.
  *(2026-10-10, later: this replaces the 86.1 gate, which has cleared.)*
- Never open a port, the host's or the sidecar's, on anything but `127.0.0.1`, install the rendered nginx edge config, or create a tunnel, a public
  DNS name or any other route in from outside this machine.
- Never put herald's records in PostgreSQL, add a storage backend, or change `db.py`'s schema.
- Never commit, print or log the secret value, and never add it as a GitHub secret.
- Never enable, edit or delete `herald-live-demo.yml`. Never edit doctor's live-proof catalog, doctor's tests, the
  pixi version registry, or the workflow inventories.
- Never edit `steward/deploy.py`, `src/platform/mcp_host/`, `config/asgi.py`'s forward or any steward file: the
  perimeter flag is steward 86.1's, and the sidecar, the forward and its flag are steward 87.3's.
- Never edit `SPEC.md`, the PRD or the spine. Never write steward's ledger.
- Never write the secret, the store or a log under a `.worktrees/` path.

**Known traps:**
- **2026-10-10 — a pixi bump rewrites the workflow while this story is open.** `scripts/pixi_version_registry.py:82`
  registers the workflow's three `pixi-version: v…` pins (`herald-live-demo.yml:75`, `:255` and `:372`) as one
  `exact` site, so a `bump-pixi-version` run on `main` before this story closes rewrites all three. That is not this
  story's change. AC7 therefore reads "unchanged by this story" (`git diff origin/main...HEAD`), not "byte-identical to
  the baseline". Never revert or hand-edit a bumped pin to make AC7 pass. The trap ends when Story 36.1 drops the
  registry site and archives the file.
- **2026-10-10 — the earlier dispatch predates the sidecar re-scope.** `dispatch/pyforge-herald/19.2` (tip
  `2930259bf8`, unmerged) holds the caller, the tests and the how-to built for the full-stack host. Its how-to names
  `pyforge-foundry-full-stack` as the host env, and its copy of this spec reads `status: 'done'` although AC1–AC7 never
  ran. Neither is the record. Whatever of it lands must follow this re-scope: `platform-dev` for the host, the sidecar
  for herald.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| real ship | a landing merge on `origin/main`, the host up, the secret loaded | `on-ship` 201 (Progress), `on-pr-close` 201 (`claim_id`) | — |
| restart | the host stopped and started from the same rendered line | records readable; re-delivery returns the same `claim_id`; one claim | — |
| not a landing | a commit `landing_evidence` does not classify | nothing sent | caller exits non-zero, naming the subject |
| no secret | `HERALD_WEBHOOK_SECRET` unset or empty | nothing sent; the host refuses at the first webhook request (`resolve_webhook_secret`) | caller exits non-zero, naming the env var |
| wrong signature | a secret differing between caller and host | `401` from the webhook | caller exits non-zero, printing the status |
| non-loopback URL | `--url http://<lan address>:…` | nothing sent | caller refuses before connecting |
| throwaway store | `HERALD_REPO_ROOT` under `/tmp`, `.worktrees/` or `runner.temp` | not a proof | AC6 fails; the story stays open |
| steward story not landed | the perimeter has no `--asgi-application` | the story stays `blocked` | no hand-edited unit counts as AC1 |
| steward 87.3 not landed | the host does not forward herald's webhooks | the story stays `blocked` | no in-process or standalone herald host counts as the proof |
| sidecar down | `MCP_HOST_SIDECAR_BASE_URL` set, nothing on `:8090` | the host answers `502` | caller exits non-zero, printing the status |
| flag OFF or URL unset | the host does not forward | the host answers 87.1's `404` (herald not installed) | caller exits non-zero, printing the status |
| a same-day second `on-ship` | a second landing for the same station on one UTC day | replaces that day's record (`progress.upsert`, `(station, date)`) | documented in the how-to; not a defect |
| a hung handler | DW-13-6-2 | the caller's request times out (500 after 120 s) | restart the host; DW-13-6-2 stays open |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-10 (live backend, local host) entry.
- Spec: `spec-pyforge-herald` CAP-38 (← `spec-herald-moments-2-4-live-backend` LB-2, webhook endpoint) and CAP-39
  (← LB-3, cron scheduler). Epic 13's success signal (Story 13.6). Unifying-strategy batch rows C6 and C11 (the
  2026-09-09 `foundry-side` parking of C11 is superseded for this story by the 2026-10-10 ruling). No CAP is minted.
  `spec-pyforge-herald/.memlog.md` records the ruling verbatim, the decision and the re-scope.
- Architecture: AD-14 as built (the webhook mounts on the host ASGI inside Steward's trust boundary) and AD-13/AD-17
  as built (SQLite, not PostgreSQL), both unchanged. The spine's and the PRD's § Currency reconciliation — 2026-10-10
  record the re-scope.
- Epic: Epic 19 (Herald in effect). Its HARD boundaries hold: no new capability, `herald-live-demo.yml` stays disabled,
  no second console, no extra public port.
- Ledger key: `19-2-one-real-ship-records-itself-against-a-persistent-store`. Ledger status: `blocked` (unchanged by
  this re-scope); `backlog` from 2026-10-10, the one pre-authorised flip, made once steward 86.1 was `done` on main;
  `blocked` again from 2026-10-10 (later), gated on steward 87.3.
- Deps: S-19.1 (`done`).
- Cross-project gate: the steward story that closes DW-13-6-1 (`86-1-deploy-perimeter-renders-the-asgi-application-it-is-given`). Marshal's `Deps:` parser is
  station-local, so the gate is this row's ledger `blocked`, which the operator flips (AGENTS.md § Known pitfalls). The
  ruling pre-authorises the one flip named in § Boundaries. Cleared 2026-10-10 (§ Intent, *Gate cleared*).
- Cross-project gate (2026-10-10, later): steward Story 87.3 (`87-3-the-host-forwards-herald-s-webhooks-to-the-mcp-host-sidecar`),
  the host's forward to the mcp-host sidecar, from the operator's ruling "Via the sidecar (Recommended)". The gate is
  this row's ledger `blocked`, and § Boundaries names its one flip.
- Follow-on: herald Story 36.1 (`36-1-the-ci-live-demo-workflow-moves-to-the-archive-and-its-readers-follow`, Epic 36,
  `Deps: S-19.2`) archives `herald-live-demo.yml` after this story lands (operator ruling 2026-10-10, "Archive after
  19.2"). Nothing in this story waits on it.
- Dispatch note: `marshal-policy.toml` `[epic_surfaces]."19"` (added 2026-10-10 with this re-scope) admits:
  - the herald package and its tests;
  - `src/platform/tests/test_station_api_host_dispatch.py`;
  - the how-to, `docs/how-to/README.md`, `docs/map.yaml` and `docs/MAP.md`;
  - `pixi.toml`, `pixi.lock` and `environment.yaml`;
  - the spec-surface baseline and every Spec memlog.

  Nothing else is admitted. The live run is operator-side: a dispatched session builds the caller, the tests and the
  docs, and the proof (AC1–AC7) runs on this machine against the primary checkout.
- Minted 2026-09-18 from `epics.md` (CHAIN-STANDARD §5 filename). Re-scoped 2026-10-10 by the operator's ruling.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test`, expected to pass (the station's `verify_commands`),
  including `tests/unit/test_local_ship.py`.
- `pixi run -e platform-ci-test pytest src/platform/tests/test_station_api_host_dispatch.py -q`, expected to pass,
  including the signed `201` through the host.
- `pixi run --frozen -e pyforge-guild lint-types`, expected to exit 0.
- `pixi run -e pyforge-guild docs-map-hygiene-check` and `pixi run -e pyforge-guild docs-currency-check`, expected to
  exit 0.
- `pixi run -e pyforge-guild spec-surface-check`, expected to exit 0 after the memlog reconciles and the scoped stamps.

**Operator-run proof (this machine, primary checkout; not a dispatch gate):**
- `HERALD_LIVE_WEBHOOK=1 pixi run --frozen -e pyforge-herald pytest -rs src/shared/packages/pyforge-herald/tests/unit/test_webhook_live_smoke.py`,
  expected to pass with no skip, including the restart case.
- The how-to's run, end to end (AC1–AC6), host plus sidecar, transcribed into
  `spec-pyforge-herald/live-host-proof-<date>.md`.
- `gh api repos/rxm7706/local-recipes/actions/workflows/herald-live-demo.yml --jq .state`, expected to print
  `disabled_manually` (AC7).

## Spec Change Log

### 2026-10-11 — Implementer response to gap review iteration 1

Separate implementer session, on `c70384e9cc` with `origin/main` `2a725c113f` merged in (staged, not committed). The
merge conflicted only in `.claude/memory/MEMORY.md` and `spec-pyforge-core/.memlog.md`; both were resolved as a union,
main first. Each of the eleven items below is closed and verified. No AC was rewritten: the AC1, AC4 and AC6 wording
notes are recorded here instead.

1. **Live restart test.** `test_webhook_live_smoke.py` reads claims from `tmp_path / claims.DEFAULT_CLAIMS_PATH`. A new
   `_stop_daphne` terminates each process and kills it if it outlives 5 s; `_start_daphne` stops its process when the
   port never opens; and the docstring's test path now names `tests/unit/`. Verified:
   `HERALD_LIVE_WEBHOOK=1 pixi run --frozen -e pyforge-herald pytest -rs .../test_webhook_live_smoke.py` gave 3 passed,
   0 skipped, rc 0, and no daphne process was left.
2. **How-to rewritten for the sidecar topology** (`docs/how-to/run-herald-live-backend-locally.md`). It now covers:
   - the host from `platform-dev`, and the sidecar from `pixi run --frozen -e mcp-host mcp-host-serve` with
     `HERALD_REPO_ROOT` and `.herald/webhook.env` (the host takes no secret);
   - `MCP_HOST_SIDECAR_BASE_URL`, and `PYFORGE_ENVIRONMENT` unset or `dev`;
   - the negative `import pyforge.herald` check;
   - `ps -o args=` and `ss` for 8001 and 8090, before and after restarting **both** processes;
   - reads before re-delivery, then the one-claim check;
   - a troubleshooting table (401, 404, 502, 503, a refused connection, a same-day second `on-ship`), plus DW-13-6-2
     with "restart the sidecar" as its remedy;
   - the AC5 raw-log layout and transcription checklist, and the AC6 checks.

   Verified by extracting the page's 16 bash blocks and running them in order, as one script, against a scratch root.
   Four substitutions were made: `pixi run --manifest-path`, the absolute `src/platform`, `--repo-root <worktree>` for
   the caller's git, and `git -C` for `check-ignore`/`grep`. The store and the secret stayed out of the primary
   checkout and out of `.worktrees/`. The database was a throwaway PostgreSQL 17 from `platform-dev` on `127.0.0.1` with
   no Unix socket, migrated. Every step held:
   - the render exited 0;
   - `ss` showed `127.0.0.1:8001` and `127.0.0.1:8090` only, and `import pyforge.herald` failed under `platform-dev`;
   - through the host, `on-ship` answered 201 (`marshal`) and `on-pr-close` 201 with a `claim_id`, and the sidecar's
     log shows both POSTs;
   - after both processes stopped and started again, the records read back before re-delivery, the re-delivery
     returned the same `claim_id`, and the claim list held one claim;
   - the scheduler gave `records_aggregated` 1, with `snapshot_path` under `.herald/`;
   - `check-ignore` passed, `webhook.env` was mode 600, and `git grep` found no leak;
   - every process stopped.

   Each troubleshooting row was then reproduced live:
   - 401: a different secret;
   - 404 `herald is not installed on this host`: the host without `MCP_HOST_SIDECAR_BASE_URL`;
   - 502 `mcp-host sidecar unreachable`: the sidecar stopped;
   - 503 naming `HERALD_REPO_ROOT`: the sidecar started without it;
   - `"status": null` with `Connection refused`: the host stopped.
3. **The render command, and AC1's wording.** Since steward Story 84.1, `steward deploy perimeter` refuses
   `--output-dir` (rc 1) without `--trusted-address`, `--tls-cert`, `--tls-key`, `--app-db-role` and
   `--audit-retention-db-role`, because the same render writes the nginx edge config and the audit grants SQL. AC1
   names only `--workers 1`, `--asgi-application config.asgi:application` and `--output-dir .herald/perimeter/`. AC1 is
   met with those three **plus** the five, given placeholder values:
   - `--trusted-address 127.0.0.1`;
   - `--tls-cert .herald/perimeter/unused-tls.crt` and `--tls-key .herald/perimeter/unused-tls.key` (the files need not
     exist);
   - `--app-db-role platform_app` and `--audit-retention-db-role platform_audit_retention`.

   The how-to says the nginx conf is never installed and the grants SQL never applied.
4. **The host line and port.** The how-to quotes the rendered
   `ExecStart=daphne --bind 127.0.0.1 --port %i --proxy-headers config.asgi:application` with `%i` = 8001, the
   instance port the unit's own `systemctl enable` comment names. `local_ship.DEFAULT_HOST_URL` is
   `http://127.0.0.1:8001`, and `test_default_url_is_the_rendered_host_port` pins it.
5. **Platform tests isolated from `MCP_HOST_SIDECAR_BASE_URL`.** `_reset_herald_webhook_app`, which all three herald
   webhook tests call, now runs `monkeypatch.delenv("MCP_HOST_SIDECAR_BASE_URL", raising=False)`. Verified:
   `pixi run --frozen -e platform-ci-test pytest src/platform/tests/test_station_api_host_dispatch.py -q` gave 11 passed
   (rc 0) with the variable unset, and 11 passed (rc 0) with `MCP_HOST_SIDECAR_BASE_URL=http://127.0.0.1:9` exported.
6. **The false "landed" memlog line.** `git diff origin/main` showed `spec-pyforge-core/.memlog.md`'s "Story 19.2
   landed (run …a4b44f7d)" as a branch-only addition. That one line was removed by hand, and `git diff origin/main` on
   the file was empty afterwards. In its place, `memlog.py append` wrote a co-governor surface-reconcile entry for
   `local_ship.py`.
7. **Herald's docs.**
   - `cli-runbooks.md`: the intro, *The webhook endpoint*, *What is not a failure mode here* and the scheduler-trigger
     note.
   - `automation-troubleshooting.md`: the intro, a lead note on *Webhook demo job failing in CI* (it applies only if the
     workflow is re-enabled), and *Auto-extract failed*.
   - `operator-guide.md`: the architecture sentence, the CLI-surface bullet, the FAQ, and its stale "perimeter renders
     only a hardcoded placeholder" line, which steward 86.1 fixed.

   Each now says the disabled CI demo is not running, names the sidecar behind the host's forward, and points at the
   how-to (its `#troubleshooting` anchor replaces the old `#dw-13-6-2-request-timeouts`).
8. **The stale env name.** The `pixi.toml` `herald-ship-local` description and `local_ship.py`'s docstring now say
   `pixi run -e pyforge-herald herald-ship-local`, posting to the host, which forwards to the sidecar.
   `pixi project export conda-environment -e build` is byte-identical to `environment.yaml` (`cmp` rc 0), and
   `pixi.lock` is untouched.
9. **The CAP that does not exist.** `test_bridge.py` now reads "no CAP; CAP-38/CAP-39 effect". Triage item 9's own
   wording cited that number as a bare CAP id, which `detectors-ci`'s `cap-citation` reported as a new issue; it now
   names the number without the `CAP-` prefix.
10. **Caller robustness** (`local_ship.py`).
    - The JSON names `target`, and each request's `url`.
    - A transport failure is recorded per request as `"status": null` plus `error`, so the other response survives.
      This covers `URLError`, and also `OSError`/`http.client.HTTPException`: urllib wraps only connect-time errors,
      so a `TimeoutError` while waiting for the response arrives bare. The 2026-10-11 follow-up review's `[false]`
      "socket.timeout uncaught" rejection was wrong for that case.
    - The timeout is `REQUEST_TIMEOUT_SECONDS = 150.0`, above `webhook_host`'s 120 s, and a test pins the order.

    Five new tests and one extended test cover this in `test_local_ship.py`.
11. **Frontmatter and the Auto Run Result.** `baseline_revision` is now the merged `origin/main` (`2a725c113f`), and the
    Auto Run Result's status matches the frontmatter.

**Two more AC wording notes, found by running the how-to.**
- **AC4:** `herald scheduler run --repo-root <root> --json` writes its snapshot to `<root>/web/public/progress.json`
  (the `--out-dir` default), which is not under `.herald/` and is not ignored. AC4's third bullet holds only with
  `--out-dir <primary checkout>/.herald`, which the how-to passes, as does its crontab line.
- **AC6:** `git check-ignore -q .herald/herald.db .herald/webhook.env` exits 128 with
  `fatal: --quiet is only valid with a single pathname`. The how-to checks each path with its own `-q` call.

**New finding, not fixed (outside this story's surface).** Under `platform-dev`, `python manage.py migrate` (tutorial
Step 2) stops in Django's URL system check with `ModuleNotFoundError: No module named 'pyforge.herald'`. The chain runs
`config/urls.py:40` → `django_pyforge/urls.py:15` → `django_herald_portal/urls.py:3` → `views.py:10` →
`deck_viewer.py:9`, which imports `pyforge.herald.deck_twins` at module level (Story 30.2), and `platform-dev`
carries no herald. With `--skip-checks` the migration ran (rc 0), and the how-to documents that workaround. The fix
belongs in herald's `django-herald` portal, which is not on this story's surface, and it needs its own story. No
deferred-work row was written here.

**Gates** (each read from its exit code): see the Auto Run Result below.

Status: `in-progress -> in-review`. AC5's live proof stays the operator's. A fresh independent review gates the
landing.

- **2026-10-11 — unblocked.** Steward Story 87.3 is done on main (merge `85e70dedf5`, ancestor of `origin/main`; ledger `done`), and Story 87.5 closed the forward's review findings (PR #2111). One flip under the operator's pre-authorisation: ledger `blocked -> backlog`, spec `blocked -> ready-for-dev`. No AC, boundary or verification changed.
- **2026-10-10 — re-scoped to the local host (operator ruling, option 1).**
  - **Before:** "name the host used, or stay explicitly `foundry-side` and blocked on the cutover giving Herald a
    perimeter". The store was "a persistent path or a provisioned DB", and the only AC was "the progress record exists
    after the process exits … cited by evidence".
  - **After:**
    - the host is the platform's one ASGI host on `pyforge-foundry-full-stack` (PostgreSQL 17), loopback only, rendered
      by `steward deploy perimeter --asgi-application`;
    - the store is SQLite at `<primary checkout>/.herald/herald.db`: herald has no PostgreSQL backend, and the spine
      closed that choice;
    - the gate is the steward story that closes DW-13-6-1 (`86-1-deploy-perimeter-renders-the-asgi-application-it-is-given`), and the operator's flip is
      pre-authorised;
    - ACs 1–10 are machine-checkable, and the workflow is left disabled and unchanged.

  The ledger key and the heading are unchanged, and status stays `blocked`. Recorded in `spec-pyforge-herald/.memlog.md`
  and on the Dream.
- **2026-10-10 (later) — the gate cleared; AC7 reads this story's own change.**
  - **Gate:** steward 86.1 landed (PR #2056, merge `7d8ab99e88`, an ancestor of `origin/main`; steward's row reads
    `done`). The ledger key moved `blocked -> backlog` under the ruling's pre-authorisation, and this spec moved
    `blocked -> ready-for-dev`. ACs 1–6 and 8–10 are unchanged.
  - **AC7:** the second bullet read `git diff <baseline> -- .github/workflows/herald-live-demo.yml` is empty. It now reads
    `git diff origin/main...HEAD -- …` is empty: the file is unchanged *by this story*. A `bump-pixi-version` run on
    `main` rewrites the file's three registered pins and would fail the old wording with no change of this story's
    (Known traps). The first bullet (`disabled_manually`) is unchanged.
  - **Cleanup ordered:** the operator ruled "Archive after 19.2" the same day. Herald Story 36.1 archives the workflow
    after this story lands. This story's Never list still holds until it closes.

  Recorded in `spec-pyforge-herald/.memlog.md`.
- **2026-10-10 (later still) — the host plus the mcp-host sidecar (operator ruling "Via the sidecar
  (Recommended)").**
  - **The ruling, verbatim:** "Mint a steward story: mcp-host env gains pyforge-herald; the sidecar mounts herald's
    webhook ASGI; the host forwards /stations/herald/api/v1/webhooks/* to MCP_HOST_SIDECAR_BASE_URL like MCP. 19.2's
    proof runs host + sidecar locally (loopback). 87.1 stays (host never imports herald); 87.2's full-stack composition
    can be dropped."
  - **Before:** the host ran from `pyforge-foundry-full-stack`, which steward 87.2 would have given the host's
    packages.
  - **After:** the host runs from `platform-dev` (the rendered daphne unit stays AC1's host line), herald's webhook
    runs in the mcp-host sidecar (`mcp-host-serve`), and the caller posts to the host, which forwards. AC1, AC2, AC3,
    AC5 and AC9 add the sidecar. The gate is steward 87.3. ACs 4, 6, 7, 8 and 10 are unchanged.
  - **Status:** the ledger key moved `backlog -> blocked` (worktree-local Tier-3 feed and `sprint-ledger-sync
    --project herald`; no `--allow-regression` needed), and this spec `ready-for-dev -> blocked`. On main the spec
    read `ready-for-dev`; the `done` on `dispatch/pyforge-herald/19.2` is not the record (§ Known traps).
  - AD-14 as built holds: the host is still the one entry, and the sidecar is steward's process inside steward's trust
    boundary. No CAP, FR or AD moves. Recorded in `spec-pyforge-herald/.memlog.md` and on the Dream.
- **2026-10-11 — dispatch reused a pre-sidecar branch.** The 2026-10-11 dispatch (run `pyforge-herald-20261011T145445292Z-69725fea`) found `dispatch/pyforge-herald/19.2` from 2026-10-10, whose spec read `done` under the scope before the sidecar re-scope; it ran a follow-up review pass and tried to land, and the landing was refused (MRS-DISP-038, this file conflicted with main). Main's spec is the record. The branch's code and its review records are kept as the starting point; status moves to `in-progress` until an independent review judges the branch against the current ACs (the sidecar re-scope: AC1, AC2, AC3, AC5, AC9) and the gaps are closed.

## Review Triage Log

### 2026-10-11 — Independent gap review against the sidecar re-scope, iteration 1: sent back (3 high, 3 medium, 5 low)

Separate agent, on `d0192628cf` (PR #2123), judged against this spec as re-scoped (host from `platform-dev`, herald's webhook in the mcp-host sidecar, the host forwarding to `MCP_HOST_SIDECAR_BASE_URL`). The caller and the default-gate tests hold under the re-scope: live on 127.0.0.1, `herald-ship-local` derived a real landing from origin/main and sent it through the sidecar app; on-ship and on-pr-close returned 201 with a claim_id and re-delivery returned the same claim_id. `environment.yaml` matches the export; AC7 holds; nothing binds beyond 127.0.0.1; no secret committed; records stay in SQLite; `platform-dev` cannot import herald. Gates: `pyforge-herald-test` 0 (1768), `platform-ci-local -- --test` 0 (1206), `lint-types` 0, `spec-surface-check` 0, `docs-currency-check` 0, `flag-gate-check` 0; the opt-in live smoke 1; the platform host-dispatch tests 1 once `MCP_HOST_SIDECAR_BASE_URL` is exported. AC verdicts: AC4, AC6, AC7 pass; AC5 correctly operator-owned; AC1, AC2, AC3 gaps; AC8, AC9 fail.

1. `[high]` `[patch]` `src/shared/packages/pyforge-herald/tests/unit/test_webhook_live_smoke.py:241` calls `claims.list_claims(tmp_path)` on the repo root and raises `HeraldError: unable to open database file`; use `claims.list_claims(tmp_path / claims.DEFAULT_CLAIMS_PATH)`; wrap `_start_daphne` in try/finally with a kill fallback.
2. `[high]` `[patch]` `docs/how-to/run-herald-live-backend-locally.md` describes the pre-sidecar topology. Rewrite: host on `platform-dev`; sidecar `pixi run --frozen -e mcp-host mcp-host-serve` with `HERALD_REPO_ROOT` and `webhook.env` (the host needs no secret); host gets `MCP_HOST_SIDECAR_BASE_URL=http://127.0.0.1:8090` and `PYFORGE_ENVIRONMENT` unset or `dev`; restart both processes, capturing `ps -o args=` and `ss` for 8001 and 8090; the negative check that `import pyforge.herald` fails under `platform-dev`; a troubleshooting table (401, 404, 502, same-day second on-ship); DW-13-6-2's remedy is restarting the sidecar; the AC5 raw-log layout `.herald/live-host/<UTC ts>/` and transcription checklist.
3. `[high]` `[patch]` the how-to's render command exits 1: since steward 84.1 `--output-dir` also requires `--trusted-address`, `--tls-cert`, `--tls-key`, `--app-db-role`, `--audit-retention-db-role`. Use placeholders, say the nginx conf and grants SQL are never installed or applied, and record the extra flags against AC1's wording in this Spec Change Log.
4. `[medium]` `[patch]` the rendered ExecStart is `daphne --bind 127.0.0.1 --port %i --proxy-headers config.asgi:application` on instance port 8001 (`steward/deploy.py:532`); the how-to's hand-written `-p 8000` line, its `HERALD_WEBHOOK_URL` and `local_ship.py:189`'s default all say 8000. Quote the rendered line with 8001 and match the URL and default.
5. `[medium]` `[patch]` `src/platform/tests/test_station_api_host_dispatch.py:127`, `:170`, `:228` need `monkeypatch.delenv("MCP_HOST_SIDECAR_BASE_URL", raising=False)`; they return 502 whenever the AC2 environment is exported.
6. `[medium]` `[patch]` `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md:564` says "Story 19.2 landed (run ...a4b44f7d)"; it never landed. Replace that branch-only line with a co-governor surface-reconcile entry for `local_ship.py` and re-stamp `spec-pyforge-core` scoped.
7. `[low]` `[patch]` herald `cli-runbooks.md:161-167`, `:490-520` and `automation-troubleshooting.md:155-165` still describe the disabled CI demo as running; point at the how-to and name the sidecar.
8. `[low]` `[patch]` `pixi.toml:3166` (task description) and `local_ship.py:6` still say `pyforge-foundry-full-stack`; use `pixi run -e pyforge-herald herald-ship-local`.
9. `[low]` `[patch]` `test_bridge.py:386` cites a CAP number, 58, that herald's Spec does not define; this spec mints no CAP.
10. `[low]` `[patch]` `local_ship.py`: print the target URL in the JSON; record a per-request `URLError` instead of exiting (`:143-144`), so a failed on-pr-close keeps the on-ship response; raise the 120 s timeout above `webhook_host`'s own 120 s.
11. `[low]` `[patch]` Auto Run Result reads "Status: done" against frontmatter `in-progress`; `baseline_revision` is stale.

Send-back: 1-11 in one pass; AC5's live proof stays the operator's. A fresh independent review gates the landing.

### 2026-10-10 — Review pass
- verdicts: 2 findings — high 0, medium 1, low 0, false 0, maybe-false 1
- findings:
  - `[medium]` `[defer]` AC5 live-host proof file not produced in dispatch — operator run on primary checkout still required.
  - `[maybe-false]` `[reject]` environment.yaml unchanged after pixi.toml task add — export produced no diff.

### 2026-10-11 — Review pass (follow-up)
- verdicts: 24 findings — high 0, medium 0, low 0, false 12, maybe-false 2, defer 8, patch 3 (applied), reject 1
- findings:
  - `[false]` `[reject]` Story marked done while AC5 deferred — follow-up pass; AC5 remains operator-side by design (existing deferred row).
  - `[defer]` `[defer]` AC10 ledger/epic sync not in branch — harness/operator writes Tier-3 feed, not dispatch code.
  - `[patch]` `[patch]` automation-troubleshooting pointed at missing "troubleshooting section" — fixed anchor to DW-13-6-2 in how-to.
  - `[defer]` `[defer]` Live restart smoke uses webhook_host not config.asgi — AC8 explicitly places restart on opt-in webhook_host daphne.
  - `[patch]` `[patch]` Platform test lacked signed on-pr-close through config.asgi — added `test_host_dispatches_herald_webhook_signed_on_pr_close_returns_201`.
  - `[false]` `[reject]` No worktree guard on --repo-root — how-to documents primary checkout; not an AC8 requirement.
  - `[false]` `[reject]` Hardcoded _DEFAULT_REPO — matches estate landing grammar and herald-live-demo precedent.
  - `[false]` `[reject]` Baseline stamp narrative vs marshal co-governor churn — prior landing reconcile; not introduced this pass.
  - `[defer]` `[reject]` Incomplete spec-pyforge-core memlog — pre-existing; core co-governor unchanged this pass.
  - `[defer]` `[defer]` How-to example daphne line vs rendered ExecStart — operator doc polish; AC1 proof is operator-run.
  - `[false]` `[reject]` Git log line missing tab — git `%x09` format always emits tab.
  - `[false]` `[reject]` socket.timeout uncaught — urlopen wraps timeout in URLError, caught.
  - `[defer]` `[defer]` Partial delivery leaves progress without claim — exit 1 when either status != 201; acceptable.
  - `[false]` `[reject]` 201 with empty JSON body — main checks HTTP status only per AC2 status bullets.
  - `[false]` `[reject]` environment.yaml missing — task-only pixi add; export produces no diff (carried maybe-false from 2026-10-10).
  - `[defer]` `[carried]` `[defer]` AC5 operator proof — unchanged; primary checkout still required.
  - `[defer]` `[defer]` Platform CI path filter skips herald-only PRs — estate policy; herald changes touching platform tests run platform-ci.
  - `[defer]` `[defer]` Opt-in restart not in default gate — AC8 design.
  - `[patch]` `[patch]` deliver_landing URL paths not asserted — added on-ship/on-pr-close suffix checks in test_local_ship.
  - `[defer]` `[defer]` Intent alignment Reading B (full AC1–6 before done) — dispatch delivers machinery; operator proof separate.
  - `[false]` `[reject]` Blind hunter intent-alignment items duplicated above.

## Auto Run Result

Status: in-review

Summary: Gap review iteration 1's send-back (items 1-11) is closed on the branch, with `origin/main` `2a725c113f` merged
in. Story 19.2 has **not** landed. Details: the Spec Change Log entry "2026-10-11 — Implementer response to gap review
iteration 1".

Files changed (this pass):
- `src/shared/packages/pyforge-herald/tests/unit/test_webhook_live_smoke.py` — the restart test reads the claims
  store; the processes are always stopped
- `src/shared/packages/pyforge-herald/src/pyforge/herald/local_ship.py` — default URL 8001, target and URLs in the
  JSON, transport failures recorded per request, 150 s timeout, docstring
- `src/shared/packages/pyforge-herald/tests/unit/test_local_ship.py` — tests for the above
- `src/shared/packages/pyforge-herald/tests/unit/test_bridge.py` — the CAP citation
- `src/platform/tests/test_station_api_host_dispatch.py` — the herald webhook tests unset `MCP_HOST_SIDECAR_BASE_URL`
- `docs/how-to/run-herald-live-backend-locally.md` — rewritten for the host plus sidecar
- `src/shared/packages/pyforge-herald/docs/{cli-runbooks,automation-troubleshooting,operator-guide}.md` — the
  pointers, and the disabled CI demo described as disabled
- `pixi.toml` — the `herald-ship-local` description
- `spec-pyforge-core/.memlog.md` — the false "landed" line replaced by a reconcile entry

Verification (each read from its exit code):
- `pixi run --frozen -e pyforge-herald pyforge-herald-test`: rc 0 (1773 passed, 5 skipped)
- `HERALD_LIVE_WEBHOOK=1 pixi run --frozen -e pyforge-herald pytest -rs src/shared/packages/pyforge-herald/tests/unit/test_webhook_live_smoke.py`:
  rc 0 (3 passed, 0 skipped; 127.0.0.1 only; no daphne left)
- `pixi run --frozen -e platform-ci-test pytest src/platform/tests/test_station_api_host_dispatch.py -q`: rc 0 (11
  passed) with `MCP_HOST_SIDECAR_BASE_URL` unset, and rc 0 (11 passed) with it exported as `http://127.0.0.1:9`
- `pixi run --frozen -e pyforge-guild platform-ci-local -- --test`: rc 0 (ruff, format, mypy; policy 96 passed; full
  suite 1206 passed, 13 skipped)
- `pixi run --frozen -e pyforge-guild lint-types`: rc 0
- `pixi run --frozen -e pyforge-guild docs-currency-check`: rc 0 (warn-only lines name no file this story touches)
- `pixi run --frozen -e pyforge-guild docs-map-hygiene-check`: rc 0
- `pixi run --frozen -e pyforge-guild flag-gate-check`: rc 0 (0 fail)
- `pixi run --frozen -e pyforge-guild spec-surface-check`: rc 0 (no drift named, so no stamp)
- `pixi run --frozen -e pyforge-guild detectors-ci`: rc 0
- `pixi run --frozen -e pyforge-guild chain-currency-sweep-check`: rc 0 (all 8 spines current)
- `pixi run --frozen -e pyforge-guild deferred-work-check`: rc 0
- `pixi project export conda-environment -e build` against `environment.yaml`: `cmp` rc 0; `pixi.lock` untouched
- The how-to, run end to end against a scratch root and a throwaway PostgreSQL 17, everything on `127.0.0.1`: every
  step held (see the Spec Change Log)

Residual: AC5 is the operator's. AC1–AC6 run on the primary checkout per the how-to, transcribed into
`spec-pyforge-herald/live-host-proof-<date>.md`. The `platform-dev` migrate finding needs its own story.
