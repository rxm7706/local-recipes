---
title: "84.1: An operator-run refresh reads every harness's live model list and reports drift"
type: 'feature'
created: '2026-10-02'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: detector-or-gate   # a check that judges declared model ids against live lists; a gated check reports a silent green (spec-feature-flag-governance Q2)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/claude.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/cursor.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/gemini.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/copilot.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/adapters.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model_cost.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/oidc_pkce.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Every model id in marshal's policies is typed by hand and checked by hand. On 2026-10-02 Cursor no longer listed `grok-4.6`, which the medium tier of four stations named, and listed a new `grok-4.7-high`; it was found only because a session looked. Each harness exposes its list differently: Cursor's CLI lists the account's models (`cursor-agent models`, 246 ids on 2026-10-02); Claude Code and the Gemini CLI have no listing subcommand, but their APIs do (Anthropic `GET /v1/models`, Gemini `models.list`, both paged); the Copilot CLI documents none.

**Approach:** Each harness profile declares where its live list comes from: a command whose output lists ids, or a paged HTTP JSON listing with the credential named by an environment variable, plus the aliases its CLI accepts that no listing shows. One operator-run marshal command reads every declared source, writes a dated snapshot of every id it read, and prints an advisory report. The report names each declared model id that its harness's live list does not carry and the profile does not declare as an alias, with the file and key that declare it, and each id added or removed since the previous snapshot. A harness with no source, or one whose source cannot be read, is reported `unavailable` with the reason; the others still report.

Ledger key: `84-1-an-operator-run-refresh-reads-every-harness-s-live-model-list-and-reports-drift`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-285 (FR-232). Lands on AD-4 (the parsing, comparison, diff and report are pure `core/` functions), AD-19 (the source is profile data), AD-20 (the process and HTTP calls are injected ports) and AD-34 (no credential crosses into the snapshot, the report or the journal). Flag-exempt `detector-or-gate`: the command judges declared ids against live lists and changes no behaviour of dispatch.

## Acceptance Criteria

- Given a profile that declares a command source (`cursor-agent models`) When the refresh runs Then each `id - Display Name` line yields one id and the snapshot records the ids under that harness
- Given a profile that declares a paged HTTP source When the refresh runs Then it follows every page (Anthropic `has_more` with `after_id`; Gemini `nextPageToken` with `pageToken`), sends the credential from the environment variable the profile names, and for Gemini keeps only models whose `supportedGenerationMethods` include `generateContent`
- Given a model id that a station's `model_tier_map`, marshal's `model_cost_catalog` or a profile's `model_map` declares, which its harness's live list does not carry and its profile does not declare as an alias When the report renders Then it names the id, the harness, and the file and key that declare it
- Given a catalog provider that no profile names When the report renders Then that provider is reported `unchecked`, never as drift and never as clean
- Given a previous snapshot When `--write` writes a new one Then the report names every id added and every id removed since that snapshot
- Given a profile with no source, a missing binary, an unset credential variable, a non-2xx response or a timeout When the refresh runs Then that harness reports `unavailable` with the reason and every other harness still reports
- Given any run When the snapshot, the report and the journal are written Then no credential value appears in any of them
- Given drift When the command exits Then the exit code is the one for a rendered report (drift never changes it)
- Given dispatch, drain, spin or policy load When they run Then none of them reads a live model list
- Given the alias rule removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Declare each source in the harness profile (a `model_list` table in the packaged profiles, overridable by a project-local profile overlay, for example to point an HTTP source at an internal mirror). Run commands and HTTP requests through injected ports with fakes in the tests. Keep the parsing, the comparison, the snapshot diff and the report rendering in `core/` with no I/O.

**Never:** Never branch on a harness name. Never import an LLM client or the Copilot SDK, and never make a model call. Never write prices or edit `model_cost_catalog` (operator ruling 2026-10-02: the catalog keeps only priced models; the snapshot records every live id). Never call a live endpoint from the test suite. Never read a live list from dispatch, drain, spin or policy load. Never package or install the Gemini or Copilot CLIs (operator ruling 2026-10-02).

</intent-contract>

## Design notes (non-binding)

- **Grammar:** a new `models` action on `marshal adapters`, beside `probe`, `smoke` and `matrix`. It prints the report by default; `--write` also writes the snapshot.
- **Snapshot:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/model-lists/model-list-<YYYY-MM-DD>.json`, one file per day for every harness (a same-day re-run replaces that day's file). The diff baseline is the newest earlier file.
- **Seed sources, as of 2026-10-02:**
  - claude: HTTP `https://api.anthropic.com/v1/models`, header `x-api-key` from `ANTHROPIC_API_KEY` and `anthropic-version: 2023-06-01`, paged by `limit` and `after_id`. Declared aliases: the CLI's own (`sonnet`, `opus`, `haiku` and the others its model-config page documents).
  - cursor: command `cursor-agent models`. The CLI also accepts ids its list does not show (`grok-4.6` and `sonnet` both ran on 2026-10-02), so an id absent from the list is reported as not listed, never as invalid.
  - gemini: HTTP `https://generativelanguage.googleapis.com/v1beta/models`, header `x-goog-api-key` from `GEMINI_API_KEY`, paged by `pageSize` and `pageToken`.
  - copilot: no source (CLI 1.0.80 documents none), so `unavailable`.
- **Catalog providers to harnesses:** a declared key on the profile names the catalog provider it checks (claude: `anthropic`, cursor: `cursor`, gemini: `google`). A provider no profile names (`openai` today) is `unchecked`.
- **HTTP precedent:** `adapters/oidc_pkce.py` is the package's one direct HTTP client; reuse its shape behind a port.

## Binding

Parent: `spec-pyforge-marshal` CAP-285 (FR-232).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 (night, later) entry.
Ledger key: `84-1-an-operator-run-refresh-reads-every-harness-s-live-model-list-and-reports-drift`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 at the operator's request: refresh the model lists for Claude, Cursor, Gemini and Copilot from their live sources.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (operator, after landing):**
- Run the new command live with `--write` once, read the report, and commit the first snapshot.

## Review Triage Log

- No review has run yet.
