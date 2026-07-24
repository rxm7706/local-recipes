"""Unit tests -- per-component + Python-runtime currency verdicts (Story
6.3): the tier ladder (bundled LTS registry -> cached endoflife.date ->
unknown), reason-token precedence (eol > over-lag > unknown), the
``!python-runtime`` sentinel, ``Finding``/id construction, and the hard
``currency_rung`` warn-cap. Also covers ``CurrencyEngine``'s thin
coverage-and-``EngineResult`` wrapper. Mirrors ``test_license.py``'s style.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pyforge.warden import feeds
from pyforge.warden.currency import (
    DEFAULT_CURRENCY_POLICY,
    _as_date,
    _best_match,
    _classify,
    _load_registry,
    _normalize_name,
    _registry_alias_index,
    _Resolution,
    _resolve,
    _resolve_from_cycles,
    _resolve_from_lines,
    currency_findings,
    currency_rung,
)
from pyforge.warden.engines import CurrencyEngine
from pyforge.warden.inventory import ResolvedInventory, merge_components
from pyforge.warden.models import (
    AXIS_CURRENCY,
    CurrencyInfo,
    CurrencyVerdict,
    Ecosystem,
    Finding,
    ScannedManifest,
    Status,
    StatusDriver,
)

_NOW = datetime(2026, 7, 23, tzinfo=UTC)
MANIFEST = ScannedManifest(path="pyproject.toml", kind="pyproject.toml")


def _pin_cache_mtime_to_now(cache_dir) -> None:
    """Pin a just-written endoflife cache file's mtime to ``_NOW`` so a
    test that passes the fixed ``_NOW`` stays deterministic: ``feeds.
    is_feed_stale`` treats a FUTURE-dated snapshot (a real wall-clock
    mtime vs. the pinned ``now``) as stale, never fresh — without this,
    the cache the test just provisioned would be silently skipped as
    tier-2 input (review finding, 2026-07-23)."""
    path = feeds.endoflife_cache_path(cache_dir)
    timestamp = _NOW.timestamp()
    os.utime(path, (timestamp, timestamp))


# --- currency_rung (the hard warn-cap) ---------------------------------------


@pytest.mark.parametrize(
    ("reason", "verdict"),
    [
        ("eol", CurrencyVerdict.EOL),
        ("over-lag", CurrencyVerdict.SUPPORTED),
        ("unknown", CurrencyVerdict.UNKNOWN),
    ],
)
def test_currency_rung_is_always_warn(reason, verdict):
    finding = Finding(
        id=f"currency:{reason}:pkg@1.0.0",
        axis=AXIS_CURRENCY,
        message="m",
        subject="pkg",
        severity=None,
        currency=CurrencyInfo(verdict=verdict, latest="1.0.0", lag=0, eol_date="2099-01-01")
        if reason != "unknown"
        else CurrencyInfo(verdict=verdict),
    )
    status, driver = currency_rung(finding)
    assert status is Status.WARN
    assert driver == StatusDriver(axis=AXIS_CURRENCY, finding_id=finding.id)


def test_default_currency_policy_covers_only_finding_eligible_verdicts():
    """Mirrors ``DEFAULT_LICENSE_POLICY``'s omission of ``allowed`` --
    ``supported`` is deliberately absent (see ``currency.py``'s module
    docstring: it can mean either clean or over-lag, a distinction this
    table can't make by verdict alone)."""
    assert dict(DEFAULT_CURRENCY_POLICY) == {
        CurrencyVerdict.EOL: Status.WARN,
        CurrencyVerdict.UNKNOWN: Status.WARN,
    }


# --- _normalize_name / _as_date / _best_match --------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Django", "django"),
        ("some_backported_lib", "some-backported-lib"),
        ("  Requests  ", "requests"),
    ],
)
def test_normalize_name(raw, expected):
    assert _normalize_name(raw) == expected


def test_as_date_accepts_yaml_date_object():
    import datetime as dt

    assert _as_date(dt.date(2026, 1, 1)) == dt.date(2026, 1, 1)


def test_as_date_accepts_iso_string():
    import datetime as dt

    assert _as_date("2026-01-01") == dt.date(2026, 1, 1)


def test_as_date_none_on_unparsable():
    assert _as_date("not-a-date") is None
    assert _as_date(None) is None
    assert _as_date(42) is None


def test_best_match_prefers_the_longest_prefix():
    import datetime as dt

    entries = [("6", dt.date(2020, 1, 1), None), ("6.1", dt.date(2023, 1, 1), None)]
    assert _best_match(entries, "6.1.5") == 1


def test_best_match_none_when_nothing_matches():
    import datetime as dt

    entries = [("6.1", dt.date(2023, 1, 1), None)]
    assert _best_match(entries, "7.0.0") is None


def test_best_match_exact_version_equals_identifier():
    import datetime as dt

    entries = [("2.31.0", dt.date(2023, 1, 1), None)]
    assert _best_match(entries, "2.31.0") == 0


def test_best_match_tie_prefers_the_first_entry_in_the_date_sorted_order():
    """An exact length tie between two matching identifiers: the first one
    encountered in ``entries`` wins (a strict ``>``, never ``>=``). Two
    DIFFERENT identifiers of equal length can't both prefix-match the same
    concrete version string, so the tie is constructed the way it actually
    arises in practice -- a data-quality edge in the source registry/feed
    (a duplicated identifier, e.g. two ``lts_lines``/cycle entries both
    named ``"6.1"``) -- both real callers pre-sort ``entries`` ascending by
    release date, so index 0 (the OLDER entry) winning is the documented
    behavior."""
    import datetime as dt

    entries = [
        ("6.1", dt.date(2020, 1, 1), None),  # older -- first, and wins the tie
        ("6.1", dt.date(2023, 1, 1), None),  # newer, same identifier
    ]
    assert _best_match(entries, "6.1.5") == 0


# --- _resolve_from_lines (tier 1: bundled LTS registry lts_lines) -----------


_LINES = [
    {"line": "6.1", "released": "2023-11-16", "eol": "2028-12-31", "lts": True},
    {"line": "5.3", "released": "2020-10-27", "eol": "2024-12-31", "lts": True},
]


def test_resolve_from_lines_eol_line():
    resolved = _resolve_from_lines(_LINES, "5.3.0", now=_NOW)
    assert resolved == _Resolution(
        tier="lts-registry",
        verdict=CurrencyVerdict.EOL,
        latest="6.1",
        lag=1,
        eol_date="2024-12-31",
    )


def test_resolve_from_lines_clean_latest_line():
    resolved = _resolve_from_lines(_LINES, "6.1.5", now=_NOW)
    assert resolved == _Resolution(
        tier="lts-registry",
        verdict=CurrencyVerdict.SUPPORTED,
        latest="6.1",
        lag=0,
        eol_date="2028-12-31",
    )


def test_resolve_from_lines_no_match_is_none():
    assert _resolve_from_lines(_LINES, "9.0.0", now=_NOW) is None


def test_resolve_from_lines_empty_list_is_none():
    assert _resolve_from_lines([], "6.1.5", now=_NOW) is None


def test_resolve_from_lines_skips_malformed_entries():
    lines = [
        "not-a-dict",
        {"line": "6.1"},  # missing released/eol
        {"line": "5.3", "released": "2020-10-27", "eol": "2024-12-31"},
    ]
    resolved = _resolve_from_lines(lines, "5.3.0", now=_NOW)
    assert resolved is not None
    assert resolved.tier == "lts-registry"
    assert resolved.lag == 0  # only the one usable entry


# --- _resolve_from_cycles (tier 2: endoflife.date cache) --------------------


_CYCLES = [
    {"cycle": "2.0.0", "releaseDate": "2020-01-01", "eol": "2099-01-01", "latest": "2.0.0"},
    {"cycle": "2.31.0", "releaseDate": "2023-05-22", "eol": "2099-01-01", "latest": "2.31.0"},
]


def test_resolve_from_cycles_over_lag():
    resolved = _resolve_from_cycles(_CYCLES, "2.0.0", now=_NOW)
    assert resolved == _Resolution(
        tier="endoflife-date",
        verdict=CurrencyVerdict.SUPPORTED,
        latest="2.31.0",
        lag=1,
        eol_date="2099-01-01",
    )


def test_resolve_from_cycles_clean_latest_cycle():
    resolved = _resolve_from_cycles(_CYCLES, "2.31.0", now=_NOW)
    assert resolved is not None
    assert resolved.lag == 0
    assert resolved.verdict is CurrencyVerdict.SUPPORTED


def test_resolve_from_cycles_eol():
    cycles = [{"cycle": "1.11", "releaseDate": "2019-12-02", "eol": "2020-04-01"}]
    resolved = _resolve_from_cycles(cycles, "1.11.29", now=_NOW)
    assert resolved is not None
    assert resolved.verdict is CurrencyVerdict.EOL
    assert resolved.eol_date == "2020-04-01"


def test_resolve_from_cycles_no_match_is_none():
    assert _resolve_from_cycles(_CYCLES, "9.9.9", now=_NOW) is None


def test_resolve_from_cycles_unusable_eol_degrades_to_none():
    """A matched cycle whose own ``eol`` is truly unusable (absent, empty,
    or junk -- NOT the real API's documented booleans, honored below)
    degrades the WHOLE resolution to None rather than fabricating an
    eol_date -- never guess."""
    cycles = [{"cycle": "2.31.0", "releaseDate": "2023-05-22", "eol": None}]
    assert _resolve_from_cycles(cycles, "2.31.0", now=_NOW) is None
    cycles = [{"cycle": "2.31.0", "releaseDate": "2023-05-22"}]
    assert _resolve_from_cycles(cycles, "2.31.0", now=_NOW) is None


def test_resolve_from_cycles_boolean_eol_false_current_is_supported():
    """endoflife.date's boolean ``eol: false`` shape on a FULLY CURRENT
    match is an explicit still-supported assertion -- resolves SUPPORTED
    with ``eol_date=None`` (lag 0 -> no finding at the axis level, so the
    null date never reaches the frozen 6.1 model invariant), never noised
    into unknown (review finding, 2026-07-23)."""
    cycles = [{"cycle": "2.31.0", "releaseDate": "2023-05-22", "eol": False}]
    resolved = _resolve_from_cycles(cycles, "2.31.0", now=_NOW)
    assert resolved is not None
    assert resolved.verdict is CurrencyVerdict.SUPPORTED
    assert resolved.eol_date is None
    assert resolved.lag == 0


def test_resolve_from_cycles_boolean_eol_shapes_that_would_need_a_dateless_finding_degrade():
    """``eol: true`` (already-EOL, no date published) and ``eol: false``
    on a BEHIND match would each need an eol/over-lag ``Finding`` with
    ``eol_date=None`` -- the frozen 6.1 model invariant requires non-null
    latest/lag/eol_date on both reasons, so these degrade to ``None``
    (unknown) rather than fabricating a date. Schema-blocked, not a
    producer choice -- see the deferred-work ledger (2026-07-23)."""
    eol_true = [{"cycle": "1.0", "releaseDate": "2015-01-01", "eol": True}]
    assert _resolve_from_cycles(eol_true, "1.0.9", now=_NOW) is None

    eol_false_behind = [
        {"cycle": "1.0", "releaseDate": "2015-01-01", "eol": False},
        {"cycle": "2.0", "releaseDate": "2020-01-01", "eol": False},
    ]
    assert _resolve_from_cycles(eol_false_behind, "1.0.9", now=_NOW) is None


def test_resolve_from_cycles_numeric_cycle_is_coerced_to_string():
    cycles = [{"cycle": 3.12, "releaseDate": "2023-10-02", "eol": "2028-10-31"}]
    resolved = _resolve_from_cycles(cycles, "3.12.5", now=_NOW)
    assert resolved is not None
    assert resolved.tier == "endoflife-date"


def test_resolve_from_cycles_skips_empty_string_cycle():
    """Mirrors ``_resolve_from_lines``'s own non-empty ``line`` filter: an
    empty-string ``cycle`` (after ``str()`` coercion) is skipped, not
    treated as a usable (if odd) identifier."""
    cycles = [
        {"cycle": "", "releaseDate": "2023-05-22", "eol": "2099-01-01"},
        {"cycle": "2.31.0", "releaseDate": "2023-05-22", "eol": "2099-01-01"},
    ]
    resolved = _resolve_from_cycles(cycles, "2.31.0", now=_NOW)
    assert resolved is not None
    assert resolved.lag == 0  # only the one usable entry counted


# --- _classify (the 3-way reason-token precedence) --------------------------


def test_classify_none_resolution_is_unknown():
    assert _classify(None) == ("unknown", CurrencyVerdict.UNKNOWN)


def test_classify_eol_wins_even_when_also_over_lag():
    """Decision record § 2, worked example 4: eol beats over-lag even when
    BOTH conditions hold on the same resolution."""
    resolution = _Resolution(
        tier="lts-registry", verdict=CurrencyVerdict.EOL, latest="6.1", lag=3, eol_date="2020-01-01"
    )
    assert _classify(resolution) == ("eol", CurrencyVerdict.EOL)


def test_classify_over_lag_when_supported_and_behind():
    resolution = _Resolution(
        tier="endoflife-date",
        verdict=CurrencyVerdict.SUPPORTED,
        latest="2.31.0",
        lag=1,
        eol_date="2099-01-01",
    )
    assert _classify(resolution) == ("over-lag", CurrencyVerdict.SUPPORTED)


def test_classify_clean_resolution_is_none():
    resolution = _Resolution(
        tier="endoflife-date",
        verdict=CurrencyVerdict.SUPPORTED,
        latest="2.31.0",
        lag=0,
        eol_date="2099-01-01",
    )
    assert _classify(resolution) is None


# --- _resolve (the full tier ladder) ----------------------------------------


def _products():
    products = _load_registry().get("products")
    assert isinstance(products, dict)
    return products


def _alias_index():
    return _registry_alias_index(_products())


def test_registry_alias_index_raises_on_a_cross_product_alias_collision():
    """A malformed bundled registry with two different products claiming
    the same normalized name/alias must raise loudly (a packaged-data
    integrity bug) rather than silently letting the second product's key
    overwrite the first's -- that would misroute one product's currency
    lookups to the other's data."""
    products = {
        "django": {"aliases": ["djangoproject"]},
        "flask": {"aliases": ["djangoproject"]},  # collides with django's alias
    }
    with pytest.raises(ValueError, match="djangoproject"):
        _registry_alias_index(products)


def test_resolve_hits_tier_1_for_a_manual_registry_entry():
    resolved = _resolve(
        "spring-framework",
        "5.3.0",
        products=_products(),
        alias_index=_alias_index(),
        registry_fresh=True,
        endoflife_snapshot=None,
        endoflife_fresh=False,
        now=_NOW,
    )
    assert resolved is not None
    assert resolved.tier == "lts-registry"
    assert resolved.verdict is CurrencyVerdict.EOL


def test_resolve_case_insensitive_alias_match():
    resolved = _resolve(
        "springframework",  # a registered alias, different casing/spelling
        "6.1.5",
        products=_products(),
        alias_index=_alias_index(),
        registry_fresh=True,
        endoflife_snapshot=None,
        endoflife_fresh=False,
        now=_NOW,
    )
    assert resolved is not None
    assert resolved.tier == "lts-registry"


def test_resolve_routes_an_endoflife_sourced_registry_entry_via_its_slug():
    """``python`` has NO ``lts_lines`` of its own (source: endoflife) -- it
    must route to the endoflife cache keyed by its ``slug`` (also
    ``"python"``), not resolve at tier 1."""
    resolved = _resolve(
        "python",
        "3.12.5",
        products=_products(),
        alias_index=_alias_index(),
        registry_fresh=True,
        endoflife_snapshot={"python": [{"cycle": "3.12", "releaseDate": "2023-10-02", "eol": "2028-10-31"}]},
        endoflife_fresh=True,
        now=_NOW,
    )
    assert resolved is not None
    assert resolved.tier == "endoflife-date"


def test_resolve_bare_name_endoflife_hit_when_no_registry_match():
    resolved = _resolve(
        "requests",
        "2.31.0",
        products=_products(),
        alias_index=_alias_index(),
        registry_fresh=True,
        endoflife_snapshot={"requests": _CYCLES},
        endoflife_fresh=True,
        now=_NOW,
    )
    assert resolved is not None
    assert resolved.tier == "endoflife-date"


def test_resolve_stale_registry_skips_tier_1_entirely():
    """NFR-S9: a stale registry never silently reports supported -- tier 1
    is skipped, not merely flagged, when ``registry_fresh=False``."""
    resolved = _resolve(
        "spring-framework",
        "6.1.5",  # would otherwise resolve cleanly (SUPPORTED, lag=0)
        products=_products(),
        alias_index=_alias_index(),
        registry_fresh=False,
        endoflife_snapshot=None,
        endoflife_fresh=False,
        now=_NOW,
    )
    assert resolved is None


def test_resolve_stale_endoflife_skips_tier_2_entirely():
    resolved = _resolve(
        "requests",
        "2.31.0",
        products=_products(),
        alias_index=_alias_index(),
        registry_fresh=True,
        endoflife_snapshot={"requests": _CYCLES},
        endoflife_fresh=False,  # stale -- must not be consulted
        now=_NOW,
    )
    assert resolved is None


def test_resolve_nothing_matches_anywhere_is_none():
    resolved = _resolve(
        "totally-unheard-of-package",
        "1.0.0",
        products=_products(),
        alias_index=_alias_index(),
        registry_fresh=True,
        endoflife_snapshot={"requests": _CYCLES},
        endoflife_fresh=True,
        now=_NOW,
    )
    assert resolved is None


# --- currency_findings (the whole-axis integration) --------------------------


def make_inventory(*components) -> ResolvedInventory:
    return ResolvedInventory(
        components=merge_components(components), resolved_scan_set=(MANIFEST,)
    )


def test_currency_findings_mixed_fixture_covers_all_three_reasons(
    component_factory, monkeypatch, tmp_path
):
    """The story's own AC: a mixed fixture (an LTS-registry hit, an
    endoflife-only hit, an unresolvable component) -- every finding composes
    at warn and currency.gating stays false (gating is config.py's job, not
    this function's -- currency_findings takes no gating parameter at all).

    Uses the fixed ``_NOW`` like every other test here, NEVER the wall
    clock: the tier-1 leg depends on ``registry_fresh``, which the real
    bundled registry's ``updated:`` date only satisfies within its 180-day
    max-age window -- a wall-clock ``now`` would flip this test red on a
    fixed future calendar date with no code change (review finding,
    2026-07-23). The cache file's mtime is pinned to ``_NOW`` too (see
    ``_pin_cache_mtime_to_now``) so the tier-2 leg stays fresh under the
    same fixed clock."""
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(tmp_path))
    feeds.write_endoflife_cache(tmp_path, {"requests": _CYCLES})
    _pin_cache_mtime_to_now(tmp_path)
    now = _NOW

    components = [
        component_factory(name="spring-framework", version="5.3.0"),  # tier 1, eol
        component_factory(name="requests", version="2.0.0"),  # tier 2, over-lag
        component_factory(name="mystery-pkg", version="9.9.9"),  # unknown
    ]
    findings, currency_data = currency_findings(components, now=now)

    by_reason = {f.id.split(":")[1]: f for f in findings if not f.id.startswith("currency:unknown:!python")}
    assert set(by_reason) == {"eol", "over-lag", "unknown"}
    for finding in findings:
        status, _driver = currency_rung(finding)
        assert status is Status.WARN
    assert currency_data is not None
    assert currency_data.source == "pyforge.warden/data/lts-registry.yaml"


def test_currency_findings_no_finding_for_a_fully_current_component(
    component_factory,
):
    """A component resolving SUPPORTED with zero lag emits nothing -- mirrors
    ``license_findings``'s "allowed emits nothing" rule. Filters out the
    always-present runtime finding (its own resolution is independent of
    this fixture's ambient ``PYFORGE_WARDEN_FEED_CACHE_DIR`` ordering
    relative to the fixed ``_NOW`` used here)."""
    components = [component_factory(name="spring-framework", version="6.1.5")]
    findings, _data = currency_findings(components, now=_NOW)
    non_runtime = [f for f in findings if f.subject != "!python-runtime"]
    assert non_runtime == []


def test_currency_findings_runtime_always_assessed(monkeypatch):
    """The Python runtime is put through the SAME ladder every scan -- with
    no endoflife cache consulted at all (env var explicitly unset here, so
    tier 2 is unreachable regardless of the session's ambient fixture), it
    degrades to unknown (still assessed, never skipped)."""
    monkeypatch.delenv(feeds.FEED_CACHE_DIR_ENV_VAR, raising=False)
    findings, _data = currency_findings([], now=_NOW)
    runtime_findings = [f for f in findings if f.subject == "!python-runtime"]
    assert len(runtime_findings) == 1
    assert runtime_findings[0].id.startswith("currency:unknown:!python-runtime@")
    assert runtime_findings[0].currency.verdict is CurrencyVerdict.UNKNOWN


def test_currency_findings_version_less_component_is_unknown(component_factory):
    components = [component_factory(name="leftpad", version=None)]
    findings, _data = currency_findings(components, now=_NOW)
    ids = {f.id for f in findings if f.subject != "!python-runtime"}
    assert "currency:unknown:leftpad@unspecified" in ids


def test_currency_findings_is_ecosystem_agnostic(component_factory):
    """FR34: "for every resolved component" -- a conda component gets the
    SAME tier-ladder treatment as a pypi one (unlike license.py, currency
    resolution never dispatches on ``component.ecosystem``)."""
    components = [
        component_factory(
            name="spring-framework", version="5.3.0", ecosystem=Ecosystem.CONDA
        )
    ]
    findings, _data = currency_findings(components, now=_NOW)
    non_runtime = [f for f in findings if f.subject != "!python-runtime"]
    assert len(non_runtime) == 1
    assert non_runtime[0].id == "currency:eol:spring-framework@5.3.0"


def test_currency_findings_are_sorted_by_id(component_factory):
    components = [
        component_factory(name="zzz-unknown", version="1.0.0"),
        component_factory(name="aaa-unknown", version="1.0.0"),
    ]
    findings, _data = currency_findings(components, now=_NOW)
    ids = [f.id for f in findings]
    assert ids == sorted(ids)


def test_currency_findings_twice_run_is_byte_identical(component_factory):
    components = [component_factory(name="spring-framework", version="5.3.0")]
    first, first_data = currency_findings(components, now=_NOW)
    second, second_data = currency_findings(components, now=_NOW)
    assert first == second
    assert first_data == second_data


def test_currency_findings_drops_colliding_snapshot_keys_entirely(
    component_factory, monkeypatch, tmp_path
):
    """Two DIFFERENT snapshot keys normalizing to the same product key
    (``Django``/``django``) are ambiguous -- BOTH are dropped (the lookup
    degrades to unknown) rather than letting dict iteration order silently
    pick a winner (review finding, 2026-07-23; contrast the bundled
    registry's alias index, packaged data, which raises instead)."""
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(tmp_path))
    feeds.write_endoflife_cache(
        tmp_path,
        {
            "Django": [
                {"cycle": "4.2", "releaseDate": "2023-04-03", "eol": "2026-04-07"}
            ],
            "django": [
                {"cycle": "5.2", "releaseDate": "2025-04-02", "eol": "2028-04-30"}
            ],
        },
    )
    _pin_cache_mtime_to_now(tmp_path)
    components = [component_factory(name="django", version="4.2.1")]
    findings, _data = currency_findings(components, now=_NOW)
    non_runtime = [f for f in findings if f.subject != "!python-runtime"]
    assert len(non_runtime) == 1
    assert non_runtime[0].id == "currency:unknown:django@4.2.1"


def test_currency_findings_boolean_eol_false_current_emits_no_finding(
    component_factory, monkeypatch, tmp_path
):
    """End-to-end proof for the expressible half of the boolean-``eol``
    fix (review finding, 2026-07-23): a fully-current component whose
    matched cycle carries ``eol: false`` emits NO finding at all --
    previously it flooded ``currency:unknown`` warn noise on every scan
    against a real provisioned endoflife.date snapshot."""
    monkeypatch.setenv(feeds.FEED_CACHE_DIR_ENV_VAR, str(tmp_path))
    feeds.write_endoflife_cache(
        tmp_path,
        {"leftpad": [{"cycle": "1.0", "releaseDate": "2015-01-01", "eol": False}]},
    )
    _pin_cache_mtime_to_now(tmp_path)
    components = [component_factory(name="leftpad", version="1.0.2")]
    findings, _data = currency_findings(components, now=_NOW)
    non_runtime = [f for f in findings if f.subject != "!python-runtime"]
    assert non_runtime == []


def test_ambient_snapshot_keeps_every_pinned_fixture_dep_it_covers_fully_current():
    """Cross-check for the hidden two-file invariant between ``tests/
    conftest.py``'s session-scoped ambient endoflife snapshot and the
    fixture manifests under ``tests/fixtures/projects/`` (review finding,
    2026-07-23): every ``name==version`` pin whose name the ambient
    snapshot covers must resolve fully current (supported, lag 0). Without
    this guard, a routine fixture-pin bump (e.g. requests 2.31.0 ->
    2.32.0) silently regresses a "must stay clean" fixture into
    ``currency:unknown`` warn noise, and the resulting failure points at
    the verdict -- this test fails HERE instead, naming the real fix:
    update ``_currency_ambient_feed_env`` in tests/conftest.py alongside
    the pin."""
    fixtures_root = Path(__file__).resolve().parent.parent / "fixtures" / "projects"
    assert fixtures_root.is_dir()
    cache_dir = feeds.resolve_cache_dir()
    assert cache_dir is not None, "ambient feed cache env var not set -- see conftest"
    snapshot = feeds.load_endoflife_snapshot(feeds.endoflife_cache_path(cache_dir))
    assert snapshot, "ambient endoflife snapshot missing -- see tests/conftest.py"
    normalized_snapshot = {_normalize_name(key): value for key, value in snapshot.items()}

    requirement_pin = re.compile(r"\b([A-Za-z0-9][A-Za-z0-9._-]*)==([0-9][A-Za-z0-9._+!-]*)")
    toml_pin = re.compile(r'(?m)^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*=\s*"\s*==\s*([0-9][^"]*)"')
    stale: list[str] = []
    for path in sorted(fixtures_root.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for name, version in requirement_pin.findall(text) + toml_pin.findall(text):
            cycles = normalized_snapshot.get(_normalize_name(name))
            if cycles is None:
                continue  # not an ambient-covered dep; cleanliness not claimed
            resolution = _resolve_from_cycles(cycles, version, now=_NOW)
            fully_current = (
                resolution is not None
                and resolution.verdict is CurrencyVerdict.SUPPORTED
                and resolution.lag == 0
            )
            if not fully_current:
                stale.append(f"{path.relative_to(fixtures_root)}: {name}=={version}")
    assert not stale, (
        "fixture pins drifted from tests/conftest.py's ambient endoflife "
        "snapshot (they would now emit currency findings and regress "
        "'must stay clean' fixtures): " + "; ".join(sorted(set(stale)))
    )


# --- CurrencyEngine (the thin coverage-and-EngineResult wrapper) ------------


def test_currency_engine_reports_full_coverage(tmp_path, component_factory):
    engine = CurrencyEngine()
    inventory = make_inventory(
        component_factory(name="spring-framework", version="6.1.5")
    )
    result = engine.run(tmp_path, inventory)
    assert result.axis == AXIS_CURRENCY
    (coverage,) = result.coverage
    assert coverage.deps_total == inventory.count
    assert coverage.deps_assessed == inventory.count
    assert result.currency_data is not None


def test_currency_engine_name_and_axis():
    engine = CurrencyEngine()
    assert engine.name == "currency"
    assert engine.axis == AXIS_CURRENCY
