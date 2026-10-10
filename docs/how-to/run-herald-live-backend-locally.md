# Run Herald's live backend locally

Story 19.2. Prove one real story landing records Progress and a draft success
claim in a **persistent** SQLite store at `<primary checkout>/.herald/herald.db`,
with the platform's one ASGI host on loopback only. This replaces the
CI-contained `.github/workflows/herald-live-demo.yml` demo as the estate's
proof path once you complete the operator run transcribed in
`_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/live-host-proof-<date>.md`.

## Prerequisites

- The **primary checkout** of this repo (not a `.worktrees/` path). Herald
  resolves `HERALD_REPO_ROOT` to that root; WAL needs a stable disk.
- `pixi run -e pyforge-foundry-full-stack` — PostgreSQL 17, Redis, and the
  platform stack per [local platform development](../tutorials/local-platform-development.md).
- Follow that tutorial's **Step 2** for `initdb`, `pg_ctl`, `DATABASE_URL`, and
  `migrate` under `src/platform/`. Do not duplicate those steps here.

## Secret and env file

From the primary checkout:

```bash
install -d -m 700 .herald
umask 077
python - <<'PY'
import secrets
from pathlib import Path
path = Path(".herald/webhook.env")
path.write_text(f"HERALD_WEBHOOK_SECRET={secrets.token_hex(32)}\n")
print(f"wrote {path} (mode 600)")
PY
chmod 600 .herald/webhook.env
```

Never commit `.herald/webhook.env`. Load it when starting the host and when
running the caller:

```bash
set -a && source .herald/webhook.env && set +a
export HERALD_REPO_ROOT="$PWD"
```

PostgreSQL holds Django's platform database only. Herald Progress, Claims, and
Notices stay in SQLite (`db.py` is sqlite3-only; the spine closed that choice).

## Render the daphne unit (do not install nginx)

From the repo root:

```bash
pixi run -e pyforge-steward pyforge steward deploy perimeter \
  --workers 1 \
  --asgi-application config.asgi:application \
  --output-dir .herald/perimeter/
```

Use the rendered daphne unit's `ExecStart` line only. Do **not** install the
rendered nginx edge config (no public endpoint).

## Start, stop, and restart the host

From `src/platform/` with the env above and `DATABASE_URL` set:

```bash
cd src/platform
# Example — quote the exact ExecStart from .herald/perimeter/ after render:
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

Confirm loopback bind:

```bash
ss -ltnH | grep 127.0.0.1
```

Stop with `SIGTERM` to the daphne pid. To prove persistence (Story 19.2 AC3),
stop until the port is free, then start again from the **same** rendered line.

## Deliver one real landing

With the host up and `.herald/webhook.env` loaded:

```bash
cd /path/to/primary/checkout
set -a && source .herald/webhook.env && set +a
export HERALD_WEBHOOK_URL=http://127.0.0.1:8000
pixi run -e pyforge-foundry-full-stack herald-ship-local
```

Optional: pass a merge commit sha instead of defaulting to the newest landing
on `origin/main`.

Read records back:

```bash
pixi run -e pyforge-herald herald progress <station> --json
pixi run -e pyforge-herald herald success --repo-root "$PWD" get <claim_id>
```

## Scheduler (LB-3)

```bash
pixi run -e pyforge-herald herald scheduler run --repo-root "$PWD" --json
```

Weekly operator crontab (optional — installing it is your choice):

```cron
0 3 * * 1 cd /path/to/primary/checkout && pixi run -e pyforge-herald herald scheduler run --repo-root /path/to/primary/checkout --json >> .herald/scheduler.log 2>&1
```

## Why not `herald-live-demo.yml`?

That workflow stays **disabled** and uses a throwaway `runner.temp` database on
GitHub-hosted runners. It cannot prove persistence on your checkout and needs a
GitHub secret. Story 19.2's proof is this local loopback host plus
`herald-ship-local`. Story 36.1 archives the workflow after 19.2 lands.

## DW-13-6-2 (request timeouts)

If signed POSTs hang until timeout (~120s), the host's handler thread may be
stuck (documented in Story 13.6). **Remedy:** stop and restart daphne from the
same rendered `ExecStart` line; the SQLite store under `.herald/` survives.
