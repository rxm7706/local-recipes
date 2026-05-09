# Dependency Input Formats — Support Matrix

This document is the canonical reference for which dependency / SBOM /
manifest formats `scan_project.py` (and the broader cf_atlas tooling)
accepts as input, what fields are extracted, and what variants are
known-supported vs known-skipped vs not-yet-implemented.

Update this file when adding a new parser, a new SBOM format, or a new
tool integration. The status column is the contract; if you change a
parser's behavior (new fields, new fallbacks, new gotchas), update the
matching row here in the same change.

---

## Status legend

| Marker | Meaning |
|---|---|
| ✅ supported | Parser exists, exercised, fields documented |
| ⚠️ partial | Parser exists but only handles common cases — caveats listed |
| 📋 planned | Not yet shipped; tracked for future release |
| ❌ unsupported | Out of scope (specialized tool, proprietary, etc.) |

---

## I. Python ecosystem

| Format | Status | What we extract | Notes |
|---|---|---|---|
| `requirements.txt` (pip / pip-tools / pip-compile) | ✅ | `name`, `version` from `==`/`>=`/`~=` pins | URL-spec lines (`-e git+https://…`) skipped. `--hash` mode: name+version only, hashes ignored. `-r included.txt` recursion: not followed (rare in lock-style files). |
| `pyproject.toml` (PEP 621 `[project]`) | ✅ | `dependencies`, `optional-dependencies`, `[dependency-groups]` (PEP 735) | Reads top-level + Poetry's `[tool.poetry.dependencies]` + Hatchling's `[tool.hatch.envs.*.dependencies]` + PEP 735 `[dependency-groups]` (each group flattened with group name in extras). |
| `pyproject.toml` (Poetry) | ✅ | `[tool.poetry.dependencies]`, `[tool.poetry.dev-dependencies]` | Version-spec strings (`^1.2.3`, `~1.2`) preserved verbatim in `version_range` extras; stripped in `version` field. |
| `pyproject.toml` (PDM) | ✅ | `[project.dependencies]` + `[tool.pdm.dev-dependencies]` (groups flattened) | PDM dev-groups labeled with their group name in `extras["group"]`. |
| `pyproject.toml` (Hatchling) | ⚠️ | `[project.dependencies]` + `[tool.hatch.envs.<name>.dependencies]` | Per-env deps not propagated — they're tagged with the env name in manifest. |
| `pyproject.toml` (Flit) | ⚠️ | `[project.dependencies]` only (PEP 621) | Flit-specific `[tool.flit.metadata.requires-extra]` not parsed. |
| `pyproject.toml` (setuptools) | ✅ | `[project.dependencies]` (PEP 621) | Legacy `setup.cfg` / `setup.py install_requires` NOT parsed (deprecated by PEP 621). |
| `uv.lock` | ✅ | `[[package]]` `name` + `version` | Resolved versions used. uv's source-info / extras / markers not propagated. |
| `poetry.lock` | ✅ | `[[package]]` `name` + `version` | Same shape as uv. Hash data ignored. |
| `Pipfile.lock` (pipenv) | ✅ | `default` + `develop` sections; `==X.Y.Z` version strings stripped to bare version | Hash data ignored. |
| `conda-lock.yml` (conda-lock 2.x) | ✅ | `package:` list — name, version, manager (conda→`conda` ecosystem, pip→`pypi`), platform | Per-platform entries dedup'd by (name, version, ecosystem). |

---

## II. conda / conda-forge ecosystem

| Format | Status | What we extract | Notes |
|---|---|---|---|
| `pixi.lock` | ✅ | Resolved conda + pypi packages, all envs | Always preferred over `pixi.toml` when both exist. Reads URL-form (`https://conda.anaconda.org/conda-forge/<subdir>/<name>-<version>-<build>.conda`) and extracts name+version via regex. |
| `pixi.toml` | ✅ | `[dependencies]`, `[pypi-dependencies]`, `[feature.*.dependencies]`, `[feature.*.pypi-dependencies]` | Only when `pixi.lock` is absent (less precise — no resolved versions). |
| `environment.yml` / `environment.yaml` | ✅ | conda `dependencies:` list + nested `pip:` block | Channel-prefixed (`conda-forge::pkg`) deps stripped to bare name. Pin specs preserved. |
| `recipe.yaml` (v1) | ⚠️ | n/a (not parsed by scan_project; recipe authoring is the conda-forge-expert skill's other half) | This file is the recipe under `.claude/skills/conda-forge-expert/`'s OWN authoring tooling, not scan_project. |
| `meta.yaml` (v0) | ⚠️ | Same as above | scan_project doesn't read recipe files; the cf_atlas builder reads them via Phase E from cf-graph cache. |

---

## III. Other language ecosystems

| Format | Status | What we extract | Notes |
|---|---|---|---|
| `package.json` (npm/yarn/pnpm) | ✅ | `dependencies`, `devDependencies`, `peerDependencies`, `optionalDependencies` | Semver-range prefixes (`^`, `~`, `>=`, `<`) stripped from version field; raw stored in `version_range` extras. **Skipped if `package-lock.json` is present** — the lockfile is more accurate. |
| `package-lock.json` (npm v1/v2/v3) | ✅ | v2/v3: top-level `packages` keyed by `node_modules/<name>` (incl. scoped packages). v1: nested `dependencies` walked recursively | Resolved versions for the entire transitive tree. |
| `yarn.lock` (yarn 1+) | ✅ | Custom lockfile format — header lines `name@spec[, name@spec]:` + `version "X.Y.Z"` | Auto-detected (no `__metadata` key). |
| `yarn.lock` (yarn 2+ Berry) | ✅ | YAML format with `__metadata` block + resolution keys like `name@npm:^X` | Auto-detected via `__metadata` presence. |
| `pnpm-lock.yaml` | ✅ | YAML with `packages:` keyed by `/<name>@<version>` or `/@<scope>/<name>@<version>` | pnpm peer-dep markers `(peer@x.y.z)` stripped from version. |
| `Cargo.lock` | ✅ | `[[package]]` `name` + `version` | Rust workspace deps. |
| `Cargo.toml` | ✅ | `[dependencies]`, `[dev-dependencies]`, `[build-dependencies]` | Read only when `Cargo.lock` absent. |
| `go.mod` | ✅ | `require ( … )` block + single-line `require name version` | Read only when `go.sum` absent. |
| `go.sum` | ✅ | One line per (name, version[/go.mod] hash); `/go.mod` lines deduped | Module-line entries used for resolved versions. |
| `Gemfile.lock` (Ruby/Bundler) | ✅ | `GEM`/`PATH`/`GIT` sections — `specs:` blocks with `name (version)` lines at indent=4 | Sub-dep lines (indent=6) skipped to avoid double-counting. |
| `composer.lock` (PHP/Composer) | ✅ | `packages` + `packages-dev` arrays — `name`, `version` per entry | Composer 2.x lockfile format. |
| `pubspec.lock` (Dart/Flutter) | 📋 | n/a | Planned. |
| `Pipfile` (pipenv) | 📋 | n/a | Planned. Lock variant covered above. |

---

## IV. SBOM formats

The standard SBOM formats are CycloneDX and SPDX. cf_atlas accepts both as
input via `--sbom-in <file>` (auto-detected from JSON content) and emits
both via `--sbom cyclonedx` / `--sbom spdx`.

| Format | Version | Status | What we extract | Notes |
|---|---|---|---|---|
| **CycloneDX JSON** | 1.4 | ✅ | `components[]` array — `name`, `version`, `purl`, `bom-ref` | purl-derived ecosystem (pypi/conda/npm/deb/rpm/apk/cargo/maven/gem). |
| CycloneDX JSON | 1.5 | ✅ | Same as 1.4 | Schema-compatible at the fields we read. |
| CycloneDX JSON | 1.6 | ✅ | Same as 1.5 + new vex linkage (vex links not yet ingested) | This is what `--sbom cyclonedx` emits. |
| CycloneDX XML | 1.x | ✅ | `<components><component>` walked via xml.etree (built-in, no deps); name/version/purl extracted; namespace-agnostic so 1.4/1.5/1.6 all work. Filename aliases: `bom.xml`, `cyclonedx.xml`, `sbom.cyclonedx.xml`. `--sbom-in <file>.xml` auto-routes here by extension. |
| CycloneDX Protobuf | 1.x | ❌ | n/a | Out of scope; needs `cyclonedx-python-lib` heavy dep, and protobuf SBOM exchange is rare. |
| **SPDX JSON** | 2.2 | ⚠️ | `packages[]` `name`, `versionInfo`; ecosystem from `externalRefs[].referenceLocator` purl | License + relationship info read but not surfaced. |
| SPDX JSON | 2.3 | ✅ | Same as 2.2 + `primaryPackagePurpose` ignored | This is what `--sbom spdx` emits. |
| SPDX 3.0 (JSON-LD) | ✅ | `@graph` (or `elements`) array → `software_Package` (or `Package`) elements with `name`, `software_packageVersion`, optional `externalIdentifier[].identifier` for purl ecosystem | Auto-detected via top-level `@context` + `@graph`. |
| SPDX 2.x tag-value | (any) | ✅ | Plain text key-value pairs (`PackageName:` / `PackageVersion:` / `ExternalRef: PACKAGE_MANAGER purl <purl>`); ecosystem derived from purl prefix. Filename aliases: `sbom.spdx`, `sbom.spdx.tag`. `--sbom-in <file>.spdx` auto-routes here by extension. |
| SPDX RDF / XML | ❌ | n/a | Out of scope; needs `rdflib` and is rarely produced. JSON / tag-value cover ~99% of SPDX use. |
| **Syft native JSON** | (any) | ✅ | Top-level `artifacts[]` + `descriptor.name="syft"` auto-detected by `--sbom-in`. Type field maps to ecosystem (`python` → pypi, `deb` → apt, `go-module` → golang, etc.); purl-prefix fallback when type is missing. Filename aliases: `syft.json`, `sbom.syft.json`. |
| **Trivy native JSON** | (any) | ✅ | Top-level `Results[]` auto-detected. Per-result `Type` field maps to ecosystem (`debian`/`ubuntu` → apt, `pip` → pypi, `gomod` → golang, etc.). Filename aliases: `trivy.json`, `sbom.trivy.json`, `trivy-report.json`. |

---

## V. Container image + Kubernetes input

| Method | Status | Tools required | What we get |
|---|---|---|---|
| `--image <ref>` (single) | ✅ | `syft` (preferred) or `trivy` | Full SBOM extracted, dependency-level CVE lookup via vdb + atlas enrichment |
| `--image <ref1>,<ref2>` or repeated `--image` flag | ✅ | same | Multiple images scanned and merged into one report; per-image SBOM extraction in sequence |
| `--image-tool {auto\|syft\|trivy}` | ✅ | the chosen tool | Forces one extractor (auto picks first available, syft preferred) |
| `--oci-archive <path>` | ✅ | `syft` or `trivy` | Local OCI archive (.tar) or extracted dir; passes through with `oci-archive:` / `dir:` scheme prefix |
| `Containerfile` / `Dockerfile` static parse | ✅ (existing) | none | Reads `FROM`, `RUN apt/dnf/apk/pip/npm` lines from a recipe file. Less precise than image scan — captures only what's visible in the recipe, not transitive deps from base images. |
| **Kubernetes manifests** (`k8s/`, `kubernetes/`, `manifests/`, `deploy/`, `deployment/`, `openshift/`, `ocp/`, `helm/`, `charts/`, `kustomize/`, `overlays/`, `argo/`) | ✅ | none | Multi-document YAML walk; extracts every `image:` reference from Deployment / StatefulSet / DaemonSet / CronJob / Job / Pod / ReplicaSet / Knative Service / Argo Rollout / arbitrary CRDs that embed PodSpecs. Each image becomes a `Dep` with `ecosystem='oci-image'` for downstream `--image` chained scan. |
| **Helm chart `values.yaml`** | ✅ | none | Best-effort `image:` extraction at any depth; handles both string form (`image: nginx:1.25`) and Helm structured form (`image: {repository, tag, registry}`). Templated values (`{{ … }}`) auto-skipped — recommend `helm template … > rendered.yaml` first for accuracy. |
| Image registry direct (no syft/trivy) | 📋 | n/a | Would require implementing OCI-distribution registry client + container layer parser. Heavy; defer. |
| Live cluster scan via `--kubectl-all` / `--kubectl-context <ctx>` / `--kubectl-namespace <ns>` | ✅ | `kubectl` | Runs `kubectl get pods … -o json`, walks the JSON for every `image:` reference. Auto-skips with clear error if kubectl is not installed or the cluster is unreachable. |
| `--helm-chart <path>` (with optional repeatable `--helm-values <file>`) | ✅ | `helm` | Runs `helm template <path>` and parses the rendered multi-document YAML; resolves `{{ … }}` templating that the static `values.yaml` walk can't. |
| `--kustomize <dir>` | ✅ | `kustomize` (or `kubectl kustomize`) | Runs `kustomize build <dir>` (falls back to `kubectl kustomize` if standalone kustomize is unavailable) and parses the rendered output. |
| **Live conda env directory** (`--conda-env <path>`) | ✅ | none | Reads `<env>/conda-meta/*.json` for installed conda packages + `<env>/lib/python*/site-packages/*.dist-info/METADATA` for pip-installed packages. Offline-safe; matches `conda list --json` output without invoking conda. |
| **Live Python virtualenv** (`--venv <path>`) | ✅ | none | Walks `lib/python*/site-packages/*.dist-info/METADATA` and `Lib/site-packages/*.dist-info/METADATA` (Windows). Works with venv / virtualenv / uv-created envs / pipenv envs / poetry envs. |

**Authentication**: image references that require registry auth use the
local Docker / Podman / `~/.docker/config.json` credentials picked up by
syft/trivy. cf_atlas does not handle registry login — set up the
underlying tool first.

---

## VI. Vulnerability scanner outputs (third-party)

These are tools that produce their own report formats. cf_atlas does NOT
re-parse their native formats (each is non-trivial and proprietary), but
accepts their CycloneDX/SPDX exports.

| Tool | Native format | Their export options | Recommended path |
|---|---|---|---|
| **Anchore Grype** | `grype.json` (custom) | CycloneDX, SARIF | `grype <img> -o cyclonedx-json > sbom.json && cf_atlas --sbom-in sbom.json` |
| **Anchore Syft** | `syft.json` (custom) | CycloneDX, SPDX | Same — use `syft <img> -o cyclonedx-json` |
| **Aqua Trivy** | `trivy.json` (custom) | CycloneDX, SPDX, SARIF | Same — use `trivy image --format cyclonedx` |
| **Snyk** | `snyk-test.json` | CycloneDX (paid tier) | If you have CycloneDX export, use `--sbom-in`. Native Snyk JSON: ❌ out of scope. |
| **BlackDuck** | `bdio2` / proprietary JSON | CycloneDX, SPDX | Export as SPDX or CycloneDX, then `--sbom-in`. |
| **Google Wiz** | Wiz UI / API | CycloneDX | Same. |
| **AVR (Anchore Vulnerability Report)** | proprietary JSON | CycloneDX (via syft pre-step) | Two-step: syft → CycloneDX, then `--sbom-in`. |
| **Fossa** | `fossa-cli.json` | CycloneDX, SPDX | Export, then `--sbom-in`. |
| **GitHub Dependency Graph** | GitHub's GraphQL | SBOM via `gh sbom <repo>` (preview) | Same — pipe through `--sbom-in`. |
| **OWASP DependencyTrack** | API / UI | CycloneDX (native; same data model) | Direct ingest. |
| **Sonatype Nexus IQ** | proprietary | CycloneDX (export) | Same. |
| **JFrog Xray** | Xray API | CycloneDX, SPDX | Same. |

**General rule**: any tool that supports CycloneDX or SPDX export is
covered by `--sbom-in`. cf_atlas will not gain native parsers for
proprietary formats — the SBOM standards are the bridge.

---

## VII. cf_atlas-only enrichment (joined to your SBOM/manifest input)

Beyond CVEs, cf_atlas adds these signals (all from `cf_atlas.db`) to any
deps it recognizes as `conda` or `pypi` ecosystem:

| Signal | Joined column | Source | When useful |
|---|---|---|---|
| Latest conda-forge version | `latest_conda_version` (Phase B) | conda-forge `current_repodata.json` | "Is conda-forge current?" |
| PyPI version | `pypi_current_version` (Phase H) | `pypi.org/pypi/<name>/json` | Behind-upstream detection |
| GitHub/GitLab/Codeberg version | `github_current_version` + `upstream_versions` (Phase K) | VCS host APIs | Behind-upstream when source is VCS, not PyPI |
| Lifetime download count | `total_downloads` (Phase F) | anaconda.org files API | Reach / criticality |
| Latest-version downloads | `latest_version_downloads` (Phase F) | Same | Adoption signal for current |
| Critical/High/KEV CVEs affecting current | `vuln_*_affecting_current` (Phase G) | AppThreat vdb | Risk dashboard |
| CVE count delta vs last week | `vuln_history` (Phase G snapshot) | Snapshots | "What just changed?" |
| Bot stuck on version updates | `bot_version_errors_count` (Phase M) | cf-graph `version_pr_info` | Maintenance attention |
| Open bot PR awaiting review | `bot_open_pr_count` (Phase M) | cf-graph `pr_info` | Same |
| Feedstock 'bad' flag | `feedstock_bad` (Phase M) | cf-graph | Channel-wide breakage indicator |
| Archived feedstock | `feedstock_archived` + `archived_at` (Phase E.5) | conda-forge org GraphQL | "Is this dep abandoned?" |
| Maintainers list | junction `package_maintainers` | cf-graph node_attrs | Bus-factor analysis |
| Direct dependents | `dependencies` (Phase J) | cf-graph requirements | Blast-radius for changes |

---

## VIII. Known gaps and prioritization

After the v6.9.0 / scan-project parsers expansion + the deployment-context
sweep (k8s / helm / live envs / OCI archive / multi-image), these are the
remaining gaps:

| Gap | Effort | Persona impact |
|---|---|---|
| OCI image registry **layer** fetch (no syft/trivy) — currently only manifest probe is shipped | L | offline-only environments where syft/trivy aren't installable |
| CycloneDX Protobuf | (out of scope) | — |
| SPDX RDF | (out of scope) | — |
| `nerdctl` / `podman` CLI integration (local image inspect) | S | offline image scanning without registry access |
| `crane` / `regctl` registry inspection | S | alternative to syft/trivy for image manifest fetch |

S/M/L/XS = small (<50 lines) / medium (50-200) / large (>200) / extra-small (<10).

**Recently flipped 📋 → ✅ in v7.0.0** (the closeout / no-open-items push):
- PEP 735 `[dependency-groups]` (pyproject.toml) ✅
- PDM `[tool.pdm.dev-dependencies]` (group-aware) ✅
- Argo CD `Application` CR → resolved manifests, with auto git-clone fallback when source path is remote ✅
- Flux CD `Kustomization` / `HelmRelease` CR (same shape; auto git-clone fallback) ✅
- Maven Central upstream resolver — `maven_coord` schema column + Phase E autopopulation from cf-graph URL pattern + Phase L resolver ✅
- SBOM relationship traversal (CycloneDX `dependencies[]` + SPDX `relationships[]`) — parsed + stashed on `dep.extras["depends_on"]` + rendered as a tree in `scan-project` output ✅
- VEX status surfaced in render output — `not_affected`/`false_positive` analysis state shown alongside the dep card ✅
- OCI manifest probe (Bearer-challenge dance against `*/v2/<repo>/manifests/<tag>`) — extracts image config + layer digests without syft/trivy ✅
- Dockerfile multi-stage `COPY --from=<external-image>` attribution ✅

**Recently flipped 📋 → ✅ in v6.9.0** (pre-7.0 sweep):
- Native syft JSON ingestion (`syft.json`, `sbom.syft.json`) ✅
- Native trivy JSON ingestion (`trivy.json`, `sbom.trivy.json`, `trivy-report.json`) ✅
- CycloneDX XML 1.4/1.5/1.6 ingestion (xml.etree, built-in) ✅
- SPDX 2.x tag-value ingestion ✅
- VEX (CycloneDX 1.5+) ingestion ✅
- `package-lock.json` (npm v1/v2/v3) ✅
- `yarn.lock` (v1 + v2+ Berry, both via auto-detect) ✅
- `pnpm-lock.yaml` ✅
- `go.mod` + `go.sum` (lockfile-priority rule applied) ✅
- `Pipfile.lock` (pipenv) + `Pipfile` (manifest) ✅
- `conda-lock.yml` / `conda-lock.yaml` ✅
- `Gemfile.lock` (Ruby/Bundler) ✅
- `composer.lock` (PHP/Composer) ✅
- SPDX 3.0 JSON-LD ✅
- `requirements.in` (pip-tools input) ✅
- Kubernetes / OpenShift / Knative / Argo / Helm chart manifests under conventional paths ✅
- `--image <ref>` multi-image with comma-split / repeated flags ✅
- `--oci-archive <path>` (`.tar` or extracted dir) ✅
- `--conda-env <path>` (live conda env via `conda-meta/*.json` + dist-info walk) ✅
- `--venv <path>` (live Python venv via `lib/python*/site-packages/*.dist-info/METADATA`) ✅
- Pixi.lock parser bugfix: regex was matching subdir segment for some URLs (`linux@64/_openmp_mutex` ← `linux` mis-captured as name); now extracts basename first via `rsplit("/", 1)`

---

## IX. End-to-end CLI examples

```bash
# Local manifest discovery (auto-detects everything)
pixi run -e vuln-db scan-project /path/to/project

# GitHub repo (clone, scan, clean up)
pixi run -e vuln-db scan-project --github rxm7706/local-recipes

# Container image scan (syft preferred)
pixi run -e vuln-db scan-project --image python:3.12 --brief

# Container image scan (force trivy)
pixi run -e vuln-db scan-project --image nvcr.io/nvidia/pytorch:24.01-py3 --image-tool trivy

# Ingest a CycloneDX SBOM from any external tool
pixi run -e vuln-db scan-project --sbom-in /path/to/grype-output.cyclonedx.json

# Ingest an SPDX SBOM
pixi run -e vuln-db scan-project --sbom-in /path/to/spdx-2.3.json

# Generate a CycloneDX SBOM from a project, then ingest it elsewhere
pixi run -e vuln-db scan-project /path/to/project --sbom cyclonedx --sbom-out /tmp/project.cdx.json
# … later …
pixi run -e vuln-db scan-project --sbom-in /tmp/project.cdx.json --json | jq .vulns_by_dep

# Pipe a third-party tool's SBOM directly
syft alpine:latest -o cyclonedx-json | tee /tmp/alpine.sbom.json
pixi run -e vuln-db scan-project --sbom-in /tmp/alpine.sbom.json --brief

# OWASP DependencyTrack export → cf_atlas
curl -s -H "X-Api-Key: ..." \
  https://depTrack.example/api/v1/bom/cyclonedx/project/<uuid> > /tmp/dt.cdx.json
pixi run -e vuln-db scan-project --sbom-in /tmp/dt.cdx.json
```

---

## X. Glossary / file-name aliases

scan_project recognizes these names case-insensitively under any path
not blocked by `_SKIP_PATH_PARTS` (e.g., `.git`, `node_modules`,
`.pixi`, `.venv`, `__pycache__`, `target`, `vendor`, `gopath`, etc.):

| Filename | Matched parser | Ecosystem |
|---|---|---|
| `pixi.lock` | `parse_pixi_lock` | conda + pypi |
| `pixi.toml` | `parse_pixi_toml` | conda + pypi (when no lock) |
| `requirements.txt` | `parse_requirements_txt` | pypi |
| `pyproject.toml` | `parse_pyproject_toml` | pypi |
| `environment.yml` / `environment.yaml` | `parse_environment_yml` | conda |
| `Cargo.lock` | `parse_cargo_lock` | cargo |
| `Cargo.toml` | `parse_cargo_toml` | cargo (when no lock) |
| `uv.lock` | `parse_uv_lock` | pypi |
| `poetry.lock` | `parse_poetry_lock` | pypi |
| `Pipfile.lock` | `parse_pipfile_lock` | pypi |
| `Pipfile` | `parse_pipfile` | pypi (when no `Pipfile.lock`) |
| `requirements.in` (pip-tools input) | `parse_requirements_in` | pypi |
| `package.json` | `parse_package_json` | npm (when no `package-lock.json`) |
| `package-lock.json` | `parse_package_lock_json` | npm (preferred over `package.json`) |
| `yarn.lock` | `parse_yarn_lock` | npm (auto-detects v1 vs v2+ Berry) |
| `pnpm-lock.yaml` | `parse_pnpm_lock` | npm |
| `go.mod` | `parse_go_mod` | golang (when no `go.sum`) |
| `go.sum` | `parse_go_sum` | golang (preferred over `go.mod`) |
| `Gemfile.lock` | `parse_gemfile_lock` | gem |
| `composer.lock` | `parse_composer_lock` | composer |
| `conda-lock.yml` / `conda-lock.yaml` | `parse_conda_lock` | conda + pypi (manager-aware) |
| `Containerfile`, `Dockerfile`, `*.Containerfile`, `*.Dockerfile` | `parse_containerfile` | mixed (FROM + RUN) |
| `bom.json`, `cyclonedx.json`, `sbom.cyclonedx.json` | `parse_sbom_cyclonedx` | derived from purl |
| `sbom.spdx.json` | `parse_sbom_spdx` | derived from externalRefs |
| `sbom.spdx3.json`, `sbom.jsonld` | `parse_sbom_spdx_3` | derived from externalIdentifier purls |
| `values.yaml` (Helm chart values) | `parse_helm_values` | oci-image (best-effort) |
| `*.yaml`/`*.yml` under `k8s/`, `kubernetes/`, `manifests/`, `deploy/`, `deployment/`, `openshift/`, `ocp/`, `helm/`, `charts/`, `kustomize/`, `overlays/`, `argo/`, `kustomization/` | `parse_kubernetes_manifest` | oci-image |

Anything not in this list is silently skipped. If you have a project
that uses a non-standard filename (e.g., `requirements-dev.in` from
pip-tools), either rename it on the fly or pass via `--sbom-in` after
generating an SBOM from your tool of choice.
