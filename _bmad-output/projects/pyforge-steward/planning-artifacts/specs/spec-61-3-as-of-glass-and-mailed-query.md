---
title: '61.3: As-of glass and mailed query'
type: 'feature'
created: '2026-09-16'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred: []
declared_low_risk: false
baseline_revision: 'dfddf7be04329995ca1b53819b49638f3d8b7ef6'
---

<intent-contract>

## Intent

**Problem:** Standup asks "any news from the vendor?"

**Approach:** Standup cites a waybill; empty on-time file fails; late drop leaves yesterday stale; unborn before first waybill. A mailed/export of the same table is a switchable plugin.

## Boundaries & Constraints

**Always:**
- Standup cites a waybill.
- Empty on-time file fails.
- Late drop leaves yesterday stale.

**Never:**
- Do not invent a second standup source of truth.
- Do not treat Epic 8 as this product.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| empty on-time file | waybill present, file empty | fail | fail |
| late drop | file after window | yesterday remains visible | n/a |
| before first waybill | no waybill yet | unborn, not empty-success | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-work-passports-dated-extracts CAP-3`.
Surface: existing app views standup and shipped; optional CSV/markdown export..
Ledger key: `61-3-as-of-glass-and-mailed-query`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-61-3-as-of-glass-and-mailed-query.md`.

## Code Map

Investigated live (2026-09-19). `dashboard/models.py` has `CorridorLoad` (Story 61.1: `direction`
∈ `{inbound, outbound}`, `batch_sha`, `waybill`, `transport`, `loaded_at` `auto_now_add`, `Meta.ordering
= ["-loaded_at", "-id"]`) — content-free: `corridor.py`'s `load_extract` only ever hashes the whole
file, never parses rows (61.1/61.2 Design Notes, both already litigated). `CorridorLoad` has no
`vendor_id` (v1 is one vendor; the companion doc's "no second standup pane until on" needs no
per-vendor filter yet). No `standup`/`shipped`/`as_of`/`stale` concept exists anywhere in this
package today — greenfield, same posture as 61.1.

**Reading "empty" without a new field or touching `corridor.py`.** `corridor.py` deliberately never
inspects file content (61.1/61.2's shipped, already-reviewed boundary — this story's declared
Surface is the view layer, not the loader). An empty (0-byte) inbound file's `batch_sha` is always
the well-known SHA-256 of zero bytes (`hashlib.sha256(b"").hexdigest()` —
`e3b0c449...b7852b855`), so "empty" is detectable from `CorridorLoad.batch_sha` alone with **no
migration, no corridor.py change, no new column**.

**Base module (NEW):** `src/shared/packages/pyforge-steward/src/pyforge/steward/glass.py`
(django-free, mirrors `corridor.py`/`passport.py`'s shape: top-level `from .interfaces import
DutyResult`, `from .corridor import DIRECTIONS`, `from .sprint_ledger_query import eval_flag,
flag_off_message, parse_flag_overrides` — all base-module siblings, no django):

```python
EMPTY_FILE_SHA256 = hashlib.sha256(b"").hexdigest()
GLASS_STATES: tuple[str, ...] = ("unborn", "fresh", "stale", "failed")

class GlassError(ValueError):
    """Unknown direction, or a naive (non-timezone-aware) `now`."""

@dataclass(frozen=True)
class GlassReading:
    status: str            # "ok" | "refused"
    direction: str
    state: str | None      # one of GLASS_STATES; None when status == "refused"
    waybill: str | None
    batch_sha: str | None
    loaded_at: str | None  # ISO 8601; None when unborn/refused
    message: str = ""

def compute_glass_reading(*, direction: str, now: datetime | None = None) -> GlassReading:
    # validate direction in DIRECTIONS -> GlassError; reference_now = now or
    # datetime.now(timezone.utc); naive `now` -> GlassError.
    # importlib.import_module("pyforge.steward.dashboard.glass_query") ->
    # ImportError -> GlassReading(status="refused", state=None, message="pyforge-steward[dashboard] extra not installed").
    # outcome = module.read_latest_corridor_load(direction=direction)
    # outcome["status"] == "refused" -> GlassReading(status="refused", state=None, message=outcome["message"]).
    # not outcome["found"] -> GlassReading(status="ok", state="unborn", waybill=None, batch_sha=None,
    #     loaded_at=None, message="no waybill has ever loaded for this direction").
    # else: is_today = date(outcome["loaded_at"]) == date(reference_now) (both compared in UTC).
    #   is_today and outcome["batch_sha"] == EMPTY_FILE_SHA256 -> state="failed", message="today's on-time file is empty".
    #   is_today (non-empty) -> state="fresh".
    #   not is_today -> state="stale", message="no drop yet today -- showing the last known waybill"
    #     (the I/O Matrix's "late drop" row generalized past literally "yesterday" to "not today").
    #   Both failed/fresh/stale still carry outcome["waybill"]/["batch_sha"]/["loaded_at"] -- "standup
    #   cites a waybill" holds in every state except unborn/refused.

FLAG_GLASS_EXPORT = "enable_glass_export"
GLASS_EXPORT_FORMATS: tuple[str, ...] = ("csv", "markdown")

def render_glass_table(readings: dict[str, GlassReading], fmt: str) -> str:
    # fmt not in GLASS_EXPORT_FORMATS -> GlassError.
    # rows = [("Standup", readings["standup"]), ("Shipped", readings["shipped"])]
    # fmt == "csv": io.StringIO() + csv.writer (mirror sprint_ledger_query.JiraCSVFormatter,
    #   header ["View", "Direction", "State", "Waybill", "Loaded At (UTC)", "Message"]).
    # fmt == "markdown": pipe-table lines (mirror sprint_ledger_query's MarkdownFormatter/
    #   sync-matrix table-building idiom), same columns, "|---|---|---|---|---|---|" separator.
    # `reading.state or "refused"` / `reading.waybill or ""` / `reading.loaded_at or ""` per row.

def _direction_ok(reading: GlassReading) -> bool:
    return reading.status == "ok" and reading.state != "failed"   # "empty on-time file fails" is the
        # only state this story's own Boundaries call a failure; "stale"/"unborn" are legitimate,
        # non-failing answers ("late drop leaves yesterday stale" is explicitly NOT a fail).

def _glass_result(ok: bool, payload: dict, plain_summary: str, as_json: bool) -> DutyResult:
    # one unified --json/payload-shape helper across every branch, applying 61.2's own review
    # lesson from the start (never unify per-branch after the fact).
    return DutyResult(ok=ok, summary=(json.dumps(payload, indent=2, sort_keys=True) if as_json else plain_summary), details=payload)

class GlassDuty:
    name = "glass"
    def run(self, ns: argparse.Namespace) -> DutyResult:
        # as_json = bool(getattr(ns, "json", False)); verb = getattr(ns, "glass_verb", None).
        # Wrap the whole body in one outer try/except Exception as exc:  # noqa: BLE001 -- duty
        #   boundary -> _glass_result(False, {"message": f"glass failed: {exc}"}, f"glass failed: {exc}", as_json).
        # verb is None (bare): standup = compute_glass_reading(direction="inbound");
        #   shipped = compute_glass_reading(direction="outbound"); payload =
        #   {"standup": asdict(standup), "shipped": asdict(shipped)}; ok = _direction_ok(standup) and
        #   _direction_ok(shipped); plain = f"{_line('standup', standup)} | {_line('shipped', shipped)}"
        #   (a `_line` helper: "refused (message)" when status == "refused", else
        #   f"{label}: {state} waybill={waybill or '-'}" + optional " (message)"); return
        #   _glass_result(ok, payload, plain, as_json).
        # verb == "export": check the flag FIRST (cheaper, gate-before-fetch): overrides =
        #   parse_flag_overrides(getattr(ns, "flag", None)); not eval_flag(FLAG_GLASS_EXPORT, False,
        #   overrides) -> _glass_result(False, {"message": flag_off_message(FLAG_GLASS_EXPORT)},
        #   flag_off_message(FLAG_GLASS_EXPORT), as_json). Else compute both readings, table =
        #   render_glass_table({...}, getattr(ns, "format", "markdown")); _glass_result(True,
        #   {"format": fmt, "table": table}, table, as_json).
        # else: _glass_result(False, {"message": f"glass: unknown verb {verb!r}"}, ..., as_json).
```

**Dashboard module (NEW):** `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/glass_query.py`
— copy `corridor_load.py`'s shape verbatim (lazy `import django` inside the function, `_SETTINGS_UNSET`
constant, `_refused(direction, exc)` helper):
```python
def read_latest_corridor_load(*, direction: str) -> dict:
    # try: import django; from django.apps import apps; from django.conf import settings;
    #   from django.core.exceptions import ImproperlyConfigured; except ImportError as exc: return _refused(...).
    # settings-unset check -> {"status": "refused", "direction": direction, "message": _SETTINGS_UNSET}.
    # try: if not apps.ready: django.setup(); from pyforge.steward.dashboard.models import CorridorLoad
    #   except (ImportError, ImproperlyConfigured) as exc: return _refused(...).
    # from django.db import DataError, OperationalError, ProgrammingError
    # try: row = CorridorLoad.objects.filter(direction=direction).first()  # Meta.ordering does the
    #   "most recent" sort -- no explicit .order_by() needed.
    # except (OperationalError, ProgrammingError, DataError) as exc: return _refused(...).
    # row is None -> {"status": "ok", "direction": direction, "found": False}.
    # else -> {"status": "ok", "direction": direction, "found": True, "waybill": row.waybill,
    #   "batch_sha": row.batch_sha, "loaded_at": row.loaded_at.isoformat()}.
```
No new model, no migration — this is a read-only query over the `CorridorLoad` table 61.1 already
shipped.

**Views (edit existing `dashboard/views_htmx.py`, already django-lazy per its own docstring):**
`standup_htmx_view(request)` (direction="inbound", label "Standup — any news from the vendor?") and
`shipped_htmx_view(request)` (direction="outbound", label "Shipped"), both calling
`glass.compute_glass_reading` and a shared `_render_glass_fragment(reading, title, dom_id) -> str`
helper (pure string-building, `html.escape` on `waybill`/`loaded_at`/`message` — `waybill` is
caller-supplied free text per 61.1, same escaping discipline `backlog_htmx_view` already applies to
every interpolated field) that renders a state badge (fresh/stale/failed green/amber/red,
`refused`/`unborn` grey — mirror `backlog_htmx_view`'s inline `badge_cls` dict idiom) plus the cited
waybill and `loaded_at`. Each view wraps the fragment in `HttpResponse(fragment,
content_type="text/html")` with `response["Cache-Control"] = "no-store"` (django imported lazily
inside each view function, matching this file's existing pattern — no module-level django import
added). No new routing: this package ships no `urls.py` (AD-1); an adopter wires these in
externally, same as `backlog_htmx_view` today.

**CLI wiring (edit existing `cli.py`):**
- `DUTIES` tuple (currently 22, ending `..., "load", "passport"`): append `"glass"` (23rd duty).
  Update the enumerating comment above it with a `glass` line (Epic 61, Story 61.3).
- `_HELP["glass"]`: `"as-of glass -- standup/shipped freshness over the inbound/outbound corridor
  (cites a waybill; empty on-time file fails; late drop leaves yesterday stale; unborn before the
  first waybill); export is a flag-gated CSV/markdown plugin (Story 61.3)"`.
- `build_parser()` elif-chain: add `elif name == "glass": _add_glass_subparsers(duty_parser)` after
  the `passport` branch.
- New `_add_glass_subparsers(glass_parser)` (place near `_add_passport_subparsers`): `--json` on the
  parent only (mirrors `load`/`passport`'s parent-only placement); a subparsers block
  `dest="glass_verb", metavar="{export}"`; one `export` subparser with `--format {csv,markdown}`
  (default `"markdown"`) and a repeatable `--flag NAME=VALUE` (mirrors `_add_ledger_query_subparsers`'s
  identical `--flag` option, reusing `parse_flag_overrides`).
- `resolve_duty()`: add `if name == "glass": from .glass import GlassDuty; return GlassDuty()`.

**Tests (NEW):** `src/shared/packages/pyforge-steward/tests/unit/test_glass.py` — mirror
`test_corridor.py`'s settings-configure race-guard idiom (needs the real migrated `CorridorLoad`
table). Cover: `compute_glass_reading` (bad direction -> `GlassError`; naive `now` -> `GlassError`;
no rows for a direction -> `state="unborn"`, `waybill=None`; a row loaded "today" with a non-empty
`batch_sha` -> `state="fresh"`; a row loaded "today" with `batch_sha == EMPTY_FILE_SHA256` ->
`state="failed"`; a row loaded on an earlier date, none today -> `state="stale"`, citing that row's
waybill — **the I/O Matrix's three required scenarios**; `[dashboard]` extra absent — patch
`sys.modules`/`importlib` to raise `ImportError` — -> `status="refused"`); `render_glass_table`
(csv and markdown shape for both readings; unknown format -> `GlassError`); `GlassDuty.run()` (bare
with both directions fresh -> `ok=True`; bare with one direction `"failed"` -> `ok=False`; export
with the flag off (default) -> `ok=False`, summary names the flag; export with
`--flag enable_glass_export=true` -> `ok=True`, table content present for both csv and markdown;
`--json` on a bare and an export call, both success and failure branches); CLI parsing
(`build_parser().parse_args(["glass"])`, `["glass", "export", "--format", "csv"]`, default format
`"markdown"`).

**Existing tests to edit:**
- `tests/unit/test_cli.py:35-59` (`test_there_are_exactly_twenty_two_duties`): rename to
  `test_there_are_exactly_twenty_three_duties`, append `"glass"` to the tuple.
- `tests/unit/test_cli.py`'s `test_each_duty_dispatches_and_succeeds` exclusion tuple (currently
  ending `..., cutover, passport`): add `"glass"` — a bare `steward glass` needs Django to answer
  (it queries `CorridorLoad`), so in the bare test sandbox (no `DJANGO_SETTINGS_MODULE`) both
  readings come back `status="refused"` and `_direction_ok` is `False` — same posture as
  `passport`'s own bare-refuses exclusion, not `load`'s bare-reports-config-only one.
- `tests/unit/test_restore_duty.py:18` (`assert len(DUTIES) == 22`): update to `23`, extend the
  trailing comment with `+ glass (Story 61.3)`.
- `tests/unit/test_dashboard_admin_and_htmx.py`: add `standup_htmx_view`/`shipped_htmx_view` cases
  mirroring `backlog_htmx_view`'s `RequestFactory` pattern — assert escaped waybill, the state
  badge, `Cache-Control: no-store`, and coverage across `fresh`/`stale`/`failed`/`unborn`/`refused`.
- `tests/meta/test_invariants.py`'s `test_no_module_outside_dashboard_imports_dashboard_django_or_channels`
  (~line 344-473): add a **4th** sanctioned-reach block for `glass.py` -> `"pyforge.steward.dashboard.glass_query"`,
  copying the existing `corridor.py`/`passport.py` blocks' shape exactly.
- `tests/meta/test_invariants.py`'s `test_the_dashboard_module_split_is_pinned_not_merely_documented`
  (~line 543-614): add `"glass_query.py"` to the `documented` set.
- `dashboard/__init__.py`'s module-split docstring: add a "since Story 61.3" clause naming
  `glass_query.py` as a fourth lazy-django-import dashboard module, alongside `passport_sync.py`,
  `corridor_load.py`, and `passport_mint.py`.

## Tasks & Acceptance

**Execution:**
- `glass.py` -- NEW: `GlassError`, `GlassReading`, `compute_glass_reading` (dynamic dashboard reach,
  empty-file-by-hash detection, no-migration design), `render_glass_table` (CSV/markdown), the
  flag-gated `FLAG_GLASS_EXPORT`, `GlassDuty` (bare reports both directions; `export` verb).
- `dashboard/glass_query.py` -- NEW: `read_latest_corridor_load()`, the Django-ORM read-only half
  (lazy `import django`, no lookup mutation, relies on `CorridorLoad.Meta.ordering`).
- `dashboard/views_htmx.py` -- add `standup_htmx_view`, `shipped_htmx_view`, `_render_glass_fragment`.
- `cli.py` -- register the 23rd duty `glass` (`DUTIES`, `_HELP`, `build_parser` elif-chain +
  `_add_glass_subparsers`, `resolve_duty`).
- `tests/unit/test_glass.py` -- NEW, full coverage per Code Map above, including the I/O Matrix's
  three required scenarios (empty-on-time-fails, late-drop-stale, unborn).
- `tests/unit/test_cli.py` -- duty count 22 -> 23, tuple updated, exclusion list updated.
- `tests/unit/test_restore_duty.py` -- `len(DUTIES)` 22 -> 23.
- `tests/unit/test_dashboard_admin_and_htmx.py` -- new `standup_htmx_view`/`shipped_htmx_view` cases.
- `tests/meta/test_invariants.py` -- add the `glass.py` AST assertion (4th sanctioned reach) and the
  `glass_query.py` module-split entry.
- `dashboard/__init__.py` -- docstring updated for the fourth lazy-import dashboard module.

**Acceptance Criteria:**
- Given no `CorridorLoad` row has ever loaded for a direction, when `standup`/`shipped` (or bare
  `steward glass`) reads it, then it reports `state="unborn"` with no waybill cited — never rendered
  as an empty-but-successful reading.
- Given an inbound file loaded today whose content is empty (`batch_sha` equals the SHA-256 of zero
  bytes), when standup reads it, then it reports `state="failed"` and `_direction_ok` is `False`
  (the I/O Matrix's "empty on-time file" row — the one state this story's Boundaries call a fail).
- Given the most recent inbound load happened on an earlier day and nothing has loaded today, when
  standup reads it, then it reports `state="stale"`, still citing that earlier waybill (`yesterday
  remains visible`), and this is NOT treated as a failure.
- Given an inbound file loaded today with real (non-empty) content, when standup reads it, then it
  reports `state="fresh"` citing that waybill.
- Given `pyforge-steward[dashboard]` is not installed, when `compute_glass_reading` or
  `GlassDuty.run()` runs, then it returns `status="refused"` (never a raised `ImportError` escaping
  the duty boundary).
- Given `FLAG_GLASS_EXPORT` is off (the default), when `steward glass export` runs, then it returns
  `ok=False` naming the flag needed to enable it, and no table is produced.
- Given `FLAG_GLASS_EXPORT` is on (`--flag enable_glass_export=true`, env, or `flags.json`), when
  `steward glass export --format csv|markdown` runs, then it returns `ok=True` with a two-row table
  (standup + shipped) in the requested format — the companion doc's "mailed/export of last waybill
  (CSV or markdown) | plugin, available" made real as a switchable, off-by-default plugin, matching
  `corridor.yaml`'s own on/off-transport precedent.

## Spec Change Log

## Review Triage Log

## Design Notes

- **Two views, one glass, one shared function — "do not invent a second standup source of truth."**
  `standup` (inbound: "any news FROM the vendor?") and `shipped` (outbound: what WE have sent) are
  read as the two directions of the *same* `CorridorLoad` idempotency record 61.1 already shipped,
  through one shared `compute_glass_reading(direction=...)` — neither view (nor any future one)
  computes freshness itself. `spec-work-passports-dated-extracts CAP-3`'s own success text
  ("shipped-from-last-inbound; standup cites a...") and the companion doc's Given/When/Then state
  the freshness rule generically (not per-direction), which is what makes one shared function the
  natural reading rather than two independently hand-rolled ones — the reading this story's own
  "Never: do not invent a second standup source of truth" boundary is written to prevent.
- **"Empty" is a zero-byte-file check, not content parsing.** `corridor.py`'s `load_extract` was
  already shipped (61.1) and re-confirmed (61.2) as deliberately content-blind — it hashes the whole
  file and stops there, with "no per-row hook... to extend." Extending it to parse rows would cross
  this story's own declared Surface (the view layer + optional export, not the loader) and reopen an
  already-litigated boundary from two prior stories. Comparing `batch_sha` to the well-known SHA-256
  of zero bytes answers "was the file empty?" with zero new schema and zero loader changes —
  the only reading consistent with what the codebase already, deliberately, does not do.
- **"On time" means "today" (UTC calendar date); "late"/"stale" means "not today."** No cutoff-hour
  or business-day config exists anywhere in this Spec's companion docs or the codebase, and adding
  one would be speculative — the I/O Matrix's own "late drop | file after window" row is fully
  satisfied by the simpler day-boundary reading (a file loaded on a prior day is definitionally
  outside "today's window"). `stale` fires for ANY most-recent load that is not from today, a
  deliberate generalization of the literal example "yesterday" — the rule does not special-case
  exactly one day back.
- **"Their clock and our received clock"** (61.1's Design Notes deferred this exact phrase to CAP-141
  / this story): `loaded_at` (`CorridorLoad`'s `auto_now_add`, "our received clock") drives the
  fresh/stale/failed computation; `waybill` (caller-supplied, "their clock"/label, per 61.1) is only
  ever cited, never used for freshness math — the two clocks are kept deliberately separate.
- **No per-vendor scoping.** `CorridorLoad` carries no `vendor_id` (unlike `WorkPassport`, 61.2);
  v1 runs exactly one vendor and the companion doc states "no second standup pane until on" — adding
  a vendor filter now would be speculative against a schema that cannot yet distinguish vendors on
  this table.
- **Export flag reuses the estate's one flag engine (`sprint_ledger_query.eval_flag`), not a new
  mechanism.** `FLAG_GLASS_EXPORT` is a new flag name, but resolution (override → env → `flags.json`
  → default) is the same four-tier engine `ledger-query`'s formatters already use — SPEC.md's own
  words ("every optional integration sits behind a flag") point at this exact engine, not a bespoke
  corridor-style on/off YAML declaration (that shape fits a fixed enumerable set like transports;
  a single boolean plugin toggle is what the flag engine is already for).
- **"Mailed" stays "export."** The companion doc's "email is an empty slot until enabled" / "v1 does
  not require a mailbox parser" (61.1, already shipped scope) still holds — `glass export` produces
  a CSV/markdown string a human can mail themselves; this story does not send anything over the
  (still-off) email transport.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

**Manual checks:**
- `PYTHONPATH=src/shared/packages/pyforge-steward/src python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_glass.py src/shared/packages/pyforge-steward/tests/unit/test_cli.py src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py src/shared/packages/pyforge-steward/tests/unit/test_dashboard_admin_and_htmx.py src/shared/packages/pyforge-steward/tests/meta/test_invariants.py -q` -- expected: all pass, including the new `glass.py` AST-guard assertion and `test_the_dashboard_module_split_is_pinned_not_merely_documented`.
- `PYTHONPATH=src/shared/packages/pyforge-steward/src python -m pyforge.steward.cli glass` -- like `passport mint` (61.2), this needs a configured `DJANGO_SETTINGS_MODULE`, which a bare shell in this sandbox does not have; expected here is a clean `ok=False` refusal for both directions, never a raised `ImportError`/traceback. The real ORM path (`unborn`/`fresh`/`stale`/`failed`) is exercised and passes under the test suite's migrated in-memory SQLite database (`test_glass.py`), which is where this duty is actually verified end-to-end.
- `pixi run -e pyforge-steward pyforge-steward-coverage-gate` -- expected: `glass.py` and `dashboard/glass_query.py` at or above the station's coverage floor.

