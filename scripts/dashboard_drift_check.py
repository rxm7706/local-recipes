#!/usr/bin/env python3
"""Detector: the committed `docs/dashboard/data.js` still tells the truth.

Two ways the board goes quietly wrong, both observed live on 2026-07-29/30, both
invisible to every existing detector (`dashboard-check` proves the board's
JavaScript *runs*, not that its contents are current).

**1. A stale committed baseline (`stale-done`).**
`generate.py --source git` is what the Pages workflow runs, and it only ever
UPGRADES a story to done — state it cannot derive from history "stays at the
committed baseline", i.e. at whatever `data.js` already says. That is the
mechanism that lets a hand-curated in-flight state survive a deploy, and it is
also the mechanism by which a *wrong* state survives forever.

It bit atlas: Epic 10's completions exist only as `Merge bmad-loop/<run>/10-N-…`
subjects on `loop/pyforge-atlas`, and squash-merging PR #132 made those commits
non-ancestors of `main`, while #132's own squash subject matched none of the four
conventions `done_ids_from_git` recognises. The published board sat at 36/38 with
`lineState: in flight@10.5` — a ticking wall clock on a finished story — for a day,
and nothing complained. The next squash-merged epic would do it again.

**2. A story that exists in `epics.md` but not on the board (`missing-story`).**
`scan_projects` refuses to overwrite a line whose story headings it cannot parse
(it warns and keeps the hand-authored entry). That guard is CORRECT — see the note
on `_first_or_second_id` below — but it means such a project's story list is
maintained by hand, so a newly added story is silently absent from the board.

This detector is deliberately LOCAL-ONLY: check 1 reads each project's
`sprint-status.yaml`, which is gitignored Tier-3 that CI cannot see. That is the
same asymmetry that caused the bug, so the check lives where the truth lives.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATE = REPO_ROOT / "docs" / "dashboard" / "generate.py"
DATA_JS = REPO_ROOT / "docs" / "dashboard" / "data.js"

# `### Story A1 (2.1): title` and `### Story 1.1: title` both. Group 1 is the
# leading id, group 2 the parenthesised alternate (absent for the simple form).
_STORY_HEADING = re.compile(
    r"^###\s+Story\s+([A-Za-z0-9.]+)\s*(?:\(\s*([A-Za-z0-9.]+)\s*\))?\s*[:—-]"
)

# Terminal statuses: a story here is finished and the board must say so.
_DONE = {"done"}


def _load_generate():
    """Import generate.py so its parsers are REUSED, never reimplemented.

    `parse_sprint_status` and `dashboard_id_to_status` already encode the
    feed-key -> board-id mapping (including `10-6` -> `10.6`); duplicating that
    here would let the two drift, which is the class of bug this file exists for.
    """
    spec = importlib.util.spec_from_file_location("_dashboard_generate", GENERATE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_dashboard_generate"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_data_js() -> dict:
    text = DATA_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.DASHBOARD_DATA\s*=\s*(\{.*?\});?\s*$", text, re.S)
    if not m:
        raise SystemExit(f"cannot parse {DATA_JS.relative_to(REPO_ROOT)}")
    return json.loads(m.group(1))


def _board_stories(proj: dict) -> list[list]:
    return [s for e in proj.get("epics", []) or [] for s in e.get("stories", []) or []]


def _epics_md_ids(path: Path) -> list[tuple[str, str | None]]:
    """Every story heading in an epics.md as (leading_id, parenthesised_id|None).

    Parsed for COMPARISON ONLY. Deriving the board's story list from these would
    have to pick one id per heading, and atlas proves there is no single right
    choice: Waves 0-H are keyed by the LEADING id (`A1`) because their completion
    signal is a `story(A1)` commit subject, while Epic 10 is keyed by the
    PARENTHESISED id (`10.6`) because its signal is a bmad-loop `10-6-…` merge.
    Each epic's ids match whatever its era's signal emits, so a mechanical
    derivation would break one half. Accepting EITHER id as a match keeps this
    check agnostic instead of encoding that scheme.
    """
    out: list[tuple[str, str | None]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _STORY_HEADING.match(line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def main() -> int:
    gen = _load_generate()
    data = _load_data_js()
    projects = data.get("projects", {})
    findings: list[str] = []
    checked_done = checked_stories = 0

    for key, proj in sorted(projects.items()):
        stories = _board_stories(proj)
        board_ids = {s[0] for s in stories}

        # --- check 1: the committed baseline agrees with the local feed --------
        rel = gen.PROJECT_SOURCES.get(key)
        feed_path = REPO_ROOT / rel if rel else None
        if feed_path and feed_path.is_file():
            sprint = gen.parse_sprint_status(feed_path)
            for sid, status, *_rest in stories:
                feed = gen.dashboard_id_to_status(sid, sprint)
                if feed is None:
                    continue
                checked_done += 1
                if feed in _DONE and status not in _DONE:
                    findings.append(
                        f"[stale-done] {key}:{sid} is '{feed}' in the sprint feed but "
                        f"'{status}' on the board — the committed baseline is behind. "
                        f"`--source git` never downgrades, so this will NOT self-heal "
                        f"at deploy: run `pixi run -e local-recipes dashboard-gen` and "
                        f"commit data.js."
                    )

        # --- check 2: no epics.md story is missing from the board -------------
        # Same key -> slug rule scan_projects uses (its `_KEY_SLUG_OVERRIDE`
        # inverted, else the `pyforge-` prefix it strips).
        slug = gen._KEY_SLUG_OVERRIDE.get(key, f"pyforge-{key}")
        epics_md = (REPO_ROOT / "_bmad-output" / "projects" / slug
                    / "planning-artifacts" / "epics.md")
        if not epics_md.is_file() or key in getattr(gen, "_DERIVE_EXCLUDE", set()):
            continue
        heading_ids = _epics_md_ids(epics_md)
        if not heading_ids:
            continue
        checked_stories += len(heading_ids)
        for lead, alt in heading_ids:
            if lead in board_ids or (alt and alt in board_ids):
                continue
            shown = f"{lead}" + (f" ({alt})" if alt else "")
            findings.append(
                f"[missing-story] {key}: epics.md has Story {shown} but no story with "
                f"that id is on the board. If this line's story list is hand-authored "
                f"(scan_projects warns when it cannot parse the headings), add it to "
                f"data.js by hand."
            )

    print(f"dashboard drift — {len(projects)} line(s) · {checked_done} story status(es) "
          f"cross-checked against sprint feeds · {checked_stories} epics.md heading(s) "
          f"cross-checked against the board")
    if findings:
        print(f"\nFINDINGS ({len(findings)}):")
        for f in findings:
            print(f"  ✗ {f}")
        return 1
    print("\nOK: the committed data.js matches the feeds, and every epics.md story "
          "is on the board.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
