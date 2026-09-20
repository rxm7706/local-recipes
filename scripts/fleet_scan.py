#!/usr/bin/env python3
"""Fleet/chain/sprint parsers extracted from the retired Guildhall generator.

Steward Story 30.2 deleted ``docs/dashboard/generate.py``. Chain-layers audit,
sprint-ledger sync, and marshal land/deploy still need the parsers. The
``data.js`` write CLI is retired — ``main()`` exits nonzero.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import tomllib

# PROJECT_SOURCES (dashboard project-key -> its sprint-status.yaml) is DERIVED
# below, once resolve_project() exists -- see "one resolver, one override
# table" after REPO_ROOT is defined.

# git-history DONE detection (used by --source git). Verified against main's subjects.
MAIN_BRANCH = "main"
# bmad-loop merge commits `Merge bmad-loop/<run-id>/<X-Y>-<slug> into <target> …`.
# Numeric story keys COLLIDE across loop-driven projects (warden 1-1 vs herald 1-1),
# so attribution is by the merge TARGET branch when present: loop/pyforge-herald ->
# herald, etc. Bare/legacy matches (warden's epic-tail branches) default to warden.
_LOOP_DONE = re.compile(r"Merge bmad-loop/[^/]+/(\d+-\d+)-\S*(?:\s+into\s+(\S+))?")
# Attribution is DERIVED from the merge target: `loop/pyforge-<slug>` -> `<slug>`.
# It used to be a hardcoded 5-entry tuple with a blanket `warden` fallback, which
# failed the moment a new smith existed: marshal's Story 1.1 merged into
# loop/pyforge-marshal, matched nothing, and was silently CREDITED TO WARDEN —
# so marshal read 0/41 on the published board while reading 1/41 locally.
# A stray `claude/pdos-1-3-…` branch was being credited to warden the same way.
# Deriving the slug means a new loop home needs no edit here; an unrecognised
# target now WARNS and is skipped rather than being charged to warden.
# Deliberately `[a-z0-9]+` (NO hyphen): project slugs are single words, and the
# target may carry a suffix — `loop/pyforge-marshal` -> marshal, but also
# `pyforge-warden-loop-policy-tiering` -> warden. Allowing hyphens captured the
# whole tail, matched no project, and silently dropped 10 real warden stories.
_LOOP_TARGET_SLUG = re.compile(r"pyforge-([a-z0-9]+)")
# Legacy subjects that predate the loop/pyforge-<slug> convention.
# `claude/pdos-*` is warden's pre-rename Epic-1 branch family (pdos = the project's
# earlier name); its stories are warden's.
_LOOP_TARGET_LEGACY = (("warden-epic", "warden"), ("claude/pdos", "warden"))
# A story can also land as a plain PR MERGE rather than a bmad-loop merge — those
# subjects never match _LOOP_DONE, which is why warden 1.2/1.3/1.4 read pending on
# the published board while reading done locally. Two shapes exist on main:
#   Merge pull request #53 from rxm7706/claude/pdos-1-2-interfaces-null-engine
#   Merge pull request #115 from rxm7706/build/pyforge-doctor-1-1
_PR_BUILD_DONE = re.compile(r"Merge pull request #\d+ from \S+/build/pyforge-([a-z0-9]+)-(\d+)-(\d+)")
_PR_PDOS_DONE = re.compile(r"Merge pull request #\d+ from \S+/claude/pdos-(\d+)-(\d+)")
# RETIRED convention, warden-only: warden's Epic-1 landed as bare `story N.N: …`
# subjects before any loop/PR branch convention existed. All six such subjects on
# main are warden's (1.1–1.4); nothing else has ever used the form, and current
# work uses the loop/build shapes above. Anchored to start-of-subject so it cannot
# match prose mid-line. Distinct from _ATLAS_STORY, which requires parens: story(A1).
# If a future project adopts a bare `story N.N:` subject it WILL be miscredited to
# warden — the durable fix is a tracked done-manifest, not another regex.
_WARDEN_LEGACY_STORY = re.compile(r"^story (\d+\.\d+):")
# PROJECT-QUALIFIED story subjects — the safe form, because the prefix names its
# own project(s) and every token is validated against the LIVE project set, so an
# unknown prefix is ignored rather than misattributed. Covers both shapes on main:
#   pyforge-warden: story 6.10 decision record — …      (single, optional prefix)
#   mason + steward: Story 1.1 — two stations reach code (MULTI-project, `+`-joined)
# The multi form is why mason and steward read 0 on the published board: their only
# completion signal names two projects at once and matched no single-project regex.
_QUALIFIED_STORY = re.compile(r"^([a-z0-9 +\-]+?):\s*story\s+(\d+\.\d+)\b", re.IGNORECASE)
# Atlas: most stories land as `story(A1)` / `story(B10)` / `story(0.1)`; the Wave
# G/H tail uses bare `GN:` / `HN:` subjects instead.
_ATLAS_STORY = re.compile(r"story\((\w[\w.]*)\)")
_ATLAS_GH = re.compile(r"\b([GH]\d+):")
# Regenerable-factory program: per-story commits `rf(<id>): …` on main.

def _discover_repo_root() -> Path:
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / "pixi.toml").is_file() and (ancestor / "docs" / "dreams").is_dir():
            return ancestor
    if here.parent.name == "scripts":
        return here.parent.parent
    return here.parent  # fixture / non-checkout load; callers overwrite REPO_ROOT


HERE = Path(__file__).resolve().parent
REPO_ROOT = _discover_repo_root()
DATA_JS = REPO_ROOT / "docs" / "dashboard" / "data.js"  # retired; writers unused

sys.path.insert(0, str(REPO_ROOT / "scripts"))

_ENTRY = re.compile(r"^\s{2}(?P<key>[^:#\s][^:]*?):\s*(?P<val>[a-z][a-z-]*)\s*(#.*)?$")
_SNAP_TS = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC")


# ---- project resolution: one resolver, one override table -------------------
#
# A roster/campaign slug ("marshal", "presenton-pixi-image", "pyforge-genesis")
# maps to its real `_bmad-output/projects/<dir>` tree -- or explicitly to NO
# tree -- through exactly ONE function, resolve_project(), backed by exactly
# ONE hand-authored table, _PROJECT_OVERRIDES. Everything that used to build
# that path itself (the old PROJECT_SOURCES literal, five independent
# `_KEY_SLUG_OVERRIDE.get(key, f"pyforge-{key}")` call sites,
# CAMPAIGN_PROJECT_OVERRIDE, IMPL_CAMPAIGN's per-entry `epics_path`,
# IMPL_CAMPAIGN_LEDGER) now derives from this instead. Five independent
# hand-authored mechanisms, each with its own patch for the slug != directory
# cases, is how two real bugs shipped (see spec-16-1-one-resolver-derived-
# sources-loud-failures and spec-dashboard-project-path-derivation).
@dataclass(frozen=True)
class ProjectResolution:
    project_dir: str | None         # e.g. "pyforge-marshal"; None = no tree (dissolved)
    epics_path: str | None          # repo-relative; None = no epics.md for this slug
    sprint_status_path: str | None  # Tier-3 gitignored; existence checked lazily by callers
    ledger_path: str | None         # tracked planning-artifacts/sprint-status-ledger.yaml
    redirect: str | None            # explicit link target, set only when project_dir is None


class UnresolvableProjectError(Exception):
    """Raised by resolve_project() for a slug with no override and no matching
    `_bmad-output/projects/<dir>` -- a loud failure (FR-143) instead of a
    silently wrong path."""

    def __init__(self, slug: str, guessed_dir: str) -> None:
        self.slug = slug
        super().__init__(
            f"cannot resolve project slug {slug!r}: no entry in _PROJECT_OVERRIDES "
            f"and no _bmad-output/projects/{guessed_dir}/ directory"
        )


# Dissolved/absorbed divergences ONLY -- every other slug derives its
# `_bmad-output/projects/<dir>` from the slug itself (see resolve_project()
# below). A future dissolution or absorption is a one-line addition here and
# nowhere else.
_PROJECT_OVERRIDES: dict[str, dict[str, object]] = {
    # Dissolved 2026-08-02: constitutive, ships no product, no project tree of
    # its own. Its two load-bearing specs live under docs/governance/, not a
    # planning-artifacts tree -- `have` stays all-False for it wherever this
    # table drives a chain-completeness check; only its LINK redirects.
    "pyforge-genesis": {"project_dir": None, "redirect": "docs/governance"},
    # Absorbed into pyforge-mason -- never had its own `_bmad-output/projects/`
    # tree. Its epics live inside mason's tree under a non-default filename,
    # and it has no sprint-status.yaml of its own (mason's own board entry
    # already covers mason's live feed) -- both overridden explicitly rather
    # than left to default-guess mason's paths as if they were this slug's.
    "presenton-pixi-image": {
        "project_dir": "pyforge-mason",
        "epics_path": "_bmad-output/projects/pyforge-mason/planning-artifacts/epics-presenton-pixi-image.md",
        # Not cleanly split from mason's own shared ledger (2026-08-08 note in
        # the old IMPL_CAMPAIGN_LEDGER) -- left on the IMPL_CAMPAIGN static
        # fallback rather than guessing a partition.
        "ledger_path": None,
        "sprint_status_path": None,
    },
    # Absorbed into pyforge-atlas. PRD+architecture only by design -- no
    # epics.md of their own yet, so both fold to explicit None rather than a
    # guessed (and wrong) `pyforge-atlas/planning-artifacts/epics.md`; no
    # sprint-status.yaml of their own either (atlas's own board entry already
    # covers atlas's live feed).
    "wasm-analytics-stack": {"project_dir": "pyforge-atlas", "epics_path": None,
                              "ledger_path": None, "sprint_status_path": None},
    "unity-data-stack": {"project_dir": "pyforge-atlas", "epics_path": None,
                          "ledger_path": None, "sprint_status_path": None},
}
_PROJECT_RESOLUTION_FIELDS = frozenset(
    {"project_dir", "epics_path", "sprint_status_path", "ledger_path", "redirect"})


def _validate_project_overrides(overrides: dict[str, dict[str, object]]) -> None:
    """Fail loud on a malformed `_PROJECT_OVERRIDES` entry -- a typo'd or
    missing key here would otherwise silently fall through to a wrong
    default (an omitted `project_dir` reads as `None`/dissolved; an unknown
    key is just ignored) instead of erroring on the authoring mistake."""
    for slug, override in overrides.items():
        if "project_dir" not in override:
            raise ValueError(f"_PROJECT_OVERRIDES[{slug!r}] omits required key 'project_dir'")
        unknown = set(override) - _PROJECT_RESOLUTION_FIELDS
        if unknown:
            raise ValueError(f"_PROJECT_OVERRIDES[{slug!r}] has unknown key(s): {sorted(unknown)}")
        if override["project_dir"] is None and not override.get("redirect"):
            raise ValueError(
                f"_PROJECT_OVERRIDES[{slug!r}] has project_dir=None but no redirect -- "
                "a dissolved slug with no tree must say where its link goes")


_validate_project_overrides(_PROJECT_OVERRIDES)


def resolve_project(slug: str) -> ProjectResolution:
    """The one place a roster/campaign slug becomes real filesystem state.

    Two paths:
    * `slug` is in `_PROJECT_OVERRIDES` -- the table is trusted as-authored,
      never re-verified against the filesystem. (This is what let the retired
      `regen` line keep rendering its frozen last-known state for the 11 days
      between its own project dir being retired and the line itself being
      pulled: an override is a human-declared fact, not a live probe.)
    * otherwise -- `project_dir` defaults to the slug itself if it already
      carries the `pyforge-` prefix, else `f"pyforge-{slug}"`, and THAT
      default must exist as a real `_bmad-output/projects/<dir>` or the slug
      is unresolvable (FR-143): no override to trust, and the naive guess
      does not correspond to anything real.

    The three derived paths (`epics_path`, `sprint_status_path`, `ledger_path`)
    default to the standard per-project layout under `project_dir`, or `None`
    when `project_dir` itself is `None`; any of the three can be overridden
    per-slug (explicit `None` included) via the same table entry.
    """
    override = _PROJECT_OVERRIDES.get(slug)
    if override is not None:
        project_dir = override.get("project_dir")
    else:
        project_dir = slug if slug.startswith("pyforge-") else f"pyforge-{slug}"
        if not (REPO_ROOT / "_bmad-output" / "projects" / project_dir).is_dir():
            raise UnresolvableProjectError(slug, project_dir)
        override = {}

    def _field(name: str, filename: str, base: str) -> str | None:
        if name in override:
            return override[name]  # type: ignore[return-value]
        if project_dir is None:
            return None
        return f"_bmad-output/projects/{project_dir}/{base}/{filename}"

    return ProjectResolution(
        project_dir=project_dir,
        epics_path=_field("epics_path", "epics.md", "planning-artifacts"),
        sprint_status_path=_field(
            "sprint_status_path", "sprint-status.yaml", "implementation-artifacts"),
        ledger_path=_field(
            "ledger_path", "sprint-status-ledger.yaml", "planning-artifacts"),
        redirect=override.get("redirect"),
    )


def _discovered_epics_files() -> list[Path]:
    """Every BMAD project with a tracked `epics.md` -- the CI-safe discovery
    basis (never depends on the gitignored Tier-3 `sprint-status.yaml`
    existing). Shared by `scan_projects()` (the board lines) and
    `PROJECT_SOURCES` (their sprint-status source) so the two key sets can
    never disagree."""
    return sorted((REPO_ROOT / "_bmad-output" / "projects").glob(
        "*/planning-artifacts/epics.md"))


def _discovered_board_keys() -> list[str]:
    """Bare dashboard keys (`marshal`, not `pyforge-marshal`) for every
    discovered project -- the input set `PROJECT_SOURCES` derives over.

    Two discovered directories stripping to the same bare key (e.g. a future
    non-`pyforge-`-prefixed sibling of an existing station) would otherwise
    silently clobber one another in the `PROJECT_SOURCES` dict comprehension
    below -- the exact silent-misrouting failure mode CAP-4 exists to turn
    loud, so this is checked here rather than left to a `dict` to swallow.
    """
    keys: list[str] = []
    seen: dict[str, str] = {}
    for ep in _discovered_epics_files():
        dir_name = ep.relative_to(REPO_ROOT / "_bmad-output" / "projects").parts[0]
        key = dir_name.removeprefix("pyforge-")
        if key in seen and seen[key] != dir_name:
            raise ValueError(
                f"project directories {seen[key]!r} and {dir_name!r} both derive "
                f"board key {key!r} -- add a _PROJECT_OVERRIDES entry to disambiguate")
        seen[key] = dir_name
        keys.append(key)
    return keys


# dashboard project-key -> its sprint-status.yaml (repo-root-relative) --
# DERIVED from resolve_project() over the discovered project set, not
# hand-declared: a new project with the standard layout appears here with
# zero edits the moment its epics.md lands (closes the TODO that used to sit
# here).
#
# resolve_project()'s default branch re-derives `pyforge-<key>` from the bare
# key _discovered_board_keys() strips -- round-tripping to the same directory
# this glob just found relies on every discovered directory actually being
# `pyforge-`-prefixed. That is a Charter-level constitutive naming rule for
# every Smith/station (see `docs/dreams/pyforge-charter.md` § Branding / § The
# Lexicon -- the canonical source; the retired project-context.md "Identity &
# Vocabulary" section was a mirror of it, never the original), not merely an
# assumption local to this file, so a directory that
# violated it would already be invalid elsewhere in the repo. If that rule
# is ever relaxed, resolve_project() would raise UnresolvableProjectError
# here at import time (before main()'s own try/except runs) -- still a loud,
# non-zero-exit failure naming the slug per FR-143, just via an uncaught
# traceback instead of the polished `[resolve] FAIL` message.
PROJECT_SOURCES: dict[str, str] = {
    key: resolve_project(key).sprint_status_path for key in _discovered_board_keys()
}


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
# Keys carried forward verbatim when a project's row is rebuilt. `sub` joined the
# list 2026-08-08: normalizing atlas made its story set derivable for the first
# time, so its row was rebuilt rather than preserved wholesale — and silently
# dropped a 1,200-character curated narrative (the Waves 0–H closeout, merged-PR
# citations, and the "Wave I is NOT part of the migration" distinction). Nothing
# regenerates prose like that; it is written once by a human and must survive
# every rebuild.
_EDITORIAL = ("label", "accentVar", "branch", "contract", "seglabels",
              "inflight", "velocity", "timing", "lineState", "sub", "roadmap")

# Both of these are now VESTIGIAL: generate.py's own logic reads
# `_PROJECT_OVERRIDES`/`resolve_project()` instead (see "one resolver, one
# override table" above). They stay present, unused internally, ONLY because
# `pyforge-doctor`'s `src/pyforge/doctor/sources/board.py` reads them by name
# via a dynamic `exec_module` of this file (out of this story's surface).
#
# Dashboard key -> BMAD project slug, where they differ. Empty since the `regen`
# line was retired (2026-08-08) -- every remaining key matches its project slug.
_KEY_SLUG_OVERRIDE: dict[str, str] = {}
# Lines whose story set is NOT its project's epics.md. Empty since `regen` retired;
# a future entry here means a line deliberately renders something other than its
# project's epics.
_DERIVE_EXCLUDE: set[str] = set()


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
    for ep in _discovered_epics_files():
        slug = ep.relative_to(REPO_ROOT / "_bmad-output" / "projects").parts[0]
        # No discovered project directory has a key override in
        # _PROJECT_OVERRIDES -- that table holds only DISSOLVED/ABSORBED
        # satellite slugs, which by definition never have their own epics.md
        # to be discovered here. The reverse (directory -> board key) is
        # therefore always the plain strip, not a resolve_project() lookup.
        key = slug.removeprefix("pyforge-")
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
        # Guard on STORIES, not just epics. pyforge-atlas parses to 10 epics with
        # ZERO stories because its story headings are `A1`/`B1`/`0.1`, not
        # `Story 1.1` — and a naive `if not epics` guard let that through and
        # silently overwrote 32 real stories. A project whose epics.md uses a
        # different convention keeps its previous entry and says so loudly.
        #
        # DO NOT "fix" this by teaching the parser a station's convention. Tried
        # and reverted 2026-07-30 for atlas, whose headings carried a canonical
        # pair (`### Story A1 (2.1):`) while its sprint-status keys were MIXED —
        # waves A–H keyed off the DISPLAY letter (`A1` -> `a1-scaffold-…`), Epic
        # 10 off the PARENS (`I0 (10.1)` -> `10-1-restore-…`). Deriving either
        # alone dropped the other half: emitting the canonical pair took atlas
        # from 38 matched / 0 unmatched to 6 / 32, and the board still rendered
        # and still looked plausible.
        #
        # RESOLVED 2026-08-08 by fixing the DATA, not the parser: atlas was
        # normalized to the canonical `<epic>.<num>` across headings, ledger
        # keys, story-spec filenames and board ids in lockstep
        # (EXEMPLAR-STANDARD INV-5), so no project carries a dual id any more.
        #
        # This guard STAYS — it is not an atlas accommodation. It protects EVERY
        # project from a parse failure silently blanking curated state, which is
        # how 32 real stories were once overwritten. What was removed is the
        # atlas-specific "EXPECTED for this project" message below.
        if sum(len(e["stories"]) for e in epics) == 0:
            if prev:
                print(f"[projects] WARN {slug}: epics.md parsed {len(epics)} epic(s) "
                      f"but NO stories (unrecognised story-heading convention) — "
                      f"keeping the existing line, NOT overwriting it. Fix the "
                      f"headings to `### Story <epic>.<num>:` (EXEMPLAR-STANDARD "
                      f"INV-5); do not teach this parser a new shape.")
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
    slugs = {ep.relative_to(REPO_ROOT / "_bmad-output" / "projects").parts[0]
             for ep in _discovered_epics_files()}
    covered: set[str] = set()
    for k in projects:
        try:
            resolved = resolve_project(k).project_dir
        except UnresolvableProjectError:
            continue  # a board line with no real project dir covers nothing
        if resolved:
            covered.add(resolved)
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
# DISCOVERED, not hardcoded. This was a fixed dict of four sibling directory
# names, which missed a live run two ways at once: a project not in the list was
# invisible, and loop homes moved to a SHORT root (~/.bmad-loops/<slug>, to keep
# the pixi-build-python path-length panic unreachable) so the sibling paths no
# longer resolve. Marshal's first run was live and unrendered for exactly this
# reason (2026-07-25). Both roots are searched; legacy siblings still work.
def _discover_loop_homes() -> dict[str, Path]:
    roots = [Path(os.environ.get("BMAD_LOOP_HOME_ROOT", Path.home() / ".bmad-loops")),
             REPO_ROOT.parent]
    homes: dict[str, Path] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if not (d / ".bmad-loop").is_dir():
                continue
            slug = d.name
            for prefix in (f"{REPO_ROOT.name}-loop-", ""):
                if prefix and slug.startswith(prefix):
                    slug = slug[len(prefix):]
                    break
            key = slug.removeprefix("pyforge-")
            homes.setdefault(key, d)      # short root wins over a legacy sibling
    return homes


LOOP_HOMES = _discover_loop_homes()
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
        runs_dir = Path(home) / ".bmad-loop" / "runs"
        if proj is None or not runs_dir.is_dir():
            continue
        runs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        active_ids = set()
        live = _live_loop_sessions()
        fresh = bool(runs) and (time.time() - runs[0].stat().st_mtime) < _RUN_FRESH_SECS
        if runs and (runs[0].name in live or fresh):
            # A worktree's PRESENCE is not evidence a story is running: policy
            # `keep_failed = true` deliberately leaves a deferred/escalated story's
            # worktree on disk so its work can be recovered. Keying on presence alone
            # made a paused run read as in flight -- live 2026-07-31, scribe reported
            # "in-flight: 1.3, 1.4" with 1.3 deferred, 1.4 escalated and the run PAUSED,
            # and the card ran a wall clock on a story that had stopped 3 hours earlier.
            # Same class as _RUN_FRESH_SECS above: the console must not claim motion it
            # has not measured. state.json is the authority for a story's phase (AD-33:
            # the journal owns process facts), so intersect presence with it.
            done_phases = {"deferred", "escalated", "done", "abandoned"}
            phases: dict[str, str] = {}
            try:
                st = json.loads((runs[0] / "state.json").read_text())
                phases = {k: (v or {}).get("phase", "") for k, v in (st.get("tasks") or {}).items()}
            except Exception:
                phases = {}  # unreadable state -> fall back to presence, as before
            wts = runs[0] / "worktrees"
            if wts.is_dir():
                for wt in wts.iterdir():
                    m = _WT_STORY.match(wt.name)
                    if m and phases.get(wt.name, "") not in done_phases:
                        active_ids.add(m.group(1).replace("-", "."))
        if not active_ids:
            # Nothing running -> CLEAR any card a previous render left behind.
            # `continue`ing here (the old behaviour) preserved a stale card forever:
            # the run that set it had since paused, so the board kept a live elapsed
            # clock on a story that had stopped. A card is a claim about NOW; absent
            # evidence it must be withdrawn, not retained (AD-8's no-silent-pass, in
            # presentational form).
            if proj.get("inflight"):
                print(f"[{pkey}] clearing stale in-flight card (nothing running)")
                proj["inflight"] = None
            continue
        marked = []
        for epic in proj["epics"]:
            for story in epic["stories"]:
                # `active_ids` is ALREADY the authority (state.json, gated above on
                # done_phases) — a story landing here is proven non-terminal from the
                # run's own perspective regardless of what `story[1]` currently reads.
                # Gating on `== "pending"` broke that precedence: the Tier-3 feed marks
                # a story `done` at DEV completion, before review (documented above and
                # in `promote_sprint_status.py`), so a story mid-review still reads
                # "done" here while state.json correctly still calls it active — the
                # flip silently never fired, `_set_inflight_card` below populated the
                # card anyway, and the board showed a live elapsed clock next to a
                # PAUSED chip for the exact same story (caught 2026-08-13, steward 9.2).
                if story[0] in active_ids and story[1] != "active":
                    story[1] = "active"
                    marked.append(story[0])
        if marked:
            print(f"[{pkey}] loop-home in-flight: {', '.join(marked)} (run {runs[0].name})")
        _set_inflight_card(proj, pkey, runs[0], active_ids)


def _set_inflight_card(proj: dict, pkey: str, run: Path, active_ids: set[str]) -> None:
    """Populate `inflight` — the live elapsed clock / progress / ETA card.

    The card has always existed in the renderer; nothing ever FED it. The function
    above is named `apply_loop_inflight` but only ever flipped a story's status from
    pending to active, so `inflight` stayed whatever a human last hand-pasted — which
    is why the clock vanished from every line the moment nobody hand-pasted one.

    ALL-OR-NOTHING, deliberately. The renderer guards with `if (p.inflight)` and then
    reads startEpoch/median/lo/hi/key/title/phase/attempt/phaseAsOf unconditionally —
    `Math.round(f.median / f.hi * 100)` throws on a partial object and takes the whole
    board down with it. Emit every field or leave it None.
    """
    import time
    jf = run / "journal.jsonl"
    if not jf.is_file():
        return
    start_ts, last_task = None, None
    for line in jf.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            e = json.loads(line)
        except Exception:
            continue
        kind, ts = e.get("kind"), e.get("ts")
        if kind == "story-start" and isinstance(ts, (int, float)):
            start_ts = ts                      # a re-drive restarts the clock, as it should
        elif kind == "session-start" and e.get("task_id"):
            last_task = e["task_id"]
    if start_ts is None or not last_task:
        return

    # task ids are `<story-key>-<phase>-<attempt>`; phase/attempt come from the tail so
    # the card says "review · attempt 2" rather than guessing from run state.
    m = re.search(r"-(dev|review|triage)-(\d+)$", last_task)
    phase, attempt = (m.group(1), m.group(2)) if m else ("dev", "1")

    sid = sorted(active_ids)[0]
    title = next((s[2] for e in proj["epics"] for s in e["stories"] if s[0] == sid), sid)

    # Baseline for the progress bar + ETA: this line's OWN measured stories. Using
    # another line's numbers would compare unlike metrics (warden measures active
    # compute, atlas wall-clock), so a line with no history simply gets no card.
    per = (proj.get("timing") or {}).get("perStory") or {}
    mins = sorted(v for v in per.values() if isinstance(v, (int, float)) and v > 0)
    if not mins:
        return
    median = mins[len(mins) // 2] if len(mins) % 2 else \
        round((mins[len(mins) // 2 - 1] + mins[len(mins) // 2]) / 2)

    proj["inflight"] = {
        "key": sid,
        "title": title,
        "phase": phase,
        "attempt": attempt,
        "startEpoch": int(start_ts),
        "median": int(median),
        "lo": int(mins[0]),
        "hi": int(max(mins[-1], median + 1)),   # hi is a divisor in the renderer
        "phaseAsOf": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
    }
    print(f"[{pkey}] in-flight card: {sid} · {phase} attempt {attempt} · "
          f"started {int((time.time() - start_ts) / 60)} min ago · median {median}m")


# ---- source: git (hands-off / CI) -------------------------------------------

def done_ids_from_git(branch: str, project_keys: tuple[str, ...] = ()) -> dict[str, set[str]]:
    """PER-PROJECT done story ids from `branch`'s commit subjects.

    Numeric story ids collide across projects (marshal's 5.1 is NOT warden's
    5.1), so each project matches ONLY its own commit convention — never a
    shared pool.

    `project_keys` seeds the buckets from the LIVE project set rather than a
    literal, so a newly provisioned smith is never missing one.
    """
    ref = branch
    if subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", branch], capture_output=True
    ).returncode != 0:
        ref = "HEAD"  # detached checkout (e.g. some CI) — HEAD is the branch tip
    log = subprocess.run(
        ["git", "log", ref, "--format=%s"], capture_output=True, text=True, check=True
    ).stdout
    done: dict[str, set[str]] = {k: set() for k in project_keys}
    for fixed in ("warden", "atlas", "herald", "doctor", "scribe"):
        done.setdefault(fixed, set())  # always present, even pre-scan
    unattributed: set[str] = set()
    for line in log.splitlines():
        m = _LOOP_DONE.search(line)
        if m:
            target = m.group(2) or ""
            slug = _LOOP_TARGET_SLUG.search(target)
            if slug and slug.group(1) in done:
                pkey = slug.group(1)
            else:
                pkey = next((p for frag, p in _LOOP_TARGET_LEGACY if frag in target), None)
            if pkey is None:
                # No target at all = pre-convention subject, historically warden's.
                # A target that exists but resolves to no known project is NOT
                # warden's — charging it there is how marshal's story vanished.
                if not target:
                    pkey = "warden"
                else:
                    unattributed.add(target)
                    continue
            done[pkey].add(m.group(1).replace("-", "."))  # 6-1 -> 6.1
        for a in _ATLAS_STORY.finditer(line):
            done["atlas"].add(a.group(1))  # A1, B10, 0.1, F4 ...
        for a in _ATLAS_GH.finditer(line):
            done["atlas"].add(a.group(1))  # G3, H1, H2 ...
        pm = _PR_BUILD_DONE.search(line)
        if pm and pm.group(1) in done:
            done[pm.group(1)].add(f"{pm.group(2)}.{pm.group(3)}")
        pm = _PR_PDOS_DONE.search(line)
        if pm:
            done["warden"].add(f"{pm.group(1)}.{pm.group(2)}")
        pm = _WARDEN_LEGACY_STORY.match(line)
        if pm:
            done["warden"].add(pm.group(1))
        qm = _QUALIFIED_STORY.match(line)
        if qm:
            sid = qm.group(2)
            for tok in qm.group(1).split("+"):
                key = tok.strip().lower()
                key = key.removeprefix("pyforge-")
                if key in done:          # validated against the live project set
                    done[key].add(sid)
    if unattributed:
        print(f"[git] WARN {len(unattributed)} bmad-loop merge target(s) matched no "
              f"known project — their stories are NOT counted (previously they were "
              f"silently credited to warden): {', '.join(sorted(unattributed))}")
    return done


def apply_tracked_ledger(projects: dict) -> None:
    """Upgrade stories to `done` from each project's TRACKED status ledger.

    `implementation-artifacts/` is gitignored wholesale, so the sprint feed — the
    only place that knows a story finished — is invisible to CI and absent from
    every clone. That is why the git path had to reconstruct DONE from commit
    subjects, and why it broke the moment a completion signal stopped being an
    ancestor of `main`: squash-merging PR #132 left Epic 10's
    `Merge bmad-loop/<run>/10-N-…` subjects unreachable and the board sat at 36/38
    with a ticking clock on a finished story.

    `scripts/promote_sprint_status.py` promotes that map to
    `planning-artifacts/sprint-status-ledger.yaml`, which IS tracked — the same
    move already made for `deferred-work-ledger.md`. This reads it, so the deploy
    reads truth rather than guessing, whatever the merge strategy was.

    UPGRADE-ONLY, deliberately. It never sets a story back to pending even if a
    ledger says so: a stale twin must not be able to un-finish a shipped story,
    and the never-downgrade invariant is what lets curated in-flight state survive
    a deploy. `dashboard-drift-check` is what catches a stale twin.
    """
    for pkey in sorted(projects):
        resolution = resolve_project(pkey)
        if resolution.ledger_path is None:
            continue
        ledger = REPO_ROOT / resolution.ledger_path
        if not ledger.is_file():
            continue
        statuses = parse_sprint_status(ledger)
        if not statuses:
            print(f"[{pkey}] tracked ledger parsed 0 statuses — ignored")
            continue
        upgraded = 0
        for epic in projects[pkey].get("epics", []):
            for story in epic.get("stories", []):
                if story[1] == "done":
                    continue
                if dashboard_id_to_status(story[0], statuses) == "done":
                    story[1] = "done"
                    upgraded += 1
        print(f"[{pkey}] tracked ledger: {len(statuses)} status(es), "
              f"{upgraded} story(ies) upgraded to done")



def build_fleet_progress(projects: dict) -> dict:
    """Per-station done/total/blocked plus a PyForge roll-up (CI-safe).

    Reads each project's TRACKED `sprint-status-ledger.yaml` through
    `parse_sprint_status` — the same parser `apply_tracked_ledger` uses, never a
    second one that could drift — so this renders identically on a laptop and on
    Pages. `implementation-artifacts/` is gitignored, so the Tier-3 feed is not
    an option here.

    **Why not read the board's own story states.** They are `done`/`active`/
    `pending` only: the board cannot distinguish a BLOCKED story from one merely
    not started, so 6 stories that will never run look exactly like 119 that
    will. Counting from the ledger is what makes `blocked` real.

    **Deliberately carries no live fields.** No running state, no projection, no
    ATTENTION — those derive from `marshal status`, which reads tmux and
    `~/.bmad-loops`. CI has neither, so publishing them would publish a number
    the deploy cannot measure. `pixi run -e local-recipes fleet-picture` is the
    local view that adds them; this is the half that is true everywhere.

    An epic counts as done only when EVERY story in it is done, matching the
    report's rule so the two never disagree.
    """
    rows, total = [], collections.Counter()
    for pkey in sorted(projects):
        resolution = resolve_project(pkey)
        if resolution.ledger_path is None:
            continue
        ledger = REPO_ROOT / resolution.ledger_path
        if not ledger.is_file():
            continue
        statuses = parse_sprint_status(ledger)
        if not statuses:
            continue
        stories = {k: v for k, v in statuses.items() if not k.startswith("epic-")}
        by_epic: dict[str, list[str]] = collections.defaultdict(list)
        for key, value in stories.items():
            head = key.split("-", 1)[0]
            if head.isdigit():
                by_epic[head].append(value)
        done = sum(1 for v in stories.values() if v == "done")
        blocked = sum(1 for v in stories.values() if v == "blocked")
        epics_done = sum(1 for e in by_epic.values() if all(v == "done" for v in e))
        rows.append({"key": pkey, "stories": len(stories), "done": done,
                     "blocked": blocked, "epics": len(by_epic),
                     "epicsDone": epics_done,
                     "complete": done == len(stories) and len(stories) > 0})
        for field, value in (("stories", len(stories)), ("done", done),
                             ("blocked", blocked), ("epics", len(by_epic)),
                             ("epicsDone", epics_done)):
            total[field] += value
    return {"rows": rows, "total": dict(total),
            "note": ("counts from the tracked sprint ledgers; blocked stories are "
                     "counted separately because they will not run. Live run state "
                     "and projections are local-only "
                     "(`pixi run -e local-recipes fleet-picture`).")}



def live_running_stations() -> tuple[set[str], str | None]:
    """Bare station keys (no `pyforge-` prefix) with a genuinely live bmad-loop
    engine right now, per `marshal status --format json` — the SAME authority
    `scripts/fleet_picture.py` reads, so nothing on this page can disagree with
    the CLI about who is running. `(set(), error)` if the check itself failed —
    never let a subprocess failure silently masquerade as "nothing running."

    Computed ONCE per render and threaded into every LOCAL-ONLY panel that
    needs a live/not-live distinction (`enrich_fleet_progress_live`,
    `scan_impl_campaign`) — a second definition of "running" is exactly how
    the build-campaign panel drifted from this one and started calling a
    stopped station "RUNNING" whenever it merely had `done > 0` (2026-08-13).

    `data.get("data", data)` mirrors `scripts/fleet_picture.py::_live()`'s own
    unwrap exactly: `marshal status --format json`'s payload is nested under a
    `data` envelope key (`{assumptions, command, data: {homes: [...]}, ...}`),
    which this function's own prior version read from the top level and so
    NEVER found a single running station (caught 2026-08-13 diffing this
    function's own output against `fleet_picture.py`'s, which unwraps
    correctly).
    """
    try:
        out = subprocess.run(
            ["pixi", "run", "-e", "pyforge-marshal", "--", "marshal", "status",
             "--format", "json"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=300).stdout
        parsed = json.loads(out[out.index("{"):out.rindex("}") + 1])
        rows = parsed.get("data", parsed).get("homes", [])
        return ({(r.get("slug") or "").replace("pyforge-", "") for r in rows
                  if r.get("state") == "running"}, None)
    except Exception as exc:                       # never break a local render
        return set(), str(exc)


def enrich_fleet_progress_live(fleet: dict, projects: dict, running: set[str],
                                live_error: str | None) -> None:
    """LOCAL-ONLY: add run state and a projection to the fleet roll-up.

    The operator asked the right question — the LOCAL board is generated on the
    machine that has tmux and `~/.bmad-loops`, so it can match
    `pixi run -e local-recipes fleet-picture` completely. Only the PAGES deploy
    is limited, because CI has neither. So the live fields are added here, in the
    local branch only, exactly like `apply_loop_inflight` — and their ABSENCE is
    what makes a Pages render honest rather than stale.

    `running`/`live_error` come from `live_running_stations()`, called ONCE by
    the caller and shared with `scan_impl_campaign` — never a second definition
    of "live" that could disagree with the row directly above it on the same
    page.

    `projected` = done + pending for a RUNNING station, done alone for a stopped
    one. Blocked is excluded by construction: those stories are not pending and
    will not be dispatched.
    """
    if live_error is not None:                     # never break a local render
        fleet["liveError"] = f"marshal status unavailable: {live_error}"
    total_proj = 0
    for row in fleet.get("rows", []):
        is_running = row["key"] in running
        pending = row["stories"] - row["done"] - row["blocked"]
        row["running"] = is_running
        row["projected"] = row["done"] + (pending if is_running else 0)
        total_proj += row["projected"]
    fleet["live"] = {"running": sorted(running), "projected": total_proj}
    fleet["note"] += (" Live fields present: this is a LOCAL render. A Pages "
                      "render omits them because CI cannot read tmux or "
                      "~/.bmad-loops.")

def apply_git(projects: dict) -> None:
    per_project = done_ids_from_git(MAIN_BRANCH, tuple(projects))
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

# The Guild's own vocabulary, read from its single home rather than restated.
# See docs/governance/guild-roster.json for why it lives beside the governance
# kernel and not inside either consumer (Doctor Story 6-8).
_GUILD_ROSTER = json.loads(
    (REPO_ROOT / "docs" / "governance" / "guild-roster.json").read_text(encoding="utf-8")
)
# The lifecycle, each state named for the ACT THAT COMPLETED — never for the
# artifact that proves it, and never for activity. Status declares what EXISTS
# (stable, honestly hand-declarable); the board DERIVES what is happening from
# live build lines. A `building` status was considered and rejected: it would go
# stale the moment a line pauses or finishes — exactly how pyforge-warden came to
# read `in-spec` while shipped 31/31, and deckcraft `dreamt` while holding a deck
# AND a Spec (both found + fixed 2026-07-25).
# RE-DECLARED here until 2026-08-09, identical to bmad_drift_check.py's copy by
# luck rather than by construction — the same duplication hazard that made
# GUILD_DREAMS/STATIONS imports below, one drift too late. Now read from the
# single home, docs/governance/guild-roster.json (Doctor Story 6-8), which also
# carries the reasoning these comments used to hold.
DREAM_STATUSES = tuple(_GUILD_ROSTER["dream_statuses"])
# Perpetual concerns — tended, never finished. They sit OUTSIDE the lifecycle:
# excluded from backlog (nobody can close them) and from realized (never done).
DREAM_TYPES = tuple(_GUILD_ROSTER["dream_types"])

# The eight Smiths — the canonical station roster (docs/dreams/pyforge-charter.md
# §§1-8). `owner:` on a Dream names the station accountable for carrying it all
# the way Dream -> code; the station is the POST, not the product, so owning a
# Dream does not mean it becomes that Smith's package.
#
# IMPORTED from scripts/bmad_drift_check.py, not re-declared — same GUILD_DREAMS
# duplication-hazard fix. One definition, one place to update.
# The one Dream that may name no station, because it PRECEDES them: the Charter, which
# constitutes the stations. `guild` is NOT a ninth station and never renders as one — it
# marks a Dream sitting above the roster, not beside it.
#
# IMPORTED from scripts/bmad_drift_check.py, not re-declared — a hand-mirrored copy was
# missed on 2026-07-28 and the board warned on a Dream the Charter explicitly permits.
# One definition, one place to update.
#
# History, because this list flipped three times. It briefly held Genesis, then dropped it
# on the reasoning that "the bootstrapper that installs the operating model anywhere" is
# Marshal's craft — true of the INSTALLER and only the installer. Genesis was doing two
# jobs in one Dream: constitutive records (Charter, Lexicon, membership) AND a buildable
# bootstrapper; removing it wholesale fixed the second and broke the first. Split
# 2026-07-28 — installer to marshal, constitutive half back here. Closed 2026-08-08: with
# the project dissolved and the installer gone, the constitutive half was two names for
# one record, so it was absorbed into the Charter and `guild` closed at one. Charter §5 +
# its Realization log carry all three rulings.
# 2026-08-09 (Doctor Story 6-8): these were IMPORTED from
# scripts/bmad_drift_check.py, which was the right fix for the 2026-07-28 drift
# but made the board depend on a DETECTOR for constitutive data — and Story 6-9
# retires that file into Doctor's package, where this environment cannot import
# it. Both now read the same JSON both tools read; the import direction problem
# disappears with the import.
GUILD_DREAMS = tuple(_GUILD_ROSTER["guild_dreams"])
STATIONS = tuple(_GUILD_ROSTER["stations"])

# Deck dirs whose name differs from the dream slug (mason's chapter deck backs
# the packaging-factory dream, etc.).
DREAM_DECK_ALIASES = {
    "packaging-factory": "pyforge-mason",
    "agentic-sdlc-autonomy": "agentic-sdlc",
    # The master vision deck. The directory keeps its original name after the
    # 2026-08-08 absorption: it is a published artifact with a Claude Design twin,
    # and renaming it would desync the bridge for a cosmetic gain.
    "pyforge-charter": "pyforge-genesis",
}
# Dreams whose build runs as a console program (chip shows live done/total).
DREAM_PROGRAM = {
    "pyforge-warden": "warden",
    "pyforge-atlas": "atlas",
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
    """Spec KERNELS only (Row 4) — .../specs/spec-<slug>/SPEC.md. For per-story specs (Row 7) see scan_story_specs().

    Includes docs/governance/spec-*/ -- the constitutive (`owner: guild`) kernel, which
    lives outside `_bmad-output/projects/` entirely since 2026-08-02 (`pyforge-genesis`
    dissolved; see GOVERNANCE_DIR). One kernel since 2026-08-08, when the Lexicon half
    was absorbed into spec-pyforge-charter and `guild` closed at one Dream.
    """
    rows: list[dict] = []
    spec_dirs = (sorted((REPO_ROOT / "_bmad-output" / "projects").glob(
            "*/planning-artifacts/specs/spec-*"))
        + sorted((REPO_ROOT / GOVERNANCE_DIR).glob("spec-*")))
    for spec_dir in spec_dirs:
        smd = spec_dir / "SPEC.md"
        if not smd.is_file():
            continue
        text = smd.read_text(encoding="utf-8")
        slug = spec_dir.name.removeprefix("spec-")
        project = (GOVERNANCE_DIR if spec_dir.parent == REPO_ROOT / GOVERNANCE_DIR
                   else spec_dir.relative_to(REPO_ROOT / "_bmad-output" / "projects").parts[0])
        m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = (m.group(1).strip() if m else slug)
        title = re.sub(r"^SPEC\s*[—–-]\s*", "", title)
        caps = len(set(re.findall(r"\bCAP-\d+\b", text)))
        comp = 0
        if text.startswith("---"):
            fm = text.split("---", 2)[1]
            cm = re.search(r"^companions:\s*\n((?:[ \t]*-[ \t].*\n)*)", fm, re.MULTILINE)
            if cm:
                comp = len(re.findall(r"^[ \t]*-[ \t]", cm.group(1), re.MULTILINE))
            inline = re.search(r"^companions:\s*\[([^\]]*)\]", fm, re.MULTILINE)
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


def scan_story_specs() -> list[dict]:
    """Per-station Row-7 compliance: done stories vs. tracked flat specs (spec-*.md pattern only, excludes nested SPEC.md)."""
    rows: list[dict] = []
    projects_base = REPO_ROOT / "_bmad-output" / "projects"

    for project_dir in sorted(projects_base.glob("pyforge-*")):
        # Count done stories from sprint-status-ledger.yaml (exclude epic-*/epic-*-retrospective)
        # Parsed with stdlib rather than PyYAML to work in CI (bare Python env, no third-party).
        ledger_path = project_dir / "planning-artifacts" / "sprint-status-ledger.yaml"
        done_count = 0
        if ledger_path.exists():
            try:
                ledger_text = ledger_path.read_text(encoding="utf-8")
                in_status_block = False
                for line in ledger_text.splitlines():
                    stripped = line.strip()
                    if stripped == "development_status:":
                        in_status_block = True
                        continue
                    if in_status_block:
                        if not line.startswith(" "):  # end of block (dedent)
                            break
                        if ": done" in line:
                            # Extract story ID (key before ": done")
                            key = line.split(":")[0].strip()
                            if not key.startswith("epic-"):  # exclude epic entries
                                done_count += 1
            except Exception:
                pass

        # Count tracked flat story-spec files (spec-*.md at top level, not nested dirs with SPEC.md)
        specs_dir = project_dir / "planning-artifacts" / "specs"
        tracked_count = 0
        if specs_dir.exists():
            # Flat files matching spec-*.md (not nested kernel dirs like spec-<slug>/SPEC.md)
            tracked_count = len([f for f in specs_dir.glob("spec-*.md") if f.is_file()])

        gap = max(0, done_count - tracked_count)  # clamp; spec-first is healthy surplus
        project_slug = project_dir.name
        rows.append({
            "station": project_slug,
            "done": done_count,
            "tracked": tracked_count,
            "gap": gap
        })

    total_done = sum(r["done"] for r in rows)
    total_tracked = sum(r["tracked"] for r in rows)
    total_gap = sum(r["gap"] for r in rows)
    print(f"[story-specs] {len(rows)} station(s), {total_done} done, {total_tracked} tracked, {total_gap} gap(s)")
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

# CAMPAIGN_PROJECT_OVERRIDE folded into _PROJECT_OVERRIDES (one resolver, one
# table). 3 of these 10 roster slugs are dissolved-and-absorbed (PROJECTS.md)
# -- their chain moved to the owning Smith's tree, so a naive `<slug>/planning-
# artifacts` path both mis-detects `have` (false "not landed") and any link
# built from it 404s. pyforge-genesis resolves to `project_dir: None` (its
# own data shape, not force-fit into the absorbed-satellite one): its
# standard PRD/brief/architecture/epics chain was retired outright
# (constitutive, ships no product) -- `have: all False` for it is honest, not
# a bug; only its link redirects (data-driven now, not a JS special case).
# It stays in CAMPAIGN_ROSTER above because that roster is the HISTORICAL record of
# the 2026-07-25 campaign, in which it really was wave 2d; rewriting history to hide
# a since-retired name would be the drift this board exists to catch. As of
# 2026-08-08 the name is retired everywhere else -- absorbed into pyforge-charter.


def scan_campaign() -> dict:
    """Stage completion per chain, detected from planning-artifacts on main.

    In-flight chains write in isolated loop worktrees, so main shows nothing
    until a chain merges — roster `state` covers the gap (running/queued);
    detection upgrades it to partial/landed automatically at each merge.
    """
    rows: list[dict] = []
    for e in CAMPAIGN_ROSTER:
        resolution = resolve_project(e["slug"])
        real_project = resolution.project_dir
        if real_project is None:
            # The dissolved case: no tree to glob against. `have` stays
            # honestly all-False rather than force-fitting the absorbed-
            # satellite shape onto a project that was retired outright.
            have = {s: False for s in CAMPAIGN_STAGES}
        else:
            pa = REPO_ROOT / "_bmad-output" / "projects" / real_project / "planning-artifacts"
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
        rows.append({**e, "have": have, "n": n, "of": len(target), "status": status,
                     "planning_project": real_project, "redirect": resolution.redirect})
    landed = sum(1 for r in rows if r["status"] == "landed")
    running = sum(1 for r in rows if r["status"] == "running")
    print(f"[campaign] {len(rows)} chains · {running} running · {landed} landed")
    return {"launched": "2026-07-25",
            "chain": "research → brief → PRD → architecture → epics",
            "rows": rows}


# ---- build campaign (implementation lines across all bmad-projects) ----------

IMPL_CAMPAIGN = [
    # pkey = data.js projects key when the line is dashboard-wired (done/total live
    # via `projects`); everything else derives from its own sprint-status-ledger.yaml
    # (IMPL_CAMPAIGN_LEDGER below) -- `stories`/`state` here are only the FALLBACK
    # when no ledger exists yet (wasm/unity: genuinely 0 stories, PRD+arch only).
    # 2026-08-02: this used to be a static, 2026-07-25-dated snapshot with `done`
    # hardcoded to 0 forever for every non-pkey row -- marshal read "0/40" the whole
    # time it was actually 10/50, same bug on mason (0/38, actually 4/48) and
    # steward (0/18, actually 3/26). Never derived, so it never caught up.
    {"slug": "pyforge-herald",       "pkey": "herald", "stories": 17, "state": "running",
     "note": "line 1 — smallest full product, spec settled 0 OQs"},
    {"slug": "pyforge-doctor",       "pkey": "doctor", "stories": 12, "state": "running",
     "note": "line 2 — consolidative wrap"},
    {"slug": "pyforge-scribe",       "pkey": "scribe", "stories": 9,  "state": "running",
     "note": "line 3 — team memory + graph"},
    {"slug": "pyforge-steward",      "pkey": None, "stories": 18, "state": "queued",
     "note": "next free slot"},
    {"slug": "pyforge-mason",        "pkey": None, "stories": 38, "state": "queued",
     "note": "longest persona line; CFE Rule-2 retro at closeout"},
    {"slug": "presenton-pixi-image", "pkey": None, "stories": 30, "state": "held",
     "note": "operator Phase-0 gates: MS disconnected-stack check + memory-subsystem scope"},
    {"slug": "pyforge-marshal",      "pkey": None, "stories": 86, "state": "held",
     "note": "epics 1-12 — the seed installer's epics 7-12 merged in 2026-08-08; one canonical epics.md"},
    {"slug": "wasm-analytics-stack", "pkey": None, "stories": 0,  "state": "future",
     "note": "PRD+arch only by design; stories decompose when scheduled"},
    {"slug": "unity-data-stack",     "pkey": None, "stories": 0,  "state": "future",
     "note": "PRD+arch only by design; stories decompose when scheduled"},
]

# IMPL_CAMPAIGN_LEDGER folded into _PROJECT_OVERRIDES's `ledger_path` field
# (one resolver, one table). The non-`pkey` rows above now derive their live
# ledger through `resolve_project(e["slug"]).ledger_path`, which defaults to
# the standard `<project_dir>/planning-artifacts/sprint-status-ledger.yaml`
# for marshal/mason/steward -- exactly what this dict used to hand-declare --
# and is explicit `None` (via the override table) for presenton-pixi-image
# (not cleanly split from mason's own shared ledger) and wasm/unity (no
# ledger exists yet), so those three keep their IMPL_CAMPAIGN static fallback.
#
# 2026-08-08: the `genesis-installer` row is GONE, not relabelled. It existed because
# marshal's ledger was fed by two epics documents -- `epics.md` (Epics 1-6) and
# `epics-genesis-installer.md` (Epics 7-12) -- so the board split one station into two
# rows by epic number, and PR #233 could only label that split rather than remove it.
# The two documents are now one canonical `epics.md` covering Epics 1-12 (86 stories,
# verified against this same ledger), so marshal reads UNBOUNDED and renders as the one
# station it always was -- which is also why the resolver's default `ledger_path`
# (unbounded, no epic_min/epic_max) is sufficient and the old epic-range parameters
# were dropped from `_ledger_done_total` below.
_LEDGER_STORY_KEY = re.compile(r"^(\d+)-\d+-")


def _ledger_done_total(rel_path: str) -> tuple[int, int] | None:
    """`(done, total)` for a ledger's story-shaped keys.

    Non-story keys (`epic-N`, `epic-N-retrospective`) are excluded -- they aren't
    stories and would double-count. `None` if the ledger doesn't exist yet.
    """
    p = REPO_ROOT / rel_path
    if not p.is_file():
        return None
    statuses = parse_sprint_status(p)
    done = total = 0
    for key, status in statuses.items():
        if not _LEDGER_STORY_KEY.match(key):
            continue
        total += 1
        if status == "done":
            done += 1
    return done, total


def scan_impl_campaign(projects: dict, running_stations: set[str] | None = None) -> dict:
    """Build-campaign roster; wired lines derive done/total live from `projects`,
    unwired lines derive it from their own sprint-status-ledger.yaml (IMPL_CAMPAIGN_LEDGER).

    `running_stations` is the SAME live set `enrich_fleet_progress_live` uses
    (from `live_running_stations()`) — `None` on a `--source git` render, where
    no live authority exists at all. A row's `state` is `"running"` ONLY when
    its own bmad-loop engine is actually live right now; `done > 0` alone earns
    `"in-progress"`, a distinct, honestly-labeled state — conflating the two
    is what made a stopped station (`done > 0`, no live engine) render as
    "RUNNING" (2026-08-13, caught by inspection against `fleet-picture`, which
    already made this exact distinction for the sibling fleet-roll-up panel).
    """
    rows: list[dict] = []
    for e in IMPL_CAMPAIGN:
        resolution = resolve_project(e["slug"])
        done, total = 0, e["stories"]
        if e["pkey"] and e["pkey"] in projects:
            stories = [s for ep in projects[e["pkey"]]["epics"] for s in ep["stories"]]
            total = len(stories)
            done = sum(1 for s in stories if s[1] == "done")
        elif resolution.ledger_path:
            ledger_live = _ledger_done_total(resolution.ledger_path)
            if ledger_live is not None:
                done, total = ledger_live
        is_running = running_stations is not None and e["slug"].removeprefix("pyforge-") in running_stations
        if total and done == total:
            state = "done"
        elif is_running:
            state = "running"
        elif done > 0:
            state = "in-progress"
        else:
            state = e["state"]
        rows.append({**e, "done": done, "total": total, "state": state,
                     "epics_path": resolution.epics_path, "redirect": resolution.redirect})
    running = sum(1 for r in rows if r["state"] == "running")
    dn = sum(1 for r in rows if r["state"] == "done")
    print(f"[build-campaign] {len(rows)} lines · {running} running · {dn} done")
    return {"launched": "2026-07-25", "rows": rows}


# ---- build-line state (every In Build / Realized row carries a chip) ---------

LINE_HOMES = {"herald": "pyforge-herald", "doctor": "pyforge-doctor",
              "scribe": "pyforge-scribe", "warden": "pyforge-warden", "atlas": "pyforge-atlas"}
_STORY_KEY = re.compile(r"^\s*(\d+-\d+-[a-z0-9-]+):\s*backlog", re.MULTILINE)


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
     "_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md"),
    ("spec-surface", "spec-surface-check", "every tracked file under a Spec surface", ""),
    ("llms-full",    "llms-full-check",    "library catalog freshness", ""),
]
_FINDING_RE = re.compile(r"(\d+)\s+(?:integrity|currency|finding)")
_FINDINGS_HDR = re.compile(r"^FINDINGS \((\d+)\)")   # spec-surface-check's form


def _task_cmd(task: str) -> list[str] | None:
    """This task's own `cmd` from pixi.toml, retargeted at the running interpreter.

    DERIVED, never declared twice: a task's command is written down in exactly one
    place, so the direct runner below cannot drift away from what `pixi run` does.
    Only plain `python script.py` tasks are returned — anything else must go
    through pixi, which is what the fallback in _run_detector is for.
    """
    try:
        cfg = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    except Exception:
        return None
    for feat in cfg.get("feature", {}).values():
        spec = (feat.get("tasks") or {}).get(task)
        cmd = spec.get("cmd") if isinstance(spec, dict) else spec
        if isinstance(cmd, str) and cmd.split() and cmd.split()[0] == "python":
            return [sys.executable, *cmd.split()[1:]]
    return None


def _run_detector(task: str):
    """Run a detector DIRECTLY where possible, falling back to `pixi run`.

    Direct-first is deliberate. All three detectors are stdlib-only and shell out
    to `git` alone — nothing in them needs the pixi environment, so requiring one
    bought nothing and cost everything: `pixi run -e local-recipes` is unavailable
    on the Pages runner, so the published board reported every detector as
    "could not run here" while they read green locally. Materialising that env in
    CI to satisfy the launcher would mean a ~9.8 GB download per deploy against a
    10 GB cache ceiling. The environment was never the requirement.

    pixi remains the fallback for any detector whose task is not a plain
    `python script.py` invocation.
    """
    for cmd in (_task_cmd(task), ["pixi", "run", "--frozen", "-e", "local-recipes", task]):
        if not cmd:
            continue
        try:
            return subprocess.run(cmd, capture_output=True, text=True,
                                  cwd=REPO_ROOT, timeout=120)
        except Exception:                      # interpreter/pixi absent, timeout, anything
            continue
    return None


def scan_health() -> dict:
    """Run the standing detectors; capture verdict + finding count + remedy."""
    rows = []
    for name, task, guards, runbook in DETECTORS:
        r = _run_detector(task)
        if r is None:
            state, verdict_line, n = "unknown", "detector could not run here", 0
        else:
            out = (r.stdout + r.stderr).strip().splitlines()
            verdict_line = next((l.strip() for l in reversed(out)
                                 if l.strip().startswith(("OK:", "DRIFT:", "FAIL:", "FINDINGS ("))), "")
            state = "green" if r.returncode == 0 else ("fail" if verdict_line.startswith("FAIL") else "drift")
            hdr = _FINDINGS_HDR.match(verdict_line)
            n = int(hdr.group(1)) if hdr else (
                sum(int(m) for m in _FINDING_RE.findall(verdict_line)) if verdict_line else 0)
        rows.append({"name": name, "task": task, "guards": guards, "state": state,
                     "findings": n, "verdict": verdict_line[:120], "runbook": runbook})

    # Baseline state: compare the recorded FACTORY FINGERPRINT to live, not commit
    # counts — the baseline commit often isn't on main's first-parent chain (this repo
    # is a staged-recipes fork), so "N commits behind" is noise. The fingerprint is
    # exactly what makes drift-check's `surface-changed` fire.
    base, deltas = {}, []
    bp = REPO_ROOT / "_bmad-output/projects/pyforge-marshal/.sync-baseline.json"
    if bp.is_file():
        try:
            base = json.loads(bp.read_text(encoding="utf-8"))
            live = {}
            g = _run_detector("bmad-groundtruth")   # direct-first, same as the detectors
            if g is not None and g.returncode == 0:
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
    # "matches baseline" is only true if a baseline was actually READ. When the file is
    # missing, `deltas` is empty VACUOUSLY -- reporting a match there is a false green, and
    # it is exactly what happened when the baseline moved projects (2026-07-28).
    if not base:
        fingerprint = f"NO BASELINE at {bp.relative_to(REPO_ROOT)} — nothing compared"
    elif deltas:
        fingerprint = f"{len(deltas)} fingerprint delta(s) vs baseline"
    else:
        fingerprint = "fingerprint matches baseline"
    print(f"[health] {green}/{len(rows)} detectors green · " + fingerprint)
    return {"detectors": rows,
            "baseline": {"skill": base.get("skill_version", ""), "head": (base.get("git_head") or "")[:10],
                         "deltas": deltas,
                         "runbook": "_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md"}}


# ---- fleet view (Dream -> Code, per project: stage, recency, version) --------

# Display-name overrides. Everything else uses the slug with any `pyforge-` prefix
# dropped — the roster is DERIVED (see `_fleet_chains`), so this holds only the handful
# of names that read better short.
FLEET_LABELS = {
    "presenton-pixi-image": "presenton",
    "unity-data-stack": "unity",
    "wasm-analytics-stack": "wasm",
}
# Lifecycle order — the Dream-to-Code chain, left to right. Grown from 9 to 15 because
# several dots stood for a whole artifact SET or hid a distinct gate: `research` is three
# disciplines, `deck` is the six-artifact family contract, `epics` and `code` each hid a
# second question (is it drivable? does it verify?), and `ux` / `context` / `gates` /
# `retro` are real chain artifacts that had no dot at all.
FLEET_STAGES = ("dream", "deck", "spec", "research", "brief", "prd", "ux", "arch",
                "context", "epics", "sprint", "tea", "gates", "code", "verify", "retro")
# Where a guild-owned (constitutive, `owner: guild`) chain's Spec kernel lives — NOT a
# `_bmad-output/projects/<x>/` tree, because it ships no product and owns no Smith-shaped
# scaffolding (2026-08-02: pyforge-genesis dissolved, Charter/Lexicon specs moved here;
# 2026-08-08: the two merged into spec-pyforge-charter and `guild` closed at one).
# `_fleet_chains()`/`_stage_globs()` special-case this sentinel value of `project`.
GOVERNANCE_DIR = "docs/governance"
# Stages whose dot stands for a SET: {stage: the artifacts that must all be present}.
RESEARCH_TYPES = ("domain", "market", "technical")
DECK_FAMILY = ("prototype", "exec", "infographic", "marp", "standalone", "pptx")
FLEET_SUBSCORE = {"research": RESEARCH_TYPES, "deck": DECK_FAMILY}
# Stages a CHAIN legitimately does not have (depth chosen at planning time). Keyed by
# CHAIN slug, matching the fleet row key — it used to be read with the PROJECT slug, so it
# matched nothing and every row rendered `na: []`, which is why unity-data-stack and
# wasm-analytics-stack both reported a complete 9/9 chain while owning neither epics nor
# code. `ux` is n/a everywhere except chains that declare a UI surface.
FLEET_NA = {
    "pyforge-charter": {"research", "brief", "context"},  # constitutive (Charter §5), precedes stations
    "unity-data-stack": {"epics"},
    "wasm-analytics-stack": {"epics"},
    "regenerable-factory": {"prd", "arch", "brief", "context"},  # shipped practice-type, no brief/UX by design
}
FLEET_UX = {"presenton-pixi-image", "unity-data-stack", "wasm-analytics-stack"}
# Verify gate task-name aliases: chains whose test task doesn't follow {slug}-test pattern.
FLEET_VERIFY_ALIAS = {"pyforge-atlas": ("kedro-test",)}
_STALE_DAYS = 30
# Shelf life in days, per stage. A global default keeps this usable with no configuration;
# override only where the artifact really ages differently. `None` = never goes stale: a
# Dream is a standing aspiration and a Spec is a contract — neither expires by the calendar,
# they expire when something downstream contradicts them, which is what the
# stale-by-dependency check is for.
_SHELF_LIFE_DEFAULT = 90
_SHELF_LIFE = {"dream": None, "spec": None, "context": None, "tea": None, "retro": None}

def _frontmatter_scalars(path: Path, keys: tuple[str, ...]) -> dict[str, str]:
    """The named top-level scalars from a file's `---` frontmatter, comments stripped."""
    out: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return out
    if not lines or lines[0].strip() != "---":
        return out
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        for k in keys:
            if ln.startswith(f"{k}:"):
                out[k] = _strip_yaml_comment(ln.split(":", 1)[1])
    return out


def _fleet_chains() -> list[tuple[str, str, str, str]]:
    """Every chain in the repo as `(slug, project, owner, dream_status)` — DERIVED.

    The roster was a 13-entry literal while the repo held 34 chains, so 21 chains — every
    one of them carrying a SPEC.md — had no Fleet row at all, including all three that
    carry unresolved `open_questions`. A hardcoded roster omits exactly the newest thing;
    deriving it and warning on what cannot be placed is the standing rule here.

    A chain is a Dream (`docs/dreams/<slug>.md`) OR a Spec directory
    (`…/planning-artifacts/specs/spec-<slug>/`). The UNION on purpose: a Dream with no Spec
    and a Spec with no Dream are both real conditions worth seeing, and taking either side
    alone would hide one of them. The Spec's own location names the owning project —
    authoritative in a way `owner:` is not, since `owner: guild` names no project tree.
    """
    spec_project: dict[str, str] = {}
    owner_dream: dict[str, str] = {}
    for d in sorted(REPO_ROOT.glob("_bmad-output/projects/*/planning-artifacts/specs/spec-*")):
        if not (d / "SPEC.md").is_file():
            continue
        slug = d.name[len("spec-"):]
        spec_project.setdefault(slug, d.parts[-4])
        # A chain need not have a Dream FILE of its own. Charter §5: one Dream can spawn
        # several Specs, and such a Spec names its parent in `owner-dream:`. Reading that
        # is what distinguishes a legitimate sub-chain from genuinely unattributed work —
        # without it, bmad-loop-governance and multi-loop-isolation read as ownerless and
        # tripped the Charter §7 accountability gate, which refuses to publish a row it
        # cannot attribute.
        od = _frontmatter_scalars(d / "SPEC.md", ("owner-dream",)).get("owner-dream", "")
        if od:
            owner_dream.setdefault(slug, Path(od.strip("'\"")).stem)
    for d in sorted(REPO_ROOT.glob(f"{GOVERNANCE_DIR}/spec-*")):
        if not (d / "SPEC.md").is_file():
            continue
        slug = d.name[len("spec-"):]
        spec_project.setdefault(slug, GOVERNANCE_DIR)
        od = _frontmatter_scalars(d / "SPEC.md", ("owner-dream",)).get("owner-dream", "")
        if od:
            owner_dream.setdefault(slug, Path(od.strip("'\"")).stem)
    dreams = {f.stem: _frontmatter_scalars(f, ("owner", "status"))
              for f in sorted(DREAMS_DIR.glob("*.md")) if f.name != "README.md"}
    out = []
    for slug in sorted(set(spec_project) | set(dreams)):
        meta = dreams.get(slug, {})
        parent = owner_dream.get(slug, "")
        # Own Dream first; else inherit the parent Dream's station.
        owner = meta.get("owner") or dreams.get(parent, {}).get("owner", "")
        project = spec_project.get(slug)
        if not project and owner and owner != "guild":
            project = f"pyforge-{owner}"
        if not project:
            print(f"[fleet] WARN chain {slug!r}: no spec directory and no station owner — "
                  f"its artifact lookups have nowhere to look")
        if not owner:
            print(f"[fleet] WARN chain {slug!r}: no owner — no Dream of its own and no "
                  f"`owner-dream:` in its SPEC.md; the Charter §7 gate will refuse it")
        out.append((slug, project or "", owner, meta.get("status", ""), parent))
    # Stations first (a chain whose slug names its own project), then satellites grouped
    # under the station that owns them — the reading order the hand-written roster had.
    return sorted(out, key=lambda c: (c[0] != c[1], c[2], c[0]))


_ISO = re.compile(r"(\d{4}-\d{2}-\d{2})")
# Every path a stage glob can resolve MUST sit under one of these, or _artifact_dates()
# returns ("", "") for it and scan_fleet reads the stage as never reached even though
# _resolve() found the file. Root AGENTS.md joined 2026-09-20: Story 30.2 (2026-09-06)
# repointed the `context` stage at it without widening this tuple, and every station
# except atlas (whose child AGENTS.md sits under src/shared/packages) carried a phantom
# `context` gap — the CAP-3 layers checkpoint read `fail` beside "15/15 layers present".
# The doctor's test_every_stage_glob_is_inside_the_git_date_index pins the invariant.
_GIT_SCOPES = ("docs/dreams", "docs/governance", "_bmad-output", "presentations",
               "src/shared/packages", "AGENTS.md")
_GIT_FIRST: dict[str, str] = {}
_GIT_LAST: dict[str, str] = {}


def _build_git_index() -> None:
    """First-seen and last-touched dates for every tracked path, in ONE git pass.

    This used to be one `git log` per matched path. At 13 chains x 9 stages that was
    tolerable; at 34 x 15, with two dates per artifact, it is ~500 subprocesses on every CI
    deploy. One `--name-only` walk over the scoped paths indexes ~3,900 paths from ~480
    commits in about a tenth of a second. `git log` is newest-first, so a path's FIRST
    sighting is its last-touched and its LAST sighting is when it was added.
    """
    if _GIT_FIRST:
        return
    r = subprocess.run(["git", "log", "--format=%x00%ad", "--date=short", "--name-only",
                        "--", *_GIT_SCOPES],
                       capture_output=True, text=True, cwd=REPO_ROOT)
    when = ""
    for line in r.stdout.splitlines():
        if line.startswith("\0"):
            when = line[1:]
        elif line.strip():
            _GIT_LAST.setdefault(line, when)
            _GIT_FIRST[line] = when


def _artifact_dates(rel: str) -> tuple[str, str]:
    """`(created, updated)` for one tracked path, as full ISO. `("", "")` if unknown.

    TWO clocks, because the board asks two different questions and one date cannot answer
    both: `created` orders the chain (is this backfilled?), `updated` judges currency (is
    this still true?).

    The PATH date wins, per the adopted convention — a date in the filename or directory
    name is the artifact's own "as of" claim, it is universal here (every one of the 38
    dated artifact directories carries it), and it cannot silently drift from the file the
    way a frontmatter field can. Frontmatter is consulted next, git only as a last resort:
    git-add is the one source measured to lie, differing from the path date on 86 paths by
    up to ~88 days, because the 2026-07-29 spec-recovery wave committed artifacts authored
    in May.

    A path date is fixed at creation and so cannot express an update; for the `updated`
    clock it is therefore a FLOOR, taking whichever of it and git's last-touched is later.
    Full ISO throughout: the old `%m-%d` format discarded the year, which made the
    chain-ordering comparison behind `backfilled` year-blind.
    """
    _build_git_index()
    m = _ISO.search(rel)
    path_date = m.group(1) if m else ""
    fm = {}
    p = REPO_ROOT / rel
    if p.is_file() and p.suffix in (".md", ".yaml", ".yml"):
        try:
            fm = _frontmatter_scalars(p, ("created", "updated", "date"))
        except OSError:
            fm = {}
    fm = {k: v.strip("'\"") for k, v in fm.items()}
    created = path_date or fm.get("created") or fm.get("date") or _GIT_FIRST.get(rel, "")
    # STRICT precedence, never max(). An explicit `updated:` is the only field that can
    # express a refresh, so it leads; the path date is next per the adopted convention;
    # git is the last resort. Taking the max let git's last-touched win, and a bulk commit
    # is not a refresh: the 2026-07-29 spec-recovery wave re-committed most of the tree in
    # one go, which made 41 of 45 currency findings report that wave rather than any real
    # staleness. If an artifact declares a date, that date IS its currency.
    updated = (fm.get("updated") or path_date or fm.get("date")
               or _GIT_LAST.get(rel, "") or created)
    return created, updated


def _resolve(patterns: list[str]) -> list[str]:
    """Repo-relative paths matching any of the globs, deduped and sorted."""
    out: set[str] = set()
    for pat in patterns:
        for path in glob.glob(str(REPO_ROOT / pat), recursive=True):
            p = Path(path)
            if p.is_file():
                out.add(str(p.resolve().relative_to(REPO_ROOT)))
    return sorted(out)


def _stage_dates(paths: list[str]) -> tuple[str, str]:
    """`(created, updated)` for a STAGE, across every file that satisfies it.

    EARLIEST created, because a stage is reached when its first artifact appears; LATEST
    updated, because the stage is only as current as its most recently refreshed piece.
    """
    pairs = [_artifact_dates(p) for p in paths]
    created = [a for a, _ in pairs if a]
    updated = [b for _, b in pairs if b]
    return (min(created) if created else "", max(updated) if updated else "")


def _last_touched(prefixes: list[str]) -> str:
    """Most recent commit date (ISO) under any of the given path prefixes."""
    _build_git_index()
    keys = [p.rstrip("/") for p in prefixes]
    best = ""
    for rel, when in _GIT_LAST.items():
        if when > best and any(rel == k or rel.startswith(k + "/") for k in keys):
            best = when
    return best


def _pixi_tasks() -> set[str]:
    """Every task name declared in the workspace manifest (all feature tables)."""
    global _PIXI_TASKS
    if _PIXI_TASKS is None:
        try:
            data = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        names = set(data.get("tasks", {}))
        for feat in (data.get("feature") or {}).values():
            names |= set((feat or {}).get("tasks") or {})
        _PIXI_TASKS = names
    return _PIXI_TASKS


_PIXI_TASKS: set[str] | None = None


def _pkg_version(slug: str) -> str:
    f = REPO_ROOT / "src" / "shared" / "packages" / slug / "pyproject.toml"
    if not f.is_file():
        return ""
    m = re.search(r'^version\s*=\s*"([^"]+)"', f.read_text(encoding="utf-8"), re.MULTILINE)
    return m.group(1) if m else ""


_FM_ITEM = re.compile(r"^( +)-\s+\S")


def _strip_yaml_comment(value: str) -> str:
    """Drop a trailing `# …` comment from a scalar, honouring quotes.

    `open_questions: []   # all four resolved 2026-07-25` is the live shape in
    spec-pyforge-atlas, and a naive reader calls that an unrecognised value and warns about
    a file that is perfectly well-formed. A `#` inside quotes is content, not a comment.
    """
    quote = None
    for i, ch in enumerate(value):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1].isspace()):
            return value[:i].strip()
    return value.strip()


def _spec_open_questions(project: str, dream: str) -> int:
    """Unresolved `open_questions[]` in THIS CHAIN's SPEC.md (0 when none).

    CHAIN-scoped, matching the `spec` stage's `spec-{dream}/SPEC.md` rule — not
    project-scoped. A project hosts many chains (Charter §5 as amended), so globbing
    `spec-*/SPEC.md` and returning the first non-empty count credited one chain's
    unanswered questions to a DIFFERENT chain's row. Measured before the fix: all five
    `overtaken` badges named a chain whose own SPEC.md was clean — steward was wearing
    `spec-enterprise-airgap`'s question, marshal `spec-agent-tool-surface`'s, and atlas +
    unity-data-stack + wasm-analytics-stack were all wearing the same six from
    `spec-upstream-discovery` — while those three chains, the only ones that really carry
    open questions, have no Fleet row at all. The lookup was left project-keyed when the
    rows themselves were converted to chain-keyed (see `scan_fleet`).

    Parsed with stdlib rather than PyYAML deliberately. That lazy `import yaml` was this
    generator's ONLY third-party import and it sat inside a blanket `except Exception`,
    so on CI — which runs the generator on a bare `actions/setup-python` interpreter with
    no PyYAML, the pixi env never being activated for that step — the import raised, the
    except swallowed it, and the published board reported 0 open questions for all 13 rows
    while the local board reported 5. A dependency that exists only locally is worse than
    no dependency: it makes the two boards disagree with neither one erroring.
    """
    smd = (REPO_ROOT / "_bmad-output" / "projects" / project / "planning-artifacts" /
           "specs" / f"spec-{dream}" / "SPEC.md")
    if not smd.is_file():
        return 0
    lines = smd.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return 0
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), -1)
    if end < 0:
        print(f"[fleet] WARN {smd}: frontmatter is never closed — reporting 0")
        return 0
    fm = lines[1:end]
    key = next((i for i, ln in enumerate(fm) if ln.startswith("open_questions:")), -1)
    if key < 0:
        return 0
    inline = _strip_yaml_comment(fm[key].split(":", 1)[1])
    if inline:
        if not (inline.startswith("[") and inline.endswith("]")):
            # Anything else (an anchor, a folded scalar) is a shape this reader does not
            # understand. Say so — silently answering 0 is the defect being removed.
            print(f"[fleet] WARN {smd}: unrecognised open_questions value {inline!r} "
                  f"— reporting 0")
            return 0
        return len([x for x in inline[1:-1].split(",") if x.strip()])
    # Block list. Count only items at the FIRST item's indent, so a wrapped continuation
    # line and any nested list are not miscounted as questions of their own.
    count, indent = 0, None
    for ln in fm[key + 1:]:
        if ln.strip() and not ln.startswith((" ", "\t")):
            break  # the next top-level key ends the list
        m = _FM_ITEM.match(ln)
        if not m:
            continue
        if indent is None:
            indent = len(m.group(1))
        if len(m.group(1)) == indent:
            count += 1
    return count


def _stage_globs(slug: str, project: str, primary: bool) -> dict[str, list[str]]:
    """Where each stage's artifacts live for ONE chain.

    Chain-scoped first, always. A chain may claim the project-ROOT artifacts (`prd.md`,
    `architecture.md`, `epics.md`, the flat `research/`, the package, the deck) only when
    it is PRIMARY — its slug names its own project, i.e. it is the station's own chain.
    Those belong to the station, not to every chain parked in its tree; crediting them to
    satellites is what let unity-data-stack and wasm-analytics-stack each report a complete
    9/9 chain while owning neither epics nor code.

    `research`, `gates` and `retro` have no chain component in the repo's naming convention
    yet (unlike prd/arch/brief/epics, which all carry `-<chain>-`), so the chain-scoped
    globs here match a slug ANYWHERE in the name and will start resolving as the migration
    adds it. Until then those artifacts answer only for the primary chain, and
    `unattributed` below reports what that leaves unaccounted for.
    """
    if project == GOVERNANCE_DIR:
        # Guild-owned, constitutive: no product, no Smith-shaped scaffolding. Only
        # dream/deck/spec apply -- everything else stays an empty glob (never matches, so
        # the stage stays unreached and `required` never grows past `spec` for this chain).
        gdir = f"{GOVERNANCE_DIR}/spec-{slug}"
        empty: list[str] = []
        return {
            "dream": [f"docs/dreams/{slug}.md"],
            "deck": [f"presentations/{slug}/project/*.html"],
            "spec": [f"{gdir}/SPEC.md", f"{gdir}/.memlog.md"],
            "research": empty, "brief": empty, "prd": empty, "ux": empty, "arch": empty,
            "context": empty, "epics": empty, "sprint": empty, "tea": empty, "gates": empty,
            "code": empty, "verify": empty, "retro": empty,
        }
    pa = f"_bmad-output/projects/{project}/planning-artifacts"
    proj = f"_bmad-output/projects/{project}"
    g: dict[str, list[str]] = {
        "dream":    [f"docs/dreams/{slug}.md"],
        "deck":     [f"presentations/{slug}/project/*.html"],
        # The memlog joins the spec stage on purpose. `SPEC.md` carries no path date and no
        # `updated:`, so its currency fell through to git last-touched — which the 2026-07-29
        # promotion wave set for nearly every spec at once, producing 11 identical and
        # meaningless `spec newer than prd` findings. The sibling `.memlog.md` IS the spec's
        # change log and does carry `updated:`, so it answers the question honestly.
        "spec":     [f"{pa}/specs/spec-{slug}/SPEC.md", f"{pa}/specs/spec-{slug}/.memlog.md"],
        # Station research is INHERITED by its satellites, and marked as such (see
        # `_subscore`). The three disciplines were commissioned once per station and the
        # satellite chains genuinely draw on them; calling that a gap on 23 chains would
        # invent work that was already done. A chain that commissions its own research
        # names itself in the filename and stops being marked inherited.
        "research": [f"{pa}/research/*{slug}*.md", f"{pa}/research/*.md"],
        "brief":    [f"{pa}/product-brief-{slug}*.md",
                     f"{pa}/briefs/brief-{slug}-*/brief*.md"],
        "prd":      [f"{pa}/prds/prd-{slug}-*/prd.md"],
        "ux":       [f"{pa}/ux-{slug}*.md", f"{pa}/ux/{slug}*.md"],
        "arch":     [f"{pa}/architecture/architecture-{slug}-*/*.md"],
        # BMAD-METHOD 6.12.0 ships `persistent_facts = []`; the project-context surface is now
        # a `bmad:context` managed block (D1, Story 30.2, 2026-09-06), not a per-station
        # rulebook file. Every chain resolves the shared root AGENTS.md; a station whose
        # content warranted `bmad-project-context`'s "child" split (subtree-exclusive,
        # substantial -- pyforge-atlas is the first) also gets its own block at
        # src/shared/packages/<slug>/AGENTS.md, so both paths count.
        "context":  ["AGENTS.md", f"src/shared/packages/{slug}/AGENTS.md"],
        "epics":    [f"{pa}/epics-{slug}.md"],
        "sprint":   [f"{pa}/sprint-status-ledger-{slug}.yaml"],
        # CAP-1, spec-pyforge-testing-charter (2026-08-02): real tests live at the
        # canonical src/shared/packages/pyforge-<slug>/tests/ location per the root
        # AGENTS.md's `bmad:context` block's workspace-package convention -- NOT under
        # _bmad-output/projects/<slug>/tests/, which holds only planning-scaffold
        # mocks/fixtures (or, for 6 of 8 stations, nothing but empty __init__.py
        # stubs). The old glob undercounted every station's real coverage.
        "tea":      [f"src/shared/packages/{slug}/tests/**/test_*.py",
                     f"src/shared/packages/{slug}/tests/**/*.spec.ts"],
        "gates":    [f"{pa}/implementation-readiness-report*{slug}*.md",
                     f"{pa}/validation-report-PRD*{slug}*.md"],
        "code":     [f"src/shared/packages/{slug}/pyproject.toml"],
        "verify":   [],   # not a file — a declared gate; resolved in scan_fleet
        "retro":    [f"{pa}/retros/*{slug}*.md"],
    }
    if primary:
        g["deck"] += [f"presentations/{project}/project/*.html"]
        g["research"] += [f"{pa}/research/*.md"]
        g["brief"] += [f"{pa}/product-brief*.md"]
        g["prd"] += [f"{pa}/prd.md", f"{pa}/PRD.md"]
        g["ux"] += [f"{pa}/ux*.md"]
        g["arch"] += [f"{pa}/architecture.md"]
        g["epics"] += [f"{pa}/epics.md"]
        g["sprint"] += [f"{pa}/sprint-status-ledger.yaml"]
        g["gates"] += [f"{pa}/implementation-readiness-report*.md",
                       f"{pa}/validation-report-PRD*.md"]
        g["retro"] += [f"{pa}/retros/*.md"]
    return g


def _subscore(stage: str, slug: str, project: str, primary: bool,
              paths: list[str], pitch: dict) -> dict | None:
    """`{have, of, missing}` for a stage whose dot stands for a SET, else None.

    A single green dot for `research` hid five projects missing an entire discipline, and a
    single green dot for `deck` hid a partial family. A set-valued stage reports partial.
    """
    if stage == "research":
        have = {t: any(Path(p).name.startswith(t + "-") for p in paths)
                for t in RESEARCH_TYPES}
        own = [p for p in paths if slug in Path(p).name]
        return {"have": have, "n": sum(have.values()), "of": len(have),
                "missing": sorted(k for k, v in have.items() if not v),
                "inherited": bool(paths) and not own and not primary}
    elif stage == "deck":
        card = pitch.get(slug) or (pitch.get(project) if primary else None)
        have = dict(card["have"]) if card else {k: False for k in DECK_FAMILY}
    else:
        return None
    return {"have": have, "n": sum(have.values()), "of": len(have),
            "missing": sorted(k for k, v in have.items() if not v)}


def _dream_chain_orphan_index() -> dict[str, list[str]]:
    """Once-per-``scan_fleet`` map: project slug -> failing dream-chain kinds."""
    try:
        from pyforge.doctor.sources.chain import dream_chain_orphan_index

        return dream_chain_orphan_index(REPO_ROOT)
    except Exception as exc:  # noqa: BLE001 -- dashboard still renders
        print(f"[fleet] WARN dream-chain orphan index unavailable: {exc}")
        return {}


def _chain_audit_verdict(row: dict, orphan_kinds: list[str]) -> dict:
    """CAP-3 pass/fail per checkpoint — live row signals + dream-chain orphans.

    Story 21.1 / FR-192 CAP-3: extends layer-presence (17.3) with
    coherence, staleness, and orphan-freedom. Never a cached per-station table.
    """
    gaps = row.get("gaps") or []
    partial = row.get("partial") or []
    stale_by = row.get("staleBy") or []
    layers_pass = not gaps and not partial
    coherence_pass = (
        not row.get("noDream") and not row.get("unowned") and not row.get("overtaken")
    )
    staleness_pass = not stale_by
    orphans_pass = not orphan_kinds
    checkpoints = {
        "layers": {"pass": layers_pass, "gaps": gaps, "partial": partial},
        "coherence": {
            "pass": coherence_pass,
            "noDream": bool(row.get("noDream")),
            "unowned": bool(row.get("unowned")),
            "overtaken": bool(row.get("overtaken")),
        },
        "staleness": {"pass": staleness_pass, "staleBy": stale_by},
        "orphans": {"pass": orphans_pass, "kinds": sorted(set(orphan_kinds))},
    }
    verdict = all(cp["pass"] for cp in checkpoints.values())
    return {"verdict": "pass" if verdict else "fail", "checkpoints": checkpoints}


def scan_fleet(projects: dict, pitch_cards: list[dict] | None = None) -> dict:
    """Per-CHAIN Dream-to-Code state: stages, sub-scores, currency, gaps, version."""
    from datetime import date
    today = date.today()
    pitch = {c["slug"]: c for c in (pitch_cards or [])}
    tasks = _pixi_tasks()
    orphan_index = _dream_chain_orphan_index()
    rows, unattributed = [], []
    for slug, project, owner, dstatus, parent in _fleet_chains():
        primary = (slug == project)
        globs = _stage_globs(slug, project, primary)
        stages, updated_at, files = {}, {}, {}
        for st in FLEET_STAGES:
            if st == "verify":
                # Not a file. A chain verifies when the workspace declares a gate for it.
                candidates = [f"{slug}-test", f"{project}-test"] + list(FLEET_VERIFY_ALIAS.get(slug, ()))
                gate = next((t for t in candidates if t in tasks), "")
                stages[st] = stages.get("code", "") if gate else ""
                updated_at[st] = updated_at.get("code", "")
                files[st] = [gate] if gate else []
                continue
            found = _resolve(globs[st])
            files[st] = found
            stages[st], updated_at[st] = _stage_dates(found)
        na = set(FLEET_NA.get(slug, set())) | (set() if slug in FLEET_UX else {"ux"})
        if parent:
            na |= {"dream"}
        # Deck-on-demand (operator ruling 2026-08-27, from the pyforge-unifying-strategy
        # pilot): a deck is REQUIRED only for a station flagship chain or where one
        # already exists. Every other chain reads n/a rather than a standing gap — the
        # pilot showed deck cost scales with the grounding corpus, and a chain without a
        # rich SPEC pack yields a thin deck or forces invention. DERIVED, not declared:
        # a satellite that gains presentations/<slug>/ is measured again automatically.
        if not primary and not files["deck"]:
            na |= {"deck"}
        sub = {st: s for st in FLEET_SUBSCORE
               if (s := _subscore(st, slug, project, primary, files[st], pitch))}
        reached = [s for s in FLEET_STAGES if stages[s]]
        furthest = reached[-1] if reached else "dream"
        # REQUIRED = every stage up to and including the furthest one reached. A chain that
        # got to `code` owes everything before it; a chain that only reached `spec` is judged
        # on dream/deck/spec alone. That turns the row from "how far along" into "is this
        # chain sound", and it self-scales instead of showing a dreamt chain 13 red dots.
        cut = FLEET_STAGES.index(furthest)
        required = [s for s in FLEET_STAGES[:cut + 1] if s not in na]
        gaps = [s for s in required if not stages[s]]
        partial = [st for st, s in sub.items() if s["n"] and s["n"] < s["of"]]
        project_path = (f"{GOVERNANCE_DIR}/spec-{slug}" if project == GOVERNANCE_DIR
                        else f"_bmad-output/projects/{project}")
        updated = _last_touched([f"docs/dreams/{slug}.md", project_path]
                                + ([f"presentations/{project}", f"src/shared/packages/{project}"]
                                   if primary else [f"presentations/{slug}"]))
        age = ""
        if updated:
            try:
                y, m, d = (int(x) for x in updated.split("-"))
                age = (today - date(y, m, d)).days
            except ValueError:
                age = ""
        prog = ""
        pkey = project.removeprefix("pyforge-") if primary else ""
        if pkey and pkey in projects:
            st_ = [s for e in projects[pkey]["epics"] for s in e["stories"]]
            prog = f"{sum(1 for s in st_ if s[1] == 'done')}/{len(st_)}"
        # Ordering is judged on the chain's OWN artifacts. An inherited stage carries the
        # station's date, not this chain's, so counting it invented ordering inversions —
        # it took `backfilled` from 16 chains to 25 the moment research inheritance landed,
        # which is the signal decaying into noise rather than 9 chains becoming backfilled.
        inherited = {st for st, s in sub.items() if s.get("inherited")}
        seq = [stages[s] for s in FLEET_STAGES if stages[s] and s not in inherited]
        backfilled = seq != sorted(seq)
        open_q = _spec_open_questions(project, slug)
        overtaken = bool(open_q) and bool(stages["prd"]) and bool(stages["arch"])
        stale_by = _currency(slug, stages, updated_at, na, today,
                             realized=(dstatus == "realized"))
        if (sub.get("research") or {}).get("inherited"):
            unattributed.append(slug)
        row = {
            "label": FLEET_LABELS.get(slug) or slug.removeprefix("pyforge-"),
            "slug": slug, "project": project, "dream": slug, "owner": owner,
            "stages": stages, "updatedAt": updated_at, "sub": sub,
            "archived": dstatus == "archived", "dreamStatus": dstatus,
            # A chain without its OWN Dream file is only a Dream-first violation when it
            # also names no parent. Charter §5 lets one Dream spawn several Specs, and such
            # a Spec declares `owner-dream:` — that is a sub-chain, not unattributed work.
            "ownerDream": parent, "noDream": not stages["dream"] and not parent,
            "unowned": not owner,
            "backfilled": backfilled, "openQuestions": open_q, "overtaken": overtaken,
            "na": sorted(na), "required": required, "gaps": gaps, "partial": sorted(partial),
            "staleBy": stale_by, "furthest": furthest, "updated": updated, "age": age,
            "stale": isinstance(age, int) and age > _STALE_DAYS,
            "version": _pkg_version(project) if primary else "", "progress": prog,
            "complete": len(required) - len(gaps), "of": len(required),
        }
        row["chainAudit"] = _chain_audit_verdict(
            row, orphan_index.get(project, []) if project else []
        )
        rows.append(row)
    live = [r for r in rows if not r["archived"]]
    sound = [r for r in live if not r["gaps"] and not r["partial"] and not r["staleBy"]]
    flags = {k: [r["slug"] for r in live if r[k]]
             for k in ("noDream", "unowned", "overtaken", "backfilled")}
    reached = sum(1 for r in live if not r["gaps"])
    print(f"[fleet] {len(rows)} chains ({len(live)} live, {len(rows) - len(live)} archived) · "
          f"{len(sound)} sound · {reached} no-gap · {sum(len(r['gaps']) for r in live)} gap(s) · "
          f"{sum(len(r['partial']) for r in live)} partial set(s) · "
          f"{sum(len(r['staleBy']) for r in live)} currency finding(s)")
    for k, v in flags.items():
        if v:
            print(f"[fleet]   {k}: {', '.join(v)}")
    if unattributed:
        print(f"[fleet]   research inherited from the station (no chain-scoped research of "
              f"its own): {len(unattributed)} chain(s)")
    return {"stages": list(FLEET_STAGES), "staleDays": _STALE_DAYS,
            "shelfLife": {s: _SHELF_LIFE.get(s, _SHELF_LIFE_DEFAULT) for s in FLEET_STAGES},
            "sound": len(sound), "live": len(live), "reached": reached,
            "gaps": sum(len(r["gaps"]) for r in live),
            "findings": sum(len(r["staleBy"]) for r in live),
            "rows": rows}


# Which stage must not be older than which. A chain is a pipeline: research feeds the
# brief, the brief the PRD, the PRD the architecture, and so on. An upstream artifact
# DATED AFTER the thing built from it means the input moved and the output was never
# re-derived — the live defect `backfilled` deliberately does not cover, because
# `backfilled` describes true history (a chain retro-fitted after the fact) while this
# describes a contract that has quietly gone out of date.
_FEEDS = (("research", "brief"), ("brief", "prd"), ("prd", "arch"), ("spec", "prd"),
          ("arch", "epics"), ("code", "retro"))
# `("epics", "sprint")` deliberately excluded (2026-09-04): the tracked sprint ledger is a
# GENERATED twin of the Tier-3 feed with no frontmatter, so its `updated` is git last-touch,
# and `sprint-ledger-sync` writes nothing when no status changed. On an idle station the
# ledger therefore cannot move, and any currency-only epics re-stamp left a permanent
# "epics newer than sprint" finding (scribe, 2026-09-04) that no honest act could clear --
# the runbook's "self-heals, the ledger stamps daily" premise does not hold. The question
# the edge asked -- did the ledger follow the epics? -- is answered exactly, by content,
# by chain-completeness INV-B (epics.md story ids == ledger keys, both directions), which
# fires the moment a story is minted without its key. The sprint stage still counts for
# layer presence and shelf life.
# `("prd", "gates")` deliberately excluded: a readiness report is a point-in-time snapshot
# of a check that ran once, not a living document meant to track the PRD's every touch --
# an administrative PRD bump does not mean the check needs re-running. `_SHELF_LIFE_DEFAULT`
# (90 days) already covers the real question, "has this gate gone stale on its own merits."

# A spec's `.memlog.md` gets a fresh `updated:` on every append -- routine corrections,
# validation passes, cross-reference fixes -- far more often than its PRD is touched. A
# same-day or next-day gap is that normal cadence, not "the input moved and the output was
# never re-derived". Below this many days, a feed pair does not count as stale; the same
# "always red, gets ignored" trap this module already suppresses for `behind-code`.
_FEEDS_GRACE_DAYS = 2


def _currency(slug: str, stages: dict, updated_at: dict, na: set, today,
              realized: bool = False) -> list[dict]:
    """Every way this chain's artifacts are out of date. Empty list when current."""
    from datetime import date
    out = []
    for up, down in _FEEDS:
        u, d = updated_at.get(up, ""), updated_at.get(down, "")
        if u and d and u > d and up not in na and down not in na:
            try:
                uy, um, ud = (int(x) for x in u[:10].split("-"))
                dy, dm, dd = (int(x) for x in d[:10].split("-"))
                gap_days = (date(uy, um, ud) - date(dy, dm, dd)).days
            except ValueError:
                gap_days = _FEEDS_GRACE_DAYS + 1  # unparseable date: don't silently suppress
            if gap_days > _FEEDS_GRACE_DAYS:
                out.append({"kind": "feeds", "stage": up, "than": down, "at": u, "other": d})
    for st in FLEET_STAGES:
        life = _SHELF_LIFE.get(st, _SHELF_LIFE_DEFAULT)
        when = updated_at.get(st, "")
        if life is None or not when or st in na:
            continue
        try:
            y, m, dd = (int(x) for x in when.split("-"))
        except ValueError:
            continue
        days = (today - date(y, m, dd)).days
        if days > life:
            out.append({"kind": "shelf", "stage": st, "at": when, "days": days, "life": life})
    # The contract has fallen behind the implementation: a spec/PRD/architecture older than
    # the last change to the code it governs.
    #
    # SUPPRESSED once the Dream is `realized`. A shipped chain's code goes on moving —
    # bug fixes, follow-up reviews, dependency bumps — so this would pin warden and atlas
    # permanently red for behaving normally, and a board that is always red gets ignored.
    # The signal is aimed at chains still being built, where a contract falling behind the
    # code means the contract stopped being the thing that drives it. Stale-by-dependency
    # still applies to realized chains, because THAT compares two contracts and stays
    # meaningful after ship.
    code = updated_at.get("code", "")
    if not realized:
        for st in ("spec", "prd", "arch"):
            when = updated_at.get(st, "")
            if code and when and when < code and st not in na:
                out.append({"kind": "behind-code", "stage": st, "at": when, "other": code})
    return out


# ---- pitch roster (the deck family) ------------------------------------------

PITCH_TITLES = {"agentic-sdlc": "Agentic AI across the SDLC"}
# the 6-artifact family standard, per docs/specs/presentation-deck.md
_PITCH_CHECK = ("prototype", "exec", "infographic", "marp", "standalone", "pptx")
# spec-design-sync-loop CAP-2 (Story 23.2): presentations/_design-systems/ is
# a library home (Modernist/Broadsheet/Nocturne, mirrored not authored), not
# a deck; six-quarter-roadmap/ and llm-knowledge-bases/ are local twins that
# do not follow the deck-family build pipeline either (each one's own README
# says so) -- scoring any of the three against the 6-artifact standard would
# report a permanent, meaningless partial "deck".
_NOT_A_DECK = frozenset({"_design-systems", "six-quarter-roadmap", "llm-knowledge-bases"})


def scan_pitch() -> list[dict]:
    cards: list[dict] = []
    for deck_dir in sorted((REPO_ROOT / "presentations").iterdir()):
        if not deck_dir.is_dir() or deck_dir.name in _NOT_A_DECK:
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


# ---- command center (SDLC phase-grouped view) --------------------------------

def scan_readiness() -> dict:
    """What can actually be launched right now" — the question the board could not
    answer before 2026-08-08.

    Distinct from the Command Center, which reports whether an ARTIFACT EXISTS per SDLC
    phase. This reports whether WORK CAN START: how much of each station is done, what
    the next runnable story is, what is blocked, and — critically — where readiness is
    UNKNOWN rather than green.

    Derived entirely from the tracked ledgers via `parse_sprint_status` (never a regex:
    atlas keys stories `a1-`/`b2-` by design, and an `^\\d+-\\d+` assumption produced
    three wrong findings on 2026-08-08, one of them published and retracted).
    """
    rows, totals = [], collections.Counter()
    for key in sorted(PROJECT_SOURCES):
        resolution = resolve_project(key)
        slug = resolution.project_dir
        if slug is None or resolution.ledger_path is None:
            continue
        ledger = REPO_ROOT / resolution.ledger_path
        if not ledger.is_file():
            continue
        statuses = {k: v for k, v in parse_sprint_status(ledger).items()
                    if not k.startswith("epic-")}
        if not statuses:
            continue
        counts = collections.Counter(statuses.values())
        totals.update(counts)
        nxt = sorted(k for k, v in statuses.items() if v == "backlog")
        blocked = sorted(k for k, v in statuses.items() if v == "blocked")
        pa = f"_bmad-output/projects/{slug}/planning-artifacts"
        specs_dir = REPO_ROOT / pa / "specs"
        open_specs = []
        if specs_dir.is_dir():
            for sm in sorted(specs_dir.glob("spec-*/SPEC.md")):
                st = ""
                try:
                    head = sm.read_text(encoding="utf-8").split("---")[1]
                    m = re.search(r"^status:\s*(\S+)", head, re.M)
                    st = m.group(1).strip() if m else ""
                except Exception:
                    pass
                if st in ("draft", "ready", "in-progress"):
                    open_specs.append({"slug": sm.parent.name, "status": st,
                                       "path": f"{pa}/specs/{sm.parent.name}/SPEC.md"})
        rows.append({
            "station": key,
            "project": slug,
            "epicsPath": f"{pa}/epics.md",
            "ledgerPath": f"{pa}/sprint-status-ledger.yaml",
            "specsPath": f"{pa}/specs",
            "openSpecs": open_specs,
            "done": counts.get("done", 0),
            "backlog": counts.get("backlog", 0),
            "blocked": counts.get("blocked", 0),
            "total": len(statuses),
            "next": nxt[0] if nxt else "",
            "blockedKeys": blocked[:8],
            "backlogKeys": nxt[:8],
            # A station with nothing runnable is not "ready" — it is finished or stuck,
            # and the board should say which rather than rendering an empty cell.
            "state": ("complete" if counts.get("done", 0) == len(statuses)
                      else "blocked" if not nxt and blocked
                      else "ready" if nxt else "idle"),
        })
    rows.sort(key=lambda r: (-r["backlog"], r["station"]))
    return {
        "rows": rows,
        "totals": {"done": totals.get("done", 0), "backlog": totals.get("backlog", 0),
                   "blocked": totals.get("blocked", 0), "total": sum(totals.values())},
    }


def _implementation_gate() -> str:
    """The IMPLEMENTATION phase gate, derived from each station's tracked ledger.

    Replaces a hardcoded literal. Reads the SAME tracked ledgers the readiness
    view uses, via `parse_sprint_status`, so the gate cannot disagree with the
    numbers rendered beside it — and never re-parses with an ad-hoc regex, which
    under-counts any station keying stories outside `<int>-<int>`.
    """
    complete, building = [], []
    for station in sorted(STATIONS):  # STATIONS is a tuple of station names
        ledger = (REPO_ROOT / "_bmad-output" / "projects" / f"pyforge-{station}"
                  / "planning-artifacts" / "sprint-status-ledger.yaml")
        if not ledger.is_file():
            continue
        statuses = parse_sprint_status(ledger)
        stories = {k: v for k, v in statuses.items() if not k.startswith("epic-")}
        if not stories:
            continue
        done = sum(1 for v in stories.values() if v == "done")
        (complete if done == len(stories) else building).append(station)
    if not (complete or building):
        return "no tracked ledger readable — status unknown"
    parts = []
    if complete:
        parts.append(f"{len(complete)} complete ({', '.join(complete)})")
    if building:
        parts.append(f"{len(building)} building ({', '.join(building)})")
    return "; ".join(parts)


def scan_command_center(fleet: dict) -> dict:
    """PyForge Guild Fleet view grouped by SDLC phases.

    Derives from fleet data: maps each station/project's artifacts to their
    corresponding SDLC phases (ANALYSIS → PLANNING → SOLUTIONING → IMPLEMENTATION).
    Status indicators reflect actual artifact existence from the fleet.
    Aggregates per-station data (showing only primary chain per station per phase).
    """
    # Map fleet stages to SDLC phases
    phase_map = {
        "analysis": ["dream", "research", "brief", "deck"],
        "planning": ["prd"],
        "solutioning": ["arch", "epics", "context"],
        "implementation": ["sprint", "code", "verify", "retro"]
    }

    # Station info: emoji + full name mapping (in display order)
    # Order + membership come from the imported STATIONS (single source of truth, shared
    # with scripts/bmad_drift_check.py) rather than a separately hand-typed list — a 9th
    # station added to STATIONS used to be silently omitted from the Command Center table.
    # Display metadata (emoji) has no home in STATIONS itself, so it stays a local lookup,
    # but with a graceful fallback: an unmapped station still renders (title-cased slug,
    # generic emoji) instead of vanishing.
    station_order = list(STATIONS)
    _STATION_EMOJI = {
        "herald": "🎺", "marshal": "⚔️", "atlas": "🗺️", "warden": "🛡️",
        "mason": "🧱", "doctor": "🏥", "scribe": "📖", "steward": "👑",
    }
    station_info = {
        slug: (_STATION_EMOJI.get(slug, "🔹"), slug.title())
        for slug in STATIONS
    }

    # Artifact display names
    artifact_labels = {
        "dream": "DREAMS",
        "research": "res",
        "brief": "prod-brief",
        "deck": "PITCH-DECKS",
        "prd": "PRD",
        "arch": "arch",
        "epics": "epics",
        "context": "specs",
        "sprint": "sprint-status",
        "code": "code",
        "verify": "tests",
        "retro": "retro"
    }

    # Build per-station fleet summary (one row per station, aggregating all chains)
    station_fleets = {}
    for row in fleet.get("rows", []):
        owner = row.get("owner", "").lower()
        if owner not in station_info:
            continue
        # Take the first (primary) row per station if multiple exist
        if owner not in station_fleets:
            station_fleets[owner] = row

    # Build phase data from aggregated fleet
    phases = []
    phase_info = {
        "analysis": {
            "name": "ANALYSIS Phase",
            "flow": "Dream → Pitch deck",
            "artifacts": ["DREAMS", "res-domain", "res-market", "res-tech", "prod-brief", "PITCH-DECKS"],
            "gate": "All 8 stations complete analysis"
        },
        "planning": {
            "name": "PLANNING Phase",
            "flow": "PRD requirements",
            "artifacts": ["PRD"],
            "gate": "All 8 stations have PRD"
        },
        "solutioning": {
            "name": "SOLUTIONING Phase",
            "flow": "Architecture → specs",
            "artifacts": ["arch", "epics", "specs"],
            "gate": "All 8 stations complete solutioning"
        },
        "implementation": {
            "name": "IMPLEMENTATION Phase",
            "flow": "Code → ship + retro",
            "artifacts": ["sprint-status", "code", "tests", "retro"],
            # DERIVED, not asserted. This read "Herald coding; others queued or
            # ready" as a hardcoded literal until 2026-08-08 — stale prose from an
            # era when that was true. Herald has been 47/47 for days and five
            # stations are mid-build, so the gate was describing a fleet that no
            # longer existed. A hand-typed status line has no refresh path and
            # therefore no way to stop being wrong.
            "gate": _implementation_gate()
        }
    }

    for phase_id, phase_config in phase_info.items():
        phase_stages = phase_map.get(phase_id, [])
        stations = []

        # Build station rows in defined order
        for owner in station_order:
            if owner not in station_fleets:
                continue

            row = station_fleets[owner]
            emoji, name = station_info[owner]
            statuses = {}

            # Derive status for each artifact in this phase
            for stage in phase_stages:
                if stage == "research":
                    # `research` is a SET (domain/market/technical), not one file --
                    # a single combined dot hid stations missing a whole discipline
                    # (see `_subscore`). Emit one status per RESEARCH_TYPES entry so
                    # it matches the analysis phase's res-domain/res-market/res-tech
                    # artifact labels instead of falling through to '◯' for all three.
                    have = (row.get("sub", {}).get("research") or {}).get("have", {})
                    for rtype in RESEARCH_TYPES:
                        label = f"res-{'tech' if rtype == 'technical' else rtype}"
                        statuses[label] = "✅" if have.get(rtype) else "◯"
                    continue

                has_stage = bool(row.get("stages", {}).get(stage, ""))

                # Determine status indicator based on artifact existence
                if stage == "dream" and has_stage:
                    status = "🚀"  # active
                elif has_stage:
                    status = "✅"  # complete
                else:
                    status = "◯"  # not started

                # Map stage to artifact label
                label = artifact_labels.get(stage, stage)
                statuses[label] = status

            stations.append({
                "name": name,
                "emoji": emoji,
                "statuses": statuses
            })

        phases.append({
            "id": phase_id,
            "name": phase_config["name"],
            "flow": phase_config["flow"],
            "artifacts": phase_config["artifacts"],
            "gate": phase_config["gate"],
            "stations": stations
        })

    return {"phases": phases}


# ---- open work (the tracked deferred-work ledgers) ---------------------------

_DW_HEAD = re.compile(r"^#{2,4}\s+(DW-[A-Za-z0-9][A-Za-z0-9-]*)\s*[—:-]?\s*(.*)$", re.MULTILINE)
_DW_STATUS = re.compile(r"^\s*status:\s*(\S.*?)\s*$", re.MULTILINE)
_DW_SEVERITY = re.compile(r"^\s*severity:\s*(\w+)", re.MULTILINE)
# atlas encodes severity in the heading — `## DW-B1-1 — title (HIGH, context)`.
_DW_SEV_HEAD = re.compile(r"\((CRITICAL|HIGH|MEDIUM|LOW)\b", re.IGNORECASE)
# `verified:` is the sweep-protocol result line — an entry checked against the actual code
# with file:line or a measured count as evidence. `resolution:` is the older annotation for
# the same thing. Either means a human (or this protocol) has LOOKED; a bare `open` with
# neither means the ledger's word is all we have.
_DW_RESOLUTION = re.compile(r"^\s*(?:resolution|verified):\s*\S", re.MULTILINE)
_SEVERITIES = ("critical", "high", "medium", "low", "unspecified")


def scan_deferred() -> dict:
    """Open deferred work per project, from the TRACKED ledgers.

    This is the factory's largest body of known-but-unscheduled work and it had NO board
    surface at all — 143 entries across five ledgers, invisible to anyone not reading the
    files. It could not be surfaced earlier because four incompatible shapes and 82 entries
    without ids left nothing stable to count; the 2026-07-30 normalization is what made this
    function possible.

    The `verified` count is reported separately and deliberately: 134 of the status lines
    were added mechanically by that normalization, which recorded what the ledger SAID, not
    what the code shows. An entry carrying a `resolution:` or a non-bare status has actually
    been triaged; a bare `open` means nobody has checked. Reporting one number for both
    would repeat the conflation that hid this work in the first place.
    """
    projects, totals = [], {"open": 0, "done": 0, "triaged": 0}
    by_sev: dict[str, int] = {s: 0 for s in _SEVERITIES}
    for led in sorted(REPO_ROOT.glob(
            "_bmad-output/projects/*/planning-artifacts/deferred-work-ledger.md")):
        slug = led.parts[-3]
        text = led.read_text(encoding="utf-8")
        marks = [(m.start(), m.group(1), m.group(2)) for m in _DW_HEAD.finditer(text)]
        rows = []
        for i, (pos, ident, title) in enumerate(marks):
            body = text[pos:marks[i + 1][0] if i + 1 < len(marks) else len(text)]
            sm = _DW_STATUS.search(body)
            status = (sm.group(1) if sm else "open").strip()
            done = status.lower().startswith(("done", "closed", "superseded", "resolved"))
            sev = (_DW_SEVERITY.search(body) or _DW_SEV_HEAD.search(title))
            sev = (sev.group(1).lower() if sev else "unspecified")
            if sev not in by_sev:
                sev = "unspecified"
            triaged = bool(_DW_RESOLUTION.search(body)) or status.lower() != "open"
            rows.append({"id": ident, "title": title.strip()[:120],
                         "status": "done" if done else "open",
                         "severity": sev, "triaged": triaged})
            totals["done" if done else "open"] += 1
            if not done:
                by_sev[sev] += 1
                totals["triaged"] += bool(triaged)
        projects.append({
            "project": slug, "path": str(led.relative_to(REPO_ROOT)),
            "open": sum(1 for r in rows if r["status"] == "open"),
            "done": sum(1 for r in rows if r["status"] == "done"),
            "triaged": sum(1 for r in rows if r["status"] == "open" and r["triaged"]),
            "entries": rows,
        })
    projects.sort(key=lambda p: -p["open"])
    print(f"[open-work] {totals['open']} open · {totals['done']} done across "
          f"{len(projects)} ledger(s) · {totals['triaged']} of the open entries have been "
          f"verified against the code, {totals['open'] - totals['triaged']} have not")
    return {"open": totals["open"], "done": totals["done"],
            "triaged": totals["triaged"], "bySeverity": by_sev, "projects": projects}


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

def _decomposed_satellites(dreams: list[dict]) -> set[str]:
    """Dream slugs whose Spec is decomposed into their owner station's epics.

    The same test `chain-completeness` INV-A applies (`spec-<slug>` named in the
    station's own prose), read here so the console's "is it building?" question is
    answered by the chain rather than by a hand-maintained station map. A Dream with
    no owner, no project tree, or an unreadable epics.md simply is not counted --
    absence of evidence stays absence, never a claim of motion.
    """
    out: set[str] = set()
    for d in dreams:
        owner = d.get("owner") or ""
        slug = d.get("slug") or ""
        if not owner or not slug or owner == "guild":
            continue
        pa = REPO_ROOT / f"_bmad-output/projects/pyforge-{owner}/planning-artifacts"
        # INV-A's own test, mirrored EXACTLY: `spec-<slug>` OR the bare slug, across the
        # station's PRD + epics prose (board.py `_check_project_chain_completeness`).
        # A narrower `spec-<slug>`-only match missed steward's Epic 8, which decomposes
        # `jira-github-projects-sync` while citing it through its architecture document
        # rather than its spec filename -- an epic with a story RUNNING at the time the
        # panel still called that Dream "owned, not started".
        prose = ""
        for doc in list(pa.glob("prds/*/prd.md")) + list(pa.glob("epics*.md")):
            try:
                prose += doc.read_text(encoding="utf-8")
            except OSError:
                continue
        if f"spec-{slug}" in prose or slug in prose:
            out.add(slug)
    return out


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
    # PROGRAM_DREAM maps a project to its STATION Dream, so the set above can only
    # ever hold the 9 station slugs -- a SATELLITE Dream (one whose work lives inside
    # a station's epics rather than in its own build line) was structurally unable to
    # read as building, and sat in BACKLOG forever no matter how far it got. Live
    # 2026-08-11: four satellites were decomposed into mason E6 / doctor E7 / herald
    # E13 / steward E9 with ledger stories and their stations RUNNING, and the panel
    # still called all four "owned, not started". Derive the missing half from the
    # same signal chain-completeness INV-A uses -- is `spec-<slug>` referenced by the
    # owner station's epics? -- rather than from a slug map that cannot grow.
    building |= _decomposed_satellites(dreams)
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


# ---- delivery timing / velocity (journals + wall-clock fallback) -------------

_WALL_CLOCK_CEILING_METRIC = (
    "wall-clock ceiling per story (final_revision − baseline_revision commit "
    "timestamps; includes idle before dispatch) — from promoted story-spec "
    "revision fields"
)
_JOURNAL_METRIC = (
    "active agent-compute per story (dev + review; excludes gate-pause wait) "
    "— from bmad-loop run journals"
)
_MIXED_METRIC = (
    "active agent-compute from bmad-loop journals; wall-clock ceiling "
    "(final_revision − baseline_revision commit timestamps; includes idle "
    "before dispatch) for hand-driven stories with revision fields — never "
    "the same class"
)
TIMING_CLASS_ACTIVE = "active-compute"
TIMING_CLASS_WALL_CLOCK = "wall-clock-ceiling"

# CAP-3 coverage caption partitions (Story 23.3) — align with 23.1/23.2 metric classes.
TIMING_COVERAGE_JOURNAL = "journal-measured"
TIMING_COVERAGE_WALL_CLOCK = "wall-clock-derived"
TIMING_COVERAGE_SPEC_NO_REVS = "spec-without-revision-fields"
TIMING_COVERAGE_NO_SPEC = "no-spec-at-all"


def _timing_total_label_active(mins: int) -> str:
    if mins >= 60:
        return f"~{mins / 60:.1f} h active compute"
    return f"~{mins} min active compute"


def _timing_total_label_wall_clock(mins: int) -> str:
    if mins >= 60:
        return f"~{mins / 60:.1f} h wall-clock ceiling"
    return f"~{mins} min wall-clock ceiling"


def timing_chip_css_class(per_story_class: dict | None, sid: str) -> str:
    """CSS class suffix for a story timing chip (empty if unknown / legacy)."""
    if not isinstance(per_story_class, dict):
        return ""
    cls = per_story_class.get(sid)
    if cls in (TIMING_CLASS_ACTIVE, TIMING_CLASS_WALL_CLOCK):
        return cls
    return ""


def _unquote_fm(value: object) -> str:
    if not isinstance(value, str):
        return ""
    s = value.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def git_commit_timestamp(rev: str, *, cwd: Path | None = None) -> int | None:
    """Unix epoch seconds for a local commit, or None if unresolvable.

    Offline only — never fabricates. `NO_VCS`, empty, and unknown revs skip.
    """
    if not rev or rev == "NO_VCS":
        return None
    try:
        r = subprocess.run(
            ["git", "show", "-s", "--format=%ct", rev],
            cwd=cwd or REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    out = r.stdout.strip()
    if not out or not out.isdigit():
        return None
    return int(out)


def wall_clock_ceiling_minutes(
    baseline_rev: str, final_rev: str, *, cwd: Path | None = None,
) -> int | None:
    """Ceiling minutes = round((ts(final) − ts(baseline)) / 60), or None.

    Equal or inverted timestamps, and sub-minute spans that round to 0, stay
    absent — a zero mark is not a resolvable signal (never fabricate).
    """
    ts_b = git_commit_timestamp(baseline_rev, cwd=cwd)
    ts_f = git_commit_timestamp(final_rev, cwd=cwd)
    if ts_b is None or ts_f is None or ts_f <= ts_b:
        return None
    mins = round((ts_f - ts_b) / 60)
    return mins if mins > 0 else None


def _story_spec_path(
    pkey: str, sid: str, *, repo_root: Path | None = None,
) -> Path | None:
    """Unique promoted story spec file, or None if missing / ambiguous."""
    root = repo_root or REPO_ROOT
    m = re.match(r"^(\d+)\.(\d+)$", sid)
    if not m:
        return None
    try:
        resolution = resolve_project(pkey)
    except UnresolvableProjectError:
        return None
    if not resolution.project_dir:
        return None
    specs_dir = (
        root / "_bmad-output" / "projects" / resolution.project_dir
        / "planning-artifacts" / "specs"
    )
    matches = sorted(specs_dir.glob(f"spec-{m.group(1)}-{m.group(2)}-*.md"))
    files = [p for p in matches if p.is_file()]
    if len(files) != 1:
        return None
    return files[0]


def story_spec_revision_fields(
    pkey: str, sid: str, *, repo_root: Path | None = None,
) -> tuple[str, str] | None:
    """`(baseline_revision, final_revision)` from the matching promoted story spec.

    Looks up `_bmad-output/projects/<dir>/planning-artifacts/specs/spec-{e}-{n}-*.md`
    via `resolve_project`. Missing file / ambiguous multi-match / fields /
    `NO_VCS` → None (silent skip — never pick silently among collisions).
    """
    spec_path = _story_spec_path(pkey, sid, repo_root=repo_root)
    if spec_path is None:
        return None
    fm = _frontmatter_scalars(spec_path, ("baseline_revision", "final_revision"))
    baseline = _unquote_fm(fm.get("baseline_revision", ""))
    final = _unquote_fm(fm.get("final_revision", ""))
    if not baseline or not final or baseline == "NO_VCS" or final == "NO_VCS":
        return None
    return baseline, final


def _story_has_resolvable_revision_fields(
    pkey: str, sid: str, *, repo_root: Path | None = None,
) -> bool:
    """True when the promoted spec carries non-sentinel baseline/final fields."""
    spec_path = _story_spec_path(pkey, sid, repo_root=repo_root)
    if spec_path is None:
        return False
    fm = _frontmatter_scalars(spec_path, ("baseline_revision", "final_revision"))
    baseline = _unquote_fm(fm.get("baseline_revision", ""))
    final = _unquote_fm(fm.get("final_revision", ""))
    return bool(
        baseline and final and baseline != "NO_VCS" and final != "NO_VCS")


def _classify_story_timing_coverage(
    pkey: str,
    sid: str,
    status: str,
    bar_sids: set[str],
    wall_clock_sids: set[str],
    *,
    repo_root: Path | None = None,
) -> str | None:
    """Return one CAP-3 coverage class, or None for in-flight / non-applicable."""
    if sid in bar_sids:
        return TIMING_COVERAGE_JOURNAL
    if sid in wall_clock_sids:
        return TIMING_COVERAGE_WALL_CLOCK
    if status != "done":
        return None
    if _story_has_resolvable_revision_fields(pkey, sid, repo_root=repo_root):
        # Revision-bearing hand-driven — never "predates instrumentation".
        return TIMING_COVERAGE_WALL_CLOCK
    if _story_spec_path(pkey, sid, repo_root=repo_root) is not None:
        return TIMING_COVERAGE_SPEC_NO_REVS
    return TIMING_COVERAGE_NO_SPEC


def partition_timing_coverage(
    pkey: str,
    proj: dict,
    bar_sids: set[str],
    wall_clock_sids: set[str],
    *,
    repo_root: Path | None = None,
) -> dict[str, int]:
    """Count stories in each CAP-3 coverage class for caption partitioning."""
    counts: dict[str, int] = {}
    for epic in proj.get("epics", []):
        for story in epic.get("stories", []):
            if len(story) < 2:
                continue
            sid, status = story[0], story[1]
            cls = _classify_story_timing_coverage(
                pkey, sid, status, bar_sids, wall_clock_sids,
                repo_root=repo_root)
            if cls is None:
                continue
            counts[cls] = counts.get(cls, 0) + 1
    return counts


def _velocity_coverage_sub_caption(
    n_bars: int,
    n_stories: int,
    partitions: dict[str, int],
) -> str:
    """Velocity-axis coverage caption — four true classes, never 'predates'."""
    inflight = (
        ". A story still in flight contributes only its CLOSED sessions, "
        "so its bar is a floor, not a total."
    )
    base = (
        "Active agent-compute per story (dev + review; excludes "
        "gate-pause wait) — derived from this line's bmad-loop journals. "
        f"{n_bars} of {n_stories} stories journal-measured on this axis"
    )
    if n_bars >= n_stories:
        return base + inflight
    parts: list[str] = []
    wc = partitions.get(TIMING_COVERAGE_WALL_CLOCK, 0)
    if wc:
        parts.append(
            f"{wc} wall-clock-derived on the timing strip only "
            "(a different metric — see the timing strip)"
        )
    snr = partitions.get(TIMING_COVERAGE_SPEC_NO_REVS, 0)
    if snr:
        parts.append(
            f"{snr} spec-without-revision-fields deliberately absent"
        )
    ns = partitions.get(TIMING_COVERAGE_NO_SPEC, 0)
    if ns:
        parts.append(f"{ns} no-spec-at-all deliberately absent")
    detail = "; ".join(parts) if parts else "remainder deliberately absent"
    return base + f"; {detail} — not plotted on this axis" + inflight


def _sid_from_journal_key(key: str) -> str:
    m = re.match(r"^(\d+)-(\d+)", key)
    return f"{m.group(1)}.{m.group(2)}" if m else key


def derive_wall_clock_per_story(
    pkey: str,
    proj: dict,
    journal_sids: set[str],
    *,
    repo_root: Path | None = None,
    cwd: Path | None = None,
) -> dict[str, int]:
    """Wall-clock ceiling minutes for done stories with zero journal coverage.

    Per-story precedence: any closed journal session for that sid wins — no
    wall-clock overwrite. Unresolvable revs stay absent (never fabricate).
    """
    out: dict[str, int] = {}
    for epic in proj.get("epics", []):
        for story in epic.get("stories", []):
            if len(story) < 2:
                continue
            sid, status = story[0], story[1]
            if status != "done" or sid in journal_sids:
                continue
            revs = story_spec_revision_fields(pkey, sid, repo_root=repo_root)
            if revs is None:
                continue
            mins = wall_clock_ceiling_minutes(revs[0], revs[1], cwd=cwd)
            if mins is None:
                continue
            out[sid] = mins
    return out


def scan_timing(projects: dict) -> None:
    """Per-story timing: journal active-compute + wall-clock ceiling fallback.

    In Build showed no clock and no velocity while Realized did, because warden's
    and atlas's numbers were computed once from these same journals and then
    hand-pasted into data.js. Any line without that manual step rendered bare.

    Active compute = the sum of `session-end.ts - session-start.ts` per story
    (dev + review). Gate-pause wait falls out for free: a pause happens BETWEEN
    sessions, so it is never inside a summed span — which is exactly warden's
    stated metric.

    Wall-clock fallback (CAP-1): for `done` stories with resolvable
    `baseline_revision`/`final_revision` on the promoted story spec and zero
    closed journal sessions, derive ceiling minutes from local git commit
    timestamps (final − baseline). Those minutes land on `timing.perStory`
    only — never on `velocity.bars`. Metric/note name the ceiling bound.

    Class separation (CAP-2): every `perStory` sid carries a `perStoryClass`
    of `active-compute` or `wall-clock-ceiling`. Epic rollups never blend —
    journal → `epicMin`, wall-clock → `epicMinWallClock`. Mixed lines emit a
    dual `totalLabel` (never a single "combined marks" number). The renderer
    styles chips by class and shows a legend when both classes appear.

    Hand-authored `timing`/`velocity` are PRESERVED, never overwritten. Warden's
    carry human judgement no derivation can reproduce (6.4's bar is its delivered
    dev-2 pass, excluding a rolled-back dev-1; 6.9's is recovered from a stalled
    session). Derivation fills the gap for lines that have none; it does not
    second-guess a curated number.
    """
    # Every board line, not only those with a loop home: wall-clock-only projects
    # (and mixed lines whose journals are empty) must still gain timing marks.
    for pkey in sorted(projects):
        proj = projects.get(pkey)
        # Skip CURATED timing only. Derived output carries `derived: true` so a
        # later run can refresh (or repair) it — without that marker the first
        # derivation became permanent, and a bug in it could never be fixed by
        # re-running the generator.
        if not isinstance(proj, dict):
            continue
        existing_t, existing_v = proj.get("timing"), proj.get("velocity")
        # A timing object WITHOUT `perStory` is broken by definition — the
        # renderer does `p.timing && p.timing.perStory[key]`, so a partial object
        # passes the truthiness guard and then throws, aborting the whole script.
        # Treat it as stale and regenerate, whatever its `derived` marker says.
        # (The marker alone was insufficient: output written before the marker
        # existed looked curated and could never be repaired by re-running.)
        broken = isinstance(existing_t, dict) and "perStory" not in existing_t
        # Curated-ness is PER FIELD, not per project. The old all-or-nothing test
        # skipped the whole project when EITHER field was hand-authored — so atlas,
        # which has a curated `timing` (wall-clock from PR timestamps, because waves
        # 0-H ran in a web session with no journals) but NO `velocity` at all, could
        # never gain a velocity graph even once it had real loop journals. Warden is
        # unaffected: both of its fields are curated, so there is nothing to fill.
        timing_curated = (not broken) and isinstance(existing_t, dict) \
            and not existing_t.get("derived")
        velocity_curated = isinstance(existing_v, dict) and not existing_v.get("derived")
        if timing_curated and velocity_curated:
            continue
        spans: dict[str, float] = {}
        home = LOOP_HOMES.get(pkey)
        runs = (Path(home) / ".bmad-loop" / "runs") if home is not None else None
        if runs is not None and runs.is_dir():
            for jf in sorted(runs.glob("*/journal.jsonl")):
                # `session-end` carries ONLY task_id — no story_key (verified against
                # live journals). Pairing on story_key silently closed nothing and
                # every line derived zero. The story is carried on session-START and
                # looked up by task_id when the session ends.
                open_at: dict[str, tuple[float, str]] = {}
                for line in jf.read_text(encoding="utf-8", errors="replace").splitlines():
                    try:
                        e = json.loads(line)
                    except Exception:
                        continue
                    kind, ts, task = e.get("kind"), e.get("ts"), e.get("task_id")
                    if not task or not isinstance(ts, (int, float)):
                        continue
                    if kind == "session-start" and e.get("story_key"):
                        open_at[task] = (ts, e["story_key"])
                    elif kind == "session-end" and task in open_at:
                        started, key = open_at.pop(task)
                        spans[key] = spans.get(key, 0.0) + max(0.0, ts - started)
        journal_sids = {_sid_from_journal_key(k) for k in spans}
        wall_clock: dict[str, int] = {}
        if not timing_curated:
            wall_clock = derive_wall_clock_per_story(pkey, proj, journal_sids)
        # Do not early-exit solely because journal spans are empty if wall-clock
        # marks exist (hand-driven lines with no loop home / no closed sessions).
        if not spans and not wall_clock:
            continue
        bars = []
        for key, secs in spans.items():
            bars.append([_sid_from_journal_key(key), round(secs / 60)])
        bars.sort(key=lambda b: [int(x) if x.isdigit() else 0 for x in b[0].split(".")])
        st = [s for e in proj.get("epics", []) for s in e.get("stories", [])]
        done_n = sum(1 for s in st if len(s) >= 2 and s[1] == "done")
        velocity_obj = None
        if bars:
            total_h = sum(b[1] for b in bars) / 60
            # The renderer reads v.{bars,sub,foot} — ALL of them. `foot` is not
            # optional: `v.foot.map(...)` throws on a partial object exactly as
            # `timing.perStory` did. Enumerated from the render rather than guessed,
            # after fixing the same class of bug twice in a row.
            bar_mins = sorted(b[1] for b in bars)
            median = bar_mins[len(bar_mins) // 2] if len(bar_mins) % 2 else \
                round((bar_mins[len(bar_mins) // 2 - 1]
                       + bar_mins[len(bar_mins) // 2]) / 2)
            bar_sids = {sid for sid, _ in bars}
            coverage_parts = partition_timing_coverage(
                pkey, proj, bar_sids, set(wall_clock))
            velocity_obj = {
                "derived": True,
                # The in-flight caveat has to live HERE too, not only on `timing.note`:
                # velocity is now derivable on a line whose timing is curated (atlas), so
                # the note that used to carry this never reaches the reader.
                #
                # COVERAGE IS STATED, never implied. CAP-3 partitions by true absence
                # class (journal-measured / wall-clock-derived /
                # spec-without-revision-fields / no-spec-at-all) — never lump revision-
                # bearing hand-driven stories under "predates instrumentation".
                "sub": _velocity_coverage_sub_caption(
                    len(bars), len(st), coverage_parts),
                "bars": bars,
                "foot": [
                    [f"~{median} min", "median / story", "var(--done)"],
                    [f"{bar_mins[0]}–{bar_mins[-1]} min"
                     if len(bar_mins) > 1 else f"{bar_mins[0]} min",
                     "observed range", ""],
                    [f"{done_n}/{len(st)}", "stories complete", "var(--done)"],
                    [f"{len(st) - done_n}", "remaining", ""],
                ],
            }
        # The renderer reads timing.{perStory,perStoryClass,epicMin,metric,note,
        # totalLabel} — ALL of them. Emitting a partial object is worse than
        # emitting none: `p.timing && p.timing.perStory[key]` passes the
        # truthiness guard and then throws on the missing key, which aborts the
        # whole script and took In Build / Realized / Archived down with it
        # (2026-07-26). Match the curated shape exactly.
        per_story = {sid: m for sid, m in bars}
        per_story.update(wall_clock)  # journal sids already excluded from wall_clock
        per_story_class: dict[str, str] = {
            sid: TIMING_CLASS_ACTIVE for sid, _ in bars}
        per_story_class.update(
            {sid: TIMING_CLASS_WALL_CLOCK for sid in wall_clock})
        # CAP-2: epic rollups never blend classes. Journal → epicMin;
        # wall-clock → epicMinWallClock. `total` is the primary class only
        # (active-compute when any journal bars exist; else wall-clock).
        epic_min: dict[str, int] = {}
        epic_min_wall: dict[str, int] = {}
        for sid, mins in bars:
            epic_min[f"E{sid.split('.')[0]}"] = (
                epic_min.get(f"E{sid.split('.')[0]}", 0) + mins)
        for sid, mins in wall_clock.items():
            epic_min_wall[f"E{sid.split('.')[0]}"] = (
                epic_min_wall.get(f"E{sid.split('.')[0]}", 0) + mins)
        journal_mins = sum(b[1] for b in bars)
        wall_mins = sum(wall_clock.values())
        total_mins = journal_mins if bars else wall_mins
        if wall_clock and bars:
            metric = _MIXED_METRIC
            note = (
                f"Derived from {len(bars)} journal-measured + {len(wall_clock)} "
                f"wall-clock-ceiling "
                f"stor{'y' if (len(bars) + len(wall_clock)) == 1 else 'ies'}; "
                f"wall-clock is a ceiling spanning baseline→final commit timestamps "
                f"(includes idle before dispatch), not active agent-compute. "
                f"Journal bars still in flight contribute only closed sessions."
            )
            total_label = (
                f"{_timing_total_label_active(journal_mins)} · "
                f"{_timing_total_label_wall_clock(wall_mins)}")
        elif wall_clock:
            metric = _WALL_CLOCK_CEILING_METRIC
            note = (
                f"Derived from {len(wall_clock)} wall-clock-ceiling "
                f"stor{'y' if len(wall_clock) == 1 else 'ies'}; "
                f"ceiling = final_revision − baseline_revision commit timestamps "
                f"(includes idle before dispatch), not active agent-compute."
            )
            total_label = _timing_total_label_wall_clock(wall_mins)
        else:
            metric = _JOURNAL_METRIC
            note = (
                f"Derived from {len(bars)} measured "
                f"stor{'y' if len(bars) == 1 else 'ies'}; a story still in "
                f"flight contributes only its closed sessions."
            )
            total_label = _timing_total_label_active(journal_mins)
        timing_obj = {
            "derived": True,
            "metric": metric,
            "total": total_mins,
            "totalLabel": total_label,
            "note": note,
            "perStory": per_story,
            "perStoryClass": per_story_class,
            "epicMin": epic_min,
        }
        if epic_min_wall:
            timing_obj["epicMinWallClock"] = epic_min_wall
        # Assign PER FIELD — a curated field is never overwritten, but its presence
        # no longer blocks the other from being filled. Wall-clock never writes
        # velocity.bars (journal spans only).
        wrote = []
        if not velocity_curated and velocity_obj is not None:
            proj["velocity"] = velocity_obj
            wrote.append("velocity")
        if not timing_curated and per_story:
            proj["timing"] = timing_obj
            wrote.append("timing")
        if not wrote:
            continue
        print(
            f"[{pkey}] {'+'.join(wrote)} derived: "
            f"{len(bars)} journal / {len(wall_clock)} wall-clock stories, "
            f"{sum(b[1] for b in bars)} min active compute"
            + (f", {sum(wall_clock.values())} min wall-clock ceiling"
               if wall_clock else "")
            + (" (curated timing preserved)" if timing_curated else "")
        )


# ---- station ownership (the Dream -> code through-line) ----------------------

# Console program key -> the Dream whose owner is accountable for that build line.
PROGRAM_DREAM = {"warden": "pyforge-warden", "atlas": "pyforge-atlas",
                 "herald": "pyforge-herald", "doctor": "pyforge-doctor",
                 "scribe": "pyforge-scribe",
                 "marshal": "pyforge-marshal", "mason": "pyforge-mason",
                 "steward": "pyforge-steward",
                 # auto-discovered lines whose Dream slug is NOT pyforge-prefixed
                 "presenton-pixi-image": "presenton-pixi-image"}


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
        # A sub-chain has no Dream FILE of its own; its SPEC names the parent in
        # `owner-dream:` (Charter §5 — one Dream can spawn several Specs). Resolving
        # through the parent keeps the single source of truth this function exists to
        # enforce: the owner still comes from Dream frontmatter, just the parent's.
        row["owner"] = by_slug.get(row["dream"], "") or by_slug.get(row.get("ownerDream", ""), "")
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



# ---- the accountability gate (Charter §7, amended 2026-07-28) ----------------

def gate_ownership(data: dict) -> list[str]:
    """Refuse to publish a hall that cannot say who is accountable for a row.

    Charter §7: the Guildhall is the unit of *accountability made real*, not merely of
    visibility — "visibility without consequence is decoration". This is the only place
    the whole Dream->Code chain is assembled in one view, so it is the only place a break
    in that chain can be seen whole.

    Corrects an inversion: check_render.js exited non-zero on a JavaScript TypeError while
    this generator printed `· UNOWNED: …` and exited clean — a cosmetic fault blocked
    publication while a governance fault shipped. The `[owner]` line already computed the
    answer and threw it away.

    Hard gate from day one, deliberately: a grace period on the model's critical path is
    how drift becomes permanent.
    """
    valid = set(STATIONS) | {"guild"}
    v: list[str] = []

    for d in data.get("dreams", []):
        o = d.get("owner") or ""
        if not o:
            v.append(f"dream {d['slug']}: no owner")
        elif o not in valid:
            v.append(f"dream {d['slug']}: owner {o!r} is not one of the eight (+guild)")

    for row in (data.get("fleet") or {}).get("rows", []):
        # campaigns are deliberately unowned (they span stations) — see apply_owner
        if not row.get("owner") and not row.get("campaign"):
            v.append(f"fleet row {row.get('slug', '?')}: blank station")

    for key, proj in (data.get("projects") or {}).items():
        if not proj.get("owner") and not proj.get("practice"):
            v.append(f"build line {key}: no owning station")

    return v


# ---- shared ------------------------------------------------------------------

def load_data() -> dict:
    inner = DATA_JS.read_text(encoding="utf-8").strip()
    inner = re.sub(r"^window\.DASHBOARD_DATA\s*=\s*", "", inner).rstrip().rstrip(";")
    return json.loads(inner)


def now_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---- console status block (the header chips) -------------------------------
def build_status(data: dict, source: str) -> dict:
    """The three facts the header chips render: generated-at, running now, last shipped.

    Emitted as DATA rather than baked into the `snapshot` prose string, because the
    front-end needs the pieces separately and a reader needs to know WHICH board
    they are looking at. `source` is carried through for exactly that reason: the
    local (`sprint-status`) and published (`git`) boards answer different questions
    by design -- the factory-console Dream calls this the "two-source refresh" --
    and a header that does not say which one it is invites the "why don't these
    match?" question this block exists to pre-empt.

    `running` is LOCAL-ONLY by construction: it derives from ~/.bmad-loops and tmux,
    neither of which exists on a CI runner. On the published board it is therefore
    reported as `unavailable` rather than omitted -- an honest absence, not a
    silent one, so the board never implies "nothing is running" when it simply
    cannot know.
    """
    # Derive `running` from the in-flight CARD, not from `lineState`.
    #
    # lineState is computed from the sprint feed, and bmad-loop marks a story
    # `done` in that feed when its DEV pass finishes — while the REVIEW is still
    # running. In that window the feed says done, lineState moves on to the next
    # story, and a feed-derived chip reports "running nothing" about a story that
    # is visibly still running. Observed live 2026-07-31: doctor 1.5 sat in
    # `review-running` for 20+ minutes while the board claimed nothing was in
    # flight.
    #
    # `inflight` comes from apply_loop_inflight's scan of the loop home — the
    # story worktree plus its state.json phase — which is the harness's own view
    # and owes nothing to the feed. Same lesson as the deferred-story false green
    # one layer up: the feed reports intent, the run reports fact.
    running = []
    projects = data.get("projects") or {}
    for proj in (projects.values() if isinstance(projects, dict) else projects):
        if not isinstance(proj, dict):
            continue
        infl = proj.get("inflight") or {}
        if infl.get("key"):
            running.append({
                "station": proj.get("label", "?"),
                "story": infl.get("key", ""),
                "phase": infl.get("phase", ""),
                "startEpoch": infl.get("startEpoch"),
            })

    shipped = None
    out = subprocess.run(
        ["git", "log", MAIN_BRANCH, "--format=%H%x1f%ct%x1f%s", "-n", "400"],
        capture_output=True, text=True, cwd=REPO_ROOT).stdout
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 3:
            continue
        sha, when, subject = parts
        key = slug = None
        m = _LOOP_DONE.search(subject)
        if m:
            key = m.group(1).replace("-", ".")
            tgt = _LOOP_TARGET_SLUG.search(m.group(2) or "")
            slug = tgt.group(1) if tgt else None
        if not key:
            # hand-landed: `<station>: ... Story <e>.<s> ...` in the SUBJECT
            m2 = re.search(r"story\s+(\d+)\.(\d+)", subject, re.IGNORECASE)
            if m2:
                for cand in PROJECT_SOURCES:
                    if cand in subject.lower():
                        key, slug = f"{m2.group(1)}.{m2.group(2)}", cand
                        break
        if key and slug:
            shipped = {"station": slug, "story": key, "epoch": int(when),
                       "sha": sha[:9], "subject": subject[:120]}
            break

    return {"source": source, "running": running, "lastShipped": shipped,
            "runningAvailable": source == "sprint-status"}


def _resolve_roster_slugs() -> tuple[int, int]:
    """Resolve every PROJECT_SOURCES/CAMPAIGN_ROSTER/IMPL_CAMPAIGN slug once,
    up front. Fails loud (FR-143) via resolve_project()'s own
    UnresolvableProjectError before any other work happens, rather than
    partway through a long run; returns `(total, via_override)` for the
    match-summary `main()` prints.
    """
    slugs = sorted(set(PROJECT_SOURCES) | {e["slug"] for e in CAMPAIGN_ROSTER}
                    | {e["slug"] for e in IMPL_CAMPAIGN})
    via_override = 0
    for slug in slugs:
        resolve_project(slug)
        if slug in _PROJECT_OVERRIDES:
            via_override += 1
    return len(slugs), via_override


def main() -> int:
    print(
        "retired: Guildhall generate.py is gone (steward 30.2). "
        "Use Lane 1 /console/ and steward deploy dashboard for Kedro-Viz.",
        file=sys.stderr,
    )
    return 2


def _generate(args: argparse.Namespace) -> int:
    n_resolved, via_override = _resolve_roster_slugs()
    print(f"[resolve] {n_resolved} slug(s) resolved ({via_override} via override, "
          f"{n_resolved - via_override} default)")

    data = load_data()
    data["projects"] = scan_projects(data["projects"])
    check_project_coverage(data["projects"])
    if args.source == "git":
        # Tracked truth FIRST, archaeology second. The ledger twins are committed,
        # so CI can read them; `apply_git` then only has to cover whatever predates
        # a twin. Order matters only for the log's readability — both paths upgrade
        # and neither downgrades.
        apply_tracked_ledger(data["projects"])
        apply_git(data["projects"])
    else:
        apply_sprint_status(data["projects"])
        # Tracked twins as a FLOOR under local mode too, and last so it can only
        # raise. `apply_sprint_status` leaves a project "as-is" when its Tier-3
        # feed is missing — and as-is is the embedded `pending` baseline, not the
        # project's real state. That is invisible in the main worktree, where all
        # ten feeds exist, and wrong in every other one: run from a bmad-loop home,
        # where only the running project's feed is symlinked in, this rendered SIX
        # projects' shipped stories back to `pending` (2026-07-30, caught before
        # commit by diffing against the published board). `dashboard-drift-check`
        # could not catch it there either — it compares the board against feeds
        # that are themselves absent, so it reported OK on a regressed board.
        apply_tracked_ledger(data["projects"])
        apply_loop_inflight(data["projects"])
    data["dreams"] = scan_dreams()
    data["specs"] = scan_specs()
    data["storySpecs"] = scan_story_specs()
    data.pop("campaign", None)
    data.pop("campaign2", None)
    spec_c = scan_campaign()
    # Computed ONCE, shared by every LOCAL-ONLY panel needing a live/not-live
    # distinction — see `live_running_stations()`'s own docstring for why a
    # second definition of "running" is exactly how the build-campaign panel
    # drifted from the fleet roll-up panel and mislabeled a stopped station.
    running_stations: set[str] = set()
    live_error: str | None = None
    if args.source != "git":
        running_stations, live_error = live_running_stations()
    build_c = scan_impl_campaign(data["projects"],
                                  running_stations if args.source != "git" else None)
    apply_line_state(data["projects"])
    # Fleet roll-up: tracked-only, so it renders the same on Pages as locally.
    data["fleetProgress"] = build_fleet_progress(data["projects"])
    if args.source != "git":
        # Local render only — see the function's own docstring for why
        # Pages must NOT carry these.
        enrich_fleet_progress_live(data["fleetProgress"], data["projects"],
                                    running_stations, live_error)
    data["health"] = scan_health()
    # Pitch BEFORE fleet: the deck dot is sub-scored against the six-artifact family
    # contract, and scan_pitch already computes exactly that per deck. Recomputing it
    # inside the fleet would be a second producer of one fact.
    data["pitch"] = scan_pitch()
    data["fleet"] = scan_fleet(data["projects"], data["pitch"])
    data["commandCenter"] = scan_command_center(data["fleet"])
    data["readiness"] = scan_readiness()
    data["campaigns"] = [
        {"id": "spec-completion-2026-07-25", "title": "Spec Completion",
         "kind": "planning", "status": "completed", "completed": "2026-07-25",
         "record": "_bmad-output/projects/local-recipes/planning-artifacts/campaign-spec-completion-2026-07-25.md",
         **spec_c},
        {"id": "build-2026-07-25", "title": "The Build", "kind": "build",
         "status": "active", **build_c},
    ]
    data["openwork"] = scan_deferred()
    data["archived"] = build_archived(data["dreams"])
    # apply_owner MUST precede scan_guild: the Guild's `building` column reads
    # proj["owner"], which apply_owner sets. Ordered the other way it silently
    # worked for pre-existing lines (their owner persisted in data.js from an
    # earlier run) and reported every NEW line as idle — caught when marshal /
    # mason / steward / genesis were added 2026-07-25.
    apply_owner(data)
    scan_timing(data["projects"])
    data["backlog"] = scan_backlog(data["dreams"], data["projects"])
    data["guild"] = scan_guild(data["dreams"], data["projects"], data["backlog"])

    violations = gate_ownership(data)
    if violations:
        print(f"\n[GATE] ACCOUNTABILITY — {len(violations)} violation(s); NOT publishing:")
        for x in violations:
            print(f"     ✗ {x}")
        print("  Charter §7: the hall does not put a row on the wall it cannot attribute.")
        return 1

    ts = now_utc()
    data["snapshot"] = _SNAP_TS.sub(ts, data["snapshot"], count=1)
    data["status"] = build_status(data, args.source)
    data["status"]["generatedAt"] = ts
    # epoch too, so the front-end can render it in the VIEWER's timezone --
    # a UTC string alone forces mental arithmetic on every glance.
    data["status"]["generatedEpoch"] = int(time.time())
    DATA_JS.write_text(
        "window.DASHBOARD_DATA = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"\nsnapshot -> {ts}  ·  source: {args.source}  ·  data.js rewritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
