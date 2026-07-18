#!/usr/bin/env python3
"""Refresh docs/dashboard/data.js — the committed Warden+Atlas program console.

Two sources (`--source`):

* `sprint-status` (default, LOCAL) — reads each project's
  `sprint-status.yaml` and sets every mapped story to its full status
  (done / active / gated / pending). Richest view, but those files are Tier-3
  **gitignored / local-only**, so this mode can't run in CI.

* `git` (hands-off, CI-safe) — derives the DONE story set from `main`'s commit
  subjects (bmad-loop merge commits + atlas `story(...)` / `GN:`/`HN:` commits).
  It only ever UPGRADES a story to `done`; it never downgrades (an in-flight
  `active`/`gated` state isn't derivable from history, so those stay at their
  committed baseline). This is what the GitHub Pages workflow runs at deploy
  time against a full-history checkout, so the published site auto-updates as
  stories merge to `main` — no bot commit-back needed.

Local refresh:  python docs/dashboard/generate.py            (or: pixi run dashboard-gen)
CI (in-workflow): python docs/dashboard/generate.py --source git
"""
from __future__ import annotations

import argparse
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

# git-history DONE detection (used by --source git). Verified against main's subjects.
MAIN_BRANCH = "main"
# Warden: per-story bmad-loop merge commits `Merge bmad-loop/<run-id>/<X-Y>-<slug>`.
# The `[^/]+/` skips the run-id (2nd segment) so the capture is the story key (3rd).
_WARDEN_DONE = re.compile(r"Merge bmad-loop/[^/]+/(\d+-\d+)-")
# Atlas: most stories land as `story(A1)` / `story(B10)` / `story(0.1)`; the Wave
# G/H tail uses bare `GN:` / `HN:` subjects instead.
_ATLAS_STORY = re.compile(r"story\((\w[\w.]*)\)")
_ATLAS_GH = re.compile(r"\b([GH]\d+):")

HERE = Path(__file__).resolve().parent
DATA_JS = HERE / "data.js"
REPO_ROOT = HERE.parent.parent  # repo root = two levels up from docs/dashboard/

_ENTRY = re.compile(r"^\s{2}(?P<key>[^:#\s][^:]*?):\s*(?P<val>[a-z][a-z-]*)\s*(#.*)?$")
_SNAP_TS = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC")


# ---- source: sprint-status (local) ------------------------------------------

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
        if line and not line[0].isspace() and not stripped.startswith("#"):
            break  # next top-level key
        m = _ENTRY.match(line)
        if m:
            out[m.group("key")] = m.group("val")
    return out


def dashboard_id_to_status(story_id: str, sprint: dict[str, str]) -> str | None:
    """Map a dashboard story id (`6.4`, `A1`, `0.1`, `B10`) to its sprint status."""
    prefix = story_id.lower().replace(".", "-") + "-"
    for key, status in sprint.items():
        if key.startswith(prefix):
            return status
    return None


def sprint_to_dashboard_status(sprint_status: str, current: str) -> str:
    if sprint_status == "done":
        return "done"
    if sprint_status == "in-progress":
        return "active"
    if current == "gated":
        return "gated"
    return "pending"


def apply_sprint_status(projects: dict) -> None:
    for pkey, rel in PROJECT_SOURCES.items():
        proj = projects.get(pkey)
        if proj is None:
            print(f"[{pkey}] not in data.js — skipped")
            continue
        src = REPO_ROOT / rel
        if not src.exists():
            print(f"[{pkey}] sprint-status not found at {rel} — statuses left as-is")
            continue
        sprint = parse_sprint_status(src)
        matched, unmatched = 0, []
        for epic in proj["epics"]:
            for story in epic["stories"]:
                sstat = dashboard_id_to_status(story[0], sprint)
                if sstat is None:
                    unmatched.append(story[0])
                    continue
                story[1] = sprint_to_dashboard_status(sstat, story[1])
                matched += 1
        note = f"  unmatched: {', '.join(unmatched)}" if unmatched else ""
        print(f"[{pkey}] {matched} matched / {len(unmatched)} unmatched "
              f"(of {matched + len(unmatched)}){note}")


# ---- source: git (hands-off / CI) -------------------------------------------

def done_ids_from_git(branch: str) -> set[str]:
    """DONE dashboard-story ids derived from `branch`'s commit subjects."""
    ref = branch
    if subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", branch], capture_output=True
    ).returncode != 0:
        ref = "HEAD"  # detached checkout (e.g. some CI) — HEAD is the branch tip
    log = subprocess.run(
        ["git", "log", ref, "--format=%s"], capture_output=True, text=True, check=True
    ).stdout
    done: set[str] = set()
    for line in log.splitlines():
        m = _WARDEN_DONE.search(line)
        if m:
            done.add(m.group(1).replace("-", "."))  # 6-1 -> 6.1
        for a in _ATLAS_STORY.finditer(line):
            done.add(a.group(1))  # A1, B10, 0.1, F4 ...
        for a in _ATLAS_GH.finditer(line):
            done.add(a.group(1))  # G3, H1, H2 ...
    return done


def apply_git(projects: dict) -> None:
    done_ids = done_ids_from_git(MAIN_BRANCH)
    print(f"git-derived DONE ids ({len(done_ids)}): {', '.join(sorted(done_ids))}")
    for pkey, proj in projects.items():
        upgraded = done = 0
        for epic in proj["epics"]:
            for story in epic["stories"]:
                if story[0] in done_ids and story[1] != "done":
                    story[1] = "done"
                    upgraded += 1
                if story[1] == "done":  # after upgrade (incl. baseline dones)
                    done += 1
        total = sum(len(e["stories"]) for e in proj["epics"])
        print(f"[{pkey}] {done}/{total} done (+{upgraded} upgraded from git; "
              f"baseline dones preserved, never downgraded)")


# ---- shared ------------------------------------------------------------------

def load_data() -> dict:
    inner = DATA_JS.read_text().strip()
    inner = re.sub(r"^window\.DASHBOARD_DATA\s*=\s*", "", inner).rstrip().rstrip(";")
    return json.loads(inner)


def now_utc() -> str:
    return subprocess.run(
        ["date", "-u", "+%Y-%m-%d %H:%M UTC"], capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--source", choices=["sprint-status", "git"], default="sprint-status",
        help="sprint-status (default, local, richest) | git (hands-off, CI, done-only)",
    )
    args = ap.parse_args()

    data = load_data()
    if args.source == "git":
        apply_git(data["projects"])
    else:
        apply_sprint_status(data["projects"])

    ts = now_utc()
    data["snapshot"] = _SNAP_TS.sub(ts, data["snapshot"], count=1)
    DATA_JS.write_text(
        "window.DASHBOARD_DATA = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n"
    )
    print(f"\nsnapshot -> {ts}  ·  source: {args.source}  ·  data.js rewritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
