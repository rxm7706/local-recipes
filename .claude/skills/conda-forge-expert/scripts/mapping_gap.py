#!/usr/bin/env python3
"""
mapping-gap — Close conda↔PyPI mapping gaps offline (cyclonedx-universe-
inventory Wave A / S2; the effort's ONE DB write path — DRY-RUN by default).

Working set: `v_actionable_packages WHERE pypi_name IS NULL OR pypi_name=''`.

Classification:
  • python-track — has a `python` run-dep in `dependencies` OR an
    `upstream_versions` row with source='pypi'.
  • non-python-with-identity — any other upstream_versions row exists.
  • non-python-no-identity — no upstream identity at all (freshness
    unknowable until Phase L/K covers them — reported, not fixed here).

Recovery (OFFLINE ONLY — no live probing): inverse-G10 candidates from the
conda name — folding subsumes the `-`/`_` swap, so ≤4 distinct transforms:
bare, strip `-py`, strip `-python`, strip `python-` — validated against a
fold-keyed index of `pypi_universe` plus a one-time REVERSE index of the
grayskull cache (`pypi_conda_map.json` is `{pypi_lower: conda_name}`-keyed).
The written value is the universe's STORED spelling (folding is lookup-only,
G98-safe).

Confidence (D2): `verified` only when an independent corroborator agrees —
the reverse grayskull cache, or (D2-ext, eighth amendment) the
purl-associator mappings bundle when cached locally; `likely` on universe
membership alone. Ambiguous (2+ distinct candidates, no tiebreak) → NO
write. Collision (candidate already set on a DIFFERENT conda package — the
wasmtime-vs-wasmtime-py trap) → skip; never a "bare name wins" heuristic.

Writeback (pinned SQL — idempotent, no-clobber, commit_every=500):

    UPDATE packages
       SET pypi_name = ?, match_source = 'g10_spelling', match_confidence = ?
     WHERE conda_name = ?
       AND (pypi_name IS NULL OR pypi_name = '')
       AND match_source NOT IN ('parselmouth', 'recipe_source_url')

A second `--write` run reporting 0 rows written IS the idempotency proof.

ORPHAN_RULE: `pypi_intelligence` rows with no `pypi_universe` counterpart
(deleted/renamed projects) are never version truth; consumers read
`v_pypi_intelligence_valid` (schema v29). This CLI reports the orphan count.

CLI:
  mapping-gap [--write] [--json] [--limit N] [--report PATH]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any


def _get_data_dir() -> Path:
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


DB_PATH = _get_data_dir() / "cf_atlas.db"
GRAYSKULL_CACHE_PATH = _get_data_dir() / "pypi_conda_map.json"
PURL_ASSOCIATOR_PATH = _get_data_dir() / "purl-associator-mappings.json"
DEFAULT_REPORT_PATH = _get_data_dir() / "mapping-gap-report.md"

ORPHAN_RULE = (
    "pypi_intelligence rows with no pypi_universe counterpart "
    "(deleted/renamed PyPI projects) are excluded from version truth; "
    "consumers read v_pypi_intelligence_valid (schema v29), never the raw "
    "table."
)

WRITEBACK_SQL = """
UPDATE packages
   SET pypi_name = ?, match_source = 'g10_spelling', match_confidence = ?
 WHERE conda_name = ?
   AND (pypi_name IS NULL OR pypi_name = '')
   AND match_source NOT IN ('parselmouth', 'recipe_source_url')
"""

COMMIT_EVERY = 500


def fold_name(name: str) -> str:
    """PEP-503-style fold for membership lookup only (D1/G98-safe)."""
    return re.sub(r"[-_.]+", "-", name.lower())


# --- indexes -----------------------------------------------------------------

def build_universe_fold_index(conn: sqlite3.Connection) -> dict[str, set[str]]:
    """fold(pypi_name) → {stored spellings} over the full pypi_universe."""
    index: dict[str, set[str]] = {}
    for (name,) in conn.execute("SELECT pypi_name FROM pypi_universe"):
        index.setdefault(fold_name(name), set()).add(name)
    return index


def load_grayskull_reverse(
    path: Path = GRAYSKULL_CACHE_PATH,
) -> tuple[dict[str, set[str]] | None, str, str | None]:
    """Reverse the `{pypi_lower: conda_name}` grayskull cache into
    `conda_name.lower() → {pypi names}`.

    Returns (reverse | None, state, mtime_iso | None) with state one of
    'ok' / 'absent' / 'corrupt' — a present-but-unreadable cache must NOT
    be reported as absent (the operator would re-fetch instead of
    investigating corruption). mtime is stamped only when the cache was
    actually loaded (no exists()/stat() TOCTOU)."""
    try:
        stat = path.stat()
    except OSError:
        return None, "absent", None
    mtime = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime))
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None, "corrupt", mtime
    if not isinstance(raw, dict):
        return None, "corrupt", mtime
    reverse: dict[str, set[str]] = {}
    for pypi_name, conda_name in raw.items():
        if isinstance(conda_name, str) and isinstance(pypi_name, str):
            reverse.setdefault(conda_name.lower(), set()).add(pypi_name)
    return reverse, "ok", mtime


_PYPI_PURL_RE = re.compile(r"pkg:pypi/([A-Za-z0-9._-]+)")


def load_purl_associator_reverse(path: Path = PURL_ASSOCIATOR_PATH) -> dict[str, set[str]] | None:
    """D2-ext (optional corroborator): tolerant reader for a locally-cached
    prefix-dev/purl-associator mappings bundle. Schema-agnostic — extracts
    every `pkg:pypi/<name>` purl found under each conda-name key. None when
    no bundle is cached (the common case; never fetched here — offline rule)."""
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, dict):
        return None
    reverse: dict[str, set[str]] = {}
    for conda_name, record in raw.items():
        if not isinstance(conda_name, str):
            continue
        for m in _PYPI_PURL_RE.finditer(json.dumps(record)):
            reverse.setdefault(conda_name.lower(), set()).add(m.group(1))
    return reverse or None


# --- working set + classification ---------------------------------------------

def fetch_working_set(conn: sqlite3.Connection, limit: int | None = None) -> list[str]:
    sql = (
        "SELECT conda_name FROM v_actionable_packages "
        "WHERE pypi_name IS NULL OR pypi_name = '' "
        "ORDER BY conda_name"
    )
    if limit is not None:
        # Clamp: SQLite treats a negative LIMIT as "no limit".
        sql += f" LIMIT {max(0, int(limit))}"
    return [r[0] for r in conn.execute(sql)]


def count_unmapped(conn: sqlite3.Connection) -> int:
    """Full (un-limited) unmapped count — the honest denominator for the
    report's `remaining unmapped` line even when --limit bounds the run."""
    return conn.execute(
        "SELECT COUNT(*) FROM v_actionable_packages "
        "WHERE pypi_name IS NULL OR pypi_name = ''"
    ).fetchone()[0]


def classify(conn: sqlite3.Connection, conda_names: list[str]) -> dict[str, list[str]]:
    """Split the working set into python_track / non_python_with_identity /
    non_python_no_identity per the S2 contract."""
    python_dep = {
        r[0] for r in conn.execute(
            "SELECT DISTINCT source_conda_name FROM dependencies "
            "WHERE target_conda_name = 'python' AND requirement_type = 'run'"
        )
    }
    upstream_sources: dict[str, set[str]] = {}
    for name, source in conn.execute(
        "SELECT conda_name, source FROM upstream_versions"
    ):
        upstream_sources.setdefault(name, set()).add(source)

    buckets: dict[str, list[str]] = {
        "python_track": [],
        "non_python_with_identity": [],
        "non_python_no_identity": [],
    }
    for name in conda_names:
        sources = upstream_sources.get(name, set())
        if name in python_dep or "pypi" in sources:
            buckets["python_track"].append(name)
        elif sources:
            buckets["non_python_with_identity"].append(name)
        else:
            buckets["non_python_no_identity"].append(name)
    return buckets


# --- recovery -------------------------------------------------------------------

def spelling_candidates(conda_name: str) -> dict[str, str]:
    """≤4 distinct inverse-G10 transforms: transform-name → candidate string.
    Folding at lookup subsumes the `-`/`_` swap."""
    cands: dict[str, str] = {"bare": conda_name}
    if conda_name.endswith("-py"):
        cands["strip-py"] = conda_name[: -len("-py")]
    if conda_name.endswith("-python"):
        cands["strip-python"] = conda_name[: -len("-python")]
    if conda_name.startswith("python-"):
        cands["strip-python-prefix"] = conda_name[len("python-"):]
    return cands


def recover(
    conn: sqlite3.Connection,
    python_track: list[str],
    universe_index: dict[str, set[str]],
    grayskull_reverse: dict[str, set[str]] | None,
    associator_reverse: dict[str, set[str]] | None,
) -> dict[str, Any]:
    """Offline recovery over the python-track rows. Returns buckets:
    recovered (list of dicts), ambiguous, collisions, unrecovered."""
    # Collision index: fold(pypi_name) → conda_name for every already-mapped
    # row anywhere in packages (the wasmtime-vs-wasmtime-py trap). ORDER BY
    # keeps `claimed_by` deterministic when several rows fold identically,
    # and the index is UPDATED as in-run recoveries are accepted so two
    # unmapped packages can never both claim the same PyPI name in one run
    # (the intra-run face of the same trap).
    # scope: collision detection must see EVERY mapped row, including
    # archived/inactive ones — a narrower view would miss real claims.
    claimed: dict[str, str] = {}
    for pypi_name, conda_name in conn.execute(
        "SELECT pypi_name, conda_name FROM packages "
        "WHERE pypi_name IS NOT NULL AND pypi_name <> '' "
        "ORDER BY conda_name"
    ):
        claimed.setdefault(fold_name(pypi_name), conda_name)

    recovered: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    unrecovered: list[str] = []

    for conda_name in python_track:
        hits: dict[str, str] = {}  # stored spelling → transform that found it
        for transform, cand in spelling_candidates(conda_name).items():
            for stored in sorted(universe_index.get(fold_name(cand), ())):
                hits.setdefault(stored, transform)

        if not hits:
            unrecovered.append(conda_name)
            continue

        # Corroborators: does an independent source map THIS conda name to
        # one of the hit spellings?
        corroborated: set[str] = set()
        corroborator_names: set[str] = set()
        for reverse in (grayskull_reverse, associator_reverse):
            if not reverse:
                continue
            for pypi_name in reverse.get(conda_name.lower(), ()):
                corroborator_names.add(pypi_name)
                folded = fold_name(pypi_name)
                for stored in hits:
                    if fold_name(stored) == folded:
                        corroborated.add(stored)

        # An independent source that ACTIVELY DISAGREES (it names pypi
        # projects for this conda name, none matching any universe hit) is
        # stronger evidence of a wrong mapping than no corroborator — route
        # to the human-triage queue instead of writing a `likely` guess.
        if corroborator_names and not corroborated:
            ambiguous.append({
                "conda_name": conda_name,
                "candidates": sorted(hits),
                "corroborator_suggests": sorted(corroborator_names),
            })
            continue

        if len(hits) > 1 and len(corroborated) != 1:
            ambiguous.append({
                "conda_name": conda_name,
                "candidates": sorted(hits),
            })
            continue

        chosen = next(iter(corroborated)) if len(corroborated) == 1 else next(iter(hits))
        confidence = "verified" if chosen in corroborated else "likely"

        claimant = claimed.get(fold_name(chosen))
        if claimant and claimant != conda_name:
            collisions.append({
                "conda_name": conda_name,
                "candidate": chosen,
                "claimed_by": claimant,
            })
            continue

        claimed[fold_name(chosen)] = conda_name  # intra-run claim
        recovered.append({
            "conda_name": conda_name,
            "pypi_name": chosen,
            "confidence": confidence,
            "transform": hits[chosen],
        })

    return {
        "recovered": recovered,
        "ambiguous": ambiguous,
        "collisions": collisions,
        "unrecovered": unrecovered,
    }


# --- write path -------------------------------------------------------------------

def write_recoveries(conn: sqlite3.Connection, recovered: list[dict[str, Any]]) -> int:
    """Apply the pinned no-clobber UPDATE with incremental commits
    (commit_every=500, Phase C pattern). Returns rows actually written."""
    written = 0
    pending = 0
    for rec in recovered:
        cur = conn.execute(
            WRITEBACK_SQL,
            (rec["pypi_name"], rec["confidence"], rec["conda_name"]),
        )
        written += cur.rowcount
        pending += 1
        if pending >= COMMIT_EVERY:
            conn.commit()
            pending = 0
    conn.commit()
    return written


# --- orphan stats ---------------------------------------------------------------

def orphan_intelligence_stats(conn: sqlite3.Connection, sample: int = 5) -> dict[str, Any]:
    """Count + sample pypi_intelligence rows with no pypi_universe
    counterpart (the rows v_pypi_intelligence_valid excludes)."""
    # scope: the orphan probe must read the RAW table — measuring exactly
    # the rows the v_pypi_intelligence_valid view excludes.
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name IN ('pypi_intelligence', 'pypi_universe')"
    )}
    if tables != {"pypi_intelligence", "pypi_universe"}:
        return {"count": 0, "sample": [], "rule": ORPHAN_RULE}
    count = conn.execute(
        "SELECT COUNT(*) FROM pypi_intelligence pi "
        "LEFT JOIN pypi_universe pu ON pu.pypi_name = pi.pypi_name "
        "WHERE pu.pypi_name IS NULL"
    ).fetchone()[0]
    # scope: raw-table read by design — sampling the orphans the
    # v_pypi_intelligence_valid view excludes. NULL pypi_name (legal in a
    # SQLite TEXT PK) is coerced so report rendering can't crash on join().
    sample_rows = [str(r[0]) for r in conn.execute(
        "SELECT pi.pypi_name FROM pypi_intelligence pi "
        "LEFT JOIN pypi_universe pu ON pu.pypi_name = pi.pypi_name "
        "WHERE pu.pypi_name IS NULL ORDER BY pi.pypi_name LIMIT ?",
        (sample,),
    )]
    return {"count": count, "sample": sample_rows, "rule": ORPHAN_RULE}


# --- report ------------------------------------------------------------------------

def _mapped_count(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM v_actionable_packages "
        "WHERE pypi_name IS NOT NULL AND pypi_name <> ''"
    ).fetchone()[0]


def _atlas_built_at(conn: sqlite3.Connection) -> str:
    try:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'built_at'"
        ).fetchone()
        return str(row[0]) if row else "unknown"
    except sqlite3.Error:
        return "unknown"


def render_report(result: dict[str, Any]) -> str:
    r = result
    lines = [
        "# mapping-gap report",
        "",
        f"- generated_at: {r['generated_at']}",
        f"- atlas built_at: {r['built_at']}",
        f"- mode: {'WRITE' if r['mode'] == 'write' else 'DRY-RUN'}",
        f"- grayskull cache: "
        + (f"present (mtime {r['grayskull_cache_mtime']})"
           if r["grayskull_cache_state"] == "ok"
           else ("PRESENT BUT UNREADABLE (corrupt?) — likely-only mode"
                 if r["grayskull_cache_state"] == "corrupt"
                 else "ABSENT — likely-only mode")),
        f"- purl-associator bundle (D2-ext): "
        + ("present" if r["purl_associator_present"] else "absent"),
        "",
        "## Summary",
        "",
        f"- actionable unmapped (working set): {r['actionable_unmapped']:,}",
        f"- mapped before: {r['mapped_before']:,} · after: {r['mapped_after']:,}",
        f"- recovered: {len(r['recovered']):,} (rows written: {r['rows_written']:,})",
        f"- remaining unmapped: {r['remaining_unmapped']:,}",
        "",
        "## Classification",
        "",
        f"- python-track: {len(r['python_track']):,}",
        f"- non-python with upstream identity: {len(r['non_python_with_identity']):,}",
        f"- non-python, NO upstream identity (freshness unknowable until "
        f"Phase L/K covers them): {len(r['non_python_no_identity']):,}",
        "",
        "### Recovered by confidence × transform",
        "",
    ]
    by_ct: dict[str, int] = {}
    for rec in r["recovered"]:
        key = f"{rec['confidence']} × {rec['transform']}"
        by_ct[key] = by_ct.get(key, 0) + 1
    for key in sorted(by_ct):
        lines.append(f"- {key}: {by_ct[key]:,}")
    if not by_ct:
        lines.append("- (none)")
    lines += ["", "## Human-triage queue", "", "### Ambiguous", ""]
    for a in r["ambiguous"]:
        lines.append(f"- {a['conda_name']}: candidates {', '.join(a['candidates'])}")
    if not r["ambiguous"]:
        lines.append("- (none)")
    lines += ["", "### Collisions", ""]
    for c in r["collisions"]:
        lines.append(
            f"- {c['conda_name']}: candidate {c['candidate']} already claimed "
            f"by {c['claimed_by']}"
        )
    if not r["collisions"]:
        lines.append("- (none)")
    lines += [
        "",
        "## Orphan pypi_intelligence rows",
        "",
        f"> {r['orphans']['rule']}",
        "",
        f"- count: {r['orphans']['count']:,}",
        f"- sample: {', '.join(r['orphans']['sample']) or '(none)'}",
        "",
        "## Recovered pairs (appendix)",
        "",
    ]
    for rec in r["recovered"]:
        lines.append(
            f"- {rec['conda_name']} → {rec['pypi_name']} "
            f"({rec['confidence']}, {rec['transform']})"
        )
    if not r["recovered"]:
        lines.append("- (none)")
    return "\n".join(lines) + "\n"


# --- main --------------------------------------------------------------------------

def run(
    conn: sqlite3.Connection,
    write: bool,
    limit: int | None,
    grayskull_path: Path = GRAYSKULL_CACHE_PATH,
    associator_path: Path = PURL_ASSOCIATOR_PATH,
) -> dict[str, Any]:
    grayskull_reverse, grayskull_state, grayskull_mtime = load_grayskull_reverse(grayskull_path)
    if grayskull_state == "absent":
        sys.stderr.write(
            f"  warn: grayskull cache absent at {grayskull_path} — "
            "continuing in likely-only mode (refresh via update_mapping_cache)\n"
        )
    elif grayskull_state == "corrupt":
        sys.stderr.write(
            f"  warn: grayskull cache at {grayskull_path} is present but "
            "unreadable (corrupt JSON?) — continuing in likely-only mode; "
            "investigate the file before re-fetching\n"
        )
    associator_reverse = load_purl_associator_reverse(associator_path)

    universe_index = build_universe_fold_index(conn)
    working = fetch_working_set(conn, limit)
    buckets = classify(conn, working)
    mapped_before = _mapped_count(conn)

    rec = recover(
        conn, buckets["python_track"], universe_index,
        grayskull_reverse, associator_reverse,
    )

    rows_written = 0
    if write and rec["recovered"]:
        rows_written = write_recoveries(conn, rec["recovered"])

    mapped_after = _mapped_count(conn)
    result: dict[str, Any] = {
        "mode": "write" if write else "dry-run",
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "built_at": _atlas_built_at(conn),
        "grayskull_cache_present": grayskull_state == "ok",
        "grayskull_cache_state": grayskull_state,
        "grayskull_cache_mtime": grayskull_mtime,
        "purl_associator_present": associator_reverse is not None,
        "actionable_unmapped": len(working),
        "python_track": buckets["python_track"],
        "non_python_with_identity": buckets["non_python_with_identity"],
        "non_python_no_identity": buckets["non_python_no_identity"],
        "recovered": rec["recovered"],
        "ambiguous": rec["ambiguous"],
        "collisions": rec["collisions"],
        "unrecovered_python_track": rec["unrecovered"],
        "rows_written": rows_written,
        "mapped_before": mapped_before,
        "mapped_after": mapped_after,
        # Honest denominator: the FULL unmapped population post-run, not the
        # --limit-bounded working set.
        "remaining_unmapped": count_unmapped(conn),
        "orphans": orphan_intelligence_stats(conn),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify + recover conda↔PyPI mapping gaps (dry-run by default)."
    )
    parser.add_argument("--write", action="store_true",
                        help="Apply the no-clobber writeback (default: dry-run)")
    parser.add_argument("--json", action="store_true",
                        help="Emit the full result as JSON (buckets summarized)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process at most N working-set rows")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH,
                        help=f"Markdown report path (default {DEFAULT_REPORT_PATH})")
    args = parser.parse_args()

    if not DB_PATH.exists():
        sys.stderr.write(
            f"cf_atlas.db not found at {DB_PATH}. "
            "Run `pixi run -e local-recipes build-cf-atlas` first.\n"
        )
        return 1

    if args.write:
        conn = sqlite3.connect(DB_PATH)
    else:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        result = run(conn, write=args.write, limit=args.limit)
    except sqlite3.OperationalError as exc:
        sys.stderr.write(
            f"atlas schema too old or incomplete ({exc}). "
            "Re-run `pixi run -e local-recipes build-cf-atlas` (schema v29+ "
            "adds v_pypi_intelligence_valid; v20+ adds pypi_universe).\n"
        )
        return 1
    finally:
        conn.close()

    report_text = render_report(result)
    try:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report_text, encoding="utf-8")
    except OSError as exc:
        sys.stderr.write(f"  warn: could not write report to {args.report}: {exc}\n")

    if args.json:
        summary = dict(result)
        # Keep JSON compact: bucket lists → counts (full detail is in the report).
        for key in ("python_track", "non_python_with_identity",
                    "non_python_no_identity", "unrecovered_python_track"):
            summary[key] = len(result[key])
        print(json.dumps(summary, indent=2, default=str))
    else:
        sys.stdout.write(report_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
