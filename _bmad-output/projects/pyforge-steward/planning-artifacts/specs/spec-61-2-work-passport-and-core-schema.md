---
title: '61.2: Work passport and core schema'
type: 'feature'
created: '2026-09-16'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      This PR touches only non-recipe paths and needs the `maintenance` label at PR open time.
    evidence: |-
      Diff touches only `_bmad-output/**` and `src/shared/packages/**`, no `recipes/**`.
      CLAUDE.md / AGENTS.md require `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`
      for any such PR. No PR exists yet from this single-story dev dispatch.
    location: >-
      PR mechanics (not a file)
    severity: low
declared_low_risk: false
baseline_revision: 'b338a1c7b968255480f18d70cd5e45e6f9b1f681'
---

<intent-contract>

## Intent

**Problem:** Jira keys and GitHub numbers can collide across rooms.

**Approach:** Identity is a UUID we mint; keys and numbers are nicknames. vendor_id is on inbound rows; v1 operates one vendor.

## Boundaries & Constraints

**Always:**
- Identity is a minted UUID.
- vendor_id is on inbound rows; v1 is one vendor.

**Never:**
- Do not use Jira keys or GitHub numbers as primary identity.
- Do not treat Epic 8 as this product.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| same Jira key two rooms | two inbound rows | two UUIDs; keys are nicknames | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-work-passports-dated-extracts CAP-2`.
Surface: the existing Postgres join store..
Ledger key: `61-2-work-passport-and-core-schema`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-61-2-work-passport-and-core-schema.md`.

## Code Map

Investigated live (2026-09-19). `dashboard/models.py` (143 lines) already has `WorkPassport`
(Story 65.1: `passport_id` UUID-string PK, `story_id`, `station`, `epic_id`, `title`, `status`,
`jira_key`, `github_item_id`, `effort`, timestamps — no uniqueness beyond the PK) and, from Story
61.1, `CorridorDirection`/`CorridorLoad` (a batch-level idempotency record; it never parses a
loaded file's content, only hashes the whole file — no per-row hook exists to extend, and this
story's declared surface is the Postgres join store, not the corridor, so `corridor.py` /
`CorridorLoad` are not touched here). `WorkPassport` is also populated today by a **separate,
existing, deterministic** mint path this story must not disturb: `sprint_ledger_query.py`'s
`parse_epics_markdown` mints `passport_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"pyforge:{station}:{story_id}"))`
for internal BMAD-ledger stories, synced via `dashboard/passport_sync.py::sync_work_passports_db`
(`update_or_create` keyed on `passport_id`). That path has nothing to do with vendors and shares
only the table — this story's new field must be nullable so those rows are unaffected, and its new
mint path must never look up an existing row by key (that would risk conflating an internal
passport with a vendor one).

**Model change (`dashboard/models.py`):** add `vendor_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)` to `WorkPassport`, immediately after `github_item_id`. Null/blank because internal-mint rows carry no vendor. Reword the class docstring: drop "Story 61.2 remains the passport story of record" (now landed) and state instead that `vendor_id` plus the always-fresh vendor mint path (`dashboard/passport_mint.py`) are this story's addition — CAP-140 fully realized. No new uniqueness constraint — the whole point of this story's identity rule is that two rows sharing a `jira_key`/`github_item_id` never merge.

**Migration (NEW):** `dashboard/migrations/0004_workpassport_vendor_id.py`, `dependencies = [("pyforge_steward_dashboard", "0003_corridorload")]`. Generate for real via the disposable-script `makemigrations` dance 61.1 used (`tests/unit/test_dashboard_audit.py:1-58`'s settings-configure block), verified zero-drift against `test_the_shipped_migration_matches_the_model`.

**Base-package module (NEW):** `src/pyforge/steward/passport.py` (django-free, mirrors `corridor.py`'s shape):
- `PassportMintError(ValueError)` — raised for a blank `vendor_id`, or when neither `jira_key` nor `github_item_id` is given (a vendor passport must carry at least one nickname).
- `mint_vendor_passport(*, vendor_id: str, jira_key: str | None = None, github_item_id: str | None = None, title: str = "") -> dict` — validates inputs (raises `PassportMintError`), then reaches the ORM via the same dynamic idiom as `corridor.load_extract` (copy verbatim in shape): `importlib.import_module("pyforge.steward.dashboard.passport_mint")`, `ImportError` → `{"status": "refused", "vendor_id": vendor_id, "message": "pyforge-steward[dashboard] extra not installed"}`; otherwise call `module.record_vendor_passport(vendor_id=vendor_id, jira_key=jira_key, github_item_id=github_item_id, title=title)` and return its dict verbatim.
- `PassportDuty` (the `Duty`-conforming class, `interfaces.py:19-51`). `name = "passport"`. `run(ns)`, mirroring `RestoreDuty`'s bare-refuses shape (`restore.py`) rather than `LoadDuty`'s bare-reports shape — there is no config to report read-only on a bare invocation:
  - `verb = getattr(ns, "passport_verb", None)`. **If `None`**: `DutyResult(ok=False, summary="passport: a verb is required (mint)")`.
  - **If `"mint"`**: read `ns.vendor_id`, `ns.jira_key`, `ns.github_item_id`, `ns.title`; call `mint_vendor_passport(...)` inside `try/except PassportMintError as exc: return DutyResult(ok=False, summary=f"passport mint: {exc}")`. Map the outcome dict through one small `_mint_result(outcome, as_json)` helper used on every branch (learn from 61.1's review finding: unify `--json`/payload shape from the start, never per-branch): `status == "minted"` → `ok=True`, plain summary `f"minted passport_id={outcome['passport_id']} vendor={outcome['vendor_id']}"`; `status in ("refused", "error")` → `ok=False`, plain summary `f"passport mint: {outcome['message']}"`; when `as_json` (`ns.json`), `summary` is `json.dumps(outcome, indent=2, sort_keys=True)` instead, on every branch including the `PassportMintError` one (wrap that dict the same way before returning).
  - Wrap the whole body in one outer `try/except Exception as exc:  # noqa: BLE001 — duty boundary` returning `DutyResult(ok=False, summary=f"passport failed: {exc}")` (mirrors `restore.py`/`corridor.py`'s duty-boundary shape).

**Dashboard module (NEW):** `src/pyforge/steward/dashboard/passport_mint.py`:
- Copy `dashboard/corridor_load.py`'s module shape verbatim (module docstring, lazy `import django` inside the function, `_SETTINGS_UNSET` constant, never a top-level django import).
- `record_vendor_passport(*, vendor_id: str, jira_key: str | None, github_item_id: str | None, title: str) -> dict`:
  1. `try: import django; from django.apps import apps; from django.conf import settings; from django.core.exceptions import ImproperlyConfigured; except ImportError as exc: return _refused(vendor_id, exc)`.
  2. Settings-unset check → `{"status": "refused", "vendor_id": vendor_id, "message": _SETTINGS_UNSET}`.
  3. `try: if not apps.ready: django.setup(); from django.db import DataError, IntegrityError, OperationalError, ProgrammingError; from pyforge.steward.dashboard.models import WorkPassport; except (ImportError, ImproperlyConfigured) as exc: return _refused(vendor_id, exc)`.
  4. **No lookup.** `passport_id = str(uuid.uuid4())` — a fresh random UUID every call, never `uuid5` of anything key-derived (this is the identity rule: never merge by Jira key or GitHub number). `try: WorkPassport.objects.create(passport_id=passport_id, vendor_id=vendor_id, jira_key=jira_key, github_item_id=github_item_id, title=title)` (leave `story_id`/`station`/`epic_id`/`status`/`effort` at their model defaults — those fields describe an internal BMAD story and are meaningless for a vendor passport; documented trade-off of extending the existing model rather than minting a second one) `except (ImproperlyConfigured, OperationalError, ProgrammingError) as exc: return _refused(vendor_id, exc)` / `except (DataError, IntegrityError) as exc: return {"status": "error", "vendor_id": vendor_id, "message": f"{type(exc).__name__}: {exc}"}`.
  5. `return {"status": "minted", "passport_id": passport_id, "vendor_id": vendor_id, "jira_key": jira_key, "github_item_id": github_item_id}`.
  - `_refused(vendor_id, exc) -> dict` helper (mirrors `corridor_load.py`'s `_refused`).

**Admin (edit existing `dashboard/admin.py`):** extend `WorkPassportAdmin` — add `"vendor_id"` to `list_display`, `list_filter`, and `search_fields`. Stays editable (no permission overrides), matching its existing precedent: a human links nicknames per Operator ruling 3, and the same admin now also curates vendor rows.

**CLI wiring (edit existing `cli.py`):**
- `DUTIES` tuple (currently 21, ending `..., "catalog", "load"`): append `"passport"` (22nd duty).
- `_HELP`: add `"passport": "vendor work-passport identity -- mints a FRESH UUID per inbound key, never merges by Jira key or GitHub number (Story 61.2)"`.
- `build_parser()` elif-chain: add `elif name == "passport": _add_passport_subparsers(duty_parser)`.
- New `_add_passport_subparsers(passport_parser)` (place near `_add_load_subparsers`): `--json` on the parent only (mirrors `load`'s parent-only placement); a subparsers block `dest="passport_verb", metavar="{mint}"`; one `mint` subparser with `--vendor-id` (required), `--jira-key` (default `None`), `--github-item-id` (default `None`), `--title` (default `""`).
- `resolve_duty()`: add `if name == "passport": from .passport import PassportDuty; return PassportDuty()`.

**Tests (NEW):** `src/pyforge/steward/tests/unit/test_passport_mint.py` — mirror `test_corridor.py`'s settings-configure race-guard idiom (the real migrated table is needed). Cover: `mint_vendor_passport` (blank `vendor_id` → `PassportMintError`; neither key given → `PassportMintError`; `[dashboard]` extra absent — patch `sys.modules`/`importlib` to raise `ImportError` — → `status: "refused"`); `record_vendor_passport` (happy path with only `jira_key`; happy path with only `github_item_id`; **identical repeat call with the same `vendor_id` + `jira_key` → two rows, two distinct `passport_id`s, both present — the I/O Matrix's required scenario**; a simulated `IntegrityError`/`DataError` on `.create()` → `status: "error"`, distinct from `"refused"`); `PassportDuty.run()` (bare → `ok=False`; `mint` happy path → `ok=True`, summary names the passport id; `mint` with neither key → `ok=False`; `--json` on both a success and a failure branch); CLI parsing (`build_parser().parse_args(["passport", "mint", "--vendor-id", "acme", "--jira-key", "PROJ-1"])` produces the expected namespace; missing `--vendor-id` raises `SystemExit` at parse time).

**Existing tests to edit:**
- `tests/unit/test_cli.py:35-58` (`test_there_are_exactly_twenty_one_duties`): rename to `test_there_are_exactly_twenty_two_duties`, append `"passport"` to the tuple.
- `tests/unit/test_cli.py`'s `test_each_duty_dispatches_and_succeeds` exclusion tuple (currently `init, setup, initrepo, validate-fast, restore, revoke, cutover`): add `"passport"` — bare `steward passport` refuses (no verb), matching `restore`'s own bare-refuses precedent, not `load`'s bare-reports one.
- `tests/unit/test_restore_duty.py:18` (`assert len(DUTIES) == 21`): update to `22` and extend the trailing comment with `+ passport (Story 61.2)`.
- `tests/unit/test_dashboard_admin_and_htmx.py` (`test_work_passport_model_and_admin`, ~line 122-141): extend the `wp_admin.list_display` tuple assertion with `"vendor_id"`.
- `tests/meta/test_invariants.py`'s `test_no_module_outside_dashboard_imports_dashboard_django_or_channels` (~line 344-452): add a `passport.py` scoped assertion (parse its own AST, assert no banned top-level import, assert the literal string `"pyforge.steward.dashboard.passport_mint"` appears in its source) — copy the existing `corridor.py` block's shape exactly.
- `tests/meta/test_invariants.py`'s `test_the_dashboard_module_split_is_pinned_not_merely_documented` (~line 522-592): add `"passport_mint.py"` to the `documented` set.
- `dashboard/__init__.py`'s module-split docstring: add a "since Story 61.2" clause naming `passport_mint.py` as a third lazy-django-import dashboard module, alongside `passport_sync.py` and `corridor_load.py`.

## Tasks & Acceptance

**Execution:**
- `dashboard/models.py` -- add `WorkPassport.vendor_id`, reword class docstring -- CAP-140's schema gap.
- `dashboard/migrations/0004_workpassport_vendor_id.py` -- generated (not hand-written) migration for the field above.
- `dashboard/admin.py` -- extend `WorkPassportAdmin` with `vendor_id`.
- `dashboard/passport_mint.py` -- NEW: `record_vendor_passport()`, the Django-ORM half (lazy `import django`, always a fresh `uuid.uuid4()`, no lookup-by-key).
- `passport.py` -- NEW: `PassportMintError`, `mint_vendor_passport` (dynamic dashboard reach), `PassportDuty`.
- `cli.py` -- register the 22nd duty `passport` (`DUTIES`, `_HELP`, `build_parser` elif-chain + `_add_passport_subparsers`, `resolve_duty`).
- `tests/unit/test_passport_mint.py` -- NEW, full coverage per Code Map above, including the I/O Matrix's same-key-two-mints scenario.
- `tests/unit/test_cli.py` -- duty count 21 → 22, tuple updated, exclusion list updated.
- `tests/unit/test_restore_duty.py` -- `len(DUTIES)` 21 → 22.
- `tests/unit/test_dashboard_admin_and_htmx.py` -- `WorkPassportAdmin.list_display` assertion extended.
- `tests/meta/test_invariants.py` -- add the `passport.py` AST assertion and the `passport_mint.py` module-split entry.
- `dashboard/__init__.py` -- docstring updated for the new lazy-import module.

**Acceptance Criteria:**
- Given two mint calls with the same `vendor_id` and the same `jira_key`, when each runs via `steward passport mint`, then each returns `ok=True` with a distinct `passport_id`, and both rows exist in `WorkPassport` — no merge by key (the I/O Matrix's one required scenario).
- Given a `mint` call with neither `--jira-key` nor `--github-item-id`, when it runs, then it returns `ok=False` naming that at least one nickname is required, and no row is created.
- Given the bare `steward passport` invocation (no verb), when it runs, then it returns `ok=False` naming that a verb is required, without touching Django/the database.
- Given `pyforge-steward[dashboard]` is not installed (django not importable), when `steward passport mint ...` runs, then `mint_vendor_passport` returns `status: "refused"` (never a raised `ImportError` escaping the duty boundary).
- Given an existing internal-mint `WorkPassport` row created by `sprint_ledger_query.py`'s ledger sync (no `vendor_id`), when the migration and this story's code land, then that row is unaffected (`vendor_id` reads `None`) and still round-trips through `sync_work_passports_db`.

## Spec Change Log

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 14 findings — high 0, medium 1, low 11, false 2, maybe-false 0
- findings:
  - `[false]` (Blind Hunter) `sprint-status-ledger.yaml` still reads `backlog` for `61-2-work-passport-and-core-schema` with no ledger update in the diff. Refuted: per this repo's own convention (AGENTS.md) and 61.1's own identical, already-litigated finding, the spec's internal dev-loop `status` and the ledger's story status are two intentionally decoupled tracks — ledger promotion happens via a separate `sprint-ledger-sync` step, never automatically during dev.
  - `[low]` `[reject]` (Blind Hunter) This spec's own Design Notes cites the pre-diff `WorkPassport` docstring wording ("61.2 remains the story of record and builds on it") as the dated rationale for building on the existing model, and this diff rewords that docstring — the citation now describes a historical, not current, docstring state. Rejected per this workflow's own rule: a finding whose only fix is editing this build's spec is rejected outright; the citation still correctly attributes the parent Spec's CAP-140 ruling (unchanged by this diff) that actually drove the decision.
  - `[false]` (Blind Hunter) `_HELP["passport"]`'s "mints a FRESH UUID per inbound key" could be misread as a uniqueness/dedupe guarantee. Refuted: the same help string's second clause, in the identical diff hunk, reads "...never merges by Jira key or GitHub number (Story 61.2)" — read as the one string it is, the clarifying clause resolves the ambiguity the isolated first half appeared to raise.
  - `[low]` `[patch]` (Blind Hunter + Verification Gap Reviewer, grouped — identical claim) `WorkPassportAdmin.list_filter`/`search_fields` gained `"vendor_id"` but no test asserts either tuple (only `list_display` is asserted), unlike the sibling `CorridorLoadAdmin`, whose own test does assert both. Verified: `test_work_passport_model_and_admin` in `test_dashboard_admin_and_htmx.py` only checks `list_display`. Action: extend that test to assert `list_filter` and `search_fields` include `vendor_id`, mirroring `CorridorLoadAdmin`'s precedent.
  - `[low]` `[patch]` (Blind Hunter) `record_vendor_passport`'s success return dict omits `title` even though it is accepted and persisted, and no test reads `row.title` back. Verified: the `return {"status": "minted", ...}` block and every `test_record_vendor_passport_*` test confirm this. Action: add `"title": title` to the return dict and assert the persisted `row.title` in the existing happy-path tests.
  - `[low]` `[patch]` (Blind Hunter) The blank-`vendor_id` `PassportMintError` path is tested only by calling `mint_vendor_passport` directly, never through `PassportDuty.run()`'s own try/except-to-`DutyResult` conversion (unlike the "neither key" case, which is tested at both levels). Verified by reading `test_passport_mint.py`: no `test_passport_duty_mint_blank_vendor_id_fails`. Action: add that test.
  - `[low]` `[reject]` (Blind Hunter) `test_invariants.py`'s three near-identical AST-parsing blocks (`sprint_ledger_query.py`, `corridor.py`, now `passport.py`) duplicate rather than share a parametrized helper. Rejected: this diff's block replicates the exact pattern Story 61.1 already added and 61.1's own review did not flag; extracting a shared helper now would mean touching the other two, unrelated stories' existing blocks too — more than this story's smallest fix, and unlikely to cause real harm (test correctness, not DRY-ness, is what's load-bearing here).
  - `[low]` `[patch]` (Blind Hunter) `passport_mint.py`'s `_refused()` returns only `status`/`vendor_id`/`message`, dropping `jira_key`/`github_item_id`/`title`, unlike `corridor_load.py`'s `_refused()`, which echoes every identifying field it was given. Verified by reading both helpers. Action: echo `jira_key`, `github_item_id`, and `title` in `passport_mint.py`'s `_refused()` too.
  - `[low]` `[defer]` (Blind Hunter) This PR touches only `_bmad-output/**` and `src/shared/packages/**`, no `recipes/**`, so it needs the `maintenance` label at PR open time per CLAUDE.md/AGENTS.md. Deferred: this is a PR-mechanics step for whoever opens the PR, not a code or spec defect — no PR exists yet from this single-story dev dispatch (same posture as 61.1's own "no ledger/PR mechanics were run" residual note).
  - `[low]` `[reject]` (Edge Case Hunter) `record_vendor_passport`'s `except (DataError, IntegrityError)` does not also catch `InterfaceError`/`InternalError`/`NotSupportedError`. Verified the exception set is byte-for-byte identical to `corridor_load.record_corridor_load`'s own already-shipped, already-reviewed set, and that an escaping exception is still caught by `PassportDuty.run()`'s outer `except Exception` duty boundary (AD-8 holds; the caller gets a generic "passport failed: ..." rather than a structured `error` payload). Rejected on the same grounds 61.1's identical outer-catch-all finding was rejected: unlikely in everyday use, and widening the except clause without a demonstrated real trigger is more than the smallest fix.
  - `[medium]` `[patch]` (Edge Case Hunter) `mint_vendor_passport` validates `vendor_id` with `.strip()` but passes the un-stripped value through to `record_vendor_passport`, so `"  acme  "` and `"acme"` mint as two different, never-matching vendor identities — verified by reading the validation-then-passthrough code directly. This can fragment the intent-contract's "Always: vendor_id is on inbound rows; v1 is one vendor" invariant under a realistic trigger (a copy-pasted CLI argument). Action: pass `vendor_id.strip()` through to `record_vendor_passport`.
  - `[low]` `[patch]` (Edge Case Hunter) The "at least one nickname" check (`if not jira_key and not github_item_id`) treats a whitespace-only string (e.g. `" "`) as a valid nickname, since it is non-empty. Verified by reading the check. Action: check `(jira_key or "").strip()` / `(github_item_id or "").strip()` instead.
  - `[low]` `[reject]` (Edge Case Hunter) `record_vendor_passport` never sets `station`/`story_id`, so a vendor passport's `__str__` and admin ordering render with empty leading segments. Rejected: this is the exact, explicitly documented trade-off in this spec's own Design Notes ("a vendor passport's `story_id`/`station`/... fields are meaningless... simply left at their empty-string... defaults") — the suggested fix (a fabricated sentinel like `station="vendor"`) would invent data the intent never asked for, for a purely cosmetic `__str__`/ordering effect.

## Design Notes

- **`vendor_id` is a free-form caller-supplied string, not a validated registry.** v1 runs exactly one vendor (Operator ruling 4), and a `Vendor` model or an allow-list would be speculative for a value nothing yet validates against — the simpler option is taken, matching `--waybill`'s precedent from Story 61.1 (also caller-supplied, recorded verbatim).
- **No wiring from `corridor.py`/`CorridorLoad` into this mint path.** This story's declared Surface is "the existing Postgres join store" only; `CorridorLoad` stays a batch-level idempotency record with no row-level content, exactly as 61.1 shipped it. Turning an uploaded file's individual rows into `passport mint` calls (a real extract-file format) is not specified anywhere in this Spec's Boundaries or I/O Matrix and is left to whichever later story defines that format — this story only builds the identity primitive those rows will mint through.
- **Reusing `WorkPassport` rather than a second model carries an accepted cost**: a vendor passport's `story_id`/`station`/`epic_id`/`status`/`effort` fields are meaningless (they describe an internal BMAD story) and are simply left at their empty-string/`"backlog"` defaults. This is the explicit, dated direction in the parent Spec's CAP-140 annotation and the model's own Story 65.1 docstring ("61.2 remains the story of record and builds on it") — not a design choice made fresh here.
- **Never a lookup-then-create.** `record_vendor_passport` always calls `.create()`, never `.filter(...).first()` first (unlike `corridor_load.py`'s idempotent load) — idempotency is the wrong property here; the identity rule is the opposite: the same key must never resolve to the same row twice.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

**Manual checks:**
- `PYTHONPATH=src/shared/packages/pyforge-steward/src python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_passport_mint.py src/shared/packages/pyforge-steward/tests/unit/test_cli.py src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py src/shared/packages/pyforge-steward/tests/unit/test_dashboard_admin_and_htmx.py src/shared/packages/pyforge-steward/tests/unit/test_sprint_ledger_query.py src/shared/packages/pyforge-steward/tests/meta/test_invariants.py -q` -- expected: all pass, including `test_the_shipped_migration_matches_the_model` and `test_no_module_outside_dashboard_imports_dashboard_django_or_channels`.
- `PYTHONPATH=src/shared/packages/pyforge-steward/src python -m pyforge.steward.cli passport mint --vendor-id acme --jira-key PROJ-1` -- like `load inbound` (61.1), this verb needs a configured `DJANGO_SETTINGS_MODULE`, which a bare shell in this sandbox does not have; expected here is a clean refusal (`passport mint: DJANGO_SETTINGS_MODULE is unset...`, exit 1), never a raised `ImportError`/traceback -- confirmed identical to `load inbound`'s own behavior under the same bare invocation. The real ORM path (`status: minted`, a persisted row) is exercised and passes under the test suite's migrated in-memory SQLite database (`test_passport_mint.py`), which is where this duty is actually verified end-to-end.
- `pixi run -e pyforge-steward pyforge-steward-coverage-gate` -- expected: `passport.py` and `dashboard/passport_mint.py` at or above the station's coverage floor.

## Note — 2026-09-19

Story 65.1 (PR #1507) shipped a `WorkPassport` Django model (`dashboard/models.py`, migration
`0002_workpassport`: minted UUID `passport_id`; `jira_key` / `github_item_id` as aliases), its
admin and a flag-gated `passport_sync` — CAP-140's identity rule realized in part, outside this
story's declared surface (no `vendor_id`; not the existing Postgres join store; 61.1's corridor not
landed). This story builds on that model; it does not mint a second one.
