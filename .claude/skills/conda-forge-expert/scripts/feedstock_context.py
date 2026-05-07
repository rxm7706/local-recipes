#!/usr/bin/env python3
"""Surface open issues + recent closed issues from an existing conda-forge feedstock
as planning context for the agent before recipe generation/update.

v6.4 implementation of item 3c. Non-blocking — produces a structured note that
the agent can present to the user. Never auto-applied or auto-fixed.

Issue scope (per session memory D2):
  - All open issues (capped at 50 to bound token cost)
  - Last 10 closed issues
  - Each issue: number, title, labels, state, author, url, closed_at (when closed)

Output is a JSON dict the agent renders or includes in PR descriptions.

CLI:
    feedstock_context.py <pkg_name>
    feedstock_context.py <pkg_name> --max-open 30 --max-closed 5
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "conda-forge-expert"
_CACHE_DIR = _DATA_DIR / "feedstock_issue_cache"
_CACHE_TTL_SECONDS = 1800  # 30 min — issue state changes faster than recipe content


@dataclass
class IssueSummary:
    number: int
    title: str
    state: str  # "open" | "closed"
    author: str
    url: str
    labels: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    closed_at: Optional[str] = None  # only for closed issues
    comments: int = 0


@dataclass
class FeedstockContext:
    pkg_name: str
    feedstock_repo: Optional[str] = None
    feedstock_exists: bool = False
    open_issues: List[IssueSummary] = field(default_factory=list)
    recent_closed_issues: List[IssueSummary] = field(default_factory=list)
    cached: bool = False
    error: Optional[str] = None


def _cache_path(pkg_name: str) -> Path:
    safe = pkg_name.replace("/", "_").replace(" ", "_")
    return _CACHE_DIR / f"{safe}.json"


def _load_cache(pkg_name: str) -> Optional[dict]:
    cache = _cache_path(pkg_name)
    if not cache.exists():
        return None
    try:
        if time.time() - cache.stat().st_mtime > _CACHE_TTL_SECONDS:
            return None
        return json.loads(cache.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _store_cache(pkg_name: str, data: dict) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(pkg_name).write_text(json.dumps(data, indent=2))
    except OSError:
        pass


def _gh_issue_list(repo: str, state: str, limit: int) -> List[dict]:
    """Fetch issues via `gh issue list` (excludes PRs by default)."""
    cmd = [
        "gh", "issue", "list",
        "--repo", repo,
        "--state", state,
        "--limit", str(limit),
        "--json", "number,title,state,author,url,labels,createdAt,closedAt,comments",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    try:
        return json.loads(result.stdout) or []
    except json.JSONDecodeError:
        return []


def _to_summary(api_issue: dict) -> IssueSummary:
    author = api_issue.get("author") or {}
    labels = [lbl.get("name", "") for lbl in (api_issue.get("labels") or []) if lbl.get("name")]
    # gh issue list returns `comments` as a list of comment objects, not a count.
    raw_comments = api_issue.get("comments", 0)
    if isinstance(raw_comments, list):
        comment_count = len(raw_comments)
    else:
        try:
            comment_count = int(raw_comments or 0)
        except (TypeError, ValueError):
            comment_count = 0
    return IssueSummary(
        number=api_issue.get("number", 0),
        title=api_issue.get("title", ""),
        state=str(api_issue.get("state", "open")).lower(),
        author=author.get("login", "") if isinstance(author, dict) else "",
        url=api_issue.get("url", ""),
        labels=labels,
        created_at=api_issue.get("createdAt"),
        closed_at=api_issue.get("closedAt"),
        comments=comment_count,
    )


def fetch_feedstock_context(
    pkg_name: str,
    *,
    max_open: int = 50,
    max_closed: int = 10,
    use_cache: bool = True,
) -> FeedstockContext:
    """Fetch open + recent closed issues for `conda-forge/<pkg_name>-feedstock`.

    Returns a FeedstockContext with `feedstock_exists=False` (and empty lists)
    when the feedstock doesn't exist — callers treat this as "no prior context."
    """
    if not pkg_name or "/" in pkg_name:
        return FeedstockContext(pkg_name=pkg_name, error="invalid package name")

    if use_cache:
        cached = _load_cache(pkg_name)
        if cached is not None:
            cached["cached"] = True
            cached["open_issues"] = [IssueSummary(**i) for i in cached.get("open_issues", [])]
            cached["recent_closed_issues"] = [IssueSummary(**i) for i in cached.get("recent_closed_issues", [])]
            return FeedstockContext(**cached)

    feedstock_repo = f"conda-forge/{pkg_name}-feedstock"

    # Quick existence probe — saves two failing issue list calls when feedstock is absent.
    try:
        repo_check = subprocess.run(
            ["gh", "api", f"/repos/{feedstock_repo}"],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return FeedstockContext(pkg_name=pkg_name, error="gh CLI unavailable or timed out")
    if repo_check.returncode != 0:
        ctx = FeedstockContext(pkg_name=pkg_name, feedstock_repo=feedstock_repo, feedstock_exists=False)
        _store_cache(pkg_name, asdict(ctx))
        return ctx

    open_raw = _gh_issue_list(feedstock_repo, "open", max_open)
    closed_raw = _gh_issue_list(feedstock_repo, "closed", max_closed)

    ctx = FeedstockContext(
        pkg_name=pkg_name,
        feedstock_repo=feedstock_repo,
        feedstock_exists=True,
        open_issues=[_to_summary(i) for i in open_raw],
        recent_closed_issues=[_to_summary(i) for i in closed_raw],
    )
    _store_cache(pkg_name, asdict(ctx))
    return ctx


def _serialize(ctx: FeedstockContext) -> dict:
    """asdict-compatible serialization for the dataclass nest."""
    return {
        "pkg_name": ctx.pkg_name,
        "feedstock_repo": ctx.feedstock_repo,
        "feedstock_exists": ctx.feedstock_exists,
        "open_count": len(ctx.open_issues),
        "recent_closed_count": len(ctx.recent_closed_issues),
        "open_issues": [asdict(i) for i in ctx.open_issues],
        "recent_closed_issues": [asdict(i) for i in ctx.recent_closed_issues],
        "cached": ctx.cached,
        "error": ctx.error,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "feedstock_context").split("\n")[0]
    )
    parser.add_argument("pkg_name", help="Package name (e.g. 'numpy')")
    parser.add_argument("--max-open", type=int, default=50, help="Cap on open issues fetched (default: 50)")
    parser.add_argument("--max-closed", type=int, default=10, help="Cap on recent closed issues fetched (default: 10)")
    parser.add_argument("--no-cache", action="store_true", help="Bypass the local cache")
    args = parser.parse_args()

    ctx = fetch_feedstock_context(
        args.pkg_name,
        max_open=args.max_open,
        max_closed=args.max_closed,
        use_cache=not args.no_cache,
    )
    print(json.dumps(_serialize(ctx), indent=2, default=str))
    return 0 if ctx.error is None else 1


if __name__ == "__main__":
    sys.exit(main())
