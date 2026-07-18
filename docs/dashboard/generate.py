#!/usr/bin/env python3
"""Refresh docs/dashboard/data.js from live BMAD sprint-status.yaml files.

Run LOCALLY from the repo root: `python docs/dashboard/generate.py`
(or `pixi run dashboard-gen`). The sprint-status.yaml sources live under
`_bmad-output/projects/<slug>/implementation-artifacts/` which is Tier-3
**gitignored / local-only** — so this generator CANNOT run in CI. The refresh
flow is: run this locally -> it rewrites the committed `data.js` -> commit +
push -> the GitHub Pages workflow republishes the static `docs/dashboard/`.

It updates two things in data.js, nothing else:
  * each dashboard story's status, from the matching `development_status:` entry
  * the snapshot timestamp (the `YYYY-MM-DD HH:MM UTC` substring)

The render shell (index.html), the story titles, timing, gatenotes, roadmap and
all narrative copy stay hand-curated in data.js — this only syncs status + time.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# dashboard project-key -> its sprint-status.yaml (repo-root-relative)
PROJECT_SOURCES = {
    "warden": "_bmad-output/projects/pyforge-warden/implementation-artifacts/sprint-status.yaml",
    "atlas": "_bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml",
}

HERE = Path(__file__).resolve().parent
DATA_JS = HERE / "data.js"
# repo root = two levels up from docs/dashboard/
REPO_ROOT = HERE.parent.parent

_ENTRY = re.compile(r"^\s{2}(?P<key>[^:#\s][^:]*?):\s*(?P<val>[a-z][a-z-]*)\s*(#.*)?$")
_SNAP_TS = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC")


def parse_sprint_status(path: Path) -> dict[str, str]:
    """Return {sprint_key: status} from the `development_status:` block."""
    out: dict[str, str] = {}
    in_block = False
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not in_block:
            if stripped == "development_status:":
                in_block = True
            continue
        # stop at the next top-level key (column-0, non-comment, non-blank)
        if line and not line[0].isspace() and not stripped.startswith("#"):
            break
        m = _ENTRY.match(line)
        if m:
            out[m.group("key")] = m.group("val")
    return out


def dashboard_id_to_status(story_id: str, sprint: dict[str, str]) -> str | None:
    """Map a dashboard story id (`6.4`, `A1`, `0.1`, `B10`) to its sprint status."""
    norm = story_id.lower().replace(".", "-")
    prefix = norm + "-"
    for key, status in sprint.items():
        if key.startswith(prefix):
            return status
    return None


def sprint_to_dashboard_status(sprint_status: str, current: str) -> str:
    if sprint_status == "done":
        return "done"
    if sprint_status == "in-progress":
        return "active"
    # keep an explicit hard-gate marker if the dashboard set one
    if current == "gated":
        return "gated"
    return "pending"


def load_data() -> dict:
    text = DATA_JS.read_text()
    inner = text.strip()
    inner = re.sub(r"^window\.DASHBOARD_DATA\s*=\s*", "", inner)
    inner = inner.rstrip().rstrip(";")
    return json.loads(inner)


def now_utc() -> str:
    return subprocess.run(
        ["date", "-u", "+%Y-%m-%d %H:%M UTC"], capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> int:
    data = load_data()
    projects = data["projects"]
    total_matched = total_unmatched = 0

    for pkey, rel in PROJECT_SOURCES.items():
        proj = projects.get(pkey)
        if proj is None:
            print(f"[{pkey}] not in data.js — skipped")
            continue
        src = (REPO_ROOT / rel)
        if not src.exists():
            print(f"[{pkey}] sprint-status not found at {rel} — statuses left as-is")
            continue
        sprint = parse_sprint_status(src)
        matched, unmatched = 0, []
        for epic in proj["epics"]:
            for story in epic["stories"]:
                sid = story[0]
                sstat = dashboard_id_to_status(sid, sprint)
                if sstat is None:
                    unmatched.append(sid)
                    continue
                story[1] = sprint_to_dashboard_status(sstat, story[1])
                matched += 1
        total_matched += matched
        total_unmatched += len(unmatched)
        note = f"  unmatched: {', '.join(unmatched)}" if unmatched else ""
        print(f"[{pkey}] {matched} matched / {len(unmatched)} unmatched (of "
              f"{matched + len(unmatched)}){note}")

    # refresh the snapshot timestamp in place, preserving the provenance suffix
    ts = now_utc()
    data["snapshot"] = _SNAP_TS.sub(ts, data["snapshot"], count=1)

    DATA_JS.write_text(
        "window.DASHBOARD_DATA = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n"
    )
    print(f"\nsnapshot -> {ts}")
    print(f"data.js rewritten ({total_matched} matched, {total_unmatched} unmatched total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
