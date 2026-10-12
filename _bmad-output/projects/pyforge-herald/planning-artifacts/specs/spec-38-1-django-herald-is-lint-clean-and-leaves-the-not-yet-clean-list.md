---
title: '38.1: django-herald is lint-clean and leaves the not-yet-clean list'
type: 'fix'
created: '2026-10-11'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-93-1-the-lint-gate-covers-the-nine-django-portal-packages-and-its-not-yet-clean-list-only-shrinks.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-37-1-the-herald-portal-loads-without-herald-and-says-why.md
  - scripts/lint_types.py
  - src/shared/packages/django-herald/pyproject.toml
  - src/shared/packages/django-herald/src/django_herald_portal/deck_twin_routes.py
  - src/shared/packages/django-herald/src/django_herald_portal/deck_export_routes.py
  - src/shared/packages/django-herald/src/django_herald_portal/deck_export_sync.py
  - src/shared/packages/pyforge-herald/tests/meta/test_portal_import_boundary.py
  - src/shared/packages/pyforge-herald/tests/meta/test_portal_herald_guard.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the django-herald portal package has never been linted. No gate covered the `django-*` packages until
steward Story 93.1, which this story waits on. 93.1 gives django-herald the nine portal packages' `[tool.ruff]` table and
lists it in `NOT_YET_CLEAN` (in `scripts/lint_types.py`) for both ruff verbs, so its findings are reported but do not
fail the gate. This story clears them and takes the entry off the list, so any new finding in herald's portal fails
`lint-types` like one in any `pyforge-*` package.

**Inventory** (measured 2026-10-11 on `2b5e0d649b` with the guild ruff 0.16.9, from
`src/shared/packages/django-herald`, `--no-cache`; paths relative to `src/django_herald_portal/`):

*(a) The gate's inventory: the table steward 93.1 lands* (`target-version = "py312"`, line length 120, `select = ["E",
"F", "W", "I"]`, `ignore = ["E501"]`, migrations excluded; measured with `--config` overrides before that table
existed):

| # | file:line | rule | what changes |
|---|---|---|---|
| 1 | `deck_export_routes.py:3` | I001 | `pyforge.herald.deck_exports` (third-party here) moves above the first-party block and its two imports join |
| 2 | `deck_export_sync.py:3` | I001 | `from datetime import UTC` and `from datetime import datetime` join |
| 3 | `deck_twin_routes.py:3` | I001 | the `pyforge.herald.deck_twins` imports move above `django_herald_portal.deck_export_routes` |
| 4 | `deck_twin_routes.py:8` | F401 | `StoreError` is imported and used nowhere (no other module imports it from here) |
| 5 | `management/commands/refresh_deck_exports.py:3` | I001 | the two `portal_runner` imports join, and a blank line follows the import block |
| 6 | `deck_viewer.py` (from :40) | format | two wrapped query chains fit in 120 columns |
| 7 | `herald_guard.py` (from :45) | format | one wrapped f-string fits in 120 columns |
| 8 | `management/commands/refresh_deck_exports.py` (from :16) | format | one generator fits in 120 columns; the blank line of row 5 |

All five check findings are ruff's safe fixes, and the three format changes are layout only.

*(b) The operator's 17: ruff's own default rule set*, which applies today because the package has no `[tool.ruff]`
table. Five are rows 1-5 above. The other twelve, and what this story does with each:

| file:line | rule | disposition |
|---|---|---|
| `apps.py:14`, `apps.py:15` | RUF100 (unused `noqa: S105`) | remove the directive: the package's table does not enable S105 |
| `apps.py:24`, `apps.py:29`, `deck_export_routes.py:93`, `deck_twin_routes.py:13`, `deck_twin_routes.py:27`, `mcp_asgi.py:29` | RUF100 (unused `noqa: PLC0415`) | remove the directive: the table does not enable PLC0415; the function-local imports stay where they are |
| `deck_export_sync.py:34` | DTZ007 | make the parse zone-explicit without changing the date read: `datetime.strptime(..., "%Y-%m-%d").replace(tzinfo=UTC).date()` (verified: ruff accepts that chain) |
| `deck_export_sync.py:18` | TRY004 | keep `ValueError`, and record why in the Auto Run Result: `parse_export_records` rejects a malformed payload, `json.loads` raises `ValueError` (`JSONDecodeError`) for the other malformed case, so one type covers every malformed payload; the only caller (`sync_slug_exports`, from `refresh_deck_exports.handle`) catches neither, and no test pins it |
| `migrations/0001_initial.py:10`, `:13` | RUF012 | leave: a generated migration, which the gate's table excludes and no story hand-edits |

**Approach:** after steward 93.1 has landed, fix the eight gate items in place (`ruff check --fix src` and
`ruff format src` from the package directory produce exactly rows 1-8; read the diff before keeping it), make the
twelve dispositions above, and delete the `django-herald` entry from `NOT_YET_CLEAN`. Nothing else moves.

Ledger key: `38-1-django-herald-is-lint-clean-and-leaves-the-not-yet-clean-list`.
Type / Effort / Deps: fix / S / cross-station gate on steward 93.1 (a ledger `blocked` row).

### Living CAP citations

- **`spec-pyforge-herald` CAP-55** (a deck is readable in the browser from its HTML twin): its intent names the
  django-herald portal, and Stories 30.2 and 37.1 edited it under this CAP. **CAP-54** (each current export is also
  kept in object storage) covers the deck-export projection files Story 29.2 added: `deck_export_routes.py`,
  `deck_export_sync.py` and `management/commands/refresh_deck_exports.py`. A lint fix changes neither CAP's behaviour,
  so no CAP is minted and no `SPEC.md` text changes.
- **The gate:** `spec-pyforge-steward:CAP-153`, through steward Story 93.1, which ships the table and the list.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Origin.** `docs/dreams/pyforge-herald.md` Realization log, 2026-10-11 (django-herald lint clean). The operator's
  request, verbatim: "Do this task here: Lint django-herald package and add it to a gate". Asked how wide to go, the
  operator chose, verbatim label "Gate all, clean herald (Recommended)": "Two stories. Steward's story extends
  lint-types to every django-* package and adds an explicit 'not yet clean' list that can only shrink. Herald's story
  clears django-herald's 17 findings and takes it off that list. The other stations follow later as their own fix
  stories."

## Acceptance Criteria

- **AC1 — Clean under the gate's table.** From `src/shared/packages/django-herald`, `ruff check src` and
  `ruff format --check src` both exit 0 under the package's own `[tool.ruff]` table, as steward 93.1 lands it. Rows 1-8
  of inventory (a) are fixed. If the measurement on the story's base differs from the inventory, the Auto Run Result
  lists the difference, and every finding on the base is fixed either way.
- **AC2 — The operator's 17 are each accounted for.** The eight RUF100 directives are gone. DTZ007 is cleared by the
  zone-explicit parse, and the date it returns is unchanged. TRY004 stays as `ValueError`, and the Auto Run Result
  records the reason. The two RUF012 in `migrations/0001_initial.py` are left. Run with ruff's defaults at the
  package's own line length (`ruff check --isolated --line-length 120 src` from the package directory), django-herald
  reports exactly three findings: the TRY004 and the two RUF012. (At ruff's default 88 columns, isort would also re-wrap
  one import line the gate's 120 columns keep; measured on a scratch copy with the fixes applied.)
- **AC3 — No blanket ignore.** The package's `[tool.ruff]` table is byte-identical to the one steward 93.1 landed
  (steward's meta test pins it). No file-level `# ruff: noqa`, no new `# noqa` and no per-file ignore is added. None is
  needed, because every gate finding is a safe fix. If one ever is, it names the file, the code and the reason, and the
  story goes back for review.
- **AC4 — Off the list.** The `django-herald` entry is deleted from `NOT_YET_CLEAN` in `scripts/lint_types.py`, and no
  other line of that file changes. Steward 93.1's ceiling test still passes.
- **AC5 — The gate is green.** `pixi run --frozen -e pyforge-guild lint-types` exits 0, with django-herald reported
  `ok` on the `ruff` and `ruff-format` verbs.
- **AC6 — Herald-present behaviour is unchanged.** `pixi run --frozen -e pyforge-herald pyforge-herald-test` passes,
  including Story 37.1's `tests/meta/test_portal_import_boundary.py` and `tests/meta/test_portal_herald_guard.py`.
  Story 30.2's tests pass unedited. `pixi run -e pyforge-guild platform-ci-local -- --test` passes, including
  `src/platform/tests/test_herald_portal_without_herald.py`.
- **AC7 — The diff is lint-only.** Under `src/shared/packages/django-herald/`, every changed line is one of: an import
  moved, joined or removed (`StoreError` only); a removed `noqa` comment; a formatting change; or the DTZ007
  `.replace(tzinfo=UTC)`. No other statement, string, log message or behaviour changes. `pyproject.toml` and
  `migrations/` do not change.
- **AC8 — The surface is reconciled.** `spec-pyforge-unifying-strategy`, which governs the portal's files, and
  `spec-pyforge-steward`, which governs `scripts/lint_types.py`, each get a memlog entry naming their paths and this
  story, and one scoped stamp each. Any other Spec the detector names gets the same. `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Edit only the eight files listed in the epic's Surface, under `src/shared/packages/django-herald/src/django_herald_portal/`,
  and the one entry in `scripts/lint_types.py`, plus the memlogs and the baseline stamp.
- Keep `deck_twin_routes.py`'s and `deck_export_routes.py`'s module-level `pyforge.herald` imports at module level.
  Only `pyforge.herald.station_api` loads these two modules, with herald installed, and Story 37.1's import-boundary
  meta-test allows it there. Reordering them is fine.
- Keep every function-local import function-local. Removing a stale `noqa` never moves the import.

**Ask First:**
- Any change to the package's `[tool.ruff]` table, or any `noqa` or per-file ignore.

**Never:**
- Never edit another `django-*` package, another `NOT_YET_CLEAN` entry, or any other part of `lint_types.py`.
- Never hand-edit `migrations/0001_initial.py`.
- Never change behaviour: TRY004's exception type, the guard's decision, a route, a log line or a template.
- `deck_twin_routes.py` and `deck_export_routes.py`, which Story 37.1 kept unedited, may change now, and for lint only.

**Residual risk:**
- Once off the list, django-herald is gated like a `pyforge-*` package. Marshal's pre-verify ruff pass (Stories 83.9
  and 83.15) covers only `pyforge-*` files, so a later story that edits the portal must run `ruff format` there itself,
  or `lint-types` in `pr-preflight` and CI fails it.

## I/O & Edge-Case Matrix

| Situation | Before (93.1 landed, herald listed) | After |
|---|---|---|
| `lint-types` on the story's tree | herald reported, not yet clean (listed) | herald `ok` on both verbs |
| a new lint finding in django-herald | reported, does not fail | fails `lint-types` |
| django-herald clean but still listed | fails `lint-types` (93.1's ratchet) | not possible: the entry is gone |
| herald installed, any portal page | unchanged | unchanged |
| herald absent (37.1's guard) | 404 with the reason | unchanged |
| `herald deck exports` payload that is not a JSON list | `ValueError` | `ValueError` (TRY004 kept) |
| export date `"2026-10-11"` | `date(2026, 10, 11)` | `date(2026, 10, 11)` |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-11 (django-herald lint clean) entry.
- Spec: `spec-pyforge-herald` CAP-55, with CAP-54. No CAP is minted. `spec-pyforge-herald/.memlog.md` records the
  ruling verbatim, the inventory and dispositions, and the mint.
- Epic: Epic 38 (minted with this story). Epics 29, 30 and 37 are `done`.
- Ledger key: `38-1-django-herald-is-lint-clean-and-leaves-the-not-yet-clean-list`; `epic-38` and
  `epic-38-retrospective` minted with it.
- Ledger status at mint: `blocked`. It is a cross-station gate on steward Story 93.1
  (`93-1-the-lint-gate-covers-the-nine-django-portal-packages-and-its-not-yet-clean-list-only-shrinks`); marshal's
  `Deps:` parser is station-local, so the gate is this ledger row. The operator flips it once 93.1 is `done` on `main`.
  This spec reads `ready-for-dev`: the row, not the spec, holds the gate.
- Dispatch note: `marshal-policy.toml` `[epic_surfaces]."38"` (added with this mint) admits:
  - the herald package and `src/shared/packages/django-herald/**`;
  - `scripts/lint_types.py`;
  - herald's story specs and Tier-3 artifacts;
  - the spec-surface baseline and every Spec memlog.

  Nothing else is admitted.
- Minted 2026-10-11 in one chain commit (CHAIN-STANDARD §5 filename).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` -- expected: pass, including Story 37.1's two portal meta-tests (`verify_commands`).

**Run before the push (not dispatch gates):**
- From `src/shared/packages/django-herald`: `ruff check src` and `ruff format --check src` with the guild env's ruff -- expected: exit 0 each (AC1). Read each exit code directly, never through a pipe.
- From the same directory: `ruff check --isolated --line-length 120 src` -- expected: exactly the TRY004 and the two RUF012 (AC2).
- `pixi run --frozen -e pyforge-guild lint-types` -- expected: exit 0, django-herald `ok` on both ruff verbs (AC5).
- `pixi run -e pyforge-guild platform-ci-local -- --test` -- expected: exit 0 (AC6).
- `git diff origin/main...HEAD --stat` -- expected: only AC7's paths under `src/shared/packages/django-herald/`, `scripts/lint_types.py`, the memlogs and `scripts/.spec-surface-baseline.json`.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` -- expected: exit 0 after the memlogs and the scoped stamps (AC8).
- `pixi run --frozen -e pyforge-guild detectors-ci` -- expected: no new finding against `main`.

## Spec Change Log

- 2026-10-11: minted from the operator's ruling "Gate all, clean herald (Recommended)". `type: fix`, no flag, no CAP;
  bound to `spec-pyforge-herald` CAP-55 with CAP-54. Its ledger key is minted `blocked` on steward 93.1.
