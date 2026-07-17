# Full HTTP Layer and Migration Boundary

Citations at commit `b18cbb5`. `HT` = `.claude/skills/conda-forge-expert/scripts/_http.py`;
spec = `docs/specs/cfe-atlas-datapipeline-kedro-migration.md`.

## Contents

- [The 19 resolve_*_urls helpers](#the-19-resolve__urls-helpers)
- [Atomic write helpers](#atomic-write-helpers)
- [Auth chain and the FR-1 JFrog defect](#auth-chain-and-the-fr-1-jfrog-defect)
- [Retry / resumable-fetch helpers](#retry--resumable-fetch-helpers)
- [Migration boundary (spec 3.4)](#migration-boundary-spec-34)
- [Not modeled](#not-modeled)

## The 19 resolve_*_urls helpers

Count verified exactly 19 at commit b18cbb5 (spec:178–184 confirms; FR-19's 20th
helper `resolve_basilisk_urls` is PLANNED, not present — spec:182). Pattern:
HOST_BASE_URL env first, public default last (e.g. `CONDA_FORGE_BASE_URL` HT:424;
dynamic per-channel `{CHANNEL}_BASE_URL` HT:740). Supporting: `_dedup_strip` HT:396,
`read_pixi_config` HT:368 (project → user → system, HT:380–384), defaults HT:291–360.

| # | Function | def |
|---|----------|-----|
| 1 | `resolve_conda_forge_urls(config=None)` | [SRC:HT:L410] |
| 2 | `resolve_pypi_simple_urls(config=None)` | L446 |
| 3 | `resolve_pypi_json_urls(package_name, version=None, config=None)` | L473 |
| 4 | `resolve_github_urls(repo, path="")` | L507 |
| 5 | `resolve_github_raw_urls(repo, ref, path)` | L524 |
| 6 | `resolve_npm_urls(package_name)` | L541 |
| 7 | `resolve_cran_urls(name)` | L566 |
| 8 | `resolve_cpan_urls(dist)` | L577 |
| 9 | `resolve_luarocks_urls(name)` | L589 |
| 10 | `resolve_crates_urls(name)` | L601 |
| 11 | `resolve_rubygems_urls(name)` | L614 |
| 12 | `resolve_maven_urls(query_path)` | L627 |
| 13 | `resolve_nuget_urls(package_name)` | L640 |
| 14 | `resolve_endoflife_urls(product)` | L653 (docstring directs call sites to `skip_auth=True` L658–659) |
| 15 | `resolve_github_api_urls(path_suffix="")` | L667 |
| 16 | `resolve_gitlab_api_urls(path_suffix="")` | L687 |
| 17 | `resolve_codeberg_api_urls(path_suffix="")` | L703 |
| 18 | `resolve_anaconda_channel_urls(channel, subdir="noarch", filename="current_repodata.json")` | L719 |
| 19 | `resolve_s3_parquet_urls(month)` | L748 |

## Atomic write helpers

- `atomic_writer(path, mode="w", **kwargs)` — `@contextlib.contextmanager` L91, def
  [SRC:HT:L92]: `.tmp` sibling L116, flush+fsync L120–127, `os.replace` L129;
  on exception the tmp is unlinked, target untouched L130–139; parent dir created L114.
- `atomic_write_bytes(path, data)` [SRC:HT:L142]; `atomic_write_text(path, text, encoding="utf-8")` [SRC:HT:L148].

## Auth chain and the FR-1 JFrog defect

Chain (module docstring HT:13–18; `auth_headers_for` [SRC:HT:L186]):
(1) `JFROG_API_KEY` → `X-JFrog-Art-Api` header HT:214–215;
(2) `JFROG_USERNAME`+`JFROG_PASSWORD` → Basic HT:216–218;
(3) github.com hosts → `GITHUB_TOKEN`/`GH_TOKEN` Bearer HT:220–223, else netrc Basic HT:224–227;
(4) generic netrc fallback HT:228–233. `skip_auth=True` → `{}` HT:208–209.
Support: `inject_ssl_truststore` L49 (guard L46, applied per-request by `open_url`
L263 at L270), `netrc_credentials` L156 (honors `$NETRC` L167), `make_request` L238
(caller `Authorization` wins via setdefault L256–259).

**FR-1 DEFECT (fix-not-port):** the JFrog branch is evaluated FIRST and is NOT
host-conditional — with `JFROG_API_KEY` set, the Artifactory credential is attached
to EVERY outbound URL (pypi.org, api.github.com, crates.io, …): `host` computed
HT:211 but never consulted before the JFrog branch [SRC:HT:L213–218]. In-code
acknowledgement: `auth_headers_for` docstring HT:200–206 ("the documented
cross-resolver leak — skip_auth is the call-site opt-out until a host allowlist
lands"). Spec characterization: spec:188–194 ("FR-1 fixes rather than ports …
documented workaround today is `unset JFROG_API_KEY`"), FR-1 definition spec:586–588
("API datasets scope credentials per destination host — fixing, not porting"),
cross-ref spec:1263. The migration FIXES this in the Kedro catalog; ports must NOT
reproduce the unconditional injection.

## Retry / resumable-fetch helpers

- `fetch_with_fallback(urls, ...)` [SRC:HT:L848]: 4xx (except 408/429) → next URL
  L886–888; 5xx/network → exponential `2 ** attempt` backoff L890–894 (un-jittered);
  RuntimeError on exhaustion L896–898.
- `fetch_to_file_resumable(target, urls, ...)` [SRC:HT:L903]: `.part` sibling +
  `Range: bytes=N-` resume L939–947; 206 append / 200 restart / 416
  discard-and-restart L960–1001; atomic `os.replace` finalize L989; backoff
  L1007–1011; primary case = 4 GB OSV all.zip (docstring L924–925).
- NOTE: `_parse_retry_after` + the Retry-After/±25%-jitter machinery live in
  `conda_forge_atlas.py:2668` (consumed L2732/L4121/L8184), NOT in _http.py.
- Debug logging `_log` L1020, gated on `CFE_DEBUG`/`CONDA_FORGE_EXPERT_DEBUG` L1022–1023.

## Migration boundary (spec 3.4)

Boundary rule verbatim: "This section fixes the scope boundary — anything not listed
in § 3.3 or here is out of the migration's universe." (spec:329–330). Three stores
"enter this migration's scope as external-refresh assets (§ 5.2, Story B5); the rest
stay outside" (spec:326–328).

**IN SCOPE — 3 separately-built local data stores** (table spec:335–339):

1. **AppThreat vdb** (`vdb/` + `vdb-cache/`, ~2.5 GB) — refreshed by `vdb-refresh`
   (vuln-db env); NVD/GHSA/OSV/npm/Snyk feeds; consumers Phases G/G' (read-only),
   detail-cf-atlas, inventory-channel, scan-project — spec:337.
2. **Offline OSV CVE store** (`cve/`) — `update-cve-db` → `cve_manager.py`; osv.dev
   GCS bucket; consumer vulnerability_scanner.py offline mode — spec:338.
3. **`pypi_conda_map.json` flat mapping cache** — `update-mapping-cache` →
   `mapping_manager.py`; parselmouth + conda-forge-metadata API; consumers
   name_resolver.py, recipe-generator.py, mapping_gap.py; independent of Phase C — spec:339.

Plus: bootstrap already orchestrates the first two alongside the atlas build; the
migrated pipeline must not regress below that coverage (spec:341–342).

**OUT OF SCOPE — declared-input classes** (spec:344–367):

- Static git-tracked seeds: `lts-registry.yaml`, `cwe_categories_seed.json`,
  `spdx.schema.json`, legacy mapping seeds, `config/skill-config.yaml` — spec:346–349.
- Recipe template trees (`templates/`, 14 language families; Phase S stores only the
  path string) — spec:350–352.
- Live authoring-time fetches: recipe-generator.py, dependency-checker.py,
  pr_artifacts.py, submit_pr.py + feedstock maintenance, npm/GitHub version checkers;
  pipeline snapshots are ADVISORY for submission gating (G66/G74/G78 corollary) — spec:353–364.
- User-supplied inputs: `recipes/` tree + manifests/locks/SBOMs/containers — spec:363–365.
- The skill knowledge base (SKILL.md, reference/, guides/) — "documentation, not data" — spec:366–367.

**Seed-freshness report nodes** (spec:369–397): the 4 report-only suggesters
(`lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap`) form the
Seed-Gaps Pipeline (§ 5.2 item 6, Story B6; table spec:380–386);
`mapping-gap` is the SOLE write-back exception (g10_spelling UPDATE) and stays in the
mapping / Phase-C layer (spec:376–378, 386, 388–390, 396–397).

## Not modeled

Answer "not modeled" (AD-19) for anything outside § 3.3 + § 3.4, including:

- `gemini_server.py` (explicitly outside FR-7's audit scope — spec:172–177).
- The 23 recipe-authoring MCP tools' internals (listed for count-completeness in
  `references/mcp-tools.md` but not part of the migration surface).
- `detail_cf_atlas.py` internals (only the two boundary pointers recorded:
  `_coerce_cvss_score` at :295, `fetch_vdb_data` reuse) — and every other read-side
  CLI module (staleness_report, whodepends, …): the spec counts them (28 read CLIs,
  spec:165–171) but this skill models the ORCHESTRATOR surface, not the read layer.
- The `recipes/` tree, BMAD/bmad-loop tooling, pixi task graph, Kedro target design
  (that is the migration's OUTPUT, not the legacy surface).
- Anything at a commit other than `b18cbb5` without live re-verification.
