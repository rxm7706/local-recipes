---
title: '61.1: Corridor transports — upload default'
type: 'feature'
created: '2026-09-16'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred: []
declared_low_risk: false
baseline_revision: '1a0857aa9be731c5868e3f1f76bcb2b46d621a43'
---

<intent-contract>

## Intent

**Problem:** Vendor and estate lists have no idempotent drop path.

**Approach:** Inbound and outbound files load by batch sha + waybill. Default transport is app upload; email and share-folder are plugins. Do not treat Epic 8 as this product. Do not PAT into the vendor private GitHub.

## Boundaries & Constraints

**Always:**
- Load is idempotent on batch sha + waybill.
- Default transport is app upload.

**Never:**
- Do not treat steward Epic 8 as this product.
- Do not PAT into the vendor private GitHub.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| duplicate drop | same batch sha + waybill | idempotent no-op | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-work-passports-dated-extracts CAP-1`.
Surface: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-work-passports-dated-extracts/transports-and-vendors.md; the existing Postgres app / a steward load duty..
Ledger key: `61-1-corridor-transports-upload-default`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-61-1-corridor-transports-upload-default.md`.

## Code Map

Investigated live (2026-09-19): grepped `batch sha`/`waybill`/`corridor`/`idempotent`/`transport` across `src/shared/packages/pyforge-steward/` — **zero prior art**; this is greenfield. `dashboard/models.py` already has `WorkPassport` (Story 65.1, PR #1507) but it is the sprint-ledger-query identity model (`passport_id`/`story_id`/`station`), not a vendor/estate concept — do not touch it, do not add `vendor_id` to it (that is Story 61.2's job on a different capability).

**Base-package module (NEW):** `src/shared/packages/pyforge-steward/src/pyforge/steward/corridor.py`
- Copy the config-loading idiom from `catalog.py:78-154` (`CatalogConfigError`, `_load_yaml_mapping`) and `sync.py:98-163` (`SyncConfigError`, frozen `@dataclass` config, `yaml.safe_load` only, four named failures: missing / malformed YAML / unreadable / not-a-mapping) — name the error `CorridorConfigError(ValueError)`.
- `TransportDecl` — frozen `@dataclass`: `name: str`, `state: str` (`state` ∈ `("on", "off")`, mirrors `catalog.py`'s `BackendDecl`/`SourceDecl` shape, scaled down — no `plugin`/`options` fields needed, v1 has no third-party transport plugin to bind).
- `CorridorConfig` — frozen `@dataclass`: `transports: tuple[TransportDecl, ...]`, with a `transport(name) -> TransportDecl | None` lookup helper.
- `default_corridor_dir(root=None) -> Path` returning `<root>/src/shared/packages/pyforge-steward/corridor` (mirrors `catalog.py:129-131` `default_catalog_dir`).
- `load_config(config_path: Path) -> CorridorConfig` — reads a `transports:` mapping (`{name: {state: "on"|"off"}}`); missing/malformed/not-a-mapping/bad-state are each a distinct `CorridorConfigError` message (same idiom as `catalog.py`'s `_require_str` et al., simplified — no nested plugin binding to validate).
- `compute_batch_sha(data: bytes) -> str` — `hashlib.sha256(data).hexdigest()`.
- `DIRECTIONS: tuple[str, ...] = ("inbound", "outbound")` — plain module constant (NOT a Django `TextChoices`; this module must stay django-free, see below).
- `CorridorLoadError(ValueError)` — raised for an unknown transport name or a transport whose declared `state` is `"off"`.
- `LoadOutcome` — frozen `@dataclass`: `status: str` (`"loaded" | "idempotent" | "refused"`), `direction: str`, `batch_sha: str`, `waybill: str`, `transport: str`, `message: str = ""`.
- `load_extract(*, direction, batch_sha, waybill, transport, config) -> LoadOutcome` — validates `direction in DIRECTIONS` and `config.transport(transport)` exists and is `state == "on"` (raise `CorridorLoadError` otherwise, message naming the declared transports so a typo is diagnosable), then reaches the ORM via the **one sanctioned dynamic base→dashboard idiom** — copy `sprint_ledger_query.py:1282-1296` (`sync_to_postgres`) verbatim in shape:
  ```python
  import importlib
  try:
      module = importlib.import_module("pyforge.steward.dashboard.corridor_load")
  except ImportError:
      return LoadOutcome(status="refused", direction=direction, batch_sha=batch_sha, waybill=waybill, transport=transport, message="pyforge-steward[dashboard] extra not installed")
  result = module.record_corridor_load(direction=direction, batch_sha=batch_sha, waybill=waybill, transport=transport)
  return LoadOutcome(status=result["status"], direction=result["direction"], batch_sha=result["batch_sha"], waybill=result["waybill"], transport=result["transport"], message=result.get("message", ""))
  ```
  **This is load-bearing, not optional style**: `tests/meta/test_invariants.py::test_no_module_outside_dashboard_imports_dashboard_django_or_channels` AST-scans every `.py` file under `pyforge/steward/` OUTSIDE `dashboard/` (including inside function bodies) and fails on ANY `import`/`from import` naming `django`, `channels`, or `pyforge.steward.dashboard*` — a plain `from pyforge.steward.dashboard.corridor_load import record_corridor_load` anywhere in `corridor.py`, even function-local, reds that test. Only `importlib.import_module(...)` (a dynamic string call) is invisible to its AST walk.
- `LoadDuty` — the `Duty`-conforming class (`interfaces.py:19-51`: `DutyResult(ok, summary, details)` frozen, never `sys.exit` — AD-8). `name = "load"`. `run(ns)` shape, mirroring `catalog.py:1132-1229`'s `CatalogDuty.run` (bare-verb default like `catalog`'s bare→`check`, not like `restore`/`revoke`/`cutover`'s required-flag refusal):
  - Resolve `corridor_dir` from `getattr(ns, "corridor", None)` or `default_corridor_dir(repo_root())`; `repo_root` imports from `.bootstrap` (see `catalog.py:49`).
  - `load_config(corridor_dir / "corridor.yaml")`; on `CorridorConfigError`, return `DutyResult(ok=False, ...)`.
  - `verb = getattr(ns, "load_verb", None)`. **If `verb is None`** (bare `steward load`): return `DutyResult(ok=True, summary=<one line per transport, e.g. "app-upload: on, shared-folder: off, email: off">, details={"transports": [{"name": t.name, "state": t.state} for t in config.transports]})` — read-only, must succeed against the real tracked `corridor.yaml` with no Django/DB touch at all (this is what keeps `load` OUT of `test_cli.py`'s `test_each_duty_dispatches_and_succeeds` exclusion list — see Tasks below).
  - **If `verb` is `"inbound"` or `"outbound"`**: read `ns.file` (required, `Path`); if not `Path(ns.file).is_file()`, return `DutyResult(ok=False, summary=f"load {verb}: {ns.file}: not found")`. Else `data = Path(ns.file).read_bytes()`; `batch_sha = compute_batch_sha(data)`; call `load_extract(direction=verb, batch_sha=batch_sha, waybill=ns.waybill, transport=getattr(ns, "transport", "app-upload"), config=config)` inside a `try/except CorridorLoadError as exc: return DutyResult(ok=False, summary=f"load {verb}: {exc}")`.
  - Outcome mapping: `status in ("loaded", "idempotent")` → `DutyResult(ok=True, summary=f"{status}: {verb} waybill={outcome.waybill} sha={outcome.batch_sha[:12]} via {outcome.transport}", details={...})`; `status == "refused"` → `DutyResult(ok=False, summary=f"load {verb}: {outcome.message}", details={...})`.
  - `--json` flag (mirror `catalog`'s): when set, `summary` is `json.dumps(payload, indent=2, sort_keys=True)` instead of the one-liner.
  - Wrap the whole body in one outer `try/except Exception as exc:  # noqa: BLE001 — duty boundary` returning `DutyResult(ok=False, summary=f"load failed: {exc}")` (mirrors `restore.py`'s and `catalog.py`'s duty-boundary shape).

**Dashboard module (NEW):** `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/corridor_load.py`
- Copy `dashboard/passport_sync.py` verbatim in shape (module docstring pattern, lazy `import django` INSIDE the function, never at module top — `passport_sync.py` has no top-level django import at all).
- `_SETTINGS_UNSET` message constant (copy `passport_sync.py:15-18` verbatim, same wording).
- `record_corridor_load(*, direction: str, batch_sha: str, waybill: str, transport: str) -> dict` — mirrors `passport_sync.sync_work_passports_db`'s try/except structure exactly:
  1. `try: import django; from django.apps import apps; from django.conf import settings; from django.core.exceptions import ImproperlyConfigured; except ImportError as exc: return _refused(..., exc)`.
  2. `if not settings.configured and not os.environ.get("DJANGO_SETTINGS_MODULE"): return {"status": "refused", ..., "message": _SETTINGS_UNSET}`.
  3. `try: if not apps.ready: django.setup(); from django.db import DataError, IntegrityError, OperationalError, ProgrammingError; from pyforge.steward.dashboard.models import CorridorLoad; except (ImportError, ImproperlyConfigured) as exc: return _refused(..., exc)` — this import IS static `from pyforge.steward.dashboard.models import CorridorLoad`, which is FINE here because this file lives INSIDE `dashboard/` itself (the AST guard only bans dashboard/django/channels imports OUTSIDE `dashboard/`).
  4. `existing = CorridorLoad.objects.filter(direction=direction, batch_sha=batch_sha, waybill=waybill).first()`. If found: `return {"status": "idempotent", "direction": direction, "batch_sha": batch_sha, "waybill": waybill, "transport": existing.transport}` — **this is the idempotency: no new row, and the transport reported is the ORIGINALLY recorded one, never the one this call was invoked with**. Else `CorridorLoad.objects.create(direction=direction, batch_sha=batch_sha, waybill=waybill, transport=transport)` inside `try/except (ImproperlyConfigured, OperationalError, ProgrammingError) as exc: return _refused(...)` / `except (DataError, IntegrityError) as exc: return {"status": "error", ...}`, then `return {"status": "loaded", "direction": direction, "batch_sha": batch_sha, "waybill": waybill, "transport": transport}`.
  - `_refused(direction, batch_sha, waybill, transport, exc) -> dict` helper (mirrors `passport_sync.py:87-93` `_fallback`), `message=f"Django ORM unavailable ({type(exc).__name__}: {exc})"`.

**Model (NEW, add to existing `dashboard/models.py`):**
```python
class CorridorDirection(models.TextChoices):
    INBOUND = "inbound", "Inbound"
    OUTBOUND = "outbound", "Outbound"


class CorridorLoad(models.Model):
    """CAP-139 (spec-work-passports-dated-extracts CAP-1 / spec-pyforge-steward
    CAP-139): one durable record of a corridor drop. Idempotent on
    (direction, batch_sha, waybill) -- see dashboard/corridor_load.py."""

    direction = models.CharField(max_length=8, choices=CorridorDirection.choices, db_index=True)
    batch_sha = models.CharField(max_length=64, db_index=True)
    waybill = models.CharField(max_length=128, db_index=True)
    transport = models.CharField(max_length=32)
    loaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-loaded_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["direction", "batch_sha", "waybill"],
                name="corridorload_unique_direction_batch_sha_waybill",
            )
        ]
        verbose_name = "Corridor Load"
        verbose_name_plural = "Corridor Loads"

    def __str__(self) -> str:
        return f"{self.direction}:{self.waybill} ({self.batch_sha[:8]})"
```
Add this class after `WorkPassport` in `dashboard/models.py`. The `UniqueConstraint` is a DB-level backstop; `corridor_load.py`'s `.filter(...).first()` read-before-write is what actually implements the idempotent no-op path (the constraint only guards a theoretical race, which this story does not need to test).

**Migration (NEW):** `dashboard/migrations/0003_corridorload.py`, `dependencies = [("pyforge_steward_dashboard", "0002_workpassport")]`. **Do not hand-transcribe it.** Generate it for real to guarantee zero drift against `tests/unit/test_dashboard_audit.py::test_the_shipped_migration_matches_the_model` (which generically re-checks EVERY model in this app via `call_command("makemigrations", "--check", "--dry-run", interactive=False, verbosity=0)`): write a disposable script that does the same `settings.configure(INSTALLED_APPS=["pyforge.steward.dashboard"], DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}, USE_TZ=True)` + `django.setup()` dance every dashboard test file already does (see `tests/unit/test_dashboard_audit.py:1-58` for the exact block to copy), then `call_command("makemigrations", "pyforge_steward_dashboard", name="corridorload")` pointed at the real `dashboard/migrations/` dir, inspect the generated file, then delete the disposable script.

**Admin (add to existing `dashboard/admin.py`):** register `CorridorLoadAdmin(admin.ModelAdmin)` mirroring `AuditEntryAdmin` (`admin.py:9-27`) exactly — read-only (`has_add_permission`/`has_change_permission`/`has_delete_permission` all `False`; a load record is a durable fact, not an editable row), `list_display = ("direction", "waybill", "batch_sha", "transport", "loaded_at")`, `list_filter = ("direction", "transport")`, `search_fields = ("batch_sha", "waybill")`, `ordering = ("-loaded_at",)`.

**Config (NEW, tracked):** `src/shared/packages/pyforge-steward/corridor/corridor.yaml` (git is the edit store, same philosophy as `catalog/catalog.yaml`):
```yaml
# Steward corridor -- transports (Story 61.1, spec-pyforge-steward CAP-139).
# Every transport writes the SAME loader (batch sha + waybill,
# corridor.py::load_extract). A new transport is a declared row bound to a
# state, never an engine rewrite.
transports:
  app-upload:
    state: on
  shared-folder:
    state: off
  email:
    state: off
```

**CLI wiring (edit existing `src/pyforge/steward/cli.py`):**
- `DUTIES` tuple (`cli.py:43-64`): append `"load"` after `"catalog"` (21st duty). Update the enumerating comment above it (`cli.py:35-42`) with a `load` line (Epic 61, Story 61.1).
- `_HELP` dict (`cli.py:66-...`): add `"load": "extract corridor -- idempotent inbound/outbound file loads keyed by batch sha + waybill; transports declared in corridor.yaml (Story 61.1)"`.
- `build_parser()` elif-chain (`cli.py:163-...`): add `elif name == "load": _add_load_subparsers(duty_parser)`.
- New `_add_load_subparsers(load_parser: argparse.ArgumentParser) -> None` function (place near `_add_catalog_subparsers`, `cli.py:425`): add `--corridor DIR` (default `None`) and `--json` (`store_true`) on the parent, a subparsers block `dest="load_verb", metavar="{inbound,outbound}"`, and for each of `"inbound"`, `"outbound"` a subparser taking `--file PATH` (required), `--waybill LABEL` (required), `--transport NAME` (default `"app-upload"`) — mirror `_add_catalog_subparsers`'s (`cli.py:425-...`) pattern of accepting `--corridor`/`--json` both before and after the verb if that pattern is easy to replicate; if not trivially reusable, a single placement (on the parent `load_parser` only) is acceptable — this story does not require the same both-positions UX catalog has, only that `--corridor`/`--json` parse in the conventional position (before the verb).
- `resolve_duty()` (`cli.py:1124-1223`): add `if name == "load": from .corridor import LoadDuty; return LoadDuty()`.

**Tests (NEW):** `src/shared/packages/pyforge-steward/tests/unit/test_corridor.py` — mirror the settings-configure race-guard idiom from `tests/unit/test_dashboard_admin_and_htmx.py:1-56` (or `test_dashboard_audit.py:1-58`) verbatim (guarded `settings.configure(...)`, containment assert on `INSTALLED_APPS`, `django.setup()`, `call_command("migrate", run_syncdb=True, verbosity=0)`) since this file needs the real migrated `CorridorLoad` table. Cover: `load_config` (missing file, malformed YAML, not-a-mapping, missing `transports` key, bad `state` value, happy path with the real tracked `corridor.yaml`); `compute_batch_sha`; `load_extract` (unknown transport → `CorridorLoadError`; declared-off transport → `CorridorLoadError`; fresh load → `status="loaded"`, one row created; **identical repeat (same direction+batch_sha+waybill) → `status="idempotent"`, still exactly one row — this is the I/O Matrix's one required scenario**; a different `waybill` for the same `batch_sha` creates a second, distinct row); `LoadDuty.run()` (bare invocation → `ok=True`, reports 3 transports, no DB touch needed; `inbound`/`outbound` first load → `ok=True` "loaded"; repeat → `ok=True` "idempotent"; missing `--file` path → `ok=False`; `--transport email` (declared off) → `ok=False`); CLI parsing (`build_parser().parse_args(["load", "inbound", "--file", "x", "--waybill", "w"])` produces the expected namespace).

**Existing tests to edit:**
- `tests/unit/test_cli.py:35-57` (`test_there_are_exactly_twenty_duties`): rename to `test_there_are_exactly_twenty_one_duties`, append `"load"` to the tuple.
- `tests/unit/test_cli.py`'s `test_each_duty_dispatches_and_succeeds` exclusion list (currently `init, setup, initrepo, validate-fast, restore, revoke, cutover`): **do NOT add `"load"`** — `main(["load"])` (bare, no verb) must return `EXIT_OK` by reading the real tracked `corridor.yaml`, same as `main(["catalog"])` already does against the real tracked `catalog.yaml`.
- `tests/meta/test_invariants.py` (~line 344-429, `test_no_module_outside_dashboard_imports_dashboard_django_or_channels`): the general AST scan already covers `corridor.py` for free (no edit needed there). Its docstring (~line 367) currently claims `sync_to_postgres`'s reach is "the ONE sanctioned base→dashboard reach" — this becomes inaccurate once `corridor.py` adds a second one; reword to "one of the sanctioned...reaches" (or similar minimal wording fix) and add a second scoped assertion mirroring the existing one at ~line 410-429 (parse `corridor.py`'s own AST, assert no banned top-level import, assert the literal string `"pyforge.steward.dashboard.corridor_load"` appears in its source) — copy the existing `sprint_ledger_query.py` block's shape exactly, targeting `corridor.py` instead.

## Tasks & Acceptance

**Execution:**
- `dashboard/models.py` -- add `CorridorDirection` + `CorridorLoad` -- the durable idempotency record.
- `dashboard/migrations/0003_corridorload.py` -- generated (not hand-written) migration for the model above.
- `dashboard/admin.py` -- register `CorridorLoadAdmin`, read-only, mirrors `AuditEntryAdmin`.
- `dashboard/corridor_load.py` -- NEW: `record_corridor_load()`, the Django-ORM half (lazy `import django`, never at module top).
- `corridor.py` -- NEW: config loading, `compute_batch_sha`, `load_extract` (dynamic `importlib.import_module` reach into `dashboard/corridor_load.py`), `LoadDuty`.
- `corridor/corridor.yaml` -- NEW tracked transport declaration (`app-upload: on`, `shared-folder: off`, `email: off`).
- `cli.py` -- register the 21st duty `load` (`DUTIES`, `_HELP`, `build_parser` elif-chain + `_add_load_subparsers`, `resolve_duty`).
- `tests/unit/test_corridor.py` -- NEW, full coverage per Code Map above, including the I/O Matrix's duplicate-drop scenario.
- `tests/unit/test_cli.py` -- duty count 20 → 21, tuple updated; `load` NOT added to the bare-invocation exclusion list.
- `tests/meta/test_invariants.py` -- reword the "ONE sanctioned reach" docstring claim and add the mirrored `corridor.py` assertion.

**Acceptance Criteria:**
- Given a fresh inbound file at a waybill never seen before, when `steward load inbound --file <path> --waybill <w>` runs, then it returns `ok=True` with `status: loaded` and exactly one `CorridorLoad` row exists for `(inbound, <sha>, <w>)`.
- Given that exact same file dropped again with the same `--waybill`, when `steward load inbound` runs again, then it returns `ok=True` with `status: idempotent` and the row count for `(inbound, <sha>, <w>)` is still exactly one (the I/O Matrix's duplicate-drop scenario).
- Given `--transport email` or `--transport shared-folder` (both declared `state: off` in `corridor.yaml`), when `steward load inbound|outbound` runs with that transport, then it returns `ok=False` naming the transport as off, and no `CorridorLoad` row is created.
- Given the bare `steward load` invocation (no verb), when it runs, then it returns `ok=True` and reports all three declared transports and their states, without touching Django/the database at all.
- Given `pyforge-steward[dashboard]` is not installed (django not importable), when `steward load inbound ...` runs, then `load_extract` returns `status: refused` (never a raised `ImportError` escaping the duty boundary).

## Spec Change Log

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 21 findings — high 0, medium 8, low 8, false 5, maybe-false 0
- findings:
  - `[medium]` `[patch]` (Blind Hunter) Concurrent double-drop races `.filter().first()` against `.create()` in `dashboard/corridor_load.py`; the loser hits the `UniqueConstraint` and returns `status: "error"` instead of the promised idempotent no-op — verified by reading `record_corridor_load`'s `except (DataError, IntegrityError)` catch, which does not distinguish a genuine data error from a lost idempotency race. Grouped with the Edge Case Hunter's identical finding below. Action: catch `IntegrityError` specifically around `.create()`, re-query, return `idempotent`.
  - `[low]` `[patch]` (Blind Hunter) `load_extract`'s own `except ImportError:` branch (`[dashboard]` extra absent, `status="refused"`) is untested — every existing refusal test targets `record_corridor_load` directly, never `load_extract`'s `importlib.import_module` failure path. Verified by reading `test_corridor.py`: no test patches `sys.modules["pyforge.steward.dashboard.corridor_load"]`. Action: add that test.
  - `[medium]` `[patch]` (Blind Hunter) `--json` is honored in the config-error and outcome branches of `LoadDuty.run` but not in the "file not found" or `CorridorLoadError` branches (both always emit plain text), and the JSON payload shape differs per branch (`ok` key present only in the config-error payload). Verified by reading `corridor.py:557-558` and `:570-571` — no `as_json` check present. Grouped with the payload-shape finding and both Edge Case Hunter `--json` findings below (shared root cause: incomplete `--json` handling). Action: make every branch respect `as_json` consistently and standardize the payload shape; add a `--json` test.
  - `[low]` `[patch]` (Blind Hunter) `LoadDuty.run`'s `except CorridorConfigError` branch (reached via a bad/missing `--corridor` dir) is untested at the duty level — only the underlying `load_config` function has direct tests. Action: add a duty-level test pointing `--corridor` at a `tmp_path` with a broken `corridor.yaml`.
  - `[low]` `[reject]` (Blind Hunter) `LoadDuty.run`'s outer `except Exception` duty-boundary catch-all is never exercised by a test. Rejected: this generic safety net is copied verbatim from the established `restore.py`/`catalog.py` idiom (neither of which unit-tests its own outer catch-all either), forcing it requires a contrived monkeypatch of internals for negligible protective value, and it is unlikely to be met in everyday use.
  - `[medium]` `[patch]` (Blind Hunter) Same finding as above (`--json` payload shape inconsistency: `{"ok": False, "message": ...}` only on the config-error path). Grouped with the entry two rows up.
  - `[false]` (Blind Hunter) `import importlib` is deferred into `load_extract`'s function body even though `importlib` is not one of the AST guard's banned modules. Refuted: no named harm beyond "adds noise" (the reviewer's own words) — a vague style preference with no demonstrated bad outcome is not a defect (per this pass's own classify rule).
  - `[medium]` `[patch]` (Blind Hunter) `load_extract` validates transport existence/state BEFORE checking idempotency, so a repeat drop of an already-loaded `(direction, batch_sha, waybill)` incorrectly raises `CorridorLoadError` when the caller passes an unknown or currently-`off` transport on the repeat call — verified by reading `load_extract`'s body: the `decl.state != STATE_ON` raise happens before any ORM lookup. This contradicts the Always rule "Load is idempotent on batch sha + waybill" (no transport qualifier). Action: check for an existing record first; only validate the transport on the path that would create a new record.
  - `[false]` (Blind Hunter) Spec frontmatter `status` flipped `ready`→`in-progress` with no corresponding `sprint-status-ledger.yaml` update in the diff. Refuted: per this repo's own convention (AGENTS.md), the spec's internal dev-loop `status` and the ledger's story status are two intentionally decoupled tracks — ledger promotion happens via a separate `sprint-ledger-sync` step, never automatically during dev.
  - `[false]` (Blind Hunter) `CorridorLoadAdmin.list_display` shows the full 64-char `batch_sha` while `__str__` truncates to 8 chars. Refuted: matches the existing `WorkPassportAdmin` precedent in the same file, which also shows the full `passport_id` in `list_display` while truncating only in `__str__` — not an inconsistency this diff introduced.
  - `[false]` (Blind Hunter) `db_index=True` on `CorridorLoad.direction` is redundant given the composite `UniqueConstraint`. Refuted: `CorridorLoadAdmin.list_filter = ("direction", "transport")` filters by `direction` alone in the Django admin changelist, a query path the composite constraint does not serve — the standalone index has a real, independent use.
  - `[medium]` `[patch]` (Edge Case Hunter) `--json` set + `--file` path missing returns plain text, not JSON. Same root cause as the Blind Hunter `--json` finding above; grouped there.
  - `[medium]` `[patch]` (Edge Case Hunter) `--json` set + `load_extract` raises `CorridorLoadError` returns plain text, not JSON. Same root cause; grouped with the `--json` entries above.
  - `[low]` `[patch]` (Edge Case Hunter) `outcome.status == "error"` (a genuine `DataError`) is handled by the same branch and comment (`# status == "refused"`) as a mundane extra-not-installed refusal, so a data-integrity failure is reported identically to a routine refusal. Verified by reading the branch: the comment names only `"refused"` but the condition also matches `"error"`. Action: correct the comment and give `"error"` a distinct message prefix.
  - `[low]` `[reject]` (Edge Case Hunter) `--corridor ""` (empty string) silently falls back to the default corridor dir with no error. Rejected: unlikely to occur outside a self-inflicted shell scripting error, and a fix requires adding a new validation guard — meets both prongs of the low-rejection rule.
  - `[medium]` `[patch]` (Edge Case Hunter) Same concurrent-race finding as the Blind Hunter entry above (`.filter().first()` / `.create()` not atomic). Grouped there.
  - `[medium]` `[patch]` (Edge Case Hunter) `--waybill` is unbounded free-form input written into a `CharField(max_length=128)` with no Python-level length check; SQLite (used in every test) does not enforce `VARCHAR(n)` but PostgreSQL ("the existing Postgres app" this story targets) does — verified against `dashboard/audit.py`'s own module docstring, which already documents this exact SQLite-vs-PostgreSQL divergence and enforces caps in Python for `AuditEntry` for precisely this reason; `CorridorLoad` has no equivalent guard. Action: add the same kind of length check before the ORM call.
  - `[low]` `[reject]` (Edge Case Hunter) A `corridor.yaml` declaring zero transports produces an uninformative bare-invocation summary. Rejected: the tracked, hand-authored `corridor.yaml` will never actually be empty, the scenario is unlikely to be met in everyday use, and the fix requires adding a fallback branch — meets both prongs of the low-rejection rule.
  - `[false]` (Edge Case Hunter, self-flagged `confidence: medium`) `email`/`shared-folder` are called "plugins" in the intent but have no plugin extension point in the code. Refuted: the companion doc's own words ("email is an empty slot until enabled," "v1 does not require a mailbox parser") and this spec's own Design Notes explicitly establish that v1 transports are declarative on/off labels, not implemented plugin code paths — this is the documented, correct scope, not an oversight.
  - `[low]` `[patch]` (Verification Gap, pre-verified) `record_corridor_load`'s idempotent branch reports `existing.transport` (the originally recorded transport), but no test passes a *different* transport on the repeat call to distinguish that from "the transport just passed in" — demonstrated: if `existing.transport` were swapped for the incoming parameter, every existing test would still pass. Action: add a differentiating test.
  - `[low]` `[patch]` (Verification Gap, pre-verified) `CorridorLoadAdmin` is never instantiated or asserted on by any test, unlike its sibling `AuditEntryAdmin` (`test_audit_entry_admin_is_read_only`) — demonstrated: `grep -rn "CorridorLoadAdmin"` across the package returns only its own definition. Action: add an equivalent test.
- Intent Alignment Auditor filed no discrete findings (its brief is strictly descriptive); its report confirms the diff consistently implements the CAP-139-scoped reading already documented in this spec's Design Notes (mechanism-only corridor, caller-supplied waybill, transports as on/off labels, no vendor content) — no intent gap identified.
- Patches applied: all 8 `patch`-routed findings above (4 groups covering the 8 `medium`/`low` `[patch]` rows) were fixed in one pass by the step-03 implementation subagent, re-engaged with the exact findings above. `record_corridor_load` gained `create_if_missing`, checks existence unconditionally first, and recovers a concurrent `.create()` race via a scoped `except IntegrityError` re-query (finding 1); `load_extract` now probes existence before validating transport, closing the off-transport-blocks-idempotent-repeat gap (finding 3, grouped with the race fix's root idea); `LoadDuty.run` gained a `_load_result` helper unifying `--json`/payload-shape handling across every branch (findings 2/2-dup/6-dup) plus a `_MAX_WAYBILL_LENGTH = 128` Python-side cap mirroring `audit.py`'s SQLite-vs-PostgreSQL precedent (waybill-length finding) and a corrected `"error"`-vs-`"refused"` comment/message split (status-comment finding); new tests cover the race, the off-transport repeat, `load_extract`'s own `ImportError` path, `--json` on both a success and a failure branch, the waybill cap, the `--corridor`-config-error duty branch, transport-provenance-on-repeat, and `CorridorLoadAdmin`. Verified: 77 targeted tests pass (`test_corridor.py`, `test_cli.py`, `test_invariants.py`), including `test_each_duty_dispatches_and_succeeds[load]` and the AST dashboard-import-guard tests (no new module-level `django`/`channels` import introduced). Full-suite and coverage-gate re-verification follows below.

## Design Notes

- **`waybill` is caller-supplied, not system-generated.** The Dream (`docs/dreams/work-passports-dated-extracts.md`) defines waybill as "which drop and which clocks," and the companion doc's only hard requirement is "idempotent on batch sha + waybill" (one I/O Matrix row). Nothing in the intent specifies HOW a waybill label is produced, and both a caller-supplied label and a system-auto-incremented sequence satisfy the one tested scenario identically — this is not an intent gap (no observably different outcome hinges on it), so the simpler option is taken: `--waybill LABEL` is a required CLI argument, a free-form string (e.g. `drop-42`, a date stamp), recorded verbatim. Auto-numbering, per-vendor waybill scoping, and the "their clock and our received clock" as-of semantics are CAP-141 / Story 61.3's job ("as-of glass"), not this story's.
- **No `vendor_id` on `CorridorLoad`.** The Dream's vendor table (`transports-and-vendors.md`) ties `vendor_id` to the passport schema (CAP-140 / Story 61.2), and v1 runs exactly one vendor — adding an unused column here would be speculative. `CorridorLoad` is scoped to the corridor/transport mechanism alone.
- **`shared-folder` and `email` transports have no runtime behavior in v1** — they exist only as `state: off` rows in `corridor.yaml` so `load_extract` can name them and refuse them by config, matching the companion doc verbatim ("email is an empty slot until enabled," "v1 does not require a mailbox parser"). A file always arrives via `--file PATH` regardless of which transport name is passed; "transport" in v1 is a provenance label + on/off gate, not a distinct ingestion code path.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

**Manual checks:**
- `PYTHONPATH=src/shared/packages/pyforge-steward/src python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_corridor.py src/shared/packages/pyforge-steward/tests/unit/test_cli.py src/shared/packages/pyforge-steward/tests/unit/test_dashboard_admin_and_htmx.py src/shared/packages/pyforge-steward/tests/unit/test_dashboard_audit.py src/shared/packages/pyforge-steward/tests/meta/test_invariants.py -q` -- expected: all pass, including `test_the_shipped_migration_matches_the_model` (proves the generated migration matches `models.py` with no drift) and `test_no_module_outside_dashboard_imports_dashboard_django_or_channels` (proves `corridor.py` stays django-free at the AST level).
- `PYTHONPATH=src/shared/packages/pyforge-steward/src python -m pyforge.steward.cli load` -- expected: exit 0, reports 3 transports (`app-upload: on`, `shared-folder: off`, `email: off`) against the real tracked `corridor.yaml`.
- `pixi run -e pyforge-steward pyforge-steward-coverage-gate` -- expected: `corridor.py` and `dashboard/corridor_load.py` at or above the station's coverage floor.

