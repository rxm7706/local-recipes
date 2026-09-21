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
| `wagtail` | Pinned on `python-agent-platform` (steward CMS lane) | **In** with Phase 1 platform stack |
| `vizro-ai` / `vizro-mcp` / `dagster-webserver` pile, `dbt-*`, `minio`, `ollama`, `coderedcms` (as fat-only extras) | Fat `local-recipes` pins; not station/platform feature deps unless proven | **Out** until code/operator need is shown |
| Fat `local-recipes` feature as a whole | Kitchen sink | **Never compose** the fat feature |

No separate `desktop-lab` feature.

---

## Plan

### Phase 1 — BoM core + full platform local stack (this PR)

One compose onto `pyforge-foundry-full`:

**BoM core:** `build` + `grayskull` + `crm` + `conda-smithy`

**Full platform local stack:** `platform-dev` + `python-agent-platform` + `platform-object-storage`  
→ Postgres+pgvector, redis-server, Silo, Langflow/dashboard bring-up

**Also:** `pnpm` on an existing feature (`python` or `pyforge-guild`) — not a new feature.

Station-owned runtime deps (e.g. atlas `vizro`/`dagster`) stay with their station features — already in the foundry-full union when the package declares them.

**Do not** compose fat `local-recipes`. **Do not** invent `desktop-lab`.

### Phase 2 — Checkable SBOM + laptop gate

CI install + `pixi list` + channel audit + **laptop gate** (lint/tests/local CI + platform bring-up smokes). Failure ⇒ SBOM incomplete, not “use fat local-recipes.”

### Phase 3 — OpenTeams triage

Ticket every CF gap (SEM / pip / node / npm) **and** every “fat-only pin”: either promote into a composed feature (usage proven) or explicit won’t-do.

### Phase 4 — Point estate at foundry-full

CFE / AGENTS / mason → `pyforge-foundry-full`.

### Phase 5 — Close conda-forge gaps

Execute OpenTeams list (CF-SEM-*, CF-PIP-01, CF-NODE-*, CF-NPM-*).

---

## Success criteria

- [ ] **Phase 1:** BoM core + platform stack composed (`build`/`grayskull`/`crm`/`conda-smithy` + `platform-dev`/`python-agent-platform`/`platform-object-storage` + `pnpm`); usage-based deps available without fat `local-recipes`; `pixi.lock` in sync / CI green.
- [ ] Phase 2 laptop gate green from foundry-full alone.
- [ ] Phase 3 tickets for CF gaps + fat-only promote/won’t-do decisions.
- [ ] Phase 4 docs point at foundry-full.
- [ ] Phase 5 CF gaps closed or deferred.

## Mental model

```
include  = used by PyForge code OR needed by PyForge developer/operator
exclude  = unused kitchen-sink pins; never compose fat local-recipes feature
Phase 1  = BoM core + platform-dev + python-agent-platform + platform-object-storage (+ pnpm)
edit PR #1564 only — no side PRs, no desktop-lab
```
