---
sources:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/corridor.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/passport.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/quarantine.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/glass.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/corridor_load.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/glass_query.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/passport_mint.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/quarantine_admit.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/apps.py
  - src/shared/packages/pyforge-steward/tests/unit/test_corridor.py
  - src/shared/packages/pyforge-steward/corridor/corridor.yaml
  - src/platform/config/settings/base.py
  - src/platform/db/sqlmigrate-map.yaml
  - src/shared/packages/django-steward/src/django_steward_portal/station_apps.py
verified: 2026-11-21
---

# How to move vendor extracts through the corridor

Use steward's `load`, `passport`, `quarantine` and `glass` duties to record a vendor's extract file once, give its rows an identity, shelve the rows that have none, and see whether today's drop arrived.

## When to use this

- A vendor sent an extract file and it must be recorded exactly once.
- An inbound row has no identity yet and needs one, or needs to wait for a human.
- Standup asks whether the vendor's file arrived today.
- An extract has to leave the estate, signed.

## When to skip this

- You are reconciling a GitHub Projects item with its Jira issue. That is `steward sync`; see [How to use steward duties that need operator consent](use-steward-duties-that-need-operator-consent.md).

:::note
**Prerequisites.** These duties read and write Django models, so they need a Django project that installs the app `pyforge.steward.dashboard` and a database its migrations have been applied to. The platform host is that project: its settings install the app, and its database is where the corridor's records live. § *Give the duties a Django project* below says how to point the duties at it. Without a project every verb refuses with a message and exit `1`; it never crashes.
:::

:::caution[Important]
`load`, `passport mint` and `quarantine admit` write shared records. An agent runs only the two reads, `glass` and `quarantine shelf`. An outbound load carries data out of the estate: the operator runs it.
:::

## The terms

| Term | Meaning |
| --- | --- |
| **Waybill** | A label you supply for one drop. A load is keyed on the file's hash and its waybill. |
| **Transport** | How the file arrived. Declared in `src/shared/packages/pyforge-steward/corridor/corridor.yaml`; `app-upload` is on, `shared-folder` and `email` are off. |
| **Work Passport** | A freshly minted UUID that is a row's identity. A Jira key or GitHub item id is only a nickname on it. |
| **Quarantine shelf** | Where an inbound row without a passport waits until a human links it. |
| **Glass** | The freshness reading of the most recent inbound load. |

## Give the duties a Django project

### Against the platform's database

The platform host installs `pyforge.steward.dashboard`, declared for it by the `django-steward` portal package (`src/shared/packages/django-steward/src/django_steward_portal/station_apps.py`), so the corridor's four tables are part of the platform's database: `manage.py migrate` creates them locally, and the Liquibase changesets `pyforge-steward:1` to `:7` create them in production. Use `-e platform-dev`, which carries the steward CLI, Django and the PostgreSQL drivers.

1. Have the platform's database running and migrated, as in [Local platform development](../tutorials/local-platform-development.md) § *Step 2: Configure the Database*:

   ```bash
   cd src/platform
   pixi run -e platform-dev python manage.py migrate
   ```

2. In that shell, still in `src/platform/`, point the duties at the platform's settings. `DATABASE_URL` defaults to `postgres:///platform`; set it only when your database is elsewhere.

   ```bash
   export DJANGO_SETTINGS_MODULE=config.settings.local
   export COMPONENT_RUNTIME=local
   export PYTHONPATH=.
   ```

3. Run a read to confirm:

   ```bash
   pixi run -e platform-dev steward glass
   ```

   ```text
   standup: unborn waybill=- (no waybill has ever loaded for this direction) | shipped: unborn waybill=- (no waybill has ever loaded for this direction)
   ```

Every command in § *Steps* is then run the same way, from `src/platform/`: `pixi run -e platform-dev steward …`.

### Against a scratch SQLite file (a laptop with no platform)

Use `-e pyforge-steward`, which has Django (the `dashboard` extra) but no PostgreSQL driver, so it reaches a SQLite file only.

1. Write a settings module in a directory outside the repository, for example `~/.config/pyforge/corridor_settings.py`:

   ```python
   INSTALLED_APPS = [
       "django.contrib.contenttypes",
       "django.contrib.auth",
       "pyforge.steward.dashboard",
   ]
   DATABASES = {
       "default": {
           "ENGINE": "django.db.backends.sqlite3",
           "NAME": "/absolute/path/to/corridor.sqlite3",
       }
   }
   USE_TZ = True
   SECRET_KEY = "local-only-not-a-secret"
   ```

2. Point Django at it, from the repository root:

   ```bash
   export PYTHONPATH="$HOME/.config/pyforge"
   export DJANGO_SETTINGS_MODULE=corridor_settings
   ```

3. Create the tables, once per database:

   ```bash
   pixi run -e pyforge-steward python -m django migrate
   ```

4. Run `pixi run -e pyforge-steward pyforge steward glass` to confirm, and every command in § *Steps* the same way.

### What each missing piece looks like

| You see | What is missing |
| --- | --- |
| `Django ORM unavailable (ModuleNotFoundError: No module named 'django')` | Django. You are in `-e pyforge-guild`; use `-e platform-dev` or `-e pyforge-steward`. |
| `DJANGO_SETTINGS_MODULE is unset and django settings are not configured` | The settings variable. |
| `Django ORM unavailable (ModuleNotFoundError: No module named 'config')` | The platform's settings are on the path only from `src/platform/` with `PYTHONPATH=.`. |
| `glass failed: Model class pyforge.steward.dashboard.models.AuditEntry doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS.` | `pyforge.steward.dashboard` in your own settings module's `INSTALLED_APPS`. |
| `Django ORM unavailable (ProgrammingError: relation "pyforge_steward_dashboard_corridorload" does not exist …)` | The platform's migrations. Run `manage.py migrate`. |
| `Django ORM unavailable (OperationalError: no such table: pyforge_steward_dashboard_corridorload)` | The SQLite file's migration. |

Each exits `1`.

## Steps

### 1. Load an inbound extract

```bash
pyforge steward load inbound --file <path> --waybill <label>
```

The load is idempotent: loading the same file with the same waybill again is a no-op, not a duplicate. `--transport NAME` names a declared transport and defaults to `app-upload`; a transport whose state is off is refused. `--corridor DIR` (before `inbound`) points at another directory holding `corridor.yaml`.

### 2. Give a row an identity

```bash
pyforge steward passport mint --vendor-id <name> [--jira-key KEY] [--github-item-id ID] [--title TEXT]
```

Every call mints a new UUID. Two mints with the same vendor and the same Jira key never merge, so mint once per row.

### 3. Shelve a row that has no passport

```bash
pyforge steward quarantine admit --vendor-id <name> [--jira-key KEY] [--github-item-id ID] [--title TEXT] [--arrived-at ISO8601]
pyforge steward quarantine shelf
```

`admit` puts the row on the shelf. Inside the missing-passport window, 14 days from `--arrived-at` (default: now), it also mints a passport for the row. After the window it refuses to mint, and the row lands on the shelf with no passport.

`shelf` lists the rows nobody has linked yet; `--include-linked` adds the ones a human already linked.

### 4. Check whether today's drop arrived

```bash
pyforge steward glass
```

`glass` reads the most recent inbound load and reports it twice, as `standup` and as `shipped`. Both are the same reading. Each has one of four states:

| State | Meaning |
| --- | --- |
| `unborn` | Nothing has ever loaded. |
| `fresh` | A drop arrived today. |
| `stale` | The last drop was not today. |
| `failed` | Today's drop is an empty file. |

`glass export --format {csv,markdown}` renders the two rows as a table. It sits behind the flag `pyforge.steward.glass_export`, which is off; `--flag enable_glass_export=true` turns it on for one call.

### 5. Send an outbound extract (operator)

```bash
pyforge steward load outbound --file <path> --waybill <label> --slice <name> --signer <name>
```

Outbound is default deny. A new outbound load is refused without a named `--slice` and a recorded `--signer`, the person who authorized that slice. It uses the same declared transports as inbound; it does not push to anyone's system.

## How to tell it worked

| Exit | Meaning |
| --- | --- |
| `0` | The duty ran and reported ok. |
| `1` | The duty ran and reported not ok, including a refusal because Django is unavailable. |
| `2` | A usage error. |
| `70` | An internal error. |

Add `--json` (before the verb, as in `steward glass --json` or `steward load --json inbound …`) for machine-readable output. After a load, `glass` should read `fresh`.

## Tips

- Checked on 2026-11-21, on macOS, in `-e platform-dev` against PostgreSQL 17.11 migrated by the platform's own `manage.py migrate`: § *Against the platform's database* as written, `load inbound` and its idempotent repeat, `passport mint`, `quarantine admit` and `shelf`, `glass` reading `unborn` and then `fresh`, and the two platform refusals in the table. A real Liquibase update of the whole changelog builds the same corridor schema. The SQLite path was checked on 2026-11-18 in `-e pyforge-steward`; the package's own test, `tests/unit/test_corridor.py`, runs the writes against a migrated SQLite file. `load outbound` and `glass export` were not run for this page; they are taken from `--help` and the modules.
- Before 2026-11-18 `quarantine admit` and `quarantine shelf` refused with the `DJANGO_SETTINGS_MODULE is unset` message even when the variable was set. That is fixed (steward Story 126.3).
- The loader never parses the file's content. It records the hash, the waybill and the transport.
- Every flag is a row of the station contract, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md`.
