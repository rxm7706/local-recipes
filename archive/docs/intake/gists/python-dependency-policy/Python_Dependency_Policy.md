Evaluation Tool (Consolidated Description)

The evaluation tool is awrapper over standard Python libraries that resolves dependency manifests into a BOM and collects metadata for risk evaluation.

It leverages common ecosystem tooling such as:

    packaging, importlib.metadata, pip/resolvelib → dependency resolution and version analysis
    PyPI APIs (requests or internal mirrors) → release history and package metadata
    pip-audit / safety → vulnerabilities
    license-expression → license parsing
    optional networkx → dependency graph analysis

What It Collects (Core Signals)

For each package in the resolved graph:

    Release history → version density, recency, freshness percentile
    Python compatibility → runtime support validation
    License → compliance check
    Maintainer presence → basic maturity signal
    Distribution artifacts → wheel vs source risk
    Dependencies → graph depth and fan-out
    Metadata completeness → required fields present or missing

1. Python Runtime
To ensure Wells Fargo applications receive current security fixes to manage risk and exposure to exploits and vulnerabilities, all Python applications must use, at a minimum, the active Python releases published by the Python project.

The two runtimes supported are python from python.org, and miniforge from conda-forge.org. Miniforge Installer, conda tool and conda enviornments are the recommended packaging tool and virtual enviornment management solution for scientific computing. 

https://packaging.python.org/en/latest/guides/tool-recommendations/

2. Dependency Manifest
Python applications must provide a standard dependency manifest at a discoverable path for EPLX (GitHub Actions used in CI and CD) evaluation.

  Dependency manifests should declare only direct dependencies except where additional entries are required to resolve dependency conflicts. All direct dependencies must specify pinned versions.
  
  There are three supported CI pipelines supported today, pip, conda and pixi (limited supported not GA in 2026). 
  Pixi is the next generation of conda, supported by the conda-forge ecosystem, it supports installation from both pypi.org and conda-forge channels. Pixi and ratler-build is expected to be supported more broadly in 2027, in sync with the adoption and migration of the conda-forge ecosystem.

Supported manifest formats include:

pyproject.toml (PEP 621 standard, supporting PEPs 517, 518, 639, 735), requirements.txt, environment.yaml, meta.yaml (v0), recipe.yaml (v1), pixi.toml
requirements.txt (frozen), conda-lock.yml pixi.lock

pylock.toml (PEP 751 standard), poetry.lock uv.lock, pdm.lock are not supported yet, but maybe supported in the future.

3. Dependency Evaluation
EPLX will use a Wells Fargo-developed evaluation package to resolve the dependency manifest into a complete SBOM.

The package will evaluate and analyze both direct and transitive dependencies for:

Python runtime compatibility

Dependency freshness

Known vulnerabilities

License metadata

Dependency graph depth and fan-out

Metadata completeness

Automated evaluation should compare declared dependency constraints against current available package versions to identify libraries that materially lag the current Python ecosystem. For packages with a dense version history we expect pagackages to be in the top 20 percentile of eligible versions.  When the package history is not dense then last eligible version -1 is acceptable. 

4. Metadata Quality
Package Metadata completeness is an indication of package maturity. When metadata is incomplete, ambiguous, or policy thresholds are exceeded, the build must be blocked and the package flagged for review.

Approved exception lists may be maintained and considered by the evaluation package.

5. Deployments
The EPLX evaluation package shall generate a BOM during build and store it as a deployment artifact.

During deployment, Harness shall execute the same evaluation package to verify that the deployed dependency graph matches the approved build BOM. Any additional packages or libraries found will generate SNOW tickets for removal.

