---
title: "Currency review — architecture spine"
chain: pyforge-unifying-strategy
artifact: architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
created: "2026-08-24"
reviewer: currency-check (web + repo + trusted research)
verdict: PASS-WITH-FLAGS
---

# Currency review — Architecture Spine

**Spine:** `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md`

**Trusted (not re-litigated unless contradicted):**

- `research/technical-pyforge-unifying-strategy-research-2026-08-24.md`
- `research/technical-pyforge-unifying-strategy-mcp-runtime-2026-08-24.md`
- `research/technical-pyforge-unifying-strategy-dependency-currency-2026-08-24.md`
- `specs/spec-pyforge-unifying-strategy/stack.md`

**Method:** every named technology and version in the spine’s ADOPTED ADs, Stack table, and Structural Seed was checked against (a) those four documents, (b) this repo (`pixi.toml`, `src/platform/deploy/charts/platform/values.yaml`, `compose.yml`, `migrate-job.yaml`), and (c) public sources on 2026-08-24 for the five packages called out in the brief plus other live-version claims.

**Verdict: PASS-WITH-FLAGS.** Named versions that the spine commits still exist, still fit Django 5.2 / Python 3.12 / conda-forge (or are explicitly gated as absent), and match the trusted research. Nothing in the Stack table is a training-data phantom. Flags are: one Lane-2 technology with no version and no research citation (HTMX), one companion that still contradicts later research (`stack.md` Django CVE “not audited”), and two “easy to grab the wrong package” traps that do not invalidate the ADs.

---

## Named-version matrix (Stack table)

| Spine pin | Exists? | Current public / repo | Fits this estate? | Evidence |
|---|---|---|---|---|
| Python `3.12.*` | yes | parent host invariant; pixi platform env | yes | inherited AD-8; not re-opened |
| Django `>=5.2.15,<6` (recommend `>=5.2.17,<6`) | yes | upstream **5.2.17** (2026-08-04 security); conda-forge **5.2.15** only | yes, with known SBOM gap | [Django 5.2.17 notes](https://docs.djangoproject.com/en/5.2/releases/5.2.17/); [security weblog](https://www.djangoproject.com/weblog/2026/aug/04/security-releases/); currency research Part A; `pixi.toml` lines 177 / 450 / 1643 |
| Wagtail **7.4.3** | yes | PyPI + GitHub tag **7.4.3** (2026-08-20); pixi `>=7.4.3,<8.0` | yes — Django `>=5.2`, Python 3.12 | [PyPI](https://pypi.org/project/wagtail/7.4.3/); [tag](https://github.com/wagtail/wagtail/releases/tag/v7.4.3); `pixi.toml` 1646 |
| `mcp` `>=2.0.0` | yes | PyPI **2.0.0** (still latest 2026-08-24) | yes — dual-era SDK | PyPI JSON `info.version`; MCP runtime research Part B/C |
| `fastmcp >=3.4.7,<4` · `mcp >=1.24,<2.0` (stopgap) | yes | matches live `pixi.toml` 1605 / 1611 | yes as stopgap only | MCP runtime research Part C; first research file still says `fastmcp` 3.4.4 — **spine is newer and matches the repo** |
| Liquibase Community `>=5.0.4` | yes | **5.0.4** is latest Community (2026-08-20); no 5.0.5 | yes; Java 17+; #7791 fixed here | [Releases](https://github.com/liquibase/liquibase/releases); [docs index](https://docs.liquibase.com/community/release-notes); currency research Part B |
| OpenJDK **25.0.2** | yes | conda-forge current line **25.0.2** | yes — exceeds Liquibase Java 17 floor | [anaconda.org/conda-forge/openjdk](https://anaconda.org/conda-forge/openjdk) |
| OpenFeature + flagd FILE | packages **absent** on conda-forge | PyPI `openfeature-provider-flagd` still pins `cachebox >=5.1,<6`; FILE resolver still documented | adoption blocked until feedstocks — as AD-11/AD-16 say | stack.md; research §5; [flagd Python](https://flagd.dev/providers/python/); [PyPI provider](https://pypi.org/project/openfeature-provider-flagd/) |
| `cachebox` 5.x (`<6`) | 5.x needed; conda-forge ships **6.2.5** | pin still `<6` on latest provider | yes as a packaging constraint | stack.md; research §5 |
| PyBreaker **1.4.1** | yes | PyPI **1.4.1** (still latest) | yes for sync; async wrapper still required | PyPI JSON; research §4 |
| `django-lasuite` **0.0.28** | yes | PyPI **0.0.28**; conda-forge feedstock live | yes as OIDC only (`django>=5.0`) | [PyPI](https://pypi.org/project/django-lasuite/0.0.28/); research §5 |
| `django-storages` **1.14.6** | yes | PyPI **latest = 1.14.6** | yes (`Django>=3.2`) | [pypistats](https://pypistats.org/packages/django-storages); [readthedocs 1.14.6](https://django-storages.readthedocs.io/) |
| `django-redis` **7.0.0** | yes | PyPI **latest = 7.0.0** (2026-06-02); `Django>=5.2,<7` | yes | [PyPI 7.0.0](https://pypi.org/project/django-redis/7.0.0/); [GitHub release](https://github.com/jazzband/django-redis/releases/tag/7.0.0) |
| PostgreSQL **17** | yes | chart `postgres.image.tag: "17"`; compose `postgres:17` | yes — “existing chart”, not latest-upstream | `src/platform/deploy/charts/platform/values.yaml`; `src/platform/compose/compose.yml` |
| Redis **7** | yes | chart `redis.image.tag: "7"`; compose `redis:7` | yes — same | same files |
| CloudEvents **1.0** | yes | CNCF core latest **document** is **v1.0.2** (2022-02-05); wire `specversion` remains **`1.0`** | yes | [cloudevents/spec](https://github.com/cloudevents/spec/); [RELEASES.md](https://github.com/cloudevents/spec/blob/main/docs/RELEASES.md) |

---

## AD-by-AD (committed decisions, not just versions)

| ID | Decision | Reality-checked? | Note |
|---|---|---|---|
| AD-1..4 | Django reusable apps, `/stations/<name>/`, chrome in `django-pyforge`, naming triple | **design**, not a library version | host exists at `src/platform/`; `migrate-job.yaml` still `migrate --noinput` at weight 0 — Liquibase Job is **future**, correctly described |
| AD-5 | official `mcp` SDK, POST `/stations/<name>/mcp`, revisions `2025-03-26`–`2026-07-28`, echo on `initialize` | **yes, with wording compression** | MCP runtime research: five revisions; handshake vs modern dual-era. `2026-07-28` **removed** `initialize`; echo-on-initialize is handshake-era only. Spine still correct if read with that research. Public changelog confirms `-32022` and stale `-32003`/`-32004` ([spec changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)). |
| AD-6 | `start_*`/`get_*` over PostgreSQL, not SEP-2663 runtime | **yes** | MCP runtime Part A: SDK 2.0.0 still has no Tasks runtime |
| AD-7 | two clients, one assertion | design | no library to version |
| AD-8 | CloudEvents on Redis Streams | **spec yes; SDK unpinned** | `specversion=1.0` is correct. No Python `cloudevents` package in the Stack table (story-level, Deferred also leaves extension attribute names open) |
| AD-9 | Liquibase 5.0.4+, `liquibase` tracking schema, `preserveSchemaCase` off, direct PG | **yes** | 5.0.4 latest; JDBC **not** bundled in Community 5.0 ([LPM](https://docs.liquibase.com/community/user-guide-5-0/what-is-lpm), [issue #7580](https://github.com/liquibase/liquibase/issues/7580)) — matches stack.md, not restated in the spine Stack table (packaging lives in AD-16 / feedstock) |
| AD-10 | two Redis Deployments; Celery `BaseTaskBackend`; not django-tasks DB/RQ | **yes** | chart today is **one** Redis Deployment — the split is the new work. django-tasks still has no first-party Celery backend. **Trap:** PyPI `django-tasks-celery` 0.1.1 requires **Django 6.0+** — unusable under this pin |
| AD-11 | OpenFeature FILE in-process | **yes** | FILE resolver still exists; WASM/`wasmtime` still absent |
| AD-12 | supervisor → PostgreSQL | design | no new library |
| AD-13 | django-storages, django-redis renditions, PG FTS, `WAGTAILADMIN_LOGIN_URL` | **yes** | versions current; setting documented since 6.0 / 7.1 in research |
| AD-14 | five tiers | process | n/a |
| AD-15 | PyBreaker + asyncio wrapper | **yes** | 1.4.1 still latest; async still missing upstream |
| AD-16 | packaging gate; Django 5.2.17 is maintenance | **yes vs currency research** | **contradicts `stack.md`**, which still says 5.2.16/5.2.17 security “was not audited” |
| AD-17 | SKF content skills | **yes** | [armelhbobdad/bmad-module-skill-forge](https://github.com/armelhbobdad/bmad-module-skill-forge/) exists (v2.1.0 2026-08-07); `_bmad/skf/` in-repo |

---

## Requested public checks (detail)

### CloudEvents 1.0

Still the only `specversion` value for the 1.0 family. Latest **released** core spec is **v1.0.2**; main is `1.0.3-wip`. Producers MUST still emit `1.0`. Spine “CloudEvents 1.0” is the correct wire contract, not an obsolete 2019-only document. **Not stale.**

### django-storages 1.14.6

Current PyPI latest. Still the object-storage collection Wagtail docs expect for media-off-pod. **Not stale.**

### django-redis 7.0.0

Current PyPI latest. Declares `Django>=5.2,<7` — fits the 5.2 pin. Repo `pixi.toml` still pins **`django-redis ==6.0.0`** on unrelated cookiecutter/kedro-hub features; the **platform** env does not yet declare 7.0.0. Spine is a target pin, not a live solve. **Not stale as an architecture pin.**

### Wagtail 7.4.3

Current stable on PyPI; LTS 7.4 line; supports Django **5.2.x and 6.0.x** and Python 3.12. **Fits.** Wagtail **8.0 is in development** ([docs](https://docs.wagtail.org/en/latest/releases/8.0.html)); pixi `<8.0` is correct.

**Research overstatement (does not break the AD):** first research / `stack.md` say “5.2 is the only Django supported across the entire 7.0→8.0 range.” That is **false for 7.4.3**, which also supports Django 6.0. The weaker claim “no Wagtail version *requires* Django 6” still holds. Stay on 5.2.

### Liquibase 5.0.4

Latest Community release as of 2026-08-24. #7791 fix confirmed in trusted currency research. Community 5.0 **stopped bundling drivers**; PostgreSQL JDBC is LPM/Maven — still true ([docs](https://docs.liquibase.com/community/integration-guide-5-0/connect-liquibase-with-postgresql)). Secure-tier bundled drivers must not be confused with Community. **Not stale.**

---

## Flags (not confirmed, or confirmed stale)

### F1 — HTMX is committed without a version or research citation **[unconfirmed]**

Paradigm table: “Lane 2 portals … **HTMX** apps under `/stations/<name>/`.” HTMX is not in the Stack table, not in the four trusted research files, and not pinned in `pixi.toml`.

Public 2026-08-24: `django-htmx` **1.29.0** (2026-08-06) vendors **htmx 2.0.10** as default and **htmx 4 as beta**; changelog 1.28.0 dropped Django 4.2–5.1 (5.2 remains). conda-forge `django-htmx` last published **2026-07-16** — likely **behind** 1.29.0.

**Risk:** a portal story could adopt htmx 4 beta from django-htmx’s example project. Needs an explicit pin (htmx 2 / django-htmx floor) in the Stack table before implementation.

### F2 — `stack.md` Django CVE sentence is stale vs the spine and currency research **[companion contradiction]**

`stack.md` § Fixed floor: “Whether 5.2.16 or 5.2.17 carry security fixes was not audited.” Currency research (same day) audited both; 5.2.17 carries **CVE-2026-15307 (high)** plus six other CVEs; reachability in `src/platform/` is none. Spine AD-16 already treats the pin move as maintenance, not incident. **Do not treat `stack.md` as current on this point.**

### F3 — `django-tasks-celery` looks like the AD-10 backend and is not **[wrong-package trap]**

AD-10 “write a `BaseTaskBackend`” is still right under Django 5.2. A public package `django-tasks-celery` 0.1.1 implements Celery **for Django 6.0+ only**. Grabbing it would violate AD-8 (Python 3.12 + Django 5.2). Unmentioned in the spine — stories should be told not to.

### F4 — `django-lasuite` pixi floor vs spine pin **[env drift, minor]**

Spine: `0.0.28`. `pixi.toml` local-recipes: `django-lasuite >=0.0.27`. Solver may still land 0.0.28; the floor is one patch looser than the architecture pin.

### F5 — first research `fastmcp` 3.4.4 vs spine/repo 3.4.7 **[research older; spine correct]**

Not a spine defect. First technical research’s conda table is behind MCP-runtime research and `pixi.toml`.

---

## Explicitly not flags

- **PostgreSQL 18** appearing in some story notes vs chart **17**: spine binds the **existing chart**, which is 17.
- **CloudEvents 1.0 vs 1.0.2:** wire vs document patch; spine is right.
- **Django 5.2.15 on conda-forge vs 5.2.17 upstream:** known, owned by AD-16; 5.2.17 **does** contain security fixes (currency research), including one high-severity GIS CVE unreachable without GeoDjango.
- **Redis 7** vs newer Redis: existing chart, parent AD-1.
- **SKF GitHub URL:** live.

---

## Recommendation

Keep the Stack table as-is except:

1. Add **HTMX / `django-htmx`** with an explicit **htmx 2.x** (stable) pin and a note that htmx 4 is beta.
2. Optionally name the CloudEvents **Python SDK** when the first producer story picks one.
3. Fix `stack.md` CVE “not audited” so it cannot re-poison later planning.

No AD needs to be reopened on currency grounds.
