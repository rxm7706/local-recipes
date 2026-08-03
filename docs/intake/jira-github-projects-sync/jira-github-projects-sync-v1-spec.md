# Technical Specification: GitHub Projects V2 & Jira Bidirectional Sync

**Artifact Type:** BMAD System Architecture & Product Requirements Document (PRD)

**Target Systems:** GitHub Projects V2, Atlassian Jira Cloud

**Engineers / Agents:** Architectural Agent, Developer Agent, QA Agent

**Version:** 1.0

---

## 1. Product Requirements Document (PRD)

### 1.1 Objective & Scope

Build a bidirectional, two-way sync engine between **GitHub Projects V2** and **Jira Cloud** without relying on third-party SaaS tools (such as Unito or Exalate). The system must keep status, metadata, and custom fields synchronized in near-real-time while remaining cost-effective, maintainable, and loop-free.

### 1.2 Non-Functional Requirements (NFRs)

* **Zero Loop Guarantee:** Neither system must enter an infinite update loop (e.g., Jira updating GitHub triggering GitHub to update Jira).
* **Idempotency:** Re-processing an update payload must produce the exact same system state.
* **Security:** API tokens (GitHub Fine-Grained PATs, Jira API Tokens) must be stored securely (GitHub Secrets / Environment Variables) using least-privilege scopes.

### 1.3 System Modes Supported

1. **Mode A: Serverless Event-Driven Sync (GitHub Actions + Jira Automations)**
* *Best for:* Real-time updates, zero-hosting cost, serverless environments.


2. **Mode B: Centralized Data Hub Sync (`dlt` + PostgreSQL)**
* *Best for:* Scheduled batch processing, full historical audit trails, reporting/analytics, and complex conflict-resolution logic.



---

## 2. Shared Data Model & ID Mapping Strategy

To correlate records across systems, each side must hold a reference identifier to the other.

| Entity | GitHub Projects V2 Field | Jira Cloud Field |
| --- | --- | --- |
| **Primary Link** | Custom Text Field (`custom_jira_key`) | Custom Field (`github_item_id`) |
| **Entity ID** | Project V2 Item `node_id` (e.g. `PVTI_lAD...`) | Issue Key (e.g. `PROJ-123`) |
| **Status Mapping** | Single-Select Field (`custom_status`) | Issue Status Name (`status.name`) |
| **Assignee** | Assignee Username | Assignee Account ID / Display Name |

---

## 3. Architecture Specification

### Architecture Mode A: Serverless Event-Driven (Real-Time)

```
+------------------+         Webhook (Event)        +--------------------+
|                  | -----------------------------> |                    |
|  GitHub Projects |                                |   Jira Cloud API   |
|        V2        | <----------------------------- |                    |
+------------------+   Repository Dispatch / GHA    +--------------------+

```

#### Flow A1: GitHub -> Jira

1. **Trigger:** A field (e.g., Status) is modified on a GitHub Project V2 item.
2. **Execution:** The `project_v2_item` webhook triggers a GitHub Action workflow (`github-to-jira.yml`).
3. **Guard Clause:** Check if the update was performed by the `github-actions[bot]` or a dedicated Sync Bot. If yes, exit immediately.
4. **Processing:**
* Extract the Jira Issue Key from `custom_jira_key`.
* Call Jira REST API v3 `/rest/api/3/issue/{issueKey}/transitions` to transition the Jira ticket.



#### Flow A2: Jira -> GitHub

1. **Trigger:** A Jira Automation rule fires on "Field value changed" (Status/Assignee).
2. **Guard Clause:** Jira rule checks: `Initiator != "Sync Bot Account"`.
3. **Execution:** Jira sends a Web request (`POST`) to GitHub's Repository Dispatch API (`https://api.github.com/repos/{owner}/{repo}/dispatches`).
4. **Payload:**
```json
{
  "event_type": "jira_issue_updated",
  "client_payload": {
    "jira_key": "{{issue.key}}",
    "new_status": "{{issue.status.name}}",
    "github_item_id": "{{issue.customfield_10010}}"
  }
}

```


5. **Processing:** The GitHub Action (`jira-to-github.yml`) runs a GraphQL mutation to update the target field on GitHub Project V2.

---

### Architecture Mode B: Centralized Data Hub (`dlt` + PostgreSQL)

```
+--------------------+        dlt Ingestion       +--------------------+
|  GitHub Projects  | -------------------------> |                    |
+--------------------+                            |                    |
                                                  |  PostgreSQL Data   |
+--------------------+        dlt Ingestion       |        Hub         |
|     Jira Cloud     | -------------------------> |                    |
+--------------------+                            +--------------------+
                                                            |
                                                   Diff SQL Views
                                                            |
                                           Reverse ETL (dlt / Python)
                                                            |
                                                            v
                                                  Target System Mutations

```

#### Step B1: Data Ingestion (ETL)

Two separate `dlt` pipelines pull live state into PostgreSQL on a scheduled frequency (e.g., every 5-15 minutes).

* **GitHub Pipeline:** Queries GitHub V2 GraphQL API and yields records into `github_data.github_project_items`.
* **Jira Pipeline:** Queries Jira REST API v3 (using JQL `project = "PROJ"`) and yields records into `jira_data.jira_issues`.

#### Step B2: Conflict & Diff Resolution (SQL View)

PostgreSQL evaluates state differences using a SQL View to determine which records need synchronization.

```sql
CREATE OR REPLACE VIEW vw_sync_discrepancies AS
SELECT 
    j.key AS jira_key,
    j.github_item_id,
    j.status AS jira_status,
    g.custom_status AS github_status,
    j.updated_at AS jira_updated_at,
    g.updated_at AS github_updated_at,
    CASE 
        -- If Jira updated more recently, sync Jira -> GitHub
        WHEN j.updated_at > g.updated_at THEN 'PUSH_TO_GITHUB'
        -- If GitHub updated more recently, sync GitHub -> Jira
        WHEN g.updated_at > j.updated_at THEN 'PUSH_TO_JIRA'
        ELSE 'IN_SYNC'
    END AS sync_direction
FROM jira_data.jira_issues j
JOIN github_data.github_project_items g 
  ON j.github_item_id = g.id
WHERE j.status <> g.custom_status;

```

#### Step B3: Reverse ETL (Pushing Updates Back)

A Python worker queries `vw_sync_discrepancies` and routes changes using `@dlt.destination`:

1. **For `PUSH_TO_GITHUB`:** Execute GraphQL mutation `updateProjectV2ItemFieldValue` using the `github_item_id`.
2. **For `PUSH_TO_JIRA`:** Execute Jira API POST request `/rest/api/3/issue/{jira_key}/transitions`.

---

## 4. Epics & Story Breakdown (Implementation Tasks)

### Epic 1: Identity & Custom Field Provisioning

* **Story 1.1:** Create custom text field `custom_jira_key` on target GitHub Project V2 board.
* **Story 1.2:** Create custom text field `github_item_id` in Jira Cloud project.
* **Story 1.3:** Create service accounts / bot API tokens for GitHub and Jira with minimum required scopes.

### Epic 2: Mode A — Serverless Real-Time Pipeline

* **Story 2.1:** Implement `.github/workflows/github-to-jira.yml` to process GitHub Project V2 webhook events and update Jira via REST API.
* **Story 2.2:** Configure Jira Automation Rule to dispatch a JSON payload to GitHub `repository_dispatch` endpoint upon ticket changes.
* **Story 2.3:** Implement `.github/workflows/jira-to-github.yml` to listen to `jira_issue_updated` events and run GraphQL mutations against GitHub Projects V2.
* **Story 2.4:** Implement loop-prevention filters checking for `bot` initiators on both GitHub Actions and Jira Automation conditions.

### Epic 3: Mode B — Data Hub Pipeline (`dlt` + Postgres)

* **Story 3.1:** Implement `dlt` ingestion script for GitHub Projects V2 GraphQL endpoint saving to PostgreSQL.
* **Story 3.2:** Implement `dlt` ingestion script for Jira REST API v3 JQL endpoint saving to PostgreSQL.
* **Story 3.3:** Draft PostgreSQL `vw_sync_discrepancies` SQL view comparing Jira and GitHub statuses and timestamps.
* **Story 3.4:** Build Reverse ETL Python runner using `dlt` custom destinations to consume `vw_sync_discrepancies` and push updates to target APIs.

---

## 5. Acceptance Criteria Checklist

* [ ] Moving a item status on GitHub Project V2 updates the corresponding Jira issue status within expected SLA (< 30s for Mode A, < next schedule for Mode B).
* [ ] Updating a Jira issue status updates the corresponding GitHub Project card.
* [ ] Modifying a card in GitHub does **not** trigger a loop back from Jira.
* [ ] Unlinked issues (missing `github_item_id` or `custom_jira_key`) fail gracefully and generate log warnings without crashing pipelines.
