# `pyforge-foundry-full` as the PyForge SBOM

**Status:** Phase 1 in [PR #1564](https://github.com/rxm7706/local-recipes/pull/1564) only (no side PRs).
**Env:** `pixi install -e pyforge-foundry-full` (never the default session env).
**Not the SBOM:** the fat `local-recipes` *feature blob* (~200+ pins / ~10 GB) as a kitchen sink.

---

## What “full SBOM” means

`pyforge-foundry-full` is complete only when a **developer laptop** can, from that env alone:

1. `pixi install -e pyforge-foundry-full`
2. **Launch** the apps (stations / guild / **Langflow + dashboard** local bring-up)
3. **Run tests**
4. **Lint**
5. **Run local CI** mirrors
6. Use **platform plugins** by composing **existing** features (no new “desktop-lab”):
   - **`platform-dev`** — PostgreSQL + pgvector, redis-server, Silo
   - **`python-agent-platform`** — Langflow / Django / Celery clients for dashboard bring-up
   - **`platform-object-storage`** — Silo/Garage up/down/status tasks
   - **Playwright + Chromium** — already on atlas / herald
   - **`pnpm`** — pin on existing `python` or `pyforge-guild` when herald/atlas web/wasm need it

### Inclusion rule (not a name blacklist)

**Keep out of foundry-full** anything that is **not** in PyForge code and **not** required by a PyForge developer/operator workflow — even if it currently sits in fat `local-recipes`.

**Pull into foundry-full** (via the feature that owns it) anything that **is** used by PyForge code or needed to develop/operate PyForge — even if the pin historically lived only under fat `local-recipes`.

Examples of applying the rule (audit, don’t assume):

| Package | Evidence | SBOM stance |
|---|---|---|
| `vizro`, `dagster` | Declared + imported in `pyforge-atlas` package (`pixi.toml` / tests / dashboard) | **In** — via atlas (already composed); not “banned because Vizro” |
| `wagtail` | Pinned on `python-agent-platform` (steward CMS lane) | **In** once `python-agent-platform` solves into the union (see gaps) |
| `vizro-ai` / `vizro-mcp` / `dagster-webserver` pile, `dbt-*`, `minio`, `ollama`, `coderedcms` (as fat-only extras) | Fat `local-recipes` pins; not station/platform feature deps unless proven | **Out** until code/operator need is shown |
| Fat `local-recipes` feature as a whole | Kitchen sink | **Never compose** the fat feature |

No separate `desktop-lab` feature.

---


**libpq-17 caps (keep Postgres 17):** `psycopg = ">=3.2.9,<3.2.10"` (3.2.10+/3.3.x `psycopg-c` need libpq 18) and `pgvector = ">=0.8.0,<0.8.2"` (0.8.2+ need libpq 18). Do **not** bump `postgresql` to 18 to paper over those.

## Plan

### Phase 1 — BoM core + full platform local stack (this PR)

**Target compose** onto `pyforge-foundry-full`:

- **BoM core:** `build` + `grayskull` + `crm` + `conda-smithy`
- **Full platform local stack:** `platform-dev` + `python-agent-platform` + `platform-object-storage`
- **Also:** `pnpm` on an existing feature (`python` / `pyforge-guild`)

**Landed in this PR (solvable union):** `build` + `grayskull` + `crm` + `platform-dev` + `platform-object-storage` + `pnpm`, with `postgresql` bumped to `>=18.3,<19` so `platform-dev` aligns with `psycopg`/`libpq` 18.

**Phase 1 residual solve gaps (do not compose fat `local-recipes` to paper over them):**

| Gap | Blocker | Interim |
|---|---|---|
| `conda-smithy` in foundry-full | 3.x wants `py-rattler <0.23` or `conda <26.3`; union has `py-rattler >=0.25` and `conda >=26.5` from `build` | Keep using `pixi exec conda-smithy…` (already how the feature’s lint task works); ticket a CalVer/`conda` co-solve or drop from union |
| `python-agent-platform` in foundry-full | `langflow` → `pandas >=2,<3` / `onnxruntime` clash with the station union | Ticket; until then dashboard/Langflow via `-e python-agent-platform` / `-e platform-dev` |

**Do not** compose fat `local-recipes`. **Do not** invent `desktop-lab`.

### Phase 2 — Checkable SBOM + laptop gate

CI install + `pixi list` + channel audit + **laptop gate** (lint/tests/local CI + platform bring-up smokes). Failure ⇒ SBOM incomplete, not “use fat local-recipes.”

### Phase 3 — OpenTeams triage

Ticket every CF gap (SEM / pip / node / npm) **and** every “fat-only pin”: either promote into a composed feature (usage proven) or explicit won’t-do. **Also** the Phase 1 residual solve gaps above.

### Phase 4 — Point estate at foundry-full

CFE / AGENTS / mason → `pyforge-foundry-full`.

### Phase 5 — Close conda-forge gaps

Execute OpenTeams list (CF-SEM-*, CF-PIP-01, CF-NODE-*, CF-NPM-*).

---

## Success criteria

- [x] **Phase 1 (partial):** BoM `build`/`grayskull`/`crm` + `platform-dev`/`platform-object-storage` + `pnpm` composed; `pixi.lock` refreshed; usage-based deps without fat `local-recipes`.
- [ ] **Phase 1 (complete):** `conda-smithy` + `python-agent-platform` also in the foundry-full union (solve gaps closed).
- [ ] Phase 2 laptop gate green from foundry-full alone.
- [ ] Phase 3 tickets for CF gaps + fat-only promote/won’t-do + Phase 1 residual gaps.
- [ ] Phase 4 docs point at foundry-full.
- [ ] Phase 5 CF gaps closed or deferred.

## Mental model

```
include  = used by PyForge code OR needed by PyForge developer/operator
exclude  = unused kitchen-sink pins; never compose fat local-recipes feature
Phase 1  = BoM core + platform stack (land what solves; ticket the rest)
edit PR #1564 only — no side PRs, no desktop-lab
```
