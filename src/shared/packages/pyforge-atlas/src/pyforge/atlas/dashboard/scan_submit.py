"""The two live-scan pages' submit path (Story 27.3, closing DW-FU-20-5-2).

``scan-project`` and ``env-inspect`` are the one page pair DESIGN.md § 3.6/3.7
marks ``live-scan-artifact``: the dashboard itself submits the per-invocation
scan on user input, rather than only surfacing a cached report (the FR-9 shape
the ``report-artifact`` pages keep). This module is that submit path, and the
only place in the dashboard that starts a process.

Process seam (AD-4): every invocation goes through
:class:`pyforge.core.process.PosixProcess` — the one sanctioned subprocess
seam. This package imports ``subprocess`` nowhere outside
``query_plane_boot.py``'s single exempted launch site, and
``tests/unit/catalog/test_no_inline_io.py`` keeps it that way.

Neither CLI is importable from the atlas package: both are shipped scripts
under ``.claude/skills/conda-forge-expert/scripts/`` and each declares the pixi
env it needs, so each is invoked by its own pixi task
(``pixi run -e <env> <task> …``), exactly as an operator would run it.

The CLIs' ``--json`` payloads are reshaped by PURE functions — one per page —
into exactly the columns that page's BSL loader declares, then written to the
page's own cached Parquet, the same file :mod:`pyforge.atlas.dashboard.data`
reads. Nothing here re-implements a metric and nothing fabricates a row: a
payload that does not carry a field leaves it null.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from . import data as _data

# Each page's CLI invocation(s). A tuple of argv tails because `env-inspect`'s
# two declared column groups (licenses, security) are two of its modes.
# `env-inspect` runs its script in `pyforge-guild`: only the guild env exists at runtime, never the
# `local-recipes` recipe-factory env (spec-pyforge-steward CAP-152; steward's
# test_no_station_assumes_local_recipes.py). The script needs nothing the guild env lacks.
_ENV_INSPECT = ("pixi", "run", "-e", "pyforge-guild", "python", ".claude/scripts/conda-forge-expert/env_inspect.py")
SCAN_INVOCATIONS: dict[str, tuple[tuple[str, ...], ...]] = {
    "scan-project": (("pixi", "run", "-e", "vuln-db", "scan-project", "{path}", "--json"),),
    "env-inspect": (
        (*_ENV_INSPECT, "--prefix", "{path}", "--licenses", "--json"),
        (*_ENV_INSPECT, "--prefix", "{path}", "--security", "--json"),
    ),
}

SCAN_PARQUETS: dict[str, str] = {
    "scan-project": _data.SCAN_RESULT_LATEST_PARQUET,
    "env-inspect": _data.ENV_INSPECT_LATEST_PARQUET,
}

SCAN_PROJECT_COLUMNS = ("conda_name", "severity", "license_spdx", "fix_available", "scan_status", "finding_count")
ENV_INSPECT_COLUMNS = ("conda_name", "license_spdx", "non_permissive_flag", "vuln_critical", "vuln_high")


@dataclass(frozen=True)
class ScanSubmission:
    """One submit's outcome — the value the page's status component renders.

    ``status`` is ``"refused"`` (the input never reached a process),
    ``"failed"`` (the CLI ran and did not succeed, or its payload was
    unreadable) or ``"ok"``. ``frame`` is the refreshed page data on ``"ok"``
    and ``None`` otherwise, so a failed submit never replaces a good cache.
    """

    status: str
    message: str
    frame: pd.DataFrame | None = None
    parquet: Path | None = None


def _refused(message: str) -> ScanSubmission:
    return ScanSubmission(status="refused", message=message)


def _failed(message: str) -> ScanSubmission:
    return ScanSubmission(status="failed", message=message)


def _severity_of(vuln: Any) -> str:
    if isinstance(vuln, dict):
        raw = vuln.get("severity")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return "Unknown"


def _dep_key_name(dep_key: str) -> str:
    """``"conda:numpy@1.26.0"`` -> ``"numpy"``; the key shape scan_project.py's
    own ``lookup_vulns`` builds (``f"{ecosystem}:{name}@{version}"``)."""
    _, _, tail = dep_key.partition(":")
    name, _, _ = tail.partition("@")
    return name or dep_key


def normalize_scan_project(payload: dict[str, Any]) -> pd.DataFrame:
    """``scan-project --json`` -> the page's declared columns.

    One row per (package, severity): ``finding_count`` is how many of that
    package's vulnerabilities carry that severity, and a package with no
    vulnerabilities still gets its row at severity ``"None"`` with count 0 —
    a clean scan is a result, not an absence. ``license_spdx`` comes from the
    atlas record the CLI already attached; it is null when the CLI did not
    carry one, never guessed.
    """
    deps = payload.get("deps") or []
    vulns_by_dep = payload.get("vulns_by_dep") or {}
    atlas_records = payload.get("atlas_records") or {}

    licenses: dict[str, Any] = {}
    if isinstance(atlas_records, dict):
        for key, record in atlas_records.items():
            if isinstance(record, dict):
                licenses[_dep_key_name(str(key))] = record.get("license_spdx") or record.get("license")

    fixed: dict[str, bool] = {}
    counts: dict[tuple[str, str], int] = {}
    if isinstance(vulns_by_dep, dict):
        for key, vulns in vulns_by_dep.items():
            name = _dep_key_name(str(key))
            for vuln in vulns or []:
                severity = _severity_of(vuln)
                counts[(name, severity)] = counts.get((name, severity), 0) + 1
                if isinstance(vuln, dict) and (vuln.get("fixed_version") or vuln.get("fix_available")):
                    fixed[name] = True

    scanned = [str(dep.get("name")) for dep in deps if isinstance(dep, dict) and dep.get("name")]
    for name in scanned:
        if not any(key[0] == name for key in counts):
            counts[(name, "None")] = 0

    rows = [
        {
            "conda_name": name,
            "severity": severity,
            "license_spdx": licenses.get(name),
            "fix_available": bool(fixed.get(name, False)),
            "scan_status": "clean" if severity == "None" else "vulnerable",
            "finding_count": count,
        }
        for (name, severity), count in sorted(counts.items())
    ]
    return pd.DataFrame(rows, columns=list(SCAN_PROJECT_COLUMNS))


def normalize_env_inspect(licenses_payload: dict[str, Any], security_payload: dict[str, Any]) -> pd.DataFrame:
    """``env-inspect --licenses --json`` + ``--security --json`` -> the page's
    declared columns, joined on the package name both modes key their rows by.

    A package present in only one of the two payloads keeps nulls for the
    other's columns rather than a zero that would read as "scanned, clean".
    """
    by_name: dict[str, dict[str, Any]] = {}
    for row in licenses_payload.get("rows") or []:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        by_name.setdefault(str(row["name"]), {})["license_spdx"] = row.get("license")
        by_name[str(row["name"])]["non_permissive_flag"] = row.get("class") == "non_permissive"
    for row in security_payload.get("rows") or []:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        entry = by_name.setdefault(str(row["name"]), {})
        entry["vuln_critical"] = row.get("critical")
        entry["vuln_high"] = row.get("high")

    rows = [
        {
            "conda_name": name,
            "license_spdx": entry.get("license_spdx"),
            "non_permissive_flag": entry.get("non_permissive_flag"),
            "vuln_critical": entry.get("vuln_critical"),
            "vuln_high": entry.get("vuln_high"),
        }
        for name, entry in sorted(by_name.items())
    ]
    return pd.DataFrame(rows, columns=list(ENV_INSPECT_COLUMNS))


def _write_parquet(frame: pd.DataFrame, target: Path) -> None:
    """Replace the cached result in one step, so a reader never sees a half file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(f".{target.name}.staging")
    frame.to_parquet(staging, index=False)
    os.replace(staging, target)


def submit_scan(
    page_id: str,
    path_value: str | None,
    *,
    data_root: str | Path,
    process: ProcessPort | None = None,
    repo_root: str | Path | None = None,
    timeout_s: float | None = 900.0,
) -> ScanSubmission:
    """Run ``page_id``'s scan over ``path_value`` and refresh the page's cache.

    Refuses — without starting anything — an unknown page, an empty path, or a
    path that does not exist. A non-zero exit or an unreadable payload is a
    ``"failed"`` submission that leaves the previous cached result in place.
    """
    if page_id not in SCAN_INVOCATIONS:
        return _refused(f"`{page_id}` is not a live-scan page.")
    if not path_value or not str(path_value).strip():
        return _refused("Enter a path to scan, then press Run.")

    target = Path(str(path_value).strip()).expanduser()
    if not target.exists():
        return _refused(f"`{target}` does not exist on this host — nothing was run.")

    runner = process if process is not None else PosixProcess()
    cwd = Path(repo_root) if repo_root is not None else Path.cwd()

    payloads: list[dict[str, Any]] = []
    for argv_template in SCAN_INVOCATIONS[page_id]:
        argv = [part.replace("{path}", str(target)) for part in argv_template]
        try:
            result = runner.run(argv, cwd=cwd, timeout_s=timeout_s)
        except ProcessError as exc:
            return _failed(f"`{' '.join(argv)}` could not be run: {exc}")
        if result.returncode != 0:
            tail = (result.stderr or result.stdout or "").strip().splitlines()[-1:] or ["no output"]
            return _failed(f"`{' '.join(argv)}` exited {result.returncode}: {tail[0]}")
        try:
            payload = json.loads(result.stdout)
        except ValueError as exc:
            return _failed(f"`{' '.join(argv)}` did not emit readable JSON: {exc}")
        if not isinstance(payload, dict):
            return _failed(f"`{' '.join(argv)}` emitted a {type(payload).__name__}, not a JSON object.")
        payloads.append(payload)

    frame = normalize_scan_project(payloads[0]) if page_id == "scan-project" else normalize_env_inspect(*payloads)
    parquet = Path(data_root) / SCAN_PARQUETS[page_id]
    _write_parquet(frame, parquet)
    return ScanSubmission(
        status="ok",
        message=f"Scanned `{target}` — {len(frame)} row(s) written to `{SCAN_PARQUETS[page_id]}`.",
        frame=frame,
        parquet=parquet,
    )
