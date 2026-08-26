---
title: 'Story 12.7 live-cluster verification (orbit of spec-12-1)'
type: 'verification'
created: '2026-08-25'
updated: '2026-08-25'
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
- **Attempted 2026-08-25 evening:** CRC VM **Stopped**; `oc` / `helm` not on PATH. `:17`/`:18` **not applied**. Optionals (DB-GPT sidecar image, `platform_app` DML role / 27-2, OpenFeature ×4 / cachebox / Liquibase / Django 5.2.17 feedstocks) **not started**. Re-run after `crc start` and a platform-image push that contains those changesets.

## Contingency ladder (postgres/redis)

**None used.** Official images ran under SCC-assigned UID 1000650000.

## What is claimed

- Helm release `platform` **deployed** after Liquibase + `migrate --fake`.
- `/ht/` **200** and `/api/health` **200** through the Route.
- Route admission, SCC `restricted-v2` UID 1000650000, PVC Bound, official postgres/redis.

## What is not claimed

- Real DB-GPT sidecar image in the registry (sidecar CrashLoop).
- `platform_app` DML role / 27-2 closeout.
- Full Wagtail/taggit/celery-beat DDL in Liquibase.
- Host MCP Streamable HTTP faces on the CRC image (mcp 1.x vs 2.0).
- Story 12.9 CI smoke as a substitute for this record.
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
