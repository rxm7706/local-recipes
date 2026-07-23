# Unity Data Stack Constitution

<!-- This was the initial Preamble. -->

<!--
The Unity Data Stack is an opinionated start to shared monorepo project dedicated to building a robust, scalable, and maintainable python innersource delivery model for enterprise use.
It allows teams to co-contribute to the build out reusable templates, plugins, libraries, components, services, dashboards, reports, and applications that form the backbone of a python-first engineering platform.
The monorepo model encourages the sharing of code, modules, and best practices built around chosen enterprise standards, enabling teams to deliver high-quality solutions faster while maintaining consistency and reliability across the enterprise.
The Inner-Source Model leverages open-source culture and development practices within the enterprise, fostering collaboration, transparency, and innovation among internal teams.
The Enterprise use requires the selection of certain standards, technologies, tools, and practices that ensure security, compliance, scalability, and maintainability of the solutions built within this monorepo.
The Opinionated start picks certain technologies and practices as defaults to streamline adoption and reduce decision fatigue for teams getting started.
The initial set of solutions were picked from existing innersource python contributions, the projects and principles of the [Linux Foundation](https://www.linuxfoundation.org/) with a focus on Cloud Native Computing Foundation [CNCF](https://www.cncf.io/), and the Linux Foundation Artificial Intelligence and Data [LFAI](https://lfaidata.foundation/)
This constitution establishes the immutable principles and standards that govern all development within this project.
-->

<!-- This was the initial Core Architecture. -->

<!--
- **Local First**: The highest priority is to enable fast local dev loops with per-package pixi environments, comprehensive testing, and clear documentation.
- **Orchestration**: Dagster (>=1.12.0) for asset-based pipeline management
- **Production Deployment**: Red Hat OpenShift Container Platform (OCP) with GitOps (Argo CD)
- **Package Management**: Pixi (conda-forge based, air-gap capable)
- **Data Mesh**: Domain-driven organization with three-layer architecture
- **Data Science**: Kedro as the toolbox for production-ready data science.
- **Web Applications**: Django as the Python web framework, with React as the front end. Django's Primary Role (Web Application): Django is responsible for the user-facing parts: managing user authentication, sessions, serving the React frontend (or acting as a backend for the React app), rendering HTML templates (if necessary), and routing requests for major web pages.
- **API**: FASTAPI for building APIs with Python. FASTAPI's Primary Role (API/Service Layer): FASTAPI is perfect for building high-performance, asynchronous services (APIs, microservices, background task handlers). These services handle data processing, machine learning predictions, or complex calculations. The Integration Point between django and fast api When a user interacts with the Django/React frontend (e.g., clicks a button to retrieve a large dataset or start an analysis), the React client or the Django backend makes an HTTP request to the separate, dedicated FASTAPI service. The FASTAPI service processes the request, potentially interacts with Dagster or Kedro assets, and returns the result (usually JSON) back to the Django/React application to display to the user.
- **MCP**: MCP for connecting an agent to a tool or data.
- **Agents**: A2A provides the standardized language and infrastructure for agents to interact and form collaborative multi-agent systems.
- **Environments**: 12-stage SDLC (public, local, agents, vendor, dev, ci, integration, testing, uat, production, dr, oss)
-->

## Preamble

**WHEREAS** the **Unity Data Stack** is established as an opinionated, shared **monorepo** dedicated to delivering a robust, scalable, and maintainable **Python Inner-Source Engineering Platform** for enterprise use;

**WHEREAS** this project mandates strict adherence to codified standards for security, compliance, and quality, guided by principles including [CNCF](https://www.cncf.io/) and [LFAI](https://lfaidata.foundation/);

**WHEREAS** this Constitution is declared the **single, immutable source of truth** for all principles and specifications, thereby adopting **Spec-Driven Development (SDD)** as the mandated governance model;

**NOW, THEREFORE, BE IT RESOLVED** that **Autonomous Agents** (including, but not limited to, `spec-kit` and `specify`) are hereby empowered as the primary operational entity to **audit, generate, and enforce** all standards defined herein, ensuring **non-negotiable consistency** and accelerated delivery across the entire project.

---

# I. Mission Statement

The primary objective is **To deliver the Unity Data Stack** as a **production-ready, enterprise-scale** data platform. This delivery is governed by the mandate for a **Data Mesh Architecture**, the operational necessity for **Air-Gapped Deployments**, and the continuous pursuit of world-class developer experience through **standardized tooling and practices**.

# II. Core Architectural Standards (Mandates)

These standards are the non-negotiable, foundational technology choices for the Unity Data Stack. Compliance is automatically enforced and audited by Autonomous Agents.

| Component | Standard Mandate | Enforcement Priority |
| :--- | :--- | :--- |
| **Local First (Architecture)** | **MANDATE:** The **Local First** principle requires that all components support rapid, isolated development loops via per-package **Pixi environments**, mandatory comprehensive testing, and clear developer documentation. | CRITICAL |
| **Package Management (Implementation)** | **Pixi** (conda-forge based) is the required package and environment manager, ensuring **air-gap capability** and deterministic dependency resolution. | CRITICAL |
| **Production (Implementation)** | Deployment shall be exclusively managed via **Red Hat OpenShift Container Platform (OCP)**, governed by a **GitOps** workflow enforced through **Argo CD**. | CRITICAL |
| **MCP (Communication Transport)** | **MANDATE:** **MCP** (Multi-Agent Communication Protocol) is the required standard defining the **data structure and transport mechanism** for all synchronous and asynchronous agent messages (the *HOW*). | CRITICAL |
| **A2A (Collaborative Language)** | **MANDATE:** **A2A** (Agent-to-Agent) provides the standardized **operational language, semantics, and contractual expectations** for agents to interact and form collaborative multi-agent systems (the *WHAT*). | CRITICAL |
| **REST (Architecture)** | **MANDATE:** **REST API** principles are the **foundational standard** for all API communication, enabling secure, cross-company agent and inter-service interaction. | CRITICAL |
| **Environments (Implementation)** | The system must support a **12-stage SDLC** defined as: `public`, `local`, `agents`, `vendor`, `dev`, `ci`, `integration`, `testing`, `uat`, `production`, `dr`, and `oss`. | CRITICAL |
| **Orchestration (Implementation)** | **Dagster (>= 1.12.0)** is the sole platform for asset-based pipeline definition and execution. | HIGH |
| **Data Mesh (Architecture)** | All data assets must conform to a **Domain-Driven Design (DDD)**, implemented as a three-layer architecture (**Raw, Curated, Consumption**). | HIGH |
| **Data Science (Implementation)** | **MANDATE:** **Kedro** is the sole approved toolbox for building production-ready, highly reproducible data science and machine learning projects, mandating adherence to established Kedro project and **data layering** structures. | HIGH |
| **Web Application (Implementation)** | **MANDATE:** **Django** is the **preferred** Python backend framework, coupled with **React** for all **user-facing applications**. Django's primary role is user authentication, sessions, UI routing, and serving the React frontend. | HIGH |
| **RESTful API (Implementation)** | **MANDATE:** **FASTAPI** is the **preferred** framework for building high-performance, asynchronous Python services. These services are the mandated HTTP integration layer between the Django/React web application and core data/agent logic. | MEDIUM |

## Article I: Project Identity

### Section 1.1: Mission Statement
Enable organizations to build, deploy, and operate data pipelines at scale with:
- **Reproducibility**: Lock files, version pinning, deterministic builds
- **Enterprise Compatibility**: Air-gap support, Artifactory integration, OpenShift native
- **Developer Experience**: Modern tooling (Pixi, Ruff, Pyright), comprehensive testing, clear documentation
- **Data Mesh Principles**: Domain ownership, data as a product, federated governance

### Section 1.2: Technology Stack
- **Languages**: Python 3.14+ (preferred), 3.12, 3.13 (supported); Node.js 24.x (frontend tooling)
- **Orchestration**: Dagster (primary), MLflow, Airflow (legacy support), Nebari, dbt-core
- **Frameworks**: FastAPI (>=0.121.0), Django (>=5.2.8), Wagtail, Kedro
- **Data Storage**: DuckDB (dev), PostgreSQL (prod), MongoDB, Redis, MinIO (S3-compatible)
- **Data Processing**: Polars, Pandas, Dask, PyArrow, Ibis, daft
- **Container Platform**: Podman (preferred), Docker (compatible), OpenShift/Kubernetes
- **Quality Tools**: Ruff (lint/format), Pyright (types), Pytest (testing), Pre-commit hooks, SQLFluff
- **Package Management**: Pixi (>=0.59.0 primary), Conda-forge (source), Artifactory (enterprise mirror)
- **AI/Agentic**: **MCP, A2A SDK** (Mandated communication protocols for all Autonomous Agents), FastMCP, Django MCP Server

### Section 1.3: Repository Structure
Monorepo workspace with:
- `src/shared/packages/` - Shared utilities (common)
- `src/platform/data-platform/infrastructure/` - 11 infrastructure services
- `src/tech-domains/` - 11 domain-driven packages (ccibt, cdo, cdxo, ct, cto, customer, dti, eft, ics, ohot, tcoo)
- `config/` - Configuration management (airgap, environments, feature-flags, secrets)
- `docs/` - Comprehensive documentation (including specs)
- `templates/` - Copier templates for **Agentic Code Generation**
- `vendors/` - Pre-staged binaries for air-gapped environments

---

## Article II: Pixi-First Package Management (AGENT DEPENDENCY SPEC)

### Section 2.1: Primary Principle
**ALL package management MUST use Pixi.** Direct pip usage is strictly prohibited. Pixi provides the deterministic environment specification necessary for Agent reproducibility.

### Section 2.2: Rationale
- **Enterprise Compatibility**: Works in air-gapped environments with Artifactory
- **Reproducibility**: Lock files ensure consistent environments across local development, CI, and **Autonomous Agents**.
- **Multi-Platform**: Supports linux-64, osx-64, osx-arm64, win-64
- **OpenShift Native**: Compatible with containerized deployments

### Section 2.3: Mandated Commands
```bash
# CORRECT - Always use these
pixi add <package>                    # Add dependencies
pixi add --feature dev <package>      # Add dev dependencies
pixi run <task-name>                  # Run tasks
pixi install --all                    # Install all environments
pixi exec <command>                   # Execute in pixi environment

# FORBIDDEN - Never use these (Blocked by Agentic Enforcement)
pip install <package>                 # ❌ BLOCKED
pip3 install <package>                # ❌ BLOCKED
python -m pip install <package>       # ❌ BLOCKED
```

### Section 2.4: Enforcement
- **Autonomous Agents** prevent pip usage during pre-commit and CI.
- CI validates no direct pip calls.
- Code reviews must verify Pixi compliance.

### Section 2.5: Exceptions
Exceptions require:
1. Documented justification in ADR (Architecture Decision Record)
2. Team approval
3. Plan for migration back to Pixi
4. Temporary time-boxed exemption

---

## Article III: Spec Validation (NON-NEGOTIABLE)

### Section 3.1: Spec Coverage Requirements
- **Dagster Assets**: 100% coverage (every asset must have tests/specs validated)
- **Python Modules**: 80% minimum code coverage
- **New Code**: Specs (tests) written BEFORE implementation
- **Bug Fixes**: Regression spec (test) required before fix

### Section 3.2: Validation Structure (Test Structure)
```
tests/
├── unit/              # Pure functions, business logic (Spec Checks)
├── integration/       # Database, API, service interactions (Contract Validation)
└── assets/            # Dagster asset tests (Input/Output Spec Validation)
```

### Section 3.3: Asset Testing Requirements
Every Dagster asset MUST have tests covering:
1. **Input Validation**: Schema, data types, constraints
2. **Transformation Logic**: Business rules, calculations
3. **Output Schema**: Expected structure, types (The Data Product Contract)
4. **Edge Cases**: Empty data, nulls, duplicates
5. **Dependencies**: Upstream asset integration

### Section 3.4: Spec Validation Commands
```bash
pixi run test                  # Run all Spec Validation
pixi run test-<package>        # Validate specific package
pixi run test --cov            # With coverage report
```

### Section 3.5: CI Gate
- All Spec Validation must pass before merge.
- Coverage must not decrease.
- Asset specs required for new Dagster assets.

---

## Article IV: Agentic Quality Enforcement (NON-NEGOTIABLE)

### Section 4.1: Linting
- **Tool**: Ruff (Python linter and formatter)
- **Config**: pyproject.toml in each package
- **Rules**: Enforced via pre-commit hooks (executed by the local Agent)
- **Command**: `pixi run lint`

### Section 4.2: Formatting
- **Tool**: Ruff format (Python), Taplo (TOML), Prettier (YAML)
- **Style**: Black-compatible formatting
- **Enforcement**: Pre-commit hooks auto-format (Agentic Auto-correction)
- **Command**: `pixi run format`

### Section 4.3: Type Checking
- **Tool**: Pyright (primary), Mypy (supplemental)
- **Requirement**: Type hints for all functions, assets (Type Spec)
- **Strict Mode**: Enabled for new packages
- **Command**: `pixi run lint` (includes type checking)

### Section 4.4: Security Scanning
- **Tools**: Bandit (code security), Safety (dependency vulnerabilities)
- **Frequency**: Every commit (pre-commit), every PR (CI)
- **Response**: Critical vulnerabilities block merge (Agent intervention)

### Section 4.5: Pre-Commit Hooks
All quality checks run automatically:
```bash
pixi run pre-commit            # Run all local Agent checks
pixi run check-all             # Run ALL quality checks (matches CI enforcement)
```

Hooks include:
- Ruff linting and formatting
- TOML/YAML validation
- Type checking
- Security scans
- No direct pip usage check
- Trailing whitespace removal
- Large file prevention

### Section 4.6: Quality Gate
Before any commit:
```bash
pixi run check-all
```
This matches exactly what CI runs - if this passes locally, the **CI Agent** will pass the check.

---

## Article V: Specification Standards (The Agent Contract)

### Section 5.1: Code Specifications (Docstrings)
- **Docstrings**: Required for all functions, classes, Dagster assets
- **Format**: Google-style or NumPy-style docstrings
- **Type Hints**: Required - docstrings supplement, not replace
- **Examples**: Include usage examples for complex functions (Operational Spec)

### Section 5.2: Dagster Asset Metadata Spec
Every asset **metadata** MUST document the data product's contract, allowing Agents to audit and discover:
```python
@asset(
    description="Clear description of what this asset produces",
    metadata={
        "owner": "team-name",
        "domain": "customer|transaction|profile|...",
        "layer": "raw|curated|consumption", # Updated Layer Spec
        "update_frequency": "daily|hourly|...",
    }
)
def my_asset(...):
    """
    Detailed description of transformation logic (The Implementation Spec).

    Args:
        upstream_asset: Description

    Returns:
        DataFrame with schema: ... (The Output Data Contract)
    """
```

### Section 5.3: README Requirements
Every major directory must have a README.md:
- Purpose and overview
- Setup instructions
- Usage examples
- Dependencies and integration points (Contractual Dependencies)
- Contact/ownership information

### Section 5.4: Architecture Decision Records (ADRs)
Major technical decisions require ADRs in `docs/architecture/decisions/`, serving as the rationale spec for Agents:
- Context and problem statement
- Considered alternatives
- Decision and rationale
- Consequences (positive and negative)

### Section 5.5: Conciseness Principle
- Specs should be clear and complete, not verbose.
- Prefer 10-30% shorter documentation when possible.
- Code should be self-documenting; comments explain *why* (rationale), not *what* (implementation).

---

## Article VI: 12-Stage SDLC Environment Spec

### Section 6.1: 12-Stage SDLC Environment Model
The full deployment pipeline structure is mandated to ensure air-gapped compliance and security segmentation.


| # | Environment | GitFlow Branch | Data Classification | Network | Database |
|---|-------------|----------------|---------------------|---------|----------|
| 1 | **public** | `main/*` | Public | Internet | DuckDB |
| 2 | **local** | `feature/*` | Deidentified | AirGap | DuckDB |
| 3 | **agents** | `feature/*` | Deidentified | AirGap | DuckDB |
| 4 | **vendor** | `feature/*` | Proprietary | Internet | DuckDB |
| 5 | **dev** | `develop` | Deidentified | Internet | DuckDB |
| 6 | **ci** | All (PR) | Deidentified | AirGap | DuckDB |
| 7 | **integration** | `develop` | Deidentified | AirGap | PostgreSQL |
| 8 | **testing** | `release/*` | Deidentified | AirGap | PostgreSQL |
| 9 | **uat** | `release/*` | Restricted | AirGap | PostgreSQL |
| 10 | **production** | `main` | Restricted | AirGap | PostgreSQL |
| 11 | **dr** | `main` | Restricted | AirGap | PostgreSQL |
| 12 | **oss** | `main/*` | Public | Internet | DuckDB |

### Section 6.2: Data Classification
- **Public**: Non-sensitive, OSS compatible, no access restrictions
- **Deidentified**: Anonymized data, no PII, safe for development
- **Proprietary**: Third-party vendor data, restricted distribution
- **Restricted**: Sensitive/PII data, requires access controls and audit logging

### Section 6.3: Configuration Management
- **Location**: `config/environments/`
- **Format**: YAML or TOML configuration files
- **Loading**: Environment variables override config files
- **Validation**: Schema validation on load (Agent enforcement)

### Section 6.4: Environment Variables (Agent-Injectable)
```python
# CORRECT - Environment-aware
DATABASE_URL = os.getenv("DATABASE_URL", "duckdb://local.db")
APP_ENV = os.getenv("APP_ENV", "dev")

# WRONG - Hardcoded (Fails Agent Audit)
DATABASE_URL = "postgresql://prod-db:5432/mydb"  # ❌ Never hardcode
```

### Section 6.5: Secret Management
- **Never commit secrets** to version control
- Use `.secrets` file (gitignored) for local development
- Use environment variables or secret management service (production)
- Validate presence of required secrets at startup

### Section 6.6: Feature Flags
- Centralized in `config/feature-flags/`
- Environment-specific toggles (dev.json, integration.json, testing.json, uat.json, production.json)
- Enable/disable features without code changes
- Document flag purpose and owner

---

## Article VII: Data Mesh Architecture (Data Product Spec)

### Section 7.1: Domain Organization
**Current Tech Domains (11 total)**:
- ccibt - Cross-Channel Integration & Business Technology
- cdo - Chief Data Office
- cdxo - Chief Digital Experience Office
- ct - Corporate Technology
- cto - Chief Technology Office
- customer - Customer Domain (reference implementation)
- dti - Digital Technology & Innovation
- eft - Electronic Funds Transfer
- ics - International Card Services
- ohot - Online & Hospitality Operations Technology
- tcoo - Technology Chief Operating Office

### Section 7.2: Three-Layer Architecture
All data products must adhere to this architecture.
```
Raw Layer (Ingestion Spec)
├── Source data as-is
├── Minimal transformation
└── Partitioned by ingestion time

Curated Layer (Transformation Spec)
├── Cleaned and validated
├── Business rules applied
└── Deduplicated

Consumption Layer (API/Query Spec)
├── Aggregated for analysis
├── Joined across domains
└── Optimized for queries
```

### Section 7.3: Asset Naming Convention
**Format**: `<domain>_<layer>_<entity>_<verb>`

**Examples**:
- `customer_raw_profile_ingest` - Raw customer profile ingestion
- `customer_curated_profile_clean` - Cleaned customer profiles
- `customer_consumption_profile_aggregate` - Aggregated customer analytics
- `transaction_raw_payment_ingest` - Raw payment transaction ingestion
- `transaction_curated_fraud_detect` - Fraud detection on transactions

**Rules**:
- Use lowercase with underscores
- Domain must match tech domain name
- Layer must be: **raw, curated, or consumption**
- Entity is the business object
- Verb describes the transformation

### Section 7.4: Domain Boundaries
- Each domain has clear ownership
- Cross-domain dependencies via published assets
- No direct database access across domains
- APIs or asset dependencies for data sharing

### Section 7.5: Data as a Product
Each domain must:
- Document data contracts (schemas)
- Maintain backward compatibility
- Version breaking changes
- Monitor data quality
- Provide usage documentation

---

## Article VIII: Spec-Driven Collaboration (Workflow)

### Section 8.1: Branching Strategy
Based on **Gitflow**, enforced by Agents:
- `develop` - Default integration branch (NOT `main`)
- `feature/*` - New features (branch from develop)
- `fix/*` - Bug fixes (branch from develop)
- `hotfix/*` - Production hotfixes (branch from main)
- `release/*` - Release preparation
- `chore/*` - Maintenance tasks

**Important**: This repository uses `develop` as the default branch, not `main`.

### Section 8.2: Conventional Commits (Agent Trigger Spec)
**Format**: `<type>(<scope>): <description>`

**Types**:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `chore` - Maintenance tasks
- `refactor` - Code refactoring
- `test` - Adding/updating tests
- `ci` - CI/CD changes
- `perf` - Performance improvements

**Examples**:
```
feat(customer): add email validation asset
fix(dagster): correct partition configuration
docs(api): update REST API documentation
chore(deps): update dagster to 1.12.2
```

### Section 8.3: Pull Request Requirements (Agent Audit Gates)
Before merge, PRs must have:
1. ✅ All **Spec Validation** passing
2. ✅ Code coverage maintained or increased
3. ✅ **Agentic Quality Checks** passing (`pixi run check-all`)
4. ✅ Documentation/Specs updated
5. ✅ At least one human approval (Contractual Sign-off)
6. ✅ No merge conflicts
7. ✅ Conventional commit format

### Section 8.4: Code Review Standards (Human Contract Sign-off)
Reviewers must verify:
- Pixi-first compliance (no pip)
- Test coverage (especially asset specs)
- Documentation completeness
- Type hints present
- Error handling implemented
- Security considerations addressed
- Performance implications considered

---

## Article IX: Dagster Best Practices (Asset Specification)

### Section 9.1: Asset Definitions
```python
@asset(
    description="Clear, concise description (The Data Product Spec)",
    metadata={
        "owner": "team-name",
        "domain": "domain-name",
        "layer": "raw|curated|consumption",
    },
    retry_policy=RetryPolicy(max_retries=3, delay=60),
    partitions_def=DailyPartitionsDefinition(start_date="2025-01-01"),
)
def asset_name(context, upstream_asset: pd.DataFrame) -> pd.DataFrame:
    """Detailed docstring with transformation logic (The Implementation)."""
    context.log.info("Processing asset")
    # Implementation
    return result
```

### Section 9.2: Asset Naming and Organization
- Follow data mesh naming: `<domain>_<layer>_<entity>_<verb>`
- Group by domain in directory structure
- Clear dependencies via function parameters
- Explicit return types (Contract enforcement)

### Section 9.3: Error Handling
```python
@asset(retry_policy=RetryPolicy(max_retries=3, delay=60))
def my_asset(context):
    try:
        # Asset logic
        result = process_data()
        context.log.info(f"Processed {len(result)} records")
        return result
    except SpecificException as e:
        context.log.error(f"Failed to process: {e}")
        raise  # Let retry policy handle
```

### Section 9.4: Testing Assets
```python
def test_customer_profile_clean():
    # Setup
    context = build_asset_context()
    input_data = pd.DataFrame({"email": ["test@example.com"]})

    # Execute
    result = customer_processed_profile_clean(context, input_data)

    # Verify (Against the Output Spec)
    assert len(result) == 1
    assert "email_validated" in result.columns
```

### Section 9.5: Observability
- Use `context.log` for all logging
- Log key metrics (record counts, processing time)
- Include structured metadata
- Track data quality metrics

---

## Article X: Continuous Spec Enforcement (CI/CD)

### Section 10.1: Continuous Integration
**Triggers**: Every PR, every push to develop/main

**CI Workflow (Agent Execution)**:
1. Install pixi environment (Spec Dependency Check)
2. Run `pixi run check-all` (Agentic Quality Enforcement)
   - Pre-commit hooks
   - Linting (ruff, pyright, taplo, yamllint)
   - Formatting checks
   - Security scans
3. Run `pixi run test` with coverage (Spec Validation)
4. Build Docker images
5. Validate pixi compliance (no pip usage)
6. Link checking (documentation)

### Section 10.2: GitHub Actions Workflows
- `ci-shared.yml` - Shared packages CI
- `ci-domains.yml` - Domain services CI
- `link-check.yml` - Documentation link validation
- `validate-configs.yml` - Configuration validation
- `pr-title-conventional-lint.yml` - PR title format

### Section 10.3: Local CI Testing
Before pushing, run CI locally:
```bash
pixi run act-ci-all            # Run all CI workflows locally (Local Agent Check)
pixi run act-ci-shared         # Shared packages only
pixi run act-ci-domains        # Domain services only
```

### Section 10.4: Deployment Pipeline (12-Stage)
- **Local/Dev**: Auto-deploy on merge to develop
- **Integration**: Auto-sync from develop (GitOps)
- **Testing**: Manual promotion from integration
- **UAT**: Manual promotion with restricted data access
- **Production**: Manual promotion with multi-approval
- **DR**: Mirror of production with manual sync

### Section 10.5: GitOps Architecture (Agent Deployment Spec)
All production deployments are managed by a dedicated Agent system.
```
Git (Source of Truth / Spec) → Argo CD (GitOps Agent Engine) → Kubernetes (Runtime)
```
**Key Components**:
- **Argo CD**: GitOps continuous delivery for Kubernetes
- **Kustomize**: Configuration overlays per environment (Environment Spec)
- **Sealed Secrets**: GitOps-safe secret management
- **Image Updater**: Automatic image updates for dev environments

**GitOps Workflow**:
- Development: Auto-sync enabled (push to Git → automatic deployment)
- Production: Manual sync required (approval gates)

**Configuration**: `config/gitops/` with Kustomize overlays

### Section 10.6: Container Builds
- Podman/Docker builds for all services
- OCI-compliant container images
- Multi-stage builds for minimal image size
- Helm charts for Kubernetes/OpenShift deployment

---

## Article XI: Performance and Scalability

### Section 11.1: Asset Performance Monitoring
- Track execution time for all assets
- Alert on assets exceeding thresholds (Agent Alert Spec)
- Regular performance reviews
- Optimize slow-running assets

### Section 11.2: Database Query Optimization
- Use query profiling (EXPLAIN ANALYZE)
- Create appropriate indexes
- Avoid N+1 queries
- Use batch operations for bulk inserts

### Section 11.3: Partitioning Strategy
For large datasets:
- Daily partitions for event data
- Monthly partitions for historical data
- Partition pruning for queries
- Backfill strategies documented

### Section 11.4: Memory Management
- Profile memory usage for large datasets
- Use generators/iterators for streaming
- Chunk large DataFrames
- Monitor memory in production

### Section 11.5: Caching
- Cache expensive computations
- Use Dagster's memoization for dev
- Redis for distributed caching
- Document cache invalidation strategy

---

## Article XII: Security and Compliance

### Section 12.1: Secrets Management
- Never commit secrets to git
- Use `.secrets` file (gitignored) for local dev
- Environment variables for production
- Rotate secrets regularly
- Audit secret access

### Section 12.2: Principle of Least Privilege
- Database users have minimal permissions
- Service accounts scoped to necessary resources
- No shared credentials
- Regular access reviews

### Section 12.3: Input Validation
All external inputs must be validated:
- Schema validation for data files
- Type checking for API inputs
- Sanitization to prevent injection
- Whitelist approach for allowed values

### Section 12.4: Dependency Management
- Regular dependency updates (`pixi update`)
- Security scanning (Safety, Bandit)
- Pin versions in lock files
- Review dependency licenses

### Section 12.5: Security Scans
- **Bandit**: Python code security (runs in pre-commit)
- **Safety**: Dependency vulnerability scanning
- **Trivy**: Container image scanning (in CI)
- Critical vulnerabilities block deployment (Agent Intervention)

### Section 12.6: Data Privacy and Compliance
- GDPR compliance for personal data
- Data retention policies enforced
- PII masking in non-production environments
- Audit logging for data access
- Right to deletion implemented

---

## Article XIII: Simplicity Gate

### Section 13.1: Principle of Simplicity
**Start simple. Add complexity only when justified.** (Simplicity Spec)

### Section 13.2: Initial Implementation
- Choose the simplest solution that works
- Avoid premature optimization
- Defer architectural decisions when possible
- Implement minimal viable features first

### Section 13.3: Adding Complexity
Complexity is justified when:
- Performance requirements demand it (with benchmarks)
- Scalability requirements proven (with metrics)
- Reliability improvements demonstrated (with SLOs)
- Business value clearly articulated

Complexity requires:
1. ADR documenting decision
2. Simpler alternatives considered
3. Metrics showing improvement
4. Plan to reduce complexity if assumptions change

### Section 13.4: Refactoring First
Before adding features:
- Refactor to simplify
- Remove dead code
- Consolidate duplicates
- Improve clarity

### Section 13.5: YAGNI Principle
"You Aren't Gonna Need It"
- Don't build features speculatively
- Don't add configuration for "future flexibility"
- Don't abstract before you have 2+ use cases
- Wait until requirements are clear

---

## Article XIV: Python Version Support

### Section 14.1: Supported Versions
- **Python 3.14+**: Preferred development version
- **Python 3.12**: Fully supported (legacy baseline)
- **Python 3.13**: Fully supported

### Section 14.2: Compatibility Requirements
- Code must work across all supported versions
- Use version guards for version-specific features
- Test matrix in CI for all versions

### Section 14.3: CI Matrix Testing
```yaml
strategy:
  matrix:
    python-version: [py312, py313, py314]
```

### Section 14.4: Deprecation Policy
- Support each Python version for 2 years after release
- Deprecation warnings 6 months before drop
- Migration guide for version upgrades

---

## Appendix A: Quick Reference

### Essential Commands
```bash
# Environment setup
pixi install                        # Install default environment
pixi install --all                  # Install all environments (dev, ci, agents, etc.)

# Quality checks (run before committing)
pixi run check-all                  # ALL Agent checks (matches CI exactly)
pixi run lint                       # Lint Python, TOML, YAML
pixi run format                     # Format all code
pixi run test                       # Run all Spec Validation

# Development services
pixi run dev                        # Start full stack (Podman Compose)
pixi run dagster-dev                # Dagster UI on port 3000
pixi run start-duckdb               # DuckDB server on port 8082
pixi run start-profile              # Profile service on port 8001

# Package-specific
pixi run test-<package>             # Test specific package
pixi run lint-<package>             # Lint specific package

# Container operations
pixi run build-all                  # Build all service images
pixi run int-up                     # Integration environment
pixi run qa-up                      # QA environment

# Local CI testing
pixi run act-ci-all                 # Run all CI workflows locally (Local Agent Check)
```

### File Structure Overview
```
unity-data-stack/
├── src/
│   ├── shared/packages/common/          # Shared utilities
│   ├── platform/data-platform/
│   │   └── infrastructure/              # 11 infrastructure services
│   └── tech-domains/                    # 11 domain packages
├── config/                              # Configuration management
│   ├── airgap.conf                     # Air-gap/enterprise settings
│   ├── environments/                    # Environment configs
│   └── feature-flags/                   # Feature toggles
├── docs/                                # Documentation (Specs, ADRs)
├── templates/                           # Copier templates (Agent Generator Spec)
├── vendors/                             # Pre-staged binaries (air-gap)
├── pixi.toml                           # Workspace package management
├── pixi.lock                           # Lock file (committed)
└── CLAUDE.md                           # AI assistant memory bank (Agent State)
```

### Data Mesh Layers
- **Raw Layer**: Source data as-is, minimal transformation
- **Curated Layer**: Cleaned, validated, business rules applied
- **Consumption Layer**: Aggregated, joined, optimized for queries

### Asset Naming Examples
- `customer_raw_profile_ingest`
- `customer_curated_profile_clean`
- `customer_consumption_profile_aggregate`
- `transaction_raw_payment_ingest`
- `transaction_curated_fraud_detect`

---

## Governance (Agent Mandate and Protocol)

### Constitutional Authority
This constitution supersedes all other development practices and guidelines. In case of conflict, constitutional principles take precedence.

### Amendment Process
Amendments require:
1. Proposal with rationale (ADR format)
2. Team discussion and consensus (Human Sign-off)
3. Documentation of changes (Spec Update)
4. Migration plan if existing code affected
5. Version bump and ratified date update

### Enforcement
- **Autonomous Agents** perform mandatory audits on all PRs.
- Violations must be documented and justified (if approved).
- Repeated violations trigger architecture review.
- Complexity additions require explicit justification.

### Living Document
This constitution is a living document:
- Regular reviews (quarterly)
- Feedback-driven improvements
- Adaptation to new tools and practices
- Balance between stability and evolution

### Agent Mandate
All Autonomous Agents (including large language models and operational bots) shall operate under this Mandate:
- **Primary Directive**: Enforce **Spec-Driven Development (SDD)** by auditing compliance with the Constitution.
- **Protocol**: All inter-agent communication MUST use **MCP** (transport) and **A2A** (language).
- **Tooling**: Agents MUST use **Pixi** to create deterministic environments for all operations and code generation.
- **Reporting**: Agents MUST report audit failures by referencing the specific section and clause of this Constitution that was violated.

---

**Version**: 1.2.0
**Ratified**: 2025-11-20
**Last Amended**: 2025-11-20
**Next Review**: 2026-02-20

### Amendment Log
- **1.2.0** (2025-11-20): Refined for Agent-Driven, Spec-Driven Development (SDD).
  - Preamble heavily reinforced Agent authority and SDD mandate.
  - Renamed key sections: "Test-Driven Development" -> "Spec Validation"; "Code Quality" -> "Agentic Quality Enforcement"; "Documentation" -> "Specification Standards"; "CI/CD" -> "Continuous Spec Enforcement."
  - Renamed Data Mesh Layers to the mandatory **Raw, Curated, Consumption** standard (from Processed/Analytics).
  - Updated Governance section to define the **Agent Mandate** and protocol.
  - Added specific image tags for SDLC, Gitflow, Data Mesh, and GitOps diagrams.
- **1.1.0** (2025-11-20): Aligned with actual codebase state
  - Updated to 12-stage SDLC environment model with data classification
  - Added GitOps architecture with Argo CD details
  - Updated Python version preference to 3.14+ (from 3.12)
  - Expanded technology stack with frameworks, data processing, and AI/agentic tools
  - Updated deployment pipeline to match 12-environment model
