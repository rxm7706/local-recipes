# MyBMAD Dashboard (conda package)

This package builds the upstream **MyBMAD Dashboard** web app (the `web/`
directory of [bmad-method-ui](https://github.com/bmad-code-org/bmad-method-ui))
into a Next.js standalone server bundle and ships a `mybmad` launcher that runs
it with a self-managed local PostgreSQL database.

A source patch adds runtime **`MYBMAD_LOCALE`** (default `en`). Postgres
lifecycle, secret generation, and migrations live in this wrapper.

## Quick start

```bash
mybmad up              # start Postgres + apply migrations + run the web server
```

Then open <http://localhost:3002>, register an account, and (in another shell):

```bash
mybmad promote-admin --email you@example.com   # grant admin role
mybmad stop                                    # stop the local database
```

## Commands

| Command | What it does |
|---|---|
| `mybmad up` | Provision/start the local Postgres cluster, generate secrets on first run, apply migrations, then run the web server (foreground). Stops Postgres on exit. |
| `mybmad stop` | Stop the launcher-managed Postgres cluster. |
| `mybmad migrate` | Apply pending database migrations and exit. |
| `mybmad promote-admin --email <e>` | Set a registered user's role to `admin`. |
| `mybmad info` | Print resolved paths, data dir, ports, and env. |

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `MYBMAD_HOME` | `~/.local/share/mybmad` (XDG) | Data dir: Postgres cluster, logs, secrets. |
| `MYBMAD_PORT` | `3002` | Web server port. |
| `MYBMAD_HOSTNAME` | `127.0.0.1` | Bind address. Use the matching URL in the browser (`http://127.0.0.1:3002` or `http://localhost:3002`); both origins are trusted. |
| `MYBMAD_DB_PORT` | `54329` | Local Postgres port. |
| `MYBMAD_ENABLE_LOCAL_FS` | `true` | Allow importing BMAD projects from local folders. |
| `MYBMAD_ALLOW_REGISTRATION` | `true` | Allow self-registration (turn off after creating your account). |
| `MYBMAD_LOCALE` | `en` | UI language. `en` or `fr` (`en-US` / `fr-FR` normalize to the language tag). |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | unset | Optional GitHub OAuth login. |
| `GITHUB_PAT` | unset | Optional GitHub token to raise API rate limits. |

Secrets (`BETTER_AUTH_SECRET`, `REVALIDATE_SECRET`) are generated once and
persisted in `$MYBMAD_HOME/config.json`.
