#!/usr/bin/env python3
"""
Offline PyPI-version source backed by the conda-forge bot's graph.

Phase H normally fetches `pypi.org/pypi/<name>/json` per row. The bot's
`version_pr_info` archive that Phase E already downloads
(`.claude/data/conda-forge-expert/cf-graph-version_pr_info.tar.gz`, from
`conda-forge/conda-forge-bot-data-version_pr_info`; see `_cf_graph_source`)
holds one `<feedstock>.json` per feedstock whose `new_version` field is the
conda-forge autotick-bot's view of upstream. That signal is the bulk-load
shortcut for Phase H: zero network, zero auth, ~1-2 min wall clock versus
~30 min of pypi.org fan-out. A cache in the pre-split combined layout
(`cf-graph-countyfair.tar.gz` with `version_pr_info/` inside) still reads.

Trade-off: cf-graph lags pypi.org by hours-to-days (bot polling cadence),
and it does NOT carry PEP 592 yanked status. Rows populated from cf-graph
get `pypi_version_source='cf-graph'` and `pypi_current_version_yanked` left
NULL so consumers can opt into a `pypi-json` rerun for strict yank checks.

Private module (underscore-prefixed) — not exposed as a CLI.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).parent))

import _cf_graph_source as _cfgs  # type: ignore[import-not-found]  # noqa: E402

_KIND = "version_pr_info"


def _data_dir() -> Path:
    # _paths walks to the repo root by marker; the pre-2026-10 hand-rolled
    # four-parent walk lives on only as the fallback when that walk fails.
    from _paths import get_data_dir  # type: ignore[import-not-found]

    return get_data_dir() or (
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "conda-forge-expert"
    )


def default_tarball_path() -> Path:
    """The cache Phase E populates: the split archive, else the legacy combined one.

    Returns the split path when neither exists, so "missing" names the file
    Phase E would write.
    """
    data_dir = _data_dir()
    return _cfgs.source_path(data_dir, _KIND) or _cfgs.split_cache_path(data_dir, _KIND)


def tarball_available(path: Path | None = None) -> bool:
    """True iff the cf-graph tarball exists and is non-empty."""
    path = path or default_tarball_path()
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def iter_feedstock_versions(
    path: Path | None = None,
) -> Iterator[tuple[str, str]]:
    """Yield `(feedstock_name, new_version)` for every shard with a version.

    Reads the tarball in a single streaming pass. Shards whose `new_version`
    is missing, null, false (cf-graph's "no upstream detected" sentinel), or
    obviously malformed are skipped silently — the contract is "bulk-load
    what we can; pypi-json source handles the rest."
    """
    path = path or default_tarball_path()
    if not tarball_available(path):
        return

    for feedstock, payload in _cfgs.iter_tar_records(path, _KIND):
        new_version = payload.get("new_version")
        if not isinstance(new_version, str) or not new_version:
            continue
        yield feedstock, new_version


def has_version_records(path: Path | None = None) -> bool:
    """True when the tarball holds at least one version_pr_info record.

    A cache that holds none (the 2026-10 redirect of regro/cf-graph-countyfair
    to conda-forge/conda-forge-bot-data served such an archive) must not be
    read as "the bot found no upstream for every feedstock".
    """
    path = path or default_tarball_path()
    return tarball_available(path) and _cfgs.has_records(path, _KIND)


def build_pypi_version_map(
    pypi_name_by_feedstock: dict[str, str],
    *,
    path: Path | None = None,
) -> dict[str, str]:
    """Project the cf-graph stream into `{pypi_name: new_version}`.

    `pypi_name_by_feedstock` is the join key — caller supplies it from
    `packages.feedstock_name` → `packages.pypi_name`. Feedstocks without a
    PyPI mapping (npm, CRAN, etc.) are filtered out implicitly.
    """
    out: dict[str, str] = {}
    for feedstock, version in iter_feedstock_versions(path=path):
        pypi_name = pypi_name_by_feedstock.get(feedstock)
        if not pypi_name:
            continue
        # First write wins; cf-graph has at most one shard per feedstock so
        # collisions only happen when two feedstocks share a pypi_name
        # (extremely rare; resolved by leaving the first match in place).
        out.setdefault(pypi_name, version)
    return out
