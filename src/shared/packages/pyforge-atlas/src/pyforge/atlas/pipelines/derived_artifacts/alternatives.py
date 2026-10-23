"""The find-alternative candidates for every archived package (Story 37.7, CAP-69).

A port of legacy ``find_alternative.py``'s ``find_alternatives`` scorer, run for each archived package on the channel
instead of one package per query. PURE: every input arrives as a frame.

Legacy's score, kept: keyword Jaccard x3 + summary-term Jaccard x2 + shared-dependent Jaccard x4 + shared-maintainer
Jaccard x1, over candidates with a keyword or summary-term overlap, dropped under 0.10; the composite multiplies by
``0.5 + 0.5 * recency`` (1.0 within 30 days, falling linearly to 0 over five years, 1.0 with no upload time) and by
0.5 for a candidate with no downloads; the top ``limit`` by composite.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from typing import Any

import pandas as pd

from ...datasets.core_sources import ABOUT_FIELDS, package_recipe_fields

#: legacy ``find_alternative.py``'s defaults
LIMIT = 10
MIN_SCORE = 0.10
WEIGHTS = {"kw": 3, "term": 2, "dep": 4, "maint": 1}
RECENCY_SPAN_DAYS = 5 * 365
#: the candidate's adoption-stage inputs, passed through so the board classifies them as build_packages_model does
STAGE_COLUMNS = ["latest_upload_age_days", "releases_30d", "total_versions"]
COLUMNS = [
    "archived_name",
    "candidate_name",
    "rank",
    "similarity_score",
    "kw_score",
    "term_score",
    "dep_score",
    "maint_score",
    "downloads_total",
    "summary",
    *STAGE_COLUMNS,
]

_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "with",
    "is", "are", "be", "this", "that", "from", "as", "by", "at", "it",
    "package", "library", "module", "tool", "tools", "python", "py",
    "client", "lib", "support", "via", "based", "uses", "use", "using",
    "implementation", "wrapper", "interface", "api",
}  # fmt: skip
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]+")


def tokenize(text: Any) -> frozenset[str]:
    """Legacy ``_tokenize``: lowercased words of three characters or more, stopwords out."""
    if not isinstance(text, str) or not text:
        return frozenset()
    return frozenset(t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 2 and t.lower() not in _STOPWORDS)


def keyword_set(value: Any) -> frozenset[str]:
    """Legacy's keyword parse: a list's non-empty entries, lowercased; anything else is none."""
    if isinstance(value, str) or not hasattr(value, "__iter__"):
        return frozenset()
    return frozenset(str(k).lower() for k in value if k)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Legacy ``_jaccard``: 0 when either side is empty."""
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _grouped(frame: pd.DataFrame | None, key: str, value: str) -> dict[str, frozenset[str]]:
    if frame is None or frame.empty or not {key, value} <= set(frame.columns):
        return {}
    pairs = frame[[key, value]].dropna().drop_duplicates()
    return {str(k): frozenset(str(v) for v in group) for k, group in pairs.groupby(key)[value]}


def _as_bool(value: Any) -> bool:
    return False if value is None or pd.isna(value) else bool(value)


def _num(value: Any) -> float | None:
    return None if value is None or pd.isna(value) else float(value)


def _column(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    return frame[column].to_dict() if column in frame.columns else {}


def _factor(upload: float | None, downloads: float | None, now_ts: int) -> float:
    """Legacy's composite multiplier: ``0.5 + 0.5 * recency``, halved for a candidate with no downloads."""
    recency = 1.0 if not upload else max(0.0, 1.0 - (now_ts - upload) / 86400 / RECENCY_SPAN_DAYS)
    return (0.5 + 0.5 * recency) * (1.0 if (downloads or 0) > 0 else 0.5)


def score_alternative_candidates(
    core_cf_graph_raw: pd.DataFrame,
    core_feedstock_attribution: pd.DataFrame,
    semantic_packages: pd.DataFrame,
    core_dependencies: pd.DataFrame,
    vcs_package_maintainers: pd.DataFrame,
    now: int | None = None,
) -> pd.DataFrame:
    # legacy: find_alternative.py::find_alternatives (one query per archived package)
    """Rank up to ``LIMIT`` alternatives for each archived package on the channel.

    The packages are ``semantic_packages`` rows. One is archived when ``semantic_packages.feedstock_archived`` (from
    ``vcs_archived_feedstocks``) or the cf-graph's ``archived`` flag says so; a candidate is active, unarchived and
    not the package itself. Summary and keywords come from the cf-graph anchor rows by feedstock attribution;
    dependents from ``core_dependencies`` (who depends on a package); maintainers from ``vcs_package_maintainers``.
    """
    if semantic_packages is None or semantic_packages.empty or "conda_name" not in semantic_packages.columns:
        return _typed(pd.DataFrame(columns=COLUMNS))
    now_ts = int(time.time()) if now is None else now
    pkgs = semantic_packages.dropna(subset=["conda_name"]).drop_duplicates("conda_name")
    pkgs = pkgs.assign(conda_name=pkgs["conda_name"].astype(str)).set_index("conda_name")
    about = package_recipe_fields(core_cf_graph_raw, core_feedstock_attribution, (*ABOUT_FIELDS, "feedstock_archived"))
    about = about.drop_duplicates("conda_name").set_index("conda_name")
    summaries, graph_archived = _column(about, "summary"), _column(about, "feedstock_archived")
    row_archived, status = _column(pkgs, "feedstock_archived"), _column(pkgs, "latest_status")
    uploads, downloads = _column(pkgs, "latest_conda_upload"), _column(pkgs, "downloads_total")
    stage = {col: _column(pkgs, col) for col in STAGE_COLUMNS}

    names = list(pkgs.index)
    is_archived = {n: _as_bool(row_archived.get(n)) or _as_bool(graph_archived.get(n)) for n in names}
    terms = {n: tokenize(summaries.get(n)) for n in names}
    about_keywords = _column(about, "keywords")
    keywords = {n: keyword_set(about_keywords.get(n)) for n in names}
    dependents = _grouped(
        core_dependencies.rename(columns={"conda_name": "dependent", "depends_on": "conda_name"})
        if core_dependencies is not None
        else None,
        "conda_name",
        "dependent",
    )
    maintainers = _grouped(vcs_package_maintainers, "conda_name", "maintainer")

    candidates = [n for n in names if status.get(n) == "active" and not is_archived[n]]
    factor = {n: _factor(_num(uploads.get(n)), _num(downloads.get(n)), now_ts) for n in candidates}
    by_keyword: dict[str, list[str]] = defaultdict(list)
    by_term: dict[str, list[str]] = defaultdict(list)
    for name in candidates:
        for word in keywords[name]:
            by_keyword[word].append(name)
        for word in terms[name]:
            by_term[word].append(name)

    rows: list[dict[str, Any]] = []
    empty: frozenset[str] = frozenset()
    for src in (n for n in names if is_archived[n]):
        src_kw, src_terms = keywords[src], terms[src]
        src_deps, src_maint = dependents.get(src, empty), maintainers.get(src, empty)
        pool = {c for word in src_kw for c in by_keyword.get(word, ())}
        pool.update(c for word in src_terms for c in by_term.get(word, ()))  # never src: it is archived
        scored = []
        for cand in pool:
            kw = jaccard(src_kw, keywords[cand])
            term = jaccard(src_terms, terms[cand])
            dep = jaccard(src_deps, dependents.get(cand, empty)) if src_deps else 0.0
            maint = jaccard(src_maint, maintainers.get(cand, empty)) if src_maint else 0.0
            score = WEIGHTS["kw"] * kw + WEIGHTS["term"] * term + WEIGHTS["dep"] * dep + WEIGHTS["maint"] * maint
            if score < MIN_SCORE:
                continue
            scored.append((round(score * factor[cand], 3), cand, kw, term, dep, maint))
        scored.sort(key=lambda s: (-s[0], s[1]))
        for rank, (composite, cand, kw, term, dep, maint) in enumerate(scored[:LIMIT], start=1):
            rows.append(
                {
                    "archived_name": src,
                    "candidate_name": cand,
                    "rank": rank,
                    "similarity_score": composite,
                    "kw_score": round(kw, 3),
                    "term_score": round(term, 3),
                    "dep_score": round(dep, 3),
                    "maint_score": round(maint, 3),
                    "downloads_total": int(_num(downloads.get(cand)) or 0),
                    "summary": summaries.get(cand),
                    **{col: _num(stage[col].get(cand)) for col in STAGE_COLUMNS},
                }
            )
    out = _typed(pd.DataFrame(rows, columns=COLUMNS))
    return out.sort_values(["archived_name", "rank"], kind="stable", ignore_index=True)


def _typed(frame: pd.DataFrame) -> pd.DataFrame:
    """Typed columns, so an empty or all-null column still reads back as a number, not Arrow ``null``."""
    return frame.astype(
        {
            "rank": "int64",
            **dict.fromkeys(["similarity_score", "kw_score", "term_score", "dep_score", "maint_score"], "float64"),
            "downloads_total": "int64",
            **dict.fromkeys(STAGE_COLUMNS, "Int64"),
        }
    )
