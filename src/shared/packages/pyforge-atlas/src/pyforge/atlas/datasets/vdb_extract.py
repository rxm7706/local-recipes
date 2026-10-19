"""Story 34.7 (CAP-64): the vdb extractor, a standalone script for the ``vuln-db`` pixi env.

``VDBStoreDataset``'s live refresher runs it through ``pyforge.core.process`` as
``pixi run --frozen -e vuln-db python -I <this file> ...``. The ``vuln-db`` env has
``appthreat-vulnerability-db`` and ``pyarrow`` but not pyforge, so this file imports nothing
from pyforge: the standard library at module level, and ``vdb`` / ``pyarrow`` only inside
:func:`main`.

Two commands:

- ``age`` prints the vdb's age in seconds (from ``$VDB_HOME/vdb.meta``'s ``created_utc``), or
  ``-1`` when there is no vdb yet, so the refresher knows whether to run ``vdb-refresh``.
- ``extract --targets FILE --out FILE`` reads ``[[conda_name, pypi_name, version, npm_name,
  github_repo], ...]`` (the last two optional) and
  writes one parquet row per (package, vulnerability): ``package_name``, ``version``,
  ``cve_id``, ``cvss_score``, ``severity``, ``cwe_id``. ``version`` is the package's current
  version when a version-pinned purl matched (the vulnerability affects it), else null.

Legacy reference: Phase G (``phase_g_vdb_summary``, CFA:3771) queries the same purls per
package through ``detail_cf_atlas.fetch_vdb_data`` (DCA:499): ``pkg:pypi/<name>``,
``pkg:conda/<name>`` and ``pkg:npm/<name>``, each unpinned and pinned at the current version,
and ``pkg:github/<owner>/<repo>`` unpinned.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import warnings
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

COLUMNS = ["package_name", "version", "cve_id", "cvss_score", "severity", "cwe_id"]

_CVSS_KEYS = ("cvssV4_0", "cvssV4", "cvssV3_1", "cvssV3_0", "cvssV3", "cvssV2_0", "cvssV2")
_MAX_DEPTH = 8


def coerce_score(value: Any) -> float | None:
    """A CVSS base score as a float: vdb's model dump leaves ``{"root": x}``, a RootModel or an
    enum (legacy ``_coerce_cvss_score``)."""
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("root", value)
    value = getattr(value, "root", value)
    value = getattr(value, "value", value)
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def walk_cvss(obj: Any, depth: int = 0) -> tuple[float | None, str | None] | None:
    """The first CVSS block anywhere in a model dump: ``(score, severity)`` (legacy
    ``_walk_for_cvss``; NVD puts metrics under ``adp``, GHSA under ``cna``)."""
    if depth > _MAX_DEPTH:
        return None
    if isinstance(obj, dict):
        for key in _CVSS_KEYS:
            block = obj.get(key)
            if isinstance(block, dict) and block.get("baseScore") is not None:
                severity = block.get("baseSeverity")
                severity = severity.get("root") if isinstance(severity, dict) else severity
                label = str(severity).rsplit(".", 1)[-1].title() if severity else None
                return coerce_score(block.get("baseScore")), label
        children: Iterable[Any] = obj.values()
    elif isinstance(obj, list):
        children = obj
    else:
        return None
    for child in children:
        found = walk_cvss(child, depth + 1)
        if found:
            return found
    return None


def walk_cwe(obj: Any, depth: int = 0) -> str | None:
    """The first ``CWE-`` id anywhere in a model dump (legacy ``_walk_for_cwe``)."""
    if depth > _MAX_DEPTH:
        return None
    if isinstance(obj, dict):
        cwe = obj.get("cweId")
        if cwe and str(cwe).startswith("CWE-"):
            return str(cwe)
        children: Iterable[Any] = obj.values()
    elif isinstance(obj, list):
        children = obj
    else:
        return None
    for child in children:
        found = walk_cwe(child, depth + 1)
        if found:
            return found
    return None


def fields(result: dict[str, Any]) -> dict[str, Any]:
    """``cve_id``, ``cvss_score``, ``severity`` and ``cwe_id`` from one vdb search result."""
    out: dict[str, Any] = {"cve_id": result.get("cve_id"), "cvss_score": None, "severity": None, "cwe_id": None}
    data = result.get("source_data")
    if data is None or not hasattr(data, "model_dump"):
        return out
    try:
        dump = data.model_dump(exclude_none=True)
    except Exception:  # noqa: BLE001 -- vdb's partial dumps raise assorted pydantic errors
        return out
    cvss = walk_cvss(dump)
    if cvss:
        out["cvss_score"], out["severity"] = cvss
    out["cwe_id"] = walk_cwe(dump)
    return out


def purls(
    conda_name: str, pypi_name: str, version: str, npm_name: str = "", github_repo: str = ""
) -> list[tuple[str, bool]]:
    """``(purl, pinned)`` pairs, as legacy Phase G derives them (CFA:3771 via
    ``fetch_vdb_data``, DCA:520-541): PyPI, conda and npm, each unpinned and pinned at the
    current version, then the GitHub repo unpinned. ``pinned`` is explicit: legacy reads
    ``"@" in purl``, which counts a scoped npm name's ``@`` as a pin."""
    out: list[tuple[str, bool]] = []
    for ecosystem, name in (("pypi", pypi_name), ("conda", conda_name), ("npm", npm_name)):
        if not name:
            continue
        out.append((f"pkg:{ecosystem}/{name}", False))
        if version:
            out.append((f"pkg:{ecosystem}/{name}@{version}", True))
    if github_repo:
        out.append((f"pkg:github/{github_repo}", False))
    return out


def extract(
    targets: Iterable[list[str] | tuple[str, ...]],
    search: Callable[[str], Iterable[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], int]:
    """One row per (package, vulnerability id); ``version`` is set when a pinned purl matched.
    Returns the rows and the count of purl searches that raised (each skipped)."""
    rows: list[dict[str, Any]] = []
    errors = 0
    for target in targets:
        conda_name, pypi_name, version, npm_name, github_repo = (str(v or "") for v in [*target, "", ""][:5])
        if not conda_name:
            continue
        seen: dict[str, dict[str, Any]] = {}
        for purl, pinned in purls(conda_name, pypi_name, version, npm_name, github_repo):
            try:
                results = list(search(purl) or [])
            except Exception:  # noqa: BLE001 -- one bad purl never stops the extraction
                errors += 1
                continue
            for result in results:
                row = fields(result)
                vid = row["cve_id"]
                if not vid:
                    continue
                kept = seen.setdefault(vid, {"package_name": conda_name, "version": None, **row})
                if pinned:
                    kept["version"] = version
        rows.extend(seen.values())
    return rows, errors


def vdb_age_seconds(home: str | None, now: datetime.datetime | None = None) -> float:
    """Seconds since ``$VDB_HOME/vdb.meta``'s ``created_utc``; ``-1`` when there is none."""
    if not home:
        return -1.0
    try:
        meta = json.loads((Path(home) / "vdb.meta").read_text(encoding="utf-8"))
        created = datetime.datetime.fromisoformat(str(meta["created_utc"]))
    except OSError, ValueError, KeyError, TypeError:
        return -1.0
    if created.tzinfo is None:
        created = created.replace(tzinfo=datetime.UTC)
    return ((now or datetime.datetime.now(tz=datetime.UTC)) - created).total_seconds()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("age")
    ext = sub.add_parser("extract")
    ext.add_argument("--targets", required=True)
    ext.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    if args.command == "age":
        print(int(vdb_age_seconds(os.environ.get("VDB_HOME"))))
        return 0

    # vdb's partial model dumps warn once per field (PydanticSerializationUnexpectedValue); the
    # refresher captures stderr, so a full scan would carry megabytes of them
    warnings.simplefilter("ignore")
    import pyarrow as pa
    import pyarrow.parquet as pq
    from vdb.lib import search as vdb_search  # type: ignore[import-not-found, unused-ignore]

    targets = json.loads(Path(args.targets).read_text(encoding="utf-8"))
    rows, errors = extract(targets, lambda purl: vdb_search.search_by_purl_like(purl, with_data=True))
    table = pa.table({c: [r.get(c) for r in rows] for c in COLUMNS})
    pq.write_table(table, args.out)
    print(json.dumps({"targets": len(targets), "rows": len(rows), "search_errors": errors}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
