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
under `seeded`.

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
    "regen": "_bmad-output/projects/local-recipes/implementation-artifacts/sprint-status.yaml",
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
    done: dict[str, set[str]] = {"warden": set(), "atlas": set(), "regen": set()}
    for line in log.splitlines():
        m = _WARDEN_DONE.search(line)
        if m:
            done["warden"].add(m.group(1).replace("-", "."))  # 6-1 -> 6.1
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
DREAM_STATUSES = ("seeded", "in-deck", "in-spec", "realized", "archived")


# Deck dirs whose name differs from the dream slug (mason's chapter deck backs
# the packaging-factory dream, etc.).
DREAM_DECK_ALIASES = {
    "packaging-factory": "pyforge-mason",
    "agentic-sdlc-autonomy": "agentic-sdlc",
    "ecosystem-crew": "pyforge-genesis",   # the master vision deck
}
# Dreams whose build runs as a console program (chip shows live done/total).
DREAM_PROGRAM = {
    "pyforge-warden": "warden",
    "pyforge-atlas": "atlas",
    "regenerable-factory": "regen",
}


def dream_chain(slug: str) -> dict:
    """Chain links for the drill-through indicators (no-straggler visibility):
    deck dir (exact slug or alias), spec-kernel folder, BMAD project dir,
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
        if status not in DREAM_STATUSES:
            print(f"[dreams] WARN {f.name}: status {status!r} not in {DREAM_STATUSES}"
                  " — passed through; board shows it under 'seeded'")
        if not owner:
            print(f"[dreams] WARN {f.name}: no owner: in frontmatter")
        dream = {"slug": f.stem, "title": title or f.stem,
                 "status": status or "", "owner": owner or "",
                 "chain": dream_chain(f.stem)}
        if archived_reason:
            dream["archived_reason"] = archived_reason
        dreams.append(dream)
    by_status = {s: sum(1 for d in dreams if d["status"] == s) for s in DREAM_STATUSES}
    print(f"[dreams] {len(dreams)} scanned: "
          + " / ".join(f"{n} {s}" for s, n in by_status.items()))
    return dreams


# ---- specs roster (all BMAD kernels; docs/specs legacy is deliberately out) --

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
    print(f"[specs] {len(rows)} kernels scanned "
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
    {"wave": "2a", "slug": "presenton-pixi-image", "model": "sonnet", "depth": "epics",    "state": "queued"},
    {"wave": "2b", "slug": "wasm-analytics-stack", "model": "sonnet", "depth": "prd+arch", "state": "queued"},
    {"wave": "2c", "slug": "unity-data-stack",     "model": "opus",   "depth": "prd+arch", "state": "queued"},
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

ARCHIVED_SEED = [
    {"name": "Sentinel — knowledge-graph persona", "reason": "absorbed",
     "note": "charter absorbed into Scribe ('the graph is the product')",
     "link": "docs/dreams/pyforge-scribe.md"},
    {"name": "microsoft-conda-forge sweep", "reason": "absorbed",
     "note": "absorbed as trendshift Track B (the June 2026 org audit)",
     "link": "docs/specs/trendshift-conda-forge.md"},
    {"name": "claude.ai Artifact console", "reason": "retired",
     "note": "replaced by this GitHub Pages console (2026-07)",
     "link": "docs/dashboard"},
    {"name": "DB-GPT conda-forge effort", "reason": "terminal",
     "note": "delivered externally via staged-recipes #33883 (consume-not-submit, G58)",
     "link": "docs/specs/db-gpt-conda-forge.md"},
    {"name": "copilot-cli recipe", "reason": "blocked",
     "note": "LICENSE §2 standalone-redistribution clause — staged-recipes #32522 rejected",
     "link": "recipes/copilot-cli"},
]


def build_archived(dreams: list[dict]) -> list[dict]:
    """Seeded cases + any Dream frontmatter-marked `status: archived`."""
    out = [dict(e) for e in ARCHIVED_SEED]
    for d in dreams:
        if d["status"] == "archived":
            out.append({"name": d["title"],
                        "reason": d.get("archived_reason") or "retired",
                        "note": "archived via docs/dreams frontmatter",
                        "link": f"docs/dreams/{d['slug']}.md"})
    print(f"[archived] {len(out)} entries ({len(out) - len(ARCHIVED_SEED)} from frontmatter)")
    return out


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
    if args.source == "git":
        apply_git(data["projects"])
    else:
        apply_sprint_status(data["projects"])
    data["dreams"] = scan_dreams()
    data["specs"] = scan_specs()
    data["campaign"] = scan_campaign()
    data["pitch"] = scan_pitch()
    data["archived"] = build_archived(data["dreams"])

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
