---
title: Herald Moments 2–4 Test Architecture (BMAD TEA)
slug: herald-test-architecture-tea
status: draft
created: 2026-08-02
updated: 2026-08-02
methodology: bmad-tea
coverage_target_unit: ">80%"
coverage_target_integration: ">70%"
coverage_target_e2e: "happy_path + top_3_risks"
---

# Herald Moments 2–4 Test Architecture (BMAD TEA)

**Scope**: Complete test architecture applying BMAD TEA (Test Architecture Enterprise) methodology to all 18 stories across 7 epics for Herald Moments 2–4.

**Key Principle**: Risk drives test focus. Coverage targets are minimums, not ceilings. High-risk integration points (webhook reliability, evidence validation, automation gates) receive disproportionate test investment.

---

## Executive Summary

- **18 stories** across 7 epics (Epics 1–2 foundation, Epics 3–5 core Moments, Epic 6 integration, Epic 7 docs)
- **Risk assessment**: 11 High-risk items (automation reliability, evidence integrity, authorization gates), 14 Medium-risk (CLI/web usability, performance), 7 Low-risk (help text, logging)
- **Test matrix**: 18 stories × 3 test levels (unit/integration/e2e) = 54 test suites
- **Framework scope**: Shared CLI mocks, database fixtures, webhook payloads, evidence stubs
- **Quality gates**: Unit >80%, integration >70%, e2e happy-path + 3 critical risks; ready-to-merge per epic; ready-to-ship (full system)
- **Integration scenarios**: 3 end-to-end flows (PR→Progress→Claim→Publish, Notice→Archive→Redirect, Stale-Link Detection)

---

---

# MOMENT 2: RISK-BASED PLANNING

## Risk Heat Map (All Epics)

| Epic | Title | FR Coverage | Risk Level | Probability | Impact | Key Failure Modes |
|------|-------|-------------|------------|-------------|--------|-------------------|
| 1 | CLI Architecture | FR-1.1–1.3 | **Medium** | Medium (argument parsing edge cases) | Medium (usability) | Flag parsing fails; auth context missing; role checks bypass |
| 2 | Web Surface | FR-2.1–2.3 | **Low** | Low (UI-level, no logic) | Low (UX friction) | Responsive layout breaks on tablet; tab nav doesn't persist state |
| 3 | Progress Visibility | FR-3.1–3.4 | **High** | High (webhook + cron) | High (silent shipping) | Webhook doesn't fire; cron misses week; cost extraction fails; narrative loses context |
| 4 | Success Proclamation | FR-4.1–4.5 | **High** | High (auto-extract + evidence) | High (false claims) | Auto-extract loses evidence; evidence links 404 at publish; operator gate bypassed |
| 5 | Operations Notices | FR-5.1–5.6 | **Medium** | Medium (manual auth + archive) | Medium (downstream confusion) | Notice URL changes (404s for old links); redirect rule fails; archive indexing breaks |
| 6 | Integration Testing | FR-6.1–7.4 | **High** | High (cross-Moment coordination) | High (system doesn't work) | Moment 2 + 3 auto-triggers race (claim created before progress); evidence validation inconsistent; auth leaks across Moments |
| 7 | Documentation | Implicit (NFRs) | **Low** | Low (docs-only) | Low (onboarding friction) | Help text outdated; examples don't work; no troubleshooting guide |

### High-Risk Items (Invest Heavily)

1. **Webhook reliability (Moment 2 & 3)** — on-ship + on-PR-close must fire, deserialize, and retry on failure. **Test focus**: mock CI webhooks, payload validation, retry logic with exponential backoff.
2. **Evidence validation (Moment 3 & cross-Moment)** — all evidence links must be validated at publish time (404 detection, redirect resolution). **Test focus**: mock HTTP responses, redirect chains, validation library integration.
3. **Authorization gates (Epic 1 + all Moments)** — write operations must require operator role; role checks must not be bypassable. **Test focus**: auth context setup, role verification before handler execution, permission denied flows.
4. **Automation state machine (Epics 3–5)** — Progress/Claim/Notice draft→published→closed transitions must be atomic and audit-logged. **Test focus**: concurrent writes, state corruption under load, audit trail immutability.
5. **Cross-Moment evidence linking (Epic 6)** — Claim can link to Notice; both sides must be queryable; link deletion must cascade correctly. **Test focus**: bidirectional link insertion, orphan detection, cascading deletes.
6. **Weekly async validation (Story 4.5, 1.4)** — stale links must be detected; operator must be alerted; links must remain accessible during re-validation. **Test focus**: date-based state (mock time), alert delivery, validation concurrency.
7. **CLI argument parsing (Story 1.2)** — `--date-range`, `--station`, `--json` must work identically across all subcommands. **Test focus**: flag inheritance, date-range edge cases (leap year, UTC vs. local), JSON schema validation.
8. **Database schema + indexing (Stories 3.1, 4.1)** — Progress + Claim queries must be <500ms on large datasets; no N+1 queries. **Test focus**: query benchmarks, EXPLAIN PLAN verification, concurrent write safety.
9. **Operator prompt flow (Stories 3.2, 4.2, 5.2)** — CLI prompts must not timeout; web forms must support drafts; operator can edit before publish. **Test focus**: input validation, timeout handling, draft persistence.
10. **Cron scheduling reliability (Story 3.2)** — Thursday 2300 UTC must fire reliably; missed cron must be detectable; should not block web requests. **Test focus**: time-based mocking, queue isolation, job logging.
11. **Evidence link audit trail (Story 4.5 + cross-Moment)** — every evidence link must track created_by, created_at; edits must be immutable for published claims. **Test focus**: audit log completeness, immutability enforcement, permission checks on edits.

---

## Risk Justification & Mitigation Strategy

### Why Webhook Reliability is High-Risk

**Probability**: High — network faults, CI latency, Herald service interruptions are common. Webhook deserialization errors happen regularly.  
**Impact**: High — silent missing progress records or claims (operators don't know shipping happened). Retry logic failures cascade across hours.  
**Mitigation**:
- Webhook handler wraps in try/except; all errors logged with payload + stack trace.
- Retry policy: exponential backoff (1s, 2s, 4s, then manual operator alert).
- Test: mock CI payloads with all common variants (missing fields, truncated body, network timeout).
- Test: verify retry count increments, backoff delays correct, operator alert fires after max retries.

### Why Evidence Validation is High-Risk

**Probability**: High — upstream services change, URLs break, redirects multiply. Validation is sync-blocking at publish.  
**Impact**: High — dead links in published claims undermine proof (claim without evidence is worthless). Stale links left unchecked accumulate.  
**Mitigation**:
- Sync validation at publish time: HEAD request + follow_redirects=True + timeout=5s + redirect limit 3.
- Async validation weekly: scheduled job, retries failed links, alerts operator on stale.
- Test: mock HTTP 200/404/302/500 responses; verify redirect resolution; verify stale-link detection in async job.
- Test: verify operator alert contains claim ID + URL + validation error.

### Why Authorization Gates are High-Risk

**Probability**: Medium — role verification is straightforward, but skip-auth mistakes common (code review trap).  
**Impact**: High — unauthorized operator publishes false claim or notice; audit trail compromised.  
**Mitigation**:
- Role check at dispatcher level (before handler executes), not inside handler.
- All writes logged: operation + actor + timestamp + outcome.
- Test: verify role check happens before handler (mock handler, verify it's not called if role missing).
- Test: unauthenticated writes are rejected with "unauthorized" error (not "not found").

### Why Automation State Machine is High-Risk

**Probability**: Medium — concurrent writes, edge cases in state transitions (draft→published while editing). Database transaction handling mistakes.  
**Impact**: High — data corruption (draft becomes published mid-edit), audit trail loses events.  
**Mitigation**:
- All state transitions wrapped in database transaction (ACID guarantees).
- Immutable records for published state (new record on edit, old preserved).
- Test: concurrent writers to same record (one wins, others get "conflict" error).
- Test: audit log is complete (all transitions recorded in order).

---

---

# MOMENT 3: SYSTEMATIC TEST GENERATION

## Test Matrix by Story (18 Stories × 3 Levels)

### **Story 1.1: CLI Dispatcher**

**Risk**: Medium (argument parsing, routing logic)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_dispatcher_routing` | `test_help_flag_shows_subcommands`, `test_unknown_subcommand_errors`, `test_valid_subcommand_routes` | Click CLI framework; mock subcommand handlers | Help text with 3 subcommands; error message naming invalid; handler called | Exit code 0/1/2; output contains expected strings |
| **Unit** | `test_exit_codes` | `test_no_args_exit_1`, `test_help_exit_0`, `test_invalid_cmd_exit_2`, `test_signal_int_exit_130` | Send SIGINT during CLI run | Graceful shutdown | Exit code 130 |
| **Integration** | `test_dispatcher_with_real_subcommand` | `test_progress_subcommand_callable`, `test_success_subcommand_callable`, `test_notice_subcommand_callable` | Dispatcher + stub handlers (return success) | Subcommand handler invoked, result returned | Exit code 0; mock handler called exactly once |
| **Integration** | `test_dispatcher_flag_inheritance` | `test_global_flags_passed_to_handler`, `test_handler_receives_json_flag`, `test_handler_receives_date_range` | Dispatcher with `--json --date-range ...` flags | Flags parsed and passed to handler | Handler receives dict with `json=True`, `date_range=<range>` |
| **E2E** | `test_cli_help_works` | `test_herald_help_output`, `test_herald_progress_help_output` | Run `herald --help`, `herald progress --help` | Full help text printed to stdout | Output contains "Usage:", subcommand list, examples |

### **Story 1.2: Shared Argument Conventions**

**Risk**: Medium (flag parsing, date-range edge cases)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_json_flag_parser` | `test_json_flag_valid`, `test_json_without_flag` | Click context with `--json` flag | JSON-serializable output | Output is valid JSON; no colorization codes |
| **Unit** | `test_date_range_parser` | `test_date_range_valid`, `test_date_range_invalid`, `test_date_range_leap_year`, `test_date_range_utc`, `test_date_range_edge_midnight` | `--date-range 2026-02-28..2026-03-01` | Parsed as datetime tuple (start, end) | Start ≤ end; both in UTC; no timezone surprises |
| **Unit** | `test_station_flag_parser` | `test_station_valid_name`, `test_station_unknown_name` | `--station warden` or `--station unknown` | Validated against station list | Valid: stored; Invalid: error message suggests available stations |
| **Integration** | `test_all_flags_with_all_subcommands` | `test_progress_with_json`, `test_progress_with_date_range`, `test_success_with_json`, `test_success_with_station`, `test_notice_with_date_range` | Each subcommand × each global flag | Flags correctly parsed and applied | Subcommand receives correct parsed values |
| **E2E** | `test_cli_output_formats` | `test_table_output_default`, `test_json_output_valid`, `test_date_range_filters_output` | `herald progress --json`, `herald progress --date-range 2026-08-01..2026-08-02` | Machine-readable / human-readable output | JSON is parseable; table has correct columns; date range filtered |

### **Story 1.3: CLI Authentication & Authorization**

**Risk**: High (security gate)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_auth_context_lookup` | `test_auth_from_env_var`, `test_auth_from_config_file`, `test_auth_missing` | Set `HERALD_TOKEN`, create `~/.herald/config`, or neither | Token loaded / Config loaded / Error | Auth tuple retrieved or error raised |
| **Unit** | `test_role_verification` | `test_operator_role_allows_write`, `test_viewer_role_denies_write`, `test_no_role_denies_write` | Mock auth context with role=operator/viewer/none | Role check passes/fails | Permission granted or "unauthorized" error |
| **Unit** | `test_read_ops_bypass_auth` | `test_progress_read_no_auth_required`, `test_success_list_no_auth_required` | Run read-only ops without auth context | Command succeeds | No "unauthorized" error; output returned |
| **Integration** | `test_auth_middleware_before_handler` | `test_write_op_with_operator_role`, `test_write_op_without_role` | Full CLI path: auth → role check → handler | Handler called / Error before handler | Mock handler called only if role=operator |
| **Integration** | `test_operator_confirmation_prompt` | `test_operator_accepts_prompt`, `test_operator_rejects_prompt` | Simulate user input: Y / n | Proceed / Abort | Handler invoked / Handler skipped |
| **E2E** | `test_auth_context_missing_error` | `test_missing_auth_context_error_message` | Run write op with no auth setup | Error message with setup instructions | Output contains "HERALD_TOKEN" or "herald auth login" |

### **Story 1.4: Evidence Link Validation Protocol (Shared Infrastructure)**

**Risk**: High (cross-Moment integration)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_sync_validation_http_head` | `test_link_200_valid`, `test_link_404_invalid`, `test_link_403_forbidden`, `test_link_timeout` | Mock HTTP responses (200, 404, 403, timeout) | Validation result: {is_valid, status, url, last_validated_at} | is_valid=True/False matches status code; last_validated_at is now |
| **Unit** | `test_redirect_resolution` | `test_redirect_1_hop`, `test_redirect_3_hops`, `test_redirect_chain_exceeds_limit` | Mock redirect chain (302 → 302 → 302 → 200) | Final URL resolved / Warning on >2 hops | last_url matches final destination; is_valid=True if final is 2xx |
| **Unit** | `test_validation_library_interface` | `test_validate_link_signature`, `test_schedule_async_validation_signature` | Import evidence_protocol module | Functions callable with expected signatures | `validate_link(url) → dict`, `schedule_async_validation() → None` |
| **Integration** | `test_publish_gate_rejects_invalid_links` | `test_publish_with_404_link`, `test_publish_with_valid_link` | Create claim with evidence links; call publish gate | Publish rejected with error / Publish succeeds | Exit code 1 + error message; Exit code 0 + claim published |
| **Integration** | `test_async_validation_job` | `test_weekly_cron_validates_all_links`, `test_stale_link_detection`, `test_operator_alert_on_stale` | Mock APScheduler; call weekly cron job | All links re-validated; stale links marked; operator alerted | is_stale=True for links >7 days old; alert contains claim_id + url |
| **E2E** | `test_evidence_validation_end_to_end` | `test_claim_publish_with_evidence_validation`, `test_notice_publish_with_evidence_validation` | Full CLI path: create claim/notice with evidence → publish → weekly async check | Claim published; stale link detected next week | Claim status=published after sync validation; stale flag set after async |

### **Story 1.5: CLI Help & First-Day Usability**

**Risk**: Low (UX-only)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_help_text_content` | `test_herald_help_contains_usage`, `test_herald_help_lists_subcommands`, `test_herald_help_documents_flags`, `test_subcommand_help_complete` | Parse Click help output | Help text contains all sections | "Usage:", "progress", "success", "notice", "--help", "--json" all present |
| **Unit** | `test_help_text_examples` | `test_examples_are_copy_paste_ready` | Run examples from help text verbatim | Examples should execute or fail gracefully | No syntax errors in example commands |
| **Integration** | `test_error_messages_helpful` | `test_unknown_flag_suggests_help`, `test_unknown_subcommand_suggests_valid_ones` | Run with invalid input | Error message contains suggestions | "See --help" or "Available:" in error |
| **E2E** | `test_new_operator_can_learn_cli` | `test_herald_help_sufficient_for_first_use` | Fresh operator; only resource is `--help` | Can discover and run commands | Operator successfully runs `herald progress warden` |

### **Story 2.1: Web Layout (Header, Tabs, Sidebar, Responsive)**

**Risk**: Low (UI-level, no logic)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_layout_component_renders` | `test_header_renders`, `test_tab_nav_renders`, `test_sidebar_renders` | React component mount | No exceptions; HTML tree present | Snapshot test passes (or JSX structure verified) |
| **Integration** | `test_responsive_layout` | `test_layout_desktop_1200px`, `test_layout_tablet_768px`, `test_layout_mobile_375px` | Mount at different viewport widths; query DOM | Layout adapts without horizontal scroll | Sidebar present/hamburger visible; content area fills space; text readable |
| **Integration** | `test_tab_navigation` | `test_clicking_tab_changes_content`, `test_tab_state_persists_reload`, `test_active_tab_highlighted` | Click tabs; reload page; verify visual state | Content area changes; URL hash updated; tab visually active | React Router state or localStorage contains active tab |
| **Integration** | `test_sidebar_filters` | `test_station_filter_updates_content`, `test_date_range_filter_updates_content`, `test_search_filter_updates_content` | Select filter in sidebar; observe content area | Content updates with loading state | API called with correct params; result set filtered |
| **E2E** | `test_responsive_visual_regression` | `test_desktop_layout_screenshot`, `test_tablet_layout_screenshot`, `test_mobile_layout_screenshot` | Render app at breakpoints; capture screenshots | Visual consistency | Visual diffs minimal; no layout shift |

### **Story 2.2: Web Tooltips & Inline Help**

**Risk**: Low (UX-only)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_tooltip_renders` | `test_tooltip_on_hover`, `test_tooltip_on_focus`, `test_tooltip_content_correct` | Hover/focus element with tooltip | Tooltip appears after 200ms | Popper positioned; content visible; no overlap |
| **Integration** | `test_help_icon_opens_modal` | `test_help_icon_click_opens_help`, `test_help_modal_closes_on_escape` | Click "?" icon next to field | Help modal appears / closes | Modal DOM visible; content readable; keyboard trap handled |
| **Integration** | `test_empty_state_messaging` | `test_no_progress_shows_helpful_message`, `test_no_claims_shows_helpful_message` | Load tab with no data | Placeholder text + suggestions shown | Message contains actionable next step (e.g., CLI command) |
| **E2E** | `test_operator_discovers_feature_via_help` | `test_tooltip_explains_filter_purpose`, `test_help_modal_sufficient_for_first_use` | Operator hovers/clicks help without external docs | Feature purpose clear | Tooltip/modal text is self-explanatory |

### **Story 3.1: Progress Data Model & Database Schema**

**Risk**: High (data integrity)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_progress_table_schema` | `test_table_exists`, `test_columns_exist`, `test_column_types_correct` | Query database schema | Table + columns match spec | id=UUID, station=string, date=timestamp, etc. |
| **Unit** | `test_progress_indexes` | `test_composite_index_station_date`, `test_index_created_at` | Query index definitions | Indexes present | Query planner uses indexes for common queries |
| **Unit** | `test_concurrent_write_safety` | `test_two_writers_same_record`, `test_transaction_isolation` | Simulate concurrent writes; check for corruption | No data corruption; ACID guaranteed | Last-write wins or conflict error; no partial writes |
| **Integration** | `test_query_performance` | `test_query_latest_by_station`, `test_query_by_date_range`, `test_query_by_station_and_date` | Run queries on 10k records | Results returned in <500ms | EXPLAIN PLAN shows index usage; no full table scan |
| **Integration** | `test_migration_creates_table` | `test_alembic_migration_runs` | Run Alembic migration | Table created with correct schema | Table queryable; columns have expected types |

### **Story 3.2: On-Ship Webhook & Weekly Cron Automation**

**Risk**: High (reliability, state machine)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_webhook_payload_parsing` | `test_valid_webhook_payload`, `test_missing_field_payload`, `test_malformed_json` | Send webhook payloads (valid, incomplete, corrupt) | Parsed / Error with field name | Webhook handler extracts pr_url, commit_sha, merged_at |
| **Unit** | `test_webhook_signature_validation` | `test_valid_signature`, `test_invalid_signature`, `test_missing_signature` | Webhook with HMAC signature (valid, invalid, missing) | Accepted / Rejected | Signature validation calls correct library; security enforced |
| **Unit** | `test_progress_record_creation` | `test_draft_record_created`, `test_fields_populated_correctly` | Webhook handler creates record | Draft Progress record in database | status=draft; all extracted fields present |
| **Unit** | `test_cron_scheduler_config` | `test_cron_runs_thursday_2300_utc`, `test_cron_collects_week_events` | Mock time to Thursday 23:00 UTC | Cron job triggered | Aggregated Progress record created for past 7 days |
| **Unit** | `test_retry_logic` | `test_retry_exponential_backoff`, `test_max_retries_exhausted`, `test_operator_alert_on_max_retries` | Simulate webhook handler failure | Retries with 1s, 2s, 4s delays; alert sent after 3 retries | Retry count incremented; alert email/dashboard entry created |
| **Integration** | `test_webhook_end_to_end` | `test_on_ship_webhook_creates_progress` | Full webhook flow: CI sends → Herald receives → Progress created | Draft record visible in CLI/web | `herald progress <station> --list` shows new record |
| **Integration** | `test_async_cost_extraction` | `test_cost_extracted_from_journal`, `test_timeout_graceful_fallback` | Webhook handler queries journal for costs (success / timeout) | Costs populated / Blank with retry scheduled | compute_hours + token_spend populated or null |
| **E2E** | `test_on_ship_to_progress_published` | `test_webhook_progress_draft_operator_authors_narrative` | Webhook fires → draft created → operator runs `herald progress <station>` → authors narrative → publishes | Published progress visible in web/CLI | Progress status=published; narrative persisted |

### **Story 3.3: Progress CLI (`herald progress` subcommand)**

**Risk**: Medium (CLI, user-facing)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_progress_cli_routing` | `test_progress_subcommand_exists`, `test_progress_help_text` | Run `herald progress --help` | Help text printed | "Usage: herald progress", subcommand flags documented |
| **Unit** | `test_progress_query` | `test_query_latest_by_station`, `test_query_not_found` | Query Progress by station (exists / not exists) | Record returned / Error message | JSON or table formatted; error names available stations |
| **Unit** | `test_progress_list_filtering` | `test_list_all_stations`, `test_list_with_station_filter`, `test_list_with_date_range`, `test_list_with_week_filter` | Query with `--station <name>`, `--date-range`, `--week recent|N` | Results filtered correctly | Only matching records returned; exit code 0 |
| **Integration** | `test_progress_output_formats` | `test_table_output`, `test_json_output`, `test_ndjson_output` | Run `herald progress <station>` with/without `--json` | Table (colored) / JSON (uncolored) | Output parseable; table readable; JSON valid |
| **Integration** | `test_progress_manual_update_trigger` | `test_progress_update_flag`, `test_update_creates_new_record` | Run `herald progress <station> --update` | New Progress record created for today | `herald progress <station> --list` shows new record with today's date |
| **E2E** | `test_operator_queries_progress_workflow` | `test_operator_checks_latest_progress`, `test_operator_lists_week_progress`, `test_operator_triggers_update` | Realistic operator workflow: check latest, list week, trigger update | All commands succeed; output is clear and actionable | Exit codes 0; no cryptic error messages |

### **Story 3.4: Progress Web Tab**

**Risk**: Medium (web, data display)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_progress_component_renders` | `test_card_component_renders`, `test_card_summary_fields` | Mount ProgressTab component | Cards render without errors | Card shows station, date, shipped_capabilities count |
| **Integration** | `test_progress_api_integration` | `test_fetch_progress_records`, `test_filter_by_station`, `test_filter_by_date_range` | Mock API responses; call ProgressTab | Records displayed; filters applied | API called with correct params; results sorted correctly |
| **Integration** | `test_expandable_detail_view` | `test_click_card_expands_detail`, `test_detail_shows_full_narrative`, `test_close_collapses_detail` | Click card; view detail; close | Expandable section shows/hides narrative + cost breakdown | Animation smooth; detail readable; close button works |
| **Integration** | `test_responsive_card_layout` | `test_cards_stack_mobile`, `test_cards_grid_desktop` | Mount at mobile/desktop viewports | Cards stack vertically / grid layout | Layout adapts; touch targets ≥44px |
| **E2E** | `test_operator_views_progress_in_web` | `test_load_progress_tab_success`, `test_filter_by_station_success`, `test_expand_card_and_read_narrative` | Open Herald web → click Progress tab → filter → expand → read | Progress visible; filters work; detail readable | Tab loads <2s; filters instant; narrative displays fully |

### **Story 4.1: Claim Data Model & Database Schema**

**Risk**: High (data integrity)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_claim_table_schema` | `test_table_exists`, `test_required_columns_exist`, `test_evidence_column_type` | Query database schema | Claims table + columns | id=UUID, project_name, status=enum, thesis, evidence=JSON |
| **Unit** | `test_claim_status_enum` | `test_status_draft_valid`, `test_status_published_valid`, `test_status_closed_valid`, `test_status_invalid_rejected` | Create record with status=draft/published/closed/invalid | Valid statuses accepted / Invalid rejected | Enum constraint enforced by DB |
| **Unit** | `test_evidence_schema` | `test_evidence_list_structure`, `test_evidence_link_fields`, `test_evidence_validation_timestamp` | Insert evidence array with links | Evidence stored as JSON | Evidence array is valid; each link has type, url, label, validated_at |
| **Unit** | `test_claim_versioning` | `test_version_field_increments`, `test_old_version_preserved`, `test_current_version_marked` | Edit claim thesis; check history | New version created; old preserved | version=1/2/3; current=true only on latest |
| **Unit** | `test_concurrent_write_safety` | `test_two_writers_same_claim`, `test_version_conflict_handling` | Simulate concurrent edits | No corruption; ACID guaranteed | Last-write-wins or conflict error; audit log complete |
| **Integration** | `test_migration_creates_tables` | `test_alembic_migration_runs` | Run migration | Claims + Evidence tables created | Tables queryable; indexes present |

### **Story 4.2: Auto-Extract & Operator Review Gate**

**Risk**: High (automation, evidence extraction)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_on_pr_close_webhook_parsing` | `test_valid_webhook_payload`, `test_gates_passed_field` | Send webhook with gates_passed=true/false | Payload parsed; gates_passed extracted | gates_passed=True → extract; False → skip |
| **Unit** | `test_project_name_extraction` | `test_extract_from_pr_title`, `test_extract_from_pr_labels`, `test_fallback_to_default` | PR title: "[Marshal] S-1.10 Harness Policy" | project_name extracted | result="Marshal S-1.10" |
| **Unit** | `test_evidence_extraction` | `test_extract_test_results_link`, `test_extract_metrics_link`, `test_extract_adoption_links`, `test_no_metrics_graceful_missing` | Mock CI job URL + dashboard API | Evidence list populated | evidence array contains test_results link; metrics link if available |
| **Unit** | `test_draft_claim_creation` | `test_draft_claim_created`, `test_thesis_initially_null`, `test_status_draft` | Auto-extract completes | Draft Claim in database | status=draft; thesis=null; evidence list populated; shipped_date set |
| **Unit** | `test_operator_prompt_on_extract` | `test_review_prompt_shown`, `test_operator_can_defer_review` | After extraction, prompt operator | Operator shown claim ID + link to review | `herald success review <claim-id>` available immediately |
| **Integration** | `test_webhook_to_draft_claim_end_to_end` | `test_on_pr_close_webhook_creates_draft_claim` | Send on-PR-close webhook; mock gates=true | Draft Claim visible in `herald success list --status draft` | Claim status=draft; all evidence populated |
| **Integration** | `test_operator_review_flow` | `test_operator_reviews_claim`, `test_operator_edits_thesis`, `test_operator_publishes` | `herald success review <claim-id>` → edit thesis → publish | Thesis updated; claim published | status=published; thesis persisted; published_at set |
| **E2E** | `test_pr_close_to_claim_published` | `test_full_workflow_webhook_extract_review_publish` | Webhook → draft → operator review → publish | Claim visible in `herald success list --status published` | All steps succeed; claim in archive |

### **Story 4.3: Success CLI**

**Risk**: Medium (CLI, user-facing)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_success_cli_routing` | `test_success_subcommand_exists`, `test_success_help_text` | Run `herald success --help` | Help text printed | Usage, subcommands (review, publish, list, get) documented |
| **Unit** | `test_success_review_command` | `test_review_displays_draft_claim`, `test_review_shows_evidence`, `test_review_nonexistent_claim` | Run `herald success review <claim-id>` (valid / not found) | Claim displayed / Error message | Exit code 0; claim details + prompt shown; exit code 1 + "not found" |
| **Unit** | `test_success_publish_command` | `test_publish_with_thesis_flag`, `test_publish_validates_evidence`, `test_publish_sets_status` | Run `herald success publish <claim-id> --thesis "..."` | Thesis updated; evidence validated; status→published | Exit code 0; claim status=published; published_at set |
| **Unit** | `test_editor_input_flow` | `test_thesis_editor_opens`, `test_thesis_editor_multiline_input`, `test_thesis_editor_timeout` | Mock EDITOR env var; simulate user input | Thesis read from temp file | Multiline input captured; timeout handled gracefully |
| **Unit** | `test_success_list_filtering` | `test_list_all_claims`, `test_list_published_only`, `test_list_by_date_range` | Run `herald success list [--status published --date-range ...]` | Results filtered | Only matching claims returned; exit code 0 |
| **Unit** | `test_success_get_command` | `test_get_displays_full_claim`, `test_get_includes_evidence`, `test_get_includes_edit_history` | Run `herald success get <claim-id>` | Full claim details + evidence + history | Exit code 0; all fields present |
| **Integration** | `test_output_formats` | `test_table_output`, `test_json_output` | Run with/without `--json` flag | Table / JSON | Output parseable; table readable; JSON valid |
| **E2E** | `test_operator_publishes_claim_workflow` | `test_operator_reviews_and_publishes_claim` | `herald success review <id>` → `herald success publish <id> --thesis "..."` | Claim published successfully | `herald success list --status published` shows claim |

### **Story 4.4: Success Web Archive**

**Risk**: Medium (web, data display)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_claim_card_component` | `test_card_renders`, `test_card_fields_displayed`, `test_evidence_badges_render` | Mount ClaimCard component | Card renders without errors | Card shows project, thesis, date, evidence badges |
| **Integration** | `test_success_tab_api_integration` | `test_fetch_published_claims`, `test_chronological_order`, `test_filter_by_date_range` | Mock API `/api/herald/success?status=published` | Claims displayed newest first; filters applied | API called correctly; results sorted by shipped_date DESC |
| **Integration** | `test_evidence_badge_styling` | `test_green_badge_valid_link`, `test_yellow_badge_stale_link`, `test_red_badge_broken_link` | Claim with valid/stale/broken evidence | Badges rendered with correct color | CSS classes applied; colors distinguish status |
| **Integration** | `test_expandable_claim_detail` | `test_click_card_expands`, `test_detail_shows_full_thesis`, `test_detail_shows_evidence_links`, `test_close_collapses` | Click claim card; expand detail; close | Detail section shows/hides; all fields visible | Animation smooth; links clickable; close button works |
| **Integration** | `test_stale_link_tooltip` | `test_hover_stale_badge_shows_warning`, `test_tooltip_content_helpful` | Hover over yellow stale badge | Tooltip appears | Tooltip contains "hasn't been validated recently" + last_validated_at |
| **E2E** | `test_operator_browses_success_archive` | `test_open_success_tab_loads`, `test_filter_by_date`, `test_search_by_project`, `test_click_evidence_link` | Open Success tab → filter → search → click evidence link | Archive loads; filters work; links resolve | Tab loads <2s; filters instant; evidence links open in browser |

### **Story 4.5: Evidence Validation (Sync + Async)**

**Risk**: High (integration)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_sync_validation_at_publish` | `test_valid_links_allowed`, `test_invalid_404_rejected`, `test_mixed_valid_invalid` | Publish claim with valid/invalid evidence | Valid: published / Invalid: error before publish | Exit code 0 / 1; error message names bad links |
| **Unit** | `test_async_validation_weekly` | `test_cron_schedules_weekly_check`, `test_all_published_claims_checked`, `test_stale_detection_by_date` | Mock APScheduler; run weekly cron; check dates | All published claims with evidence re-validated | is_stale=True for last_validated_at >7 days ago |
| **Unit** | `test_operator_alert_on_stale` | `test_alert_created_on_stale_detection`, `test_alert_content_includes_claim_id`, `test_alert_delivered` | Async validation detects stale link | Operator alert created + sent | Alert in email/dashboard with claim_id + URL + last_validated_at |
| **Integration** | `test_validation_library_integration` | `test_sync_validation_calls_library`, `test_async_validation_uses_library` | Call publish + weekly cron | Both use same validation library | validate_link() called from both code paths |
| **Integration** | `test_validation_with_redirects` | `test_1_hop_redirect_resolved`, `test_3_hop_redirect_resolved`, `test_redirect_chain_exceeds_limit` | Mock redirect chains | Final URL resolved / Warning on >2 hops | is_valid=True if final is 2xx; warning logged for chains |
| **E2E** | `test_evidence_lifecycle_sync_and_async` | `test_claim_publish_with_sync_validation`, `test_weekly_stale_detection`, `test_operator_alert_received` | Publish claim → wait 7+ days (mocked time) → cron runs | Claim published after sync; stale flag set; operator alerted | Claim status=published; evidence.is_stale=True; alert email received |

### **Stories 5.1–5.6: Notice Data Model, Authoring, Archive, CLI, Web, Lifecycle**

**Risk**: Medium (similar to Claims, but manual authoring instead of auto-extract)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_notice_table_schema` | `test_table_exists`, `test_required_columns` | Query schema | Notice table created | type=enum(deprecation\|fix\|eol), component, what_changed, why, migration_path, deadline, reason_link, notice_url |
| **Unit** | `test_notice_authoring_prompt` | `test_required_fields_prompted`, `test_optional_fields_optional`, `test_validation_on_input` | Run `herald notice author --type deprecation --component auth-api-v1` | Interactive prompts for missing fields | STDIN captured; fields validated; draft notice created |
| **Unit** | `test_archive_directory_structure` | `test_archive_path_generation`, `test_permanent_url_format` | Archive a notice | Notice stored in `/operations/notices/YYYY-MM/category/component.md` | Path matches spec; URL permanent (no changes on re-run) |
| **Unit** | `test_redirect_rule_creation` | `test_redirect_when_component_renamed`, `test_old_url_redirects_to_new` | Rename notice component | Redirect rule created | Old URL (404) → new archive URL (200); operator confirms |
| **Unit** | `test_notice_state_machine` | `test_draft_status_initial`, `test_draft_to_published`, `test_published_to_closed` | Create notice → publish → close | Status transitions correct | edit_history preserved at each step |
| **Integration** | `test_notice_cli_authoring` | `test_author_command_creates_draft`, `test_author_command_publishes` | `herald notice author --type deprecation --component auth-api` → confirm publish | Draft created; operator prompted to publish | Notice status=published; notice_url set; archive path correct |
| **Integration** | `test_notice_archive_indexing` | `test_list_by_type_and_month`, `test_archive_command_shows_structure` | Run `herald notice archive` | Archive tree displayed | Categories + months + component counts shown |
| **E2E** | `test_notice_lifecycle_author_to_archive` | `test_author_deprecation_notice_workflow`, `test_notice_visible_in_web`, `test_redirect_works` | Author notice → publish → check archive → rename → verify redirect | Notice published; visible in web; redirect works; archive permanent | All steps succeed; no 404s; audit trail complete |

### **Story 6: Integration Testing (CLI + Web + Automation)**

**Risk**: High (cross-Moment coordination)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Integration** | `test_webhook_handlers_dont_race` | `test_concurrent_webhooks_same_station`, `test_webhook_and_cron_race`, `test_claim_created_before_progress` | Fire webhooks + cron simultaneously | No state corruption; events ordered correctly | Audit logs show proper sequence; no orphaned records |
| **Integration** | `test_cross_moment_evidence_linking` | `test_claim_links_to_notice`, `test_notice_links_to_claim`, `test_bidirectional_links_resolve` | Create claim + notice with cross-links | Both directions queryable | `herald success get <id>` shows notice link; `herald notice get <id>` shows claim link |
| **Integration** | `test_auth_consistent_across_surfaces` | `test_cli_and_web_same_auth_source`, `test_operator_role_works_cli_and_web`, `test_readonly_public_both_surfaces` | Try auth on CLI and web | Same auth context recognized; role enforced | Token used for both; role check consistent; public reads work both ways |
| **Integration** | `test_shared_flags_work_all_subcommands` | `test_json_flag_all_subcommands`, `test_date_range_all_subcommands`, `test_station_all_subcommands` | Run each subcommand with each shared flag | Flags inherited and applied consistently | Output format/filtering matches expectations |

### **Story 6.2: Automation Reliability**

**Risk**: High (operational)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_webhook_retry_logic` | `test_transient_failure_retried`, `test_exponential_backoff_timing`, `test_max_retries_alert` | Simulate webhook failures (network timeout, 500 error) | Retries with backoff; alert after max | Retry count = 3; delays = 1s, 2s, 4s; alert sent |
| **Unit** | `test_cron_scheduling` | `test_cron_thursday_2300_utc`, `test_cron_is_isolated_from_web` | Mock APScheduler; advance time to Thursday 23:00 | Cron job fires; web not blocked | Job logs start + end; web requests continue during job |
| **Unit** | `test_gate_checks_enforced` | `test_claim_created_only_if_gates_passed`, `test_claim_skipped_if_gates_failed` | Send webhook with gates_passed=true/false | Claim created / Skipped | gates_passed=False → no claim created; no error logged either |
| **Unit** | `test_operator_alert_delivery` | `test_alert_email_sent_on_failure`, `test_alert_dashboard_entry_created`, `test_alert_content_actionable` | Webhook exhausts retries; automation fails | Alert email + dashboard entry | Email contains error + remediation steps; dashboard entry timestamp is accurate |
| **Integration** | `test_full_automation_flow` | `test_webhook_to_database_end_to_end`, `test_cron_aggregation_end_to_end` | Realistic webhook + cron scenario | Data ends in database as expected | Records created with correct state; no data loss |

### **Stories 6.3–6.4: Evidence Linking & Performance Testing**

**Risk**: Medium (cross-Moment + performance)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_cli_command_latency` | `test_progress_cli_latency`, `test_success_list_latency`, `test_notice_archive_latency` | Run commands; measure latency | <1s (95th percentile) | Latency benchmark passed; no outliers |
| **Unit** | `test_query_performance_at_scale` | `test_10k_progress_records`, `test_10k_claims`, `test_index_usage_verified` | Create 10k records; run queries | Queries return in <500ms | EXPLAIN PLAN shows index usage; no full table scans |
| **Integration** | `test_web_tab_load_performance` | `test_progress_tab_load_<2s`, `test_success_tab_load_<2s`, `test_operations_tab_load_<2s` | Open tab; measure load time | <2s (95th percentile) | No waterfall bottlenecks; assets cached |
| **Integration** | `test_no_memory_leaks` | `test_long_session_memory_growth`, `test_tab_switch_memory_stable` | Long session; switch tabs repeatedly | Memory stable over 30+ min | No unbounded growth; GC handles cleanup |

### **Story 7: Documentation & Operator Experience**

**Risk**: Low (docs-only)

| Level | Test Suite | Test Cases | Input/Setup | Expected Output | Assertion |
|-------|-----------|-----------|------------|-----------------|-----------|
| **Unit** | `test_help_text_completeness` | `test_herald_help_full`, `test_all_subcommands_documented`, `test_all_flags_documented` | Read generated help text | All commands + flags documented | No blank descriptions; examples present |
| **Integration** | `test_runbook_examples_work` | `test_progress_runbook_commands_execute`, `test_notice_authoring_runbook_works` | Run commands from runbook verbatim | Commands execute without error | Exit codes 0; output matches expected format |
| **Integration** | `test_troubleshooting_guide_accuracy` | `test_webhook_failure_diagnosis_steps`, `test_stale_link_diagnosis_steps` | Follow troubleshooting steps | Issues resolved or root cause found | Steps are accurate; suggestions work |

---

---

# MOMENT 4: INTEGRATION SCENARIOS (End-to-End Testing)

## Scenario 1: PR Merge → Progress Created → Claim Auto-Extracted → Published

**Objective**: Verify complete flow from shipping event (PR merge) through progress visibility and success proclamation.

**Risk Coverage**: Webhook reliability, evidence extraction, state machine, operator gates.

### Setup

```yaml
Pre-conditions:
  - Herald web service running
  - Herald CLI configured with operator token
  - CI system configured to send on-ship + on-PR-close webhooks
  - Database initialized (Progress + Claim tables)
  - APScheduler cron configured (not active for this scenario)

Actors:
  - CI system (sends webhooks)
  - Herald automation (webhook handlers)
  - Operator (reviews + publishes)
```

### Step-by-Step Execution

| Step | Action | Input | Expected Output | Assertion |
|------|--------|-------|-----------------|-----------|
| 1 | PR merges to main (simulated) | CI sends on-ship webhook: `{pr_url: "github.com/rx...", commit_sha: "abc123", test_job_url: "ci.../jobs/456", merged_at: "2026-08-02T15:00:00Z", station_tag: "marshal"}` | Webhook received; no 500 error | HTTP 202 response from Herald |
| 2 | Herald processes webhook | Webhook handler extracts payload fields | Progress record created in database with status=draft | `SELECT * FROM progress WHERE station='marshal'` returns 1 row with status='draft' |
| 3 | Herald queries CI job for test results + cost | Mock API calls to CI + dashboard | Evidence extracted: test_results link + compute_hours + token_spend | Progress record evidence array contains at least test_results type |
| 4 | Operator is alerted (CLI/web) | Progress dashboard shows new draft record | Operator sees "Author narrative for Marshal progress?" | CLI prompt or web notification appears |
| 5 | Operator authors progress narrative | Operator runs `herald progress marshal --list --status draft` | Draft record displayed with all fields | Exit code 0; narrative field visible (currently empty) |
| 6 | Operator adds narrative | Operator runs `herald progress marshal --update --narrative "Delivered harness policy to 8 stations"` | Narrative updated; record published | `herald progress marshal --list --status published` shows record with narrative |
| 7 | Same CI fires on-PR-close webhook | CI sends: `{pr_url: "...", gates_passed: true, ...}` | Webhook received | HTTP 202 response |
| 8 | Herald auto-extracts success claim | Claim handler creates draft Claim | Draft Claim in database with evidence | `SELECT * FROM claims WHERE status='draft'` returns 1 row with project_name='Marshal', evidence array not empty |
| 9 | Operator reviews extracted claim | Operator runs `herald success review <claim-id>` | Claim details + evidence + prompt shown | Exit code 0; claim displayable; `Publish? [Y/n]` prompt appears |
| 10 | Operator authors thesis | Operator runs `herald success publish <claim-id> --thesis "Harness policy governance layer"` | Evidence validated (sync); claim published | Exit code 0; claim status='published'; published_at set; `herald success list --status published` shows claim |
| 11 | Claim visible in web archive | Operator opens Herald web → Success tab | Claim displayed with project, thesis, evidence badges | Tab loads <2s; claim card visible; all badges green (evidence valid) |

### Assertions (Summary)

- ✅ Progress record created by webhook with correct station, shipped_date, evidence  
- ✅ Operator can author narrative without separate CLI tool  
- ✅ Claim auto-extracted with project name + evidence links correct  
- ✅ Claim published only after operator review + thesis authoring  
- ✅ Both visible in CLI + web with consistent state  
- ✅ No data corruption; audit trail complete for all transitions

---

## Scenario 2: Notice Authored → Published → Archive Indexed → Redirect Rule Works

**Objective**: Verify deprecation notice lifecycle from authoring through archive indexing and URL permanence.

**Risk Coverage**: Manual operator authoring, archive indexing, redirect rules, state machine.

### Setup

```yaml
Pre-conditions:
  - Herald CLI configured with operator token
  - Notice table initialized
  - Archive directory (/operations/notices/) ready
  - Redirect middleware configured

Actors:
  - Operator (authors notice)
  - Herald system (manages archive + redirects)
```

### Step-by-Step Execution

| Step | Action | Input | Expected Output | Assertion |
|------|--------|-------|-----------------|-----------|
| 1 | Operator authors deprecation notice | Operator runs `herald notice author --type deprecation --component auth-api-v1 --deadline 2026-12-31` | Interactive prompts for what_changed, why, migration_path | CLI shows fields one by one; operator inputs for each |
| 2 | System generates draft notice | Operator provides all fields interactively | Draft notice stored; not yet published | `herald notice list --status draft` shows new notice; `herald notice archive` doesn't include it yet |
| 3 | Operator confirms publish | Operator prompted: "Publish notice? [Y/n]" (user enters Y) | Notice moved to published state; archive path generated | Notice status='published'; notice_url set to `/operations/notices/deprecation/2026-08/auth-api-v1.md` |
| 4 | Notice archived as markdown file | Herald system writes notice to disk | File created at `/operations/notices/deprecation/2026-08/auth-api-v1.md` | File exists; frontmatter + content readable |
| 5 | Archive indexing updated | Cron or event-driven indexing | Archive index lists: deprecation → 2026-08 → auth-api-v1 | `herald notice archive` shows category count ("Deprecation: 1 notice") |
| 6 | Operator accesses notice via archive URL | Operator opens browser to `/operations/notices/deprecation/2026-08/auth-api-v1.md` | Notice displayed in Herald web (Operations tab) OR static HTML | Notice readable; deadline visible; migration path clear |
| 7 | Component renamed (simulated) | Operator runs `herald notice rename auth-api-v1 auth-api-deprecated` | Old component name updated to new | New notice_url generated; redirect rule created |
| 8 | Redirect rule applied | Old URL accessed: `/operations/notices/deprecation/2026-08/auth-api-v1.md` | HTTP 301/302 redirect to new URL | Browser follows redirect; notice displayed at new URL |
| 9 | Old URL still accessible (no 404) | Operator/tool hits old URL | Redirect fired; new URL resolved | Exit code 0; notice found at new location |
| 10 | Notice closed after deadline | Operator or cron marks notice closed (after 2026-12-31) | Notice status='closed'; archived (invisible to new readers) OR still visible with "archived" indicator | Notice remains queryable; no 404; UI indicates "closed" |

### Assertions (Summary)

- ✅ Notice authored interactively without external editor  
- ✅ Draft invisible; published visible; closed archived  
- ✅ Archive directory structure correct (YYYY-MM/category/name.md)  
- ✅ Notice URLs permanent (no 404 if component renamed)  
- ✅ Redirect rules work transparently (old URL → new URL)  
- ✅ Audit trail tracks all transitions + who + when

---

## Scenario 3: Evidence Link Broken (Stale) → Weekly Validation Catches It → Operator Alerted

**Objective**: Verify evidence integrity checking: stale links detected, operator alerted, link re-validation atomic.

**Risk Coverage**: Async validation, evidence integrity, operator alerting, state consistency.

### Setup

```yaml
Pre-conditions:
  - Herald running with published Claim containing evidence link
  - APScheduler weekly cron configured (test via time-mocking)
  - Operator email/dashboard alerts configured
  - Mock HTTP server (simulates evidence URLs)

Actors:
  - Herald system (async validation job)
  - Operator (receives alert)
  - External service (evidence URL provider)
```

### Step-by-Step Execution

| Step | Action | Input | Expected Output | Assertion |
|------|--------|-------|-----------------|-----------|
| 1 | Claim published with valid evidence | Operator runs `herald success publish <id> --thesis "..."` with evidence link to CI job URL | Sync validation passes (mock HTTP 200); claim published | claim.status='published'; evidence.is_valid=True; evidence.last_validated_at=now |
| 2 | Time passes (mocked) | Advance test time 7 days forward | No operations; claim remains published | Claim state unchanged; is_valid still True |
| 3 | Weekly validation cron fires | Thursday 2300 UTC arrives (mocked) | Async job runs; queries all published claims | Job start logged; claim included in batch |
| 4 | Validation job re-checks evidence link | Async job makes HEAD request to evidence URL | Mock server returns 404 (upstream CI job URL deleted) | Validation result: is_valid=False; status=404; last_validated_at=now |
| 5 | Stale link marked + audit logged | Validation result stored; evidence.is_stale=True | Database updated atomically; audit log entry created | evidence.is_stale=True; evidence.stale_detected_at set; audit log: {claim_id, evidence_url, status_was_404, actor=system} |
| 6 | Operator alert generated | Alert system queries stale evidence; creates notification | Email + dashboard entry | Operator receives email: "Evidence link may be broken: [claim-id] [URL]"; dashboard shows alert icon |
| 7 | Operator opens web dashboard | Operator logs in; visits Success tab | Claim card shows evidence badge in yellow (stale) instead of green (valid) | Badge color changed; tooltip shows "hasn't been validated recently" + date |
| 8 | Operator hovers evidence badge | Operator views warning tooltip | Tooltip explains stale status + last validation date | Tooltip text: "Last validated [date]. Review this link." + "Link may be broken: HTTP 404" |
| 9 | Operator clicks evidence link | Operator attempts to open CI URL | Link resolves to 404 page (or is blocked) | Operator confirms link is broken; can unlink or wait for operator to fix |
| 10 | Operator removes broken link (optional) | Operator runs `herald success unlink-evidence <claim-id> <evidence-id>` | Broken link removed; claim still published (but with fewer evidence links) | evidence array updated; audit log: {claim_id, removed_evidence_id, actor=<operator>, reason="404"} |
| 11 | Claim remains published (no revocation) | Claim visible in archive without broken link | Claim status=published (unchanged); evidence array has 1 fewer link | Archive still shows claim; just with updated evidence count |

### Assertions (Summary)

- ✅ Sync validation blocks publish if links are 404  
- ✅ Async validation detects 404s weekly  
- ✅ Stale links marked + operator alerted  
- ✅ Operator can remove broken links without revoking claim  
- ✅ Audit trail records all validation + removal actions  
- ✅ Claim remains published (evidence integrity issue, not claim rejection)  
- ✅ No race conditions (concurrent validation + removal)

---

---

# MOMENT 4: FRAMEWORK ARCHITECTURE

## Fixture Strategy (Reusable Test Infrastructure)

### 1. CLI Testing Fixtures

**Purpose**: Mock Click CLI framework without launching actual subprocess.

```python
# tests/fixtures/cli_fixtures.py

@pytest.fixture
def herald_cli_runner():
    """Return Click CliRunner for CLI testing."""
    from click.testing import CliRunner
    return CliRunner()

@pytest.fixture
def mock_auth_context():
    """Return mock auth context (operator role)."""
    return {
        'token': 'test-token-xyz',
        'actor': 'test-operator',
        'role': 'operator',  # 'operator' or 'viewer'
    }

@pytest.fixture
def mock_auth_context_viewer():
    """Return mock auth context (viewer role, read-only)."""
    return {
        'token': 'test-token-viewer',
        'actor': 'test-viewer',
        'role': 'viewer',
    }

@pytest.fixture
def mock_auth_missing():
    """Return mock auth context (missing token)."""
    return None

@pytest.fixture
def herald_cli_with_auth(herald_cli_runner, mock_auth_context, monkeypatch):
    """Return CliRunner + inject auth context into environment."""
    monkeypatch.setenv('HERALD_TOKEN', mock_auth_context['token'])
    return herald_cli_runner
```

### 2. Database Fixtures

**Purpose**: Isolated test database with schema + sample data.

```python
# tests/fixtures/db_fixtures.py

@pytest.fixture(scope='function')
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

@pytest.fixture
def progress_record_factory(test_db):
    """Factory to create Progress records."""
    def make_progress(
        station='warden',
        date=None,
        shipped_capabilities=None,
        compute_hours=10.5,
        token_spend=50000,
        wall_clock_hours=4.2,
        unblock_narrative='Test narrative',
        status='draft',
    ):
        if date is None:
            date = datetime.utcnow()
        if shipped_capabilities is None:
            shipped_capabilities = ['Feature A', 'Feature B']
        
        record = Progress(
            station=station,
            date=date,
            shipped_capabilities=shipped_capabilities,
            compute_hours=compute_hours,
            token_spend=token_spend,
            wall_clock_hours=wall_clock_hours,
            unblock_narrative=unblock_narrative,
            status=status,
        )
        test_db.add(record)
        test_db.commit()
        return record
    
    return make_progress

@pytest.fixture
def claim_record_factory(test_db):
    """Factory to create Claim records."""
    def make_claim(
        project_name='Marshal S-1.10',
        thesis=None,
        status='draft',
        evidence=None,
        shipped_date=None,
    ):
        if shipped_date is None:
            shipped_date = datetime.utcnow()
        if evidence is None:
            evidence = [
                {
                    'type': 'test_results',
                    'url': 'https://ci.example.com/jobs/123',
                    'label': 'CI job #123',
                    'is_valid': True,
                    'last_validated_at': datetime.utcnow().isoformat(),
                }
            ]
        
        record = Claim(
            project_name=project_name,
            thesis=thesis,
            status=status,
            evidence=evidence,
            shipped_date=shipped_date,
        )
        test_db.add(record)
        test_db.commit()
        return record
    
    return make_claim
```

### 3. Webhook Payload Fixtures

**Purpose**: Real-world CI webhook payloads for testing deserialization + handler logic.

```python
# tests/fixtures/webhook_fixtures.py

@pytest.fixture
def on_ship_webhook_payload():
    """Valid on-ship webhook from CI."""
    return {
        'pr_url': 'https://github.com/rxm7706/local-recipes/pull/123',
        'commit_sha': 'abc123def456',
        'test_job_url': 'https://ci.example.com/jobs/456',
        'merged_at': '2026-08-02T15:00:00Z',
        'station_tag': 'marshal',
    }

@pytest.fixture
def on_pr_close_webhook_payload():
    """Valid on-PR-close webhook from CI."""
    return {
        'pr_url': 'https://github.com/rxm7706/local-recipes/pull/123',
        'commit_sha': 'abc123def456',
        'test_job_url': 'https://ci.example.com/jobs/456',
        'close_at': '2026-08-02T15:30:00Z',
        'gates_passed': True,
    }

@pytest.fixture
def on_pr_close_webhook_gates_failed():
    """on-PR-close webhook with failed gates."""
    return {
        'pr_url': 'https://github.com/rxm7706/local-recipes/pull/124',
        'commit_sha': 'xyz789',
        'close_at': '2026-08-02T16:00:00Z',
        'gates_passed': False,
    }

@pytest.fixture
def webhook_payload_missing_field():
    """Invalid webhook payload (missing required field)."""
    return {
        'pr_url': 'https://github.com/...',
        # missing: commit_sha, merged_at, etc.
    }
```

### 4. HTTP Mocking Fixtures

**Purpose**: Mock external HTTP services (CI, dashboard, evidence URLs).

```python
# tests/fixtures/http_fixtures.py

@pytest.fixture
def mock_http_responses(requests_mock):
    """Mock HTTP responses for evidence validation + dashboard queries."""
    # CI job URL (test results)
    requests_mock.head(
        'https://ci.example.com/jobs/456',
        status_code=200,
        headers={'Content-Length': '1000'},
    )
    
    # Dashboard metrics API
    requests_mock.get(
        'https://dashboard.example.com/api/metrics/marshal-s-1-10',
        json={'error_rate': 0.01, 'latency_p99': 250},
    )
    
    # Broken link (404)
    requests_mock.head(
        'https://old-ci.example.com/jobs/deleted',
        status_code=404,
    )
    
    # Redirect chain
    requests_mock.head(
        'https://example.com/old-path',
        status_code=302,
        headers={'Location': 'https://example.com/new-path'},
    )
    requests_mock.head(
        'https://example.com/new-path',
        status_code=200,
    )
    
    return requests_mock

@pytest.fixture
def mock_ci_job_api():
    """Mock CI job API for extracting test results."""
    return {
        'status': 'passed',
        'tests_passed': 456,
        'tests_failed': 0,
        'duration': 120,  # seconds
    }
```

### 5. Time-Based Fixtures

**Purpose**: Mock system time for cron scheduling + stale-link detection.

```python
# tests/fixtures/time_fixtures.py

@pytest.fixture
def mock_time(freezegun):
    """Freeze time to a known date (2026-08-02 15:00:00 UTC)."""
    with freezegun.freeze_time('2026-08-02 15:00:00'):
        yield freezegun.freeze_time

@pytest.fixture
def time_advanced_7_days(freezegun):
    """Advance time 7 days forward (for stale-link detection)."""
    with freezegun.freeze_time('2026-08-09 15:00:00'):  # 7 days later
        yield freezegun.freeze_time

@pytest.fixture
def time_thursday_2300_utc(freezegun):
    """Mock time to Thursday 23:00 UTC (for weekly cron)."""
    # 2026-08-06 is a Thursday
    with freezegun.freeze_time('2026-08-06 23:00:00'):
        yield freezegun.freeze_time
```

### 6. State + Assertion Helpers

**Purpose**: Helper functions for common state checks + assertions.

```python
# tests/fixtures/assertion_helpers.py

@pytest.fixture
def assert_progress_record():
    """Assert Progress record has expected state."""
    def _assert(record, **kwargs):
        for key, expected_value in kwargs.items():
            actual = getattr(record, key)
            assert actual == expected_value, f"Progress.{key}: expected {expected_value}, got {actual}"
    return _assert

@pytest.fixture
def assert_claim_published():
    """Assert Claim is published with valid evidence."""
    def _assert(claim):
        assert claim.status == 'published', f"Claim status: expected 'published', got {claim.status}"
        assert claim.published_at is not None, "Claim.published_at is None"
        assert claim.thesis is not None and len(claim.thesis) > 0, "Claim.thesis is empty"
        assert len(claim.evidence) > 0, "Claim.evidence is empty"
        for link in claim.evidence:
            assert link['is_valid'] == True, f"Evidence link invalid: {link['url']}"
    return _assert

@pytest.fixture
def assert_evidence_link_validated():
    """Assert evidence link has validation metadata."""
    def _assert(link):
        assert 'url' in link, "Evidence link missing 'url'"
        assert 'is_valid' in link, "Evidence link missing 'is_valid'"
        assert 'last_validated_at' in link, "Evidence link missing 'last_validated_at'"
    return _assert
```

---

## Test Data Builders

**Purpose**: Composable builders for complex test scenarios.

```python
# tests/builders/test_data_builders.py

class ProgressBuilder:
    """Builder for Progress records with fluent API."""
    def __init__(self):
        self.data = {
            'station': 'warden',
            'date': datetime.utcnow(),
            'shipped_capabilities': ['Feature A'],
            'compute_hours': 10.0,
            'token_spend': 50000,
            'wall_clock_hours': 4.0,
            'unblock_narrative': None,
            'status': 'draft',
        }
    
    def with_station(self, station):
        self.data['station'] = station
        return self
    
    def with_narrative(self, narrative):
        self.data['unblock_narrative'] = narrative
        return self
    
    def published(self):
        self.data['status'] = 'published'
        return self
    
    def with_capabilities(self, *capabilities):
        self.data['shipped_capabilities'] = list(capabilities)
        return self
    
    def build(self):
        return Progress(**self.data)

class ClaimBuilder:
    """Builder for Claim records."""
    def __init__(self):
        self.data = {
            'project_name': 'Test Project',
            'thesis': None,
            'status': 'draft',
            'evidence': [],
            'shipped_date': datetime.utcnow(),
        }
    
    def with_evidence_link(self, link_type, url, label):
        self.data['evidence'].append({
            'type': link_type,
            'url': url,
            'label': label,
            'is_valid': True,
            'last_validated_at': datetime.utcnow().isoformat(),
        })
        return self
    
    def with_thesis(self, thesis):
        self.data['thesis'] = thesis
        return self
    
    def published(self):
        self.data['status'] = 'published'
        return self
    
    def build(self):
        return Claim(**self.data)

# Usage:
# claim = ClaimBuilder() \
#     .with_evidence_link('test_results', 'https://ci.../job/123', 'CI tests') \
#     .with_thesis('Delivered feature X') \
#     .published() \
#     .build()
```

---

## Framework Scaffold (Directory Structure)

```
tests/
├── fixtures/
│   ├── __init__.py
│   ├── cli_fixtures.py          # CLI runner, auth context
│   ├── db_fixtures.py           # Database + record factories
│   ├── webhook_fixtures.py      # CI webhook payloads
│   ├── http_fixtures.py         # Mock HTTP responses
│   ├── time_fixtures.py         # Time mocking (freezegun)
│   ├── assertion_helpers.py     # State assertion helpers
│   └── conftest.py              # Shared pytest config
│
├── builders/
│   ├── __init__.py
│   └── test_data_builders.py    # Fluent builders (ProgressBuilder, ClaimBuilder, etc.)
│
├── unit/
│   ├── __init__.py
│   ├── test_dispatcher.py       # Story 1.1
│   ├── test_cli_args.py         # Story 1.2
│   ├── test_auth.py             # Story 1.3
│   ├── test_evidence_validation.py  # Story 1.4
│   ├── test_progress_model.py   # Story 3.1
│   ├── test_webhook_handlers.py # Story 3.2
│   ├── test_claim_model.py      # Story 4.1
│   ├── test_claim_extract.py    # Story 4.2
│   └── [more unit tests per story]
│
├── integration/
│   ├── __init__.py
│   ├── test_cli_web_integration.py   # Cross-surface
│   ├── test_webhook_to_progress.py   # Story 3.2 integration
│   ├── test_webhook_to_claim.py      # Story 4.2 integration
│   ├── test_evidence_validation_sync_async.py  # Story 4.5
│   └── [more integration tests per story]
│
├── e2e/
│   ├── __init__.py
│   ├── test_scenario_1_pr_to_claim.py      # Scenario 1
│   ├── test_scenario_2_notice_archive.py   # Scenario 2
│   ├── test_scenario_3_stale_link.py       # Scenario 3
│   └── test_cross_moment_workflows.py      # Multi-scenario
│
├── performance/
│   ├── __init__.py
│   ├── test_cli_latency.py      # CLI <1s (95th percentile)
│   ├── test_query_performance.py # Queries <500ms
│   ├── test_web_load_time.py    # Tabs <2s
│   └── test_memory_leaks.py     # No unbounded growth
│
└── conftest.py                  # Root pytest config
```

---

---

# PLAYWRIGHT IMPLEMENTATION (Default Framework)

## Overview

**Playwright is the default testing framework** for Herald Moments 2–4, covering:
- ✅ **Web UI testing** (React components, interactions, responsive design, visual regression)
- ✅ **CLI testing** (spawning `herald` subprocess, capturing output, exit codes)
- ✅ **Integration testing** (coordinating CLI + web + database + webhooks)
- ✅ **Automation testing** (async validation, cron scheduling, webhook simulation)

**Framework Pluggability**: The test architecture remains framework-agnostic. Playwright is the default implementation, but other frameworks (Cypress, Selenium, custom scripts) can substitute if they implement the same test matrix and fixtures interface.

---

## Setup & Configuration

### Installation

```bash
# Add Playwright to conda-forge or pixi environment
pixi add --channel conda-forge playwright python-playwright

# OR via conda
conda install -c conda-forge playwright

# Install browser binaries
playwright install chromium firefox webkit

# For CI (headless + xvfb if needed)
playwright install-deps
```

### Configuration Files

#### `playwright.config.ts` (Root)

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: '**/*test.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],
  
  use: {
    baseURL: 'http://localhost:5173', // Vite dev server
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
  
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],
});
```

#### `pytest.ini` (Python unit/integration)

```ini
[pytest]
testpaths = tests/unit tests/integration tests/performance
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --cov=herald 
    --cov-report=html 
    --cov-report=term-missing 
    --strict-markers
markers =
    unit: unit tests (fast)
    integration: integration tests (medium)
    e2e: end-to-end tests (slow)
    performance: performance benchmarks
    high_risk: high-risk feature tests
```

---

## CLI Testing with Playwright

### Pattern 1: Subprocess-Based CLI Testing (Recommended)

**Purpose**: Test the actual `herald` CLI as an external process, capturing stdout/stderr/exit codes.

```typescript
// tests/e2e/cli/cli-fixtures.ts

import { spawn } from 'child_process';
import { promisify } from 'util';
import { exec } from 'child_process';

const execAsync = promisify(exec);

export class CliRunner {
  private pythonPath: string;
  private env: NodeJS.ProcessEnv;
  
  constructor(pythonPath = 'python', env?: NodeJS.ProcessEnv) {
    this.pythonPath = pythonPath;
    this.env = {
      PATH: process.env.PATH,
      HERALD_TOKEN: 'test-token-xyz',
      HERALD_ROLE: 'operator',
      ...env,
    };
  }
  
  async run(args: string[]): Promise<CliResult> {
    const command = `${this.pythonPath} -m herald ${args.join(' ')}`;
    
    try {
      const { stdout, stderr } = await execAsync(command, {
        env: this.env,
        timeout: 10000, // 10s timeout
      });
      
      return {
        success: true,
        stdout: stdout.trim(),
        stderr: stderr.trim(),
        exitCode: 0,
      };
    } catch (error: any) {
      return {
        success: false,
        stdout: error.stdout?.trim() || '',
        stderr: error.stderr?.trim() || '',
        exitCode: error.code || 1,
      };
    }
  }
  
  async runJson(args: string[]): Promise<any> {
    const result = await this.run([...args, '--json']);
    if (!result.success) throw new Error(result.stderr);
    return JSON.parse(result.stdout);
  }
}

export interface CliResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exitCode: number;
}
```

### Pattern 2: CLI Test Cases

```typescript
// tests/e2e/cli/test-progress-cli.ts

import { test, expect } from '@playwright/test';
import { CliRunner } from './cli-fixtures';

test.describe('herald progress command', () => {
  let cli: CliRunner;
  
  test.beforeEach(() => {
    cli = new CliRunner(process.env.PYTHON_PATH || 'python');
  });
  
  test('progress <station> returns latest record', async () => {
    // Setup: create sample progress record in test DB
    // (this would typically be done via API or fixture)
    
    const result = await cli.run(['progress', 'warden']);
    
    expect(result.exitCode).toBe(0);
    expect(result.stdout).toContain('warden');
    expect(result.stdout).toContain('shipped_capabilities');
  });
  
  test('progress --json returns valid JSON', async () => {
    const data = await cli.runJson(['progress', 'warden']);
    
    expect(data).toHaveProperty('station', 'warden');
    expect(data).toHaveProperty('shipped_capabilities');
    expect(Array.isArray(data.shipped_capabilities)).toBe(true);
  });
  
  test('progress --date-range filters by date', async () => {
    const result = await cli.run([
      'progress',
      '--list',
      '--date-range', '2026-08-01..2026-08-02',
    ]);
    
    expect(result.exitCode).toBe(0);
    // Verify only records in date range returned
  });
  
  test('progress with unknown station returns error', async () => {
    const result = await cli.run(['progress', 'unknown-station']);
    
    expect(result.success).toBe(false);
    expect(result.exitCode).toBe(1);
    expect(result.stderr).toContain('not found');
    expect(result.stderr).toContain('Available:');
  });
  
  test('progress --help shows usage and examples', async () => {
    const result = await cli.run(['progress', '--help']);
    
    expect(result.exitCode).toBe(0);
    expect(result.stdout).toContain('Usage:');
    expect(result.stdout).toContain('--update');
    expect(result.stdout).toContain('--date-range');
    expect(result.stdout).toContain('Examples:');
  });
});
```

---

## Web Testing with Playwright

### Pattern 3: Page Object Model

```typescript
// tests/e2e/pages/herald-page.ts

import { Page } from '@playwright/test';

export class HeraldPage {
  constructor(private page: Page) {}
  
  async navigate() {
    await this.page.goto('/');
  }
  
  async clickTab(tabName: 'progress' | 'success' | 'operations') {
    await this.page.click(`[data-test="tab-${tabName}"]`);
    // Wait for tab content to load
    await this.page.waitForSelector(`[data-test="tab-content-${tabName}"]`);
  }
  
  async selectStation(station: string) {
    await this.page.selectOption('[data-test="station-filter"]', station);
    // Wait for content to re-filter
    await this.page.waitForTimeout(300);
  }
  
  async setDateRange(start: string, end: string) {
    await this.page.fill('[data-test="date-range-start"]', start);
    await this.page.fill('[data-test="date-range-end"]', end);
    await this.page.click('[data-test="apply-filters"]');
  }
  
  async getTabContent() {
    return await this.page.innerText('[data-test="tab-content"]');
  }
  
  async searchFor(query: string) {
    await this.page.fill('[data-test="search-box"]', query);
    await this.page.press('[data-test="search-box"]', 'Enter');
  }
}

export class ProgressTabPage extends HeraldPage {
  async getProgressCards() {
    return await this.page.$$('[data-test="progress-card"]');
  }
  
  async expandCard(index: number) {
    const cards = await this.getProgressCards();
    await cards[index].click();
    await this.page.waitForSelector('[data-test="card-detail"]');
  }
  
  async getCardDetail(index: number) {
    await this.expandCard(index);
    return await this.page.innerText('[data-test="card-detail"]');
  }
  
  async triggerProgressUpdate() {
    await this.page.click('[data-test="trigger-update-button"]');
    await this.page.waitForNavigation();
  }
}

export class SuccessTabPage extends HeraldPage {
  async getClaimCards() {
    return await this.page.$$('[data-test="claim-card"]');
  }
  
  async getEvidenceBadges(claimIndex: number) {
    const cards = await this.getClaimCards();
    const card = cards[claimIndex];
    return await card.$$('[data-test="evidence-badge"]');
  }
  
  async clickEvidenceLink(claimIndex: number, linkIndex: number) {
    const cards = await this.getClaimCards();
    const card = cards[claimIndex];
    await card.click();
    const links = await card.$$('[data-test="evidence-link"]');
    // Return in new context (window opens)
    const [popup] = await Promise.all([
      this.page.context().waitForEvent('page'),
      links[linkIndex].click(),
    ]);
    return popup;
  }
}
```

### Pattern 4: Web Test Cases

```typescript
// tests/e2e/web/test-progress-tab.ts

import { test, expect } from '@playwright/test';
import { HeraldPage, ProgressTabPage } from '../pages';

test.describe('Progress Tab', () => {
  let heraldPage: HeraldPage;
  let progressPage: ProgressTabPage;
  
  test.beforeEach(async ({ page }) => {
    heraldPage = new HeraldPage(page);
    progressPage = new ProgressTabPage(page);
    await heraldPage.navigate();
    await heraldPage.clickTab('progress');
  });
  
  test('displays progress cards for all stations', async ({ page }) => {
    const cards = await progressPage.getProgressCards();
    expect(cards.length).toBeGreaterThan(0);
  });
  
  test('card shows station, date, and shipped count', async () => {
    const detail = await page.innerText('[data-test="progress-card:0"]');
    expect(detail).toContain('warden');
    expect(detail).toContain('2026-08');
    expect(detail).toContain('shipped');
  });
  
  test('filter by station updates results', async ({ page }) => {
    await progressPage.selectStation('atlas');
    const cards = await progressPage.getProgressCards();
    
    for (const card of cards) {
      const text = await card.innerText();
      expect(text).toContain('atlas');
    }
  });
  
  test('expand card shows full narrative', async () => {
    const detail = await progressPage.getCardDetail(0);
    expect(detail).toContain('unblock narrative');
    expect(detail).toContain('compute_hours');
  });
  
  test('responsive layout: mobile stacks cards vertically', async ({ page }) => {
    // Emulate mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    const cards = await progressPage.getProgressCards();
    for (const card of cards) {
      const box = await card.boundingBox();
      // Card width should be ~375px (full mobile width)
      expect(box?.width).toBeLessThanOrEqual(375);
    }
  });
  
  test('trigger update button calls API', async ({ page }) => {
    // Mock API response
    await page.route('**/api/herald/progress*', async (route) => {
      route.abort('failed'); // Simulate error
    });
    
    await progressPage.triggerProgressUpdate();
    
    const errorMsg = await page.innerText('[data-test="error-message"]');
    expect(errorMsg).toContain('failed');
  });
});
```

---

## Integration Testing: CLI + Web Coordination

### Pattern 5: Coordinated CLI + Web Tests

```typescript
// tests/e2e/integration/test-cli-web-sync.ts

import { test, expect } from '@playwright/test';
import { CliRunner } from '../cli/cli-fixtures';
import { ProgressTabPage } from '../pages';

test.describe('CLI ↔ Web Synchronization', () => {
  let cli: CliRunner;
  let progressPage: ProgressTabPage;
  
  test.beforeEach(async ({ page }) => {
    cli = new CliRunner();
    progressPage = new ProgressTabPage(page);
  });
  
  test('CLI updates progress → Web reflects change', async ({ page }) => {
    // 1. Create progress via CLI
    const result = await cli.run([
      'progress', 'warden',
      '--update',
      '--narrative', 'Test narrative'
    ]);
    expect(result.exitCode).toBe(0);
    
    // 2. Navigate to web, refresh
    await progressPage.navigate();
    await progressPage.clickTab('progress');
    await progressPage.selectStation('warden');
    
    // 3. Verify progress visible in web
    const detail = await progressPage.getCardDetail(0);
    expect(detail).toContain('Test narrative');
  });
  
  test('Web publishes claim → CLI lists it', async ({ page }) => {
    // 1. Publish claim via web form
    // (this would involve navigating to success tab, filling form, clicking publish)
    
    // 2. Query via CLI
    const data = await cli.runJson(['success', 'list', '--status', 'published']);
    
    // 3. Verify CLI shows published claim
    expect(data.claims.length).toBeGreaterThan(0);
  });
});
```

---

## Async & Automation Testing

### Pattern 6: Webhook + Cron Simulation

```typescript
// tests/e2e/integration/test-webhook-automation.ts

import { test, expect } from '@playwright/test';
import { CliRunner } from '../cli/cli-fixtures';
import axios from 'axios';

test.describe('Webhook Automation', () => {
  let cli: CliRunner;
  
  test.beforeEach(async () => {
    cli = new CliRunner();
  });
  
  test('on-ship webhook creates progress record', async () => {
    // 1. Simulate CI webhook
    const webhookPayload = {
      pr_url: 'https://github.com/rxm7706/local-recipes/pull/200',
      commit_sha: 'abc123def456',
      test_job_url: 'https://ci.example.com/jobs/12345',
      merged_at: new Date().toISOString(),
      station_tag: 'warden',
    };
    
    const response = await axios.post(
      'http://localhost:8000/api/herald/webhooks/on-ship',
      webhookPayload,
      {
        headers: {
          'X-Webhook-Signature': computeSignature(webhookPayload),
          'Content-Type': 'application/json',
        },
      }
    );
    
    expect(response.status).toBe(200);
    
    // 2. Query progress via CLI
    const data = await cli.runJson(['progress', 'warden']);
    expect(data.station).toBe('warden');
    expect(data.shipped_capabilities).toEqual(expect.any(Array));
  });
  
  test('weekly cron aggregates progress', async ({ clock }) => {
    // 1. Mock time to Thursday 2300 UTC
    clock.setSystemTime(new Date('2026-08-05T23:00:00Z')); // Thursday
    
    // 2. Trigger cron job manually (or wait for scheduler)
    const result = await cli.run(['_cron', 'progress-weekly']);
    expect(result.exitCode).toBe(0);
    
    // 3. Verify aggregated progress created
    const data = await cli.runJson(['progress', '--list', '--week', '0']);
    expect(data.records.length).toBeGreaterThan(0);
  });
});
```

### Pattern 7: Async Validation Testing

```typescript
// tests/e2e/integration/test-evidence-validation.ts

import { test, expect } from '@playwright/test';

test.describe('Evidence Validation (Sync + Async)', () => {
  test('sync validation at publish time', async ({ page, context }) => {
    // 1. Mock evidence URL (200 OK)
    await context.routeFromHAR('fixtures/evidence-urls.har', {
      url: 'https://ci.example.com/**',
      updateMode: 'missing',
    });
    
    // 2. Publish claim with evidence
    const result = await cli.run([
      'success', 'publish', 'claim-123',
      '--thesis', 'Feature shipped',
    ]);
    
    expect(result.exitCode).toBe(0);
    
    // 3. Verify all evidence links validated
    // (Check database or API for validation_status)
  });
  
  test('async weekly validation detects stale links', async ({ clock }) => {
    // 1. Mock time: 8 days after evidence link created
    clock.setSystemTime(new Date('2026-08-10T00:00:00Z'));
    
    // 2. Trigger async validation
    const result = await cli.run(['_cron', 'evidence-validation-weekly']);
    expect(result.exitCode).toBe(0);
    
    // 3. Verify stale link flagged
    const data = await cli.runJson(['success', 'get', 'claim-123']);
    const evidenceLink = data.evidence[0];
    expect(evidenceLink.is_stale).toBe(true);
  });
});
```

---

## Visual Regression Testing

### Pattern 8: Screenshot & Diff

```typescript
// tests/e2e/visual/test-responsive-layout.ts

import { test, expect } from '@playwright/test';

test.describe('Visual Regression', () => {
  test('progress tab desktop layout', async ({ page }) => {
    await page.goto('/');
    await page.click('[data-test="tab-progress"]');
    
    // Take screenshot at desktop size
    await expect(page).toHaveScreenshot('progress-tab-desktop.png', {
      maxDiffPixels: 100, // Allow 100px diff (rounding, date changes)
    });
  });
  
  test('success tab mobile layout', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.click('[data-test="tab-success"]');
    
    await expect(page).toHaveScreenshot('success-tab-mobile.png');
  });
  
  test('error state styling', async ({ page }) => {
    await page.goto('/');
    
    // Simulate error
    await page.route('**/api/**', (route) => route.abort('failed'));
    await page.click('[data-test="refresh-button"]');
    
    await expect(page).toHaveScreenshot('error-state.png');
  });
});
```

---

## Performance Testing with Playwright

### Pattern 9: Load Time & Latency Benchmarks

```typescript
// tests/performance/test-cli-latency.ts

import { test, expect } from '@playwright/test';
import { CliRunner } from '../e2e/cli/cli-fixtures';

test.describe('CLI Performance', () => {
  let cli: CliRunner;
  
  test.beforeEach(() => {
    cli = new CliRunner();
  });
  
  test('herald progress <station> responds <1s', async () => {
    const startTime = Date.now();
    const result = await cli.run(['progress', 'warden']);
    const elapsedMs = Date.now() - startTime;
    
    expect(result.exitCode).toBe(0);
    expect(elapsedMs).toBeLessThan(1000); // 1 second
  });
  
  test('herald success list responds <500ms', async () => {
    const startTime = Date.now();
    const result = await cli.run(['success', 'list']);
    const elapsedMs = Date.now() - startTime;
    
    expect(result.exitCode).toBe(0);
    expect(elapsedMs).toBeLessThan(500); // 500ms
  });
});

// tests/performance/test-web-load-time.ts
test.describe('Web Performance', () => {
  test('progress tab loads <2s', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/');
    await page.click('[data-test="tab-progress"]');
    await page.waitForSelector('[data-test="progress-card"]');
    const elapsedMs = Date.now() - startTime;
    
    expect(elapsedMs).toBeLessThan(2000); // 2 seconds (95th percentile target)
  });
});
```

---

## Making It Pluggable (Framework-Agnostic)

### Fixture Interface Contract

All test fixtures must implement this interface to remain framework-interchangeable:

```typescript
// tests/fixtures/fixture-interface.ts

export interface ICliRunner {
  run(args: string[]): Promise<CliResult>;
  runJson(args: string[]): Promise<any>;
}

export interface IWebPage {
  navigate(): Promise<void>;
  clickTab(tabName: string): Promise<void>;
  selectStation(station: string): Promise<void>;
  getContent(): Promise<string>;
}

export interface ITestDatabase {
  init(): Promise<void>;
  teardown(): Promise<void>;
  getRecord(table: string, id: string): Promise<any>;
  insertRecord(table: string, data: any): Promise<any>;
}

// Implementation can be Playwright, Cypress, or custom
// As long as interface is satisfied, tests remain portable
```

---

# MOMENT 4: QUALITY GATES & READINESS CRITERIA

## Coverage Targets

| Level | Target | Rationale | Measurement |
|-------|--------|-----------|-------------|
| **Unit** | >80% | Core logic (parsing, validation, state transitions) must be well-tested | `pytest --cov=herald/` |
| **Integration** | >70% | Cross-layer flows (CLI → DB, webhook → database, sync → async) need good coverage | `pytest tests/integration/ --cov=herald/` |
| **E2E** | Happy path + top 3 risks | Cannot test all scenarios; focus on critical paths: PR→Progress→Claim, Notice lifecycle, Evidence validation | `pytest tests/e2e/ -k "scenario"` |

### Unit Coverage by Epic

| Epic | Module | Coverage Target | Critical Paths |
|------|--------|-----------------|-----------------|
| 1 | herald/cli/dispatcher.py, herald/cli/args.py, herald/auth.py | >80% | Subcommand routing, flag parsing, role verification |
| 2 | herald/web/components/ (React) | >60% (lower for UI) | Responsive layout, tab nav, sidebar filters |
| 3 | herald/progress/model.py, herald/progress/cli.py, herald/progress/web.py | >80% | Progress CRUD, CLI output formatting, web API integration |
| 4 | herald/success/model.py, herald/success/extract.py, herald/success/cli.py | >80% | Claim CRUD, auto-extract logic, evidence validation |
| 5 | herald/notice/model.py, herald/notice/cli.py, herald/notice/archive.py | >75% | Notice CRUD, archive indexing, redirect rules |
| 6 | herald/evidence/protocol.py, herald/evidence/validation.py | >85% | Evidence validation (sync + async), link schema |

---

## Ready-to-Merge Criteria (Per Epic)

### Epic 1: CLI Architecture + Shared Infrastructure

**Must-Have**:
- ✅ All unit tests pass (dispatcher, args, auth)
- ✅ Unit coverage >80%
- ✅ Dispatcher routes all subcommands correctly (`herald --help` shows progress, success, notice)
- ✅ All global flags work across subcommands (`--json`, `--date-range`, `--station`)
- ✅ Role-based write gates enforced (operator role required for writes)
- ✅ Evidence validation library callable and tested
- ✅ Help text complete + examples work
- ✅ No security regressions (auth context not leaked; role checks not bypassed)

**Nice-to-Have**:
- CLI bash completion scripts
- Man page generation from help text

**Sign-Off**: Tech lead (CLI architecture) + Security (auth review)

---

### Epic 2: Web Surface

**Must-Have**:
- ✅ All components render without errors (header, tabs, sidebar, responsive layout)
- ✅ Responsive layout tested at 375px, 768px, 1200px (no horizontal scroll)
- ✅ Tab navigation works (state persists on reload)
- ✅ Sidebar filters functional (station, date range, search)
- ✅ Tooltips + help text display correctly
- ✅ Empty state messages helpful + actionable
- ✅ No console errors (React warnings fixed)
- ✅ Accessibility: keyboard navigation + screen-reader support for critical elements

**Nice-to-Have**:
- Dark mode support
- Keyboard shortcuts (j/k for tab nav, etc.)

**Sign-Off**: Tech lead (web) + UX (usability review)

---

### Epic 3: Progress Visibility

**Must-Have**:
- ✅ Progress table schema matches spec (all columns, types, indexes)
- ✅ Query performance <500ms on 10k records (EXPLAIN PLAN verified)
- ✅ Webhook handler deserialization correct (all payload variants handled)
- ✅ Webhook retry logic works (exponential backoff, max 3 retries)
- ✅ Cron scheduling verified (Thursday 2300 UTC fires)
- ✅ Progress records created with correct state (draft → published)
- ✅ Operator can author narrative via CLI or web
- ✅ CLI `herald progress` queries correct, output formatted properly
- ✅ Web Progress tab displays + filters work
- ✅ Unit tests >80%, integration >70%, e2e scenario passes
- ✅ Audit trail: all state transitions logged (who, what, when)

**Sign-Off**: Tech lead (backend + database) + Ops (automation review)

---

### Epic 4: Success Proclamation

**Must-Have**:
- ✅ Claim table schema matches spec (all columns, evidence schema)
- ✅ Query performance <500ms on 10k records
- ✅ Auto-extract logic works (webhook → draft claim with evidence)
- ✅ Evidence validation sync works (404 detection blocks publish)
- ✅ Evidence validation async works (weekly check, stale detection, alerts)
- ✅ Operator review gate enforced (no publish without thesis)
- ✅ Operator can author thesis via CLI or web
- ✅ CLI `herald success` commands work (review, publish, list, get)
- ✅ Web Success archive displays + filters work
- ✅ Evidence links clickable + redirect chains resolved
- ✅ Unit tests >80%, integration >70%, e2e scenario passes
- ✅ Audit trail: claim lifecycle logged (draft → published, evidence added/removed)

**Sign-Off**: Tech lead (backend) + Ops (automation + evidence review)

---

### Epic 5: Operations Notices

**Must-Have**:
- ✅ Notice table schema matches spec
- ✅ Archive directory structure correct (YYYY-MM/category/name.md)
- ✅ Operator can author notice via CLI (interactive prompts)
- ✅ Operator can publish notice (draft → published)
- ✅ Operator can close notice after deadline (published → closed)
- ✅ Notice URLs permanent (no 404 if component renamed; redirect rule works)
- ✅ Archive indexing correct (categories + months visible)
- ✅ CLI `herald notice` commands work (author, list, archive, get)
- ✅ Web Operations tab displays notices + filters work
- ✅ Unit tests >75%, integration >65%
- ✅ Audit trail: notice lifecycle logged

**Sign-Off**: Tech lead (backend) + Ops (notice authoring)

---

### Epic 6: Integration Testing & Automation Reliability

**Must-Have**:
- ✅ **Scenario 1** (PR → Progress → Claim → Published) passes end-to-end
- ✅ **Scenario 2** (Notice authored → published → archived → redirect works) passes
- ✅ **Scenario 3** (Evidence link breaks → weekly detection → operator alert) passes
- ✅ Webhook handlers don't race (concurrent webhooks handled safely)
- ✅ Cron + webhook don't race (claim created before progress, not after)
- ✅ Auth consistent across CLI + web (same role model, same tokens)
- ✅ Cross-Moment evidence linking works (Claim ↔ Notice bidirectional links)
- ✅ CLI latency <1s (95th percentile), <500ms (median)
- ✅ Query performance <500ms on realistic data (10k+ records)
- ✅ Web tab load <2s (95th percentile)
- ✅ No memory leaks (long session stable)
- ✅ E2E coverage: all 3 scenarios pass
- ✅ Operator alerts delivered correctly (email + dashboard)

**Sign-Off**: Tech lead (integration) + QA (scenarios)

---

### Epic 7: Documentation & Operator Experience

**Must-Have**:
- ✅ Help text complete (`herald --help`, `herald <subcommand> --help`)
- ✅ Examples in help text work (copy-paste ready)
- ✅ Error messages helpful (name problem + suggest fix)
- ✅ Runbooks written (progress authoring, notice authoring, troubleshooting)
- ✅ Inline web help (tooltips, ? buttons, empty-state messages)
- ✅ Troubleshooting guide covers key scenarios (webhook failures, automation misses, stale links)

**Sign-Off**: Tech lead (docs) + Ops (accuracy review)

---

## Ready-to-Ship Criteria (Full System)

**All Epics 1–7 merged + working together**:

| Criterion | Measurement | Pass/Fail |
|-----------|-------------|-----------|
| Unit test coverage >80% | `pytest --cov` output | ✅ Pass (no regressions) |
| Integration test coverage >70% | `pytest tests/integration --cov` | ✅ Pass |
| E2E scenarios all pass | 3 full end-to-end flows succeed | ✅ Pass (Scenarios 1, 2, 3) |
| Performance benchmarks | CLI <1s (p95), web tabs <2s (p95), queries <500ms | ✅ Pass (no regressions) |
| Security gates | Auth context not leaked; role checks not bypassed; no SQL injection | ✅ Pass (security review) |
| Evidence integrity | All evidence links validated at publish + weekly; stale links detected | ✅ Pass (no broken links in prod) |
| Automation reliability | Webhooks retry on failure; cron fires reliably; no silent data loss | ✅ Pass (operator alerts functional) |
| Cross-Moment coordination | Progress + Claim + Notice work together; evidence linking bidirectional | ✅ Pass (Scenario 1, 3 cover) |
| Operator experience | Help text complete; examples work; errors actionable; prompts clear | ✅ Pass (usability review) |
| Database migrations | Schema created + indexed correctly; concurrent writes safe | ✅ Pass (production-ready) |
| Deployment readiness | CI/CD gating verified; rollback plan documented; runbooks written | ✅ Pass (ops review) |

**Exit Criteria**:
- 🟢 All 11 criteria marked ✅ Pass
- 🟢 No known Critical or High bugs (Medium + Low acceptable with waivers)
- 🟢 Tech lead sign-off + Ops sign-off
- 🟢 Ready to deploy to staging → production

---

## Risk Acceptance Matrix (Known Waivers)

| Risk | Description | Mitigation | Waiver Owner |
|------|-------------|-----------|--------------|
| UI responsiveness at <375px | Very small phones may have layout issues | CSS media queries tested down to 375px; users can zoom | UX lead |
| Full-text search (Moment 4 archive) | Date/category filtering only; no keyword search | Acceptable for <100 notices/month; add full-text later if scale increases | Ops lead |
| Real-time collaboration | No live sync between operators | Acceptable; pull model is explicit (operator refreshes) | Product lead |
| Internationalization | English-only for now | Acceptable for internal factory; i18n added later if needed | Product lead |
| Multi-region Herald | Single unified service assumed | Acceptable for single-region deployment; geo-replication deferred | Ops lead |

---

---

## Summary

| Dimension | Target | Achievement Criteria |
|-----------|--------|----------------------|
| **Test Coverage** | Unit >80%, Integration >70%, E2E 3 scenarios | All critical paths covered; no gaps in core logic |
| **Risk Mitigation** | High-risk items have 2+ test levels | Webhook reliability, evidence integrity, auth gates all heavily tested |
| **Readiness** | Per-epic merge gates + system-level ship gate | Each epic independently ready; all together = production-ready |
| **Quality** | No regressions; performance benchmarks met | Automated checks enforce; manual review for sign-off |
| **Operator Experience** | Help text complete; examples work; errors actionable | Usability review + first-use operator trial before ship |

---

**Status**: ✅ **FRAMEWORK COMPLETE**

Test architecture is ready for handoff to implementation teams. Each story team has:
- Clear test matrix (unit/integration/e2e)
- Reusable fixtures (CLI runners, database, webhooks, HTTP mocks)
- Scenario-driven integration tests (3 end-to-end flows)
- Merge gates (per-epic) + ship gates (system-level)
- Performance benchmarks (CLI, queries, web)

All 18 stories can develop independently while sharing test infrastructure. Integration testing happens in Epic 6 with full scenario coverage.

---

# APPENDIX: Reusable Pattern for Other PyForge Projects

This test architecture is a **canonical reference** for all PyForge projects. Use this pattern for pyforge-atlas, pyforge-warden, pyforge-marshal, and the remaining 5 stations without re-deriving it.

## When to Apply This Pattern

✅ **Use this pattern for**:
- Any BMAD project with stories (output from `bmad-create-epics-and-stories`)
- Projects with CLI, web, API, or automation components
- Any project needing systematic test architecture before development

## How to Apply: 3-Step Process

### **Step 1: Dream → Spec**

Run `bmad-spec` to produce the spec.

```bash
bmad-spec docs/dreams/pyforge-atlas-improvements.md --project pyforge-atlas
```

Output: `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-*.md`

### **Step 2: Spec → Stories**

Run `bmad-create-epics-and-stories` to produce epics + stories with BDD acceptance criteria.

```bash
bmad-create-epics-and-stories \
  --spec _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-*.md \
  --project pyforge-atlas
```

Output: `_bmad-output/projects/pyforge-atlas/planning-artifacts/epics-with-stories.md`

### **Step 3: Stories → Test Architecture**

Run the automation script to generate test architecture:

```bash
python _bmad/scripts/bmad_tea_playwright.py \
  --project pyforge-atlas \
  --epics _bmad-output/projects/pyforge-atlas/planning-artifacts/epics-with-stories.md \
  --architecture _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/ARCHITECTURE-SPINE.md
```

Output: `_bmad-output/projects/pyforge-atlas/planning-artifacts/test-architecture-tea.md`

## Output Structure (Template)

Every project using this pattern will have:

```
<project>/
├── tests/
│   ├── fixtures/
│   │   ├── cli_fixtures.ts          # (if project has CLI)
│   │   ├── web_fixtures.ts          # (if project has web)
│   │   ├── db_fixtures.py           # (if project has database)
│   │   └── conftest.py              # pytest config
│   │
│   ├── unit/
│   │   ├── test_*.py                # Per-story unit tests
│   │   └── conftest.py
│   │
│   ├── integration/
│   │   ├── test_*.py                # Cross-story integration tests
│   │   └── conftest.py
│   │
│   ├── e2e/
│   │   ├── cli/
│   │   │   └── test_*.ts            # CLI e2e tests (Playwright)
│   │   ├── web/
│   │   │   └── test_*.ts            # Web e2e tests (Playwright)
│   │   ├── pages/                   # Page objects
│   │   └── conftest.ts
│   │
│   ├── performance/
│   │   └── test_*.ts                # Latency, throughput benchmarks
│   │
│   └── visual/
│       └── test_*.ts                # Visual regression tests
│
├── playwright.config.ts             # Playwright config (generated, project-specific)
├── pytest.ini                       # Pytest config (generated)
└── test-architecture-tea.md         # This file (generated)
```

## Key Customization Points

Each project's test architecture is customized based on:

1. **Project components**: Does it have CLI? Web? API? Webhooks?
2. **Risk profile**: High-risk items get more test layers
3. **Automation patterns**: Webhook + cron, manual authoring, real-time, etc.
4. **Technology stack**: 
   - Python backend → pytest + Click CliRunner
   - React frontend → Playwright web tests
   - Async jobs → mock time + async fixtures
   - Database → SQLAlchemy + test DB factories

## Shared Fixtures Package

All projects use the **same fixture patterns**. Use the shared package:

### `pyforge-testing-kit` (Shared Package)

Location: `src/shared/packages/pyforge-testing-kit/`

```
pyforge-testing-kit/
├── playwright/
│   ├── cli_runner.ts       # CliRunner base class (spawn subprocess)
│   ├── page_fixtures.ts    # Shared page objects (Header, Sidebar, etc.)
│   ├── http_mocks.ts       # Shared HTTP mocking patterns
│   └── time_mocks.ts       # Time-based mocking (freezegun, playright.clock)
│
├── pytest/
│   ├── db_fixtures.py      # Database factory base classes
│   ├── auth_fixtures.py    # Auth context fixtures
│   ├── builders.py         # Test data builders (ProgressBuilder, etc.)
│   └── assertion_helpers.py  # Shared assertion helpers
│
└── templates/
    ├── playwright.config.ts.jinja    # Config template (customizable per project)
    ├── pytest.ini.jinja              # Pytest config template
    └── conftest.ts.jinja             # Playwright conftest template
```

**Usage in each project**:
```python
# tests/fixtures/conftest.py
from pyforge_testing_kit.pytest import db_fixtures, auth_fixtures

# Reuse shared fixtures
@pytest.fixture
def test_db():
    return db_fixtures.create_test_db()

@pytest.fixture
def mock_auth():
    return auth_fixtures.mock_operator_role()
```

## Fleet Deployment Checklist

### Per Project

- [ ] Dream exists: `docs/dreams/<project>.md`
- [ ] Spec produced: `_bmad-output/projects/<project>/planning-artifacts/specs/spec-*.md`
- [ ] PRD produced: `_bmad-output/projects/<project>/planning-artifacts/prds/prd-*.md`
- [ ] Architecture produced: `_bmad-output/projects/<project>/planning-artifacts/architecture/*.md`
- [ ] Epics + Stories produced: `epics-with-stories.md`
- [ ] **Test architecture generated**: `test-architecture-tea.md`
- [ ] `tests/` directory scaffolded with fixtures
- [ ] `playwright.config.ts` + `pytest.ini` created
- [ ] Development teams ready to execute stories with tests

## Fleet Metrics

Dashboard should track per project:

```
Project          | Dream | Spec | PRD | Arch | Epics | Stories | Test Arch | Dev Ready
-----------------|-------|------|-----|------|-------|---------|-----------|----------
pyforge-herald   |  ✅   |  ✅  |  ✅  |  ✅  |   ✅   |    ✅    |    ✅     |    🚀
pyforge-atlas    |  ✅   |  ✅  |  ✅  |  ✅  |   ✅   |    ✅    |    ⏳     |    ⏸️
pyforge-warden   |  ✅   |  ✅  |  ✅  |  ✅  |   ✅   |    ✅    |    ⏳     |    ⏸️
pyforge-marshal  |  ✅   |  ✅  |  ✅  |  ✅  |   ✅   |    ✅    |    📋     |    ⏸️
```

Each step in the chain is **automated or templated** (no manual re-work per project).

## References

- **Automation Script**: `_bmad/scripts/bmad_tea_playwright.py`
- **Shared Testing Kit**: `src/shared/packages/pyforge-testing-kit/` (to be created)
- **Playwright docs**: https://playwright.dev/
- **BMAD TEA docs**: https://bmad-code-org.github.io/bmad-method-test-architecture-enterprise/llms-full.txt

