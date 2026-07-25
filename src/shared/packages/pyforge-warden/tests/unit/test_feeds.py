"""Unit tests -- ``feeds.py`` (Story 6.4): cache-dir resolution, the KEV
cache path helper, staleness math, ``FeedProvenance`` construction, the KEV
catalog loader, and the atomic cache writer. Mirrors ``test_vuln.py``'s
style -- pure-logic coverage, no subprocess, no network.

Story 6.3 adds the endoflife.date trio's own coverage (``endoflife_cache_
path``/``load_endoflife_snapshot``/``write_endoflife_cache``), mirroring the
KEV sections above one-for-one.

Story 6.7 adds the EPSS trio's own coverage (``epss_cache_path``/
``load_epss_scores``/``write_epss_cache``), mirroring the KEV sections
one-for-one.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from pyforge.warden.feeds import (
    DEFAULT_FEED_MAX_AGE_DAYS,
    FEED_CACHE_DIR_ENV_VAR,
    endoflife_cache_path,
    epss_cache_path,
    feed_provenance,
    feed_snapshot_at,
    is_feed_stale,
    kev_cache_path,
    load_endoflife_snapshot,
    load_epss_scores,
    load_kev_catalog,
    resolve_cache_dir,
    write_endoflife_cache,
    write_epss_cache,
    write_kev_cache,
)
from pyforge.warden.models import FeedProvenance

_NOW = datetime(2026, 7, 18, 12, 0, 0, tzinfo=UTC)


# --- resolve_cache_dir --------------------------------------------------------


def test_resolve_cache_dir_reads_the_env_var():
    assert (
        resolve_cache_dir(env={FEED_CACHE_DIR_ENV_VAR: "/some/cache"})
        == "/some/cache"
    )


def test_resolve_cache_dir_is_none_when_unset():
    assert resolve_cache_dir(env={}) is None


def test_resolve_cache_dir_is_none_when_empty_string():
    assert resolve_cache_dir(env={FEED_CACHE_DIR_ENV_VAR: ""}) is None


# --- kev_cache_path ------------------------------------------------------------


def test_kev_cache_path_layout(tmp_path):
    assert kev_cache_path(tmp_path) == (
        tmp_path / "kev" / "known_exploited_vulnerabilities.json"
    )


# --- feed_snapshot_at ----------------------------------------------------------


def test_feed_snapshot_at_is_the_files_own_mtime_iso8601(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text("{}", encoding="utf-8")
    snapshot_at = feed_snapshot_at(path)
    parsed = datetime.fromisoformat(snapshot_at)
    assert parsed.tzinfo is not None


# --- is_feed_stale (mirrors vuln.is_db_stale's own boundary rigor) -----------


def test_is_feed_stale_exactly_at_the_boundary_is_not_stale():
    snapshot_at = (_NOW - timedelta(days=DEFAULT_FEED_MAX_AGE_DAYS)).isoformat()
    assert is_feed_stale(snapshot_at, DEFAULT_FEED_MAX_AGE_DAYS, now=_NOW) is False


def test_is_feed_stale_one_second_past_the_boundary_is_stale():
    snapshot_at = (
        _NOW - timedelta(days=DEFAULT_FEED_MAX_AGE_DAYS, seconds=1)
    ).isoformat()
    assert is_feed_stale(snapshot_at, DEFAULT_FEED_MAX_AGE_DAYS, now=_NOW) is True


def test_is_feed_stale_a_fresh_snapshot_is_not_stale():
    snapshot_at = (_NOW - timedelta(days=1)).isoformat()
    assert is_feed_stale(snapshot_at, DEFAULT_FEED_MAX_AGE_DAYS, now=_NOW) is False


def test_is_feed_stale_future_dated_is_stale_never_fresh():
    snapshot_at = (_NOW + timedelta(hours=1)).isoformat()
    assert is_feed_stale(snapshot_at, DEFAULT_FEED_MAX_AGE_DAYS, now=_NOW) is True


def test_is_feed_stale_none_snapshot_is_stale():
    assert is_feed_stale(None, DEFAULT_FEED_MAX_AGE_DAYS, now=_NOW) is True


@pytest.mark.parametrize(
    "snapshot_at",
    ["not-a-timestamp", "", "2026-13-99T99:99:99+00:00"],
)
def test_is_feed_stale_unparsable_snapshot_is_stale_never_raises(snapshot_at):
    assert is_feed_stale(snapshot_at, DEFAULT_FEED_MAX_AGE_DAYS, now=_NOW) is True


def test_is_feed_stale_naive_snapshot_is_stale():
    assert (
        is_feed_stale("2026-07-16T00:00:00", DEFAULT_FEED_MAX_AGE_DAYS, now=_NOW)
        is True
    )


# --- feed_provenance -----------------------------------------------------------


def test_feed_provenance_fresh(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text("{}", encoding="utf-8")
    provenance = feed_provenance(
        source=str(path),
        path=path,
        max_age_days=DEFAULT_FEED_MAX_AGE_DAYS,
        now=datetime.now(UTC),
    )
    assert isinstance(provenance, FeedProvenance)
    assert provenance.source == str(path)
    assert provenance.snapshot_at is not None
    assert provenance.max_age_ok is True


def test_feed_provenance_stale(tmp_path):
    import os
    import time

    path = tmp_path / "feed.json"
    path.write_text("{}", encoding="utf-8")
    stale_mtime = time.time() - (DEFAULT_FEED_MAX_AGE_DAYS + 1) * 86400
    os.utime(path, (stale_mtime, stale_mtime))
    provenance = feed_provenance(
        source=str(path),
        path=path,
        max_age_days=DEFAULT_FEED_MAX_AGE_DAYS,
        now=datetime.now(UTC),
    )
    assert provenance.max_age_ok is False


# --- load_kev_catalog ------------------------------------------------------------


def test_load_kev_catalog_missing_file_is_none(tmp_path):
    assert load_kev_catalog(tmp_path / "does-not-exist.json") is None


def test_load_kev_catalog_undecodable_bytes_is_none(tmp_path):
    """A partially-written/corrupted cache file (non-UTF-8 bytes) must
    degrade to "no usable feed" like any other unreadable file, never raise
    ``UnicodeDecodeError`` out of the loader."""
    path = tmp_path / "feed.json"
    path.write_bytes(b"\xff\xfe\x00not valid utf-8")
    assert load_kev_catalog(path) is None


def test_load_kev_catalog_invalid_json_is_none(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text("{ not valid json ]", encoding="utf-8")
    assert load_kev_catalog(path) is None


def test_load_kev_catalog_non_object_top_level_is_none(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert load_kev_catalog(path) is None


def test_load_kev_catalog_missing_vulnerabilities_key_is_none(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text(json.dumps({"unexpected": "shape"}), encoding="utf-8")
    assert load_kev_catalog(path) is None


def test_load_kev_catalog_present_but_empty_is_an_empty_dict_not_none(tmp_path):
    """The distinction the Story 6.4 ambient test fixture depends on:
    present + fresh + zero entries reads as ``{}``, never ``None`` (which
    would mean "no usable feed at all")."""
    path = tmp_path / "feed.json"
    path.write_text(json.dumps({"vulnerabilities": []}), encoding="utf-8")
    assert load_kev_catalog(path) == {}


def test_load_kev_catalog_extracts_cve_id_to_date_added(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text(
        json.dumps(
            {
                "vulnerabilities": [
                    {"cveID": "CVE-1970-00001", "dateAdded": "2026-01-01"},
                    {"cveID": "CVE-1970-00002", "dateAdded": "2026-02-02"},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert load_kev_catalog(path) == {
        "CVE-1970-00001": "2026-01-01",
        "CVE-1970-00002": "2026-02-02",
    }


def test_load_kev_catalog_skips_malformed_entries_without_aborting(tmp_path):
    """One malformed entry (missing cveID, missing dateAdded, non-dict) must
    not abort the load of the rest -- mirrors ``vuln.py``'s per-entry
    tolerance throughout."""
    path = tmp_path / "feed.json"
    path.write_text(
        json.dumps(
            {
                "vulnerabilities": [
                    "not-a-dict",
                    {"dateAdded": "2026-01-01"},  # missing cveID
                    {"cveID": "CVE-1970-00003"},  # missing dateAdded
                    {"cveID": "", "dateAdded": "2026-01-01"},  # empty cveID
                    {"cveID": "CVE-1970-00004", "dateAdded": "2026-04-04"},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert load_kev_catalog(path) == {"CVE-1970-00004": "2026-04-04"}


# --- write_kev_cache -------------------------------------------------------------


def test_write_kev_cache_round_trips_through_load_kev_catalog(tmp_path):
    document = {
        "vulnerabilities": [
            {"cveID": "CVE-1970-00005", "dateAdded": "2026-05-05"},
        ]
    }
    written_path = write_kev_cache(tmp_path, document)
    assert written_path == kev_cache_path(tmp_path)
    assert load_kev_catalog(written_path) == {"CVE-1970-00005": "2026-05-05"}


def test_write_kev_cache_creates_the_parent_directory(tmp_path):
    cache_dir = tmp_path / "nested" / "cache"
    write_kev_cache(cache_dir, {"vulnerabilities": []})
    assert kev_cache_path(cache_dir).is_file()


def test_write_kev_cache_leaves_no_temp_file_behind(tmp_path):
    write_kev_cache(tmp_path, {"vulnerabilities": []})
    entries = {p.name for p in kev_cache_path(tmp_path).parent.iterdir()}
    assert entries == {"known_exploited_vulnerabilities.json"}


def test_write_kev_cache_is_atomic_replace_on_a_second_write(tmp_path):
    write_kev_cache(tmp_path, {"vulnerabilities": []})
    write_kev_cache(
        tmp_path,
        {"vulnerabilities": [{"cveID": "CVE-1970-00006", "dateAdded": "2026-06-06"}]},
    )
    assert load_kev_catalog(kev_cache_path(tmp_path)) == {
        "CVE-1970-00006": "2026-06-06"
    }


# --- endoflife_cache_path (Story 6.3) -----------------------------------------


def test_endoflife_cache_path_layout(tmp_path):
    assert endoflife_cache_path(tmp_path) == (
        tmp_path / "endoflife" / "endoflife_snapshot.json"
    )


# --- load_endoflife_snapshot ---------------------------------------------------


def test_load_endoflife_snapshot_missing_file_is_none(tmp_path):
    assert load_endoflife_snapshot(tmp_path / "does-not-exist.json") is None


def test_load_endoflife_snapshot_undecodable_bytes_is_none(tmp_path):
    path = tmp_path / "feed.json"
    path.write_bytes(b"\xff\xfe\x00not valid utf-8")
    assert load_endoflife_snapshot(path) is None


def test_load_endoflife_snapshot_invalid_json_is_none(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text("{ not valid json ]", encoding="utf-8")
    assert load_endoflife_snapshot(path) is None


def test_load_endoflife_snapshot_non_object_top_level_is_none(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert load_endoflife_snapshot(path) is None


def test_load_endoflife_snapshot_present_but_empty_is_an_empty_dict_not_none(tmp_path):
    """The same present/fresh/zero-entries distinction ``load_kev_catalog``'s
    own docstring establishes."""
    path = tmp_path / "feed.json"
    path.write_text(json.dumps({}), encoding="utf-8")
    assert load_endoflife_snapshot(path) == {}


def test_load_endoflife_snapshot_extracts_slug_to_cycle_array(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text(
        json.dumps(
            {
                "python": [{"cycle": "3.12", "eol": "2028-10-31"}],
                "django": [{"cycle": "5.2", "eol": "2028-04-30"}],
            }
        ),
        encoding="utf-8",
    )
    assert load_endoflife_snapshot(path) == {
        "python": [{"cycle": "3.12", "eol": "2028-10-31"}],
        "django": [{"cycle": "5.2", "eol": "2028-04-30"}],
    }


def test_load_endoflife_snapshot_drops_non_array_slug_values_without_aborting(
    tmp_path,
):
    """A malformed per-slug value (not a JSON array) is skipped -- never
    partially trusted, never aborts the load of the rest (mirrors
    ``load_kev_catalog``'s own per-entry tolerance)."""
    path = tmp_path / "feed.json"
    path.write_text(
        json.dumps(
            {
                "python": [{"cycle": "3.12", "eol": "2028-10-31"}],
                "bogus": "not-a-list",
                123: "non-string-key-impossible-in-real-json",  # json.dumps coerces
            }
        ),
        encoding="utf-8",
    )
    assert load_endoflife_snapshot(path) == {
        "python": [{"cycle": "3.12", "eol": "2028-10-31"}]
    }


# --- write_endoflife_cache ------------------------------------------------------


def test_write_endoflife_cache_round_trips_through_load_endoflife_snapshot(tmp_path):
    document = {"python": [{"cycle": "3.12", "eol": "2028-10-31"}]}
    written_path = write_endoflife_cache(tmp_path, document)
    assert written_path == endoflife_cache_path(tmp_path)
    assert load_endoflife_snapshot(written_path) == document


def test_write_endoflife_cache_creates_the_parent_directory(tmp_path):
    cache_dir = tmp_path / "nested" / "cache"
    write_endoflife_cache(cache_dir, {})
    assert endoflife_cache_path(cache_dir).is_file()


def test_write_endoflife_cache_leaves_no_temp_file_behind(tmp_path):
    write_endoflife_cache(tmp_path, {})
    entries = {p.name for p in endoflife_cache_path(tmp_path).parent.iterdir()}
    assert entries == {"endoflife_snapshot.json"}


def test_write_endoflife_cache_is_atomic_replace_on_a_second_write(tmp_path):
    write_endoflife_cache(tmp_path, {"python": [{"cycle": "3.11"}]})
    write_endoflife_cache(tmp_path, {"python": [{"cycle": "3.12"}]})
    assert load_endoflife_snapshot(endoflife_cache_path(tmp_path)) == {
        "python": [{"cycle": "3.12"}]
    }


# --- epss_cache_path (Story 6.7) -----------------------------------------------


def test_epss_cache_path_layout(tmp_path):
    assert epss_cache_path(tmp_path) == (tmp_path / "epss" / "epss_scores.json")


# --- load_epss_scores ------------------------------------------------------------


def test_load_epss_scores_missing_file_is_none(tmp_path):
    assert load_epss_scores(tmp_path / "does-not-exist.json") is None


def test_load_epss_scores_undecodable_bytes_is_none(tmp_path):
    path = tmp_path / "feed.json"
    path.write_bytes(b"\xff\xfe\x00not valid utf-8")
    assert load_epss_scores(path) is None


def test_load_epss_scores_invalid_json_is_none(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text("{ not valid json ]", encoding="utf-8")
    assert load_epss_scores(path) is None


def test_load_epss_scores_non_object_top_level_is_none(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert load_epss_scores(path) is None


def test_load_epss_scores_missing_scores_key_is_none(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text(json.dumps({"unexpected": "shape"}), encoding="utf-8")
    assert load_epss_scores(path) is None


def test_load_epss_scores_present_but_empty_is_an_empty_dict_not_none(tmp_path):
    """The same present/fresh/zero-entries distinction ``load_kev_catalog``'s
    own docstring establishes."""
    path = tmp_path / "feed.json"
    path.write_text(json.dumps({"scores": []}), encoding="utf-8")
    assert load_epss_scores(path) == {}


def test_load_epss_scores_extracts_cve_to_score_percentile_tuple(tmp_path):
    path = tmp_path / "feed.json"
    path.write_text(
        json.dumps(
            {
                "scores": [
                    {"cve": "CVE-1970-00001", "epss": 0.7, "percentile": 0.9},
                    {"cve": "CVE-1970-00002", "epss": 0.1, "percentile": 0.2},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert load_epss_scores(path) == {
        "CVE-1970-00001": (0.7, 0.9),
        "CVE-1970-00002": (0.1, 0.2),
    }


def test_load_epss_scores_skips_malformed_entries_without_aborting(tmp_path):
    """One malformed entry (missing cve, non-numeric epss/percentile,
    non-dict) must not abort the load of the rest -- mirrors
    ``load_kev_catalog``'s per-entry tolerance."""
    path = tmp_path / "feed.json"
    path.write_text(
        json.dumps(
            {
                "scores": [
                    "not-a-dict",
                    {"epss": 0.5, "percentile": 0.5},  # missing cve
                    {"cve": "CVE-1970-00003", "epss": "not-a-number", "percentile": 0.5},
                    {"cve": "CVE-1970-00004", "epss": 0.5, "percentile": "bad"},
                    {"cve": "CVE-1970-00005", "epss": True, "percentile": 0.5},
                    {"cve": "CVE-1970-00006", "epss": 0.4, "percentile": 0.6},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert load_epss_scores(path) == {"CVE-1970-00006": (0.4, 0.6)}


def test_load_epss_scores_skips_non_finite_and_out_of_domain_entries(tmp_path):
    """Review finding (follow-up pass): ``json.loads`` happily parses
    ``NaN``/``Infinity`` tokens and out-of-range numbers, and a shape-only
    load would hand such an entry to ``engines._stamp_epss``, whose
    crash-guard silently drops the stamp -- turning a domain-corrupt cache
    into a silent pass for that CVE. The load filter makes every surviving
    catalog entry trustworthy by construction: non-finite or
    outside-``[0, 1]`` ``epss``/``percentile`` entries are skipped exactly
    like any other malformed entry."""
    path = tmp_path / "feed.json"
    # json.dumps emits bare NaN/Infinity tokens for these (allow_nan
    # defaults True) -- the exact lenient-JSON shape json.loads reads back.
    path.write_text(
        json.dumps(
            {
                "scores": [
                    {"cve": "CVE-1970-00010", "epss": float("nan"), "percentile": 0.5},
                    {"cve": "CVE-1970-00011", "epss": float("inf"), "percentile": 0.5},
                    {"cve": "CVE-1970-00012", "epss": 0.5, "percentile": float("-inf")},
                    {"cve": "CVE-1970-00013", "epss": 2.0, "percentile": 0.9},
                    {"cve": "CVE-1970-00014", "epss": -0.1, "percentile": 0.9},
                    {"cve": "CVE-1970-00015", "epss": 0.9, "percentile": 1.5},
                    {"cve": "CVE-1970-00016", "epss": 0.0, "percentile": 1.0},
                ]
            }
        ),
        encoding="utf-8",
    )
    # Only the boundary-valid entry survives (0.0 and 1.0 are both legal).
    assert load_epss_scores(path) == {"CVE-1970-00016": (0.0, 1.0)}


# --- write_epss_cache --------------------------------------------------------


def test_write_epss_cache_round_trips_through_load_epss_scores(tmp_path):
    document = {"scores": [{"cve": "CVE-1970-00007", "epss": 0.8, "percentile": 0.95}]}
    written_path = write_epss_cache(tmp_path, document)
    assert written_path == epss_cache_path(tmp_path)
    assert load_epss_scores(written_path) == {"CVE-1970-00007": (0.8, 0.95)}


def test_write_epss_cache_creates_the_parent_directory(tmp_path):
    cache_dir = tmp_path / "nested" / "cache"
    write_epss_cache(cache_dir, {"scores": []})
    assert epss_cache_path(cache_dir).is_file()


def test_write_epss_cache_leaves_no_temp_file_behind(tmp_path):
    write_epss_cache(tmp_path, {"scores": []})
    entries = {p.name for p in epss_cache_path(tmp_path).parent.iterdir()}
    assert entries == {"epss_scores.json"}


def test_write_epss_cache_is_atomic_replace_on_a_second_write(tmp_path):
    write_epss_cache(tmp_path, {"scores": []})
    write_epss_cache(
        tmp_path,
        {"scores": [{"cve": "CVE-1970-00008", "epss": 0.3, "percentile": 0.4}]},
    )
    assert load_epss_scores(epss_cache_path(tmp_path)) == {
        "CVE-1970-00008": (0.3, 0.4)
    }
