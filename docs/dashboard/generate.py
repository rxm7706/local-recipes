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

Both modes ALSO rescan `docs/dreams/*.md` frontmatter into `data["dreams"]`
(slug/title/status) — the Dreamscape lifecycle board. Unknown or missing
`status:` values are warned about here (this scan doubles as the Dream
frontmatter detector) and passed through raw; the front-end buckets them
under `dreamt`.

Local refresh:  python docs/dashboard/generate.py            (or: pixi run dashboard-gen)
CI (in-workflow): python docs/dashboard/generate.py --source git
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

# dashboard project-key -> its sprint-status.yaml (repo-root-relative)
PROJECT_SOURCES = {
    "warden": "_bmad-output/projects/pyforge-warden/implementation-artifacts/sprint-status.yaml",
    "atlas": "_bmad-output/projects/pyforge-atlas/implementation-artifacts/sprint-status.yaml",
    "regen": "_bmad-output/projects/local-recipes/implementation-artifacts/sprint-status.yaml",
    "herald": "_bmad-output/projects/pyforge-herald/implementation-artifacts/sprint-status.yaml",
    "doctor": "_bmad-output/projects/pyforge-doctor/implementation-artifacts/sprint-status.yaml",
    "scribe": "_bmad-output/projects/pyforge-scribe/implementation-artifacts/sprint-status.yaml",
    "marshal": "_bmad-output/projects/pyforge-marshal/implementation-artifacts/sprint-status.yaml",
    "mason": "_bmad-output/projects/pyforge-mason/implementation-artifacts/sprint-status.yaml",
    "steward": "_bmad-output/projects/pyforge-steward/implementation-artifacts/sprint-status.yaml",
    "genesis": "_bmad-output/projects/pyforge-genesis/implementation-artifacts/sprint-status.yaml",
}

# git-history DONE detection (used by --source git). Verified against main's subjects.
MAIN_BRANCH = "main"
# bmad-loop merge commits `Merge bmad-loop/<run-id>/<X-Y>-<slug> into <target> …`.
# Numeric story keys COLLIDE across loop-driven projects (warden 1-1 vs herald 1-1),
# so attribution is by the merge TARGET branch when present: loop/pyforge-herald ->
# herald, etc. Bare/legacy matches (warden's epic-tail branches) default to warden.
_LOOP_DONE = re.compile(r"Merge bmad-loop/[^/]+/(\d+-\d+)-\S*(?:\s+into\s+(\S+))?")
_LOOP_TARGET_PROJECT = (
    ("pyforge-herald", "herald"),
    ("pyforge-doctor", "doctor"),
    ("pyforge-scribe", "scribe"),
    ("pyforge-warden", "warden"),
    ("warden-epic", "warden"),
)
# Atlas: most stories land as `story(A1)` / `story(B10)` / `story(0.1)`; the Wave
# G/H tail uses bare `GN:` / `HN:` subjects instead.
_ATLAS_STORY = re.compile(r"story\((\w[\w.]*)\)")
_ATLAS_GH = re.compile(r"\b([GH]\d+):")
# Regenerable-factory program: per-story commits `rf(<id>): …` on main.
_RF_STORY = re.compile(r"\brf\((\d+\.\w+)\):")

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
    for line in path.read_text(encoding="utf-8").splitlines():
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


# Editorial metadata only. Everything STRUCTURAL (epics, stories, titles) is
# derived from epics.md by scan_projects() — see its docstring for why.
_EDITORIAL = ("label", "accentVar", "branch", "contract", "seglabels",
              "inflight", "velocity", "timing", "lineState")

# Dashboard key -> BMAD project slug, where they differ.
_KEY_SLUG_OVERRIDE = {"regen": "local-recipes"}
# Lines whose story set is NOT its project's epics.md. `regen` renders the
# regenerable-factory PRACTICE (4 CAPs / 14 stories from its own Spec), while
# local-recipes/epics.md is the 15-epic factory REBUILD spec — different things.
# Deriving it would replace 14 stories with 239.
_DERIVE_EXCLUDE = {"regen"}


def scan_projects(existing: dict) -> dict:
    """One build line per BMAD project that has an `epics.md` — DERIVED.

    Previously `data.projects` was hand-maintained: the epic/story skeleton was
    copied into data.js by hand, so it could drift from epics.md silently, and a
    project with no entry simply did not exist on the board. That is exactly what
    happened on 2026-07-25 — marshal, mason, steward and genesis all had epics
    (and two had shipped code) while In Build showed nothing, because nobody had
    hand-added them.

    Now the structure is derived and only *editorial* fields (label, contract
    blurb, accent, segment labels) are carried forward from the previous run. A
    new project appears on the board the moment it has an `epics.md`; a renamed
    or re-scoped epic follows automatically. `check_project_coverage()` turns the
    remaining "should this have a line at all?" judgement into a loud failure
    rather than a silent omission.
    """
    out: dict = {}
    for ep in sorted((REPO_ROOT / "_bmad-output" / "projects").glob(
            "*/planning-artifacts/epics.md")):
        slug = ep.relative_to(REPO_ROOT / "_bmad-output" / "projects").parts[0]
        key = next((k for k, s in _KEY_SLUG_OVERRIDE.items() if s == slug),
                   slug.removeprefix("pyforge-"))
        prev = existing.get(key, {})
        if key in _DERIVE_EXCLUDE:
            if prev:
                out[key] = prev
            continue
        epics, cur = [], None
        for line in ep.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^## Epic (\d+)\s*[:—-]\s*(.+)$", line)
            if m:
                cur = {"badge": f"E{m.group(1)}", "title": m.group(2).strip(), "stories": []}
                epics.append(cur)
                continue
            m = re.match(r"^### Story (\d+)\.(\d+)\s*[:—-]\s*(.+)$", line)
            if m and cur and m.group(1) == cur["badge"][1:]:
                epics[-1]["stories"].append(
                    [f"{m.group(1)}.{m.group(2)}", "pending", m.group(3).strip()])
        # Guard on STORIES, not just epics. pyforge-atlas parses to 9 epics with
        # ZERO stories because its story headings are `A1`/`B1`/`0.1`, not
        # `Story 1.1` — and a naive `if not epics` guard let that through and
        # silently overwrote 32 real stories. A project whose epics.md uses a
        # different convention keeps its previous entry and says so loudly.
        if sum(len(e["stories"]) for e in epics) == 0:
            if prev:
                print(f"[projects] WARN {slug}: epics.md parsed {len(epics)} epic(s) "
                      f"but NO stories (unrecognised story-heading convention) — "
                      f"keeping the existing hand-authored line, NOT overwriting it")
            continue
        row = {k: prev[k] for k in _EDITORIAL if k in prev}
        row.setdefault("label", key.capitalize())
        row.setdefault("accentVar", "--accent")
        row.setdefault("branch", "not started")
        row.setdefault("contract", f"spec-{slug}")
        row.setdefault("seglabels", [e["badge"] for e in epics][:6])
        row.setdefault("inflight", None)
        row.setdefault("velocity", "")
        row.setdefault("timing", "")
        row.setdefault("lineState", {"state": "ready", "at": ""})
        row["epics"] = epics
        out[key] = row
    for key, row in existing.items():          # keep anything not epics-backed
        out.setdefault(key, row)
    added = [k for k in out if k not in existing]
    print(f"[projects] {len(out)} lines derived from epics.md"
          + (f" · NEW: {', '.join(added)}" if added else ""))
    return out


def check_project_coverage(projects: dict) -> None:
    """Every BMAD project with an epics.md must have a line, or say why not.

    The silent-omission guard. Without it, "this project is missing from In
    Build" is invisible — which is how four lines went unrendered.
    """
    slugs = {p.relative_to(REPO_ROOT / "_bmad-output" / "projects").parts[0]
             for p in (REPO_ROOT / "_bmad-output" / "projects").glob(
                 "*/planning-artifacts/epics.md")}
    covered = {_KEY_SLUG_OVERRIDE.get(k, f"pyforge-{k}" if f"pyforge-{k}" in slugs else k)
               for k in projects}
    missing = sorted(slugs - covered)
    if missing:
        print(f"[projects] WARN {len(missing)} project(s) have epics.md but NO "
              f"build line: {', '.join(missing)}")


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


# dashboard project-key -> its bmad-loop loop-home dir (sibling of the repo).
# Local-mode enrichment ONLY: bmad-loop writes sprint-status at story COMPLETION,
# not start — so a story being actively worked shows `backlog` in the feed. The
# latest live run's story-worktree name carries the story key; mark it active.
# CI has no sibling loop homes, so this is a structural no-op there.
LOOP_HOMES = {
    "herald": "local-recipes-loop-pyforge-herald",
    "doctor": "local-recipes-loop-pyforge-doctor",
    "scribe": "local-recipes-loop-pyforge-scribe",
    "warden": "local-recipes-loop-pyforge-warden",
}
_WT_STORY = re.compile(r"^(\d+-\d+)-")
_RUN_FRESH_SECS = 30 * 60   # a run dir older than this is NOT in flight (was 12h — a
                            # 8.5h-dead run still read "in flight", i.e. the console
                            # claimed motion it had not measured)


def _live_loop_sessions() -> set[str]:
    """Run ids with a live tmux session — the only positive proof a line is running."""
    try:
        r = subprocess.run(["tmux", "ls"], capture_output=True, text=True, timeout=10)
        return {m for m in re.findall(r"bmad-loop-(\S+?):", r.stdout)} if r.returncode == 0 else set()
    except Exception:
        return set()


def apply_loop_inflight(projects: dict) -> None:
    import time
    for pkey, home in LOOP_HOMES.items():
        proj = projects.get(pkey)
        runs_dir = REPO_ROOT.parent / home / ".bmad-loop" / "runs"
        if proj is None or not runs_dir.is_dir():
            continue
        runs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        active_ids = set()
        live = _live_loop_sessions()
        fresh = bool(runs) and (time.time() - runs[0].stat().st_mtime) < _RUN_FRESH_SECS
        if runs and (runs[0].name in live or fresh):
            wts = runs[0] / "worktrees"
            if wts.is_dir():
                for wt in wts.iterdir():
                    m = _WT_STORY.match(wt.name)
                    if m:
                        active_ids.add(m.group(1).replace("-", "."))
        if not active_ids:
            continue
        marked = []
        for epic in proj["epics"]:
            for story in epic["stories"]:
                if story[0] in active_ids and story[1] == "pending":
                    story[1] = "active"
                    marked.append(story[0])
        if marked:
            print(f"[{pkey}] loop-home in-flight: {', '.join(marked)} (run {runs[0].name})")


# ---- source: git (hands-off / CI) -------------------------------------------

def done_ids_from_git(branch: str) -> dict[str, set[str]]:
    """PER-PROJECT done story ids from `branch`'s commit subjects.

    Numeric story ids collide across projects (the regen program's rf(5.1)
    is NOT warden's 5.1), so each project matches ONLY its own commit
    convention — never a shared pool.
    """
    ref = branch
    if subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", branch], capture_output=True
    ).returncode != 0:
        ref = "HEAD"  # detached checkout (e.g. some CI) — HEAD is the branch tip
    log = subprocess.run(
        ["git", "log", ref, "--format=%s"], capture_output=True, text=True, check=True
    ).stdout
    done: dict[str, set[str]] = {"warden": set(), "atlas": set(), "regen": set(),
                                 "herald": set(), "doctor": set(), "scribe": set()}
    for line in log.splitlines():
        m = _LOOP_DONE.search(line)
        if m:
            target = m.group(2) or ""
            pkey = next((p for frag, p in _LOOP_TARGET_PROJECT if frag in target),
                        "warden")  # legacy bare matches are warden's
            done[pkey].add(m.group(1).replace("-", "."))  # 6-1 -> 6.1
        for a in _ATLAS_STORY.finditer(line):
            done["atlas"].add(a.group(1))  # A1, B10, 0.1, F4 ...
        for a in _ATLAS_GH.finditer(line):
            done["atlas"].add(a.group(1))  # G3, H1, H2 ...
        for a in _RF_STORY.finditer(line):
            done["regen"].add(a.group(1))  # 1.1, 4.R ...
    return done


def apply_git(projects: dict) -> None:
    per_project = done_ids_from_git(MAIN_BRANCH)
    for pkey, ids in per_project.items():
        print(f"git-derived DONE ids [{pkey}] ({len(ids)}): {', '.join(sorted(ids))}")
    for pkey, proj in projects.items():
        done_ids = per_project.get(pkey, set())
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


# ---- dreams (both modes) -----------------------------------------------------

DREAMS_DIR = REPO_ROOT / "docs" / "dreams"
# The lifecycle, each state named for the ACT THAT COMPLETED — never for the
# artifact that proves it, and never for activity. Status declares what EXISTS
# (stable, honestly hand-declarable); the board DERIVES what is happening from
# live build lines. A `building` status was considered and rejected: it would go
# stale the moment a line pauses or finishes — exactly how pyforge-warden came to
# read `in-spec` while shipped 31/31, and deckcraft `dreamt` while holding a deck
# AND a Spec (both found + fixed 2026-07-25).
DREAM_STATUSES = ("dreamt", "pitched", "specified", "realized", "archived")
# Perpetual concerns — tended, never finished. They sit OUTSIDE the lifecycle:
# excluded from backlog (nobody can close them) and from realized (never done).
DREAM_TYPES = ("dream", "practice")

# The eight Smiths — the canonical station roster (docs/dreams/pyforge-charter.md
# §§1-8). `owner:` on a Dream names the station accountable for carrying it all
# the way Dream -> code; the station is the POST, not the product, so owning a
# Dream does not mean it becomes that Smith's package.
STATIONS = ("herald", "marshal", "atlas", "warden",
            "mason", "doctor", "scribe", "steward")
# The ONE Dream that may name no station, because it CONSTITUTES them: the
# Charter. `guild` is NOT a ninth station and never renders as one — it marks a
# Dream sitting above the roster, not beside it. (Genesis was briefly here and
# was wrong: its origin doc is Marshal's own setup plan, and "the bootstrapper
# that installs the operating model anywhere" is Marshal's craft.)
GUILD_DREAMS = ("pyforge-charter",)


# Deck dirs whose name differs from the dream slug (mason's chapter deck backs
# the packaging-factory dream, etc.).
DREAM_DECK_ALIASES = {
    "packaging-factory": "pyforge-mason",
    "agentic-sdlc-autonomy": "agentic-sdlc",
    "pyforge-charter": "pyforge-genesis",   # the master vision deck
}
# Dreams whose build runs as a console program (chip shows live done/total).
DREAM_PROGRAM = {
    "pyforge-warden": "warden",
    "pyforge-atlas": "atlas",
    "regenerable-factory": "regen",
}


def dream_chain(slug: str) -> dict:
    """Chain links for the drill-through indicators (no-straggler visibility):
    deck dir (exact slug or alias), Spec folder, BMAD project dir,
    console-program key."""
    chain: dict[str, str] = {}
    deck = DREAM_DECK_ALIASES.get(slug, slug)
    if (REPO_ROOT / "presentations" / deck).is_dir():
        chain["deck"] = f"presentations/{deck}"
    hits = sorted((REPO_ROOT / "_bmad-output" / "projects").glob(
        f"*/planning-artifacts/specs/spec-{slug}"))
    if hits:
        chain["spec"] = str(hits[0].relative_to(REPO_ROOT))
    if (REPO_ROOT / "_bmad-output" / "projects" / slug).is_dir():
        chain["project"] = f"_bmad-output/projects/{slug}"
    if slug in DREAM_PROGRAM:
        chain["program"] = DREAM_PROGRAM[slug]
    return chain


def scan_dreams() -> list[dict]:
    """[{slug, title, status}] from docs/dreams/*.md frontmatter (README skipped)."""
    dreams: list[dict] = []
    for f in sorted(DREAMS_DIR.glob("*.md")):
        if f.name == "README.md":
            continue
        title, status, owner, archived_reason = None, None, None, None
        dtype, blocked_on = None, None
        lines = f.read_text(encoding="utf-8").splitlines()
        if lines and lines[0].strip() == "---":
            for line in lines[1:]:
                if line.strip() == "---":
                    break
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip()
                elif line.startswith("status:"):
                    status = line.split(":", 1)[1].strip()
                elif line.startswith("owner:"):
                    owner = line.split(":", 1)[1].strip()
                elif line.startswith("archived-reason:"):
                    archived_reason = line.split(":", 1)[1].strip()
                elif line.startswith("type:"):
                    dtype = line.split(":", 1)[1].strip()
                elif line.startswith("blocked-on:"):
                    blocked_on = line.split(":", 1)[1].strip()
        if status not in DREAM_STATUSES:
            print(f"[dreams] WARN {f.name}: status {status!r} not in {DREAM_STATUSES}"
                  " — passed through; board shows it under 'dreamt'")
        if not owner:
            print(f"[dreams] WARN {f.name}: no owner: in frontmatter")
        elif owner == "guild" and f.stem not in GUILD_DREAMS:
            print(f"[dreams] WARN {f.name}: owner 'guild' is reserved for "
                  f"{GUILD_DREAMS} — every other Dream must name a station")
        elif owner not in STATIONS and owner != "guild":
            print(f"[dreams] WARN {f.name}: owner {owner!r} is not one of the "
                  f"eight Smiths {STATIONS}")
        if dtype and dtype not in DREAM_TYPES:
            print(f"[dreams] WARN {f.name}: type {dtype!r} not in {DREAM_TYPES}")
        dream = {"slug": f.stem, "title": title or f.stem,
                 "status": status or "", "owner": owner or "",
                 "type": dtype or "dream",
                 "chain": dream_chain(f.stem)}
        if blocked_on:
            dream["blockedOn"] = blocked_on
        if archived_reason:
            dream["archived_reason"] = archived_reason
        dreams.append(dream)
    by_status = {s: sum(1 for d in dreams if d["status"] == s) for s in DREAM_STATUSES}
    print(f"[dreams] {len(dreams)} scanned: "
          + " / ".join(f"{n} {s}" for s, n in by_status.items()))
    return dreams


# ---- specs roster (all BMAD Specs; docs/specs legacy is deliberately out) --

def _git_date(path: Path) -> str:
    r = subprocess.run(
        ["git", "log", "-1", "--format=%ad", "--date=format:%Y-%m-%d", "--",
         str(path.relative_to(REPO_ROOT))],
        capture_output=True, text=True, cwd=REPO_ROOT)
    return r.stdout.strip()


def scan_specs() -> list[dict]:
    """Every _bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md."""
    rows: list[dict] = []
    for spec_dir in sorted((REPO_ROOT / "_bmad-output" / "projects").glob(
            "*/planning-artifacts/specs/spec-*")):
        smd = spec_dir / "SPEC.md"
        if not smd.is_file():
            continue
        text = smd.read_text(encoding="utf-8")
        slug = spec_dir.name.removeprefix("spec-")
        project = spec_dir.relative_to(REPO_ROOT / "_bmad-output" / "projects").parts[0]
        m = re.search(r"^#\s+(.+)$", text, re.M)
        title = (m.group(1).strip() if m else slug)
        title = re.sub(r"^SPEC\s*[—–-]\s*", "", title)
        caps = len(set(re.findall(r"\bCAP-\d+\b", text)))
        comp = 0
        if text.startswith("---"):
            fm = text.split("---", 2)[1]
            cm = re.search(r"^companions:\s*\n((?:[ \t]*-[ \t].*\n)*)", fm, re.M)
            if cm:
                comp = len(re.findall(r"^[ \t]*-[ \t]", cm.group(1), re.M))
            inline = re.search(r"^companions:\s*\[([^\]]*)\]", fm, re.M)
            if inline and inline.group(1).strip():
                comp = len(inline.group(1).split(","))
        dream = slug if (DREAMS_DIR / f"{slug}.md").exists() else ""
        rows.append({"slug": slug, "project": project, "title": title,
                     "caps": caps, "companions": comp,
                     "updated": _git_date(spec_dir), "dream": dream,
                     "path": str(spec_dir.relative_to(REPO_ROOT))})
    print(f"[specs] {len(rows)} Specs scanned "
          f"({', '.join(sorted({r['project'] for r in rows}))})")
    return rows


# ---- spec campaign (2026-07-25 factory spec-completion program) --------------

CAMPAIGN_ROSTER = [
    # wave · project · agent model · depth (epics = full chain; prd+arch stops early) · seed state
    {"wave": "1a", "slug": "pyforge-doctor",       "model": "sonnet", "depth": "epics",    "state": "running"},
    {"wave": "1b", "slug": "pyforge-steward",      "model": "sonnet", "depth": "epics",    "state": "running"},
    {"wave": "1c", "slug": "pyforge-scribe",       "model": "sonnet", "depth": "epics",    "state": "running"},
    {"wave": "1d", "slug": "pyforge-herald",       "model": "sonnet", "depth": "epics",    "state": "running"},
    {"wave": "1e", "slug": "pyforge-marshal",      "model": "opus",   "depth": "epics",    "state": "running"},
    {"wave": "1f", "slug": "pyforge-mason",        "model": "opus",   "depth": "epics",    "state": "running"},
    {"wave": "2a", "slug": "presenton-pixi-image", "model": "sonnet", "depth": "epics",    "state": "running"},
    {"wave": "2b", "slug": "wasm-analytics-stack", "model": "sonnet", "depth": "prd+arch", "state": "running"},
    {"wave": "2c", "slug": "unity-data-stack",     "model": "opus",   "depth": "prd+arch", "state": "running"},
    {"wave": "2d", "slug": "pyforge-genesis",      "model": "opus",   "depth": "epics",    "state": "queued"},
]

CAMPAIGN_STAGES = ("research", "brief", "prd", "architecture", "epics")


def scan_campaign() -> dict:
    """Stage completion per chain, detected from planning-artifacts on main.

    In-flight chains write in isolated loop worktrees, so main shows nothing
    until a chain merges — roster `state` covers the gap (running/queued);
    detection upgrades it to partial/landed automatically at each merge.
    """
    rows: list[dict] = []
    for e in CAMPAIGN_ROSTER:
        pa = REPO_ROOT / "_bmad-output" / "projects" / e["slug"] / "planning-artifacts"
        have = {
            "research": bool(list((pa / "research").glob("*.md"))) if (pa / "research").is_dir() else False,
            "brief": bool(list(pa.glob("product-brief*")) or list(pa.glob("*/product-brief*"))
                          or list(pa.glob("briefs/**/brief*.md"))),
            "prd": (pa / "prd.md").is_file() or bool(list(pa.glob("prds/*/prd.md"))),
            "architecture": ((pa / "architecture.md").is_file()
                             or bool(list(pa.glob("architecture/*/*.md")))),
            "epics": (pa / "epics.md").is_file(),
        }
        target = [s for s in CAMPAIGN_STAGES
                  if not (s == "epics" and e["depth"] == "prd+arch")]
        n = sum(have[s] for s in target)
        status = "landed" if n == len(target) else ("partial" if n else e["state"])
        rows.append({**e, "have": have, "n": n, "of": len(target), "status": status})
    landed = sum(1 for r in rows if r["status"] == "landed")
    running = sum(1 for r in rows if r["status"] == "running")
    print(f"[campaign] {len(rows)} chains · {running} running · {landed} landed")
    return {"launched": "2026-07-25",
            "chain": "research → brief → PRD → architecture → epics",
            "rows": rows}


# ---- build campaign (implementation lines across all bmad-projects) ----------

IMPL_CAMPAIGN = [
    # pkey = data.js projects key when the line is dashboard-wired; stories = static count otherwise
    {"slug": "pyforge-herald",       "pkey": "herald", "stories": 17, "state": "running",
     "note": "line 1 — smallest full product, spec settled 0 OQs"},
    {"slug": "pyforge-doctor",       "pkey": "doctor", "stories": 12, "state": "running",
     "note": "line 2 — consolidative wrap"},
    {"slug": "pyforge-scribe",       "pkey": "scribe", "stories": 9,  "state": "running",
     "note": "line 3 — team memory + graph"},
    {"slug": "pyforge-steward",      "pkey": None, "stories": 18, "state": "queued",
     "note": "next free slot"},
    {"slug": "deckcraft",            "pkey": None, "stories": 28, "state": "queued",
     "note": "planned pre-campaign (6 epics); research backfill advisable before launch"},
    {"slug": "pyforge-mason",        "pkey": None, "stories": 38, "state": "queued",
     "note": "longest persona line; CFE Rule-2 retro at closeout"},
    {"slug": "presenton-pixi-image", "pkey": None, "stories": 30, "state": "held",
     "note": "operator Phase-0 gates: MS disconnected-stack check + memory-subsystem scope"},
    {"slug": "pyforge-marshal",      "pkey": None, "stories": 40, "state": "held",
     "note": "AD-25–39 adversarial pass + floor quiescence (touches loop machinery)"},
    {"slug": "pyforge-genesis",      "pkey": None, "stories": 36, "state": "held",
     "note": "last — model stability + consumes marshal-owned scripts"},
    {"slug": "wasm-analytics-stack", "pkey": None, "stories": 0,  "state": "future",
     "note": "PRD+arch only by design; stories decompose when scheduled"},
    {"slug": "unity-data-stack",     "pkey": None, "stories": 0,  "state": "future",
     "note": "PRD+arch only by design; stories decompose when scheduled"},
]


def scan_impl_campaign(projects: dict) -> dict:
    """Build-campaign roster; wired lines derive done/total live from `projects`."""
    rows: list[dict] = []
    for e in IMPL_CAMPAIGN:
        done, total = 0, e["stories"]
        if e["pkey"] and e["pkey"] in projects:
            stories = [s for ep in projects[e["pkey"]]["epics"] for s in ep["stories"]]
            total = len(stories)
            done = sum(1 for s in stories if s[1] == "done")
        state = "done" if total and done == total else e["state"]
        rows.append({**e, "done": done, "total": total, "state": state})
    running = sum(1 for r in rows if r["state"] == "running")
    dn = sum(1 for r in rows if r["state"] == "done")
    print(f"[build-campaign] {len(rows)} lines · {running} running · {dn} done")
    return {"launched": "2026-07-25", "rows": rows}


# ---- build-line state (every In Build / Realized row carries a chip) ---------

LINE_HOMES = {"herald": "pyforge-herald", "doctor": "pyforge-doctor",
              "scribe": "pyforge-scribe", "warden": "pyforge-warden", "atlas": "pyforge-atlas"}
_STORY_KEY = re.compile(r"^\s*(\d+-\d+-[a-z0-9-]+):\s*backlog", re.M)


def apply_line_state(projects: dict) -> None:
    """Attach {state, at} to each project: complete | in-flight | paused | ready."""
    live = _live_loop_sessions()
    for pkey, proj in projects.items():
        stories = [s for e in proj["epics"] for s in e["stories"]]
        done = sum(1 for s in stories if s[1] == "done")
        active = next((s[0] for s in stories if s[1] == "active"), "")
        slug = LINE_HOMES.get(pkey)
        state, at = "ready", ""
        if stories and done == len(stories):
            state = "complete"
        elif active:
            state, at = "in flight", active
        else:
            # parked: name the resume point from the sprint feed, else the first pending story
            nxt = ""
            if slug:
                feed = REPO_ROOT / f"_bmad-output/projects/{slug}/implementation-artifacts/sprint-status.yaml"
                if feed.is_file():
                    m = _STORY_KEY.search(feed.read_text(encoding="utf-8"))
                    if m:
                        nxt = ".".join(m.group(1).split("-")[:2])
            if not nxt:
                nxt = next((s[0] for s in stories if s[1] != "done"), "")
            state, at = ("paused" if done else "ready"), nxt
        proj["lineState"] = {"state": state, "at": at}
    counts: dict[str, int] = {}
    for proj in projects.values():
        counts[proj["lineState"]["state"]] = counts.get(proj["lineState"]["state"], 0) + 1
    print("[lines] " + " · ".join(f"{v} {k}" for k, v in sorted(counts.items()))
          + (f" · live sessions: {len(live)}" if live else " · no live sessions"))


# ---- sync & health (the standing detectors + reconciliation state) -----------
# The factory-console Dream's frontier calls for a "fleet health strip"; these are
# the three always-on detectors CLAUDE.md/SYNC-RUNBOOK.md define. Each runs in ~1s.
# CI (--source git) may lack pixi/atlas, so a detector that cannot run reports
# "unknown" — the strip never claims green it did not measure.

DETECTORS = [
    ("drift-check",  "bmad-drift-check",   "BMAD artifacts vs the live factory",
     "_bmad-output/projects/local-recipes/SYNC-RUNBOOK.md"),
    ("spec-surface", "spec-surface-check", "every tracked file under a Spec surface", ""),
    ("llms-full",    "llms-full-check",    "library catalog freshness", ""),
]
_FINDING_RE = re.compile(r"(\d+)\s+(?:integrity|currency|finding)")
_FINDINGS_HDR = re.compile(r"^FINDINGS \((\d+)\)")   # spec-surface-check's form


def scan_health() -> dict:
    """Run the standing detectors; capture verdict + finding count + remedy."""
    rows = []
    for name, task, guards, runbook in DETECTORS:
        try:
            r = subprocess.run(["pixi", "run", "--frozen", "-e", "local-recipes", task],
                               capture_output=True, text=True, cwd=REPO_ROOT, timeout=120)
            out = (r.stdout + r.stderr).strip().splitlines()
            verdict_line = next((l.strip() for l in reversed(out)
                                 if l.strip().startswith(("OK:", "DRIFT:", "FAIL:", "FINDINGS ("))), "")
            state = "green" if r.returncode == 0 else ("fail" if verdict_line.startswith("FAIL") else "drift")
            hdr = _FINDINGS_HDR.match(verdict_line)
            n = int(hdr.group(1)) if hdr else (
                sum(int(m) for m in _FINDING_RE.findall(verdict_line)) if verdict_line else 0)
        except Exception:                      # pixi absent (CI), timeout, anything
            state, verdict_line, n = "unknown", "detector could not run here", 0
        rows.append({"name": name, "task": task, "guards": guards, "state": state,
                     "findings": n, "verdict": verdict_line[:120], "runbook": runbook})

    # Baseline state: compare the recorded FACTORY FINGERPRINT to live, not commit
    # counts — the baseline commit often isn't on main's first-parent chain (this repo
    # is a staged-recipes fork), so "N commits behind" is noise. The fingerprint is
    # exactly what makes drift-check's `surface-changed` fire.
    base, deltas = {}, []
    bp = REPO_ROOT / "_bmad-output/projects/local-recipes/.sync-baseline.json"
    if bp.is_file():
        try:
            base = json.loads(bp.read_text(encoding="utf-8"))
            live = {}
            g = subprocess.run(["pixi", "run", "--frozen", "-e", "local-recipes", "bmad-groundtruth"],
                               capture_output=True, text=True, cwd=REPO_ROOT, timeout=120)
            if g.returncode == 0:
                s = g.stdout[g.stdout.find("{"):g.stdout.rfind("}") + 1]
                live = json.loads(s) if s else {}
            for key, label in (("skill_version", "skill"), ("pixi_envs", "pixi envs"),
                               ("mcp_tools", "MCP tools"), ("atlas_phases", "phases"),
                               ("schema_version", "schema")):
                b, l = base.get(key), live.get(key)
                if b is not None and l is not None and str(b) != str(l):
                    deltas.append({"what": label, "baseline": str(b), "live": str(l)})
        except Exception:
            pass
    green = sum(1 for r in rows if r["state"] == "green")
    print(f"[health] {green}/{len(rows)} detectors green · "
          + (f"{len(deltas)} fingerprint delta(s) vs baseline" if deltas else "fingerprint matches baseline"))
    return {"detectors": rows,
            "baseline": {"skill": base.get("skill_version", ""), "head": (base.get("git_head") or "")[:10],
                         "deltas": deltas,
                         "runbook": "_bmad-output/projects/local-recipes/SYNC-RUNBOOK.md"}}


# ---- fleet view (Dream -> Code, per project: stage, recency, version) --------

FLEET_PROJECTS = [
    # (display label, project slug, dream slug — differs where the Dream predates the station)
    ("herald", "pyforge-herald", "pyforge-herald"),
    ("doctor", "pyforge-doctor", "pyforge-doctor"),
    ("scribe", "pyforge-scribe", "pyforge-scribe"),
    ("steward", "pyforge-steward", "pyforge-steward"),
    ("marshal", "pyforge-marshal", "pyforge-marshal"),
    ("mason", "pyforge-mason", "pyforge-mason"),
    ("atlas", "pyforge-atlas", "pyforge-atlas"),
    ("warden", "pyforge-warden", "pyforge-warden"),
    ("genesis", "pyforge-genesis", "pyforge-genesis"),
    ("deckcraft", "deckcraft", "deckcraft"),
    ("presenton", "presenton-pixi-image", "presenton-pixi-image"),
    ("unity", "unity-data-stack", "unity-data-stack"),
    ("wasm", "wasm-analytics-stack", "wasm-analytics-stack"),
]
# lifecycle order — the Dream-to-Code chain, left to right
FLEET_STAGES = ("dream", "deck", "spec", "research", "brief", "prd", "arch", "epics", "code")
# stages a project legitimately does not have (depth chosen at planning time)
FLEET_NA = {"unity-data-stack": {"epics"}, "wasm-analytics-stack": {"epics"}}
_STALE_DAYS = 30


def _added(patterns: list[str]) -> str:
    """Earliest add-date across matching paths (MM-DD), '' when absent."""
    best = ""
    for pat in patterns:
        for path in glob.glob(pat, recursive=True):
            rel = str(Path(path).resolve().relative_to(REPO_ROOT))
            r = subprocess.run(["git", "log", "--diff-filter=A", "--format=%ad",
                                "--date=format:%m-%d", "--", rel],
                               capture_output=True, text=True, cwd=REPO_ROOT)
            dates = [d for d in r.stdout.strip().split("\n") if d]
            if dates and (not best or dates[-1] < best):
                best = dates[-1]
    return best


def _last_touched(paths: list[str]) -> str:
    """Most recent commit date (ISO) across the given paths."""
    existing = [p for p in paths if (REPO_ROOT / p).exists()]
    if not existing:
        return ""
    r = subprocess.run(["git", "log", "-1", "--format=%ad", "--date=short", "--"] + existing,
                       capture_output=True, text=True, cwd=REPO_ROOT)
    return r.stdout.strip()


def _pkg_version(slug: str) -> str:
    f = REPO_ROOT / "src" / "shared" / "packages" / slug / "pyproject.toml"
    if not f.is_file():
        return ""
    m = re.search(r'^version\s*=\s*"([^"]+)"', f.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else ""


def _spec_open_questions(slug: str) -> int:
    """Unresolved `open_questions[]` in this project's SPEC.md (0 when none)."""
    for smd in sorted((REPO_ROOT / "_bmad-output" / "projects" / slug /
                       "planning-artifacts" / "specs").glob("spec-*/SPEC.md")):
        text = smd.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        try:
            import yaml
            fm = yaml.safe_load(text.split("---")[1]) or {}
        except Exception:
            continue
        q = fm.get("open_questions") or []
        if q:
            return len(q)
    return 0


def scan_fleet(projects: dict) -> dict:
    """Per-project Dream-to-Code state: stage dates, furthest stage, recency, version."""
    from datetime import date
    today = date.today()
    rows = []
    for label, slug, dream in FLEET_PROJECTS:
        pa = f"_bmad-output/projects/{slug}/planning-artifacts"
        stages = {
            "dream":    _added([f"docs/dreams/{dream}.md"]),
            "deck":     _added([f"presentations/{slug}/project/*.dc.html"]),
            "spec":     _added([f"{pa}/specs/spec-*/SPEC.md"]),
            "research": _added([f"{pa}/research/*.md"]),
            "brief":    _added([f"{pa}/product-brief*", f"{pa}/briefs/**/brief*.md"]),
            "prd":      _added([f"{pa}/prd.md", f"{pa}/prds/*/prd.md"]),
            "arch":     _added([f"{pa}/architecture.md", f"{pa}/architecture/*/*.md"]),
            "epics":    _added([f"{pa}/epics.md"]),
            "code":     _added([f"src/shared/packages/{slug}/pyproject.toml"]),
        }
        na = FLEET_NA.get(slug, set())
        reached = [s for s in FLEET_STAGES if stages[s]]
        furthest = reached[-1] if reached else "dream"
        updated = _last_touched([f"docs/dreams/{dream}.md",
                                 f"_bmad-output/projects/{slug}",
                                 f"presentations/{slug}",
                                 f"src/shared/packages/{slug}"])
        age = ""
        if updated:
            try:
                y, m, d = (int(x) for x in updated.split("-"))
                age = (today - date(y, m, d)).days
            except ValueError:
                age = ""
        # story progress when this project is a wired build line
        prog = ""
        pkey = {"pyforge-herald": "herald", "pyforge-doctor": "doctor",
                "pyforge-scribe": "scribe", "pyforge-warden": "warden",
                "pyforge-atlas": "atlas", "pyforge-marshal": "marshal",
                "pyforge-mason": "mason", "pyforge-steward": "steward",
                "pyforge-genesis": "genesis"}.get(slug)
        if pkey and pkey in projects:
            st = [s for e in projects[pkey]["epics"] for s in e["stories"]]
            prog = f"{sum(1 for s in st if s[1] == 'done')}/{len(st)}"
        # F1 — a row whose stage dates do not ascend was BACKFILLED, not built out
        # of order. docs/dreams/README.md mandates it: "realized is not exempt from
        # the chain" — a Dream that shipped before the model existed gets its
        # PRD/spec retro-fitted. warden shipped from a 07-14 PRD, then got its Dream
        # 07-23 and its Spec 07-25. True history, previously invisible.
        seq = [stages[s] for s in FLEET_STAGES if stages[s]]
        backfilled = seq != sorted(seq)
        # F3 — the contract has unanswered questions while its decomposition
        # already exists. bmad-spec emits open_questions[] by design for gaps the
        # Dream could not resolve; research/PRD are what resolve them. Non-empty
        # here + PRD + architecture present = downstream has overtaken the Spec.
        open_q = _spec_open_questions(slug)
        overtaken = bool(open_q) and bool(stages["prd"]) and bool(stages["arch"])
        rows.append({"label": label, "slug": slug, "dream": dream, "stages": stages,
                     "backfilled": backfilled, "openQuestions": open_q,
                     "overtaken": overtaken,
                     "na": sorted(na), "furthest": furthest, "updated": updated,
                     "age": age, "stale": isinstance(age, int) and age > _STALE_DAYS,
                     "version": _pkg_version(slug), "progress": prog,
                     "complete": sum(1 for s in FLEET_STAGES if stages[s] or s in na),
                     "of": len(FLEET_STAGES)})
    full = sum(1 for r in rows if r["complete"] == r["of"])
    bf = [r["slug"] for r in rows if r["backfilled"]]
    ov = [f"{r['slug']}({r['openQuestions']})" for r in rows if r["overtaken"]]
    print(f"[fleet] {len(rows)} projects · {full} complete chains · "
          f"{sum(1 for r in rows if r['stale'])} stale (>{_STALE_DAYS}d)"
          + (f" · {len(bf)} backfilled: {', '.join(bf)}" if bf else "")
          + (f" · overtaken: {', '.join(ov)}" if ov else ""))
    return {"stages": list(FLEET_STAGES), "staleDays": _STALE_DAYS, "rows": rows}


# ---- pitch roster (the deck family) ------------------------------------------

PITCH_TITLES = {"agentic-sdlc": "Agentic AI across the SDLC"}
# the 6-artifact family standard, per docs/specs/presentation-deck.md
_PITCH_CHECK = ("prototype", "exec", "infographic", "marp", "standalone", "pptx")


def scan_pitch() -> list[dict]:
    cards: list[dict] = []
    for deck_dir in sorted((REPO_ROOT / "presentations").iterdir()):
        if not deck_dir.is_dir():
            continue
        slug = deck_dir.name
        proj, marp, pptx = deck_dir / "project", deck_dir / "src" / "marp", deck_dir / "src" / "pptx"
        names = [f.name for f in proj.glob("*.html")] if proj.is_dir() else []
        marp_md = list(marp.glob("*.md")) if marp.is_dir() else []
        pptx_files = list(pptx.glob("*.pptx")) if pptx.is_dir() else []
        have = {
            "prototype": any(n.endswith(".dc.html") and "Executive Summary" not in n
                             and "Infographic" not in n for n in names),
            "exec": any("Executive Summary" in n for n in names),
            "infographic": (any(n.endswith("- Infographic.dc.html") for n in names)
                            and any("Infographic Deck" in n for n in names)
                            and any("Infographic standalone" in n for n in names)),
            "marp": len(marp_md) >= 3,
            "standalone": bool(list(marp.glob("*standalone*.html"))) if marp.is_dir() else False,
            "pptx": len(pptx_files) >= 2,
        }
        dates = re.findall(r"(\d{4}-\d{2}-\d{2})", " ".join(f.name for f in pptx_files))
        title = PITCH_TITLES.get(slug) or "PyForge " + slug.removeprefix("pyforge-").capitalize()
        cards.append({"slug": slug, "title": title, "have": have,
                      "n": sum(have.values()), "of": len(_PITCH_CHECK),
                      "export": max(dates) if dates else "",
                      "path": f"presentations/{slug}"})
    full = sum(1 for c in cards if c["n"] == c["of"])
    print(f"[pitch] {len(cards)} decks scanned ({full} with the full family)")
    return cards


# ---- archived (absorbed / retired / terminal / blocked) ----------------------

# Archived is driven ENTIRELY by Dream frontmatter (`status: archived` +
# `archived-reason:`) — the former hardcoded ARCHIVED_SEED list was retired
# 2026-07-25 when its five entries became real archived Dreams. One source of
# truth: a thing cannot be archived on the board without being archived in its
# Dream, which is what let Sentinel render as a live backlog Dream AND an
# archived entry simultaneously.


def build_archived(dreams: list[dict]) -> list[dict]:
    """Every Dream frontmatter-marked `status: archived`."""
    out: list[dict] = []
    for d in dreams:
        if d["status"] == "archived":
            out.append({"name": d["title"],
                        "reason": d.get("archived_reason") or "retired",
                        "owner": d.get("owner", ""),
                        "note": d["title"],
                        "link": f"docs/dreams/{d['slug']}.md"})
    by_reason: dict[str, int] = {}
    for e in out:
        by_reason[e["reason"]] = by_reason.get(e["reason"], 0) + 1
    print(f"[archived] {len(out)} entries — "
          + " / ".join(f"{v} {k}" for k, v in sorted(by_reason.items())))
    return out


# ---- the Guild (every station, every Dream it owns) -------------------------

def scan_guild(dreams: list[dict], projects: dict | None = None,
               backlog: dict | None = None) -> dict:
    """One row per Smith — all eight, always, including empty ones.

    Grouping by station is the accountability view the `owner:` through-line
    exists for: "what is Atlas answerable for, and where does each piece stand?"
    Every station renders even at zero, so a thin station is VISIBLE rather than
    merely absent (Warden and Doctor own one Dream each; Marshal owns six).

    The Charter is NOT a ninth row. It constitutes the Guild, so it sits above
    the roster, not beside it — `guild` is not a station.
    """
    rows = []
    for st in STATIONS:
        mine = [d for d in dreams if d.get("owner") == st]
        counts = {s: sum(1 for d in mine if d["status"] == s and d.get("type") != "practice")
                  for s in DREAM_STATUSES}
        counts["practice"] = sum(1 for d in mine if d.get("type") == "practice")
        # G1 — what this station is actually DOING. The Guild counted Dreams and
        # said nothing about activity: a station could own four Dreams and have
        # nothing running. Derived from the build lines, never declared.
        line = ""
        for key, proj in (projects or {}).items():
            if proj.get("owner") != st or proj.get("practice"):
                continue
            ls = proj.get("lineState") or {}
            state, at = ls.get("state", ""), ls.get("at", "")
            cand = f"{state} {at}".strip()
            # a live/paused line outranks a complete one for display
            if state in ("in flight", "paused") or not line:
                line = cand
        # G2 — backlog load. Makes a thin station meaningful: warden owns one
        # Dream AND has zero pending, which is a different fact from being small.
        load = ((backlog or {}).get("byOwner") or {}).get(st, 0)
        blocked = sum(1 for r in (backlog or {}).get("rows", [])
                      if r.get("owner") == st and r.get("blockedOn"))
        rows.append({
            "station": st, "total": len(mine), "counts": counts,
            "line": line, "load": load, "blocked": blocked,
            "dreams": [{"slug": d["slug"], "title": d["title"], "status": d["status"],
                        "type": d.get("type", "dream"),
                        "blockedOn": d.get("blockedOn", "")}
                       for d in sorted(mine, key=lambda x: (x["status"], x["slug"]))],
        })
    constitutive = [{"slug": d["slug"], "title": d["title"], "status": d["status"]}
                    for d in dreams if d.get("owner") == "guild"]
    idle = [r["station"] for r in rows if not r["line"] and not r["load"]]
    print(f"[guild] {sum(r['total'] for r in rows)} dreams across {len(rows)} stations"
          f" · {len(constitutive)} constitutive"
          + (f" · idle (no line, no backlog): {', '.join(idle)}" if idle else ""))
    # `practice` sits with the ACTIVE states, before `archived` — archived is the
    # terminal state and belongs last. A practice is tended, not ended.
    order = [s for s in DREAM_STATUSES if s != "archived"] + ["practice", "archived"]
    return {"stations": list(STATIONS), "order": order,
            "rows": rows, "constitutive": constitutive}


# ---- backlog (what a station owns that is not building and not done) --------

def scan_backlog(dreams: list[dict], projects: dict) -> dict:
    """Dreams a station owns that are neither building nor finished.

    The naive definition — "not in Realized and not In Build" — does NOT hold,
    because those two sections are driven by the 6 wired build lines, not by the
    26 Dreams. It swept in 7 realized-but-never-a-build-line Dreams
    (factory-console, modernist-identity, design-code-bridge, ...), every future
    `archived` one, and the perpetual practices. Bucketing off the Dream's OWN
    lifecycle is total and non-overlapping instead:

      dreamt / pitched / specified  -> backlog, UNLESS a build line exists
      realized                      -> Realized
      archived                      -> Archived
      type: practice                -> neither (tended, never finished)

    `blocked-on:` splits backlog into WAITING vs AVAILABLE — backlog implies
    pickup-ready, and work held on an external gate is not.
    """
    building = {PROGRAM_DREAM[k] for k, v in projects.items()
                if k in PROGRAM_DREAM and (v.get("lineState") or {}).get("state")
                in ("in flight", "paused")}
    rows = []
    for d in dreams:
        if d.get("type") == "practice" or d["status"] in ("realized", "archived"):
            continue
        if d.get("owner") == "guild":
            continue          # constitutive — not any station's pending work
        if d["slug"] in building:
            continue
        rows.append({"slug": d["slug"], "title": d["title"], "status": d["status"],
                     "owner": d["owner"], "blockedOn": d.get("blockedOn", ""),
                     "chain": d.get("chain", {})})
    order = {s: i for i, s in enumerate(DREAM_STATUSES)}
    rows.sort(key=lambda r: (bool(r["blockedOn"]), order.get(r["status"], 9), r["slug"]))
    blocked = sum(1 for r in rows if r["blockedOn"])
    by_owner: dict[str, int] = {}
    for r in rows:
        by_owner[r["owner"]] = by_owner.get(r["owner"], 0) + 1
    practices = [{"slug": d["slug"], "title": d["title"], "owner": d["owner"],
                  "status": d["status"]} for d in dreams if d.get("type") == "practice"]
    print(f"[backlog] {len(rows)} open ({len(rows) - blocked} available / {blocked} blocked)"
          f" · {len(practices)} standing practices")
    return {"rows": rows, "blocked": blocked, "byOwner": by_owner, "practices": practices}


# ---- station ownership (the Dream -> code through-line) ----------------------

# Console program key -> the Dream whose owner is accountable for that build line.
PROGRAM_DREAM = {"warden": "pyforge-warden", "atlas": "pyforge-atlas",
                 "herald": "pyforge-herald", "doctor": "pyforge-doctor",
                 "scribe": "pyforge-scribe", "regen": "regenerable-factory",
                 "marshal": "pyforge-marshal", "mason": "pyforge-mason",
                 "steward": "pyforge-steward", "genesis": "pyforge-genesis"}


def apply_owner(data: dict) -> None:
    """Stamp `owner` (the accountable station) onto every downstream row.

    The Charter's rule is that a Dream becomes code THROUGH a Smith, so the
    owner is not a label on Tier 0 — it is the through-line. It was already
    authored on all 26 Dreams and then dropped: Fleet, In Build / Realized,
    Pitch and Archived each showed the same effort with no accountable post.
    One pass resolves them all from the Dream index, so the mapping lives in
    exactly one place (the Dream's frontmatter) and cannot drift per-section.
    """
    by_slug = {d["slug"]: d.get("owner", "") for d in data["dreams"]}
    # deck dir -> dream slug (the alias table runs the other way)
    deck_to_dream = {v: k for k, v in DREAM_DECK_ALIASES.items()}
    missing: list[str] = []

    for row in data["fleet"]["rows"]:                    # carries `dream` already
        row["owner"] = by_slug.get(row["dream"], "")
        if not row["owner"]:
            missing.append(f"fleet:{row['slug']}")

    by_type = {d["slug"]: d.get("type", "dream") for d in data["dreams"]}
    for key, proj in data["projects"].items():           # In Build / Realized
        dream = PROGRAM_DREAM.get(key, "")
        proj["owner"] = by_slug.get(dream, "")
        # A line whose Dream is a PRACTICE is not a product line: it is a
        # standing property tended forever (regenerable-factory's surface
        # manifests must claim every new file, permanently). It carries real
        # story history, so the data stays — the zones just don't show it as
        # something that shipped.
        proj["practice"] = by_type.get(dream) == "practice"
        if not proj["owner"]:
            missing.append(f"projects:{key}")

    for card in data["pitch"]:
        slug = card["slug"]
        card["owner"] = by_slug.get(slug) or by_slug.get(deck_to_dream.get(slug, ""), "")
        if not card["owner"]:
            missing.append(f"pitch:{slug}")

    for entry in data["archived"]:                       # seeds carry their own
        entry.setdefault("owner", "")
        if not entry["owner"]:
            missing.append(f"archived:{entry['name']}")

    # Campaigns are deliberately NOT owned: a campaign spans many stations
    # (spec-completion touched all eight), so a single owner would be a lie.
    owned = sum(1 for r in data["fleet"]["rows"] if r["owner"])
    print(f"[owner] {owned}/{len(data['fleet']['rows'])} fleet rows attributed"
          + (f" · UNOWNED: {', '.join(missing)}" if missing else " · all sections attributed"))


# ---- shared ------------------------------------------------------------------

def load_data() -> dict:
    inner = DATA_JS.read_text(encoding="utf-8").strip()
    inner = re.sub(r"^window\.DASHBOARD_DATA\s*=\s*", "", inner).rstrip().rstrip(";")
    return json.loads(inner)


def now_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--source", choices=["sprint-status", "git"], default="sprint-status",
        help="sprint-status (default, local, richest) | git (hands-off, CI, done-only)",
    )
    args = ap.parse_args()

    data = load_data()
    data["projects"] = scan_projects(data["projects"])
    check_project_coverage(data["projects"])
    if args.source == "git":
        apply_git(data["projects"])
    else:
        apply_sprint_status(data["projects"])
        apply_loop_inflight(data["projects"])
    data["dreams"] = scan_dreams()
    data["specs"] = scan_specs()
    data.pop("campaign", None)
    data.pop("campaign2", None)
    spec_c = scan_campaign()
    build_c = scan_impl_campaign(data["projects"])
    apply_line_state(data["projects"])
    data["health"] = scan_health()
    data["fleet"] = scan_fleet(data["projects"])
    data["campaigns"] = [
        {"id": "spec-completion-2026-07-25", "title": "Spec Completion",
         "kind": "planning", "status": "completed", "completed": "2026-07-25",
         "record": "_bmad-output/projects/local-recipes/planning-artifacts/campaign-spec-completion-2026-07-25.md",
         **spec_c},
        {"id": "build-2026-07-25", "title": "The Build", "kind": "build",
         "status": "active", **build_c},
    ]
    data["pitch"] = scan_pitch()
    data["archived"] = build_archived(data["dreams"])
    # apply_owner MUST precede scan_guild: the Guild's `building` column reads
    # proj["owner"], which apply_owner sets. Ordered the other way it silently
    # worked for pre-existing lines (their owner persisted in data.js from an
    # earlier run) and reported every NEW line as idle — caught when marshal /
    # mason / steward / genesis were added 2026-07-25.
    apply_owner(data)
    data["backlog"] = scan_backlog(data["dreams"], data["projects"])
    data["guild"] = scan_guild(data["dreams"], data["projects"], data["backlog"])

    ts = now_utc()
    data["snapshot"] = _SNAP_TS.sub(ts, data["snapshot"], count=1)
    DATA_JS.write_text(
        "window.DASHBOARD_DATA = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"\nsnapshot -> {ts}  ·  source: {args.source}  ·  data.js rewritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
