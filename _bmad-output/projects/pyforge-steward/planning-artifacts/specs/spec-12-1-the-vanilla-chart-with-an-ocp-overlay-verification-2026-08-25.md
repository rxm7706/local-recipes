---
title: 'Story 12.7 live-cluster verification (orbit of spec-12-1)'
type: 'verification'
created: '2026-08-25'
updated: '2026-08-26'
status: 'done'
cluster: 'CRC 2.63.0 / OpenShift 4.22.7 (apps-crc.testing)'
---

# Story 12.7 — attended CRC verification, 2026-08-25

Host: Ubuntu 24.04 (CRC-unsupported; operator proceeded). After `crc stop` + `crc config set disk-size 80` + `crc start -p ~/.config/openshift/pull-secret.json`, VM disk is **~30 / 85 GiB**. Image path: overlay-commit of `localhost/platform:local` (full `podman build` of `src/platform/Containerfile` hit conda **503**) → push to **CRC internal registry only** (`default-route-openshift-image-registry.apps-crc.testing/platform/platform:local`). No public registry push.

Helm: core release `platform` **`deployed`** (2026-08-25 13:40 CDT). Overlay `platform-ocp` **`deployed`**. Jobs: `platform-liquibase` **Complete**, `platform-migrate` **Complete**. Web **Ready**. Sidecar **CrashLoopBackOff** (host ImageStream stand-in, not Story 10.5).

## Proofs (Given helm install of core + overlay)

| Item | Result | Evidence |
|------|--------|----------|
| **Route admission** | **PASS** | `route/platform-ocp` admitted `True`. Host `platform.apps-crc.testing`, `spec.to.name=platform`. |
| **SCC enforcement** | **PASS** | Annotation `openshift.io/scc=restricted-v2` on web `platform-7694dbcbb5-vfwpl`. Web spec: `runAsNonRoot=true`, **no** `runAsUser`. `oc exec` web: `uid=1000650000 gid=0`. |
| **PVC binding** | **PASS (with finding)** | Claims **Bound** (`data-platform-postgres-0`, `platform-media` RWX, `platform-dbgpt-sqlite`). StorageClass `crc-csi-hostpath-provisioner`. |
| **Official postgres/redis under SCC UID** | **PASS — no fallback** | Images `postgres:17` and `redis:7`. Overlay nulled `runAsUser`/`fsGroup`; SCC assigned **1000650000**. Postgres and redis-broker `id`: `uid=1000650000 gid=0`. |
| **Fresh-install migration window** | **PASS — window closed** | Liquibase `update` succeeded (15 recorded changesets including `:15` contrib auth/contenttypes and `:16` wagtailcore 0001 squashed). `migrate --fake` Job **Complete**. Overlay curl `https://platform.apps-crc.testing/ht/` → **200**. `/api/health` → **200**. |

## Findings (not silent notes)

1. **CRC hostpath PVCs ignore Helm `size`.** `--set postgres.persistence.size=1Gi` (and 1Gi / 512Mi for media/sidecar) still Bound at **79Gi** each.
2. **Empty `sidecar.image.registry` resolves to Docker Hub.** This run pointed sidecar at the **host** ImageStream so CRI-O stayed in-cluster; that pod is **not** the Story 10.5 DB-GPT image and remains CrashLoopBackOff. Helm `--wait` would still fail on that replica; this install omitted `--wait` so hooks could complete.
3. **Liquibase requires schema `liquibase` up front.** `ensure_liquibase_schema()` in `db/liquibase_update.py` (`CREATE SCHEMA IF NOT EXISTS liquibase`) is now in the image.
4. **Liquibase changeset 6 needs Django `auth_group`.** Changeset **`:15`** (`python-agent-platform-15-django-contrib-auth-contenttypes.sql`) lands contenttypes/auth/sessions SQL before users.
5. **Liquibase changeset 8 needs `wagtailcore_page`.** Changeset **`:16`** is **only** `sqlmigrate wagtailcore.0001_squashed` (not the full Wagtail history — isolated later `sqlmigrate` emitted unsafe `ALTER COLUMN` type changes). Remaining Wagtail/taggit/celery-beat tables are **not** in Liquibase; `migrate --fake` records Django history only.
6. **Worker crash (image layout).** `_repo_root()` in `runtime_catalog.py` walks for `pixi.toml` / `docs/dreams` / `manage.py`+`platformapp` so `/app` does not `IndexError`.
7. **Web boot vs `mcp.server.mcpserver`.** python-agent-platform conda ships mcp 1.x (Langflow). Host MCP faces need mcp 2.0. `django_pyforge.mcp_http` now skips `ImportError` on station/flags MCP factories so gunicorn still boots. Station MCP on CRC is degraded until the pip-layer fold (`NEXT-AFTER-12-7.md`).
8. **`migrate --fake` post_migrate vs missing celery-beat tables.** `seed_detector_schedule()` now returns on `ProgrammingError` so the hook Job can Complete.
9. **`DATABASE_URL` used the migration role `platform`**, not `platform_app`. Changeset `:2` is preconditioned on `pg_roles.platform_app` and was skipped (`CONTINUE`). `platform_app` was not created (`create_app_role.sql` is operator SQL — 27-2). **12.7 is not 27-2 closeout.**
10. **Stale hook Jobs / Terminating PVCs.** A leftover `platform-liquibase` Job can block `before-hook-creation`. CRC media PVC stayed `Terminating` until the worker pod was force-deleted.
11. **Image pip layer vs conda overlap.** `mcp` / `sse-starlette` / `python-multipart` dropped from `[feature.platform-image-pip]`. Follow-up remains Dream → spec (`NEXT-AFTER-12-7.md`).

## Addendum — 2026-08-25 (do not rewrite the proof table above)

The CRC proofs in the table stand. Findings **5, 7, 8, 11** are dated as of that Helm run.

- **Finding 5 / 8 (celery-beat / satellite DDL).** Changelog **`:17`** (`django_celery_beat`) and **`:18`** (admin/taggit/Wagtail satellite 0001 + allauth account/socialaccount) are in `db.changelog-master.yaml`. Isolated `mfa` sqlmigrate still fails; later Wagtailcore after 0001 stays `migrate --fake` (unsafe ALTERs, same as `:16`). Apply `:17`/`:18` on the next Liquibase upgrade — not a 12-7 re-prove. `seed_detector_schedule()` still swallows `ProgrammingError` for DBs that have not applied `:17`.
- **Finding 7 / 11 (pip layer vs conda `mcp`).** Follow-up is `spec-platform-image-one-pixi-env`: extras on `[feature.python-agent-platform]` conda deps; Containerfile has no `pip install --no-deps`; `[feature.platform-image-pip]` retired. `mcp-types` / `httpx2` were not folded (mcp 2.0 still a later story).
- **Image proof (2026-08-25, not CRC).** `podman build -f src/platform/Containerfile -t localhost/platform:one-pixi-env .` → `localhost/platform:one-pixi-env` id `8cbee8e8f879`. Runtime `python -c` imports `django_structlog` and `rjsmin`. Do not treat this as a 12-7 Route/SCC re-prove.
- **Next cluster upgrade (Liquibase only).** Apply changelog `:17` and `:18` on the next `liquibase update` / Helm hook. Not a 12-7 re-prove. Isolated `mfa` sqlmigrate and later Wagtailcore remain fake.
- **Attempted 2026-08-25 evening:** CRC VM **Stopped**; `oc` / `helm` not on PATH. `:17`/`:18` **not applied** then.
- **Applied 2026-08-26 (Liquibase only; not a 12-7 re-prove).** CRC VM Running / OpenShift Running (v4.22.7). Running image still predates `:17`/`:18` files, so host `pixi run -e python-agent-platform python db/liquibase_update.py` against `oc port-forward svc/platform-postgres 15432:5432` (URL rewritten to `127.0.0.1:15432`; secret never printed). Changesets **`:17`** and **`:18`** `EXECUTED`. `:2` still skipped (`platform_app` missing — finding 9). `manage.py migrate --fake --noinput` via `/app/.pixi/envs/python-agent-platform/bin/python` on `deploy/platform` web: **No migrations to apply** (Django history already recorded; tables now exist). Not claimed: Route/SCC re-prove, Helm hook rebuild, 27-2, real DB-GPT sidecar.
- **Follow-through 2026-08-26 (still not a 12-7 re-prove).** `account.W001` fixed (`ACCOUNT_LOGIN_METHODS={"email"}`, `ACCOUNT_SIGNUP_FIELDS=["email*"]`; registration still off). `front_door` 0002 `captured_at` default aligned with the model (no `:19`). Operator created `platform_app`, grants including `ON ALL TABLES` in `public`/`langflow_schema`/`dbgpt_schema` (`oc exec -i` required), Liquibase **`:2` EXECUTED**, `DATABASE_URL` rotated; web `/api/health` **200** as `platform_app`; `CREATE` on `public` refused. Overlay-commit of `localhost/platform:one-pixi-env` (`8cbee8e8f879`) + those two files → ImageStream `platform/platform:crc-20260826`; in-pod `manage.py check` reported no issues.
- **Sidecar + Libro leftover 2026-08-26 (still not a 12-7 re-prove).** Finding 2's CrashLoop was the **host ImageStream stand-in**. Real Story 10.5 image `localhost/platform-dbgpt-sidecar:crc-20260826` was built after `.dockerignore` gained `.worktrees/` and `output/` (a prior `COPY . /app` hung and filled the disk). Pushed to the CRC ImageStream; `deploy/platform-dbgpt` **1/1 Ready**. Libro is **off**: no conda-forge/PyPI pin; `NOTE_BOOK_ENABLE=false` in the Containerfile (`ENV`), Helm, and compose so `dbgpt_serve.libro` does not `Popen(["libro"])`. Rebuild `localhost/platform-dbgpt-sidecar:crc-20260826b` (`b365be2c53df`) bakes that ENV (the `crc-20260826` tag predates the line; live pod had `oc set env` until this rebuild). Logs have no `start libro exception！`. Placeholder LLM / `No healthy urls` can still appear — config, not CrashLoop. `lane1-serves-dw-h3` stays **no**. Code for this leftover merged as [#856](https://github.com/rxm7706/local-recipes/pull/856).
- **Wagtail `site_name` leftover 2026-08-26 (still not a 12-7 re-prove).** Finding 5 left `wagtailcore_site` at 0001-squashed (no `site_name`). Changelog **`:19`** (`python-agent-platform-19-wagtail-7-4-catchup.sql`) adds the Wagtail 7.4 columns/tables (additive; no `ALTER TYPE`) and seeds locale `en` + Root collection. Applied on CRC via host `liquibase update` against port-forward. In-pod `Site.objects` / `Locale` / `Collection` succeed. Isolated later `mfa` sqlmigrate stays fake.
- **Lane 1 published `/` 2026-08-26 (CAP-2 closeout; still not a 12-7 re-prove).** Default Site hostname `platform.apps-crc.testing` port 443 + published `HomePage` slug `home`. `GET https://platform.apps-crc.testing/` **200** (`PyForge Lane 1 — published from PostgreSQL.`). Unauthenticated `GET /cms/` **302** to `/accounts/oidc/oidc/login/?next=/cms/`. `/ht/` still **200**. Repo seed: `seed_lane1_homepage` on `front_door` `post_migrate`. See `sprint-change-proposal-2026-08-26-canopy-closeout.md`.

## Contingency ladder (postgres/redis)

**None used.** Official images ran under SCC-assigned UID 1000650000.

## What is claimed

- Helm release `platform` **deployed** after Liquibase + `migrate --fake`.
- `/ht/` **200** and `/api/health` **200** through the Route.
- Route admission, SCC `restricted-v2` UID 1000650000, PVC Bound, official postgres/redis.

## What is not claimed

- Real DB-GPT sidecar on the **12.7 Helm install** (that pod was CrashLoop on a host ImageStream stand-in). CRC 2026-08-26 leftover **did** push Story 10.5 `platform-dbgpt-sidecar` (`crc-20260826`, then `crc-20260826b` with baked `NOTE_BOOK_ENABLE=false`) and the sidecar is Ready — not a 12-7 re-prove.
- `platform_app` DML role on a *fresh* cluster (CRC 2026-08-26 did create the role, apply `:2`, and rotate `DATABASE_URL`; not a 12-7 re-prove).
- Full Wagtail history after `wagtailcore` 0001, or isolated `mfa` sqlmigrate (those stay `migrate --fake`). `:17`/`:18` **are** in Liquibase and were applied 2026-08-26.
- Host MCP Streamable HTTP faces **on the 12.7 image** (mcp 1.x vs 2.0). Sidecar host slice 1 shipped later (`spec-mcp-era-isolation`); not this record.
- Story 12.9 CI smoke as a substitute for this record (honesty gap until Actions minutes).
- Public registry push.

## Commands used (no secrets)

```text
crc config set disk-size 80 && crc stop && crc start -p ~/.config/openshift/pull-secret.json
podman commit <overlay> localhost/platform:local
podman push default-route-openshift-image-registry.apps-crc.testing/platform/platform:local --tls-verify=false
helm install platform … -f overlays/ocp/core-overrides.yaml --set-file flags.tree=src/platform/config/flags.json --timeout 15m
# overlay already: helm install platform-ocp overlays/ocp/chart --set route.host=platform.apps-crc.testing --set route.service.name=platform
oc get route platform-ocp -o jsonpath='{.status.ingress[0].conditions}'
oc exec platform-postgres-0 -- id
curl -sk -o /dev/null -w '%{http_code}' https://platform.apps-crc.testing/ht/
```
