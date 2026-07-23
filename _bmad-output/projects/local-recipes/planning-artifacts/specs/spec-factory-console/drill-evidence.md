# Regeneration drill — 2026-07-23 (spec-regenerable-factory CAP-4, story rf(2.2))

**Verdict: PASS.** A clean-room subagent (no repo access; input = `console-contract.md`
alone) rebuilt `docs/dashboard/generate.py` (293 lines). Verification: both scripts run
against identical inputs; `data.js` outputs byte-identical after timestamp
normalization (`DATA EQUIVALENT`); `--source git` mode ran green (25 dreams scanned,
correct tallies). Production keeps the original (battle-tested); this rebuilt artifact
is retained below as evidence. Procedure: back up original -> install rebuild -> run
both modes -> normalized diff -> restore.

```python
#!/usr/bin/env python3
"""Regenerate docs/dashboard/data.js: story statuses, dreams list, snapshot stamp.

Sources:
  sprint-status (default) — full-fidelity sync of story statuses from each
      project's _bmad-output sprint-status.yaml (may downgrade statuses).
  git — upgrade-only derivation of done story ids from git commit subjects
      (CI-safe, hands-off; never downgrades).

Stdlib only. All paths resolve relative to this script file. Only story
status (index 1), data["dreams"], and data["snapshot"] are ever modified;
all other data.js content is hand-curated and round-trips untouched.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA_JS = os.path.join(HERE, "data.js")

# Per-project sprint-status sources (repo-root-relative).
PROJECT_SOURCES = {
    "warden": "_bmad-output/projects/pyforge-warden/implementation-artifacts/sprint-status.yaml",
    "atlas": "_bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml",
    "regen": "_bmad-output/projects/local-recipes/implementation-artifacts/sprint-status.yaml",
}

VALID_DREAM_STATUSES = ("seeded", "in-deck", "in-spec", "realized")

DATA_PREFIX_RE = re.compile(r"^window\.DASHBOARD_DATA\s*=\s*")
SPRINT_ENTRY_RE = re.compile(
    r"^\s{2}(?P<key>[^:#\s][^:]*?):\s*(?P<val>[a-z][a-z-]*)\s*(#.*)?$"
)
SNAPSHOT_RE = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC")

# git-mode DONE-id extraction patterns.
WARDEN_MERGE_RE = re.compile(r"Merge bmad-loop/[^/]+/(\d+-\d+)-")
ATLAS_STORY_RE = re.compile(r"story\((\w[\w.]*)\)")
ATLAS_GH_RE = re.compile(r"\b([GH]\d+):")
REGEN_RF_RE = re.compile(r"\brf\((\d+\.\w+)\):")


def read_data():
    """Load DASHBOARD_DATA from data.js."""
    with open(DATA_JS, encoding="utf-8") as fh:
        text = fh.read().strip()
    text = DATA_PREFIX_RE.sub("", text, count=1).strip()
    if text.endswith(";"):
        text = text[:-1]
    return json.loads(text)


def write_data(data):
    """Serialize DASHBOARD_DATA back to data.js."""
    with open(DATA_JS, "w", encoding="utf-8") as fh:
        fh.write(
            "window.DASHBOARD_DATA = "
            + json.dumps(data, indent=2, ensure_ascii=False)
            + ";\n"
        )


def iter_stories(project):
    """Yield every story list of a project (each is [id, status, title, ...])."""
    for epic in project.get("epics", []):
        for story in epic.get("stories", []):
            yield story


# ---------------------------------------------------------------------------
# Source: sprint-status
# ---------------------------------------------------------------------------

def parse_sprint_status(path):
    """Extract the development_status mapping from a sprint-status.yaml (no YAML lib)."""
    entries = {}
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    in_block = False
    for line in lines:
        if not in_block:
            if line == "development_status:":
                in_block = True
            continue
        stripped = line.strip()
        if stripped and not line[0].isspace() and not stripped.startswith("#"):
            break  # block ends at the next non-indented, non-comment, non-empty line
        m = SPRINT_ENTRY_RE.match(line)
        if m:
            entries[m.group("key")] = m.group("val")
    return entries


def sprint_status_for(story_id, sprint):
    """First sprint key starting with the story-id prefix supplies the status."""
    prefix = story_id.lower().replace(".", "-") + "-"
    for key, val in sprint.items():
        if key.startswith(prefix):
            return val
    return None


def sync_from_sprint_status(data):
    projects = data.get("projects", {})
    for key, rel_path in PROJECT_SOURCES.items():
        if key not in projects:
            print(f"[{key}] not present in data.js -- skipped")
            continue
        path = os.path.join(REPO_ROOT, rel_path)
        if not os.path.isfile(path):
            print(f"[{key}] source file missing ({rel_path}) -- skipped")
            continue
        sprint = parse_sprint_status(path)
        matched = 0
        unmatched = []
        for story in iter_stories(projects[key]):
            story_id = str(story[0])
            status = sprint_status_for(story_id, sprint)
            if status is None:
                unmatched.append(story_id)
                continue
            matched += 1
            if status == "done":
                story[1] = "done"
            elif status == "in-progress":
                story[1] = "active"
            else:
                story[1] = "gated" if story[1] == "gated" else "pending"
        total = matched + len(unmatched)
        line = f"[{key}] {matched} matched / {len(unmatched)} unmatched (of {total})"
        if unmatched:
            line += ": unmatched ids: " + ", ".join(unmatched)
        print(line)


# ---------------------------------------------------------------------------
# Source: git
# ---------------------------------------------------------------------------

def git_ref():
    """Prefer main; fall back to HEAD (detached CI)."""
    probe = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "main"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return "main" if probe.returncode == 0 else "HEAD"


def git_done_ids():
    """Derive the set of DONE story ids from git commit subjects."""
    out = subprocess.run(
        ["git", "log", git_ref(), "--format=%s"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    done = set()
    for subject in out.splitlines():
        for m in WARDEN_MERGE_RE.finditer(subject):
            done.add(m.group(1).replace("-", "."))
        for m in ATLAS_STORY_RE.finditer(subject):
            done.add(m.group(1))
        for m in ATLAS_GH_RE.finditer(subject):
            done.add(m.group(1))
        for m in REGEN_RF_RE.finditer(subject):
            done.add(m.group(1))
    return done


def sync_from_git(data):
    done_ids = git_done_ids()
    print(
        f"Derived {len(done_ids)} done id(s) from git history: "
        + (", ".join(sorted(done_ids)) or "(none)")
    )
    for key, project in data.get("projects", {}).items():
        total = 0
        done_count = 0
        upgraded = []
        for story in iter_stories(project):
            total += 1
            story_id = str(story[0])
            # UPGRADE ONLY -- never downgrade (in-flight states aren't
            # derivable from history).
            if story_id in done_ids and story[1] != "done":
                story[1] = "done"
                upgraded.append(story_id)
            if story[1] == "done":
                done_count += 1
        line = f"[{key}] {done_count}/{total} done (+{len(upgraded)} upgraded"
        if upgraded:
            line += ": " + ", ".join(upgraded)
        line += ")"
        print(line)


# ---------------------------------------------------------------------------
# Dreams scan (both modes, every run)
# ---------------------------------------------------------------------------

def parse_dream_frontmatter(path):
    """Return (title, status, owner) from a dream file's YAML frontmatter."""
    title = status = owner = ""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return title, status, owner
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key == "title":
            title = value
        elif key == "status":
            status = value
        elif key == "owner":
            owner = value
    return title, status, owner


def scan_dreams(data):
    dreams_dir = os.path.join(REPO_ROOT, "docs", "dreams")
    dreams = []
    tallies = {}
    for path in sorted(glob.glob(os.path.join(dreams_dir, "*.md"))):
        name = os.path.basename(path)
        if name == "README.md":
            continue
        stem = os.path.splitext(name)[0]
        title, status, owner = parse_dream_frontmatter(path)
        if status not in VALID_DREAM_STATUSES:
            # Value passes through raw; the front-end buckets unknowns under seeded.
            print(f"WARN: {name}: unknown or missing dream status {status!r}")
        if not owner:
            print(f"WARN: {name}: missing owner")
        dreams.append(
            {
                "slug": stem,
                "title": title or stem,
                "status": status or "",
                "owner": owner or "",
            }
        )
        bucket = status or "(missing)"
        tallies[bucket] = tallies.get(bucket, 0) + 1
    data["dreams"] = dreams
    tally_str = ", ".join(f"{k}: {v}" for k, v in sorted(tallies.items()))
    print(f"Dreams: {len(dreams)} scanned" + (f" ({tally_str})" if tally_str else ""))


# ---------------------------------------------------------------------------
# Snapshot stamp
# ---------------------------------------------------------------------------

def stamp_snapshot(data, source):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    data["snapshot"] = SNAPSHOT_RE.sub(now, data.get("snapshot", ""), count=1)
    print(f"Snapshot stamped {now} (source: {source})")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        choices=("sprint-status", "git"),
        default="sprint-status",
        help="status source: sprint-status (local default, full fidelity) "
        "or git (CI, upgrade-only)",
    )
    args = parser.parse_args(argv)

    data = read_data()
    if args.source == "sprint-status":
        sync_from_sprint_status(data)
    else:
        sync_from_git(data)
    scan_dreams(data)
    stamp_snapshot(data, args.source)
    write_data(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
