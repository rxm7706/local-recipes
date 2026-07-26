---
doc_type: deployment-guide
project_name: local-recipes
date: 2026-07-25
source_pin: 'conda-forge-expert v8.79.1'
---

# Deployment Guide

> **Re-grounded 2026-07-25** (source_pin → v8.79.1). **Headline corrections:** the repo has **15 pixi environments / 17 features**, not 9 (9 factory + 6 `no-default-feature` product envs — see `development-guide.md` § Environments); every `docs/…` path in this guide was wrong and now points at `docs/reference/…`; and the guide previously never said **what actually deploys**. It does now: exactly one thing — the **Guildhall** dashboard to GitHub Pages at `https://rxm7706.github.io/local-recipes/`. New in this pass: § *CI / CD Considerations* now enumerates all **12 active workflows** (+1 disabled), documents the **two always-on staged-recipes-linter gates** (`maintenance` label for anything outside `recipes/`; the **ungated** `environment.yaml`↔`pixi.toml` sync check), and records that `create_feedstocks.yml` is hard-gated to `conda-forge/staged-recipes` and is therefore a **permanent no-op on this fork** — **no package or feedstock is published from this repo by CI**. Re-verified **unchanged and still accurate**: the `_http.py` SSL + auth chain, the `<HOST>_BASE_URL` mirror-routing convention, the mirror-infrastructure checklist, the `vuln-db` / `files.pythonhosted.org` failure mode, and — prominently — **the JFROG_API_KEY cross-host leak, which is still unfixed**. Live facts: `pixi run --frozen -e local-recipes bmad-groundtruth` (schema **v29**, **46 MCP tools**, **22 executable atlas phases** — 23 cataloged, **G106**, **15 pixi envs**).


How to deploy and operate `local-recipes` in enterprise, air-gapped, and JFrog Artifactory environments. This guide consolidates `docs/reference/enterprise-deployment.md` with the deployment-relevant rules from `project-context.md` and the integration architecture's auth chain.

For interactive dev setup, see `development-guide.md`. For end-to-end source provenance, see `docs/reference/enterprise-deployment.md` (this guide is the planning view; that file is the operational reference).

---

## What actually deploys

Read this before the rest of the guide — it reframes everything below.

**`local-recipes` is not a service.** It is a packaging factory plus a set of local tools. "Deployment"
here almost always means *installing and configuring the factory on a machine or CI agent*, not
shipping a running system. Verified 2026-07-25:

| Thing | Deploys? | Detail |
|---|---|---|
| **Guildhall dashboard** (`docs/dashboard/`) | **Yes — the only one** | GitHub Pages, `https://rxm7706.github.io/local-recipes/`. See § GitHub Pages below |
| Feedstocks / conda packages | **No** | `create_feedstocks.yml` is hard-gated `if: github.repository == 'conda-forge/staged-recipes'` — a permanent no-op on this fork. `publish`, `publish-range`, `submit-pr` are developer-invoked, never CI-invoked |
| Containers | **No** | The only tracked `Dockerfile` is a **test fixture** under `.claude/skills/conda-forge-expert/tests/fixtures/manifest_samples/` |
| Kubernetes | **No** | Likewise the only tracked k8s manifest is a test fixture. There is **no `Chart.yaml` anywhere** in the repo |
| `helm/lasuite-docs/values.yaml` | **No** | A values override with **no chart and no apply step** — an air-gapped La Suite Docs design artifact, described in `docs/reference/enterprise-deployment.md`. Unreferenced by any in-repo code path |
| `conf/base/knowledge.yml` | **No** | Config for the `sentinel` wiki agent (`src/sentinel/`, the 14 `wiki-*` tasks). Also unreferenced by any deploy path |

Treat `helm/` and `conf/` as **design/intent artifacts**, not deployable units. Nothing in this repo
applies them.

---

## Deployment Modes

Three operational modes, listed by network constraint:

| Mode | Network | Setup needed |
|---|---|---|
| **Open internet** | All public hosts reachable | None — pixi resolves from conda-forge + pypi.org directly |
| **JFrog-proxied** | Public hosts via JFrog Artifactory remote repositories | `.pixi/config.toml` + per-host `*_BASE_URL` env vars |
| **Fully air-gapped** | No public hosts; only internal mirrors | All of JFrog-proxied + internal CVE/vdb mirrors + S3 parquet mirror |

**Most enterprise deployments are JFrog-proxied.** Fully air-gapped is the strictest case and the design target — workflows that fail air-gapped will also fail in JFrog-proxied environments where coverage is incomplete.

### Which environments you actually have to provision

The repo defines **15 pixi environments across 17 features** — not the 9 an earlier revision of this
guide assumed. Provisioning cost differs sharply between the two families:

- **Factory envs (9)** — `linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`,
  **`local-recipes`** (the default, and the fat one), `vuln-db`, `gcloud`. `local-recipes` composes
  `python + build + grayskull + conda-smithy + local-recipes`; it is the env an air-gapped mirror
  must fully cover.
- **Product envs (6)** — `pyforge-warden`, `pyforge-atlas`, `pyforge-doctor`, `pyforge-scribe`,
  `pyforge-herald`, `bmad-ui` — all `no-default-feature = true`, so each excludes the fat default
  dep set (`python 3.14.*`, `pixi`, `conda`, `pip`, `uv`) and carries only its own built package +
  run-deps + pytest. These are cheap; that is deliberate, so a per-story worktree can materialize
  one.

Two provisioning notes that bite in restricted networks:

1. **`build` is the env the CI linter exports.** The `environment.yaml`↔`pixi.toml` sync gate runs
   `pixi project export conda-environment -e build`. Whatever else you trim, keep `build`
   resolvable.
2. **`bmad-ui` is linux-64 only and declares its own channels — including the local path
   `./build_artifacts/linux64`.** It consumes locally-built `bmad-dashboard` /
   `mybmad-dashboard` packages. `build_artifacts/` is gitignored but is a **real, referenced conda
   channel**; a recent commit had to scrub a worktree-absolute `build_artifacts` channel path that
   leaked into `pixi.lock` ("lock poisoning"). Never let an unfrozen re-solve in a worktree rewrite
   the lock — see `development-guide.md` § `--frozen`.

Also local-only, and therefore **not** something a deployment mirrors: `conda_build_config.yaml`
(1,103 lines — a local copy of conda-forge-pinning so local rattler-build / conda-build can resolve
compilers and `stdlib("c")` outside CI) and `.ci_support/local_testing_overrides.yaml` (explicitly
"should NOT be used in real CI"). `SDKs/` is gitignored and holds the local `MacOSX11.0.sdk` used by
`build-local-setup-sdk` / `OSX_SDK_DIR`.

---

## Configuration Surfaces

Three places that need configuration for non-open-internet deployments:

### 1. `.pixi/config.toml` (per-user, gitignored)

The primary configuration file for pixi-level network routing. Example for JFrog:

```toml
# .pixi/config.toml (gitignored)
default-channels = [
  "https://artifactory.company.com/artifactory/api/conda/conda-forge-virtual"
]

[mirrors]
"https://conda.anaconda.org/conda-forge" = [
  "https://artifactory.company.com/artifactory/api/conda/conda-forge-virtual"
]

[pypi-config]
index-url = "https://artifactory.company.com/artifactory/api/pypi/pypi-virtual/simple"

# Disable sharded repodata (most JFrog conda remote repos don't proxy it correctly):
[repodata-config]
disable-sharded = true

# Use OS-native trust store for corporate CAs:
tls-root-certs = "native"
```

A sample template lives at **`docs/reference/pixi-config-jfrog.example.toml`** (the path moved — an earlier revision of this guide cited `docs/pixi-config-jfrog.example.toml`, which does not exist). Copy to `.pixi/config.toml` and edit hosts.

A skill-level enterprise template also exists at
`.claude/skills/conda-forge-expert/config/enterprise-config.yaml.template`. The shipped
`.claude/skills/conda-forge-expert/config/skill-config.yaml` has
`features.enable_enterprise: false` and `features.enable_airgapped: false` — enterprise behaviour is
**runtime-driven by env vars**, never by committed config.

### 2. Environment variables (per-shell)

#### 2a. Authentication

All of it lives in one file: **`.claude/skills/conda-forge-expert/scripts/_http.py`** (1,024 LOC).

**SSL trust chain**, applied once per process by `inject_ssl_truststore()`:
`REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` → `truststore.inject_into_ssl()` (system OS anchors) →
certifi default.

**Auth chain**, resolved per request by `auth_headers_for(url)` — first match wins:

| # | Condition | Header emitted |
|---|---|---|
| 1 | `JFROG_API_KEY` set | `X-JFrog-Art-Api` — **★ unconditional, every host. See the leak section below.** |
| 2 | `JFROG_USERNAME` + `JFROG_PASSWORD` | `Authorization: Basic` |
| 3 | host is `github.com` / `api.github.com` and `GITHUB_TOKEN` or `GH_TOKEN` set | `Authorization: Bearer` |
| 3b | same host, no token, but a `~/.netrc` (or `$NETRC`) entry exists | `Authorization: Basic` |
| 4 | any other host with a `~/.netrc` entry | `Authorization: Basic` (covers Artifactory, Nexus, GitLab, …) |
| 5 | otherwise | unauthenticated |

`make_request()` and the `requests` path both delegate to `auth_headers_for`, so the semantics are
identical across the two HTTP paths.

| Variable | Used by | Purpose |
|---|---|---|
| `JFROG_API_KEY` | `_http.py` | `X-JFrog-Art-Api` header for JFrog. **★ Leaks cross-host — see below.** |
| `JFROG_USERNAME` + `JFROG_PASSWORD` | `_http.py` | Basic-auth alternative to `JFROG_API_KEY`. |
| `GITHUB_TOKEN` / `GH_TOKEN` | `_http.py`, gh CLI | GitHub authentication (Phase K + N + submit_pr). |
| `NETRC` | `_http.py` | Non-default `.netrc` path. |
| `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` | `_http.py` | Explicit enterprise CA bundle. |

#### 2b. Upstream-host redirects (enterprise routing)

Every external host the atlas talks to is redirectable via a `<HOST>_BASE_URL` env var. Public defaults apply when unset; trailing slashes are stripped automatically. v7.8.0 + v7.8.1 added 15 new resolvers, completing air-gap parity across all upstreams the skill consults.

**Shape of the surface (verified 2026-07-25):** `_http.py` defines **18 explicit resolvers**, plus a
**generic per-channel derivation** — `f"{channel.upper().replace('-','_')}_BASE_URL"` — which yields
`BIOCONDA_BASE_URL`, `PYTORCH_BASE_URL`, and `ROBOSTACK_STAGING_BASE_URL` for the named alternate
channels, for **21** mirror-routing variables in total. Two more live outside `_http.py`:
`ANACONDA_API_BASE_URL` (in `conda_forge_atlas.py`) and the `OSV_*` pair (in `cve_manager.py` /
`vulnerability_scanner.py`). All are listed below.

| Variable | Default host | Used by |
|---|---|---|
| `CONDA_FORGE_BASE_URL` | `https://conda.anaconda.org/conda-forge` | Phase B current_repodata.json |
| `PYPI_BASE_URL` | `https://pypi.org/simple` | Phase D, mapping refresh, recipe-generator |
| `PYPI_JSON_BASE_URL` | `https://pypi.org` | recipe-generator PyPI JSON metadata |
| `S3_PARQUET_BASE_URL` | `https://anaconda-package-data.s3.amazonaws.com` | Phase F S3 path |
| `ANACONDA_API_BASE_URL` (legacy alias `ANACONDA_API_BASE`) | `https://api.anaconda.org` | Phase F API path; `detail_cf_atlas`. **Read in `conda_forge_atlas.py`, not `_http.py`** |
| `GITHUB_BASE_URL` | `https://github.com` | Archive / tarball URLs (cf-graph download, etc.) |
| `GITHUB_RAW_BASE_URL` | `https://raw.githubusercontent.com` | Raw-content URLs |
| `GITHUB_API_BASE_URL` | `https://api.github.com` | Phase K REST + GraphQL. **One var covers GHES** — set to `https://<ghes>/api`. |
| `GITLAB_API_BASE_URL` | `https://gitlab.com/api/v4` | Phase K REST (self-hosted GitLab CE/EE). |
| `CODEBERG_API_BASE_URL` | `https://codeberg.org/api/v1` | Phase K REST (Forgejo, self-hosted Gitea). |
| `NPM_BASE_URL` (also honors npm CLI's `npm_config_registry`) | `https://registry.npmjs.org` | Phase L npm; `npm_updater`; `recipe-generator npm`. |
| `CRAN_BASE_URL` | `https://crandb.r-pkg.org` | Phase L CRAN. |
| `CPAN_BASE_URL` | `https://fastapi.metacpan.org` | Phase L CPAN. |
| `LUAROCKS_BASE_URL` | `https://luarocks.org` | Phase L LuaRocks. |
| `CRATES_BASE_URL` | `https://crates.io` | Phase L crates.io. |
| `RUBYGEMS_BASE_URL` | `https://rubygems.org` | Phase L RubyGems. |
| `MAVEN_BASE_URL` | `https://search.maven.org` | Phase L Maven Central. |
| `NUGET_BASE_URL` | `https://api.nuget.org` | Phase L NuGet. |
| `ENDOFLIFE_BASE_URL` | `https://endoflife.date` | LTS / end-of-life signals (`lts-registry-gap`, `library-futures`, `recommend-2027`). |
| `BIOCONDA_BASE_URL`, `PYTORCH_BASE_URL`, `ROBOSTACK_STAGING_BASE_URL` | the respective `conda.anaconda.org/<channel>` | **Derived generically**, not hard-coded: the channel-resolver builds `<CHANNEL>_BASE_URL` by uppercasing the channel name and replacing `-` with `_`. Any alternate channel gets a var by the same rule. |
| `OSV_API_BASE_URL` | `https://api.osv.dev` | `vulnerability_scanner` (OSV querybatch API). **Read in `vulnerability_scanner.py`, not `_http.py`** |
| `OSV_VULNS_BUCKET_URL` | `https://osv-vulnerabilities.storage.googleapis.com` | `cve_manager` (OSV `<eco>/all.zip` bulk feed). **Read in `cve_manager.py`, not `_http.py`** |
| `PHASE_P_CH_BASE_URL` | (unset) | Phase P ClickHouse endpoint. |

#### 2c. Phase tunables (operational)

| Variable | Default | Purpose |
|---|---|---|
| `PHASE_F_SOURCE` | `auto` | `auto` / `anaconda-api` / `s3-parquet`. Large orgs should use `s3-parquet` to skip api.anaconda.org entirely. |
| `PHASE_F_CONCURRENCY` | **3** (was 8 pre-v7.8.0) | api.anaconda.org per-IP secondary rate limit reliably tripped at 8 workers. |
| `PHASE_H_SOURCE` | `pypi-json` | `pypi-json` / `cf-graph`. `cf-graph` is the safer choice for cold-start backfills. |
| `PHASE_H_CONCURRENCY` | **3** (was 8 pre-v7.8.1) | pypi.org has a documented ~30 req/s per-IP ceiling. |
| `PHASE_F_S3_MONTHS` | unlimited | Trailing-N-months cap for the S3 parquet path. |
| `PHASE_GP_ENABLED` | unset | `1` to enable per-version vulnerability scoring. |
| `PHASE_K_GRAPHQL_DISABLED` | unset | `1` to fall back to REST fanout for GitHub (debug/recovery only). |
| `PHASE_K_GRAPHQL_BATCH_SIZE` | `100` | Repos per GraphQL POST. Stay under ~150 to respect GitHub's node-complexity ceiling. |
| `PHASE_L_CONCURRENCY` | per-host defaults | Legacy uniform cap. Overridden per-source via `PHASE_L_CONCURRENCY_<SOURCE>`. |
| `PHASE_L_CONCURRENCY_<SOURCE>` | npm=4, nuget=4, cran=cpan=luarocks=maven=2, crates=1, rubygems=1 | Per-registry concurrency override. Defaults reflect documented per-host rate limits. |
| `ATLAS_CFGRAPH_TTL_DAYS` | `1.0` | Days the cached cf-graph tarball stays fresh. Weekly-cron users should set to `7` to skip the ~150 MB re-download. Shared across Phases E + J + M. |
| `VDB_HOME` | (auto-set by `vuln-db` env) | AppThreat vdb location. |
| `BOOTSTRAP_<STEP>_TIMEOUT` | sized for cold `--fresh` | Per-step timeout in seconds. |
| `GEMINI_API_KEY` | unset | If the Gemini bridge is used. |

**Setting `*_BASE_URL` env vars**: typical pattern is a per-user `~/.bashrc` / `~/.zshrc` block, OR a per-directory `.envrc` file with `direnv`, OR exported in the pixi env's activation script via `[feature.<env>.activation.env]`.

> **Engineering rule book**: phase-engineering patterns (per-host rate limits, GraphQL batching, Retry-After + jitter, per-registry concurrency, atomic writes, incremental commits + idempotent SQL, streaming tarfiles, page-level checkpoints, `<HOST>_BASE_URL` routing convention) are documented in `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md`. Consult before authoring or refactoring a phase.

### 3. Internal mirror infrastructure (JFrog admin domain)

For full air-gap, you need:

- **conda-forge mirror**: JFrog "Conda Remote Repository" pointing at `https://conda.anaconda.org/conda-forge` — proxies channel data
- **PyPI mirror**: JFrog "PyPI Remote Repository" pointing at `https://pypi.org/simple/` — proxies PyPI Simple API
- **`files.pythonhosted.org` mirror** (uncommon but required for many sdist URLs): JFrog "PyPI Remote Repository" pointing at `https://files.pythonhosted.org/` — see `docs/reference/enterprise-deployment.md` § 3 for why
- **anaconda.org API mirror** (optional, for Phase F API path): JFrog "Generic Remote Repository" pointing at `https://api.anaconda.org/`
- **S3 parquet mirror** (recommended, for Phase F S3 path): JFrog generic repository or internal S3-compatible store seeded from `s3://anaconda-package-data/`
- **GitHub API mirror** (optional, for self-hosted GHES): point `GITHUB_API_BASE_URL` at `https://<ghes>/api`. Covers both REST (Phase K REST tail) and GraphQL (Phase K batched + Phase N + Phase E5).
- **GitLab API mirror** (optional, for self-hosted GitLab): point `GITLAB_API_BASE_URL` at `https://<your-gitlab>/api/v4`. Layout is identical across CE/EE.
- **Codeberg/Gitea API mirror** (optional, for self-hosted Gitea or Forgejo): point `CODEBERG_API_BASE_URL` at `https://<your-gitea>/api/v1`.
- **Phase L registry mirrors** (optional, one per registry your recipes touch): JFrog Remote Repository for each of npm / CRAN / CPAN / LuaRocks / crates / RubyGems / Maven Central / NuGet. Each has its own `<HOST>_BASE_URL` env var. Most enterprise atlases need at most 2-3 of these.
- **OSV API mirror** (optional, for vulnerability scanning): point `OSV_API_BASE_URL` at an internal mirror of `https://api.osv.dev`.
- **OSV bulk-feed mirror** (recommended, for CVE database refresh): point `OSV_VULNS_BUCKET_URL` at a mirror of `https://osv-vulnerabilities.storage.googleapis.com`. The PyPI `all.zip` is ~4 GB; `cve_manager` now streams + resumes (v7.8.1), so a dropped connection at 95% no longer restarts from 0.
- **CVE feed mirror** (NVD, GHSA, OSV): internal copy refreshed by your security team
- **AppThreat vdb mirror**: internal copy of the vdb tarball

The skill's `_http.py` will auto-route to each via the corresponding `*_BASE_URL` env var. No code changes required.

See `docs/reference/enterprise-deployment.md` § 1-5 for JFrog REST API examples and full setup.

---

## The JFROG_API_KEY Cross-Host Leak (Critical Constraint)

> ★ **When `JFROG_API_KEY` is set in the environment, `_http.py` attaches the `X-JFrog-Art-Api` header to EVERY outbound HTTP request, regardless of destination host.**

**Status 2026-07-25: STILL UNRESOLVED.** Re-verified against
`.claude/skills/conda-forge-expert/scripts/_http.py` — `auth_headers_for()` step 1 is an
unconditional `if os.environ.get("JFROG_API_KEY"):` that runs before any host inspection. The
file's own docstring names it: *"The unconditional JFROG_API_KEY injection in step 1 above is the
documented cross-resolver leak."*

This is the single most important security constraint in the deployment layer. It affects all four parts because all four route their HTTP through `_http.py` (Part 1's `scripts/_http.py`).

### Partial mitigation that now exists in code

`auth_headers_for(url, skip_auth=...)` and `make_request(url, skip_auth=...)` take a **`skip_auth=True`
opt-out** that returns an empty header dict without consulting any env var or netrc entry. It is
used at **8 callsites** today, for known-public endpoints (e.g. dev.azure.com's public conda-forge
feedstock-builds project).

This is a **per-callsite** escape hatch, not a fix: it is opt-in, it must be remembered at every new
callsite, and it defaults to the leaking behaviour. Treat the shell-level patterns below as the real
control.

**Contrast — the leak is fixed in the Kedro reimplementation, and not ported back.** pyforge-atlas's
`conf/base/catalog.yml` states it plainly: *"the legacy `_http.py` JFrog leak is FIXED, not ported:
no global credential injection exists; a JFrog key may only ever be attached to a dataset whose
endpoint-base resolves to an Artifactory host."* Per-dataset credentials, declared in the catalog,
no global injection. That is the shape the `_http.py` fix should take when someone does it.

### What leaks

A `JFROG_API_KEY` exported in a shell that runs:
- `submit_pr` / `prepare_pr` → leaks to `github.com` (PR submission)
- `generate_recipe_from_pypi` → leaks to `pypi.org` (recipe scaffolding)
- `update_recipe_from_github` → leaks to `api.github.com`
- `update_cve_database` → leaks to `nvd.nist.gov`, `osv.dev`, etc.
- `update_mapping_cache` → leaks to `pypi.org`
- `atlas-phase F` in `s3-parquet` or `auto` mode → leaks to AWS S3
- `atlas-phase K` → leaks to `api.github.com`
- `atlas-phase H` in `cf-graph` mode → leaks to `github.com`

### Mitigation patterns

**Pattern A — per-command subshell scoping** (recommended for one-offs):

```bash
( unset JFROG_API_KEY; pixi run -e local-recipes submit-pr <recipe> )
( unset JFROG_API_KEY; pixi run -e local-recipes generate-recipe -- <pkg> )
```

The parentheses spawn a subshell; the unset only affects that subshell; the rest of the parent shell keeps `JFROG_API_KEY` set for JFrog-only work.

**Pattern B — per-shell discipline**:

Maintain two separate terminal panes / tmux windows / sessions:
- **"JFrog-only" pane**: `JFROG_API_KEY` exported here. Only runs commands that hit JFrog mirrors (atlas refresh, `update-cve-db` if mirrored, recipe generation if PyPI fully proxied).
- **"External" pane**: `JFROG_API_KEY` unset. Runs commands that hit github.com (PR submission, autotick).

**Pattern C — direnv `.envrc` scoping**:

Use `direnv` to scope env vars to specific directories:

```bash
# In ~/projects/jfrog-work/.envrc:
export JFROG_API_KEY="<key>"
export CONDA_FORGE_BASE_URL="https://artifactory.company.com/..."

# In ~/projects/local-recipes/.envrc:
# (no JFROG_API_KEY here — scope is repo-wide for external operations)
```

`direnv` loads `.envrc` automatically when you `cd` into the directory.

**Pattern D — activation hook in `[feature.<env>.activation.env]`**:

```toml
# pixi.toml — risky if applied to the default env
[feature.atlas-jfrog.activation.env]
JFROG_API_KEY = "${JFROG_API_KEY}"  # pass-through from launching shell
CONDA_FORGE_BASE_URL = "https://artifactory.company.com/..."
```

Only export the key in envs that explicitly need it. Don't add it to `feature.local-recipes.activation.env` (the default env) — that would re-introduce the leak on every command.

### What does NOT work

- **Trying to teach `_http.py` to be host-aware**: this is the right long-term fix (deferred work; tracked in auto-memory `project_http_jfrog_unconditional_injection.md`). It requires explicit host allow-lists keyed against `JFROG_API_KEY` exposure. Not currently implemented — `skip_auth=True` is the interim per-callsite opt-out, not the allow-list.
- **Setting `*_BASE_URL` to redirect everything to JFrog**: covers PyPI / conda-forge / anaconda.org, but NOT github.com (no `GITHUB_BASE_URL` is meaningful for the actual `submit_pr` PR-open call — it ALWAYS hits `api.github.com`). The leak still happens.
- **Relying on JFrog logs to detect the leak**: the header is silently rejected by non-JFrog hosts. Detection requires audit at the source (`_http.py` `make_request` callsite).

### Documentation locations

- `docs/reference/enterprise-deployment.md` § 2 → "Cross-host credential leak" — operational reference with the subshell pattern + enumerated commands
- `_bmad-output/projects/local-recipes/project-context.md` § Air-Gapped/Enterprise — Critical Constraint with the unset-before-external-commands rule
- This doc § "Mitigation patterns" above
- Auto-memory `project_http_jfrog_unconditional_injection.md` — durable reminder

---

## Deployment Checklist

For a new air-gapped / JFrog-proxied deployment:

### Setup (one-time)

- [ ] Confirm JFrog has remote repositories for: conda-forge, pypi.org, files.pythonhosted.org (recommended), api.anaconda.org (optional)
- [ ] Set up corporate CA in OS trust store, or set `REQUESTS_CA_BUNDLE` env var, or pixi's `tls-root-certs = "native"`
- [ ] Author `.pixi/config.toml` from template at `docs/reference/pixi-config-jfrog.example.toml`
- [ ] Set up `*_BASE_URL` env vars in `~/.bashrc` / `.envrc` / pixi env activation (see table above)
- [ ] Bootstrap CVE database from internal mirror: `pixi run -e vuln-db update-cve-db`
- [ ] Bootstrap atlas: `pixi run bootstrap-data --fresh` (will take 30-45 min; uses your `*_BASE_URL` overrides)
- [ ] Validate: `pixi run health-check` (expects no public-host errors)
- [ ] Confirm the `build` env resolves — the CI linter exports `environment.yaml` from it
- [ ] Decide which of the 6 product envs you need; they are `no-default-feature` and cheap, but each still pulls its own run-deps
- [ ] **Do NOT** budget for `pixi run bmad-preflight` — that task is broken (`scripts/ensure-bmad-preflight.sh` does not exist)

### Per-session

- [ ] Confirm `JFROG_API_KEY` is set ONLY in JFrog-only shells (or use subshell scoping)
- [ ] Confirm the active BMAD project. In an interactive single-agent session, `scripts/bmad-switch --current`. **From any parallel agent or automated job, do not call `bmad-switch` at all** — the marker and the two `_bmad-output/{planning,implementation}-artifacts` symlinks are per-working-tree global state; address projects by physical path and pass `BMAD_ACTIVE_PROJECT=<slug>` per invocation
- [ ] Inside a bmad-loop worktree, every pixi command carries `--frozen` (an unfrozen re-solve panics `pixi-build-python` 0.8.3 and poisons `pixi.lock` with worktree-absolute `file://` channel paths)
- [ ] If running cron jobs, ensure each cron command is wrapped in a subshell that unsets `JFROG_API_KEY` if it hits external hosts

### Per-PR

- [ ] Touched anything outside `recipes/`? → `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`
- [ ] Touched `pixi.toml`? → `pixi project export conda-environment -e build > environment.yaml` and commit it (the `maintenance` label does **not** suppress this check)
- [ ] Opening by hand? → `gh pr create --repo rxm7706/local-recipes …`

### Periodic maintenance

- [ ] Weekly: `pixi run atlas-phase F` + `atlas-phase G` + `atlas-phase H` + `atlas-phase K`
- [ ] Weekly: `pixi run update-cve-db`
- [ ] Monthly: `pixi run bootstrap-data --resume`
- [ ] Quarterly: review skill CHANGELOG for new constraints; re-verify project-context.md drift pin
- [ ] After any out-of-band change to `recipes/`, `.claude/`, `pixi.toml`, or `docs/specs/`: `pixi run --frozen -e local-recipes bmad-drift-check`, then reconcile per `SYNC-RUNBOOK.md`

---

## Special: `vuln-db` Env in JFrog-Proxied Environments

The `vuln-db` env pulls `appthreat-vulnerability-db` from PyPI. On corporate networks, `pixi install -e vuln-db` can fail even when `pypi.org` itself is reachable through JFrog. Root cause: PyPI's Simple API returns wheel/sdist URLs at `files.pythonhosted.org/packages/<aa>/<bb>/<hash>/...`, and a standard JFrog "PyPI Remote Repository" proxies `pypi.org` but **not** `files.pythonhosted.org`.

### Fix

Configure `.pixi/config.toml` with `pypi-config.index-url` pointing at JFrog's PyPI Simple endpoint (which rewrites the URLs to flow through JFrog):

```toml
[pypi-config]
index-url = "https://USER:TOKEN@artifactory.company.com/artifactory/api/pypi/pypi-remote/simple"
# OR omit auth from URL and use authentication-override-file:
# index-url = "https://artifactory.company.com/artifactory/api/pypi/pypi-remote/simple"
# authentication-override-file = "/path/to/auth.json"
```

See `docs/reference/enterprise-deployment.md` § 4 for the full mechanism + diagnostic patterns.

### Verification

```bash
pixi install -e vuln-db -vvv 2>&1 | grep -E "files.pythonhosted|artifactory|401|403|404"
```

Look for `files.pythonhosted.org` connection timeouts → your `index-url` didn't take effect. Look for 401/403 → auth issue. Look for 404 on `appthreat-vulnerability-db` → JFrog allow-list excludes the package.

---

## CI / CD Considerations

### The two always-on PR gates (pre-empt these; don't wait for red CI)

`.github/workflows/staged-recipes-linter.yml` runs
`.github/workflows/scripts/linter.py` on every PR — `opened`, `synchronize`, `reopened`,
**`labeled`, `unlabeled`**. Two of its checks fire constantly on this fork:

**Gate 1 — anything outside `recipes/` requires the `maintenance` label.** The check is
`if "maintenance" not in labels:` → then any changed file not starting with `recipes/` (and any edit
to `recipes/example/meta.yaml` or `recipes/example-v1/recipe.yaml`) is a lint failure. Docs,
`.github/`, `_bmad-output/`, `src/`, `scripts/`, `pixi.toml`, dashboards — all of it.

```bash
gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance
```

The `labeled` / `unlabeled` triggers exist precisely so adding the label re-runs the job.

**Gate 2 — `environment.yaml` must match `pixi.toml`, and the label does NOT suppress it.** The
check sits *outside* the `maintenance` branch. It runs
`pixi project export conda-environment -e build`, compares it to `environment.yaml` with an exact
`.rstrip()` string comparison, and prints a unified diff on mismatch.

```bash
pixi project export conda-environment -e build > environment.yaml
```

Fix `main` directly whenever a `pixi.toml` dep change lands there. **Verified in sync 2026-07-25.**
Cosmetic artifact worth knowing before someone "cleans it up": the export emits `python` twice —
`>=3.14.6,3.14.*` from `feature.python` and `3.14.*` from the default `[dependencies]`. Both sides
of the comparison contain it, so the check passes; hand-editing `environment.yaml` to dedupe would
**break** it.

The linter's remaining checks: a recipe must live in its own subdirectory under `recipes/`; the
feedstock must not already exist (tried as `name`, `name.replace('-','_')`,
`name.replace('_','-')`, bioconda, plus a PyPI-name collision lookup against
`regro/cf-graph-countyfair`'s `name_mapping.yaml`); every listed maintainer must have commented or
be the PR author (exempt: `conda-forge/r`, `conda-forge/cuda`, and any `org/team` entry); only
`conda-forge/*` teams may be maintainers; and a hint fires when a multi-output recipe omits
`extra.feedstock-name`.

Also: `gh pr create` **must** carry `--repo rxm7706/local-recipes`. This repo is a fork of
`conda-forge/staged-recipes`, so `gh` otherwise defaults the base to `conda-forge:main`.

### The 12 active workflows (+1 disabled)

| Workflow | Trigger | Notes |
|---|---|---|
| `staged-recipes-linter.yml` | PR (incl. `labeled`/`unlabeled`) | The two gates above. Runs on `ubuntu-slim` via micromamba |
| `dashboard.yml` | push to `main`, daily cron, dispatch | **The only deploy.** See § GitHub Pages |
| `test-all.yml` | **`workflow_dispatch` only** | "to preserve GitHub Actions quota". Fans out to the three platform workflows via `workflow_call`; caps an `all` run at `head -20` changed recipes; excludes `example`, `example-new-recipe`, `broken-recipes` |
| `test-linux.yml` | `workflow_call` | Docker-based, incl. an aarch64 QEMU leg and a CUDA leg |
| `test-macos.yml` | `workflow_call` | `macos-15-large` (Intel) + `macos-14` (arm64) |
| `test-windows.yml` | `workflow_call` | `windows-2022`, `CONDA_BLD_PATH=D:\bld` |
| `create_feedstocks.yml` | — | **Hard-gated `if: github.repository == 'conda-forge/staged-recipes'` → permanent no-op on this fork** |
| `sync-pypi-mappings.yml` | schedule + on mapping change | Refreshes the PyPI↔conda name mapping |
| `linter_issue_comment.yml`, `correct_directory.yml`, `do_not_edit_example.yml`, `automate-review-labels.yml` | PR / issue events | Inherited staged-recipes review automation |
| `tokens.yml.notused` | — | **Disabled** (extension renamed) |

Platform test jobs branch on recipe type: `recipe.yaml` → **rattler-build**, `meta.yaml` →
**conda-build**. Recipe builds are therefore **not automatic on push** — a human dispatches
`test-all`.

**Consequence for deployment planning: no feedstock and no conda package is published from this
repo by CI.** `publish`, `publish-range`, `submit-pr`, `prepare-pr` are all developer-invoked pixi
tasks. If you need artifacts from a PR's CI, pull them with `pixi run pr-artifacts` (Azure DevOps
Build Artifacts REST API).

### Azure DevOps

`azure-pipelines.yml` is inherited from upstream staged-recipes but heavily trimmed (+8 / −69):

- **Branch builds are fully disabled** — `trigger.branches.exclude: ["*"]`.
- PRs to `main` are allowed (`pr: [main]`).
- `[skip ci]` / `[skip azp]` / `[ci skip]` / `[azp skip]` are honored by a `Check` stage that gates
  the `Build` stage.
- Upstream's `fast_finish` and `status` aggregation jobs were **deleted**.
- Templates remain under `.azure-pipelines/` (linux / osx / win).

> **Unverifiable from the repo:** whether an Azure DevOps project is actually attached to this fork.
> The YAML is present and syntactically live, but nothing in-repo proves a pipeline is registered.
> Confirm in the Azure DevOps org before relying on any Azure leg.

If you *do* run on-prem / air-gapped Azure DevOps:

1. **Self-hosted agents** must have pixi + Docker + corporate CA trust
2. **Pixi config**: the same `.pixi/config.toml` from above; usually shipped via a `.pixi/config.toml.template` in the repo and rendered by a pipeline step
3. **JFROG_API_KEY**: stored as an Azure DevOps secret variable; injected per-pipeline-step. Steps that touch external hosts (`submit-pr`) must NOT have it set — the leak above applies to CI exactly as it does to a laptop
4. **Build artifacts retention**: `azure.store_build_artifacts: true` in `conda-forge.yml` (per-recipe overrides under `recipes/<name>/conda-forge.yml`) makes failed-build artifacts downloadable for diagnosis

`.scripts/` (5 CI build drivers) and `.ci_support/{build_all,compute_build_graph}.py` are identical
to upstream — patch them only with a very good reason, since upstream sync will fight you.

For on-prem GitHub Enterprise, replicate `sync-pypi-mappings.yml` and `dashboard.yml` there; both
run against public GitHub by default.

---

## GitHub Pages — the one real deploy target

`.github/workflows/dashboard.yml` publishes the **Guildhall** program console (`docs/dashboard/`) to
GitHub Pages. Verified live 2026-07-25:

| Setting | Value |
|---|---|
| URL | `https://rxm7706.github.io/local-recipes/` |
| Build type | `workflow` (GitHub Actions, not the legacy branch builder) |
| Source | branch `main`, path `/` |
| Visibility | public, **HTTPS enforced** |
| CNAME | none |

Pipeline:

```
push:[main]  |  schedule: 17 6 * * *  |  workflow_dispatch
        ↓            concurrency: group=pages, cancel-in-progress=false
actions/checkout@v4 (fetch-depth: 0 — full history)
        ↓
actions/setup-python@v5 (3.12)
        ↓
python docs/dashboard/generate.py --source git
        ↓
actions/configure-pages@v5
        ↓
actions/upload-pages-artifact@v3 (path: docs/dashboard)
        ↓
actions/deploy-pages@v4
```

Two design decisions to preserve:

1. **It regenerates at deploy time and deliberately does NOT commit `data.js` back.** Committing the
   regenerated file would push to `main`, which would re-trigger this workflow — an infinite loop.
   The workflow comment says so explicitly.
2. **`--source git` only upgrades, never downgrades.** It derives DONE state from `main` commit
   subjects. The **committed `data.js` is the seed/floor** — it carries the hand-curated narrative
   plus in-flight and gated state that git history cannot derive. Refresh the seed deliberately with
   `pixi run dashboard-gen` (which reads the live per-project `sprint-status.yaml` files); never
   assume the deployed site can be reconstructed from `data.js` alone, or vice versa.

Permissions required by the job: `contents: read`, `pages: write`, `id-token: write`.

**Air-gapped note:** there is no air-gapped equivalent. The Guildhall is a public artifact. On an
internal GitHub Enterprise instance, replicate the workflow against that instance's Pages
equivalent, or serve `docs/dashboard/` as static files — it is a self-contained `index.html` +
`data.js`, no backend.

---

## Common Deployment Failure Modes

| Symptom | Root cause | Fix |
|---|---|---|
| `pixi install -e vuln-db` fails on `files.pythonhosted.org` | JFrog only proxies `pypi.org`, not `files.pythonhosted.org` | Use JFrog Simple index in `pypi-config.index-url` (see above) |
| `pixi run validate` fails: TLS / "unable to get local issuer certificate" | Corporate CA not trusted | Set `tls-root-certs = "native"` in `.pixi/config.toml` or `REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt` |
| `pixi run bootstrap-data` Phase F times out | `api.anaconda.org` unreachable | Set `PHASE_F_SOURCE=s3-parquet`; ensure `S3_PARQUET_BASE_URL` points at a mirror or AWS S3 is reachable |
| `pixi run bootstrap-data` Phase H hangs | Per-row pypi.org fan-out on cold start | Set `PHASE_H_SOURCE=cf-graph` (default on `--fresh`) |
| `update-cve-db` fails: NVD unreachable | NVD not mirrored | Ensure internal NVD mirror is set up; AppThreat vdb fetches from multiple sources |
| `submit-pr` returns "Authentication failed" + leaks JFrog header in audit log | `JFROG_API_KEY` set in a shell that hits github.com | Use subshell pattern: `( unset JFROG_API_KEY; pixi run submit-pr ... )` |
| `gh auth status` fails | `GITHUB_TOKEN` not set or expired | `gh auth login` or set `GITHUB_TOKEN` env var |
| Phase K rate-limited (`HTTP 403 secondary rate limit`) | GitHub burst fanout exceeded secondary throttle | Wait + retry with `--reset-ttl`; longer-term mitigation deferred |
| PR red: "Do not edit files outside of the `recipes/` directory" | Linter gate 1 | Add the `maintenance` label (`gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`) |
| PR red: "`environment.yaml` is out of sync with `pixi.toml`" **even with the `maintenance` label** | Linter gate 2 is ungated by design | `pixi project export conda-environment -e build > environment.yaml`, commit |
| `gh pr create` opened a PR against `conda-forge/staged-recipes` | This repo is a fork; `gh` defaults base to the upstream | Always pass `--repo rxm7706/local-recipes` |
| `pixi run bmad-preflight` → "No such file or directory" | The task invokes `bash scripts/ensure-bmad-preflight.sh`, which does not exist | Use `pixi run verify-env` + `bmad-groundtruth`. Fixing/removing the task is open work |
| `pixi run scan-project` / `inventory-channel` → task not found | Those tasks live only in the `vuln-db` env | `pixi run -e vuln-db <task>` |
| `pixi.lock` diff shows worktree-absolute `file://` channel paths | An unfrozen re-solve ran inside a bmad-loop worktree | Revert the lock; re-run with `--frozen`. Loop homes now root at `~/.bmad-loops/<slug>` to shorten the path |
| A feedstock never appeared after a merged recipe PR | `create_feedstocks.yml` is a no-op on this fork | Expected — this repo publishes nothing. Submit upstream via `pixi run submit-pr` |

---

## Rebuild Implications

If you're rebuilding `local-recipes` on a clean repo and deployment matters:

1. **Author `_http.py` first** — every other Part imports it. Include the truststore + JFrog + GitHub + .netrc chain AND the per-host base-URL override logic. **But do not reproduce the unconditional JFrog injection** — build the host allow-list in from day one. pyforge-atlas's Kedro catalog shows the target shape: per-dataset credentials, attached only where the endpoint-base resolves to an Artifactory host, no global injection.
2. **Document the `JFROG_API_KEY` cross-host leak in 3 places** (CLAUDE.md, project-context, `docs/reference/enterprise-deployment.md`) — repetition is intentional; agents and humans both need the warning at the surface they read first.
3. **Author `docs/reference/enterprise-deployment.md`** alongside the skill — without this, every new deployment will rediscover the JFrog gotchas the hard way.
4. **Provide `docs/reference/pixi-config-jfrog.example.toml`** as a copy-pasteable starter for `.pixi/config.toml`.
5. **Make the `vuln-db` env separate** from `local-recipes` — don't bundle AppThreat into the default env (Contract 6 in integration architecture).
6. **Split factory envs from product envs from the start.** The `no-default-feature = true` pattern is what makes a per-story loop worktree affordable; retrofitting it later means re-deriving every product's run-dep set.
7. **Keep the `environment.yaml`↔`pixi.toml` export check.** It is the only thing that stops the two drifting, and it costs one command.
8. **Future work** (deferred): teach `_http.py` to be host-aware so the JFROG_API_KEY leak becomes architecturally impossible. `skip_auth=True` is today's per-callsite stopgap, not the fix. Tracked in `project_http_jfrog_unconditional_injection.md` auto-memory.
