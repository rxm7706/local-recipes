---
doc_type: deployment-guide
project_name: local-recipes
date: 2026-05-12
source_pin: 'conda-forge-expert v7.7'
---

# Deployment Guide

How to deploy and operate `local-recipes` in enterprise, air-gapped, and JFrog Artifactory environments. This guide consolidates `docs/enterprise-deployment.md` with the deployment-relevant rules from `project-context.md` and the integration architecture's auth chain.

For interactive dev setup, see `development-guide.md`. For end-to-end source provenance, see `docs/enterprise-deployment.md` (this guide is the planning view; that file is the operational reference).

---

## Deployment Modes

Three operational modes, listed by network constraint:

| Mode | Network | Setup needed |
|---|---|---|
| **Open internet** | All public hosts reachable | None — pixi resolves from conda-forge + pypi.org directly |
| **JFrog-proxied** | Public hosts via JFrog Artifactory remote repositories | `.pixi/config.toml` + per-host `*_BASE_URL` env vars |
| **Fully air-gapped** | No public hosts; only internal mirrors | All of JFrog-proxied + internal CVE/vdb mirrors + S3 parquet mirror |

**Most enterprise deployments are JFrog-proxied.** Fully air-gapped is the strictest case and the design target — workflows that fail air-gapped will also fail in JFrog-proxied environments where coverage is incomplete.

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

A sample template lives at `docs/pixi-config-jfrog.example.toml`. Copy to `.pixi/config.toml` and edit hosts.

### 2. Environment variables (per-shell)

| Variable | Used by | Purpose |
|---|---|---|
| `JFROG_API_KEY` | `_http.py` | Bearer auth header for JFrog. **★ Leaks cross-host — see below.** |
| `GITHUB_TOKEN` | `_http.py`, gh CLI | GitHub authentication (Phase K + N + submit_pr) |
| `CONDA_FORGE_BASE_URL` | `_http.py` (Phase B current_repodata.json fallback) | Override conda-forge channel base |
| `PYPI_BASE_URL` | `_http.py` (Phase D, mapping refresh, recipe-generator) | Override pypi.org base |
| `ANACONDA_API_BASE` | `_http.py` (Phase F API path) | Override api.anaconda.org base |
| `S3_PARQUET_BASE_URL` | `_http.py` (Phase F S3 path) | Override AWS S3 parquet base |
| `GITHUB_API_BASE_URL` | `_http.py` (Phase K + N + gh integrations) | Override api.github.com base |
| `PHASE_F_SOURCE` | atlas Phase F | `auto` (default) / `anaconda-api` / `s3-parquet` |
| `PHASE_H_SOURCE` | atlas Phase H | `pypi-json` (default) / `cf-graph` |
| `PHASE_F_S3_MONTHS` | atlas Phase F S3 path | Trailing-N-months cap (default: unlimited) |
| `PHASE_GP_ENABLED` | atlas Phase G' | `1` to enable per-version vulnerability scoring |
| `VDB_HOME` | atlas Phases G + G' | AppThreat vdb location (auto-set by `vuln-db` env activation) |
| `BOOTSTRAP_<STEP>_TIMEOUT` | `bootstrap-data` | Per-step timeout in seconds (defaults sized for cold `--fresh`) |
| `GEMINI_API_KEY` | `gemini_server.py` (auxiliary MCP) | If Gemini bridge is used |

**Setting `*_BASE_URL` env vars**: typical pattern is a per-user `~/.bashrc` / `~/.zshrc` block, OR a per-directory `.envrc` file with `direnv`, OR exported in the pixi env's activation script via `[feature.<env>.activation.env]`.

### 3. Internal mirror infrastructure (JFrog admin domain)

For full air-gap, you need:

- **conda-forge mirror**: JFrog "Conda Remote Repository" pointing at `https://conda.anaconda.org/conda-forge` — proxies channel data
- **PyPI mirror**: JFrog "PyPI Remote Repository" pointing at `https://pypi.org/simple/` — proxies PyPI Simple API
- **`files.pythonhosted.org` mirror** (uncommon but required for many sdist URLs): JFrog "PyPI Remote Repository" pointing at `https://files.pythonhosted.org/` — see `docs/enterprise-deployment.md` § 3 for why
- **anaconda.org API mirror** (optional, for Phase F API path): JFrog "Generic Remote Repository" pointing at `https://api.anaconda.org/`
- **S3 parquet mirror** (recommended, for Phase F S3 path): JFrog generic repository or internal S3-compatible store seeded from `s3://anaconda-package-data/`
- **CVE feed mirror** (NVD, GHSA, OSV): internal copy refreshed by your security team
- **AppThreat vdb mirror**: internal copy of the vdb tarball

The skill's `_http.py` will auto-route to each via the corresponding `*_BASE_URL` env var. No code changes required.

See `docs/enterprise-deployment.md` § 1-5 for JFrog REST API examples and full setup.

---

## The JFROG_API_KEY Cross-Host Leak (Critical Constraint)

> ★ **When `JFROG_API_KEY` is set in the environment, `_http.py` attaches the `X-JFrog-Art-Api` header to EVERY outbound HTTP request, regardless of destination host.**

This is the single most important security constraint in the deployment layer. It affects all four parts because all four route their HTTP through `_http.py` (Part 1's `scripts/_http.py`).

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

- **Trying to teach `_http.py` to be host-aware**: this is the right long-term fix (deferred work; tracked in auto-memory `project_http_jfrog_unconditional_injection.md`). It requires explicit host allow-lists keyed against `JFROG_API_KEY` exposure. Not currently implemented.
- **Setting `*_BASE_URL` to redirect everything to JFrog**: covers PyPI / conda-forge / anaconda.org, but NOT github.com (no `GITHUB_BASE_URL` is meaningful for the actual `submit_pr` PR-open call — it ALWAYS hits `api.github.com`). The leak still happens.
- **Relying on JFrog logs to detect the leak**: the header is silently rejected by non-JFrog hosts. Detection requires audit at the source (`_http.py` `make_request` callsite).

### Documentation locations

- `docs/enterprise-deployment.md` § 2 → "Cross-host credential leak" — operational reference with the subshell pattern + enumerated commands
- `_bmad-output/projects/local-recipes/project-context.md` § Air-Gapped/Enterprise — Critical Constraint with the unset-before-external-commands rule
- This doc § "Mitigation patterns" above
- Auto-memory `project_http_jfrog_unconditional_injection.md` — durable reminder

---

## Deployment Checklist

For a new air-gapped / JFrog-proxied deployment:

### Setup (one-time)

- [ ] Confirm JFrog has remote repositories for: conda-forge, pypi.org, files.pythonhosted.org (recommended), api.anaconda.org (optional)
- [ ] Set up corporate CA in OS trust store, or set `REQUESTS_CA_BUNDLE` env var, or pixi's `tls-root-certs = "native"`
- [ ] Author `.pixi/config.toml` from template at `docs/pixi-config-jfrog.example.toml`
- [ ] Set up `*_BASE_URL` env vars in `~/.bashrc` / `.envrc` / pixi env activation (see table above)
- [ ] Bootstrap CVE database from internal mirror: `pixi run -e vuln-db update-cve-db`
- [ ] Bootstrap atlas: `pixi run bootstrap-data --fresh` (will take 30-45 min; uses your `*_BASE_URL` overrides)
- [ ] Validate: `pixi run health-check` (expects no public-host errors)

### Per-session

- [ ] Confirm `JFROG_API_KEY` is set ONLY in JFrog-only shells (or use subshell scoping)
- [ ] Confirm `scripts/bmad-switch --current` shows the right project
- [ ] If running cron jobs, ensure each cron command is wrapped in a subshell that unsets `JFROG_API_KEY` if it hits external hosts

### Periodic maintenance

- [ ] Weekly: `pixi run atlas-phase F` + `atlas-phase G` + `atlas-phase H` + `atlas-phase K`
- [ ] Weekly: `pixi run update-cve-db`
- [ ] Monthly: `pixi run bootstrap-data --resume`
- [ ] Quarterly: review skill CHANGELOG for new constraints; re-verify project-context.md drift pin

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

See `docs/enterprise-deployment.md` § 4 for the full mechanism + diagnostic patterns.

### Verification

```bash
pixi install -e vuln-db -vvv 2>&1 | grep -E "files.pythonhosted|artifactory|401|403|404"
```

Look for `files.pythonhosted.org` connection timeouts → your `index-url` didn't take effect. Look for 401/403 → auth issue. Look for 404 on `appthreat-vulnerability-db` → JFrog allow-list excludes the package.

---

## CI / CD Considerations

`azure-pipelines.yml` is the primary CI. In air-gapped / on-prem Azure DevOps:

1. **Self-hosted Azure agents** must have pixi + Docker + corporate CA trust
2. **Pixi config**: the same `.pixi/config.toml` from above; usually shipped via a `.pixi/config.toml.template` in the repo and rendered by a pipeline step
3. **JFROG_API_KEY**: stored as Azure DevOps secret variable; injected per-pipeline-step. Pipelines that touch external hosts (`submit-pr` step) must NOT have it set
4. **Build artifacts retention**: `azure.store_build_artifacts: true` in `.conda-forge.yml` (per-recipe overrides under `recipes/<name>/conda-forge.yml`) makes failed-build artifacts downloadable for diagnosis

GitHub Actions (`.github/workflows/sync-pypi-mappings.yml`) runs on the public GitHub by default; for on-prem GitHub Enterprise, replicate the workflow there.

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

---

## Rebuild Implications

If you're rebuilding `local-recipes` on a clean repo and deployment matters:

1. **Author `_http.py` first** — every other Part imports it. Include the truststore + JFrog + GitHub + .netrc chain AND the per-host base-URL override logic.
2. **Document the `JFROG_API_KEY` cross-host leak in 3 places** (CLAUDE.md, project-context, docs/enterprise-deployment) — repetition is intentional; agents and humans both need the warning at the surface they read first.
3. **Author `docs/enterprise-deployment.md`** alongside the skill — without this, every new deployment will rediscover the JFrog gotchas the hard way.
4. **Provide `docs/pixi-config-jfrog.example.toml`** as a copy-pasteable starter for `.pixi/config.toml`.
5. **Make the `vuln-db` env separate** from `local-recipes` — don't bundle AppThreat into the default env (Contract 6 in integration architecture).
6. **Future work** (deferred): teach `_http.py` to be host-aware so the JFROG_API_KEY leak becomes architecturally impossible. This is in `project_http_jfrog_unconditional_injection.md` auto-memory.
