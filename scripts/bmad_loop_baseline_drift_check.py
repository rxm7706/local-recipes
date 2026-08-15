#!/usr/bin/env python3
"""Detector: a story permanently deferred by bmad-loop's stuck-orchestrator
baseline-drift bug (docs/dreams/bmad-loop-baseline-drift.md,
spec-bmad-loop-baseline-drift, CAP-1/CAP-2) and not yet recovered.

THE BUG (not ours to fix -- bmad_loop ships git-pinned via pixi, editing
site-packages is wiped on the next `pixi install` and would be a live edit
under a run importing it mid-flight). `task.baseline_commit`, stamped once
when a story's isolated worktree opens, can drift to the shared
`loop/<slug>` branch's later tip while a dev session is still running.
`_verify_shared_gates` then compares the session's own correct
`baseline_revision` against the drifted value, mismatches, and permanently
defers real, reviewed work -- while the dispatcher silently opens the next
story's worktree. Hit five times in one session on 2026-08-14 (marshal
8.1-9.5, 9.6; mason 3.6-3.9) before this containment existed; three more
same-day (atlas 14-2, herald 14-2/14-3) confirmed the recurrence was not a
one-off. Every occurrence's real, reviewed commits survive as an
`attempt-preserve/<run>-<hash>` branch -- recoverable by hand (create
`land/<slug>-<story>` off `origin/loop/<slug>`, merge the preserve branch's
commits in, land as a normal PR), but invisible until an operator notices,
which is exactly what this containment (CAP-1/CAP-2) ends.

HOW IT DECIDES
--------------
For every run directory under every `~/.bmad-loops/<slug>/.bmad-loop/runs/`,
scan `journal.jsonl` for a `story-deferred` entry whose `reason` matches the
baseline-drift signature. A match is UNRECOVERED unless the story already
reads `done` in that station's TRACKED `sprint-status-ledger.yaml` -- the
same source of truth `fleet-picture` itself reads, so a hand-landed recovery
(a `land/<slug>-<story>` PR, same shape as PRs #482-484/#510) silences the
finding the moment `sprint-ledger-sync` picks it up, without this detector
having to understand recovery-PR shape or commit-message conventions.

EXIT
    0  no unrecovered baseline-drift defer found
    1  at least one unrecovered baseline-drift defer found
"""
from __future__ import annotations

# Registry declaration -- see scripts/detectors.py. `runtime`: reads host
# state (gitignored Tier-3 sprint feeds, ~/.bmad-loops), so CI cannot run it.
DETECTOR = {"scope": "runtime"}

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOOP_ROOT = Path.home() / ".bmad-loops"

DRIFT_RE = re.compile(
    r"spec baseline (\S+) does not match orchestrator-recorded baseline (\S+)"
)


def tracked_status(slug: str) -> dict[str, str]:
    path = (
        REPO
        / f"_bmad-output/projects/pyforge-{slug}/planning-artifacts"
        / "sprint-status-ledger.yaml"
    )
    if not path.is_file():
        return {}
    import yaml

    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return doc.get("development_status", {})


def preserve_refs(run_id: str) -> list[str]:
    """attempt-preserve/<run_id>-* branches, visible from any worktree sharing
    this repo's object database (confirmed empirically -- they need no fetch)."""
    r = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)",
         f"refs/heads/attempt-preserve/{run_id}-*"],
        cwd=REPO, capture_output=True, text=True, timeout=30,
    )
    return [line for line in r.stdout.splitlines() if line.strip()]


def find_defers(journal: Path) -> list[dict]:
    out = []
    try:
        lines = journal.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("kind") != "story-deferred":
            continue
        reason = d.get("reason") or ""
        m = DRIFT_RE.search(reason)
        if m:
            out.append({
                "story_key": d.get("story_key") or "",
                "drifted": m.group(2),
                "real": m.group(1),
            })
    return out


def main() -> int:
    if not LOOP_ROOT.is_dir():
        print(f"no loop homes at {LOOP_ROOT} -- nothing to check")
        return 0

    findings = []
    for home in sorted(p for p in LOOP_ROOT.iterdir() if (p / ".git").exists()):
        slug = home.name.replace("pyforge-", "")
        status = tracked_status(slug)
        runs_dir = home / ".bmad-loop" / "runs"
        if not runs_dir.is_dir():
            continue
        for run in sorted(runs_dir.glob("*/")):
            for defer in find_defers(run / "journal.jsonl"):
                story = defer["story_key"]
                if status.get(story) == "done":
                    continue  # recovered -- the tracked ledger already says so
                refs = preserve_refs(run.name)
                findings.append({
                    "slug": slug, "run": run.name, "story": story,
                    "real": defer["real"], "drifted": defer["drifted"],
                    "refs": refs,
                })

    print(f"baseline-drift-check -- {len(findings)} unrecovered defer(s)\n")
    if findings:
        for f in findings:
            print(f"  ✗ [unrecovered] {f['slug']}/{f['story']} (run {f['run']}): "
                  f"real basis {f['real']} != orchestrator-recorded {f['drifted']}")
            if f["refs"]:
                print(f"      recover from: {', '.join(f['refs'])}")
            else:
                print(f"      no attempt-preserve/{f['run']}-* branch found -- "
                      f"check failed/{f['story']}/changes.patch in the run dir")
        print(f"\n{len(findings)} finding(s). Recover: create land/<slug>-<story> off "
              f"origin/loop/<slug>, merge the preserve branch's real commits in, land "
              f"as a normal PR (same shape as PRs #482-484, #510).")
        return 1

    print("OK: no unrecovered baseline-drift defer in any loop home.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
