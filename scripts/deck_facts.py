#!/usr/bin/env python3
"""Derive a presentation deck's fact ledger and check its poster against it.

``presentations/<slug>/facts.yaml`` is the per-deck fact ledger (contract:
``spec-deck-family-currency`` CAP-2 / CAP-5, shape in its ``facts-ledger.md``):
every count / version / status / date a poster shows has a row -- ``id``,
``value``, ``source``, ``method``, ``shown_as`` -- re-derived from TRACKED live
sources only. Nothing here reads ``implementation-artifacts/``, another poster,
or memory; a fact the derivation cannot source is omitted and named on stderr,
never guessed.

Deterministic on purpose: facts are sorted by ``id``, ``tree`` is the HEAD sha
(suffixed ``-dirty`` when tracked files were uncommitted) and ``derived_at`` the
HEAD commit date, so a re-run on an unchanged tree writes identical bytes.

``--check`` reads the deck's ``project/<Persona> Infographic standalone.html``
(visible text only -- ``<style>``/``<script>``/``<title>`` skipped) and reports,
one line per finding plus a summary:

    unmarked   a visible n/n, x.y.z (optional leading v) or YYYY-MM-DD token
               matching no row
    mismatch   a ``data-fact="<id>"`` element whose text is neither the row's
               value nor one of its shown_as literals
    drifted    a row whose fresh derivation differs from the file
    unsourced  a row the current run could not derive (its omit reason follows)
    unshown    a row neither marked nor shown anywhere in the poster

The check is advisory: exit 0 always. The only non-zero exit is a usage error
(unknown slug, ``--check`` before a ledger exists) -- exit 2. This is NOT a
detector (no ``DETECTOR`` marker, never in ``detectors``/``detectors-ci``).

Usage (the ``scripts/deck_export.py`` precedent: one script, one pixi task)::

    pixi run -e local-recipes deck-facts <slug> [--check] [--with-tests]

``--with-tests`` adds a ``tests_collected`` row by running the station's own
``pytest --collect-only -q`` over its ``tests/`` in its own pixi env; the default
run is offline and takes seconds.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import tomllib
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fleet_scan import parse_sprint_status

POSTER_SUFFIX = " Infographic standalone.html"
STATION_PREFIX = "pyforge-"
# The one deck whose "own" ledger is another station's: the Unifying Strategy
# poster reports steward's sprint ledger (spec-deck-family-currency
# facts-ledger.md). Its pair is the per-station `steward_*` pair every deck
# carries -- annotated, never duplicated under an unprefixed id.
LEDGER_PROXY = {"pyforge-unifying-strategy": "steward"}
GROUNDTRUTH_SOURCE = "pixi run -e local-recipes bmad-groundtruth"
TREE_DATE_SOURCE = "git log -1 --format=%cs"

# Literal first argument of an argparse ``add_parser("…")`` call, possibly on
# the next line. Dynamic ``add_parser(name)`` calls are deliberately not counted.
_ADD_PARSER = re.compile(r"""\.add_parser\(\s*["']([^"'\n]+)["']""")
# A capability DEFINITION line in the spec's own id scheme -- a bold `- **CAP-N`
# bullet or a `### HER-4..HER-10` heading (ranges expand) -- never a prose
# mention, so a plain `- CAP-6's surface …` bullet does not count.
_CAP_DEF = re.compile(r"^\s*(?:-\s*\*\*|#+\s*\*{0,2})(CAP|HER)-(\d+)(?:\.\.(?:CAP-|HER-)?(\d+))?\b")
# A dated Realization-log entry in a Dream: `- **2026-07-23** — …` (also
# `- **2026-07-17/18**`, `- **2026-07-23 (later)**`; the first date is the entry's).
_DREAM_LOG = re.compile(r"^\s*-\s*\*\*(\d{4}-\d{2}-\d{2})")
_CONDA_PKG = re.compile(r"/bmad-loop-(\d[^-/]*)-[^-/]+\.(?:conda|tar\.bz2)\b")
# `2132 tests collected in 1.3s` and `45/50 tests collected (5 deselected)` -> N.
_PYTEST_COLLECTED = re.compile(r"(\d+)(?:/\d+)? tests? collected")
# The visible fact tokens --check sweeps: n/n, x.y.z (optional leading v),
# YYYY-MM-DD. The boundaries keep "8" out of "2026-08-01" and "1.2" out of "1.2.3".
_TOKEN = re.compile(r"(?<![\w./-])v?(\d+\.\d+\.\d+|\d+/\d+|\d{4}-\d{2}-\d{2})(?![\w./-])")
_LEADING_V = re.compile(r"^v(?=\d)")
_SKIP_TAGS = frozenset(["style", "script", "title"])
_VOID_TAGS = frozenset(
    ["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"]
)
# A block boundary always separates (`<td>a</td><td>b</td>` stays two tokens);
# an inline boundary joins with no separator ONLY when it falls inside a token --
# token characters on both sides, as in `<b>847</b>/878` -- and separates
# otherwise, so sibling chips `<span>The Proclaimer</span><span>4/27</span>`
# never fuse into "Proclaimer4/27".
_BLOCK_TAGS = frozenset(
    ["div", "p", "li", "td", "th", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
     "section", "header", "footer", "br", "table", "ul", "ol"]
)
_INLINE_JOIN = "\x00"   # placeholder resolved by _join()
_INSIDE_TOKEN_JOIN = re.compile(r"(?<=[0-9./-])\x00+(?=[0-9./-])")


# ----------------------------------------------------------------- primitives

def fact(fid: str, value: str, source: str, method: str,
         shown_as: list[str] | None = None) -> dict:
    literals = [value] + [s for s in (shown_as or []) if s != value]
    return {"id": fid, "value": value, "source": source, "method": method,
            "shown_as": literals}


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def head_info(root: Path) -> dict:
    """HEAD sha, commit date (ISO-8601 and YYYY-MM-DD) and whether tracked files
    are uncommitted -- the ledger's `tree` / `derived_at` / `tree_commit_date`."""
    return {
        "sha": _git(root, "rev-parse", "HEAD"),
        "date": _git(root, "log", "-1", "--format=%cI"),
        "short_date": _git(root, "log", "-1", "--format=%cs"),
        "dirty": bool(_git(root, "status", "--porcelain", "--untracked-files=no")),
    }


def poster_commit_date(root: Path, poster: Path) -> str | None:
    """The poster's last commit date (YYYY-MM-DD), None when it has none."""
    try:
        return _git(root, "log", "-1", "--format=%cs", "--", poster.relative_to(root).as_posix()) or None
    except subprocess.CalledProcessError:
        return None


def _frontmatter_split(path: Path) -> tuple[list[str], list[str]] | None:
    """(frontmatter lines, body lines) or None when the file has no frontmatter."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for i, ln in enumerate(lines[1:], 1):
        if ln.strip() == "---":
            return lines[1:i], lines[i + 1:]
    return lines[1:], []


def frontmatter_scalar(path: Path, key: str) -> str | None:
    """A top-level scalar from a file's `---` frontmatter, trailing comment and
    matching quotes stripped."""
    split = _frontmatter_split(path)
    if split is None:
        return None
    for ln in split[0]:
        if ln.startswith(f"{key}:"):
            val = ln.split(":", 1)[1].split("#", 1)[0].strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            return val or None
    return None


def ledger_counts(path: Path) -> tuple[str, str]:
    """('done/total' stories, 'done/total' epics) via the real parser.

    Stories are every `development_status` key not starting `epic-`; epics are the
    `epic-N` keys without `-retrospective`; `done` is the literal.
    """
    status = parse_sprint_status(path)
    stories = {k: v for k, v in status.items() if not k.startswith("epic-")}
    epics = {k: v for k, v in status.items()
             if k.startswith("epic-") and not k.endswith("-retrospective")}
    s_done = sum(v == "done" for v in stories.values())
    e_done = sum(v == "done" for v in epics.values())
    return f"{s_done}/{len(stories)}", f"{e_done}/{len(epics)}"


def stations(root: Path) -> list[str]:
    roster = json.loads((root / "docs/governance/guild-roster.json").read_text(encoding="utf-8"))
    return sorted(roster["stations"])


def ledger_path(root: Path, station: str) -> Path:
    return root / "_bmad-output/projects" / f"pyforge-{station}" / "planning-artifacts/sprint-status-ledger.yaml"


def groundtruth(root: Path) -> dict | None:
    """The `bmad-groundtruth` JSON (the task's own command, run in-process env)."""
    proc = subprocess.run(
        [sys.executable, "-m", "pyforge.doctor.sources", "bmad-drift", "--groundtruth"],
        cwd=root, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def tests_command(station: str) -> list[str]:
    """The station's own suite in its own env -- a repo-root collect would sweep
    build_artifacts/ and other envs' tests and error out."""
    return ["pixi", "run", "-e", f"pyforge-{station}", "pytest", "--collect-only", "-q",
            f"src/shared/packages/pyforge-{station}/tests"]


def tests_collected(root: Path, station: str) -> str | None:
    proc = subprocess.run(tests_command(station), cwd=root, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return None
    for line in reversed(proc.stdout.splitlines()):
        m = _PYTEST_COLLECTED.search(line)
        if m:
            return m.group(1)
    return None


def cli_verbs(root: Path, pkg_dir: Path, station: str, entry: str) -> tuple[list[str], str] | None:
    """(sorted distinct literal add_parser verbs, scanned path) for a console entry.

    The console entry `pyforge.<station>.<mod>:main` names the CLI module; when
    that module sits in a sub-package (marshal's `cli/main.py`) the whole
    sub-package is scanned, otherwise the single file.
    """
    module = entry.split(":", 1)[0]
    prefix = f"pyforge.{station}."
    if not module.startswith(prefix):
        return None
    src = pkg_dir / "src" / "pyforge" / station
    candidate = src.joinpath(*module[len(prefix):].split("."))
    if candidate.with_suffix(".py").is_file():
        mod_file = candidate.with_suffix(".py")
    elif (candidate / "__init__.py").is_file():
        mod_file = candidate / "__init__.py"
    else:
        return None
    if mod_file.parent == src:
        files, scanned = [mod_file], mod_file
    else:
        files, scanned = sorted(mod_file.parent.glob("*.py")), mod_file.parent
    verbs: set[str] = set()
    for f in files:
        verbs.update(_ADD_PARSER.findall(f.read_text(encoding="utf-8")))
    return sorted(verbs), scanned.relative_to(root).as_posix()


def poster_hits(root: Path, slug: str) -> list[Path]:
    return sorted((root / "presentations" / slug / "project").glob(f"*{POSTER_SUFFIX}"))


# ------------------------------------------------------------------- derive

def derive(root: Path, slug: str, with_tests: bool = False) -> tuple[dict, list[str], list[tuple[list[str], str]]]:
    """(facts.yaml document, stderr notes, omitted-fact reasons) for `slug`.

    `omitted` pairs id patterns (fnmatch) with the reason they were not derived;
    --check uses it to tell an `unsourced` row from a `drifted` one.
    """
    facts: list[dict] = []
    notes: list[str] = []
    omitted: list[tuple[list[str], str]] = []
    guild = stations(root)
    rel = lambda p: p.relative_to(root).as_posix()

    def omit(ids: str, why: str, quiet: bool = False) -> None:
        omitted.append(([i.strip() for i in ids.split(",")], why))
        if not quiet:
            notes.append(f"omitted {ids}: {why}")

    hits = poster_hits(root, slug)
    poster = hits[0] if hits else None
    if len(hits) > 1:
        notes.append(f"multiple posters match presentations/{slug}/project/*{POSTER_SUFFIX}: "
                     f"{', '.join(p.name for p in hits)} -- using {poster.name}")
    if poster is None:
        notes.append(f"no poster: presentations/{slug}/project/*{POSTER_SUFFIX} -- persona left empty")

    # --- every deck: one pair of per-station rows and the fleet totals over them
    story_method = "done/total story keys (parse_sprint_status; epic-* keys excluded)"
    epic_method = "done/total epic-N keys (parse_sprint_status; -retrospective keys excluded)"
    fleet = [0, 0, 0, 0]
    missing: list[str] = []
    own_pair: tuple[str, str, Path] | None = None
    station = slug[len(STATION_PREFIX):] if slug.startswith(STATION_PREFIX) else None
    for st in guild:
        lp = ledger_path(root, st)
        if not lp.is_file():
            missing.append(st)
            omit(f"{st}_stories_done_total, {st}_epics_done_total", f"{rel(lp)} not found")
            continue
        s, e = ledger_counts(lp)
        for i, part in enumerate(s.split("/") + e.split("/")):
            fleet[i] += int(part)
        proxy = " -- this deck's own ledger (LEDGER_PROXY)" if LEDGER_PROXY.get(slug) == st else ""
        facts.append(fact(f"{st}_stories_done_total", s, rel(lp), story_method + proxy, [s.replace("/", " of ")]))
        facts.append(fact(f"{st}_epics_done_total", e, rel(lp), epic_method + proxy, [e.replace("/", " of ")]))
        if st == station:
            own_pair = (s, e, lp)
    ledgers_src = "_bmad-output/projects/pyforge-*/planning-artifacts/sprint-status-ledger.yaml"
    if missing:
        omit("fleet_stories_done_total, fleet_epics_done_total", f"ledger missing for {', '.join(missing)}")
    else:
        facts.append(fact("fleet_stories_done_total", f"{fleet[0]}/{fleet[1]}", ledgers_src,
                          f"sum over the guild-roster stations of {story_method}",
                          [f"{fleet[0]} of {fleet[1]}"]))
        facts.append(fact("fleet_epics_done_total", f"{fleet[2]}/{fleet[3]}", ledgers_src,
                          f"sum over the guild-roster stations of {epic_method}",
                          [f"{fleet[2]} of {fleet[3]}"]))
    if own_pair:
        s, e, lp = own_pair
        facts.append(fact("stories_done_total", s, rel(lp), story_method, [s.replace("/", " of ")]))
        facts.append(fact("epics_done_total", e, rel(lp), epic_method, [e.replace("/", " of ")]))

    # --- every deck: tooling versions
    manifest = root / "_bmad/_config/manifest.yaml"
    core = None
    if manifest.is_file():
        # BaseLoader keeps every scalar a string: safe_load would read `6.10` as 6.1.
        loaded = yaml.load(manifest.read_text(encoding="utf-8"), Loader=yaml.BaseLoader) or {}
        core = (loaded.get("installation") or {}).get("version") if isinstance(loaded, dict) else None
    if core:
        facts.append(fact("bmad_core_version", str(core), rel(manifest), "installation.version"))
    else:
        omit("bmad_core_version", f"installation.version not read from {rel(manifest)}")

    lock = root / "pixi.lock"
    versions = sorted(set(_CONDA_PKG.findall(lock.read_text(encoding="utf-8")))) if lock.is_file() else []
    if len(versions) == 1:
        facts.append(fact("bmad_loop_version", versions[0], "pixi.lock",
                          "version segment of the locked bmad-loop conda package filename"))
    else:
        omit("bmad_loop_version", f"pixi.lock locks {len(versions)} distinct bmad-loop versions: {versions or 'none'}")

    skill = root / ".claude/skills/conda-forge-expert/SKILL.md"
    cfe = frontmatter_scalar(skill, "version")
    if cfe:
        facts.append(fact("cfe_skill_version", cfe, rel(skill), "frontmatter version"))
    else:
        omit("cfe_skill_version", f"no frontmatter version in {rel(skill)}")

    gt = groundtruth(root)
    if gt is None:
        omit("groundtruth_*", f"`{GROUNDTRUTH_SOURCE}` did not return a JSON object")
    else:
        for key in sorted(gt):
            if gt[key] is None:
                omit(f"groundtruth_{key}", f"null in the `{GROUNDTRUTH_SOURCE}` JSON")
            else:
                facts.append(fact(f"groundtruth_{key}", str(gt[key]), GROUNDTRUTH_SOURCE, f"JSON key {key}"))

    recipes = root / "recipes"
    if recipes.is_dir():
        templates = {"example", "examples"}
        n = sum(1 for p in recipes.iterdir()
                if p.is_dir() and not p.name.startswith(".") and p.name not in templates)
        facts.append(fact("recipes_count", str(n), "recipes/",
                          "count of recipes/*/ directories, excluding the staged-recipes "
                          "templates recipes/example/ and recipes/examples/"))
    else:
        omit("recipes_count", "recipes/ not found")

    # --- every deck: the date class
    head = head_info(root)
    facts.append(fact("tree_commit_date", head["short_date"], TREE_DATE_SOURCE, "HEAD commit date (YYYY-MM-DD)"))
    if poster is not None:
        pdate = poster_commit_date(root, poster)
        if pdate:
            facts.append(fact("poster_last_commit_date", pdate, rel(poster),
                              "git log -1 --format=%cs -- <poster> (last commit touching the poster)"))
        else:
            omit("poster_last_commit_date", f"{rel(poster)} has no commit yet")
    else:
        omit("poster_last_commit_date", "no poster")

    # --- the deck's own chain: SPEC.md status + capabilities, Dream status + log dates
    spec_hits = sorted((root / "_bmad-output/projects").glob(
        f"*/planning-artifacts/specs/spec-{slug}/SPEC.md"))
    if len(spec_hits) == 1:
        spec = spec_hits[0]
        status = frontmatter_scalar(spec, "status")
        if status:
            facts.append(fact("spec_status", status, rel(spec), "frontmatter status"))
        else:
            omit("spec_status", f"no frontmatter status in {rel(spec)}")
        split = _frontmatter_split(spec)
        body = split[1] if split else spec.read_text(encoding="utf-8").splitlines()
        defs: dict[str, set[int]] = {}
        for ln in body:
            m = _CAP_DEF.match(ln)
            if m:
                lo, hi = int(m.group(2)), int(m.group(3) or m.group(2))
                defs.setdefault(m.group(1), set()).update(range(lo, hi + 1))
        if len(defs) == 1:
            prefix, nums = next(iter(defs.items()))
            ordered = sorted(nums)
            contiguous = ordered == list(range(1, len(ordered) + 1))
            shown = [f"{prefix}-1..{ordered[-1]}", f"{prefix}-1..{prefix}-{ordered[-1]}"] if contiguous else []
            facts.append(fact("spec_capabilities", str(len(ordered)), rel(spec),
                              "capability definition lines (CAP-N or HER-N), never prose mentions", shown))
        elif not defs:
            omit("spec_capabilities", f"no capability definition lines (- **CAP-N** / - **HER-N**) in {rel(spec)}")
        else:
            omit("spec_capabilities", f"{rel(spec)} defines capabilities under mixed id schemes {sorted(defs)}")
    else:
        omit("spec_status, spec_capabilities",
             f"{len(spec_hits)} SPEC.md match _bmad-output/projects/*/planning-artifacts/specs/spec-{slug}/")

    dream = root / "docs/dreams" / f"{slug}.md"
    dstatus = frontmatter_scalar(dream, "status")
    if dstatus:
        facts.append(fact("dream_status", dstatus, rel(dream), "frontmatter status"))
    else:
        omit("dream_status", f"{rel(dream)} missing or has no frontmatter status")
    if dream.is_file():
        dates = sorted({m.group(1) for ln in dream.read_text(encoding="utf-8").splitlines()
                        if (m := _DREAM_LOG.match(ln))})
        for d in dates:
            facts.append(fact(f"dream_log_{d}", d, rel(dream), "Realization log entry date"))
        if not dates:
            omit("dream_log_*", f"no dated `- **YYYY-MM-DD` entries in {rel(dream)}")
    else:
        omit("dream_log_*", f"{rel(dream)} missing")

    # --- station decks: package, console entry, CLI verbs, test count
    if station in guild:
        pkg_dir = root / "src/shared/packages" / slug
        pyproject = pkg_dir / "pyproject.toml"
        if pyproject.is_file():
            proj = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
            if proj.get("version"):
                facts.append(fact("package_version", str(proj["version"]), rel(pyproject), "project.version"))
            else:
                omit("package_version", f"no project.version in {rel(pyproject)}")
            scripts = proj.get("scripts") or {}
            if scripts:
                name, entry = min(scripts.items())
                facts.append(fact("console_entry", name, rel(pyproject),
                                  "first [project.scripts] key (sorted)"))
                found = cli_verbs(root, pkg_dir, station, entry)
                if found and found[0]:
                    verbs, scanned = found
                    facts.append(fact("cli_verbs", str(len(verbs)), scanned,
                                      'distinct literal add_parser("…") first arguments under the '
                                      "console entry's module (static scan; dynamic add_parser(name) not counted)",
                                      [", ".join(verbs)]))
                else:
                    omit("cli_verbs", f"no literal add_parser(\"…\") calls under {entry}")
            else:
                omit("console_entry, cli_verbs", f"no [project.scripts] in {rel(pyproject)}")
        else:
            omit("package_version, console_entry, cli_verbs", f"{rel(pyproject)} not found")

    if not with_tests:
        omit("tests_collected", "only derived under --with-tests", quiet=True)
    elif station in guild:
        n = tests_collected(root, station)
        if n is not None:
            facts.append(fact("tests_collected", n, " ".join(tests_command(station)),
                              "N from the trailing `N tests collected` line"))
        else:
            omit("tests_collected", f"`{' '.join(tests_command(station))}` failed or printed no count")
    else:
        omit("tests_collected", f"{slug} is not a station: no pyforge-<station> env to collect from")

    # --- genesis: the guild roster and the Dream tier
    if slug == "pyforge-genesis":
        roster = root / "docs/governance/guild-roster.json"
        facts.append(fact("guild_stations", str(len(guild)), rel(roster), "length of stations"))
        counts: dict[str, int] = {}
        for md in sorted((root / "docs/dreams").glob("*.md")):
            st = frontmatter_scalar(md, "status")
            if st:
                counts[st] = counts.get(st, 0) + 1
        facts.append(fact("dreams_total", str(sum(counts.values())), "docs/dreams/*.md",
                          "count of files with a frontmatter status"))
        for st in sorted(counts):
            facts.append(fact(f"dreams_{st}", str(counts[st]), "docs/dreams/*.md",
                              f"count of files whose frontmatter status is {st}"))

    doc = {
        "deck": slug,
        "persona": poster.name[: -len(POSTER_SUFFIX)] if poster else "",
        "derived_at": head["date"],
        "tree": head["sha"] + ("-dirty" if head["dirty"] else ""),
        "facts": sorted(facts, key=lambda f: f["id"]),
    }
    return doc, notes, omitted


def render_yaml(doc: dict) -> str:
    q = lambda s: json.dumps(s, ensure_ascii=False)
    out = [
        "# GENERATED by scripts/deck_facts.py -- do not hand-edit. Regenerate with:",
        f"#     pixi run -e local-recipes deck-facts {doc['deck']}",
        ("# Shape + source catalog: _bmad-output/projects/pyforge-herald/planning-artifacts/"
         "specs/spec-deck-family-currency/facts-ledger.md"),
        f"deck: {doc['deck']}",
        f"persona: {q(doc['persona'])}",
        f"derived_at: {q(doc['derived_at'])}",
        f"tree: {q(doc['tree'])}",
        "facts:" if doc["facts"] else "facts: []",
    ]
    for f in doc["facts"]:
        out += [
            f"  - id: {f['id']}",
            f"    value: {q(f['value'])}",
            f"    source: {q(f['source'])}",
            f"    method: {q(f['method'])}",
            f"    shown_as: [{', '.join(q(s) for s in f['shown_as'])}]",
        ]
    return "\n".join(out) + "\n"


# -------------------------------------------------------------------- check

def _norm(text: str) -> str:
    """Collapse whitespace and close up `94 / 95` so fractions compare as one token."""
    return re.sub(r"\s*/\s*", "/", " ".join(text.split()))


def _join(parts: list[str]) -> str:
    """Visible text from segments: inline boundaries inside a token vanish, every
    other boundary is a space (see _BLOCK_TAGS)."""
    text = _INSIDE_TOKEN_JOIN.sub("", "".join(parts))
    return _norm(text.replace(_INLINE_JOIN, " "))


class _PosterText(HTMLParser):
    """Visible text segments (style/script/title skipped) plus `data-fact` marks.

    Every tag boundary contributes a separator segment -- " " for a block tag,
    the _INLINE_JOIN placeholder otherwise -- which _join() resolves.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.segments: list[tuple[str, str | None]] = []   # (text, mark id or None)
        self.marks: list[tuple[str, str]] = []              # (id, normalized text)
        self._stack: list[str] = []
        self._skip = 0
        self._mark: tuple[str, int, list[str]] | None = None

    def _boundary(self, tag: str) -> None:
        if self._skip or tag in _SKIP_TAGS:
            return
        sep = " " if tag in _BLOCK_TAGS else _INLINE_JOIN
        self.segments.append((sep, self._mark[0] if self._mark else None))

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1
        self._boundary(tag)
        if tag in _VOID_TAGS:
            return
        self._stack.append(tag)
        attr = dict(attrs)
        if "data-fact" in attr and self._mark is None:
            self._mark = (attr["data-fact"] or "", len(self._stack), [])

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1
        if tag in _VOID_TAGS or tag not in self._stack:
            return
        while self._stack and self._stack.pop() != tag:
            pass
        if self._mark and len(self._stack) < self._mark[1]:
            fid, _, buf = self._mark
            self.marks.append((fid, _norm("".join(buf))))
            self._mark = None
        self._boundary(tag)

    def handle_data(self, data):
        if self._skip:
            return
        if self._mark:
            self._mark[2].append(data)
            self.segments.append((data, self._mark[0]))
        else:
            self.segments.append((data, None))


def _shown(literal: str, text: str) -> bool:
    v = "v?" if literal[:1].isdigit() else ""
    return re.search(rf"(?<![\w./-]){v}{re.escape(literal)}(?![\w./-])", text) is not None


def check(root: Path, slug: str, ledger: dict, fresh: dict,
          omitted: list[tuple[list[str], str]] | None = None) -> list[str]:
    rows = {f["id"]: f for f in ledger.get("facts") or []}
    literals = {fid: [str(f["value"]), *(str(s) for s in f.get("shown_as") or [])] for fid, f in rows.items()}
    by_literal: dict[str, str] = {}
    for fid in sorted(rows):
        for lit in literals[fid]:
            by_literal.setdefault(lit, fid)

    def omit_reason(fid: str) -> str | None:
        for patterns, why in omitted or []:
            if any(fnmatch.fnmatchcase(fid, p) for p in patterns):
                return why
        return None

    lines: list[str] = []
    n_unmarked = n_mismatch = n_drifted = n_unsourced = n_unshown = 0
    resolved = shown = 0
    marked_ids: set[str] = set()

    hits = poster_hits(root, slug)
    poster = hits[0] if hits else None
    if poster is None:
        lines.append(f"no poster: presentations/{slug}/project/*{POSTER_SUFFIX}")
        all_text = ""
    else:
        parser = _PosterText()
        parser.feed(poster.read_text(encoding="utf-8"))
        parser.close()
        all_text = _join([t for t, _ in parser.segments])
        for fid, text in parser.marks:
            shown += 1
            marked_ids.add(fid)
            if fid not in rows:
                n_mismatch += 1
                lines.append(f'mismatch  {fid}  shows "{text}" -- no such row in facts.yaml')
            elif _LEADING_V.sub("", text) not in literals[fid]:
                n_mismatch += 1
                lines.append(f'mismatch  {fid}  shows "{text}", ledger "{rows[fid]["value"]}"')
            else:
                resolved += 1
        # Marked segments become a boundary so text on either side never fuses.
        sweep = _join([t if mark is None else " " for t, mark in parser.segments])
        seen: list[str] = []
        for m in _TOKEN.finditer(sweep):
            if m.group(1) not in seen:
                seen.append(m.group(1))
        for tok in seen:
            shown += 1
            if tok in by_literal:
                resolved += 1
            else:
                n_unmarked += 1
                lines.append(f"unmarked  {tok}  no facts.yaml row matches this visible token")

    fresh_rows = {f["id"]: f for f in fresh.get("facts") or []}
    for fid in sorted(set(rows) | set(fresh_rows)):
        lv = rows[fid]["value"] if fid in rows else None
        fv = fresh_rows[fid]["value"] if fid in fresh_rows else None
        if lv == fv:
            continue
        why = omit_reason(fid) if fv is None else None
        if why is not None:
            n_unsourced += 1
            lines.append(f'unsourced  {fid}  ledger "{lv}" -- not derived this run: {why}')
        else:
            n_drifted += 1
            show = lambda v: f'"{v}"' if v is not None else "absent"
            lines.append(f"drifted   {fid}  ledger {show(lv)}, fresh {show(fv)}")

    if poster is not None:
        for fid in sorted(rows):
            if fid in marked_ids or any(_shown(lit, all_text) for lit in literals[fid]):
                continue
            n_unshown += 1
            lines.append(f'unshown   {fid}  "{rows[fid]["value"]}"')

    lines.append(
        f"summary   {slug}: {n_unmarked} unmarked, {n_mismatch} mismatch, {n_drifted} drifted, "
        f"{n_unsourced} unsourced, {n_unshown} unshown; facts {resolved}/{shown}")
    return lines


# --------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug", help="deck directory under presentations/")
    ap.add_argument("--check", action="store_true",
                    help="read the poster against facts.yaml and report findings (advisory, exit 0)")
    ap.add_argument("--with-tests", action="store_true",
                    help="add a tests_collected row (runs the station's pytest --collect-only)")
    args = ap.parse_args(argv)

    root = ROOT
    deck_dir = root / "presentations" / args.slug
    if not deck_dir.is_dir():
        ap.error(f"presentations/{args.slug} not found")
    ledger_file = deck_dir / "facts.yaml"

    fresh, notes, omitted = derive(root, args.slug, with_tests=args.with_tests)
    for note in notes:
        print(note, file=sys.stderr)

    if args.check:
        if not ledger_file.is_file():
            ap.error(f"presentations/{args.slug}/facts.yaml not found -- run: "
                     f"pixi run -e local-recipes deck-facts {args.slug}")
        ledger = yaml.safe_load(ledger_file.read_text(encoding="utf-8")) or {}
        for line in check(root, args.slug, ledger, fresh, omitted):
            print(line)
        return 0

    text = render_yaml(fresh)
    changed = not ledger_file.is_file() or ledger_file.read_text(encoding="utf-8") != text
    ledger_file.write_text(text, encoding="utf-8")
    print(f"{args.slug}: {'wrote' if changed else 'unchanged'} "
          f"presentations/{args.slug}/facts.yaml ({len(fresh['facts'])} facts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
