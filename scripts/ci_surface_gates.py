#!/usr/bin/env python3
"""Judge CI workflow vars.* switches against docs/governance/ci-surfaces.yaml.

Offline by default (--check). Optional --live adds GitHub Actions workflow state
rules via read-only ``gh api`` (never part of detectors-ci when unauthenticated).

Exit 0 clean, 1 findings, 2 cannot observe (Story 99.1 / CAP-166).
"""
from __future__ import annotations

DETECTOR = {"scope": "repo"}

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ci_surface_gates_lib as lib  # noqa: E402

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
    remaining = int(core.get("remaining") or 0)
    if limit <= 60:
        return False, "gh api rate_limit shows no authenticated quota (core limit 60)"
    if remaining <= 0:
        return False, "gh api rate_limit core remaining is 0"
    return True, ""


def fetch_workflow_states(repo: str) -> tuple[list[dict[str, Any]] | None, str]:
    data, err = _gh_json([f"repos/{repo}/actions/workflows"])
    if data is None:
        return None, err
    workflows = data.get("workflows")
    if not isinstance(workflows, list):
        return None, "workflows response missing workflows array"
    return workflows, ""


def run_check(
    *,
    root: Path,
    registry_path: Path,
    schema_path: Path,
    workflows_dir: Path | None,
    live: bool,
    fixture_workflows: list[dict[str, Any]] | None,
    repo: str,
) -> tuple[list[str], int | None]:
    if not registry_path.is_file():
        return [f"missing registry {registry_path.relative_to(root)}"], 2
    try:
        registry = lib.load_registry(registry_path)
    except (OSError, ValueError) as exc:
        return [str(exc)], 2

    findings: list[str] = []
    if schema_path.is_file():
        findings.extend(lib.validate_registry_schema(registry, schema_path))

    findings.extend(
        lib.offline_check(root, registry, workflows_dir=workflows_dir)
    )

    if not live:
        return findings, None

    if fixture_workflows is not None:
        findings.extend(lib.live_check(registry, workflows_payload=fixture_workflows))
        return findings, None

    ok, err = gh_has_authenticated_quota()
    if not ok:
        return findings + [err], 2

    workflows, err = fetch_workflow_states(repo)
    if workflows is None:
        return findings + [f"live workflow fetch failed: {err}"], 2

    findings.extend(lib.live_check(registry, workflows_payload=workflows))
    return findings, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="run offline registry/workflow checks (default when no other mode)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="also compare GitHub workflow disabled_manually state (read-only gh api)",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / lib.REGISTRY_REL,
        help="path to ci-surfaces.yaml",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=ROOT / lib.SCHEMA_REL,
        help="path to ci-surfaces.schema.json",
    )
    parser.add_argument(
        "--workflows-dir",
        type=Path,
        default=None,
        help="override .github/workflows for fixture trees",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root",
    )
    parser.add_argument(
        "--fixture-workflows",
        type=Path,
        help="JSON file with a workflows array (gh api shape) for live-mode tests",
    )
    parser.add_argument("--repo", default=DEFAULT_REPO, help="owner/repo for --live")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = parser.parse_args()

    fixture_payload: list[dict[str, Any]] | None = None
    if args.fixture_workflows is not None:
        raw = json.loads(args.fixture_workflows.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("workflows"), list):
            fixture_payload = raw["workflows"]
        elif isinstance(raw, list):
            fixture_payload = raw
        else:
            print("fixture-workflows must be a list or {workflows: [...]}", file=sys.stderr)
            return 2

    live = args.live or args.fixture_workflows is not None
    findings, override = run_check(
        root=args.root,
        registry_path=args.registry,
        schema_path=args.schema,
        workflows_dir=args.workflows_dir,
        live=live,
        fixture_workflows=fixture_payload,
        repo=args.repo,
    )

    if args.json:
        print(json.dumps({"findings": findings}, indent=2))
    else:
        for line in findings:
            print(line)

    if override == 2:
        return 2
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
