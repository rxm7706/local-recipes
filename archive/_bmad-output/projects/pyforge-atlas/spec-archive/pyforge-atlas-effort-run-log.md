# pyforge-atlas — effort run log (reconstructed)

**⚠️ This is NOT a `bmad-loop` run journal.** The pyforge-atlas Kedro-migration was
never executed through the `bmad-loop` tmux orchestrator, so no `.bmad-loop/runs/<id>/`
journals exist. This document is a **reconstructed narrative** of how the effort actually
ran, assembled from the git history (merged PRs #81–#103, + Gemini-fix PR #105), the
in-session subagent transcripts (`atlas-agentloop-transcripts.tar.gz`), `deferred-work.md`,
and `sprint-status.yaml`. Treat it as an honest behind-the-scenes trace, not an
orchestrator-emitted record.

Session: `8c301a61` · Project: `pyforge-atlas` · Spec: `docs/specs/cfe-atlas-datapipeline-kedro-migration.md`
· Base branch: `claude/cfe-atlas-kedro-analysis-vgrol9` (waves) → squash-merged to `main`.

---

## How the effort actually ran (execution model)

Instead of `bmad-loop run <story>` (DEV → VERIFY → REVIEW → VERIFY → COMMIT in tmux
worktrees), each story ran through an **in-session agent loop** driven by the main agent:

1. **Draft** — a drafting subagent (or the main agent directly for mechanical stories)
   implements the story against the spec.
2. **In-loop review ×2** — two adversarial reviewer subagents probe the diff.
3. **Independent review ×1** — a *fresh-eyes* reviewer subagent, given only the spec +
   files (no prior context), hunts for real must-fixes. This pass repeatedly caught defects
   the in-loop reviewers missed (see the "independent review" rows below).
4. **Verify** — the main agent runs the *real* gates (`kedro-test`, `dagster-dryrun`,
   `no-inline-IO`, the per-story pixi task) and probes load-bearing invariants directly.
5. **Fix → commit → PR → self-merge → restart branch** from `origin/main`.

Honest deferral was used throughout: genuinely attended / credentialed / network-heavy
pieces were recorded as `DW-*` ledger entries rather than faked (54 deferrals total —
see the index at the end).

**Legend:** ✅ merged · mode `LOOP-S`=per-story-spec-approval · `LOOP-E`=per-epic ·
`DEV-AUTO`=judgment-heavy · `ATTENDED`=boundary event. "Indep. review" = a finding the
fresh-eyes reviewer caught that the in-loop pair missed.

---

## Wave 0 — preconditions

| Story | Commits | What |
|---|---|---|
| 0.1 | `b18cbb5` `6658049` | Skill Forge provisioned (`bmad-module-skill-forge@2.0.1`); `cf-atlas-legacy` contextual skill forged — SKF gates 100/100, staging promoted. |

## Wave A — scaffold (PRs pre-#81)

| Story | Commits | What + review |
|---|---|---|
| A1 | `1d8c5ab`→`188c6ef` | pyforge-atlas warden-pattern member scaffold; `kedro-test` gate green. Review patches applied. |
| A2 | `8b04f3b`→`0d6c801` | Data catalog — 73 entries; `kedro-catalog-check` gate. **Gemini PR-71** gate-hardening (4 medium) applied; a late reviewer round made the gate provably bite. |
| A3 | `2b53d3e`→`b2565ad` | `IncrementalParquetDataset` + TTL hook. **Gemini PR-72** perf + cross-platform fixes (3 medium) applied. |

## Wave B — pipelines (PRs ~#76–#83)

| Story | Commit(s) | PR | What + review findings |
|---|---|---|---|
| B1 (keystone) | `c90a44e` `8878ba4` | — | 12 conda-side backbone phases → Kedro nodes. **Indep. follow-up:** fixed a `downloads_source='merged'` contract violation. |
| B2 (keystone) | `2bee4cb` `121b8e6` | — | PyPI + vulnerability pipelines — 14 nodes, Phase-P cost gate, scheduler wired. Indep. follow-up: `_serial_moved` coercion. |
| B3 | `10ab9e9` `9ce0cc5` | #76 | Data surface re-exposed as Kedro-API-native MCP tools. **Gemini PR-76 (HIGH):** `read_dataset` MCP serialization fix. |
| B4 | `de5a7b7` | — | Parity harness hardened + credentialed-run + fail-closed retirement gate. Credentialed legacy-DB compare **deferred** (attended). |
| B5 | `f6b537b` `e5cbf6c` | #? | 3 external-refresh assets (§3.4), AD-13 keep-last-good. **Indep. review (HIGH):** AD-13 `UnicodeDecodeError` guard hole. |
| B6 | `35b88a5` | — | Seed-Gaps pipeline — 4 read-only gap suggesters, byte-identical seeds. |
| B7 | `4806fef` `1527803` | — | Universal SBOM intake extension. **Indep. review F1 (HIGH):** `_REQ_RE` extras/URL garbage-version fix. |
| B8 | `0968014` `05dcb1b` | #81 | Basilisk conda-native vuln ingestion (FR-19). **Indep. review (MED):** AD-13 never-fail gap in `_persist`. |
| B9 | `73e477f` | #82 | Release-to-availability velocity columns (FR-20). |
| B10 | `ecc161a` `520a75b` | #83 | Migration-readiness datasets + classifier (FR-21). Reviewer F1: hardened the inferred-label test with a confirmed-pending row. |

## Wave C — orchestration (PRs #84–#85)

| Story | Commit | PR | What |
|---|---|---|---|
| C1 | `166eb42` | #84 | kedro-dagster glue + `dagster-dryrun` gate (FR-6). Live daemon bring-up **deferred** (DW-C1-1). |
| C2 | `d4d7372` | #85 | kedro-viz behind a pixi `viz` task (FR-6/AC-3). |

## Wave D — semantic + dashboards (PRs #86–#88)

| Story | Commit(s) | PR | What |
|---|---|---|---|
| D1 | `580e5ba` | #86 | Boring Semantic Layer models over the core metrics (FR-8), pure Ibis→DuckDB. |
| D2 | `7b6b3ca` | #87 | BSL-driven Vizro dashboard + core CLI-port pages (FR-9). |
| D3 | `d58a4bd` | #88 | Vizro-AI NL interface + `query_vizro_ai` MCP tool (FR-9). LLM backend **deferred** (DW-D3-1). |

## Wave E — inter-agent + observability (PRs #90–#91)

| Story | Commit(s) | PR | What + review |
|---|---|---|---|
| E1 | `210b3a3` `01f8f82` | #90 | A2A structured-payload surface (FR-11). **Review:** hardened the AD-20 guard, enforced `schema_version`, closed a `model_construct` bypass. |
| E2 | `153a5ad` | #91 | OpenLineage + OpenTelemetry via the hook layer (FR-12). |

## Wave F — DuckDB singularity + gates (PRs #92–#95)

| Story | Commit(s) | PR | What + review |
|---|---|---|---|
| F1 | `13a5ce3` | #92 | DuckDB-singularity AST gate. Attended benchmark **deferred** (DW-F1-1). |
| F2 | `1e122c8` | #93 | Data-validation hook + inline Pandera contracts (FR-10). |
| F3 | `df58bfc` `2acfeaa` | #94 | DuckDB `vss` vector similarity RAG (FR-5). **Indep. review (LOW):** tightened identifier regex `$`→`\Z` (defense-in-depth). |
| F4 | `fd8e1c9` | #95 | Dependency-hygiene node + unified CI policy gate (FR-16/18/10). |

## Wave G — WASM + sensors (PRs #96–#98)

| Story | Commit(s) | PR | What + review |
|---|---|---|---|
| G1 | `203be0c` | #96 | DuckDB-WASM in-browser read surface + `wasm-smoke` gate (FR-14). |
| G2 | `6146f83` `33b3fd8` | #97 | Host-agnostic static-host Parquet emitter + HTTP-Range gate (FR-14). **Indep. review:** path-traversal MUST-FIX (`_require_safe_name`), then reject over-long names up front (LOW). |
| G3 | `40b9eae` | #98 | Dagster sensors for near-real-time upstream ingestion (FR-6). First story to complete its own full review loop. Live daemon **deferred** (DW-G3). |

## Wave H — AI Software Factory (PRs #99–#102)

Each H-story got a dedicated independent adversarial review; findings + fixes:

| Story | Commit | PR | What + independent-review findings (all fixed pre-merge) |
|---|---|---|---|
| H1 | `fe52bbd` | #99 | Karpathy wiki scaffold + 5 factory personas (FR-22a). Review probed AD-22 path-traversal (hammered 33 crafted names) — held. |
| H2 | `2f4240f` | #100 | agno compile/lint/Q&A crews (FR-22b). **2 MUST-FIX:** inline-`stale:` frontmatter laundering; lint/QA crash-on-malformed-page. **1 SHOULD-FIX:** leaf-only broken-link matching. |
| H3 | `4e95efb` | #101 | La Suite/Wagtail REST sync (FR-22c). **3 SHOULD-FIX:** malformed-2xx `KeyError`; non-atomic sidecar write; `compiled`-vs-`outputs` contract contradiction (source-stage corrected to `outputs/`). |
| H4 | `6cc2dbf` | #102 | Dagster crew assets + new-raw-file sensor + weekly-lint schedule (FR-22d/FR-6). **1 SHOULD-FIX:** `_decode_cursor` crash on a nested cursor. Verified `_kedro_jobs` test-scoping did not weaken any C1/G3 guard. |

## Closeout

| Item | Commit | PR | What |
|---|---|---|---|
| CFE Rule-2 retro | `e642fd6` | #103 | conda-forge-expert skill v8.78.0→**v8.79.0** (MINOR): new `atlas-phase-engineering.md` §14 (injected-IO/offline-first + AD-13 staleness propagation), CHANGELOG, Version History. Honest scoping: the effort authored no recipes. |

## Post-merge — Gemini review-comment sweep (PR #105, branch `claude/gemini-review-fixes`)

Gemini reviewed the whole series #81–#103 (~48 comments). Triage + fixes on one new
branch from `main`:

| Commit | What |
|---|---|
| `9ae2a17` | 25 files: applied the actionable findings (vuln-axis driver filter, fail-safe OL emit, transactional RAG index, recursive JSON-native coercion, cross-platform backslash/`as_posix`/`.git`-anchored roots, `StrictSafeLoader`, `kedro-viz` in the lean feature, test hygiene, type hints). Declined w/ rationale: **#86 `ibis.cases` false positive** (correct in ibis 12.0.0; `ibis.case` doesn't exist — would break working code), a2a defensive-copy + strict-`Literal` kind, empty-env-as-unset, perf micro-opts. |
| `3530e1e` | Second Gemini round: guard `type(obj).__module__` (can be `None`) before `.split()` in `_coerce_json_native`. |

All ~49 review threads resolved. Full atlas suite green (795 passed) throughout.

---

## Deferred-work ledger (54 entries — the honest deferrals)

Attended / credentialed / network / live-daemon pieces recorded rather than faked. Full
text in `implementation-artifacts/deferred-work.md`. Index:

`DW-A1-5` · `DW-A2-P4` · `DW-B1-1/2/3` · `DW-B2-1..5` · `DW-B4-1..6` · `DW-B5-1..4` ·
`DW-B6-1/2` · `DW-B7-1/2/3` · `DW-B8-1/2/3` · `DW-C1-1/2` · `DW-D2` · `DW-D2-1/2/3` ·
`DW-D3-1/2` · `DW-E1-1` · `DW-E2-1/2/3` · `DW-F1-1` · `DW-F2-1/2` · `DW-F3-1/2` ·
`DW-G1-1/2` · `DW-G2-1/2` · `DW-G3` · `DW-H1` (MinIO/PostgreSQL server) ·
`DW-H2` (agno/LLM synthesis + F3-vss retriever) · `DW-H3` (live Wagtail + httpx opener) ·
`DW-H4` (live crew daemon).

## Companion artifacts (delivered separately)

- `atlas-agentloop-transcripts.tar.gz` — the 125 raw subagent JSONL transcripts (the
  draft + review agents this log summarizes).
- `pyforge-atlas-implementation-artifacts.tar.gz` — Tier-3 gitignored state
  (`sprint-status.yaml`, `deferred-work.md`, A/B story files, `forge-data/`).
- Build artifacts — pyforge-atlas + pyforge-warden wheel/sdist/.conda (built @ `3530e1e`).
