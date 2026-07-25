---
title: "Addendum: Unity Data Stack product brief"
status: "draft"
created: "2026-07-25"
updated: "2026-07-25"
project_slug: "unity-data-stack"
purpose: "Depth from the intake artifacts that belongs downstream (PRD / architecture) rather than in the 1-2 page brief."
---

# Addendum — Unity Data Stack

Detail extracted from the three intake gists and the research reports, preserved for the PRD and
architecture stages. Nothing here is decided; this is the raw material the brief distils.

---

## A. The Constitution — article map and provenance

Source: `docs/intake/gists/spec-kit/constitution.md` — **v1.2.0, ratified 2025-11-20, last
amended 2025-11-20, next review 2026-02-20** (i.e. the stated review date has passed).

Amendment log records: 1.1.0 aligned the document to the then-actual codebase (12-stage SDLC,
GitOps/Argo CD, Python 3.14+ preference); 1.2.0 reframed it for agent-driven SDD, renaming
"Test-Driven Development" → "Spec Validation", "Code Quality" → "Agentic Quality Enforcement",
"Documentation" → "Specification Standards", "CI/CD" → "Continuous Spec Enforcement", and
renaming the data-mesh layers Processed/Analytics → **Raw / Curated / Consumption**.

| Article | Subject | Priority markers | Notes for the PRD |
|---|---|---|---|
| Preamble | SDD mandate; agents empowered to audit/generate/enforce | — | Names `spec-kit` and `specify` as operational entities |
| I | Project identity: mission, tech stack, repo structure | — | § 1.2 is the full mandated stack; § 1.3 the directory contract |
| II | Pixi-first package management | **CRITICAL** ×7, HIGH ×4, MEDIUM ×1 (mandate table) | `pip install` explicitly BLOCKED; § 2.5 is the *only* structured exception mechanism, and it is pixi-scoped |
| III | Spec validation (tests) | NON-NEGOTIABLE | 100% Dagster asset coverage; 80% module coverage; tests before implementation |
| IV | Agentic quality enforcement | NON-NEGOTIABLE | Ruff / Pyright / Bandit / Safety; `check-all` == CI |
| V | Specification standards | — | Docstrings, asset metadata contract, README-per-directory, **ADRs**, conciseness |
| VI | 12-stage SDLC environment spec | CRITICAL | The table below (§ B) |
| VII | Data mesh | HIGH | 11 domains, 3 layers, `<domain>_<layer>_<entity>_<verb>` naming, data-as-product |
| VIII | Spec-driven collaboration | — | Gitflow (**`develop` is default, not `main`**), conventional commits, 7 PR gates |
| IX | Dagster best practices | — | Asset definition/naming/error-handling/testing/observability patterns |
| X | Continuous spec enforcement (CI/CD) | — | 5 named workflows; `act` local CI; GitOps via Argo CD + Kustomize + Sealed Secrets |
| XI | Performance and scalability | — | Asset timing, query optimization, partitioning, memory, caching |
| XII | Security and compliance | — | Secrets, least privilege, input validation, dep management, scans, **GDPR/PII** |
| XIII | Simplicity gate | — | YAGNI; complexity requires ADR + alternatives + metrics + reduction plan |
| XIV | Python version support | — | 3.14+ preferred / 3.12 legacy baseline / 3.13 supported; 2-year support rule |
| Governance | Authority, amendment, enforcement, agent mandate | — | Constitution "supersedes all other development practices" |

### A.1 Requirements-with-provenance candidates

Articles III, IV, V, VIII, XII, XIII translate almost directly into testable requirements. Article
II's mandate table is the source of the CRITICAL/HIGH/MEDIUM enforcement-priority grading, which
the PRD should preserve as requirement priority rather than re-derive.

### A.2 Internal inconsistencies found

1. **Art. XIV § 14.4 vs § 14.1.** The 2-year support rule, applied literally to Python 3.12
   (released 2023-10), expires it — yet § 14.1 names 3.12 the "legacy baseline" and the working
   root pins `python = ">=3.12.12,<3.15"` with a `[feature.py312]`. Rule and implementation
   disagree.
2. **Art. II mandate table vs § 1.2 stack list.** The table declares Dagster "the sole platform"
   and Kedro "the sole approved toolbox", while § 1.2 lists MLflow, Airflow (legacy), Nebari, and
   dbt-core under Orchestration and five processing libraries (Polars, Pandas, Dask, PyArrow,
   Ibis, daft) without a sole-choice. Which are mandates and which are menus is unstated.
3. **Art. VIII § 8.3** requires "at least one human approval (Contractual Sign-off)" without
   specifying whose — the trusted-committer gap.
4. **"MCP" is expanded incorrectly.** Art. II calls it "Multi-Agent Communication Protocol";
   the industry term (and § 1.2's own "Model Context Protocol core" dependency) is **Model
   Context Protocol**. Cosmetic, but it is a mandate row.
5. **Next review date (2026-02-20) has passed** with no amendment — the "living document" clause
   is unexercised.

---

## B. The 12-stage SDLC

| # | Environment | GitFlow branch | Data classification | Network | Database | Working-root features |
|---|---|---|---|---|---|---|
| 1 | public | `main/*` | Public | Internet | DuckDB | runtime, test, lint, dev, container, local-recipes, agentic, k8s, monorepo-full-stack |
| 2 | local | `feature/*` | Deidentified | AirGap | DuckDB | *(`local-dev`)* runtime, test, lint, dev, agentic |
| 3 | agents | `feature/*` | Deidentified | AirGap | DuckDB | runtime, agentic, container |
| 4 | vendor | `feature/*` | Proprietary | Internet | DuckDB | runtime, test, lint, dev, container |
| 5 | dev | `develop` | Deidentified | Internet | DuckDB | runtime, test, lint, dev, container |
| 6 | ci | All (PR) | Deidentified | AirGap | DuckDB | runtime, test, lint |
| 7 | integration | `develop` | Deidentified | AirGap | PostgreSQL | runtime, test, lint, dev, container |
| 8 | testing | `release/*` | Deidentified | AirGap | PostgreSQL | runtime, test, lint, dev, container |
| 9 | uat | `release/*` | Restricted | AirGap | PostgreSQL | runtime, test, lint, dev, container |
| 10 | production | `main` | Restricted | AirGap | PostgreSQL | runtime |
| 11 | dr | `main` | Restricted | AirGap | PostgreSQL | runtime |
| 12 | oss | `main/*` | Public | Internet | DuckDB | runtime |

**Data classifications:** Public (no restriction) · Deidentified (anonymized, no PII) ·
Proprietary (third-party vendor, restricted distribution) · Restricted (PII, access controls +
audit logging).

### B.1 The collapse analysis (research OQ-M11)

- **Five environments are byte-identical**: `vendor`, `dev`, `integration`, `testing`, `uat` all
  equal `["runtime","test","lint","dev","container"]`.
- **Three more are identical**: `production`, `dr`, `oss` all equal `["runtime"]`.
- So 12 declared stages collapse to **~4 distinct dependency sets**.

The stages differ along **branch, data classification, network posture, and database** — none of
which is a dependency-set difference. This suggests the taxonomy is a *deployment/data-governance*
axis wrongly projected onto pixi's *package-set* axis. Cost of the current shape: eight redundant
solves, eight environments to install and cache, and a `[system-requirements]`/solve-group
surface far larger than the real variation.

Counter-argument to record fairly: semantic environment names may be worth their cost as an
operator-facing contract (`pixi run -e uat …` reads better than a flag), and they differ by
activation env-vars even where dependencies match. The PRD should decide explicitly rather than
inherit.

---

## C. The working root — inventory

Source: `docs/intake/gists/unity-data-stack-pixi-toml/Unity-Data-Stack-Pixi.toml`, **1,726 lines**.

| Property | Value |
|---|---|
| `[workspace] name` / `version` | `unity-data-stack` / `2025.11.0` |
| Channels | `conda-forge` (primary), `SelfExplainML` (fallback) |
| Platforms | `linux-64`, `osx-64`, `osx-arm64`, `win-64` |
| `requires-pixi` | `==0.59.0` **(exact — current pixi is 0.73.0)** |
| Solve strategy / channel priority | `highest` / `strict` |
| `[system-requirements]` | `linux = "3.10"` (RHEL 7+ / Ubuntu 18.04+), `macos = "11.0"` |
| Tasks | **~200** in `[tasks]` (lines 215–771) |
| Features | 20 feature blocks + platform targets |
| Environments | **~20** declared |
| Workspace members | 3 via `[pypi-dependencies]` editable paths |

### C.1 Feature inventory

`base` · `runtime` (+ 4 platform targets, each with `.dependencies` and `.pypi-dependencies`) ·
`test` (+ `activation.env`) · `lint` · `dev` (+ 3 platform targets) · `container` (+ linux-64
target) · `k8s` (linux-64 target only) · `local-recipes` (+ activation) · `py312` · `py313` ·
`py314` *(commented out)* · `agentic` (+ 4 platform pypi targets) · `monorepo-full-stack` ·
`scripts-conda-pypi`.

### C.2 Task taxonomy (~200 tasks, banner-derived)

Public API (`start`, `stop`, `status`, `verify`) · composite quality (`check-all`) · testing
(pytest + **BDD via behave**, with `@smoke` / `@integration` / API / customer tag slices) ·
lint & type-check · formatting · pre-commit + link checking · **per-service local-dev lifecycle**
(dagster, duckdb, postgres, mongodb, redis, minio, celery, mlflow, nebari — each with
up/down/status) · aggregate local-dev up/down/status/restart · health verification · domain
services (profile-service, web-app) · container ops (engine-neutral podman/docker) · image builds ·
environment-specific compose (`int-up`, `qa-up`) · OCP/K8s cluster management · **MCP servers**
(conda-forge, Dagster, Pixi — with a note that MCP tests run as a CI matrix job for a "14min
speedup") · GitHub Actions local testing via `act` · scaffolding (Copier) · Artifactory config ·
package-specific delegation (`test-<package>`, `lint-<package>`).

### C.3 Package inventory (from the root's own comments)

- **Shared libraries (1):** `src/shared/packages/common`
- **Platform infrastructure (10 active):** dagster-server (:3000), mlflow-server (:5000),
  nebari-server (K8s), duckdb-server (:8082), postgres-server (:5433), mongodb-server (:27018),
  redis-server (:6380), celery-server (Flower :5555), minio-server (:9000/:9001), ocpk8s-server
- **Domain services (2):** `customer/services/profile-service` (:8001),
  `customer/services/web-app` (:8000)
- **Excluded (2, with reasons):** airflow-server — *SQLAlchemy <2.0 conflict with Dagster,
  DEPRECATED, use Dagster*; sharepoint-mcp-server — *pyjwt version conflict*
- **Empty tech domains (10):** ccibt, cdo, cdxo, ct, cto, dti, eft, ics, ohot, tcoo — "scaffolding
  only"

> **Sizing implication (research OQ-D10):** the root states 1 reference domain implemented, 10
> empty. A PRD scoped to "11 domains" is an order of magnitude larger than one scoped to "the
> domain pattern + 1 worked example."

### C.4 Known defects in the working root

1. **Exact pixi pin** (`requires-pixi = "==0.59.0"` + `pixi = "==0.59.0"`) blocks any current
   install. → floor + tested ceiling.
2. **Fat base `[dependencies]`** — ~30 packages (conda, conda-build, conda-index, conda-lock,
   conda-pack, rattler-build, rattler-index, pixi-pack, pixi-unpack, hatch, hatchling, hatch-vcs,
   twine, uv, uv-build, wheel, setuptools, setuptools-scm, python-build, act, gh, direnv,
   gitpython, beautifulsoup4, requests, pyyaml, platformdirs, pip …) inherited by **every**
   environment including `production`, `dr`, `oss`, which are declared minimal-footprint. Directly
   contradicts their stated purpose. → `no-default-feature = true` (the pattern this repository's
   own `pixi.toml` uses for exactly this reason on three environments).
3. **Commented-out duplication** — `[feature.runtime.dependencies]` opens with ~35 commented lines
   annotated `# Note: Already included in base dependencies`. → pixi 0.73.0's `workspace = true`
   makes this expressible natively.
4. **`setuptools` capped** `>=80.9.0,<81` with the recorded reason "setuptools 81 removes
   `pkg_resources`" — a real, dated constraint worth carrying forward as a documented pin.
5. **Stale Python-3.14 exclusion** in `monorepo-full-stack` (`python = ">=3.12.12,<3.14"`) whose
   stated cause (dagster) is resolved upstream — dagster 1.13.15 declares `<3.15,>=3.10`.
6. **`py314` environment commented out** — should be re-enabled subject to (5).
7. **Trailing "-- From Pyproject.toml (temporary)" blocks** at the end of the file and inside
   `[feature.test]`/`[feature.lint]` — an unfinished migration left mid-flight.

### C.5 Platform-conditional dependency knowledge (valuable, keep)

Hard-won conda-forge portability facts recorded in the root, worth preserving verbatim into the
architecture:

| Package | Constraint |
|---|---|
| `dlt` | `dlt-pendulum` on conda-forge for linux-64 / osx-64 / win-64 only → **PyPI fallback on osx-arm64** |
| `pygwalker` | needs `python-quickjs`, absent on conda-forge osx-arm64 → **PyPI fallback on osx-arm64**; conda-forge `build_2+` required for numpy 2.x |
| `gunicorn`, `supervisor`, `nginx` | UNIX-only → linux-64 / osx-* only |
| `honcho` | Windows substitute for `supervisor` |
| `powershell` | conda-forge has it for linux-64 / osx-arm64 / win-64 — **not osx-64** |
| `kind` | **not on conda-forge at all** → `local-dev-k8s` documented as NOT IMPLEMENTED |
| `channels_redis` | underscore, not hyphen (import/spelling trap) |
| `pyarrow` | `<22` was a streamlit-only constraint (streamlit 1.51.0 needed `pyarrow>=7,<22`) — now relaxed |
| `gql` | `>=4.0.0` chosen because v4 dropped the `websockets` dependency |
| `websockets` | `>=15.0.1` because fastmcp requires it |
| `redis-py`, `python-kubernetes` | conda-forge naming differs from PyPI (`redis`, `kubernetes`) |

This corroborates repo memory `feedback_pypi_conda_mapping_unreliable.md` — conda names diverge
from PyPI names in non-obvious ways, and the root has already paid that cost once.

### C.6 The upgrade-exclusion list (an unrecorded decision)

The root header carries:

```
pixi upgrade --pinning-strategy latest-up --exclude coloredlogs --exclude pydantic --exclude typer
  --exclude tomlkit --exclude python --exclude django --exclude wagtail --exclude nodejs
  --exclude coderedcms --exclude dagster
```

Ten packages held back, with the reasons only partly recoverable from nearby comments (LTS pins
for django/wagtail/coderedcms/nodejs; dagster-transitive pins for coloredlogs/pydantic/typer/
tomlkit). This is a **policy decision with no ADR** — the PRD should require it be captured as one.

---

## D. The toolchain spec — components and gaps

Source: `docs/intake/gists/bmad-method-spec-enterprise-monorepo-cross-platform-deployme/…md`,
12 KB. Note: the source file's markdown is partially mangled (headings run into body text), which
is why several claims required careful reading rather than skimming.

### D.1 The five core systemic constraints (verbatim intent)

1. **Single Source of Truth** — root `/pyproject.toml` holds all structural config, workspace
   mappings, tool definitions.
2. **Universal Cryptographic Lockfile** — one `/pylock.toml` (PEP 751) tracking multi-platform
   targets, hashes, file references. → **falsified in part**: PEP 751 does not guarantee this
   (research D1).
3. **Zero-State Local Deployment Rule** — cloud pipelines, production servers, and automated test
   runtimes boot using **only** `pylock.toml`, independent of `pixi.lock` or workspace manifests.
   → the crux of the two-lockfile conflict.
4. **Token Isolation Rules** — no Artifactory tokens or target env-vars hardcoded in config or VCS.
   → **violated in spirit** by the spec's own credentials-in-URL `extra-index-urls` and its CI's
   `--index-url` interpolation.
5. **Targeted Distribution Isolation** — production images slim; runtime trees only, no fat images.

### D.2 Layout conflict

| | Toolchain spec | Working root |
|---|---|---|
| Members | `apps/*`, `libs/*` | `src/shared/packages/*`, `src/platform/data-platform/infrastructure/*`, `src/tech-domains/*` |
| Mechanism | `[tool.pdm.workspace] members` | `[pypi-dependencies]` `{ path = …, editable = true }` |
| Manifest | `pyproject.toml` | `pixi.toml` |
| Local link | `core-utils @ file://../../libs/core_utils` | editable path install |

Third option now available: pixi's own multi-package workspaces (`{ path = … }` members +
`{ workspace = true }` shared versions) — **preview status** (research OQ-M8).

### D.3 The four lifecycle phases

1. **Developer local** — `pixi init --format pyproject`; `pixi run lock-monorepo`.
2. **Production container** — two-stage Dockerfile: `ghcr.io/prefix-dev/pixi:latest` builder →
   `python:3.11-slim` production. Uses `pixi run --manifest-path /dev/null` to force zero-state,
   `pip install --target=/monorepo/dist-packages --only-binary=:all: --platform manylinux2014_x86_64
   --implementation cp --python-version 311 -r pylock.toml`, generates `sbom-runtime.json`, sets
   `PYTHONPATH`, labels `org.opencontainers.image.sbom`.
3. **Self-healing automation** (`auto-patch.yml`) — daily cron; `pip-audit` → on failure
   `pdm update --update-reuse` + re-lock → `peter-evans/create-pull-request@v6`.
4. **Unified testing & compliance** (`ci.yml`) — 3-OS matrix with per-OS `pip-platform`
   (`manylinux2014_x86_64` / `macosx_11_0_arm64` / `win_amd64`), `setup-pixi@v0.9.4` with
   Artifactory auth, targeted pytest, `sbom-prod` + `sbom-full` on ubuntu, artifact upload.

**Observations for the architecture:**
- The Dockerfile hardcodes **Python 3.11** (`python:3.11-slim`, `--python-version 311`) while the
  Constitution mandates 3.12–3.14. Direct contradiction.
- `COPY libs/libs/ ./libs/` is a typo (doubled path segment).
- The production base switches away from conda — see brief § "The decisive open question".
- `pixi run --manifest-path /dev/null` is a clever zero-state trick worth keeping *if*
  pylock-primary or split-by-tier wins.
- The daily patch bot has no severity gate, no exploitation-status awareness, and no evidence
  trail — superseded by Warden.

### D.4 Role matrix → pyforge crew

| Spec role | Duties | Crew station | Fit |
|---|---|---|---|
| Architect | Workspace boundaries, risk tolerances, unified schema mappings | **Atlas** + **Marshal** | Split |
| Developer | Local toolchain, workspace config, localized coding | **Marshal** | Good |
| DevOps | Cross-platform matrix, container optimization, zero-state deploy | **Steward** | Excellent |
| Security | Static analysis vs lockfile, self-healing patch bots | **Warden** | Excellent |
| Compliance | Supply-chain mapping, scope filtering, segregated SBOM export | **Warden** + **Mason** | Good |
| — | — | **Herald** (comms) | Unmapped |
| — | — | **Doctor** (diagnostics) | Unmapped |
| — | — | **Scribe** (memory) | Unmapped |

All three unmapped stations are **feedback-loop** roles. The spec covers *doing* but not
*observing, explaining, or remembering* — the same under-specification of the human layer that the
missing trusted-committer role represents.

---

## E. Local evidence — `local-recipes` as a worked example

This repository is a live pixi multi-package monorepo of the same shape. Transferable patterns:

| Pattern | Where | Why it matters to Unity |
|---|---|---|
| `no-default-feature = true` | `pyforge-warden`, `pyforge-atlas`, `bmad-ui` environments | The direct remedy for C.4(2). Recorded rationale: worktrees must materialize a lean env, not the fat default |
| Per-environment justification comments | throughout `[environments]` | Each env states why it exists and what it excludes — the discipline Unity's 20 envs lack |
| Feature-scoped tasks | `[feature.local-recipes.tasks.*]` | Tasks live with the feature that provides their deps, rather than all in a flat root `[tasks]` |
| Activation scripts | `[feature.local-recipes.activation] scripts = ["scripts/load-env.sh"]` | Env bootstrapping without committed config |
| `default-env:` directive comment | `[environments]` header | Convention for tooling to pick a default env |

**Caveat (per the task brief): cite as evidence, do not copy blindly.** `local-recipes` is a
packaging factory with ~12 environments and a handful of internal packages; Unity is a data
platform with ~20 environments and 13+ services. The *patterns* transfer; the *scale* does not.

---

## F. Rejected / superseded from the intake set

| Item | Disposition | Reason |
|---|---|---|
| `pdm export --format pylock --override-platform=…` | **Superseded** | Flag does not exist; format token is `pylock.toml` (research D3) |
| "Universal lockfile tracks multi-platform targets" as a *format guarantee* | **Corrected** | PEP 751 uses environment markers; coverage is a property of generation, not the format |
| `pip-audit` as the security axis | **Superseded** | Warden is a strict superset — pixi manifests, CISA-KEV + EPSS, schema-validated report, CI gate |
| Daily `auto-patch.yml` as the compliance mechanism | **Superseded** | Remediation without reporting; no exploitation status, no evidence trail |
| `requires-pixi = "==0.59.0"` | **Superseded** | Blocks all current installs; floor + ceiling instead |
| `<3.14` ceiling on `monorepo-full-stack` | **Superseded** | Stated cause (dagster) resolved upstream |
| `python:3.11-slim` production base | **Flagged** | Contradicts the Constitution's 3.12–3.14 mandate |
| Credentials in `extra-index-urls` / CI `--index-url` | **Rejected** | Leaks into lockfiles, logs, process listings; use pixi auth store / `setup-pixi` auth inputs |
| `airflow-server`, `sharepoint-mcp-server` | **Kept excluded** | Documented conflicts (SQLAlchemy <2.0 vs Dagster; pyjwt) — carry the exclusion *and* its reason |
| "MCP = Multi-Agent Communication Protocol" | **Corrected** | Model Context Protocol |

---

## G. Deferred-but-valuable

Material that earned preservation but has no v1 home:

- **`local-dev-k8s`** — stubbed and documented as NOT IMPLEMENTED (kind is not on conda-forge;
  Podman unavailable for win-64 on conda-forge). The analysis is sound; keep the stub and its
  reasoning.
- **`monorepo-full-stack`** — a compatibility-testing environment combining all major libraries to
  detect conflicts early. An unusual and genuinely good idea; its existence is also an honest
  admission of the mandated stack's compatibility risk.
- **`scripts-conda-pypi`** — package-index building/analysis scripts; overlaps this repository's
  `pyforge-atlas` and `cyclonedx-universe-inventory` work. Check for duplication before building.
- **MCP server tasks** (conda-forge, Dagster, Pixi) with a CI matrix note claiming a **14-minute
  speedup** — a measured optimization worth carrying.
- **BDD via `behave`** with tag slices (`@smoke`, `@integration`) alongside pytest — a
  second testing modality the Constitution's Article III does not mention.
- **`act`-based local CI** (`act-ci-all` / `act-ci-shared` / `act-ci-domains`) — the mechanism
  behind the "local passes ⇒ CI passes" guarantee (S3).
