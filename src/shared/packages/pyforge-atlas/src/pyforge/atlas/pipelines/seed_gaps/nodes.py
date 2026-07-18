"""``seed_gaps`` pipeline nodes — the four READ-ONLY gap suggesters (Story B6).

Four PURE ``data -> pandas.DataFrame`` report nodes that PROPOSE curated-seed
additions (they NEVER mutate the seeds — the byte-identical-seed guarantee is a
pipeline test, AC-2). Each ports its legacy ``classify`` contract VERBATIM from
the shipped read-only CLI (the reference contract; do NOT re-derive the
heuristics), reading already-loaded seed + ground-truth data via catalog
datasets (§ 3.4 Seed-freshness report nodes table; AD-15 / AD-3):

- ``report_lts_registry_gap``  ← ``lts_registry_gap.py``   (exact / likely)
- ``report_cwe_seed_gap``      ← ``cwe_seed_gap.py``       (strong / weak)
- ``report_spdx_schema_gap``   ← ``spdx_schema_gap.py``    (add-to-schema / non-standard / upstream-drift)
- ``report_license_map_gap``   ← ``license_map_gap.py``    (likely / report)

pandas + stdlib ONLY (the whole-package ``test_no_inline_io`` scan bans
requests / urllib / httpx / sqlite3 / subprocess / dagster / kedro_mcp). No node
ever opens a file, hits the network, or writes a seed. ``mapping-gap`` is a
WRITER (the ``g10_spelling`` no-clobber writeback) and stays in the PyPI
Intelligence pipeline — it is deliberately NOT a node here (AC-4).
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# report_lts_registry_gap  (legacy lts_registry_gap.py:classify / _norm)
# ---------------------------------------------------------------------------

_LTS_COLS = ["conda_name", "pypi_name", "slug", "confidence", "matched_via"]


def _lts_registry_index(seed_lts_registry: Any) -> dict[str, Any]:
    """Mirror ``library_futures.load_lts_registry``'s key-fold over an
    ALREADY-LOADED registry dict: ``{alias_lower: entry}`` from
    ``doc['products']``, each product key + its ``aliases`` list, lowercased.
    A non-dict / missing ``products`` degrades to ``{}`` (legacy contract)."""
    if not isinstance(seed_lts_registry, dict):
        return {}
    index: dict[str, Any] = {}
    for name, entry in (seed_lts_registry.get("products") or {}).items():
        if not isinstance(entry, dict):
            continue
        entry = {**entry, "_name": name}
        for key in [name, *(entry.get("aliases") or [])]:
            index[str(key).lower()] = entry
    return index


def _norm(name: str) -> str:
    # legacy lts_registry_gap.py:_norm — VERBATIM.
    return name.lower().replace("_", "-")


def _classify_lts(
    candidates: list[tuple[str, str | None]],
    slugs: list[str],
    registry: dict[str, Any],
) -> list[dict[str, Any]]:
    """legacy lts_registry_gap.py:classify — ported VERBATIM. One proposal per
    conda name, highest tier wins; registry-covered names (aliases included)
    are excluded (decided, not gaps). exact = lowercase-equals a slug; likely =
    ``_``→``-`` norm, or a stripped ``python-`` / ``py-`` prefix."""
    slug_set = {s.lower() for s in slugs}
    registry_keys = {str(k).lower() for k in registry}
    proposals: list[dict[str, Any]] = []
    for conda_name, pypi_name in candidates:
        if not conda_name or conda_name.lower() in registry_keys:
            continue
        if pypi_name and pypi_name.lower() in registry_keys:
            continue
        hit: tuple[str, str, str] | None = None  # (slug, confidence, via)
        for label, value in (("conda_name", conda_name),
                             ("pypi_name", pypi_name or "")):
            if value and value.lower() in slug_set:
                hit = (value.lower(), "exact", f"{label} == slug")
                break
        if hit is None:
            for label, value in (("conda_name", conda_name),
                                 ("pypi_name", pypi_name or "")):
                if not value:
                    continue
                norm = _norm(value)
                if norm != value.lower() and norm in slug_set:
                    hit = (norm, "likely", f"{label} normalized (_ -> -)")
                    break
                for prefix in ("python-", "py-"):
                    if norm.startswith(prefix) and norm[len(prefix):] in slug_set:
                        hit = (norm[len(prefix):], "likely",
                               f"{label} sans '{prefix}' prefix")
                        break
                if hit:
                    break
        if hit:
            proposals.append({
                "conda_name": conda_name,
                "pypi_name": pypi_name,
                "slug": hit[0],
                "confidence": hit[1],
                "matched_via": hit[2],
            })
    return proposals


def _lts_candidates(
    core_packages_enumerated: Any,
    pypi_conda_mapping: Any,
) -> list[tuple[str, str | None]]:
    """The actionable ``(conda_name, pypi_name)`` list (legacy
    ``v_actionable_packages`` scope): ``core_packages_enumerated`` (conda_name)
    LEFT JOIN ``pypi_conda_mapping`` (conda_name ↔ pypi_name). Ordered by
    conda_name (legacy ``ORDER BY conda_name``)."""
    core = core_packages_enumerated
    if core is None or getattr(core, "empty", True) or "conda_name" not in getattr(core, "columns", []):
        return []
    conda_to_pypi: dict[str, str] = {}
    mapping = pypi_conda_mapping
    if (mapping is not None and not getattr(mapping, "empty", True)
            and {"conda_name", "pypi_name"} <= set(getattr(mapping, "columns", []))):
        for cn, pn in zip(mapping["conda_name"], mapping["pypi_name"]):
            if cn is None or (isinstance(cn, float) and pd.isna(cn)):
                continue
            key = str(cn)
            if key not in conda_to_pypi and pn is not None and not (isinstance(pn, float) and pd.isna(pn)):
                conda_to_pypi[key] = str(pn)
    out: list[tuple[str, str | None]] = []
    for cn in core["conda_name"]:
        if cn is None or (isinstance(cn, float) and pd.isna(cn)):
            continue
        name = str(cn)
        out.append((name, conda_to_pypi.get(name)))
    out.sort(key=lambda r: r[0])
    return out


def report_lts_registry_gap(
    seed_lts_registry: Any,
    pypi_endoflife_raw: Any,
    core_packages_enumerated: Any,
    pypi_conda_mapping: Any,
) -> pd.DataFrame:
    """§ 3.4 ``report_lts_registry_gap`` — propose ``lts-registry.yaml`` entries
    by diffing the endoflife.date product slug list against actionable atlas
    packages (legacy ``lts_registry_gap.py``). READ-ONLY report; git review
    decides. ``pypi_endoflife_raw`` is the product-slug list; ``seed_lts_registry``
    the (alias-inclusive) exclusion set. Empty feed / candidates → empty report."""
    slugs = [str(s) for s in pypi_endoflife_raw] if isinstance(pypi_endoflife_raw, (list, tuple)) else []
    if not slugs:
        return pd.DataFrame(columns=_LTS_COLS)
    registry = _lts_registry_index(seed_lts_registry)
    candidates = _lts_candidates(core_packages_enumerated, pypi_conda_mapping)
    proposals = _classify_lts(candidates, slugs, registry)
    return pd.DataFrame(proposals, columns=_LTS_COLS).reset_index(drop=True)


# ---------------------------------------------------------------------------
# report_cwe_seed_gap  (legacy cwe_seed_gap.py:classify_cwe / classify)
# ---------------------------------------------------------------------------

_CWE_COLS = ["cwe_id", "cwe_name", "category", "confidence", "matched"]

# legacy cwe_seed_gap.py — PRECEDENCE / STRONG / WEAK, ported VERBATIM.
_PRECEDENCE = ["Memory-Safety", "Traversal", "RCE", "Injection",
               "Auth-Bypass", "Info-Disclosure", "DoS"]

_STRONG: dict[str, list[str]] = {
    "Memory-Safety": [
        "buffer overflow", "buffer underflow", "out-of-bounds",
        "out of bounds", "use after free", "double free", "null pointer",
        "integer overflow", "integer underflow", "heap-based", "stack-based",
        "memory corruption", "type confusion", "wild pointer",
        "improper restriction of operations within the bounds",
        "uninitialized",
    ],
    "Traversal": [
        "path traversal", "directory traversal", "link following",
        "absolute path traversal", "relative path traversal",
    ],
    "RCE": [
        "code execution", "command injection", "os command",
        "arbitrary code", "code injection", "argument injection",
        "expression language injection",
    ],
    "Injection": [
        "cross-site scripting", "sql injection", "xml external entity",
        "ldap injection", "xpath injection", "crlf", "template injection",
        "format string", "deserialization of untrusted data",
    ],
    "Auth-Bypass": [
        "authentication bypass", "authorization bypass",
        "improper authentication", "missing authentication",
        "improper access control", "improper authorization",
        "incorrect authorization", "privilege management",
        "incorrect permission", "improper privilege",
    ],
    "Info-Disclosure": [
        "information exposure", "sensitive information",
        "information disclosure", "exposure of", "cleartext storage",
        "cleartext transmission", "insertion of sensitive information",
    ],
    "DoS": [
        "denial of service", "resource exhaustion",
        "uncontrolled resource consumption", "infinite loop",
        "reachable assertion", "excessive iteration",
        "allocation of resources",
    ],
}

_WEAK: dict[str, list[str]] = {
    "Memory-Safety": ["dereference", "memory"],
    "Traversal": ["traversal"],
    "RCE": [],
    "Injection": ["injection", "serialization"],
    "Auth-Bypass": ["authentication", "authorization", "privilege",
                    "permission"],
    "Info-Disclosure": ["exposure", "leak"],
    "DoS": ["denial of service"],
}


def _classify_cwe(name: str) -> tuple[str, str, str] | None:
    """legacy cwe_seed_gap.py:classify_cwe — VERBATIM. (category, tier,
    matched_keyword) or None. Strong beats weak globally; within a tier the
    PRECEDENCE order breaks ties."""
    lname = (name or "").lower()
    for cat in _PRECEDENCE:
        for kw in _STRONG[cat]:
            if kw in lname:
                return cat, "strong", kw
    for cat in _PRECEDENCE:
        for kw in _WEAK[cat]:
            if kw in lname:
                return cat, "weak", kw
    return None


def _classify_cwe_candidates(
    candidates: list[tuple[str, str]],
    seed: dict[str, str],
) -> list[dict[str, Any]]:
    """legacy cwe_seed_gap.py:classify — VERBATIM. One proposal per un-seeded,
    keyword-classifiable 'Other' CWE (seed coverage is a belt-and-braces
    exclusion)."""
    proposals: list[dict[str, Any]] = []
    for cwe_id, cwe_name in candidates:
        if cwe_id in seed:
            continue
        hit = _classify_cwe(cwe_name)
        if hit is None:
            continue
        proposals.append({
            "cwe_id": cwe_id,
            "cwe_name": cwe_name,
            "category": hit[0],
            "confidence": hit[1],
            "matched": hit[2],
        })
    return proposals


def report_cwe_seed_gap(
    seed_cwe_categories: Any,
    vulnerability_cwe_categories: Any,
) -> pd.DataFrame:
    """§ 3.4 ``report_cwe_seed_gap`` — propose ``cwe_categories_seed.json``
    entries by keyword-classifying MITRE CWEs currently bucketed ``'Other'``
    (legacy ``cwe_seed_gap.py``). READ-ONLY report; git review decides.
    Candidates = ``vulnerability_cwe_categories`` rows where ``category ==
    'Other'`` → ``(cwe_id, cwe_name)``; ``seed_cwe_categories`` (``_doc`` key
    stripped) → the ``{cwe_id: category}`` belt-and-braces exclusion.
    ``packages_with_other_bucket`` is deferred (DW-B6-2 — no migrated per-package
    CWE-rollup dataset yet), so the report ships the proposal rows only."""
    seed: dict[str, str] = {}
    if isinstance(seed_cwe_categories, dict):
        seed = {k: v for k, v in seed_cwe_categories.items() if not str(k).startswith("_")}
    df = vulnerability_cwe_categories
    if df is None or getattr(df, "empty", True) or not {"cwe_id", "category"} <= set(getattr(df, "columns", [])):
        return pd.DataFrame(columns=_CWE_COLS)
    others = df[df["category"] == "Other"]
    candidates: list[tuple[str, str]] = []
    for cwe_id, cwe_name in zip(others["cwe_id"], others.get("cwe_name", [""] * len(others))):
        name = "" if cwe_name is None or (isinstance(cwe_name, float) and pd.isna(cwe_name)) else str(cwe_name)
        candidates.append((cwe_id, name))
    candidates.sort(key=lambda r: str(r[0]))
    proposals = _classify_cwe_candidates(candidates, seed)
    return pd.DataFrame(proposals, columns=_CWE_COLS).reset_index(drop=True)


# ---------------------------------------------------------------------------
# report_spdx_schema_gap  (legacy spdx_schema_gap.py:classify / _is_expression)
# ---------------------------------------------------------------------------

_SPDX_COLS = ["license", "spdx_id", "packages", "tier"]
_SPDX_EXPRESSION_RE = re.compile(r"[()]|(?:^|\s)(?:AND|OR|WITH)(?:\s|$)")


def _spdx_is_expression(s: str) -> bool:
    # legacy spdx_schema_gap.py:_is_expression — VERBATIM.
    return bool(_SPDX_EXPRESSION_RE.search(s))


def _classify_spdx(
    atlas_counts: dict[str, int],
    vendored: set[str],
    upstream: set[str],
) -> dict[str, list[dict[str, Any]]]:
    """legacy spdx_schema_gap.py:classify — VERBATIM. Partition the atlas
    license strings the vendored enum misses into add-to-schema (a real upstream
    SPDX ID) vs non-standard; expressions skipped; both count-ranked."""
    vendored_lower = {v.lower() for v in vendored}
    upstream_by_lower = {u.lower(): u for u in upstream}
    add: list[dict[str, Any]] = []
    nonstd: list[dict[str, Any]] = []
    for lic, count in atlas_counts.items():
        if lic in vendored or lic.lower() in vendored_lower:
            continue
        if _spdx_is_expression(lic):
            continue
        up = upstream_by_lower.get(lic.lower())
        if up is not None:
            add.append({"license": lic, "spdx_id": up, "packages": count})
        else:
            nonstd.append({"license": lic, "packages": count})
    add.sort(key=lambda r: (-r["packages"], r["spdx_id"]))
    nonstd.sort(key=lambda r: (-r["packages"], r["license"]))
    return {"add_to_schema": add, "non_standard": nonstd}


def _spdx_upstream_ids(seed_spdx_upstream_list_raw: Any) -> list[str]:
    """licenseIds from the upstream list — a ``{'licenses': [{'licenseId': …}]}``
    dict OR a bare list of ID strings (legacy ``--source-file`` accepted both)."""
    doc = seed_spdx_upstream_list_raw
    if isinstance(doc, dict):
        lics = doc.get("licenses")
        if isinstance(lics, list):
            return [str(x["licenseId"]) for x in lics
                    if isinstance(x, dict) and x.get("licenseId")]
        return []
    if isinstance(doc, (list, tuple)):
        return [str(s) for s in doc]
    return []


def _spdx_atlas_counts(core_packages_enumerated: Any) -> dict[str, int]:
    """``{conda_license: package_count}`` from ``core_packages_enumerated`` IFF
    it carries a ``conda_license`` column. It does NOT yet (B1-scope; DW-B6-1),
    so this degrades gracefully to ``{}`` — the upstream-drift partition (below)
    carries the staleness regardless, atlas-independent."""
    df = core_packages_enumerated
    if df is None or getattr(df, "empty", True) or "conda_license" not in getattr(df, "columns", []):
        return {}
    counts: dict[str, int] = {}
    for lic in df["conda_license"]:
        if lic is None or (isinstance(lic, float) and pd.isna(lic)):
            continue
        s = str(lic)
        if s == "":
            continue
        counts[s] = counts.get(s, 0) + 1
    return counts


def report_spdx_schema_gap(
    seed_spdx_schema: Any,
    seed_spdx_upstream_list_raw: Any,
    core_packages_enumerated: Any,
) -> pd.DataFrame:
    """§ 3.4 ``report_spdx_schema_gap`` — propose ``spdx.schema.json`` enum
    additions by diffing the vendored enum against the upstream SPDX list, ranked
    by atlas license usage (legacy ``spdx_schema_gap.py``). READ-ONLY report; git
    review decides. Emits ONE report with a ``tier`` column:

    - ``add-to-schema`` — a real upstream SPDX ID the vendored enum misses, used
      by atlas packages (package-count-ranked). Empty until ``conda_license``
      lands (DW-B6-1).
    - ``non-standard`` — an atlas license the enum misses that is NOT upstream
      either (report-only normalization candidate). Empty until DW-B6-1.
    - ``upstream-drift`` — every upstream ID absent from the vendored enum
      (atlas-independent — so the report is non-empty even without
      ``conda_license``); legacy ``--drift = sorted(upstream - vendored)``.
    """
    # graceful on a malformed/enum-less schema (AD-13/AD-15: a derived report
    # node degrades, never crashes the per-rebuild run) — .get, not [].
    vendored = set(seed_spdx_schema.get("enum") or []) if isinstance(seed_spdx_schema, dict) else set()
    upstream = set(_spdx_upstream_ids(seed_spdx_upstream_list_raw))
    if not upstream:
        return pd.DataFrame(columns=_SPDX_COLS)
    atlas_counts = _spdx_atlas_counts(core_packages_enumerated)
    result = _classify_spdx(atlas_counts, vendored, upstream)
    records: list[dict[str, Any]] = []
    for r in result["add_to_schema"]:
        records.append({"license": r["license"], "spdx_id": r["spdx_id"],
                        "packages": r["packages"], "tier": "add-to-schema"})
    for r in result["non_standard"]:
        records.append({"license": r["license"], "spdx_id": None,
                        "packages": r["packages"], "tier": "non-standard"})
    for spdx_id in sorted(upstream - vendored):
        records.append({"license": spdx_id, "spdx_id": spdx_id,
                        "packages": None, "tier": "upstream-drift"})
    return pd.DataFrame(records, columns=_SPDX_COLS).reset_index(drop=True)


# ---------------------------------------------------------------------------
# report_license_map_gap  (legacy license_map_gap.py:classify / _is_junk /
#                          _candidates / _cand_pattern)
# ---------------------------------------------------------------------------

_LICMAP_COLS = ["license_raw", "packages", "candidates", "confidence", "suggested_spdx"]

# legacy license_map_gap.py — IGNORECASE expression matcher (lowercase operators).
_LICMAP_EXPRESSION_RE = re.compile(r"[()]|(?:^|\s)(?:AND|OR|WITH)(?:\s|$)", re.IGNORECASE)
_LICMAP_CANDIDATE_PAT_CACHE: dict[str, "re.Pattern[str]"] = {}
_LICMAP_MAX_LEN = 60
_LICMAP_JUNK_SUBSTRINGS = ("see ", "http://", "https://", "copyright", "\n")


def _cand_pattern(lid: str) -> "re.Pattern[str]":
    # legacy license_map_gap.py:_cand_pattern — VERBATIM (whole-token matcher).
    pat = _LICMAP_CANDIDATE_PAT_CACHE.get(lid)
    if pat is None:
        pat = re.compile(r"(?:^|[^0-9a-z])" + re.escape(lid) + r"(?:$|[^0-9a-z])")
        _LICMAP_CANDIDATE_PAT_CACHE[lid] = pat
    return pat


def _is_junk(form: str) -> bool:
    # legacy license_map_gap.py:_is_junk — VERBATIM.
    low = form.lower().strip()
    if not low or low == "unknown" or len(form) > _LICMAP_MAX_LEN:
        return True
    if any(j in low for j in _LICMAP_JUNK_SUBSTRINGS):
        return True
    if _LICMAP_EXPRESSION_RE.search(form):  # compound expression → not one entry
        return True
    return False


def _licmap_candidates(form: str, enum_by_lower: dict[str, str]) -> list[str]:
    """legacy license_map_gap.py:_candidates — VERBATIM. Vendored SPDX ids whose
    lowercased id is a whole-token match inside the lowercased form (len>=3)."""
    low = form.lower()
    hits: list[str] = []
    for lid, canon in enum_by_lower.items():
        if len(lid) < 3:  # skip 2-char ids (too noisy)
            continue
        if _cand_pattern(lid).search(low):
            hits.append(canon)
    return sorted(set(hits))


def _classify_licmap(
    unmapped: dict[str, int],
    enum: set[str],
    seed: dict[str, str],
) -> list[dict[str, Any]]:
    """legacy license_map_gap.py:classify — VERBATIM. One proposal per
    un-mapped, non-junk, not-already-seeded form. ``likely`` = exactly one
    candidate; else ``report``."""
    enum_by_lower = {e.lower(): e for e in enum}
    proposals: list[dict[str, Any]] = []
    for form, count in unmapped.items():
        if form.lower() in seed or _is_junk(form):
            continue
        cands = _licmap_candidates(form, enum_by_lower)
        proposals.append({
            "license_raw": form,
            "packages": count,
            "candidates": cands,
            "confidence": "likely" if len(cands) == 1 else "report",
            "suggested_spdx": cands[0] if len(cands) == 1 else None,
        })
    proposals.sort(key=lambda p: (-p["packages"], p["license_raw"].lower()))
    return proposals


def _unmapped_licenses(pypi_intelligence_enriched: Any) -> dict[str, int]:
    """``{TRIM(license_raw): package_count}`` for ``pypi_intelligence_enriched``
    rows the in-code ``_LICENSE_TO_SPDX`` map missed — i.e. ``license_spdx`` is
    NULL/NaN with a non-empty ``license_raw`` (legacy
    ``v_pypi_intelligence_valid WHERE license_spdx IS NULL``)."""
    df = pypi_intelligence_enriched
    if (df is None or getattr(df, "empty", True)
            or not {"license_spdx", "license_raw"} <= set(getattr(df, "columns", []))):
        return {}
    counts: dict[str, int] = {}
    for spdx, raw in zip(df["license_spdx"], df["license_raw"]):
        spdx_null = spdx is None or (isinstance(spdx, float) and pd.isna(spdx)) or str(spdx).strip() == ""
        if not spdx_null:
            continue
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            continue
        form = str(raw).strip()
        if form == "":
            continue
        counts[form] = counts.get(form, 0) + 1
    return counts


def report_license_map_gap(
    seed_spdx_schema: Any,
    pypi_intelligence_enriched: Any,
) -> pd.DataFrame:
    """§ 3.4 ``report_license_map_gap`` — propose ``_LICENSE_TO_SPDX`` entries by
    ranking raw PyPI license strings that currently normalize to nothing (legacy
    ``license_map_gap.py``). READ-ONLY report; git review decides. Candidates
    come from the vendored SPDX enum (``seed_spdx_schema['enum']``).

    NOTE (license-map wiring): the seed exclusion (``_LICENSE_TO_SPDX``) defaults
    to the EMPTY dict — a deliberate no-op belt-and-braces. ``license_spdx IS
    NULL`` upstream ALREADY encodes the in-code map's verdict (its misses), so
    the map is honored transitively and re-importing it from ``.claude/**`` (HARD
    read-only) would be redundant AND off-package. ``candidates`` is serialized
    as a comma-joined string (ParquetDataset needs serializable cells)."""
    # graceful on a malformed/enum-less schema (AD-13/AD-15) — .get, not [].
    enum = set(seed_spdx_schema.get("enum") or []) if isinstance(seed_spdx_schema, dict) else set()
    unmapped = _unmapped_licenses(pypi_intelligence_enriched)
    if not unmapped:
        return pd.DataFrame(columns=_LICMAP_COLS)
    seed: dict[str, str] = {}  # documented no-op (see docstring)
    proposals = _classify_licmap(unmapped, enum, seed)
    records = [
        {
            "license_raw": p["license_raw"],
            "packages": p["packages"],
            "candidates": ",".join(p["candidates"]),
            "confidence": p["confidence"],
            "suggested_spdx": p["suggested_spdx"],
        }
        for p in proposals
    ]
    return pd.DataFrame(records, columns=_LICMAP_COLS).reset_index(drop=True)
