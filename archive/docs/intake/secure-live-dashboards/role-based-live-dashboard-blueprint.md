# Role-Based Live Dashboard Architecture — system blueprint (intake, v1.0)

> **Intake material.** Externally authored, captured verbatim in substance on 2026-08-09.
> Source for `docs/dreams/secure-live-dashboards.md`. Recorded as given — the reconciliations,
> tensions and open decisions are flagged inline but **not resolved here**; that is the Spec
> and architecture phase's job.
>
> Framing note: the blueprint is written as a single application. The Dream scopes it as a
> **reusable pattern** other dashboards adopt, with `pyforge-atlas`'s existing Vizro board as
> first adopter. Where the blueprint says "the app", read "an adopting dashboard".

---

## 1. System integration & data refresh

**API & token management.** Interface with a protected corporate API/MCP server requiring
OAuth *and* bearer tokens. Token lifecycles are managed **server-side**: track expiry and
renew proactively before a mid-session call fails. Secrets and tokens never reach the
front-end bundle.

**Refresh across three vectors:**
1. automated background polling on a strict 15-minute cycle
2. immediate manual execution from a UI "Refresh" control
3. immediate execution on browser reload (F5)

**Server-side caching.** `Flask-Caching`, dataframe results held for at most 15 minutes
(`timeout=900`). Concurrent users must read the **shared** cache rather than each triggering a
duplicate upstream request.

## 2. Row-level security & multi-user isolation

**Identity from the proxy.** User identity and group membership come from HTTP headers set by
a corporate reverse proxy. Header names are environment-configurable via `ROLE_HEADER` and
`USER_ID_HEADER`.

**Two-step filtering pipeline — the load-bearing rule:**
1. **Global cache layer** holds the entire master dataset.
2. **Per-request slicing** filters in memory *after* it leaves the cache.
   A role-filtered dataset is **never written back** to the shared cache.

**Interface isolation.**
- *Chart level*: rows filtered on an access column (e.g. `allowed_roles`) before render.
- *Page level*: the navigation tree is **constructed conditionally**. Without an Admin role,
  admin pages are omitted from the sidebar and absent from the DOM — not merely hidden.

## 3. Auditing & webhook alerting

**Multi-environment engine.** SQLite (`dashboard_local_testing.db`) in development,
PostgreSQL in production, selected by a single `POSTGRES_URL` via SQLAlchemy.

**Audit table `dashboard_audit_trail`** — exact columns: `id`, `timestamp`, `username`,
`role`, `action_description`, `row_count`. Every data transaction, visual load, navigation and
filter event is logged.

**SecOps webhooks** (`TRIGGER_SECURITY_ALERTS=TRUE`). If an unauthorized role bypasses the UI
and calls a restricted download endpoint directly: intercept, log critical, and dispatch a
structured JSON payload to `SECURITY_WEBHOOK_URL` (SIEM / Slack / Teams).

## 4. Secure export & search

- **Role-gated export.** CSV download for authorized roles; the control is *stripped* for
  Viewers, and back-end validation drops unauthorized manual requests. The absent button is
  never the control.
- **Symmetric encryption.** `cryptography.fernet`; when `ENCRYPT_EXPORT_FILE=TRUE`, deliver a
  `.csv.enc` binary requiring `ENCRYPTION_KEY`.
- **Search.** Admin view: a live `dash_table.DataTable` of the audit trail with column-level
  native filtering, refreshed by short polling. Dashboard view: a global text box slicing
  chart metrics via pandas matching **without breaking role-level limits**.

## 5. Production infrastructure

- **WSGI.** Never the built-in server. A `wsgi.py` exposing the app to **Gunicorn**,
  `--workers 4 --worker-class gthread`.
- **Four-service Compose stack** on a private bridge: `vizro_app`, `postgres_db` (volume-backed),
  `redis_cache` (shared cache state across workers), `db_backup` (optional cron sidecar,
  `BACKUP_CRON_SCHEDULE`).
- **Nginx edge.** Front-facing gateway supporting hot reload, with env-driven
  `MAX_FILE_SIZE_LIMIT`, subnet whitelist/blacklist (`PROXY_WHITELIST_SUBNET`,
  `PROXY_DEFAULT_POLICY`), and SSL termination (`ENABLE_SSL=TRUE`, TLS 1.2/1.3).

## 6. Theme & security CI

- **Corporate palette** registered as a Plotly template: `#0F172A` slate-dark ground,
  `#3B82F6` accent, `#10B981` success; applied uniformly to charts, fonts, gridlines, hovers.
- **Security test suite** (`pytest` + mocks) that mocks request headers to impersonate
  different accounts and asserts data boundaries hold, rows do not leak, and tabs are hidden.
- **CI**: `.github/workflows/security-validation.yml` and `.gitlab-ci.yml`, running on every
  push / MR against an in-memory SQL session (`sqlite:///:memory:`) *before* a merge is allowed.

---

## Reference component map (as given)

```text
/
├── .github/workflows/security-validation.yml
├── nginx_config/{certs/,nginx_gateway.conf.template}
├── backops/database_snapshots/
├── app.py                     # dashboard logic & RLS gates
├── wsgi.py                    # Gunicorn entrypoint
├── test_security_gates.py     # security verification
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env
```

## Configuration schema (as given)

```ini
# CORE INFRASTRUCTURE
DB_NAME=compliance_db
DB_USER=corporate_secops
DB_PASSWORD=<long random>
BACKUP_CRON_SCHEDULE=0 1 * * *

# NETWORK & FIREWALL
SERVER_DOMAIN_NAME=dashboard.internal.company.com
ENABLE_SSL=TRUE
MAX_FILE_SIZE_LIMIT=250M
PROXY_WHITELIST_SUBNET_A=10.0.0.0/16
PROXY_WHITELIST_SUBNET_B=192.168.1.0/24
PROXY_BLACKLIST_SUBNET_A=10.200.5.0/24
PROXY_DEFAULT_POLICY=deny all;

# INBOUND PROXY HEADERS
ROLE_HEADER=X-Forwarded-Roles
USER_ID_HEADER=X-Forwarded-User

# CRYPTOGRAPHY & COMPLIANCE
ENCRYPT_EXPORT_FILE=TRUE
ENCRYPTION_KEY=<fernet key>

# SECOPS WEBHOOKS
TRIGGER_SECURITY_ALERTS=TRUE
SECURITY_WEBHOOK_URL=https://hooks.internal.company.com/alerts/secops
```

> **Recorded, not endorsed:** the source sample embeds a literal `ENCRYPTION_KEY` and a
> `DEFAULT_KEY` fallback constant in `app.py`. Both are secrets-in-source and are
> **incompatible with this estate**: `scripts/container-gates`' `secrets-scan` already exists
> to refuse exactly this, and Steward's `keys` surface is the sanctioned source. Captured so
> the sample is not silently copied.

## Key implementation shapes (as given)

The RLS core, reduced to its contract:

```python
def get_user_context():
    # falls back to ("local-dev", "Viewer") outside a request context
    return request.headers.get(USER_HEADER_NAME), request.headers.get(ROLE_HEADER_NAME)

@shared_cache.memoize(timeout=900)
def fetch_master_dataset(): ...          # the WHOLE dataset, shared

def get_filtered_dashboard_data(search_term=None):
    master_df = fetch_master_dataset()   # from shared cache
    user_id, user_role = get_user_context()
    # per-request slice — never written back to the cache
    ...
    save_audit_to_sql(user_id, user_role, f"Queried Dashboard Scope ...", len(df))
    return df
```

Navigation is built per-caller, so an unauthorized page never enters the DOM:

```python
pages = [vm.Page(title="Corporate Insights Portal", components=base_components)]
if user_role == "Admin":
    pages.append(vm.Page(title="Compliance Audit Node", components=[...]))
```

## Verification criteria (definition of done, as given)

1. **Zero exposure** — a `Viewer` browser state returns zero Admin/Manager rows.
2. **Perimeter hardening** — a direct POST to the download channel by an unauthorized entity
   dispatches a payload to `SECURITY_WEBHOOK_URL`.
3. **Audit completeness** — `dashboard_audit_trail` gains a permanent row, with explicit row
   metrics, for every query or export.

---

## Tensions and gaps recorded for the Spec phase

These are **not** resolved here.

- **Proxy headers are trusted implicitly.** Anything able to reach the app directly can forge
  `X-Forwarded-Roles`. The blueprint configures the header *names* but never defends the
  trust boundary. Needs either a defence or an explicitly recorded assumption.
- **The sample test suite does not prove what it claims.** `test_admin_sidebar_visibility`
  mocks a *Viewer* and asserts one page — it never exercises the Admin path, so it would pass
  against an implementation that always returns one page. It is a vacuity risk of the exact
  kind this estate's testing convention rejects.
- **`FileSystemCache` in the sample contradicts the Compose stack**, which provisions Redis
  precisely so workers share cache state. With Gunicorn `--workers 4` and a filesystem cache,
  the shared-cache guarantee does not hold.
- **Secrets appear in source** (see note above).
- **No retention or access policy for the audit trail**, which accumulates per-user activity
  and is therefore both a compliance asset and a privacy liability.
- **Search runs after role filtering in the sample**, which is correct — but nothing *enforces*
  that order, and reversing it would leak.
