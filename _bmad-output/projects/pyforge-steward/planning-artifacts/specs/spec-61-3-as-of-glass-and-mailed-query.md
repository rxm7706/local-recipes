---
title: '61.3: As-of glass and mailed query'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 1
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
    # validate direction in DIRECTIONS -> GlassError; THEN validate naive `now` -> GlassError
    # (check before binding reference_now -- review pass 1 flagged the reverse order as a
    # fragile validate-after-use pattern, harmless today but worth getting right the first time);
    # only then reference_now = now or datetime.now(timezone.utc).
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
    #   Escape each cell (`waybill`/`message` are caller-supplied free text, Story 61.1):
    #   replace "|" -> "\|" and any newline -> " " before interpolating -- review pass 1 (Edge
    #   Case Hunter): an unescaped "|" or newline in a waybill corrupts the table's column
    #   structure. The CSV branch needs no such escaping -- `csv.writer` already quotes special
    #   characters safely.
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
        #   shipped = compute_glass_reading(direction="inbound")  -- SAME reading, per the
        #   2026-09-19 bad_spec correction: "shipped" sources from inbound, not outbound
        #   (outbound belongs to Story 61.4); payload =
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
`standup_htmx_view(request)` and `shipped_htmx_view(request)` **both** call
`glass.compute_glass_reading(direction="inbound")` — per the 2026-09-19 Spec Change Log amendment,
"shipped" reads the SAME inbound corridor reading as "standup", not `direction="outbound"`
(`docs/dreams/work-passports-dated-extracts.md:45`: "Testers pull a shipped shelf from the last
**inbound** extract"; `direction="outbound"` belongs exclusively to Story 61.4's distinct "signed
outbound slice"). The two views differ only in label/framing, not in data source: `standup_htmx_view`
labels the fragment "Standup — any news from the vendor?" (a process-facing status), `shipped_htmx_view`
labels it "Shipped — what testers can currently rely on" (a testers-facing framing of the identical
as-of fact). Both call a shared `_render_glass_fragment(reading, title, dom_id) -> str` helper (pure
string-building, `html.escape` on `waybill`/`loaded_at`/`message` — `waybill` is caller-supplied free
text per 61.1, same escaping discipline `backlog_htmx_view` already applies to every interpolated
field) that renders a state badge (fresh/stale/failed green/amber/red, `refused`/`unborn` grey —
mirror `backlog_htmx_view`'s inline `badge_cls` dict idiom) plus the cited waybill and `loaded_at`.
Each view wraps the fragment in `HttpResponse(fragment, content_type="text/html")` with
`response["Cache-Control"] = "no-store"` (django imported lazily inside each view function, matching
this file's existing pattern — no module-level django import added). No new routing: this package
ships no `urls.py` (AD-1); an adopter wires these in externally, same as `backlog_htmx_view` today.
`GlassDuty`'s bare invocation follows the same correction: its "shipped" entry also calls
`compute_glass_reading(direction="inbound")`, not `"outbound"`.

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
(csv and markdown shape for both readings, **including one reading with `status="refused"`**
(review pass 1, Blind Hunter) — asserts the `reading.state or "refused"` / `reading.waybill or ""`
fallbacks render correctly; a markdown-branch case with a waybill containing `"|"` and a newline,
asserting the row is escaped and the table stays well-formed (review pass 1, Edge Case Hunter);
unknown format -> `GlassError`); `GlassDuty.run()` (bare with both standup and shipped fresh ->
`ok=True`; bare with the inbound reading `"failed"` -> `ok=False`; **bare with the dashboard extra
forced unavailable -> `ok=False` via the duty layer itself, not only via `compute_glass_reading`
directly** (review pass 1, Verification Gap Reviewer: closes the gap where `_direction_ok`'s
`status == "ok"` guard was previously unexercised at the duty level); export with the flag off
(default) -> `ok=False`, summary names the flag; export with `--flag enable_glass_export=true` ->
`ok=True`, table content present for both csv and markdown; `--json` on a bare and an export call,
both success and failure branches); a small assertion that the four state strings used across
`compute_glass_reading`'s branches are each members of `GLASS_STATES` (review pass 1, Blind Hunter:
keeps the constant from silently drifting from the literals); CLI parsing
(`build_parser().parse_args(["glass"])`, `["glass", "export", "--format", "csv"]`, default format
`"markdown"`). **Both `standup` and `shipped` test fixtures use `direction="inbound"`** — per the
2026-09-19 bad_spec correction, there is no separate "shipped reads outbound" scenario to test;
what needs proving instead is that `standup_htmx_view`/`shipped_htmx_view` (and `GlassDuty`'s two
bare-output entries) read the SAME inbound reading and differ only in label.

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
  badge, `Cache-Control: no-store`. **Both** views need the full `fresh`/`stale`/`failed`/`unborn`/`refused`
  matrix (review pass 1, Blind Hunter: `shipped_htmx_view` originally got only one case) — plus one
  case proving both views render identically from the same inbound fixture, differing only in the
  `title`/`dom_id` label text.
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
- **(Added 2026-09-19, bad_spec amendment)** Given the same inbound `CorridorLoad` state in any of
  `unborn`/`fresh`/`stale`/`failed`/`refused`, when both `standup_htmx_view` and `shipped_htmx_view`
  (or `GlassDuty`'s bare `standup`/`shipped` entries) render it, then both report the identical
  `state`/`waybill`/`loaded_at` — they differ only in label text, never in the direction read or
  the computed state — per the Dream's "shipped shelf from the last inbound extract."

## Spec Change Log

### 2026-09-19 — bad_spec amendment (review pass 1, grouped finding: Blind Hunter #2 + Intent Alignment Auditor)

**Triggering finding:** the Code Map's "Views" section and the Design Notes' "Two views, one
glass" bullet assigned `shipped_htmx_view` to `compute_glass_reading(direction="outbound")`,
reasoning "shipped (outbound: what WE have sent)". This is wrong: `docs/dreams/work-passports-dated-extracts.md:45`
states plainly "Testers pull a **shipped** shelf from the last **inbound** extract, not from a
hunt in a private repo," and `spec-pyforge-steward CAP-141`'s own success text reads
"testers see shipped-from-last-inbound." Both source "shipped" from the INBOUND corridor. The
word "outbound" in this Epic belongs exclusively to **Story 61.4** ("Signed outbound slice",
`spec-work-passports-dated-extracts CAP-4`, `epics.md` Story 61.4) — a distinct, gated,
named-signer mechanism this story must not preempt or collide with by reusing the same
`CorridorLoad.direction` value for an unrelated purpose.

**What was amended:** the Code Map's "Views" section and the Design Notes' "Two views, one
glass" bullet, below, corrected to: both `standup_htmx_view` and `shipped_htmx_view` read
`compute_glass_reading(direction="inbound")` — the same reading, two labeled perspectives for
two audiences (a daily-standup status vs. a testers'-shelf framing), not two directions. The
Tasks & Acceptance section gained an explicit "shipped" Acceptance Criterion (previously every
AC was phrased only in terms of standup/inbound — Blind Hunter #8, folded into this same
amendment since it is the same underlying under-specification).

**Known-bad state avoided:** a "shipped" view that would have perpetually read `"unborn"` in
practice (nothing in this Epic's stories other than 61.4 ever populates an `outbound`
`CorridorLoad` row for this purpose) while silently claiming kinship with Story 61.4's future,
differently-gated outbound mechanism — a genuine "second source of truth" collision the
intent-contract's own Never-boundary exists to prevent, just not the one originally suspected.

**KEEP instructions (must survive re-derivation):** the `glass.py` module shape (`GlassError`,
`GlassReading`, `GLASS_STATES`, the unborn/fresh/stale/failed state machine and its
empty-file-by-hash detection via `EMPTY_FILE_SHA256`, `render_glass_table` CSV/markdown,
`FLAG_GLASS_EXPORT`-gated `GlassDuty` reusing `sprint_ledger_query.eval_flag`); `dashboard/glass_query.py`'s
`read_latest_corridor_load()` (direction-agnostic, unchanged — the bug was in which direction a
caller passed, not in this function); the CLI wiring shape (23rd duty `glass`, `_add_glass_subparsers`,
unified `_glass_result` json/payload helper); the dynamic `importlib.import_module` dashboard-reach
idiom; the AST-guard and module-split meta-test additions; the bulk of `test_glass.py`'s coverage
(only the "shipped"/outbound-specific fixtures need to become inbound-specific, e.g. the module
no longer needs a distinct "shipped reads outbound" test — replace with "both views share one
inbound reading"). Re-derive `standup_htmx_view`/`shipped_htmx_view` and their tests to both use
`direction="inbound"`, with labels distinguishing the two audiences.

## Review Triage Log

### 2026-09-19 — Review pass

- verdicts: 17 findings — high 2, medium 1, low 11, false 3, maybe-false 0
- findings:
  - `[false]` (Blind Hunter) `sprint-status-ledger.yaml`/`epics.md` still read `backlog` for
    `61-3-as-of-glass-and-mailed-query` despite this diff landing the implementation. Refuted:
    per this repo's own convention (AGENTS.md) and 61.1/61.2's own identical, already-litigated
    findings, the spec's internal dev-loop `status` and the ledger's story status are two
    intentionally decoupled tracks — ledger promotion happens via a separate `sprint-ledger-sync`
    step at landing time, never automatically during dev.
  - `[high]` `[bad_spec]` (Blind Hunter, grouped with Intent Alignment Auditor below — same
    defect) `shipped_htmx_view`/the Code Map assign "shipped" to `direction="outbound"`
    ("what WE have sent"), contradicting the Dream's explicit "Testers pull a shipped shelf from
    the last **inbound** extract" and CAP-141's own "testers see shipped-from-last-inbound"; also
    collides with Story 61.4's own, distinct "outbound" territory. Verified directly against
    `docs/dreams/work-passports-dated-extracts.md:45` and `epics.md` Story 61.4. Action: see
    Spec Change Log amendment above; code reverted and re-derived.
  - `[low]` `[reject]` (Blind Hunter, grouped with Edge Case Hunter below — same defect)
    `render_glass_table(readings, fmt)` indexes `readings["standup"]`/`["shipped"]` directly,
    raising a bare `KeyError` for any other dict shape, inconsistent with the function's own
    `GlassError` convention one line earlier for a bad `fmt`. Rejected: unlikely in everyday use
    (the sole caller, `GlassDuty.run()`'s `export` branch, always constructs this dict correctly)
    and the fix (a key-existence guard) is more than a direct correction — meets both prongs of
    the low-rejection rule.
  - `[low]` `[reject]` (Blind Hunter) `GlassDuty.run()`'s final `else` branch (unknown
    `glass_verb`) is unreachable via the CLI — `_add_glass_subparsers` registers only `export`
    under `dest="glass_verb"`, so argparse itself rejects any other verb before `run()` is
    called — and untested. Rejected: matches 61.1/61.2's own already-litigated identical
    "defensive/outer branch untested" findings (unlikely to be met in everyday use — only
    reachable via a hand-built `Namespace` bypassing the CLI parser, not how any real caller
    invokes a duty); the station coverage floor cited as at-risk is not actually violated
    (`glass.py` measured 93% against an 80% floor).
  - `[low]` `[patch→moot]` (Blind Hunter) `GLASS_STATES` is declared but never referenced except
    in a docstring; the four literal state strings used across `compute_glass_reading`'s branches
    could silently drift from it. Verified: real but purely cosmetic (nothing validates against
    `GLASS_STATES` at runtime, so drift would not break behavior, only accuracy). Action would be
    a small test asserting the four literals are members of `GLASS_STATES` — moot this pass: a
    `bad_spec` finding exists below, so this patch is deferred to the re-derivation.
  - `[low]` `[patch→moot]` (Blind Hunter) No test renders `render_glass_table` with a `"refused"`
    `GlassReading` (the export path's `reading.state or "refused"` / `reading.waybill or ""`
    fallbacks are unexercised). Verified real by reading `test_render_glass_table_*`. Moot this
    pass (bad_spec exists); re-derivation should add this case alongside the corrected
    standup/shipped tests.
  - `[low]` `[patch→moot]` (Blind Hunter) `shipped_htmx_view` gets only one test (`fresh`) versus
    `standup_htmx_view`'s full `fresh`/`stale`/`failed`/`unborn`/`refused` matrix, short of the
    Code Map's own stated plan. Verified real by reading `test_dashboard_admin_and_htmx.py`.
    Subsumed by the bad_spec re-derivation above (the "shipped" view's tests are being rewritten
    to match the corrected `direction="inbound"` reading and should gain the same state matrix
    `standup_htmx_view` already has).
  - `[low]` `[bad_spec]` (Blind Hunter) Every Acceptance Criterion is phrased exclusively in terms
    of "standup"/inbound; none states an equivalent criterion for "shipped"/outbound (or, after
    correction, shipped/inbound), even though `compute_glass_reading` is shared and symmetric.
    Verified real by reading the spec's own `## Tasks & Acceptance`. Folded into the same
    Spec Change Log amendment as the grouped `high` finding above (same root cause: "shipped" was
    under-specified in this spec from the start) — a new AC for "shipped" is added there rather
    than as a separate loopback.
  - `[low]` `[patch→moot]` (Blind Hunter) In `compute_glass_reading`, `reference_now` is computed
    from `now` before the naive-`now` check runs, so a naive `now` is briefly bound before being
    rejected on the very next line — harmless today, but a fragile validate-after-use ordering.
    Verified: no actual bad outcome occurs (the raise fires immediately after, before
    `reference_now` is used for anything). Low, moot this pass; a two-line reorder during
    re-derivation is free to include but not required.
  - `[false]` (Blind Hunter) The spec's own Code Map pseudocode for `compute_glass_reading` omits
    the exact `datetime.fromisoformat(...).astimezone(...)` mechanism the shipped code uses, and
    `## Spec Change Log` was empty despite this "divergence." Refuted: the Code Map is explicitly
    agent-guiding pseudocode/investigation notes (per this project's own `spec-template.md`
    header comment), not literal exact code — implementation-detail refinement during step-03 is
    expected, not a spec defect. `## Spec Change Log` is documented as populated only by a
    step-04 `bad_spec` loopback (which had not yet occurred when this finding was filed), so its
    emptiness before this pass's own loopback was correct, not evidence of anything.
  - `[low]` `[reject]` (Edge Case Hunter) `glass.py`'s date comparison assumes `loaded_at` is
    always timezone-aware; a hypothetical Django project configured with `USE_TZ=False` would
    make it naive, and `.astimezone(timezone.utc)` on a naive value silently assumes host-local
    time rather than raising. Rejected: every `settings.configure(...)` call across this
    package's own test suite and established convention sets `USE_TZ=True` unconditionally
    (Django's own post-4.0 default too), so an adopter would need to deliberately misconfigure
    against every existing precedent in this package; the fix (a defensive naive-`loaded_at`
    guard) adds a new guard — meets both prongs of the low-rejection rule.
  - `[low]` `[reject]` (Edge Case Hunter, grouped with Blind Hunter above — same defect) Same
    `render_glass_table` unguarded-dict-access claim as Blind Hunter's finding above; same
    refutation and rejection.
  - `[low]` `[reject]` (Edge Case Hunter) `dashboard/glass_query.py`'s ORM-error catch
    (`DataError, OperationalError, ProgrammingError`) does not also catch
    `InterfaceError`/`IntegrityError`/`InternalError`. Rejected on the same grounds as 61.1's own
    identical, already-litigated finding against `corridor_load.py`'s equivalent catch: widening
    the exception set without a demonstrated real trigger is more than the smallest fix, and the
    risk profile (an uncaught ORM exception surfacing as a 500 from an HTMX view with no
    try/except) is identical to this same file's own pre-existing, unremediated
    `backlog_htmx_view` — not a regression this story introduces.
  - `[false]` (Edge Case Hunter) `read_latest_corridor_load` does not validate `direction` before
    querying, so an invalid direction could be masked as `found=False`/"unborn" instead of
    surfacing a caller bug. Refuted: this function's sole production caller,
    `compute_glass_reading`, already validates `direction in DIRECTIONS` and raises `GlassError`
    before ever calling `read_latest_corridor_load` — an invalid direction can never reach this
    function through the sanctioned path; only test code calls it directly, always with a valid
    direction.
  - `[low]` `[patch→moot]` (Edge Case Hunter) The markdown export branch of `render_glass_table`
    does not escape `|` or newlines in caller-supplied `waybill`/`message` text (unlike the CSV
    branch, which `csv.writer` already escapes safely for free) — a waybill containing either
    would corrupt the exported table's column structure. Verified real: `waybill` is established
    (Story 61.1) as free-form, caller-supplied text with no character restriction. Moot this pass
    (bad_spec exists); action for re-derivation: escape `|`/newlines in the markdown branch's cell
    values.
  - `[medium]` `[patch→moot]` (Verification Gap Reviewer, pre-verified) No test forces a
    `status="refused"` reading through `GlassDuty.run()` itself (every `GlassDuty` test in
    `test_glass.py` runs inside the file's fully Django-configured context, and `test_cli.py`'s
    `test_each_duty_dispatches_and_succeeds` explicitly excludes `"glass"`), so `_direction_ok`'s
    `reading.status == "ok"` guard is unexercised at the duty level — a plausible future
    simplification of `_direction_ok` (dropping that guard) would make `GlassDuty` silently report
    `ok=True` for a completely unreachable data source, and nothing in the suite would catch it.
    Accepted as filed (verification-gap findings arrive pre-verified). Moot this pass (bad_spec
    exists); action for re-derivation: add a `GlassDuty`-level test that forces a refusal (mirror
    `test_compute_glass_reading_refused_when_dashboard_extra_not_importable`'s technique) and
    asserts `result.ok is False`.
  - `[high]` `[bad_spec]` (Intent Alignment Auditor, grouped with Blind Hunter above — same
    defect) Independently, reading the diff against the Dream's own text, the auditor identified
    the identical divergence: "shipped" is implemented as `direction="outbound"` ("what WE have
    sent"), while the Dream states "Testers pull a shipped shelf from the last inbound extract" —
    the opposite source. Same verification and same action as the grouped Blind Hunter row above.
- Intent Alignment Auditor's broader report also noted two other, non-actionable divergences it
  explicitly framed as reasonable/self-documented rather than defects: (1) "stale" generalizes the
  I/O Matrix's literal "yesterday" example to "any non-today load" — already explicitly documented
  and justified in this spec's own Design Notes; (2) "mailed" narrows to "export only, no send" —
  already explicitly documented and justified in this spec's own Design Notes, citing Story 61.1's
  established "email is an empty slot until enabled" scope. Neither is logged as a separate
  finding above since the auditor did not file either as an unresolved gap.

### 2026-09-19 — Review pass (2, post bad_spec re-derivation)

- verdicts: 16 findings — high 0, medium 2, low 12, false 2, maybe-false 0
- findings:
  - `[low]` `[patch]` (Blind Hunter, grouped with Verification Gap Reviewer below — same defect)
    `_HELP["glass"]` still reads "standup/shipped freshness over the inbound/outbound corridor,"
    stale wording left over from before the direction fix — `glass` now only ever reads
    `direction="inbound"`. Verified by reading `cli.py`. Action: reword to drop "outbound".
  - `[false]` (Blind Hunter) `GlassDuty.run()`'s `export` branch returns `ok=True` on a successful
    render regardless of the underlying readings' health (unlike bare's `_direction_ok`-gated
    `ok`), so scripting off `export`'s `ok` field could miss a `refused`/`failed` reading. Refuted:
    this spec's own Acceptance Criteria explicitly define export's `ok=True` as "a table was
    rendered," a deliberately different, and equally valid, contract from bare's "is the data
    healthy" — a report legitimately needs to render and be mailed even when it says "today's file
    is empty" or "the system is currently refused"; that is the point of an export/mail plugin.
  - `[medium]` `[patch]` (Blind Hunter, grouped with Edge Case Hunter below — same defect) Both the
    bare and `export` branches of `GlassDuty.run()` call `compute_glass_reading(direction="inbound")`
    **twice** — once for `standup`, once for `shipped` — two independent reads for what the Design
    Notes and a dedicated test both assert is "the SAME reading." A `CorridorLoad` write landing
    between the two calls lets `standup` and `shipped` diverge, eroding the very "do not invent a
    second standup source of truth" invariant this story exists to protect. Verified by reading
    `GlassDuty.run()`. Action: compute the inbound reading once, reuse it for both labels.
  - `[low]` `[reject]` (Blind Hunter) A `CorridorLoad` row whose `batch_sha == EMPTY_FILE_SHA256`
    but loaded on a prior day (not today) classifies as `stale`, and the stale message ("showing
    the last known waybill") reads oddly when that waybill's content was itself empty. Rejected:
    this is the explicitly-scoped, already-documented behavior (the empty-file check applies only
    to today's citation per this spec's own Design Notes; a stale historical waybill is cited
    as-is, never re-validated) — a genuinely rare compound edge case, and any fix (a distinct
    sub-state or reworded message) adds new branches/complexity for a case unlikely to be met in
    everyday use.
  - `[low]` `[reject]` (Blind Hunter) The spec's own `## Verification` → "Manual checks" section
    still says "a clean `ok=False` refusal for both directions," leftover wording from before the
    direction fix (there is now one direction, read twice, under two labels). Rejected per this
    workflow's own rule: a finding whose only fix is editing this build's spec is rejected outright.
  - `[low]` `[patch]` (Blind Hunter) `dashboard/glass_query.py` uses `typing.Dict`/`Any` while the
    sibling `glass.py` added in this same story consistently uses builtin generics (`dict[str, ...]`)
    under the same `from __future__ import annotations` — an avoidable style inconsistency
    introduced within one change. Action: use `dict`/`Any` builtin-generic style in `glass_query.py`
    to match `glass.py`.
  - `[low]` `[patch]` (Blind Hunter) `_GLASS_BADGE_CLS` has no entry for `unborn`, so it falls
    through to the same grey used for `refused` — two very different situations (benign
    never-happened vs. the system itself couldn't answer) render with the same badge color, and
    "unborn" is a state a fresh install will show on day one, not a rare corner case. Verified by
    reading `_render_glass_fragment`. Action: add a distinct color for `unborn`.
  - `[carried]` `[low]` `[reject]` (Blind Hunter) Same claim as review pass 1's grouped
    Blind-Hunter/Edge-Case-Hunter finding: `standup_htmx_view`/`shipped_htmx_view` call
    `compute_glass_reading` with no `try/except`, and `glass_query.py`'s ORM-error catch is
    narrower than the full exception surface a live DB could raise. Code still reads as that row
    describes (unchanged in this regard). Same verdict and route stand: matches this same file's
    own pre-existing, unremediated `backlog_htmx_view` posture — not a regression this story
    introduces.
  - `[false]` (Blind Hunter) No test exercises the freshness rule's day-boundary right at UTC
    midnight, only clearly-fresh/clearly-stale fixtures. Refuted: the freshness rule is a pure
    `.date()` equality comparison with no `<`/`<=` range arithmetic or `timedelta` offset math —
    the class of bug a near-boundary test would catch (an off-by-one in a range or offset
    calculation) does not exist in this code path; a boundary-specific test would exercise the
    identical comparison the existing `days_ago=0`/`days_ago=2` fixtures already do.
  - `[low]` `[patch]` (Blind Hunter) `test_glass_duty_bare_dashboard_extra_unavailable_is_not_ok_via_duty_layer`
    asserts only `result.details["standup"]["status"] == "refused"`, never checking that `shipped`
    mirrors the same refusal — a symmetry gap in an otherwise carefully paired test suite. Verified
    by reading the test. Action: add the matching `shipped` assertion.
  - `[carried]` `[low]` `[reject]` (Edge Case Hunter) Same claim as review pass 1's grouped finding:
    `render_glass_table(readings, fmt)` indexes `readings["standup"]`/`["shipped"]` directly,
    raising a bare `KeyError` for any other dict shape. Code still reads as that row describes.
    Same verdict and route stand.
  - `[low]` `[reject]` (Edge Case Hunter) `dashboard/glass_query.py`'s `django.setup()` call is
    guarded only by `except (ImportError, ImproperlyConfigured)`; a hypothetical re-entrant-populate
    `RuntimeError` from Django's own `apps.populate()` guard would escape uncaught. Rejected:
    this exact shape is copied verbatim from the already-shipped, already-reviewed sibling
    `corridor_load.py`/`passport_mint.py`/`passport_sync.py` idiom this story's own Code Map
    directed it to mirror — the same theoretical gap already exists identically in three other
    files, so widening it here alone (without touching the other three) is inconsistent and more
    than the smallest fix for a race that requires calling this synchronous, single-threaded path
    concurrently with itself.
  - `[low]` `[reject]` (Edge Case Hunter) `loaded_at_dt` is only converted via `.astimezone(timezone.utc)`
    when it is already timezone-aware; a naive value (a Django project configured `USE_TZ=False`)
    is compared via its own naive `.date()` with no defensive guard. Verified the code no longer
    risks the specific pass-1 concern (silently assuming host-local time via an unconditional
    `.astimezone()` call on a naive value — that call is now conditional on `tzinfo is not None`).
    Rejected on the same grounds as pass 1's identical finding: every settings.configure precedent
    in this package fixes `USE_TZ=True`, so the naive branch is unreachable without a deliberate
    misconfiguration against established convention, and a defensive raise adds a new guard for an
    unmet condition.
  - `[medium]` `[patch]` (Edge Case Hunter, grouped with Blind Hunter above — same defect) Same
    TOCTOU claim: `standup`/`shipped` are each fetched via their own independent
    `compute_glass_reading(direction="inbound")` call rather than one shared result. Same
    verification and same action as the grouped Blind Hunter row above.
  - `[low]` `[patch]` (Verification Gap Reviewer, "Other findings" — not itself a verification gap;
    grouped with Blind Hunter above — same defect) Same `_HELP["glass"]` stale-wording claim.
    Verified true by reading `cli.py`. Same action as the grouped Blind Hunter row above. The
    layer's core brief reported "No verification gaps found."
- Intent Alignment Auditor filed no discrete actionable finding this pass. Its report raised a
  more fundamental question — whether the literal intent-contract text alone (given to it in
  isolation) supports a two-entity "standup + shipped" surface at all, versus a single "standup"
  surface — and noted the two-entity structure enters via material outside that narrow contract
  (the Dream, CAP-141's success text). Resolved by this orchestrator, not the auditor (whose brief
  is strictly descriptive): the story's own `## Binding` → `Surface:` line ("existing app views
  standup and shipped"), sourced directly from `epics.md`'s Story 61.3 definition, authorizes the
  two-view surface independently of the `<intent-contract>` tag — that Binding section is, by this
  project's own spec-template convention, deliberately kept outside `<intent-contract>` while
  still being load-bearing scope. Not an intent gap: the auditor was given only the narrower
  contract by design, and the fuller scope it flagged as "external" is in fact the story's own
  authoritative Surface declaration, not an invented addition.

## Design Notes

- **Two views, one glass, ONE reading — "do not invent a second standup source of truth."**
  **Corrected 2026-09-19 (bad_spec, review pass 1):** `standup` and `shipped` are NOT two
  directions of the corridor — both read `compute_glass_reading(direction="inbound")`, the exact
  same reading. The Dream (`docs/dreams/work-passports-dated-extracts.md:45`) states "Testers pull
  a shipped shelf from the last **inbound** extract," and `spec-pyforge-steward CAP-141`'s own
  success text ("testers see shipped-from-last-inbound") sources "shipped" from inbound too;
  `direction="outbound"` belongs exclusively to Story 61.4's distinct, gated "signed outbound
  slice" (`spec-work-passports-dated-extracts CAP-4`) and must not be reused here. The two views
  differ only in label/framing for two audiences (a process-facing "any news from the vendor?"
  status vs. a testers-facing "what can I currently rely on?" shelf), never in data source or
  computation — neither view (nor any future one) computes freshness itself. This is what "do not
  invent a second standup source of truth" actually protects: not just "don't duplicate storage,"
  but "don't let two views silently diverge on what they're even reading."
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
- `PYTHONPATH=src/shared/packages/pyforge-steward/src python -m pyforge.steward.cli glass` -- like `passport mint` (61.2), this needs a configured `DJANGO_SETTINGS_MODULE`, which a bare shell in this sandbox does not have; expected here is a clean `ok=False` refusal for both readings, never a raised `ImportError`/traceback. The real ORM path (`unborn`/`fresh`/`stale`/`failed`) is exercised and passes under the test suite's migrated in-memory SQLite database (`test_glass.py`), which is where this duty is actually verified end-to-end.
- `pixi run -e pyforge-steward pyforge-steward-coverage-gate` -- expected: `glass.py` and `dashboard/glass_query.py` at or above the station's coverage floor.

## Auto Run Result

Status: done
Blocking condition: none

**Summary of implemented change.** Standup ("any news from the vendor?") and shipped ("what
testers can currently rely on") now share one as-of glass over the inbound corridor
(`CorridorLoad`, Story 61.1): a new `steward glass` CLI duty (the 23rd) and two new HTMX views
(`standup_htmx_view`, `shipped_htmx_view`) both read the SAME `compute_glass_reading(direction="inbound")`
result — computed once per invocation and reused for both labels, never two independent reads —
and classify it as `unborn` (nothing has ever loaded), `fresh` (today's non-empty drop), `stale`
(the last drop was not today — "yesterday remains visible", generalized to any non-today load),
or `failed` (today's drop is a zero-byte file, detected by comparing `batch_sha` against the
well-known SHA-256 of empty bytes — no new schema, no `corridor.py` change). A mailed/export
plugin (`steward glass export --format csv|markdown`) renders the same two-row table, gated
off-by-default behind `FLAG_GLASS_EXPORT` via the estate's existing `sprint_ledger_query.eval_flag`
engine. **A significant mid-flight correction:** the first implementation pass wired `shipped` to
`direction="outbound"` ("what WE have sent"); review caught (independently, via two reviewer
layers) that this contradicted the owning Dream's explicit "Testers pull a shipped shelf from the
last **inbound** extract" and collided with Story 61.4's own, separate "signed outbound slice"
territory. The spec was corrected (`## Spec Change Log`), code reverted to baseline, and
re-derived from the corrected spec — `shipped` now reads inbound, same as standup, differing only
in label/framing for two audiences.

**Files changed.**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/glass.py` (NEW) — `GlassError`,
  `GlassReading`, `GLASS_STATES`, `EMPTY_FILE_SHA256`, `compute_glass_reading` (direction
  validated before the naive-`now` check, which is validated before `reference_now` is bound),
  `render_glass_table` (CSV/markdown, with `|`/newline escaping in the markdown branch),
  `FLAG_GLASS_EXPORT`-gated `GlassDuty` (bare computes the inbound reading once and reuses it for
  both `standup`/`shipped` labels; `export` verb does the same).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/glass_query.py` (NEW) —
  `read_latest_corridor_load()`, the read-only Django-ORM half (lazy `import django`, builtin
  `dict[str, Any]` generics, relies on `CorridorLoad.Meta.ordering`).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/views_htmx.py` — added
  `standup_htmx_view`, `shipped_htmx_view` (both read the same inbound reading), and
  `_render_glass_fragment` with a `_GLASS_BADGE_CLS` giving `unborn` its own distinct color
  (separate from `refused`'s default grey).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — registered the 23rd duty
  `glass` (`DUTIES`, `_HELP` — now correctly saying "inbound corridor", `build_parser` elif-chain +
  `_add_glass_subparsers`, `resolve_duty`).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/__init__.py` — module-split
  docstring names `glass_query.py` as the fourth lazy-django-import dashboard module.
- `src/shared/packages/pyforge-steward/tests/unit/test_glass.py` (NEW, 36 tests) — the state
  machine (including the I/O Matrix's three required scenarios), `render_glass_table` (including a
  `refused` reading and a `|`/newline-in-waybill escaping case), `GlassDuty.run()` (including a
  refusal forced through the duty layer itself, asserting both `standup` and `shipped` mirror it),
  `glass_query.py`'s own refusal branches, a `GLASS_STATES` self-check, and CLI parsing.
- `src/shared/packages/pyforge-steward/tests/unit/test_cli.py`,
  `tests/unit/test_restore_duty.py` — duty count 22 → 23.
- `src/shared/packages/pyforge-steward/tests/unit/test_dashboard_admin_and_htmx.py` — full
  `fresh`/`stale`/`failed`/`unborn`/`refused` matrix for both views, plus a test proving they
  render identically from one shared reading.
- `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` — the 4th sanctioned
  dashboard-reach AST guard (`glass.py` → `glass_query.py`), `glass_query.py` added to the pinned
  module-split set.
- This spec — planned, reviewed (2 passes), one `bad_spec` amendment, patched, re-verified.

**Review findings breakdown** (33 findings total across two review passes; every row in
`## Review Triage Log`).
- **Pass 1** (17 findings: high 2, medium 1, low 11, false 3) surfaced the direction bug as a
  grouped `high` `bad_spec` finding (Blind Hunter + Intent Alignment Auditor, independently, both
  citing the Dream's "shipped shelf from the last inbound extract") plus a related `low` `bad_spec`
  finding (missing "shipped" Acceptance Criteria). Code was reverted to baseline and re-derived
  from the corrected spec — see `## Spec Change Log`. The remaining pass-1 findings (5 `low`
  `patch`-routed, 1 `medium` `patch`-routed from the Verification Gap Reviewer) were folded
  directly into the corrected spec's Code Map/Tests plan rather than patched separately (rule:
  once `bad_spec` exists, lower entries are moot for that pass) — all five landed in the
  re-derivation: a `GLASS_STATES` self-check test, a `render_glass_table`-with-`refused` test,
  markdown `|`/newline escaping, a naive-`now` validation reorder, and a `GlassDuty`-level refusal
  test. 3 `false` (ledger/epics.md decoupling — already-litigated per AGENTS.md; a Code-Map-vs-code
  pseudocode "divergence" that misunderstood the Code Map's own documented role; an
  unreachable-without-bypassing-the-CLI direction-validation claim). 5 `low` `reject` (an unguarded
  `render_glass_table` dict access unlikely to be hit by its sole, correct caller; an unreachable
  CLI-verb `else` branch matching 61.1/61.2's own already-litigated precedent; a hypothetical
  `USE_TZ=False` naive-datetime risk against a package-wide `USE_TZ=True` convention; an ORM
  exception set matching `corridor_load.py`'s own already-shipped, already-reviewed set).
- **Pass 2** (16 findings: medium 2 grouped as 1, low 12, false 2), run fresh against the
  re-derived diff: the TOCTOU gap the re-derivation introduced (two independent
  `compute_glass_reading` calls where one shared reading was intended) was independently caught by
  both Blind Hunter and Edge Case Hunter and patched (compute once, alias both labels) — the one
  `medium`-severity patch this pass. 4 more `low` patches: stale `_HELP` wording still saying
  "inbound/outbound" (also independently flagged by the Verification Gap Reviewer), a
  `typing.Dict`/builtin-`dict` style inconsistency between the two new modules, `_GLASS_BADGE_CLS`
  conflating `unborn` with `refused`, and a test asserting only `standup`'s (not `shipped`'s)
  refusal. 2 `false` (export's `ok` deliberately means "table rendered", not "data healthy" — the
  spec's own AC already says so; no boundary-arithmetic bug class exists for a pure `.date()`
  equality check, so a midnight-boundary test would prove nothing new). 5 `low` `reject`: 2
  `carried` from pass 1 (the `render_glass_table` KeyError and the ORM-exception-set/unguarded-view
  claims — code unchanged, same verdict stands), a spec-prose-only wording fix rejected per the
  "never patch this build's own spec" rule, a `django.setup()` exception-set gap matching three
  sibling dashboard modules' identical, already-shipped shape, and the naive-`loaded_at` claim
  re-verified against the now-changed (safer) conditional-`astimezone` code and still judged
  unreachable under this package's `USE_TZ=True` convention.
- The Intent Alignment Auditor filed no discrete actionable finding in either pass. Pass 1's
  broader report independently corroborated the direction bug (logged as part of the grouped
  `bad_spec` entry). Pass 2's broader report raised whether the intent-contract text alone
  supports a two-view "standup + shipped" surface at all — resolved by this orchestrator: the
  story's own `## Binding` → `Surface:` line (from `epics.md`'s Story 61.3 definition) authorizes
  it independently of the narrower `<intent-contract>` tag the auditor is deliberately scoped to.

**Follow-up review recommendation: `false`.** This is a first pass by the frontmatter's own
`followup_pass` marker (this dispatch never resumed a `done` spec). The `bad_spec` loopback that
resolved the direction bug is not itself a "patched" entry under the computation rule. In the
final (pass 2) review, exactly one `medium`-severity entry was patched (the TOCTOU fix) and no
`high` — below the "two-or-more medium, or any high" threshold for recommending a follow-up. The
one component of this story genuinely unverified by a fresh review layer is the TOCTOU fix itself
(computing the reading once and aliasing both labels) — verified here by re-reading the code and
re-running the full suite, but not by a third independent review pass.

**Verification performed.**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` (the dispatch's configured verify,
  real env): 1534 passed / 4 skipped (pass-1 implementation) → 1540 passed / 4 skipped (pass-2
  re-derivation, before and after the 5-item patch) — independently re-run by this orchestrator at
  every stage, not just from the implementation subagents' own reports.
- `pixi run -e pyforge-steward pyforge-steward-coverage-gate`: OK at every stage; final state
  `glass.py` 95%, `dashboard/glass_query.py` 94%, both well above the 80% floor; 27/27 touched
  modules ≥ 80%.
- Manual CLI smoke check (`PYTHONPATH=... python -m pyforge.steward.cli glass`, bare shell, no
  `DJANGO_SETTINGS_MODULE`): confirmed a clean `refused` message for both `standup` and `shipped`,
  exit 1, no traceback — matches the spec's own stated expectation, re-confirmed after the patch
  pass.
- Matrix Test Audit: the I/O Matrix's three rows (empty-on-time-file, late drop, before first
  waybill) are covered by `test_compute_glass_reading_failed_for_an_empty_todays_load`,
  `test_compute_glass_reading_stale_when_last_load_was_not_today`, and
  `test_compute_glass_reading_unborn_before_first_waybill` — independently re-run and confirmed
  passing (`test_glass.py -q`: 35 passed before the patch pass).
- Diff read in full by this orchestrator at every stage (pre-`bad_spec` diff, post-re-derivation
  diff, post-patch diff), not merely summarized from any implementation subagent's own report, per
  step-03/04's "judge against the diff" instruction.

**Residual risks.**
- No ledger/PR mechanics were run: `sprint-status-ledger.yaml`/`epics.md` still read `backlog` for
  `61-3-as-of-glass-and-mailed-query` (ledger promotion via `sprint-ledger-sync`, and any PR/label
  mechanics, are a separate step per AGENTS.md from this single-story `bmad-build-auto` dispatch);
  this PR (once opened) touches only non-`recipes/` paths and needs the `maintenance` label; no
  `pixi.toml` change was made, so `pr-preflight`/the shared-surface station-test rule does not
  apply.
- No wiring exists from an actual outbound "signed slice" (Story 61.4, not yet built) into this
  glass — by design; `direction="outbound"` remains untouched by this story and is reserved for
  61.4 alone, per this dispatch's own corrected Design Notes.
- The TOCTOU fix (single read, aliased to both labels) removes the specific divergence risk
  pass-2's reviewers found, but has not itself been re-reviewed by a fresh pass (see the follow-up
  recommendation note above) — judged low-risk given its small, direct, easily-verified shape.

