# Technical Specification: GitHub Projects V2 & Jira Bidirectional Sync

**Artifact Type:** BMAD System Architecture & Product Requirements Document (PRD)

**Target Systems:** GitHub Projects V2, Atlassian Jira Cloud

**Engineers / Agents:** Architectural Agent, Developer Agent, QA Agent

**Version:** 1.1 — folds in three follow-up drops (a recap with a known API
issue + rejected alternatives, and two rounds of concrete PostgreSQL schema
detail for Mode B) into the original v1.0 spec. Distilled and merged in
place; nothing from v1.0 was removed, only extended. See each section below
for what's new.

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

### 1.4 Alternative tools evaluated and rejected *(new in v1.1)*

Two existing tools were considered before committing to a custom build; both were rejected for concrete reasons, recorded here so they aren't re-evaluated from scratch later:

* **Steampipe** — queries both GitHub and Jira via SQL without standing up a dedicated database (an attractive property). Rejected: its plugins are effectively **read-only** — no `INSERT`/`UPDATE` capability, which rules it out as the reverse-ETL half of Mode B (or any push-back mechanism at all). Still worth reconsidering purely as a *read-side* convenience if Mode B's own `dlt` ingestion pipelines ever want a lighter-weight alternative for ad-hoc querying, but it cannot replace the write path.
* **Octosync** — an existing open-source, Dockerized GitHub↔Jira sync tool, purpose-built for exactly this problem — the closest off-the-shelf match to this spec's own goal. Rejected: unmaintained (~5 years old at evaluation time), which risks incompatibility with modern GitHub/Jira API authentication (fine-grained PATs, current OAuth flows) that postdate the project's last activity.

---

## 2. Shared Data Model & ID Mapping Strategy

To correlate records across systems, each side must hold a reference identifier to the other.

| Entity | GitHub Projects V2 Field | Jira Cloud Field |
| --- | --- | --- |
| **Primary Link** | Custom Text Field (`custom_jira_key`) | Custom Field (`github_item_id`) |
| **Entity ID** | Project V2 Item `node_id` (e.g. `PVTI_lAD...`) | Issue Key (e.g. `PROJ-123`) |
| **Status Mapping** | Single-Select Field (`custom_status`) | Issue Status Name (`status.name`) |
| **Assignee** | Assignee Username | Assignee Account ID / Display Name |

**Open reconciliation *(new in v1.1)*:** § 3's Mode B now also has a concrete "control plane" of bridge tables (`sync_entity_mapping`, `sync_field_mapping`, `sync_value_translation` — see below) that does the same job as this table (linking, field mapping) plus value translation and configurable per-field sync direction, none of which this simple custom-field approach covers. Whether the bridge-table design *replaces* this section's simpler linking strategy, or the two coexist (custom fields as the human-visible link, the bridge table as the machine-authoritative one), is an open architecture-phase decision — not resolved here.

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

### Known issue affecting both flows' GitHub-side writes *(new in v1.1)*

As of early 2026, GitHub's GraphQL mutation `updateProjectV2ItemFieldValue` (used by Flow A2 above, and Mode B's Step B3 below) has a known issue: it successfully updates the underlying data store, but can fail to update the board view's **grouping index** when moving an existing item's single-select field value. The result: automation moves a card logically (the data is correct), but the board UI can appear "stuck" — the card doesn't visually move to its new column. The only known workaround is manual intervention: dragging the card in the UI, which forces a re-index. Whoever implements either mode should budget for this as an accepted UX quirk (data is correct, display may lag until a manual nudge), and should verify against GitHub's own issue tracker at implementation time whether it has since been fixed.

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

* **GitHub Pipeline:** Queries GitHub V2 GraphQL API and yields records into `github_data.github_project_items`. Custom fields are read from a Project V2 item's `fieldValues.nodes` array and dynamically mapped into flattened columns (e.g. a found `Status` field value becomes `custom_status`).
* **Jira Pipeline:** Queries Jira REST API v3 (using JQL `project = "PROJ"`) and yields records into `jira_data.jira_issues`. Jira's own opaque custom-field IDs (e.g. `customfield_10014`) are mapped to their equivalent named columns — this mapping must be declared explicitly (a field-ID → column-name table) rather than assumed structurally identical across projects, since Jira custom-field IDs are per-instance, not stable across different Jira Cloud sites.

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

This view assumes a flat, single-table shape per system (a direct `g.custom_status` column). The normalized schema draft below (§ 3.1) implies a different version of this view — see "How `vw_sync_discrepancies` actually works with the control plane" for the reconciled version.

#### Step B3: Reverse ETL (Pushing Updates Back)

A Python worker queries `vw_sync_discrepancies` and routes changes using `@dlt.destination`:

1. **For `PUSH_TO_GITHUB`:** Execute GraphQL mutation `updateProjectV2ItemFieldValue` using the `github_item_id`.
2. **For `PUSH_TO_JIRA`:** Execute Jira API POST request `/rest/api/3/issue/{jira_key}/transitions`.

### 3.1 Concrete normalized schema + control plane for Mode B *(new in v1.1)*

Two follow-up drops replaced the flattened sketch above (§ Step B1/B2) with a fully normalized, EAV-style schema for both systems, plus a third "control plane" layer of bridge tables connecting them. This is more detailed than, and in tension with, the flat-table view in Step B2 — the architecture phase needs to decide which shape Mode B actually ships (flat = simpler diff view; normalized = more general, handles arbitrary custom fields uniformly on both sides, at the cost of needing the control plane to make the join tractable). Both are recorded here as given, not reconciled.

#### GitHub-side schema

```sql
-- Represents the Project Board itself
CREATE TABLE github_projects (
    id VARCHAR(255) PRIMARY KEY, -- GitHub GraphQL Node ID
    number INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    url TEXT,
    closed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Represents the custom columns/fields in your project
CREATE TABLE github_project_fields (
    id VARCHAR(255) PRIMARY KEY,
    project_id VARCHAR(255) REFERENCES github_projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    data_type VARCHAR(50) -- e.g., 'SINGLE_SELECT', 'DATE', 'TEXT', 'NUMBER'
);

-- Represents the actual cards (Issues, PRs, or Draft Issues) on the board
CREATE TABLE github_project_items (
    id VARCHAR(255) PRIMARY KEY,
    project_id VARCHAR(255) REFERENCES github_projects(id) ON DELETE CASCADE,
    content_id VARCHAR(255),  -- Node ID of the underlying Issue or PR
    content_type VARCHAR(50), -- 'ISSUE', 'PULL_REQUEST', or 'DRAFT_ISSUE'
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Maps the values a specific card has for a specific custom field
CREATE TABLE github_item_field_values (
    item_id VARCHAR(255) REFERENCES github_project_items(id) ON DELETE CASCADE,
    field_id VARCHAR(255) REFERENCES github_project_fields(id) ON DELETE CASCADE,
    text_value TEXT,
    number_value NUMERIC,
    date_value TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (item_id, field_id)
);
```

#### Jira-side schema

Mirrors the same EAV structure while adapting to Jira's own domain model:

```sql
-- Represents the Jira Project (Equivalent to github_projects)
CREATE TABLE jira_projects (
    id VARCHAR(255) PRIMARY KEY, -- Jira's internal numeric ID (e.g., '10000')
    key VARCHAR(50) NOT NULL UNIQUE, -- The project prefix (e.g., 'PROJ')
    name VARCHAR(255) NOT NULL, -- The human-readable project name
    project_type VARCHAR(50), -- e.g., 'software', 'business', 'service_desk'
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Represents standard and custom Jira fields (Equivalent to github_project_fields)
-- Note: In Jira, custom fields are global to the instance, so there is no project_id foreign key here.
CREATE TABLE jira_fields (
    id VARCHAR(255) PRIMARY KEY, -- e.g., 'customfield_10014' or standard fields like 'status'
    name VARCHAR(255) NOT NULL,  -- e.g., 'Story Points', 'Sprint', or 'Status'
    data_type VARCHAR(50) -- e.g., 'string', 'number', 'datetime', 'array', 'option'
);

-- Represents the Jira Issues (Equivalent to github_project_items)
CREATE TABLE jira_issues (
    id VARCHAR(255) PRIMARY KEY, -- Jira's internal numeric ID for the issue
    project_id VARCHAR(255) REFERENCES jira_projects(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL UNIQUE, -- The recognizable issue key (e.g., 'PROJ-123')
    issue_type VARCHAR(50), -- e.g., 'Epic', 'Story', 'Bug', 'Task'
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Maps the values a specific Jira issue has for standard/custom fields (Equivalent to github_item_field_values)
CREATE TABLE jira_issue_field_values (
    issue_id VARCHAR(255) REFERENCES jira_issues(id) ON DELETE CASCADE,
    field_id VARCHAR(255) REFERENCES jira_fields(id) ON DELETE CASCADE,
    text_value TEXT, -- Stores strings, dropdown options, and JSON arrays
    number_value NUMERIC, -- Stores Story Points, numeric estimates
    date_value TIMESTAMP WITH TIME ZONE, -- Stores due dates, sprint start/end dates
    PRIMARY KEY (issue_id, field_id)
);
```

**Key differences from the GitHub-side schema, as given:**

- **The `key` column matters more than `id` here.** Jira relies on Project and Issue Keys (`PROJ`, `PROJ-123`) for API calls and UI links far more than the underlying numeric `id` — both `jira_projects` and `jira_issues` carry a `key` column the GitHub-side schema has no equivalent for (GitHub's `github_projects`/`github_project_items` key off `id` alone).
- **Jira fields are global, not per-project.** `jira_fields` deliberately has no `project_id` foreign key — a custom field like `customfield_10020` ("Target Date") is defined once per Jira *instance* and can be reused across many projects, unlike `github_project_fields`, which is scoped to one project board.
- **`issue_type` replaces `content_type`.** GitHub's `content_type` distinguishes `ISSUE` / `PULL_REQUEST` / `DRAFT_ISSUE`; Jira's `issue_type` distinguishes `Epic` / `Story` / `Bug` / `Task` — same shape (a type discriminator column), different vocabulary, not directly mapped 1:1 between the two systems.

#### The control plane: three bridge tables

Without these, field mappings would need hardcoding in Python, and there would be no mechanism to know which system was updated last (the precondition for loop prevention).

**1. Entity bridge — which card is which issue.** Source of truth for the github-item ↔ jira-issue relationship, and the timestamp the loop-prevention logic depends on:

```sql
CREATE TABLE sync_entity_mapping (
    github_item_id VARCHAR(255) REFERENCES github_project_items(id) ON DELETE CASCADE,
    jira_issue_id VARCHAR(255) REFERENCES jira_issues(id) ON DELETE CASCADE,
    -- Tracks the exact moment the sync engine last pushed an update
    last_sync_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- State tracker: 'IN_SYNC', 'ERROR', or 'CONFLICT'
    sync_status VARCHAR(50) DEFAULT 'IN_SYNC', 
    PRIMARY KEY (github_item_id, jira_issue_id)
);
```

**2. Field-configuration bridge — what to sync, and which direction.** Not every field should sync, and not every field should sync both ways — this makes it configurable per field rather than hardcoded (new scope beyond § 1-2 above, which implicitly assumed every mapped field syncs bidirectionally):

```sql
CREATE TABLE sync_field_mapping (
    id SERIAL PRIMARY KEY,
    github_field_id VARCHAR(255) REFERENCES github_project_fields(id) ON DELETE CASCADE,
    jira_field_id VARCHAR(255) REFERENCES jira_fields(id) ON DELETE CASCADE,
    -- 'BIDIRECTIONAL', 'GITHUB_TO_JIRA', or 'JIRA_TO_GITHUB'
    sync_direction VARCHAR(50) DEFAULT 'BIDIRECTIONAL',
    is_active BOOLEAN DEFAULT TRUE
);
```

**3. Value-translation bridge — vocabulary doesn't match across systems.** § 2's Status Mapping row implicitly assumed the two systems' status *values* line up 1:1. They don't in general — Jira might say "In Progress" while a GitHub board says "In-Progress" or "Doing," and an API call with the wrong exact string fails:

```sql
CREATE TABLE sync_value_translation (
    field_mapping_id INT REFERENCES sync_field_mapping(id) ON DELETE CASCADE,
    github_value TEXT NOT NULL, -- e.g., 'Done'
    jira_value TEXT NOT NULL,   -- e.g., 'Closed'
    PRIMARY KEY (field_mapping_id, github_value, jira_value)
);
```

#### How `vw_sync_discrepancies` actually works with the control plane

Conceptual join/filter logic, given as-provided (not yet written as literal SQL):

1. Join `github_item_field_values` to `jira_issue_field_values` **through** `sync_entity_mapping` (the entity bridge resolves which GitHub item pairs with which Jira issue).
2. Filter to only the fields declared in `sync_field_mapping` — fields not configured there are never compared, never synced.
3. Translate values through `sync_value_translation` before comparing (a GitHub "Done" is translated to "Closed" before checking it against Jira's actual value, not compared raw).
4. Compare the translated values; if they differ, check timestamps to decide direction.
5. **Loop prevention, concretely:** if `github_project_items.updated_at` is more recent than `sync_entity_mapping.last_sync_timestamp`, the change was made by a human (the sync engine's own last write is already accounted for by the timestamp), so it's safe to push to Jira without looping. This is a strictly more general mechanism than Mode A's guard clauses above (checking the update's *initiator* identity against a known bot account) — it works by *time*, not *identity*, which generalizes better to Mode B's batch/scheduled model where there may be no per-update initiator to check at all.

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
* **Story 3.3:** Draft PostgreSQL `vw_sync_discrepancies` SQL view comparing Jira and GitHub statuses and timestamps. *(§ 3.1's control-plane design gives this story a concrete, time-based mechanism to build against, as an alternative to a flat-table diff.)*
* **Story 3.4:** Build Reverse ETL Python runner using `dlt` custom destinations to consume `vw_sync_discrepancies` and push updates to target APIs.

---

## 5. Acceptance Criteria Checklist

* [ ] Moving a item status on GitHub Project V2 updates the corresponding Jira issue status within expected SLA (< 30s for Mode A, < next schedule for Mode B).
* [ ] Updating a Jira issue status updates the corresponding GitHub Project card.
* [ ] Modifying a card in GitHub does **not** trigger a loop back from Jira.
* [ ] Unlinked issues (missing `github_item_id` or `custom_jira_key`) fail gracefully and generate log warnings without crashing pipelines.
