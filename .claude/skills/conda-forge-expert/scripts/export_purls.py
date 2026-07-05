#!/usr/bin/env python3
"""
export-purls — Productized purl + mapping export (cyclonedx-universe-inventory
Wave A / S1; replaces the 2026-07-04 ad-hoc export).

Read-only exporter with two declared inputs — `cf_atlas.db` + the `recipes/`
tree — writing six artifacts into `--out-dir` (default: the skill data dir's
`purl-export/`):

  1. purls_conda-forge.txt            pkg:conda/{name}?channel=conda-forge
  2. purls_conda-forge_versioned.txt  …@{version}?channel=conda-forge
  3. purls_pypi.txt                   pkg:pypi/{name}   (G98 normalization)
  4. purls_conda-pypi_mapped.tsv      conda_purl · pypi_purl · match_source ·
                                      match_confidence (provenance passthrough)
  5. recipe-purl-exceptions.txt       pending-/blocked- recipes absent from
                                      the exports (D1: fold-both-sides lookup)
  6. purls_conda-upstream_mapped.tsv  conda_purl · upstream_purl ·
                                      upstream_source (non-PyPI upstreams)

Ordering contract (regression surface):
  • #1/#2/#4 sort by `conda_name` in C-locale — NEVER full-line sort (the
    `?` qualifier (0x3F) sorts after `-` (0x2D) and would flip name-prefix
    pairs like `foo` / `foo-bar`).
  • #3 is full-line C-sort; #5 by recipe dir; #6 by (conda_name, source).

purl conventions (G98): conda purls carry `?channel=conda-forge`; PyPI purl
names use purl-spec normalization — lowercase + `_`→`-`, dots PRESERVED
(PEP 503 over-normalizes dotted names). Folding (`[-_.]+` → `-`) is used for
MEMBERSHIP LOOKUP ONLY (D1), never for emission.

CLI:
  export-purls [--out-dir DIR] [--json]

Pixi:
  pixi run -e local-recipes export-purls -- --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

import yaml


def _get_data_dir() -> Path:
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"
DEFAULT_OUT_DIR = _get_data_dir() / "purl-export"
REPO_ROOT = Path(__file__).resolve().parents[4]
RECIPES_DIR = REPO_ROOT / "recipes"

CHANNEL_QUALIFIER = "?channel=conda-forge"


def g98_pypi_name(name: str) -> str:
    """purl-spec normalization for PyPI purl names: lowercase + `_`→`-`.

    Dots are PRESERVED (G98) — PEP 503 folding would over-normalize dotted
    project names (`fs.googledrivefs`) into identifiers that don't exist.
    """
    return name.lower().replace("_", "-")


def fold_name(name: str) -> str:
    """PEP-503-style fold for MEMBERSHIP LOOKUP ONLY (D1) — how PyPI itself
    resolves names. Never used for emission."""
    return re.sub(r"[-_.]+", "-", name.lower())


# --- artifact 1 + 2: conda purls ------------------------------------------

def fetch_active_packages(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """All active conda packages, ordered by conda_name (C-locale).

    Deliberately broader than v_actionable_packages: archived-but-active
    rows are INCLUDED — a consumer may be running one (intake-spec Wave A
    artifact-contract row 1).
    """
    # scope: Wave A/S1 artifact contract — archived-but-active INCLUDED
    # (broader than the actionable triplet); consumers may run archived pkgs.
    rows = list(conn.execute(
        """
        SELECT conda_name, latest_conda_version, pypi_name,
               match_source, match_confidence
        FROM packages
        WHERE conda_name IS NOT NULL
          AND latest_status = 'active'
        ORDER BY conda_name
        """
    ))
    return [
        {
            "conda_name": r[0],
            "latest_conda_version": r[1],
            "pypi_name": r[2],
            "match_source": r[3],
            "match_confidence": r[4],
        }
        for r in rows
    ]


def conda_purl_lines(pkgs: list[dict[str, Any]]) -> list[str]:
    return [f"pkg:conda/{p['conda_name']}{CHANNEL_QUALIFIER}" for p in pkgs]


def conda_versioned_purl_lines(pkgs: list[dict[str, Any]]) -> list[str]:
    """Same rows + order as artifact #1; NULL version → unversioned line so
    count parity with #1 holds (asserted by the meta gate)."""
    out = []
    for p in pkgs:
        ver = p["latest_conda_version"]
        if ver:
            out.append(f"pkg:conda/{p['conda_name']}@{ver}{CHANNEL_QUALIFIER}")
        else:
            out.append(f"pkg:conda/{p['conda_name']}{CHANNEL_QUALIFIER}")
    return out


# --- artifact 3: pypi universe purls ---------------------------------------

def pypi_purl_lines(conn: sqlite3.Connection) -> list[str]:
    names = [r[0] for r in conn.execute("SELECT pypi_name FROM pypi_universe")]
    return sorted(f"pkg:pypi/{g98_pypi_name(n)}" for n in names)


# --- artifact 4: conda↔pypi mapping TSV ------------------------------------

MAPPED_TSV_HEADER = "conda_purl\tpypi_purl\tmatch_source\tmatch_confidence"


def mapped_tsv_lines(pkgs: list[dict[str, Any]]) -> list[str]:
    """Artifact-#1 rows with a non-empty pypi_name. Straight provenance
    passthrough — `match_source='none'` / `match_confidence='n/a'` rows are
    INCLUDED, no filtering."""
    lines = [MAPPED_TSV_HEADER]
    for p in pkgs:  # already ordered by conda_name
        if not p["pypi_name"]:
            continue
        lines.append(
            f"pkg:conda/{p['conda_name']}{CHANNEL_QUALIFIER}\t"
            f"pkg:pypi/{g98_pypi_name(p['pypi_name'])}\t"
            f"{p['match_source'] or ''}\t{p['match_confidence'] or ''}"
        )
    return lines


# --- artifact 5: recipe exceptions ------------------------------------------

def recipe_exception_lines(
    recipes_dir: Path,
    conda_names: set[str],
    pypi_fold_index: set[str],
) -> tuple[list[str], int, int]:
    """Scan recipes/*/recipe.yaml for `pending-`/`blocked-` cfe status.

    Emits, per the intake-spec contract:
      `{dir}: conda:{name} not-on-cf (status={s})` when the conda name is
      absent from artifact #1; else, for pypi-registry recipes,
      `{dir}: pypi:{name} not-in-pypi-export` when absent from artifact #3.

    D1: membership lookup folds BOTH sides; emission keeps stored spelling.
    Returns (lines, recipes_scanned, recipes_parse_errors).
    """
    lines: list[str] = []
    scanned = 0
    parse_errors = 0
    if not recipes_dir.is_dir():
        return lines, scanned, parse_errors
    for recipe_path in sorted(recipes_dir.glob("*/recipe.yaml")):
        scanned += 1
        try:
            doc = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 — any parse failure: warn+skip
            parse_errors += 1
            sys.stderr.write(f"  warn: unparseable {recipe_path}: {exc}\n")
            continue
        if not isinstance(doc, dict):
            continue
        extra = doc.get("extra") or {}
        if not isinstance(extra, dict):
            continue
        status = str(extra.get("cfe-on-conda-forge-status") or "")
        if not (status.startswith("pending-") or status.startswith("blocked-")):
            continue
        rdir = recipe_path.parent.name
        conda_name = str(
            extra.get("cfe-conda-name")
            or (doc.get("package") or {}).get("name")
            or rdir
        )
        if conda_name not in conda_names:
            lines.append(f"{rdir}: conda:{conda_name} not-on-cf (status={status})")
            continue
        registry = str(extra.get("cfe-upstream-registry") or "")
        if registry == "pypi":
            upstream = str(extra.get("cfe-upstream-name") or conda_name)
            if fold_name(upstream) not in pypi_fold_index:
                lines.append(f"{rdir}: pypi:{upstream} not-in-pypi-export")
    return lines, scanned, parse_errors


# --- artifact 6: non-pypi upstream mapping TSV -------------------------------

UPSTREAM_TSV_HEADER = "conda_purl\tupstream_purl\tupstream_source"

_GITHUB_RE = re.compile(r"github\.com/([^/]+)/([^/#?]+)", re.IGNORECASE)
_NPM_RE = re.compile(r"registry\.npmjs\.(?:org|com)/((?:@[^/]+/)?[^/#?]+)", re.IGNORECASE)
_CRATES_RE = re.compile(r"crates\.io/(?:api/v1/crates/|crates/)([^/#?]+)", re.IGNORECASE)
_GEM_RE = re.compile(r"rubygems\.org/(?:api/v1/gems/|gems/)([^/#?]+?)(?:\.json)?$", re.IGNORECASE)
_MAVEN_RE = re.compile(r"maven2/(.+)/([^/]+)/maven-metadata", re.IGNORECASE)


def upstream_purl(source: str, url: str | None) -> str | None:
    """Map an upstream_versions (source, url) pair to a purl, or None when
    the URL doesn't parse (caller counts + skips)."""
    url = url or ""
    if source == "github":
        m = _GITHUB_RE.search(url)
        if m:
            owner, repo = m.group(1), re.sub(r"\.git$", "", m.group(2))
            return f"pkg:github/{owner}/{repo}"
        return None
    if source == "npm":
        m = _NPM_RE.search(url)
        return f"pkg:npm/{m.group(1)}" if m else None
    if source == "crates":
        m = _CRATES_RE.search(url)
        return f"pkg:cargo/{m.group(1)}" if m else None
    if source == "rubygems":
        m = _GEM_RE.search(url)
        return f"pkg:gem/{m.group(1)}" if m else None
    if source == "maven":
        m = _MAVEN_RE.search(url)
        if m:
            group = m.group(1).replace("/", ".")
            return f"pkg:maven/{group}/{m.group(2)}"
        return None
    if source in ("gitlab", "codeberg"):
        repo = re.sub(r"\.git$", "", url.rstrip("/").rsplit("/", 1)[-1]) if url else ""
        if repo:
            return f"pkg:generic/{repo}?vcs_url=git+{url}"
        return None
    return None


def upstream_tsv_lines(conn: sqlite3.Connection) -> tuple[list[str], int]:
    """Active, PyPI-unmapped packages with a non-pypi upstream_versions row —
    one row per (conda_name, source). Unparseable URL → skip + count.
    Returns (lines, unparseable_count)."""
    # scope: Wave A/S1 artifact #6 — same deliberately-broader-than-
    # actionable population as artifact #1 (archived-but-active included).
    rows = list(conn.execute(
        """
        SELECT p.conda_name, uv.source, uv.url
        FROM packages p
        JOIN upstream_versions uv ON uv.conda_name = p.conda_name
        WHERE p.conda_name IS NOT NULL
          AND p.latest_status = 'active'
          AND (p.pypi_name IS NULL OR p.pypi_name = '')
          AND uv.source <> 'pypi'
        ORDER BY p.conda_name, uv.source
        """
    ))
    lines = [UPSTREAM_TSV_HEADER]
    unparseable = 0
    for conda_name, source, url in rows:
        purl = upstream_purl(source, url)
        if purl is None:
            unparseable += 1
            continue
        lines.append(
            f"pkg:conda/{conda_name}{CHANNEL_QUALIFIER}\t{purl}\t{source}"
        )
    return lines, unparseable


# --- write + report ----------------------------------------------------------

def _count_lines(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for _ in fh)


def write_artifact(out_dir: Path, filename: str, lines: list[str]) -> dict[str, Any]:
    """Write lines (newline-terminated) atomically; report lines vs the
    previous file's line count (None when the artifact didn't exist)."""
    path = out_dir / filename
    previous = _count_lines(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(f"{ln}\n" for ln in lines), encoding="utf-8")
    os.replace(tmp, path)
    return {"lines": len(lines), "previous_lines": previous}


def export_all(
    conn: sqlite3.Connection,
    out_dir: Path,
    recipes_dir: Path = RECIPES_DIR,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pkgs = fetch_active_packages(conn)
    pypi_lines = pypi_purl_lines(conn)
    pypi_fold_index = {
        fold_name(ln[len("pkg:pypi/"):]) for ln in pypi_lines
    }
    conda_names = {p["conda_name"] for p in pkgs}

    exceptions, scanned, parse_errors = recipe_exception_lines(
        recipes_dir, conda_names, pypi_fold_index
    )
    upstream_lines, unparseable = upstream_tsv_lines(conn)

    artifacts = {
        "purls_conda-forge.txt": write_artifact(
            out_dir, "purls_conda-forge.txt", conda_purl_lines(pkgs)),
        "purls_conda-forge_versioned.txt": write_artifact(
            out_dir, "purls_conda-forge_versioned.txt",
            conda_versioned_purl_lines(pkgs)),
        "purls_pypi.txt": write_artifact(
            out_dir, "purls_pypi.txt", pypi_lines),
        "purls_conda-pypi_mapped.tsv": write_artifact(
            out_dir, "purls_conda-pypi_mapped.tsv", mapped_tsv_lines(pkgs)),
        "recipe-purl-exceptions.txt": write_artifact(
            out_dir, "recipe-purl-exceptions.txt", exceptions),
        "purls_conda-upstream_mapped.tsv": write_artifact(
            out_dir, "purls_conda-upstream_mapped.tsv", upstream_lines),
    }
    return {
        "out_dir": str(out_dir),
        "artifacts": artifacts,
        "recipes_scanned": scanned,
        "recipes_parse_errors": parse_errors,
        "unparseable_upstream": unparseable,
    }


def render_report(result: dict[str, Any]) -> str:
    out = [f"  purl export → {result['out_dir']}"]
    for name, info in result["artifacts"].items():
        prev = info["previous_lines"]
        prev_s = "new" if prev is None else f"was {prev:,}"
        out.append(f"  {name:<36} {info['lines']:>9,} lines ({prev_s})")
    out.append(
        f"  recipes scanned: {result['recipes_scanned']:,} "
        f"(parse errors: {result['recipes_parse_errors']}) · "
        f"unparseable upstream URLs: {result['unparseable_upstream']}"
    )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export purl + mapping artifacts from cf_atlas.db + recipes/."
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                        help=f"Output directory (default {DEFAULT_OUT_DIR})")
    parser.add_argument("--json", action="store_true",
                        help="Emit the per-artifact line report as JSON")
    args = parser.parse_args()

    if not DB_PATH.exists():
        sys.stderr.write(
            f"cf_atlas.db not found at {DB_PATH}. "
            "Run `pixi run -e local-recipes build-cf-atlas` first.\n"
        )
        return 1

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        result = export_all(conn, args.out_dir)
    finally:
        conn.close()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        sys.stdout.write(render_report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
