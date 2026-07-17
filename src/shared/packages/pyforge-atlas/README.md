# pyforge-atlas

[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)

Kedro/Dagster/DuckDB data-pipeline migration of the `cf_atlas` orchestrator — the
`pyforge.atlas` PEP 420 namespace package living beside `pyforge.warden`. Atlas
**provides data** (feedstock/upstream intelligence produced by its pipelines);
Warden **uses that data** (as one input to its compliance axes) — the only code
edge between them points the other way: atlas optionally imports warden's
`ComplianceReport` schema/validators via the `pyforge-atlas[gate]` extra
(consumed at the Wave-F F4 gate node). No `warden -> atlas` import exists; both
tools stay independently installable.

**Status:** Story A1 scaffold — pixi build workspace member wiring (warden
mirror), Kedro skeleton, lean env, and the `kedro-test` gate. Pipelines land
wave-by-wave per
[`docs/specs/cfe-atlas-datapipeline-kedro-migration.md`](../../../../docs/specs/cfe-atlas-datapipeline-kedro-migration.md).

## Develop

Run from the repository root (the parent pixi workspace):

```bash
pixi run --frozen -e pyforge-atlas kedro-test            # Wave A gate: import smokes + Kedro namespace seam + layout
pixi run -e pyforge-atlas pyforge-atlas-build-conda      # conda pkg (.conda) via pixi-build-python -> dist-conda/
pixi run -e pyforge-atlas pyforge-atlas-build-dist       # wheel + sdist via hatchling -> dist/
pixi run -e pyforge-atlas pyforge-atlas-build            # all three artifacts
```

The `pyforge-atlas` environment is lean by design (`no-default-feature`): loop
worktrees materialize THIS env, never the fat `local-recipes` env. It carries
the built package plus its conda run-dependencies (`kedro`, `kedro-datasets`,
`kedro-dagster`), with `pyforge-warden` and the test tooling (`pytest`,
`hatchling`, `python-build`) added at feature level by the root pixi.toml —
warden is default-installed in-repo without becoming a hard run-dep of the
built conda artifact (the `[gate]` extra stays genuinely optional externally).

The Python package is the dotted namespace package `pyforge.atlas`
(`src/pyforge/atlas/`, **no** `src/pyforge/__init__.py`) — Kedro resolves it via
`[tool.kedro] package_name = "pyforge.atlas"`. `conf/local/` is gitignored;
`conf/base/catalog.yml` declares every API source + persisted output of the
seven pipelines (Story A2), with endpoint bases in `conf/base/globals.yml`
and per-dataset TTLs in `conf/base/parameters.yml`.

## Air-gapped / enterprise provisioning (AC-4)

Two routing layers cover everything this project fetches. Configure both when
running behind JFrog Artifactory or on an air-gapped network; neither requires
changes to committed files.

### 1. Solver layer — `.pixi/config.toml [pypi-config]`

`pixi install`/`pixi lock` (conda + the PyPI-exception deps) resolve **before**
any project code runs, so they are routed by pixi's own config, not by code.
Follow **`docs/enterprise-deployment.md` § 4** (single source of truth) — it
covers the JFrog PyPI index (`pypi-config.index-url` /
`extra-index-urls`), corporate CA roots (`tls-root-certs = "native"`),
disabling sharded repodata against JFrog remotes, and why hashed
`files.pythonhosted.org` URLs bypass the standard `pypi.org` proxy (§ 3).

```bash
cp docs/pixi-config-jfrog.example.toml .pixi/config.toml   # from the repo root
$EDITOR .pixi/config.toml                                  # set JFrog URL + auth
```

### 2. Runtime layer — `_http.py`-style `resolve_*_urls` overrides

At runtime the pipeline follows the conda-forge-expert convention (spine
AD-2/AD-13): every external host is resolved through a `resolve_<host>_urls()`
chain that consults a `<HOST>_BASE_URL` environment variable first (e.g.
`CONDA_FORGE_BASE_URL`, `S3_PARQUET_BASE_URL`), falling back to the public
host; truststore + JFrog/GitHub/`.netrc` auth are injected per request. Set the
`*_BASE_URL` vars to your internal mirrors — env vars only, never committed
config. Reference implementation:
`.claude/skills/conda-forge-expert/scripts/_http.py` and
`docs/enterprise-deployment.md` § 2/§ 5.

Since Story A2 the convention is **catalog-level** (the `resolve_*_urls`
successor): `conf/base/globals.yml` declares every override point as
`${env_or:<HOST>_BASE_URL,<public-default>}` — the 20 `endpoint_bases`
(19 live helpers + the reserved `BASILISK_BASE_URL`), the `extra_overrides`
(`ANACONDA_API_BASE_URL`, `OSV_VULNS_BUCKET_URL`, `BIGQUERY_BASE_URL`), the
three vulnerability `fetcher_urls`, and the store/seed `paths`. Catalog
entries reference `${globals:...}` and never hardcode a host; an explicit
env var always beats the public default (`env_or` resolver registered in
`src/pyforge/atlas/settings.py`). `kedro-catalog-check` count-asserts the
override surface.

### 3. Credential layer — per-host keys in `conf/local/credentials.yml` (Story A2)

Credentials attach **per destination host only** (FR-1/AD-2 — this fixes,
never ports, the legacy `_http.py` global JFrog-header injection; the
interim legacy workaround was `unset JFROG_API_KEY`). The gitignored
`conf/local/credentials.yml` holds per-host keys, each referenced by
exactly the dataset(s) whose host needs it:

| Key | Attached to | Environment source |
|---|---|---|
| `github_token` | `vcs_github_api_raw` only | `GITHUB_TOKEN` / `GH_TOKEN` |
| `bigquery_adc` | `pypi_bigquery_downloads_raw` only (admin/attended-only, NFR-2) | `GOOGLE_APPLICATION_CREDENTIALS` (ADC) |
| `jfrog` | ONLY datasets whose endpoint-base actually resolves to an Artifactory host — with the shipped public defaults, none | `JFROG_API_KEY` or `JFROG_USERNAME`+`JFROG_PASSWORD` |

`netrc` remains a per-host runtime fallback, never catalog config. Nothing
credential-bearing is ever committed (`conf/local/**` + `conf/**/*credentials*`
are gitignored; the per-host key convention is documented here instead of a
tracked example file precisely because of that ignore pattern).
`kedro-catalog-check`'s credential-scoping test enforces the allowlist —
including that a JFrog key is never reachable from a non-JFrog host entry.
Credentialed runs are attended-only (NFR-2); the gate itself uses stub
credentials and never touches a live endpoint.

## Task inventory

| Task (root workspace) | What it does |
|---|---|
| `kedro-test` | Wave A deterministic gate (AD-11): `pytest src/shared/packages/pyforge-atlas/tests -q` — `pyforge.atlas` + `pyforge.warden` + `kedro_dagster` import smokes, the Kedro bootstrap/session seam on the dotted package, scaffold-layout invariants (also collects `tests/catalog/`) |
| `kedro-catalog-check` | Wave A gate 2 (Story A2, AD-11): `pytest src/shared/packages/pyforge-atlas/tests/catalog -q` — offline catalog resolution w/ stub credentials, no-inline-IO + AD-1 meta-tests, naming/layer/TTL/path conventions, 20 override points (+`ANACONDA_API_BASE_URL` extra), per-host credential scoping |
| `pyforge-atlas-build-conda` | conda package via `pixi build` (pixi-build-python wraps the hatchling wheel) |
| `pyforge-atlas-build-dist` | wheel + sdist via `python -m build --no-isolation` |
| `pyforge-atlas-build` | both of the above |
