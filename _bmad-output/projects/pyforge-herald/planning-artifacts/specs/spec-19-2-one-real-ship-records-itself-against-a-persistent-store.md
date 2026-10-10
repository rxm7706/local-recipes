---
title: '19.2: One real ship records itself against a persistent store'
type: 'feature'
created: '2026-09-18'
status: 'done'
baseline_revision: '647abbc9b21d09c54e75cc59f1e93c1ea4331f4b'
review_loop_iteration: 0
followup_review_recommended: true
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

### What the ruling means here (decided 2026-10-10)

- **The host is the platform's one ASGI host, `config.asgi:application`.** It runs under `daphne` from
  `pyforge-foundry-full-stack` on this machine, bound to `127.0.0.1` only. Its Django database is that environment's
  local PostgreSQL 17 (`DATABASE_URL`, default `postgres:///platform`, initialised and migrated as
  `docs/tutorials/local-platform-development.md` Step 2 says). Herald's routes reach the webhook through Story 19.1's
  station API seam (`/stations/herald/api/v1/webhooks/{on-ship,on-pr-close}` →
  `pyforge.herald.station_api.attach_webhook_asgi` → `webhook_host.build_application`). The daphne command is the
  `ExecStart` line that `steward deploy perimeter --asgi-application config.asgi:application` renders once the steward
  story lands. The rendered unit carries no working directory and no environment, so the how-to supplies both: the
  host starts from `src/platform/`, where `config` imports, as the tutorial runs `manage.py`, with the env file below
  loaded.
  - *Why not a standalone `pyforge.herald.webhook_host:application` process:* that is a per-station process. AGENTS.md
    § Policy says "No `services/` or `:800x` process tree". The spine's AD-14 as built mounts the webhook "onto the
    host ASGI … no bespoke Herald perimeter". Epic 19 says no extra port. It would also leave PostgreSQL 17 with no
    part in the ruling.
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
  (ignored through `/.herald/`, mode `0600`). The host and the caller load it. It is never committed and never a
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

- **AC1 — the host is rendered, not hand-edited.** Given the steward story that closes DW-13-6-1 is `done` on main,
  When `steward deploy perimeter` runs with `--workers 1`, `--asgi-application config.asgi:application` and
  `--output-dir .herald/perimeter/`, Then:
  - the rendered daphne unit's `ExecStart` names `config.asgi:application` and `--bind 127.0.0.1`;
  - the host process is started from that line, and the proof record quotes both the rendered line and the running
    process's `ps -o args=`;
  - `ss -ltnH` shows the host's port bound to `127.0.0.1` only;
  - no rendered nginx edge config is installed anywhere.
- **AC2 — one real ship is recorded.** Given the host is running with these settings:
  - `DATABASE_URL` pointing at the full-stack env's local PostgreSQL 17, migrated;
  - `HERALD_REPO_ROOT` set to the primary checkout root;
  - `.herald/webhook.env` loaded;

  When `pixi run -e pyforge-foundry-full-stack herald-ship-local` delivers one real landing from `origin/main`,
  Then:
  - `on-ship` returns `201` with the Progress record for the landed station;
  - `on-pr-close` returns `201` with a `claim_id`;
  - the response bodies name the landing's station and story.
- **AC3 — the record survives a restart of the host.** When the host process is stopped (process gone, port free) and
  started again from the same rendered line, Then:
  - run from the primary checkout's root, `herald progress <station> --json` shows the AC2 record: its station, its
    date, and the landing subject as the unblock narrative (`herald progress` resolves its store against the working
    directory and takes no `--repo-root`);
  - `herald success --repo-root <primary checkout> get <claim_id>` shows the draft claim with the landing commit as
    evidence (`--repo-root` sits on the `success` parser, before the subcommand);
  - re-delivering the same `on-pr-close` (same `event_id`) to the restarted host returns `201` with the **same**
    `claim_id`;
  - `herald success --repo-root <primary checkout> --json list` holds exactly one claim for that event.

  That last pair proves the restarted host reads the persistent store, not memory.
- **AC4 — the scheduler runs against the same store (LB-3).** When `herald scheduler run --repo-root <primary
  checkout> --json` runs, Then:
  - it exits 0;
  - `records_aggregated` is at least 1;
  - `snapshot_path` lies under `<primary checkout>/.herald/`.

  The how-to gives the local crontab line for the weekly run. Installing it is the operator's choice, not an AC.
- **AC5 — a run record the estate can see.** Two copies, and neither holds the secret value:
  - **Raw logs** go under the ignored `.herald/live-host/<UTC timestamp>/`: the host's output before and after the
    restart, the caller's two responses and the re-delivery's, the CLI reads, and the scheduler JSON.
  - **A tracked transcription** goes in `spec-pyforge-herald/live-host-proof-<date>.md`, following the
    `sync-proof-2026-09-19.md` precedent. It names:
    - the landing commit's sha and subject;
    - the store path;
    - the rendered `ExecStart` line;
    - the host command line, with its pids before and after the restart;
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
  - the full-stack env, and PostgreSQL 17 `initdb`/`pg_ctl`/`migrate` (pointing at the tutorial, not copying it);
  - generating the secret into `.herald/webhook.env`;
  - rendering through `steward deploy perimeter` (the daphne unit only, never the edge config);
  - starting, stopping and restarting the host;
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
  the rendered line.
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
- Never flip this ledger key off `blocked` before the steward story that closes DW-13-6-1 (`86-1-deploy-perimeter-renders-the-asgi-application-it-is-given`) is
  `done` on main. The operator's 2026-10-10 ruling pre-authorises exactly one flip: "flip 19.2 blocked -> backlog when
  the steward story that closes DW-13-6-1 is done on main". "Done on main" means two things hold: its landing is an
  ancestor of `origin/main` (`git merge-base --is-ancestor`), and steward's ledger row reads `done`. No other flip is
  authorised, and no agent flips it early.
- Never open a port on anything but `127.0.0.1`, install the rendered nginx edge config, or create a tunnel, a public
  DNS name or any other route in from outside this machine.
- Never put herald's records in PostgreSQL, add a storage backend, or change `db.py`'s schema.
- Never commit, print or log the secret value, and never add it as a GitHub secret.
- Never enable, edit or delete `herald-live-demo.yml`. Never edit doctor's live-proof catalog, doctor's tests, the
  pixi version registry, or the workflow inventories.
- Never edit `steward/deploy.py` or any steward file: the flag is the steward story's.
- Never edit `SPEC.md`, the PRD or the spine. Never write steward's ledger.
- Never write the secret, the store or a log under a `.worktrees/` path.

**Known traps:**
- **2026-10-10 — a pixi bump rewrites the workflow while this story is open.** `scripts/pixi_version_registry.py:82`
  registers the workflow's three `pixi-version: v…` pins (`herald-live-demo.yml:75`, `:255` and `:372`) as one
  `exact` site, so a `bump-pixi-version` run on `main` before this story closes rewrites all three. That is not this
  story's change. AC7 therefore reads "unchanged by this story" (`git diff origin/main...HEAD`), not "byte-identical to
  the baseline". Never revert or hand-edit a bumped pin to make AC7 pass. The trap ends when Story 36.1 drops the
  registry site and archives the file.

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
  this re-scope); `backlog` from 2026-10-10, the one pre-authorised flip, made once steward 86.1 was `done` on main.
- Deps: S-19.1 (`done`).
- Cross-project gate: the steward story that closes DW-13-6-1 (`86-1-deploy-perimeter-renders-the-asgi-application-it-is-given`). Marshal's `Deps:` parser is
  station-local, so the gate is this row's ledger `blocked`, which the operator flips (AGENTS.md § Known pitfalls). The
  ruling pre-authorises the one flip named in § Boundaries. Cleared 2026-10-10 (§ Intent, *Gate cleared*).
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
- The how-to's run, end to end (AC1–AC6), transcribed into `spec-pyforge-herald/live-host-proof-<date>.md`.
- `gh api repos/rxm7706/local-recipes/actions/workflows/herald-live-demo.yml --jq .state`, expected to print
  `disabled_manually` (AC7).

## Spec Change Log

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

## Review Triage Log

### 2026-10-10 — Review pass
- verdicts: 2 findings — high 0, medium 1, low 0, false 0, maybe-false 1
- findings:
  - `[medium]` `[defer]` AC5 live-host proof file not produced in dispatch — operator run on primary checkout still required.
  - `[maybe-false]` `[reject]` environment.yaml unchanged after pixi.toml task add — export produced no diff.

## Auto Run Result

Status: done

Summary: Implemented `pyforge.herald.local_ship`, `herald-ship-local` pixi task, unit/platform/live-smoke tests, Diátaxis how-to, and doc cross-links for Story 19.2. Spec-surface reconciled on `spec-pyforge-herald`, `spec-pyforge-doctor`, and `spec-pyforge-unifying-strategy` memlogs (no `--write-baseline` in this session).

Verification:
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — pass
- `pixi run -e platform-ci-test pytest src/platform/tests/test_station_api_host_dispatch.py -q` — pass
- `pixi run -e pyforge-guild lint-types` — pass
- `pixi run -e pyforge-guild docs-map-hygiene-check` / `docs-currency-check` — pass
- `python scripts/spec_surface_reconcile.py` — pass after memlog entries

Follow-up review recommended: true — AC5 operator proof on primary checkout before ledger/epic close.

Residual risks: Operator must complete AC1–AC6 and add `live-host-proof-<date>.md` before treating Epic 19 as fully closed.
