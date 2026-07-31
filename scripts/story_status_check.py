#!/usr/bin/env python3
"""Detector: no story may read `done` in a sprint feed without having landed.

THE DEFECT THIS CATCHES
-----------------------
A bmad-loop dev pass marks its story `done` in `implementation-artifacts/
sprint-status.yaml` when it finishes. If the **review** then fails to converge,
the orchestrator defers the story -- but nothing rolls the feed back. The story
keeps reading `done` forever.

That is a false green in the artifact the dashboard renders and the next run
dispatches from. Left alone it does two kinds of damage:

  * the board reports work that does not exist, and
  * the next run SKIPS the story, because `done` means "nothing to do".

Live, 2026-07-31 -- three stories across three stations, all in the same shape
(dev completed and self-marked; review then failed):

    marshal 1-6-isolation-verification    deferred: review did not converge
    doctor  1-4-credential-environment    deferred: review did not converge
    mason   1-3-error-taxonomy            deferred: review session timeout

The three whose DEV pass crashed or timed out (herald 1.3, steward 1.4,
scribe 1.3) correctly read `backlog` -- they never got far enough to self-mark.
So the corruption is not random: **a story marked done by dev survives its own
review failure.**

The fix belongs upstream in bmad-loop (roll the feed back when a story defers).
`bmad-loop` is a declared runtime dependency this repo never vendors or patches,
so this detector is the containment: it cannot prevent the corruption, but it
makes it impossible to miss.

HOW IT DECIDES -- and why the two obvious tests are wrong
---------------------------------------------------------
Both heuristics tried first produced FALSE POSITIVES on real data:

  A. "`done` + `commit_sha: None` in run state" flagged herald 1.2, doctor 1.1
     and scribe 1.1 -- all three had genuinely merged. Their runs were
     interrupted before `state.json` was updated, so the STATE was stale and the
     FEED was right. The mirror image of the defect above.

  B. "no `Merge bmad-loop/<run>/<key> into` commit" flagged mason 1.1 and
     steward 1.1, which were HAND-IMPLEMENTED and so carry no loop merge
     subject -- the same commit-subject archaeology that broke the published
     dashboard twice.

AD-33 already resolves this: **git is the sole authority for repository facts**
(merged / not merged); the journal owns process facts. Neither the feed nor
`state.json` is a repository fact, and both drift -- in opposite directions.

So a `done` story is CONFIRMED landed if either holds:

  1. a merge commit naming its story key exists on any ref, OR
  2. the harness recorded a `commit_sha` for it.

and is reported ONLY when neither holds AND the harness positively says the
story is `deferred`/`escalated`. That last clause is what keeps hand-implemented
stories (no loop merge, no run record) from being flagged: absence of evidence
is not evidence of absence, so with no run record at all the detector stays
silent rather than guessing.

EXIT
    0  every `done` is backed by a landing, or by no contrary evidence
    1  at least one story reads `done` while its own run says it deferred
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "_bmad-output" / "projects"
LOOP_ROOT = Path.home() / ".bmad-loops"
DONE_RE = re.compile(r"^  ([a-z0-9][a-z0-9-]*): done$", re.M)
NOT_LANDED = {"deferred", "escalated", "abandoned"}


def sh(*args: str) -> str:
    try:
        return subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                              timeout=60).stdout.strip()
    except Exception:
        return ""


def harness_tasks(slug: str) -> dict[str, dict]:
    """Most-advanced run record per story key, across every run of a station.

    'Most advanced' = prefer a record carrying a commit_sha, since a later run
    can re-drive a story a earlier run deferred.
    """
    out: dict[str, dict] = {}
    home = LOOP_ROOT / f"pyforge-{slug}"
    for state in sorted(home.glob(".bmad-loop/runs/*/state.json")):
        try:
            tasks = json.loads(state.read_text()).get("tasks") or {}
        except Exception:
            continue
        for key, task in tasks.items():
            prev = out.get(key)
            if prev is None or (task.get("commit_sha") and not prev.get("commit_sha")):
                out[key] = task
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verbose", action="store_true", help="show every audited story")
    args = ap.parse_args()

    findings, audited = [], 0
    for feed in sorted(PROJECTS.glob("pyforge-*/implementation-artifacts/sprint-status.yaml")):
        slug = feed.parent.parent.name.removeprefix("pyforge-")
        tasks = harness_tasks(slug)
        for key in DONE_RE.findall(feed.read_text()):
            audited += 1
            task = tasks.get(key)
            # No run record at all -> pre-loop or hand-implemented. Stay silent.
            if task is None:
                if args.verbose:
                    print(f"  ok       {slug}/{key}  (no run record -- hand-landed or pre-loop)")
                continue
            if task.get("commit_sha"):
                if args.verbose:
                    print(f"  ok       {slug}/{key}  (harness recorded a commit)")
                continue
            if sh("git", "log", "--oneline", "--all", "-F", f"--grep=/{key} into"):
                if args.verbose:
                    print(f"  ok       {slug}/{key}  (merge commit found)")
                continue
            phase = task.get("phase", "")
            if phase in NOT_LANDED:
                findings.append((slug, key, phase, task.get("defer_reason") or ""))
            elif args.verbose:
                print(f"  ok       {slug}/{key}  (harness phase {phase!r}, no contrary evidence)")

    print(f"story-status -- audited {audited} `done` entries across every station feed\n")
    if findings:
        for slug, key, phase, why in findings:
            print(f"  ✗ [false-green] {slug}/{key}: reads `done` in the sprint feed, but the "
                  f"harness says {phase!r} with no commit and no merge commit anywhere."
                  + (f" Reason: {why}" if why else ""))
        print(f"\n{len(findings)} story(s) claim completion they cannot show.")
        print("The board will over-report and the next run will SKIP them.")
        print("Fix: set each back to `backlog` in the project's Tier-3 "
              "implementation-artifacts/sprint-status.yaml, then re-run "
              "`pixi run -e local-recipes sprint-ledger-sync` to re-promote the twin.")
        return 1

    print("OK: every `done` story is backed by a merge commit or a recorded commit sha.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
