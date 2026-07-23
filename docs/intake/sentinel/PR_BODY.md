## Sentinel Build Spec v2.1 — Consolidated

This PR folds six side documents into a single build spec (`Sentinel-Build-Spec-vlatest.md`, revision `v2026-04-19-2`). It is **non-breaking for implementors who have not yet started** — same five agents, same eight epics, same four-phase rollout.

> If you read one thing: `Sentinel-Build-Spec-vlatest.md` §E Changelog.

---

### What's folded in

| Source (archived) | What it contributed |
|---|---|
| `Sentinel-Build-Spec-v2026-04-19-1.md` (v2.0) | Body — full prior revision |
| `Sentinel-License-Airgap-Audit-v2026-04-19-1.md` | 8 ADR deltas to clear the Apache-2.0 bar |
| `Sentinel-WASM-Analysis-v2026-04-19-1.md` | WASM feasibility + three modes (ADR-037) |
| `Sentinel-WASM-AllLocal-Addendum-v2026-04-19-1.md` | All-local airgap flavor, model tiers (ADR-038) |
| `Sentinel-WASM-Airgap-Install-v2026-04-19-1.md` | Split-bundle + `models.lock.json` install flow (ADR-039) |

All six moved unchanged into `archive/2026-04-19/` with `ARCHIVE_INDEX.md` as the provenance map.

### ADR ledger changes (11 total)

**Audit (8):**
- `005 → 005b` — in-house `sentinel.llm.gateway` + SDKs + vLLM (replaces LiteLLM)
- `006 → 006b` — SeaweedFS (replaces MinIO, archived Feb 2026)
- `008b retired` — analytical graph absorbed into PG via `pg_duckdb` (Kùzu archived 2025-10-10)
- `009 → 009b` — OTel GenAI semantic conventions (replaces Langfuse)
- `023 → 023b` — Impress unmodified + network-isolated + behind `KnowledgeSurface` (AGPL exception, documented)
- `034 NEW` — `pg_duckdb` analytical helpers
- `035 NEW` — `asyncpg` (Apache-2.0) replaces `psycopg[binary]` (LGPL)
- `036 NEW` — Perses + Jaeger + VictoriaLogs + VictoriaMetrics (replaces Grafana/Loki/Tempo, AGPL since Apr 2024)

**WASM branch (3):**
- `037 NEW` — WASM parallel branch; same contracts, different adapters
- `038 NEW` — all-local airgap WASM build (`SENTINEL_AIRGAP=1` tree-shakes cloud SDKs)
- `039 NEW` — split bundle + `models.lock.json` + cosign + internal mirror; four-point enforcement (build/publish/install/boot)

### License bar (hard, now explicit)

**Apache-2.0 / MIT / BSD / PostgreSQL-license only**, with exactly **one** documented AGPL exception (Impress, ADR-023b). Escape hatch: 1–2 day swap-out to `MkDocs Material + git markdown` behind the same `KnowledgeSurface` interface.

### Spec body edits (summary)

- §11.4 — L3 absorbs analytical graph into PG (`pg_duckdb` helpers; no nightly rebuild)
- §14 — topology swaps 5 components; 10 deployments total
- §16 — `pixi.toml` deltas (removed litellm/langfuse/kuzu/psycopg; added asyncpg; vLLM default; new `wasm-build` feature)
- §23 — gateway rewritten to in-house async router (~500 LOC); OTel GenAI attribute stamping
- §24 — observability rewritten to OTel GenAI → Jaeger/VictoriaLogs/Perses
- §25 — SeaweedFS buckets + PG 16 + `pg_duckdb` + `asyncpg`
- §29 — JSON-Schema-canonical contracts; Pydantic + Zod generated; `registry verify --target=wasm|server|both`
- §30 — `pins.yml` accepts local-bundle shape (`bundle_sha256` + `set_id`)
- §32 — adds weight-provenance and airgap-integrity rows
- §34 — adds `wasm-build.yml`, `wasm-airgap-verify.yml`, `wasm-eval-local.yml`
- §35 — phases unchanged; adds quarterly chaos drills from Q3
- Part VI §36–§41 — new: WASM overview, modes, adapters, all-local, airgap bundle + install, rollout W.0–W.3

### What **didn't** change

- Five agents (Analyst, Architect, Developer, QA, PO)
- Eight epics (E1…E8)
- FRs / NFRs numbering
- BMAD v6.3.x workflow (Parts II, §5–§10)
- Rollout phase dates and exit criteria
- Story template frontmatter shape

### Deliverables in this PR

- `Sentinel-Build-Spec-vlatest.md` — the spec (ship this)
- `archive/2026-04-19/` — six archived docs + `ARCHIVE_INDEX.md`
- `Sentinel-Stakeholder-Deck-v2026-04-19-2.html` — 12-slide stakeholder deck
- `Sentinel-Engineering-Deck-v2026-04-19-2.html` — 18-slide engineering deck
- `COMMIT_MSG.txt` — canonical commit message
- `scripts/commit_v2.1.sh` — shell script that does the moves + commit cleanly

### Reviewer checklist

- [ ] ADR-023b text reads as an **exception**, not an endorsement of AGPL in general
- [ ] License bar is unambiguous in §4 and §E
- [ ] `pg_duckdb` helpers replace every Kùzu call-site (search `kuzu` → zero hits in new spec body)
- [ ] `pins.yml` dual-shape example renders correctly (§30)
- [ ] WASM section says "opt-in experimental" in §3 and §37
- [ ] `archive/2026-04-19/ARCHIVE_INDEX.md` maps each archived doc to the new §
- [ ] Phase dates match v2.0
- [ ] No references to LiteLLM / Langfuse / MinIO / Kùzu / Grafana / Loki / Tempo outside `archive/` and the "retired" notes

### How to run the move + commit

```bash
bash scripts/commit_v2.1.sh
```

Or manually:

```bash
git mv Sentinel-Build-Spec-v2026-04-19-1.md          archive/2026-04-19/
git mv Sentinel-License-Airgap-Audit-v2026-04-19-1.md archive/2026-04-19/
git mv Sentinel-WASM-Analysis-v2026-04-19-1.md       archive/2026-04-19/
git mv Sentinel-WASM-AllLocal-Addendum-v2026-04-19-1.md archive/2026-04-19/
git mv Sentinel-WASM-Airgap-Install-v2026-04-19-1.md archive/2026-04-19/
git add Sentinel-Build-Spec-vlatest.md archive/2026-04-19/ARCHIVE_INDEX.md \
        Sentinel-Stakeholder-Deck-v2026-04-19-2.html \
        Sentinel-Engineering-Deck-v2026-04-19-2.html \
        deck-stage.js COMMIT_MSG.txt PR_BODY.md scripts/commit_v2.1.sh
git commit -F COMMIT_MSG.txt
```

### Open questions (resolved by / owner)

See `Sentinel-Build-Spec-vlatest.md` §B. Twelve numbered; Phase-1-exit decisions on cost ceilings (#1) and on-call ownership (#6) are the only ones blocking Q1 work.
