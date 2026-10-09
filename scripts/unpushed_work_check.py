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
                    and not already preserved under a rescue/preserve/archive tag.
                    `git gc` may collect these at any time, without warning.
  unpushed-ref      a local tag or custom ref (not under refs/heads/) whose commit
                    is on no `origin` ref — see `commit_on_origin`.

Remedy is report-only: never print a command that would mint or push a ref.
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
SYNTHETIC_SUBJECT_SUFFIX = "(not a real commit)"
REPORT_REMEDY = (
    "report; do not tag — operator review required"
    " (after Story 87.3: `marshal preserve tag`)"
)


class ObservationFailed(Exception):
    """Git could not be observed — fail closed (exit 2)."""

    def __init__(self, cmd: tuple[str, ...]) -> None:
        self.cmd = cmd
        super().__init__(" ".join(cmd))


def _run_git(*args: str, cwd: pathlib.Path = ROOT) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def git(*args: str, cwd: pathlib.Path = ROOT) -> str:
    proc = _run_git(*args, cwd=cwd)
    if proc is None or proc.returncode != 0:
        raise ObservationFailed(("git", *args))
    return proc.stdout.strip()


def git_stdout_even_on_failure(*args: str, cwd: pathlib.Path = ROOT) -> str:
    """Return stdout when present; fsck exits non-zero when it lists problems."""
    proc = _run_git(*args, cwd=cwd)
    if proc is None:
        raise ObservationFailed(("git", *args))
    out = proc.stdout.strip()
    if out:
        return out
    if proc.returncode != 0:
        raise ObservationFailed(("git", *args))
    return ""


def git_optional(*args: str, cwd: pathlib.Path = ROOT) -> str:
    """Stdout regardless of exit code — missing refs/objects are not observation loss."""
    proc = _run_git(*args, cwd=cwd)
    if proc is None:
        raise ObservationFailed(("git", *args))
    return proc.stdout.strip()


def default_remote_head() -> str:
    # Full refnames (marshal Story 60.1, CAP-270): a local branch or tag named `origin/main` would
    # shadow the short name and make unpushed work read as already on the remote.
    for ref in ("refs/remotes/origin/main", "refs/remotes/origin/master"):
        try:
            git("rev-parse", "--verify", "--quiet", ref)
            return ref
        except ObservationFailed:
            continue
    return ""


def remote_branches() -> dict[str, str]:
    """branch name -> remote tip sha (S-3.10, FR-171)."""
    out = git("ls-remote", "--heads", "origin")
    tips: dict[str, str] = {}
    for ln in out.splitlines():
        if "refs/heads/" not in ln:
            continue
        sha, _, ref = ln.partition("\t")
        tips[ref.split("refs/heads/", 1)[1]] = sha.strip()
    return tips


def origin_tip_shas() -> set[str]:
    """Tips of refs/remotes/origin/* plus tags listed on origin (CAP-287 / Story 87.2)."""
    tips: set[str] = set()
    for sha in git("for-each-ref", "--format=%(objectname)", "refs/remotes/origin/").splitlines():
        sha = sha.strip()
        if sha:
            tips.add(sha)
    for ln in git("ls-remote", "--tags", "origin").splitlines():
        if not ln.strip() or "\t" not in ln:
            continue
        sha, _, _ref = ln.partition("\t")
        tips.add(sha.strip())
    return tips


def commit_on_origin(sha: str, origin_tips: set[str]) -> bool:
    if not sha:
        return False
    if sha in origin_tips:
        return True
    for tip in origin_tips:
        proc = _run_git("merge-base", "--is-ancestor", sha, tip)
        if proc is not None and proc.returncode == 0:
            return True
    return False


def ref_peeled_commit(ref: str) -> str:
    peeled = git_optional("rev-parse", "-q", f"{ref}^{{commit}}")
    if peeled:
        return peeled
    return git_optional("rev-parse", "-q", ref)


def rescued() -> set[str]:
    """Commits already preserved — reachable from legacy rescue or preserve/archive tags."""
    commits: set[str] = set()
    for prefix in (RESCUE_PREFIX, "preserve/", "archive/"):
        out = git_optional(
            "for-each-ref",
            "--format=%(refname)",
            f"refs/tags/{prefix}*",
        )
        for ref in out.splitlines():
            ref = ref.strip()
            if not ref:
                continue
            commits.add(ref_peeled_commit(ref))
    return {c for c in commits if c}


def find_unpushed(base: str, remote: dict[str, str]) -> list[dict]:
    findings = []
    # Marshal Story 61.1: `lstrip=2`, not `short` -- `short` prints `heads/<br>`
    # when a tag shares the name, which then matches no remote branch; and every
    # read below names `refs/heads/<br>`, never the bare name a tag stands in for.
    for br in git("for-each-ref", "--format=%(refname:lstrip=2)", "refs/heads/").splitlines():
        br = br.strip()
        if not br:
            continue
        head = f"refs/heads/{br}"
        remote_sha = remote.get(br)
        ahead = 0
        if remote_sha:
            ahead_out = git_optional("rev-list", "--count", f"{remote_sha}..{head}")
            if ahead_out.isdigit():
                ahead = int(ahead_out)
            elif not git_optional("cat-file", "-e", f"{remote_sha}^{{commit}}"):
                ahead = -1
            if ahead == 0:
                continue
        files = [f for f in git("diff", "--name-only", f"{base}...{head}").splitlines() if f]
        if not files:
            continue
        stat = git("diff", "--shortstat", f"{base}...{head}")
        if remote_sha:
            behind = f"{ahead} commit(s)" if ahead > 0 else "an unfetched tip"
            note = (
                f"origin has this branch at {remote_sha[:10]} but is behind by "
                f"{behind} — a remote copy existing is not the work being safe"
            )
        else:
            note = "no branch of this name on origin at all"
        findings.append(
            {
                "kind": "unpushed-branch",
                "ref": br,
                "files": len(files),
                "stat": stat,
                "detail": note,
                "remedy": REPORT_REMEDY,
            }
        )
    return findings


def find_unpushed_refs(origin_tips: set[str]) -> list[dict]:
    """Local tags and non-head refs whose commits are not on origin."""
    findings: list[dict] = []
    for ref in git("for-each-ref", "--format=%(refname)", "refs/").splitlines():
        ref = ref.strip()
        if not ref or ref.startswith("refs/heads/") or ref.startswith("refs/remotes/"):
            continue
        commit = ref_peeled_commit(ref)
        if commit_on_origin(commit, origin_tips):
            continue
        stat = git_optional("log", "-1", "--format=%s", commit)[:70]
        findings.append(
            {
                "kind": "unpushed-ref",
                "ref": ref,
                "files": 0,
                "stat": stat or commit[:10],
                "remedy": REPORT_REMEDY,
            }
        )
    return findings


def find_dangling(min_files: int, safe: set[str]) -> list[dict]:
    findings = []
    for line in git_stdout_even_on_failure("fsck", "--no-reflogs").splitlines():
        if not line.startswith("dangling commit "):
            continue
        sha = line.split()[2]
        if sha in safe:
            continue
        subject = git_optional("log", "-1", "--format=%s", sha)
        if SYNTHETIC_SUBJECT_SUFFIX and subject.endswith(SYNTHETIC_SUBJECT_SUFFIX):
            continue
        files = [f for f in git_optional("diff", "--name-only", f"{sha}^", sha).splitlines() if f]
        if len(files) <= min_files:
            continue
        findings.append(
            {
                "kind": "dangling-commit",
                "ref": sha[:10],
                "files": len(files),
                "stat": subject[:70],
                "remedy": REPORT_REMEDY,
            }
        )
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--min-files",
        type=int,
        default=3,
        help="dangling commits touching more than this are reported (default 3)",
    )
    ap.add_argument(
        "--branches-only",
        action="store_true",
        help="skip the dangling-object scan (much faster on a large repo)",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        base = default_remote_head()
        if not base:
            print("UNKNOWN: no origin/main or origin/master — cannot judge what is unpushed.")
            return 2

        remote = remote_branches()
        if not remote:
            print(
                "UNKNOWN: could not list remote branches (offline?) — "
                "refusing to report everything as unpushed."
            )
            return 2

        findings = find_unpushed(base, remote)
        if not args.branches_only:
            origin_tips = origin_tip_shas()
            findings += find_unpushed_refs(origin_tips)
            findings += find_dangling(args.min_files, rescued())
    except ObservationFailed as exc:
        cmd = " ".join(exc.cmd)
        print(f"UNKNOWN: could not observe repository ({cmd}).")
        return 2

    if args.json:
        print(json.dumps({"base": base, "findings": findings}, indent=1))
    else:
        branches = [f for f in findings if f["kind"] == "unpushed-branch"]
        dangling = [f for f in findings if f["kind"] == "dangling-commit"]
        refs = [f for f in findings if f["kind"] == "unpushed-ref"]
        print(f"unpushed work — base {base}, {len(remote)} remote branch(es)\n")
        if not findings:
            print(
                "OK: every branch with unique content is on origin, and no "
                "unreachable commit holds real work."
            )
            return 0
        print(
            f"FINDINGS ({len(findings)}): "
            f"{len(branches)} unpushed branch(es), {len(dangling)} dangling commit(s), "
            f"{len(refs)} unpushed ref(s)\n"
        )
        for f in findings[:60]:
            print(f"  ✗ [{f['kind']}] {f['ref']}  ({f['files']} files)")
            print(f"      {f['stat']}")
            if f.get("detail"):
                print(f"      {f['detail']}")
            print(f"      → {f['remedy']}")
        if len(findings) > 60:
            print(f"\n  … {len(findings) - 60} more not shown — rerun with --json for the full set.")
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
