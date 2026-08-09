"""The board-truthfulness gather filters -- Doctor's verdict on the fleet-
status console + its data feeds (Story 6.5, FR-15).

**Why this module exists, and why it is HERE rather than in ``pyforge.marshal``.**

Charter §6, ratified 2026-07-28: *"the Doctor holds the verdict on the Marshal's
conformance — the one station that would otherwise grade itself."* The Guildhall
board (``docs/dashboard/``) is Marshal's own console, and three read-only judges of
it grew up OUTSIDE Doctor as repo-root scripts: ``scripts/chain_completeness_check.py``
(does every station's plan match its record?), ``scripts/dashboard_drift_check.py``
(does the committed board still match the feeds that fed it?) and
``docs/dashboard/check_layout.py`` (does the board's console bar actually render
without overlapping or clipping?). Story 6.4 proved the ledger port pattern; this
module is the board's turn, porting all three verbatim in behavior.

**The independence rule, which is the entire point of this module:**

    This module reads the DURABLE ARTIFACTS -- tracked planning docs, the
    committed ``data.js``, and (for ``dashboard_drift``) the gitignored Tier-3
    feeds and their tracked twins -- and never imports ``pyforge.marshal`` (or
    any other station package).

Mirrors ``sources/ledger.py``'s and ``sources/marshal.py``'s own independence
rationale exactly: a board-truthfulness verdict assembled from Marshal's own code
would be Marshal's self-report wearing Doctor's badge.
``tests/unit/test_sources_board_independence.py`` pins it.

**Degrades, never crashes** -- the house rule for every Doctor source. Each of
the three gathers below documents its own specific "cannot evaluate" paths; see
each function's own docstring.

**Two independent ``data.js`` readers, deliberately not unified.** ``_board_lines``
(used by ``gather_chain_completeness``) and ``_load_data_js`` (used by
``gather_dashboard_drift``) parse the SAME committed file with two DIFFERENT
methods, because that is what their two respective source scripts already do --
a fixed-prefix strip in one, a regex search in the other. Consolidating them would
be a redesign this story's Boundaries explicitly rule out ("preserve, don't
redesign"); each stays exactly as strict or as lenient as its own original.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("gather_chain_completeness", "gather_check_layout", "gather_dashboard_drift")


# === gather_chain_completeness ==============================================
#
# Ported from scripts/chain_completeness_check.py -- see that script's own
# module docstring for the full three-invariant rationale (Marshal's
# 2/24-decomposed PRD, Doctor's orphan ledger key, Herald's 12/19-vs-47/47
# board) and the fourth (INV-D, a canonical epics doc that parses to zero
# stories, which would let INV-B trivially "pass" over an empty set).
# ``_story_keys_from_ledger`` from the original script is NOT ported: it is
# dead code there (defined, never called by ``check()`` or ``main()``) --
# porting an unused helper would be speculative, not a verbatim behavior port.

#: Spec statuses that represent work still owed -- identical to the original.
OPEN_SPEC_STATUSES = frozenset({"draft", "ready", "in-progress"})

#: Specs deliberately NOT decomposed, each with the reason it is exempt --
#: copied verbatim from scripts/chain_completeness_check.py so a station's
#: recorded exemption is not silently dropped by the port.
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

_CHAIN_DATA_JS_PREFIX = "window.DASHBOARD_DATA = "

#: A ledger story key's leading id, in either shape -- verbatim from the original.
_LEDGER_ID = re.compile(r"^(\d+-\d+|[a-z]+\d+)-")


def _frontmatter(path: Path) -> dict[str, str]:
    """The frontmatter block's top-level ``key: value`` pairs, as raw strings.

    A tiny hand-rolled reader, NOT PyYAML -- this story's Surface excludes
    ``pixi.toml`` (mirrors ``sources/ledger.py``'s/``sources/marshal.py``'s own
    ``_parse_statuses``, adapted from an indented ``development_status:`` block
    to a top-level ``---``-fenced one). ``check()`` only ever reads two flat
    scalar keys off the result (``status``, ``epics_role``), so a nested
    list/mapping value (``surface:``, ``sources:``, ``open_questions:``) is a
    multi-line block this parser does not need to understand -- a value-less
    ``key:`` line and every indented/``-``-prefixed continuation line under it
    are simply skipped rather than parsed.

    Never raises: a missing file, an unreadable one, or a file with no
    frontmatter fence all degrade to ``{}``, mirroring the original script's
    own broad try/except.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 -- mirrors the original's own
        # `except Exception: return {}` (scripts/chain_completeness_check.py's
        # frontmatter()), so a non-UTF-8 SPEC.md degrades the same way here.
        return {}
    if not text.startswith("---"):
        return {}
    out: dict[str, str] = {}
    in_block = False
    for line in text.splitlines():
        if line.strip() == "---":
            if in_block:
                break
            in_block = True
            continue
        if not in_block:
            continue
        if not line or line[0].isspace() or line.startswith("-"):
            continue  # nested list/continuation line -- not a top-level key
        key, sep, value = line.partition(":")
        if sep and key.strip():
            out[key.strip()] = _scalar(value)
    return out


def _scalar(raw: str) -> str:
    """A frontmatter scalar's VALUE, with the two bits of YAML syntax that
    would otherwise silently change a status: an inline ``  # comment`` and
    surrounding quotes.

    The parser this replaced was ``yaml.safe_load``, which decoded both. Left
    raw, ``status: 'draft'`` reads as ``"'draft'"``, misses the
    ``OPEN_SPEC_STATUSES`` membership test, and silently EXEMPTS an open,
    undecomposed Spec -- a false negative in the one check whose whole purpose
    is making "we chose not to" distinguishable from "nobody noticed". Same
    hazard for ``epics_role: "canonical"``, where the miss skips INV-B/INV-D
    entirely. Latent today (no consumed file is quoted) but one line to close,
    and this repo demonstrably writes quoted statuses elsewhere.
    """
    value = raw.strip()
    head, hash_, _ = value.partition(" #")
    if hash_:
        value = head.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def _norm_id(token: str) -> str:
    """``2-1-scaffold-the-kedro`` and ``a1-scaffold-the-kedro`` share a tail --
    verbatim from the original."""
    return token.strip().lower().replace(".", "-")


def _story_ids_from_epics(path: Path) -> list[set[str]]:
    """One id-SET per story -- every id a ``### Story`` heading declares for
    it. Verbatim from the original (see its own docstring for the
    now-retired dual-id rationale)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out: list[set[str]] = []
    for m in re.finditer(r"^###\s+Story\s+(\d+\.\d+[a-z]?)", text, re.MULTILINE):
        out.append({_norm_id(m.group(1))})
    return out


def _ledger_rows(path: Path) -> dict[str, str]:
    """Every ``key: value`` under ``development_status:``, epic rollups
    included -- verbatim from the original (deliberately shape-agnostic; see
    its own docstring for why this counts rows rather than parsing ids)."""
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


def _ledger_story_ids(rows: dict[str, str]) -> tuple[set[str], set[str]]:
    """``(recognised ids, unrecognised keys)`` -- verbatim from the original."""
    ids, unknown = set(), set()
    for key in rows:
        m = _LEDGER_ID.match(key)
        (ids.add(_norm_id(m.group(1))) if m else unknown.add(key))
    return ids, unknown


def _canonical_epics(project_dir: Path) -> Path | None:
    """The one epics doc declaring ``epics_role: canonical``; falls back to
    ``epics.md`` for a project predating the convention -- verbatim from the
    original, using this module's own ``_frontmatter`` in place of PyYAML."""
    pa = project_dir / "planning-artifacts"
    for candidate in sorted(pa.glob("epics*.md")):
        if _frontmatter(candidate).get("epics_role") == "canonical":
            return candidate
    fallback = pa / "epics.md"
    return fallback if fallback.is_file() else None


def _board_lines(data_js: Path) -> dict[str, tuple[int, int]] | None:
    """``{station: (done, total)}`` from ``data.js``, or ``None`` when it
    cannot be read -- verbatim from the original (a fixed-prefix strip, not
    the regex ``gather_dashboard_drift`` uses; see this module's own
    docstring for why the two stay separate)."""
    try:
        text = data_js.read_text(encoding="utf-8")
        if not text.startswith(_CHAIN_DATA_JS_PREFIX):
            return None
        data = json.loads(text[len(_CHAIN_DATA_JS_PREFIX):].rstrip().rstrip(";"))
    except Exception:  # noqa: BLE001 -- "cannot read the generated board" is
        # the one thing this function promises to degrade on, mirroring the
        # original script's own broad except.
        return None
    projects = data.get("projects") if isinstance(data, dict) else None
    if not isinstance(projects, dict):
        # A structurally-wrong-but-valid-JSON board (`projects` a list, a
        # string, or absent) is "cannot read the generated board" -- the one
        # thing this function promises to degrade on -- NOT an AttributeError
        # raised from outside the caller's per-project try. INV-C treats None
        # and {} identically (`board is not None and station in board`), so
        # this only changes which failure mode a broken file produces.
        return None
    out: dict[str, tuple[int, int]] = {}
    for key, proj in projects.items():
        if not isinstance(proj, dict):
            continue  # a malformed data.js entry for ONE station must not
            # take down every other station's INV-C comparison
        epics = proj.get("epics")
        if not isinstance(epics, (list, tuple)):
            continue  # ditto: `epics` as a string/mapping is not an epic list
        stories = [
            s
            for e in epics
            # This guard MUST precede the second `for`, not trail it: a
            # comprehension evaluates the inner iterable BEFORE any trailing
            # `if`, so `e.get(...)` runs on a non-dict `e` regardless. As a
            # trailing filter it silently did nothing -- and because `board`
            # is computed OUTSIDE the per-project try, the resulting
            # AttributeError escaped to the whole-gather `degrade_on_exception`
            # and collapsed EVERY project's real FAIL into one vacuous WARN
            # (exit 0). Adversarial-review regression, reproduced live.
            if isinstance(e, dict)
            for s in (e.get("stories") or [])
            if isinstance(s, (list, tuple)) and s
        ]
        done = sum(1 for s in stories if len(s) > 1 and s[1] == "done")
        out[key] = (done, len(stories))
    return out


def _check_chain_completeness(target: Path) -> list[dict]:
    """Port of the original script's own ``check()`` -- see this module's own
    header and the original's for the full INV-A/B/C/D rationale. Findings
    are structured dicts here rather than printed lines; ``kind``/``detail``/
    ``remedy`` text is unchanged from the original.

    Each project is evaluated inside its own try/except
    (``_check_project_chain_completeness``): one project's malformed input
    (a non-UTF-8 file, an unparseable ledger) must not suppress another,
    ALREADY-COMPUTED project's real FAIL findings -- the same multi-project
    independence discipline ``sources/ledger.py``'s own ``_check`` already
    established ("a regression in one project's ledger must not suppress or
    merge with a regression in another"). Wrapping only the whole function in
    ``degrade_on_exception`` (as the first cut of this port did) does not give
    that guarantee: a single bad project anywhere converts every OTHER
    project's real findings into one vacuous WARN, silently turning a real
    compliance violation into an exit-0 "all clear" -- confirmed by adversarial
    review and reproduced live (non-UTF-8 byte in one project's SPEC.md hid a
    genuine ``spec-not-decomposed`` FAIL in an unrelated, well-formed project).
    """
    projects_dir = target / "_bmad-output" / "projects"
    findings: list[dict] = []
    if not projects_dir.is_dir():
        return findings
    board = _board_lines(target / "docs" / "dashboard" / "data.js")

    for project_dir in sorted(projects_dir.iterdir()):
        if not (project_dir / "planning-artifacts").is_dir():
            continue
        project = project_dir.name
        try:
            findings.extend(_check_project_chain_completeness(project_dir, board))
        except Exception as exc:  # noqa: BLE001 -- one project's failure must
            # not discard every other project's already-computed findings.
            findings.append({
                # NOT "INV-A": this catch wraps the whole INV-A/B/C/D
                # evaluation, so stamping one invariant would point an
                # operator (or an --inv filter) at Spec decomposition when the
                # broken input was, say, the ledger INV-B reads.
                "inv": "", "kind": "chain-completeness-unevaluable",
                "project": project, "subject": project, "status": "",
                "detail": (f"could not be evaluated here — "
                           f"{exc.__class__.__name__}: {exc}"),
                "remedy": "fix the malformed/unreadable input, then re-check",
                "warn": True,
            })
    return findings


def _check_project_chain_completeness(
    project_dir: Path, board: dict[str, tuple[int, int]] | None
) -> list[dict]:
    """One project's INV-A/B/C/D findings -- split out of
    ``_check_chain_completeness`` so its caller can isolate one project's
    failure from the rest (see that function's own docstring)."""
    findings: list[dict] = []
    project = project_dir.name
    station = project.removeprefix("pyforge-")
    pa = project_dir / "planning-artifacts"

    # ---- INV-A: every open Spec is decomposed ---------------------------------
    prose = ""
    for doc in list(pa.glob("prds/*/prd.md")) + list(pa.glob("epics*.md")):
        try:
            prose += doc.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001, S112 -- a non-UTF-8/unreadable
            # prose doc must not abort this project's whole INV-A/B/C/D
            # evaluation; nothing here needs a log line, only degradation.
            continue
    for spec_md in sorted(pa.glob("specs/spec-*/SPEC.md")):
        slug = spec_md.parent.name
        status = str(_frontmatter(spec_md).get("status", "")).strip()
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


def gather_chain_completeness(target: Path) -> tuple[Finding, ...]:
    """Judge whether every station's plan is decomposed and its epics, ledger
    and board agree -- the library form of
    ``scripts/chain_completeness_check.py``'s own ``main()``, minus the
    print/exit CLI surface. Every INV-A/B/C/D violation becomes one FAIL
    ``Finding``; an unreadable/absent ``_bmad-output/projects`` degrades to a
    vacuous OK rather than raising.
    """
    return degrade_on_exception(
        Source.CHAIN_COMPLETENESS,
        "chain-completeness",
        lambda: _gather_chain_completeness(target),
    )


def _gather_chain_completeness(target: Path) -> tuple[Finding, ...]:
    raw = _check_chain_completeness(target)
    if not raw:
        projects_dir = target / "_bmad-output" / "projects"
        n = (
            len([p for p in projects_dir.iterdir() if (p / "planning-artifacts").is_dir()])
            if projects_dir.is_dir()
            else 0
        )
        return (
            Finding(
                source=Source.CHAIN_COMPLETENESS,
                check="chain-completeness",
                status=DoctorStatus.OK,
                message="every open Spec is decomposed, and epics, ledger and board agree",
                evidence={"projects": n},
            ),
        )
    return tuple(
        Finding(
            source=Source.CHAIN_COMPLETENESS,
            check=item["kind"],
            status=DoctorStatus.WARN if item.get("warn") else DoctorStatus.FAIL,
            message=f"{item['project']}: {item['detail']}",
            evidence={
                "inv": item["inv"],
                "project": item["project"],
                "subject": item["subject"],
                "status": item["status"],
                "remedy": item["remedy"],
            },
        )
        for item in raw
    )


# === gather_dashboard_drift (scope="runtime") ===============================
#
# Ported from scripts/dashboard_drift_check.py -- see that script's own module
# docstring for the full three-way rationale (stale-done, missing-story,
# twin-stale/twin-missing/twin-ahead) and why this check is LOCAL-ONLY: it
# reads each project's gitignored Tier-3 `sprint-status.yaml`, invisible to CI.

_DRIFT_STORY_HEADING = re.compile(r"^###\s+Story\s+([0-9]+\.[0-9]+[a-z]?)\s*[:—-]")
_DRIFT_DONE = frozenset({"done"})


def _load_dashboard_generate(target: Path):
    """Import ``target/docs/dashboard/generate.py`` so its parsers are REUSED,
    never reimplemented -- the same ``importlib.util.spec_from_file_location``
    dynamic load ``dashboard_drift_check.py``'s own ``_load_generate`` already
    uses, resolved against ``target`` rather than a hardcoded path (Boundaries).
    ``parse_sprint_status``/``dashboard_id_to_status``/``PROJECT_SOURCES`` etc.
    already encode the feed-key -> board-id mapping; duplicating them here
    would let the two drift, which is the class of bug the original script --
    and this port -- exist to catch.
    """
    path = target / "docs" / "dashboard" / "generate.py"
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found")
    spec = importlib.util.spec_from_file_location(
        "_doctor_board_dashboard_generate", path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load a module spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_doctor_board_dashboard_generate"] = mod
    # generate.py does an unguarded `sys.path.insert(0, REPO_ROOT/"scripts")`
    # at import time. Harmless in the one-shot script this was ported from;
    # here it permanently prepends an ARBITRARY `target`'s scripts/ to the
    # Doctor process's import path (and grows it on every call), so a later
    # import inside Doctor could resolve against a foreign tree. Snapshot and
    # restore -- the module object we return is unaffected.
    saved_path = list(sys.path)
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop("_doctor_board_dashboard_generate", None)
        raise
    finally:
        sys.path[:] = saved_path
    return mod


def _load_data_js(target: Path) -> dict:
    """Port of ``dashboard_drift_check.py``'s own ``_load_data_js`` -- with
    one deliberate change. The original ``raise SystemExit(...)`` on an
    unparseable ``data.js`` is replaced with a plain ``ValueError``:
    ``SystemExit`` is a ``BaseException``, not an ``Exception``, so
    ``sources.degrade_on_exception`` (which ``gather_dashboard_drift`` wraps
    itself in) would never catch it, and it would escape this library call
    exactly like the CLI script's own ``exit`` was never meant to (Boundaries:
    "the gather itself must not raise it").
    """
    data_js = target / "docs" / "dashboard" / "data.js"
    text = data_js.read_text(encoding="utf-8")
    m = re.search(r"window\.DASHBOARD_DATA\s*=\s*(\{.*?\});?\s*$", text, re.DOTALL)
    if not m:
        raise ValueError(f"cannot parse {data_js}")
    return json.loads(m.group(1))


def _drift_epics_md_ids(path: Path) -> list[tuple[str, str | None]]:
    """Every story heading in an epics.md as ``(id, None)`` -- verbatim from
    the original (the second tuple slot is a retired dual-id accommodation;
    see the original's own docstring)."""
    out: list[tuple[str, str | None]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _DRIFT_STORY_HEADING.match(line)
        if m:
            out.append((m.group(1), None))
    return out


def _check_dashboard_drift(target: Path, gen, data: dict) -> list[dict]:
    """Port of ``dashboard_drift_check.py``'s own ``main()`` body -- the three
    checks (tracked twin vs. Tier-3 feed, committed baseline vs. feed,
    epics.md vs. board), producing structured dicts instead of printed lines.
    ``kind``/message text is unchanged from the original."""
    # `.get(k, default)` does NOT coerce a present-but-null key, so a
    # `{"projects": null}` data.js yielded None and raised AttributeError
    # from OUTSIDE the per-station try (mirrors _board_lines' own `or {}`).
    projects = data.get("projects") or {}
    if not isinstance(projects, dict):
        projects = {}
    findings: list[dict] = []

    for key, proj in sorted(projects.items()):
        try:
            findings.extend(_check_project_dashboard_drift(target, gen, key, proj))
        except Exception as exc:  # noqa: BLE001 -- one station's malformed
            # data.js entry or feed must not discard every other station's
            # already-computed drift findings (mirrors
            # _check_chain_completeness's own per-project isolation).
            findings.append({
                "kind": "dashboard-drift-unevaluable", "project": key,
                "detail": (f"{key}: could not be evaluated here — "
                           f"{exc.__class__.__name__}: {exc}"),
                "warn": True,
            })
    return findings


def _check_project_dashboard_drift(target: Path, gen, key: str, proj: object) -> list[dict]:
    """One station's drift findings -- split out of ``_check_dashboard_drift``
    so its caller can isolate one station's failure from the rest."""
    findings: list[dict] = []
    if not isinstance(proj, dict):
        return findings  # a malformed data.js entry has no epics to compare
    all_stories = [
        s for e in proj.get("epics", []) or []
        if isinstance(e, dict)
        for s in e.get("stories", []) or []
        if isinstance(s, (list, tuple)) and s
    ]
    # `stories` is the (id, status) unpacking set -- it needs >= 2 elements.
    # `board_ids` is a pure MEMBERSHIP set and needs only s[0], so it must be
    # built from the unfiltered list: filtering a 1-element `["1.1"]` out of
    # board_ids made a story that IS on the board look absent, emitting a
    # false `missing-story` FAIL.
    stories = [s for s in all_stories if len(s) >= 2]
    board_ids = {s[0] for s in all_stories}

    # --- twin vs the Tier-3 feed --------------------------------------
    rel_feed = gen.PROJECT_SOURCES.get(key)
    slug_ = gen._KEY_SLUG_OVERRIDE.get(key, f"pyforge-{key}")
    twin = (target / "_bmad-output" / "projects" / slug_
            / "planning-artifacts" / "sprint-status-ledger.yaml")
    feed_p = target / rel_feed if rel_feed else None
    if feed_p and feed_p.is_file() and twin.is_file():
        feed_map = gen.parse_sprint_status(feed_p)
        twin_map = gen.parse_sprint_status(twin)
        drifted = sorted(
            k for k in set(feed_map) | set(twin_map)
            if feed_map.get(k) != twin_map.get(k)
        )
        if drifted:
            shown = ", ".join(drifted[:4]) + ("…" if len(drifted) > 4 else "")
            regressing = sorted(
                k for k in drifted
                if twin_map.get(k) == "done" and feed_map.get(k) != "done"
            )
            if regressing:
                rshown = ", ".join(regressing[:4]) + ("…" if len(regressing) > 4 else "")
                findings.append({
                    "kind": "twin-ahead", "project": key,
                    "detail": (
                        f"{key}: the Tier-3 feed is BEHIND the tracked "
                        f"ledger — it would un-finish {len(regressing)} story(ies) "
                        f"({rshown}). **Do NOT run sprint-ledger-sync**: the twin is "
                        f"the durable record and the feed is the lossy one. Repair the "
                        f"feed from the twin (`sprint-ledger-sync --repair-feed "
                        f"--project {key}`), then re-check."
                    ),
                })
            else:
                findings.append({
                    "kind": "twin-stale", "project": key,
                    "detail": (
                        f"{key}: the tracked sprint-status ledger disagrees "
                        f"with the Tier-3 feed on {len(drifted)} story(ies) ({shown}), "
                        f"none of them un-finishing a story. CI reads the TWIN, so the "
                        f"deploy would render the stale set: run `pixi run -e "
                        f"local-recipes sprint-ledger-sync --project {key}` and commit."
                    ),
                })
    elif feed_p and feed_p.is_file() and not twin.is_file():
        findings.append({
            "kind": "twin-missing", "project": key,
            "detail": (
                f"{key}: has a Tier-3 sprint feed but no tracked "
                f"ledger at {twin.relative_to(target)} — CI cannot see this "
                f"project's completions and will fall back to commit archaeology. "
                f"Run `pixi run -e local-recipes sprint-ledger-sync`."
            ),
        })

    # --- committed baseline vs the local feed ---------------------------
    rel = gen.PROJECT_SOURCES.get(key)
    feed_path = target / rel if rel else None
    if feed_path and feed_path.is_file():
        sprint = gen.parse_sprint_status(feed_path)
        for sid, status, *_rest in stories:
            feed = gen.dashboard_id_to_status(sid, sprint)
            if feed is None:
                continue
            if feed in _DRIFT_DONE and status not in _DRIFT_DONE:
                findings.append({
                    "kind": "stale-done", "project": key,
                    "detail": (
                        f"{key}:{sid} is '{feed}' in the sprint feed but "
                        f"'{status}' on the board — the committed baseline is behind. "
                        f"`--source git` never downgrades, so this will NOT self-heal "
                        f"at deploy: run `pixi run -e local-recipes dashboard-gen` and "
                        f"commit data.js."
                    ),
                })

    # --- no epics.md story is missing from the board --------------------
    slug = gen._KEY_SLUG_OVERRIDE.get(key, f"pyforge-{key}")
    epics_md = (target / "_bmad-output" / "projects" / slug
                / "planning-artifacts" / "epics.md")
    if not epics_md.is_file() or key in getattr(gen, "_DERIVE_EXCLUDE", set()):
        return findings
    heading_ids = _drift_epics_md_ids(epics_md)
    if not heading_ids:
        return findings
    for lead, alt in heading_ids:
        if lead in board_ids or (alt and alt in board_ids):
            continue
        shown = f"{lead}" + (f" ({alt})" if alt else "")
        findings.append({
            "kind": "missing-story", "project": key,
            "detail": (
                f"{key}: epics.md has Story {shown} but no story with "
                f"that id is on the board. If this line's story list is hand-authored "
                f"(scan_projects warns when it cannot parse the headings), add it to "
                f"data.js by hand."
            ),
        })
    return findings


def gather_dashboard_drift(target: Path) -> tuple[Finding, ...]:
    """Judge whether the committed ``data.js`` and its tracked ledger twins
    still match the (gitignored, LOCAL-ONLY) Tier-3 sprint feeds -- the
    library form of ``scripts/dashboard_drift_check.py``'s own ``main()``,
    minus the print/exit CLI surface.

    ``scope="runtime"`` -- the epic's first (Design Notes): no dispatcher
    exists yet to call this gather, so it self-guards with
    ``sources.degrade_on_exception`` wrapped around its own host-state reads
    (dynamically loading ``generate.py``, parsing ``data.js``, globbing the
    Tier-3 feeds) rather than relying on an external wrapper that does not
    exist in this story. Every failure mode the original script
    printed-and-exited on -- a missing/unparseable ``data.js``, an unreadable
    Tier-3 feed, a missing twin -- becomes a Finding inside this gather
    itself; nothing here raises out to the caller.
    """
    return degrade_on_exception(
        Source.DASHBOARD_DRIFT,
        "dashboard-drift",
        lambda: _gather_dashboard_drift(target),
    )


def _gather_dashboard_drift(target: Path) -> tuple[Finding, ...]:
    gen = _load_dashboard_generate(target)
    data = _load_data_js(target)
    # `.get(k, default)` does NOT coerce a present-but-null key, so a
    # `{"projects": null}` data.js yielded None and raised AttributeError
    # from OUTSIDE the per-station try (mirrors _board_lines' own `or {}`).
    projects = data.get("projects") or {}
    if not isinstance(projects, dict):
        projects = {}
    raw = _check_dashboard_drift(target, gen, data)
    if not raw:
        return (
            Finding(
                source=Source.DASHBOARD_DRIFT,
                check="dashboard-drift",
                status=DoctorStatus.OK,
                message=(
                    "the committed data.js matches the feeds, every epics.md story "
                    "is on the board, and every tracked ledger matches its Tier-3 feed"
                ),
                evidence={"projects": len(projects)},
            ),
        )
    return tuple(
        Finding(
            source=Source.DASHBOARD_DRIFT,
            check=item["kind"],
            status=DoctorStatus.WARN if item.get("warn") else DoctorStatus.FAIL,
            message=item["detail"],
            evidence={"project": item["project"]},
        )
        for item in raw
    )


# === gather_check_layout =====================================================
#
# Ported from docs/dashboard/check_layout.py -- see that script's own module
# docstring for the full "why measure geometry, not just execution" rationale
# and the two live incidents (a broken status chip surviving three green
# gates; the running chip's own fix trading one visual bug for another). The
# assertions (edges/no-overlap/one-row/in-bounds/not-clipped) live in that
# script's own pure ``check()``/``_rows()`` and are reused verbatim, never
# re-derived (Design Notes) -- the only NEW code here is the browser/HTTP
# orchestration.

_LAYOUT_CHECK = "console-bar-layout"


def _load_check_layout(target: Path):
    """Dynamically import ``target/docs/dashboard/check_layout.py`` -- same
    technique as ``_load_dashboard_generate`` above. Importing it does NOT
    require ``playwright``: that script's own ``from playwright.sync_api
    import sync_playwright`` sits inside its ``main()``, guarded by its own
    try/except, never at module level -- so this module can load ``check()``,
    ``_rows()``, ``_serve()`` and the probe constants in an environment where
    ``playwright`` is not installed at all (this package's own pixi env)."""
    path = target / "docs" / "dashboard" / "check_layout.py"
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found")
    spec = importlib.util.spec_from_file_location(
        "_doctor_board_check_layout", path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load a module spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_doctor_board_check_layout"] = mod
    spec.loader.exec_module(mod)
    return mod


def _layout_warn(message: str, target: Path) -> tuple[Finding, ...]:
    return (
        Finding(
            source=Source.CHECK_LAYOUT,
            check=_LAYOUT_CHECK,
            status=DoctorStatus.WARN,
            message=message,
            evidence={"target": str(target)},
        ),
    )


def gather_check_layout(target: Path) -> tuple[Finding, ...]:
    """Judge whether the Guildhall console bar's status chips actually
    render without overlapping, clipping, or escaping the bar -- the library
    form of ``docs/dashboard/check_layout.py``'s own ``main()``, minus the
    print/exit CLI surface.

    NEVER CLAIMS GREEN IT DID NOT MEASURE, mirroring the original's own
    contract (its docstring: "a detector that cannot run reports unknown,
    never green"). A missing ``check_layout.py``, a missing ``data.js``, an
    unimportable ``playwright``, no launchable chromium, or a bar that never
    rendered at any width all degrade to exactly ONE WARN ``Finding`` --
    never a FAIL, never a raised exception. ``playwright`` stays an optional,
    try/except-guarded import here: this package's pixi env does not install
    it (Boundaries).
    """
    try:
        clm = _load_check_layout(target)
    except Exception as exc:  # noqa: BLE001 -- "cannot even load the script
        # that owns the assertions" is itself a cannot-evaluate WARN.
        return _layout_warn(
            f"console-bar layout could not be evaluated here — "
            f"{exc.__class__.__name__}: {exc}",
            target,
        )

    try:
        data_js = target / "docs" / "dashboard" / "data.js"
        if not data_js.is_file():
            return _layout_warn(f"{data_js} is absent — run `dashboard-gen` first", target)
    except OSError as exc:  # a permission/loop error on the stat itself
        return _layout_warn(
            f"data.js could not be stat'd — {exc.__class__.__name__}: {exc}", target
        )

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001 -- an INSTALLED-but-broken
        # playwright raises far more than ImportError (an ABI RuntimeError, an
        # OSError for a missing libnss3.so). This import sits OUTSIDE the
        # degrade_on_exception wrap below, so a narrow `except ImportError`
        # let those escape the gather entirely -- breaking this function's own
        # documented "never a raised exception" contract.
        return _layout_warn(
            f"playwright is not usable — {exc.__class__.__name__}: {exc}", target
        )

    return degrade_on_exception(
        Source.CHECK_LAYOUT,
        _LAYOUT_CHECK,
        lambda: _run_check_layout(target, clm, sync_playwright),
    )


def _run_check_layout(target: Path, clm, sync_playwright) -> tuple[Finding, ...]:
    """The NEW orchestration: launch a browser, serve ``target/docs/dashboard/``
    over the reused ``_serve()``, measure the console bar at every width x
    font-pressure combination the original script defines, and hand each
    width's probe result to the reused ``check()``. Every explicit ``exit 2``
    branch the original had (no usable chromium, the bar never rendering)
    becomes a WARN ``Finding`` here instead of a process exit."""
    httpd, port = clm._serve(clm.HERE)
    url = f"http://127.0.0.1:{port}/index.html"
    raw_findings: list[str] = []
    measured = 0
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome")
            except Exception:  # noqa: BLE001 -- fall back to the bundled chromium
                try:
                    browser = p.chromium.launch()
                except Exception as exc:  # noqa: BLE001 -- no usable browser at all
                    return _layout_warn(
                        f"no usable chromium ({type(exc).__name__}) — cannot measure layout",
                        target,
                    )
            try:
                for width in (*clm.WIDE, *clm.NARROW):
                    # Per-width isolation: a `networkidle` goto with a 20s
                    # timeout makes a single width's flake the EXPECTED failure
                    # mode. Without this guard one late failure unwound the
                    # whole loop and discarded every already-measured FAIL,
                    # reporting a genuinely broken bar as "could not evaluate"
                    # -- the same finding-masking class fixed per-project in
                    # _check_chain_completeness.
                    try:
                        page = browser.new_page(viewport={"width": width, "height": 900})
                        try:
                            page.goto(url, wait_until="networkidle", timeout=20000)
                            page.wait_for_timeout(250)
                            for fs in clm.PRESSURES:
                                name = f"{fs}px"
                                page.evaluate(clm.APPLY, fs)
                                page.wait_for_timeout(60)
                                m = page.evaluate(clm.PROBE)
                                if not m:
                                    raw_findings.append(
                                        f"w={width} [{name}]: .cbstatus not found — "
                                        f"the bar did not render"
                                    )
                                    continue
                                measured += 1
                                raw_findings += clm.check(width, m, name)
                        finally:
                            page.close()
                    except Exception as exc:  # noqa: BLE001, PERF203
                        raw_findings.append(
                            f"w={width}: could not be measured — "
                            f"{exc.__class__.__name__}: {exc}"
                        )
                        continue
            finally:
                browser.close()
    finally:
        # shutdown() only stops serve_forever's loop; without server_close()
        # the listening socket stays open, leaking one fd (and one held
        # ephemeral port) per call. Harmless in the one-shot CLI this was
        # ported from, unbounded in a long-lived library caller.
        httpd.shutdown()
        httpd.server_close()

    if not measured:
        return _layout_warn("the bar never rendered at any width", target)

    if not raw_findings:
        return (
            Finding(
                source=Source.CHECK_LAYOUT,
                check=_LAYOUT_CHECK,
                status=DoctorStatus.OK,
                message=(
                    f"console bar edges held, no overlap — {measured} measurement(s): "
                    f"{len(clm.WIDE) + len(clm.NARROW)} width(s) x "
                    f"{len(clm.PRESSURES)} font-pressure step(s)"
                ),
                evidence={"measured": measured},
            ),
        )
    return tuple(
        Finding(
            source=Source.CHECK_LAYOUT,
            check=_LAYOUT_CHECK,
            status=DoctorStatus.FAIL,
            message=finding_text,
            evidence={"measured": measured},
        )
        for finding_text in raw_findings
    )
