---
title: '65.1: Reusable, pluggable, feature-flagged estate sprint ledger query module & BMAD skill'
type: 'feature'
created: '2026-09-19'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md']
deferred:
  - summary: "The HTMX backlog view and the `WorkPassport` admin ship as a library (AD-1 — the pipeline, not the routing): no URLconf under `src/` registers `sprint_backlog_view` and no host `INSTALLED_APPS` lists the dashboard app, so the view and the admin are reachable only from a host project that wires them. First consumer story wires one host or records why none should."
    evidence: "`views.py` ships a view factory only; `routing.py` / `asgi.py` carry websocket patterns; `grep -rn build_navigation_view src/` finds no URLconf reference (implementer report, PR #1507 review 2026-09-19)."
    location: src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/views_htmx.py
    severity: low
  - summary: "Every HTMX render re-parses all eight stations' `epics.md` + ledgers (no caching, no mtime check); fine for a handful of operators, a hot loop for a dashboard polling on a timer. A `pre_query` hook or a source-level mtime cache is the shape when it matters."
    evidence: "`sprint_backlog_view` builds a fresh `SprintLedgerQueryEngine()` per request and `TrackedLedgerSource.load_station` reads the files every call."
    location: src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/views_htmx.py
    severity: low
  - summary: "`LedgerQueryHook`'s three default no-op methods trip ruff `B024`/`B027` (abstract base with no abstract methods); steward has no ruff lane or config, so nothing reds, but the first station-wide lint pass will."
    evidence: "`ruff check --select B024,B027 src/shared/packages/pyforge-steward/src/pyforge/steward/sprint_ledger_query.py` reports both; `F`/`E9` are clean."
    location: src/shared/packages/pyforge-steward/src/pyforge/steward/sprint_ledger_query.py
    severity: low
declared_low_risk: false
baseline_revision: '7d0fa6118c326a8b91482e1586c33c9ba717f996'
final_revision: 'pending — the merge commit of PR #1507 (`Merge pyforge-steward/65-1 into main`)'
---

<intent-contract>

## Intent

**Problem:** eight stations each keep a tracked `sprint-status-ledger.yaml` and an `epics.md`;
operators, agent tools, execution runners and dashboards read them by ad-hoc scans, and every
consumer that wants a different shape (Herald facts, an Atlas dataset, Jira, GitHub Projects,
Marshal's runnable set) re-implements the parse.

**Approach:** one query engine (`pyforge.steward.sprint_ledger_query.SprintLedgerQueryEngine`) over
the TRACKED twins only — pluggable in what it reads (`LedgerSourcePlugin`) and how it renders
(`QueryFormatterPlugin`), hookable (`pre_query` / `post_query` / `on_export`), flag-gated in what it
touches (`eval_flag`: CLI `--flag` → `FLAGS_<NAME>` → `.steward/flags.json` → default; no SDK) — with a
durable per-story identity (`WorkPassport`, minted UUID; tracker keys are aliases) and three front
doors (`steward ledger-query`, the pixi tasks, the `bmad-sprint-ledger-query` skill). Counts agree
with `fleet_scan.parse_sprint_status`, which stays the reader of record.

## Boundaries & Constraints

**Always:**
- Read the TRACKED `planning-artifacts/` twin — never the gitignored Tier-3 feed, never `docs/dashboard/data.js`.
- stdout carries the payload only; every diagnostic (sync outcome, `--output` confirmation, warnings) goes to stderr and `DutyResult.details`.
- A flag left off refuses the gated export (`ok=False`, an actionable message) — never a silent run, never a silent no-op.
- `get_runnable_backlog()` reads the same Deps grammar marshal's `spec_deps` does (`S-x.y`, bare `x.y`, `station S-x.y (note)`, sentinels `— – - none nothing n/a`, `x.*` skipped), keyed `(station, canonical key)`.
- Steward exports; Atlas renders (canopy:AD-13 / canopy:AD-23) — steward never imports vizro.
- The minted UUID is identity; Jira / GitHub ids are aliases and survive a sync that carries none.

**Never:**
- Write into another station's tree by default — only an explicit `--output PATH` writes anywhere.
- Import marshal, django or channels at module level from `sprint_ledger_query.py` (the one sanctioned lazy reach is `importlib.import_module("pyforge.steward.dashboard.passport_sync")`).
- Interpolate a ledger-derived string into HTML unescaped; accept a `?station=` outside `[A-Za-z0-9_-]+`.
- Register a pixi task in an environment where it can only refuse (the sync task lives in `pyforge-steward`, the env carrying django).

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| `--unimplemented --format summary` over the live tree | per-station done / backlog / blocked equal `fleet-picture`'s (agreement test against `scripts/fleet_scan.py::parse_sprint_status`) |
| `--format json` | validates against `steward/data/sprint-ledger-query.schema.json` (`$id` = `urn:local-recipes:pyforge-steward:sprint-ledger-query-schema`); carries `warnings` |
| `--format static-dossier` with `enable_dossier_export` off | `ok=False`, `flag enable_dossier_export is off (set FLAGS_ENABLE_DOSSIER_EXPORT=true, flags.json, or --flag …)`, 0 stdout bytes |
| `--output PATH` | file written, stdout empty, one stderr confirmation; unwritable path → `ok=False` |
| `--sync-postgres` with the flag on, no `DJANGO_SETTINGS_MODULE` | `refused` on stderr naming the variable, exit 1 |
| `--sync-postgres` in an env without the `[dashboard]` extra | `refused: pyforge-steward[dashboard] extra not installed`, exit 1 |
| `--station nope` / `--status bogus` / `--format dossier` | refused naming the known set (argparse exit 2 for the format) |
| `--epic 65` | only Epic 65's stories; `--epic 99` → 0 matches, `ok=True` |
| ledger missing / unparsable / `development_status` null | empty map, station still listed; null story value → `backlog` + one warning per ledger |
| `epics.md` unreadable | station skipped with a warning |
| a repeated `### Epic N` heading (the "Epic List" preamble) | one epic, never a duplicate; epic status = ledger `epic-N:` key, `unknown` when absent |
| story block followed by `## Deferred Work` with its own `**Status:** done` | the trailing section never folds into the last story |
| `?station=../../etc` on the HTMX view | `400`, no path created |
| a story titled `<script>` | escaped in the dossier and the HTMX row |

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/sprint_ledger_query.py` — engine, registries, plugins, hooks, `eval_flag`, formatters (10), `parse_epics_markdown`, `load_status_map`, `get_runnable_backlog`, `sync_to_postgres`, `LedgerQueryDuty`.
- `.../steward/data/sprint-ledger-query.schema.json` — the JSON payload's 2020-12 schema (force-added: `.gitignore:740`'s unanchored `data/` rule swallows it otherwise, as it did `track.schema.json`).
- `.../steward/dashboard/models.py` (`WorkPassport`), `migrations/0002_workpassport.py`, `admin.py` (`WorkPassportAdmin`; `AuditEntryAdmin` read-only), `views_htmx.py` (`sprint_backlog_view`), `passport_sync.py` (lazy django; `refused` / `fallback_payload` / `error` / `success`), `__init__.py` (split docstring).
- `.../steward/cli.py` — `ledger-query` duty (`_add_ledger_query_subparsers`: `--unimplemented --unlinked --station --status --epic --search --format --output --sync-postgres --flag`); `main()` prints nothing for an empty summary.
- `tests/unit/test_sprint_ledger_query.py` (54), `tests/unit/test_dashboard_admin_and_htmx.py`, `tests/meta/test_invariants.py` (lazy-reach pin), `tests/unit/test_cli.py` / `test_restore_duty.py` (duty count 19).
- `pixi.toml` — `[feature.guild-tasks.tasks.sprint-ledger-query]`, `[feature.pyforge-steward.tasks.sprint-ledger-postgres-sync]`.
- `.claude/skills/bmad-sprint-ledger-query/SKILL.md` — wraps the CLI; every documented invocation runs verbatim.
- `AGENTS.md` — pre-PR checklist items 2, 5, 6, 7 rewritten at review (pr-preflight; memlog-then-scoped-stamp; one-chain-per-station Dream-append rule; non-recipe PR mechanics).

## Binding

Parent Spec capability: `spec-pyforge-steward CAP-146`, `CAP-147`, `CAP-148`, `CAP-149` (folded from `spec-sprint-ledger-query-module` CAP-1/2/4/5 on 2026-09-19); partially realizes `CAP-140` (the passport; Story 61.2 remains the story of record).
Surface: as in the Code Map.
Ledger key: `65-1-reusable-pluggable-feature-flagged-estate-sprint-ledger-query-module-and-bmad-skill`.
Ledger status: `done` (set at the review of PR #1507; the `63-5` key the parallel session used never reached `main`).
Minted 2026-09-19 at the review of PR #1507: the session that opened the PR had no tracked story spec, a Story citing `CAP-1..4` nothing defined, a Surface naming paths that do not exist, and a standalone Dream + Spec pair under `fold-exemption: cross-station-seam`. This spec is the record the story should have carried from the start.

## Epic excerpt

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** spec-pyforge-steward CAP-146, CAP-147, CAP-148, CAP-149 (folded from spec-sprint-ledger-query-module 2026-09-19) • partially realizes CAP-140 (Story 61.2 remains the story of record)
**Given** estate sprint ledgers are scattered across stations and lack pluggable querying, Work Passport UUID identity, and multi-system output formatters
**When** this story lands
**Then** `SprintLedgerQueryEngine` provides a pluggable engine with feature-flag evaluation (OpenFeature-shaped `eval_flag`; no SDK), Work Passports PostgreSQL sync with minted UUIDs, multi-format output, HTMX dashboard view, Django Admin registration, CLI verb `pyforge steward ledger-query`, the two pixi tasks and the `bmad-sprint-ledger-query` skill
**Status:** done

</intent-contract>

## Spec Change Log

- 2026-09-19 — minted at review (see Binding). The parallel session's `**Then**` claimed "feature flag evaluation via OpenFeature"; the code imports no openfeature package — corrected to the file / env / CLI resolution that exists. Surface paths corrected (`steward/models.py` → `steward/dashboard/models.py` etc.).
- 2026-09-19 — `--epic` added to the CLI (CAP-146 names an epic filter; the engine had it, the duty did not expose it). `sprint-ledger-postgres-sync` moved from `guild-tasks` to the `pyforge-steward` feature (no `guild-tasks` env has django).

## Review Triage Log

### 2026-09-19 — Review pass (three layers over PR #1507 as opened: Blind Hunter, Edge Case Hunter, Intent Alignment; then a consolidated remediation)

- intent_gap: 3
- bad_spec: 4
- patch: 16 (high 4, medium 7, low 5)
- defer: 3
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` `get_runnable_backlog()` compared raw `deps` strings (`S-1.1`, `steward S-1.1 (note)`) against story ids, so nothing with a marshal-shaped Deps field was ever runnable — restated `spec_deps`'s `DEP_RE` / `NO_DEP_RE` verbatim (no marshal import), canonical keys, `(station, key)` done-set.
  - `[high]` `[patch]` `--sync-postgres` reported `ok` and printed its outcome on **stdout** while `sync_work_passports_db` could only ever return the fallback dict (django unconfigured) — outcome to stderr + `details["sync"]`; `ok=False` unless `success`; `refused` when the extra or `DJANGO_SETTINGS_MODULE` is missing; the thin `importlib` reach replaces a duplicated fallback.
  - `[high]` `[patch]` Unescaped ledger strings interpolated into the HTMX rows and the static dossier; `?station=` joined into a filesystem path — `html.escape` on every field, `fullmatch [A-Za-z0-9_-]+` else `400`.
  - `[high]` `[patch]` Every epic reported `in-progress` (status hard-coded) — status from the ledger's `epic-N:` key, `unknown` when absent; the "Epic List" preamble's repeated headings no longer duplicate epics.
  - `[medium]` `[patch]` `eval_flag` existed but nothing called it: the five "flag-gated" exporters ran unconditionally and `sync_to_postgres` was gated on nothing — `FORMATTER_FLAGS` map, duty refuses with `flag_off_message`, `--flag NAME=VALUE` overrides, hooks receive the mutable filters dict, a raising hook is reported and the rest still run.
  - `[medium]` `[patch]` Default export targets wrote into Herald's `presentations/`, Atlas's `data/` and `docs/dashboard/` — removed; only `--output PATH` writes.
  - `[medium]` `[patch]` Stock `ModelAdmin` on the append-only `AuditEntry` (CAP-4 audit trail) allowed add / change / delete from the admin — all three permissions `False`, every field read-only.
  - `[medium]` `[patch]` `herald-facts` emitted a shape Herald's `deck-facts` does not read; `atlas-dataset` claimed an Atlas catalog name Atlas never declared — Herald's `deck/persona/derived_at/tree/facts[]` shape; the atlas payload carries `producer`/`shape`/`note` and no catalog name.
  - `[medium]` `[patch]` The JSON schema the docstring cited did not exist — `steward/data/sprint-ledger-query.schema.json` ships in the wheel and the payload is validated in test.
  - `[medium]` `[patch]` `StationProgress` counted only four statuses, so `in-review` / `review` / `ready-for-dev` / `ready` / `optional` stories vanished from the totals — every fleet status buckets, `other` catches the rest, sums equal `total_stories`.
  - `[medium]` `[patch]` `sprint-ledger-postgres-sync` was registered in `guild-tasks`, where no env has django — moved to the `pyforge-steward` feature.
  - `[low]` `[patch]` The module docstring claimed an OpenFeature SDK; `cli.py`'s help listed a `dossier` format that did not exist and omitted `summary`; `--format` choices were a copied list — docstring corrected; choices from `default_formatter_names()`; duplicate registration raises.
  - `[low]` `[patch]` `SprintLedgerQueryEngine()` defaulted to `Path.cwd()` — a `repo_root()` walk-up (the per-duty precedent in `budget.py` / `provision.py`); the HTMX view takes `settings.PYFORGE_REPO_ROOT` → `$PYFORGE_REPO_ROOT` → the walk-up.
  - `[low]` `[patch]` Null / non-dict ledger values, unreadable `epics.md`, a story block swallowing the trailing `## Deferred Work` section, `JIRA-`/`GH-` aliases matching inside words — all handled, each with a fixture test.
  - `[low]` `[patch]` `--epic` (CAP-146) missing from the CLI — added with a test.
  - `[low]` `[patch]` Order-dependent dashboard tests and a tautological `assert "Found" in html` — self-sufficient fixtures under `tmp_path`, exact `Found <strong>N</strong>` counts.
  - `[intent_gap]` `[patch]` No tracked story spec, a Story citing `CAP-1..4` nothing defined, Surface paths that do not exist, no station memlog entry for changed `src/` — this spec; Story 65.1 with the real CAP ids and paths; memlog entries on `spec-pyforge-steward`, `spec-pyforge-core`, `spec-pyforge-scribe`, `spec-work-passports-dated-extracts`.
  - `[bad_spec]` `[patch]` `AGENTS.md` item 6 told agents to add `fold-exemption: cross-station-seam` for "new cross-station capabilities" — the exact bypass this PR took; rewritten as the one-chain-per-station Dream-append rule with the closed exemption list. Items 2 / 5 / 7 rewritten (pr-preflight; memlog-then-scoped-stamp; `maintenance` label + `environment.yaml` + all-8-stations).
  - `[bad_spec]` `[patch]` The PR's two `fix(governance)` commits re-stamped **marshal** specs (`spec-pyforge-marshal`, `spec-marshal-token-economy`, …) the PR never touched — laundering drift; the branch was re-merged with main's baseline and only the steward specs this PR touches are re-stamped, each after its memlog entry.
  - `[defer]` ×3 — see frontmatter `deferred:` (unrouted view / admin host wiring; per-request re-parse; ruff B024/B027 on the hook base).

## Design Notes

- Steward restates marshal's Deps grammar rather than importing it — the same restatement `spec_deps.py` makes of doctor's — because stations never import each other; the test pins the two regexes equal by value.
- The `[dashboard]` extra owns the ORM path and every fallback; the base package's only reach into it is one `importlib.import_module`, pinned by `tests/meta/test_invariants.py`.
- Q1 of the derivation record ("do exporters' default target paths need the target station's Spec to declare them?", now on the station memlog) resolved itself: there are no default target paths any more, so no other station's Spec has anything to declare.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command).

**Manual checks (real tree, no mocks):**
- `pixi run -e pyforge-guild sprint-ledger-query -- --unimplemented --format summary` — per-station done / backlog / blocked match `pixi run -e pyforge-guild fleet-picture`.
- `pixi run -e pyforge-guild sprint-ledger-query -- --format static-dossier` with no flag → exit 1, empty stdout, the flag-off message on stderr.
- `env -u DJANGO_SETTINGS_MODULE pixi run -e pyforge-steward sprint-ledger-postgres-sync -- --flag enable_postgres_sync=true` → exit 1, empty stdout, `refused … DJANGO_SETTINGS_MODULE` on stderr.

## Auto Run Result

- **Summary:** PR #1507 (a parallel session's `feat(steward): reusable estate sprint ledger query
  module & work passports integration`, 9 commits on `7d0fa6118c`) reviewed and remediated in a
  dedicated worktree, then re-merged with `main` so the spec-surface baseline is main's. Twenty-three
  findings (4 high) across the engine, the sync path, the HTMX view, the admin and the chain — all
  patched except three low deferrals. The chain was rebuilt the way a new Dream-to-code effort
  would have run: a dated seed on `docs/dreams/pyforge-steward.md`, `bmad-spec` deriving a proper
  kernel from the sketch (the derivation record is now a note on the station memlog; the
  standalone pair is removed — `chain-sprawl` reads no status), the fold into `spec-pyforge-steward`
  CAP-146..149 (+ a CAP-140 partial note), Epic 65 / Story 65.1 with real CAP ids and Surface,
  ledger rows, this tracked spec, capability-ledger rows, and memlog entries on every co-governing
  Spec. `AGENTS.md`'s checklist no longer teaches the bypass.
- **Verification (exit codes read directly, 2026-09-19):**
  - `CI=1 pixi run --frozen -e pyforge-steward pyforge-steward-test` → `1351 passed, 4 skipped`, exit 0.
  - `CI=1 COVERAGE_GATES_STATIONS=steward … scripts/coverage_gates_ci.py --base origin/main --head HEAD --suites unit` → `coverage gate OK for pyforge-steward unit: 22 module(s) ≥ 80%` (`sprint_ledger_query.py` 95 %, `cli.py` 99 %, `passport_sync.py` 88 %), exit 0.
  - `pixi run --frozen -e pyforge-core pyforge-core-test` → `1883 passed`, exit 0.
  - `pixi project export conda-environment -e build | diff - environment.yaml` → empty.
  - `sprint-ledger-query --unimplemented --format summary` → 1048 stories / 8 stations; per-station done / backlog / blocked equal `fleet-picture`'s. `--format json` → valid, 61 matching stories, validates against the shipped schema.
  - `sprint-ledger-postgres-sync` in `pyforge-steward` without `DJANGO_SETTINGS_MODULE` → exit 1, 0 stdout bytes, `refused` on stderr.
- **Files changed:** see Code Map, plus the chain: `docs/dreams/pyforge-steward.md` (seed entry),
  `docs/dreams/sprint-ledger-query-module.md` (removed) + its `docs/dreams/README.md` row,
  `specs/spec-sprint-ledger-query-module/` (removed; record folded into the station memlog),
  `specs/spec-pyforge-steward/{SPEC.md,.memlog.md}`, `epics.md` (Epic 65), `sprint-status-ledger.yaml`,
  `specs/spec-61-2-work-passport-and-core-schema.md` (note), `docs/foundry/capability-ledger.yaml`,
  co-governor memlogs (`pyforge-marshal/spec-pyforge-core`, `pyforge-scribe/spec-pyforge-scribe`,
  `pyforge-steward/spec-work-passports-dated-extracts`), `scripts/.spec-surface-baseline.json` (scoped).
