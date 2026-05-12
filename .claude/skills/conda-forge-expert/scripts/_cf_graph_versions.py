#!/usr/bin/env python3
"""
Offline PyPI-version source backed by the cf-graph-countyfair tarball.

Phase H normally fetches `pypi.org/pypi/<name>/json` per row. The cf-graph
tarball that Phase E already downloads (~150 MB at
`.claude/data/conda-forge-expert/cf-graph-countyfair.tar.gz`) contains
`version_pr_info/<sharded>/<feedstock>.json` shards whose `new_version` field
is the conda-forge autotick-bot's view of upstream. That signal is the bulk-
load shortcut for Phase H: zero network, zero auth, ~1-2 min wall clock
versus ~30 min of pypi.org fan-out.

Trade-off: cf-graph lags pypi.org by hours-to-days (bot polling cadence),
and it does NOT carry PEP 592 yanked status. Rows populated from cf-graph
get `pypi_version_source='cf-graph'` and `pypi_current_version_yanked` left
NULL so consumers can opt into a `pypi-json` rerun for strict yank checks.

Private module (underscore-prefixed) — not exposed as a CLI.
"""
from __future__ import annotations

import json
import sys
import tarfile
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).parent))


_DEFAULT_TARBALL_RELATIVE = Path("cf-graph-countyfair.tar.gz")
_VERSION_PR_INFO_MARKER = "/version_pr_info/"


def default_tarball_path() -> Path:
    """Return the canonical cache location Phase E populates."""
    base = Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"
    return base / _DEFAULT_TARBALL_RELATIVE


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

    with tarfile.open(path, "r:gz") as tf:
        for member in tf:
            if not member.isfile() or not member.name.endswith(".json"):
                continue
            if _VERSION_PR_INFO_MARKER not in member.name:
                continue
            feedstock = member.name.rsplit("/", 1)[-1][:-5]
            handle = tf.extractfile(member)
            if handle is None:
                continue
            try:
                payload = json.load(handle)
            except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                continue
            if not isinstance(payload, dict):
                continue
            new_version = payload.get("new_version")
            if not isinstance(new_version, str) or not new_version:
                continue
            yield feedstock, new_version


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
