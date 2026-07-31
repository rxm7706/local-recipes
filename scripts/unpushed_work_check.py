#!/usr/bin/env python3
"""Detector: no work exists only on this disk.

WHY THIS EXISTS. On 2026-07-31 an operator asked "is marshal's work saved?" and
the answer was no — not for marshal, and not for most of the fleet:

    6 station loop branches          8-9 commits each, none on origin
    4 recover/* branches             ~5,150 lines, none on origin
    herald 1.2 transport             734 lines over 7 files, incl. its story
                                     spec, unpushed since 2026-07-25
    156 dangling commits             real content, one `git gc` from gone
    marshal story 1.8                1,748 lines, committed by the dev phase
                                     ~40 minutes earlier and never pushed

None of it was detected. Nine detectors ran green throughout, because not one of
them asks the question this file asks. It is the same shape as the story-spec
gap that motivated docs/dreams/fidelity-enforcement.md: a real invariant that
everyone assumed and nothing checked.

The precedent is not hypothetical either — scribe 1.3's 1,102 lines survived
only as a dangling commit and were recovered by luck, one collection short of
being unrecoverable.

WHY scope=runtime, AND WHY THAT IS THE POINT. This detector reads LOCAL git
state: branches that exist in this clone, and objects reachable only from this
reflog. A CI runner has neither — a fresh shallow-ish checkout has one branch
and no dangling objects, so this check would pass **vacuously and always** on a
runner. That is a false green of the purest kind: a gate reporting success
because it is standing somewhere the failure cannot occur.

So it is `runtime`, it never runs in CI, and it joins dashboard_drift_check and
loop_stall_check as a detector with nowhere to run automatically — which is the
missing observation plane the Dream names, showing up for the third time.

WHAT COUNTS AS AT RISK:

  unpushed-branch   a local branch, absent from every remote, whose diff against
                    the default remote head contains at least one file. Branches
                    with no unique content are ignored: a merged feature branch
                    lingering locally is untidy, not a risk.
  dangling-commit   an unreachable commit touching more than `--min-files` files
                    and not already preserved under a rescue tag. `git gc` may
                    collect these at any time, without warning.

Remedy is one line and printed with the finding, because a detector that names a
problem without naming its fix is a complaint.
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `runtime`: reads local clone
# state (branches, reflog, dangling objects) that does not exist on a CI runner,
# where this check would pass vacuously.
DETECTOR = {"scope": "runtime"}

import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESCUE_PREFIX = "rescue/dangling-"


def git(*args: str, cwd: pathlib.Path = ROOT) -> str:
    try:
        p = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           text=True, timeout=120)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def default_remote_head() -> str:
    for ref in ("origin/main", "origin/master"):
        if git("rev-parse", "--verify", "--quiet", ref):
            return ref
    return ""


def remote_branches() -> set[str]:
    out = git("ls-remote", "--heads", "origin")
    return {ln.split("refs/heads/", 1)[1] for ln in out.splitlines()
            if "refs/heads/" in ln}


def rescued() -> set[str]:
    """Commits already preserved by a rescue tag — reachable, so gc-safe."""
    out = git("for-each-ref", "--format=%(objectname)", f"refs/tags/{RESCUE_PREFIX}*")
    return set(out.split())


def find_unpushed(base: str, remote: set[str]) -> list[dict]:
    findings = []
    for br in git("for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines():
        br = br.strip()
        if not br or br in remote:
            continue
        files = [f for f in git("diff", "--name-only", f"{base}...{br}").splitlines() if f]
        if not files:
            continue                      # merged/empty: untidy, not at risk
        stat = git("diff", "--shortstat", f"{base}...{br}")
        findings.append({"kind": "unpushed-branch", "ref": br,
                         "files": len(files), "stat": stat,
                         "remedy": f"git push origin {br}"})
    return findings


def find_dangling(min_files: int, safe: set[str]) -> list[dict]:
    findings = []
    for line in git("fsck", "--no-reflogs").splitlines():
        if not line.startswith("dangling commit "):
            continue
        sha = line.split()[2]
        if sha in safe:
            continue
        files = [f for f in git("diff", "--name-only", f"{sha}^", sha).splitlines() if f]
        if len(files) <= min_files:
            continue
        subject = git("log", "-1", "--format=%s", sha)[:70]
        date = git("log", "-1", "--format=%ad", "--date=format:%Y%m%d", sha)
        tag = f"{RESCUE_PREFIX}{date}-{sha[:8]}"
        findings.append({"kind": "dangling-commit", "ref": sha[:10],
                         "files": len(files), "stat": subject,
                         "remedy": f"git tag {tag} {sha} && git push origin {tag}"})
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--min-files", type=int, default=3,
                    help="dangling commits touching more than this are reported (default 3)")
    ap.add_argument("--branches-only", action="store_true",
                    help="skip the dangling-object scan (much faster on a large repo)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    base = default_remote_head()
    if not base:
        print("UNKNOWN: no origin/main or origin/master — cannot judge what is unpushed.")
        return 2

    remote = remote_branches()
    if not remote:
        print("UNKNOWN: could not list remote branches (offline?) — "
              "refusing to report everything as unpushed.")
        return 2

    findings = find_unpushed(base, remote)
    if not args.branches_only:
        findings += find_dangling(args.min_files, rescued())

    if args.json:
        print(json.dumps({"base": base, "findings": findings}, indent=1))
    else:
        branches = [f for f in findings if f["kind"] == "unpushed-branch"]
        dangling = [f for f in findings if f["kind"] == "dangling-commit"]
        print(f"unpushed work — base {base}, {len(remote)} remote branch(es)\n")
        if not findings:
            print("OK: every branch with unique content is on origin, and no "
                  "unreachable commit holds real work.")
            return 0
        print(f"FINDINGS ({len(findings)}): "
              f"{len(branches)} unpushed branch(es), {len(dangling)} dangling commit(s)\n")
        for f in findings[:60]:
            print(f"  ✗ [{f['kind']}] {f['ref']}  ({f['files']} files)")
            print(f"      {f['stat']}")
            print(f"      → {f['remedy']}")
        if len(findings) > 60:
            # No silent caps: say what was withheld and how to see it.
            print(f"\n  … {len(findings) - 60} more not shown — rerun with --json for the full set.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
