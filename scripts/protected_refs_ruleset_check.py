#!/usr/bin/env python3
"""Detector: live GitHub rulesets match the roster-derived protected-refs document.

WHY scope=runtime: the check calls ``gh api`` against repository rulesets and
``rate_limit`` — host credentials and live settings a CI runner must not treat
as a vacuous pass (steward CAP-165 / Story 85.2).

Exit 0 when the declared document matches the roster render, marshal policy
branch entries match the roster, and (unless ``--fixture``) live rulesets match
the document. Exit 1 naming each drift. Exit 2 when GitHub is unauthenticated,
rate-limited, or any API call fails — never pass on an unobservable read (AD-8).
"""
from __future__ import annotations

DETECTOR = {"scope": "runtime"}

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _protected_refs_ruleset_lib as lib  # noqa: E402

DEFAULT_REPO = "rxm7706/local-recipes"


def _gh_json(args: list[str], *, timeout: int = 60) -> tuple[Any | None, str]:
    try:
        proc = subprocess.run(
            ["gh", "api", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}"
        return None, err
    try:
        return json.loads(proc.stdout), ""
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON from gh api: {exc}"


def gh_has_authenticated_quota() -> tuple[bool, str]:
    data, err = _gh_json(["rate_limit"])
    if data is None:
        return False, err or "gh api rate_limit failed"
    core = (data.get("resources") or {}).get("core") or {}
    limit = int(core.get("limit") or 0)
    if limit <= 60:
        return False, "gh api rate_limit shows no authenticated quota (core limit 60)"
    return True, ""


def fetch_live_rulesets(repo: str) -> tuple[dict[str, dict[str, Any]] | None, str]:
    listing, err = _gh_json([f"repos/{repo}/rulesets"])
    if listing is None:
        return None, err
    if not isinstance(listing, list):
        return None, "rulesets list response was not an array"
    live: dict[str, dict[str, Any]] = {}
    for row in listing:
        if not isinstance(row, dict):
            continue
        ruleset_id = row.get("id")
        name = row.get("name")
        if ruleset_id is None or not name:
            continue
        detail, err = _gh_json([f"repos/{repo}/rulesets/{ruleset_id}"])
        if detail is None:
            return None, err
        detail["name"] = name
        live[name] = lib.normalize_ruleset(detail)
    return live, ""


def check_document_freshness(
    roster: dict[str, Any],
    *,
    document_path: Path | None = None,
) -> list[str]:
    diffs: list[str] = []
    doc_path = document_path or lib.DOCUMENT_PATH
    rendered = lib.serialize_document(lib.render_document(roster))
    if not doc_path.is_file():
        diffs.append(f"missing declared document {doc_path.relative_to(ROOT)}")
        return diffs
    on_disk = doc_path.read_text(encoding="utf-8")
    if on_disk != rendered:
        diffs.append(
            "docs/governance/rulesets/protected-refs.json is not byte-identical to "
            "a roster render — regenerate from the roster, do not hand-edit"
        )
    return diffs


def run_check(
    *,
    roster: dict[str, Any],
    fixture_live: dict[str, dict[str, Any]] | None,
    repo: str,
    skip_live: bool,
) -> tuple[list[str], int | None]:
    """Return (findings, exit_code_override). exit_code_override 2 = could not observe live."""
    diffs: list[str] = []
    diffs.extend(check_document_freshness(roster))
    diffs.extend(lib.compare_marshal_policy_to_roster(roster))

    declared_doc = lib.render_document(roster)
    declared_map = lib.rulesets_by_name(declared_doc)

    if fixture_live is not None:
        diffs.extend(lib.compare_ruleset_maps(declared_map, fixture_live))
        return diffs, None

    if skip_live:
        return diffs, None

    ok, err = gh_has_authenticated_quota()
    if not ok:
        return diffs + [err], 2

    live_map, err = fetch_live_rulesets(repo)
    if live_map is None:
        return diffs + [f"live ruleset fetch failed: {err}"], 2

    diffs.extend(lib.compare_ruleset_maps(declared_map, live_map))
    return diffs, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument(
        "--fixture",
        type=Path,
        help="compare declared rulesets to this JSON file instead of live GitHub",
    )
    parser.add_argument(
        "--skip-live",
        action="store_true",
        help="skip live GitHub ruleset fetch (document + marshal policy only)",
    )
    parser.add_argument(
        "--write-document",
        action="store_true",
        help="write docs/governance/rulesets/protected-refs.json from the roster",
    )
    parser.add_argument("--repo", default=DEFAULT_REPO, help="owner/repo for live gh api")
    args = parser.parse_args()

    roster = lib.load_roster()

    if args.write_document:
        lib.DOCUMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
        lib.DOCUMENT_PATH.write_text(
            lib.serialize_document(lib.render_document(roster)), encoding="utf-8"
        )
        if not args.fixture and not args.skip_live:
            pass

    fixture_live: dict[str, dict[str, Any]] | None = None
    if args.fixture is not None:
        raw = json.loads(args.fixture.read_text(encoding="utf-8"))
        if "rulesets" in raw and isinstance(raw["rulesets"], list):
            fixture_live = {
                rs["name"]: lib.normalize_ruleset(rs)
                for rs in raw["rulesets"]
                if rs.get("name")
            }
        else:
            fixture_live = {
                name: lib.normalize_ruleset(rs)
                for name, rs in raw.items()
                if isinstance(rs, dict)
            }

    diffs, override = run_check(
        roster=roster,
        fixture_live=fixture_live,
        repo=args.repo,
        skip_live=args.skip_live or args.write_document,
    )

    if args.json:
        print(json.dumps({"findings": diffs}, indent=2))
    else:
        for line in diffs:
            print(line)

    if override == 2:
        return 2
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
