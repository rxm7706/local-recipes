#!/usr/bin/env python3
"""Detector: a story permanently deferred by bmad-loop's stuck-orchestrator
baseline-drift bug (docs/dreams/bmad-loop-baseline-drift.md,
spec-bmad-loop-baseline-drift, CAP-1/CAP-2) and not yet recovered.

PLACEMENT (Story 20.1 — closes parent SPEC open question)
---------------------------------------------------------
Lives as ``scripts/bmad_loop_baseline_drift_check.py``, invoked via the
``baseline-drift-check`` pixi task — same shape as ``loop-stall-check``.
Rationale: it observes ``~/.bmad-loops`` host feeds (runtime scope), is
already self-registered via ``DETECTOR`` + ``*_check.py`` discovery, and
does **not** need the doctor dispatcher / ``pyforge.doctor.sources``
packaging surface (story-status-check's home). Keep it here; do not move
it into ``pyforge.doctor.sources`` — placement is decided; later stories
own loudness/ATTENTION (20.2) and upstream filing (20.3), not re-homing.

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

``LOOP_ROOT`` and ``REPO`` are module-level so tests can monkeypatch them
(loop-stall-check meta-test precedent); the detector never imports
``bmad_loop``.

EXIT
    0  no unrecovered baseline-drift defer found (at least one run observed)
    1  at least one unrecovered baseline-drift defer found
    2  could-not-observe — neither loop-home nor dispatch-runs had any run
       to examine (never exit 0 on an empty observation plane)

``--json`` (Story 20.2 / CAP-2): stdout is a bare JSON list of unrecovered
finding objects (keys: slug, run, story, real, drifted, refs). Exit codes
are unchanged — exit 1 still means findings exist. Human banners are
suppressed in this mode so fleet-picture can parse stdout safely.
"""
from __future__ import annotations

# Registry declaration -- see scripts/detectors.py. `runtime`: reads host
# state (gitignored Tier-3 sprint feeds, ~/.bmad-loops), so CI cannot run it.
DETECTOR = {"scope": "runtime"}

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOOP_ROOT = Path.home() / ".bmad-loops"

DRIFT_RE = re.compile(
    r"spec baseline (\S+) does not match orchestrator-recorded baseline (\S+)"
)

_DISPATCH_RUNS_DIRNAME = "dispatch-runs"
_COULD_NOT_OBSERVE = "could-not-observe"


@dataclass(frozen=True)
class ObservationState:
    """How many run directories were examined on each observation plane."""

    loop_runs: int = 0
    dispatch_runs: int = 0

    @property
    def any_runs(self) -> bool:
        return self.loop_runs > 0 or self.dispatch_runs > 0


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


def _count_loop_runs(loop_root: Path) -> int:
    if not loop_root.is_dir():
        return 0
    count = 0
    for home in sorted(p for p in loop_root.iterdir() if (p / ".git").exists()):
        runs_dir = home / ".bmad-loop" / "runs"
        if not runs_dir.is_dir():
            continue
        for run in sorted(runs_dir.glob("*/")):
            if run.is_dir():
                count += 1
    return count


def _iter_dispatch_run_journals(repo: Path):
    """Yield ``(slug, run_id, journal_path)`` under in-repo dispatch-runs."""
    projects = repo / "_bmad-output" / "projects"
    if not projects.is_dir():
        return
    for proj in sorted(projects.iterdir()):
        if not proj.is_dir():
            continue
        slug = proj.name.replace("pyforge-", "")
        runs = proj / "implementation-artifacts" / _DISPATCH_RUNS_DIRNAME
        if not runs.is_dir():
            continue
        for run in sorted(runs.iterdir()):
            if not run.is_dir() or run.name == "waves":
                continue
            journal = run / "journal.jsonl"
            if journal.is_file():
                yield slug, run.name, journal


def _count_dispatch_runs(repo: Path) -> int:
    return sum(1 for _ in _iter_dispatch_run_journals(repo))


def observe_planes(
    *,
    loop_root: Path | None = None,
    repo: Path | None = None,
) -> ObservationState:
    loop_root = LOOP_ROOT if loop_root is None else loop_root
    repo = REPO if repo is None else repo
    return ObservationState(
        loop_runs=_count_loop_runs(loop_root),
        dispatch_runs=_count_dispatch_runs(repo),
    )


def _collect_from_journal(
    *,
    slug: str,
    run_id: str,
    journal: Path,
    status: dict[str, str],
    findings: list[dict],
) -> None:
    for defer in find_defers(journal):
        story = defer["story_key"]
        if status.get(story) == "done":
            continue
        refs = preserve_refs(run_id)
        findings.append({
            "slug": slug,
            "run": run_id,
            "story": story,
            "real": defer["real"],
            "drifted": defer["drifted"],
            "refs": refs,
            "plane": "loop-home",
        })


def collect_findings() -> tuple[list[dict], ObservationState]:
    """Unrecovered baseline-drift defers across loop-home and dispatch planes.

    Pure collection for human stdout, ``--json``, and fleet-picture ATTENTION
    (Story 20.2). The second return value classifies observability so callers
    can exit 2 when both planes are empty.
    """
    findings: list[dict] = []

    if LOOP_ROOT.is_dir():
        for home in sorted(p for p in LOOP_ROOT.iterdir() if (p / ".git").exists()):
            slug = home.name.replace("pyforge-", "")
            status = tracked_status(slug)
            runs_dir = home / ".bmad-loop" / "runs"
            if not runs_dir.is_dir():
                continue
            for run in sorted(runs_dir.glob("*/")):
                if not run.is_dir():
                    continue
                _collect_from_journal(
                    slug=slug,
                    run_id=run.name,
                    journal=run / "journal.jsonl",
                    status=status,
                    findings=findings,
                )

    for slug, run_id, journal in _iter_dispatch_run_journals(REPO):
        status = tracked_status(slug)
        for defer in find_defers(journal):
            story = defer["story_key"]
            if status.get(story) == "done":
                continue
            refs = preserve_refs(run_id)
            findings.append({
                "slug": slug,
                "run": run_id,
                "story": story,
                "real": defer["real"],
                "drifted": defer["drifted"],
                "refs": refs,
                "plane": "dispatch-runs",
            })

    return findings, observe_planes()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0] if __doc__ else "baseline-drift-check"
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="print unrecovered findings as a JSON list (machine-readable)",
    )
    # Default [] so programmatic callers (tests, importlib) never inherit
    # the parent process's argv (e.g. pytest). CLI passes sys.argv[1:].
    args = ap.parse_args([] if argv is None else argv)

    findings, obs = collect_findings()

    if not obs.any_runs:
        msg = (
            f"{_COULD_NOT_OBSERVE}: no loop-home runs under "
            f"{LOOP_ROOT} and no dispatch-runs journals under "
            f"{REPO / '_bmad-output' / 'projects'}"
        )
        if args.json:
            print(json.dumps({"error": msg, "findings": findings}))
            return 2
        print(msg)
        return 2

    if args.json:
        print(json.dumps(findings))
        return 1 if findings else 0

    print(f"baseline-drift-check -- {len(findings)} unrecovered defer(s) "
          f"(loop-home runs={obs.loop_runs}, dispatch-runs={obs.dispatch_runs})\n")
    if findings:
        for f in findings:
            plane = f.get("plane", "loop-home")
            print(f"  ✗ [unrecovered/{plane}] {f['slug']}/{f['story']} (run {f['run']}): "
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

    print("OK: no unrecovered baseline-drift defer on either observation plane.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
