# The signal catalog — 23 ported phases, 3 additive riders

Companion to `SPEC.md`. The kernel's Capabilities declare that the 23 legacy phases run as
DAG-resolved nodes across seven typed pipelines, and that new signals ride in additively with
their failure modes fixture-pinned. This file is the per-signal catalog: which legacy phase
became which node, what it reads and writes, and which behavioral contract binds the port.

A signal is one measured fact about the conda-forge population. The kernel says *how many* and
*under what rules*; without this table, "the legacy phases survive the port with their
contracts intact" names no contract and can be neither reviewed nor refuted.

Legacy citations are `CFA` = `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py`
at `b18cbb5`. Where this file and the shipped pipeline disagree, **the code is right**.

---

## Ported phases — conda-side backbone (12 nodes)

Eleven legacy phases plus the promoted Phase I. Phase I was an *unregistered side effect* in
the monolith — per-version download history written as a by-product of Phase F — and the port
made it an explicit node with declared outputs. That promotion is the pattern: a side effect
that nobody declared is exactly the thing an agent cannot safely extend.

| Phase | Pipeline | Node | Reads | Writes | Binding contract | Legacy |
|---|---|---|---|---|---|---|
| **B** | `core` | `enumerate_conda_packages` | `core_repodata_raw`, `core_channeldata_raw` | `core_packages_enumerated` | `v_actionable_packages` scope discipline — every raw `packages` read carries the persona-filter triplet or a `# scope:` note | `phase_b_conda_enumeration` 1408 |
| **B.5** | `core` | `attribute_feedstocks` | `core_feedstock_outputs_raw` | `core_feedstock_attribution` | `_pick_feedstock` umbrella-vs-dedicated attribution: empty→`None`; `len>1 and pkg_name in feedstocks`→`pkg_name`; else `feedstocks[0]` | `_pick_feedstock` 1572 |
| **B.6** | `core` | `detect_latest_status` | `core_repodata_raw`, `core_channeldata_raw` | `core_latest_status` | **lite** presence→`latest_status`; no per-version yanked scan | `phase_b6_yanked_detection` 1665 |
| **F** | `core` | `compute_downloads` | `core_anaconda_downloads_raw`, `core_s3_download_stats_raw` | `core_downloads` + 3 breakdowns | Provenance discipline (see below) | `phase_f_downloads` 3560 |
| **I** | `core` | `compute_version_download_history` | `core_anaconda_downloads_raw` | `core_version_download_history` | Promoted from side effect to declared node output | sites 2931 / 3402 |
| **J** | `core` | `build_dependency_graph` | `core_cf_graph_raw` | `core_dependencies` | Archived-feedstock skip-set filter **at the write site** | `phase_j_dependency_graph` 6067 |
| **M** | `core` | `compute_feedstock_health` | `core_cf_graph_raw` | `core_feedstock_health` | Archived-feedstock scope filter at write SELECT | `phase_m_feedstock_health` 6263 |
| **E** | `vcs_health` | `enrich_maintainers` | `core_cf_graph_raw` (cross-pipeline) | `vcs_maintainers`, `vcs_package_maintainers` | Maintainer-universe ~44 delta documented, not silently absorbed | `phase_e_enrichment` 2188 |
| **E.5** | `vcs_health` | `detect_archived_feedstocks` | `vcs_github_api_raw` | `vcs_archived_feedstocks` | — | `phase_e5_archived_feedstocks` 2504 |
| **K** | `vcs_health` | `track_upstream_versions` | `vcs_{github,gitlab,codeberg}_api_raw` | `vcs_upstream_versions` | The token bucket (see below) | `phase_k_vcs_versions` 5039 |
| **L** | `vcs_health` | `track_registry_versions` | `vcs_registry_*_raw` (8 registries) | `vcs_registry_versions` | Per-registry concurrency caps; per-source TTL | `phase_l_extra_registries` 5841 |
| **N** | `vcs_health` | `fetch_live_health` | `vcs_github_api_raw` | `vcs_live_health` | Rate-limit-stderr detection; 1 d TTL | `phase_n_github_live` 6525 |

## Ported phases — PyPI intelligence and vulnerability (11 nodes)

| Phase | Pipeline | Node | Reads | Writes | Binding contract | Legacy |
|---|---|---|---|---|---|---|
| **C** | `pypi_intelligence` | `map_pypi_conda` | `pypi_parselmouth_mapping_raw`, `core_packages_enumerated` | `pypi_conda_mapping` | `g10_spelling` provenance tier survives as a valid `match_source`; no-clobber rule | `phase_c_parselmouth_join` 1744 |
| **C.5** | `pypi_intelligence` | `match_source_urls` | source-url data | `pypi_conda_mapping` (extend) | Same no-clobber discipline | `phase_c5_source_url_match` 1802 |
| **D** | `pypi_intelligence` | `enumerate_pypi_universe` | `pypi_simple_index_raw` | `pypi_universe` | Universe upsert TTL-gated; skippable under the consumer profile | `phase_d_pypi_enumeration` 1947 |
| **H** | `pypi_intelligence` | `fetch_pypi_current_versions` | `pypi_json_raw`, `pypi_universe` | `pypi_current_versions` | **Serial gate**: never-fetched OR serial-moved OR 30 d. Denominator excludes pypi-only. Retains `upload_time_iso_8601` — B9 depends on it. | `phase_h_pypi_versions` 4517 |
| **O** | `pypi_intelligence` | `snapshot_pypi_serials` | `pypi_simple_index_raw` | `pypi_universe_serial_snapshots` | `activity_band` from snapshot deltas; 90 d roll | `phase_o_serial_snapshots` 7051 |
| **P** | `pypi_intelligence` | `fetch_pypi_downloads` | `pypi_bigquery_downloads_raw` | `pypi_downloads_monthly` | The two-layer cost gate (see below) | `phase_p_pypi_downloads` 7352 |
| **Q** | `pypi_intelligence` | `flag_cross_channel` | `pypi_cross_channel_repodata_raw` | `pypi_cross_channel_flags` | Per-channel `in_<channel>` BOOLs from bulk repodata | `phase_q_cross_channel` 7847 |
| **R** | `pypi_intelligence` | `enrich_pypi_intelligence` | `pypi_json_raw`, candidate slice | `pypi_intelligence_enriched` | **Single-write-path**: `_phase_r_fetch_one` + `phase_r_upsert_one` shared with add-handoff | `phase_r_pypi_json_enrich` 8330 |
| **S** | `pypi_intelligence` | `score_pypi_readiness` | `pypi_intelligence_enriched` | `pypi_intelligence_scored` | `apply_readiness_scores` single-write-path; **`notes` overrides survive re-runs**; `v_pypi_intelligence_valid` view discipline | `phase_s_computed_scores` 8546 |
| **G** | `vulnerability` | `summarize_vdb_vulns` | `vulnerability_vdb_store`, KEV / EPSS / CWE | `vulnerability_package_rollup` | KEV overlay `_load_kev_cves` + `_coerce_cvss_score` score-type unwrap; `_aggregate_v8_6_0_overlays` max-EPSS with **None ≠ 0** | `phase_g_vdb_summary` 3771 |
| **G′** | `vulnerability` | `per_version_vulns` | `vulnerability_vdb_store`, `core_version_download_history` | `vulnerability_package_version_vulns` | Backs `v_current_version_vulns` — the **only** query-time-correct vuln source | `phase_g_prime_per_version_vulns` 6808 |

## The four contracts most often misread

Called out because each one, if quietly dropped in a port, produces a plausible number that is
wrong — the worst failure mode for an intelligence layer.

**Phase F provenance discipline.** `downloads_source ∈ {anaconda-api, s3-parquet, merged}` are
correlated but distinct. The three breakdown datasets are written **only on the s3-parquet
path**. Writes are replace-by-scope-key. `downloads_30d` is the latest **calendar month**, not
a rolling 30-day window. One consolidated pyarrow sweep; `pkg_python` regex-filtered before
aggregation.

**Phase K token bucket.** `_RateLimitedScheduler`, single worker, 3.0 RPS default — roughly a
3× safety margin, host-agnostic across GitHub / GitLab / Codeberg. `PHASE_K_AGGRESSIVE=1`
raises to 8 workers; **any non-`1` value does not re-arm the burst**. A 403 writes
`upstream_versions.last_error` and re-picks via TTL bypass. `_parse_retry_after` lives in CFA,
not `_http.py`.

**Phase P two-layer cost gate.** A dry-run cap *and* `maximum_bytes_billed`, plus
`PHASE_P_JOB_TIMEOUT_MS`. Bounds are **literal TIMESTAMP values, not `_PARTITIONDATE`** — the
spec prose said otherwise and the spec prose was wrong; follow the code. `PHASE_P_ENABLED=1` is
admin-only and never a default schedule. Guarded by `test_no_thirty_gb_lie`.

**Single-write-path (R, S).** Enrichment and scoring share exactly one write path with the
add-handoff surface. Two writers to one dataset is the failure the seven-pipeline rule exists
to prevent, and R/S are where it was historically tempting.

## Additive riders — the three new signals

These were **not** part of the parity scope and are never parity-gated; a parity delay does not
block them. Their correctness is held instead by one fixture per measured failure mode.

| Signal | Story | Pipeline | What it measures | Fixture-pinned failure mode |
|---|---|---|---|---|
| **Basilisk conda-native advisories** | B8 | `vulnerability` | Advisories matched **by package name**, so an advisory tagged with a foreign ecosystem still matches its conda package | `fix_available` is **tri-state**; unknown never collapses to false |
| **Release-to-availability velocity** | B9 | `pypi_intelligence` ⋈ `core` | Packaging lag from the existing join — **no new fetch** | Qualifies only on upstream releases within 90 days; computed against **first availability** (minimum per-build repodata timestamp), never latest upload, so a same-version rebuild cannot shift the measurement |
| **Migration readiness** | B10 | `core` | Four-way split driven by upstream `status/` category lists | `version_status.v2.json` is **deliberately excluded**; `not-in-tracker` membership is always labeled **inferred**, never reported as confirmed tracker status |

The 90-day window on velocity is the guard against the false "half the channel is behind"
reading. Both of its failure modes are fixture-pinned because both were *observed*, not
imagined.

No surface conflates version currency with security currency. They are different questions with
different clocks.

## What is not an Atlas signal

**Atlas measures; Warden judges.** An upstream-maintenance signal of the OpenSSF-Scorecard class
is a **Warden axis**, never an Atlas gate. Atlas may join and expose it as a feed, but the
verdict is not Atlas's to render — the Charter's *the hand that builds is never the gate that
judges*, applied to signals. This rules out scoring or thresholding any maintenance metric here.

New external data sources beyond the committed set are out of scope. Candidate feeds are
recorded, never committed; promotion requires measured evidence becoming a requirement and a
story. Do not ship more sources to look busier.
