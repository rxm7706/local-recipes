# Run Herald's live backend locally

Story 19.2. This page shows how to record one real story landing as a Progress record and a draft
success claim, in a SQLite store that survives a restart: `<primary checkout>/.herald/herald.db`.
Everything binds `127.0.0.1` only. There is no public endpoint.

Two processes run, and the caller only ever talks to the first:

| Process | Env | Listens on | Role |
|---|---|---|---|
| The platform host, `config.asgi:application` under `daphne` | `platform-dev` (carries no herald) | `127.0.0.1:8001` | Forwards `/stations/herald/api/v1/webhooks/{on-ship,on-pr-close}` to the sidecar (steward Story 87.3) |
| The mcp-host sidecar, `mcp-host-serve` | `mcp-host` (carries `pyforge-herald`) | `127.0.0.1:8090` | Runs herald's webhook (`webhook_host`): HMAC check, handlers, the SQLite store |

`herald-ship-local` derives one landing from `origin/main`, signs both webhook bodies and POSTs
them to the host. The host has no herald, so a `201` can only have come through the forward. The
forward, its flag and the sidecar are steward's: see
[platform deployment architecture](../explanation/platform-deployment-architecture.md), the
*mcp-host sidecar (Story 87.3)* bullet.

Run every command from the root of the **primary checkout**, never from a `.worktrees/` path: a
worktree is swept, and the store, the secret and the logs must outlive it.

## Before you start

- The envs are installed: `platform-dev`, `mcp-host`, `pyforge-herald` and `pyforge-steward`.
- Ports 8001 and 8090 are free: `ss -ltnH '( sport = :8001 or sport = :8090 )'` prints nothing.
- `platform-dev`'s PostgreSQL 17 is running and the platform database is migrated. Follow
  [local platform development](../tutorials/local-platform-development.md), Step 2 (`initdb`,
  `pg_ctl start`, `DATABASE_URL`, `manage.py migrate`). PostgreSQL holds the host's Django
  database only; herald's records stay in SQLite.
- `git fetch origin`, so the newest landing on `origin/main` is the one you deliver.

## 1. Generate the webhook secret

Once per checkout. Only the sidecar and the caller load it; the host needs no secret.

```bash
install -d -m 700 .herald
( umask 077 && pixi run --frozen -e pyforge-herald python -c \
    "import secrets; print('HERALD_WEBHOOK_SECRET=' + secrets.token_hex(32))" > .herald/webhook.env )
stat -c %a .herald/webhook.env                                    # 600
git check-ignore -q .herald/herald.db && git check-ignore -q .herald/webhook.env && echo ignored
```

Never print, commit or log the value, and never add it as a GitHub secret. `/.herald/` is ignored
from the repository root.

## 2. Render the host's daphne unit

```bash
pixi run --frozen -e pyforge-steward steward deploy perimeter \
  --workers 1 \
  --asgi-application config.asgi:application \
  --trusted-address 127.0.0.1 \
  --tls-cert .herald/perimeter/unused-tls.crt \
  --tls-key .herald/perimeter/unused-tls.key \
  --app-db-role platform_app \
  --audit-retention-db-role platform_audit_retention \
  --output-dir .herald/perimeter/
```

The last five flags are required whenever `--output-dir` is given (steward Story 84.1), because the
same render also writes the nginx edge config and the audit-table grants SQL. Their values are
placeholders: the TLS files need not exist, and the roles are never created. The render writes
three files:

- `pyforge-steward-dashboard@.service`: the daphne unit. Use its `ExecStart` line only.
- `pyforge-steward-dashboard.nginx.conf`: the edge config (`listen 443 ssl`). **Never install it.**
- `pyforge-steward-dashboard-audit-grants.sql`: **never apply it.**

Read the host line from the unit:

```bash
grep '^ExecStart=' '.herald/perimeter/pyforge-steward-dashboard@.service'
# ExecStart=daphne --bind 127.0.0.1 --port %i --proxy-headers config.asgi:application
grep 'systemctl enable' '.herald/perimeter/pyforge-steward-dashboard@.service'
#   systemctl enable --now pyforge-steward-dashboard@8001.service
```

The unit is a template whose instance name is its port, so `%i` is `8001`, and the host line is
`daphne --bind 127.0.0.1 --port 8001 --proxy-headers config.asgi:application`. Do not
`systemctl enable` the unit: step 3 starts daphne from that line by hand. The unit carries no
working directory and no environment, so step 3 supplies both.

## 3. Start the sidecar and the host

Make a raw-log directory for this run:

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
LOG=".herald/live-host/$TS"
install -d -m 700 "$LOG"
```

Start the sidecar with the secret and `HERALD_REPO_ROOT` (an absolute path; the task runs from
`src/platform/`):

```bash
( set -a && . .herald/webhook.env && set +a \
  && HERALD_REPO_ROOT="$PWD" exec pixi run --frozen -e mcp-host mcp-host-serve ) \
  > "$LOG/sidecar-1.log" 2>&1 &
```

Start the host from `src/platform/`, where `config` imports, with the rendered line:

```bash
( cd src/platform && unset PYFORGE_ENVIRONMENT \
  && DATABASE_URL="${DATABASE_URL:-postgres:///platform}" \
     MCP_HOST_SIDECAR_BASE_URL=http://127.0.0.1:8090 \
     exec pixi run --frozen -e platform-dev \
       daphne --bind 127.0.0.1 --port 8001 --proxy-headers config.asgi:application ) \
  > "$LOG/host-1.log" 2>&1 &
```

- `DATABASE_URL` is the tutorial's (default `postgres:///platform`).
- `MCP_HOST_SIDECAR_BASE_URL` turns the forward on.
- `PYFORGE_ENVIRONMENT` must be unset or `dev`. The flag `pyforge.steward.herald_webhook_sidecar` is
  ON only in `dev` (`src/platform/config/flag-overlays.json`), and with it OFF the host does not
  forward.

The host takes about 20 seconds to import. Wait for both ports, then record what runs:

```bash
for i in $(seq 120); do
  [ "$(ss -ltnH '( sport = :8001 or sport = :8090 )' | wc -l)" -eq 2 ] && break; sleep 1
done
listener_pid() { ss -ltnpH "sport = :$1" | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1; }
HOST_PID=$(listener_pid 8001); SIDECAR_PID=$(listener_pid 8090)
ps -o pid=,args= -p "$HOST_PID" -p "$SIDECAR_PID" | tee "$LOG/ps-1.txt"
ss -ltnH '( sport = :8001 or sport = :8090 )' | tee "$LOG/ss-1.txt"   # 127.0.0.1 only, both ports
pixi run --frozen -e platform-dev python -c "import pyforge.herald"   # must fail: ModuleNotFoundError
```

The host's log carries two expected warnings when herald is absent: steward Story 87.1's
station-API skip (`config.optional_components`) and herald Story 37.1's portal skip
(`django_herald_portal.herald_guard`), each `herald is not installed on this host` once per
process. With the forward on, herald's two webhook paths never reach the station-API skip.

## 4. Deliver one real landing

```bash
( set -a && . .herald/webhook.env && set +a \
  && exec pixi run --frozen -e pyforge-herald herald-ship-local ) > "$LOG/ship.json"
```

- The default commit is the newest `Merge pyforge-<station>/<key> into main` on `origin/main`;
  pass a merge sha as the first argument to choose another. A commit that is not a landing refuses
  before anything is sent.
- The default target is `http://127.0.0.1:8001`. `HERALD_WEBHOOK_URL` or `--url` overrides it, and
  a non-loopback URL refuses.
- `ship.json` names the target, the landing (sha, subject, station, story) and, for `on_ship` and
  `on_pr_close`, the URL, the HTTP status and the body. The task exits 0 only when both are `201`.
  A request that never got an answer shows `"status": null` with the error, and the other
  response is kept.

Check that both POSTs went through the sidecar, and read the records back:

```bash
grep webhooks "$LOG/sidecar-1.log"          # on-ship and on-pr-close, both 201 Created
read -r SHA CLAIM_ID STATION < <(pixi run --frozen -e pyforge-herald python -c \
  "import json, sys; d = json.load(open(sys.argv[1])); print(d['landing']['sha'], d['on_pr_close']['body']['claim_id'], d['landing']['station'])" \
  "$LOG/ship.json")
pixi run --frozen -e pyforge-herald herald progress "$STATION" --json | tee "$LOG/progress-1.json"
pixi run --frozen -e pyforge-herald herald success --repo-root "$PWD" get "$CLAIM_ID" | tee "$LOG/claim-1.txt"
```

`herald progress` resolves its store against the working directory and takes no `--repo-root`;
`herald success` takes `--repo-root` before its subcommand.

## 5. Stop both, start both again, re-deliver

Stop both processes and wait until both ports are free:

```bash
kill "$HOST_PID" "$SIDECAR_PID"
while ps -p "$HOST_PID" -p "$SIDECAR_PID" > /dev/null; do sleep 1; done   # both processes gone
ss -ltnH '( sport = :8001 or sport = :8090 )'                              # prints nothing: both ports free
```

Start them again from the same two lines, wait for both ports, and record the new pids:

```bash
( set -a && . .herald/webhook.env && set +a \
  && HERALD_REPO_ROOT="$PWD" exec pixi run --frozen -e mcp-host mcp-host-serve ) \
  > "$LOG/sidecar-2.log" 2>&1 &
( cd src/platform && unset PYFORGE_ENVIRONMENT \
  && DATABASE_URL="${DATABASE_URL:-postgres:///platform}" \
     MCP_HOST_SIDECAR_BASE_URL=http://127.0.0.1:8090 \
     exec pixi run --frozen -e platform-dev \
       daphne --bind 127.0.0.1 --port 8001 --proxy-headers config.asgi:application ) \
  > "$LOG/host-2.log" 2>&1 &
for i in $(seq 120); do
  [ "$(ss -ltnH '( sport = :8001 or sport = :8090 )' | wc -l)" -eq 2 ] && break; sleep 1
done
HOST_PID=$(listener_pid 8001); SIDECAR_PID=$(listener_pid 8090)
ps -o pid=,args= -p "$HOST_PID" -p "$SIDECAR_PID" | tee "$LOG/ps-2.txt"
ss -ltnH '( sport = :8001 or sport = :8090 )' | tee "$LOG/ss-2.txt"
```

Read the records before re-delivering anything. This shows the restarted sidecar reads the store
on disk:

```bash
pixi run --frozen -e pyforge-herald herald progress "$STATION" --json | tee "$LOG/progress-2.json"
pixi run --frozen -e pyforge-herald herald success --repo-root "$PWD" get "$CLAIM_ID" | tee "$LOG/claim-2.txt"
```

Re-deliver the same landing. `on-pr-close` returns `201` with the **same** `claim_id`, and the store
still holds exactly one claim for that event:

```bash
( set -a && . .herald/webhook.env && set +a \
  && exec pixi run --frozen -e pyforge-herald herald-ship-local "$SHA" ) > "$LOG/redeliver.json"
pixi run --frozen -e pyforge-herald herald success --repo-root "$PWD" --json list > "$LOG/claims-2.json"
grep -c "$SHA" "$LOG/claims-2.json"         # 1
```

The re-delivery also re-sends `on-ship`, which replaces that station's record for the same UTC
day (see Troubleshooting).

## 6. Run the scheduler (LB-3)

```bash
pixi run --frozen -e pyforge-herald herald scheduler run \
  --repo-root "$PWD" --out-dir "$PWD/.herald" --json | tee "$LOG/scheduler.json"
```

Pass `--out-dir`. Its default, `<repo-root>/web/public`, is not ignored and not under `.herald/`.
The JSON shows `records_aggregated` and a `snapshot_path` of `.herald/progress.json`.

A weekly run is a local crontab line. Installing it is your choice:

```cron
0 3 * * 1 cd /path/to/primary/checkout && pixi run --frozen -e pyforge-herald herald scheduler run --repo-root /path/to/primary/checkout --out-dir /path/to/primary/checkout/.herald --json >> .herald/scheduler.log 2>&1
```

## 7. Stop for good

```bash
kill "$HOST_PID" "$SIDECAR_PID"
while ps -p "$HOST_PID" -p "$SIDECAR_PID" > /dev/null; do sleep 1; done
```

Stop PostgreSQL as the tutorial says, if you want. The store, the secret and the logs stay under
`.herald/`.

## Check the store

```bash
realpath .herald/herald.db                  # under this checkout's .herald/, never .worktrees/, /tmp or $TMPDIR
git check-ignore -q .herald/herald.db && git check-ignore -q .herald/webhook.env && echo ignored
stat -c %a .herald/webhook.env              # 600
git grep -qF -f <(sed -n 's/^HERALD_WEBHOOK_SECRET=//p' .herald/webhook.env) && echo LEAK || echo "no leak"
```

`git check-ignore -q` takes one path at a time; given two, it stops with `fatal: --quiet is only
valid with a single pathname`. The last line passes the secret to `git grep` through a pipe, never
on the command line.

## Record the run

The raw logs are already under the ignored `.herald/live-host/<UTC timestamp>/`:

| File | What it holds |
|---|---|
| `host-1.log`, `sidecar-1.log` | The first start, including both forwarded POSTs |
| `ps-1.txt`, `ss-1.txt` | Both command lines with their pids, and both ports on `127.0.0.1` |
| `ship.json` | The caller's two responses |
| `progress-1.json`, `claim-1.txt` | The CLI reads after delivery |
| `host-2.log`, `sidecar-2.log`, `ps-2.txt`, `ss-2.txt` | The same after the restart |
| `progress-2.json`, `claim-2.txt` | The CLI reads after the restart, before re-delivery |
| `redeliver.json`, `claims-2.json` | The re-delivery's responses and the one-claim list |
| `scheduler.json` | The scheduler's JSON |

Transcribe it into
`_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/live-host-proof-<date>.md`,
following `sync-proof-2026-09-19.md` in the same folder. Name:

- the landing commit's sha and subject;
- the store path (`realpath .herald/herald.db`);
- the rendered `ExecStart` line;
- the host's and the sidecar's command lines, with their pids before and after the restart;
- every HTTP status and body, from `ship.json` and `redeliver.json`;
- the `claim_id`;
- the CLI read output and the scheduler JSON;
- the results of *Check the store*.

Never copy the secret value into it.

## Troubleshooting

The caller prints the status and body for each request and exits non-zero unless both are `201`.

| What you see | Cause | Fix |
|---|---|---|
| `401` `invalid or missing HMAC signature` | The caller and the sidecar loaded different secrets. | Load the same `.herald/webhook.env` for both. Restart the sidecar after you regenerate it. |
| `404` `herald is not installed on this host: …` | The forward is off: the host started without `MCP_HOST_SIDECAR_BASE_URL`, or with `PYFORGE_ENVIRONMENT` set to `staging` or `production`, where the flag is OFF. The request reached the host's own herald-absent answer (steward Story 87.1). | Restart the host as step 3 shows. |
| `502` `mcp-host sidecar unreachable` | Nothing listens on `127.0.0.1:8090`. | Start the sidecar. |
| `503` naming `HERALD_REPO_ROOT` or `HERALD_WEBHOOK_SECRET` | The sidecar started without `HERALD_REPO_ROOT` or without the env file. | Restart the sidecar as step 3 shows. |
| `"status": null` with `Connection refused` | Nothing listens at the target URL. | Start the host, or fix `HERALD_WEBHOOK_URL`. |
| A second `on-ship` on the same UTC day replaces the first | `progress.upsert` keys on `(station, date)`. | Expected; not a defect. |

### DW-13-6-2: requests time out

Symptom: repeated request timeouts. Signed POSTs hang for about 120 seconds and then answer `500`.
Herald's `webhook_host` gives each request a 120-second timeout; the timeout frees the caller, not
the worker thread a hung handler holds, and that thread lives in the **sidecar**. The caller waits
150 seconds, so the `500` reaches it.

Remedy: restart the sidecar (step 5's stop, then step 3's sidecar command). The store under
`.herald/` survives. DW-13-6-2 stays open in herald's deferred-work ledger.

## Why the store is SQLite

Herald's `db.py` is `sqlite3` only, and herald's architecture closed the choice as "SQLite, not
PostgreSQL" (AD-13/AD-17). PostgreSQL 17 is the host's Django database. A herald PostgreSQL backend
would be a new capability, which Epic 19 does not build. WAL needs a local disk, which the primary
checkout is on.

## Why the retired CI live-demo workflow is not the proof

Story 13.6's CI-contained demo lived at
`archive/.github/workflows/herald-live-demo.yml` after Story 36.1 archived it. When it still ran
from `.github/workflows/`, each job wrote a throwaway `runner.temp` database on a GitHub-hosted
runner and needed a GitHub repository secret, so it could never show a record surviving a restart
on this machine. This how-to and `herald-ship-local` are the estate's live proof instead.
