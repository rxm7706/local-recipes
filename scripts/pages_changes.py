#!/usr/bin/env python3
"""Write the changes page's build input for the Pages workflow (steward Story 130.1, CAP-168).

Reads ``git log --first-parent`` on the built commit and writes ``docs-site/src/content/changes.json`` in the
shape herald's ``parseChanges`` reads (herald Story 43.6; ``docs-site/src/lib/agent-surface.ts``):
``{"generated_at", "window_days", "merges": [{"date", "station", "subject", "sha"}]}``, newest first. A merge is
listed when it sits on the first-parent line and its committer time is within ``--window-days`` before the built
commit's committer time. ``generated_at`` is that commit's committer time and the window is anchored on it, never
on the wall clock, so a second run on the same commit writes the same bytes and a scheduled build of an unmoved
tree still skips its deploy. The station is read from ``Merge <station>/<E-S> into main``; any other merge is
``other``. No network and no ``gh``.

Exit 0 wrote the file; 1 git could not read the ref (named on stderr); 3 the checkout's history is too shallow
for the window (the first-parent line stops on a shallow commit inside it, whose parents git cannot see, so it
cannot be told from a merge): ``pages.yml`` fetches the commits before it runs this. Nothing is written on 1 or 3.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGES_REL = "docs-site/src/content/changes.json"
WINDOW_DAYS = 30
#: The exit code for a history too shallow for the window.
EXIT_SHALLOW = 3
#: The subject marshal's landing writes: ``Merge <station>/<E-S> into main``.
_STORY_MERGE = re.compile(r"^Merge ([a-z0-9][a-z0-9-]*)/\d+-\d+ into main$")
#: GitHub's synthetic merge commit of a pull request (``refs/pull/N/merge``).
_SYNTHETIC_MERGE = re.compile(r"^Merge [0-9a-f]{40} into [0-9a-f]{40}$")
OTHER_STATION = "other"
#: Characters XML 1.0 forbids (``XML_ILLEGAL`` in agent-surface.ts); the build refuses a subject that holds one.
_XML_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
_SHA = re.compile(r"^[0-9a-f]{7,40}$")


class ChangesError(Exception):
    """The changes input could not be written; ``code`` is the exit code."""

    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def _git(repo: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise ChangesError(f"git could not run ({exc})") from exc
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()
        raise ChangesError(f"git {' '.join(args[:2])} failed in {repo}: {detail}")
    return proc.stdout.decode("utf-8", errors="replace")


def _shallow_commits(repo: Path) -> frozenset[str]:
    """The commits whose parents this checkout does not hold (``.git/shallow``); empty in a full clone."""
    path = Path(_git(repo, "rev-parse", "--git-path", "shallow").strip())
    if not path.is_absolute():
        path = repo / path
    try:
        return frozenset(
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    except OSError:
        return frozenset()


def station_of(subject: str) -> str:
    """``pyforge-steward`` for ``Merge pyforge-steward/129-1 into main``; ``other`` for any other subject."""
    match = _STORY_MERGE.match(subject)
    return match.group(1) if match else OTHER_STATION


def changes_document(
    repo: Path, ref: str = "HEAD", window_days: int = WINDOW_DAYS
) -> dict[str, Any]:
    """The ``changes.json`` document for ``ref``: every value comes from the commits, none from the clock."""
    if window_days < 1:
        raise ChangesError(
            f"--window-days {window_days}: the window is at least one day"
        )
    generated_at = _git(repo, "log", "-1", "--format=%cI", ref, "--").strip()
    if not generated_at:
        raise ChangesError(f"{ref}: no commit time read from git")
    cutoff = datetime.fromisoformat(generated_at) - timedelta(days=window_days)
    # NUL between fields and (-z) between commits: a commit message cannot hold one, so no subject splits a record
    fields = _git(
        repo, "log", "-z", "--first-parent", "--format=%H%x00%P%x00%cI%x00%s", ref, "--"
    ).split("\x00")
    shallow = _shallow_commits(repo)
    merges: list[tuple[datetime, dict[str, str]]] = []
    seen: set[str] = set()
    for index in range(0, len(fields) - 3, 4):
        sha, parents, committed, subject = fields[index : index + 4]
        at = datetime.fromisoformat(committed)
        if at < cutoff:
            continue
        if sha in shallow:
            raise ChangesError(
                f"the history is too shallow for the {window_days}-day window: {sha[:12]} ({committed}) is inside "
                "it and its parents are not fetched",
                EXIT_SHALLOW,
            )
        subject = _XML_ILLEGAL.sub("", subject).strip()
        # A pull-request build checks out GitHub's own merge of the PR head into its base ("Merge <sha> into <sha>"):
        # no merge to main, and a new commit on every run, so it is never listed.
        if _SYNTHETIC_MERGE.match(subject):
            continue
        # parseChanges refuses an empty subject and a repeated or non-hex sha; a merge it would refuse is not listed
        if (
            len(parents.split()) < 2
            or not subject
            or not _SHA.match(sha)
            or sha in seen
        ):
            continue
        seen.add(sha)
        merges.append(
            (
                at,
                {
                    "date": at.astimezone(UTC).strftime("%Y-%m-%d"),
                    "station": station_of(subject),
                    "subject": subject,
                    "sha": sha,
                },
            )
        )
    merges.sort(
        key=lambda item: item[0], reverse=True
    )  # stable: equal times keep git's order
    return {
        "generated_at": generated_at,
        "window_days": window_days,
        "merges": [merge for _, merge in merges],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write the changes page's input from the first-parent merges before a commit."
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help=f"the Pages workflow passes {CHANGES_REL}",
    )
    parser.add_argument(
        "--ref", default="HEAD", help="the built commit (default: HEAD)"
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=WINDOW_DAYS,
        help=f"days before the built commit's committer time (default: {WINDOW_DAYS})",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=REPO_ROOT,
        help="the git checkout (default: this repository)",
    )
    args = parser.parse_args(argv)
    if not args.ref.strip() or args.ref.startswith("-"):
        print(f"pages_changes: --ref {args.ref!r} is not a revision", file=sys.stderr)
        return 1

    try:
        document = changes_document(args.repo, args.ref, args.window_days)
    except ChangesError as exc:
        print(f"pages_changes: {exc}", file=sys.stderr)
        return exc.code
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    count = len(document["merges"])
    print(
        f"pages_changes: wrote {args.out} ({count} merges in {args.window_days} days before {args.ref})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
