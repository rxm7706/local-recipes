#!/usr/bin/env python3
"""Detector: a station's board tells the truth about what it owns and what it has done.

Three invariants, each written for a failure that actually happened on 2026-08-08 and
that **no existing detector caught** — every one needed a human to look at the board and
ask a question:

  INV-A  every OPEN Spec a station owns is DECOMPOSED into that station's chain
         (its slug appears in the project's PRD or epics), or is explicitly registered
         as deferred with a reason.
         → Marshal's PRD decomposed 2 of its 24 Specs. Steward rendered 18/18 · 100%
           while owning three undecomposed draft Specs. Both invisible.

  INV-B  a project's epics.md story ids and its tracked ledger's story keys are the
         SAME SET, both directions.
         → Doctor rendered `complete 16/16` while carrying a story that existed in
           epics.md with no ledger key, so the 100% was computed over a set that
           excluded it.

  INV-C  the Guildhall's build line for a station equals that station's ledger.
         → Herald rendered 12/19 while its ledger held 47/47, because data.js's
           hand-curated epics array described a different effort entirely (zero id
           overlap). `scan_projects` only ever UPGRADES a curated line, so it could
           never self-heal.

**Why these three together.** Each answers a different question a reader of the board is
entitled to ask: *is everything this station owns on its plan* (A), *does its plan match
its record* (B), and *does the wall match the record* (C). A station can pass any two and
still publish a lie.

Deliberately stdlib + PyYAML only, so it runs in bare CI like the other repo-scope
detectors. INV-C degrades to a skip when data.js is unreadable rather than failing the
run — it is the one input that is generated rather than authored.
"""

from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: reads tracked files only.
DETECTOR = {"scope": "repo"}

import argparse
import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "_bmad-output" / "projects"
DATA_JS = ROOT / "docs" / "dashboard" / "data.js"
DATA_JS_PREFIX = "window.DASHBOARD_DATA = "

#: Spec statuses that represent work still owed. `shipped`/`archived`/`superseded` are
#: settled and need no decomposition; a `pitched` practice is a standing position with
#: nothing to decompose by definition (Charter — a practice is never finished).
OPEN_SPEC_STATUSES = frozenset({"draft", "ready", "in-progress"})

#: Specs deliberately NOT decomposed, each with the reason it is exempt. An entry here is
#: a recorded decision, not a silence — which is the whole point: the detector's job is to
#: make "we chose not to" distinguishable from "nobody noticed".
DEFERRED_SPECS: dict[str, str] = {
    "spec-agentic-sdlc-autonomy":
        "a standing position, explicitly 'not a deliverable' by its own text — "
        "there is nothing to decompose and an FR would manufacture one",
    "spec-herald-moments-2-4-live-backend":
        "archive-leaning by its OWN first open question ('is there real pull for this at "
        "all?'), and it names a hard prerequisite — replacing state.py's unlocked "
        "read-modify-write — that blocks it regardless. Decomposing it would commit the "
        "station to work its own Spec doubts. Revisit when the premise is settled",
    "spec-conda-forge-expert-rebuild":
        "feasibility unresolved: its own open questions ask whether skf-create-skill can "
        "drive code-scale compilation (~41K LOC / 67 scripts) at all, versus knowledge-"
        "layer content. Its Spec scopes to ONE pilot slice with an explicit re-scope "
        "gate; decomposing the whole rebuild before that spike would plan work nobody "
        "has shown is possible",
}


def frontmatter(path: pathlib.Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return {}
        return yaml.safe_load(text.split("---")[1]) or {}
    except Exception:
        return {}


def _norm_id(token: str) -> str:
    """One normal form for a story id, across both shapes this repo uses.

    Marshal/doctor/warden key stories `1.1`; atlas keys them by WAVE — `A1`, `B10`,
    `I0` — with the numeric form in parentheses (`### Story A1 (2.1):`), because its
    completion signal is a `story(A1)` commit subject rather than a bmad-loop merge.
    Both are legitimate; a detector that understands only one reports the other as
    unmeasurable, which is what the first cut of this module did.
    """
    return token.strip().lower().replace(".", "-")


def _story_ids_from_epics(path: pathlib.Path) -> list[set[str]]:
    """One id-SET per story — every id a `### Story` heading declares for it.

    Atlas writes a DUAL id: `### Story I0 (10.1): Restore atlas dependency-completeness`
    declares both the wave id `i0` and the numeric `10-1`, and its ledger keys on the
    numeric one for Epic 10 while keying on the wave one for Waves A-H. Both are that
    story's id. Matching on only the first token reported six phantom orphans in each
    direction — the same story counted as missing twice, once under each name.

    Returning a set per story rather than one flat set is what lets INV-B ask "is ANY
    of this story's ids in the ledger?", which is the actual question.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out: list[set[str]] = []
    for m in re.finditer(r"^###\s+Story\s+([A-Za-z0-9.]+)(?:\s*\(([A-Za-z0-9.]+)\))?",
                         text, re.MULTILINE):
        ids = {_norm_id(m.group(1))}
        if m.group(2):
            ids.add(_norm_id(m.group(2)))
        out.append(ids)
    return out


def _ledger_rows(path: pathlib.Path) -> dict[str, str]:
    """Every `key: value` under `development_status:`, epic rollups included.

    Deliberately shape-agnostic. Atlas keys on `a1-scaffold-…`/`b2-…` alongside
    `10-1-…` BY DESIGN (their completion signal is a `story(A1)` commit subject rather
    than a bmad-loop merge), so any parser that assumes `<int>-<int>` under-counts that
    station. That exact assumption produced three false findings in one day, one of
    which shipped and had to be retracted — hence this function, and hence INV-C
    counting rows rather than parsing ids.
    """
    out: dict[str, str] = {}
    in_block = False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for raw in text.splitlines():
        if raw.startswith("development_status:"):
            in_block = True
            continue
        if not in_block:
            continue
        if raw and not raw.startswith((" ", "\t")):
            break
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


#: A ledger story key's leading id, in either shape: `1-1-package-spine…` -> `1-1`,
#: `10-6-make-run-admission…` -> `10-6`, `a1-scaffold-the-kedro…` -> `a1`.
_LEDGER_ID = re.compile(r"^(\d+-\d+|[a-z]+\d+)-")


def _ledger_story_ids(rows: dict[str, str]) -> tuple[set[str], set[str]]:
    """`(recognised ids, unrecognised keys)`. An unrecognised key is REPORTED rather
    than dropped — silently ignoring a key it cannot parse is how a detector claims a
    clean set it never actually compared."""
    ids, unknown = set(), set()
    for key in rows:
        m = _LEDGER_ID.match(key)
        (ids.add(_norm_id(m.group(1))) if m else unknown.add(key))
    return ids, unknown


def _story_keys_from_ledger(path: pathlib.Path) -> set[str]:
    """Retained for INV-B's numeric comparison; see `_numeric_story_ids`."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    out: set[str] = set()
    in_block = False
    for raw in text.splitlines():
        if raw.startswith("development_status:"):
            in_block = True
            continue
        if not in_block:
            continue
        if raw and not raw.startswith((" ", "\t")):
            break
        m = re.match(r"^\s+(\d+)-(\d+)-", raw)
        if m:
            out.add(f"{m.group(1)}.{m.group(2)}")
    return out


def _canonical_epics(project_dir: pathlib.Path) -> pathlib.Path | None:
    """The one epics doc declaring `epics_role: canonical` (AD-72); falls back to
    `epics.md` for a project predating the convention."""
    pa = project_dir / "planning-artifacts"
    for candidate in sorted(pa.glob("epics*.md")):
        if frontmatter(candidate).get("epics_role") == "canonical":
            return candidate
    fallback = pa / "epics.md"
    return fallback if fallback.is_file() else None


def _board_lines() -> dict[str, tuple[int, int]] | None:
    """`{station: (done, total)}` from data.js, or None when it cannot be read."""
    try:
        text = DATA_JS.read_text(encoding="utf-8")
        if not text.startswith(DATA_JS_PREFIX):
            return None
        data = json.loads(text[len(DATA_JS_PREFIX):].rstrip().rstrip(";"))
    except Exception:
        return None
    out: dict[str, tuple[int, int]] = {}
    for key, proj in (data.get("projects") or {}).items():
        epics = proj.get("epics")
        if not epics:
            continue
        stories = [s for e in epics for s in (e.get("stories") or [])]
        done = sum(1 for s in stories if len(s) > 1 and s[1] == "done")
        out[key] = (done, len(stories))
    return out


def check() -> list[dict]:
    findings: list[dict] = []
    board = _board_lines()

    for project_dir in sorted(PROJECTS.iterdir()):
        if not (project_dir / "planning-artifacts").is_dir():
            continue
        project = project_dir.name
        station = project.removeprefix("pyforge-")
        pa = project_dir / "planning-artifacts"

        # ---- INV-A: every open Spec is decomposed ---------------------------------
        prose = ""
        for doc in list(pa.glob("prds/*/prd.md")) + list(pa.glob("epics*.md")):
            try:
                prose += doc.read_text(encoding="utf-8")
            except OSError:
                continue
        for spec_md in sorted(pa.glob("specs/spec-*/SPEC.md")):
            slug = spec_md.parent.name
            status = str(frontmatter(spec_md).get("status", "")).strip()
            if status not in OPEN_SPEC_STATUSES or slug in DEFERRED_SPECS:
                continue
            bare = slug.removeprefix("spec-")
            if bare not in prose and slug not in prose:
                findings.append({
                    "inv": "INV-A", "kind": "spec-not-decomposed",
                    "project": project, "subject": slug, "status": status,
                    "detail": (f"{station} owns an open Spec ({status}) that no FR or epic "
                               f"references — the station can render 100% while owing it"),
                    "remedy": (f"decompose {slug} into {project}'s PRD + epics, or add it "
                               f"to DEFERRED_SPECS with the reason"),
                })

        # ---- INV-B: epics.md set == ledger set ------------------------------------
        epics_md = _canonical_epics(project_dir)
        ledger = pa / "sprint-status-ledger.yaml"
        rows = _ledger_rows(ledger) if ledger.is_file() else {}
        story_rows = {k: v for k, v in rows.items() if not k.startswith("epic-")}
        led, unparsed = _ledger_story_ids(story_rows)

        if epics_md and unparsed:
            findings.append({
                "inv": "INV-B", "kind": "unparseable-ledger-key",
                "project": project, "subject": f"{len(unparsed)} key(s)",
                "status": ", ".join(sorted(unparsed)[:6]),
                "detail": ("no recognisable story id — reported rather than dropped, "
                           "because silently skipping a key is how a detector claims a "
                           "clean set it never compared"),
                "remedy": "rename to <epic>-<seq>-… or <wave><n>-…, or retire the key",
            })
        if epics_md and story_rows and not _story_ids_from_epics(epics_md):
            findings.append({
                "inv": "INV-D", "kind": "canonical-epics-declares-no-stories",
                "project": project, "subject": epics_md.name,
                "status": f"0 `### Story` headings vs {len(story_rows)} ledger key(s)",
                "detail": ("the canonical epics doc declares NO stories in the shape every "
                           "other station uses, so INV-B has nothing to compare and would "
                           "silently pass — an empty set trivially matches nothing"),
                "remedy": ("rewrite as `## Epic N: Title` + `### Story <id>: Title`, "
                           "covering every ledger story"),
            })
        if epics_md and story_rows:
            ep_sets = _story_ids_from_epics(epics_md)
            ep_all = {i for s in ep_sets for i in s}
            if ep_sets and led:
                # A story is covered if ANY of its declared ids is in the ledger; a
                # ledger key is covered if it matches any declared id.
                only_epics = sorted(next(iter(sorted(s))) for s in ep_sets if not (s & led))
                only_ledger = sorted(led - ep_all)
                if only_epics:
                    findings.append({
                        "inv": "INV-B", "kind": "story-without-ledger-key",
                        "project": project, "subject": f"{len(only_epics)} story(ies)",
                        "status": ", ".join(only_epics[:10]),
                        "detail": ("in epics.md with no ledger key — the board's percentage "
                                   "is computed over a set that excludes them"),
                        "remedy": f"add them to {project}'s Tier-3 feed, then sprint-ledger-sync",
                    })
                if only_ledger:
                    findings.append({
                        "inv": "INV-B", "kind": "ledger-key-without-story",
                        "project": project, "subject": f"{len(only_ledger)} key(s)",
                        "status": ", ".join(only_ledger[:10]),
                        "detail": "in the ledger with no epics.md story — an untraceable row",
                        "remedy": f"add the story to {epics_md.name}, or retire the key",
                    })

        # ---- INV-C: board line == ledger ------------------------------------------
        if board is not None and station in board and story_rows:
            b_done, b_total = board[station]
            l_done = sum(1 for v in story_rows.values() if v == "done")
            if (b_total, b_done) != (len(story_rows), l_done):
                findings.append({
                    "inv": "INV-C", "kind": "board-diverges-from-ledger",
                    "project": project, "subject": station,
                    "status": f"board {b_done}/{b_total} vs ledger {l_done}/{len(story_rows)}",
                    "detail": ("the Guildhall renders a different story set than the "
                               "durable record; scan_projects only UPGRADES a curated "
                               "line, so this cannot self-heal"),
                    "remedy": "rebuild the station's data.js epics array from its ledger",
                })
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="chain-completeness-check",
        description="Every open Spec is decomposed; epics, ledger and board agree.",
    )
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--inv", choices=("INV-A", "INV-B", "INV-C", "INV-D"),
                    help="report only one invariant")
    args = ap.parse_args(argv)

    findings = [f for f in check() if not args.inv or f["inv"] == args.inv]

    if args.json:
        print(json.dumps({"findings": findings}, indent=2))
        return 1 if findings else 0

    projects = len([p for p in PROJECTS.iterdir()
                    if (p / "planning-artifacts").is_dir()]) if PROJECTS.is_dir() else 0
    print(f"chain completeness — {projects} project(s)")
    if not findings:
        print("\nOK: every open Spec is decomposed, and epics, ledger and board agree.")
        return 0

    by_inv: dict[str, list[dict]] = {}
    for f in findings:
        by_inv.setdefault(f["inv"], []).append(f)
    for inv in sorted(by_inv):
        print(f"\n{inv} ({len(by_inv[inv])}):")
        for f in by_inv[inv]:
            print(f"  ✗ [{f['kind']}] {f['project']}: {f['subject']}")
            if f["status"]:
                print(f"      {f['status']}")
            print(f"      {f['detail']}")
            print(f"      → {f['remedy']}")
    print(f"\nINCOMPLETE: {len(findings)} finding(s). A station that renders a percentage "
          f"is claiming its plan is complete; these are the places that is not true.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
