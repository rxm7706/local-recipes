#!/usr/bin/env python3
"""Detector: an intent-gap halt left no preserve artifact (Story 20.5 / CAP-3).

PLACEMENT (Story 20.5 — closes parent SPEC open question)
---------------------------------------------------------
Lives as ``scripts/missing_preserve_check.py``, invoked via the
``missing-preserve-check`` pixi task — same shape as ``loop-stall-check`` and
``baseline-drift-check``. Rationale: it observes host loop-home feeds
(``~/.bmad-loops`` marshal journals + bmad-loop ``failed/*/changes.patch``)
and local git ``attempt-preserve/*`` refs — **scope=runtime**, already
self-registered via ``DETECTOR`` + ``*_check.py`` discovery. It does **not**
belong in ``pyforge.doctor.sources`` (``story-status-check``'s home): that
surface is for tracked-repo / ledger gathers under the doctor dispatcher.
Keep it here; do not re-home later stories into doctor for this signal.

THE BLIND SPOT
--------------
Story 20.4's supervisor parks ``attempt-preserve/{run}-{head8}`` (commits)
or ``failed/<story>/changes.patch`` (dirty-only) before an intent-gap halt
reverts the worktree. If that seam is bypassed, or upstream behavior
shifts so the park never lands, the halt still looks "correct" (clean
tree at baseline) while the attempt is gone — recoverable only via
transcript archaeology. This detector makes that residual gap loud.

HOW IT DECIDES
--------------
For every marshal journal under every ``~/.bmad-loops`` loop home
(``_bmad-output/projects/<slug>/implementation-artifacts/runs/*/journal.jsonl``):

* ``kind == "intent-gap-preserve-failed"`` → finding (park attempted, failed).
* ``kind == "escalation-detected"`` whose ``reason`` matches the Story 20.4
  intent-gap markers → finding unless a preserve artifact is present:
  - ``payload.preserve_ref`` naming an existing ``attempt-preserve/*`` branch
    or an existing ``changes.patch`` file, or
  - a ``failed/<story>/changes.patch`` under that home's
    ``.bmad-loop/runs/*/`` tree.

Never imports ``bmad_loop``. ``LOOP_ROOT`` and ``REPO`` are module-level so
tests can monkeypatch them (loop-stall / baseline-drift precedent).

EXIT
    0  no missing-preserve findings (at least one run observed)
    1  at least one intent-gap halt without a present preserve artifact
    2  could-not-observe — neither loop-home nor dispatch-runs had any run
       to examine (never exit 0 on an empty observation plane)

``--json``: stdout is a bare JSON list of finding objects.
"""
from __future__ import annotations

# Registry declaration -- see scripts/detectors.py. `runtime`: reads host
# state (gitignored Tier-3 journals, ~/.bmad-loops, local git refs), so CI
# cannot run it (excluded from detectors-ci like loop-stall-check).
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

# Closed vocabulary — byte-identical to supervisor/intent_gap_preserve.py
# Story 20.4 markers. Duplicated so this script never imports marshal or
# bmad_loop (detector isolation; baseline-drift precedent).
_INTENT_GAP_MARKERS = (
    "intent gap",
    "intent_gap",
    "intent-gap",
)

_ESCALATION_KIND = "escalation-detected"
_PRESERVE_FAILED_KIND = "intent-gap-preserve-failed"
_ATTEMPT_PRESERVE_PREFIX = "attempt-preserve/"
_DISPATCH_RUNS_DIRNAME = "dispatch-runs"
_COULD_NOT_OBSERVE = "could-not-observe"


@dataclass(frozen=True)
class ObservationState:
    loop_runs: int = 0
    dispatch_runs: int = 0

    @property
    def any_runs(self) -> bool:
        return self.loop_runs > 0 or self.dispatch_runs > 0


def _safe_story_segment(story_key: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", story_key).strip("-")
    return cleaned or "story"


def looks_like_intent_gap(reason: str | None) -> bool:
    if not reason:
        return False
    folded = reason.casefold()
    return any(marker in folded for marker in _INTENT_GAP_MARKERS)


def _iter_marshal_journals(loop_root: Path):
    """Yield (home, slug, run_id, journal_path) for every marshal journal."""
    if not loop_root.is_dir():
        return
    for home in sorted(p for p in loop_root.iterdir() if p.is_dir()):
        projects = home / "_bmad-output" / "projects"
        if not projects.is_dir():
            continue
        for proj in sorted(projects.iterdir()):
            if not proj.is_dir():
                continue
            runs = proj / "implementation-artifacts" / "runs"
            if not runs.is_dir():
                continue
            for run in sorted(runs.iterdir()):
                if not run.is_dir():
                    continue
                journal = run / "journal.jsonl"
                if journal.is_file():
                    yield home, proj.name, run.name, journal


def _parse_journal(path: Path) -> list[dict]:
    out: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            out.append(entry)
    return out


def _branch_exists(repo: Path, ref: str) -> bool:
    if not ref or not repo.is_dir():
        return False
    candidates = [ref]
    if not ref.startswith("refs/"):
        candidates.append("refs/heads/" + ref)
    for cand in candidates:
        r = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", cand],
            cwd=repo,
            capture_output=True,
            timeout=30,
        )
        if r.returncode == 0:
            return True
    return False


def _patch_exists(
    ref: str,
    home: Path,
    story_key: str,
    *,
    run_dir: Path | None = None,
) -> bool:
    """True when ``ref`` is an existing patch path, or the S-20.4 failed/ path exists."""
    if ref:
        p = Path(ref)
        if p.is_file():
            return True
        if run_dir is not None:
            candidate = run_dir / ref
            if candidate.is_file():
                return True
        alt = home / ref
        if alt.is_file():
            return True
    if not story_key:
        return False
    if run_dir is not None:
        patch = run_dir / "failed" / _safe_story_segment(story_key) / "changes.patch"
        if patch.is_file() and patch.stat().st_size > 0:
            return True
    runs = home / ".bmad-loop" / "runs"
    if not runs.is_dir():
        return False
    for run in runs.iterdir():
        patch = run / "failed" / story_key / "changes.patch"
        if patch.is_file() and patch.stat().st_size > 0:
            return True
    return False


def artifact_present(
    *,
    repo: Path,
    home: Path,
    story_key: str,
    preserve_ref: str | None,
    run_dir: Path | None = None,
) -> bool:
    """Whether a Story 20.4 preserve artifact exists for this halt."""
    ref = (preserve_ref or "").strip()
    if ref:
        if ref.startswith(_ATTEMPT_PRESERVE_PREFIX) or ref.startswith(
            "refs/heads/" + _ATTEMPT_PRESERVE_PREFIX
        ):
            if _branch_exists(repo, ref):
                return True
        if ref.endswith("changes.patch") or "/failed/" in ref:
            if _patch_exists(ref, home, story_key, run_dir=run_dir):
                return True
        if _branch_exists(repo, ref) or _patch_exists(
            ref, home, story_key, run_dir=run_dir
        ):
            return True
    if _patch_exists("", home, story_key, run_dir=run_dir):
        return True
    return False


def _iter_dispatch_journals(repo: Path):
    """Yield ``(repo, slug, run_id, journal, run_dir)`` for dispatch-runs."""
    projects = repo / "_bmad-output" / "projects"
    if not projects.is_dir():
        return
    for proj in sorted(projects.iterdir()):
        if not proj.is_dir():
            continue
        slug = proj.name
        runs = proj / "implementation-artifacts" / _DISPATCH_RUNS_DIRNAME
        if not runs.is_dir():
            continue
        for run in sorted(runs.iterdir()):
            if not run.is_dir() or run.name == "waves":
                continue
            journal = run / "journal.jsonl"
            if journal.is_file():
                yield repo, slug.replace("pyforge-", ""), run.name, journal, run


def _count_loop_journal_runs(loop_root: Path) -> int:
    return sum(1 for _ in _iter_marshal_journals(loop_root))


def _count_dispatch_journal_runs(repo: Path) -> int:
    return sum(1 for _ in _iter_dispatch_journals(repo))


def observe_planes(
    *,
    loop_root: Path | None = None,
    repo: Path | None = None,
) -> ObservationState:
    loop_root = LOOP_ROOT if loop_root is None else loop_root
    repo = REPO if repo is None else repo
    return ObservationState(
        loop_runs=_count_loop_journal_runs(loop_root),
        dispatch_runs=_count_dispatch_journal_runs(repo),
    )


def _scan_journal_for_findings(
    *,
    repo: Path,
    home: Path,
    slug: str,
    run_id: str,
    journal: Path,
    findings: list[dict],
    run_dir: Path | None = None,
    plane: str = "loop-home",
) -> None:
    for entry in _parse_journal(journal):
        kind = entry.get("kind")
        payload = (
            entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
        )
        story = str(payload.get("story_key") or entry.get("story") or "")
        reason = payload.get("reason")
        reason_s = reason if isinstance(reason, str) else ""

        if kind == _PRESERVE_FAILED_KIND:
            findings.append(
                {
                    "slug": slug,
                    "run": run_id,
                    "story": story,
                    "kind": kind,
                    "reason": reason_s or "intent-gap preserve park failed",
                    "preserve_ref": payload.get("preserve_ref"),
                    "home": str(home),
                    "plane": plane,
                }
            )
            continue

        if kind != _ESCALATION_KIND:
            continue
        if not looks_like_intent_gap(reason_s):
            continue

        pref = payload.get("preserve_ref")
        pref_s = pref.strip() if isinstance(pref, str) else None
        if artifact_present(
            repo=repo,
            home=home,
            story_key=story,
            preserve_ref=pref_s,
            run_dir=run_dir,
        ):
            continue

        findings.append(
            {
                "slug": slug,
                "run": run_id,
                "story": story,
                "kind": kind,
                "reason": reason_s,
                "preserve_ref": pref_s,
                "home": str(home),
                "plane": plane,
            }
        )


def collect_findings(
    *,
    loop_root: Path | None = None,
    repo: Path | None = None,
) -> tuple[list[dict], ObservationState]:
    """Intent-gap halts whose preserve artifact is missing."""
    loop_root = LOOP_ROOT if loop_root is None else loop_root
    repo = REPO if repo is None else repo
    findings: list[dict] = []

    for home, slug, run_id, journal in _iter_marshal_journals(loop_root):
        _scan_journal_for_findings(
            repo=repo,
            home=home,
            slug=slug,
            run_id=run_id,
            journal=journal,
            findings=findings,
            plane="loop-home",
        )

    for home, slug, run_id, journal, run_dir in _iter_dispatch_journals(repo):
        _scan_journal_for_findings(
            repo=repo,
            home=home,
            slug=slug,
            run_id=run_id,
            journal=journal,
            findings=findings,
            run_dir=run_dir,
            plane="dispatch-runs",
        )

    return findings, observe_planes(loop_root=loop_root, repo=repo)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0] if __doc__ else "missing-preserve-check"
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="print findings as a JSON list (machine-readable)",
    )
    args = ap.parse_args([] if argv is None else argv)

    findings, obs = collect_findings()

    if not obs.any_runs:
        msg = (
            f"{_COULD_NOT_OBSERVE}: no loop-home marshal journals under "
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

    print(
        f"missing-preserve-check -- {len(findings)} finding(s) "
        f"(loop-home runs={obs.loop_runs}, dispatch-runs={obs.dispatch_runs})\n"
    )
    if findings:
        for f in findings:
            plane = f.get("plane", "loop-home")
            print(
                f"  ✗ [missing-preserve/{plane}] {f['slug']}/{f['story']} "
                f"(run {f['run']}): intent-gap halt without preserve artifact"
            )
            print(f"      reason: {f['reason']!r}")
            if f.get("preserve_ref"):
                print(
                    f"      preserve_ref named {f['preserve_ref']!r} "
                    f"but artifact is absent"
                )
            else:
                print(
                    "      no preserve_ref and no attempt-preserve/* branch "
                    "or failed/<story>/changes.patch"
                )
        print(
            f"\n{len(findings)} finding(s). Recover via transcript archaeology "
            f"or re-drive after fixing the 20.4 preserve seam; see "
            f"spec-bmad-loop-intent-gap-work-preservation CAP-3."
        )
        return 1

    print("OK: every intent-gap halt has a present preserve artifact.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
