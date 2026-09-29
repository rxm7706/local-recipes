# Architecture Specification: Automated Security Scanning & PR Generation Engine

## 1. System Overview
This system is an automated, hybrid object-relational pipeline designed to ingest code from upstream repositories (GitHub/GitHub Enterprise), analyze dependencies, execute security scans, and automatically generate pull requests to fix vulnerabilities. 

It leverages **PostgreSQL** as the single source of truth for both relational orchestration metadata and raw Git history via the **`gitgres`** extension. Dependency parsing and PR interactions are offloaded to specialized Go binaries (**`git-pkgs`** ecosystem), all orchestrated by a **Python application engine**.

## 2. Technology Stack
*   **Orchestrator:** Python (FastAPI / Celery or similar async task worker).
*   **Database:** PostgreSQL with the `gitgres` C-extension enabled (requires `pgcrypto`).
*   **Git Interactions:** `pygit2` (linked against the custom `gitgres` libgit2 ODB backend).
*   **Dependency Engine:** `git-pkgs/manifests` (Go binary called via `subprocess`).
*   **Upstream Sync (Forge API):** `git-pkgs/forge` (Go binary/library for unified PR creation).
*   **Environment Management:** Conda / Pixi (for deterministic bundling of Python, Postgres, and compiled binaries).

## 3. Database Schema

The database relies on a hybrid schema. `gitgres` provides the native Git storage and tree traversal functions, while the application schema handles orchestration.

### 3.1 Core Gitgres Schema (Native)
*Do not implement these manually; they are created via `CREATE EXTENSION gitgres CASCADE;`*
*   `repositories (id serial, name text)`: Tracks Git repo targets.
*   `objects (repo_id, oid bytea, type smallint, size integer, data bytea)`: The raw Git ODB.
*   `refs (repo_id, name text, target bytea)`: The Git RefDB (branch pointers).
*   `reflog (...)`: Git reference history.
*   `commits_view` / `tree_entries_view`: Materialized views parsing `objects.data` into standard Git metadata (author, message, paths).
*   `git_ls_tree_r(repo_id, commit_oid)`: Recursive PL/pgSQL function to map a commit to its file tree.

### 3.2 Application Schema (Orchestration)
*To be implemented via SQLAlchemy or equivalent Python ORM.*
```sql
CREATE TABLE app_repositories (
    repo_id integer PRIMARY KEY REFERENCES repositories(id), -- Links to gitgres
    remote_url text UNIQUE NOT NULL,
    default_branch text DEFAULT 'main'
);

CREATE TABLE dependency_graphs (
    repo_id integer REFERENCES app_repositories(repo_id),
    commit_sha bytea, -- Links to git_objects
    manifest_path text NOT NULL,
    parsed_json jsonb NOT NULL,
    PRIMARY KEY (repo_id, commit_sha, manifest_path)
);

CREATE TABLE scan_jobs (
    job_id uuid PRIMARY KEY,
    repo_id integer REFERENCES app_repositories(repo_id),
    commit_sha bytea,
    status text NOT NULL, -- 'QUEUED', 'SCANNING', 'CLEAN', 'VULNERABLE'
    findings jsonb
);
```

## 4. Pipeline Workflow Execution

### Phase 1: Ingestion & Storage (Webhook Trigger)
1.  **Webhook:** Upstream GitHub sends a webhook on `push` to the Python engine.
2.  **Fetch:** Python orchestrator invokes `pygit2` (configured with the `gitgres` ODB backend) to fetch the remote repo.
3.  **Storage:** `gitgres` intercepts the objects, storing blobs/trees directly into the `objects` table and updating `refs`.
4.  **Refresh:** The Python engine runs `REFRESH MATERIALIZED VIEW commits_view;` to make the new history queryable.

### Phase 2: Manifest Resolution (Dependency Parsing)
1.  **Locate File:** Python queries `git_ls_tree_r(repo_id, latest_commit_sha)` to find files like `package.json` or `requirements.txt`.
2.  **Extract Data:** Execute `SELECT data FROM objects WHERE oid = [manifest_oid];` to pull the raw text blob directly into Python memory (bypassing disk).
3.  **Parse (git-pkgs):** Pipe the raw byte string to the `git-pkgs/manifests` binary via `subprocess`.
4.  **Persist:** Capture the JSON output from `manifests` and save it to the `dependency_graphs` table.

### Phase 3: Security Scanning (CodeQL / AST)
1.  **Materialize:** Because external SAST tools require a POSIX filesystem, query the full tree for the latest commit and stream all blobs to an ephemeral disk volume (e.g., `/tmp/scan_job_{id}`).
2.  **Execute:** Run the security scanner against the ephemeral volume.
3.  **Record & Cleanup:** Parse the scanner output, save CVE findings to the `scan_jobs` table, and delete the ephemeral volume.

### Phase 4: Remediation & PR Generation
1.  **Patch Code:** Python determines the fix (e.g., bumping a dependency version). Using `pygit2`, it modifies the file in memory, creates a new blob, updates the tree, and authors a new commit in `gitgres`.
2.  **Create Branch:** Update the `refs` table in `gitgres` to point a new branch (e.g., `refs/heads/fix-cve-123`) to the new commit.
3.  **Upstream Sync:** Python invokes the `git-pkgs/forge` binary/library.
4.  **PR Creation:** `git-pkgs/forge` handles authentication, pushes the branch to GitHub/GH Enterprise, and opens the PR cleanly.

## 5. Development & Deployment Notes
*   **Gitgres Packaging:** `gitgres` must be packaged via Conda-forge to ensure `libgit2` and `pgcrypto` headers align correctly across environments. (A `recipe.yaml` is provided out of band).
*   **Go Binary Wrapping:** Create explicit Python wrapper classes to interface with the Go binaries (`git-pkgs/manifests` and `git-pkgs/forge`), ensuring standard `stdout/stderr` error handling.

## 6. Implementation Directives for the LLM/Developer
Based on this specification, please implement the following modular components:
1.  **Database Models:** SQLAlchemy configurations bridging the native `gitgres` tables and the custom orchestration schema.
2.  **Git Interface:** A Python class utilizing `pygit2` configured to mount the `gitgres` backend for fetch/commit operations.
3.  **Go Wrappers:** Python service classes using `subprocess` to orchestrate `git-pkgs/manifests` and `git-pkgs/forge`.
4.  **Pipeline Orchestrator:** The main async function that strings together Phase 1 through Phase 4 based on a webhook payload.