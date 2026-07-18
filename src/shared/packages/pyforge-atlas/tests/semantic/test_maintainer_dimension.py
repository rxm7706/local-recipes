"""Maintainer ⋈ as a first-class BSL dimension (Story D1, AC-2).

Proves the migrated ``vcs_package_maintainers`` (conda_name ⋈ maintainer) + the packages
model compose into a DECLARED BSL query: ``staleness-report --maintainer X`` /
``feedstock-health --maintainer X`` become a filter/group-by on the ``maintainer``
dimension, not a hand-written SQL JOIN (AD-8). The expected values are computed by an
INDEPENDENT pandas groupby over the same input frames (never via the BSL layer).
"""

from __future__ import annotations

import ibis
import pandas as pd

from pyforge.atlas.semantic import models

NOW = 1_700_000_000


def _packages_df():
    return pd.DataFrame(
        {
            "conda_name": ["a", "b", "c"],
            "latest_status": ["active", "active", "active"],
            "feedstock_archived": pd.array([0, 0, 0], dtype="Int64"),
            "latest_conda_upload": pd.array([NOW, NOW, NOW], dtype="Int64"),
            "downloads_total": pd.array([100, 200, 300], dtype="Int64"),
            "downloads_30d": pd.array([1, 2, 3], dtype="Int64"),
            "latest_upload_age_days": pd.array([1, 1, 1], dtype="Int64"),
            "releases_30d": pd.array([0, 0, 0], dtype="Int64"),
            "total_versions": pd.array([1, 1, 1], dtype="Int64"),
        }
    )


def _pm_df():
    # alice ⋈ {a,b}; bob ⋈ {a}; carol ⋈ {c}
    return pd.DataFrame(
        {
            "conda_name": ["a", "a", "b", "c"],
            "maintainer": ["alice", "bob", "alice", "carol"],
        }
    )


def test_duplicate_long_form_rows_do_not_double_count(parquet_table):
    """Reviewer-B NIT: the raw vcs_package_maintainers long form can legitimately carry
    duplicate (conda_name, maintainer) rows; a maintainer-scoped download SUM must NOT
    double-count them, and package_count must dedupe. Load-bearing for the ⋈."""
    pm_dupe = pd.DataFrame(
        {"conda_name": ["a", "a", "b"], "maintainer": ["alice", "alice", "alice"]}
    )  # (a, alice) appears twice
    packages = models.build_packages_model(parquet_table(_packages_df(), "pkg"), now_unix=NOW)
    pm = models.build_package_maintainers_model(parquet_table(pm_dupe, "pm"))
    join = models.join_packages_by_maintainer(packages, pm)
    res = join.query(
        dimensions=["maintainer"], measures=["packages.downloads_total"]
    ).execute()
    downloads = {r["maintainer"]: r["packages.downloads_total"] for _, r in res.iterrows()}
    # alice ⋈ {a(100), b(200)} — a is duplicated in the long form but must sum to 300,
    # NOT 400 (no double-count from the dupe row).
    assert int(downloads["alice"]) == 300
    # package_count nunique-dedupes the dupe: alice maintains 2 distinct packages.
    pcm = models.build_package_maintainers_model(parquet_table(pm_dupe, "pm2"))
    counts = {
        r["maintainer"]: int(r["package_count"])
        for _, r in pcm.query(dimensions=["maintainer"], measures=["package_count"]).execute().iterrows()
    }
    assert counts["alice"] == 2


def test_maintainer_is_a_declared_dimension(parquet_table):
    pm = parquet_table(_pm_df(), "pm")
    model = models.build_package_maintainers_model(pm)
    assert "maintainer" in model.get_dimensions()

    # group-by maintainer → package_count, anchored to an independent pandas groupby.
    got = {
        r["maintainer"]: int(r["package_count"])
        for _, r in model.query(dimensions=["maintainer"], measures=["package_count"]).execute().iterrows()
    }
    expected = _pm_df().groupby("maintainer")["conda_name"].nunique().to_dict()
    assert got == expected


def test_maintainer_scoped_downloads_is_a_declared_join(parquet_table):
    packages = models.build_packages_model(parquet_table(_packages_df(), "pkg"), now_unix=NOW)
    pm = models.build_package_maintainers_model(parquet_table(_pm_df(), "pm"))
    join = models.join_packages_by_maintainer(packages, pm)

    got = {
        r["maintainer"]: int(r["packages.downloads_total"])
        for _, r in join.query(
            dimensions=["maintainer"], measures=["packages.downloads_total"]
        ).execute().iterrows()
    }

    # INDEPENDENT anchor: the raw-SQL JOIN consumers write today, in pandas.
    merged = _pm_df().merge(_packages_df(), on="conda_name")
    expected = merged.groupby("maintainer")["downloads_total"].sum().astype(int).to_dict()
    assert got == expected  # alice=300, bob=100, carol=300


def test_maintainer_filter_reproduces_maintainer_scoped_list(parquet_table):
    """`--maintainer alice` → the set of a maintainer's packages via a BSL filter.

    The maintainer-scoped LIST is a filter on the first-class ``maintainer`` dimension of
    the ``package_maintainers`` model — the declared-query form of the raw SQL
    ``... JOIN package_maintainers ... WHERE handle=X`` consumers write today.
    """
    pm = models.build_package_maintainers_model(parquet_table(_pm_df(), "pm"))

    res = pm.query(
        dimensions=["conda_name"], filters=[ibis._.maintainer == "alice"]
    ).execute()
    got = set(res["conda_name"])
    expected = set(_pm_df().loc[_pm_df()["maintainer"] == "alice", "conda_name"])
    assert got == expected == {"a", "b"}


def test_maintainer_with_no_packages_and_package_with_no_maintainer(parquet_table):
    """Reviewer B edge: an orphan maintainer + an unmaintained package.

    A package with a NULL maintainer DOES form a real ``None``-keyed group in the
    maintainer-scoped surface (it is present, not absent) — but its value is NULL, never
    a fabricated number, so no real package's metric is misattributed to a null
    maintainer. Both the ``None`` group's NULL value AND the fact that no real package's
    downloads land under it are asserted below (Reviewer-B NIT: the earlier "asserted by
    absence" claim was inaccurate — the group is present with a NULL value).
    """
    pm_df = pd.DataFrame(
        {"conda_name": ["a", "orphanpkg_has_no_maint"], "maintainer": ["alice", None]}
    )
    # 'zzz' maintains nothing that exists in packages.
    pm_df = pd.concat(
        [pm_df, pd.DataFrame({"conda_name": ["ghost"], "maintainer": ["zzz"]})],
        ignore_index=True,
    )
    packages = models.build_packages_model(parquet_table(_packages_df(), "pkg"), now_unix=NOW)
    pm = models.build_package_maintainers_model(parquet_table(pm_df, "pm"))
    join = models.join_packages_by_maintainer(packages, pm)

    # a maintainer (zzz) whose only package is absent from `packages` yields NULL
    # downloads on a left join — never a fabricated 0 attributed to a real package.
    res = join.query(
        dimensions=["maintainer"], measures=["packages.downloads_total"]
    ).execute()
    downloads = {r["maintainer"]: r["packages.downloads_total"] for _, r in res.iterrows()}
    assert int(downloads["alice"]) == 100  # alice ⋈ a(100) only, in this frame
    # zzz's package 'ghost' is not in packages → its downloads sum is NULL, not 100.
    assert pd.isna(downloads.get("zzz"))
    # the NULL-maintainer package (orphanpkg) forms a real None group with a NULL value
    # (present, not absent) — and critically no REAL package's downloads (e.g. a=100) are
    # attributed to it. `orphanpkg_has_no_maint` is itself not in `packages`, so its sum
    # is NULL, never a real download total mis-bucketed under the null maintainer.
    assert None in downloads  # the null-maintainer group IS present…
    assert pd.isna(downloads.get(None))  # …with a NULL value, never a fabricated number
    assert 100 not in {v for k, v in downloads.items() if k is None}
