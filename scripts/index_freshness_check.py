#!/usr/bin/env python3
"""Index freshness for codegraph and cocoindex (Story 28.7, CAP-10).

WHAT IT CHECKS
--------------
For each loop home:
  1. Resolve its policy's `[context]` layer declarations
  2. For each ENABLED layer (codegraph, cocoindex), check:
     - Is the index present?
     - If present, is its mtime at or after HEAD's timestamp?
  3. Report advisory (never blocking) findings for missing or stale indices

An index is FRESH when its mtime >= HEAD commit timestamp. This is the same
git-timestamp discipline SPEC-marshal-token-economy CAP-13 requires, and is
deterministic -- no LLM calls, no per-write model decisions.

DEGRADATION
-----------
If git cannot report HEAD's timestamp (not a repo, no commits, no `git`, a
timeout), freshness is not evaluated (no staleness claim is made); the check
reports as OK on presence alone.

EXIT
    0  no stale/missing indices in any loop home
    1  at least one home has a missing or stale index in an enabled layer
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `runtime`: reads host state
# (gitignored Tier-3 loop-home policy + index mtimes), so CI cannot run it.
DETECTOR = {"scope": "runtime"}

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

LOOP_ROOT = Path.home() / ".bmad-loops"
GIT_TIMEOUT_S = 5.0


@dataclass(frozen=True)
class IndexCheck:
    """One index's status in one loop home."""
    home_name: str
    index_name: str  # 'codegraph' or 'cocoindex'
    index_path: str
    status: str  # 'ok', 'missing', 'stale', 'layer-off', 'unavailable'
    reason: str  # human explanation


def head_commit_timestamp(repo_root: Path) -> int | None:
    """HEAD's committer timestamp as a POSIX int, or None when git
    cannot answer. None means 'make no staleness claim'."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None
    if result.returncode != 0:
        return None
    text = (result.stdout or "").strip()
    try:
        return int(text)
    except ValueError:
        return None


def check_index_freshness(
    repo_root: Path, index_path: str, index_name: str
) -> tuple[str, str]:
    """Check if index at index_path is present and fresh.

    Returns (status, reason) tuple.
    Status is one of: 'ok', 'missing', 'stale', 'unavailable'.
    """
    target = repo_root / index_path
    if not target.exists():
        return "missing", f"no {index_name} index at {index_path}"

    # Index is present; check if it's fresh
    head_ts = head_commit_timestamp(repo_root)
    if head_ts is None:
        return "ok", (
            f"index present at {index_path}; freshness not evaluated "
            "(git could not report HEAD's timestamp)"
        )

    try:
        index_mtime = int(target.stat().st_mtime)
    except OSError:
        return "ok", (
            f"index present at {index_path}; freshness not evaluated "
            "(its mtime could not be read)"
        )

    if index_mtime < head_ts:
        return "stale", (
            f"the {index_name} index at {index_path} predates HEAD "
            f"(index mtime {index_mtime}, HEAD committed {head_ts})"
        )

    return "ok", f"index present and fresh at {index_path}"


def load_loop_home_policy(home: Path) -> dict | None:
    """Load a loop home's rendered policy.

    Returns the parsed TOML dict, or None if not found/unreadable.
    """
    policy_path = home / ".bmad-loop" / "policy.toml"
    if not policy_path.exists():
        return None

    try:
        import tomllib
    except ModuleNotFoundError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return None

    try:
        return tomllib.loads(policy_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def resolve_context_layers(policy: dict | None) -> dict | None:
    """Extract [context] block from policy, or None if not present."""
    if not policy:
        return None
    context = policy.get("context")
    if not isinstance(context, dict):
        return None
    return context


def layer_enabled(context_layers: dict | None, layer: str) -> bool:
    """Whether layer is declared on in the context block."""
    if not context_layers:
        return False
    entry = context_layers.get(layer)
    if not isinstance(entry, dict):
        return False
    return bool(entry.get("enabled", False))


def check_home(home: Path) -> list[IndexCheck]:
    """Check all index layers in one loop home."""
    checks: list[IndexCheck] = []
    home_name = home.name

    # Load the rendered policy
    policy = load_loop_home_policy(home)
    context = resolve_context_layers(policy)

    # Canonical index locations — keep aligned with Story 28.3 kit + Scribe seam:
    # - codegraph: pyforge.marshal.seed.model.kit.CODEGRAPH_INDEX_RELPATH
    # - cocoindex: pyforge.scribe.extras.cocoindex_flow.default_cocoindex_index_path
    indices = [
        ("structure-graph", ".codegraph/codegraph.db", "codegraph"),
        (
            "derived-context",
            ".claude/data/pyforge-scribe/cocoindex-index.json",
            "cocoindex",
        ),
    ]

    for layer, rel_path, display_name in indices:
        if not layer_enabled(context, layer):
            checks.append(
                IndexCheck(
                    home_name=home_name,
                    index_name=display_name,
                    index_path=rel_path,
                    status="layer-off",
                    reason=f"the {layer!r} context layer is declared off",
                )
            )
            continue

        status, reason = check_index_freshness(home, rel_path, display_name)
        checks.append(
            IndexCheck(
                home_name=home_name,
                index_name=display_name,
                index_path=rel_path,
                status=status,
                reason=reason,
            )
        )

    return checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="output as JSON")
    ap.add_argument("--verbose", action="store_true", help="show all checks")
    args = ap.parse_args()

    if not LOOP_ROOT.is_dir():
        if args.json:
            print(json.dumps({"results": [], "findings": []}))
        else:
            print("index-freshness — no loop homes at ~/.bmad-loops")
        return 0

    all_checks: list[IndexCheck] = []
    findings: list[dict] = []

    for home in sorted(p for p in LOOP_ROOT.iterdir() if (p / ".git").exists()):
        checks = check_home(home)
        all_checks.extend(checks)

        for check in checks:
            # 'layer-off' is informational, not a finding
            if check.status == "layer-off":
                continue
            # 'ok' and 'unavailable' are not findings
            if check.status == "ok":
                continue
            # 'missing' and 'stale' are advisory findings
            if check.status in ("missing", "stale"):
                code = {
                    ("codegraph", "missing"): "MRS-IDXF-001",
                    ("codegraph", "stale"): "MRS-IDXF-002",
                    ("cocoindex", "missing"): "MRS-IDXF-003",
                    ("cocoindex", "stale"): "MRS-IDXF-004",
                }.get((check.index_name, check.status))
                if code:
                    findings.append(
                        {
                            "code": code,
                            "home": check.home_name,
                            "index": check.index_name,
                            "message": check.reason,
                        }
                    )

    if args.json:
        for check in all_checks:
            print(json.dumps(asdict(check)))
        if findings:
            print(json.dumps({"_findings": findings}))
    else:
        if args.verbose or findings:
            print("index-freshness — checking codegraph and cocoindex staleness\n")
        if findings:
            for finding in findings:
                print(
                    f"  {finding['code']} [{finding['home']:22s}] "
                    f"{finding['index']:9s} — {finding['message']}"
                )
            print()
        elif args.verbose:
            for check in all_checks:
                print(
                    f"  {check.status:9s} {check.home_name:22s} "
                    f"{check.index_name:9s} — {check.reason}"
                )
            print()
        else:
            if all_checks:
                print("index-freshness — all indices fresh or layers off\n")

    # Exit with 1 if any findings, 0 otherwise
    if findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
