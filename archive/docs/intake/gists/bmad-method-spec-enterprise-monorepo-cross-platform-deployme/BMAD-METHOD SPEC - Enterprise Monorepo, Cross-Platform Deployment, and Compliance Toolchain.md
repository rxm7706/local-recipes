📋 BMAD-METHOD SPEC: Enterprise Monorepo, Cross-Platform Deployment, and Compliance Toolchain1. Document Overview & MetadataSpecification Target: Unified Dependency Management, Secure Cross-Platform Packaging, and Continuous Compliance.Primary Toolchain Engine: Pixi (Orchestrator Root) + PDM / pip-tools (PEP 751 Compliant Compiler) + pip v26.1+ (Deploy Engine).Core Manifests: /pyproject.toml (Source of Truth) ➡️ /pylock.toml (Universal Secure Lockfile).2. Role Assignment MatrixThis architecture delegates specific operational constraints to a matrix of automated agents:Architect Agent: Enforces workspace boundary conditions, acceptable risk tolerances, and unified schema mappings.Developer Agent: Operates the local toolchain, updates internal workspace configurations, and handles localized application coding.DevOps Agent: Automates cross-platform matrix transformations, handles multi-stage container optimization, and orchestrates zero-state environment deployments.Security Agent: Executes static analysis audits directly against the universal lockfile and orchestrates self-healing patching bots.Compliance Agent: Maps supply-chain architectures, filters operational scopes, and exports segregated Software Bill of Materials (SBOM) arrays.3. Core Systemic ConstraintsSingle Source of Truth: The root /pyproject.toml handles all structural configurations, local multi-package workspace mappings, and tool definitions.Universal Cryptographic Lockfile: A singular /pylock.toml format (compliant with PEP 751 specifications) tracks multi-platform targets (linux, macos, windows), specific target hashes, and file references.Zero-State Local Deployment Rule: Cloud target pipelines, production servers, and automated testing runtimes must boot securely using only the pylock.toml file. They operate independently of local pixi.lock layers or workspace manifests.Token Isolation Rules: Absolute enforcement of credential isolation. No Artifactory infrastructure tokens or target environment variables may be hardcoded into configuration files or version control systems.Targeted Distribution Isolation: Production artifact images must remain slim. final outputs consume exclusively runtime application trees and localized code definitions, completely avoiding fat or bloated images.4. Multi-Package Monorepo Directory Layouttextmy-monorepo/
├── pyproject.toml              # Master Workspace Configuration
├── pylock.toml                 # Multi-Platform Universal PEP 751 Lockfile
├── apps/
│   └── api_service/            # Microservice Consumer Node
│       ├── pyproject.toml      # Local Manifest File
│       └── src/                # Functional Source Code
└── libs/
    └── core_utils/             # Shared Dependency Library Module
        ├── pyproject.toml      # Local Manifest File
        └── src/                # Functional Source Code
Use code with caution.5. Structural System Configurations📄 Component A: Root Workspace Manifest (/pyproject.toml)toml[project]
name = "monorepo-root"
version = "1.0.0"
dependencies = [] # Root manifest intentionally empty to serve purely as workspace orchestrator.

[tool.pixi.workspace]
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "win-64"]

[tool.pixi.dependencies]
pdm = ">=2.15.0"
pip-audit = ">=2.9.0"
sbom4python = ">=0.10.0"

[tool.pixi.pypi-options]
index-url = "https://pypi.org"
extra-index-urls = ["https://${PRIVATE_REGISTRY_USER}:${PRIVATE_REGISTRY_TOKEN}@my-artifactory-domain.jfrog.io/artifactory/api/pypi/pypi-virtual/simple"]

[tool.pdm.workspace]
members = [
    "apps/*",
    "libs/*"
]

[tool.pixi.tasks]
# 1. Multi-Target Comprehensive Lock Generation
lock-monorepo = "pdm export --format pylock --override-platform=linux --override-platform=macos --override-platform=windows -o pylock.toml"

# 2. Localized Structural Dependency Patch Routine
patch-dependencies = "pdm update --update-reuse"

# 3. Production Only Vulnerability Auditing
audit-prod = "pip-audit -r pylock.toml --skip-editable"

# 4. Filtered Runtime Compliance Export (Excludes Development Assets)
sbom-prod = "sbom4python --requirement pylock.toml --sbom cyclonedx --format json --output-file sbom-runtime.json"

# 5. Full Pipeline Structural Export
sbom-full = "sbom4python --requirement pylock.toml --sbom cyclonedx --format json --output-file sbom-full.json"
Use code with caution.📄 Component B: Shared Library Manifest (/libs/core_utils/pyproject.toml)toml[project]
name = "core-utils"
version = "0.4.2"
dependencies = [
    "pydantic>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
Use code with caution.📄 Component C: Application Consumer Manifest (/apps/api_service/pyproject.toml)toml[project]
name = "api-service"
version = "1.0.0"
dependencies = [
    "fastapi>=0.110.0",
    "core-utils @ file://../../libs/core_utils" # Explicit local relative tracking link
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
Use code with caution.6. Lifecycle Execution Blueprints🔄 Phase 1: Developer Local EnvironmentsInitialize Workspace Nodes: Initialize and link workspace structures inside the localized engineering context.bashpixi init --format pyproject
Use code with caution.Execute Multi-Platform Grid Compile: Transmute package definitions down into a single universal lockfile array.bashpixi run lock-monorepo
Use code with caution.🐳 Phase 2: Production Container Build EngineThe build layer runs a zero-state command path routing through /dev/null to ignore root configuration requirements, building isolated environments directly from the pylock.toml file.dockerfile# ==========================================
# Stage 1: Build & Package Extraction
# ==========================================
FROM ghcr.io/prefix-dev/pixi:latest AS builder
WORKDIR /monorepo

# Define target package at build time
ARG PKG_DIR=apps/api_service

# Selectively pull code trees into build environment
COPY pylock.toml .
COPY libs/libs/ ./libs/
COPY ${PKG_DIR} ./${PKG_DIR}

# Execute explicit isolated compilation target mapping
RUN pixi run --manifest-path /dev/null \
    -p python=3.11 \
    -p pip \
    -- pip install \
    --target=/monorepo/dist-packages \
    --only-binary=:all: \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 311 \
    -r pylock.toml

# Generate matching production compliance asset
RUN pixi run --manifest-path /dev/null -p sbom4python -- \
    sbom4python --requirement pylock.toml --sbom cyclonedx --format json --output-file sbom-runtime.json

# ==========================================
# Stage 2: Minimal Production Image
# ==========================================
FROM python:3.11-slim AS production
WORKDIR /app

# Extract compiled wheel directory structures and isolated application spaces
COPY --from=builder /monorepo/dist-packages /app/dist-packages
COPY --from=builder /monorepo/${PKG_DIR} /app/service
COPY --from=builder /monorepo/sbom-runtime.json /app/sbom.json

ENV PYTHONPATH="/app/dist-packages:/app/service/src"
LABEL org.opencontainers.image.sbom="/app/sbom.json"

EXPOSE 8000
CMD ["python", "-m", "api_service.main"]
Use code with caution.🤖 Phase 3: Self-Healing Automation Pipeline (auto-patch.yml)Runs as a daily recurring background automation agent to identify CVE flags, apply minimal updates, and open isolated Pull Requests.yamlname: Security Automated Patching Bot

on:
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:

jobs:
  patch-vulnerabilities:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Instantiate Pixi Engine
        uses: prefix-dev/setup-pixi@v0.9.4
        with:
          environments: "default"

      - name: Scan Runtime Code for Vulnerabilities
        id: scan
        run: pixi run audit-prod
        continue-on-error: true

      - name: Execute Automated Patch and Re-Lock
        if: steps.scan.outcome == 'failure'
        run: |
          pixi run patch-dependencies
          pixi run lock-monorepo

      - name: Verify Lockfile Status Changes
        id: git-check
        run: |
          if [ -n "$(git status --porcelain pylock.toml)" ]; then
            echo "changed=true" >> $GITHUB_OUTPUT
          else
            echo "changed=false" >> $GITHUB_OUTPUT
          fi

      - name: Generate Automated Remediation PR
        if: steps.git-check.outputs.changed == 'true'
        uses: peter-evans/create-pull-request@v6
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: "security: automated dependency patch for pylock.toml"
          branch: security/auto-patch-pylock
          delete-branch: true
          title: "🔒 Security: Automated Dependency Patch for pylock.toml"
          body: |
            ### 🛠️ Automated Dependency Remediation
            The automated pipeline detected one or more package vulnerabilities using `pip-audit`.

            **Actions Taken:**
            * Run `pdm update --update-reuse` to fetch secure minor versions.
            * Regenerated universal multi-platform `pylock.toml`.
Use code with caution.🧪 Phase 4: Unified Testing & Compliance Platform (ci.yml)Maps the environment across multiple operating systems, authenticates securely against Artifactory repositories, and archives split compliance logs.yamlname: Monorepo Microservice Verification Matrix
on: [push]

jobs:
  test-and-compliance:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        target-app: ["apps/api_service"]
        include:
          - os: ubuntu-latest
            pip-platform: "manylinux2014_x86_64"
          - os: macos-latest
            pip-platform: "macosx_11_0_arm64"
          - os: windows-latest
            pip-platform: "win_amd64"
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Instantiate Pixi Engine
        uses: prefix-dev/setup-pixi@v0.9.4
        with:
          environments: "default"
          auth-host: "my-artifactory-domain.jfrog.io"
          auth-username: ${{ secrets.ARTIFACTORY_USER }}
          auth-password: ${{ secrets.ARTIFACTORY_TOKEN }}

      - name: Synchronize Package Target Runtime
        run: |
          pixi run -p python=3.11 -p pip -- \
            pip install \
            --only-binary=:all: \
            --platform ${{ matrix.pip-platform }} \
            --implementation cp \
            --python-version 311 \
            --index-url "https://${{ secrets.ARTIFACTORY_USER }}:${{ secrets.ARTIFACTORY_TOKEN }}@my-artifactory-domain.jfrog.io/artifactory/api/pypi/pypi-virtual/simple" \
            -r pylock.toml

      - name: Run Targeted Microservice Test Suite
        run: pixi run -p python=3.11 -- python -m pytest ${{ matrix.target-app }}/tests/

      - name: Output Segregated Compliance Artifacts
        if: matrix.os == 'ubuntu-latest'
        run: |
          pixi run sbom-prod
          pixi run sbom-full

      - name: Archive Compliance Assets
        if: matrix.os == 'ubuntu-latest'
        uses: actions/upload-artifact@v4
        with:
          name: structural-sbom-package
          path: |
            sbom-runtime.json
            sbom-full.json
Use code with caution.7. Deterministic Technical OutcomesCryptographic Predictability: Universal pylock.toml pinning guarantees that regardless of platform or architecture, deployments utilize identical pre-computed cryptographic package hashes.Decoupled CI Operations: By eliminating the need for local toolchain configuration files during target executions, pipelines maintain clean, isolated execution states.Immutable Compliance Proofs: Generates strict, production-isolated sbom-runtime.json files that guarantee real-time regulatory compliance visibility, completely free of testing and local configuration overhead.