#!/usr/bin/env python
"""Mutation-only stamper for the flag rule's pre-rule baseline (doctor Story 34.1).

The reader is `scripts/flag_rule.py` (`is_post_rule`); this script owns the two writes
docs/governance/flag-rule-baseline.json ever takes:

    python scripts/flag_rule_baseline.py --snapshot   # ONCE, at the ruling SHA
    python scripts/flag_rule_baseline.py --prune      # remove paths that no longer exist

The population is every story spec (`spec-<epic>-<story>-*.md` under a project's
planning-artifacts/specs/, memlogs excluded) in the git tree of the ruling SHA -- the merge of
PR #1654, the commit at which spec-feature-flag-governance read `status: ready`. It is read
from that commit's tree, never the working tree: HEAD already holds specs minted after the
rule, and those are post-rule by design. A spec is post-rule exactly when it is absent.

`--snapshot` refuses when a baseline already exists (re-taking it would launder every spec
minted since). `--prune` only ever removes. There is deliberately no `--add`: a spec minted
after the rule carries a `flag:` block or a `flag-exempt:` value, not a baseline entry.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import flag_rule  # noqa: E402

# PR #1654 (`Merge intake-triage-2026-09-28 into main`): the Spec reads `status: ready` here.
RULING_SHA = "5e977accb9643ff81f02ef9feca3e435d86816f9"
RULE_DATE = "2026-09-28"

_COMMENT = [
    "flag-rule baseline (doctor Story 34.1, spec-feature-flag-governance CAP-1).",
    "Every story spec present in the git tree of `ruling_sha`, the merge of PR #1654 at which the",
    "Spec reached `ready`. A spec listed here is pre-rule: it warns and never reds (eventual",
    "consistency: a retrofit gives it a block or an exemption). A spec absent from this list is",
    "post-rule, whatever its own `created:` says. This file only ever SHRINKS --",
    "`python scripts/flag_rule_baseline.py --prune` removes paths that no longer exist. A",
    "hand-added path here is a governance act and a finding.",
]


def _git(repo_root: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=repo_root, capture_output=True, check=True).stdout


def snapshot(repo_root: Path, ruling_sha: str = RULING_SHA) -> dict[str, Any]:
    """The baseline document for the story specs in `ruling_sha`'s tree."""
    full_sha = _git(repo_root, "rev-parse", "--verify", f"{ruling_sha}^{{commit}}").decode().strip()
    # -z, because the default core.quotePath octal-quotes a non-ASCII path (an accented slug).
    names = _git(repo_root, "ls-tree", "-r", "-z", "--name-only", full_sha).decode("utf-8").split("\0")
    return {
        "$comment": _COMMENT,
        "ruling_sha": full_sha,
        "rule_date": RULE_DATE,
        "specs": sorted(n for n in names if n and flag_rule.is_story_spec(n)),
    }


def prune(repo_root: Path) -> tuple[dict[str, Any], list[str]]:
    """(the baseline without paths that no longer exist, the removed paths)."""
    data = flag_rule.read_baseline(repo_root)
    kept: list[str] = []
    removed: list[str] = []
    for rel in data["specs"]:
        (kept if (repo_root / rel).exists() else removed).append(rel)
    return {**data, "specs": kept}, removed


def _write(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None, repo_root: Path | None = None) -> int:
    ap = argparse.ArgumentParser(prog="flag-rule-baseline", description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snapshot", action="store_true", help="take the dated snapshot (once)")
    g.add_argument("--prune", action="store_true", help="remove paths that no longer exist")
    ap.add_argument("--ruling-sha", default=RULING_SHA, help="commit whose tree is the population")
    ap.add_argument("--force", action="store_true", help="allow --snapshot over an existing baseline")
    args = ap.parse_args(argv)

    root = repo_root if repo_root is not None else REPO_ROOT
    path = root / flag_rule.BASELINE_REL
    rel = flag_rule.BASELINE_REL.as_posix()
    if args.snapshot:
        if path.exists() and not args.force:
            print(f"refusing: {rel} exists -- the snapshot is taken once; use --prune, or --force if you really mean it")
            return 1
        try:
            data = snapshot(root, args.ruling_sha)
        except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
            print(f"cannot snapshot at {args.ruling_sha}: {exc}")
            return 2
        _write(path, data)
        print(f"snapshot: {len(data['specs'])} story specs at {data['ruling_sha']}")
        return 0

    try:
        data, removed = prune(root)
    except flag_rule.BaselineUnreadable as exc:
        print(exc)
        return 2
    if not removed:
        print("prune: nothing to remove")
        return 0
    _write(path, data)
    print(f"prune: removed {len(removed)} entr{'y' if len(removed) == 1 else 'ies'}")
    for entry in removed:
        print(f"  - {entry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
