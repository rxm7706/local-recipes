# Technical Specification: Local OCP Development Hybrid Environment

> Operator-authored intake (received 2026-08-22, verbatim). Source input for
> `docs/dreams/local-ocp-hybrid-environment.md` — read the Dream's
> convergence map before acting on any phase; several phases land on
> machinery the fleet already ships (steward `src/platform/` + the 12.1
> chart, the Epic 15 wiring chain), and one command named here
> (`bmad-marshal-detectors-init`) does not exist yet.

## System Architecture & Target State

This specification defines the multi-layer system architecture and agentic SDLC environment for local Red Hat OpenShift Container Platform (OCP) development. It bridges visual lifecycle management via Podman Desktop with command-line infrastructure control (`oc` CLI). Furthermore, it systematically wires the missing modules of the BMAD suite to support a `cookiecutter-django` application deployment integrated with PostgreSQL and Redis.

The environment also standardizes on **Pixi** as the foundational multi-language package manager, **GitHub Projects V2** as the authoritative issue tracker, and leverages **dlt** for localized data synchronization. Finally, it extends the application layer via ASGI multiplexing to co-host Langflow (v1.11.2) and DB-GPT alongside the Django backend.

### Architecture Diagram

```mermaid
graph TD
    subgraph Host ["Host Workstation"]
        PD[Podman Desktop]
        Pixi[Pixi Workspace]
        CLI[oc CLI]
        DLT[dlt Pipeline Runner]
    end

    subgraph External ["External SaaS"]
        GH[GitHub Projects V2]
    end

    subgraph OCP ["OpenShift Local Cluster (Single Node VM)"]
        subgraph BMAD ["BMAD Suite Environment (One Front Door)"]
            Marshal[Marshal Orchestrator / Detectors]
            TEA[Test Architecture & Build]
            Skills[Skill Forge / Labs]
            Manticore[Manticore / mc-* Skills]
        end

        subgraph Ingress ["Traefik Routing"]
            Route[ASGI Multiplexer]
        end

        subgraph Workloads ["Application Layer"]
            Django[cookiecutter-django Pod]
            Langflow[Langflow v1.11.2 Pod]
            DBGPT[DB-GPT Pod]
        end

        subgraph Stateful ["Persistent Data Layer (PVCs)"]
            PG[(PostgreSQL Pod)]
            Redis[(Redis Pod)]
        end
    end

    PD -.->|Manages VM Lifecycle| OCP
    CLI -->|Infrastructure as Code| OCP
    Pixi -->|Isolates Environment| DLT

    DLT -->|Extracts Issues & Metrics via API| GH
    DLT -->|Loads Data (github_metrics schema)| PG

    Marshal -->|Manages Packages & Skills| BMAD
    Marshal -->|Executes CLI Verbs| Manticore
    Marshal -->|Orchestrates| Skills
    TEA -.->|Validates Deployment| Workloads

    Route -->|/api/django| Django
    Route -->|/api/langflow| Langflow
    Route -->|/api/dbgpt| DBGPT

    Django -->|Reads/Writes (cookiecutter_schema)| PG
    Langflow -->|State & Memory (langflow_schema)| PG
    DBGPT -->|Vector & Agent State (dbgpt_schema)| PG
    Django <-->|Cache & Celery Broker| Redis
```

### BMAD Suite Wiring Plan

| Package | Current State | Required Wiring Action | Target Role |
| :--- | :--- | :--- | :--- |
| **bmad-method (core+bmm)** | ✅ Wired (6.11.0 in _bmad/, 65 skills) | — | Core logic |
| **bmad-module-skill-forge**| ✅ Wired (skf module 2.1.0, 16 skf-* skills)| — | Skill generation |
| **bmad-labs-skills** | ✅ Wired (~21 general-purpose skills) | — | General-purpose ops |
| **bmad-loop** | ✅ Wired (0.11 canon as of Story 25.2) | — | Orchestration loop |
| **bmad-dashboard / mybmad**| ✅ Wired (bmad-ui env, launchers work) | — | UI / Launchers |
| **TEA** | ❌ Unwired (only standalone tea-test-review CLI) | Execute `bmad-tea-install` | Test architecture |
| **bmad-builder (BMB)** | ❌ Unwired (package only, never run) | Execute `bmad-builder-install` | Build automation |
| **CIS** | ❌ Unwired | Execute `bmad-cis-install` | Continuous integration |
| **bmad-utility-skills** | ❌ Unwired | Execute `bmad-utility-skills-install`| Utility operations |
| **manticore & detectors** | ❌ Unwired (zero mc-* skills wired) | Execute `bmad-manticore-install` & configure Marshal Detectors | Advanced one-front-door ops & CLI boundaries |
| **WDS** | ❌ Deprecated upstream | *Recommend: don't wire* | N/A (wait for bmad-ux) |

---

## Phase 1: Infrastructure, Project Setup & Environment Orchestration

1. **Establish GitHub Projects V2 Tracker** — initialize the issue tracking
   and project management framework using GitHub Projects V2, linked to the
   repository to track BMAD stories, bugs, and OCP deployment tasks.

2. **Initialize OCP Local via Podman Desktop** — launch Podman Desktop,
   OpenShift Local extension → **Initialize and start**; provide the Red Hat
   pull secret; wait for "Running".

3. **Authenticate the `oc` CLI** — open the OpenShift Web Console via the
   Podman Desktop tile, extract the temporary `kubeadmin` token, `oc login`.

4. **Wire the BMAD Suite & Marshal Orchestrator** — establish the "One Front
   Door" policy by registering candidate CLI verbs and architectural
   boundaries through Marshal:
   ```bash
   # Core & Baseline Modules
   bmad-method-install
   bmad-module-skill-forge-install
   bmad-labs-skills-install
   bmad-loop-install
   bmad-dashboard-install

   # Architecture & Build Modules
   bmad-tea-install
   bmad-builder-install
   bmad-cis-install

   # Operations, Utilities & One Front Door
   bmad-utility-skills-install
   bmad-manticore-install
   bmad-marshal-detectors-init  # Register mc-* skills under the unified CLI
   bmad-module-template-init
   ```

---

## Phase 2: Application Scaffolding & ASGI Multiplexing Setup

1. **Initialize Workspace with Pixi**
   ```bash
   pixi init django-ocp-workspace
   cd django-ocp-workspace
   pixi add python cookiecutter dlt
   ```

2. **Scaffold the Django Project**
   ```bash
   pixi run cookiecutter https://github.com/cookiecutter/cookiecutter-django
   ```

3. **Configure Docker Compose for ASGI Multiplexing** — add Langflow and
   DB-GPT services to the Compose spec:
   ```yaml
   # docker-compose.local.yml (excerpt)
   services:
     django:
       build:
         context: .
         dockerfile: ./compose/local/django/Dockerfile
       depends_on:
         - postgres
         - redis

     langflow:
       image: logspace/langflow:1.11.2
       environment:
         - LANGFLOW_DATABASE_URL=postgresql://debug:debug_password@postgres-db:5432/cookiecutter_db?options=-c%20search_path=langflow_schema
       depends_on:
         - postgres

     dbgpt:
       image: eosphorosai/dbgpt:latest
       environment:
         - DBGPT_DB_URL=postgresql://debug:debug_password@postgres-db:5432/cookiecutter_db?options=-c%20search_path=dbgpt_schema
       depends_on:
         - postgres
   ```

4. **Containerize the Stack Locally**
   ```bash
   podman build -t local-django-app -f compose/local/django/Dockerfile .
   ```

---

## Phase 3: Persistent Data & Schema Isolation

1. **Establish PVCs** (`stateful-pvcs.yaml`): `postgres-pvc` 10Gi (vector +
   agent state), `redis-pvc` 2Gi; `oc apply -f stateful-pvcs.yaml`.

2. **Deploy PostgreSQL with PVC mapping**
   ```bash
   oc new-app postgres:15 --name=postgres-db -e POSTGRES_USER=debug -e POSTGRES_PASSWORD=debug_password -e POSTGRES_DB=cookiecutter_db
   oc set volume deployment/postgres-db --add --name=postgres-storage --claim-name=postgres-pvc --mount-path=/var/lib/postgresql/data
   ```
   Post-deployment, initialize the isolated schemas:
   ```bash
   PG_POD=$(oc get pods -l deployment=postgres-db -o name)
   oc exec $PG_POD -- psql -U debug -d cookiecutter_db -c "CREATE SCHEMA langflow_schema;"
   oc exec $PG_POD -- psql -U debug -d cookiecutter_db -c "CREATE SCHEMA dbgpt_schema;"
   oc exec $PG_POD -- psql -U debug -d cookiecutter_db -c "CREATE SCHEMA github_metrics;"
   ```

3. **Deploy Redis with PVC mapping**
   ```bash
   oc new-app redis:7 --name=redis-cache
   oc set volume deployment/redis-cache --add --name=redis-storage --claim-name=redis-pvc --mount-path=/data
   ```

---

## Phase 4: Application Deployment & Routing

1. **Deploy Django, Langflow, and DB-GPT to OCP**
   ```bash
   oc new-app --name=cookiecutter-django --docker-image=local-django-app
   oc new-app --name=langflow --docker-image=logspace/langflow:1.11.2
   oc new-app --name=dbgpt --docker-image=eosphorosai/dbgpt:latest
   oc expose svc/cookiecutter-django
   oc expose svc/langflow
   oc expose svc/dbgpt
   ```

2. **Wire Application Environment Variables**
   ```bash
   oc set env deployment/cookiecutter-django DATABASE_URL=postgres://debug:debug_password@postgres-db:5432/cookiecutter_db REDIS_URL=redis://redis-cache:6379/0 CELERY_BROKER_URL=redis://redis-cache:6379/1
   oc set env deployment/langflow LANGFLOW_DATABASE_URL="postgresql://debug:debug_password@postgres-db:5432/cookiecutter_db?options=-c%20search_path=langflow_schema"
   oc set env deployment/dbgpt DBGPT_DB_URL="postgresql://debug:debug_password@postgres-db:5432/cookiecutter_db?options=-c%20search_path=dbgpt_schema"
   ```

---

## Phase 5: GitHub Projects V2 Synchronization via dlt

1. `pixi run dlt init github_projects postgres`
2. Configure `.dlt/secrets.toml` (GitHub PAT; postgres credentials via
   `oc port-forward svc/postgres-db 5432:5432`).
3. Pipeline script `github_projects_pipeline.py`: V2 project items, custom
   fields, status columns → `github_metrics` dataset:
   ```python
   import dlt
   from github_projects import github_projects_source

   def load_project_data():
       pipeline = dlt.pipeline(
           pipeline_name="github_sync",
           destination="postgres",
           dataset_name="github_metrics"
       )
       data = github_projects_source(project_id="YOUR_PROJECT_ID")
       info = pipeline.run(data)
       print(info)

   if __name__ == "__main__":
       load_project_data()
   ```
4. `pixi run python github_projects_pipeline.py`

---

## Phase 6: Validation & Testing

1. **Visual Verification** — Podman Desktop dashboard: pods `postgres-db`,
   `redis-cache`, `cookiecutter-django`, `langflow`, `dbgpt` all **Running**.
2. **Database Migrations & Data Validation**
   ```bash
   DJANGO_POD=$(oc get pods -l deployment=cookiecutter-django -o name)
   oc exec $DJANGO_POD -- python manage.py migrate
   ```
   Query the synchronized GitHub data and AI schemas to confirm the bridge.
