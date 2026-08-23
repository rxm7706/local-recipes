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
    0  no missing-preserve findings
    1  at least one intent-gap halt without a present preserve artifact

``--json``: stdout is a bare JSON list of finding objects.
"""
from __future__ import annotations

# Registry declaration -- see scripts/detectors.py. `runtime`: reads host
# state (gitignored Tier-3 journals, ~/.bmad-loops, local git refs), so CI
# cannot run it (excluded from detectors-ci like loop-stall-check).
DETECTOR = {"scope": "runtime"}

import argparse
import json
import subprocess
import sys
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


def _patch_exists(ref: str, home: Path, story_key: str) -> bool:
    """True when ``ref`` is an existing patch path, or the S-20.4 failed/ path exists."""
    if ref:
        p = Path(ref)
        if p.is_file():
            return True
        alt = home / ref
        if alt.is_file():
            return True
    if not story_key:
        return False
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
            if _patch_exists(ref, home, story_key):
                return True
        if _branch_exists(repo, ref) or _patch_exists(ref, home, story_key):
            return True
    if _patch_exists("", home, story_key):
        return True
    return False


def collect_findings(
    *,
    loop_root: Path | None = None,
    repo: Path | None = None,
) -> list[dict]:
    """Intent-gap halts whose preserve artifact is missing."""
    loop_root = LOOP_ROOT if loop_root is None else loop_root
    repo = REPO if repo is None else repo
    findings: list[dict] = []

    for home, slug, run_id, journal in _iter_marshal_journals(loop_root):
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
                repo=repo, home=home, story_key=story, preserve_ref=pref_s
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
                }
            )
    return findings


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

    findings = collect_findings()

    if args.json:
        print(json.dumps(findings))
        return 1 if findings else 0

    if not LOOP_ROOT.is_dir():
        print(f"no loop homes at {LOOP_ROOT} -- nothing to check")
        return 0

    print(f"missing-preserve-check -- {len(findings)} finding(s)\n")
    if findings:
        for f in findings:
            print(
                f"  ✗ [missing-preserve] {f['slug']}/{f['story']} "
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
