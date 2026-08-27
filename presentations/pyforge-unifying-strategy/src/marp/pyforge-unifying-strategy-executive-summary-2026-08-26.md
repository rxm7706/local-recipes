---
marp: true
paginate: true
size: 16:9
title: PyForge Unifying Strategy — executive summary
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:26px; }
  h1 { letter-spacing:-0.03em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.02em; color:#201e1d; }
  strong { color:#c22a10; }
  a { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#201e1d; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); color:#f3f2f2; }
  hr { border:none; border-top:3px solid #201e1d; margin:.35em 0; }
  table { font-size:.72em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
---

<!-- _class: lead -->

EXECUTIVE SUMMARY · PYFORGE UNIFYING STRATEGY · STEWARD CHAIN · EVERGREEN

# Eight stations. One canopy. One estate.

PyForge's eight capability stations each shipped as an excellent CLI — and stopped there. The Canopy (`src/platform/`) mounts them under **one chrome, one OIDC session, one command grammar, one event backbone and one query plane**, on exactly PostgreSQL + Redis + Kubernetes.

---

## The problem, and the shape of the answer

**Before:** eight terminals, eight mental models; one of eight portals mounted; one of eight service faces; zero station-to-station signals; and an app database role that could alter its own schema.

**The answer:** a hub-and-spoke **modular monolith** — one ASGI host carrying the Wagtail front door (Lane 1), eight HTMX portals under `/stations/<name>/` (Lane 2), Vizro boards with row isolation (Lane 3), eight MCP faces for agents, and the `pyforge <station> <noun> <verb>` dispatch grammar. Heavy work rides Celery. The host **never imports `pyforge.*`**; station binaries stay first-class.

**The mandate:** air-gapped and regulated — schema change auditable by **database privilege**, identity revocable at the IdP, failure contained by tested invariants.

---

## Proven live — CRC, dated

| Check | Result |
| --- | --- |
| `GET /` (Lane 1) | **200** — "published from PostgreSQL." (2026-08-26) |
| `GET /cms/` unauthenticated | **302** to the IdP — never a local login form |
| `/ht/` on the deployed chart | **200** (story 12-7, 2026-08-25) |
| `CREATE` on `public` as `platform_app` | **refused** — the app role is provably DML-only |
| Five-tier matrix (CLI·portal·service·skill·persona) | **40/40** (2026-08-26) |

Four dated days: dreamt 08-23 → grounded 08-24 (the audit found the host already built; scope rescoped to the residual) → drained 08-24/25 (Epics 18–32 + eight peer hook stories) → deployed 08-25 → closed out **and reopened** 08-26.

---

## What's next — and what it cost

- **CAP-19, the query plane** — one DuckDB HTAP engine: live read-only attach, a Kedro-written Parquet cache on a named pipeline, `vss` vectors. Five private stores rebuilt onto it; agents never touch the OLTP DSN. First slice **shipped 2026-08-26**; the Dream is **evergreen**.
- **The committed price:** six conda-forge builds — 4 OpenFeature feedstocks, a `cachebox` 5.x build, `liquibase` 5.0.4+ (JDBC vendored). The air-gap gate is a gate, not a warning.
- **Held lines:** no ninth station · no `services/` farm · no fourth backing kind · one PR-gate verdict (Warden; scanners as plugins) · no CLI absorbed.

**19** capabilities · **4** dated days · **40/40** tiers · **6** builds · **3** backing kinds · **0** re-authentications.
