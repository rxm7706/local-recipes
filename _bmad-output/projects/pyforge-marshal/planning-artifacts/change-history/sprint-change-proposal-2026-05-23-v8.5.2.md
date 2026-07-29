---
doc_type: sprint-change-proposal
project_name: local-recipes
date: 2026-05-23
author: rxm7706
trigger_type: release-driven
trigger_release: conda-forge-expert v8.5.2
scope: documentation-sync + observability-primitives
classification: Patch (bug fixes + opt-in enablement; no FR/NFR scope shift; no breaking CLI or MCP changes)
mode: Batch
status: approved
approved_by: rxm7706
approved_date: 2026-05-23
input_docs:
  - _bmad-output/projects/local-recipes/planning-artifacts/PRD.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-cf-atlas.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture-conda-forge-expert.md
  - _bmad-output/projects/local-recipes/planning-artifacts/architecture.md
  - _bmad-output/projects/local-recipes/planning-artifacts/epics.md
  - _bmad-output/projects/local-recipes/planning-artifacts/index.md
  - _bmad-output/projects/local-recipes/planning-artifacts/project-parts.json
  - _bmad-output/projects/local-recipes/implementation-artifacts/spec-phase-k-hang-fix.md
  - _bmad-output/projects/local-recipes/implementation-artifacts/retro-phase-k-hang-fix-2026-05-23.md
  - .claude/skills/conda-forge-expert/CHANGELOG.md
  - .claude/skills/conda-forge-expert/reference/atlas-actionable-intelligence.md
ground_truth:
  - .claude/skills/conda-forge-expert/CHANGELOG.md
  - .claude/skills/conda-forge-expert/config/skill-config.yaml
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
  - .claude/skills/conda-forge-expert/tests/unit/test_phase_k_hang_fix.py
  - .claude/skills/conda-forge-expert/tests/unit/test_phase_n_partial_batch.py
  - .claude/skills/conda-forge-expert/reference/atlas-phases-overview.md
  - .claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md
  - pixi.toml
  - .claude/data/conda-forge-expert/cf_atlas.db
---

# Sprint Change Proposal — conda-forge-expert v8.5.2 (2026-05-23)

## 1. Issue Summary

**Problem statement:** The 2026-05-23 channel-wide admin-profile bootstrap (`pixi run -e local-recipes bootstrap-data --profile admin`) surfaced four distinct production gaps in the cf_atlas pipeline, each of which silently degraded the observability or correctness of the data-refresh contract that downstream tools (`pypi-intelligence`, `staleness-report`, `feedstock-health`, `behind-upstream`) depend on.

### Context (when and how discovered)

A routine "update all data for cf-atlas" request triggered a channel-wide admin run. The run hung indefinitely in Phase K (two consecutive 26+ min silent stalls at both default concurrency=8 and the lowered concurrency=2). Forcing `PHASE_K_DISABLED=1` to recover and complete the rest of the refresh surfaced a post-mortem audit that found three additional gaps:

- **Phase P** (PyPI BigQuery downloads) had never operated since its v8.1.0 introduction — `google-cloud-bigquery` was documented as `pixi add`-by-operator and the auth path (gcloud SDK + ADC) had no first-class env, so the phase always cleanly skipped.
- **Phase Q robostack channel** had been silently returning 0 matches because the channel doesn't publish to `noarch` (ROS packages are compiled with Python bindings, not noarch) AND doesn't generate `current_repodata.json` (only the full `repodata.json`).
- **Phase N** lost exactly 50 of 27,287 feedstocks because the gh CLI exits non-zero when one repo in a batch doesn't exist, but the response body still contains valid partial data for the other 24 repos. The batch handler was discarding it.

### Evidence

| Finding | Evidence |
|---|---|
| Phase K silent hang | 2 consecutive runs (concurrency=8 and concurrency=2), each ~26 min with no log output after the phase header. TCP socket `ESTAB` to `api.github.com:443`, ~0 CPU consumed. `gh api rate_limit` showed 4,624/5,000 GraphQL quota remaining — ruling out rate limit. No checkpoint row in `phase_state`. |
| Phase P never enabled | Every prior bootstrap-data log line: `"google-cloud-bigquery library not importable. Skipping."` Zero rows in `pypi_intelligence.downloads_30d`. |
| Phase Q robostack 404 | Last 3 admin runs all logged `"robostack: fetch failed — HTTPError: HTTP Error 404: Not Found; column not updated"`. `in_robostack=1` count: 0 rows. Manual `curl` to `current_repodata.json` confirmed HTTP 404; full `repodata.json` HTTP 200 with 8,487 packages in `linux-64`. |
| Phase N 50 failures | `meta.phase_N` showed `failed: 50` exactly = 2 × 25 batches. Per-feedstock error column showed both batches had been killed by ONE repo each: `staged-recipes-feedstock` (doesn't exist) and `nss-cos7-aarch64-feedstock` (renamed/removed). |

## 2. Impact Analysis

### Epic Impact

| Epic | Stories Affected | Verdict |
|---|---|---|
| **Epic 8** (cf_atlas Phase F-N + Backends + TTL Gates) | E8.S11 (Phase K), E8.S14 (Phase N) — quality+reliability improvements layered on top of existing acceptance criteria. Existing E8.S17 (Phase K secondary-rate-limit backoff) is **complementary, not redundant**: S17 addresses the v7.7.2 REST-era 403-burst pattern that the v7.8.0 GraphQL refactor mostly eliminated; v8.5.2 layers a hard-timeout watchdog + per-batch checkpoint that catches the *different* failure mode where the underlying socket read stalls indefinitely with no CLI-visible error. | No new stories needed; acceptance criteria from E8.S11/S14 already satisfied. |
| All other epics | None | No impact. |

### Artifact Conflicts

| Artifact | Conflict | Action |
|---|---|---|
| `PRD.md` | `source_pin: 'conda-forge-expert v8.5.1'` → v8.5.2; one new DW (Deferred Work) candidate ("DW4: extend per-batch checkpoint + hard-timeout watchdog pattern to Phases L/M"). | Pin bump + edit_history append; version v1.4.0 → v1.4.1 (PATCH). |
| `architecture-cf-atlas.md` | `source_pin: v8.1.0` → v8.5.2; Phase K/N/Q sections need v8.5.2 callouts; two new observability primitives need a callout under "Operational patterns". | Pin bump + targeted prose deltas. |
| `architecture-conda-forge-expert.md` | `source_pin: v8.1.0` → v8.5.2; pixi env count 8 → 9 (new `gcloud` env); mention `google-cloud-bigquery` bundled in `local-recipes`. | Pin bump + env-list update. |
| `architecture.md` (umbrella) | Cross-doc pin references. | Pin bump only. |
| `epics.md` | `sync_lineage` append v8.5.2 entry; E8.S11/S14 reliability notes. | Lineage append; no story-status changes. |
| `index.md` | Doc-set pin reference. | Pin bump. |
| `project-parts.json` | `source_pin` field; `pixi_envs` array for `conda-forge-expert` part. | Pin bump + `gcloud` added to pixi_envs. |
| `atlas-actionable-intelligence.md` | Phase P "downloads_30d / downloads_90d" rows were 📋-open pending BigQuery enablement; now shipped. Phase Q robostack-in-channel row was 📋 due to 404; now shipped. | Flip 2-3 rows from 📋 → ✅ with v8.5.2 verification line. |
| `architecture-mcp-server.md` | None — no MCP tool surface changed. | No change. |
| `validation-report-PRD.md` | None — FR/NFR set unchanged. | No re-validation required. |

### Technical Impact

| Layer | Impact |
|---|---|
| Schema | None — schema v22 preserved. The new `phase_state` row that Phase K now writes uses existing table + columns. |
| Database state | +850,477 `pypi_intelligence.downloads_30d` rows (Phase P shipped); +24,899 GitHub + 374 GitLab + 14 Codeberg `upstream_versions` rows refreshed (Phase K hang fix); +32,167 `packages.vuln_total` populated + 404,042 `package_version_vulns` rows (Phase G/G' opportunistically run from `vuln-db` env); 1 row in `pypi_intelligence.in_robostack` (`draco`); Phase N failed-batch count 50 → 2. |
| Code | `scripts/conda_forge_atlas.py`: 4 surgical changes (Phase K rewrite + Phase N partial-batch parse + Phase Q subdir/fallback + new helpers `_phase_k_backoff_seconds`, `_phase_k_fetch_with_hard_timeout`). |
| Tests | +18 unit tests (12 Phase K + 6 Phase N); suite 1088 → 1094 passing; 2 skipped (pre-existing); 1 XPASS (tracked tech-debt). |
| CLI/MCP surface | No changes. All env vars are additive (`PHASE_K_BATCH_HARD_TIMEOUT_S`, `PHASE_K_LOG_EVERY_N_BATCHES`); defaults match prior behavior except where prior behavior was broken. |
| Dependencies | `pixi.toml`: `google-cloud-bigquery >=3.41.0` added to `[feature.local-recipes.dependencies]`; new `[feature.gcloud-sdk]` with `google-cloud-sdk >=569.0.0` (linux + macOS only, no win-64 on conda-forge); new `gcloud` env in `[environments]`. |
| Configuration | `.env` (gitignored): `PHASE_P_BQ_PROJECT=gen-lang-client-0703913762` added. |
| Documentation | `reference/atlas-phases-overview.md` § Phase P expanded (4-step setup walkthrough + run commands); `quickref/commands-cheatsheet.md` new Phase P subsection. |

## 3. Recommended Approach — Option 1: Direct Adjustment

**Selected:** Direct Adjustment (pin-only updates + targeted prose deltas across listed planning artifacts, no story rewrites or epic rescoping). Matches the prior four release-driven sync proposals (v7.9.0, v8.0.0, v8.1.0, v8.5.1).

**Rationale:**

- v8.5.2 is bug-fix + opt-in enablement scope. No FR/NFR changes; no CLI/MCP surface changes; no breaking changes.
- All four shipped items have live verification on production data (24,821 GitHub repos through Phase K; 850,477 BigQuery rows through Phase P; 48 of 50 previously-failed feedstocks recovered through Phase N; Phase Q now 4/4 channels reporting).
- Risk: low. The hard-timeout watchdog has been exercised both by unit tests (12 tests covering timeout / network / HTTPError / unexpected exception paths) and by the 30 min channel-wide run.
- Effort: low. Pin updates across ~7 artifacts; ~1 page of prose updates in `architecture-cf-atlas.md` for the two new observability primitives.
- Timeline: same-day (this proposal + subsequent `bmad-edit-prd` invocation).

**Effort:** Low. **Risk:** Low. **Timeline impact:** None — closing the audit gap accelerates downstream confidence in admin-profile runs.

## 4. Detailed Change Proposals

### 4.1 PRD.md

```yaml
# Header frontmatter
OLD:
  source_pin: 'conda-forge-expert v8.5.1'
  re_validated: 2026-05-23
NEW:
  source_pin: 'conda-forge-expert v8.5.2'
  re_validated: 2026-05-23
```

Append edit_history entry:

```yaml
  - { date: '2026-05-23', via: 'bmad-correct-course', delta: 'v8.5.1 → v8.5.2 sync after the 2026-05-23 admin-refresh audit (spec-phase-k-hang-fix.md + retro-phase-k-hang-fix-2026-05-23.md): 4 bundled fixes. (a) Phase K hang fix — _phase_k_fetch_with_hard_timeout daemon-thread watchdog (45s default, env PHASE_K_BATCH_HARD_TIMEOUT_S) replaces urllib timeout that did not fire on stalled streams; per-batch progress log every N batches (env PHASE_K_LOG_EVERY_N_BATCHES, default 4); per-batch checkpoint into phase_state with running/completed status + cursor; explicit exception classification (timeout / network / HTTP / unexpected) with v7.8.1 jitter backoff helper _phase_k_backoff_seconds. (b) Phase P enablement — google-cloud-bigquery>=3.41.0 bundled in local-recipes env; new [feature.gcloud-sdk] + gcloud env for one-time gcloud auth application-default login; PHASE_P_BQ_PROJECT in .env; 4-step operator setup walkthrough in reference/atlas-phases-overview.md § Phase P. Live-verified 850,477 PyPI projects ingested. (c) Phase Q robostack 404 fix — subdir corrected to linux-64 (noarch is empty for ROS packages); current_repodata.json → repodata.json fallback in _phase_q_fetch_channel_pypi_names. Now 4/4 channels reporting. (d) Phase N partial-batch recovery — parse gh stdout regardless of returncode so partial {data, errors[]} responses from one-missing-repo batches recover the other 24 instead of poisoning the whole batch. 48 of 50 previously-failed feedstocks now recovered; the 2 remaining are real missing repos. PATCH bump (no FR/NFR scope shift; no breaking CLI or MCP changes). Suite 1088 → 1094 passing. Retro: implementation-artifacts/retro-phase-k-hang-fix-2026-05-23.md.' }
```

Optional new Deferred Work table row (if PRD's DW section is present in its current shape):

```markdown
| DW4 | Extend per-batch checkpoint + hard-timeout watchdog pattern to Phases L/M | `retro-phase-k-hang-fix-2026-05-23.md` § Follow-up |
```

Version: v1.4.0 → v1.4.1 (PATCH).

### 4.2 architecture-cf-atlas.md

**Frontmatter:**
```yaml
OLD:  source_pin: 'conda-forge-expert v8.1.0'   # or v8.5.1 if previously bumped
NEW:  source_pin: 'conda-forge-expert v8.5.2'
```

**Phase K section** — add note:
> v8.5.2 wraps the GraphQL fetch in `_phase_k_fetch_with_hard_timeout` (daemon-thread `Event`-based wall-clock budget; default 45s, env `PHASE_K_BATCH_HARD_TIMEOUT_S`). Closes a class of indefinite-hang failures where `urllib.request.urlopen`'s built-in timeout did not fire on stalled SSL streams (truststore / HTTP-2 interaction suspected). Per-batch checkpoints land in `phase_state` for forensic visibility; per-batch progress log every `PHASE_K_LOG_EVERY_N_BATCHES` (default 4).

**Phase N section** — add note:
> v8.5.2 parses gh CLI stdout regardless of returncode. GitHub returns valid partial `{data: {...}, errors: [...]}` payloads when one repo in a batch doesn't exist (e.g. renamed feedstock), but `gh api graphql` exits non-zero. Prior behavior discarded the body, losing 24 good rows per bad row. Now: extract `data` first, treat null aliases as `repo not found (404)`; fall through to whole-batch-fail only on truly empty/unparseable stdout. Matches the pattern Phase K's `_phase_k_github_graphql_batch` already uses.

**Phase Q section** — add note:
> v8.5.2: `_PHASE_Q_CONDA_CHANNELS["robostack"]` subdir corrected from `["noarch"]` to `["linux-64"]` (robostack-staging's noarch is empty — ROS packages are compiled). `_phase_q_fetch_channel_pypi_names` now falls back from `current_repodata.json` → `repodata.json` on 404 (robostack-staging doesn't generate the optimized form). 4/4 channels now reporting.

**New "Operational patterns" subsection** (or extend an existing one) — document two reusable primitives:
> **Hard-timeout watchdog (`_phase_k_fetch_with_hard_timeout`)** — when `urllib`'s built-in `timeout=` doesn't fire reliably (truststore / HTTP-2 interaction), wrap the call in a daemon thread + `threading.Event` with a wall-clock budget. Re-usable across any phase doing single-shot HTTPS POSTs through urllib.
>
> **Per-batch checkpoint (`phase_state` table)** — write a 'running'/`batch=N` cursor row per batch, flip to 'completed' on phase exit. A hang or kill leaves a forensic trail showing exactly which batch never returned. Candidate for adoption in Phases L and M (currently write only at end).

### 4.3 architecture-conda-forge-expert.md

**Frontmatter:**
```yaml
OLD:  source_pin: 'conda-forge-expert v8.1.0'
NEW:  source_pin: 'conda-forge-expert v8.5.2'
```

**Pixi env list** — update count and add new entry:
> 9 pixi envs (`linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `vuln-db`, `gcloud`); `local-recipes` is the default... New `gcloud` env (v8.5.2) carries `google-cloud-sdk` for one-time `gcloud auth application-default login` (kept separate because the SDK is ~91 MB and used only at credential-setup time). Linux + macOS only — `google-cloud-sdk` is not on conda-forge for win-64.

**Conda-forge-expert script table** — already lists `conda_forge_atlas.py` as the 22-phase orchestrator; add a one-line v8.5.2 callout for the two new helpers.

### 4.4 epics.md

Append to sync_lineage:
```yaml
  - { release: 'v8.5.2', date: '2026-05-23', via: 'sprint-change-proposal-2026-05-23-v8.5.2.md', delta: 'Phase K hang fix + Phase P enablement + Phase Q robostack + Phase N partial-batch — quality+reliability layer over E8.S11/S14; no story rescoping.' }
```

E8.S11 and E8.S14 reliability notes (optional — at the maintainer's discretion).

### 4.5 project-parts.json

```json
OLD:  "source_pin": "conda-forge-expert v8.1.0"
NEW:  "source_pin": "conda-forge-expert v8.5.2"

For the conda-forge-expert part:
OLD:  "pixi_envs": ["local-recipes", "grayskull", "conda-smithy", "vuln-db"]
NEW:  "pixi_envs": ["local-recipes", "grayskull", "conda-smithy", "vuln-db", "gcloud"]
```

### 4.6 index.md

Pin bump only — same shape as the prior 4 entries' index.md sync.

### 4.7 atlas-actionable-intelligence.md

Flip 📋 → ✅ for any rows tied to:
- Phase P PyPI download counts (downloads_30d / downloads_90d signal)
- Phase Q robostack-channel presence

Add "v8.5.2 verified 2026-05-23" tag inline.

### 4.8 architecture.md (umbrella doc)

Pin bump only.

## 5. Implementation Handoff

**Scope classification:** Minor (Patch-level documentation sync — direct implementation by Developer agent).

**Handoff recipient:** `bmad-edit-prd` skill (next invocation) for the PRD edits; remaining artifacts (architecture-cf-atlas, architecture-conda-forge-expert, architecture, epics, index, project-parts.json, atlas-actionable-intelligence) updated by the developer agent directly per § 4 deltas above.

**Success criteria:**

- [x] Sprint Change Proposal written to `planning-artifacts/sprint-change-proposal-2026-05-23-v8.5.2.md` (this document)
- [ ] PRD `source_pin` flipped to v8.5.2; edit_history entry appended; version v1.4.0 → v1.4.1
- [ ] `architecture-cf-atlas.md` pin bumped; Phase K/N/Q callouts added; Operational patterns subsection added (or extended) with watchdog + checkpoint primitives
- [ ] `architecture-conda-forge-expert.md` pin bumped; pixi env count 8 → 9; new `gcloud` env documented
- [ ] `epics.md` sync_lineage appended
- [ ] `project-parts.json` pin + pixi_envs updated
- [ ] `index.md` pin bumped
- [ ] `atlas-actionable-intelligence.md` rows for Phase P / Phase Q robostack flipped from 📋 to ✅
- [ ] All ground-truth files cited in frontmatter remain authoritative

## 6. Decision

**Approved.** Pin-only updates across listed planning artifacts; substantive content updates concentrated in `architecture-cf-atlas.md` (the technical surface) and `project-parts.json` (the structured manifest). PRD PATCH bump (no FR/NFR scope shift; bug fixes + opt-in enablement only).

No re-validation required — existing PRD validation report at `validation-report-PRD.md` remains current at the FR level.

## 7. Outcome (post-implementation expectation)

- PRD v1.4.1 pinned to `conda-forge-expert v8.5.2` with edit-history entry
- Architecture-cf-atlas reflects v8.5.2 callouts + reusable observability primitives
- Architecture-conda-forge-expert reflects 9-env pixi layout
- Retro at `retro-phase-k-hang-fix-2026-05-23.md` captures the post-mortem and the follow-up candidates
- Atlas-actionable-intelligence: 2-3 rows flipped to ✅
- 1 new DW row (DW4: extend per-batch checkpoint + hard-timeout watchdog pattern to Phases L/M)

## 8. Trigger conditions for next bump

- Live verification of the v8.5.2 admin-profile end-to-end run (now achievable since `PHASE_K_DISABLED=1` is no longer required) — confirms readiness from "implementation + targeted-rerun verified" to "channel-wide-production verified"
- DW4 (extend per-batch checkpoint pattern to Phases L/M) would bundle into v8.6.0 if operator demand surfaces — currently 📋
- Phase Q's 5 deferred channels (homebrew, nixpkgs, spack, debian, fedora) remain on v8.2.0 spec backlog; each is independent and could ship one at a time
- Schema v23 trigger: any future column-modification to existing tables (not new tables/views; those go in MINOR bumps)

---

**Approval log:** Approved by `rxm7706` on `2026-05-23` in Batch mode via `bmad-correct-course` skill invocation.
