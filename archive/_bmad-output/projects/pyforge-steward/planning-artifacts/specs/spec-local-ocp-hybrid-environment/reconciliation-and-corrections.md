# Reconciliation & corrections — intake vs fleet vs external reality

Distilled 2026-08-22 from two research passes (fleet deep-read; external
verification). Every STRIKE is binding on the stories; citations abbreviated
to their source (fleet = repo path; ext = upstream source verified live).

## Struck from the intake, with grounds

| Intake claim | Verdict | Grounds |
|---|---|---|
| Phase 2: fresh `pixi init` + cookiecutter scaffold + new compose | **STRIKE — reuse `src/platform`** | Same lineage ("Built with Cookiecutter Django", src/platform/README.md:5); Dream constraint: divergence is debt. The compose, Containerfiles, settings, and engines all exist |
| Traefik → "ASGI Multiplexer" → three pods | **STRIKE — shipped differently** | The multiplexer IS `config/asgi.py`'s in-process dispatcher (Pattern A) behind AD-4's one front door; DB-GPT is an internal sidecar (Pattern B); no Langflow pod exists. CRC's router is HAProxy, not Traefik (ext) |
| `logspace/langflow:1.11.2` image | **STRIKE** | Dead namespace — no 1.x tags, last push 2024-04 (ext: Docker Hub). Modern: `langflowai/langflow`; platform pins ≥1.11.4 and runs Langflow in-process anyway |
| `DBGPT_DB_URL=postgresql://…dbgpt_schema` | **STRIKE — structurally impossible** | Env var has 0 code hits (ext: GitHub search); metadata store supports SQLite/MySQL/OceanBase only (ext: dbgpt_app/config.py help text; fleet: AD-6 exception, dual-verified — connector gate + MySQL-only `TEXT(length)` DDL). Sanctioned: sidecar image + SQLite PVC + singleton |
| `oc expose svc/dbgpt` (+ langflow) | **STRIKE** | AD-4/AD-7: engines never the public edge; DB-GPT internal-only via `DBGPT_SIDECAR_BASE_URL` |
| Hand `oc exec psql "CREATE SCHEMA …"` | **STRIKE** | Schemas are Django `RunSQL` migrations via the chart's migrate hook Job; `github_metrics` is dlt-managed (`dataset_name`) |
| `?options=-c search_path` for Langflow | **STRIKE — silently inert** | Langflow hard-sets `connect_args={"options": "-c timezone=utc"}`; SQLAlchemy connect_args override URL params (ext: code-verified). The platform already uses the working escape hatch `LANGFLOW_DB_DRIVER_CONNECTION_SETTINGS` (fleet: settings/base.py:361-401) |
| `oc new-app --docker-image=local-django-app` | **STRIKE — cannot work on CRC** | Cluster CRI-O can't see host podman storage (ext: crc issues #2768/#4142). Canonical: internal-registry push → ImageStream (operator-locked); `--docker-image` deprecated for `--image` |
| `bmad-marshal-detectors-init` (+ `bmad-method-install`, `bmad-module-skill-forge-install`, `bmad-loop-install`) | **STRIKE — fictional names** | No such entry points. Real: `marshal check` (registry self-registers by design), `steward provision --module` (Epic 15.3), and binaries `bmad-method`/`bmad-module-skill-forge`/`bmad-loop` |
| `dlt init github_projects postgres` + `github_projects_source` | **STRIKE — no such source** | dlt's verified `github` source covers issues/PRs/reactions/stargazers only; Projects V2 is GraphQL-only → custom source (ext: verified-sources repo; GitHub GraphQL docs) |
| `postgres:15` + separate PVC yaml + `redis-pvc` | **REPLACE** | Chart renders postgres:17 StatefulSet + volumeClaimTemplate (12.1); Redis: operator-locked emptyDir + AUTH + NetworkPolicy (no PVC) |
| `CELERY_BROKER_URL=redis://…/1` | **CORRECT** | Platform convention: broker = result backend = `REDIS_URL` (settings/base.py:302-306) |
| `cookiecutter_schema` | **CORRECT** | Django owns `public`; no such schema exists (AD-5) |
| DB host `postgres-db` in the compose excerpt | **CORRECT** | Compose service is `postgres` |

## Reuse-vs-scaffold verdict per phase

Phase 1 = genuinely new bring-up + board (bounded) + wiring via 15.3.
Phase 2 = struck (reuse platform). Phase 3 = chart-rendered + two deltas
(sidecar PVC, Redis hardening). Phase 4 = the 12.1 Tier-3 verification run.
Phase 5 = the one real scaffold (custom dlt GraphQL source), kin to the
shipped sync chain's Mode-B ingestion half. Phase 6 = chart hook Job +
invariant tests + the attended checklist.

## Absorption family (recorded this landing)

`asgi-multiplexer-monolith`, `langflow-django-plugin`, `db-gpt-django-plugin`,
`enterprise-multi-agent-orchestration` all self-closed 2026-08-14 into
`python-agent-platform` ("this dream's remaining role is the decision
trail") — pointer specs authored, dreams stamped `absorbed`. Residual
carried forward: **thread-pool sizing under load** (the asgi dream's real
untested gap) — a future platform story, noted here so it survives.

## Stale-doc corrections landing with this spec

- `docs/specs/langflow-conda-forge.md` header + CLAUDE.md row: the suite
  merged and graduated to `conda-forge/langflow-feedstock`, now v1.11.4
  (8 outputs); 1.10.1/PR-#33972 framing is historical.
- The OCP Dream's own "1.10.1 bump question" line: resolved — 1.11.4
  shipped; intake's 1.11.2 was *behind* the estate.
