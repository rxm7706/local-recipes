"""Core atlas metric semantics as pure Ibis expressions (Story D1, FR-8, AD-4/AD-8).

The metric / business logic embedded in the 28 read CLIs is declared ONCE here as
Ibis expressions over the migrated canonical Parquet store, so every read surface
(pages, MCP reads, agents — Waves D2/D3) translates through the SAME semantic
interface (AD-8) instead of re-writing raw SQL.

**AD-4 — Ibis → DuckDB ONLY.** Every function below returns an Ibis expression
(``ir.Value``) evaluated by the DuckDB backend. There is NO pandas metric
arithmetic and no other engine in this layer; the models in ``models.py`` bind
these expressions to Ibis tables read from Parquet via DuckDB.

**Legacy-formula provenance (DW-B1-1 honesty).** Each metric records where its
formula comes from in ``METRIC_PROVENANCE``. Two kinds:

- ``legacy-formula`` — the expression is a faithful port of an EXPLICIT legacy CLI
  formula (cited by file + symbol). The ``tests/semantic`` parity fixtures anchor
  it by re-implementing that legacy formula INDEPENDENTLY (verbatim copy of the
  legacy function / SQL predicate) and asserting the Ibis port matches — a real
  legacy anchor, never "both sides compute the same thing".
- ``migrated-node-derived-flag-recapture`` — the migrated Parquet dataset is a
  B2/B4 SHAPE-ONLY port whose columns do not carry the exact legacy signal, so the
  expression is declared over the migrated column and FLAGGED for legacy recapture
  (exactly the B2 shape-only-seed discipline). A green gate here proves the Ibis
  expression is self-consistent, NOT that it reproduces the legacy value.

``data_wiring`` records whether the metric's inputs already live in a migrated
Parquet dataset (``migrated-column``) or whether the legacy input column is not yet
in the migrated store (``deferred-input-not-in-migrated-store``) — in the latter
case D1 lands the FORMULA + its anchor; D2 wires the live data.
"""

from __future__ import annotations

from typing import Any

import ibis

# ---------------------------------------------------------------------------
# staleness  (legacy: staleness_report.py — age_days = (now - ts)//86400)
# ---------------------------------------------------------------------------

_SECONDS_PER_DAY = 86400


def staleness_age_days(t: Any, now_unix: int) -> Any:
    """Days since the latest conda upload — the staleness core metric.

    Legacy (``staleness_report.py`` query loop)::

        r["age_days"] = (now - ts) // 86400 if ts else None

    ``ts`` falsy (NULL **or** 0) → NULL; otherwise integer floor-division. ``now`` is
    injected so the offline gate is deterministic. The result is cast to int64 so a
    Parquet round-trip that coerces ``latest_conda_upload`` to float (a nullable
    integer column becomes float64 through pandas/DuckDB) still yields the legacy
    integer day count.
    """
    ts = t.latest_conda_upload
    age = ((now_unix - ts) // _SECONDS_PER_DAY).cast("int64")
    return ibis.cases((ts.isnull() | (ts == 0), ibis.null()), else_=age)


# ---------------------------------------------------------------------------
# adoption stage  (legacy: adoption_stage.py::_classify — verbatim ported)
# ---------------------------------------------------------------------------


def adoption_stage(t: Any) -> Any:
    """Lifecycle stage classifier — faithful port of ``adoption_stage.py::_classify``.

    Legacy branch order (preserved EXACTLY, including the ``age = age_days or 99999``
    quirk where a falsy age — NULL or 0 — collapses to 99999)::

        if latest_upload_age_days is None and total_versions == 0: return "unknown"
        age = latest_upload_age_days or 99999
        if age > 730:          return "silent"
        if age > 365:          return "declining"
        if releases_30d >= 3:  return "bleeding-edge"
        if releases_30d >= 1:  return "stable"
        if age <= 365:         return "mature"
        return "unknown"

    The legacy CALL SITE coalesces both count args before ``_classify``
    (``adoption_stage.py:106`` — ``_classify(age_days, releases_30d or 0,
    total_versions or 0)``), so a brand-new package with NULL ``total_versions`` reaches
    the ``unknown`` first branch, not ``silent``. ``total_versions``/``releases_30d`` are
    therefore ``fill_null(0)``-coalesced here to keep that fidelity.
    """
    raw = t.latest_upload_age_days
    tv = t.total_versions.fill_null(0)  # call-site `total_versions or 0`
    rel = t.releases_30d.fill_null(0)  # call-site `releases_30d or 0`
    # `age_days or 99999`: falsy (NULL or 0) → 99999.
    age = ibis.cases((raw.isnull() | (raw == 0), 99999), else_=raw)
    return ibis.cases(
        (raw.isnull() & (tv == 0), "unknown"),
        (age > 730, "silent"),
        (age > 365, "declining"),
        (rel >= 3, "bleeding-edge"),
        (rel >= 1, "stable"),
        (age <= 365, "mature"),
        else_="unknown",
    )


# ---------------------------------------------------------------------------
# actionable scope  (legacy: v_actionable_packages view — conda_forge_atlas.py)
# ---------------------------------------------------------------------------


def is_actionable(t: Any) -> Any:
    """The ``v_actionable_packages`` membership predicate.

    Legacy (``conda_forge_atlas.py`` — ``CREATE VIEW v_actionable_packages``)::

        conda_name IS NOT NULL
        AND COALESCE(latest_status, 'active') = 'active'
        AND COALESCE(feedstock_archived, 0) = 0
    """
    return (
        t.conda_name.notnull()
        & (t.latest_status.fill_null("active") == "active")
        & (t.feedstock_archived.fill_null(0) == 0)
    )


# ---------------------------------------------------------------------------
# feedstock health  (legacy: feedstock_health.py --filter predicates)
# ---------------------------------------------------------------------------

# Legacy CI-red domain: gh_default_branch_status IN ('failure', 'error').
_CI_RED_STATES = ("failure", "error")


def ci_red(t: Any) -> Any:
    """CI red on the default branch.

    Legacy (``feedstock_health.py`` ``--filter ci-red``)::

        p.gh_default_branch_status IN ('failure', 'error')

    Declared over the migrated ``core_feedstock_health.ci_status`` column, which the
    B-wave shape port renamed from ``gh_default_branch_status``. The value DOMAIN is
    ASSUMED identical ({'failure','error',...}) and FLAGGED for legacy recapture — the
    migrated node is a shape port (§ PARITY_NOTES B-seeds), so this is anchored to the
    migrated column, not a credentialed legacy capture.

    AUD-ATLAS-012: a NULL ``ci_status`` (CI state never observed) must NOT read as
    CI-red — the legacy predicate is a ``--filter``, where a NULL simply fails to match
    and is therefore not ci-red. ``.fill_null(False)`` restores that parity, matching the
    sibling predicates below in effect (not mechanism): ``has_open_prs`` /
    ``has_open_issues`` coalesce their NULL-prone *inputs* (``fill_null(0) > 0``), while
    here the coalesce is on the membership test's *output*, since ``NULL.isin(...)``
    yields NULL, not False.
    """
    return t.ci_status.isin(_CI_RED_STATES).fill_null(False)


def has_open_prs(t: Any) -> Any:
    """Feedstock has open PRs.

    Legacy split this into ``--filter open-pr`` (``bot_open_pr_count > 0``, bot-only,
    Phase M) and ``--filter open-prs-human`` (``gh_open_prs_count > 0``, Phase N). The
    migrated ``core_feedstock_health.open_prs`` column does NOT preserve the bot vs
    human distinction, so this collapses to ``open_prs > 0`` and is FLAGGED for legacy
    recapture (the bot/human split needs the un-ported Phase M/N columns).
    """
    return t.open_prs.fill_null(0) > 0


def has_open_issues(t: Any) -> Any:
    """Feedstock has open issues.

    Legacy (``feedstock_health.py`` ``--filter open-issues``)::

        COALESCE(p.gh_open_issues_count, 0) > 0

    Declared over the migrated ``core_feedstock_health.open_issues`` column. The
    ``gh_open_issues_count → open_issues`` rename is a B-wave shape port (unverified),
    so this is FLAGGED for legacy recapture like the other health filters — a green gate
    proves the predicate is self-consistent, not that the migrated column equals the
    legacy signal.
    """
    return t.open_issues.fill_null(0) > 0


# ---------------------------------------------------------------------------
# release trend  (legacy: release_cadence.py::_classify — verbatim ported)
# ---------------------------------------------------------------------------


def release_trend_label(t: Any) -> Any:
    """Release-cadence trend classifier — faithful port of
    ``release_cadence.py::_classify(r30, r90, r365)``.

    Legacy branch order (preserved EXACTLY)::

        if r365 == 0: return "silent"
        older_60 = max(0, r90 - r30)
        if r30 == 0 and older_60 == 0:
            if r365 == 1: return "one-version"
            return "decelerating"
        if older_60 == 0: return "accelerating"
        ratio = r30 / older_60
        if ratio >= 1.5: return "accelerating"
        if ratio <= 0.7: return "decelerating"
        return "stable"

    Declared over ``releases_30d`` / ``releases_90d`` / ``releases_365d`` (each
    ``fill_null(0)``-coalesced — the legacy call site always passes int counts,
    never NULL). Integer division would truncate the ratio, so ``r30`` /
    ``older_60`` are cast to float64 before dividing (a 0/0 division degrades to
    NaN, never raises, and the CASE branch order never selects that value).
    """
    r30 = t.releases_30d.fill_null(0)
    r90 = t.releases_90d.fill_null(0)
    r365 = t.releases_365d.fill_null(0)
    older_60 = ibis.greatest(0, r90 - r30)
    ratio = r30.cast("float64") / older_60.cast("float64")
    return ibis.cases(
        (r365 == 0, "silent"),
        ((r30 == 0) & (older_60 == 0) & (r365 == 1), "one-version"),
        ((r30 == 0) & (older_60 == 0), "decelerating"),
        (older_60 == 0, "accelerating"),
        (ratio >= 1.5, "accelerating"),
        (ratio <= 0.7, "decelerating"),
        else_="stable",
    )


# ---------------------------------------------------------------------------
# python_min bump-safety  (legacy: pyver_breakdown.py::policy_check_status)
# ---------------------------------------------------------------------------


def _python_minor(col: Any) -> Any:
    """Extract the minor-version integer out of a ``3.X`` string column.

    A regex MISS (a malformed value like ``"garbage"`` or ``"3.9.1"``) extracts
    to an EMPTY STRING on the DuckDB backend, not NULL — casting ``''`` straight
    to int64 raises ``duckdb.ConversionException`` (NOT a ``TypeError``, so
    ``_bsl_query_or_empty``'s ``except TypeError`` degrade path would not catch
    it, crashing the whole query instead of degrading honestly). ``.nullif("")``
    folds that miss to NULL BEFORE the cast, so the empty-string case round-trips
    to NULL exactly like a genuinely missing value.
    """
    return col.re_extract(r"^3\.(\d+)$", 1).nullif("").cast("int64")


def python_min_bump_status(t: Any) -> Any:
    """Declared-vs-empirical python_min classifier — faithful port of
    ``pyver_breakdown.py::policy_check_status(declared, empirical)``.

    Legacy (minor-version tuple comparison, py2/py4 out of scope — every input
    is assumed ``3.X``)::

        if declared is None or empirical is None: return "unknown"
        if empirical > declared: return "bump-safe"
        if empirical < declared: return "aggressive"
        return "aligned"

    Declared over ``declared_python_min`` / ``empirical_floor`` (both ``3.X``
    strings). NULL passes through ``_python_minor`` as NULL; a malformed,
    non-NULL value that doesn't match ``3\\.(\\d+)`` (e.g. ``"garbage"`` or
    ``"3.9.1"``) extracts to an empty string on DuckDB, which ``_python_minor``'s
    ``.nullif("")`` folds to NULL too — so the ``isnull()`` guard below covers
    both the missing-value and malformed-value cases the same way the legacy
    ``is None`` check does, and neither case ever raises.
    """
    d = _python_minor(t.declared_python_min)
    e = _python_minor(t.empirical_floor)
    return ibis.cases(
        (d.isnull() | e.isnull(), "unknown"),
        (e > d, "bump-safe"),
        (e < d, "aggressive"),
        else_="aligned",
    )


# ---------------------------------------------------------------------------
# Provenance registry (DW-B1-1 honesty — every declared metric is classified)
# ---------------------------------------------------------------------------

# provenance ∈ {"legacy-formula", "migrated-node-derived-flag-recapture"}
# data_wiring ∈ {"migrated-column", "deferred-input-not-in-migrated-store"}
METRIC_PROVENANCE: dict[str, dict[str, str]] = {
    "staleness_age_days": {
        "kind": "dimension",
        "legacy_source": "staleness_report.py (query loop age_days)",
        "provenance": "legacy-formula",
        "data_wiring": "deferred-input-not-in-migrated-store",
        "note": "latest_conda_upload is not yet a migrated Parquet column; D1 lands "
        "the (now-ts)//86400 formula + its legacy anchor, D2 wires the column.",
    },
    "adoption_stage": {
        "kind": "dimension",
        "legacy_source": "adoption_stage.py::_classify",
        "provenance": "legacy-formula",
        "data_wiring": "deferred-input-not-in-migrated-store",
        "note": "age/releases_30d/total_versions derive from per-version upload times; "
        "migrated core_version_download_history lacks upload_unix. Formula ported "
        "verbatim + anchored; D2 wires the inputs.",
    },
    "is_actionable": {
        "kind": "dimension",
        "legacy_source": "conda_forge_atlas.py (v_actionable_packages view)",
        "provenance": "legacy-formula",
        "data_wiring": "migrated-column",
        "note": "latest_status from core_latest_status; feedstock_archived joinable "
        "from vcs_archived_feedstocks. Predicate ported verbatim from the view DDL.",
    },
    "downloads_total": {
        "kind": "measure",
        "legacy_source": "core/nodes.py::compute_downloads (downloads_total)",
        "provenance": "legacy-formula",
        "data_wiring": "migrated-column",
        "note": "core_downloads.downloads_total — a per-package sum; the BSL measure re-aggregates it with sum().",
    },
    "downloads_30d": {
        "kind": "measure",
        "legacy_source": "core/nodes.py::compute_downloads (downloads_30d, latest month)",
        "provenance": "legacy-formula",
        "data_wiring": "migrated-column",
        "note": "core_downloads.downloads_30d — latest calendar month (not rolling).",
    },
    "ci_red": {
        "kind": "dimension",
        "legacy_source": "feedstock_health.py --filter ci-red",
        "provenance": "migrated-node-derived-flag-recapture",
        "data_wiring": "migrated-column",
        "note": "gh_default_branch_status IN ('failure','error') mapped onto the "
        "migrated ci_status column; value domain assumed identical, needs recapture. "
        "NULL ci_status coalesces to FALSE (AUD-ATLAS-012 .fill_null) — an unobserved "
        "CI state is not ci-red, matching the legacy --filter's NULL-excludes semantics.",
    },
    "has_open_prs": {
        "kind": "dimension",
        "legacy_source": "feedstock_health.py --filter open-pr / open-prs-human",
        "provenance": "migrated-node-derived-flag-recapture",
        "data_wiring": "migrated-column",
        "note": "migrated open_prs loses the bot(Phase M) vs human(Phase N) split; "
        "collapsed to open_prs>0, flagged for recapture.",
    },
    "has_open_issues": {
        "kind": "dimension",
        "legacy_source": "feedstock_health.py --filter open-issues",
        "provenance": "migrated-node-derived-flag-recapture",
        "data_wiring": "migrated-column",
        "note": "COALESCE(gh_open_issues_count,0)>0 predicate ported onto the migrated "
        "open_issues column; the gh_open_issues_count→open_issues rename is a B-wave "
        "shape port (unverified), so flagged for recapture like the other health filters.",
    },
    "maintainer": {
        "kind": "dimension",
        "legacy_source": "package_maintainers ⋈ maintainers (staleness/feedstock-health --maintainer X JOINs)",
        "provenance": "legacy-formula",
        "data_wiring": "migrated-column",
        "note": "First-class dimension over vcs_package_maintainers ⋈ vcs_maintainers; "
        "the raw-SQL maintainer JOINs become declared BSL join queries (AD-8).",
    },
    "release_trend_label": {
        "kind": "dimension",
        "legacy_source": "release_cadence.py::_classify",
        "provenance": "legacy-formula",
        "data_wiring": "deferred-input-not-in-migrated-store",
        "note": "releases_30d/90d/365d are not yet a migrated Parquet column (Story 20.5 "
        "ports the release-cadence CLI page); D1/D2-style split holds: the formula lands "
        "now, the live column lands when the release_cadence dataset materializes.",
    },
    "python_min_bump_status": {
        "kind": "dimension",
        "legacy_source": "pyver_breakdown.py::policy_check_status",
        "provenance": "legacy-formula",
        "data_wiring": "deferred-input-not-in-migrated-store",
        "note": "declared_python_min/empirical_floor are not yet migrated columns (Story "
        "20.5 ports the distribution-breakdown page's python-version --policy-check "
        "facet); formula ported verbatim, live columns land with the dataset.",
    },
}

# ---------------------------------------------------------------------------
# identity ops  (Story 22.3 — ranked export presence / issue / build signals)
# ---------------------------------------------------------------------------


def has_open_teams_issue(t: Any) -> Any:
    """Package has an OpenTeams packaging-issue URL (null-safe, blank → false)."""
    return (t.OpenTeams_Issue_URL.fill_null("") != "").fill_null(False)


def has_feedstock(t: Any) -> Any:
    """Package has a conda-forge feedstock URL (null-safe, blank → false)."""
    return (t["Conda-Forge_FeedStock_URL"].fill_null("") != "").fill_null(False)


def has_staged_pr(t: Any) -> Any:
    """Package has a staged-recipes PR URL (null-safe, blank → false)."""
    return (t.Staged_Recipes_PR_URL.fill_null("") != "").fill_null(False)


def has_local_recipe(t: Any) -> Any:
    """Package has a local-recipes URL (null-safe, blank → false)."""
    return (t.Local_Recipes_URL.fill_null("") != "").fill_null(False)


def identity_local_build_status(t: Any) -> Any:
    """Normalize blank ``Local_Build_Status`` to ``blank`` (write_ops_canvas semantics)."""
    raw = t.Local_Build_Status.fill_null("")
    return (raw == "").ifelse("blank", raw)


# ---------------------------------------------------------------------------
# identity workbook  (Story 22.4 — JFROG × verification bucket classification)
# ---------------------------------------------------------------------------


def identity_is_pypi_verified(t: Any) -> Any:
    """PyPI verification per ``write_workbook_canvas`` ``is_pypi`` (null-safe)."""
    return ((t.primary_type.fill_null("") == "pypi") | t.primary_purl.fill_null("").startswith("pkg:pypi/")).fill_null(
        False
    )


def identity_is_cf_verified(t: Any) -> Any:
    """conda-forge verification per ``write_workbook_canvas`` ``is_cf`` (null-safe)."""
    return ((t["Conda-Forge_FeedStock_URL"].fill_null("") != "") | (t.conda_purl.fill_null("") != "")).fill_null(False)


def verification_match_bucket(t: Any) -> Any:
    """``jfrogMap`` bucket: ``both`` / ``pypi_only`` / ``cf_only`` / ``neither``."""
    pypi = identity_is_pypi_verified(t)
    cf = identity_is_cf_verified(t)
    return (pypi & cf).ifelse(
        "both",
        pypi.ifelse("pypi_only", cf.ifelse("cf_only", "neither")),
    )


# Legacy feedstock-health filters that the migrated shape port does NOT carry, so
# D1 deliberately does NOT declare them (would require fabricating a legacy signal).
# Documented here + asserted by the provenance test so the gap is explicit, not silent.
DEFERRED_FEEDSTOCK_HEALTH_FILTERS: dict[str, str] = {
    "stuck": "bot_version_errors_count > 0 — Phase M column not in core_feedstock_health.",
    "bad": "feedstock_bad = 1 — Phase M column not in core_feedstock_health.",
}
